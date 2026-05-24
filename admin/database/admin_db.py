"""只读数据库连接 + 聚合查询封装"""

import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

from admin.config import settings

_pool: MySQLConnectionPool | None = None


def get_pool() -> MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = MySQLConnectionPool(
            pool_name="admin_ro_pool",
            pool_size=settings.DB_POOL_SIZE,
            host=settings.MYSQL_HOST,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DATABASE,
            port=settings.MYSQL_PORT,
            charset="utf8mb4",
        )
    return _pool


def get_connection():
    conn = get_pool().get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
    except Exception:
        pass  # MySQL 5.x compatibility
    try:
        cursor.execute(f"SET SESSION max_execution_time = {settings.QUERY_TIMEOUT_SECONDS * 1000}")
    except Exception:
        pass  # not supported in all versions
    cursor.close()
    return conn


def query_one(sql: str, params=None) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def query_all(sql: str, params=None) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def query_scalar(sql: str, params=None) -> int | float:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        cursor.close()
        conn.close()


# ── Aggregation Queries ──────────────────────────────────────────────


def get_dashboard_stats() -> dict:
    total_chats = query_scalar("SELECT COUNT(*) FROM chat_logs")
    today_sessions = query_scalar(
        "SELECT COUNT(DISTINCT session_id) FROM chat_logs WHERE DATE(created_at) = CURDATE()"
    )
    total_sessions = query_scalar("SELECT COUNT(*) FROM sessions")
    total_reports = query_scalar("SELECT COUNT(*) FROM report_records")
    total_profiles = query_scalar("SELECT COUNT(*) FROM health_profiles")
    user_count = query_scalar("SELECT COUNT(*) FROM users")

    message_types = query_all(
        "SELECT message_type, COUNT(*) AS cnt FROM chat_logs GROUP BY message_type ORDER BY cnt DESC"
    )

    return {
        "total_chats": total_chats,
        "today_sessions": today_sessions,
        "total_sessions": total_sessions,
        "total_reports": total_reports,
        "total_profiles": total_profiles,
        "user_count": user_count,
        "message_types": {r["message_type"]: r["cnt"] for r in message_types},
    }


def get_trend_7days() -> list[dict]:
    return query_all("""
        SELECT DATE(created_at) AS day,
               COUNT(*) AS chat_count,
               COUNT(DISTINCT session_id) AS session_count
        FROM chat_logs
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(created_at)
        ORDER BY day
    """)


def get_compliance_stats() -> dict:
    blocked_count = query_scalar(
        "SELECT COUNT(*) FROM chat_logs WHERE message_type IN ('blocked','transfer')"
    )
    triage_count = query_scalar(
        "SELECT COUNT(*) FROM chat_logs WHERE message_type = 'triage'"
    )
    total = query_scalar("SELECT COUNT(*) FROM chat_logs")

    by_type = query_all(
        """SELECT message_type, COUNT(*) AS cnt
           FROM chat_logs
           WHERE message_type IN ('blocked','transfer','triage')
           GROUP BY message_type"""
    )

    return {
        "blocked_count": blocked_count,
        "triage_count": triage_count,
        "total_count": total,
        "block_rate": round(blocked_count / total * 100, 2) if total else 0,
        "by_type": {r["message_type"]: r["cnt"] for r in by_type},
    }


def get_session_analytics() -> dict:
    session_count = query_scalar("SELECT COUNT(*) FROM sessions")
    sessions_with_chat = query_scalar(
        "SELECT COUNT(DISTINCT session_id) FROM chat_logs"
    )

    depth_dist = query_all("""
        SELECT
            CASE
                WHEN cnt BETWEEN 1 AND 5 THEN '1-5条'
                WHEN cnt BETWEEN 6 AND 10 THEN '6-10条'
                WHEN cnt BETWEEN 11 AND 20 THEN '11-20条'
                ELSE '20+条'
            END AS depth_range,
            COUNT(*) AS session_count
        FROM (SELECT session_id, COUNT(*) AS cnt FROM chat_logs GROUP BY session_id) AS depths
        GROUP BY depth_range
        ORDER BY MIN(cnt)
    """)

    hourly = query_all("""
        SELECT HOUR(created_at) AS hour, COUNT(DISTINCT session_id) AS cnt
        FROM chat_logs
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        GROUP BY HOUR(created_at)
        ORDER BY hour
    """)

    anon_sessions = query_scalar(
        "SELECT COUNT(*) FROM sessions WHERE user_id IS NULL"
    )
    auth_sessions = query_scalar(
        "SELECT COUNT(*) FROM sessions WHERE user_id IS NOT NULL"
    )

    return {
        "total_sessions": session_count,
        "sessions_with_chat": sessions_with_chat,
        "anonymous_sessions": anon_sessions,
        "authenticated_sessions": auth_sessions,
        "depth_distribution": {r["depth_range"]: r["session_count"] for r in depth_dist},
        "hourly_distribution_24h": {r["hour"]: r["cnt"] for r in hourly},
    }


def get_qos_metrics() -> dict:
    report_types = query_all(
        "SELECT report_type, COUNT(*) AS cnt FROM report_records GROUP BY report_type ORDER BY cnt DESC"
    )

    recent_error_count = query_scalar(
        "SELECT COUNT(*) FROM chat_logs WHERE message_type = 'blocked' AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
    )

    return {
        "report_types": {r["report_type"]: r["cnt"] for r in report_types},
        "recent_24h_blocks": recent_error_count,
    }


def get_knowledge_status() -> dict:
    count = query_scalar("SELECT COUNT(*) FROM knowledge_base")
    latest = query_one(
        "SELECT updated_at FROM knowledge_base ORDER BY updated_at DESC LIMIT 1"
    )
    return {
        "entry_count": count,
        "last_updated": str(latest["updated_at"]) if latest else None,
    }
