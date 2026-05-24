from database.connection import get_connection


def save_report_record(
    session_id,
    report_type,
    report_description,
    structured_data,
    interpretation_result,
    image_hash=None,
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO report_records
               (session_id, report_type, report_description, structured_data, interpretation_result, image_hash)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (session_id, report_type, report_description, structured_data, interpretation_result, image_hash),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def get_report_records(session_id, limit=20):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, session_id, report_type, report_description, structured_data, interpretation_result, created_at
               FROM report_records
               WHERE session_id = %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (session_id, limit),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def get_recent_report(session_id):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, session_id, report_type, report_description, structured_data, interpretation_result, created_at
               FROM report_records
               WHERE session_id = %s
               ORDER BY created_at DESC
               LIMIT 1""",
            (session_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
