import os
import re
import logging
from datetime import datetime
import pytesseract
from PIL import Image, ImageEnhance

# Pillow sürüm uyumluluğu
try:
    resample_filter = Image.Resampling.BICUBIC
except AttributeError:
    resample_filter = Image.BICUBIC

# Tesseract-OCR yolu (Windows için gerekirse)
tesseract_env_path = os.getenv("TESSERACT_CMD")
if tesseract_env_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_env_path
elif os.name == 'nt':
    default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(default_path):
        pytesseract.pytesseract.tesseract_cmd = default_path

# Loglama yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_ocr_amount(val_str):
    try:
        val_str = val_str.replace(' ', '').strip()
        val_str = re.sub(r'[^\d.,]', '', val_str)
        if not val_str: return None
        if '.' in val_str and ',' in val_str:
            if val_str.rfind(',') > val_str.rfind('.'): return float(val_str.replace('.', '').replace(',', '.'))
            else: return float(val_str.replace(',', ''))
        elif ',' in val_str: return float(val_str.replace(',', '.'))
        elif '.' in val_str:
            parts = val_str.split('.')
            if len(parts) > 2: return float(val_str.replace('.', ''))
            if len(parts[-1]) == 3: return float(val_str.replace('.', ''))
            return float(val_str)
        return float(val_str)
    except: return None

def scan_receipt(image_path):
    """
    Verilen görsel yolundaki fişi tarar ve tarih, tutar, açıklama bilgilerini döner.
    """
    result = {
        "aciklama": "Fiş Taraması",
        "tutar": 0.0,
        "tarih": None,
        "text": ""
    }
    
    try:
        if not os.path.exists(image_path):
            logger.error(f"Dosya bulunamadı: {image_path}")
            return result

        logger.info(f"OCR işlemi başlatılıyor: {image_path}")

        image = Image.open(image_path).convert('L')
        image = image.resize((image.width * 2, image.height * 2), resample_filter)
        image = ImageEnhance.Sharpness(image).enhance(2.0)
        image = ImageEnhance.Contrast(image).enhance(1.5)
        
        try: 
            text = pytesseract.image_to_string(image, lang='tur+eng')
        except Exception as e: 
            logger.warning(f"Tesseract Türkçe/İngilizce tarama hatası, varsayılan dil deneniyor: {e}")
            try:
                text = pytesseract.image_to_string(image)
            except Exception as e2:
                logger.error(f"OCR metin okuma başarısız: {e2}")
                return result
        
        result["text"] = text
        
        # Tarih Bulma (İyileştirilmiş)
        # Önce YYYY (20xx) formatını ara
        tarih_match = re.search(r'(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(20\d{2})', text)
        if not tarih_match:
            # Bulamazsa YY formatını ara
            tarih_match = re.search(r'(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{2})', text)
            
        if tarih_match:
            d, m, y = tarih_match.groups()
            if len(y) == 2: y = "20" + y
            try:
                # Tarihin geçerli olup olmadığını kontrol et
                datetime.strptime(f"{d}.{m}.{y}", "%d.%m.%Y")
                result["tarih"] = f"{d.zfill(2)}.{m.zfill(2)}.{y}"
            except ValueError:
                pass
        
        # Tutar Bulma (İyileştirilmiş - Anahtar Kelime Bazlı)
        lines = text.split('\n')
        found_amount = None
        keywords = ["TOPLAM", "TUTAR", "GENEL", "ODENECEK", "ODENEN", "KREDİ", "TOTAL"]
        
        for i, line in enumerate(lines):
            line_upper = line.upper()
            if any(k in line_upper for k in keywords):
                # Satırdaki sayıları kontrol et
                line_vals = [parse_ocr_amount(m) for m in re.findall(r'(\d+(?:\s*[.,]\s*\d+)*)', line)]
                line_vals = [v for v in line_vals if v is not None and v < 1000000]
                if line_vals:
                    found_amount = max(line_vals)
                    break
                # Alt satıra bak (Genellikle "TOPLAM" yazısının altında olur)
                if i + 1 < len(lines):
                    next_vals = [parse_ocr_amount(m) for m in re.findall(r'(\d+(?:\s*[.,]\s*\d+)*)', lines[i+1])]
                    next_vals = [v for v in next_vals if v is not None and v < 1000000]
                    if next_vals:
                        found_amount = max(next_vals)
                        break
        
        if found_amount:
            result["tutar"] = found_amount
        else:
            # Fallback: En büyük sayıyı al (Yıl benzeri sayılar hariç)
            all_amounts = []
            for m in re.findall(r'(?:\b|[^0-9])(\d+(?:\s*[.,]\s*\d+)*)(?:\b|[^0-9])', text):
                val = parse_ocr_amount(m)
                if val and val < 1000000 and not (2000 <= val <= 2100 and val % 1 == 0): 
                    all_amounts.append(val)
            if all_amounts: result["tutar"] = max(all_amounts)
        
        logger.info(f"OCR Başarılı - Tarih: {result['tarih']}, Tutar: {result['tutar']}")
    except Exception as e: 
        logger.error(f"OCR Genel Hatası: {e}", exc_info=True)

    return result