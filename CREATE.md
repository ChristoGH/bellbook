# SchoolConnect — Phase 1 MVP Specification

## Product Overview

**SchoolConnect** is a Progressive Web App (PWA) that replaces WhatsApp groups, printed notices, and legacy school communication tools (like D6) with a modern, two-way communication platform for schools, teachers, and parents in South Africa.

**Target Market:** Independent and public schools in South Africa (800–1500 learners)
**Business Model:** SaaS — R5–R15 per learner/month
**Tech Stack:** React (PWA) + FastAPI + PostgreSQL + Firebase Cloud Messaging + WhatsApp Business API

---

## Phase 1 Scope — Communication MVP

Phase 1 focuses exclusively on replacing WhatsApp groups and one-way notice systems with a proper school communication platform.

### Core Features

1. **School Announcements** — broadcast notices with read tracking
2. **Direct Messaging** — parent ↔ teacher private messaging
3. **Absentee Reporting** — parents report absences from the app
4. **Digital Consent Forms** — sign permission slips digitally
5. **School Calendar** — events, terms, exam dates in one place
6. **Push Notifications** — with priority levels (urgent / normal / info)
7. **WhatsApp Fallback** — critical notices also sent via WhatsApp API

### Out of Scope (Phase 2+)

- Fee management / payments
- Gradebook / academic tracking
- Transport tracking
- Tuckshop ordering
- AI features (summaries, chatbot, anomaly detection)

---

## User Roles & Permissions

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| **Super Admin** | System administrator (you) | Manage all schools, global config |
| **School Admin** | Principal / secretary | Manage school, teachers, classes, parents |
| **Teacher** | Class teacher or subject teacher | Send class announcements, message parents, mark attendance |
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
    file_url        TEXT NOT NULL,                   -- S3/Azure Blob URL
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
    UNIQUE(conversation_id, user_id)
);

CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id       UUID NOT NULL REFERENCES users(id),
    body            TEXT NOT NULL,
    is_system       BOOLEAN DEFAULT false,          -- system-generated message
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
DELETE /api/announcements/:id       # Delete announcement
```

### Direct Messaging

```
GET    /api/conversations           # List my conversations
POST   /api/conversations           # Start new conversation
GET    /api/conversations/:id/messages  # List messages (paginated)
POST   /api/conversations/:id/messages  # Send message
PUT    /api/conversations/:id/read  # Mark conversation as read
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

---

## Frontend Structure (React PWA)

```
src/
├── app/
│   ├── layout.tsx
│   └── routes/
│       ├── auth/
│       │   ├── login.tsx            # Phone + OTP login
│       │   └── register.tsx         # Parent self-registration
│       ├── dashboard/
│       │   └── index.tsx            # Role-based home screen
│       ├── announcements/
│       │   ├── index.tsx            # Feed view
│       │   ├── [id].tsx             # Single announcement
│       │   └── create.tsx           # Create/edit (teacher/admin)
│       ├── messages/
│       │   ├── index.tsx            # Conversation list
│       │   └── [id].tsx             # Chat thread
│       ├── absences/
│       │   ├── report.tsx           # Parent: report form
│       │   └── manage.tsx           # Teacher: review absences
│       ├── consent/
│       │   ├── index.tsx            # List forms
│       │   ├── [id].tsx             # View & sign form
│       │   └── create.tsx           # Create form (admin)
│       ├── calendar/
│       │   ├── index.tsx            # Calendar view
│       │   └── create.tsx           # Create event
│       └── settings/
│           ├── profile.tsx
│           └── notifications.tsx
├── components/
│   ├── ui/                         # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   └── Avatar.tsx
│   ├── layout/
│   │   ├── AppShell.tsx            # Main app layout with nav
│   │   ├── BottomNav.tsx           # Mobile bottom navigation
│   │   └── TopBar.tsx
│   ├── announcements/
│   │   ├── AnnouncementCard.tsx
│   │   ├── AnnouncementFeed.tsx
│   │   └── ReadReceipts.tsx
│   ├── messages/
│   │   ├── ConversationList.tsx
│   │   ├── ChatBubble.tsx
│   │   └── MessageInput.tsx
│   └── common/
│       ├── PriorityBadge.tsx
│       ├── FileUpload.tsx
│       └── EmptyState.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useAnnouncements.ts
│   ├── useConversations.ts
│   └── usePushNotifications.ts
├── lib/
│   ├── api.ts                      # Axios/fetch wrapper
│   ├── auth.ts                     # JWT token management
│   └── notifications.ts            # FCM setup
├── types/
│   └── index.ts                    # TypeScript interfaces matching API
├── manifest.json                   # PWA manifest
└── service-worker.ts               # Offline caching strategy
```

