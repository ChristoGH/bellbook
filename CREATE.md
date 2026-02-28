# BellBook — Phase 1 MVP Specification

## Product Overview

**BellBook** is a Progressive Web App (PWA) that replaces WhatsApp groups, printed notices, and legacy school communication tools (like D6) with a modern, two-way communication platform for schools, teachers, and parents in South Africa.

**Target Market:** Independent and public schools in South Africa (800–1500 learners)
**Business Model:** SaaS — R5–R15 per learner/month
**Tech Stack:** Vite + React Router (PWA) + Tailwind CSS + FastAPI + PostgreSQL + Redis + ARQ + Cloudflare R2 + Firebase Cloud Messaging + WhatsApp Business API

---

## Phase 1 Scope — Communication MVP

Phase 1 focuses exclusively on replacing WhatsApp groups and one-way notice systems with a proper school communication platform.

### Core Features

1. **School Announcements** — broadcast notices with read tracking and read-percentage stats
2. **Direct Messaging** — parent ↔ teacher private messaging with safeguards
3. **Absentee Reporting** — parents report absences from the app
4. **Digital Consent Forms** — sign permission slips digitally
5. **School Calendar** — events, terms, exam dates in one place
6. **Push Notifications** — with priority levels (urgent / normal / info)
7. **WhatsApp Fallback** — critical notices also sent via WhatsApp API
8. **Real-time Updates** — SSE stream for live announcement and message delivery

### Out of Scope (Phase 2+)

- Fee management / payments
- Gradebook / academic tracking
- Transport tracking
- Tuckshop ordering
- AI features (summaries, chatbot, anomaly detection)
- WebSocket upgrade for full bidirectional chat (typing indicators, presence)

---

## User Roles & Permissions

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| **Super Admin** | System administrator (you) | Manage all schools, global config |
| **School Admin** | Principal / secretary | Manage school, teachers, classes, parents, review flagged conversations |
| **Teacher** | Class teacher or subject teacher | Send class announcements, message parents, mark attendance, mute/block conversations |
| **Parent** | Guardian of one or more learners | View announcements, message teachers, report absence, sign forms |

### Role Hierarchy

```
Super Admin
  └── School Admin
        └── Teacher
              └── Parent (linked via Learner)
```

---

## Data Model

### Entity Relationship Diagram (Text)

```
School (1) ──< (many) AcademicYear
School (1) ──< (many) User (school_admin, teacher)
School (1) ──< (many) Grade
Grade  (1) ──< (many) Class
Class  (1) ──< (many) ClassTeacher (junction)
Class  (1) ──< (many) ClassLearner (junction)
User   (1) ──< (many) ClassTeacher
Learner(1) ──< (many) ClassLearner
Learner(1) ──< (many) LearnerGuardian (junction)
User   (1) ──< (many) LearnerGuardian (parent role)
School (1) ──< (many) Channel
Channel(1) ──< (many) Announcement
User   (1) ──< (many) Announcement (author)
Announcement(1) ──< (many) AnnouncementRead
Announcement(1) ──< (many) AnnouncementAttachment
User   (1) ──< (many) Conversation (as participant)
Conversation(1) ──< (many) Message
Learner(1) ──< (many) AbsenceReport
School (1) ──< (many) ConsentForm
ConsentForm(1) ──< (many) ConsentResponse
School (1) ──< (many) CalendarEvent
User   (1) ──< (many) NotificationPreference
```

### Database Schema

