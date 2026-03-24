from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.api import router as api_router
from app.routes.chat import router as chat_router

load_dotenv()

app = FastAPI(title="Clinical Codes Finder")

_BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")

app.include_router(chat_router)
app.include_router(api_router)
