"""Bộ kiểm ảnh sau khi dựng — đo trên số thật (khung từng dòng chữ lấy từ Chrome, màu nền lấy từ ảnh đã chụp).

Mức: LỖI (phải sửa, ảnh chưa được nộp) · CẢNH BÁO (xem lại bằng mắt, sửa nếu thấy xấu) · GHI CHÚ (thông tin)."""

import re
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from . import FONTS
from .kit import contrast

CJK = re.compile(r"[㐀-鿿豈-﫿぀-ヿ]")
# MOBILE FIRST (Sếp 11/11): khách xem ảnh trên điện thoại — ảnh rộng cỡ 390px màn hình, tức 1pt layout ≈ 0,39px.
PHONE_PX_PER_PT = 0.39
MIN_PT = {"LỖI": 20, "CẢNH BÁO": 26}          # < 20pt (≈ 8px) không đọc nổi · < 26pt (≈ 10px) phải căng mắt
MIN_SUB_PT = 32                                 # dòng phụ dưới tiêu đề: ≥ 32pt (≈ 12px) — dài thì tách 2 dòng / rút gọn
SAFE_PCT = 2.5                                  # lề an toàn quanh mép ảnh (% chiều rộng)


@lru_cache(maxsize=8)
def _cmap(font: str) -> frozenset:
    return frozenset(TTFont(font, lazy=True).getBestCmap().keys())


def _rgb(css: str) -> tuple[int, int, int]:
    if css.startswith("#"):
        return int(css[1:3], 16), int(css[3:5], 16), int(css[5:7], 16)
    m = re.findall(r"[\d.]+", css)
    return tuple(round(float(v)) for v in m[:3]) if len(m) >= 3 else (255, 255, 255)


