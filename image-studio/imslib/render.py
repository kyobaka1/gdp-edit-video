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
        wm = next((m for m in ms if m.get("type") == "watermark"), None)
        if wm and info["wm"] and info["wm"]["lum"] > 0.6 and luminance(_mean(bare, wm["rect"])) > 0.45:
            pg.evaluate("document.getElementById('wm').classList.add('to-dark')")     # watermark sáng trên nền sáng → bản đậm
            if not info["wm"]["fixed"]:
                pg.evaluate("document.getElementById('wm').style.opacity = 0.16")
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
        qa.annotate(final, spec, ms, issues, job / "qa" / f"{key}.jpg")
        report = {"key": key, "kind": kind, "size": [W, H], "out": str(out.relative_to(job)), "tones": tones,
                  "logo": logo_note, "issues": issues,
                  "blocks": [{"id": m["id"], "type": m.get("type"), "rect_pct": [round(m["rect"][0] / W * 100, 1),
                              round(m["rect"][1] / H * 100, 1), round(m["rect"][2] / W * 100, 1), round(m["rect"][3] / H * 100, 1)],
                              **({"size_pt": m["got"]} if m.get("got") else {})} for m in ms]}
        (job / "qa" / f"{key}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
