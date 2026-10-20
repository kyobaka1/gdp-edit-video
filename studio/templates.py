"""Render ô chữ từ mẫu HTML của SHOP (assets/shops/<shop>/templates/) bằng Chrome ẩn (Playwright, Chrome đã cài).

Hợp đồng mẫu: assets/shops/README.md. Shop không có mẫu riêng → `templates_from` trong shop.json trỏ sang shop khác.
Renderer đặt --w/--h/--fs, dò cỡ chữ lớn nhất vừa khung, chụp #label nền trong suốt. Chữ < cỡ tối thiểu → nới ô
(ngang trước, rồi dọc) — ô mới luôn phủ trọn ô gốc.
"""

import html
import io
import json
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from studio import config

SHOPS = config.ROOT / "assets" / "shops"

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


def shop_profile(shop: str) -> dict:
    p = SHOPS / shop / "shop.json"
    if not p.exists():
        raise FileNotFoundError(f"Chưa có hồ sơ shop '{shop}' ({p}) — tạo bằng tools/init_shop.py {shop}")
    return json.loads(p.read_text(encoding="utf-8"))


def template_dir(shop: str, _seen: tuple = ()) -> Path:
    """Thư mục mẫu của shop; không có mẫu riêng thì theo `templates_from` (chặn vòng lặp)."""
    d = SHOPS / shop / "templates"
    if (d / "manifest.json").exists():
        return d
    nxt = shop_profile(shop).get("templates_from")
    if not nxt or nxt in _seen:
        raise FileNotFoundError(f"Shop '{shop}' chưa có mẫu chữ (templates/manifest.json) và không mượn shop nào "
                                f"— thiết kế mẫu (assets/shops/README.md) hoặc khai templates_from trong shop.json")
    return template_dir(nxt, _seen + (shop,))


def manifest(shop: str) -> dict:
    return json.loads((template_dir(shop) / "manifest.json").read_text(encoding="utf-8"))


class TemplateRenderer:
    def __init__(self, shop: str):
        self.shop = shop
        self.dir = template_dir(shop)
        self.man = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
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
            raise KeyError(f"Shop {self.shop} không có mẫu '{slot}' (có: {', '.join(self.man['slots'])})")
        src = (self.dir / spec["file"]).read_text(encoding="utf-8")
        filled = src.replace("{{text}}", html.escape(text)).replace("{{sub}}", html.escape(sub))
        tmp = self.dir / "_render_tmp.html"  # cùng thư mục để font tương đối tải được
        tmp.write_text(filled, encoding="utf-8")
        self._page.goto(tmp.as_uri())
        # Font thiếu thì Chrome LẶNG LẼ dùng font khác (20/10 thư mục font bị sắp lại → mọi url gãy) → ép tải
        # mọi @font-face, cái nào lỗi là dừng.
        bad = self._page.evaluate("""async () => {
            const faces = [...document.fonts];
            await Promise.allSettled(faces.map(f => f.load()));
            return faces.filter(f => f.status === 'error').map(f => f.family + ' ' + f.weight);
        }""")
        if bad:
            raise FileNotFoundError(f"Mẫu {self.dir / spec['file']} không tải được font: {', '.join(bad)} "
                                    f"— kiểm đường dẫn url(...) tới assets/fonts/")
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


def preview_sheet(shop: str) -> Path:
    """Bảng xem trước mọi mẫu của shop với chữ mẫu → <thư mục mẫu>/_preview.png"""
    samples = {
        "caption": ("Kệ treo tường không cần khoan", "", 640, 80),
        "hook": ("Bồn rửa bừa bộn, đồ dùng không chỗ để?", "", 700, 110),
        "badge": ("Chịu lực tốt", "", 360, 90),
        "info": ("Chờ keo khô 48 giờ", "Trời lạnh: chờ 72 giờ", 520, 130),
    }
    tiles = []
    with TemplateRenderer(shop) as r:
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
    out = template_dir(shop) / "_preview.png"
    sheet.save(out)
    return out
