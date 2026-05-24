"""管理后台 API — /admin/api/*"""

from fastapi import APIRouter, HTTPException, Header, Request

from admin.core.auth import get_current_admin, authenticate_admin
from admin.core.security import check_login_rate, record_login_attempt
from admin.core.audit_logger import audit_log
from admin.database.admin_db import get_dashboard_stats
from admin.services.dashboard_service import get_dashboard, get_trends
from admin.services.session_analytics import get_sessions
from admin.services.compliance_monitor import get_compliance
from admin.services.qos_service import get_qos
from admin.services.system_ops import get_health, get_config

admin_router = APIRouter()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _ok(data: dict) -> dict:
    from datetime import datetime, timezone
    return {"code": 200, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Auth ─────────────────────────────────────────────────────────────

@admin_router.post("/login")
async def admin_login(data: dict, request: Request):
    ip = _get_client_ip(request)
    if not check_login_rate(ip):
        raise HTTPException(429, "登录频率过高，请5分钟后重试")

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    token = authenticate_admin(username, password)
    if not token:
        record_login_attempt(ip)
        audit_log("LOGIN_FAILED", f"user={username}", ip)
        raise HTTPException(401, "用户名或密码错误")

    audit_log("LOGIN_SUCCESS", f"user={username}", ip)
    return _ok({"token": token, "username": username})


# ── Dashboard ─────────────────────────────────────────────────────────

@admin_router.get("/dashboard/stats")
async def dashboard_stats(authorization: str | None = Header(None)):
    admin = get_current_admin(authorization)
    if not admin:
        raise HTTPException(401, "未授权访问")
    stats = get_dashboard_stats()
    return _ok(get_dashboard(stats))


@admin_router.get("/dashboard/trends")
async def dashboard_trends(authorization: str | None = Header(None)):
    admin = get_current_admin(authorization)
    if not admin:
        raise HTTPException(401, "未授权访问")
    return _ok(get_trends())


# ── Sessions ──────────────────────────────────────────────────────────

@admin_router.get("/sessions/analytics")
async def session_analytics(authorization: str | None = Header(None)):
    admin = get_current_admin(authorization)
    if not admin:
        raise HTTPException(401, "未授权访问")
    return _ok(get_sessions())


# ── Compliance ────────────────────────────────────────────────────────

@admin_router.get("/compliance/summary")
async def compliance_summary(authorization: str | None = Header(None)):
    admin = get_current_admin(authorization)
    if not admin:
        raise HTTPException(401, "未授权访问")
    return _ok(get_compliance())


# ── QoS ───────────────────────────────────────────────────────────────

@admin_router.get("/qos/metrics")
async def qos_metrics(authorization: str | None = Header(None)):
    admin = get_current_admin(authorization)
    if not admin:
        raise HTTPException(401, "未授权访问")
    return _ok(get_qos())


# ── System ────────────────────────────────────────────────────────────

@admin_router.get("/system/health")
async def system_health(authorization: str | None = Header(None)):
    admin = get_current_admin(authorization)
    if not admin:
        raise HTTPException(401, "未授权访问")
    return _ok(get_health())


@admin_router.get("/system/config")
async def system_config(authorization: str | None = Header(None)):
    admin = get_current_admin(authorization)
    if not admin:
        raise HTTPException(401, "未授权访问")
    audit_log("CONFIG_VIEW", f"admin={admin.get('sub')}")
    return _ok({"config": get_config()})
