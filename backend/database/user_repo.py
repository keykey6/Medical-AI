"""users 表 + session_user 表操作"""

from database.connection import get_connection


def create_user(user_id: str, username: str, password_hash: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (user_id, username, password_hash)
               VALUES (%s, %s, %s)""",
            (user_id, username, password_hash),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        cursor.close()
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def bind_session_to_user(session_id: str, user_id: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO session_user (session_id, user_id, is_anonymous)
               VALUES (%s, %s, FALSE)
               ON DUPLICATE KEY UPDATE user_id = VALUES(user_id),
                                       is_anonymous = FALSE""",
            (session_id, user_id),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        cursor.close()
        conn.close()


def mark_session_anonymous(session_id: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO session_user (session_id, user_id, is_anonymous)
               VALUES (%s, NULL, TRUE)
               ON DUPLICATE KEY UPDATE is_anonymous = TRUE""",
            (session_id,),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        cursor.close()
        conn.close()


def get_session_user(session_id: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT su.session_id, su.user_id, su.is_anonymous,
                      u.username
               FROM session_user su
               LEFT JOIN users u ON su.user_id = u.user_id
               WHERE su.session_id = %s""",
            (session_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
