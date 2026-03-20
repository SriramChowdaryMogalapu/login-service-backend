import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = _to_bool(os.getenv("FLASK_DEBUG"), default=False)

    DATABASE_URL = os.getenv("DATABASE_URL")

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = _to_bool(os.getenv("MAIL_USE_TLS"), default=True)
    MAIL_USE_SSL = _to_bool(os.getenv("MAIL_USE_SSL"), default=False)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    FROM_EMAIL = os.getenv("FROM_EMAIL")
    FROM_NAME = os.getenv("FROM_NAME", "Login Service")
    MAIL_DEFAULT_SENDER = (FROM_NAME, FROM_EMAIL) if FROM_EMAIL else None
    EMAIL_BRAND_NAME = os.getenv("EMAIL_BRAND_NAME", "Login Service")
    EMAIL_PRIMARY_COLOR = os.getenv("EMAIL_PRIMARY_COLOR", "#0F766E")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "15")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "30")))
    JWT_TOKEN_LOCATION = ["cookies", "headers"]
    JWT_COOKIE_SECURE = _to_bool(os.getenv("JWT_COOKIE_SECURE"), default=ENV != "development")
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT = _to_bool(os.getenv("JWT_COOKIE_CSRF_PROTECT"), default=True)

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    DB_POOL_MIN_CONN = int(os.getenv("DB_POOL_MIN_CONN", "1"))
    DB_POOL_MAX_CONN = int(os.getenv("DB_POOL_MAX_CONN", "10"))

    PASSWORD_RESET_BASE_URL = os.getenv("PASSWORD_RESET_BASE_URL", "https://yourapp.com/reset-password")

    @classmethod
    def validate_required_envs(cls) -> None:
        required_envs = [
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
            "JWT_SECRET_KEY",
            "DATABASE_URL",
            "FROM_EMAIL",
        ]
        missing = [name for name in required_envs if not os.getenv(name)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
