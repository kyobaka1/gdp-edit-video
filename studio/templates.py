"""Render ô chữ từ mẫu HTML của brand (templates/<brand>/) bằng Chrome ẩn (Playwright, dùng Chrome đã cài).

Hợp đồng mẫu: xem templates/README.md. Renderer đặt --w/--h/--fs, dò cỡ chữ lớn nhất vừa khung, chụp #label
nền trong suốt. Chữ < cỡ tối thiểu → nới ô (ngang trước, rồi dọc) — ô mới luôn phủ trọn ô gốc.
"""

import html
import io
import json
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from studio import config

TEMPLATES = config.ROOT / "templates"

_FIT_JS = """
([fsMin, fsMax]) => {
  const root = document.documentElement, label = document.getElementById('label');
  const parts = ['text', 'sub'].map(id => document.getElementById(id)).filter(Boolean);
  const fits = fs => {
    root.style.setProperty('--fs', fs + 'px');
    if (label.scrollHeight > label.clientHeight + 1 || label.scrollWidth > label.clientWidth + 1) return false;
    return parts.every(p => p.scrollWidth <= p.clientWidth + 1);
  };
  let lo = Math.floor(fsMin), hi = Math.ceil(fsMax), best = -1;
  while (lo <= hi) { const mid = (lo + hi) >> 1; if (fits(mid)) { best = mid; lo = mid + 1; } else hi = mid - 1; }
  root.style.setProperty('--fs', (best > 0 ? best : fsMin) + 'px');
  return best;
}
"""


def manifest(brand: str) -> dict:
    p = TEMPLATES / brand.lower() / "manifest.json"
    if not p.exists():
        raise FileNotFoundError(f"Chưa có thư viện mẫu cho brand {brand}: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


class TemplateRenderer:
    def __init__(self, brand: str):
        self.brand = brand.lower()
        self.man = manifest(brand)
        self._pw = self._browser = self._page = None

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(channel="chrome", headless=True)
        self._page = self._browser.new_page(device_scale_factor=1)
        return self

    def __exit__(self, *exc):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def _load(self, slot: str, text: str, sub: str) -> None:
        spec = self.man["slots"].get(slot)
        if not spec:
            raise KeyError(f"Brand {self.brand} không có mẫu '{slot}' (có: {', '.join(self.man['slots'])})")
        src = (TEMPLATES / self.brand / spec["file"]).read_text(encoding="utf-8")
        filled = src.replace("{{text}}", html.escape(text)).replace("{{sub}}", html.escape(sub))
        tmp = TEMPLATES / self.brand / "_render_tmp.html"  # cùng thư mục để font tương đối tải được
        tmp.write_text(filled, encoding="utf-8")
        self._page.goto(tmp.as_uri())
        self._page.evaluate("document.fonts.ready")
        if not sub:
            self._page.evaluate("() => { const s = document.getElementById('sub'); if (s) s.remove(); }")
        if spec.get("nowrap"):  # mẫu một dòng (vd hook xoay chéo): không xuống dòng, cỡ chữ tự co
            self._page.evaluate("() => { document.getElementById('text').style.whiteSpace = 'nowrap'; }")

    def _fit(self, w: int, h: int, spec: dict) -> int:
        self._page.set_viewport_size({"width": max(w, 16), "height": max(h, 16)})
        self._page.evaluate(f"() => {{ const r = document.documentElement.style;"
                            f" r.setProperty('--w', '{w}px'); r.setProperty('--h', '{h}px'); }}")
        return self._page.evaluate(_FIT_JS, [h * spec["fs_min"] / 100, h * spec["fs_max"] / 100])

    def render(self, slot: str, text: str, w: int, h: int, *, sub: str = "", min_px: int = 0,
               max_w: int | None = None, max_h: int | None = None) -> tuple[Image.Image, int, int]:
        """Trả (ảnh RGBA, w, h thực dùng). Nới w rồi h khi chữ < min_px hoặc không vừa."""
        spec = self.man["slots"][slot]
        self._load(slot, text, sub)
        max_w, max_h = max_w or w, max_h or h * 3
        fs = self._fit(w, h, spec)
        while (fs < 0 or fs < min_px) and w < max_w:
            w = min(max_w, round(w * 1.08) + 4)
            fs = self._fit(w, h, spec)
        while (fs < 0 or fs < min_px) and h < max_h:
            h = min(max_h, round(h * 1.08) + 4)
            fs = self._fit(w, h, spec)
        png = self._page.locator("#label").screenshot(omit_background=True)
        return Image.open(io.BytesIO(png)).convert("RGBA"), w, h


def preview_sheet(brand: str) -> Path:
    """Bảng xem trước mọi mẫu của brand với chữ mẫu → templates/<brand>/_preview.png"""
    samples = {
        "caption": ("Kệ treo tường không cần khoan", "", 640, 80),
        "hook": ("Bồn rửa bừa bộn, đồ dùng không chỗ để?", "", 700, 110),
        "badge": ("Chịu lực tốt", "", 360, 90),
        "info": ("Chờ keo khô 48 giờ", "Trời lạnh: chờ 72 giờ", 520, 130),
    }
    tiles = []
    with TemplateRenderer(brand) as r:
        for slot in r.man["slots"]:
            text, sub, w, h = samples.get(slot, ("Chữ mẫu tiếng Việt", "", 560, 90))
            img, _, _ = r.render(slot, text, w, h, sub=sub)
            tiles.append(img)
    pad = 24
    sheet = Image.new("RGB", (max(t.width for t in tiles) + 2 * pad, sum(t.height + pad for t in tiles) + pad), "#7a8a8a")
    y = pad
    for t in tiles:
        sheet.paste(t, (pad, y), t)
        y += t.height + pad
    out = TEMPLATES / brand.lower() / "_preview.png"
    sheet.save(out)
    return out
