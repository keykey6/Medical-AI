"""医疗AI智能客服 — 一键启动脚本（前后端分离架构）"""

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from backend.config import settings
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s | %(message)s")
logger = logging.getLogger("startup")


def install_requirements():
    logger.info("正在安装依赖包...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt")])


def check_mysql():
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host=settings.MYSQL_HOST, user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD, port=settings.MYSQL_PORT,
        )
        if connection.is_connected():
            connection.close()
            logger.info("MySQL 连接成功")
            return True
    except Exception as e:
        logger.warning("MySQL 连接失败: %s", e)
    return False


def init_database():
    from backend.database.connection import init_database
    init_database()


def load_knowledge_base():
    logger.info("正在加载知识库...")
    try:
        from backend.services.rag_service import load_knowledge_base as load_kb
        load_kb()
        logger.info("知识库加载成功")
    except Exception as e:
        logger.warning("知识库加载失败: %s", e)


def start_server():
    logger.info("正在启动 FastAPI 服务...")
    logger.info("服务地址: http://localhost:%d", settings.PORT)
    logger.info("前端界面: http://localhost:%d/static/index.html", settings.PORT)
    subprocess.run([
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", settings.HOST, "--port", str(settings.PORT), "--reload",
    ])


def main():
    print("=" * 60)
    print("  医疗AI智能客服 — 前后端分离架构")
    print("=" * 60)

    install_requirements()

    print("\n检查 MySQL 连接...")
    if check_mysql():
        init_database()
    else:
        logger.warning("MySQL 不可用，数据库功能受限")

    print("\n加载知识库...")
    load_knowledge_base()

    print("\n" + "=" * 60)
    print("启动服务...")
    print("=" * 60)
    start_server()


if __name__ == "__main__":
    main()
