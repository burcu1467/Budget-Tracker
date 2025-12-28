from typing import Optional
from pydantic import BaseModel, validator

class UserAuth(BaseModel):
    username: str
    password: str
    recovery_key: str = None

class HarcamaIn(BaseModel):
    aciklama: str
    tutar: float
    kategori: str
    tarih: str = None

class GelirIn(BaseModel):
    aciklama: str
    tutar: float
    tarih: str = None

class ButceIn(BaseModel):
    tutar: float

class KategoriButceIn(BaseModel):
    kategori: str
    limit_tutar: float

class CategoryIn(BaseModel):
    name: str

class TekrarlayanIn(BaseModel):
    aciklama: str
    tutar: float
    kategori: str
    gun: int
    aktif: bool = True

class KumbaraAyarIn(BaseModel):
    mod: Optional[str] = None # "gunluk", "haftalik"
    gunluk_tutar: float = 0
    haftalik_tutar: float = 0
    hedef_tutar: Optional[float] = None
    hedef_aciklama: Optional[str] = None

    @validator('gunluk_tutar', 'haftalik_tutar', pre=True)
    def parse_float_zero(cls, v):
        if v == "" or v is None: return 0.0
        if isinstance(v, str):
            try:
                return float(v.replace(',', '.'))
            except ValueError:
                return 0.0
        return v

    @validator('hedef_tutar', pre=True)
    def parse_float_none(cls, v):
        if v == "" or v is None: return None
        if isinstance(v, str):
            try:
                return float(v.replace(',', '.'))
            except ValueError:
                return None
        return v

class KumbaraIslemIn(BaseModel):
    tutar: float
    tur: str # "ekle", "cek"

    @validator('tutar', pre=True)
    def parse_tutar(cls, v):
        if isinstance(v, str):
            try:
                return float(v.replace(',', '.'))
            except ValueError:
                return 0.0
        return v

class RecoveryUpdateIn(BaseModel):
    username: str
    password: str
    new_recovery_key: str

class PasswordChangeIn(BaseModel):
    username: str
    old_password: str
    new_password: str

class ProfileIn(BaseModel):
    email: str