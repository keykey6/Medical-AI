"""服务质量聚合"""

from admin.database.admin_db import get_qos_metrics


def get_qos() -> dict:
    data = get_qos_metrics()
    return {
        "report_type_distribution": data["report_types"],
        "recent_24h_blocks": data["recent_24h_blocks"],
    }
