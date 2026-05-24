"""仪表盘聚合指标"""

from admin.database.admin_db import get_dashboard_stats, get_trend_7days
from admin.core.security import apply_threshold


def get_dashboard(stats: dict) -> dict:
    return {
        "cards": [
            {"label": "累计对话", "value": f"{stats['total_chats']:,}", "icon": "fa-comments", "color": "teal"},
            {"label": "今日活跃会话", "value": f"{stats['today_sessions']:,}", "icon": "fa-users", "color": "gold"},
            {"label": "用户总数", "value": apply_threshold(stats["user_count"], 5), "icon": "fa-user-shield", "color": "blue"},
            {"label": "会话总数", "value": f"{stats['total_sessions']:,}", "icon": "fa-folder-tree", "color": "amber"},
            {"label": "报告解读", "value": f"{stats['total_reports']:,}", "icon": "fa-file-medical", "color": "rose"},
            {"label": "健康档案", "value": f"{stats['total_profiles']:,}", "icon": "fa-heart-pulse", "color": "green"},
        ],
        "message_type_distribution": stats["message_types"],
    }


def get_trends() -> dict:
    data = get_trend_7days()
    return {
        "days": [r["day"] for r in data],
        "chat_counts": [r["chat_count"] for r in data],
        "session_counts": [r["session_count"] for r in data],
    }