```sql
-- =====================================================
-- CORE ENTITIES
-- =====================================================

CREATE TABLE schools (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,  -- URL-friendly identifier
    address         TEXT,
    phone           VARCHAR(20),
    email           VARCHAR(255),
    logo_url        TEXT,
    timezone        VARCHAR(50) DEFAULT 'Africa/Johannesburg',
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE academic_years (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,           -- e.g., "2026"
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    is_current      BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID REFERENCES schools(id) ON DELETE CASCADE,  -- NULL for super_admin
    email           VARCHAR(255),
    phone           VARCHAR(20),                    -- SA mobile number, primary auth for parents
    password_hash   VARCHAR(255),
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('super_admin', 'school_admin', 'teacher', 'parent')),
    preferred_lang  VARCHAR(10) DEFAULT 'en',       -- en, af, zu, xh, st, etc.
    avatar_url      TEXT,
    is_active       BOOLEAN DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(school_id, email),
    UNIQUE(school_id, phone)
);

CREATE TABLE grades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    academic_year_id UUID NOT NULL REFERENCES academic_years(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,           -- e.g., "Grade 4", "Grade R"
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE classes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grade_id        UUID NOT NULL REFERENCES grades(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,           -- e.g., "4A", "4B"
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- =====================================================
-- LEARNER & RELATIONSHIPS
-- =====================================================

CREATE TABLE learners (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    date_of_birth   DATE,
    gender          VARCHAR(10),
    student_number  VARCHAR(50),                    -- school-assigned ID
    medical_notes   TEXT,                           -- allergies, conditions
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE class_learners (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id        UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    learner_id      UUID NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
    enrolled_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE(class_id, learner_id)
);

CREATE TABLE class_teachers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id        UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    teacher_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_primary      BOOLEAN DEFAULT false,          -- class teacher vs subject teacher
    UNIQUE(class_id, teacher_id)
);

CREATE TABLE learner_guardians (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id      UUID NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
    guardian_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- parent user
    relationship    VARCHAR(30) DEFAULT 'parent',   -- parent, grandparent, legal_guardian, etc.
    is_primary      BOOLEAN DEFAULT true,           -- primary contact
    can_collect     BOOLEAN DEFAULT true,           -- authorized for pickup
    UNIQUE(learner_id, guardian_id)
);

-- =====================================================
-- COMMUNICATION: ANNOUNCEMENTS
-- =====================================================

CREATE TABLE channels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,          -- e.g., "Whole School", "Grade 4", "4A", "Sport"
    type            VARCHAR(20) NOT NULL CHECK (type IN ('school', 'grade', 'class', 'custom')),
    -- Polymorphic target: depending on type, one of these is set
    grade_id        UUID REFERENCES grades(id) ON DELETE CASCADE,
    class_id        UUID REFERENCES classes(id) ON DELETE CASCADE,
    description     TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE announcements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id      UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    author_id       UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(255) NOT NULL,
    body            TEXT NOT NULL,                   -- Markdown or rich text
    priority        VARCHAR(10) DEFAULT 'normal' CHECK (priority IN ('urgent', 'normal', 'info')),
    is_pinned       BOOLEAN DEFAULT false,
    send_whatsapp   BOOLEAN DEFAULT false,          -- also push via WhatsApp API
    send_sms        BOOLEAN DEFAULT false,          -- SMS fallback for critical notices
    published_at    TIMESTAMPTZ,                    -- NULL = draft
    expires_at      TIMESTAMPTZ,                    -- auto-archive after this date
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE announcement_attachments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    announcement_id UUID NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
    file_name       VARCHAR(255) NOT NULL,
    file_url        TEXT NOT NULL,                   -- Cloudflare R2 URL
    file_size       INT,                             -- bytes
    mime_type       VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE announcement_reads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    announcement_id UUID NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    read_at         TIMESTAMPTZ DEFAULT now(),
    UNIQUE(announcement_id, user_id)
);

-- =====================================================
-- COMMUNICATION: DIRECT MESSAGING
-- =====================================================

CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    subject         VARCHAR(255),                   -- optional subject line
    learner_id      UUID REFERENCES learners(id),   -- context: which child is this about
    is_archived     BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()        -- updated on each new message
);

CREATE TABLE conversation_participants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_read_at    TIMESTAMPTZ,                    -- for unread badge
    is_muted        BOOLEAN DEFAULT false,
    is_blocked      BOOLEAN DEFAULT false,          -- teacher/admin can block a participant
    UNIQUE(conversation_id, user_id)
);

CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id       UUID NOT NULL REFERENCES users(id),
    body            TEXT NOT NULL,
    is_system       BOOLEAN DEFAULT false,          -- system-generated message (e.g., "conversation muted")
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE message_attachments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    file_name       VARCHAR(255) NOT NULL,
    file_url        TEXT NOT NULL,
    file_size       INT,
    mime_type       VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- =====================================================
-- ABSENCE REPORTING
-- =====================================================

CREATE TABLE absence_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id      UUID NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
    reported_by     UUID NOT NULL REFERENCES users(id),  -- parent
    absence_date    DATE NOT NULL,
    end_date        DATE,                           -- NULL = single day
    reason          VARCHAR(50) NOT NULL CHECK (reason IN (
        'illness', 'medical_appointment', 'family_emergency',
        'religious', 'bereavement', 'other'
    )),
    notes           TEXT,
    attachment_url  TEXT,                            -- doctor's note, etc.
    status          VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'acknowledged', 'excused', 'unexcused')),
    acknowledged_by UUID REFERENCES users(id),       -- teacher/admin who reviewed
    acknowledged_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- =====================================================
-- DIGITAL CONSENT FORMS
-- =====================================================

CREATE TABLE consent_forms (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    created_by      UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(255) NOT NULL,          -- "Grade 4 Kruger Park Trip"
    description     TEXT NOT NULL,                   -- full details of what they're consenting to
    due_date        DATE,
    target_type     VARCHAR(20) NOT NULL CHECK (target_type IN ('school', 'grade', 'class')),
    target_id       UUID,                           -- grade_id or class_id depending on target_type
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE consent_responses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consent_form_id UUID NOT NULL REFERENCES consent_forms(id) ON DELETE CASCADE,
    learner_id      UUID NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
    guardian_id     UUID NOT NULL REFERENCES users(id),
    response        VARCHAR(20) NOT NULL CHECK (response IN ('granted', 'denied')),
    notes           TEXT,                            -- parent can add notes like dietary requirements
    signed_at       TIMESTAMPTZ DEFAULT now(),
    ip_address      INET,                           -- for audit trail
    UNIQUE(consent_form_id, learner_id)             -- one response per child per form
);

-- =====================================================
-- CALENDAR
-- =====================================================

CREATE TABLE calendar_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    created_by      UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    location        VARCHAR(255),
    start_datetime  TIMESTAMPTZ NOT NULL,
    end_datetime    TIMESTAMPTZ,
    is_all_day      BOOLEAN DEFAULT false,
    event_type      VARCHAR(30) DEFAULT 'general' CHECK (event_type IN (
        'general', 'academic', 'sport', 'cultural', 'meeting', 'holiday', 'exam'
    )),
    -- Audience targeting
    target_type     VARCHAR(20) DEFAULT 'school' CHECK (target_type IN ('school', 'grade', 'class')),
    target_id       UUID,
    recurrence_rule TEXT,                            -- iCal RRULE format for recurring events
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- =====================================================
-- NOTIFICATIONS & DEVICE MANAGEMENT
-- =====================================================

CREATE TABLE push_devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_token    TEXT NOT NULL,                   -- FCM token
    device_type     VARCHAR(20),                    -- 'android', 'ios', 'web'
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE notification_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel         VARCHAR(20) NOT NULL CHECK (channel IN ('push', 'whatsapp', 'sms', 'email')),
    enabled         BOOLEAN DEFAULT true,
    quiet_hours_start TIME,                         -- e.g., 21:00
    quiet_hours_end   TIME,                         -- e.g., 06:00
    UNIQUE(user_id, channel)
);

CREATE TABLE notification_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel         VARCHAR(20) NOT NULL CHECK (channel IN ('push', 'whatsapp', 'sms', 'email')),
    title           VARCHAR(255),
    body            TEXT,
    reference_type  VARCHAR(30),                    -- 'announcement', 'message', 'absence', etc.
    reference_id    UUID,
    status          VARCHAR(20) DEFAULT 'sent' CHECK (status IN ('sent', 'delivered', 'failed', 'read')),
    sent_at         TIMESTAMPTZ DEFAULT now(),
    delivered_at    TIMESTAMPTZ,
    error_message   TEXT
);

-- =====================================================
-- AUDIT LOG
-- =====================================================

CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       UUID REFERENCES schools(id),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(50) NOT NULL,            -- 'announcement.create', 'consent.sign', etc.
    entity_type     VARCHAR(50),
    entity_id       UUID,
    metadata        JSONB,                           -- flexible payload for action details
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- =====================================================
-- ROW-LEVEL SECURITY POLICIES
-- =====================================================

-- Enable RLS on all school-scoped tables.
-- The application sets `app.current_school_id` on every connection via middleware.
-- These policies ensure no query can leak data across school boundaries,
-- even if application code omits a WHERE clause.

ALTER TABLE academic_years ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE grades ENABLE ROW LEVEL SECURITY;
ALTER TABLE classes ENABLE ROW LEVEL SECURITY;
ALTER TABLE learners ENABLE ROW LEVEL SECURITY;
ALTER TABLE channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_forms ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Example policy (applied to each table with a school_id column):
CREATE POLICY school_isolation ON academic_years
    USING (school_id = current_setting('app.current_school_id')::UUID);

-- Repeat for all school-scoped tables. Tables without a direct school_id
-- (e.g., class_learners, messages) are protected transitively via JOINs
-- on their parent tables that do have RLS.

-- =====================================================
-- INDEXES
-- =====================================================

CREATE INDEX idx_users_school_role ON users(school_id, role);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_announcements_channel ON announcements(channel_id, published_at DESC);
CREATE INDEX idx_announcements_priority ON announcements(priority) WHERE published_at IS NOT NULL;
CREATE INDEX idx_announcement_reads_announcement ON announcement_reads(announcement_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_conversations_school ON conversations(school_id, updated_at DESC);
CREATE INDEX idx_absence_reports_learner ON absence_reports(learner_id, absence_date DESC);
CREATE INDEX idx_consent_responses_form ON consent_responses(consent_form_id);
CREATE INDEX idx_calendar_events_school ON calendar_events(school_id, start_datetime);
CREATE INDEX idx_notification_log_user ON notification_log(user_id, sent_at DESC);
CREATE INDEX idx_audit_log_school ON audit_log(school_id, created_at DESC);
CREATE INDEX idx_learner_guardians_guardian ON learner_guardians(guardian_id);
CREATE INDEX idx_class_learners_learner ON class_learners(learner_id);
CREATE INDEX idx_push_devices_token ON push_devices(device_token);
```

