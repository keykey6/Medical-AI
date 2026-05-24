"""会话聚合分析"""

from admin.database.admin_db import get_session_analytics


def get_sessions() -> dict:
    data = get_session_analytics()
    return {
        "total_sessions": data["total_sessions"],
        "active_sessions": data["sessions_with_chat"],
        "anonymous_sessions": data["anonymous_sessions"],
        "authenticated_sessions": data["authenticated_sessions"],
        "depth_distribution": data["depth_distribution"],
        "hourly_24h": data["hourly_distribution_24h"],
        "summary": {
            "anonymous_rate": round(
                data["anonymous_sessions"] / data["total_sessions"] * 100, 1
            ) if data["total_sessions"] else 0,
        },
    }
