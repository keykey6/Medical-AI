"""管理后台 FastAPI 应用工厂"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

_ADMIN_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _ADMIN_DIR.parent
sys.path.insert(0, str(_ADMIN_DIR))
sys.path.insert(0, str(_PROJECT_DIR))

from admin.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("admin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"管理后台启动 — {settings.HOST}:{settings.PORT}")
    yield


def create_admin_app() -> FastAPI:
    app = FastAPI(
        title="医疗AI智能客服 — 管理后台",
        description="独立管理后台服务，仅面向管理员角色",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add API routes first (before static files)
    from admin.api.admin import admin_router
    app.include_router(admin_router, prefix="/admin/api", tags=["admin"])
    
    # Mount frontend static files at /admin path
    frontend_dir = str(_ADMIN_DIR / "frontend")
    app.mount("/admin", StaticFiles(directory=frontend_dir, html=True), name="admin_static")
    
    # Serve admin panel at root
    @app.get("/")
    async def admin_root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/admin/login.html")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "admin"}

    return app


app = create_admin_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
