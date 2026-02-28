"""Initial schema with RLS

Revision ID: 0001
Revises:
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================
    # CORE ENTITIES
    # =========================================================

    op.create_table(
        "schools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Africa/Johannesburg"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "academic_years",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column(
            "role",
            sa.String(20),
            sa.CheckConstraint("role IN ('super_admin', 'school_admin', 'teacher', 'parent')", name="users_role_check"),
            nullable=False,
        ),
        sa.Column("preferred_lang", sa.String(10), nullable=False, server_default="en"),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("school_id", "email", name="uq_users_school_email"),
        sa.UniqueConstraint("school_id", "phone", name="uq_users_school_phone"),
    )

    op.create_table(
        "grades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year_id", UUID(as_uuid=True), sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "classes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("grade_id", UUID(as_uuid=True), sa.ForeignKey("grades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # =========================================================
    # LEARNER & RELATIONSHIPS
    # =========================================================

    op.create_table(
        "learners",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("student_number", sa.String(50), nullable=True),
        sa.Column("medical_notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "class_learners",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("class_id", UUID(as_uuid=True), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learner_id", UUID(as_uuid=True), sa.ForeignKey("learners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("class_id", "learner_id"),
    )

    op.create_table(
        "class_teachers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("class_id", UUID(as_uuid=True), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("class_id", "teacher_id"),
    )

    op.create_table(
        "learner_guardians",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("learner_id", UUID(as_uuid=True), sa.ForeignKey("learners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("guardian_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship", sa.String(30), nullable=False, server_default="parent"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("can_collect", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("learner_id", "guardian_id"),
    )

    # =========================================================
    # COMMUNICATION: ANNOUNCEMENTS
    # =========================================================

    op.create_table(
        "channels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "type",
            sa.String(20),
            sa.CheckConstraint("type IN ('school', 'grade', 'class', 'custom')", name="channels_type_check"),
            nullable=False,
        ),
        sa.Column("grade_id", UUID(as_uuid=True), sa.ForeignKey("grades.id", ondelete="CASCADE"), nullable=True),
        sa.Column("class_id", UUID(as_uuid=True), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "announcements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("channel_id", UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column(
            "priority",
            sa.String(10),
            sa.CheckConstraint("priority IN ('urgent', 'normal', 'info')", name="announcements_priority_check"),
            nullable=False,
            server_default="normal",
        ),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("send_whatsapp", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("send_sms", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "announcement_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("announcement_id", UUID(as_uuid=True), sa.ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_url", sa.Text, nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "announcement_reads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("announcement_id", UUID(as_uuid=True), sa.ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("announcement_id", "user_id"),
    )

    # =========================================================
    # COMMUNICATION: DIRECT MESSAGING
    # =========================================================

    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("learner_id", UUID(as_uuid=True), sa.ForeignKey("learners.id"), nullable=True),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "conversation_participants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_muted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_blocked", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("conversation_id", "user_id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "message_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_url", sa.Text, nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # =========================================================
    # ABSENCE REPORTING
    # =========================================================

    op.create_table(
        "absence_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("learner_id", UUID(as_uuid=True), sa.ForeignKey("learners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reported_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("absence_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column(
            "reason",
            sa.String(50),
            sa.CheckConstraint(
                "reason IN ('illness', 'medical_appointment', 'family_emergency', 'religious', 'bereavement', 'other')",
                name="absence_reports_reason_check",
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("attachment_url", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            sa.CheckConstraint(
                "status IN ('pending', 'acknowledged', 'excused', 'unexcused')",
                name="absence_reports_status_check",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("acknowledged_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # =========================================================
    # DIGITAL CONSENT FORMS
    # =========================================================

    op.create_table(
        "consent_forms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column(
            "target_type",
            sa.String(20),
            sa.CheckConstraint("target_type IN ('school', 'grade', 'class')", name="consent_forms_target_type_check"),
            nullable=False,
        ),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "consent_responses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("consent_form_id", UUID(as_uuid=True), sa.ForeignKey("consent_forms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learner_id", UUID(as_uuid=True), sa.ForeignKey("learners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("guardian_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "response",
            sa.String(20),
            sa.CheckConstraint("response IN ('granted', 'denied')", name="consent_responses_response_check"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ip_address", INET, nullable=True),
        sa.UniqueConstraint("consent_form_id", "learner_id"),
    )

    # =========================================================
    # CALENDAR
    # =========================================================

    op.create_table(
        "calendar_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_all_day", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "event_type",
            sa.String(30),
            sa.CheckConstraint(
                "event_type IN ('general', 'academic', 'sport', 'cultural', 'meeting', 'holiday', 'exam')",
                name="calendar_events_event_type_check",
            ),
            nullable=False,
            server_default="general",
        ),
        sa.Column(
            "target_type",
            sa.String(20),
            sa.CheckConstraint("target_type IN ('school', 'grade', 'class')", name="calendar_events_target_type_check"),
            nullable=False,
            server_default="school",
        ),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("recurrence_rule", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # =========================================================
    # NOTIFICATIONS & DEVICE MANAGEMENT
    # =========================================================

    op.create_table(
        "push_devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_token", sa.Text, nullable=False),
        sa.Column("device_type", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "channel",
            sa.String(20),
            sa.CheckConstraint("channel IN ('push', 'whatsapp', 'sms', 'email')", name="notification_preferences_channel_check"),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("quiet_hours_start", sa.Time, nullable=True),
        sa.Column("quiet_hours_end", sa.Time, nullable=True),
        sa.UniqueConstraint("user_id", "channel"),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "channel",
            sa.String(20),
            sa.CheckConstraint("channel IN ('push', 'whatsapp', 'sms', 'email')", name="notification_log_channel_check"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            sa.CheckConstraint("status IN ('sent', 'delivered', 'failed', 'read')", name="notification_log_status_check"),
            nullable=False,
            server_default="sent",
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )

    # =========================================================
    # AUDIT LOG
    # =========================================================

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # =========================================================
    # INDEXES
    # =========================================================

    op.create_index("idx_users_school_role", "users", ["school_id", "role"])
    op.create_index("idx_users_phone", "users", ["phone"])
    op.create_index(
        "idx_announcements_channel",
        "announcements",
        ["channel_id", sa.text("published_at DESC")],
    )
    op.create_index(
        "idx_announcements_priority",
        "announcements",
        ["priority"],
        postgresql_where=sa.text("published_at IS NOT NULL"),
    )
    op.create_index("idx_announcement_reads_announcement", "announcement_reads", ["announcement_id"])
    op.create_index(
        "idx_messages_conversation",
        "messages",
        ["conversation_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_conversations_school",
        "conversations",
        ["school_id", sa.text("updated_at DESC")],
    )
    op.create_index(
        "idx_absence_reports_learner",
        "absence_reports",
        ["learner_id", sa.text("absence_date DESC")],
    )
    op.create_index("idx_consent_responses_form", "consent_responses", ["consent_form_id"])
    op.create_index("idx_calendar_events_school", "calendar_events", ["school_id", "start_datetime"])
    op.create_index(
        "idx_notification_log_user",
        "notification_log",
        ["user_id", sa.text("sent_at DESC")],
    )
    op.create_index(
        "idx_audit_log_school",
        "audit_log",
        ["school_id", sa.text("created_at DESC")],
    )
    op.create_index("idx_learner_guardians_guardian", "learner_guardians", ["guardian_id"])
    op.create_index("idx_class_learners_learner", "class_learners", ["learner_id"])
    op.create_index("idx_push_devices_token", "push_devices", ["device_token"])

    # =========================================================
    # ROW-LEVEL SECURITY
    # =========================================================

    # Enable RLS on all school-scoped tables.
    # The application sets app.current_school_id on every connection via middleware.
    rls_direct = [
        "academic_years",
        "users",
        "grades",
        "learners",
        "channels",
        "conversations",
        "consent_forms",
        "calendar_events",
    ]
    for table in rls_direct:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY school_isolation ON {table} "
            f"USING (school_id = current_setting('app.current_school_id', true)::UUID)"
        )

    # audit_log has a nullable school_id (super_admin actions have no school)
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY school_isolation ON audit_log "
        "USING (school_id IS NULL OR school_id = current_setting('app.current_school_id', true)::UUID)"
    )

    # Tables without a direct school_id — protected via parent table subquery.
    op.execute("ALTER TABLE classes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE classes FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY school_isolation ON classes "
        "USING (grade_id IN ("
        "  SELECT id FROM grades "
        "  WHERE school_id = current_setting('app.current_school_id', true)::UUID"
        "))"
    )

    op.execute("ALTER TABLE announcements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE announcements FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY school_isolation ON announcements "
        "USING (channel_id IN ("
        "  SELECT id FROM channels "
        "  WHERE school_id = current_setting('app.current_school_id', true)::UUID"
        "))"
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    tables = [
        "audit_log",
        "notification_log",
        "notification_preferences",
        "push_devices",
        "calendar_events",
        "consent_responses",
        "consent_forms",
        "absence_reports",
        "message_attachments",
        "messages",
        "conversation_participants",
        "conversations",
        "announcement_reads",
        "announcement_attachments",
        "announcements",
        "channels",
        "learner_guardians",
        "class_teachers",
        "class_learners",
        "learners",
        "classes",
        "grades",
        "users",
        "academic_years",
        "schools",
    ]
    for table in tables:
        op.drop_table(table)
