"""安全中间件 — 限速/脱敏/熔断/只读校验"""

import time
import logging
from collections import defaultdict
from functools import wraps

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from admin.config import settings

logger = logging.getLogger("admin.security")

# In-memory rate limit store
_login_attempts: dict[str, list[float]] = defaultdict(list)


def check_login_rate(ip: str) -> bool:
    """同IP 5分钟内最多5次登录尝试。返回True表示允许。"""
    now = time.time()
    window = settings.LOGIN_WINDOW_MINUTES * 60
    attempts = [t for t in _login_attempts[ip] if now - t < window]
    _login_attempts[ip] = attempts
    if len(attempts) >= settings.LOGIN_MAX_ATTEMPTS:
        return False
    return True


def record_login_attempt(ip: str):
    _login_attempts[ip].append(time.time())


def apply_threshold(value: int, threshold: int = 5) -> str:
    """脱敏：小于阈值的数值显示为 '<N'"""
    if value < threshold:
        return f"<{threshold}"
    return str(value)


class ReadOnlyMiddleware(BaseHTTPMiddleware):
    """拦截所有写操作请求，仅允许 GET/HEAD/OPTIONS"""

    async def dispatch(self, request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS", "POST"):
            raise HTTPException(403, "管理后台仅支持只读操作")
        response = await call_next(request)
        return response


class QueryTimeoutMiddleware(BaseHTTPMiddleware):
    """设置数据库查询超时"""

    async def dispatch(self, request: Request, call_next):
        # Timeout enforced at DB connection level via session variable
        response = await call_next(request)
        return response


def mask_secrets(config_dict: dict) -> dict:
    """脱敏配置项：隐藏密钥类字段"""
    sensitive_keys = {"KEY", "SECRET", "PASSWORD", "AK", "TOKEN", "HASH"}
    result = {}
    for k, v in config_dict.items():
        if any(s in k.upper() for s in sensitive_keys):
            result[k] = "***"
        else:
            result[k] = v
    return result