---

## Backend Structure (FastAPI)

```
app/
├── main.py                         # FastAPI app entry point
├── config.py                       # Settings (env vars, DB URL, etc.)
├── database.py                     # SQLAlchemy engine & session
├── models/
│   ├── __init__.py
│   ├── school.py                   # School, AcademicYear, Grade, Class
│   ├── user.py                     # User, Learner, LearnerGuardian
│   ├── announcement.py             # Channel, Announcement, Read, Attachment
│   ├── messaging.py                # Conversation, Participant, Message
│   ├── absence.py                  # AbsenceReport
│   ├── consent.py                  # ConsentForm, ConsentResponse
│   ├── calendar.py                 # CalendarEvent
│   └── notification.py             # PushDevice, NotificationLog, AuditLog
├── schemas/
│   ├── __init__.py
│   ├── auth.py                     # Login, Register, OTP request/response
│   ├── school.py
│   ├── user.py
│   ├── announcement.py
│   ├── messaging.py
│   ├── absence.py
│   ├── consent.py
│   ├── calendar.py
│   └── notification.py
├── api/
│   ├── __init__.py
│   ├── deps.py                     # Dependencies (get_db, get_current_user)
│   ├── auth.py                     # Auth routes
│   ├── schools.py
│   ├── announcements.py
│   ├── messaging.py
│   ├── absences.py
│   ├── consent.py
│   ├── calendar.py
│   └── notifications.py
├── services/
│   ├── __init__.py
│   ├── auth_service.py             # OTP generation, JWT creation
│   ├── notification_service.py     # FCM + WhatsApp + SMS dispatch
│   ├── file_service.py             # Azure Blob upload/download
│   └── import_service.py           # CSV bulk import of learners/parents
├── middleware/
│   ├── auth.py                     # JWT verification middleware
│   ├── school_context.py           # Inject school context from subdomain/header
│   └── rate_limit.py               # API rate limiting
├── tasks/
│   ├── __init__.py
│   ├── notifications.py            # Background: send push/WhatsApp/SMS
│   └── reminders.py                # Background: consent form reminders
├── alembic/                        # Database migrations
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_announcements.py
│   ├── test_messaging.py
│   └── test_absences.py
└── requirements.txt
```

---

## Key Technical Decisions

### Authentication Strategy

- **Parents:** Phone number + OTP (SMS). Most SA parents won't have work email.
- **Teachers/Admin:** Email + password (optional OTP). Schools often use institutional email.
- **JWT tokens** with short-lived access tokens (15 min) and refresh tokens (30 days).
- **School context** derived from subdomain (e.g., `rivonia-primary.schoolconnect.co.za`) or a school selection step during login.

### Multi-tenancy

- **Shared database, school_id column** approach. Simple, cost-effective for a side hustle.
- All queries scoped by `school_id` enforced at the middleware/dependency level.
- Row-Level Security (RLS) in PostgreSQL as a safety net.

### Notification Delivery Pipeline

```
Event triggers notification
    → Queue (Redis/Celery or simple background task)
        → For each recipient:
            1. Push notification (FCM) — primary
            2. If priority == 'urgent' AND user has WhatsApp: send via WhatsApp Business API
            3. If no push device registered: fallback to SMS
            4. Log to notification_log table
```

### File Storage

- **Azure Blob Storage** (you know it well) or **Cloudflare R2** (cheaper, S3-compatible).
- Presigned URLs for uploads and downloads.
- Max file size: 10MB per attachment.
- Allowed types: PDF, JPEG, PNG, DOC/DOCX.

