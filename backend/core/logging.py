import logging
import sys
from config import settings


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet down noisy third-party loggers
    for name in ("uvicorn", "uvicorn.access", "faiss", "sentence_transformers"):
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("app").info("日志系统初始化完成")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
