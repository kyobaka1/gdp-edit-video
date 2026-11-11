"""Bộ nhận diện ẢNH của shop — dùng chung `assets/shops/<shop>/` với video editor.

Ba nguồn, gộp theo thứ tự (cái sau đè cái trước):
  1. `shop.json` (hồ sơ shop của video studio): bảng màu, font, logo có sẵn, giọng văn.
  2. `image/kit.json` — brand kit lấy từ app PluSor (Shop Manager): kiểu bìa, màu tiêu đề, nhãn (badge), logo + watermark
     đúng file nhân sự đang dùng trong Editor. Đồng bộ bằng `ims.py kit sync <shop>` (không sửa tay — sync ghi đè).
  3. `shop.json` mục `"image"` — tinh chỉnh RIÊNG cho ảnh do studio đặt (sửa tay được, sync không đụng).

Shop chưa có kit riêng → mượn shop khai ở `templates_from`, không thì shop cùng `brand` đã có kit.
"""

import colorsys
import datetime
import json
import re
from pathlib import Path

from . import FONTS, SHOPS, app

# BỘ FONT (Sếp chốt 11/11) — mỗi bộ: `display` = chữ LỚN (tiêu đề, nhãn) · `body` = chữ thường · `bold` = chữ thường đậm.
# Shop khai danh sách bộ được dùng ở shop.json → image.fonts (cái đầu = mặc định); ảnh / khối chọn bộ khác bằng "font".
FONT_SETS = {
    "utm-avo": {"display": "UTM Avo/UTM_AvoBold.ttf", "body": "UTM Avo/UTM_Avo.ttf", "bold": "UTM Avo/UTM_AvoBold.ttf",
                "note": "tròn, hiện đại — ưu tiên cấp 1 cho mọi shop"},
    "averta": {"display": "Averta/Averta-ExtraBold.otf", "body": "Averta/Averta-Regular.otf", "bold": "Averta/Averta-Bold.otf",
               "note": "ExtraBold cho chữ lớn, Regular cho chữ thường — ưu tiên PHALEDO"},
    "poppins": {"display": "Poppins/DesignerVN-Poppins-ExtraBold.ttf", "body": "Poppins/DesignerVN-Poppins-Regular.ttf",
                "bold": "Poppins/DesignerVN-Poppins-ExtraBold.ttf", "note": "hình học, đậm đà — hợp chữ lớn"},
    "helvetins": {"display": "UTM HelvetIns/UTM HelvetIns.ttf", "body": "UTM Avo/UTM_Avo.ttf", "bold": "UTM Avo/UTM_AvoBold.ttf",
                  "note": "nén, rất đậm — chữ lớn của shop GDP (chữ thường đi với UTM Avo)"},
    "young": {"display": "PS Young Regular V1.2.otf", "body": "Averta/Averta-Regular.otf", "bold": "Averta/Averta-Bold.otf",
              "note": "PS Young — để thử cho tiêu đề"},
}
DEFAULT_FONTS = ["utm-avo", "poppins"]
# Tên font trong brand kit của app → bộ font
KIT_FONT = {"utm avo": "utm-avo", "averta": "averta", "poppins": "poppins", "helvetins": "helvetins"}
FALLBACK_FONT = ("BeVietnamPro/BeVietnamPro-Bold.ttf", "BeVietnamPro/BeVietnamPro-Regular.ttf")