---

## API Structure

### Authentication

```
POST   /api/auth/register          # Parent self-registration via phone OTP
POST   /api/auth/login              # Phone + OTP or email + password
POST   /api/auth/otp/request        # Request OTP via SMS
POST   /api/auth/otp/verify         # Verify OTP
POST   /api/auth/refresh            # Refresh JWT token
POST   /api/auth/logout             # Invalidate token
```

### Schools & Setup

```
GET    /api/schools/:id             # Get school details
PUT    /api/schools/:id             # Update school (admin)
POST   /api/schools/:id/grades      # Create grade
POST   /api/schools/:id/classes     # Create class
POST   /api/schools/:id/import      # Bulk import learners/parents (CSV)
```

### Users & Learners

```
GET    /api/users/me                # Current user profile
PUT    /api/users/me                # Update profile
GET    /api/learners/:id            # Get learner detail (with guardian check)
GET    /api/users/me/children       # Parent: list my children
```

### Announcements

```
GET    /api/channels                # List channels I have access to
GET    /api/channels/:id/announcements  # List announcements (paginated)
POST   /api/announcements           # Create announcement (teacher/admin)
GET    /api/announcements/:id       # Get single announcement
POST   /api/announcements/:id/read  # Mark as read
GET    /api/announcements/:id/reads # Read receipts (teacher/admin)
GET    /api/announcements/:id/stats # Read percentage + breakdown by grade/class
DELETE /api/announcements/:id       # Delete announcement
```

