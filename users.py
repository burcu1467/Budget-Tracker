"""
Kullanıcı profili işlemlerini yöneten API modülü.
"""
from fastapi import APIRouter, Depends
import sqlite3
from database import get_db
from dependencies import get_current_user
from schemas import ProfileIn

router = APIRouter()

@router.get("/profile")
def get_profile(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    c = conn.cursor()
    c.execute("SELECT email, is_verified FROM users WHERE username = ?", (current_user['username'],))
    row = c.fetchone()
    return {"email": row['email'] if row else "", "is_verified": row['is_verified'] if row else False}

@router.post("/profile")
def update_profile(p: ProfileIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if row and row['email'] != p.email:
        c.execute("UPDATE users SET email = ?, is_verified = 0, verification_token = NULL WHERE username = ?", (p.email, username))
        conn.commit()
    return {"ok": True}