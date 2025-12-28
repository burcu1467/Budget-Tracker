import os
import logging
import uvicorn
from fastapi import FastAPI, Request, APIRouter, Response
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse

from config import settings
from database import init_db
import auth
import transactions
import users

# Loglama yapılandırması
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Bütçe Takipçisi API", lifespan=lifespan)

# Güvenlik için izin verilen kökenleri (origins) belirleyin.
# Varsayılan olarak localhost portlarını ekler, üretim ortamı için .env dosyasında ALLOWED_ORIGINS tanımlanmalıdır.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hata ayıklama için gelen istekleri ve yanıt kodlarını yazdıran middleware
@app.middleware("http")
async def debug_logging(request: Request, call_next):
    logger.info(f"--> Gelen İstek: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"<-- Yanıt Kodu: {response.status_code}")
    
    # Sadece API istekleri için önbelleği devre dışı bırak (Statik dosyalar cache'lensin)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
    return response

# API rotalarını '/api' altında grupla ve etiketle
api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router, tags=["Auth"])
api_router.include_router(users.router, tags=["Users"])
api_router.include_router(transactions.router, tags=["Transactions"])
app.include_router(api_router)

# Favicon isteğini özel olarak ele al (Dosya yoksa 404 yerine 204 döndür)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    file_path = os.path.join(settings.STATIC_DIR, "favicon.ico")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return Response(status_code=204)

static_dir = settings.STATIC_DIR
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    logger.info("🚀 Uygulama çalışıyor. Codespaces 'Ports' sekmesinden adresi açabilirsiniz.")
    uvicorn.run(app, host="0.0.0.0", port=8000)