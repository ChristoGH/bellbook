from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsentForm(Base):
    __tablename__ = "consent_forms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_type: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("target_type IN ('school', 'grade', 'class')", name="consent_forms_target_type_check"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    responses: Mapped[list[ConsentResponse]] = relationship(back_populates="form")


class ConsentResponse(Base):
    __tablename__ = "consent_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consent_form_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consent_forms.id", ondelete="CASCADE"), nullable=False)
    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False)
    guardian_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    response: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("response IN ('granted', 'denied')", name="consent_responses_response_check"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)

    __table_args__ = (
        UniqueConstraint("consent_form_id", "learner_id"),
    )

    form: Mapped[ConsentForm] = relationship(back_populates="responses")
