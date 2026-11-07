r"""Render kiểm + ảnh preview cho MỘT Scene Family: mọi theme × preset qua Motion Engine (tất định, alpha, khung cuối
trong suốt) → assets/scenes/<family>/previews/<theme>-<preset>.jpg (6 mốc trên 3 nền: tối / sáng / footage giả).

    .\.venv\Scripts\python.exe tools\scene_previews.py chapter-card [--theme gdp_red] [--preset full]
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from studio import motionlib, scenes  # noqa: E402

SAMPLE = {  # chữ mẫu theo brand (preview, không phải nội dung video)
    "GIADUNGPLUS": {"title": "Bước 2: Lắp đặt", "sub": "Lau sạch tường trước khi dán", "eyebrow": "Bước 2"},
    "PHALEDO": {"title": "Thủy tinh và gỗ sồi", "sub": "Chất liệu an toàn cho căn bếp", "eyebrow": "Chương 02"},
}

ap = argparse.ArgumentParser()
ap.add_argument("family")
ap.add_argument("--theme", action="append")
ap.add_argument("--preset", action="append")
ap.add_argument("--sample", help="khoá chữ mẫu khác trong scene.json sample (vd receipt) → ảnh <theme>-<preset>-<khoá>.jpg")
a = ap.parse_args()
prof = scenes.load(a.family)
anim = motionlib.get(prof["motion_id"])
out = scenes.SCENES / a.family / "previews"
out.mkdir(exist_ok=True)
report = []
for theme, tcfg in prof["themes"].items():
    if a.theme and theme not in a.theme:
        continue
    for preset in prof["presets"]:
        if a.preset and preset not in a.preset:
            continue
        sample = prof.get("sample") or SAMPLE   # chữ mẫu riêng của family (scene.json "sample") nếu có
        # chữ mẫu: theo theme (family giao diện C13+ — mỗi theme thử 1 thương hiệu) → theo brand của theme → GDP
        smp = (sample.get(a.sample) if a.sample else None) or sample.get(theme) or sample.get(tcfg.get("brand")) or sample["GIADUNGPLUS"]
        params = {"theme": theme, "preset": preset, **smp, "seed": 1}
        t0 = time.time()
        try:
            info = motionlib.render(anim, params=params)
        except motionlib.MotionError as exc:
            print(f"✗ {theme} {preset}: {exc}")
            report.append({"theme": theme, "preset": preset, "ok": False, "error": str(exc)[:300]})
            continue
        chk = info["check"]
        shutil.copyfile(Path(info["dir"]) / "sheet.jpg", out / f"{theme}-{preset}{'-' + a.sample if a.sample else ''}.jpg")
        shutil.rmtree(info["dir"], ignore_errors=True)   # chữ mẫu → không video nào dùng lại cache này (ProRes ~90MB/giây)
        print(f"✓ {theme:13s} {preset:9s} {info['duration']:.2f}s {info['frames']} khung · khung đầu α{chk['first_alpha_max']}"
              f" · khung cuối α{chk['last_alpha_max']} · {time.time() - t0:.0f}s" + (f" · ⚠ {'; '.join(chk['warn'])}" if chk["warn"] else ""))
        report.append({"theme": theme + (f"/{a.sample}" if a.sample else ""), "preset": preset, "ok": True, "duration": info["duration"], "frames": info["frames"],
                       "first_alpha": chk["first_alpha_max"], "last_alpha": chk["last_alpha_max"], "warn": chk["warn"]})
rp = out / "_report.json"   # gộp với lần chạy trước (chạy riêng --theme/--preset không làm mất dòng khác)
old = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else []
done = {(r["theme"], r["preset"]) for r in report}
merged = [r for r in old if (r["theme"], r["preset"]) not in done] + report
rp.write_text(json.dumps(sorted(merged, key=lambda r: (r["theme"], r["preset"])), ensure_ascii=False, indent=1),
              encoding="utf-8")
print(f"→ {out}")
