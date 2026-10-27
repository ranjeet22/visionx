"""
VisionX Database Module
Manages MySQL connection pooling, transactions, and schema initialization.
"""

import logging
from contextlib import contextmanager
from typing import Generator
import pymysql
from pymysql.cursors import DictCursor

from backend import config

logger = logging.getLogger("visionx.database")


def get_raw_connection(include_database: bool = True) -> pymysql.connections.Connection:
    """Creates a raw MySQL connection using current configuration."""
    kwargs = {
        "host": config.MYSQL_HOST,
        "port": config.MYSQL_PORT,
        "user": config.MYSQL_USER,
        "password": config.MYSQL_PASSWORD,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
        "connect_timeout": 5,
    }
    if include_database:
        kwargs["database"] = config.MYSQL_DATABASE

    return pymysql.connect(**kwargs)


@contextmanager
def get_db_connection() -> Generator[pymysql.connections.Connection, None, None]:
    """
    Context manager providing a transactional MySQL connection.
    Automatically commits on normal exit and rolls back on exception.
    """
    conn = get_raw_connection(include_database=True)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()


def check_database_health() -> dict:
    """Verifies that the MySQL server and database are reachable."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS healthy;")
                row = cur.fetchone()
                return {
                    "connected": True,
                    "database": config.MYSQL_DATABASE,
                    "host": config.MYSQL_HOST,
                    "status": "ready" if row and row.get("healthy") == 1 else "unknown"
                }
    except Exception as e:
        logger.warning(f"MySQL health check failed: {e}")
        return {
            "connected": False,
            "database": config.MYSQL_DATABASE,
            "host": config.MYSQL_HOST,
            "error": str(e)
        }


def init_db():
    """
    Idempotent schema initialization:
    1. Connects to MySQL server (without database selected) to create the database if needed.
    2. Connects to the database to create all required tables and indexes.
    """
    try:
        # Step 1: Ensure database exists
        server_conn = get_raw_connection(include_database=False)
        with server_conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        server_conn.commit()
        server_conn.close()

        # Step 2: Ensure tables exist
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Users Table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_login_at DATETIME NULL,
                    INDEX idx_user_id (user_id),
                    INDEX idx_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)

                # Email OTP Verifications Table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS email_verifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    otp_hash VARCHAR(255) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    attempts INT NOT NULL DEFAULT 0,
                    resend_cooldown_until DATETIME NOT NULL,
                    is_used BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_expires_at (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)

                # User Sessions Table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(128) PRIMARY KEY,
                    user_id INT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    last_activity_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_expires_at (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)

        logger.info(f"MySQL schema initialized successfully on database '{config.MYSQL_DATABASE}'.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise
