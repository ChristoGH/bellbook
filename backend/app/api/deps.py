"""FastAPI dependency functions shared across routers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.auth_service import decode_token

_bearer = HTTPBearer()

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


# ---------------------------------------------------------------------------
# Database — sets app.current_school_id for RLS on every connection
# ---------------------------------------------------------------------------


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    school_id: str | None = getattr(request.state, "school_id", None)
    async with AsyncSessionLocal() as session:
        if school_id:
            # SET LOCAL is transaction-scoped; safe even with connection pooling.
            await session.execute(
                text("SET LOCAL app.current_school_id = :sid"),
                {"sid": str(school_id)},
            )
        yield session


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise exc

    if payload.get("type") != "access":
        raise exc

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise exc

    try:
        user = await db.get(User, uuid.UUID(user_id_str))
    except ValueError:
        raise exc

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    return user


# ---------------------------------------------------------------------------
# Role guard — usage: Depends(require_role("school_admin", "teacher"))
# ---------------------------------------------------------------------------


def require_role(*roles: str):
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check
