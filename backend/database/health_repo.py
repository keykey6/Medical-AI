from database.connection import get_connection


def save_health_profile(
    session_id,
    user_id=None,
    name=None,
    gender=None,
    age=None,
    height=None,
    weight=None,
    allergies=None,
    diseases=None,
    medications=None,
    lifestyle=None,
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Ensure session exists to satisfy FK
        cursor.execute(
            """INSERT INTO sessions (session_id) VALUES (%s)
               ON DUPLICATE KEY UPDATE last_active = CURRENT_TIMESTAMP""",
            (session_id,),
        )
        existing = get_health_profile(session_id) if not user_id else get_health_profile_by_user(user_id)
        if not existing and not user_id:
            existing = get_health_profile(session_id)

        if existing:
            cursor.execute(
                """UPDATE health_profiles SET user_id=%s, name=%s, gender=%s, age=%s,
                   height=%s, weight=%s, allergies=%s, diseases=%s, medications=%s, lifestyle=%s
                   WHERE id=%s""",
                (user_id, name, gender, age, height, weight, allergies, diseases, medications, lifestyle, existing["id"]),
            )
        else:
            cursor.execute(
                """INSERT INTO health_profiles
                   (session_id, user_id, name, gender, age, height, weight, allergies, diseases, medications, lifestyle)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (session_id, user_id, name, gender, age, height, weight, allergies, diseases, medications, lifestyle),
            )
        conn.commit()
        return True
    finally:
        cursor.close()
        conn.close()


def get_health_profile(session_id):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM health_profiles WHERE session_id = %s ORDER BY id DESC LIMIT 1",
            (session_id,),
        )
        result = cursor.fetchone()
        if result:
            result["created_at"] = str(result.get("created_at", ""))
            result["updated_at"] = str(result.get("updated_at", ""))
        return result
    finally:
        cursor.close()
        conn.close()


def get_health_profile_by_user(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM health_profiles WHERE user_id = %s ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        result = cursor.fetchone()
        if result:
            result["created_at"] = str(result.get("created_at", ""))
            result["updated_at"] = str(result.get("updated_at", ""))
        return result
    finally:
        cursor.close()
        conn.close()
