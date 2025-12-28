import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Settings:
    BASE_DIR = BASE_DIR
    DATA_DIR = os.path.join(BASE_DIR, "data")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    
    # Database
    DB_PATH = os.getenv("DB_PATH", os.path.join(DATA_DIR, "butce.db"))
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "cok-gizli-ve-guvenli-bir-anahtar-buraya-yazilmali")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))
    
    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

settings = Settings()