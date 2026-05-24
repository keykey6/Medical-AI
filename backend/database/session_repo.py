from database.connection import get_connection


def save_session(session_id, user_id=None, user_info=None, title=None):
    """创建或续期会话。登录用户绑定 user_id，游客为 NULL。"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO sessions (session_id, user_id, title, user_info)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   last_active = CURRENT_TIMESTAMP,
                   user_id = COALESCE(VALUES(user_id), user_id),
                   title = COALESCE(VALUES(title), title)""",
            (session_id, user_id, title, user_info),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_session(session_id, user_id=None):
    """获取会话。若传入 user_id 则校验归属。"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if user_id:
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
        else:
            cursor.execute("SELECT * FROM sessions WHERE session_id = %s", (session_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def list_user_sessions(user_id):
    """列出用户的所有会话，含消息数和最后消息预览。"""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.session_id, s.title, s.created_at, s.last_active,
                   COUNT(c.id) AS msg_count,
                   (SELECT c2.user_message FROM chat_logs c2
                    WHERE c2.session_id = s.session_id
                    ORDER BY c2.created_at DESC LIMIT 1) AS last_message
            FROM sessions s
            LEFT JOIN chat_logs c ON c.session_id = s.session_id
            WHERE s.user_id = %s
            GROUP BY s.session_id
            ORDER BY s.last_active DESC
        """, (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def delete_session(session_id, user_id=None):
    """删除会话。若传入 user_id 则校验归属。"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "DELETE FROM sessions WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
        else:
            cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()


def rename_session(session_id, user_id, title):
    """重命名会话（仅所有者）。"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET title = %s WHERE session_id = %s AND user_id = %s",
            (title, session_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()


def get_all_sessions():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT session_id, created_at, last_active FROM sessions ORDER BY created_at DESC"
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def delete_all_sessions():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sessions")
        count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM sessions")
        conn.commit()
        return count
    finally:
        cursor.close()
        conn.close()


def update_session_active(session_id):
    """仅更新 last_active 时间戳。"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE session_id = %s",
            (session_id,),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