### Direct Messaging

```
GET    /api/conversations           # List my conversations
POST   /api/conversations           # Start new conversation
GET    /api/conversations/:id/messages  # List messages (paginated)
POST   /api/conversations/:id/messages  # Send message (rate limited: 30/hour)
PUT    /api/conversations/:id/read  # Mark conversation as read
PUT    /api/conversations/:id/mute  # Teacher: mute conversation
PUT    /api/conversations/:id/block # Teacher/admin: block participant
```

### Absence Reporting

```
POST   /api/absences                # Parent: report absence
GET    /api/absences                # Teacher: list absences for my classes
PUT    /api/absences/:id            # Teacher: acknowledge/update status
GET    /api/learners/:id/absences   # Absence history for a learner
```

### Consent Forms

```
POST   /api/consent-forms           # Create consent form (admin/teacher)
GET    /api/consent-forms           # List active forms for me
GET    /api/consent-forms/:id       # Get form detail + responses
POST   /api/consent-forms/:id/respond  # Parent: sign form
GET    /api/consent-forms/:id/report   # Teacher: who signed/didn't
```

### Calendar

```
GET    /api/calendar                # List events (filterable by date range, type)
POST   /api/calendar                # Create event (admin/teacher)
PUT    /api/calendar/:id            # Update event
DELETE /api/calendar/:id            # Delete event
GET    /api/calendar/ical           # Export as .ics for phone calendar sync
```

### Notifications

```
POST   /api/devices                 # Register push device token
DELETE /api/devices/:token          # Unregister device
GET    /api/notifications           # Notification history
PUT    /api/notifications/settings  # User notification preferences
```

### Real-time & Health

```
GET    /api/events/stream           # SSE: authenticated event stream (announcements, messages, notifications)
GET    /api/health                  # Health check: DB + Redis + R2 connectivity
```

---

