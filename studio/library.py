"""Thư viện asset DÙNG CHUNG cho mọi video (Sếp chốt 05/11: "xây 1 lần, dùng nhiều lần").

  assets/library/index.json            danh mục: mỗi asset 1 mục (chủ đề, loại, tag, prompt, nguồn, job đã dùng, bộ)
  assets/library/<chủ-đề>/<tên>.png    ảnh (bản phụ <tên>_v2.png) + <tên>.json (nguồn AI — project.py đọc để QA nhắc)
  assets/library/kits/<bộ>.json        BỘ = đủ asset cho MỘT kiểu animation/hiệu ứng (vd thẻ cắt dán mở chương);
                                       `vs.py lib kit <bộ>` chỉ tạo phần còn THIẾU, rồi ra ảnh soát cả bộ

Luật: cần asset → `lib find` trước; có rồi thì dùng (`vs.py edit add <job> lib:<id> --key g01`), KHÔNG tạo lại. Thiếu
→ bổ sung vào BỘ của kiểu hiệu ứng đó (hoàn thiện cả bộ một lần), không tạo lẻ cho một video. Tạo bằng Codex local
(studio/imagegen.py); Codex hỏng → Claude tạo trên chatgpt.com (Chrome đã đăng nhập) rồi `vs.py lib import`.
Asset nền trong suốt dùng được cho Claude Design (tải lên project, dựng animation HTML setTime → `vs.py motion import`).
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio import config, imagegen

LIB = config.ROOT / "assets" / "library"
INDEX = LIB / "index.json"
KITS = LIB / "kits"
KINDS = {"canh": "cảnh minh hoạ / bối cảnh (có nền, làm cover)", "nen": "nền / chất liệu (giấy, gỗ…) phủ kín khung",
         "cat-dan": "miếng cắt dán nền trong suốt (giấy, người giấy, mũi tên…)",
         "icon": "biểu tượng / sticker nền trong suốt", "khac": "khác"}


class LibraryError(RuntimeError):
    pass


_lock = threading.RLock()  # kit_gen tạo song song → ghi index.json phải tuần tự


def load() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {"assets": {}}


def save(idx: dict) -> None:
    LIB.mkdir(parents=True, exist_ok=True)
    idx["assets"] = dict(sorted(idx["assets"].items()))
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


def _check_id(asset_id: str) -> tuple[str, str]:
    parts = asset_id.strip("/").split("/")
    if len(parts) != 2 or parts[0] == "kits" or \
            not all(p and p.replace("-", "").isascii() and p.replace("-", "").isalnum() and p == p.lower() for p in parts):
        raise LibraryError(f"id '{asset_id}' phải dạng <chủ-đề>/<tên> chữ thường không dấu, nối bằng '-' "
                           "(vd cat-dan-giay/mui-ten-vang)")
    return parts[0], parts[1]


def path(asset_id: str) -> Path:
    theme, name = _check_id(asset_id)
    return LIB / theme / f"{name}.png"


def get(asset_id: str) -> dict | None:
    return load()["assets"].get(asset_id)


def find(query: str = "", kind: str | None = None, theme: str | None = None) -> list[dict]:
    """Tìm theo từ (khớp id, tag, prompt — không phân biệt hoa thường, mọi từ phải có)."""
    words = [w for w in query.lower().split() if w]
    out = []
    for aid, a in load()["assets"].items():
        if kind and a.get("kind") != kind or theme and a.get("theme") != theme:
            continue
        hay = " ".join([aid, " ".join(a.get("tags", [])), a.get("prompt", ""), a.get("title", "")]).lower()
        if all(w in hay for w in words):
            out.append({"id": aid, **a})
    return out


def _record(asset_id: str, kind: str, meta: dict, tags: list[str], title: str, kit: str | None) -> dict:
    theme, _ = _check_id(asset_id)
    with _lock:
        return _record_locked(asset_id, theme, kind, meta, tags, title, kit)


def _record_locked(asset_id: str, theme: str, kind: str, meta: dict, tags: list[str], title: str, kit: str | None) -> dict:
    idx = load()
    old = idx["assets"].get(asset_id, {})
    a = {"theme": theme, "kind": kind, "title": title or old.get("title", ""),
         "tags": sorted(set(old.get("tags", [])) | set(tags)), "file": str(path(asset_id).relative_to(LIB)).replace("\\", "/"),
         "alpha": meta.get("alpha", False), "size": meta.get("size"), "prompt": meta.get("prompt", ""),
         "engine": meta.get("engine"), "model": meta.get("model"), "created": meta.get("created"),
         "variants": [v["file"] for v in meta.get("variants", [])][1:],
         "dims": [meta["variants"][0]["w"], meta["variants"][0]["h"]] if meta.get("variants") else None,
         "kits": sorted(set(old.get("kits", [])) | ({kit} if kit else set())), "used_by": old.get("used_by", [])}
    idx["assets"][asset_id] = a
    save(idx)
    return a


def gen(asset_id: str, prompt: str, kind: str = "canh", alpha: bool = False, size: str = "doc",
        tags: list[str] | None = None, refs: list[Path] | None = None, title: str = "", kit: str | None = None,
        force: bool = False) -> tuple[dict, bool]:
    """Tạo asset vào thư viện. ĐÃ CÓ thì trả lại cái cũ (created=False), chỉ tạo lại khi force=True."""
    if kind not in KINDS:
        raise LibraryError(f"kind '{kind}' không có (dùng {', '.join(KINDS)})")
    old = get(asset_id)
    if old and path(asset_id).exists() and not force:
        if kit and kit not in old.get("kits", []):
            idx = load()
            idx["assets"][asset_id]["kits"] = sorted(set(old.get("kits", [])) | {kit})
            save(idx)
        return get(asset_id), False
    meta = imagegen.generate(prompt, path(asset_id), size=size, alpha=alpha, refs=refs)
    return _record(asset_id, kind, meta, tags or [], title, kit), True


def import_file(src: Path, asset_id: str, prompt: str, kind: str, tags: list[str] | None = None, title: str = "",
                engine: str = "chatgpt-web", force: bool = False) -> dict:
    """Nạp ảnh có sẵn (tạo trên chatgpt.com qua Chrome, hoặc ảnh Sếp đưa) vào thư viện."""
    if get(asset_id) and not force:
        raise LibraryError(f"{asset_id} đã có — dùng lại, hoặc --force để thay")
    im = Image.open(src)
    alpha = im.mode in ("RGBA", "LA") and min(im.getchannel("A").getextrema()) < 250
    dst = path(asset_id)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if alpha:
        a = np.array(im.convert("RGBA"))
        a[:, :, 3] = np.where(a[:, :, 3] >= 250, 255, a[:, :, 3])  # thân ảnh AI ~253 → đặc hẳn
        Image.fromarray(a, "RGBA").save(dst)
    else:
        im.convert("RGB").save(dst)
    meta = {"engine": engine, "kind": "ai" if engine != "photo" else "photo", "prompt": prompt, "alpha": alpha,
            "created": f"{datetime.now():%Y-%m-%d %H:%M}", "variants": [{"file": dst.name, "w": im.width, "h": im.height}],
            "note": "ẢNH AI — chỉ minh hoạ bối cảnh/ý; không thay ảnh sản phẩm thật, không làm bằng chứng"
            if engine != "photo" else "ảnh thật"}
    dst.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return _record(asset_id, kind, meta, tags or [], title, None)


def mark_used(asset_id: str, job_id: str) -> None:
    idx = load()
    a = idx["assets"].get(asset_id)
    if a is not None and job_id not in a.setdefault("used_by", []):
        a["used_by"].append(job_id)
        save(idx)


def resolve(ref: str) -> tuple[Path, str | None]:
    """'lib:<chủ-đề>/<tên>' → (đường file, id); đường thường → (đường, None)."""
    if not ref.startswith("lib:"):
        return Path(ref), None
    aid = ref[4:]
    if not get(aid) or not path(aid).exists():
        raise LibraryError(f"thư viện chưa có {aid} (vs.py lib find …)")
    return path(aid), aid


# ───────────────────────── bộ (kit) = đủ asset cho 1 kiểu animation ─────────────────────────
def load_kit(kit_id: str) -> dict:
    p = KITS / f"{kit_id}.json"
    if not p.exists():
        raise LibraryError(f"chưa có bộ {kit_id} ({p})")
    return json.loads(p.read_text(encoding="utf-8"))


def kit_status(kit_id: str) -> list[dict]:
    kit = load_kit(kit_id)
    return [{**it, "have": bool(get(it["id"])) and path(it["id"]).exists()} for it in kit["assets"]]


def kit_gen(kit_id: str, parallel: int = 3, only: list[str] | None = None, log=print) -> dict:
    """Tạo các asset còn THIẾU của bộ (song song ≤3 lượt Codex). Trả {made, kept, failed}."""
    kit = load_kit(kit_id)
    style = kit.get("style", "")
    todo = [it for it in kit_status(kit_id) if not it["have"] and (not only or it["id"] in only)]
    res = {"made": [], "kept": [it["id"] for it in kit_status(kit_id) if it["have"]], "failed": {}}

    def one(it):
        prompt = it["prompt"] + (f"\nPhong cách chung của bộ: {style}" if style else "")
        a, _ = gen(it["id"], prompt, kind=it.get("kind", "cat-dan"), alpha=it.get("alpha", it.get("kind") in
                   ("cat-dan", "icon")), size=it.get("size", "vuong"), tags=it.get("tags", []) + [kit_id],
                   title=it.get("title", ""), kit=kit_id,
                   refs=[LIB / r for r in it.get("refs", kit.get("refs", []))])
        return it["id"], a

    with ThreadPoolExecutor(max_workers=max(1, parallel)) as ex:
        futs = {ex.submit(one, it): it["id"] for it in todo}
        for f, aid in futs.items():
            try:
                f.result()
                res["made"].append(aid)
                log(f"  ✓ {aid}")
            except Exception as exc:  # một ảnh hỏng không làm hỏng cả bộ — chạy lại lệnh sẽ chỉ tạo phần còn thiếu
                res["failed"][aid] = str(exc)[:200]
                log(f"  ✗ {aid}: {str(exc)[:160]}")
    idx = load()
    for aid in res["kept"]:  # asset có sẵn từ trước (vd tạo lẻ) cũng ghi tên bộ
        idx["assets"][aid]["kits"] = sorted(set(idx["assets"][aid].get("kits", [])) | {kit_id})
    save(idx)
    return res


def export_web(ids: list[str], out_dir: Path, max_px: int = 900, bg_px: int = 1080) -> dict:
    """Bản nhẹ cho HTML animation: cắt viền trong suốt + thu nhỏ (nền `nen` giữ khung) → out_dir/assets/<tên>.png và
    out_dir/assets.js (`window.KIT_ASSETS = {tên: {src, w, h}}` — Motion Engine tự chép kèm khi import)."""
    (out_dir / "assets").mkdir(parents=True, exist_ok=True)
    table = {}
    for aid in ids:
        a = get(aid)
        if not a or not path(aid).exists():
            raise LibraryError(f"thiếu asset {aid} — chạy `vs.py lib kit` trước")
        im = Image.open(path(aid)).convert("RGBA")
        if a.get("alpha"):
            bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
            im = im.crop(bb) if bb else im
            lim = max_px
        else:
            im = im.convert("RGB")
            lim = bg_px
        k = min(1.0, lim / max(im.size))
        if k < 1:
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        name = aid.split("/")[1]
        im.save(out_dir / "assets" / f"{name}.png", optimize=True)
        table[name] = {"src": f"assets/{name}.png", "w": im.width, "h": im.height}
    (out_dir / "assets.js").write_text("// sinh bởi studio/library.py export_web — không sửa tay\nwindow.KIT_ASSETS = "
                                       + json.dumps(table, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    return table


# ───────────────────────── ảnh soát ─────────────────────────
def sheet(ids: list[str], out: Path, cell: int = 300) -> Path:
    """Ảnh soát: mỗi asset 1 ô (nền trong suốt hiện trên nền ca-rô), ghi id."""
    font = ImageFont.truetype(str(config.FONT_REGULAR), 15)   # font trong repo — chạy được cả Windows lẫn Mac
    cols = min(5, max(1, len(ids)))
    rows = (len(ids) + cols - 1) // cols
    W, H = cell, int(cell * 1.25)
    board = Image.new("RGB", (cols * W, rows * (H + 24)), (24, 24, 24))
    for i, aid in enumerate(ids):
        x, y = (i % cols) * W, (i // cols) * (H + 24)
        p = path(aid)
        tile = Image.new("RGB", (W - 6, H - 6), (200, 200, 200))
        d = ImageDraw.Draw(tile)
        for cy in range(0, H, 16):
            for cx in range(0, W, 16):
                if (cx // 16 + cy // 16) % 2:
                    d.rectangle([cx, cy, cx + 15, cy + 15], fill=(160, 160, 160))
        if p.exists():
            im = Image.open(p).convert("RGBA")
            im.thumbnail((W - 6, H - 6))
            tile.paste(im, ((W - 6 - im.width) // 2, (H - 6 - im.height) // 2), im)
        else:
            d.text((10, H // 2), "CHƯA CÓ", font=font, fill=(200, 0, 0))
        board.paste(tile, (x + 3, y + 3))
        ImageDraw.Draw(board).text((x + 6, y + H + 2), aid, font=font, fill=(255, 214, 90))
    out.parent.mkdir(parents=True, exist_ok=True)
    board.save(out, quality=88)
    return out
