from database.connection import get_connection


def save_chat_log(session_id, user_message, ai_response, message_type="normal"):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO chat_logs (session_id, user_message, ai_response, message_type)
               VALUES (%s, %s, %s, %s)""",
            (session_id, user_message, ai_response, message_type),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_chat_history(session_id, limit=20):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT user_message, ai_response, created_at
               FROM chat_logs
               WHERE session_id = %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (session_id, limit),
        )
        results = cursor.fetchall()
        return list(reversed(results))
    finally:
        cursor.close()
        conn.close()
