from pydantic import BaseModel

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
    mod: str = None # "gunluk", "haftalik"
    gunluk_tutar: float = 0
    haftalik_tutar: float = 0
    hedef_tutar: float = 0
    hedef_aciklama: str = None

class KumbaraIslemIn(BaseModel):
    tutar: float
    tur: str # "ekle", "cek"

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