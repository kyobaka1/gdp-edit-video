"""ẢNH PHÂN LOẠI (ảnh đại diện của từng variant) — một THIẾT KẾ CHUNG cho mọi phân loại của một sản phẩm (Sếp 12/11).

Hai trường hợp:
  • Ảnh nguồn ĐÃ CÓ khung mô tả (nhân sự xoá chữ, giữ khung)  → `variant_set.style = "fill"`: khai MỘT bộ khối mẫu
    (`variant_set.blocks`, chữ viết `{name}`, `{sub}`…) — từng phân loại chỉ khai giá trị; bộ dựng điền vào đúng ô.
  • Ảnh nguồn CHƯA có khung (chỉ có sản phẩm)                  → dựng KHUNG PHÂN BIỆT mới, dùng chung cả bộ:
    `style = "bottom"` (khung bên dưới — sản phẩm NGANG) · `"right"` / `"left"` (khung bên cạnh — sản phẩm DỌC).
    Ảnh ra VUÔNG. Ảnh nguồn không bị chỉnh màu — chỉ được đặt (cắt / phóng) vào vùng ảnh còn lại của khung vuông.

Khung gồm 4 phần (phần nào không khai thì không có):
  name + sub   ĐIỂM PHÂN BIỆT của phân loại — chữ to nhất ("50CM" + "THANH TREO + MÓC")       → khai ở từng ảnh
  chips        2–3 điểm chung của sản phẩm ("NHÔM DÀY 1.2MM", "NHÔM KHÔNG GỈ")               → khai ở bộ
  included     PHƯƠNG THỨC LẮP ĐẶT đã gồm trong bộ (keo dán / ốc vít / miếng dán / cốc hút)  → khai ở bộ (đồ LTENG: bắt buộc)
  warranty     bảo hành ("10 NĂM")                                                            → khai ở bộ

Cỡ chữ của `name` / `sub` được chọn theo chuỗi DÀI NHẤT trong cả bộ → mọi phân loại cùng cỡ chữ, cùng bố cục."""

import copy
import html
import json
import re
from pathlib import Path

from PIL import Image

from . import HERE, SHOPS
from .compose import rich

STYLES = ("bottom", "right", "left", "fill")
TONES = ("brand", "invert", "dark")
# % cạnh ảnh dành cho khung. Sếp 12/11: khung KHÔNG được lấn sản phẩm — khung bên dưới tối đa 20% chiều cao ảnh
# (ảnh mẫu Sếp đưa: 17–24%); khung bên cạnh theo tỉ lệ ảnh mẫu (cột ≈ 31% bề rộng).
DEFAULT_PANEL = {"bottom": 20, "right": 30, "left": 30}
PANEL_RANGE = {"bottom": (14, 20), "right": (24, 32), "left": (24, 32)}
INSTALL_DIR = HERE / "asset"                                      # image-studio/asset/ — ảnh PNG phụ kiện lắp đặt Sếp cung cấp (dùng chung)

# Phương thức lắp đặt: mã → (nhãn, các tên gọi khác). Ảnh: assets/shops/<shop>/image/install/<mã>.png → image-studio/asset/<mã>.png
INSTALL = {
    "keo-dan": ("KEO DÁN", "KEO", ("keo", "keo-dan", "keodan")),
    "oc-vit": ("VÍT NỞ", "VÍT", ("vit", "oc-vit", "ocvit", "vit-no", "ban-vit", "bat-vit")),
    "mieng-dan": ("MIẾNG DÁN", "MIẾNG DÁN", ("mieng-dan", "miengdan", "dan")),
    "coc-hut": ("CỐC HÚT", "CỐC HÚT", ("coc-hut", "cochut", "hut")),
}
_ALIAS = {a: code for code, (_, _, names) in INSTALL.items() for a in names}

