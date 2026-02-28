"""Auth helpers: OTP, JWT, password hashing, SMS dispatch."""

from __future__ import annotations

import hashlib
import logging
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from jose import jwt
from passlib.context import CryptContext
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=settings.OTP_LENGTH))


def _otp_key(phone: str) -> str:
    return f"otp:{phone}"


async def store_otp(phone: str, otp: str, redis: Redis) -> None:
    ttl = settings.OTP_EXPIRY_MINUTES * 60
    await redis.setex(_otp_key(phone), ttl, otp)


async def verify_otp(phone: str, otp: str, redis: Redis) -> bool:
    stored: bytes | None = await redis.get(_otp_key(phone))
    if stored is None:
        return False
    if stored.decode() != otp:
        return False
    await redis.delete(_otp_key(phone))  # one-time use
    return True


# ---------------------------------------------------------------------------
# SMS dispatch
# ---------------------------------------------------------------------------


async def send_otp_sms(phone: str, otp: str) -> None:
    """Dispatch OTP via configured SMS provider.

    Currently a stub that logs to console. Wire up Clickatell / BulkSMS
    by setting SMS_PROVIDER and SMS_API_KEY in the environment.
    """
    if settings.ENVIRONMENT != "development" and settings.SMS_API_KEY:
        await _send_via_provider(phone, otp)
    else:
        logger.info("[SMS stub] OTP %s → %s", otp, phone)


async def _send_via_provider(phone: str, otp: str) -> None:
    message = f"Your BellBook code is {otp}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes."
    if settings.SMS_PROVIDER == "clickatell":
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://platform.clickatell.com/messages/http/send",
                params={"apiKey": settings.SMS_API_KEY, "to": phone, "content": message},
                timeout=10,
            )
            resp.raise_for_status()
    else:
        logger.warning("Unknown SMS_PROVIDER '%s'; SMS not sent.", settings.SMS_PROVIDER)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + expires_delta}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    user_id: str,
    school_id: str | None,
    role: str,
) -> str:
    return _create_token(
        {"sub": user_id, "school_id": school_id, "role": role, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises jose.JWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# Refresh-token store  (Redis)
# ---------------------------------------------------------------------------


def _refresh_key(user_id: str, token: str) -> str:
    digest = hashlib.sha256(token.encode()).hexdigest()[:24]
    return f"refresh:{user_id}:{digest}"


async def store_refresh_token(user_id: str, token: str, redis: Redis) -> None:
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400
    await redis.setex(_refresh_key(user_id, token), ttl, "1")


async def is_refresh_token_valid(user_id: str, token: str, redis: Redis) -> bool:
    return bool(await redis.exists(_refresh_key(user_id, token)))


async def revoke_refresh_token(user_id: str, token: str, redis: Redis) -> None:
    await redis.delete(_refresh_key(user_id, token))