# Mặc định cho mục "image" (shop.json ghi đè từng khoá)
IMAGE_DEFAULTS = {
    "tone": "auto",            # auto = đo nền dưới chữ: nền tối → chữ sáng, nền sáng → chữ đậm
    "ink": "brand",            # màu chữ đậm trên nền sáng: "brand" = text_on_light của shop · "auto" = hoà tông ảnh · "#rrggbb"
    "headline": "plain",       # plain | outline (viền) | plate (thanh nền màu shop) — kiểu tiêu đề mặc định
    "pill": "auto",            # auto = theo độ đục nhãn trong kit (đục <100% → kính mờ) | glass | solid
    "fonts": None,             # danh sách bộ font shop được dùng (xem FONT_SETS); None = theo kit app + mặc định
    "colors": {},              # ghi đè bảng màu cho ẢNH khi kit app lệch thực tế: heading, sub, accent, primary, dark, on_light, hl_on_dark
    "badge": {},               # ghi đè nhãn: bg, text, bg_opacity (0–100), border (#hex | null), gradient (false = tắt dải màu)
    "pill_shape": "round",     # round = nhãn bo tròn hết cỡ · square = chữ nhật bo góc nhẹ
    "heading_gradient": None,  # false = tắt dải màu chữ tiêu đề của kit app (chữ một màu phẳng)
    "watermark_mode": "image", # image = ảnh watermark của kit · text = dải chữ lặp tên shop (trắng mờ)
    "watermark_text": None,    # chữ của dải watermark (mặc định tên brand)
    "watermark_opacity": None, # ghi đè độ đục watermark (0–1)
    "edge": 0.045,             # viền NHẸ quanh tiêu đề giúp chữ nổi khỏi ảnh (em; 0 = tắt)
    "bolder": 0.012,           # làm tiêu đề đậm thêm (em; 0 = tắt)
    "shadow": 0.35,            # bóng mềm dưới chữ sáng (0 = tắt)
    "tracking": 0.01,          # giãn chữ tiêu đề (em)
    "logo": {"cover": True, "product_image": True, "description_image": True, "variant_image": True},
    "watermark": {"cover": True, "product_image": True, "description_image": True, "variant_image": True},
    "logo_margin_pct": 1.0,    # lề của logo tới mép ảnh (% chiều RỘNG ảnh) khi file logo không có khoảng đệm sẵn
    "logo_placement": None,    # ghi đè vị trí logo của kit app (top-center | top-left | top-right)
    "logo_width_pct": None,    # ghi đè bề rộng logo của kit app
    "watermark_width_pct": 24, # watermark dạng biểu tượng / chữ (không phải dải ngang): bề rộng, đặt giữa sản phẩm
}


def shop_dir(shop: str) -> Path:
    d = SHOPS / shop
    if not (d / "shop.json").is_file():
        raise SystemExit(f"Không có shop '{shop}' trong {SHOPS} — xem `vs.py shops` / tools\\init_shop.py")
    return d


def profile(shop: str) -> dict:
    return json.loads((shop_dir(shop) / "shop.json").read_text(encoding="utf-8"))


def _kit_owner(shop: str, _seen: tuple = ()) -> str | None:
    """Shop nào giữ `image/kit.json` dùng cho `shop` (chính nó → templates_from → shop cùng brand)."""
    if (SHOPS / shop / "image" / "kit.json").is_file():
        return shop
    prof = profile(shop)
    nxt = prof.get("templates_from")
    if nxt and nxt not in _seen:
        got = _kit_owner(nxt, _seen + (shop,))
        if got:
            return got
    for other in sorted(p.name for p in SHOPS.iterdir() if (p / "image" / "kit.json").is_file()):
        if profile(other).get("brand") == prof.get("brand"):
            return other
    return None


# ----------------------------- đồng bộ từ app -----------------------------
def sync(shop: str, listing_id: int | None = None, data: dict | None = None) -> Path:
    """Tải brand kit + logo + watermark của shop từ app về `assets/shops/<shop>/image/`.

    Brand kit nằm trong dữ liệu của MỘT listing bất kỳ thuộc shop → cần `listing_id` (hoặc `data` đã đọc sẵn)."""
    if data is None:
        if listing_id is None:
            mine = [l for l in app.queue() if (l.get("shop") or {}).get("name") == shop]
            if not mine:
                raise SystemExit(f"Không tìm thấy listing nào của '{shop}' trong hàng đợi — chạy lại kèm --listing <id>.")
            listing_id = mine[0]["id"]
        data = app.listing(listing_id)
    srv = data.get("shop") or {}
    if srv.get("name") != shop:
        raise SystemExit(f"Listing {data.get('id')} thuộc shop '{srv.get('name')}', không phải '{shop}'.")
    branding = srv.get("branding") or {}
    kit = dict(branding.get("kit") or {})
    if isinstance(kit.get("logo"), dict):
        kit["logo"] = {k: v for k, v in kit["logo"].items() if k != "prompt"}   # prompt cho AI tạo ảnh — không dùng
    out = shop_dir(shop) / "image"
    out.mkdir(exist_ok=True)
    files = {}
    for key, url in (("logo", branding.get("logo_url")), ("watermark", branding.get("watermark_image_url")),
                     ("font_reference", branding.get("font_reference_url"))):
        p = app.download(url, out / key) if url else None
        if p:
            files[key] = p.name
    doc = {"shop": shop, "brand_name": branding.get("brand_name") or srv.get("brand_name") or "",
           "synced_at": datetime.date.today().isoformat(), "source_listing": data.get("id"),
           "_note": "Brand kit lấy từ app (Shop Manager). KHÔNG sửa tay — `ims.py kit sync` ghi đè. "
                    "Tinh chỉnh riêng cho ảnh: shop.json mục \"image\".",
           "files": files, "kit": kit}
    path = out / "kit.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ----------------------------- gộp thành theme -----------------------------
