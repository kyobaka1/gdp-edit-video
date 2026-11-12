"""layout.json (khối chữ theo %) → trang HTML: ảnh là nền, mọi thứ còn lại là lớp phủ theo nhận diện shop.

Người / agent viết layout CHỈ khai: khối gì, chữ gì, ở đâu, to cỡ nào. Màu, font, kiểu nhãn, logo, watermark do shop quyết
(ims/kit.py) — layout không ghi mã màu trừ khi cố ý (QA sẽ ghi chú "màu ngoài bảng màu shop")."""

import html
import json
import re
from pathlib import Path

from PIL import Image, ImageFilter

from . import UI
from .kit import luminance, rgb, tint_of

ANCHORS = {"top-left": (0, 0), "top-center": (.5, 0), "top-right": (1, 0), "center-left": (0, .5), "center": (.5, .5),
           "center-right": (1, .5), "bottom-left": (0, 1), "bottom-center": (.5, 1), "bottom-right": (1, 1),
           "top": (.5, 0), "bottom": (.5, 1), "left": (0, .5), "right": (1, .5)}
TEXT_TYPES = {"headline", "sub", "text", "pills", "badge", "stat", "callout", "dim", "spec", "list", "html"}
COLOR_TOKENS = {"heading", "sub", "on_dark", "on_light", "primary", "accent", "dark", "ink"}
DEFAULT_SIZE = {"headline": 60, "sub": 34, "text": 28, "pills": 40, "badge": 40, "stat": 90, "callout": 28, "dim": 26, "spec": 26,
                "list": 26, "html": 28}


def _uri(p: Path) -> str:
    return Path(p).resolve().as_uri()


def _rgba(c: str, a: float) -> str:
    r, g, b = rgb(c)
    return f"rgba({r},{g},{b},{a:.3f})"


def _mix(a: str, b: str, ka: float) -> str:
    ra, rb = rgb(a), rgb(b)
    return "#%02x%02x%02x" % tuple(round(ra[i] * ka + rb[i] * (1 - ka)) for i in range(3))


def _grad(g: dict | None, fallback: str) -> str:
    if not g:
        return fallback
    return f"linear-gradient({g.get('angle', 90)}deg, {', '.join(g['stops'])})"


def _color(theme: dict, value: str | None) -> str | None:
    if not value:
        return None
    if value in COLOR_TOKENS:
        return f"var(--c-{value.replace('_', '-')})"
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value
    raise SystemExit(f"Màu '{value}' không hợp lệ — dùng tên trong bảng màu shop {sorted(COLOR_TOKENS)} hoặc #rrggbb.")


def rich(text: str, caps: bool = False) -> str:
    """Chữ → HTML an toàn. `*cụm*` = nhấn màu shop; xuống dòng bằng \\n (giữ nguyên, CSS pre-line)."""
    text = text.upper() if caps else text
    out = html.escape(text, quote=False)
    return re.sub(r"\*(.+?)\*", r'<span class="hl">\1</span>', out)


def plain(text: str, caps: bool = False) -> str:
    return re.sub(r"\*(.+?)\*", r"\1", text.upper() if caps else text)


def logo_variants(theme: dict, tmp: Path, ink: str = "#161616") -> list[dict]:
    """Mỗi file logo của shop → bản cắt sát phần nhìn thấy + độ sáng + có phải thẻ đặc (đặt nền nào cũng đọc được).

    Logo chữ đơn sắc SÁNG (vd PHALEDO kem, LTENG trắng) có thêm bản `<tên>-ink`: cùng hình, tô màu mực đậm của ảnh → dùng
    trên nền sáng mà không cần shop phải có sẵn file logo tối."""
    out = []
    for name, f in theme["logo"]["files"].items():
        try:
            im = Image.open(f).convert("RGBA")
        except Exception:
            continue
        a = im.getchannel("A")
        bbox = a.point(lambda v: 255 if v > 24 else 0).getbbox()
        if not bbox:
            continue
        crop = im.crop(bbox)
        ca = crop.getchannel("A")
        cover = sum(1 for v in ca.resize((64, 64)).getdata() if v > 128) / 4096
        px = [p for p in crop.resize((64, 64)).getdata() if p[3] > 128]
        lum = sum(0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2] for p in px) / (255 * len(px)) if px else 0.5
        top_row = sum(1 for v in ca.crop((0, 0, crop.width, 1)).getdata() if v > 128) / crop.width
        dst = tmp / f"logo-{name}.png"
        crop.save(dst)
        v = {"name": name, "file": dst, "lum": lum, "solid": cover > 0.6, "hang": top_row > 0.8,
             "aspect": crop.width / crop.height, "bw": (bbox[2] - bbox[0]) / im.width, "top": bbox[1] / im.width,
             "rgb": tuple(round(sum(p[i] for p in px) / len(px)) for i in range(3)) if px else (128, 128, 128)}
        out.append(v)
        spread = max(max(p[i] for p in px) - min(p[i] for p in px) for i in range(3)) if px else 255
        if not v["solid"] and lum > 0.55 and spread < 90:          # chữ đơn sắc sáng → thêm bản tô mực đậm
            tinted = Image.new("RGBA", crop.size, rgb(ink) + (0,))
            tinted.putalpha(ca)
            dst2 = tmp / f"logo-{name}-ink.png"
            tinted.save(dst2)
            out.append({**v, "name": f"{name}-ink", "file": dst2, "lum": 0.05, "rgb": rgb(ink)})
    return out


