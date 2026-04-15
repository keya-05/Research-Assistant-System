import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from app.database import engine, Base
from app.rate_limiter import limiter
from app.routers import tickets

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

app = FastAPI(title="Ticketing API")
app.state.limiter = limiter
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait a moment and try again."},
    )


Base.metadata.create_all(bind=engine)

app.include_router(tickets.router)


@app.get("/")
def home():
    return FileResponse(str(INDEX_FILE))


@app.get("/health")
def health():
    return {"message": "Ticketing API running"}
