import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of backend/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Settings:
    # MySQL
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "medical_ai")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_POOL_NAME: str = os.getenv("DB_POOL_NAME", "medical_ai_pool")

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    OLLAMA_MULTIMODAL_MODEL: str = os.getenv("OLLAMA_MULTIMODAL_MODEL", "llava:7b")

    # DeepSeek
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL: str = os.getenv(
        "DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"
    )

    # Baidu Map
    BAIDU_MAP_AK: str = os.getenv("BAIDU_MAP_AK", "")
    BAIDU_MAP_SERVER_AK: str = os.getenv("BAIDU_MAP_SERVER_AK", "")

    # Vector DB
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vector_db")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))

    # App
    CURRENT_MODEL: str = os.getenv("CURRENT_MODEL", "ollama")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_CONTEXT_LENGTH: int = int(os.getenv("MAX_CONTEXT_LENGTH", "10"))
    ENABLE_WEB_SEARCH: bool = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
    APP_TITLE: str = "医疗AI智能客服"
    APP_VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "medical-ai-secret-key-change-in-production")
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "72"))
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Compliance
    DISCLAIMER: str = "本文仅供科普参考，不构成医疗建议。如有不适，请及时就医。"


settings = Settings()
