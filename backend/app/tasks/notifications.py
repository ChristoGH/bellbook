"""ARQ background tasks for push notification dispatch.

Stub implementation — full FCM / WhatsApp / SMS pipeline in Prompt 6.

ARQ tasks receive a `ctx` dict as their first argument (the worker context).
In Prompt 6, ctx will contain a Redis connection and the firebase-admin app.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def send_announcement_notifications(
    ctx: dict,
    announcement_id: str,
    recipient_ids: list[str],
) -> None:
    """Dispatch push notifications for a newly published announcement.

    Priority:
      1. FCM push (primary)
      2. WhatsApp Business API (if priority == 'urgent' and user opted in)
      3. SMS fallback (if no registered push device)
    """
    logger.info(
        "[ARQ stub] send_announcement_notifications announcement=%s recipients=%d",
        announcement_id,
        len(recipient_ids),
    )
    # TODO (Prompt 6): implement FCM + WhatsApp + SMS dispatch with retries


class WorkerSettings:
    """ARQ worker settings — wired up in Prompt 6."""

    functions = [send_announcement_notifications]
    # redis_settings will be added in Prompt 6
