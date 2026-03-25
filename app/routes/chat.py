import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import CHAT_UI_CONFIG

router = APIRouter()

_BASE_DIR = Path(__file__).resolve().parents[1]
_TEMPLATE_PATH = _BASE_DIR / "templates" / "chat.html"


@lru_cache(maxsize=1)
def _load_template() -> str:
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


@router.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    template = _load_template()
    html = template.replace("__APP_CONFIG_JSON__", json.dumps(CHAT_UI_CONFIG))
    return HTMLResponse(content=html)
