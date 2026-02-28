"""Server-Sent Events stream endpoint.

SSE doesn't allow custom request headers, so the JWT is passed as a
query parameter (?token=<access_token>).  The middleware won't have set
request.state.school_id from the Authorization header, but SSE is a
read-only stream — no DB writes happen here, so RLS is not a concern.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request, status
from jose import JWTError
from sse_starlette.sse import EventSourceResponse

from app.services.auth_service import decode_token
from app.services.sse_service import manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])

_KEEPALIVE_INTERVAL = 15  # seconds


@router.get("/stream")
async def stream(
    request: Request,
    token: str = Query(..., description="JWT access token (query param — SSE limitation)"),
) -> EventSourceResponse:
    """Authenticated SSE stream.

    Event payload shape:
        {"type": "announcement.new", ...}
        {"type": "message.new", ...}
        {"type": "connected", "user_id": "..."}
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    async def event_generator():
        queue = await manager.connect(user_id)
        try:
            # Confirm connection
            yield {"data": json.dumps({"type": "connected", "user_id": user_id})}

            while True:
                if await request.is_disconnected():
                    logger.debug("SSE client disconnected user=%s", user_id)
                    break
                try:
                    payload_str = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_INTERVAL)
                    yield {"data": payload_str}
                except asyncio.TimeoutError:
                    # SSE comment line — keeps the connection alive through proxies
                    yield {"comment": "keepalive"}
        finally:
            manager.disconnect(user_id, queue)

    return EventSourceResponse(event_generator())