## Frontend Structure (React PWA — Vite + React Router)

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── public/
│   ├── manifest.json               # PWA manifest
│   ├── favicon.ico
│   └── icons/                      # PWA icons (192x192, 512x512)
├── src/
│   ├── main.tsx                    # Vite entry point
│   ├── App.tsx                     # Root component with router
│   ├── routes/
│   │   ├── auth/
│   │   │   ├── login.tsx           # Phone + OTP login
│   │   │   └── register.tsx        # Parent self-registration
│   │   ├── dashboard/
│   │   │   └── index.tsx           # Role-based home screen
│   │   ├── announcements/
│   │   │   ├── index.tsx           # Feed view
│   │   │   ├── [id].tsx            # Single announcement + read stats
│   │   │   └── create.tsx          # Create/edit (teacher/admin)
│   │   ├── messages/
│   │   │   ├── index.tsx           # Conversation list
│   │   │   └── [id].tsx            # Chat thread
│   │   ├── absences/
│   │   │   ├── report.tsx          # Parent: report form
│   │   │   └── manage.tsx          # Teacher: review absences
│   │   ├── consent/
│   │   │   ├── index.tsx           # List forms
│   │   │   ├── [id].tsx            # View & sign form
│   │   │   └── create.tsx          # Create form (admin)
│   │   ├── calendar/
│   │   │   ├── index.tsx           # Calendar view
│   │   │   └── create.tsx          # Create event
│   │   └── settings/
│   │       ├── profile.tsx
│   │       └── notifications.tsx
│   ├── components/
│   │   ├── ui/                     # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Avatar.tsx
│   │   ├── layout/
│   │   │   ├── AppShell.tsx        # Main app layout with nav
│   │   │   ├── BottomNav.tsx       # Mobile bottom navigation
│   │   │   └── TopBar.tsx
│   │   ├── announcements/
│   │   │   ├── AnnouncementCard.tsx
│   │   │   ├── AnnouncementFeed.tsx
│   │   │   ├── ReadReceipts.tsx
│   │   │   └── ReadPercentageBar.tsx
│   │   ├── messages/
│   │   │   ├── ConversationList.tsx
│   │   │   ├── ChatBubble.tsx
│   │   │   └── MessageInput.tsx
│   │   └── common/
│   │       ├── PriorityBadge.tsx
│   │       ├── FileUpload.tsx
│   │       └── EmptyState.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useAnnouncements.ts
│   │   ├── useConversations.ts
│   │   ├── usePushNotifications.ts
│   │   └── useSSE.ts               # SSE connection hook
│   ├── lib/
│   │   ├── api.ts                  # Fetch wrapper with auth headers
│   │   ├── auth.ts                 # JWT token management
│   │   ├── notifications.ts        # FCM setup
│   │   └── query-client.ts         # TanStack React Query client
│   ├── types/
│   │   └── index.ts                # TypeScript interfaces matching API
│   └── service-worker.ts           # Offline caching strategy
```

---

## Backend Structure (FastAPI)

```
backend/
├── app/
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # Settings (env vars, DB URL, etc.)
│   ├── database.py                 # SQLAlchemy async engine & session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── school.py               # School, AcademicYear, Grade, Class
│   │   ├── user.py                 # User, Learner, LearnerGuardian
│   │   ├── announcement.py         # Channel, Announcement, Read, Attachment
│   │   ├── messaging.py            # Conversation, Participant, Message
│   │   ├── absence.py              # AbsenceReport
│   │   ├── consent.py              # ConsentForm, ConsentResponse
│   │   ├── calendar.py             # CalendarEvent
│   │   └── notification.py         # PushDevice, NotificationPreference, NotificationLog, AuditLog
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Login, Register, OTP request/response
│   │   ├── school.py
│   │   ├── user.py
│   │   ├── announcement.py         # Includes AnnouncementStats schema
│   │   ├── messaging.py
│   │   ├── absence.py
│   │   ├── consent.py
│   │   ├── calendar.py
│   │   └── notification.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                 # Dependencies (get_db, get_current_user, require_role)
│   │   ├── auth.py                 # Auth routes
│   │   ├── schools.py
│   │   ├── announcements.py        # Includes /stats endpoint
│   │   ├── messaging.py            # Includes /mute and /block endpoints
│   │   ├── absences.py
│   │   ├── consent.py
│   │   ├── calendar.py
│   │   ├── notifications.py
│   │   ├── events.py               # SSE stream endpoint
│   │   └── health.py               # Health check endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py         # OTP generation, JWT creation
│   │   ├── notification_service.py # FCM + WhatsApp + SMS dispatch
│   │   ├── file_service.py         # Cloudflare R2 upload/download via boto3 S3-compatible API
│   │   ├── import_service.py       # CSV bulk import of learners/parents
│   │   └── sse_service.py          # SSE connection manager and event broadcasting
│   ├── middleware/
│   │   ├── auth.py                 # JWT verification middleware
│   │   ├── school_context.py       # Inject school context + SET app.current_school_id for RLS
│   │   ├── rate_limit.py           # API rate limiting (messaging: 30/hour)
│   │   └── logging.py              # Request ID injection, structlog middleware
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── worker.py               # ARQ worker entrypoint
│   │   ├── notifications.py        # Background: send push/WhatsApp/SMS via ARQ
│   │   └── reminders.py            # Background: consent form reminders via ARQ
│   ├── alembic/                    # Database migrations
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_announcements.py
│   │   ├── test_messaging.py
│   │   └── test_absences.py
│   └── requirements.txt
├── docker-compose.yml              # PostgreSQL + Redis for local dev
└── Dockerfile
```

---

## Key Technical Decisions

### Authentication Strategy

- **Parents:** Phone number + OTP (SMS). Most SA parents won't have work email.
- **Teachers/Admin:** Email + password (optional OTP). Schools often use institutional email.
- **JWT tokens** with short-lived access tokens (15 min) and refresh tokens (30 days).
- **School context** derived from subdomain (e.g., `rivonia-primary.bellbook.co.za`) or a school selection step during login.

### Multi-tenancy

- **Shared database, school_id column** approach. Simple, cost-effective for a side hustle.
- All queries scoped by `school_id` enforced at the middleware/dependency level.
- **Row-Level Security (RLS) is mandatory from day one** — not optional, not a "safety net."

### Row-Level Security

Every database connection from the application sets `app.current_school_id` via the `school_context.py` middleware before executing any query:

```python
# In school_context.py middleware
await session.execute(text("SET app.current_school_id = :school_id"), {"school_id": str(school_id)})
```

RLS policies on every school-scoped table enforce isolation:

```sql
CREATE POLICY school_isolation ON <table>
    USING (school_id = current_setting('app.current_school_id')::UUID);
