"""Scene Library (assets/scenes/<family>/scene.json) — hồ sơ cảnh dựng sẵn: theme, preset thời lượng, tham số, SFX.

cutlib.graphic() đọc hồ sơ để: chọn THEME theo shop của job, chọn PRESET theo thời lượng, chuyển cảnh vào mặc định của
theme, giải `photo="lib:<id>"` thành ảnh thật (file:// + hash để cache đúng). build.py đọc `sfx` để chèn tiếng hiệu ứng.
"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from studio import config

SCENES = config.ROOT / "assets" / "scenes"


class SceneError(ValueError):
    pass


def load(family: str) -> dict:
    p = SCENES / family / "scene.json"
    if not p.exists():
        raise SceneError(f"không có scene '{family}' ({p})")
    return {**json.loads(p.read_text(encoding="utf-8")), "dir": str(p.parent)}


def all_profiles() -> list[dict]:
    return [load(p.parent.name) for p in sorted(SCENES.glob("*/scene.json"))]


def for_motion(motion_id: str) -> dict | None:
    """Hồ sơ scene có motion_id này (None = animation thường, không thuộc Scene Library)."""
    return next((p for p in all_profiles() if p.get("motion_id") == motion_id), None)


def brand_of(shop: str | None) -> str | None:
    if not shop:
        return None
    from studio.templates import shop_profile
    return shop_profile(shop).get("brand")


def accent_of(shop: str | None) -> str | None:
    """Màu nhấn của shop (shop.json palette.accent) — family mới (brand_param) tô nhấn theo thương hiệu."""
    if not shop:
        return None
    from studio.templates import shop_profile
    try:
        return (shop_profile(shop).get("palette") or {}).get("accent")
    except FileNotFoundError:
        return None


def theme_for(prof: dict, shop: str | None, job_theme: str | None) -> str:
    if job_theme:
        if job_theme not in prof["themes"]:
            raise SceneError(f"{prof['id']}: không có theme '{job_theme}' (có: {', '.join(prof['themes'])})")
        return job_theme
    m = prof.get("theme_by_brand", {})
    return m.get(brand_of(shop) or "", m.get("*", next(iter(prof["themes"]))))


def preset_for(prof: dict, dur: float) -> str:
    for lim, name in prof.get("preset_auto", []):
        if dur < lim:
            return name
    return list(prof["presets"])[-1]


def photo_param(ref: str) -> dict:
    """'lib:<id>' → {photo: file:///…, photo_v: hash nội dung} (đổi ảnh = render lại); tên asset/none giữ nguyên."""
    if not ref.startswith("lib:"):
        return {"photo": ref}
    from studio import library
    path, aid = library.resolve(ref)
    h = hashlib.sha1(path.read_bytes()).hexdigest()[:10]
    return {"photo": Path(path).resolve().as_uri(), "photo_v": h, "_photo_id": aid,
            "_photo_ai": (library.get(aid) or {}).get("engine") not in (None, "photo")}


def text_qa(anim: dict, params: dict) -> dict:
    """Mở trang scene với đúng tham số, đọc `SCENE_MOTION.qa` (template tự báo chữ tràn / cỡ chữ) — ~3s, không chụp."""
    from studio import motionlib
    spec = motionlib.spec_for(anim, params=params)
    with motionlib.HtmlPage(anim["dir"] / spec["entry"], spec["params"], spec["canvas"]) as pg:
        qa = pg.page.evaluate("() => (window.SCENE_MOTION || {}).qa || null") or {}
        qa["errors"] = pg.errors
    return qa


@lru_cache(maxsize=64)
def sfx_peak(path: str) -> float:
    """Giây từ đầu file tới ĐỈNH âm (cửa sổ RMS 10ms to nhất). Tiếng 'chạm' (click, ting) đỉnh ≈ 0; tiếng 'vuốt'
    (whoosh, swell) đỉnh trễ 0,1–0,5s."""
    import subprocess

    import numpy as np
    raw = subprocess.run([config.FFMPEG, "-v", "error", "-i", path, "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    w = 480
    if len(a) < w:
        return 0.0
    rms = (a[:len(a) // w * w].reshape(-1, w) ** 2).mean(1)
    return round(float(rms.argmax()) * w / 48000, 3)


def _sfx_at(s: dict, f: Path, at: float) -> float:
    """Mặc định tiếng bắt đầu ĐÚNG mốc (tiếng vuốt đi cùng chuyển động vào; tiếng chạm đỉnh ≈ 0 nên cũng trúng).
    Tiếng có đỉnh trễ mà phải rơi đúng lúc 'chạm' → khai `"align": "peak"` trong scene.json: lùi cho ĐỈNH trúng mốc."""
    return max(0.0, at - sfx_peak(str(f))) if s.get("align") == "peak" else at


def sfx_events(prof: dict, g: dict) -> list[tuple[Path, float, float]]:
    """[(file, gain_db, giây)] cho 1 đồ hoạ đã giải: tiếng lúc vào ('enter'), lúc từ đầu tiên vào ('word', bảng word_at)
    và lúc 'chạm' ('land': nhãn rơi xong / chữ hiện đủ — lấy mốc thật template báo `qa.land` nếu có, không thì bảng
    land_at). `presets` = chỉ chèn ở các preset đó. `"align": "peak"` = căn ĐỈNH âm vào mốc (xem _sfx_at)."""
    th, pr = g["params"].get("theme"), g["params"].get("preset")
    land = (g.get("text_qa") or {}).get("land")
    out = []
    for s in prof.get("sfx", {}).get(th, []):
        if s.get("presets") and pr not in s["presets"]:
            continue
        if s["at"] == "item":   # mỗi nhãn con vào một tiếng (tiêu đề ghim)
            try:
                its = json.loads(g["params"].get("items") or "[]") if pr != "micro" else []
            except ValueError:
                its = []
            f = config.ROOT / "assets" / "sfx" / s["file"]
            out += [(f, float(s.get("gain_db", -24)), round(_sfx_at(s, f, g["t0"] + float(it["t"])), 3)) for it in its
                    if f.exists() and g["t0"] + float(it["t"]) < g["t1"]]
            continue
        pt = g["params"].get(f"{s['at']}_t")   # mốc theo tham số giờ (switch_t, win_t, figure_t) hoặc trang tự báo (qa)
        if pt is None:
            pt = (g.get("text_qa") or {}).get(f"{s['at']}_t")
        if s["at"] == "figure" and not g["params"].get("figure"):
            continue
        if s["at"] not in ("enter", "land", "word", "item") and pt is not None:
            off = float(pt)
        elif s["at"] == "win":   # A vs B không chốt → không tiếng
            continue
        elif s["at"] == "figure":
            off = float(land or 0.57) + 0.5
        elif s["at"] == "enter":
            off = 0.0
        elif s["at"] == "land" and land is not None:
            off = float(land)
        else:
            off = prof.get(f"{s['at']}_at", {}).get(th, {}).get(pr, 0.5)
        at = g["t0"] + off
        f = config.ROOT / "assets" / "sfx" / s["file"]
        if f.exists() and at < g["t1"]:
            out.append((f, float(s.get("gain_db", -18)), round(_sfx_at(s, f, at), 3)))
    return out
