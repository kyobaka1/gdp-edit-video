"""Chụp trang HTML thành ảnh final bằng Chrome (Playwright) + đo số liệu cho bộ kiểm.

Mỗi ảnh chụp 3 lượt trên CÙNG một trang: (1) nền trần — để chọn tông chữ, logo sáng / tối, watermark; (2) nền không chữ — để
đo tương phản thật dưới từng dòng chữ (có cả nhãn, nền lót); (3) final. Ảnh ra giữ nguyên kích thước ảnh nền."""

import io
import json
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from . import compose, qa
from .kit import contrast, luminance


def _mean(im: Image.Image, box) -> tuple:
    x, y, w, h = box
    b = (max(0, int(x)), max(0, int(y)), min(im.width, int(x + w) + 1), min(im.height, int(y + h) + 1))
    if b[2] <= b[0] or b[3] <= b[1]:
        return 128, 128, 128
    c = im.crop(b).convert("RGB")
    c.thumbnail((48, 48))
    px = list(c.getdata())
    return tuple(sum(p[i] for p in px) / len(px) for i in range(3))


class Studio:
    """Giữ một Chrome cho cả job (mở 1 lần, dựng nhiều ảnh)."""

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(channel="chrome", headless=True)
        self._page = self._browser.new_page(device_scale_factor=1)
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def _shot(self) -> Image.Image:
        return Image.open(io.BytesIO(self._page.screenshot(type="png"))).convert("RGB")

    @staticmethod
    def _shopee_preview(final: Image.Image, dst: Path) -> Path | None:
        """Ảnh bìa như khách thấy trên Shopee: đè khung chiến dịch mẫu lên, đặt cạnh bản CỠ TEM (≈ ô lưới trên điện thoại)."""
        frame_file = Path(__file__).resolve().parent.parent / "ui" / "shopee-frame.png"
        if not frame_file.is_file():
            return None
        big = final.convert("RGB").resize((640, 640), Image.LANCZOS)
        fr = Image.open(frame_file).convert("RGBA").resize((640, 640), Image.LANCZOS)
        big.paste(fr, (0, 0), fr)
        small = big.resize((190, 190), Image.LANCZOS)
        out = Image.new("RGB", (640 + 190 + 30, 640), (245, 245, 245))
        out.paste(big, (0, 0))
        out.paste(small, (640 + 20, 0))
        out.save(dst, quality=90)
        return dst

    def _place_logo(self, spec: dict, info: dict, ms: list, W: int, H: int) -> str | None:
        """Logo vướng chữ ở chỗ mặc định → tự dời sang chỗ trống khác trên mép trên (giữa → trái → phải).

        Sếp 12/11: chữ đặt theo bố cục bản gốc, LOGO linh hoạt theo chữ. Chỉ chạy khi layout không tự ghim logo
        (`logo` có `x` / `placement`). Chấm từng chỗ: đè chữ (nặng nhất) → đè sản phẩm `keep` → ưu tiên chỗ mặc định.
        Trả tên chỗ mới (top-left / top-center / top-right) hoặc None nếu giữ nguyên."""
        lg = spec.get("logo")
        if not info.get("logo") or (isinstance(lg, dict) and ("x" in lg or "placement" in lg)):
            return None
        logo = next((m for m in ms if m.get("type") == "logo"), None)
        if not logo:
            return None
        lx, ly, lw, lh = logo["rect"]
        gap_x, gap_y = 0.015 * W, 0.022 * W                 # khe tối thiểu quanh logo (QA cảnh báo "sát logo" khi < 2%)
        boxed = ("pills", "badge", "spec", "html")
        rects = []
        for m in ms:
            if m.get("type") in ("logo", "watermark"):
                continue
            b = next((x for x in spec.get("blocks") or [] if x.get("id") == m["id"]), {})
            rows = [r for t in m["texts"] for r in t["rows"]]
            if m.get("type") in boxed or b.get("bg") or b.get("style", "").startswith("plate") or not rows:
                rows = [m["rect"]]
            rects += rows
        keep = [(k[0] / 100 * W, k[1] / 100 * H, (k[2] - k[0]) / 100 * W, (k[3] - k[1]) / 100 * H) for k in spec.get("keep") or []]

        def hit(a, b):
            w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
            h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
            return w * h if w > 0 and h > 0 else 0.0

        mx = 0.025 * W                                      # lề an toàn mép ảnh
        here = lx + lw / 2
        spots = [("hiện tại", here), ("top-center", W / 2), ("top-left", mx + lw / 2), ("top-right", W - mx - lw / 2)]
        best = None
        for order, (name, cx) in enumerate(spots):
            r = (cx - lw / 2 - gap_x, ly, lw + 2 * gap_x, lh + gap_y)
            score = (sum(hit(r, t) for t in rects), sum(hit((cx - lw / 2, ly, lw, lh), k) for k in keep), order)
            if best is None or score < best[0]:
                best = (score, name, cx)
        if best[1] == "hiện tại" or abs(best[2] - here) < 1:
            return None
        self._page.evaluate("([x]) => { document.getElementById('logo').style.left = x + '%'; }", [best[2] / W * 100])
        return best[1]

    def render(self, job: Path, key: str, spec: dict, theme: dict) -> dict:
        base = job / spec["base"]
        if not base.is_file():
            raise SystemExit(f"[{key}] không thấy ảnh nền {base}")
        src = Image.open(base)
        W, H = src.size
        small = src.convert("RGB").copy()
        small.thumbnail((240, 240))

        def probe(x0, y0, x1, y1):
            return _mean(small, (x0 / 100 * small.width, y0 / 100 * small.height,
                                 (x1 - x0) / 100 * small.width, (y1 - y0) / 100 * small.height))

        tmp = job / "_tmp"
        tmp.mkdir(exist_ok=True)
        kind = spec.get("kind", "product_image")
        doc, info = compose.page(spec, theme, base, (W, H), probe, tmp)
        page_file = job / "html" / f"{key}.html"
        page_file.parent.mkdir(exist_ok=True)
        page_file.write_text(doc, encoding="utf-8")

        pg = self._page
        pg.set_viewport_size({"width": W, "height": H})
        pg.goto(page_file.resolve().as_uri())
        bad = pg.evaluate("""async () => {
            await Promise.all([...document.fonts].map(f => f.load().catch(() => null)));
            await document.fonts.ready;
            await Promise.all([...document.images].map(i => i.decode().catch(() => null)));
            return [...document.fonts].filter(f => f.status !== 'loaded').map(f => f.family + ' ' + f.weight);
        }""")
        if bad:
            raise SystemExit(f"[{key}] không tải được font: {', '.join(bad)} — kiểm assets/fonts/")
        pg.evaluate("IMS.fit()")

        # --- lượt 1: nền trần (ẩn mọi khối) → chọn tông chữ / logo / watermark theo nền thật ---
        pg.add_style_tag(content="body.bare .b, body.bare .logo, body.bare .wm, body.bare #lines{visibility:hidden}")
        pg.evaluate("document.body.classList.add('bare')")
        bare = self._shot()
        pg.evaluate("document.body.classList.remove('bare')")
        ms = pg.evaluate("IMS.measure()")
        logo_moved = self._place_logo(spec, info, ms, W, H)
        if logo_moved:
            ms = pg.evaluate("IMS.measure()")
        blocks = {b.get("id") or f"{b['type']}{i}": b for i, b in enumerate(spec.get("blocks") or [], 1)}
        light, dark = theme["color"]["heading"], info["ink"]
        tones = {}
        for m in ms:
            b = blocks.get(m["id"])
            if b is None or (b.get("tone") or theme["image"]["tone"]) != "auto" or b.get("color"):
                continue
            rows = [r for t in m["texts"] for r in t["rows"]] or [m["rect"]]
            x0, y0 = min(r[0] for r in rows), min(r[1] for r in rows)
            x1, y1 = max(r[0] + r[2] for r in rows), max(r[1] + r[3] for r in rows)
            under = _mean(bare, (x0, y0, x1 - x0, y1 - y0))
            bg = b.get("bg")
            if bg:                                              # nền lót: trộn màu lót với ảnh theo độ đục
                bg = {} if bg is True else bg
                fill = {"ink": info["ink"], "brand": theme["badge"]["bg"]}.get(bg.get("fill", "dark")) \
                    or theme["color"].get(bg.get("fill", "dark"), bg.get("fill"))
                a = 1.0 if bg.get("fill") == "brand" else float(bg.get("opacity", .6))
                fr = (int(fill[1:3], 16), int(fill[3:5], 16), int(fill[5:7], 16))
                under = tuple(fr[i] * a + under[i] * (1 - a) for i in range(3))
            tone = "light" if contrast(light, under) >= contrast(dark, under) else "dark"
            if b["type"] in ("pills", "badge") and theme["badge"]["opacity"] >= 1:
                tone = "light"                                  # nhãn đặc tự mang nền — không đổi theo ảnh
            elif b["type"] in ("pills", "badge"):               # nhãn kính mờ: nền nhãn = màu nhãn pha với ảnh theo độ đục
                bd = theme["badge"]
                br = (int(bd["bg"][1:3], 16), int(bd["bg"][3:5], 16), int(bd["bg"][5:7], 16))
                glass = tuple(br[i] * bd["opacity"] + under[i] * (1 - bd["opacity"]) for i in range(3))
                if contrast(bd["text"], glass) < 4.0:           # chữ nhãn chìm trên kính ở nền này → nhãn nền đậm chữ sáng
                    tone = "dark"
            tones[m["id"]] = tone
            pg.evaluate("([i, t]) => IMS.setTone(i, t)", [m["id"], tone])

        logo_note = None
        lg = next((m for m in ms if m.get("type") == "logo"), None)
        if lg and info["logo"]:
            under = _mean(bare, lg["rect"])
            vs = info["logo"]["variants"]
            pick = next((v for v in vs if v["name"] == info["logo"]["pick"]), None)
            if info["logo"]["pick"] and not pick:
                raise SystemExit(f"[{key}] logo '{info['logo']['pick']}' không có — shop có: {[v['name'] for v in vs]}")
            if not pick:
                ref = next(v for v in vs if v["name"] == info["logo"]["ref"])
                score = {v["name"]: (21.0 if v["solid"] else contrast(v["rgb"], under)) for v in vs}
                # ưu tiên đúng logo nhân sự dùng trên app (ref) → bản tô mực của nó → file nào rõ nhất
                own = [v for v in vs if v["name"] in (ref["name"], ref["name"] + "-ink") and score[v["name"]] >= 2.6]
                pick = own[0] if own else max(vs, key=lambda v: score[v["name"]])
            pg.evaluate("([s]) => IMS.setSrc('logo', s)", [pick["file"].resolve().as_uri()])
            c = 21.0 if pick["solid"] else contrast(pick["rgb"], under)
            logo_note = {"file": pick["name"], "contrast": round(c, 1)}
            if logo_moved:
                logo_note["moved"] = logo_moved
        wm = next((m for m in ms if m.get("type") == "watermark"), None)
        if wm and info["wm"] and info["wm"]["lum"] > 0.6 and luminance(_mean(bare, wm["rect"])) > 0.45:
            pg.evaluate("document.getElementById('wm').classList.add('to-dark')")     # watermark sáng trên nền sáng → bản đậm
            if not info["wm"]["fixed"]:
                pg.evaluate("document.getElementById('wm').style.opacity = 0.10")
        pg.evaluate("IMS.fit(); IMS.drawLines()")
        pg.evaluate("document.images.logo ? document.images.logo.decode().catch(() => null) : null")

        # --- lượt 2: nền không chữ (đo tương phản) · lượt 3: final ---
        pg.evaluate("document.body.classList.add('notext')")
        nobg = self._shot()
        pg.evaluate("document.body.classList.remove('notext')")
        ms = pg.evaluate("IMS.measure()")
        for m in ms:                                            # chữ dải màu: lấy màu giữa dải làm màu đo
            for t in m["texts"]:
                if t.get("gradColor"):
                    t["color"] = t["gradColor"]
        final = self._shot()
        if final.size != (W, H):
            final = final.resize((W, H), Image.LANCZOS)
        out = job / "out" / f"{key}.jpg"
        out.parent.mkdir(exist_ok=True)
        final.save(out, "JPEG", quality=95, subsampling=0, optimize=True)

        issues = qa.check(spec, theme, kind, ms, nobg, final.size, (W, H))
        if logo_note and logo_note["contrast"] < 2.0:
            issues.append({"level": "CẢNH BÁO", "id": "logo", "msg": f"logo mờ trên nền này (tương phản {logo_note['contrast']}) "
                           "— chỉ định file logo khác (khai `logo.file`) hoặc dời logo"})
        if logo_moved:
            issues.append({"level": "GHI CHÚ", "id": "logo", "msg": f"logo vướng chữ ở chỗ mặc định → tự dời sang {logo_moved} "
                           "(muốn ghim: khai `logo.placement` / `logo.x`)"})
        qa.annotate(final, spec, ms, issues, job / "qa" / f"{key}.jpg", theme)
        tem = self._shopee_preview(final, job / "qa" / f"{key}.tem.jpg") if kind == "cover" else None
        report = {"key": key, "kind": kind, "size": [W, H], "out": str(out.relative_to(job)), "tones": tones,
                  "logo": logo_note, "issues": issues, "tem": str(tem.relative_to(job)) if tem else None,
                  "blocks": [{"id": m["id"], "type": m.get("type"), "rect_pct": [round(m["rect"][0] / W * 100, 1),
                              round(m["rect"][1] / H * 100, 1), round(m["rect"][2] / W * 100, 1), round(m["rect"][3] / H * 100, 1)],
                              **({"size_pt": m["got"]} if m.get("got") else {})} for m in ms]}
        (job / "qa" / f"{key}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
