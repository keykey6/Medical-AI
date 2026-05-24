"""合规监控聚合"""

from admin.database.admin_db import get_compliance_stats


def get_compliance() -> dict:
    data = get_compliance_stats()
    return {
        "blocked_count": data["blocked_count"],
        "triage_count": data["triage_count"],
        "total_count": data["total_count"],
        "block_rate_pct": data["block_rate"],
        "by_type": data["by_type"],
        "summary": "合规拦截 + 转人工占比分析",
    }
