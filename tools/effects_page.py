r"""Thư viện hiệu ứng → trang xem hieu-ung.html (mở thẳng bằng Chrome, không cần server).

    .\.venv\Scripts\python.exe tools\effects_page.py            # cắt clip demo + ảnh thu nhỏ còn thiếu, rồi dựng trang
    .\.venv\Scripts\python.exe tools\effects_page.py --html     # chỉ dựng lại trang (sửa catalog.json / page.html)
    .\.venv\Scripts\python.exe tools\effects_page.py --force    # làm lại toàn bộ media

Nguồn: assets/effects/catalog.json (tên gọi, nhóm, liều lượng, demo) + assets/scenes/<family>/scene.json (thẻ cảnh C01–C11,
tự đồng bộ) + assets/motion/<id>/motion.json (animation thương hiệu). Media sinh ra ở assets/effects/media/ (clip 360×640 cắt
từ video đã dựng, ảnh thu nhỏ). Khuôn trang: assets/effects/page.html. Thêm hiệu ứng = thêm mục vào catalog.json → chạy lại.
"""
import argparse
import base64
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image  # noqa: E402

from studio import motionlib, scenes  # noqa: E402

FX = ROOT / "assets" / "effects"
MEDIA = FX / "media"
OUT = ROOT / "hieu-ung.html"
THEMES = ["gdp_red", "phaledo_dark", "phaledo_warm"]
THEME_BRAND = {"gdp_red": "GIADUNGPLUS", "phaledo_dark": "PHALEDO", "phaledo_warm": "PHALEDO"}
CHAPTER_SAMPLE = {"GIADUNGPLUS": {"title": "Bước 2: Lắp đặt", "sub": "Lau sạch tường trước khi dán", "eyebrow": "Bước 2"},
                  "PHALEDO": {"title": "Thủy tinh và gỗ sồi", "sub": "Chất liệu an toàn cho căn bếp", "eyebrow": "Chương 02"}}
THUMB = (270, 480)


def rel(p: Path) -> str:
    return quote(p.resolve().relative_to(ROOT).as_posix())


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def all_demos(e: dict) -> list[dict]:
    out = [e["demo"]] if e.get("demo") else []
    out += [v["demo"] for v in e.get("variants", []) + e.get("demos", [])]
    return out


def clip_media(d: dict, sources: dict, force: bool) -> None:
    """Clip demo cắt từ video đã dựng (360×640, có tiếng) + ảnh thu nhỏ đúng giây 'thumb'."""
    src = ROOT / sources[d["src"]]["path"]
    key = f"{d['src']}_{d['t0']:05.2f}_{d['t1']:05.2f}".replace(".", "-")
    mp4, jpg = MEDIA / "clips" / f"{key}.mp4", MEDIA / "thumbs" / f"{key}.jpg"
    if force or not mp4.exists():
        ff("-ss", d["t0"], "-to", d["t1"], "-i", src, "-vf", "scale=360:640:flags=lanczos", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "80k", "-movflags", "+faststart", mp4)
        print("  clip", mp4.name)
    if force or not jpg.exists():
        ff("-ss", d.get("thumb", (d["t0"] + d["t1"]) / 2), "-i", src, "-frames:v", "1", "-vf", f"scale={THUMB[0]}:{THUMB[1]}:flags=lanczos",
           "-q:v", "4", jpg)
    d["mp4"], d["jpg"] = rel(mp4), rel(jpg)


def video_media(d: dict, force: bool) -> None:
    src = ROOT / d["path"]
    jpg = MEDIA / "thumbs" / f"video_{src.stem.replace(' ', '-')}.jpg"
    if force or not jpg.exists():
        ff("-ss", 1.2, "-i", src, "-frames:v", "1", "-vf", f"scale={THUMB[0]}:{THUMB[1]}:force_original_aspect_ratio=decrease,"
           f"pad={THUMB[0]}:{THUMB[1]}:(ow-iw)/2:(oh-ih)/2:color=0x191714", "-q:v", "4", jpg)
    d["mp4"], d["jpg"] = rel(src), rel(jpg)


def motion_media(d: dict, force: bool) -> None:
    a = motionlib.get(d["id"])
    spec = motionlib.spec_for(a, None, None, None)
    entry = a["dir"] / spec["entry"]
    jpg = MEDIA / "thumbs" / f"motion_{d['id']}.jpg"
    dur = float(spec.get("duration") or a.get("duration") or 3.0)
    if force or not jpg.exists():
        with motionlib.HtmlPage(entry, spec["params"], spec["canvas"]) as pg:
            dur = float(pg.info.get("duration") or dur)
            im = Image.open(io.BytesIO(pg.frame(dur * 0.72))).convert("RGBA")
        bg = Image.new("RGBA", im.size, (25, 23, 20, 255))
        bg.alpha_composite(im)
        bg.thumbnail((THUMB[0] * 2, THUMB[1]))
        bg.convert("RGB").save(jpg, quality=86)
        print("  motion", jpg.name)
    d.update(src=rel(entry) + "?" + "&".join(f"{k}={quote(str(v))}" for k, v in spec["params"].items()),
             canvas=spec["canvas"], duration=dur, jpg=rel(jpg), name=a.get("name") or d["id"])


