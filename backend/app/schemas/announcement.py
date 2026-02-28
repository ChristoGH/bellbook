from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


class ChannelOut(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    name: str
    type: str
    description: str | None
    grade_id: uuid.UUID | None
    class_id: uuid.UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------


class AnnouncementCreate(BaseModel):
    channel_id: uuid.UUID
    title: str
    body: str
    priority: str = "normal"
    is_pinned: bool = False
    send_whatsapp: bool = False
    send_sms: bool = False
    # None = publish immediately; future datetime = draft/scheduled
    published_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in ("urgent", "normal", "info"):
            raise ValueError("priority must be 'urgent', 'normal', or 'info'")
        return v


class AnnouncementOut(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID
    author_id: uuid.UUID
    title: str
    body: str
    priority: str
    is_pinned: bool
    send_whatsapp: bool
    send_sms: bool
    published_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Injected per-request: None if the calling user has not read it yet
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Read receipts
# ---------------------------------------------------------------------------


class AnnouncementReadOut(BaseModel):
    user_id: uuid.UUID
    first_name: str
    last_name: str
    read_at: datetime


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class ClassBreakdown(BaseModel):
    target: str       # e.g. "Grade 4 4A"
    total: int        # total unique parent recipients in this class
    read: int         # how many have read
    percentage: float


class AnnouncementStats(BaseModel):
    announcement_id: uuid.UUID
    total_recipients: int
    read_count: int
    read_percentage: float
    unread_count: int
    breakdown: list[ClassBreakdown]
    last_read_at: datetime | None
