import os
from pathlib import Path
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class AdminSettings:
    # MySQL read-only
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "medical_ai")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    DB_POOL_SIZE: int = 3

    # Admin auth
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD_HASH: str = os.getenv("ADMIN_PASSWORD_HASH", "")
    JWT_SECRET_KEY: str = os.getenv("ADMIN_JWT_SECRET", "admin-secret-change-in-production")
    JWT_EXPIRE_HOURS: int = 2
    JWT_ALGORITHM: str = "HS256"

    # Service
    HOST: str = os.getenv("ADMIN_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("ADMIN_PORT", "8001"))
    MAIN_APP_URL: str = os.getenv("MAIN_APP_URL", "http://localhost:8000")

    # Rate limit
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 5

    # Query
    QUERY_TIMEOUT_SECONDS: int = 5

    # Log
    AUDIT_LOG_PATH: str = str(_PROJECT_ROOT / "admin" / "admin_audit.log")


settings = AdminSettings()
