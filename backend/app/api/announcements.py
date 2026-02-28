"""Channels and announcements endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.announcement import Announcement, AnnouncementRead, Channel
from app.models.school import Class, Grade
from app.models.user import ClassLearner, ClassTeacher, Learner, LearnerGuardian, User
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementOut,
    AnnouncementReadOut,
    AnnouncementStats,
    ChannelOut,
    ClassBreakdown,
)
from app.services.sse_service import manager as sse_manager

router = APIRouter(prefix="/api", tags=["announcements"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _assert_channel_access(channel: Channel, user: User, db: AsyncSession) -> None:
    """Raise 403 if *user* cannot access *channel*."""
    if user.role in ("super_admin", "school_admin"):
        return
    if channel.school_id != user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


async def _get_channel_or_404(channel_id: uuid.UUID, db: AsyncSession) -> Channel:
    channel = await db.get(Channel, channel_id)
    if channel is None or not channel.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return channel


async def _get_announcement_or_404(announcement_id: uuid.UUID, db: AsyncSession) -> Announcement:
    ann = await db.get(Announcement, announcement_id)
    if ann is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    return ann


async def _recipient_ids(channel: Channel, db: AsyncSession) -> list[str]:
    """Return the distinct parent user_ids who should receive this channel's announcements."""
    if channel.type == "school":
        stmt = (
            select(distinct(LearnerGuardian.guardian_id))
            .join(Learner, Learner.id == LearnerGuardian.learner_id)
            .join(User, User.id == LearnerGuardian.guardian_id)
            .where(Learner.school_id == channel.school_id, User.is_active == True)  # noqa: E712
        )
    elif channel.type == "grade":
        class_ids = select(Class.id).where(Class.grade_id == channel.grade_id)
        stmt = (
            select(distinct(LearnerGuardian.guardian_id))
            .join(ClassLearner, ClassLearner.learner_id == LearnerGuardian.learner_id)
            .join(User, User.id == LearnerGuardian.guardian_id)
            .where(ClassLearner.class_id.in_(class_ids), User.is_active == True)  # noqa: E712
        )
    else:  # "class" or "custom"
        target_class_id = channel.class_id
        stmt = (
            select(distinct(LearnerGuardian.guardian_id))
            .join(ClassLearner, ClassLearner.learner_id == LearnerGuardian.learner_id)
            .join(User, User.id == LearnerGuardian.guardian_id)
            .where(ClassLearner.class_id == target_class_id, User.is_active == True)  # noqa: E712
        )
    rows = await db.execute(stmt)
    return [str(row[0]) for row in rows.fetchall()]


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


@router.get("/channels", response_model=list[ChannelOut])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Channel]:
    """List channels accessible to the current user."""
    if current_user.role in ("super_admin", "school_admin"):
        stmt = select(Channel).where(
            Channel.school_id == current_user.school_id,
            Channel.is_active == True,  # noqa: E712
        )
    elif current_user.role == "teacher":
        # School-wide channels + channels for the teacher's assigned classes/grades
        assigned_class_ids = select(ClassTeacher.class_id).where(
            ClassTeacher.teacher_id == current_user.id
        )
        assigned_grade_ids = (
            select(Grade.id)
            .join(Class, Class.grade_id == Grade.id)
            .join(ClassTeacher, ClassTeacher.class_id == Class.id)
            .where(ClassTeacher.teacher_id == current_user.id)
        )
        stmt = select(Channel).where(
            Channel.school_id == current_user.school_id,
            Channel.is_active == True,  # noqa: E712
            or_(
                Channel.type == "school",
                Channel.class_id.in_(assigned_class_ids),
                Channel.grade_id.in_(assigned_grade_ids),
            ),
        )
    else:  # parent
        # Channels for the parent's children's classes/grades + school-wide
        children_class_ids = (
            select(ClassLearner.class_id)
            .join(LearnerGuardian, LearnerGuardian.learner_id == ClassLearner.learner_id)
            .where(LearnerGuardian.guardian_id == current_user.id)
        )
        children_grade_ids = (
            select(Class.grade_id)
            .where(Class.id.in_(children_class_ids))
        )
        stmt = select(Channel).where(
            Channel.school_id == current_user.school_id,
            Channel.is_active == True,  # noqa: E712
            or_(
                Channel.type == "school",
                Channel.class_id.in_(children_class_ids),
                Channel.grade_id.in_(children_grade_ids),
            ),
        )

    result = await db.execute(stmt.order_by(Channel.name))
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Announcements — list
# ---------------------------------------------------------------------------


