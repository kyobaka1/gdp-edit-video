"""Công cụ soát bằng mắt: lưới toạ độ + vùng trống, ảnh so Trung gốc | sạch | final, ảnh mẫu khối của shop."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

from . import FONTS, JOBS, KINDS, SHOPS, kit


def _font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / "BeVietnamPro" / "BeVietnamPro-Bold.ttf"), px)


def grid_zoom(image: Path, dst: Path, box: tuple) -> Path:
    """Phóng to vùng [x0, y0, x1, y1] (%) của ảnh, vạch mỗi 2% (đậm mỗi 10%) ghi toạ độ % của ẢNH GỐC → đo ô icon, chi tiết nhỏ."""
    im = Image.open(image).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = box
    crop = im.crop((round(x0 / 100 * W), round(y0 / 100 * H), round(x1 / 100 * W), round(y1 / 100 * H)))
    k = 1400 / crop.width
    crop = crop.resize((1400, max(1, round(crop.height * k))), Image.LANCZOS)
    d = ImageDraw.Draw(crop, "RGBA")
    f = _font(15)
    for axis, (lo, hi, size) in enumerate(((x0, x1, crop.width), (y0, y1, crop.height))):
        v = int(lo // 2 * 2)
        while v <= hi:
            if v >= lo:
                p = (v - lo) / (hi - lo) * size
                major = v % 10 == 0
                xy = [p, 0, p, crop.height] if axis == 0 else [0, p, crop.width, p]
                d.line(xy, fill=(0, 0, 0, 110), width=3 if major else 1)
                d.line(xy, fill=(255, 255, 255, 230 if major else 120), width=1)
                d.text((p + 3, 3) if axis == 0 else (3, p + 2), f"{'x' if axis == 0 else 'y'}{v}", font=f,
                       fill=(255, 255, 0, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
            v += 2
    dst.parent.mkdir(parents=True, exist_ok=True)
    crop.save(dst, quality=90)
    return dst


def grid(image: Path, dst: Path) -> tuple[Path, str]:
    """Ảnh + lưới 10% có số + tô đỏ các ô 'bận' (nhiều chi tiết = sản phẩm / vật thể). Trả (ảnh, bảng chữ).

    Bảng chữ: mỗi ô 5% — '#' bận, '.' trống tối, ':' trống sáng → biết chỗ đặt chữ và nên dùng chữ sáng hay đậm."""
    im = Image.open(image).convert("RGB")
    W, H = im.size
    cols = 20
    rows = max(1, round(cols * H / W))
    g = im.convert("L").resize((cols * 12, rows * 12))
    edges = g.filter(ImageFilter.FIND_EDGES)
    busy, lum = [], []
    for r in range(rows):
        for c in range(cols):
            box = (c * 12 + 1, r * 12 + 1, c * 12 + 11, r * 12 + 11)
            busy.append(ImageStat.Stat(edges.crop(box)).mean[0])
            lum.append(ImageStat.Stat(g.crop(box)).mean[0] / 255)
    cut = max(9.0, sorted(busy)[len(busy) * 55 // 100])
    view = im.copy()
    view.thumbnail((1400, 1400))
    vw, vh = view.size
    d = ImageDraw.Draw(view, "RGBA")
    lines = []
    for r in range(rows):
        row = ""
        for c in range(cols):
            b = busy[r * cols + c] > cut
            row += "#" if b else (":" if lum[r * cols + c] > .55 else ".")
            if b:
                d.rectangle([c * vw / cols, r * vh / rows, (c + 1) * vw / cols, (r + 1) * vh / rows], fill=(255, 40, 40, 50))
        lines.append(f"  y{round(r * 100 / rows):>3}% {row}")
    f = _font(max(14, vw // 60))
    for k in range(1, 20, 2):                                # vạch phụ 5% (mảnh)
        d.line([k * vw / 20, 0, k * vw / 20, vh], fill=(255, 255, 255, 70), width=1)
        d.line([0, k * vh / 20, vw, k * vh / 20], fill=(255, 255, 255, 70), width=1)
    for k in range(1, 10):
        x, y = k * vw / 10, k * vh / 10
        for xy in ([x, 0, x, vh], [0, y, vw, y]):
            d.line(xy, fill=(0, 0, 0, 120), width=3)
            d.line(xy, fill=(255, 255, 255, 220), width=1)
        for pos, txt in (((x + 4, 4), f"x{k * 10}"), ((4, y + 4), f"y{k * 10}")):
            d.text(pos, txt, font=f, fill=(255, 255, 0, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    dst.parent.mkdir(parents=True, exist_ok=True)
    view.save(dst, quality=88)
    head = f"  {W}×{H} ({W / H:.2f}) · mỗi ký tự = ô 5% bề rộng · # bận (sản phẩm/vật thể) · '.' trống nền TỐI · ':' trống nền SÁNG\n" \
           f"        x0%{' ' * 7}x50%{' ' * 6}x100%"
    return dst, head + "\n" + "\n".join(lines)


def sheet(job: Path, meta: dict, layout: dict, per_page: int = 6) -> list[Path]:
    """Ảnh so từng hàng: Trung gốc | sạch (nền) | final. Nhiều ảnh → nhiều trang."""
    keys = list(layout["images"])
    cw, pad, head = 440, 12, 34
    f, out = _font(18), []
    for page in range(0, len(keys), per_page):
        chunk = keys[page:page + per_page]
        cells = []
        for key in chunk:
            im = meta["images"].get(key) or {}
            row = []
            for rel in (im.get("src"), layout["images"][key].get("base"), f"out/{key}.jpg"):
                p = job / rel if rel else None
                if p and p.is_file():
                    t = Image.open(p).convert("RGB")
                    t.thumbnail((cw, cw * 2))
                    row.append(t)
                else:
                    row.append(None)
            cells.append((key, im.get("kind") or layout["images"][key].get("kind"), row))
        heights = [max((t.height for t in row if t), default=120) for _, _, row in cells]
        sh = Image.new("RGB", (3 * cw + 4 * pad, sum(heights) + (head + pad) * len(cells) + pad), (32, 32, 34))
        d = ImageDraw.Draw(sh)
        y = pad
        for (key, kind, row), h in zip(cells, heights):
            d.text((pad, y + 6), f"{key} · {KINDS.get(kind, kind)}", font=f, fill=(255, 220, 90))
            for c, label in enumerate(("Trung gốc", "đã xoá chữ (nền)", "FINAL")):
                lw = d.textlength(label, font=_font(14))
                d.text((pad + c * (cw + pad) + cw - lw, y + 10), label, font=_font(14), fill=(170, 170, 170))
            y += head
            for c, t in enumerate(row):
                x = pad + c * (cw + pad)
                if t:
                    sh.paste(t, (x, y))
                else:
                    d.rectangle([x, y, x + cw, y + h], outline=(80, 80, 80))
                    d.text((x + 12, y + 12), "(chưa có)", font=_font(14), fill=(120, 120, 120))
            y += h + pad
        p = job / (f"sheet-{page // per_page + 1}.jpg" if len(keys) > per_page else "sheet.jpg")
        sh.save(p, quality=86)
        out.append(p)
    return out


def kit_demo(shop: str) -> Path:
    """Ảnh mẫu: mọi loại khối theo nhận diện shop, trên nền tối và nền sáng → `assets/shops/<shop>/image/_demo.jpg`."""
    from .render import Studio
    theme = kit.load(shop)
    job = JOBS / f"_demo-{shop}"
    (job / "clean").mkdir(parents=True, exist_ok=True)
    W = 1200
    for name, a, b in (("dark", (58, 44, 38), (20, 18, 18)), ("light", (247, 240, 228), (214, 196, 170))):
        im = Image.new("RGB", (W, W))
        px = im.load()
        for y in range(W):
            t = y / W
            col = tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))
            for x in range(W):
                px[x, y] = col
        im.save(job / "clean" / f"{name}.png")
    blocks = [
        {"type": "headline", "text": "TIÊU ĐỀ *BÁN HÀNG*\nHAI DÒNG", "x": 50, "y": 21, "w": 88, "size": 62},
        {"type": "sub", "text": "Dòng phụ ngắn, nêu số liệu thật của sản phẩm", "x": 50, "y": 33.5, "w": 88, "size": 30},
        {"type": "pills", "items": ["1 ĐỔI 1", "180 NGÀY"], "x": 50, "y": 43, "size": 44},
        {"type": "callout", "text": "Nắp gỗ keo", "note": "kín khí, chống ẩm", "x": 8, "y": 56, "anchor": "top-left", "size": 26, "to": [46, 66]},
        {"type": "dim", "text": "12 cm", "from": [58, 54], "to": [58, 74], "size": 24},
        {"type": "list", "items": ["Thuỷ tinh borosilicate", "Kèm thìa gỗ", "An toàn thực phẩm"], "x": 66, "y": 54, "anchor": "top-left", "w": 30, "size": 24},
        {"type": "spec", "title": "THÔNG SỐ", "rows": [["Chất liệu", "Thuỷ tinh + gỗ keo"], ["Dung tích", "450 ml"]],
         "x": 8, "y": 77, "anchor": "top-left", "w": 44, "size": 24, "bg": {"fill": "dark", "opacity": 0.5}},
        {"type": "headline", "text": "TIÊU ĐỀ VIỀN", "x": 77, "y": 80, "size": 40, "lines": 1, "style": "outline"},
        {"type": "headline", "text": "TIÊU ĐỀ THANH NỀN", "x": 77, "y": 90, "size": 34, "lines": 1, "style": "plate"},
    ]
    layout = {"images": {n: {"kind": "cover", "base": f"clean/{n}.png", "watermark": {"y": 47}, "blocks": blocks} for n in ("dark", "light")}}
    (job / "job.json").write_text(json.dumps({"job": job.name, "shop": shop, "images": {}}, ensure_ascii=False), encoding="utf-8")
    (job / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=1), encoding="utf-8")
    with Studio() as st:
        for n in ("dark", "light"):
            st.render(job, n, layout["images"][n], theme)
    out = Image.new("RGB", (W * 2, W))
    for i, n in enumerate(("dark", "light")):
        out.paste(Image.open(job / "out" / f"{n}.jpg"), (i * W, 0))
    out.thumbnail((2000, 1000))
    dst = SHOPS / (theme["kit_from"] or shop) / "image" / "_demo.jpg"
    dst.parent.mkdir(exist_ok=True)
    out.save(dst, quality=88)

    # bảng so các BỘ FONT shop được dùng (cùng một câu, nền tối | nền sáng) → `_fonts.jpg`
    sets = list(theme["font"]["sets"])
    rh = 300
    for name in ("dark", "light"):
        Image.open(job / "clean" / f"{name}.png").resize((W, rh * len(sets))).save(job / "clean" / f"f-{name}.png")
    fb = []
    for i, n in enumerate(sets):
        y0 = 100 * i / len(sets)
        step = 100 / len(sets)
        fb += [{"type": "text", "text": n + (" (mặc định)" if i == 0 else ""), "x": 4, "y": y0 + step * .12, "anchor": "center-left", "size": 20, "font": sets[0]},
               {"type": "headline", "text": "MỘT THÌA LÀ VỪA 180 NGÀY", "x": 50, "y": y0 + step * .36, "size": 58, "lines": 1, "font": n},
               {"type": "sub", "text": "Hũ đường thuỷ tinh nắp gỗ keo, thêm nét ấm cho gian bếp", "x": 50, "y": y0 + step * .6, "size": 28, "font": n},
               {"type": "pills", "items": ["1 ĐỔI 1", "KÍN KHÍ CHỐNG ẨM"], "x": 50, "y": y0 + step * .82, "size": 30, "font": n}]
    fl = {n: {"kind": "product_image", "base": f"clean/f-{n}.png", "logo": False, "watermark": False, "blocks": fb} for n in ("dark", "light")}
    with Studio() as st:
        for n in ("dark", "light"):
            st.render(job, f"f-{n}", fl[n], theme)
    out = Image.new("RGB", (W * 2, rh * len(sets)))
    for i, n in enumerate(("dark", "light")):
        out.paste(Image.open(job / "out" / f"f-{n}.jpg"), (i * W, 0))
    out.thumbnail((2000, 2000))
    out.save(dst.with_name("_fonts.jpg"), quality=88)
    return dst