```

Tables without a direct `school_id` (e.g., `class_learners`, `messages`) are protected transitively via JOINs on parent tables that have RLS. Super admin queries bypass RLS by using a privileged database role.

### Real-time Strategy (Phase 1: SSE)

- **Server-Sent Events (SSE)** for one-way real-time updates: new announcements, new messages, notification alerts.
- Single authenticated endpoint: `GET /api/events/stream` with JWT in query parameter (SSE doesn't support custom headers).
- Server maintains a per-user connection registry (in-memory dict, keyed by user_id).
- When an event occurs (new announcement published, new message sent), the SSE service broadcasts to all connected recipients.
- Clients use the `useSSE` hook to subscribe and update React Query cache on incoming events.
- **Phase 2:** Upgrade to WebSocket for bidirectional features (typing indicators, presence, read receipts in real-time).

### Notification Delivery Pipeline

```
Event triggers notification
    → ARQ task enqueued in Redis
        → ARQ worker picks up task
            → For each recipient:
                1. Push notification (FCM) — primary channel
                2. If priority == 'urgent' AND user has WhatsApp enabled: send via WhatsApp Business API
                3. If no push device registered: fallback to SMS
                4. Log to notification_log table
                5. Broadcast via SSE to connected clients
            → On failure: ARQ retries up to 3 times with exponential backoff
