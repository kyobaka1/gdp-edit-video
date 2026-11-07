r"""Ảnh demo từng PHONG CÁCH (assets/styles/<id>/demo.jpg): chữ động thật (assets/kinetic) với skin của phong cách,
trên khung hình đã chỉnh màu theo phong cách, cho 2 thương hiệu (GDP · PHALEDO) + màn chữ kính mờ.
Không render video — chỉ chụp tĩnh để soát kiểu chữ / màu / vị trí (vài giây mỗi phong cách).

    .\.venv\Scripts\python.exe tools\style_previews.py [gdp-ban-hang ...] [--bg ảnh.jpg]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from studio import config, media  # noqa: E402
from studio.edit import styles  # noqa: E402
from studio.edit.build import _glass, _grade  # noqa: E402
from studio.edit.cutlib import Cut  # noqa: E402
from studio.edit.kinetic import Kinetic  # noqa: E402

W, H = 540, 960
SHOPS = {"GIADUNGPLUS": "giadungplus_official", "PHALEDO": "phaledo_official"}
# chữ mẫu (markup như c.cap) — 3 khung: chữ thường + cụm khoá · nhấn màu / nghiêng · màn chữ
SAMPLE = {
    "GIADUNGPLUS": [".mẹo này giúp / !tủ bếp gọn gàng", "chỉ cần / ^dán là xong / !!không cần khoan", "~10 phút / .cho cả căn bếp"],
    "PHALEDO": [".chất liệu / !thủy tinh dày", "an toàn / ^cho cả gia đình / !!rửa máy được", "~Gỗ sồi / .và thủy tinh"],
}


def bg_frame(path: Path | None) -> np.ndarray:
    if path and path.exists():
        f = cv2.imread(str(path)) if path.suffix.lower() in (".jpg", ".png") else None
        if f is None:
            tmp = config.ROOT / "assets" / "styles" / "_bg.jpg"
            media.extract_frame(path, 14.0, tmp, width=W)
            f = cv2.imread(str(tmp))
        h0, w0 = f.shape[:2]
        sc = max(W / w0, H / h0)
        f = cv2.resize(f, (int(w0 * sc + 0.5), int(h0 * sc + 0.5)))
        y0, x0 = (f.shape[0] - H) // 2, (f.shape[1] - W) // 2
        return f[y0:y0 + H, x0:x0 + W].copy()
    yy = np.linspace(0, 1, H)[:, None, None]   # nền giả: tường ấm + vùng "người" tối ở giữa
    f = (np.array([150, 170, 190]) * (1 - yy) + np.array([60, 70, 85]) * yy).astype(np.uint8)
    f = np.repeat(f, W, axis=1)
    cv2.ellipse(f, (W // 2, int(H * 0.42)), (int(W * 0.22), int(H * 0.2)), 0, 0, 360, (70, 80, 100), -1)
    return f


def blocks_for(markups: list[str], y: float, card_idx: int) -> list[dict]:
    out = []
    for k, m in enumerate(markups):
        lines = Cut._parse(None, m)
        t = k * 10.0
        for ln in lines:
            ln["words"] = [{"text": tok["text"], "t": t + 0.05 * i} for i, tok in enumerate(ln.pop("toks"))]
        out.append({"id": f"s{k}", "end": t + 5, "exit": "words", "card": k == card_idx, "lines": lines,
                    "align": "center", "x": 0.5 if k == card_idx else 0.46, "y": 0.47 if k == card_idx else y})
    return out


def compose(base: np.ndarray, rgba_png: Path) -> np.ndarray:
    ov = cv2.imread(str(rgba_png), cv2.IMREAD_UNCHANGED)
    if ov is None or ov.shape[2] < 4:
        return base
    a = ov[..., 3:4].astype(np.float32) / 255
    return (base.astype(np.float32) * (1 - a) + ov[..., :3].astype(np.float32) * a).astype(np.uint8)


def label(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    cv2.rectangle(out, (0, 0), (W, 34), (20, 20, 20), -1)
    cv2.putText(out, text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1, cv2.LINE_AA)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--bg", type=Path, default=None, help="ảnh / video nền (mặc định: nền giả)")
    a = ap.parse_args()
    raw = bg_frame(a.bg)
    tmp = config.ROOT / "assets" / "styles" / "_tmp.png"
    for sid in a.ids or styles.ids():
        st = styles.load(sid)
        rows = []
        for brand, shop in SHOPS.items():
            cfg = styles.resolve(st, shop)
            graded = _grade(W, H, cfg["grade"])(raw.copy()) if cfg["grade"] else raw.copy()
            bl = blocks_for(SAMPLE[brand], cfg["captions"].get("y", 0.47), card_idx=2)
            panels = []
            with Kinetic(cfg["page"], W, H, cfg["skin"]) as kin:
                kin.load(bl)
                for k, b in enumerate(bl):
                    kin.still(b["end"] - 0.5, tmp)
                    base = _glass(graded) if b["card"] and cfg["card_bg"] == "glass" else \
                        np.zeros_like(graded) if b["card"] else graded
                    panels.append(label(compose(base, tmp), f"{brand} · {['chu + cum khoa', 'nhan mau / nghieng', 'man chu ' + cfg['card_bg']][k]}"))
            rows.append(np.hstack(panels))
        board = np.vstack(rows)
        out = Path(st["dir"]) / "demo.jpg"
        cv2.imwrite(str(out), board, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"✓ {sid}: {out}")
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
