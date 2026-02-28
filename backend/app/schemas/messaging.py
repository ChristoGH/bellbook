from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Messages (defined first — referenced by ConversationOut)
# ---------------------------------------------------------------------------


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    is_system: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


class ParticipantOut(BaseModel):
    user_id: uuid.UUID
    first_name: str
    last_name: str
    role: str
    avatar_url: str | None
    is_muted: bool
    is_blocked: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class ConversationCreate(BaseModel):
    learner_id: uuid.UUID
    participant_id: uuid.UUID  # the other party (teacher_id or parent_id)
    subject: str | None = None


class ConversationOut(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    subject: str | None
    learner_id: uuid.UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    participants: list[ParticipantOut] = []
    last_message: MessageOut | None = None
    unread_count: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Message create
# ---------------------------------------------------------------------------


class MessageCreate(BaseModel):
    body: str


# ---------------------------------------------------------------------------
# Teacher / admin actions
# ---------------------------------------------------------------------------


class MuteRequest(BaseModel):
    muted: bool = True


class BlockRequest(BaseModel):
    user_id: uuid.UUID
    blocked: bool = True