### Offline / Low-Data Support (PWA)

- Service worker caches the app shell and recent announcements.
- Announcements viewable offline (text + metadata cached).
- Messages queue locally and sync when back online.
- Images lazy-loaded with low-res placeholders.

---

## Onboarding Flow

### School Setup (Admin)

1. Admin registers school → creates academic year, grades, classes.
2. Admin uploads CSV of learners with parent phone numbers.
3. System sends SMS invite to each parent: "Your school is now on SchoolConnect. Tap to set up: [link]"
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
- [ ] Data stored in South Africa (Azure South Africa North region)
- [ ] Information Officer details published
- [ ] Data breach notification process documented

---

## Development Roadmap — Phase 1

### Sprint 1 (Week 1-2): Foundation
- [ ] Project scaffolding (FastAPI + React + PostgreSQL)
- [ ] Database schema + Alembic migrations
- [ ] Auth system (OTP + JWT)
- [ ] School/Grade/Class CRUD
- [ ] CSV import for learners/parents

### Sprint 2 (Week 3-4): Communication Core
- [ ] Channels + Announcements (CRUD + read tracking)
- [ ] Push notifications (FCM setup)
- [ ] Direct messaging (conversations + real-time via WebSocket)
- [ ] Announcement feed UI (PWA)

### Sprint 3 (Week 5-6): Supporting Features
- [ ] Absence reporting (create + review flow)
- [ ] Consent forms (create + sign flow)
- [ ] Calendar (CRUD + iCal export)
- [ ] WhatsApp API integration for urgent notices

### Sprint 4 (Week 7-8): Polish & Launch
- [ ] PWA manifest + service worker (offline support)
- [ ] Notification preferences
- [ ] School admin dashboard (read stats, usage metrics)
- [ ] POPIA consent flows
- [ ] Load testing
- [ ] Pilot school deployment

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/schoolconnect

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

# File Storage
AZURE_STORAGE_CONNECTION_STRING=xxx
AZURE_STORAGE_CONTAINER=schoolconnect-files

# App
APP_URL=https://schoolconnect.co.za
ENVIRONMENT=development
```

---

## Agent Instructions

This spec is designed to be handed to Claude Code or Cursor agent. Here's the recommended approach:

### Getting Started

```bash
# 1. Create the project
mkdir schoolconnect && cd schoolconnect

# 2. Backend setup
mkdir -p backend && cd backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary pydantic python-jose passlib python-multipart aiofiles celery redis firebase-admin httpx

# 3. Frontend setup
cd .. && npx create-react-app frontend --template typescript
cd frontend
npm install react-router-dom axios date-fns lucide-react tailwindcss
```

### Agent Prompts (Copy-Paste Ready)

**Prompt 1 — Database & Models:**
> Using the SQL schema in the spec, create SQLAlchemy models in `app/models/`. Use `declarative_base`. Create Alembic migration for the initial schema. Follow the exact table names and column types from the spec.

**Prompt 2 — Auth System:**
> Implement phone-based OTP authentication in FastAPI. Create `app/api/auth.py` with endpoints for OTP request (via SMS), OTP verify, JWT token creation, and token refresh. Use python-jose for JWT. OTP should be 6 digits, expire in 5 minutes, stored in Redis or a DB table.

**Prompt 3 — Announcements:**
> Build the announcements feature: channels, announcements CRUD, read tracking. Teachers can create announcements in channels they have access to. Parents see announcements for channels linked to their children's classes. Include pagination, priority filtering, and read receipt endpoints.

**Prompt 4 — Frontend Shell:**
> Create a React PWA with bottom navigation (Home, Messages, Calendar, Profile). Use Tailwind CSS. Add manifest.json for PWA. Build the app shell with auth-protected routes. Mobile-first responsive design.

**Prompt 5 — Messaging:**
> Implement direct messaging between parents and teachers. Use WebSocket for real-time message delivery. Conversations are linked to a specific learner for context. Include unread badges and typing indicators.