from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://bellbook:bellbook_dev@localhost:5432/bellbook"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # SMS / OTP
    SMS_PROVIDER: str = "clickatell"
    SMS_API_KEY: str = ""
    OTP_LENGTH: int = 6
    OTP_EXPIRY_MINUTES: int = 5

    # WhatsApp Business API
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0/"
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    # Firebase Cloud Messaging
    FCM_PROJECT_ID: str = ""
    FCM_CREDENTIALS_PATH: str = "/path/to/firebase-credentials.json"

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "bellbook-files"
    R2_PUBLIC_URL: str = "https://files.bellbook.co.za"

    # Observability
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    # App
    APP_URL: str = "https://bellbook.co.za"
    ENVIRONMENT: str = "development"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
