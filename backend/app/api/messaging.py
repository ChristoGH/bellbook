"""Direct messaging endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, get_redis
from app.middleware.rate_limit import check_message_rate_limit
from app.models.messaging import Conversation, ConversationParticipant, Message
from app.models.notification import AuditLog
from app.models.user import User
from app.schemas.messaging import (
    BlockRequest,
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
    MuteRequest,
    ParticipantOut,
)
from app.services.sse_service import manager as sse_manager

router = APIRouter(prefix="/api/conversations", tags=["messaging"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_admin(user: User) -> bool:
    return user.role in ("school_admin", "super_admin")


async def _get_conversation_or_403(
    conversation_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Conversation:
    """Fetch a conversation and verify the current user is a participant (admins bypass)."""
    conv = await db.get(
        Conversation,
        conversation_id,
        options=[selectinload(Conversation.participants)],
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if not _is_admin(current_user):
        participant_ids = {p.user_id for p in conv.participants}
        if current_user.id not in participant_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")

    return conv


async def _log_admin_access(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    request: Request,
) -> None:
    """Log school_admin access to a conversation in audit_log."""
    entry = AuditLog(
        school_id=user.school_id,
        user_id=user.id,
        action="view_conversation",
        entity_type="conversation",
        entity_id=conversation_id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(entry)
    await db.flush()


async def _build_participant_list(
    conversation_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[list[ParticipantOut], dict[uuid.UUID, datetime | None]]:
    """Return (participant_out_list, {user_id: last_read_at}) for a conversation."""
    stmt = (
        select(ConversationParticipant, User)
        .join(User, User.id == ConversationParticipant.user_id)
        .where(ConversationParticipant.conversation_id == conversation_id)
    )
    rows = list((await db.execute(stmt)).all())

    participants: list[ParticipantOut] = []
    last_read_map: dict[uuid.UUID, datetime | None] = {}

    for cp, user in rows:
        participants.append(
            ParticipantOut(
                user_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                avatar_url=user.avatar_url,
                is_muted=cp.is_muted,
                is_blocked=cp.is_blocked,
            )
        )
        last_read_map[user.id] = cp.last_read_at

    return participants, last_read_map


async def _build_conversation_out(
    conv: Conversation,
    current_user_id: uuid.UUID,
    db: AsyncSession,
) -> ConversationOut:
    """Build a ConversationOut with participants, last message, and unread count."""
    participants, last_read_map = await _build_participant_list(conv.id, db)

    my_last_read = last_read_map.get(current_user_id)

    # Last message
    last_msg = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    last_message = MessageOut.model_validate(last_msg) if last_msg else None

    # Unread count (non-system messages after last_read_at)
    unread_stmt = select(func.count()).select_from(Message).where(
        Message.conversation_id == conv.id,
        Message.is_system.is_(False),
    )
    if my_last_read:
        unread_stmt = unread_stmt.where(Message.created_at > my_last_read)
    unread_count: int = (await db.execute(unread_stmt)).scalar_one()

    return ConversationOut(
        id=conv.id,
        school_id=conv.school_id,
        subject=conv.subject,
        learner_id=conv.learner_id,
        is_archived=conv.is_archived,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        participants=participants,
        last_message=last_message,
        unread_count=unread_count,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    """List all conversations for the current user, newest first."""
    if _is_admin(current_user):
        stmt = (
            select(Conversation)
            .where(Conversation.school_id == current_user.school_id)
            .order_by(Conversation.updated_at.desc())
        )
    else:
        stmt = (
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(ConversationParticipant.user_id == current_user.id)
            .order_by(Conversation.updated_at.desc())
        )

    convs = list((await db.execute(stmt)).scalars())
    return [await _build_conversation_out(c, current_user.id, db) for c in convs]


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationOut:
    """Start a new conversation about a learner.

    If a conversation between the same two participants about the same learner
    already exists it is returned instead of creating a duplicate.
    """
    # Look for an existing conversation between these two users about this learner
    existing_stmt = (
        select(Conversation)
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.id,
        )
        .where(
            Conversation.learner_id == body.learner_id,
            ConversationParticipant.user_id == current_user.id,
        )
        .limit(10)
    )
    candidates = list((await db.execute(existing_stmt)).scalars())

    for candidate in candidates:
        other = await db.scalar(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == candidate.id,
                ConversationParticipant.user_id == body.participant_id,
            )
        )
        if other:
            return await _build_conversation_out(candidate, current_user.id, db)

    # Create new conversation
    conv = Conversation(
        school_id=current_user.school_id,
        learner_id=body.learner_id,
        subject=body.subject,
    )
    db.add(conv)
    await db.flush()

    for uid in (current_user.id, body.participant_id):
        db.add(ConversationParticipant(conversation_id=conv.id, user_id=uid))

    await db.commit()
    await db.refresh(conv)

    return await _build_conversation_out(conv, current_user.id, db)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: uuid.UUID,
    request: Request,
    before: datetime | None = Query(None, description="Cursor: return messages before this timestamp"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    """List messages in a conversation, newest first (use `before` cursor for pagination)."""
    conv = await _get_conversation_or_403(conversation_id, current_user, db)

    # Log admin oversight access (only when admin is not themselves a participant)
    if _is_admin(current_user):
        participant_ids = {p.user_id for p in conv.participants}
        if current_user.id not in participant_ids:
            await _log_admin_access(db, current_user, conversation_id, request)
            await db.commit()

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if before:
        stmt = stmt.where(Message.created_at < before)

    msgs = list((await db.execute(stmt)).scalars())
    msgs.reverse()  # chronological order for display
    return [MessageOut.model_validate(m) for m in msgs]


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageOut:
    """Send a message. Enforces rate limit (30/hour) and block status."""
    conv = await _get_conversation_or_403(conversation_id, current_user, db)

    # Check if the current user is blocked
    my_participant = next(
        (p for p in conv.participants if p.user_id == current_user.id), None
    )
    if my_participant and my_participant.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have been blocked from sending messages in this conversation",
        )

    # Rate limit
    within_limit = await check_message_rate_limit(str(current_user.id), redis)
    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: 30 messages per hour",
        )

    msg = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=body.body.strip(),
        is_system=False,
    )
    db.add(msg)

    # Bump conversation.updated_at
    await db.execute(
        text("UPDATE conversations SET updated_at = now() WHERE id = :cid"),
        {"cid": str(conversation_id)},
    )

    await db.commit()
    await db.refresh(msg)

    # SSE broadcast to all non-blocked participants
    other_ids = [
        str(p.user_id)
        for p in conv.participants
        if p.user_id != current_user.id and not p.is_blocked
    ]
    await sse_manager.broadcast(
        other_ids,
        {
            "type": "message.new",
            "conversation_id": str(conversation_id),
            "message_id": str(msg.id),
        },
    )

    return MessageOut.model_validate(msg)


@router.put("/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark all messages in a conversation as read for the current user."""
    conv = await _get_conversation_or_403(conversation_id, current_user, db)

    my_participant = next(
        (p for p in conv.participants if p.user_id == current_user.id), None
    )
    if my_participant:
        my_participant.last_read_at = datetime.now(timezone.utc)
        await db.commit()


