import sqlite3
import hashlib
import os
from pathlib import Path

DB_PATH = "data/app.db"


def get_db():
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # FB Pages table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fb_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            page_id TEXT NOT NULL,
            access_token TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # User ↔ Page access table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_page_access (
            user_id INTEGER NOT NULL,
            page_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, page_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (page_id) REFERENCES fb_pages(id)
        )
    """)

    # Create default admin if not exists
    admin_pass = hash_password(os.getenv("ADMIN_PASSWORD", "admin123"))
    cur.execute("""
        INSERT OR IGNORE INTO users (username, password_hash, role)
        VALUES (?, ?, 'admin')
    """, ("admin", admin_pass))

    conn.commit()
    conn.close()
    print("✅ Database initialized")
