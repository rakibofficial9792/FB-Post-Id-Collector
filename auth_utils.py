import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3

from database import get_db, DB_PATH

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-use-random-32-chars")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")


def require_admin(current_user=Depends(verify_token)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def get_user_pages(username: str) -> list:
    """Get pages this user has access to"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Admin gets all pages
    cur.execute("SELECT role FROM users WHERE username=?", (username,))
    user = cur.fetchone()

    if user and user["role"] == "admin":
        cur.execute("SELECT * FROM fb_pages WHERE is_active=1")
    else:
        cur.execute("""
            SELECT fp.* FROM fb_pages fp
            JOIN user_page_access upa ON fp.id = upa.page_id
            JOIN users u ON u.id = upa.user_id
            WHERE u.username=? AND fp.is_active=1
        """, (username,))

    pages = [dict(row) for row in cur.fetchall()]
    conn.close()
    return pages
