"""管理员认证 — JWT签发/验证 + 密码哈希"""

import os
from datetime import datetime, timedelta, timezone

import jwt

from admin.config import settings
from shared.auth_utils import hash_password, verify_password


def create_admin_token(username: str) -> str:
    payload = {
        "sub": username,
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_admin_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("role") != "admin":
            return None
        return payload
    except jwt.InvalidTokenError:
        return None


def get_current_admin(authorization: str | None) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return verify_admin_token(authorization[7:])


def authenticate_admin(username: str, password: str) -> str | None:
    if username != settings.ADMIN_USERNAME:
        return None
    if not settings.ADMIN_PASSWORD_HASH:
        # First run fallback: compare against plain config
        if password == os.getenv("ADMIN_PASSWORD", "admin123"):
            return create_admin_token(username)
        return None
    if not verify_password(password, settings.ADMIN_PASSWORD_HASH):
        return None
    return create_admin_token(username)
