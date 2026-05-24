import logging

import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

from config import settings

logger = logging.getLogger("app.db")

_pool: MySQLConnectionPool | None = None


def get_pool() -> MySQLConnectionPool:
    global _pool
    if _pool is None:
        try:
            _pool = MySQLConnectionPool(
                pool_name=settings.DB_POOL_NAME,
                pool_size=settings.DB_POOL_SIZE,
                host=settings.MYSQL_HOST,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                port=settings.MYSQL_PORT,
                charset="utf8mb4",
            )
        except Error as e:
            raise RuntimeError(f"数据库连接池初始化失败: {e}")
    return _pool


def get_connection():
    try:
        return get_pool().get_connection()
    except Error as e:
        raise RuntimeError(f"获取数据库连接失败: {e}")


def init_database():
    try:
        connection = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            port=settings.MYSQL_PORT,
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DATABASE}"
            )
            cursor.execute(f"USE {settings.MYSQL_DATABASE}")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NULL,
                    title VARCHAR(200) NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_info TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    source_url VARCHAR(500),
                    category VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_title_source (title, source_url)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(64) NOT NULL,
                    user_message TEXT,
                    ai_response TEXT,
                    message_type VARCHAR(20) DEFAULT 'normal',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(64) NOT NULL,
                    report_type VARCHAR(100),
                    report_description TEXT,
                    structured_data TEXT,
                    interpretation_result TEXT,
                    image_hash VARCHAR(64),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(64) NULL,
                    name VARCHAR(100),
                    gender VARCHAR(10),
                    age INT,
                    height DECIMAL(5,2),
                    weight DECIMAL(5,2),
                    allergies TEXT,
                    diseases TEXT,
                    medications TEXT,
                    lifestyle TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(64) PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_user (
                    session_id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(64) NULL,
                    is_anonymous BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Ensure unique key for knowledge_base (compatible with existing tables)
            try:
                cursor.execute(
                    "ALTER TABLE knowledge_base ADD UNIQUE KEY uk_title_source (title, source_url)"
                )
            except Exception:
                pass

            # Migration: add user_id to health_profiles if missing
            try:
                cursor.execute(
                    "ALTER TABLE health_profiles ADD COLUMN user_id VARCHAR(64) NULL"
                )
            except Exception:
                pass

            # Migration: add user_id/title to sessions if missing
            for col, col_def in [("user_id", "VARCHAR(64) NULL"), ("title", "VARCHAR(200) NULL")]:
                try:
                    cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_def}")
                except Exception:
                    pass

            connection.commit()
            cursor.close()
            connection.close()
            logger.info("数据库初始化成功")
    except Error as e:
        logger.error("数据库初始化失败: %s", e)