def _hex(c: str, default: str = "#ffffff") -> str:
    c = (c or "").strip()
    return c.lower() if re.fullmatch(r"#[0-9a-fA-F]{6}", c) else default


def rgb(c: str) -> tuple[int, int, int]:
    c = _hex(c)
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def luminance(c) -> float:
    """Độ sáng tương đối WCAG (0–1) của màu hex hoặc bộ (r, g, b)."""
    r, g, b = (rgb(c) if isinstance(c, str) else c)[:3]
    lin = [v / 255 for v in (r, g, b)]
    lin = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in lin]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def tint_of(rgb_mean: tuple, lightness: float = 0.11, sat_cap: float = 0.55) -> str:
    """Màu đậm hoà tông ảnh: giữ sắc độ trung bình của vùng ảnh, hạ độ sáng → scrim / mực chữ không bị 'đen chết'."""
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb_mean[:3]))
    r, g, b = colorsys.hls_to_rgb(h, lightness, min(s, sat_cap))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def font_sets(shop: str, img: dict, kit: dict) -> dict:
    """Các bộ font shop được dùng, theo thứ tự ưu tiên (cái đầu = mặc định). Thiếu file → dừng, không lặng lẽ thay."""
    names = list(img.get("fonts") or [])
    if not names:
        kname = ((kit.get("typography") or {}).get("font_name") or "").lower()
        names = [s for key, s in KIT_FONT.items() if key in kname] + DEFAULT_FONTS
    names = list(dict.fromkeys(names))
    out = {}
    for n in names:
        if n not in FONT_SETS:
            raise SystemExit(f"Shop {shop}: bộ font '{n}' không có — có: {sorted(FONT_SETS)} (shop.json → image.fonts)")
        out[n] = {k: FONTS / FONT_SETS[n][k] for k in ("display", "body", "bold")}
        for f in out[n].values():
            if not f.is_file():
                raise SystemExit(f"Thiếu font của bộ '{n}': {f} — thả file vào assets/fonts/ (xin Sếp nếu chưa có).")
    return out


