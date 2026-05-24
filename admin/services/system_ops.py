"""系统运维探测"""

import os
import requests

from admin.config import settings
from admin.core.security import mask_secrets
from admin.database.admin_db import get_knowledge_status


def get_health() -> dict:
    services = {}

    # Main app health check
    try:
        r = requests.get(f"{settings.MAIN_APP_URL}/health", timeout=3)
        services["main_app"] = "healthy" if r.status_code == 200 else "degraded"
    except Exception:
        services["main_app"] = "unreachable"

    # MySQL connection check
    try:
        from admin.database.admin_db import get_pool
        conn = get_pool().get_connection()
        conn.ping()
        conn.close()
        services["mysql"] = "healthy"
    except Exception:
        services["mysql"] = "unreachable"

    # Ollama check
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        r = requests.get(f"{ollama_url}/api/tags", timeout=3)
        services["ollama"] = "healthy" if r.status_code == 200 else "degraded"
    except Exception:
        services["ollama"] = "unreachable"

    return {"services": services, "knowledge": get_knowledge_status()}


def get_config() -> dict:
    raw = {
        "MYSQL_HOST": settings.MYSQL_HOST,
        "MYSQL_DATABASE": settings.MYSQL_DATABASE,
        "MYSQL_PORT": settings.MYSQL_PORT,
        "DB_POOL_SIZE": settings.DB_POOL_SIZE,
        "CURRENT_MODEL": os.getenv("CURRENT_MODEL", "ollama"),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", ""),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", ""),
        "BAIDU_MAP_AK": os.getenv("BAIDU_MAP_AK", ""),
        "PORT": os.getenv("PORT", "8000"),
        "ADMIN_PORT": str(settings.PORT),
        "ENABLE_WEB_SEARCH": os.getenv("ENABLE_WEB_SEARCH", ""),
        "MAX_CONTEXT_LENGTH": os.getenv("MAX_CONTEXT_LENGTH", ""),
    }
    return mask_secrets(raw)
