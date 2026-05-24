import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app")


async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.exception(f"未处理的异常: {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "服务器内部错误，请稍后重试",
                "error": str(e) if __debug__ else None,
            },
        )
