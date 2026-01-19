import sqlite3
from pathlib import Path

DB_PATH = Path("app.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # пользователи
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            first_name TEXT NOT NULL,
            last_name TEXT,
            middle_name TEXT,
            age INTEGER,
            about TEXT,
            drinks TEXT,
            topics TEXT,
            location TEXT,
            balance REAL DEFAULT 0,
            is_subscribed INTEGER DEFAULT 0
        );
        """
    )

    # приглашения
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_tg_id INTEGER NOT NULL,
            to_tg_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # сообщения
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_tg_id INTEGER NOT NULL,
            to_tg_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conn.commit()
    conn.close()