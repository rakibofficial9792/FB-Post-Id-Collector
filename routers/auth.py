from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import sqlite3

from database import get_db, hash_password
from auth_utils import create_token

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, db=Depends(get_db)):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Username এবং Password দাও")

    pw_hash = hash_password(body.password)
    cur = db.cursor()
    cur.execute(
        "SELECT id, username, role, is_active FROM users WHERE username=? AND password_hash=?",
        (body.username.strip(), pw_hash)
    )
    user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Username বা Password ভুল")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account নিষ্ক্রিয় করা হয়েছে")

    token = create_token({"sub": user["username"], "role": user["role"]})

    return {
        "token":    token,
        "username": user["username"],
        "role":     user["role"],
    }
