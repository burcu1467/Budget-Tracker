from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse, StreamingResponse
import logging
import sqlite3
import os
import uuid
import shutil
import calendar
from datetime import datetime
from io import BytesIO
from urllib.parse import unquote
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from PIL import Image, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from database import get_db, UPLOAD_DIR, sync_user_data
from dependencies import get_current_user, get_msg
from schemas import HarcamaIn, GelirIn, ButceIn, KategoriButceIn, CategoryIn, TekrarlayanIn, KumbaraAyarIn, KumbaraIslemIn
from utils import scan_receipt

# Logger yapılandırması
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Transactions"])

CATEGORIES = {
    "tr": ["Yemek", "Ulaşım", "Eğlence", "Alışveriş", "Sağlık", "Faturalar", "Diğer"],
    "en": ["Food", "Transportation", "Entertainment", "Shopping", "Health", "Bills", "Other"]
}

@router.get("/categories")
def get_categories(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    lang = current_user['lang']
    defaults = CATEGORIES.get(lang, CATEGORIES["tr"])
    c = conn.cursor()
    c.execute("SELECT name FROM custom_categories WHERE username = ?", (username,))
    customs = [row['name'] for row in c.fetchall()]
    combined = list(defaults)
    for cat in customs:
        if cat not in combined: combined.append(cat)
    return combined

@router.post("/categories")
def add_category(cat: CategoryIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT 1 FROM custom_categories WHERE username = ? AND name = ?", (username, cat.name))
    if c.fetchone(): raise HTTPException(status_code=400, detail="Kategori zaten mevcut")
    c.execute("INSERT INTO custom_categories (username, name) VALUES (?, ?)", (username, cat.name))
    conn.commit()
    return {"ok": True}

@router.put("/categories/{old_name}")
def update_category(old_name: str, cat: CategoryIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("UPDATE custom_categories SET name = ? WHERE username = ? AND name = ?", (cat.name, username, old_name))
    if c.rowcount == 0: raise HTTPException(status_code=404, detail="Kategori bulunamadı")
    conn.commit()
    return {"ok": True}

@router.delete("/categories/{name}")
def delete_category(name: str, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("DELETE FROM custom_categories WHERE username = ? AND name = ?", (username, name))
    if c.rowcount == 0: raise HTTPException(status_code=404, detail="Kategori bulunamadı")
    conn.commit()
    return {"ok": True}

@router.get("/harcamalar")
def list_harcamalar(kategori: str = None, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    if kategori: c.execute("SELECT * FROM harcamalar WHERE username = ? AND kategori = ? ORDER BY rowid", (username, kategori))
    else: c.execute("SELECT * FROM harcamalar WHERE username = ? ORDER BY rowid", (username,))
    return [dict(row) for row in c.fetchall()]

@router.post("/harcamalar")
def add_harcama(aciklama: str = Form(...), tutar: float = Form(...), kategori: str = Form(...), tarih: str = Form(None), fis_dosyasi: UploadFile = File(None), current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    logger.info(f"📝 Harcama Ekleme İsteği: {aciklama} - {tutar} TL")
    item_tarih = tarih if tarih and tarih.strip() else datetime.now().strftime("%d.%m.%Y")
    item_id = str(uuid.uuid4())
    file_path_to_db = None
    if fis_dosyasi:
        logger.info(f"📥 Dosya Yükleniyor: {fis_dosyasi.filename}")
        file_extension = os.path.splitext(fis_dosyasi.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_save_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        try:
            # Görseli aç, yönünü düzelt ve küçült
            img = Image.open(fis_dosyasi.file)
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            
            img.thumbnail((1024, 1024)) # En boy oranını koruyarak max 1024px yap
            img.save(file_save_path, quality=80, optimize=True)
            file_path_to_db = unique_filename
        except Exception as e:
            logger.error(f"Görsel küçültme hatası (Orijinal kaydediliyor): {e}")
            fis_dosyasi.file.seek(0)
            with open(file_save_path, "wb") as buffer: shutil.copyfileobj(fis_dosyasi.file, buffer)
            file_path_to_db = unique_filename
        fis_dosyasi.file.close()
    else:
        logger.warning("⚠️ Dosya Yok veya Alınamadı (fis_dosyasi parametresi boş)")
    c = conn.cursor()
    c.execute("INSERT INTO harcamalar (id, username, aciklama, tutar, kategori, tarih, fis_dosyasi) VALUES (?, ?, ?, ?, ?, ?, ?)", (item_id, username, aciklama, tutar, kategori, item_tarih, file_path_to_db))
    conn.commit()
    
    # Rozet Kontrolü: İlk Harcama
    c.execute("SELECT COUNT(*) as count FROM harcamalar WHERE username = ?", (username,))
    row_count = c.fetchone()
    if row_count and row_count['count'] == 1:
        try:
            c.execute("INSERT INTO user_badges (username, badge_code, earned_at) VALUES (?, ?, ?)", (username, 'FIRST_EXPENSE', item_tarih))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    # Rozet Kontrolü: Gece Kuşu (00:00 - 05:00 arası)
    now = datetime.now()
    if 0 <= now.hour < 5:
        try:
            c.execute("INSERT INTO user_badges (username, badge_code, earned_at) VALUES (?, ?, ?)", (username, 'NIGHT_OWL', now.strftime("%d.%m.%Y")))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    c.execute("SELECT * FROM harcamalar WHERE username = ? ORDER BY rowid", (username,))
    return [dict(row) for row in c.fetchall()]

@router.delete("/harcamalar/{identifier}")
def delete_harcama(identifier: str, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT id, fis_dosyasi FROM harcamalar WHERE id = ? AND username = ?", (identifier, username))
    row = c.fetchone()
    target_id, file_to_delete = None, None
    if row:
        target_id, file_to_delete = row['id'], row['fis_dosyasi']
    elif identifier.isdigit():
        c.execute("SELECT id, fis_dosyasi FROM harcamalar WHERE username = ? ORDER BY rowid", (username,))
        rows = c.fetchall()
        index = int(identifier)
        if 0 <= index < len(rows): target_id, file_to_delete = rows[index]['id'], rows[index]['fis_dosyasi']
    if target_id:
        c.execute("DELETE FROM harcamalar WHERE id = ?", (target_id,))
        conn.commit()
        if file_to_delete:
            try: os.remove(os.path.join(UPLOAD_DIR, file_to_delete))
            except OSError: pass
        return {"ok": True}
    raise HTTPException(status_code=404, detail=get_msg("expense_not_found", current_user['lang']))

@router.get("/gelirler")
def list_gelirler(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT * FROM gelirler WHERE username = ? ORDER BY rowid", (username,))
    return [dict(row) for row in c.fetchall()]

@router.post("/gelirler")
def add_gelir(g: GelirIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    item = g.dict()
    if not item.get("tarih"): item["tarih"] = datetime.now().strftime("%d.%m.%Y")
    item["id"] = str(uuid.uuid4())
    c = conn.cursor()
    c.execute("INSERT INTO gelirler (id, username, aciklama, tutar, tarih) VALUES (?, ?, ?, ?, ?)", (item["id"], username, item["aciklama"], item["tutar"], item["tarih"]))
    conn.commit()
    c.execute("SELECT * FROM gelirler WHERE username = ?", (username,))
    
    # Rozet Kontrolü: Gece Kuşu
    now = datetime.now()
    if 0 <= now.hour < 5:
        try:
            c.execute("INSERT INTO user_badges (username, badge_code, earned_at) VALUES (?, ?, ?)", (username, 'NIGHT_OWL', now.strftime("%d.%m.%Y")))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    return [dict(row) for row in c.fetchall()]

@router.delete("/gelirler/{identifier}")
def delete_gelir(identifier: str, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("DELETE FROM gelirler WHERE id = ? AND username = ?", (identifier, username))
    if c.rowcount > 0:
        conn.commit()
        return {"ok": True}
    if identifier.isdigit():
        c.execute("SELECT id FROM gelirler WHERE username = ? ORDER BY rowid", (username,))
        rows = c.fetchall()
        if 0 <= int(identifier) < len(rows):
            c.execute("DELETE FROM gelirler WHERE id = ?", (rows[int(identifier)]['id'],))
            conn.commit()
            return {"ok": True}
    raise HTTPException(status_code=404, detail=get_msg("income_not_found", current_user['lang']))

@router.get("/ozet")
def ozet(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    sync_user_data(username, conn)
    c = conn.cursor()
    c.execute("SELECT SUM(tutar) as total FROM harcamalar WHERE username = ?", (username,))
    res_gider = c.fetchone()
    toplam_gider = res_gider['total'] if res_gider and res_gider['total'] else 0
    c.execute("SELECT SUM(tutar) as total FROM gelirler WHERE username = ?", (username,))
    res_gelir = c.fetchone()
    toplam_gelir = res_gelir['total'] if res_gelir and res_gelir['total'] else 0
    c.execute("SELECT tutar FROM butce WHERE username = ?", (username,))
    res_butce = c.fetchone()
    butce_val = res_butce['tutar'] if res_butce else 0
    
    # Rozet Kontrolü: Tasarruf Ustası (Gelir > Gider)
    if toplam_gelir > 0 and toplam_gelir > toplam_gider:
        try:
            c.execute("INSERT INTO user_badges (username, badge_code, earned_at) VALUES (?, ?, ?)", (username, 'SAVINGS_MASTER', datetime.now().strftime("%d.%m.%Y")))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
    
    # Rozetleri Çek
    c.execute("SELECT badge_code FROM user_badges WHERE username = ?", (username,))
    badges = [row['badge_code'] for row in c.fetchall()]
    
    return {"toplam_gider": toplam_gider, "toplam_gelir": toplam_gelir, "net": toplam_gelir - toplam_gider, "butce": butce_val, "kalan_butce": butce_val - toplam_gider, "badges": badges}

@router.get("/uploads/{filename}")
async def get_upload(filename: str, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT 1 FROM harcamalar WHERE username = ? AND fis_dosyasi = ?", (username, filename))
    if not c.fetchone(): raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    file_path = os.path.join(UPLOAD_DIR, filename)
    print(f"📸 Dosya İsteği: {filename} -> {file_path} (Mevcut: {os.path.exists(file_path)})")
    if not os.path.isfile(file_path): raise HTTPException(status_code=404, detail="Dosya yok")
    return FileResponse(file_path)

@router.get("/butce")
def get_butce(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT tutar FROM butce WHERE username = ?", (username,))
    row = c.fetchone()
    return {"butce": row['tutar'] if row else 0}

@router.post("/butce")
def set_butce(b: ButceIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO butce (username, tutar) VALUES (?, ?)", (username, b.tutar))
    conn.commit()
    return {"ok": True, "butce": b.tutar}

@router.get("/butce/kategori")
def get_kategori_butce(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT kategori, limit_tutar FROM kategori_butce WHERE username = ?", (username,))
    return [dict(row) for row in c.fetchall()]

@router.post("/butce/kategori")
def set_kategori_butce(kb: KategoriButceIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("DELETE FROM kategori_butce WHERE username = ? AND kategori = ?", (username, kb.kategori))
    if kb.limit_tutar > 0:
        c.execute("INSERT INTO kategori_butce (username, kategori, limit_tutar) VALUES (?, ?, ?)", (username, kb.kategori, kb.limit_tutar))
    conn.commit()
    return {"ok": True}

@router.get("/tekrarlayan")
def list_tekrarlayan(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT * FROM tekrarlayan WHERE username = ? ORDER BY id", (username,))
    return [dict(row) for row in c.fetchall()]

@router.post("/tekrarlayan")
def add_tekrarlayan(t: TekrarlayanIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("INSERT INTO tekrarlayan (username, aciklama, tutar, kategori, gun, aktif) VALUES (?, ?, ?, ?, ?, ?)", (username, t.aciklama, t.tutar, t.kategori, t.gun, 1 if t.aktif else 0))
    conn.commit()
    return {"ok": True}

@router.delete("/tekrarlayan/{index}")
def delete_tekrarlayan(index: int, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT id FROM tekrarlayan WHERE username = ? ORDER BY id", (username,))
    rows = c.fetchall()
    if 0 <= index < len(rows):
        c.execute("DELETE FROM tekrarlayan WHERE id = ?", (rows[index]['id'],))
        conn.commit()
        return {"ok": True}
    raise HTTPException(status_code=404)

@router.get("/kumbara")
def get_kumbara(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT * FROM kumbara_ayarlar WHERE username = ?", (username,))
    ayar_row = c.fetchone()
    c.execute("SELECT * FROM kumbara_islemleri WHERE username = ?", (username,))
    islemler = [dict(row) for row in c.fetchall()]
    ayar = dict(ayar_row) if ayar_row else {"bakiye": 0, "mod": None, "gunluk_tutar": 0, "haftalik_tutar": 0, "son_tarih": None, "hedef_tutar": 0, "hedef_aciklama": None}
    
    # Rozetleri Çek
    c.execute("SELECT badge_code FROM user_badges WHERE username = ?", (username,))
    badges = [row['badge_code'] for row in c.fetchall()]
    
    bakiye = ayar.get("bakiye") or 0
    hedef = ayar.get("hedef_tutar") or 0
    yuzde = 0
    message = None
    is_completed = False
    new_badge = None
    
    if hedef > 0:
        yuzde = min(100, (bakiye / hedef) * 100)
        if bakiye >= hedef:
            message = "🎉 Tebrikler! Hedefinize ulaştınız!"
            is_completed = True
        
    return {"bakiye": bakiye, "islemler": islemler, "ayar": ayar, "progress": {"yuzde": round(yuzde, 1), "kalan": max(0, hedef - bakiye)}, "message": message, "is_completed": is_completed, "badges": badges}

@router.post("/kumbara/ayarlar")
def set_kumbara_ayar(a: KumbaraAyarIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    sync_user_data(username, conn)
    c = conn.cursor()
    
    # Mevcut ayarları çek (Merge işlemi için)
    c.execute("SELECT * FROM kumbara_ayarlar WHERE username = ?", (username,))
    row = c.fetchone()
    current = dict(row) if row else {}
    
    bakiye = current.get('bakiye', 0)
    
    # Merge Mantığı: Gelen veride değer varsa kullan, yoksa mevcut değeri koru
    # Birikim Ayarları
    if a.mod is not None and a.mod != "":
        new_mod = a.mod
        new_gunluk = a.gunluk_tutar
        new_haftalik = a.haftalik_tutar
        new_son_tarih = datetime.now().strftime("%d.%m.%Y")
    else:
        new_mod = current.get('mod')
        new_gunluk = current.get('gunluk_tutar', 0)
        new_haftalik = current.get('haftalik_tutar', 0)
        new_son_tarih = current.get('son_tarih', datetime.now().strftime("%d.%m.%Y"))
    
    # Hedef Ayarları
    if a.hedef_tutar is not None:
        # Eğer tutar 0 ise ve aynı anda birikim modu ayarlanıyorsa (mod != None), 
        # bu muhtemelen formun yan etkisidir (default 0). Mevcut hedefi koru.
        if a.hedef_tutar == 0 and a.mod is not None and a.mod != "":
            new_hedef_tutar = current.get('hedef_tutar', 0)
        else:
            new_hedef_tutar = a.hedef_tutar
    else:
        new_hedef_tutar = current.get('hedef_tutar', 0)
        
    new_hedef_aciklama = a.hedef_aciklama if a.hedef_aciklama is not None else current.get('hedef_aciklama')

    print(f"💰 Kumbara Ayar: Hedef={new_hedef_tutar}, Açıklama={new_hedef_aciklama}, Mod={new_mod}")
    c.execute("INSERT OR REPLACE INTO kumbara_ayarlar (username, bakiye, mod, gunluk_tutar, haftalik_tutar, son_tarih, hedef_tutar, hedef_aciklama) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (username, bakiye, new_mod, new_gunluk, new_haftalik, new_son_tarih, new_hedef_tutar, new_hedef_aciklama))
    conn.commit()
    return {"ok": True}

@router.post("/kumbara/islem")
def kumbara_islem(i: KumbaraIslemIn, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT * FROM kumbara_ayarlar WHERE username = ?", (username,))
    ayar_row = c.fetchone()
    bakiye = ayar_row['bakiye'] if ayar_row else 0
    if i.tur == "ekle": bakiye += i.tutar
    elif i.tur == "cek":
        if bakiye < i.tutar: raise HTTPException(status_code=400, detail="Yetersiz bakiye")
        bakiye -= i.tutar
    tarih = datetime.now().strftime("%d.%m.%Y")
    if ayar_row: c.execute("UPDATE kumbara_ayarlar SET bakiye = ? WHERE username = ?", (bakiye, username))
    else: c.execute("INSERT INTO kumbara_ayarlar (username, bakiye) VALUES (?, ?)", (username, bakiye))
    c.execute("INSERT INTO kumbara_islemleri (username, tarih, tutar, tur, aciklama) VALUES (?, ?, ?, ?, ?)", (username, tarih, i.tutar, i.tur, "Manuel işlem"))
    conn.commit()
    
    # Rozet Kontrolü: Gece Kuşu
    now = datetime.now()
    if 0 <= now.hour < 5:
        try:
            c.execute("INSERT INTO user_badges (username, badge_code, earned_at) VALUES (?, ?, ?)", (username, 'NIGHT_OWL', now.strftime("%d.%m.%Y")))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
    
    message = None
    is_completed = False
    new_badge = None
    
    hedef = ayar_row['hedef_tutar'] if ayar_row else 0
    if hedef > 0 and bakiye >= hedef:
        message = "🎉 Tebrikler! Hedefinize ulaştınız!"
        is_completed = True
        
        # Rozet Ver: Hedef Avcısı
        try:
            c.execute("INSERT INTO user_badges (username, badge_code, earned_at) VALUES (?, ?, ?)", (username, 'GOAL_MASTER', tarih))
            conn.commit() # Rozeti kaydet
            new_badge = "GOAL_MASTER"
        except sqlite3.IntegrityError:
            pass # Zaten rozeti var
        
    return {"ok": True, "bakiye": bakiye, "message": message, "is_completed": is_completed, "new_badge": new_badge}

@router.post("/harcamalar/otomatik-fis")
def add_harcama_ocr(file: UploadFile = File(...), current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_save_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_save_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    file.file.close()
    
    ocr_result = scan_receipt(file_save_path)
    
    # OCR işleminden sonra görseli küçült (Yer tasarrufu için)
    try:
        img = Image.open(file_save_path)
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((1024, 1024))
        img.save(file_save_path, quality=80, optimize=True)
    except Exception as e:
        print(f"OCR sonrası görsel küçültme hatası: {e}")

    aciklama = ocr_result["aciklama"]
    tutar = ocr_result["tutar"]
    tarih = ocr_result["tarih"] or datetime.now().strftime("%d.%m.%Y")

    item_id = str(uuid.uuid4())
    c = conn.cursor()
    c.execute("INSERT INTO harcamalar (id, username, aciklama, tutar, kategori, tarih, fis_dosyasi) VALUES (?, ?, ?, ?, ?, ?, ?)", (item_id, username, aciklama, tutar, "Diğer", tarih, unique_filename))
    conn.commit()
    
    # Rozet Kontrolü: İlk Harcama
    c.execute("SELECT COUNT(*) as count FROM harcamalar WHERE username = ?", (username,))
    row_count = c.fetchone()
    if row_count and row_count['count'] == 1:
        try:
            c.execute("INSERT INTO user_badges (username, badge_code, earned_at) VALUES (?, ?, ?)", (username, 'FIRST_EXPENSE', tarih))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    # Rozet Kontrolü: Gece Kuşu
    now = datetime.now()
    if 0 <= now.hour < 5:
        try:
            c.execute("INSERT INTO user_badges (username, badge_code, earned_at) VALUES (?, ?, ?)", (username, 'NIGHT_OWL', now.strftime("%d.%m.%Y")))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    c.execute("SELECT * FROM harcamalar WHERE id = ?", (item_id,))
    return dict(c.fetchone())

@router.post("/ocr")
def ocr_scan(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Fişi kaydetmeden sadece tarar ve verileri döner (Önizleme için)"""
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"temp_{uuid.uuid4()}{file_extension}"
    file_save_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_save_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        file.file.close()
        
        # Utils modülündeki fonksiyonu kullan
        ocr_result = scan_receipt(file_save_path)
        
        # Geçici dosyayı sil
        if os.path.exists(file_save_path): os.remove(file_save_path)
        
        # Eski API formatına uyumlu dönüş
        data = {
            "text": ocr_result.get("text", ""),
            "tarih": ocr_result.get("tarih"),
            "toplam": ocr_result.get("tutar"),
            "isyeri": ocr_result.get("aciklama")
        }
        return {"ok": True, "data": data}
    except Exception as e:
        if os.path.exists(file_save_path): os.remove(file_save_path)
        raise HTTPException(status_code=500, detail=f"OCR Hatası: {str(e)}")

@router.get("/tahmin")
def butce_tahmini(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT * FROM harcamalar WHERE username = ?", (username,))
    harcamalar = [dict(row) for row in c.fetchall()]
    bugun = datetime.now()
    ay_sonu_gun = calendar.monthrange(bugun.year, bugun.month)[1]
    bu_ay_harcama = sum(h['tutar'] for h in harcamalar if datetime.strptime(h['tarih'], "%d.%m.%Y").month == bugun.month)
    gunluk_ort = bu_ay_harcama / bugun.day if bugun.day > 0 else 0
    return {"bu_ay_harcama": bu_ay_harcama, "gunluk_ortalama": gunluk_ort, "tahmini_ay_sonu": bu_ay_harcama + (gunluk_ort * (ay_sonu_gun - bugun.day))}

@router.get("/export/excel")
def export_excel(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT * FROM harcamalar WHERE username = ?", (username,))
    harcamalar = [dict(row) for row in c.fetchall()]
    wb = Workbook()
    ws = wb.active
    ws.title = "Harcamalar"
    ws.append(["Tarih", "Kategori", "Açıklama", "Tutar"])
    for h in harcamalar: ws.append([h.get("tarih"), h.get("kategori"), h.get("aciklama"), h.get("tutar")])
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=butce_rapor.xlsx"})

@router.get("/export/pdf")
def export_pdf(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    username = current_user['username']
    c = conn.cursor()
    c.execute("SELECT * FROM harcamalar WHERE username = ?", (username,))
    harcamalar = [dict(row) for row in c.fetchall()]
    c.execute("SELECT * FROM gelirler WHERE username = ?", (username,))
    gelirler = [dict(row) for row in c.fetchall()]
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Başlık
    elements.append(Paragraph("Bütçe Raporu", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Harcamalar Tablosu
    elements.append(Paragraph("Harcamalar", styles['Heading2']))
    data = [["Tarih", "Kategori", "Açıklama", "Tutar"]]
    for h in harcamalar:
        data.append([h.get("tarih"), h.get("kategori"), h.get("aciklama"), str(h.get("tutar"))])
        
    if len(data) > 1:
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("Harcama kaydı bulunamadı.", styles['Normal']))

    elements.append(Spacer(1, 12))

    # Gelirler Tablosu (Basitçe eklendi, detaylandırılabilir)
    elements.append(Paragraph("Gelirler", styles['Heading2']))
    # ... Gelir tablosu mantığı buraya eklenebilir veya basitçe geçilebilir ...
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"butce_rapor_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )