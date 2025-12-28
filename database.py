import os
import sqlite3
import uuid
from datetime import datetime
from urllib.parse import unquote
from config import settings

# Ayarları config dosyasından al
DATA_DIR = settings.DATA_DIR
UPLOAD_DIR = settings.UPLOAD_DIR
DB_FILE = settings.DB_PATH


if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def _ensure_columns(cursor, table_name, new_columns):
    """Tabloda eksik sütunları kontrol eder ve ekler."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {col[1] for col in cursor.fetchall()}
    
    for col_name, col_def in new_columns.items():
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")
    
    # Tabloları oluştur
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, recovery_key_hash TEXT, email TEXT, is_verified INTEGER DEFAULT 0, verification_token TEXT)''')
    
    # Migrations (Sütun kontrolleri)
    _ensure_columns(c, "users", {
        "recovery_key_hash": "TEXT",
        "email": "TEXT",
        "is_verified": "INTEGER DEFAULT 0",
        "verification_token": "TEXT"
    })

    c.execute('''CREATE TABLE IF NOT EXISTS harcamalar (id TEXT PRIMARY KEY, username TEXT, aciklama TEXT, tutar REAL, kategori TEXT, tarih TEXT, fis_dosyasi TEXT)''')
    
    _ensure_columns(c, "harcamalar", {
        "fis_dosyasi": "TEXT"
    })

    c.execute('''CREATE TABLE IF NOT EXISTS gelirler (id TEXT PRIMARY KEY, username TEXT, aciklama TEXT, tutar REAL, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS butce (username TEXT PRIMARY KEY, tutar REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tekrarlayan (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, aciklama TEXT, tutar REAL, kategori TEXT, gun INTEGER, aktif BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS kumbara_ayarlar (username TEXT PRIMARY KEY, bakiye REAL DEFAULT 0, mod TEXT, gunluk_tutar REAL, haftalik_tutar REAL, son_tarih TEXT)''')
    
    _ensure_columns(c, "kumbara_ayarlar", {
        "hedef_tutar": "REAL DEFAULT 0",
        "hedef_aciklama": "TEXT"
    })

    c.execute('''CREATE TABLE IF NOT EXISTS kumbara_islemleri (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, tarih TEXT, tutar REAL, tur TEXT, aciklama TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS kategori_butce (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, kategori TEXT, limit_tutar REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS custom_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_badges (username TEXT, badge_code TEXT, earned_at TEXT, PRIMARY KEY (username, badge_code))''')
    conn.commit()
    conn.close()

def sync_user_data(username: str, conn: sqlite3.Connection):
    username = unquote(username).lower()
    c = conn.cursor()
    
    # Tekrarlayan
    c.execute("SELECT * FROM tekrarlayan WHERE username = ? AND aktif = 1", (username,))
    tekrarlayan = c.fetchall()
    bugun = datetime.now()
    gun = bugun.day
    bugune_git = bugun.strftime("%d.%m.%Y")
    
    for t in tekrarlayan:
        if t['gun'] == gun:
            c.execute("SELECT 1 FROM harcamalar WHERE username=? AND tarih=? AND aciklama=?", (username, bugune_git, t['aciklama']))
            if not c.fetchone():
                new_id = str(uuid.uuid4())
                c.execute("INSERT INTO harcamalar (id, username, aciklama, tutar, kategori, tarih) VALUES (?, ?, ?, ?, ?, ?)", (new_id, username, t['aciklama'], t['tutar'], t['kategori'], bugune_git))

    # Kumbara
    c.execute("SELECT * FROM kumbara_ayarlar WHERE username = ?", (username,))
    ayar = c.fetchone()
    if ayar and ayar['mod']:
        son_tarih_str = ayar['son_tarih']
        son_tarih = datetime.strptime(son_tarih_str, "%d.%m.%Y") if son_tarih_str else None
        tutar_ekle = 0
        if ayar['mod'] == "gunluk":
            diff = (bugun - son_tarih).days if son_tarih else 1
            if diff > 0: tutar_ekle = ayar['gunluk_tutar'] * diff
        elif ayar['mod'] == "haftalik":
            diff = (bugun - son_tarih).days // 7 if son_tarih else 1
            if diff > 0: tutar_ekle = ayar['haftalik_tutar'] * diff
            
        if tutar_ekle > 0:
            new_bakiye = ayar['bakiye'] + tutar_ekle
            bugun_str = bugun.strftime("%d.%m.%Y")
            c.execute("UPDATE kumbara_ayarlar SET bakiye = ?, son_tarih = ? WHERE username = ?", (new_bakiye, bugun_str, username))
            c.execute("INSERT INTO kumbara_islemleri (username, tarih, tutar, tur, aciklama) VALUES (?, ?, ?, ?, ?)", (username, bugun_str, tutar_ekle, "ekleme", "Otomatik"))
    conn.commit()