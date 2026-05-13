import os
import hashlib
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    with engine.connect() as conn:

        # Users table
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'worker',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        # Facebook pages table
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS fb_pages (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            page_id TEXT NOT NULL,
            access_token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        # User page access
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_page_access (
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            page_id INTEGER REFERENCES fb_pages(id) ON DELETE CASCADE,
            PRIMARY KEY(user_id, page_id)
        )
        """))

        # Posts table
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            post_id TEXT,
            caption TEXT,
            image_url TEXT,
            post_time TEXT,
            page_id INTEGER REFERENCES fb_pages(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        # Default admin
        admin_pass = hash_password(
            os.getenv("ADMIN_PASSWORD", "admin123")
        )

        conn.execute(text("""
        INSERT INTO users
        (username, password_hash, role)
        VALUES
        (:username, :password_hash, :role)
        ON CONFLICT (username) DO NOTHING
        """), {
            "username": "admin",
            "password_hash": admin_pass,
            "role": "admin"
        })

        conn.commit()

    print("✅ PostgreSQL Database initialized")
