"""操作审计日志"""

import logging
from datetime import datetime

from admin.config import settings

logger = logging.getLogger("admin.audit")


def audit_log(action: str, detail: str = "", ip: str = ""):
    msg = f"{datetime.now().isoformat()} | {action} | {detail} | IP={ip}"
    logger.info(msg)
    try:
        with open(settings.AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