def thin_watermark(file: Path, tmp: Path, ratio: float) -> Path:
    """Bào mảnh nét của ảnh watermark (giữ nguyên kiểu chữ logo): co kênh alpha vào trong `ratio` × chiều cao ảnh."""
    if not ratio:
        return file
    im = Image.open(file).convert("RGBA")
    big = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)          # phóng 3 lần cho mép mịn
    r = max(1, round(ratio * im.height * 3))
    alpha = big.getchannel("A").filter(ImageFilter.MinFilter(2 * r + 1)).filter(ImageFilter.GaussianBlur(0.8))
    big.putalpha(alpha)
    dst = tmp / f"wm-thin-{Path(file).stem}.png"
    big.resize((im.width * 2, im.height * 2), Image.LANCZOS).save(dst)
    return dst


def _block(b: dict, i: int, theme: dict, kind: str, default_font: str) -> tuple[str, str]:
    """1 khối → (html, css thêm)."""
    t = b.get("type")
    if t not in TEXT_TYPES:
        raise SystemExit(f"Khối #{i}: type '{t}' không có — dùng một trong {sorted(TEXT_TYPES)}.")
    bid = b.get("id") or f"{t}{i}"
    if t == "dim":                                       # đường kích thước: con số nằm giữa 2 đầu mút
        b = {**b, "x": (b["from"][0] + b["to"][0]) / 2, "y": (b["from"][1] + b["to"][1]) / 2, "anchor": "center"}
    if "x" not in b or "y" not in b:
        raise SystemExit(f"Khối '{bid}': thiếu x / y (toạ độ %, 0–100).")
    anchor = b.get("anchor", "center")
    if anchor not in ANCHORS:
        raise SystemExit(f"Khối '{bid}': anchor '{anchor}' không có — dùng {sorted(ANCHORS)}.")
    ax, ay = ANCHORS[anchor]
    size = float(b.get("size") or DEFAULT_SIZE[t])
    align = b.get("align") or ("left" if ax == 0 else "right" if ax == 1 else "center")
    style = [f"left:{b['x']}%", f"top:{b['y']}%", f"transform:translate({-ax * 100}%,{-ay * 100}%)",
             f"text-align:{align}", f"--fs:{size}"]
    if b.get("w"):
        style.append(f"width:{b['w']}%")
    else:
        style.append("width:max-content")            # khối sát mép phải không bị trình duyệt bó hẹp rồi tự co chữ
    col = _color(theme, b.get("color"))
    if col:
        style.append(f"--c:{col}")
        hexcol = b["color"] if b["color"].startswith("#") else theme["color"].get(b["color"])
        if hexcol:                                       # chữ ép màu: viền tự chọn trắng / đen cho tương phản với chính màu chữ
            style.append(f"--oc:{'#ffffff' if luminance(hexcol) < .4 else '#111111'}")
    fset = b.get("font") or default_font
    if fset not in theme["font"]["sets"]:
        raise SystemExit(f"Khối '{bid}': bộ font '{fset}' không nằm trong danh sách của shop {sorted(theme['font']['sets'])} "
                         f"(shop.json → image.fonts).")
    if b.get("font"):
        style += [f"--font-display:D_{fset}", f"--font-body:B_{fset}"]
    for k, em in (("edge", {"none": 0, "soft": .045, "bold": .1}), ("bolder", {})):
        if b.get(k) is not None:
            style.append(f"--{k}:{em.get(b[k], b[k])}")
    bg = b.get("bg")
    if bg:                                               # nền lót ngay dưới khối chữ
        bg = {} if bg is True else bg
        if bg.get("fill") == "brand":                    # tấm màu nhãn của shop (đặc, giữ nguyên dải màu nếu có)
            style.append("background:var(--badge-solid)")
        else:
            fill = _color(theme, bg.get("fill", "dark"))
            style.append(f"background:color-mix(in srgb, {fill} {round(float(bg.get('opacity', .6)) * 100)}%, transparent)")
            if bg.get("glass", True):
                style.append("backdrop-filter:blur(calc(var(--u)*14)) saturate(1.08)")
        style += [f"padding:calc(var(--u)*{bg.get('pad', 22)}) calc(var(--u)*{bg.get('pad_x', bg.get('pad', 22) * 1.5)})",
                  f"border-radius:calc(var(--u)*{bg.get('radius', 18)})", "--edge:0",
                  "box-shadow:0 calc(var(--u)*6) calc(var(--u)*20) rgba(0,0,0,.2)"]
    tone = b.get("tone") or theme["image"]["tone"]
    cls = ["b", t if t != "badge" else "pills", f"tone-{'light' if tone == 'auto' else tone}"]
    data = {"type": t, "fs": size, "fd": theme["font"]["sets"][fset]["display"], "fb": theme["font"]["sets"][fset]["body"]}
    if tone == "auto" and not col:
        data["auto"] = 1
    lines = b.get("lines", 2 if t == "headline" else 1 if t in ("sub", "pills", "badge", "dim") else 0)
    if lines:
        data["lines"] = lines
    if lines == 1 and t in ("headline", "sub", "text", "dim", "callout"):
        data["nowrap"] = ""
    if b.get("bold"):
        cls.append("bold")
    if b.get("display"):
        cls.append("disp")
    caps = bool(b.get("caps"))
    inner = ""

    if t in ("headline", "sub", "text"):
        txt = b.get("text", "")
        if t == "headline":
            st = b.get("style") or theme["image"]["headline"]
            if st not in ("plain", "outline", "plate", "plate-dark"):
                raise SystemExit(f"Khối '{bid}': style '{st}' không có — dùng plain · outline · plate · plate-dark.")
            cls += ["st-plate", "st-plate-dark"] if st == "plate-dark" else [f"st-{st}"]
            if theme.get("heading_gradient") and not st.startswith("plate"):
                cls.append("grad")
                mid = theme["heading_gradient"]["stops"][len(theme["heading_gradient"]["stops"]) // 2]
                inner = f'<span class="tx" data-color-dark="{mid}">{rich(txt, caps)}</span>'
            data["text"] = plain(txt, caps)
        inner = inner or f'<span class="tx">{rich(txt, caps)}</span>'
        if b.get("note"):
            inner = inner[:-7] + f"<small>{rich(b['note'])}</small></span>"
    elif t in ("pills", "badge"):
        items = b.get("items") or [b.get("text", "")]
        variant = b.get("variant") or theme["image"]["pill"]
        if variant == "auto":
            variant = "glass" if theme["badge"]["opacity"] < 1 else "solid"
        if b.get("dir") == "col":
            cls.append("col")
        if b.get("gap") is not None:
            style.append(f"--gap:{b['gap']}")
        sq = " sq" if (b.get("shape") or theme["image"]["pill_shape"]) == "square" else ""
        parts = []
        for x in items:                                  # mỗi nhãn có thể tự chọn kiểu: {"text": "…", "variant": "invert"}
            x = x if isinstance(x, dict) else {"text": str(x)}
            v = x.get("variant") or variant
            if v not in ("glass", "solid", "invert", "dark", "line"):
                raise SystemExit(f"Khối '{bid}': variant '{v}' không có — dùng glass · solid · invert · dark · line.")
            parts.append(f'<span class="pill {v}{sq}"><span class="tx">{rich(str(x.get("text", "")), caps)}</span></span>')
        inner = "".join(parts)
    elif t == "stat":                                    # CON SỐ TO: nhãn nhỏ phía trên + số rất lớn, chung một tấm nền
        v = b.get("variant") or "solid"
        if v not in ("solid", "invert", "dark"):
            raise SystemExit(f"Khối '{bid}': variant '{v}' không có — stat dùng solid · invert · dark.")
        label = f'<span class="tx lb">{rich(b["label"], caps)}</span>' if b.get("label") else ""
        rule = (" rule" if b.get("rule") else "") + (" even" if b.get("even") else "")   # even: 2 dòng cùng cỡ (vd DÁN TƯỜNG / KHOAN VÍT)
        foot = ""
        if b.get("foot"):                                # dải chân MÀU KHÁC gắn liền thẻ: thông số phụ (vd "NHÔM DÀY 1.2MM")
            note = f"<small>{rich(b['foot_note'])}</small>" if b.get("foot_note") else ""
            foot = f'<span class="ft"><span class="tx">{rich(b["foot"], caps)}{note}</span></span>'
        inner = f'<span class="card {v}{rule}">{label}<span class="tx val">{rich(str(b.get("value", "")))}</span>{foot}</span>'
    elif t == "callout":
        note = f"<small>{rich(b['note'])}</small>" if b.get("note") else ""
        inner = f'<span class="tx">{rich(b.get("text", ""), caps)}{note}</span>'
        if b.get("to"):
            data["to"] = json.dumps(b["to"])
    elif t == "dim":
        inner = f'<span class="tx">{rich(b.get("text", ""))}</span>'
        data["from"], data["to"] = json.dumps(b["from"]), json.dumps(b["to"])
    elif t == "spec":
        rows = "".join(f'<div class="row"><span class="k">{rich(str(k))}</span><span class="v">{rich(str(v))}</span></div>'
                       for k, v in b.get("rows", []))
        title = f'<div class="title">{rich(b["title"], caps)}</div>' if b.get("title") else ""
        inner = title + rows
    elif t == "list":
        marker = b.get("marker", "check")
        cls.append(marker)
        parts = []
        for n, it in enumerate(b.get("items", []), int(b.get("start", 1))):
            it = {"text": it} if isinstance(it, str) else it
            mk = f"{n:02d}" if marker == "number" else "✓" if marker == "check" else ""
            note = f"<small>{rich(it['note'])}</small>" if it.get("note") else ""
            parts.append(f'<div class="li"><span class="mk">{mk}</span><span class="tx">{rich(it["text"])}{note}</span></div>')
        inner = "".join(parts)
    elif t == "html":
        inner = b.get("html", "")

    attrs = " ".join(f'data-{k}="{html.escape(str(v), quote=True)}"' if v != "" else f"data-{k}" for k, v in data.items())
    return (f'<div id="{html.escape(bid)}" class="{" ".join(cls)}" style="{";".join(style)}" {attrs}>{inner}</div>',
            b.get("css", "") if t == "html" else "")


def page(spec: dict, theme: dict, base: Path, size: tuple[int, int], probe, tmp: Path) -> tuple[str, dict]:
    """Dựng trang cho 1 ảnh. `probe(x0,y0,x1,y1)` → màu trung bình vùng ảnh (toạ độ %). Trả (html, thông tin phụ)."""
    W, H = size
    kind = spec.get("kind", "product_image")
    c, bd, img = theme["color"], theme["badge"], theme["image"]
    ink = (tint_of(probe(0, 0, 100, 100), 0.15, 0.45) if img["ink"] == "auto"
           else img["ink"] if str(img["ink"]).startswith("#") else c["on_light"])
    f = theme["font"]
    fset = spec.get("font") or f["default"]
    if fset not in f["sets"]:
        raise SystemExit(f"Ảnh khai font '{fset}' — shop chỉ được dùng {sorted(f['sets'])} (shop.json → image.fonts).")
    root = {
        "--font-display": f"D_{fset}", "--font-body": f"B_{fset}", "--edge": img["edge"], "--bolder": img["bolder"],
        "--u": f"{W / 1000}px", "--c-heading": c["heading"], "--c-sub": c["sub"], "--c-on-dark": c["on_dark"],
        "--c-on-light": c["on_light"], "--c-primary": c["primary"], "--c-accent": c["accent"], "--c-dark": c["dark"],
        "--c-ink": ink, "--badge-solid": _grad(bd["gradient"], bd["bg"]), "--badge-glass": _rgba(bd["bg"], bd["opacity"]),
        "--badge-text": bd["text"], "--badge-border": bd["border"] or "transparent",
        "--badge-bw": f"{bd['border_pct'] / 100 * 1.6:.4f}", "--pill-ink": _rgba(ink, .80),
        "--pill-ink-border": _rgba(c["heading"], .5), "--radius": theme["radius_pct"],
        "--grad-heading": _grad(theme.get("heading_gradient"), c["primary"]),
        "--plate-bg": _grad(theme.get("heading_gradient"), c["primary"]), "--plate-fg": c["on_dark"],
        "--shadow-a": img["shadow"], "--tracking": img["tracking"],
        # màu nhấn `*cụm*`: màu accent của shop, tự làm sáng / đậm thêm nếu chìm vào nền
        "--hl-light": c.get("hl_on_dark") or (c["accent"] if luminance(c["accent"]) >= .22 else _mix(c["accent"], "#ffffff", .5)),
        # nhãn đảo màu (nền = màu chữ nhãn, chữ = màu nền nhãn) và nhãn đen
        "--badge-inv-bg": bd["text"], "--badge-inv-fg": bd["bg"], "--badge-dark-bg": "#141414",
        # màu NHẤN PHỤ (dải chân thẻ số…): layout / shop khai `pop: {"bg", "text"}`; không khai = bản đảo của nhãn
        "--pop-bg": (spec.get("pop") or img.get("pop") or {}).get("bg", bd["text"]),
        "--pop-fg": (spec.get("pop") or img.get("pop") or {}).get("text", bd["bg"]), "--badge-dark-fg": "#ffffff",
        "--hl-dark": c["accent"] if luminance(c["accent"]) <= .2 else _mix(c["accent"], ink, .58),
    }
    css = [f'@font-face{{font-family:D_{n};font-weight:800;src:url("{_uri(s["display"])}")}}'
           f'@font-face{{font-family:B_{n};font-weight:700;src:url("{_uri(s["bold"])}")}}'
           f'@font-face{{font-family:B_{n};font-weight:400;src:url("{_uri(s["body"])}")}}' for n, s in f["sets"].items()]
    css += [f'@font-face{{font-family:Fallback;font-weight:700;src:url("{_uri(f["fallback_bold"])}")}}',
           f'@font-face{{font-family:Fallback;font-weight:400;src:url("{_uri(f["fallback_regular"])}")}}',
           ":root{" + ";".join(f"{k}:{v}" for k, v in root.items()) + "}",
           (UI / "base.css").read_text(encoding="utf-8")]
    body = [f'<img id="base" src="{_uri(base)}">']

    # KHÔNG CHỈNH MÀU ẢNH (Sếp 12/11): chỉ thêm chữ + logo lên ảnh đã cung cấp. Không có lớp tối dần / lớp phủ màu rộng.
    if spec.get("scrims"):
        raise SystemExit("`scrims` đã bỏ (Sếp 12/11: không chỉnh màu ảnh — chỉ thêm chữ, logo). Để chữ nổi: để `tone` tự chọn theo nền, "
                         "dùng tiêu đề `style` plate / plate-dark / outline, nhãn (`pills`), hoặc nền lót ôm chữ (`bg`).")
    for p in spec.get("panels") or []:
        if float(p["w"]) * float(p["h"]) > 2500:
            raise SystemExit("`panels`: tấm nền phủ hơn 25% ảnh là đổi màu ảnh (Sếp 12/11 không cho) — thu nhỏ vừa khối chữ, hoặc dùng `bg`.")
        if p.get("fill") == "brand":
            back = f'background:var(--badge-solid);opacity:{float(p.get("opacity", 1))}'
        else:
            back = (f'background:color-mix(in srgb, {_color(theme, p.get("fill", "dark"))} '
                    f'{round(float(p.get("opacity", .55)) * 100)}%, transparent)')
        body.append(f'<div class="panel{" glass" if p.get("glass", True) and p.get("fill") != "brand" else ""}" '
                    f'style="left:{p["x"]}%;top:{p["y"]}%;width:{p["w"]}%;height:{p["h"]}%;--pr:{p.get("radius", 18)};{back}"></div>')

    info = {"logo": None, "wm": None, "ink": ink, "font": fset}

    wm = spec.get("watermark", img["watermark"].get(kind, True))
    wfile = theme["watermark"]["file"]
    if wm and theme["watermark"]["mode"] == "text" and theme["watermark"]["text"]:
        # dải chữ lặp tên shop, trắng mờ, vắt ngang sản phẩm (kiểu ảnh thật của shop GDP)
        wm = {} if wm is True else wm
        keep = (spec.get("keep") or [[30, 35, 70, 85]])[0]
        y, op = wm.get("y", (keep[1] + keep[3]) / 2), wm.get("opacity", theme["watermark"]["opacity"])
        txt = "  -  ".join([html.escape(theme["watermark"]["text"].upper())] * 8)
        body.append(f'<div id="wm" class="wm text" data-type="watermark" style="top:{y}%;opacity:{op};'
                    f'--fs:{wm.get("size", 30)}">{txt}</div>')
        info["wm"] = {"strip": True, "opacity": op, "fixed": "opacity" in wm, "lum": 1.0}
    elif wm and wfile:
        wm = {} if wm is True else wm
        im = Image.open(wfile)
        strip = im.width / im.height >= 5
        keep = (spec.get("keep") or [[30, 35, 70, 85]])[0]
        if strip:
            x, y, w, op = 50, wm.get("y", 79), wm.get("w", 105), wm.get("opacity", theme["watermark"]["opacity"])
            st = f"left:{x}%;top:{y}%;width:{w}%;transform:translateX(-50%)"
        else:
            x, y = wm.get("x", (keep[0] + keep[2]) / 2), wm.get("y", (keep[1] + keep[3]) / 2)
            w, op = wm.get("w", img["watermark_width_pct"]), wm.get("opacity", theme["watermark"]["opacity"])
            st = f"left:{x}%;top:{y}%;width:{w}%;transform:translate(-50%,-50%)"
        body.append(f'<img id="wm" class="wm" data-type="watermark" src="{_uri(thin_watermark(wfile, tmp, img["watermark_thin"]))}" '
                    f'style="{st};opacity:{op}">')
        px = [q for q in im.convert("RGBA").resize((96, max(1, round(96 * im.height / im.width)))).getdata() if q[3] > 40]
        info["wm"] = {"strip": strip, "opacity": op, "fixed": "opacity" in wm,
                      "lum": sum(.2126 * q[0] + .7152 * q[1] + .0722 * q[2] for q in px) / (255 * len(px)) if px else .5}

    extra_css = []
    for i, b in enumerate(spec.get("blocks") or [], 1):
        h, x = _block(b, i, theme, kind, fset)
        body.append(h)
        if x:
            extra_css.append(x)
    body.append('<svg id="lines" xmlns="http://www.w3.org/2000/svg"></svg>')

    lg = spec.get("logo", img["logo"].get(kind, True))
    variants = logo_variants(theme, tmp, ink) if lg else []
    if lg and variants:
        lg = {} if lg is True else {"file": lg} if isinstance(lg, str) else lg
        ref = next((v for v in variants if v["name"] == "kit"), variants[0])
        vis_w = lg.get("w", (img.get("logo_width_pct") or theme["logo"]["width_pct"]) * ref["bw"])            # bề rộng phần logo NHÌN THẤY (% rộng ảnh)
        top_w = ref["top"] * theme["logo"]["width_pct"]                        # lề trên theo cách nhân sự đặt (% rộng ảnh)
        if top_w < .5:                                                         # thẻ logo đặc: treo sát mép trên như nhân sự đặt
            top_w = 0 if ref["hang"] else img["logo_margin_pct"]
        place = lg.get("placement") or img.get("logo_placement") or theme["logo"]["placement"]
        mx = img["logo_margin_pct"]
        x = lg.get("x", {"top-left": mx + vis_w / 2, "top-right": 100 - mx - vis_w / 2}.get(place, 50))
        y = lg.get("y", top_w * W / H)                                         # → % chiều cao
        body.append(f'<img id="logo" class="logo" data-type="logo" src="{_uri(ref["file"])}" '
                    f'style="left:{x}%;top:{y}%;width:{vis_w}%;transform:translateX(-50%)">')
        info["logo"] = {"variants": variants, "pick": lg.get("file"), "ref": ref["name"]}

    doc = (f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><style>{"".join(css)}{"".join(extra_css)}</style>'
           f'</head><body><div id="stage">{"".join(body)}</div><script>{(UI / "page.js").read_text(encoding="utf-8")}'
           f'</script></body></html>')
    return doc, info
