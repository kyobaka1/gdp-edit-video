"""Kiểm thử Motion Engine (animation thương hiệu, Sếp 23/10) — 7 case:

  A  Job cũ (không edl.motion) render ra Y HỆT code trước khi có motion (git HEAD ở worktree tạm): filter + khung hình.
  B  Clip alpha ghép lên nền tối / sáng / footage thật bằng ffmpeg: ngoài vật thể = nền gốc (không nền đen/trắng),
     trong vật thể đúng màu, chi tiết TRẮNG của logo còn nguyên, alpha giải mã khớp bản render.
  C  Tách brand: shop LTENG không thấy animation GDP/PHALEDO; chèn sai brand → lỗi; shop kế thừa cấu hình
     (phaledo ← phaledo_official); override riêng shop (lteng_hcm rail-glide rtl) có hiệu lực.
  D  Xung đột: job GDP AUTO → brand reveal thay logo tĩnh (không còn logo.png), watermark động thay chữ (không còn
     watermark.png), không chồng ô chữ > 4%, QA animation đạt, thời lượng + tiếng không đổi.
  E  Phiên bản: import đè → v2, cache khác; job đã chốt dùng bản v1 (cache, rồi _versions khi xoá cache); update → v2.
  F  Mở rộng: animation HOÀN TOÀN MỚI (không thuộc 10 cái có sẵn) import bằng CLI, không sửa Python → có trong list,
     render, chèn vào video (thấy trong khung, hết giờ thì sạch overlay).
  G  Lỗi: không setTime · thiếu asset · nền đục · khung không tái lập · gọi CDN · MP4 không alpha · id không có ·
     animation đang tắt → đều báo rõ, không lọt vào video.
  V2 (Motion Director V2):
  H  Reveal đầu video → logo thường trực ẩn đúng lúc reveal, TIẾP QUẢN tới hết video chính (đo điểm ảnh vùng logo).
  I  Reveal giữa video → logo có từ đầu, ẩn đúng đoạn, hiện lại.
  J  Không có reveal → logo hiện suốt, không khoảng ẩn.
  K  Watermark: intro → (dim) → giữ MỘT chỗ; intro rõ, giữ mờ; khung giữ hợp lệ; PHALEDO (giữ tại 2,45s) có pha mờ.
  L  Watermark xuất hiện → chìm dần → đổi chỗ: mặc định TRƯỢT êm mỗi period (như cũ, chỉ sau khi chìm xong); kiểu
     fade: chỗ cũ mờ ra, chỗ mới hiện; tắt relocate → 1 chỗ.
  M  Xung đột: animation không thay logo không đè logo góc; logo chỉ ẩn trong animation thay logo; watermark xa logo
     góc; accent né intro watermark; QA bắt animation chèn tay đè logo.
  N  AUTO đa vai trò: GDP chọn reveal + accent trong budget; PHALEDO không ép (có lý do); bảng budget.
  O  Cỡ/vị trí theo tỉ lệ khung 9:16 / 3:4 / 16:9: logo thường trực + reveal đúng % bề rộng, lề trên 3% chiều cao.

  .venv\\Scripts\\python.exe tools\\test_motion.py [A B …] [--keep]
Job thử ở thư mục tạm; animation thử ở thư viện tạm (không đụng assets/motion thật ngoài đọc + cache)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studio import config, media, motiondirector, render  # noqa: E402
from studio import motionlib as ml  # noqa: E402

PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
TMP = Path(tempfile.mkdtemp(prefix="gdp_motion_test_"))
REAL_LIB = ml.LIB
TEST_LIB = TMP / "motionlib"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "FFMPEG_PATH": config.FFMPEG or "", "FFPROBE_PATH": config.FFPROBE or ""}
GDP_JOB, LTENG_VN_JOB, LTENG_HCM_JOB = "gdp-moc-treo-cua-01", "lteng-vn-moc-treo-cua-01", "lteng-hcm-moc-treo-cua-01"
RESULTS: list[tuple[str, bool, str]] = []

PULSE = """<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8"><title>Test Pulse Ring</title>
<style>html,body{margin:0;padding:0;background:transparent;overflow:hidden}#c{display:block}</style></head><body>
<canvas id="c" width="1080" height="1920"></canvas>
<script>
const W = 1080, H = 1920, D = 2.0, q = new URLSearchParams(location.search);
const color = q.get('color') || '%COLOR%';
const ctx = document.getElementById('c').getContext('2d');
function draw(t) {
  ctx.clearRect(0, 0, W, H);
  const p = Math.min(1, t / D), r = 60 + 220 * p, a = p < 0.8 ? 1 : Math.max(0, 1 - (p - 0.8) / 0.2);
  ctx.globalAlpha = a; ctx.lineWidth = 28; ctx.strokeStyle = color;
  ctx.beginPath(); ctx.arc(W / 2, H / 2, r, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(W / 2, H / 2, 40, 0, Math.PI * 2); ctx.fill();
  ctx.globalAlpha = 1;%EXTRA%
}
window.setTime = (t) => draw(Math.max(0, Math.min(D, +t || 0)));
window.TEST_MOTION = { name: 'Test Pulse Ring', duration: D, width: W, height: H, ready: Promise.resolve(), setTime: window.setTime };
draw(0);
</script></body></html>
"""


def check(case: str, ok: bool, msg: str) -> None:
    RESULTS.append((case, bool(ok), msg))
    print(f"  [{'ĐẠT' if ok else 'LỖI'}] {case}: {msg}")


def make_job(src: str, name: str, patch: dict | None = None, drop: tuple = ()) -> Path:
    s, d = config.JOBS / src, TMP / name
    d.mkdir(parents=True, exist_ok=True)
    for f in ("source.mp4", "meta.json", "edl.json", "narration.json", "narration.wav", "music.mp3"):
        if (s / f).exists():
            shutil.copy2(s / f, d / f)
    edl = json.loads((d / "edl.json").read_text(encoding="utf-8"))
    for k in drop:
        edl.pop(k, None)
    edl.update(patch or {})
    (d / "edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=2), encoding="utf-8")
    return d


def frame(video: Path, t: float) -> np.ndarray:
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"không đọc được khung {t}s của {video}")
    return fr.astype(np.int16)


def rdiff(a: np.ndarray, b: np.ndarray, rect) -> float:
    x, y, w, h = rect
    return float(np.abs(a[y:y + h, x:x + w] - b[y:y + h, x:x + w]).mean())


def write_html(folder: Path, name: str, color: str = "#2a9d8f", extra: str = "", head: str = "") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / name
    p.write_text(PULSE.replace("%COLOR%", color).replace("%EXTRA%", extra).replace("<title>", head + "<title>"),
                 encoding="utf-8")
    return p


# ───────────────────────────── A ─────────────────────────────
def case_A() -> None:
    old = TMP / "oldstudio"
    subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--detach", str(old), "HEAD"], check=True,
                   capture_output=True)
    try:
        jo, jn = make_job(GDP_JOB, "A_old", drop=("motion",)), make_job(GDP_JOB, "A_new", drop=("motion",))
        code = "import sys; from pathlib import Path; from studio import render; render.run(Path(sys.argv[1]))"
        for cwd, job in ((old, jo), (ROOT, jn)):
            r = subprocess.run([PY, "-c", code, str(job)], cwd=cwd, env=ENV, capture_output=True, text=True,
                               encoding="utf-8")
            if r.returncode:
                raise RuntimeError(f"render {job.name} lỗi: {r.stderr[-600:]}")
        fo = (jo / "filter.txt").read_text(encoding="utf-8").replace(str(jo), "JOB")
        fn = (jn / "filter.txt").read_text(encoding="utf-8").replace(str(jn), "JOB")
        check("A", fo == fn, "filter_complex giống hệt code cũ (logo + watermark chữ + ô chữ + outro)")
        check("A", (jo / "watermark.png").read_bytes() == (jn / "watermark.png").read_bytes()
              and (jo / "logo.png").read_bytes() == (jn / "logo.png").read_bytes(), "logo.png + watermark.png giống hệt")
        check("A", not (jn / "motion_plan.json").exists(), "không khai edl.motion → không có motion_plan.json")
        meta = json.loads((jn / "meta.json").read_text(encoding="utf-8"))
        diffs = [float(np.abs(frame(jo / "preview.mp4", t) - frame(jn / "preview.mp4", t)).max())
                 for t in np.linspace(0.3, meta["duration"] + 2.5, 8)]
        check("A", max(diffs) == 0, f"8 khung (cả outro) lệch điểm ảnh tối đa {max(diffs)}")
        lo, ln = render.measure_lufs(jo / "preview.mp4"), render.measure_lufs(jn / "preview.mp4")
        check("A", lo == ln, f"độ to {lo} vs {ln} LUFS")
    finally:
        subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(old)], capture_output=True)


# ───────────────────────────── B ─────────────────────────────
def case_B() -> None:
    ml.LIB = REAL_LIB
    a = ml.get("gdp-orbit-settle")
    info = ml.render(a)
    d = Path(info["dir"])
    peak = info["check"]["peak_frame"]
    dec = TMP / "B_peak_dec.png"
    media.run([config.FFMPEG, "-y", "-v", "error", "-i", info["mov"], "-vf", f"select=eq(n\\,{peak}),format=rgba",
               "-frames:v", "1", str(dec)])
    ref = cv2.imread(str(d / "peak.png"), cv2.IMREAD_UNCHANGED).astype(np.int16)
    got = cv2.imread(str(dec), cv2.IMREAD_UNCHANGED).astype(np.int16)
    solid = ref[..., 3] >= 250
    check("B", int(np.abs(ref[..., 3] - got[..., 3]).max()) <= 2, f"alpha giải mã ProRes khớp bản render (lệch "
          f"{int(np.abs(ref[..., 3] - got[..., 3]).max())})")
    check("B", float(np.abs(ref[..., :3] - got[..., :3])[solid].max()) <= 8,
          f"màu vùng đặc lệch tối đa {float(np.abs(ref[..., :3] - got[..., :3])[solid].max())} (ProRes 10-bit)")
    whites = int(((ref[..., :3].min(-1) > 235) & solid).sum())
    meta = json.loads((config.JOBS / GDP_JOB / "meta.json").read_text(encoding="utf-8"))
    foot = TMP / "B_foot.png"
    media.extract_frame(config.JOBS / GDP_JOB / "source.mp4", 5.0, foot)
    w, h = info["bbox"][2], info["bbox"][3]
    t = peak / info["fps"]
    for name, src in (("tối", f"color=c=0x141414:s={w}x{h}"), ("sáng", f"color=c=0xEDEDED:s={w}x{h}"),
                      ("footage", None)):
        out = TMP / f"B_comp_{['dark', 'light', 'footage'][['tối', 'sáng', 'footage'].index(name)]}.png"  # cv2 không đọc đường dẫn có dấu
        fps = info["fps"]
        bg_in = (["-f", "lavfi", "-i", src + f":r={fps}:d={info['duration']}"] if src else
                 ["-loop", "1", "-framerate", f"{fps}", "-t", str(info["duration"]), "-i", str(foot)])
        scale = "" if src else f"scale={w}:{h},"
        media.run([config.FFMPEG, "-y", "-v", "error", *bg_in, "-i", info["mov"], "-filter_complex",
                   f"[0:v]{scale}format=rgb24[b];[1:v]format=rgba[m];[b][m]overlay=0:0:format=auto,format=rgb24,"
                   f"select='gte(t\\,{t - 0.5 / fps:.4f})'", "-frames:v", "1", str(out)])
        comp = cv2.imread(str(out)).astype(np.int16)
        if src:
            bgc = np.array([0x14] * 3 if name == "tối" else [0xED] * 3)
        else:  # nền tham chiếu = cùng khung footage, cùng bộ co giãn ffmpeg, KHÔNG ghép
            ref_bg = TMP / "B_bg_footage.png"
            media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(foot), "-vf", f"scale={w}:{h},format=rgb24",
                       "-frames:v", "1", str(ref_bg)])
            bgc = cv2.imread(str(ref_bg)).astype(np.int16)
        clear = got[..., 3] == 0
        bg_err = float(np.abs(comp - bgc)[clear].max()) if clear.any() else 0
        ink = float(np.abs(comp[solid] - got[..., :3][solid]).max())  # cv2 đọc BGR cả hai → so trực tiếp
        keep_white = int(((comp.min(-1) > 225) & solid & (ref[..., :3].min(-1) > 235)).sum())
        check("B", bg_err <= 3 and ink <= 10 and keep_white >= 0.97 * whites,
              f"ghép nền {name}: ngoài vật thể lệch nền {bg_err} (không nền đen/trắng thừa) · vật thể lệch {ink} · "
              f"giữ {keep_white}/{whites} điểm trắng của logo")
    check("B", (d / "sheet.jpg").exists(), f"ảnh soát 3 nền: {d / 'sheet.jpg'} (video {meta['width']}x{meta['height']})")


# ───────────────────────────── C ─────────────────────────────
def case_C() -> None:
    ml.LIB = REAL_LIB
    for shop, brand in (("lteng_vn", "LTENG"), ("lteng_hcm", "LTENG"), ("giadungplus_official", "GIADUNGPLUS"),
                        ("phaledo", "PHALEDO")):
        cat = ml.catalog(shop)
        wrong = [a["id"] for a in cat if brand not in a["brands"] and "*" not in a["brands"]]
        check("C", cat and not wrong, f"{shop}: {len(cat)} animation, đều brand {brand} (sai: {wrong or 'không'})")
    check("C", motiondirector.shop_motion("phaledo") == motiondirector.shop_motion("phaledo_official"),
          "shop phaledo kế thừa cấu hình motion của phaledo_official (templates_from)")
    job = make_job(LTENG_VN_JOB, "C_lteng_vn")
    edl = json.loads((job / "edl.json").read_text(encoding="utf-8"))
    meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    edl["motion"] = {"mode": "manual", "items": [{"id": "gdp-roll-smile", "start": 2}]}
    try:
        motiondirector.plan(job, edl, meta, [])
        check("C", False, "chèn animation GDP vào job LTENG phải báo lỗi")
    except motiondirector.MotionPlanError as exc:
        check("C", "KHÔNG dùng" in str(exc), f"chèn sai brand bị chặn: {str(exc)[:90]}…")
    params = {}
    for src, shop in ((LTENG_VN_JOB, "lteng_vn"), (LTENG_HCM_JOB, "lteng_hcm")):
        j = make_job(src, f"C_{shop}_rail")
        e = json.loads((j / "edl.json").read_text(encoding="utf-8"))
        e["motion"] = {"mode": "manual", "watermark": False, "items": [{"id": "lteng-rail-glide", "start": 2, "variant": "on_dark"}]}
        p = motiondirector.plan(j, e, meta, [])
        params[shop] = p["items"][0]["params"].get("direction")
    check("C", params == {"lteng_vn": "ltr", "lteng_hcm": "rtl"},
          f"cùng animation lteng-rail-glide, override riêng shop: {params}")
    # AUTO cho LTENG chỉ chọn trong thư viện LTENG
    e = dict(edl, motion={"mode": "auto"})
    p = motiondirector.plan(job, e, meta, render.label_boxes(job, e, meta))
    ids = [it["id"] for it in p["items"]] + ([p["watermark"]["id"]] if p["watermark"] else [])
    check("C", all(ml.get(i)["brands"] == ["LTENG"] for i in ids), f"AUTO job LTENG VN chọn: {ids or 'không chèn'}")


# ───────────────────────────── D ─────────────────────────────
def case_D() -> None:
    ml.LIB = REAL_LIB
    job = make_job(GDP_JOB, "D_gdp_auto", {"motion": {"mode": "auto"}})
    render.run(job)
    mp = json.loads((job / "motion_plan.json").read_text(encoding="utf-8"))
    layers = json.loads((job / "layers.json").read_text(encoding="utf-8"))
    reveal = [it for it in mp["items"] if "logo" in it["replaces"]]
    print(f"    AUTO chọn: {[(it['id'], it['start'], it['reason']) for it in mp['items']]} · notes {mp['notes']}")
    print(f"    lớp đã ghép: {layers}")
    check("D", layers["logo"] and layers["logo_mode"] == "persistent",
          f"logo THƯỜNG TRỰC có trong bản dựng ({layers['logo_rect']}) — V2 không tắt logo cả video")
    if reveal:
        r = reveal[0]
        check("D", all(r["start"] <= a and b <= r["end"] for a, b in layers["logo_hidden"]) and layers["logo_hidden"],
              f"logo chỉ ẩn {layers['logo_hidden']} trong lúc {r['id']} chạy ({r['start']}–{r['end']}s)")
    else:
        check("D", not layers["logo_hidden"], "không có brand reveal → logo hiện suốt")
    filt = (job / "filter.txt").read_text(encoding="utf-8")
    order = [filt.find(s) for s in ("[vwm]", "[vm", "[v1]", "[vlogo]")]
    check("D", all(o >= 0 for o in order) and order == sorted(order),
          "thứ tự lớp: watermark → animation (dưới chữ) → ô chữ → logo thường trực")
    check("D", mp["watermark"] and layers["watermark"] == f"motion:{mp['watermark']['id']}",
          f"watermark động {mp['watermark'] and mp['watermark']['id']} thay chữ — đúng 1 watermark ({layers['watermark']})")
    check("D", layers["outro"] and layers["motion"] == [it["id"] for it in mp["items"]],
          "outro vẫn nối; animation trong bản dựng khớp kế hoạch")
    check("D", all(it["overlap"] <= motiondirector.MAX_OVERLAP for it in mp["items"]),
          f"chồng ô chữ: {[it['overlap'] for it in mp['items']]} (≤ {motiondirector.MAX_OVERLAP})")
    meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    edl = json.loads((job / "edl.json").read_text(encoding="utf-8"))
    from studio import outro
    q = motiondirector.qa(job, job / "preview.mp4", outro.total_duration(edl, meta))
    check("D", q["ok"], f"QA animation: {q['problems'] or 'đạt'} · {q['info'] or ''}")
    for it in reveal:  # thấy animation trong lúc chạy (so với nguồn)
        src, out = job / "source.mp4", job / "preview.mp4"
        t = (it["start"] + it["end"]) / 2
        k = 960 / meta["height"]
        rect = [round(v * k) for v in (it["x"], it["y"], it["w"], it["h"])]
        a, b = frame(src, t), frame(out, t)
        if a.shape != b.shape:
            a = cv2.resize(a.astype(np.uint8), (b.shape[1], b.shape[0])).astype(np.int16)
        check("D", rdiff(a, b, rect) > 8, f"{it['id']} hiện trên video lúc {t:.1f}s (lệch vùng {rdiff(a, b, rect):.1f})")


# ───────────────────────────── E ─────────────────────────────
def case_E() -> None:
    ml.LIB = TEST_LIB
    src = write_html(TMP / "E_src", "zz-pulse.html", "#2a9d8f")
    r1 = ml.import_source(src, anim_id="zz-pulse", brands=["GIADUNGPLUS"], roles=["accent"])
    h1, k1 = r1["info"]["src_hash"], r1["info"]["key"]
    job = make_job(GDP_JOB, "E_job")
    edl = json.loads((job / "edl.json").read_text(encoding="utf-8"))
    meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    edl["motion"] = {"mode": "manual", "watermark": False, "items": [{"id": "zz-pulse", "start": 3}]}
    p1 = motiondirector.plan(job, edl, meta, [])
    write_html(TMP / "E_src", "zz-pulse.html", "#e76f51")  # Sếp sửa animation ở Claude Design → import lại
    r2 = ml.import_source(src, anim_id="zz-pulse", brands=["GIADUNGPLUS"], roles=["accent"])
    h2, k2 = r2["info"]["src_hash"], r2["info"]["key"]
    check("E", r2["anim"]["version"] == 2 and r2["archived"] and h1 != h2 and k1 != k2,
          f"import đè → v2, bản v1 cất {r2['archived'].name}, hash {h1[:8]}→{h2[:8]}, cache key đổi")
    p2 = motiondirector.plan(job, edl, meta, [])
    check("E", p2["items"][0]["src_hash"] == h1 and p1["items"][0]["key"] == p2["items"][0]["key"],
          f"job đã chốt giữ bản v1 ({p2['notes'][:1]})")
    shutil.rmtree(Path(p1["items"][0]["mov"]).parent)  # mất cache bản cũ → render lại từ _versions
    p3 = motiondirector.plan(job, edl, meta, [])
    check("E", p3["items"][0]["src_hash"] == h1 and Path(p3["items"][0]["mov"]).exists(),
          f"xoá cache v1 → render lại từ _versions ({p3['notes'][:1]})")
    edl["motion"]["update"] = True
    p4 = motiondirector.plan(job, edl, meta, [])
    check("E", p4["items"][0]["src_hash"] == h2, "edl.motion.update=true → dùng bản v2")
    ml.use_version("zz-pulse", 1)
    check("E", ml.source_hash(ml.get("zz-pulse")) == h1, "vs.py motion use zz-pulse 1 → quay về bản v1")


# ───────────────────────────── F ─────────────────────────────
def case_F() -> None:
    lib = TMP / "F_lib"
    env = {**ENV, "GDP_MOTION_LIB": str(lib)}
    src = write_html(TMP / "F_download", "brand-new-sparkle.html", "#8e44ad")

    def vs(*args):
        r = subprocess.run([PY, "vs.py", "motion", *args], cwd=ROOT, env=env, capture_output=True, text=True,
                           encoding="utf-8")
        return r.returncode, r.stdout + r.stderr

    code, out = vs("scan", str(src.parent))
    check("F", code == 0 and "✓ brand-new-sparkle.html" in out, "scan nhận ra nguồn render được")
    code, out = vs("import", str(src), "--id", "zz-sparkle", "--brand", "GIADUNGPLUS", "--role", "sparkle_accent")
    check("F", code == 0 and "✓ alpha" in out, f"import CLI + render alpha (vai trò mới 'sparkle_accent', không sửa code)")
    code, out = vs("list", "--shop", "giadungplus_official")
    check("F", "zz-sparkle" in out, "có trong danh sách shop GDP")
    code, out = vs("list", "--shop", "lteng_vn")
    check("F", "zz-sparkle" not in out, "không có trong danh sách shop LTENG")
    ml.LIB = lib
    job = make_job(GDP_JOB, "F_job", {"motion": {"mode": "manual", "watermark": False, "keep_logo": True,
                                                  "items": [{"id": "zz-sparkle", "start": 4.0,
                                                             "placement": {"width_pct": 0.5, "y": 0.45}}]},
                                       "logo": {"enabled": False}, "watermark": {"enabled": False}})
    render.run(job)
    mp = json.loads((job / "motion_plan.json").read_text(encoding="utf-8"))
    it = mp["items"][0]
    meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    k = 960 / meta["height"]
    rect = [round(v * k) for v in (it["x"], it["y"], it["w"], it["h"])]
    src_v, out_v = job / "source.mp4", job / "preview.mp4"

    def d(t):
        a, b = frame(src_v, t), frame(out_v, t)
        if a.shape != b.shape:
            a = cv2.resize(a.astype(np.uint8), (b.shape[1], b.shape[0])).astype(np.int16)
        return rdiff(a, b, rect)
    before, during, after = d(it["start"] - 0.5), d(it["start"] + 0.8), d(it["end"] + 0.4)
    check("F", during > 10 and before < 6 and after < 6,
          f"chèn vào video: trước {before:.1f} · trong {during:.1f} · sau {after:.1f} (không overlay thừa)")


# ───────────────────────────── G ─────────────────────────────
def case_G() -> None:
    ml.LIB = TEST_LIB
    g = TMP / "G_src"

    def expect(label: str, fn, needle: str) -> None:
        try:
            fn()
            check("G", False, f"{label}: KHÔNG báo lỗi")
        except (ml.MotionError, motiondirector.MotionPlanError, render.EdlError) as exc:
            check("G", needle in str(exc), f"{label}: {str(exc)[:110]}")

    nost = g / "no-settime.html"
    write_html(g, "no-settime.html")
    nost.write_text(nost.read_text(encoding="utf-8").replace("window.setTime =", "window.play =")
                    .replace("setTime: window.setTime", "play: window.play"), encoding="utf-8")
    expect("không setTime", lambda: ml.import_source(nost, anim_id="zz-g1", brands=["GIADUNGPLUS"]), "setTime")
    miss = write_html(g, "missing-asset.html", extra="\n  const logo = new Image(); logo.src = 'assets/missing-logo.png';")
    expect("thiếu asset", lambda: ml.import_source(miss, anim_id="zz-g2", brands=["GIADUNGPLUS"]), "thiếu")
    opq = write_html(g, "opaque.html")
    opq.write_text(opq.read_text(encoding="utf-8").replace("background:transparent", "background:#ffffff"), encoding="utf-8")
    expect("nền đục", lambda: ml.import_source(opq, anim_id="zz-g3", brands=["GIADUNGPLUS"]), "KHÔNG trong suốt")
    check("G", ml.get("zz-g3")["enabled"] is False, "animation lỗi khi import → để TẮT (AUTO không chọn)")
    rnd = write_html(g, "random.html", extra="\n  ctx.fillRect(Math.random() * 900, 300, 60, 60);")
    expect("khung không tái lập", lambda: ml.import_source(rnd, anim_id="zz-g4", brands=["GIADUNGPLUS"]), "đồng bộ")
    cdn = write_html(g, "cdn.html", head='<script src="https://cdn.example.com/lib.js"></script>')
    expect("gọi CDN", lambda: ml.import_source(cdn, anim_id="zz-g5", brands=["GIADUNGPLUS"]), "Internet")
    mp4 = g / "no-alpha.mp4"
    media.run([config.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=320x240:d=1", "-c:v", "libx264",
               "-pix_fmt", "yuv420p", str(mp4)])
    expect("MP4 không alpha", lambda: ml.import_source(mp4, anim_id="zz-g6", brands=["GIADUNGPLUS"]), "alpha")
    job = make_job(GDP_JOB, "G_job", {"motion": {"mode": "manual", "items": [{"id": "khong-ton-tai", "start": 1}]}})
    expect("id không có", lambda: render.run(job), "Không có animation")
    ok = write_html(g, "ok.html")
    ml.import_source(ok, anim_id="zz-g7", brands=["GIADUNGPLUS"])
    ml.set_enabled("zz-g7", False)
    job2 = make_job(GDP_JOB, "G_job2", {"motion": {"mode": "manual", "items": [{"id": "zz-g7", "start": 1}]}})
    expect("animation đang tắt", lambda: render.run(job2), "TẮT")
    check("G", not (job / "preview.mp4").exists() and not (job2 / "preview.mp4").exists(),
          "lỗi animation → KHÔNG ra video")


# ───────────────────────────── V2: logo thường trực, watermark vòng đời, AUTO đa vai trò ─────────────────────────────
def _vis(job: Path, rect, t: float) -> float:
    """Độ lệch vùng rect giữa bản dựng và nguồn tại giây t (cao = có lớp phủ)."""
    a, b = frame(job / "source.mp4", t), frame(job / "preview.mp4", t)
    if a.shape != b.shape:
        a = cv2.resize(a.astype(np.uint8), (b.shape[1], b.shape[0])).astype(np.int16)
    k = b.shape[0] / json.loads((job / "meta.json").read_text(encoding="utf-8"))["height"]
    return rdiff(a, b, [round(v * k) for v in rect])


def case_H() -> None:  # reveal đầu video → logo thường trực tiếp quản
    ml.LIB = REAL_LIB
    job = make_job(GDP_JOB, "H_reveal_start", {"motion": {"mode": "manual", "watermark": False,
                                                           "items": [{"id": "gdp-roll-smile", "start": 0.8}]},
                                                "watermark": {"enabled": False}})
    render.run(job)
    mp = json.loads((job / "motion_plan.json").read_text(encoding="utf-8"))
    r, lg = mp["items"][0], mp["logo"]
    rect = lg["rect"]
    before, mid, after, late = (_vis(job, rect, 0.3), _vis(job, rect, (r["start"] + r["end"]) / 2),
                                _vis(job, rect, r["end"] + 0.4), _vis(job, rect, mp["duration"] - 0.4))
    check("H", lg["hidden"] and lg["hidden"][0][0] >= r["start"] and lg["hidden"][0][1] <= r["end"],
          f"logo ẩn {lg['hidden']} ⊂ reveal {r['start']}–{r['end']}s")
    check("H", before > 15 and mid < 5 and after > 15 and late > 15,
          f"logo góc: trước reveal {before:.1f} · giữa reveal {mid:.1f} (ẩn) · sau reveal {after:.1f} · cuối video "
          f"{late:.1f} (tiếp quản tới hết)")


def case_I() -> None:  # reveal giữa video → logo có từ đầu, ẩn đúng đoạn, hiện lại
    ml.LIB = REAL_LIB
    job = make_job(GDP_JOB, "I_reveal_mid", {"motion": {"mode": "manual", "watermark": False,
                                                         "items": [{"id": "gdp-roll-smile", "start": 7.0}]},
                                              "watermark": {"enabled": False}})
    render.run(job)
    mp = json.loads((job / "motion_plan.json").read_text(encoding="utf-8"))
    r, rect = mp["items"][0], mp["logo"]["rect"]
    v = [_vis(job, rect, t) for t in (2.0, (r["start"] + r["end"]) / 2, r["end"] + 0.4)]
    check("I", v[0] > 15 and v[1] < 5 and v[2] > 15,
          f"reveal {r['start']}–{r['end']}s: logo trước {v[0]:.1f} · trong {v[1]:.1f} · sau {v[2]:.1f}")
    check("I", mp["logo"]["visible"][0][0] == 0 and mp["logo"]["visible"][-1][1] == mp["duration"],
          f"logo hiện {mp['logo']['visible']}")


def case_J() -> None:  # không có reveal → logo thường trực hiện suốt, không có khoảng ẩn
    ml.LIB = REAL_LIB
    job = make_job(GDP_JOB, "J_no_reveal", {"motion": {"mode": "manual", "watermark": False, "items": []},
                                             "watermark": {"enabled": False}})
    render.run(job)
    mp = json.loads((job / "motion_plan.json").read_text(encoding="utf-8"))
    layers = json.loads((job / "layers.json").read_text(encoding="utf-8"))
    rect = layers["logo_rect"]
    vals = [_vis(job, rect, t) for t in (0.3, 6.0, 12.0, mp["duration"] - 0.4)]
    check("J", not layers["logo_hidden"] and mp["logo"]["visible"] == [[0.0, mp["duration"]]] and min(vals) > 15,
          f"logo hiện suốt (lệch vùng {[round(x, 1) for x in vals]})")


def case_K() -> None:  # watermark: intro → (dim) → hold tại 1 chỗ, không di chuyển trước khi giữ
    ml.LIB = REAL_LIB
    job = make_job(GDP_JOB, "K_wm", {"motion": {"mode": "auto"}})
    render.run(job)
    mp = json.loads((job / "motion_plan.json").read_text(encoding="utf-8"))
    wm, ph = mp["watermark"], mp["watermark"]["phases"]
    seg0 = wm["segments"][0]
    check("K", seg0["start"] == ph["intro"][0] and seg0["end"] >= ph["hold"][1] and ph["hold"][0] >= ph["intro"][1],
          f"chặng 1 ({seg0['x']},{seg0['y']}) {seg0['start']}–{seg0['end']}s chứa intro {ph['intro']} + giữ {ph['hold']}")
    rect = (seg0["x"], seg0["y"], wm["w"], wm["h"])
    intro = _vis(job, rect, (ph["intro"][0] + ph["intro"][1]) / 2)
    h1, h2 = _vis(job, rect, ph["hold"][0] + 1.0), _vis(job, rect, min(ph["hold"][1], mp["duration"]) - 1.0)
    check("K", intro > 2 * max(h1, h2) and min(h1, h2) > 0.6,
          f"intro rõ {intro:.1f} → giữ mờ {h1:.1f} / {h2:.1f} cùng một chỗ")
    pose = wm["pose"]
    check("K", pose["ok"], f"khung giữ watermark {pose['time']}s hợp lệ ({pose['note']})")
    # animation reveal dùng làm watermark (PHALEDO, giữ tại 2,45s): có pha DIM, opacity áp 1 lần
    pj = make_job("phaledo-0337", "K_wm_phaledo", {"motion": {"mode": "manual", "items": []}})
    e = json.loads((pj / "edl.json").read_text(encoding="utf-8"))
    m = json.loads((pj / "meta.json").read_text(encoding="utf-8"))
    pp = motiondirector.plan(pj, e, m, [])
    w2 = pp["watermark"]
    check("K", w2["dim"] > 0 and w2["pose"]["mode"] == "time" and w2["pose"]["ok"] and 0.08 <= w2["opacity"] <= 0.16,
          f"PHALEDO: giữ khung {w2['pose']['time']}s, mờ {w2['dim']}s về {w2['opacity']:.0%} (khung giữ đạt)")


def _flat(wm: dict, W: int, H: int, dur: float, times: list[float], rects: list) -> list[list[float]]:
    """Chạy ĐÚNG filter watermark của kế hoạch lên nền xám phẳng; trả lệch tối đa từng vùng (+ cả khung) tại mỗi mốc."""
    ins, lines = motiondirector.chain_watermark(1, "0:v", "out", wm, dur)
    res = []
    for t in times:
        out = TMP / f"L_{t:.2f}.png"
        media.run([config.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x808080:s={W}x{H}:r=30:d={dur}",
                   *ins, "-filter_complex", ";".join(lines) + ";[out]format=rgb24[o]", "-map", "[o]", "-ss", f"{t:.3f}",
                   "-frames:v", "1", str(out)])
        im = np.abs(cv2.imread(str(out)).astype(np.int16) - 128)
        res.append([float(im[y:y + h, x:x + w].max()) for x, y, w, h in rects] + [float(im.max())])
    return res


def case_L() -> None:  # watermark: xuất hiện → chìm dần → đổi chỗ (mặc định trượt êm như cũ; tuỳ chọn mờ ra/hiện lại)
    ml.LIB = REAL_LIB
    job = make_job("phaledo-0337", "L_reloc", {"motion": {"mode": "manual", "items": []}})
    render.run(job)
    mp = json.loads((job / "motion_plan.json").read_text(encoding="utf-8"))
    meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    W, H, dur = meta["width"], meta["height"], mp["duration"]
    wm = mp["watermark"]
    segs, ph = wm["segments"], wm["phases"]
    period = wm["life"]["period"]
    check("L", ph["relocate_mode"] == "slide" and len(segs) >= 3 and segs[1]["start"] >= ph["settled"] - 0.01
          and all(abs((s["end"] - s["start"]) - period) < 0.01 for s in segs[1:-1]),
          f"mặc định TRƯỢT như cũ: chìm xong {ph['settled']}s rồi đổi chỗ mỗi {period:g}s "
          f"{[(s['start'], s['end']) for s in segs]}")
    r = segs[1]["start"]
    a, b = (segs[0]["x"], segs[0]["y"], wm["w"], wm["h"]), (segs[1]["x"], segs[1]["y"], wm["w"], wm["h"])
    move = 1.4
    g = _flat(wm, W, H, dur, [r - 0.3, r + move / 2, r + move + 0.3], [a, b])
    sep = not motiondirector._inter(a, b)
    check("L", g[0][0] > 10 and g[1][2] > 10 and g[2][1] > 10 and (not sep or (g[0][1] == 0 and g[2][0] == 0)),
          f"trượt lúc {r}s (nền phẳng, lệch tối đa [chỗ cũ, chỗ mới, cả khung]): trước {g[0]} · đang trượt {g[1]} "
          f"(vẫn thấy, không tắt) · trượt xong {g[2]}")
    # tuỳ chọn relocate_mode "fade": giữ lâu, mờ ra chỗ cũ / hiện ở chỗ mới, không trượt
    e = json.loads((job / "edl.json").read_text(encoding="utf-8"))
    e["watermark"] = {"lifecycle": {"relocate_mode": "fade"}}
    pf = motiondirector.plan(job, e, meta, [])
    wf = pf["watermark"]
    sf = wf["segments"]
    ok_seg = len(sf) >= 2 and sf[1]["start"] >= wf["phases"]["hold"][1] - 0.01 and         all(s["end"] - s["start"] >= 0.6 * wf["life"]["hold"] for s in sf[1:])
    check("L", ok_seg, f"kiểu fade: {len(sf)} chặng {[(s['start'], s['end']) for s in sf]} (giữ ≥ {wf['life']['hold']}s)")
    if ok_seg:
        r = sf[1]["start"]
        a, b = (sf[0]["x"], sf[0]["y"], wf["w"], wf["h"]), (sf[1]["x"], sf[1]["y"], wf["w"], wf["h"])
        g = _flat(wf, W, H, dur, [r - 1.0, r - 0.05, r + 0.05, r + 1.0], [a, b])
        check("L", g[0][0] > 10 and g[0][1] == 0 and g[3][0] == 0 and g[3][1] > 10 and max(g[1][:2] + g[2][:2]) < 0.25 * g[0][0],
              f"kiểu fade lúc {r}s: trước 1s {g[0][:2]} · sát trước {g[1][:2]} · sát sau {g[2][:2]} · sau 1s {g[3][:2]} "
              f"→ mờ ra chỗ cũ, hiện ở chỗ mới")
    e["watermark"] = {"lifecycle": {"relocate": False}}
    p2 = motiondirector.plan(job, e, meta, [])
    check("L", len(p2["watermark"]["segments"]) == 1, "tắt relocate → watermark giữ 1 chỗ tới hết")


def case_M() -> None:  # xung đột logo / animation / watermark
    ml.LIB = REAL_LIB
    job = make_job(LTENG_VN_JOB, "M_conflict", {"motion": {"mode": "auto"}})
    e = json.loads((job / "edl.json").read_text(encoding="utf-8"))
    m = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    from studio import logo as lg_mod
    boxes = render.label_boxes(job, e, m)
    lp = lg_mod.plan(job, e, m, boxes, persistent=True)
    lr = (lp["x"], lp["y"], lp["w"], lp["h"])
    p = motiondirector.plan(job, e, m, boxes, lr)
    bad = [it["id"] for it in p["items"] if "logo" not in it["replaces"] and motiondirector._inter(lr, (it["x"], it["y"], it["w"], it["h"]))]
    check("M", not bad, f"animation không thay logo không đè logo góc (vi phạm: {bad or 'không'})")
    reps = [it for it in p["items"] if "logo" in it["replaces"]]
    check("M", all(any(it["start"] <= a and b <= it["end"] for it in reps) for a, b in p["logo"]["hidden"]),
          f"logo ẩn {p['logo']['hidden']} chỉ trong animation thay logo {[(it['id'], it['start'], it['end']) for it in reps]}")
    wm = p["watermark"]
    zone = (lr[0] - round(m["width"] * 0.03), 0, lr[2] + 2 * round(m["width"] * 0.03), lr[1] + lr[3] + round(m["height"] * 0.15))
    check("M", all(not motiondirector._inter(zone, (s["x"], s["y"], wm["w"], wm["h"])) for s in wm["segments"]),
          f"watermark không nằm sát/đè logo góc ({[(s['x'], s['y']) for s in wm['segments']]})")
    intro = wm["phases"]["intro"]
    late = [it for it in p["items"] if it["start"] >= 3.0]
    check("M", all(it["end"] + 2.5 <= intro[0] or it["start"] >= (wm["phases"]["dim"] or intro)[1] + 2.5 for it in late),
          f"accent né đoạn intro watermark {intro} (cách ≥ min_gap)")
    # chèn tay đè logo góc → QA phải bắt
    j2 = make_job(GDP_JOB, "M_manual_clash", {"motion": {"mode": "manual", "watermark": False, "items": [
        {"id": "gdp-peek-a-boo", "start": 6.0, "placement": {"params": {"side": "right"}, "x": "right", "y": "top",
                                                             "margin_y_pct": 0.02}}]}})
    render.run(j2)
    from studio import outro
    e2 = json.loads((j2 / "edl.json").read_text(encoding="utf-8"))
    m2 = json.loads((j2 / "meta.json").read_text(encoding="utf-8"))
    q = motiondirector.qa(j2, j2 / "preview.mp4", outro.total_duration(e2, m2))
    check("M", not q["ok"] and any("đè logo" in x for x in q["problems"]), f"QA bắt animation chèn tay đè logo: {q['problems']}")


def case_N() -> None:  # AUTO đa vai trò: reveal + accent khi có chỗ; không ép khi hết ứng viên (ghi lý do)
    ml.LIB = REAL_LIB
    job = make_job(GDP_JOB, "N_multi", {"motion": {"mode": "auto"}})
    e = json.loads((job / "edl.json").read_text(encoding="utf-8"))
    m = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    from studio import logo as lg_mod
    boxes = render.label_boxes(job, e, m)
    lp = lg_mod.plan(job, e, m, boxes, persistent=True)
    p = motiondirector.plan(job, e, m, boxes, (lp["x"], lp["y"], lp["w"], lp["h"]))
    roles = [it["role"] for it in p["items"]]
    check("N", "brand_reveal" in roles and "accent" in roles and len(p["items"]) <= sum(p["budget"].values()),
          f"GDP 18s: chọn {[(it['id'], it['role'], it['start']) for it in p['items']]} · budget {p['budget']}")
    check("N", p["library"]["total"] >= 10 and p["library"]["usable"] >= 4 and all(s.get("reason") for s in p["skipped"]),
          f"giải thích: thư viện {p['library']['total']}, dùng được {p['library']['usable']}, bỏ {len(p['skipped'])} (đều có lý do)")
    pj = make_job("phaledo-0337", "N_phaledo", {"motion": {"mode": "auto"}})
    e2 = json.loads((pj / "edl.json").read_text(encoding="utf-8"))
    m2 = json.loads((pj / "meta.json").read_text(encoding="utf-8"))
    p2 = motiondirector.plan(pj, e2, m2, render.label_boxes(pj, e2, m2))
    acc = [it for it in p2["items"] if it["role"] == "accent"]
    check("N", acc or any("accent" in n for n in p2["notes"]),
          f"PHALEDO 33s: accent {[(i['id'], i['start']) for i in acc] or 'không — ' + '; '.join(n for n in p2['notes'] if 'accent' in n)}")
    check("N", motiondirector.budget({"budget": [[15, 1], [30, 1], [60, 2]], "per_extra_30s": 1}, 90) == 3
          and motiondirector.budget({"budget": [[15, 1], [30, 1], [60, 2]], "per_extra_30s": 1}, 12) == 1
          and motiondirector.budget({"budget": [[30, 0], [60, 1]]}, 20) == 0, "bảng budget theo thời lượng (cấu hình được)")


def case_O() -> None:  # cỡ / vị trí theo tỉ lệ khung: logo thường trực + reveal
    ml.LIB = REAL_LIB
    from studio import logo as lg_mod
    src = config.JOBS / GDP_JOB / "source.mp4"
    info = ml.render(ml.get("gdp-roll-smile"))
    pl = ml.get("gdp-roll-smile")["placement"]
    for W, H in ((1080, 1920), (720, 960), (1920, 1080)):
        d = TMP / f"O_{W}x{H}"
        d.mkdir(exist_ok=True)
        media.run([config.FFMPEG, "-y", "-v", "error", "-t", "3", "-i", str(src), "-vf",
                   f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2", "-an",
                   str(d / "source.mp4")])
        meta = {"id": d.name, "source": "source.mp4", "width": W, "height": H, "fps": 30.0, "duration": 3.0}
        edl = {"shop": "giadungplus_official", "logo": {"enabled": True}, "motion": {"mode": "auto"}}
        lp = lg_mod.plan(d, edl, meta, [], persistent=True)
        want = round(W * lg_mod.by_aspect(lg_mod.shop_profile("giadungplus_official")["logo"]["persistent"]["width_pct"], W, H))
        L = motiondirector.layout(info, pl, W, H)
        want_r = lg_mod.by_aspect(pl["width_pct"], W, H) * W
        check("O", abs(lp["w"] - want) <= 1 and lp["y"] == round(H * 0.03) and min(lp["x"], W - lp["x"] - lp["w"]) == round(W * 0.04)
              and abs(L["w"] - want_r) <= 2 and L["y"] == round(H * 0.03) and L["x"] == 0,
              f"{W}x{H}: logo {lp['w']}x{lp['h']} tại ({lp['x']},{lp['y']}) · reveal {L['w']}x{L['h']} tại ({L['x']},{L['y']}) "
              f"(lề trên {lp['y'] / H:.1%})")


CASES = {"A": case_A, "B": case_B, "C": case_C, "D": case_D, "E": case_E, "F": case_F, "G": case_G,
         "H": case_H, "I": case_I, "J": case_J, "K": case_K, "L": case_L, "M": case_M, "N": case_N, "O": case_O}


def main() -> None:
    want = [c for c in sys.argv[1:] if c in CASES] or list(CASES)
    print(f"Thư mục tạm: {TMP}")
    for c in want:
        print(f"== Case {c}")
        try:
            CASES[c]()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            check(c, False, f"văng lỗi: {exc}")
    ok = sum(1 for r in RESULTS if r[1])
    print(f"\nTỔNG: {ok}/{len(RESULTS)} kiểm tra đạt · case lỗi: {sorted({r[0] for r in RESULTS if not r[1]}) or 'không'}")
    if "--keep" not in sys.argv:
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
