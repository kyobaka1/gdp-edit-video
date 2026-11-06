"""Scene Library (assets/scenes/<family>/scene.json) — hồ sơ cảnh dựng sẵn: theme, preset thời lượng, tham số, SFX.

cutlib.graphic() đọc hồ sơ để: chọn THEME theo shop của job, chọn PRESET theo thời lượng, chuyển cảnh vào mặc định của
theme, giải `photo="lib:<id>"` thành ảnh thật (file:// + hash để cache đúng). build.py đọc `sfx` để chèn tiếng hiệu ứng.
"""

import hashlib
import json
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


def sfx_events(prof: dict, g: dict) -> list[tuple[Path, float, float]]:
    """[(file, gain_db, giây)] cho 1 đồ hoạ đã giải: tiếng lúc vào ('enter'), lúc từ đầu tiên vào ('word', bảng word_at)
    và lúc 'chạm' ('land': nhãn rơi xong / chữ hiện đủ — lấy mốc thật template báo `qa.land` nếu có, không thì bảng
    land_at). `presets` = chỉ chèn ở các preset đó."""
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
            out += [(f, float(s.get("gain_db", -24)), round(g["t0"] + float(it["t"]), 3)) for it in its
                    if f.exists() and g["t0"] + float(it["t"]) < g["t1"]]
            continue
        if s["at"] in ("win", "figure"):   # lúc chốt (A vs B win_t) / số liệu đập vào (Evidence figure_t)
            pt = g["params"].get(f"{s['at']}_t")
            if (s["at"] == "win" and pt is None) or (s["at"] == "figure" and not g["params"].get("figure")):
                continue
            off = float(pt) if pt is not None else float(land or 0.57) + 0.5
        elif s["at"] == "enter":
            off = 0.0
        elif s["at"] == "land" and land is not None:
            off = float(land)
        else:
            off = prof.get(f"{s['at']}_at", {}).get(th, {}).get(pr, 0.5)
        at = g["t0"] + off
        f = config.ROOT / "assets" / "sfx" / s["file"]
        if f.exists() and at < g["t1"]:
            out.append((f, float(s.get("gain_db", -18)), round(at, 3)))
    return out
