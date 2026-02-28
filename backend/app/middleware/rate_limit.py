"""Redis fixed-window rate limiter for messaging."""

from redis.asyncio import Redis


async def check_message_rate_limit(user_id: str, redis: Redis) -> bool:
    """Fixed-window rate limiter: 30 messages per user per hour.

    Returns True if the request is within limits, False if exceeded.
    Uses INCR + EXPIRE (atomic on first call; safe for Phase 1 single-process).
    """
    key = f"rate:msg:{user_id}"
    count = await redis.incr(key)
    if count == 1:
        # First message in this window — set 1-hour TTL
        await redis.expire(key, 3600)
    return count <= 30
