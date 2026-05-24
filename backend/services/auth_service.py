"""认证服务 — JWT令牌管理 + 用户注册/登录"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from config import settings
from database.user_repo import (
    create_user, get_user_by_username, get_user_by_id,
    bind_session_to_user, mark_session_anonymous, get_session_user,
)
from shared.auth_utils import hash_password, verify_password


def create_access_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user(authorization: str | None) -> dict | None:
    """从 Authorization Header 提取当前用户。返回 {user_id, username} 或 None。"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        return None
    return {"user_id": payload["sub"], "username": payload["username"]}


def register_user(username: str, password: str) -> dict | None:
    """注册新用户。返回用户信息或None（用户名已存在）。"""
    existing = get_user_by_username(username)
    if existing:
        return None
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    ok = create_user(user_id, username, password_hash)
    if not ok:
        return None
    return {"user_id": user_id, "username": username}


def login_user(username: str, password: str, session_id: str | None = None) -> dict | None:
    """验证登录，返回 token + user_info。可选绑定session。"""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    token = create_access_token(user["user_id"], user["username"])
    if session_id:
        bind_session_to_user(session_id, user["user_id"])
    return {
        "token": token,
        "user_id": user["user_id"],
        "username": user["username"],
    }


def create_guest_session(session_id: str | None = None) -> dict:
    """创建游客会话。"""
    sid = session_id or str(uuid.uuid4())
    mark_session_anonymous(sid)
    return {"session_id": sid, "is_anonymous": True}
