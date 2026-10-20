"""Tạo khung thư mục chuẩn cho một shop: assets/shops/<mã>/ + shop.json mẫu. Không ghi đè file đã có.

Chạy: .venv\\Scripts\\python.exe tools\\init_shop.py <mã shop> [--brand PHALEDO] [--templates-from <mã shop khác>]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config  # noqa: E402

SHOPS = config.ROOT / "assets" / "shops"
FOLDERS = {
    "logo": "Thả logo: logo.png (màu gốc, nền trong suốt) · logo-white.png (trên nền tối) · logo-dark.png (trên nền sáng) · icon.png (vuông) · logo.svg (tuỳ chọn).",
    "intro": "Tuỳ chọn: intro.mp4 — đoạn mở đầu ≤ 3 giây, dọc 9:16 (1080×1920).",
    "outro": "Tuỳ chọn: outro.mp4 — màn kết logo + lời kêu gọi mua, ≤ 4 giây, 9:16.",
    "templates": "Mẫu chữ đè HTML + manifest.json (hợp đồng: assets/shops/README.md). Không có → khai templates_from trong shop.json.",
    "music": "Nhạc nền đã duyệt bản quyền cho shop (mp3/wav).",
    "watermark": "watermark.png nếu shop dùng watermark.",
    "fonts": "Font riêng của shop (nếu có). Font chung ở assets/fonts/.",
    "reference": "Ảnh tham chiếu phong cách: mẫu font, ảnh bìa, bài đăng mẫu.",
}


def skeleton(code: str, brand: str = "", templates_from: str | None = None) -> dict:
    return {
        "shop": code,
        "title": "",
        "platform": "",
        "brand": brand,
        "configured": False,
        "palette": {"dark": "", "accent": "", "primary": "", "text_on_dark": "", "text_on_light": ""},
        "tone": "",
        "templates_from": templates_from,
        "logo": {
            "placement": "top-center",
            "files": {"primary": "logo/logo.png", "on_dark": "logo/logo-white.png",
                      "on_light": "logo/logo-dark.png", "icon": "logo/icon.png", "vector": "logo/logo.svg"},
        },
        "intro": {"file": "intro/intro.mp4", "enabled": False},
        "outro": {"file": "outro/outro.mp4", "enabled": False, "cta": ""},
        "music": {"default": None},
        "prod": {},
        "notes": "",
    }


def init(code: str, brand: str = "", templates_from: str | None = None, data: dict | None = None) -> Path:
    root = SHOPS / code
    for name, hint in FOLDERS.items():
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        readme = d / "_README.txt"
        if not readme.exists():
            readme.write_text(hint + "\n", encoding="utf-8")
    sj = root / "shop.json"
    if not sj.exists():
        doc = skeleton(code, brand, templates_from)
        if data:
            doc.update(data)
        sj.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("--brand", default="")
    p.add_argument("--templates-from")
    a = p.parse_args()
    print(init(a.code, a.brand, a.templates_from))
