"""Render ô chữ từ mẫu HTML của SHOP (assets/shops/<shop>/templates/) bằng Chrome ẩn (Playwright, Chrome đã cài).

Hợp đồng mẫu: assets/shops/README.md. Shop không có mẫu riêng → `templates_from` trong shop.json trỏ sang shop khác.
Renderer đặt --w/--h/--fs, dò cỡ chữ lớn nhất vừa khung, chụp #label nền trong suốt. Chữ < cỡ tối thiểu → nới ô
(ngang trước, rồi dọc) — ô mới luôn phủ trọn ô gốc.
"""

import html
import io
import json
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from studio import config

SHOPS = config.ROOT / "assets" / "shops"

_FIT_JS = """
([fsMin, fsMax]) => {
  const root = document.documentElement, label = document.getElementById('label');
  const parts = ['text', 'sub'].map(id => document.getElementById(id)).filter(Boolean);
  // Đo so với VÙNG TRONG phần đệm: chữ tràn vào padding không làm #label báo tràn (scrollWidth gồm cả padding)
  // → bản đầu tưởng vừa, chữ chạm sát mép (Sếp chê 20/10).
  const fits = fs => {
    root.style.setProperty('--fs', fs + 'px');
    const cs = getComputedStyle(label);
    const innerW = label.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const innerH = label.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    const gap = parseFloat(cs.rowGap) || 0;
    const cols = cs.flexDirection.startsWith('column');
    const widest = Math.max(...parts.map(p => p.scrollWidth));
    const tall = cols ? parts.reduce((s, p) => s + p.scrollHeight, 0) + gap * (parts.length - 1)
                      : Math.max(...parts.map(p => p.scrollHeight));
    return widest <= innerW + 1 && tall <= innerH + 1;
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


def shop_voice(shop: str, _seen: tuple = ()) -> dict | None:
    """Giọng đọc của shop (shop.json voice); không khai thì theo shop mượn mẫu (templates_from)."""
    prof = shop_profile(shop)
    if prof.get("voice", {}).get("name"):
        return prof["voice"]
    nxt = prof.get("templates_from")
    return shop_voice(nxt, _seen + (shop,)) if nxt and nxt not in _seen else None


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
        if getattr(self, "_tmp", None):
            self._tmp.unlink(missing_ok=True)
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def _load(self, slot: str, lines: list[str], sub: str) -> None:
        """Nạp mẫu với chữ đã chia dòng sẵn (renderer tự quyết chỗ xuống dòng, trình duyệt không tự bẻ)."""
        spec = self.man["slots"].get(slot)
        if not spec:
            raise KeyError(f"Shop {self.shop} không có mẫu '{slot}' (có: {', '.join(self.man['slots'])})")
        src = (self.dir / spec["file"]).read_text(encoding="utf-8")
        # Font thiếu ký tự (UTM Avo/HelvetIns không có · – — •) → Chrome mượn font khác cho riêng ký tự đó → thay trước
        for a, b in self.man.get("replace", {}).items():
            lines, sub = [ln.replace(a, b) for ln in lines], sub.replace(a, b)
        text_html = "<br>".join(html.escape(ln) for ln in lines)
        filled = src.replace("{{text}}", text_html).replace("{{sub}}", html.escape(sub))
        # cùng thư mục để font tương đối tải được; tên riêng theo tiến trình → 2 job song song không ghi đè nhau
        tmp = self.dir / f"_render_tmp_{os.getpid()}_{id(self)}.html"
        self._tmp = tmp
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
        # Luôn nowrap: chỗ xuống dòng do renderer chọn (tại dấu ngắt câu) — trình duyệt tự bẻ thì ra kiểu
        # "…khoan, Chịu / lực tốt" (Sếp chê 20/10).
        self._page.evaluate("() => { document.getElementById('text').style.whiteSpace = 'nowrap'; }")

    def _fit(self, w: int, h: int, spec: dict, n_lines: int = 1) -> int:
        """Cỡ chữ lớn nhất vừa khung, -1 nếu không cỡ nào vừa. fs_min/fs_max (% chiều cao ô) là cho MỘT dòng →
        chia cho số dòng; không chia thì nới ô cao cho 2 dòng lại đẩy cỡ tối thiểu lên theo → càng nới càng tràn."""
        self._page.set_viewport_size({"width": max(w, 16), "height": max(h, 16)})
        self._page.evaluate(f"() => {{ const r = document.documentElement.style;"
                            f" r.setProperty('--w', '{w}px'); r.setProperty('--h', '{h}px'); }}")
        n = max(1, n_lines)
        return self._page.evaluate(_FIT_JS, [h * spec["fs_min"] / 100 / n, h * spec["fs_max"] / 100 / n])

    def covers(self, slot: str) -> bool:
        """Mẫu có nền đục (che được chữ Trung)? `covers: false` = chữ không nền, chỉ để chèn chữ mới."""
        return bool(self.man["slots"].get(slot, {}).get("covers", True))

    def render(self, slot: str, text: str, w: int, h: int, *, sub: str = "", min_px: int = 0,
               max_w: int | None = None, max_h: int | None = None) -> tuple[Image.Image, int, int]:
        """Trả (ảnh RGBA, w, h thực dùng). Nới w rồi h khi chữ < min_px hoặc không vừa."""
        spec = self.man["slots"][slot]
        max_w, max_h = max_w or w, max_h or h * 3
        explicit = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(explicit) > 1:  # đạo diễn tự xuống dòng bằng "\n"
            lines = explicit
        else:
            lines = [text.strip()]
        self._load(slot, lines, sub)
        nl = len(lines) + (1 if sub else 0)
        fs = self._fit(w, h, spec, nl)
        two = None if (spec.get("nowrap") or len(lines) > 1) else split_two(text)
        if two and not has_separator(text):
            # không có dấu ngắt câu: nới NGANG một dòng trước; chia đôi theo từ chỉ khi nới hết cỡ vẫn thiếu
            # (bản trước chia ngay → "Gỡ miếng cố định / tạm là dùng được", gãy giữa cụm từ)
            while (fs < 0 or fs < min_px) and w < max_w:
                w = min(max_w, round(w * 1.08) + 4)
                fs = self._fit(w, h, spec, nl)
        if two and (fs < 0 or fs < min_px):
            # một dòng không đủ cỡ chữ → hai dòng, tách tại dấu ngắt câu (Sếp 20/10)
            self._load(slot, two, sub)
            fs2 = self._fit(w, h, spec, nl + 1)
            if fs2 >= fs:
                lines, fs, nl = two, fs2, nl + 1
            else:
                self._load(slot, lines, sub)
                fs = self._fit(w, h, spec, nl)
        while (fs < 0 or fs < min_px) and w < max_w:
            w = min(max_w, round(w * 1.08) + 4)
            fs = self._fit(w, h, spec, nl)
        while (fs < 0 or fs < min_px) and h < max_h:
            h = min(max_h, round(h * 1.08) + 4)
            fs = self._fit(w, h, spec, nl)
        if fs < 0:
            raise ValueError(f"Chữ '{text}' không vừa mẫu {slot} kể cả khi nới tới {w}×{h} — rút câu")
        png = self._page.locator("#label").screenshot(omit_background=True)
        return Image.open(io.BytesIO(png)).convert("RGBA"), w, h


_SEPARATORS = [" · ", " • ", " - ", " – ", " — ", ". ", "! ", "? ", "; ", ": ", ", "]


def has_separator(text: str) -> bool:
    """Câu có dấu ngắt ở khoảng giữa (20–80% độ dài) để xuống dòng đẹp không."""
    text = " ".join(text.split())
    n = len(text)
    return any(0.2 * n <= i <= 0.8 * n for sep in _SEPARATORS for i in _find_all(text, sep))


def _find_all(text: str, sep: str) -> list[int]:
    out, start = [], 0
    while (i := text.find(sep, start)) >= 0:
        out.append(i)
        start = i + 1
    return out


def split_two(text: str) -> list[str] | None:
    """Chia câu dài thành 2 dòng: ưu tiên dấu ngắt câu mạnh nhất (· . ! ? ; : rồi ,), chọn chỗ gần giữa nhất,
    BỎ dấu ngắt ở chỗ xuống dòng ("Kệ treo tường không cần khoan · Chịu lực tốt" → 2 dòng). Không có dấu →
    chia theo từ sao cho 2 dòng dài gần bằng nhau (không để chữ mồ côi), chỉ khi câu ≥5 từ. Muốn tự quyết chỗ
    xuống dòng: đạo diễn ghi "\\n" trong text_vi."""
    text = " ".join(text.split())
    words = text.split(" ")
    if len(words) < 3:
        return None
    mid = len(text) / 2
    for sep in _SEPARATORS:
        idx, start = [], 0
        while (i := text.find(sep, start)) >= 0:
            idx.append(i)
            start = i + 1
        idx = [i for i in idx if 0.2 * len(text) <= i <= 0.8 * len(text)]  # đừng tách ra 1 dòng quá ngắn
        if idx:
            i = min(idx, key=lambda k: abs(k - mid))
            left = text[:i].rstrip()
            if sep.strip() in ".!?":  # giữ dấu kết câu ở cuối dòng 1, bỏ các dấu nối (· - ; : ,)
                left += sep.strip()
            right = text[i + len(sep):].strip()
            return [left, right[:1].upper() + right[1:]]  # dòng 2 là ý mới → viết hoa chữ đầu
    if len(words) < 5:  # câu ngắn không có dấu ngắt: giữ 1 dòng (nới ô) thay vì bẻ "Chịu / lực tốt"
        return None
    k = min(range(1, len(words)), key=lambda k: max(len(" ".join(words[:k])), len(" ".join(words[k:]))))
    return [" ".join(words[:k]), " ".join(words[k:])]


def preview_sheet(shop: str) -> Path:
    """Bảng xem trước mọi mẫu của shop với chữ mẫu → <thư mục mẫu>/_preview.png"""
    samples = {
        "caption": ("Kệ treo tường không cần khoan · Chịu lực tốt", "", 700, 80),
        "hook": ("Bồn rửa bừa bộn, đồ dùng không chỗ để?", "", 760, 100),
        "badge": ("Chịu lực tốt", "", 360, 90),
        "info": ("Chờ keo khô 48 giờ", "Trời lạnh: chờ 72 giờ", 520, 130),
        "outline-black": ("Lắp đặt chỉ 3 phút", "", 620, 110),
        "outline-red": ("Giảm 50% hôm nay", "", 620, 110),
    }
    tiles = []
    with TemplateRenderer(shop) as r:
        for slot in r.man["slots"]:
            text, sub, w, h = samples.get(slot, ("Chữ mẫu tiếng Việt", "", 560, 90))
            img, _, _ = r.render(slot, text, w, h, sub=sub, min_px=29, max_w=round(w * 1.15))  # 29px ≈ 3% khung 960
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
