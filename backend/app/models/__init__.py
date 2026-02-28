# Import all models so they are registered with Base.metadata
# before Alembic or SQLAlchemy inspects it.
from app.models.school import School, AcademicYear, Grade, Class  # noqa: F401
from app.models.user import User, Learner, ClassLearner, ClassTeacher, LearnerGuardian  # noqa: F401
from app.models.announcement import Channel, Announcement, AnnouncementAttachment, AnnouncementRead  # noqa: F401
from app.models.messaging import Conversation, ConversationParticipant, Message, MessageAttachment  # noqa: F401
from app.models.absence import AbsenceReport  # noqa: F401
from app.models.consent import ConsentForm, ConsentResponse  # noqa: F401
from app.models.calendar import CalendarEvent  # noqa: F401
from app.models.notification import PushDevice, NotificationPreference, NotificationLog, AuditLog  # noqa: F401
