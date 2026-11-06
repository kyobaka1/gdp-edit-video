"""Thư viện animation thương hiệu (thiết kế bằng Claude Design) → overlay ALPHA dùng lại được.

Một animation = một thư mục: `assets/motion/<id>/` (dùng chung theo brand) hoặc `assets/shops/<shop>/motion/<id>/`
(riêng một shop), gồm `motion.json` (metadata) + `src/` (nguồn chép NGUYÊN VĂN từ Claude Design, không sửa tay).
Thêm animation mới = `vs.py motion import <file/thư mục/zip>` hoặc tự thả thư mục — KHÔNG sửa code.
Hợp đồng + cách thêm: assets/motion/README.md.

Render: nguồn HTML phải có `window.setTime(giây)` vẽ ĐỒNG BỘ đúng khung (Claude Design xuất sẵn) → Chrome ẩn chụp từng
khung nền trong suốt → cắt theo vùng có hình (hợp alpha mọi khung) → ProRes 4444 có alpha, cache theo hash (nguồn +
tham số ảnh hưởng điểm ảnh). Vị trí / thời điểm / cỡ trên video do compositor (render.py) lo → đổi chỗ không render lại.
Nguồn khác: thư mục PNG RGBA (frames) hoặc video CÓ alpha (ProRes 4444 / WebM VP9 / mov png). MP4 H.264 không có alpha
→ từ chối (ra nền đen/trắng). HTML không có setTime → từ chối, không chụp theo thời gian thực (khung không tái lập).
"""

import hashlib
import io
import json
import os
import re
import shutil
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode

import cv2
import numpy as np
from PIL import Image

from studio import config, media

LIB = Path(os.getenv("GDP_MOTION_LIB") or config.ROOT / "assets" / "motion")  # env: test dùng thư viện tạm
SHOPS = config.ROOT / "assets" / "shops"
ENGINE = "3"   # đổi khi cách render / info.json đổi → cache cũ tự vô hiệu (2: khung điểm cuối · 3: solid_frame)
KINDS = ("html", "frames", "video")
ROLES_HINT = ("brand_reveal", "watermark", "accent", "corner_signature", "transition", "outro", "custom")  # mở rộng tự do
DEFAULTS = {"version": 1, "enabled": True, "priority": 50, "brands": [], "shops": [], "roles": ["custom"], "tags": [],
            "fps": 30, "params": {}, "variants": {}, "default_variant": None, "placement": {}, "replaces": [],
            "z": "below_text", "ends_transparent": True, "hold": None, "opaque": False}
VIDEO_EXT = (".mov", ".webm", ".mkv", ".mp4", ".m4v")
DEP_EXT = r"png|jpe?g|webp|gif|svg|js|mjs|css|woff2?|ttf|otf|json|wav|mp3"


class MotionError(RuntimeError):
    pass


def cache_root() -> Path:
    return LIB / "_cache"


# ───────────────────────────── thư viện ─────────────────────────────

def _read(mdir: Path, shop: str | None) -> dict:
    raw = json.loads((mdir / "motion.json").read_text(encoding="utf-8"))
    a = {**DEFAULTS, **raw}
    a["dir"], a["shop_scope"] = mdir, shop
    a["source"] = {"kind": "html", **(raw.get("source") or {})}
    a["problems"] = problems(a)
    return a


def problems(a: dict) -> list[str]:
    """Lỗi khai báo (không render): thiếu id/nguồn, sai kiểu… Rỗng = hợp lệ."""
    out = []
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", str(a.get("id", ""))):
        out.append("id phải là chữ thường/số/-/_ (vd gdp-roll-smile)")
    src = a["source"]
    if src.get("kind") not in KINDS:
        out.append(f"source.kind '{src.get('kind')}' không hỗ trợ ({' | '.join(KINDS)})")
    entry = a["dir"] / str(src.get("entry", ""))
    if not src.get("entry") or not entry.exists():
        out.append(f"không thấy nguồn source.entry = {src.get('entry')}")
    for k in ("brands", "shops", "roles", "tags", "replaces"):
        if not isinstance(a.get(k), list):
            out.append(f"'{k}' phải là danh sách")
    if not a.get("brands") and not a.get("shops") and not a.get("shop_scope"):
        out.append("chưa gán brands / shops → không shop nào dùng được")
    if not isinstance(a.get("variants"), dict):
        out.append("'variants' phải là object {tên: {tham số}}")
    return out


def discover() -> list[dict]:
    """Mọi animation: assets/motion/*/motion.json (theo brand) + assets/shops/*/motion/*/motion.json (riêng shop)."""
    found = [_read(p.parent, None) for p in sorted(LIB.glob("*/motion.json")) if not p.parent.name.startswith(("_", "."))]
    found += [_read(p.parent, p.parent.parent.parent.name) for p in sorted(SHOPS.glob("*/motion/*/motion.json"))]
    seen: dict[str, Path] = {}
    for a in found:
        if a["id"] in seen:
            a["problems"].append(f"trùng id với {seen[a['id']]}")
        seen.setdefault(a["id"], a["dir"])
    return found


def get(anim_id: str) -> dict:
    for a in discover():
        if a["id"] == anim_id:
            return a
    raise MotionError(f"Không có animation '{anim_id}' trong thư viện ({LIB}) — `vs.py motion list` xem danh sách")


def applies_to(a: dict, shop: str, brand: str) -> bool:
    if a.get("shop_scope"):
        return a["shop_scope"] == shop
    return shop in a["shops"] or (brand and brand in a["brands"]) or "*" in a["brands"]


def catalog(shop: str | None = None, role: str | None = None, include_disabled: bool = False) -> list[dict]:
    from studio.templates import shop_profile
    brand = shop_profile(shop).get("brand", "") if shop else ""
    out = []
    for a in discover():
        if shop and not applies_to(a, shop, brand):
            continue
        if role and role not in a["roles"]:
            continue
        if not include_disabled and (not a["enabled"] or a["problems"]):
            continue
        out.append(a)
    return sorted(out, key=lambda a: (-a["priority"], a["id"]))


