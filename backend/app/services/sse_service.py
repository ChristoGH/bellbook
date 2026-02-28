"""Server-Sent Events connection manager.

Phase 1: single-process in-memory queues keyed by user_id.

For multi-process / multi-node deployments (Phase 2+) replace with a
Redis pub/sub backend so events reach clients regardless of which
worker process holds the SSE connection.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_QUEUE_MAXSIZE = 64  # drop events silently if a slow client falls this far behind


class SSEManager:
    def __init__(self) -> None:
        # user_id → set of per-connection asyncio queues
        self._connections: dict[str, set[asyncio.Queue]] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, user_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._connections.setdefault(user_id, set()).add(q)
        logger.debug("SSE connected user=%s open_connections=%d", user_id, len(self._connections[user_id]))
        return q

    def disconnect(self, user_id: str, queue: asyncio.Queue) -> None:
        conns = self._connections.get(user_id)
        if conns:
            conns.discard(queue)
            if not conns:
                del self._connections[user_id]
        logger.debug("SSE disconnected user=%s", user_id)

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    async def send_to_user(self, user_id: str, event: dict[str, Any]) -> None:
        queues = self._connections.get(user_id)
        if not queues:
            return
        payload = json.dumps(event)
        for q in set(queues):  # snapshot to avoid mutation during iteration
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("SSE queue full for user=%s; dropping event", user_id)

    async def broadcast(self, user_ids: list[str], event: dict[str, Any]) -> None:
        """Send an event to multiple users in parallel."""
        if not user_ids:
            return
        await asyncio.gather(*(self.send_to_user(uid, event) for uid in user_ids))


# Singleton — imported by the events endpoint and the announcements router.
manager = SSEManager()
