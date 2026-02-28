import uuid

from pydantic import BaseModel, field_validator


class OTPRequestSchema(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def normalise_phone(cls, v: str) -> str:
        # Strip spaces and dashes; keep leading +
        return v.replace(" ", "").replace("-", "")


class OTPVerifySchema(BaseModel):
    phone: str
    otp: str


class RegisterSchema(BaseModel):
    """Parent self-registration via phone OTP."""

    phone: str
    otp: str
    first_name: str
    last_name: str
    school_id: uuid.UUID  # encoded in the invite link


class EmailLoginSchema(BaseModel):
    """Teacher / school_admin login via email + password."""

    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID | None
    email: str | None
    phone: str | None
    first_name: str
    last_name: str
    role: str
    preferred_lang: str
    avatar_url: str | None
    is_active: bool

    model_config = {"from_attributes": True}
