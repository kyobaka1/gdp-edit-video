"""Cấu hình chung: đường dẫn, key, ffmpeg. Đọc từ .env ở gốc studio."""

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

INBOX = ROOT / "inbox"
JOBS = ROOT / "jobs"
FONTS = ROOT / "assets" / "fonts"
BRANDS = ROOT / "assets" / "brands"

FONT_BOLD = FONTS / "BeVietnamPro-Bold.ttf"
FONT_EXTRABOLD = FONTS / "BeVietnamPro-ExtraBold.ttf"
FONT_REGULAR = FONTS / "BeVietnamPro-Regular.ttf"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip() or "gemini-3-flash-preview"

_WINGET_LINKS = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links"


def _resolve_tool(name: str, env_var: str) -> str | None:
    """Ưu tiên biến .env, rồi PATH, rồi WinGet\\Links (PATH của tiến trình có thể cũ sau khi cài)."""
    explicit = os.getenv(env_var, "").strip()
    if explicit:
        return explicit if Path(explicit).exists() else None
    found = shutil.which(name)
    if found:
        return found
    candidate = _WINGET_LINKS / f"{name}.exe"
    return str(candidate) if candidate.exists() else None


FFMPEG = _resolve_tool("ffmpeg", "FFMPEG_PATH")
FFPROBE = _resolve_tool("ffprobe", "FFPROBE_PATH")
