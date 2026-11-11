"""Kết nối app PluSor (giadungplus.store) — đọc listing / tải ảnh / nộp ảnh kết quả. Dùng chung token với plusor.py.

Token KHÔNG chép sang chỗ khác: đọc theo thứ tự biến môi trường → `.env` của studio → `.env` của plusor-pipeline
(biến `PLUSOR_ENV_FILE`, mặc định `~/Desktop/Codex Workflow/plusor-pipeline/.env`)."""

import os
from pathlib import Path
from urllib.parse import urlparse

import requests

from . import ROOT

API = "/marketing/listing/api/bot"
_ENV_FILES = [ROOT / ".env",
              Path(os.getenv("PLUSOR_ENV_FILE", "") or Path.home() / "Desktop" / "Codex Workflow" / "plusor-pipeline" / ".env")]


def cfg() -> tuple[str, str]:
    for f in _ENV_FILES:
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    base, token = os.getenv("PLUSOR_BASE_URL", "").rstrip("/"), os.getenv("PLUSOR_TOKEN", "")
    if not base or not token:
        raise SystemExit("Thiếu PLUSOR_BASE_URL / PLUSOR_TOKEN — đặt trong .env của studio hoặc của plusor-pipeline "
                         "(PLUSOR_ENV_FILE trỏ tới file đó).")
    return base, token


def _session() -> tuple[requests.Session, str]:
    base, token = cfg()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})
    return s, base


def _check(r: requests.Response, what: str) -> requests.Response:
    if r.status_code >= 400:
        raise SystemExit(f"{what} → HTTP {r.status_code}: {r.text[:300]!r}")
    return r


def listing(lid: int) -> dict:
    s, base = _session()
    return _check(s.get(f"{base}{API}/listings/{lid}/", timeout=120), f"đọc listing {lid}").json()["data"]


def design_plan(lid: int) -> dict:
    """Design plan (chữ bán hàng đã soạn sẵn cho Editor — skill gdp-listing-plan). Chưa có → {}."""
    s, base = _session()
    r = s.get(f"{base}{API}/listings/{lid}/design-plan/", timeout=120)
    return (r.json().get("data") or {}).get("design_plan") or {} if r.status_code < 400 else {}


def queue(shop: str = "") -> list[dict]:
    s, base = _session()
    r = _check(s.get(f"{base}{API}/queue/", params={"shop": shop} if shop else {}, timeout=120), "đọc hàng đợi")
    return r.json()["data"]["listings"]


def download(url: str, dest: Path) -> Path | None:
    """Tải 1 file (URL ký sẵn của R2, hoặc đường dẫn tương đối qua app) → `dest` + đuôi đúng. Lỗi → None."""
    if not url:
        return None
    s, base = _session()
    if url.startswith("http"):
        r = requests.get(url, timeout=180)          # URL ký sẵn: không gửi token ra ngoài app
    else:
        r = s.get(base + "/" + url.lstrip("/"), timeout=180)
    if r.status_code >= 400 or not r.content:
        return None
    ext = Path(urlparse(url).path).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ctype = r.headers.get("content-type", "")
        ext = ".png" if "png" in ctype else ".webp" if "webp" in ctype else ".jpg"
    dest = dest.with_suffix(ext)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


def upload_result(item_id: int, file: Path, note: str = "") -> None:
    """Nộp ảnh kết quả cho 1 item (GHI ĐÈ kết quả đang có trên app) — chỉ gọi khi Sếp đã duyệt."""
    s, base = _session()
    with open(file, "rb") as fh:
        r = s.post(f"{base}{API}/items/{item_id}/upload-result/", files={"file": (file.name, fh)},
                   data={"note": note} if note else None, timeout=300)
    _check(r, f"nộp ảnh item {item_id}")


def request_review(lid: int, kind: str) -> None:
    s, base = _session()
    _check(s.post(f"{base}{API}/listings/{lid}/request-review/", json={"kind": kind}, timeout=60), f"xin duyệt {kind}")


def comment(lid: int, kind: str, content: str) -> None:
    s, base = _session()
    _check(s.post(f"{base}{API}/listings/{lid}/section-comment/", json={"kind": kind, "content": content}, timeout=60),
           f"ghi trao đổi {kind}")
