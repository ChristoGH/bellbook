"""Authentication endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.auth import (
    EmailLoginSchema,
    OTPRequestSchema,
    OTPVerifySchema,
    RefreshRequest,
    RegisterSchema,
    TokenResponse,
    UserOut,
)
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    is_refresh_token_valid,
    revoke_refresh_token,
    send_otp_sms,
    store_otp,
    store_refresh_token,
    verify_otp,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer()


def _make_tokens(user: User) -> dict:
    school_id_str = str(user.school_id) if user.school_id else None
    access = create_access_token(str(user.id), school_id_str, user.role)
    refresh = create_refresh_token(str(user.id))
    return {"access": access, "refresh": refresh}


# ---------------------------------------------------------------------------
# OTP request
# ---------------------------------------------------------------------------


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def otp_request(
    body: OTPRequestSchema,
    redis: Redis = Depends(get_redis),
) -> dict:
    """Generate a 6-digit OTP and send it via SMS to the given phone number."""
    otp = generate_otp()
    await store_otp(body.phone, otp, redis)
    await send_otp_sms(body.phone, otp)
    return {"detail": "OTP sent"}


# ---------------------------------------------------------------------------
# OTP verify  (for existing parent accounts)
# ---------------------------------------------------------------------------


@router.post("/otp/verify", response_model=TokenResponse)
async def otp_verify(
    body: OTPVerifySchema,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """Verify OTP and return tokens for an existing parent user.

    The school context must be provided via the X-School-ID request header
    (or derived from the subdomain by the middleware) so that RLS can scope
    the user lookup correctly.
    """
    if not await verify_otp(body.phone, body.otp, redis):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

    result = await db.execute(select(User).where(User.phone == body.phone, User.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for this phone number. Please register first.",
        )

    tokens = _make_tokens(user)
    await store_refresh_token(str(user.id), tokens["refresh"], redis)
    return TokenResponse(access_token=tokens["access"], refresh_token=tokens["refresh"])


# ---------------------------------------------------------------------------
# Parent self-registration
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterSchema,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """Register a new parent account via phone OTP.

    The school_id is encoded in the invite link sent by the school admin.
    """
    if not await verify_otp(body.phone, body.otp, redis):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

    # The school_id comes from the invite link body, not from a JWT.
    # Explicitly set the RLS context so all subsequent queries on this session
    # are scoped to the correct school.
    await db.execute(text("SET LOCAL app.current_school_id = :sid"), {"sid": str(body.school_id)})

    # Guard: phone must not already be registered in this school
    existing = await db.execute(
        select(User).where(User.phone == body.phone, User.school_id == body.school_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered")

    user = User(
        id=uuid.uuid4(),
        school_id=body.school_id,
        phone=body.phone,
        first_name=body.first_name,
        last_name=body.last_name,
        role="parent",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = _make_tokens(user)
    await store_refresh_token(str(user.id), tokens["refresh"], redis)
    return TokenResponse(access_token=tokens["access"], refresh_token=tokens["refresh"])


# ---------------------------------------------------------------------------
# Email + password login  (teacher / school_admin)
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(
    body: EmailLoginSchema,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """Login with email and password (teachers and school admins)."""
    result = await db.execute(
        select(User).where(User.email == body.email, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    tokens = _make_tokens(user)
    await store_refresh_token(str(user.id), tokens["refresh"], redis)
    return TokenResponse(access_token=tokens["access"], refresh_token=tokens["refresh"])


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise exc

    if payload.get("type") != "refresh":
        raise exc

    user_id = payload.get("sub")
    if not user_id:
        raise exc

    if not await is_refresh_token_valid(user_id, body.refresh_token, redis):
        raise exc

    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise exc

    # Rotate: revoke old, issue new
    await revoke_refresh_token(user_id, body.refresh_token, redis)
    tokens = _make_tokens(user)
    await store_refresh_token(str(user.id), tokens["refresh"], redis)
    return TokenResponse(access_token=tokens["access"], refresh_token=tokens["refresh"])


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    redis: Redis = Depends(get_redis),
) -> None:
    """Revoke the refresh token. The short-lived access token expires naturally."""
    try:
        payload = decode_token(body.refresh_token)
        user_id = payload.get("sub")
        if user_id:
            await revoke_refresh_token(user_id, body.refresh_token, redis)
    except JWTError:
        pass  # treat invalid tokens as already revoked


# ---------------------------------------------------------------------------
# Current user (convenience)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