def load(shop: str) -> dict:
    """Theme đã gộp cho bộ dựng ảnh. Mọi đường dẫn file là tuyệt đối; thiếu file bắt buộc → dừng, không lặng lẽ thay."""
    prof = profile(shop)
    owner = _kit_owner(shop)
    kdoc = json.loads((SHOPS / owner / "image" / "kit.json").read_text(encoding="utf-8")) if owner else {}
    kit = kdoc.get("kit") or {}
    kdir = SHOPS / owner / "image" if owner else None
    img = {**IMAGE_DEFAULTS, **(profile(owner).get("image") or {} if owner and owner != shop else {}),
           **(prof.get("image") or {})}
    for k in ("logo", "watermark"):                       # gộp sâu 1 tầng cho 2 bảng bật/tắt theo loại ảnh
        if isinstance(img[k], dict):
            img[k] = {**IMAGE_DEFAULTS[k], **img[k]}

    own = img.get("colors") or {}
    pal = {**(prof.get("palette") or {}), **(kit.get("palette") or {})}
    for k_pal, k_own in (("text_on_dark", "on_dark"), ("text_on_light", "on_light"), ("primary", "primary"),
                         ("accent", "accent"), ("dark", "dark")):
        if own.get(k_own):
            pal[k_pal] = own[k_own]
    bk = prof.get("brand_kit") or {}
    cover = kit.get("cover") or {}
    badge = {**(bk.get("badge") or {}), **(kit.get("badge") or {}), **{k: v for k, v in (img.get("badge") or {}).items()
                                                                        if k not in ("border", "gradient")}}
    ib = img.get("badge") or {}
    if "border" in ib:                                    # shop chốt viền nhãn: màu hex, hoặc null = không viền
        badge["border"] = {"on": bool(ib["border"]), "color": ib["border"] or "#000000", "width_pct": ib.get("border_pct", 3.0)}
    if ib.get("gradient") is False:
        badge["bg_gradient"], badge["gradient"] = {}, {}
    border = badge.get("border")
    if isinstance(border, str):                           # shop.json cũ ghi border là 1 màu
        border = {"on": True, "color": border, "width_pct": 4.0}
    border = border or {}
    grad = badge.get("bg_gradient") or badge.get("gradient") or {}
    hgrad = cover.get("heading_gradient") or bk.get("heading_gradient") or {}
    opacity = badge.get("bg_opacity", 100)
    # Nhãn kính mờ (đục < 100%) dùng MÀU NỀN nhạt của kit; dải màu chỉ áp cho nhãn đặc (kit Phaledo bật dải xanh mặc
    # định của app nhưng nhân sự vẫn dùng nền be đục 35% → theo thực tế đang dùng).
    use_grad = bool(grad.get("on", bool(grad))) and bool(grad.get("stops")) and opacity >= 100

    sets = font_sets(shop, img, kit)

    logo_files = {}
    if kdir and (kdoc.get("files") or {}).get("logo"):
        logo_files["kit"] = kdir / kdoc["files"]["logo"]
    for key, rel in ((prof.get("logo") or {}).get("files") or {}).items():
        p = SHOPS / shop / rel
        if p.is_file():
            logo_files[key] = p
    klogo = kit.get("logo") or {}
    wm_file = kdir / kdoc["files"]["watermark"] if kdir and (kdoc.get("files") or {}).get("watermark") else None
    kwm = kit.get("watermark") or {}

    return {
        "shop": shop, "kit_from": owner, "brand": kdoc.get("brand_name") or prof.get("brand") or shop,
        "tone_of_voice": kit.get("tone") or prof.get("tone") or "",
        "cover_style": cover.get("style") or bk.get("cover_style") or "minimal_premium",
        "font": {"default": next(iter(sets)), "sets": sets,
                 "fallback_bold": FONTS / FALLBACK_FONT[0], "fallback_regular": FONTS / FALLBACK_FONT[1]},
        "color": {
            "heading": _hex(own.get("heading") or cover.get("heading_color") or bk.get("heading_color") or pal.get("text_on_dark")),
            "sub": _hex(own.get("sub") or own.get("heading") or cover.get("sub_color") or cover.get("heading_color")
                        or pal.get("text_on_dark")),
            "hl_on_dark": _hex(own.get("hl_on_dark"), "") if own.get("hl_on_dark") else None,
            "on_dark": _hex(pal.get("text_on_dark")), "on_light": _hex(pal.get("text_on_light"), "#161616"),
            "primary": _hex(pal.get("primary"), "#222222"), "accent": _hex(pal.get("accent"), "#b89a6a"),
            "dark": _hex(pal.get("dark"), "#161616"),
        },
        "heading_gradient": ({"stops": [_hex(s) for s in hgrad["stops"]], "angle": hgrad.get("angle", 90)}
                             if hgrad.get("on", bool(hgrad)) and hgrad.get("stops") and img.get("heading_gradient") is not False
                             else None),
        "badge": {
            "bg": _hex(badge.get("bg"), "#222222"), "text": _hex(badge.get("text")),
            "opacity": max(0.0, min(1.0, opacity / 100)),
            "gradient": {"stops": [_hex(s) for s in grad["stops"]], "angle": grad.get("angle", 90)} if use_grad else None,
            "border": _hex(border.get("color")) if border.get("on") else None,
            "border_pct": float(border.get("width_pct") or 4.0),
        },
        "radius_pct": float(kit.get("text_radius_pct") or bk.get("text_radius_pct") or 15),
        "logo": {"files": logo_files, "placement": klogo.get("placement") or (prof.get("logo") or {}).get("placement")
                 or "top-center", "width_pct": float(klogo.get("width_pct") or 26)},
        "watermark": {"file": wm_file, "text": img.get("watermark_text") or kwm.get("text") or kdoc.get("brand_name") or prof.get("brand") or "",
                      "mode": img.get("watermark_mode") or "image",
                      "opacity": img["watermark_opacity"] if img.get("watermark_opacity") is not None
                      else (kwm.get("image_opacity") or 100) / 100},
        "rules": kit.get("typography") or bk.get("typography") or {},
        "image": img,
    }
