import re

from pydantic import BaseModel, EmailStr, validator

from app.utils.security import validate_password_strength


class AuthRequest(BaseModel):
    app_name: str
    email: EmailStr
    password: str

    @validator("app_name")
    def validate_app_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("App name is required")
        if len(value) > 100:
            raise ValueError("App name too long")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\- ]*[A-Za-z0-9]", value):
            raise ValueError("Invalid app_name format")
        return value


class SignupRequest(BaseModel):
    app_name: str
    email: EmailStr
    password: str
    super_user: bool = False

    @validator("app_name")
    def validate_app_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("App name is required")
        if len(value) > 100:
            raise ValueError("App name too long")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\- ]*[A-Za-z0-9]", value):
            raise ValueError("Invalid app_name format")
        return value

    @validator("password")
    def strong_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class PasswordResetRequest(BaseModel):
    app_name: str
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    app_name: str
    password: str
    token: str

    @validator("password")
    def strong_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class MpinRequest(BaseModel):
    app_name: str
    mpin: str

    @validator("mpin")
    def validate_mpin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4,8}", value):
            raise ValueError("MPIN must be 4 to 8 digits")
        return value


class CreateAppRequest(BaseModel):
    app_name: str
    client_secret: str | None = None

    @validator("app_name")
    def validate_app_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("App name is required")
        if len(value) > 100:
            raise ValueError("App name too long")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\- ]*[A-Za-z0-9]", value):
            raise ValueError("Invalid app_name format")
        return value


class PromoteSuperUserRequest(BaseModel):
    app_name: str
    email: EmailStr
    super_user: bool = True
