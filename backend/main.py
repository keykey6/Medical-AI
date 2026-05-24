import asyncio
import logging
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure backend/ and project root are on path
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _BACKEND_DIR.parent
sys.path.insert(0, str(_BACKEND_DIR))
sys.path.insert(0, str(_PROJECT_DIR))

from config import settings
from core import setup_logging, global_exception_handler

logger = logging.getLogger("app")

# Paths
_FRONTEND_DIR = str(_PROJECT_DIR / "frontend")
_KNOWLEDGE_DIR = str(_PROJECT_DIR / "知识库")
_STATIC_DIR = str(_PROJECT_DIR / "static")  # fallback if old static/ exists


async def _async_init_rag():
    await asyncio.sleep(2)
    try:
        from services.rag_service import load_knowledge_base
        load_knowledge_base()
    except Exception:
        logger.warning("后台加载知识库失败（不影响基础服务）")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from database.connection import init_database
    init_database()
    asyncio.create_task(_async_init_rag())
    logger.info("医疗AI智能客服服务启动成功")
    yield


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.APP_TITLE,
        description="合规医疗知识问答系统",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(global_exception_handler)

    # Mount frontend as static files
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR, html=True), name="static")

    from api.chat import chat_router
    from api.session import session_router
    from api.report import report_router
    from api.health import health_router
    from api.map import map_router
    from api.auth import auth_router

    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    app.include_router(session_router, prefix="/api/session", tags=["session"])
    app.include_router(report_router, prefix="/api/report", tags=["report"])
    app.include_router(health_router, prefix="/api/health", tags=["health"])
    app.include_router(map_router, prefix="/api/map", tags=["map"])
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

    @app.get("/")
    async def root():
        return {"message": "医疗AI智能客服服务已启动"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
