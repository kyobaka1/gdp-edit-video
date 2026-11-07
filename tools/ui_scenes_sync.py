r"""Scene "giao diện" C13+ (scene.json có "uikit": true): chép UI Kit chung + font vào src/, nhập (lại) vào Motion
Engine với motion.json chuẩn Scene Library. Sửa assets/scenes/_uikit/uikit.js hoặc template xong thì chạy lại.

    .\.venv\Scripts\python.exe tools\ui_scenes_sync.py [list-motion ...]     # rồi: tools\scene_previews.py <family>
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from studio import config, motionlib, scenes  # noqa: E402

KIT = scenes.SCENES / "_uikit" / "uikit.js"
FONTS = [config.ROOT / "assets" / "fonts" / "UTM Avo" / "UTM_AvoBold.ttf", config.ROOT / "assets" / "fonts" / "UTM Avo" / "UTM_Avo.ttf",
         *(config.ROOT / "assets" / "fonts" / "Averta" / f for f in ("Averta-Bold.otf", "Averta-Regular.otf", "Averta-Light.otf"))]


def sync(family: str) -> None:
    prof = scenes.load(family)
    src = Path(prof["dir"]) / "src"
    shutil.copy2(KIT, src / "uikit.js")
    (src / "fonts").mkdir(exist_ok=True)
    for f in FONTS:
        shutil.copy2(f, src / "fonts" / f.name)
    entry = src / f"{family}.html"
    res = motionlib.import_source(entry, anim_id=prof["motion_id"], brands=["*"], roles=["scene", family.replace("-", "_")],
                                  name=f"Scene {prof['code']} {prof['name'].split(' — ')[0]}", test_render=False)
    mdir = Path(res["anim"]["dir"]) if isinstance(res.get("anim"), dict) and res["anim"].get("dir") else \
        motionlib.LIB / prof["motion_id"]
    if (src / "assets").is_dir():   # ảnh mẫu tham chiếu trong JS (Motion Engine chỉ dò url()/src=) → chép nguyên thư mục
        shutil.copytree(src / "assets", mdir / "src" / "assets", dirs_exist_ok=True)
    mj = mdir / "motion.json"
    meta = json.loads(mj.read_text(encoding="utf-8"))
    first_theme = next(iter(prof["themes"]))
    meta.update({
        "params": {"theme": first_theme, "preset": "standard", "brand": "GIADUNGPLUS", "accent": "",
                   **{k: "" for k in prof.get("params", {}) if k not in ("theme", "preset", "brand", "accent")}, "seed": 1},
        "placement": {"scale": 1, "x": "center", "y": "center", "margin_x_pct": 0, "margin_y_pct": 0},
        "replaces": [], "ends_transparent": True, "opaque": True, "z": "top", "variants": {},
        "scene": family, "tags": sorted(set(meta.get("tags", []) + ["scene", "uikit"] + prof.get("tags", []))),
        "notes": f"Scene Library {prof['code']} {prof['name']} v{prof['version']} — hồ sơ assets/scenes/{family}/scene.json. "
                 f"UI Kit chung (assets/scenes/_uikit). Dùng: {prof.get('examples', [''])[0]}",
    })
    if "items" in meta["params"]:
        meta["params"]["items"] = "[]"
    mj.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    a = motionlib.get(prof["motion_id"])
    print(f"✓ {family}: {prof['motion_id']} v{meta['version']}" + (f" · ⚠ {'; '.join(a['problems'])}" if a["problems"] else ""))


if __name__ == "__main__":
    fams = sys.argv[1:] or [p["id"] for p in scenes.all_profiles() if p.get("uikit")]
    for fam in fams:
        sync(fam)
