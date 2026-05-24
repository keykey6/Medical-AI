"""认证路由 — 注册 / 登录 / 游客 / 当前用户"""

from fastapi import APIRouter, HTTPException, Header

from database import save_session
from services.auth_service import (
    register_user, login_user, create_guest_session, get_current_user,
)

auth_router = APIRouter()


@auth_router.post("/register")
async def auth_register(data: dict):
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "")

    if not username or len(username) < 2:
        raise HTTPException(400, "用户名至少2个字符")
    if not password or len(password) < 4:
        raise HTTPException(400, "密码至少4个字符")

    result = register_user(username, password)
    if not result:
        raise HTTPException(409, "用户名已存在")

    return {"status": "success", "user_id": result["user_id"], "username": result["username"]}


@auth_router.post("/login")
async def auth_login(data: dict):
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    session_id = (data.get("session_id") or "").strip() or None

    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")

    if session_id:
        save_session(session_id)

    result = login_user(username, password, session_id)
    if not result:
        raise HTTPException(401, "用户名或密码错误")

    return {
        "status": "success",
        "token": result["token"],
        "user_id": result["user_id"],
        "username": result["username"],
    }


@auth_router.post("/guest")
async def auth_guest(data: dict | None = None):
    session_id = (data or {}).get("session_id", "").strip() or None
    result = create_guest_session(session_id)
    if result.get("session_id"):
        save_session(result["session_id"])
    return {"status": "success", "session_id": result["session_id"], "is_anonymous": True}


@auth_router.get("/me")
async def auth_me(authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    if not user:
        return {"user": None, "is_anonymous": True}
    return {
        "user": {"user_id": user["user_id"], "username": user["username"]},
        "is_anonymous": False,
    }