@router.put("/{conversation_id}/mute", status_code=status.HTTP_204_NO_CONTENT)
async def mute_conversation(
    conversation_id: uuid.UUID,
    body: MuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Teacher: mute or unmute a conversation. Inserts a system message when muting."""
    if current_user.role not in ("teacher", "school_admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can mute conversations",
        )

    conv = await _get_conversation_or_403(conversation_id, current_user, db)

    my_participant = next(
        (p for p in conv.participants if p.user_id == current_user.id), None
    )
    if my_participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not a participant")

    was_muted = my_participant.is_muted
    my_participant.is_muted = body.muted

    if body.muted and not was_muted:
        db.add(
            Message(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                body="This conversation has been muted by the teacher.",
                is_system=True,
            )
        )

    await db.commit()


@router.put("/{conversation_id}/block", status_code=status.HTTP_204_NO_CONTENT)
async def block_participant(
    conversation_id: uuid.UUID,
    body: BlockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Teacher/admin: block or unblock a participant. Inserts a system message when blocking."""
    if current_user.role not in ("teacher", "school_admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and admins can block participants",
        )

    conv = await _get_conversation_or_403(conversation_id, current_user, db)

    target = next(
        (p for p in conv.participants if p.user_id == body.user_id), None
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    was_blocked = target.is_blocked
    target.is_blocked = body.blocked

    if body.blocked and not was_blocked:
        db.add(
            Message(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                body="This conversation has been paused. Contact the school office if you need assistance.",
                is_system=True,
            )
        )

    await db.commit()
