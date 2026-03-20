import hashlib
import re


def hash_value(raw_value: str) -> str:
    return hashlib.sha256(raw_value.encode()).hexdigest()


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must include at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must include at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must include at least one digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must include at least one special character")