@router.get("/channels/{channel_id}/announcements", response_model=list[AnnouncementOut])
async def list_announcements(
    channel_id: uuid.UUID,
    priority: str | None = Query(None, description="Filter by priority: urgent | normal | info"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnnouncementOut]:
    channel = await _get_channel_or_404(channel_id, db)
    await _assert_channel_access(channel, current_user, db)

    now = datetime.now(timezone.utc)
    conditions = [
        Announcement.channel_id == channel_id,
        Announcement.published_at != None,  # noqa: E711 — only published
        Announcement.published_at <= now,
        or_(Announcement.expires_at == None, Announcement.expires_at > now),  # noqa: E711
    ]
    if priority:
        conditions.append(Announcement.priority == priority)

    stmt = (
        select(Announcement)
        .where(and_(*conditions))
        .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    announcements = result.scalars().all()

    # Annotate with the current user's read_at (one query for all)
    ann_ids = [a.id for a in announcements]
    reads_result = await db.execute(
        select(AnnouncementRead).where(
            AnnouncementRead.announcement_id.in_(ann_ids),
            AnnouncementRead.user_id == current_user.id,
        )
    )
    reads_by_id = {r.announcement_id: r.read_at for r in reads_result.scalars().all()}

    out = []
    for ann in announcements:
        data = AnnouncementOut.model_validate(ann)
        data.read_at = reads_by_id.get(ann.id)
        out.append(data)
    return out


# ---------------------------------------------------------------------------
# Announcements — create
# ---------------------------------------------------------------------------


@router.post("/announcements", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    body: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("school_admin", "teacher")),
) -> AnnouncementOut:
    channel = await _get_channel_or_404(body.channel_id, db)
    await _assert_channel_access(channel, current_user, db)

    published_at = body.published_at or datetime.now(timezone.utc)

    ann = Announcement(
        id=uuid.uuid4(),
        channel_id=body.channel_id,
        author_id=current_user.id,
        title=body.title,
        body=body.body,
        priority=body.priority,
        is_pinned=body.is_pinned,
        send_whatsapp=body.send_whatsapp,
        send_sms=body.send_sms,
        published_at=published_at,
        expires_at=body.expires_at,
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)

    # SSE broadcast to all recipients (fire-and-forget)
    recipient_ids = await _recipient_ids(channel, db)
    await sse_manager.broadcast(
        recipient_ids,
        {
            "type": "announcement.new",
            "announcement_id": str(ann.id),
            "channel_id": str(channel.id),
            "title": ann.title,
            "priority": ann.priority,
        },
    )

    # TODO (Prompt 6): enqueue ARQ task for FCM / WhatsApp / SMS dispatch
    # await arq_pool.enqueue_job("send_announcement_notifications", str(ann.id), recipient_ids)

    return AnnouncementOut.model_validate(ann)


# ---------------------------------------------------------------------------
# Announcements — get single
# ---------------------------------------------------------------------------


@router.get("/announcements/{announcement_id}", response_model=AnnouncementOut)
async def get_announcement(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementOut:
    ann = await _get_announcement_or_404(announcement_id, db)
    channel = await _get_channel_or_404(ann.channel_id, db)
    await _assert_channel_access(channel, current_user, db)

    read_result = await db.execute(
        select(AnnouncementRead).where(
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.user_id == current_user.id,
        )
    )
    read = read_result.scalar_one_or_none()

    out = AnnouncementOut.model_validate(ann)
    out.read_at = read.read_at if read else None
    return out


# ---------------------------------------------------------------------------
# Announcements — mark as read
# ---------------------------------------------------------------------------


@router.post("/announcements/{announcement_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    ann = await _get_announcement_or_404(announcement_id, db)
    channel = await _get_channel_or_404(ann.channel_id, db)
    await _assert_channel_access(channel, current_user, db)

    existing = await db.execute(
        select(AnnouncementRead).where(
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(AnnouncementRead(
            id=uuid.uuid4(),
            announcement_id=announcement_id,
            user_id=current_user.id,
        ))
        await db.commit()


# ---------------------------------------------------------------------------
# Announcements — read receipts  (teacher / admin)
# ---------------------------------------------------------------------------


@router.get("/announcements/{announcement_id}/reads", response_model=list[AnnouncementReadOut])
async def get_reads(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("school_admin", "teacher")),
) -> list[AnnouncementReadOut]:
    await _get_announcement_or_404(announcement_id, db)

    stmt = (
        select(
            AnnouncementRead.user_id,
            User.first_name,
            User.last_name,
            AnnouncementRead.read_at,
        )
        .join(User, User.id == AnnouncementRead.user_id)
        .where(AnnouncementRead.announcement_id == announcement_id)
        .order_by(AnnouncementRead.read_at.desc())
    )
    rows = await db.execute(stmt)
    return [
        AnnouncementReadOut(
            user_id=row.user_id,
            first_name=row.first_name,
            last_name=row.last_name,
            read_at=row.read_at,
        )
        for row in rows.fetchall()
    ]


# ---------------------------------------------------------------------------
# Announcements — stats  (teacher / admin)
# ---------------------------------------------------------------------------


@router.get("/announcements/{announcement_id}/stats", response_model=AnnouncementStats)
async def get_stats(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("school_admin", "teacher")),
) -> AnnouncementStats:
    ann = await _get_announcement_or_404(announcement_id, db)
    channel = await _get_channel_or_404(ann.channel_id, db)

    # --- total unique recipients for the whole channel ---
    if channel.type == "school":
        total_stmt = (
            select(func.count(distinct(LearnerGuardian.guardian_id)))
            .join(Learner, Learner.id == LearnerGuardian.learner_id)
            .join(User, User.id == LearnerGuardian.guardian_id)
            .where(Learner.school_id == channel.school_id, User.is_active == True)  # noqa: E712
        )
    elif channel.type == "grade":
        class_ids_sub = select(Class.id).where(Class.grade_id == channel.grade_id)
        total_stmt = (
            select(func.count(distinct(LearnerGuardian.guardian_id)))
            .join(ClassLearner, ClassLearner.learner_id == LearnerGuardian.learner_id)
            .join(User, User.id == LearnerGuardian.guardian_id)
            .where(ClassLearner.class_id.in_(class_ids_sub), User.is_active == True)  # noqa: E712
        )
    else:  # class / custom
        total_stmt = (
            select(func.count(distinct(LearnerGuardian.guardian_id)))
            .join(ClassLearner, ClassLearner.learner_id == LearnerGuardian.learner_id)
            .join(User, User.id == LearnerGuardian.guardian_id)
            .where(ClassLearner.class_id == channel.class_id, User.is_active == True)  # noqa: E712
        )
    total_recipients: int = (await db.execute(total_stmt)).scalar() or 0

    # --- overall read count + last_read_at ---
    agg = await db.execute(
        select(
            func.count(AnnouncementRead.id),
            func.max(AnnouncementRead.read_at),
        ).where(AnnouncementRead.announcement_id == announcement_id)
    )
    read_count, last_read_at = agg.one()
    read_count = read_count or 0
    read_percentage = round(read_count / total_recipients * 100, 1) if total_recipients else 0.0

    # --- per-class breakdown ---
    if channel.type == "school":
        classes_stmt = (
            select(Class, Grade)
            .join(Grade, Grade.id == Class.grade_id)
            .where(Grade.school_id == channel.school_id)
            .order_by(Grade.sort_order, Class.name)
        )
    elif channel.type == "grade":
        classes_stmt = (
            select(Class, Grade)
            .join(Grade, Grade.id == Class.grade_id)
            .where(Class.grade_id == channel.grade_id)
            .order_by(Grade.sort_order, Class.name)
        )
    else:
        classes_stmt = (
            select(Class, Grade)
            .join(Grade, Grade.id == Class.grade_id)
            .where(Class.id == channel.class_id)
        )
    classes_rows = (await db.execute(classes_stmt)).all()

    breakdown: list[ClassBreakdown] = []
    for cls, grade in classes_rows:
        # parents in this class
        cls_total: int = (
            await db.execute(
                select(func.count(distinct(LearnerGuardian.guardian_id)))
                .join(ClassLearner, ClassLearner.learner_id == LearnerGuardian.learner_id)
                .join(User, User.id == LearnerGuardian.guardian_id)
                .where(ClassLearner.class_id == cls.id, User.is_active == True)  # noqa: E712
            )
        ).scalar() or 0

        # reads from parents in this class
        cls_reads: int = (
            await db.execute(
                select(func.count(distinct(AnnouncementRead.user_id)))
                .join(LearnerGuardian, LearnerGuardian.guardian_id == AnnouncementRead.user_id)
                .join(ClassLearner, ClassLearner.learner_id == LearnerGuardian.learner_id)
                .where(
                    AnnouncementRead.announcement_id == announcement_id,
                    ClassLearner.class_id == cls.id,
                )
            )
        ).scalar() or 0

        breakdown.append(
            ClassBreakdown(
                target=f"{grade.name} {cls.name}",
                total=cls_total,
                read=cls_reads,
                percentage=round(cls_reads / cls_total * 100, 1) if cls_total else 0.0,
            )
        )

    return AnnouncementStats(
        announcement_id=announcement_id,
        total_recipients=total_recipients,
        read_count=read_count,
        read_percentage=read_percentage,
        unread_count=total_recipients - read_count,
        breakdown=breakdown,
        last_read_at=last_read_at,
    )


# ---------------------------------------------------------------------------
# Announcements — delete
# ---------------------------------------------------------------------------


@router.delete("/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("school_admin", "teacher")),
) -> None:
    ann = await _get_announcement_or_404(announcement_id, db)

    # Teachers may only delete their own announcements
    if current_user.role == "teacher" and ann.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another teacher's announcement")

    await db.delete(ann)
    await db.commit()
