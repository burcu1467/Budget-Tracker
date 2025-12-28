from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
import sqlite3
import uuid
from datetime import timedelta

from database import get_db
from dependencies import get_language, get_msg, get_hash, create_access_token, pwd_context, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from schemas import UserAuth, RecoveryUpdateIn, PasswordChangeIn

router = APIRouter(tags=["Auth"])

def normalize_username(username: str) -> str:
    return "".join(c for c in username if c.isalnum()).lower()

@router.post("/register")
def register(user: UserAuth, lang: str = Depends(get_language), conn: sqlite3.Connection = Depends(get_db)):
    username_key = normalize_username(user.username)
    if not username_key:
        raise HTTPException(status_code=400, detail=get_msg("invalid_username", lang))
    
    if not user.recovery_key:
        raise HTTPException(status_code=400, detail=get_msg("recovery_key_required", lang))
    
    c = conn.cursor()
    
    pw_hash = get_hash(user.password)
    rc_hash = get_hash(user.recovery_key)
    
    try:
        c.execute("INSERT INTO users (username, password_hash, recovery_key_hash) VALUES (?, ?, ?)", (username_key, pw_hash, rc_hash))
        conn.commit()
        return {"ok": True, "message": get_msg("registration_success", lang)}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail=get_msg("username_taken", lang))

@router.post("/login")
def login(user: UserAuth, lang: str = Depends(get_language), conn: sqlite3.Connection = Depends(get_db)):
    username_key = normalize_username(user.username)
    if not username_key:
        raise HTTPException(status_code=400, detail=get_msg("invalid_username_format", lang))
    
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username_key,))
    row = c.fetchone()
    
    if not row or not pwd_context.verify(user.password, row['password_hash']):
        raise HTTPException(status_code=400, detail=get_msg("invalid_credentials", lang))
    
    access_token = create_access_token(data={"sub": username_key}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer", "username": username_key}

@router.post("/reset-password")
def reset_password(user: UserAuth, lang: str = Depends(get_language), conn: sqlite3.Connection = Depends(get_db)):
    username_key = normalize_username(user.username)
    c = conn.cursor()
    c.execute("SELECT recovery_key_hash FROM users WHERE username = ?", (username_key,))
    row = c.fetchone()
    
    if not row or not pwd_context.verify(user.recovery_key, row['recovery_key_hash']):
        raise HTTPException(status_code=400, detail=get_msg("recovery_key_invalid", lang))
    
    new_pw_hash = get_hash(user.password)
    c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_pw_hash, username_key))
    conn.commit()
    return {"ok": True, "message": get_msg("password_reset_success", lang)}

@router.post("/update-recovery-key")
def update_recovery_key(data: RecoveryUpdateIn, lang: str = Depends(get_language), conn: sqlite3.Connection = Depends(get_db)):
    username_key = normalize_username(data.username)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username_key,))
    row = c.fetchone()
    
    if not row or not pwd_context.verify(data.password, row['password_hash']):
        raise HTTPException(status_code=400, detail=get_msg("current_password_invalid", lang))
        
    rc_hash = get_hash(data.new_recovery_key)
    c.execute("UPDATE users SET recovery_key_hash = ? WHERE username = ?", (rc_hash, username_key))
    conn.commit()
    return {"ok": True, "message": get_msg("recovery_key_updated", lang)}

@router.post("/change-password")
def change_password(data: PasswordChangeIn, lang: str = Depends(get_language), conn: sqlite3.Connection = Depends(get_db)):
    username_key = normalize_username(data.username)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username_key,))
    row = c.fetchone()
    
    if not row or not pwd_context.verify(data.old_password, row['password_hash']):
        raise HTTPException(status_code=400, detail=get_msg("current_password_invalid", lang))
        
    new_pw_hash = get_hash(data.new_password)
    c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_pw_hash, username_key))
    conn.commit()
    return {"ok": True, "message": get_msg("password_change_success", lang)}

@router.get("/verify-email")
def verify_email(token: str, conn: sqlite3.Connection = Depends(get_db)):
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE verification_token = ?", (token,))
    row = c.fetchone()
    if not row: return HTMLResponse(content="<h1>Geçersiz link</h1>", status_code=400)
    c.execute("UPDATE users SET is_verified = 1, verification_token = NULL WHERE username = ?", (row['username'],))
    conn.commit()
    return HTMLResponse(content="<h1>✅ E-posta doğrulandı!</h1>")

@router.post("/resend-verification")
def resend_verification(request: Request, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    new_token = str(uuid.uuid4())
    conn.execute("UPDATE users SET verification_token = ? WHERE username = ?", (new_token, current_user['username'])).commit()
    print(f"\n📧 [SİMÜLASYON] Link: {request.base_url}api/verify-email?token={new_token}\n")
    return {"ok": True, "message": "Link konsola yazıldı"}