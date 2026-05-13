from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3

from database import get_db, hash_password
from auth_utils import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Models ────────────────────────────────────────────────
class CreateUser(BaseModel):
    username: str
    password: str
    role: str = "user"

class UpdateUser(BaseModel):
    password: Optional[str] = None
    is_active: Optional[int] = None
    role: Optional[str] = None

class CreatePage(BaseModel):
    name: str
    page_id: str
    access_token: str

class AssignPage(BaseModel):
    user_id: int
    page_id: int


# ── Users ─────────────────────────────────────────────────
@router.get("/users")
async def list_users(db=Depends(get_db), _=Depends(require_admin)):
    cur = db.cursor()
    cur.execute("SELECT id, username, role, is_active, created_at FROM users ORDER BY id")
    return {"users": [dict(r) for r in cur.fetchall()]}


@router.post("/users")
async def create_user(body: CreateUser, db=Depends(get_db), _=Depends(require_admin)):
    if not body.username or not body.password:
        raise HTTPException(400, "Username এবং Password দাও")
    if body.role not in ("admin", "user"):
        raise HTTPException(400, "Role হবে 'admin' বা 'user'")
    try:
        cur = db.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (body.username.strip(), hash_password(body.password), body.role)
        )
        db.commit()
        return {"message": f"User '{body.username}' তৈরি হয়েছে", "id": cur.lastrowid}
    except sqlite3.IntegrityError:
        raise HTTPException(409, "এই username আগে থেকেই আছে")


@router.patch("/users/{user_id}")
async def update_user(user_id: int, body: UpdateUser, db=Depends(get_db), _=Depends(require_admin)):
    cur = db.cursor()
    if body.password:
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(body.password), user_id))
    if body.is_active is not None:
        cur.execute("UPDATE users SET is_active=? WHERE id=?", (body.is_active, user_id))
    if body.role:
        cur.execute("UPDATE users SET role=? WHERE id=?", (body.role, user_id))
    db.commit()
    return {"message": "User আপডেট হয়েছে"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db=Depends(get_db), _=Depends(require_admin)):
    cur = db.cursor()
    cur.execute("DELETE FROM user_page_access WHERE user_id=?", (user_id,))
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    return {"message": "User ডিলিট হয়েছে"}


# ── Pages ─────────────────────────────────────────────────
@router.get("/pages")
async def list_pages(db=Depends(get_db), _=Depends(require_admin)):
    cur = db.cursor()
    cur.execute("SELECT id, name, page_id, is_active, created_at FROM fb_pages ORDER BY id")
    return {"pages": [dict(r) for r in cur.fetchall()]}


@router.post("/pages")
async def create_page(body: CreatePage, db=Depends(get_db), _=Depends(require_admin)):
    cur = db.cursor()
    cur.execute(
        "INSERT INTO fb_pages (name, page_id, access_token) VALUES (?,?,?)",
        (body.name, body.page_id, body.access_token)
    )
    db.commit()
    return {"message": f"Page '{body.name}' যোগ হয়েছে", "id": cur.lastrowid}


@router.delete("/pages/{page_id}")
async def delete_page(page_id: int, db=Depends(get_db), _=Depends(require_admin)):
    cur = db.cursor()
    cur.execute("DELETE FROM user_page_access WHERE page_id=?", (page_id,))
    cur.execute("DELETE FROM fb_pages WHERE id=?", (page_id,))
    db.commit()
    return {"message": "Page ডিলিট হয়েছে"}


# ── Assign Page to User ───────────────────────────────────
@router.post("/assign")
async def assign_page(body: AssignPage, db=Depends(get_db), _=Depends(require_admin)):
    try:
        cur = db.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO user_page_access (user_id, page_id) VALUES (?,?)",
            (body.user_id, body.page_id)
        )
        db.commit()
        return {"message": "Page access দেওয়া হয়েছে"}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/assign")
async def remove_page_access(body: AssignPage, db=Depends(get_db), _=Depends(require_admin)):
    cur = db.cursor()
    cur.execute(
        "DELETE FROM user_page_access WHERE user_id=? AND page_id=?",
        (body.user_id, body.page_id)
    )
    db.commit()
    return {"message": "Page access সরানো হয়েছে"}
