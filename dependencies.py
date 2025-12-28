import os
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings

# --- Dil ve Mesajlar ---
MESSAGES = {
    "tr": {
        "invalid_username": "Geçersiz kullanıcı adı",
        "recovery_key_required": "Kurtarma anahtarı zorunludur",
        "username_taken": "Bu kullanıcı adı zaten alınmış",
        "registration_success": "Kayıt başarılı",
        "server_error": "Sunucu hatası: {}",
        "invalid_username_format": "Geçersiz kullanıcı adı formatı",
        "invalid_credentials": "Kullanıcı adı veya şifre hatalı",
        "session_expired": "Oturum süresi doldu veya geçersiz",
        "recovery_key_not_found": "Bu kullanıcı için kurtarma anahtarı bulunamadı",
        "recovery_key_invalid": "Kurtarma anahtarı hatalı",
        "password_reset_success": "Şifre başarıyla sıfırlandı",
        "user_not_found": "Kullanıcı bulunamadı",
        "current_password_invalid": "Mevcut şifre hatalı",
        "recovery_key_updated": "Kurtarma anahtarı güncellendi",
        "password_change_success": "Şifre başarıyla değiştirildi",
        "expense_not_found": "Harcama bulunamadı",
        "income_not_found": "Gelir bulunamadı",
        "email_required": "Önce profilinizden bir e-posta adresi kaydedin.",
        "already_verified": "Zaten doğrulanmış.",
        "verification_sent": "Doğrulama bağlantısı sunucu konsoluna yazdırıldı (Simülasyon).",
        "insufficient_balance": "Yetersiz bakiye"
    },
    "en": {
        "invalid_username": "Invalid username",
        "recovery_key_required": "Recovery key is required",
        "username_taken": "Username already taken",
        "registration_success": "Registration successful",
        "server_error": "Server error: {}",
        "invalid_username_format": "Invalid username format",
        "invalid_credentials": "Invalid username or password",
        "session_expired": "Session expired or invalid",
        "recovery_key_not_found": "Recovery key not found for this user",
        "recovery_key_invalid": "Invalid recovery key",
        "password_reset_success": "Password reset successfully",
        "user_not_found": "User not found",
        "current_password_invalid": "Invalid current password",
        "recovery_key_updated": "Recovery key updated",
        "password_change_success": "Password changed successfully",
        "expense_not_found": "Expense not found",
        "income_not_found": "Income not found",
        "email_required": "Please save an email address in your profile first.",
        "already_verified": "Already verified.",
        "verification_sent": "Verification link printed to server console (Simulation).",
        "insufficient_balance": "Insufficient balance"
    }
}

def get_language(accept_language: str = Header(default="tr", alias="Accept-Language")):
    if not accept_language:
        return "tr"
    lang = accept_language.split(",")[0].split("-")[0].lower()
    return lang if lang in MESSAGES else "tr"

def get_msg(key: str, lang: str = "tr", *args):
    msg = MESSAGES.get(lang, MESSAGES["tr"]).get(key, key)
    if args:
        return msg.format(*args)
    return msg

# --- Güvenlik ve Parola Yönetimi ---
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def get_hash(text: str) -> str:
    return pwd_context.hash(text)

# --- JWT Ayarları ---
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), lang: str = Depends(get_language)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=get_msg("session_expired", lang),
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return {"username": username, "lang": lang}