# ───────────────────────────── hash / cache ─────────────────────────────

def _src_files(a: dict) -> list[Path]:
    root = a["dir"] / "src"
    if not root.exists():  # nguồn khai ngoài src/ (thư mục cũ) → chỉ file entry
        return [a["dir"] / a["source"]["entry"]]
    return sorted(p for p in root.rglob("*") if p.is_file())


def source_hash(a: dict) -> str:
    h = hashlib.sha256()
    for p in _src_files(a):
        h.update(str(p.relative_to(a["dir"])).replace("\\", "/").encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def spec_for(a: dict, variant: str | None = None, params: dict | None = None, duration: float | None = None) -> dict:
    """Cấu hình render ảnh hưởng điểm ảnh: tham số mặc định ← biến thể màu ← tham số riêng."""
    var = variant if variant is not None else a.get("default_variant")
    if var and var not in a["variants"]:
        raise MotionError(f"{a['id']}: không có biến thể '{var}' (có: {', '.join(a['variants']) or 'không'})")
    p = {**a["params"], **(a["variants"].get(var) or {}), **(params or {})}
    canvas = a.get("canvas") or [1080, 1920]
    # duration chỉ khi ép tay; không thì lấy theo trang (phụ thuộc params, vd ?dur=) → motion.json.duration (dự phòng)
    return {"entry": a["source"]["entry"], "kind": a["source"]["kind"], "params": p, "variant": var,
            "canvas": list(canvas), "fps": float(a["fps"]), "duration": duration}


def cache_key(src_hash: str, spec: dict) -> str:
    blob = json.dumps({"engine": ENGINE, "src": src_hash, "spec": spec}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


@contextmanager
def _lock(path: Path, wait: float = 600):
    """Khoá file đơn giản: 2–3 job render song song cùng 1 animation → một tiến trình render, các tiến trình khác chờ."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - path.stat().st_mtime > wait:  # khoá mồ côi (tiến trình chết) → gỡ
                path.unlink(missing_ok=True)
            elif time.time() - t0 > wait:
                raise MotionError(f"Chờ khoá render quá lâu: {path}")
            time.sleep(0.5)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def find_cached(anim_id: str, key: str) -> dict | None:
    p = cache_root() / f"{anim_id}-{key}" / "info.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ───────────────────────────── adapters → khung PNG RGBA ─────────────────────────────

_PROBE_JS = """() => {
  const k = Object.keys(window).find(k => /_MOTION$/.test(k) && window[k] && typeof window[k] === 'object');
  const M = k ? window[k] : (window.MOTION || null);
  const num = v => (typeof v === 'number' && isFinite(v) ? v : null);
  return {api: k || (window.MOTION ? 'MOTION' : null),
          setTime: typeof window.setTime === 'function' || !!(M && typeof M.setTime === 'function'),
          duration: M ? num(M.duration) : null, width: M ? num(M.width) : null, height: M ? num(M.height) : null,
          fps: M ? num(M.fps) : null, name: (M && typeof M.name === 'string' && M.name) || document.title || null,
          scenes: M && Array.isArray(M.scenes) ? M.scenes : null};
}"""
_READY_JS = """async () => {
  const k = Object.keys(window).find(k => /_MOTION$/.test(k) && window[k] && typeof window[k] === 'object');
  const M = k ? window[k] : (window.MOTION || null);
  if (M && M.ready && typeof M.ready.then === 'function') await M.ready;
  const faces = [...document.fonts];
  await Promise.allSettled(faces.map(f => f.load()));
  await document.fonts.ready;
  return faces.filter(f => f.status === 'error').map(f => f.family + ' ' + f.weight);
}"""
_SET_JS = """async (t) => {
  const k = Object.keys(window).find(k => /_MOTION$/.test(k) && window[k] && typeof window[k].setTime === 'function');
  if (typeof window.setTime === 'function') window.setTime(t); else window[k].setTime(t);
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
}"""


class HtmlPage:
    """Một trang HTML animation trong Chrome ẩn (Playwright, Chrome đã cài — giống templates.py)."""

    def __init__(self, entry: Path, params: dict, canvas: list[int]):
        self.entry, self.params, self.canvas = entry, params, canvas
        self.errors: list[str] = []
        self.blocked: list[str] = []

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        # --disable-gpu: vẽ bằng CPU. Đo 05/11: Chrome vẽ GPU (RTX 4060) cho miếng giấy xoay có bóng đổ lệch tới 67 mức
        # khi vẽ lại cùng t (tuỳ khung trước đó) → kiểm tất định trượt; vẽ CPU lệch ≤ 2, tốc độ gần như cũ.
        self._browser = self._pw.chromium.launch(channel="chrome", headless=True, args=["--disable-gpu"])
        w, h = self.canvas
        self.page = self._browser.new_page(viewport={"width": int(w), "height": int(h)}, device_scale_factor=1)

        def route(r):  # ⛔ không tải gì từ Internet: render phải tái lập, không phụ thuộc CDN
            if r.request.url.startswith(("http://", "https://")):
                self.blocked.append(r.request.url)
                return r.abort()
            return r.continue_()
        self.page.route("**/*", route)
        self.page.on("requestfailed", lambda req: req.url.startswith("file:") and self.errors.append(
            f"thiếu file: {req.url.split('/')[-1]} ({req.failure})"))
        self.page.on("pageerror", lambda e: self.errors.append(f"lỗi JS: {e}"))
        self.page.on("console", lambda m: m.type == "error" and self.errors.append(f"console: {m.text[:200]}"))
        q = urlencode({"render": "1", **{k: v for k, v in self.params.items() if v is not None}})
        self.page.goto(self.entry.resolve().as_uri() + "?" + q)
        try:
            self.page.wait_for_function("() => typeof window.setTime === 'function' || "
                                        "Object.keys(window).some(k => /_MOTION$/.test(k) && window[k] && "
                                        "typeof window[k].setTime === 'function')", timeout=15000)
        except Exception:
            raise MotionError(f"{self.entry.name}: không có window.setTime(giây) — không tua đúng khung được. Nhờ "
                              f"Claude Design thêm API setTime (vẽ đồng bộ tại thời điểm t), KHÔNG chụp theo thời gian thực."
                              + (f" Lỗi trang: {'; '.join(self.errors[:3])}" if self.errors else ""))
        try:
            bad_fonts = self.page.evaluate(_READY_JS)
        except Exception as exc:
            raise MotionError(f"{self.entry.name}: chờ sẵn sàng lỗi ({str(exc)[:200]}) — thường do thiếu ảnh/asset")
        if bad_fonts:
            self.errors.append(f"font không tải được: {', '.join(bad_fonts)}")
        self.info = self.page.evaluate(_PROBE_JS)
        if self.info["width"] and self.info["height"] and [self.info["width"], self.info["height"]] != list(self.canvas):
            self.canvas = [int(self.info["width"]), int(self.info["height"])]
            self.page.set_viewport_size({"width": self.canvas[0], "height": self.canvas[1]})
        return self

    def frame(self, t: float) -> bytes:
        self.page.evaluate(_SET_JS, t)
        return self.page.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": self.canvas[0],
                                                                "height": self.canvas[1]})

    def __exit__(self, *exc):
        if getattr(self, "_browser", None):
            self._browser.close()
        if getattr(self, "_pw", None):
            self._pw.stop()


def probe_html(entry: Path, params: dict | None = None, canvas: list[int] | None = None) -> dict:
    """Đọc thông tin animation HTML (tên, thời lượng, khung, cảnh) — không chụp khung."""
    with HtmlPage(entry, params or {}, canvas or [1080, 1920]) as pg:
        info = {**pg.info, "canvas": pg.canvas, "errors": pg.errors, "blocked": pg.blocked}
    return info


def _frames_html(a: dict, spec: dict, out: Path) -> dict:
    entry = a["dir"] / spec["entry"]
    with HtmlPage(entry, spec["params"], spec["canvas"]) as pg:
        dur = spec["duration"] or pg.info["duration"] or a.get("duration")
        if not dur:
            raise MotionError(f"{a['id']}: không biết thời lượng — khai 'duration' trong motion.json "
                              f"(trang không có *_MOTION.duration)")
        fps = spec["fps"]
        # chụp cả khung ĐIỂM CUỐI t = duration (trạng thái kết): Claude Design export dừng ở duration − 1/fps nên
        # logo lăn ra (gdp-roll-smile) còn mẩu ở mép khung cuối → overlay tắt đột ngột
        n = max(1, round(float(dur) * fps)) + 1
        for i in range(n):
            fp = out / f"{i:05d}.png"
            fp.write_bytes(pg.frame(min(i / fps, float(dur))))
            if a.get("opaque"):  # khung phủ kín → Chrome trả PNG RGB (bỏ alpha) → thêm alpha đặc cho chuỗi đồng nhất
                im = Image.open(fp)
                if im.mode != "RGBA":
                    im.convert("RGBA").save(fp)
        mid = n // 2  # tái lập: vẽ lại 1 khung giữa phải ra y hệt (setTime vẽ đồng bộ, không phụ thuộc giờ thật)
        again = np.asarray(Image.open(io.BytesIO(pg.frame(mid / fps))).convert("RGBA"), dtype=np.int16)
        first = np.asarray(Image.open(out / f"{mid:05d}.png").convert("RGBA"), dtype=np.int16)
        # so màu ĐÃ NHÂN độ đục (thứ thực sự hiện ra khi ghép): điểm gần trong suốt (α≈20) làm tròn RGB khác nhau
        # vài chục mức nhưng ghép lên hình chỉ lệch <1 mức → không phải "vẽ không đồng bộ" (đo 05/11 scene-chapter-card)
        def premul(x):
            return np.concatenate([x[..., :3] * (x[..., 3:4] / 255.0), x[..., 3:4]], axis=-1)
        if np.abs(premul(again) - premul(first)).max() > 8:
            raise MotionError(f"{a['id']}: vẽ lại cùng thời điểm ra khung khác — setTime không vẽ đồng bộ "
                              f"(animation chạy theo giờ thật?) → không render alpha chính xác được")
        if pg.blocked:
            raise MotionError(f"{a['id']}: nguồn gọi Internet ({', '.join(pg.blocked[:3])}) — phải tự chứa "
                              f"(chép font/ảnh vào src/, không CDN)")
        if pg.errors:
            raise MotionError(f"{a['id']}: lỗi khi render — " + "; ".join(pg.errors[:5]))
        return {"duration": n / fps, "fps": fps, "frames": n, "canvas": pg.canvas, "name": pg.info.get("name")}


def _frames_seq(a: dict, spec: dict, out: Path) -> dict:
    src = a["dir"] / spec["entry"]
    files = sorted(src.glob("*.png"), key=lambda p: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.name)])
    if len(files) < 2:
        raise MotionError(f"{a['id']}: thư mục khung {src} cần ≥2 ảnh PNG")
    for i, f in enumerate(files):
        im = Image.open(f)
        if im.mode != "RGBA":
            raise MotionError(f"{a['id']}: khung {f.name} không có alpha (mode {im.mode}) — cần PNG RGBA nền trong suốt")
        shutil.copyfile(f, out / f"{i:05d}.png")
    w, h = Image.open(files[0]).size
    return {"duration": len(files) / spec["fps"], "fps": spec["fps"], "frames": len(files), "canvas": [w, h]}


def video_alpha(path: Path) -> tuple[bool, list[str]]:
    """(có alpha?, tham số giải mã). WebM VP8/VP9 alpha nằm ở luồng phụ → phải giải bằng libvpx."""
    out = media.run([config.FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_streams", "-print_format",
                     "json", str(path)]).stdout
    s = json.loads(out)["streams"][0]
    pix, codec = s.get("pix_fmt", ""), s.get("codec_name", "")
    if codec in ("vp8", "vp9") and str((s.get("tags") or {}).get("alpha_mode", (s.get("tags") or {}).get("ALPHA_MODE", ""))) == "1":
        return True, ["-c:v", "libvpx-vp9" if codec == "vp9" else "libvpx"]
    return ("a" in pix.replace("gray", "")) or pix in ("rgba", "bgra", "argb", "abgr"), []


def _frames_video(a: dict, spec: dict, out: Path) -> dict:
    src = a["dir"] / spec["entry"]
    ok, dec = video_alpha(src)
    if not ok:
        raise MotionError(f"{a['id']}: video {src.name} KHÔNG có kênh alpha (MP4 H.264 luôn nền đặc) — cần ProRes 4444, "
                          f"WebM VP9 alpha hoặc chuỗi PNG RGBA")
    media.run([config.FFMPEG, "-y", "-v", "error", *dec, "-i", str(src), "-vf", f"fps={spec['fps']},format=rgba",
               str(out / "%05d.png")])
    files = sorted(out.glob("*.png"))
    for i, f in enumerate(files):  # ffmpeg đánh số từ 1 → về 0
        f.rename(out / f"_{i:05d}.png")
    for f in sorted(out.glob("_*.png")):
        f.rename(out / f.name[1:])
    w, h = Image.open(out / "00000.png").size
    return {"duration": len(files) / spec["fps"], "fps": spec["fps"], "frames": len(files), "canvas": [w, h]}


ADAPTERS = {"html": _frames_html, "frames": _frames_seq, "video": _frames_video}


# ───────────────────────────── kiểm alpha ─────────────────────────────

def analyze_frames(paths: list[Path], opaque_ok: bool = False, bg: str | None = None) -> dict:
    """Kiểm alpha THẬT trên từng khung: có kênh alpha, ngoài vật thể trong suốt (không còn nền preview), khung đầu/cuối,
    chớp nền, viền tối/sáng (halo). bg = nền biến thể nhắm tới ("dark"/"light") → chỉ cảnh báo viền thấy được trên nền
    đó (viền sáng của bản cho nền sáng là thiết kế, vd viền kính PHALEDO). Trả {bbox hợp mọi khung, …, fatal[], warn[]}."""
    fatal, warn = [], []
    bbox = None
    cover, border_opaque = [], []
    peak, peak_cov = None, -1.0
    solid_best, solid_n = 0, -1
    for i, p in enumerate(paths):
        im = Image.open(p)
        if im.mode != "RGBA":  # Chrome trả PNG không alpha khi cả trang có nền màu
            fatal.append(f"nền KHÔNG trong suốt — khung {i} không có kênh alpha (mode {im.mode}): còn nền preview/màu "
                         f"nền trang; html/body/stage phải transparent")
            break
        a = np.asarray(im)[..., 3]
        h, w = a.shape
        m = a > 2
        cov = float(m.mean())
        cover.append(cov)
        if cov > peak_cov:
            peak, peak_cov = i, cov
        ns = int((a >= 250).sum())
        if ns > solid_n:  # khung logo đứng yên đặc nhất → đo viền khử răng cưa (không lẫn hiệu ứng ánh sáng đang chạy)
            solid_best, solid_n = i, ns
        bw = max(2, round(min(w, h) * 0.02))
        band = np.concatenate([a[:bw].ravel(), a[-bw:].ravel(), a[:, :bw].ravel(), a[:, -bw:].ravel()])
        border_opaque.append(float((band >= 250).mean()))
        ys, xs = np.nonzero(m)
        if len(xs):
            b = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
            bbox = b if bbox is None else (min(bbox[0], b[0]), min(bbox[1], b[1]), max(bbox[2], b[2]), max(bbox[3], b[3]))
    if fatal:
        return {"fatal": fatal, "warn": warn}
    if bbox is None:
        fatal.append("mọi khung trong suốt hoàn toàn — không có hình (ảnh/asset không tải được?)")
        return {"fatal": fatal, "warn": warn}
    if not opaque_ok:
        bad = [i for i, f in enumerate(border_opaque) if f > 0.5]
        if len(bad) > 0.6 * len(paths):
            fatal.append("nền KHÔNG trong suốt (mép khung đục ở hầu hết khung) — còn nền preview/màu nền trang; "
                         "body/stage phải transparent")
        elif bad:
            warn.append(f"chớp nền đục ở {len(bad)} khung (vd khung {bad[0]}) — kiểm hiệu ứng flash")
    W, H = Image.open(paths[0]).size
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - 2), max(0, y0 - 2)
    x1, y1 = min(W, x1 + 2), min(H, y1 + 2)
    x0, y0 = x0 // 2 * 2, y0 // 2 * 2
    x1, y1 = min(W, (x1 + 1) // 2 * 2), min(H, (y1 + 1) // 2 * 2)
    rgba = np.asarray(Image.open(paths[solid_best]).convert("RGBA"), dtype=np.float32)
    lum = rgba[..., 0] * 0.299 + rgba[..., 1] * 0.587 + rgba[..., 2] * 0.114
    al = rgba[..., 3]
    solid_m = (al >= 250).astype(np.uint8)
    ring_m = (cv2.dilate(solid_m, np.ones((5, 5), np.uint8)) > 0) & (al > 16) & (al < 240)  # dải viền sát nét đặc
    semi, solid = lum[ring_m], lum[solid_m > 0]
    halo = None
    if semi.size > 200 and solid.size > 200:
        halo = round(float(np.median(solid) - np.median(semi)), 1)
        if halo > 90 and bg != "dark":
            warn.append(f"viền TỐI quanh hình (halo {halo}) — ghép lên nền sáng sẽ thấy viền đen")
        elif halo < -90 and bg != "light":
            warn.append(f"viền SÁNG quanh hình (halo {halo}) — ghép lên nền tối sẽ thấy viền trắng")
    first_max = int(np.asarray(Image.open(paths[0]))[..., 3].max())
    last_max = int(np.asarray(Image.open(paths[-1]))[..., 3].max())
    touches = [n for n, hit in (("left", x0 == 0), ("top", y0 == 0), ("right", x1 == W), ("bottom", y1 == H)) if hit]
    return {"fatal": fatal, "warn": warn, "bbox": [x0, y0, x1 - x0, y1 - y0], "canvas": [W, H],
            "coverage_peak": round(peak_cov, 4), "peak_frame": peak, "first_alpha_max": first_max,
            "last_alpha_max": last_max, "halo": halo, "touches_edge": touches,
            "solid_frame": solid_best, "solid_n": solid_n}  # khung logo đặc nhất → suy ra khung giữ watermark


def preview_sheet(paths: list[Path], bbox: list[int], out: Path, footage: Path | None = None, cols: int = 6) -> Path:
    """Ghép thử khung đã cắt lên 3 nền: tối, sáng, footage (khung video thật nếu có, không thì nền giả lập) → ảnh soát."""
    x, y, w, h = bbox
    idx = sorted({round(i * (len(paths) - 1) / (cols - 1)) for i in range(cols)})
    tw = 220
    th = max(40, round(h * tw / w))
    if footage is not None and footage.exists():
        fimg = Image.open(footage).convert("RGB").resize((tw, th))
    else:  # giả lập footage: dải màu + ô caro (vừa sáng vừa tối, có chi tiết)
        g = np.linspace(30, 225, tw, dtype=np.float32)[None, :].repeat(th, 0)
        chk = ((np.arange(th)[:, None] // 12 + np.arange(tw)[None, :] // 12) % 2) * 28
        arr = np.stack([g + chk, g * 0.8 + chk, g * 0.6 + 40], -1).clip(0, 255).astype(np.uint8)
        fimg = Image.fromarray(arr, "RGB")
    bgs = [Image.new("RGB", (tw, th), "#141414"), Image.new("RGB", (tw, th), "#EDEDED"), fimg]
    pad = 6
    sheet = Image.new("RGB", (len(idx) * (tw + pad) + pad, len(bgs) * (th + pad) + pad), "#777777")
    for c, i in enumerate(idx):
        fr = Image.open(paths[i]).convert("RGBA").crop((x, y, x + w, y + h)).resize((tw, th), Image.LANCZOS)
        for r, bg in enumerate(bgs):
            tile = bg.copy()
            tile.paste(fr, (0, 0), fr)
            sheet.paste(tile, (pad + c * (tw + pad), pad + r * (th + pad)))
    sheet.save(out, quality=88)
    return out


def _encode(frames_dir: Path, fps: float, bbox: list[int], out: Path) -> None:
    x, y, w, h = bbox
    media.run([config.FFMPEG, "-y", "-v", "error", "-framerate", f"{fps}", "-i", str(frames_dir / "%05d.png"),
               "-vf", f"crop={w}:{h}:{x}:{y},format=yuva444p10le", "-c:v", "prores_ks", "-profile:v", "4444",
               "-alpha_bits", "16", "-vendor", "apl0", "-pix_fmt", "yuva444p10le", str(out)])


def verify_clip(mov: Path, frames: int, fps: float) -> list[str]:
    """Kiểm file đã mã hoá: còn alpha, đủ số khung, đúng fps."""
    out = media.run([config.FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                     "stream=pix_fmt,nb_read_frames,r_frame_rate,width,height", "-print_format", "json", str(mov)]).stdout
    s = json.loads(out)["streams"][0]
    bad = []
    if "a" not in s.get("pix_fmt", "").replace("gray", ""):
        bad.append(f"mất alpha sau mã hoá (pix_fmt {s.get('pix_fmt')})")
    if int(s.get("nb_read_frames", 0)) != frames:
        bad.append(f"số khung {s.get('nb_read_frames')} ≠ {frames}")
    num, den = (int(v) for v in s.get("r_frame_rate", "0/1").split("/"))
    if den and abs(num / den - fps) > 0.01:
        bad.append(f"fps {num}/{den} ≠ {fps}")
    return bad


# ───────────────────────────── render (có cache) ─────────────────────────────

def render(a: dict, variant: str | None = None, params: dict | None = None, duration: float | None = None,
           force: bool = False, footage: Path | None = None, src_hash: str | None = None) -> dict:
    """Render animation ra clip alpha (cache). Trả info: mov, bbox, canvas, fps, frames, duration, key, src_hash, check.
    Lỗi nghiêm trọng (không alpha, nền đục, thiếu asset, không setTime…) → MotionError, KHÔNG ghi cache."""
    if a["problems"]:
        raise MotionError(f"{a['id']}: motion.json chưa hợp lệ — " + "; ".join(a["problems"]))
    spec = spec_for(a, variant, params, duration)
    sh = src_hash or source_hash(a)
    key = cache_key(sh, spec)
    d = cache_root() / f"{a['id']}-{key}"
    info_p = d / "info.json"
    if info_p.exists() and not force:
        return json.loads(info_p.read_text(encoding="utf-8"))
    with _lock(cache_root() / f".{a['id']}-{key}.lock"):
        if info_p.exists() and not force:  # tiến trình khác vừa render xong
            return json.loads(info_p.read_text(encoding="utf-8"))
        if d.exists():
            shutil.rmtree(d)
        frames = d / "frames"
        frames.mkdir(parents=True)
        t0 = time.time()
        try:
            got = ADAPTERS[spec["kind"]](a, spec, frames)
            paths = sorted(frames.glob("*.png"))
            bg = {"on_dark": "dark", "on_light": "light"}.get(spec["variant"] or "")
            chk = analyze_frames(paths, opaque_ok=bool(a.get("opaque")), bg=bg)
            if chk["fatal"]:
                raise MotionError(f"{a['id']}: " + "; ".join(chk["fatal"]))
            if a.get("ends_transparent") and chk["last_alpha_max"] > 8:
                chk["warn"].append(f"khung cuối còn hình (alpha {chk['last_alpha_max']}) dù khai ends_transparent — "
                                   f"overlay sẽ tắt đột ngột")
            mov = d / "clip.mov"
            _encode(frames, got["fps"], chk["bbox"], mov)
            bad = verify_clip(mov, got["frames"], got["fps"])
            if bad:
                raise MotionError(f"{a['id']}: clip mã hoá lỗi — " + "; ".join(bad))
            preview_sheet(paths, chk["bbox"], d / "sheet.jpg", footage)
            x, y, w, h = chk["bbox"]
            Image.open(paths[-1]).crop((x, y, x + w, y + h)).save(d / "last.png")  # khung giữ (watermark hold)
            Image.open(paths[chk["peak_frame"]]).crop((x, y, x + w, y + h)).save(d / "peak.png")
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            raise
        shutil.rmtree(frames, ignore_errors=True)
        info = {"id": a["id"], "version": a["version"], "key": key, "src_hash": sh, "spec": spec,
                "mov": str(mov), "dir": str(d), "bbox": chk["bbox"], "canvas": got["canvas"], "fps": got["fps"],
                "frames": got["frames"], "duration": round(got["duration"], 4), "check": chk,
                "render_seconds": round(time.time() - t0, 1), "rendered_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        info_p.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        return info


def still(info: dict, t: float) -> Image.Image:
    """Một khung của clip đã render (đã cắt) tại giây t — dùng làm watermark tĩnh từ animation reveal."""
    t = max(0.0, min(t, info["duration"] - 1 / info["fps"]))
    out = Path(info["dir"]) / f"still_{t:06.3f}.png"
    if not out.exists():
        media.run([config.FFMPEG, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", info["mov"], "-frames:v", "1",
                   "-vf", "format=rgba", str(out)])
    return Image.open(out).convert("RGBA")


def hold_pose(a: dict, info: dict, hold_time: float | None = None) -> dict:
    """Khung GIỮ cho watermark (logo đứng yên): khai `hold_time` → kiểm; không khai → khung cuối nếu còn hình (animation
    tự mờ xuống rồi giữ), khung cuối trong suốt → khung logo đặc nhất (solid_frame). Kiểm: logo hoàn chỉnh (lượng điểm đặc
    ≥85% khung đặc nhất, hình trùng ≥80%), không bị cắt mép clip. Trả {time, mode: last|time, ok, problems}."""
    chk, fps = info["check"], info["fps"]
    last_t = (info["frames"] - 1) / fps
    if hold_time is None:
        hold_time = a.get("hold_time")
    if hold_time is None and a.get("hold") == "last" and chk["last_alpha_max"] > 8:
        return {"time": round(last_t, 4), "mode": "last", "ok": True, "problems": [],
                "note": "khung cuối (animation tự mờ xuống rồi giữ)"}
    if hold_time is None:
        hold_time = chk["solid_frame"] / fps
        note = f"suy ra = khung logo đặc nhất ({hold_time:.2f}s; khung cuối α{chk['last_alpha_max']})"
    else:
        note = f"khai báo hold_time {hold_time}s"
    hold_time = max(0.0, min(float(hold_time), last_t))
    ref = np.asarray(still(info, chk["solid_frame"] / fps))[..., 3] >= 250
    got_img = np.asarray(still(info, hold_time))
    got = got_img[..., 3] >= 250
    problems = []
    if ref.sum() and got.sum() < 0.85 * ref.sum():
        problems.append(f"khung {hold_time:.2f}s chưa đủ logo ({got.sum()}/{ref.sum()} điểm đặc)")
    inter, union = (ref & got).sum(), (ref | got).sum()
    if union and inter / union < 0.8:
        problems.append(f"khung {hold_time:.2f}s lệch hình so với logo hoàn chỉnh (IoU {inter / union:.2f})")
    a_any = got_img[..., 3] > 8
    edges = [n for n, hit in (("trái", a_any[:, 0].any()), ("phải", a_any[:, -1].any()), ("trên", a_any[0].any()),
                              ("dưới", a_any[-1].any())) if hit]
    canvas_edges = info["check"].get("touches_edge", [])
    if edges and not canvas_edges:
        problems.append(f"logo chạm mép clip ({', '.join(edges)}) — có thể bị cắt")
    return {"time": round(hold_time, 4), "mode": "time", "ok": not problems, "problems": problems, "note": note}


def archived_source(a: dict, src_hash: str) -> dict | None:
    """Animation đã chốt ở phiên bản cũ (job ghim src_hash) → tìm nguồn cũ trong <id>/_versions/*/."""
    for vdir in sorted((a["dir"] / "_versions").glob("*")):
        if not (vdir / "motion.json").exists():
            continue
        old = _read(vdir, a.get("shop_scope"))
        old["id"] = a["id"]
        old["problems"] = [p for p in old["problems"] if "trùng id" not in p]
        if source_hash(old) == src_hash:
            return old
    return None


# ───────────────────────────── quét / nhập từ Claude Design ─────────────────────────────

def _deps(html: Path) -> tuple[list[str], list[str]]:
    """Tài nguyên tương đối mà file HTML/JS/CSS tham chiếu (script src, ảnh, font, chuỗi 'assets/x.png'…).
    Trả (có, thiếu). Đi sâu 1 tầng vào .js/.css được tham chiếu."""
    have, miss, todo, seen = [], [], [html], set()
    root = html.parent
    pat = re.compile(r"""(?:src|href)\s*=\s*["']([^"'#?]+)["']|url\(\s*["']?([^"')#?]+)["']?\s*\)|["']((?:\./)?[\w./ -]+\.(?:%s))["']""" % DEP_EXT, re.I)
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in pat.finditer(text):
            ref = next(g for g in m.groups() if g)
            if ref.startswith(("data:", "http:", "https:", "//", "#", "blob:", "javascript:")) or "${" in ref:
                continue
            p = (f.parent / ref).resolve()
            try:
                rel = str(p.relative_to(root.resolve())).replace("\\", "/")
            except ValueError:
                miss.append(f"{ref} (ngoài thư mục nguồn)")
                continue
            if p.exists() and p.is_file():
                if rel not in have:
                    have.append(rel)
                if p.suffix.lower() in (".js", ".css", ".mjs"):
                    todo.append(p)
            elif rel not in miss:
                miss.append(rel)
    return have, miss


def classify(p: Path) -> dict:
    """Phân loại một file trong thư mục tải về: nguồn render được / preview / bản nguồn chưa đóng gói / asset / video…"""
    s = p.suffix.lower()
    if s == ".html":
        text = p.read_text(encoding="utf-8", errors="replace")
        if p.name.endswith(".dc.html") or "<x-dc" in text or "support.js" in text:
            return {"kind": "preview", "ok": False, "note": "trang PREVIEW của Claude Design (nền/khung xem thử) — không phải nguồn render"}
        if re.search(r"""["']__[A-Z][A-Z0-9_]{2,}__["']""", text):
            return {"kind": "unbundled", "ok": False, "note": "bản nguồn CHƯA đóng gói (chuỗi giữ chỗ __X__) — dùng bản .html đầy đủ"}
        if not re.search(r"\bsetTime\b", text):
            return {"kind": "html", "ok": False, "note": "HTML không có setTime(t) — không tua đúng khung được"}
        have, miss = _deps(p)
        return {"kind": "html", "ok": not miss, "deps": have, "missing": miss,
                "note": ("thiếu: " + ", ".join(miss)) if miss else f"render được ({len(have)} tài nguyên kèm)"}
    if s in VIDEO_EXT:
        try:
            ok, _ = video_alpha(p)
        except Exception as exc:
            return {"kind": "video", "ok": False, "note": f"không đọc được video: {str(exc)[:80]}"}
        return {"kind": "video", "ok": ok, "note": "video có alpha" if ok else "video KHÔNG alpha (nền đặc) — không dùng làm overlay"}
    if s == ".zip":
        return {"kind": "zip", "ok": True, "note": "file nén — import sẽ giải nén rồi quét"}
    return {"kind": "asset", "ok": False, "note": ""}


def scan(folder: Path) -> list[dict]:
    """Quét MỘT thư mục (không đệ quy toàn máy): file HTML/video/zip + thư mục con là chuỗi PNG."""
    rows = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in (".html", ".zip", *VIDEO_EXT):
            rows.append({"path": p, **classify(p)})
        elif p.is_dir() and not p.name.startswith((".", "_")) and _is_sequence(p):
            pngs = sorted(p.glob("*.png"))
            rgba = Image.open(pngs[0]).mode == "RGBA"
            rows.append({"path": p, "kind": "frames", "ok": rgba,
                         "note": f"chuỗi {len(pngs)} PNG " + ("RGBA" if rgba else "KHÔNG alpha")})
    return rows


def _is_sequence(folder: Path) -> bool:
    """Chuỗi khung = ≥8 PNG đánh số cùng tiền tố, cùng kích thước (thư mục assets/ chứa logo lẻ thì không phải)."""
    pngs = sorted(folder.glob("*.png"))
    if len(pngs) < 8:
        return False
    prefixes = [m.group(1) for p in pngs if (m := re.fullmatch(r"(.*?)(\d+)\.png", p.name, re.I))]
    if len(prefixes) < 0.9 * len(pngs) or len(set(prefixes)) > 1:
        return False
    return Image.open(pngs[0]).size == Image.open(pngs[-1]).size


def slug(name: str) -> str:
    s = re.sub(r"\(standalone\)|\.src$|\.html?$", "", name, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def guess_brand(name: str) -> str | None:
    """Đoán brand theo tên file ↔ brand/mã shop trong shop.json (không cứng tên brand trong code)."""
    from studio.templates import shop_profile
    low = name.lower()
    for d in sorted(SHOPS.iterdir()):
        if not (d / "shop.json").exists():
            continue
        prof = shop_profile(d.name)
        keys = {prof.get("brand", "").lower(), d.name.split("_")[0].lower(), *[k.lower() for k in prof.get("aliases", [])]}
        if any(k and re.search(rf"(^|[^a-z]){re.escape(k)}([^a-z]|$)", low) for k in keys):
            return prof.get("brand")
    return None


def import_source(path: Path, anim_id: str | None = None, brands: list[str] | None = None,
                  roles: list[str] | None = None, name: str | None = None, shop: str | None = None,
                  entry: str | None = None, test_render: bool = True) -> dict:
    """Nhập 1 animation: file HTML (kèm mọi tài nguyên nó tham chiếu) / thư mục (chọn nguồn) / zip / video alpha /
    thư mục chuỗi PNG → chép NGUYÊN VĂN vào thư viện, sinh motion.json nháp (giữ metadata cũ nếu id đã có, cất bản cũ
    vào _versions/), rồi render thử + kiểm alpha. Trả {anim, info|None, archived}."""
    path = Path(path).resolve()
    tmp = None
    try:
        if path.suffix.lower() == ".zip":
            tmp = cache_root() / f"_import_{os.getpid()}_{int(time.time())}"
            with zipfile.ZipFile(path) as z:
                for m in z.namelist():  # chặn zip-slip
                    if Path(m).is_absolute() or ".." in Path(m).parts:
                        raise MotionError(f"zip có đường dẫn nguy hiểm: {m}")
                z.extractall(tmp)
            path = tmp
        if path.is_dir():
            if entry:
                path = path / entry
            else:
                rows = [r for r in scan(path) if r["ok"] and r["kind"] in ("html", "video", "frames")]
                if not rows:  # zip thường có 1 thư mục con
                    subs = [p for p in path.iterdir() if p.is_dir()]
                    if len(subs) == 1:
                        rows = [r for r in scan(subs[0]) if r["ok"] and r["kind"] in ("html", "video", "frames")]
                if len(rows) != 1:
                    raise MotionError("Thư mục có " + (f"{len(rows)} nguồn render được: " + ", ".join(r["path"].name for r in rows)
                                      if rows else "0 nguồn render được") + " — chỉ rõ bằng --entry <file>")
                path = rows[0]["path"]
        kind = "frames" if path.is_dir() else ("video" if path.suffix.lower() in VIDEO_EXT else "html")
        c = classify(path) if kind != "frames" else {"ok": True, "deps": []}
        if kind == "html" and not c["ok"]:
            raise MotionError(f"{path.name}: {c['note']}")
        if kind == "video" and not c["ok"]:
            raise MotionError(f"{path.name}: {c['note']}")
        aid = anim_id or slug(path.stem if path.is_file() else path.name)
        brands = brands or ([] if shop else [b for b in [guess_brand(path.name)] if b])
        if not brands and not shop:
            raise MotionError(f"Không đoán được brand của '{path.name}' — thêm --brand <BRAND> (theo shop.json brand) hoặc --shop")
        base = (SHOPS / shop / "motion") if shop else LIB
        mdir = base / aid
        archived = None
        old_meta = {}
        if (mdir / "motion.json").exists():
            old_meta = json.loads((mdir / "motion.json").read_text(encoding="utf-8"))
            vdir = mdir / "_versions" / f"v{old_meta.get('version', 1)}"
            if vdir.exists():
                shutil.rmtree(vdir)
            vdir.mkdir(parents=True)
            if (mdir / "src").exists():
                shutil.move(str(mdir / "src"), str(vdir / "src"))
            shutil.copyfile(mdir / "motion.json", vdir / "motion.json")
            archived = vdir
        dst = mdir / "src"
        dst.mkdir(parents=True, exist_ok=True)
        if kind == "html":
            shutil.copy2(path, dst / path.name)
            for rel in c["deps"]:
                (dst / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path.parent / rel, dst / rel)
            src_entry = f"src/{path.name}"
        elif kind == "video":
            shutil.copy2(path, dst / path.name)
            src_entry = f"src/{path.name}"
        else:
            (dst / "frames").mkdir(exist_ok=True)
            for f in path.glob("*.png"):
                shutil.copy2(f, dst / "frames" / f.name)
            src_entry = "src/frames"
        meta = {**old_meta}
        meta.update({"id": aid, "source": {**(old_meta.get("source") or {}), "kind": kind, "entry": src_entry,
                                           "origin": str(path if not tmp else Path(path).name)},
                     "version": int(old_meta.get("version", 0)) + 1})
        meta.setdefault("name", name or aid)
        if name:
            meta["name"] = name
        if brands:
            meta["brands"] = brands
        meta.setdefault("brands", [])
        if roles:
            meta["roles"] = roles
        meta.setdefault("roles", ["custom"])
        meta.setdefault("enabled", True)
        meta.setdefault("priority", 50)
        meta.setdefault("tags", [])
        if kind == "html":
            pr = probe_html(dst / path.name, meta.get("params") or {})
            if not name and not old_meta.get("name") and pr.get("name"):
                meta["name"] = re.sub(r"\s*\((render|standalone)\)\s*$", "", pr["name"], flags=re.I)
            meta.setdefault("canvas", pr["canvas"])
            if pr.get("duration"):
                meta.setdefault("duration", round(pr["duration"], 4))
            if pr.get("fps"):
                meta.setdefault("fps", pr["fps"])
            if pr.get("scenes"):
                meta["scenes"] = pr["scenes"]
        meta.setdefault("fps", 30)
        meta.setdefault("params", {})
        meta.setdefault("placement", {})
        meta.setdefault("replaces", ["logo"] if "brand_reveal" in meta["roles"] else [])
        meta.setdefault("ends_transparent", "watermark" not in meta["roles"])
        (mdir / "motion.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        a = _read(mdir, shop)
        info = None
        if test_render and not a["problems"]:
            try:
                info = render(a)
            except MotionError as exc:  # nhập rồi nhưng TẮT: AUTO không chọn, chèn tay báo lỗi — không lọt vào video
                meta.update({"enabled": False, "disabled_reason": f"import: {str(exc)[:300]}"})
                (mdir / "motion.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                raise MotionError(f"{exc} — đã chép vào {mdir} nhưng để TẮT; sửa nguồn rồi import lại cùng --id")
            if str(meta.get("disabled_reason", "")).startswith("import:"):  # lần trước lỗi, nay đạt → bật lại
                meta.pop("disabled_reason")
                meta["enabled"] = True
                (mdir / "motion.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                a = _read(mdir, shop)
        return {"anim": a, "info": info, "archived": archived}
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


def use_version(anim_id: str, version: int) -> dict:
    """Đổi phiên bản hiện hành sang bản đã cất trong _versions/v<N> (bản hiện tại được cất lại)."""
    a = get(anim_id)
    src_v = a["dir"] / "_versions" / f"v{version}"
    if not (src_v / "motion.json").exists():
        have = sorted(p.name for p in (a["dir"] / "_versions").glob("v*"))
        raise MotionError(f"{anim_id}: không có bản v{version} (có: {', '.join(have) or 'không'})")
    cur_v = a["dir"] / "_versions" / f"v{a['version']}"
    if not cur_v.exists():
        cur_v.mkdir(parents=True)
        shutil.move(str(a["dir"] / "src"), str(cur_v / "src"))
        shutil.copyfile(a["dir"] / "motion.json", cur_v / "motion.json")
    else:
        shutil.rmtree(a["dir"] / "src", ignore_errors=True)
    shutil.copytree(src_v / "src", a["dir"] / "src")
    shutil.copyfile(src_v / "motion.json", a["dir"] / "motion.json")
    return get(anim_id)


def set_enabled(anim_id: str, on: bool) -> dict:
    a = get(anim_id)
    p = a["dir"] / "motion.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["enabled"] = on
    p.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return get(anim_id)


def versions(a: dict) -> list[dict]:
    out = [{"version": a["version"], "current": True, "src_hash": source_hash(a)}]
    for vdir in sorted((a["dir"] / "_versions").glob("v*")):
        if (vdir / "motion.json").exists():
            old = _read(vdir, a.get("shop_scope"))
            out.append({"version": old.get("version"), "current": False, "src_hash": source_hash(old)})
    return out


def cached_renders(anim_id: str) -> list[dict]:
    out = []
    for p in sorted(cache_root().glob(f"{anim_id}-*/info.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out