```

### Messaging Safeguards

BellBook is a school communication tool, not a social network. Messaging is scoped and controlled:

- **Rate limits:** 30 messages per user per hour. Enforced at the API level via `rate_limit.py`.
- **Mute:** Teachers can mute a conversation — they stop receiving notifications but messages are still delivered. A system message is generated: "This conversation has been muted by the teacher."
- **Block:** Teachers or school admins can block a participant in a conversation — the blocked user cannot send further messages. A system message is generated: "This conversation has been paused. Contact the school office if you need assistance."
- **Admin oversight:** School admins can view any conversation within their school for safeguarding purposes. All admin access is logged to `audit_log`.
- **Context required:** Every conversation must be linked to a specific learner (`learner_id`), keeping discussions focused and auditable.

### File Storage

- **Cloudflare R2** — S3-compatible, zero egress fees, cheaper at small scale.
- Presigned URLs for uploads and downloads via `boto3` S3-compatible client.
- Max file size: 10MB per attachment.
- Allowed types: PDF, JPEG, PNG, DOC/DOCX.

### Offline / Low-Data Support (PWA)

- Service worker caches the app shell and recent announcements.
- Announcements viewable offline (text + metadata cached).
- Messages queue locally and sync when back online.
- Images lazy-loaded with low-res placeholders.

### Observability

- **Structured logging:** `structlog` with JSON output. Every request gets a unique `request_id` injected by middleware for correlation across log lines.
- **Error tracking:** `sentry-sdk[fastapi]` — free tier provides 5k events/month, more than enough for Phase 1. Captures unhandled exceptions, slow transactions, and failed background tasks.
- **Health check:** `GET /api/health` returns connectivity status for PostgreSQL, Redis, and Cloudflare R2. Used by Docker health checks and uptime monitoring.

---

## Announcement Read Stats (First-Class Feature)

The killer metric for school admins is knowing what percentage of parents have read a notice. This drives WhatsApp/SMS fallback decisions and proves the platform's value over WhatsApp groups.

### API

```
GET /api/announcements/:id/stats
```

### Response Schema

```json
{
    "announcement_id": "uuid",
    "total_recipients": 120,
    "read_count": 102,
    "read_percentage": 85.0,
    "unread_count": 18,
    "breakdown": [
        {
            "target": "Grade 4A",
            "total": 30,
            "read": 28,
            "percentage": 93.3
        },
        {
            "target": "Grade 4B",
            "total": 32,
            "read": 25,
            "percentage": 78.1
        }
    ],
    "last_read_at": "2026-03-15T14:30:00Z"
}
```

### Dashboard View

The admin dashboard surfaces:
- Per-announcement read percentage bar (green > 80%, amber 50–80%, red < 50%)
- "Send reminder" button that re-pushes via WhatsApp/SMS to unread parents
- Daily/weekly digest of announcement engagement

---

## Onboarding Flow

### School Setup (Admin)

1. Admin registers school → creates academic year, grades, classes.
2. Admin uploads CSV of learners with parent phone numbers.
3. System sends SMS invite to each parent: "Your school is now on BellBook. Tap to set up: [link]"
4. Admin assigns teachers to classes.

### Parent Registration

1. Parent receives SMS with link.
2. Opens PWA → enters phone number → receives OTP.
3. Verifies OTP → prompted to add to home screen.
4. Sees their children (pre-linked by admin) → confirms.
5. Done. Announcements start flowing.

### CSV Import Format

```csv
learner_first_name,learner_last_name,grade,class,parent1_first_name,parent1_last_name,parent1_phone,parent1_email,parent2_first_name,parent2_last_name,parent2_phone,parent2_email
Thabo,Mokoena,Grade 4,4A,Sipho,Mokoena,0821234567,sipho@email.com,Lindiwe,Mokoena,0839876543,
```

---

## POPIA Compliance Checklist

- [ ] Privacy policy clearly displayed at registration
- [ ] Explicit consent for processing children's data
- [ ] Data minimization — only collect what's needed
- [ ] Parents can request data export (POPIA Section 23)
- [ ] Parents can request data deletion (POPIA Section 24)
- [ ] Encrypted at rest (database) and in transit (HTTPS)
- [ ] Access logs via audit_log table
- [ ] Data residency: Cloudflare R2 does not yet guarantee SA-only storage — flag for review; consider R2 jurisdiction controls or fallback to Azure South Africa North if required by pilot school
- [ ] Information Officer details published
- [ ] Data breach notification process documented

---

## Development Roadmap — Phase 1 (12 Weeks)

### Sprint 1 (Weeks 1–2): Foundation
- [ ] Project scaffolding: Vite + React Router frontend, FastAPI backend
- [ ] Docker Compose for local dev (PostgreSQL 16 + Redis 7)
- [ ] Database schema + Alembic initial migration
- [ ] Row-Level Security policies on all school-scoped tables
- [ ] Structlog + Sentry integration
- [ ] Health check endpoint

### Sprint 2 (Weeks 3–4): Auth + School Setup
- [ ] Auth system: phone OTP + email/password + JWT (access + refresh tokens)
- [ ] School CRUD + academic year, grade, class management
- [ ] CSV import for learners and parents
- [ ] User management (invite, deactivate)
- [ ] School context middleware with RLS enforcement

### Sprint 3 (Weeks 5–6): Announcements + Push
- [ ] Channels + Announcements CRUD with read tracking
- [ ] Read percentage stats endpoint + dashboard component
- [ ] Push notifications via FCM (ARQ background task)
- [ ] SSE stream for real-time announcement delivery
- [ ] Announcement feed UI (mobile-first PWA)
- [ ] Priority badges, pinned notices, draft/publish flow

### Sprint 4 (Weeks 7–8): Messaging + Admin Dashboard
- [ ] Direct messaging: conversations, messages, participants
- [ ] SSE-based message delivery (new message notifications)
- [ ] Messaging safeguards: rate limits, mute, block
- [ ] Admin read-stats dashboard (per-announcement engagement)
- [ ] "Send reminder" to unread parents (WhatsApp/SMS via ARQ)
- [ ] Conversation list + chat thread UI

### Sprint 5 (Weeks 9–10): Pilot + Supporting Features
- [ ] Pilot school onboarding (first real school)
- [ ] Feedback loop: gather and prioritize issues
- [ ] Absence reporting (parent create + teacher review flow)
- [ ] Consent forms (create + sign + report flow)
- [ ] Calendar (CRUD + iCal export)

### Sprint 6 (Weeks 11–12): Polish + Stabilize
- [ ] PWA manifest + service worker (offline support)
- [ ] WhatsApp Business API integration for urgent notices
- [ ] Notification preferences UI
- [ ] POPIA consent flows (registration privacy policy, data export request)
- [ ] Load testing (target: 1500 concurrent parents receiving a push)
- [ ] Bug fixes from pilot feedback
- [ ] Production deployment

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bellbook

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# SMS / OTP
SMS_PROVIDER=clickatell  # or bulksms
SMS_API_KEY=xxx
OTP_LENGTH=6
OTP_EXPIRY_MINUTES=5

# WhatsApp Business API
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_ACCESS_TOKEN=xxx

# Firebase Cloud Messaging
FCM_PROJECT_ID=xxx
FCM_CREDENTIALS_PATH=/path/to/firebase-credentials.json

# Cloudflare R2
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=bellbook-files
R2_PUBLIC_URL=https://files.bellbook.co.za

# Observability
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=INFO

# App
APP_URL=https://bellbook.co.za
ENVIRONMENT=development
```

