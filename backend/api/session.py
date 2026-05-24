"""会话管理 API — 用户隔离的会话列表/创建/删除/重命名"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from database import (
    save_session, get_session, delete_session,
    list_user_sessions, rename_session,
)
from services.auth_service import get_current_user
import uuid

session_router = APIRouter()


class SessionCreate(BaseModel):
    user_info: str | None = None


class SessionItem(BaseModel):
    session_id: str
    title: str | None = None
    created_at: str | None = None
    last_active: str | None = None
    msg_count: int = 0
    last_message: str | None = None


class SessionListResponse(BaseModel):
    sessions: List[SessionItem]
    total: int


class RenameRequest(BaseModel):
    title: str


@session_router.post("/create")
async def create_session(authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    session_id = str(uuid.uuid4())
    save_session(session_id, user_id=user["user_id"] if user else None)
    return {"session_id": session_id, "user_id": user["user_id"] if user else None}


@session_router.get("/list", response_model=SessionListResponse)
async def list_sessions(authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    if not user:
        return SessionListResponse(sessions=[], total=0)

    sessions = list_user_sessions(user["user_id"])
    items = [
        SessionItem(
            session_id=s["session_id"],
            title=s.get("title"),
            created_at=str(s.get("created_at", "")),
            last_active=str(s.get("last_active", "")),
            msg_count=s.get("msg_count", 0),
            last_message=s.get("last_message"),
        )
        for s in (sessions or [])
    ]
    return SessionListResponse(sessions=items, total=len(items))


@session_router.get("/{session_id}")
async def get_session_info(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {
        "session_id": session["session_id"],
        "title": session.get("title"),
        "created_at": str(session.get("created_at", "")),
        "last_active": str(session.get("last_active", "")),
    }


@session_router.post("/{session_id}/keepalive")
async def keepalive(session_id: str):
    save_session(session_id)
    return {"status": "success"}


@session_router.delete("/{session_id}")
async def delete_session_by_id(session_id: str, authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    success = delete_session(session_id, user_id=user["user_id"] if user else None)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在或无权删除")
    return {"status": "success", "message": "会话已删除"}


@session_router.post("/{session_id}/rename")
async def rename(session_id: str, request: RenameRequest, authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    success = rename_session(session_id, user["user_id"], request.title[:50].strip())
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在或无权操作")
    return {"status": "success", "title": request.title[:50].strip()}