# Hình vẽ TẠM khi chưa có ảnh PNG thật (nét đơn, màu theo chữ của ô) — có PNG là tự thay.
_SVG = {
    "keo-dan": '<path d="M38 8h24v10H38zM34 18h32l-4 62H38zM40 80h20l-4 12h-12z"/><path d="M42 34h16M41 46h18M40 58h20"/>',
    "oc-vit": '<path d="M30 14h40l-6 14H36zM44 28h12v52l-6 12-6-12z"/><path d="M44 40l12-5M44 52l12-5M44 64l12-5M44 76l12-5"/>',
    "mieng-dan": '<rect x="16" y="16" width="68" height="68" rx="12"/><path d="M60 84V66a6 6 0 0 1 6-6h18"/><circle cx="42" cy="42" r="6"/>',
    "coc-hut": '<circle cx="50" cy="50" r="36"/><circle cx="50" cy="50" r="22"/><circle cx="50" cy="50" r="6"/>',
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def install_item(shop: str, item, job: Path) -> dict:
    """1 món lắp đặt → {"code", "label", "img": Path | None}. `item` là mã ("keo-dan", "vit"…) hoặc
    {"img": "<file trong job hoặc đường dẫn>", "label": "…"} cho phụ kiện riêng của sản phẩm."""
    if isinstance(item, dict):
        p = Path(item.get("img", ""))
        p = p if p.is_absolute() else job / p
        if not p.is_file():
            raise SystemExit(f"`included`: không thấy ảnh {p}")
        return {"code": p.stem, "label": item.get("label", ""), "short": item.get("label", ""), "img": p}
    code = _ALIAS.get(str(item).lower().strip())
    if not code:
        raise SystemExit(f"`included`: không hiểu '{item}' — dùng {sorted(INSTALL)} hoặc {{\"img\": …, \"label\": …}}.")
    img = next((p for p in (SHOPS / shop / "image" / "install" / f"{code}.png", INSTALL_DIR / f"{code}.png") if p.is_file()), None)
    return {"code": code, "label": INSTALL[code][0], "short": INSTALL[code][1], "img": img}


def trimmed(img: Path, tmp: Path) -> tuple[Path, float]:
    """Cắt sát phần NHÌN THẤY của ảnh phụ kiện (bỏ lề trong suốt) để nó to hết cỡ trong ô. Trả (file, tỉ lệ rộng / cao)."""
    im = Image.open(img).convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
    if box and box != (0, 0, im.width, im.height):
        im = im.crop(box)
    tmp.mkdir(exist_ok=True)
    dst = tmp / f"inst-{img.stem}.png"
    im.save(dst)
    return dst, im.width / im.height


def merged(vset: dict, own: dict | None) -> dict:
    """Thiết kế chung của bộ + phần riêng của một phân loại (phần riêng thắng)."""
    out = {k: v for k, v in (vset or {}).items() if not k.startswith("_") and k != "blocks"}
    out.update(own or {})
    return out


SUB_STYLES = ("box", "plain", "pop")        # ô kiểu: hộp sáng viền (mặc định) · dòng chữ trơn · thẻ màu nhấn phụ


def balance(text: str, limit: int = 12) -> str:
    """Ô kiểu chứa được chữ ÍT hoặc NHIỀU (Sếp 12/11): dài hơn `limit` ký tự mà chưa tự ngắt → chia 2 dòng cân nhau,
    ưu tiên ngắt trước dấu "+" / "&" / "-" (vd "THANH TREO + MÓC" → "THANH TREO\n+ MÓC")."""
    text = str(text).strip()
    if "\n" in text or len(text) <= limit or " " not in text:
        return text
    cuts = [m.start() for m in re.finditer(r" ", text)]
    best = min(cuts, key=lambda i: (abs(len(text[:i]) - len(text[i + 1:])) - (4 if text[i + 1] in "+&-–" else 0), i))
    return text[:best] + "\n" + text[best + 1:]


def name_html(text: str) -> str:
    """Tên phân loại là SỐ + ĐƠN VỊ ("50CM", "1.2L", "3 TẦNG") → số to, đơn vị nhỏ — con số là thứ khách so giữa các loại."""
    text = str(text).strip().upper()
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*([^\d\s].{0,7})", text)
    if not m:
        return rich(text)
    return f'{html.escape(m.group(1))}<span class="vunit">{html.escape(m.group(2))}</span>'


def collect(layout: dict) -> dict:
    """Mọi `name` / `sub` của bộ → để chọn MỘT cỡ chữ vừa cho chuỗi dài nhất (cả bộ cùng cỡ)."""
    vs = [im.get("variant") or {} for im in layout.get("images", {}).values() if im.get("kind") == "variant_image"]
    return {"name": sorted({str(v["name"]) for v in vs if v.get("name")}),
            "sub": sorted({str(v["sub"]).strip() for v in vs if v.get("sub")})}


def fill_blocks(vset: dict, own: dict) -> list:
    """Kiểu `fill`: khối mẫu của bộ, thay `{name}` / `{sub}` / `{khoá bất kỳ}` bằng giá trị của phân loại."""
    vals = {k: str(v) for k, v in merged(vset, own).items() if isinstance(v, (str, int, float))}

    def sub(x):
        if isinstance(x, str):
            for k, v in vals.items():
                x = x.replace("{" + k + "}", v)
            return x
        if isinstance(x, list):
            return [sub(i) for i in x]
        if isinstance(x, dict):
            return {k: sub(v) for k, v in x.items()}
        return x

    blocks = sub(copy.deepcopy(vset.get("blocks") or []))
    left = [b.get("id") or b.get("type") for b in blocks if "{" in json.dumps(b, ensure_ascii=False) and "}" in json.dumps(b, ensure_ascii=False)
            and any("{" + k + "}" in json.dumps(b, ensure_ascii=False) for k in ("name", "sub"))]
    if left:
        raise SystemExit(f"Phân loại thiếu `name` / `sub` cho khối mẫu {left} — khai trong `variant` của ảnh.")
    return blocks


def _place(src: tuple, frame: tuple, vis: tuple, keep: list, focus, zoom: float) -> tuple:
    """Đặt ảnh nguồn vào vùng ảnh `frame` (px): phủ kín vùng, phóng thêm `zoom`, căn TÂM sản phẩm vào tâm vùng nhìn thấy `vis`.
    Trả (left, top, rộng, cao, scale) của ảnh trong hệ toạ độ ảnh ra."""
    sw, sh = src
    fx, fy, fw, fh = frame
    scale = max(fw / sw, fh / sh) * zoom
    dw, dh = sw * scale, sh * scale
    if focus:
        cx, cy = focus[0] / 100 * dw, focus[1] / 100 * dh
    elif keep:
        cx = (min(k[0] for k in keep) + max(k[2] for k in keep)) / 200 * dw
        cy = (min(k[1] for k in keep) + max(k[3] for k in keep)) / 200 * dh
    else:
        cx, cy = dw / 2, dh / 2
    vx, vy = vis[0] + vis[2] / 2, vis[1] + vis[3] / 2
    left = _clamp(vx - cx, fx + fw - dw, fx)
    top = _clamp(vy - cy, fy + fh - dh, fy)
    return left, top, dw, dh, scale


def build(spec: dict, vset: dict, theme: dict, src: tuple, job: Path) -> dict:
    """Ảnh phân loại kiểu dựng khung → {"canvas", "base_html", "panel_html", "spec" (keep đã đổi sang toạ độ ảnh ra), "issues"}."""
    # mặc định theo SHOP (shop.json → image.variant: name_font, font, tone, sub_style… Sếp đã chọn) → bộ → từng ảnh
    v = merged({**(theme["image"].get("variant") or {}), **(vset or {})}, spec.get("variant"))
    style = v.get("style", "bottom")
    if style not in ("bottom", "right", "left"):
        raise SystemExit(f"variant_set.style '{style}' không có — dùng bottom · right · left · fill.")
    tone = v.get("tone", "brand")
    if tone not in TONES:
        raise SystemExit(f"variant_set.tone '{tone}' không có — dùng {' · '.join(TONES)}.")
    if not v.get("name"):
        raise SystemExit("Ảnh phân loại thiếu `variant.name` (điểm phân biệt — chữ to nhất, vd \"50CM\").")
    S = int(v.get("size", 1000))
    u = S / 1000
    p = float(v.get("panel", DEFAULT_PANEL[style]))
    lo, hi = PANEL_RANGE[style]
    if not lo <= p <= hi:
        raise SystemExit(f"variant_set.panel {p:g}% ngoài khoảng {lo}–{hi}% của kiểu {style} — khung to hơn là lấn sản phẩm (Sếp 12/11: vùng chữ "
                         f"không được quá lớn so với sản phẩm), bé hơn thì chữ chết. Chữ không vừa → BỚT phần / rút chữ, không nới khung.")
    issues = []
    radius = 24 * u
    logo_on = spec.get("logo", theme["image"]["logo"].get("variant_image", True))
    head = 0.085 * S if logo_on else 0                                 # chừa chỗ logo treo mép trên khi căn sản phẩm
    P = p / 100 * S
    if style == "bottom":
        frame, vis = (0, 0, S, S - P + radius), (0, head, S, S - P - head)
    elif style == "right":
        frame, vis = (0, 0, S - P + radius, S), (0, head, S - P, S - head)
    else:
        frame, vis = (P - radius, 0, S - P + radius, S), (P, head, S - P, S - head)
    keep = spec.get("keep") or []
    left, top, dw, dh, scale = _place(src, frame, vis, keep, v.get("focus"), float(v.get("zoom", 1)))

    # `keep` khai theo % ẢNH NGUỒN (đo bằng `ims.py grid`) → đổi sang % ảnh ra để watermark + bộ kiểm dùng
    keep_out = [[(left + k[0] / 100 * dw) / S * 100, (top + k[1] / 100 * dh) / S * 100,
                 (left + k[2] / 100 * dw) / S * 100, (top + k[3] / 100 * dh) / S * 100] for k in keep]
    x0, y0, x1, y1 = vis[0] / S * 100, 0, (vis[0] + vis[2]) / S * 100, (vis[1] + vis[3]) / S * 100
    for k in keep_out:
        cut = max(x0 - k[0], k[2] - x1, y0 - k[1], k[3] - y1)
        if cut > 0.5:
            where = "khung phân biệt che" if (style == "bottom" and k[3] > y1) or (style == "right" and k[2] > x1) or \
                (style == "left" and k[0] < x0) else "mép ảnh cắt"
            issues.append({"level": "LỖI", "id": "khung", "msg": f"{where} sản phẩm {cut:.0f}% — giảm `panel` (đang {p:g}%), "
                           f"chỉnh `focus` / `zoom`, hoặc đổi `style` (sản phẩm ngang → bottom, dọc → right)"})
            break
    if not keep:
        issues.append({"level": "CẢNH BÁO", "id": "khung", "msg": "chưa khai `keep` (hộp bao sản phẩm, % của ẢNH NGUỒN) — bộ dựng không "
                       "biết sản phẩm ở đâu để căn giữa và kiểm khung có che sản phẩm không"})
    if abs(src[0] - src[1]) > 2 and scale * min(src) < S * 0.6:
        issues.append({"level": "GHI CHÚ", "id": "ảnh", "msg": f"ảnh nguồn {src[0]}×{src[1]} bị phóng {scale:.2f} lần — có thể mờ"})

    # ---------- khung ----------
    all_ = vset.get("_all") or {}
    fd, fb = theme["font"]["sets"], v.get("font") or theme["font"]["default"]
    if fb not in fd:
        raise SystemExit(f"variant_set.font '{fb}' không nằm trong bộ font của shop {sorted(fd)}.")
    num_font = v.get("name_font") or fb
    if num_font not in fd:
        raise SystemExit(f"variant_set.name_font '{num_font}' không nằm trong bộ font của shop {sorted(fd)}.")

    def blk(bid, cls, inner, vfs, font=fb, extra=""):
        return (f'<div id="{bid}" class="b disp vb {cls}" data-type="variant" data-vfs="{vfs}" data-fd="{fd[font]["display"]}" '
                f'data-fb="{fd[font]["body"]}" style="--font-display:D_{font};--font-body:B_{font}" {extra}>{inner}</div>')

    def alts(key, fn):
        vals = all_.get(key) or []
        return f"data-all='{html.escape(json.dumps([fn(x) for x in vals], ensure_ascii=False), quote=True)}'" if len(vals) > 1 else ""

    sub_style = v.get("sub_style", "box")
    if sub_style not in SUB_STYLES:
        raise SystemExit(f"variant_set.sub_style '{sub_style}' không có — dùng {' · '.join(SUB_STYLES)}.")
    lim = 16 if style == "bottom" else 12                    # số ký tự một dòng còn đọc được ở ≥ 26pt trong ô kiểu
    sub_txt = balance(v["sub"], lim) if v.get("sub") else ""
    two = " two" if any("\n" in balance(x, lim) for x in (all_.get("sub") or [sub_txt])) else ""      # cả bộ cùng chiều cao ô kiểu

    side = style != "bottom"
    sizes = {"name": 132 if side else 124, "sub": 38 if side else 27, "chip": 31 if side else 28, "inc": 28 if side else 26,
             "war": 112 if side else 114}
    sizes.update(v.get("sizes") or {})
    cols, weights = [], []

    name = blk("ten", "vname", f'<span class="tx">{name_html(v["name"])}</span>', sizes["name"], num_font, alts("name", name_html))
    sub = (blk("kieu", f"vsub s-{sub_style}{two}", f'<span class="vtag"><span class="tx">{rich(sub_txt, True)}</span></span>', sizes["sub"], fb,
               alts("sub", lambda x: rich(balance(x, lim), True))) if sub_txt else "")
    cols.append(f'<div class="vc vc-name">{name}{sub}</div>')
    weights.append(33)

    chips = [str(c) for c in v.get("chips") or []][:3]
    if chips:
        inner = "".join(blk(f"diem-{i}", "vchip", f'<span class="tx">{rich(c, True)}</span>', sizes["chip"], fb, 'data-group="chip"')
                        for i, c in enumerate(chips, 1))
        cols.append(f'<div class="vc vc-chips">{inner}</div>')
        weights.append(28)

    inc = v.get("included")
    if inc:
        inc = {"items": inc} if isinstance(inc, list) else inc
        items = [install_item(theme["shop"], it, job) for it in inc.get("items") or []]
        if not items:
            raise SystemExit("`included.items` rỗng — khai phương thức lắp đặt đã gồm trong bộ (keo-dan · oc-vit · mieng-dan · coc-hut).")
        pics, n_wide = [], 0
        for it in items:
            if it["img"]:
                f, ratio = trimmed(Path(it["img"]), job / "_tmp")
                wide = ratio >= 2.2 and len(items) > 1                     # vật dài (tuýp keo) nằm riêng một hàng cho đủ to
                n_wide += wide
                pics.append(f'<img class="vpic{" wide" if wide else ""}" src="{f.resolve().as_uri()}">')
            else:
                pics.append(f'<svg class="vpic draw" viewBox="0 0 100 100">{_SVG.get(it["code"], _SVG["mieng-dan"])}</svg>')
                issues.append({"level": "CẢNH BÁO", "id": "da-gom", "msg": f"chưa có ảnh PNG cho '{it['code']}' — đang dùng HÌNH VẼ TẠM. "
                               f"Thả ảnh nền trong suốt vào {INSTALL_DIR / (it['code'] + '.png')} (hoặc assets/shops/{theme['shop']}/image/install/) rồi render lại"})
        # DÒNG CHỮ dưới ảnh là bắt buộc (Sếp 12/11: ảnh phụ kiện "vẫn cần text để sub" — khách không tự đoán được món gì):
        # ≤ 2 món tự ghép ("KEO + VÍT"); từ 3 món phải khai `label` ngắn, 1–2 dòng (vd "KEO - ỐC VÍT\nĐI KÈM").
        label = str(inc.get("label") or (" + ".join(it["label" if len(items) == 1 else "short"] for it in items if it["label"])
                                         if len(items) <= 2 else "")).strip()
        if not label:
            issues.append({"level": "LỖI", "id": "da-gom", "msg": "ô phụ kiện đi kèm chưa có dòng chữ — từ 3 món phải khai `included.label` ngắn, "
                           "1–2 dòng (vd \"KEO - ỐC VÍT\\nĐI KÈM\"); Sếp 12/11: có ảnh vẫn cần chữ"})
        # nhãn 2 dòng đã tự nói "đi kèm / đã gồm" → mặc định bỏ tiêu đề trên cho ảnh đủ to; khai `title` nếu vẫn muốn
        title = str(inc.get("title", "" if "\n" in label else "ĐÃ GỒM")).strip()
        per_row = max(1, len(items) - n_wide)
        grid_css = f"grid-template-columns:repeat({per_row},1fr);grid-template-rows:repeat({n_wide + (1 if len(items) > n_wide else 0)},1fr)"
        note = f'<span class="tx vnote">{rich(inc["note"])}</span>' if inc.get("note") else ""
        inner = ((f'<span class="tx vinc-t">{rich(title, True)}</span>' if title else "")
                 + f'<span class="vpics n{len(items)}" style="{grid_css}">{"".join(pics)}</span>'
                 + (f'<span class="tx vinc-l">{rich(label, True)}</span>' if label else "") + note)
        cols.append(f'<div class="vc vc-inc">{blk("da-gom", "vinc", inner, sizes["inc"])}</div>')
        weights.append(19)
        if len(items) >= 3 and len(weights) == 3:                 # 3 món: ô rộng thêm một chút, lấy từ cột điểm chung + cột bảo hành
            weights[:] = [weights[0], weights[1] - 1, 21]         # (không lấy của cột tên: chữ ô kiểu sẽ tụt dưới 26pt)
    elif theme.get("brand", "").upper().startswith("LTENG"):
        issues.append({"level": "CẢNH BÁO", "id": "khung", "msg": "đồ LTENG nên ghi PHƯƠNG THỨC LẮP ĐẶT đã gồm trong bộ (`included`: keo-dan · "
                       "oc-vit · mieng-dan · coc-hut) — Sếp 12/11"})

    war = v.get("warranty")
    if war:
        war = {"value": str(war)} if not isinstance(war, dict) else war
        inner = (f'<span class="tx wl">{rich(war.get("label", "BẢO HÀNH"), True)}</span><span class="wrow"><span class="tx wv">{rich(str(war["value"]))}</span>'
                 + (f'<span class="tx wu">{rich(str(war["unit"]), True)}</span>' if war.get("unit") else "") + "</span>")
        cols.append(f'<div class="vc vc-war">{blk("bao-hanh", "vwar", inner, sizes["war"], num_font)}</div>')
        weights.append(19 if 21 in weights else 20)              # ô "đã gồm" 3 món đã lấy 1 phần của cột này

    grid = " ".join(f"{w}fr" for w in weights)
    panel = (f'<div id="vp" class="vp vp-{style} vt-{tone}" style="--vp:{p};--vgrid:{grid};--vfont-text:D_{fb}"><div class="vp-in">{"".join(cols)}</div></div>')
    base = (f'<div class="vframe" style="left:{frame[0]}px;top:{frame[1]}px;width:{frame[2]}px;height:{frame[3]}px">'
            f'<img id="base" src="{{src}}" style="left:{left - frame[0]:.2f}px;top:{top - frame[1]:.2f}px;width:{dw:.2f}px;height:{dh:.2f}px"></div>')

    out = {k: v2 for k, v2 in spec.items() if k not in ("blocks", "panels")}
    out["keep"] = [[round(x, 1) for x in k] for k in keep_out]
    out["blocks"] = []
    if isinstance(logo_on, dict) or logo_on is True:
        lg = {} if logo_on is True else dict(logo_on)
        if "x" not in lg and "placement" not in lg and side:            # logo treo giữa VÙNG ẢNH, không phải giữa cả khung vuông
            lg["x"] = (vis[0] + vis[2] / 2) / S * 100
        out["logo"] = lg or True
    return {"canvas": (S, S), "base_html": base, "panel_html": panel, "spec": out, "issues": issues,
            "info": {"style": style, "panel": p, "tone": tone, "zoom": round(scale, 3)}}


def consistency(layout: dict, reports: dict) -> list[str]:
    """Cả bộ ảnh phân loại phải CÙNG một thiết kế: cùng kiểu khung, cùng cỡ khung, cùng tông, cùng các phần."""
    out, seen = [], {}
    for key, r in reports.items():
        c = r.get("card")
        if c:
            seen.setdefault((c["style"], c["panel"], c["tone"]), []).append(key)
    if len(seen) > 1:
        out.append("bộ ảnh phân loại KHÔNG cùng thiết kế: " + " | ".join(f"{s} {p:g}% {t}: {', '.join(ks)}" for (s, p, t), ks in seen.items())
                   + " — khai chung ở `variant_set`, đừng ghi đè style / panel / tone ở từng ảnh")
    sizes = {}
    for key, r in reports.items():
        for b in r.get("blocks", []):
            if b["id"] in ("ten", "kieu") and b.get("size_pt"):
                sizes.setdefault(b["id"], {}).setdefault(b["size_pt"], []).append(key)
    for bid, by in sizes.items():
        if len(by) > 1:
            out.append(f"cỡ chữ khối '{bid}' lệch nhau giữa các phân loại: " + " | ".join(f"{pt:g}pt: {', '.join(ks)}" for pt, ks in by.items())
                       + " — render lại CẢ BỘ (không render lẻ từng ảnh sau khi đổi tên phân loại)")
    return out