---

## Docker Compose (Local Development)

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: bellbook
      POSTGRES_USER: bellbook
      POSTGRES_PASSWORD: bellbook_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

---

## Agent Instructions

This spec is designed to be handed to a Cursor agent. Here's the recommended approach:

### Getting Started

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Backend setup
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# 3. Frontend setup
cd ../frontend
npm install
npm run dev

# 4. Run ARQ worker (separate terminal)
cd backend && source venv/bin/activate
arq app.tasks.worker.WorkerSettings
```

### Backend Requirements (requirements.txt)

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.30.0
alembic>=1.14.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.18
aiofiles>=24.0.0
arq>=0.26.0
redis>=5.0.0
firebase-admin>=6.0.0
httpx>=0.28.0
boto3>=1.35.0
structlog>=24.0.0
sentry-sdk[fastapi]>=2.0.0
sse-starlette>=2.0.0
```

### Frontend Setup

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom @tanstack/react-query date-fns lucide-react
npm install -D tailwindcss @tailwindcss/vite
```

### Agent Prompts (Copy-Paste Ready)

**Prompt 0 — Local Dev Environment:**
> Set up Docker Compose with PostgreSQL 16 and Redis 7 for local development. Create the `docker-compose.yml` in the project root. Add a `Makefile` with common commands: `make up`, `make down`, `make migrate`, `make worker`. Verify connectivity with a health check endpoint at `GET /api/health` that pings DB and Redis.

**Prompt 1 — Database & Models:**
> Using the SQL schema in the spec, create SQLAlchemy async models in `app/models/` using `DeclarativeBase`. Create Alembic migration for the initial schema. Follow the exact table names and column types from the spec. Include RLS policy setup in the migration — enable RLS on all school-scoped tables and create `school_isolation` policies. Use `asyncpg` as the database driver.

**Prompt 2 — Auth System:**
> Implement phone-based OTP authentication in FastAPI. Create `app/api/auth.py` with endpoints for OTP request (via SMS), OTP verify, JWT token creation, and token refresh. Use python-jose for JWT. OTP should be 6 digits, expire in 5 minutes, stored in Redis with a TTL. The `school_context.py` middleware must set `app.current_school_id` on every DB session for RLS enforcement.

**Prompt 3 — Announcements + Read Stats:**
> Build the announcements feature: channels, announcements CRUD, read tracking. Teachers can create announcements in channels they have access to. Parents see announcements for channels linked to their children's classes. Include pagination, priority filtering, and read receipt endpoints. Add a `GET /api/announcements/:id/stats` endpoint that returns total recipients, read count, read percentage, and breakdown by grade/class. Push new announcements via SSE to connected clients.

**Prompt 4 — Frontend Shell:**
> Create a React PWA with Vite and React Router. Bottom navigation: Home, Messages, Calendar, Profile. Use Tailwind CSS. Add `manifest.json` for PWA. Build the app shell with auth-protected routes. Mobile-first responsive design. Set up TanStack React Query for server state. Create a `useSSE` hook that connects to `GET /api/events/stream` and invalidates relevant queries on incoming events.

**Prompt 5 — Messaging:**
> Implement direct messaging between parents and teachers. Use SSE for real-time message delivery (not WebSocket). Conversations are linked to a specific learner for context. Include unread badges. Add safeguards: rate limit of 30 messages per user per hour, mute and block endpoints for teachers/admins, system messages on mute/block actions. School admins can view any conversation for safeguarding (logged to audit_log).

**Prompt 6 — Notification Pipeline:**
> Set up ARQ as the background task queue with Redis. Create `app/tasks/worker.py` as the ARQ worker entrypoint. Implement notification dispatch: FCM push as primary, WhatsApp Business API for urgent priority, SMS fallback for users without push devices. Log all notifications to `notification_log`. Retry failed deliveries up to 3 times with exponential backoff. Add consent form reminder tasks.