def _inter(a, b) -> float:
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _bg_contrast(bg: Image.Image, row, fg) -> float:
    """Tương phản chữ ↔ nền ở phần KHÓ ĐỌC nhất của dòng (phân vị 20 theo từng điểm ảnh nền)."""
    x, y, w, h = row
    box = (max(0, int(x)), max(0, int(y)), min(bg.width, int(x + w) + 1), min(bg.height, int(y + h) + 1))
    if box[2] <= box[0] or box[3] <= box[1]:
        return 21.0
    crop = bg.crop(box).convert("RGB")
    crop.thumbnail((80, 40))
    vals = sorted(contrast(fg, p) for p in crop.getdata())
    return vals[len(vals) // 5]


def check(spec: dict, theme: dict, kind: str, measures: list, bg: Image.Image, size: tuple, base_size: tuple) -> list[dict]:
    W, H = size
    u = W / 1000
    issues = []

    def add(level, bid, msg):
        issues.append({"level": level, "id": bid, "msg": msg})

    if size != base_size:
        add("LỖI", "ảnh", f"kích thước ảnh ra {size} khác ảnh nền {base_size}")
    if kind == "cover" and abs(W - H) > 2:
        add("CẢNH BÁO", "ảnh", f"ảnh bìa không vuông ({W}×{H}) — Shopee cắt bìa 1:1")

    keep = [(k[0] / 100 * W, k[1] / 100 * H, (k[2] - k[0]) / 100 * W, (k[3] - k[1]) / 100 * H) for k in spec.get("keep") or []]
    by_id = {b.get("id") or f"{b['type']}{i}": b for i, b in enumerate(spec.get("blocks") or [], 1)}
    rows_all = []                                   # (id, khung dòng) — để dò chồng nhau
    cover_heads = []                                # cỡ các tiêu đề trên ảnh bìa
    text_area = 0.0

    for m in measures:
        bid, t = m["id"], m.get("type")
        src = by_id.get(bid, {})
        if t in ("logo", "watermark"):
            if t == "logo":
                rows_all.append((bid, m["rect"]))
            continue
        if not m["texts"] and t != "html":
            add("LỖI", bid, "khối không có chữ")
        if m.get("want") and m.get("got") and m["got"] < m["want"] * 0.86:
            add("CẢNH BÁO", bid, f"chữ bị co {m['want']:g}pt → {m['got']:g}pt cho vừa khung — rút chữ, nới `w`, hoặc tăng `lines`")
        for tx in m["texts"]:
            txt = tx["text"].strip()
            if tx.get("part") == "note":                    # dòng phụ nhỏ (`note`): chỉ kiểm cỡ chữ — mobile first
                pt = tx["px"] / u
                if pt < MIN_PT["CẢNH BÁO"]:
                    add("LỖI" if pt < MIN_PT["LỖI"] else "CẢNH BÁO", bid, f"dòng `note` {pt:.0f}pt nhỏ (≈ {pt * PHONE_PX_PER_PT:.0f}px "
                        f"trên điện thoại) — nên ≥ {MIN_PT['CẢNH BÁO']}pt: tăng `size` của khối hoặc rút gọn")
                continue
            if tx.get("part"):                              # cụm nhấn `*…*`: chỉ đo tương phản, phần khác đã đo ở khối cha
                worst = min((_bg_contrast(bg, row, _rgb(tx["color"])) for row in tx["rows"]), default=21.0)
                if worst < 3.0 and not tx["outlined"]:
                    add("LỖI" if worst < 2.1 else "CẢNH BÁO", bid, f"cụm nhấn “{txt[:24]}” (màu accent) chìm vào nền: tương phản "
                        f"{worst:.1f} — bỏ dấu *…*, hoặc tiêu đề `style: outline` / `plate`")
                continue
            if CJK.search(txt):
                add("LỖI", bid, f"còn chữ Hán: “{txt[:30]}”")
            cmap = _cmap(tx["font"]) if tx.get("font") else frozenset()
            miss = sorted({ch for ch in txt if not ch.isspace() and ord(ch) not in cmap}) if cmap else []
            if any(ch.isalpha() for ch in miss):
                add("LỖI", bid, f"font shop thiếu chữ cái {''.join(miss)!r} → Chrome đang mượn font khác (sai nhận diện)")
            elif miss:
                add("GHI CHÚ", bid, f"ký hiệu {''.join(miss)!r} không có trong font shop — đang hiện bằng font dự phòng")
            if m.get("maxLines") and tx["lines"] > m["maxLines"] and t not in ("spec", "list"):
                add("LỖI", bid, f"chữ xuống {tx['lines']} dòng, cho phép {m['maxLines']} — rút chữ hoặc nới `w`")
            pt = tx["px"] / u
            phone = f"≈ {pt * PHONE_PX_PER_PT:.0f}px trên điện thoại"
            fix = "nâng cỡ rồi tách 2 dòng, hoặc rút gọn chữ"
            if pt < MIN_PT["LỖI"]:
                add("LỖI", bid, f"chữ {pt:.0f}pt quá nhỏ ({phone}) — tối thiểu {MIN_PT['CẢNH BÁO']}pt: {fix}")
            elif pt < MIN_PT["CẢNH BÁO"]:
                add("CẢNH BÁO", bid, f"chữ {pt:.0f}pt nhỏ ({phone}) — nên ≥ {MIN_PT['CẢNH BÁO']}pt: {fix}")
            elif t == "sub" and pt < MIN_SUB_PT:
                add("CẢNH BÁO", bid, f"dòng phụ {pt:.0f}pt nhỏ ({phone}) — nên ≥ {MIN_SUB_PT}pt: {fix}")
            if kind == "cover" and t == "headline":
                cover_heads.append((pt, bid))
            fg = _rgb(tx["color"])
            need = 3.0 if (pt >= 30 and tx["weight"] >= 600) or pt >= 38 else 4.5
            worst = 21.0
            for row in tx["rows"]:
                rows_all.append((bid, row))
                text_area += row[2] * row[3]
                x, y, w, h = row
                if x < -1 or y < -1 or x + w > W + 1 or y + h > H + 1:
                    add("LỖI", bid, "chữ tràn ra ngoài ảnh")
                elif min(x, W - x - w) < SAFE_PCT / 100 * W - 1 or min(y, H - y - h) < SAFE_PCT / 100 * W - 1:
                    add("CẢNH BÁO", bid, f"chữ sát mép ảnh (lề an toàn {SAFE_PCT}% bề rộng)")
                if not src.get("over"):
                    for k in keep:
                        if _inter(row, k) > 0.04 * w * h:
                            add("LỖI", bid, "chữ đè lên vùng sản phẩm (`keep`) — dời chữ, hoặc khai `over: true` nếu cố ý")
                            break
                if not tx["outlined"]:
                    worst = min(worst, _bg_contrast(bg, row, fg))
            if tx.get("edged"):                              # tiêu đề có viền nhẹ màu tương phản → đọc được ở mức thấp hơn
                need = round(need * 0.8, 1)
            if worst < need * 0.72:
                add("LỖI", bid, f"chữ khó đọc: tương phản với nền {worst:.1f} (cần ≥ {need}) — dời sang vùng nền đều màu, hoặc cho chữ nền riêng: tiêu đề `style` plate / plate-dark / outline, nhãn, `bg` (không phủ màu lên ảnh)")
            elif worst < need:
                add("CẢNH BÁO", bid, f"tương phản chữ ↔ nền {worst:.1f} (chuẩn {need}) — soát bằng mắt")
        if src.get("color", "").startswith("#"):
            add("GHI CHÚ", bid, f"màu {src['color']} ghi tay — ngoài bảng màu shop")

    if cover_heads and max(cover_heads)[0] < 48:
        pt, bid = max(cover_heads)
        add("CẢNH BÁO", bid, f"tiêu đề bìa {pt:.0f}pt — bìa cần chữ rất lớn (56–72pt)")
    logo = next((m["rect"] for m in measures if m.get("type") == "logo"), None)
    if logo:
        near = set()
        for b_id, r in rows_all:
            gap = r[1] - (logo[1] + logo[3])                 # khe dọc giữa đáy logo và đỉnh dòng chữ
            if b_id != "logo" and b_id not in near and 0 <= gap < 0.02 * W and _inter((r[0], 0, r[2], 1), (logo[0], 0, logo[2], 1)):
                near.add(b_id)
                add("CẢNH BÁO", b_id, f"chữ sát logo (khe {gap / W * 100:.1f}% bề rộng, dấu thanh có thể chạm) — hạ `y` xuống thêm")
    seen = set()
    for i, (a_id, a) in enumerate(rows_all):
        for b_id, b in rows_all[i + 1:]:
            if a_id != b_id and (a_id, b_id) not in seen and _inter(a, b) > 0.03 * min(a[2] * a[3], b[2] * b[3]):
                seen.add((a_id, b_id))
                add("LỖI", a_id, f"đè lên khối '{b_id}'")
    if kind == "cover" and text_area > 0.28 * W * H:
        add("CẢNH BÁO", "ảnh", f"chữ phủ {text_area / (W * H):.0%} ảnh bìa — bìa rối, bớt chữ")
    uniq = dict.fromkeys((x["level"], x["id"], x["msg"]) for x in issues)                    # bỏ dòng lặp, giữ thứ tự
    return [{"level": a, "id": b, "msg": c} for a, b, c in uniq]


def annotate(final: Image.Image, spec: dict, measures: list, issues: list, dst: Path) -> None:
    """Ảnh soát: khung từng khối (đỏ = có lỗi, cam = cảnh báo, xanh = ổn) + vùng `keep` (vàng) + lề an toàn."""
    im = final.convert("RGB").copy()
    d = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    lw = max(2, W // 500)
    fs = max(14, W // 64)
    font = ImageFont.truetype(str(FONTS / "BeVietnamPro" / "BeVietnamPro-Bold.ttf"), fs)
    bad = {}
    for x in issues:
        if x["level"] == "LỖI" or (x["level"] == "CẢNH BÁO" and bad.get(x["id"]) != "LỖI"):
            bad[x["id"]] = x["level"]
    m = SAFE_PCT / 100 * W
    d.rectangle([m, m, W - m, H - m], outline=(255, 255, 255, 110), width=1)
    for k in spec.get("keep") or []:
        d.rectangle([k[0] / 100 * W, k[1] / 100 * H, k[2] / 100 * W, k[3] / 100 * H], outline=(255, 220, 0, 230), width=lw)
    for b in measures:
        col = {"LỖI": (255, 40, 40, 255), "CẢNH BÁO": (255, 150, 0, 255)}.get(bad.get(b["id"]), (40, 220, 120, 255))
        x, y, w, h = b["rect"]
        d.rectangle([x, y, x + w, y + h], outline=col, width=lw)
        d.text((x + 4, max(0, y - fs - 4)), b["id"], fill=col, font=font, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.thumbnail((1400, 1400))
    im.save(dst, quality=88)