def scene_info(e: dict) -> dict:
    """Hồ sơ thẻ cảnh từ scene.json (nguồn sự thật) → dữ liệu trang."""
    prof = scenes.load(e["scene"])
    entry = ROOT / "assets" / "scenes" / e["scene"] / "src" / f"{e['scene']}.html"
    sample = prof.get("sample") or CHAPTER_SAMPLE
    return {"purpose": prof.get("purpose"), "use": prof.get("use_when", []), "avoid": prof.get("avoid_when", []),
            "presets": {k: {"dur": v["dur"], "covers": v.get("covers", True), "note": v.get("note", ""), "default": v.get("default")}
                        for k, v in prof["presets"].items()},
            "preset_rule": prof.get("preset_rule") or prof.get("preset_auto"),
            "themes": {k: v.get("look", "") for k, v in prof["themes"].items()},
            "params": {k: {kk: vv for kk, vv in v.items() if kk in ("note", "required", "max_chars")} for k, v in prof.get("params", {}).items()},
            "examples": prof.get("examples", []), "sample": sample, "src": rel(entry), "motion_id": prof.get("motion_id"),
            "version": prof.get("version")}


def scene_thumbs(e: dict, info: dict, footage: Image.Image, force: bool) -> dict:
    """Ảnh thu nhỏ thẻ cảnh: 3 theme, preset standard (đè footage nếu không phủ khung), khung lúc nội dung hiện đủ."""
    out = {}
    entry = ROOT / "assets" / "scenes" / e["scene"] / "src" / f"{e['scene']}.html"
    for th in THEMES:
        jpg = MEDIA / "thumbs" / f"scene_{e['scene']}_{th}.jpg"
        out[th] = rel(jpg)
        if jpg.exists() and not force:
            continue
        params = {**info["sample"].get(THEME_BRAND[th], {}), "theme": th, "preset": "standard", "seed": 1}
        with motionlib.HtmlPage(entry, params, [1080, 1920]) as pg:
            qa = pg.page.evaluate("() => (window.SCENE_MOTION || {}).qa || {}")
            dur = float(pg.info.get("duration") or 3)
            t = qa.get("full_at") or qa.get("land") or dur * 0.55
            t = min(dur - 0.4, float(t) + 0.15)
            if e["scene"] == "problem-solution":
                t = dur - 0.6
            im = Image.open(io.BytesIO(pg.frame(t))).convert("RGBA")
        base = footage.copy()
        base.alpha_composite(im)
        base.convert("RGB").resize(THUMB, Image.LANCZOS).save(jpg, quality=86)
        print("  scene", jpg.name)
    return out


def build_media(cat: dict, force: bool) -> dict:
    for d in ("clips", "thumbs"):
        (MEDIA / d).mkdir(parents=True, exist_ok=True)
    footage_p = MEDIA / "footage.jpg"
    footage = Image.open(footage_p).convert("RGBA").resize((1080, 1920))
    for e in cat["effects"]:
        if e.get("scene"):
            e["status"] = "co-san"
            e["sceneinfo"] = scene_info(e)
            e["thumbs"] = scene_thumbs(e, e["sceneinfo"], footage, force)
        for d in all_demos(e):
            if d["kind"] == "clip":
                clip_media(d, cat["sources"], force)
            elif d["kind"] == "video":
                video_media(d, force)
            elif d["kind"] == "motion":
                motion_media(d, force)
    cat["footage"] = rel(footage_p)
    return cat


def font_face(name: str, path: Path, weight: str) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode()
    return (f'@font-face{{font-family:"{name}";src:url(data:font/woff2;base64,{b64}) format("woff2");'
            f'font-weight:{weight};font-style:normal;font-display:swap}}')


def build_html(cat: dict) -> None:
    fd = ROOT / "assets" / "font" / "AvetaStdCY"
    fonts = "\n".join([font_face("Averta Std CY", fd / "AvertaStdCY-Regular.woff2", "100 550"),
                       font_face("Averta Std CY", fd / "AvertaStdCY-Bold.woff2", "551 900")])
    story = json.loads((ROOT / "assets" / "scenes" / "stories.json").read_text(encoding="utf-8"))
    cat["stories"] = story["stories"]
    cat["family_names"] = story["families"]
    tpl = (FX / "page.html").read_text(encoding="utf-8")
    data = json.dumps(cat, ensure_ascii=False).replace("</", "<\\/")
    html = tpl.replace("/*__FONTS__*/", fonts).replace("/*__DATA__*/null", data)
    OUT.write_text(html, encoding="utf-8")
    n = {s: sum(1 for e in cat["effects"] if e.get("status") == s) for s in ("co-san", "y-tuong")}
    print(f"→ {OUT}  ({len(cat['effects'])} hiệu ứng: {n['co-san']} có sẵn · {n['y-tuong']} ý tưởng · {OUT.stat().st_size // 1024} KB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", action="store_true", help="không làm media mới (vẫn đọc media đã có)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    cat = json.loads((FX / "catalog.json").read_text(encoding="utf-8"))
    if a.html and not (MEDIA / "thumbs").exists():
        sys.exit("chưa có media — chạy không kèm --html trước")
    cat = build_media(cat, a.force)
    build_html(cat)


if __name__ == "__main__":
    main()
