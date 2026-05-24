from database.connection import get_connection


def add_knowledge_item(title, content, source_url=None, category=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT IGNORE INTO knowledge_base (title, content, source_url, category)
               VALUES (%s, %s, %s, %s)""",
            (title, content, source_url, category),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def get_knowledge_items(category=None, limit=100):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if category:
            cursor.execute(
                """SELECT * FROM knowledge_base
                   WHERE category = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (category, limit),
            )
        else:
            cursor.execute(
                """SELECT * FROM knowledge_base
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (limit,),
            )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
