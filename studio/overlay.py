"""Vẽ ô chữ đè (nền đặc + viền + bo góc + chữ Việt tự co vừa ô) thành PNG trong suốt."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from studio.config import FONT_BOLD


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if draw.textlength(trial, font=font) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def _insets(width: int, height: int) -> tuple[int, int, int]:
    border_px = max(2, round(min(width, height) * 0.06))
    return border_px, border_px + round(width * 0.06), border_px + round(height * 0.10)


def fit_font(text: str, width: int, height: int, font_path: Path = FONT_BOLD) -> int:
    """Cỡ chữ lớn nhất (px) để text vừa ô width×height (tự xuống dòng)."""
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    _, pad_x, pad_y = _insets(width, height)
    inner_w, inner_h = width - 2 * pad_x, height - 2 * pad_y
    for size in range(round(height * 0.6), 7, -1):
        font = ImageFont.truetype(str(font_path), size)
        lines = _wrap(draw, text, font, inner_w)
        if round(size * 1.22) * len(lines) <= inner_h and max(draw.textlength(l, font=font) for l in lines) <= inner_w:
            return size
    return 8


def grow_to_min_font(text: str, x: int, y: int, w: int, h: int, frame_w: int, frame_h: int,
                     min_px: int) -> tuple[int, int, int, int]:
    """Chữ Việt dài hơn chữ Trung → ô gốc làm chữ nhỏ hơn min_px. Nới NGANG trước (giữ tâm, ≤92% khung),
    chưa đủ mới nới DỌC. Ô mới luôn phủ trọn ô gốc. Trả (x, y, w, h)."""
    if not text or fit_font(text, w, h) >= min_px:
        return x, y, w, h
    max_w = max(w, round(frame_w * 0.92))
    new_w = w
    for new_w in range(w + 8, max_w + 1, 8):
        if fit_font(text, new_w, h) >= min_px:
            break
    new_h = h
    if fit_font(text, new_w, h) < min_px:
        for new_h in range(h + 4, min(frame_h, h * 3) + 1, 4):
            if fit_font(text, new_w, new_h) >= min_px:
                break
    new_x = max(0, min(frame_w - new_w, x - (new_w - w) // 2))
    new_y = max(0, min(frame_h - new_h, y - (new_h - h) // 2))
    return new_x, new_y, new_w, new_h


def render_label(
    text: str,
    width: int,
    height: int,
    *,
    bg: str = "#FFFFFF",
    border: str = "#D7262E",
    text_color: str = "#1A1A1A",
    border_px: int | None = None,
    radius_px: int | None = None,
    font_path: Path = FONT_BOLD,
    max_font_px: int | None = None,
) -> Image.Image:
    """Ô kích thước đúng width×height; nền che kín hoàn toàn vùng bên dưới."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    short = min(width, height)
    border_px = border_px if border_px is not None else max(2, round(short * 0.06))
    radius_px = radius_px if radius_px is not None else round(short * 0.18)
    draw.rounded_rectangle(
        (0, 0, width - 1, height - 1), radius=radius_px, fill=bg, outline=border, width=border_px
    )

    pad_x = border_px + round(width * 0.06)
    pad_y = border_px + round(height * 0.10)
    inner_w, inner_h = width - 2 * pad_x, height - 2 * pad_y
    size = max_font_px or round(height * 0.6)
    while size >= 8:
        font = ImageFont.truetype(str(font_path), size)
        lines = _wrap(draw, text, font, inner_w)
        line_h = round(size * 1.22)
        block_h = line_h * len(lines)
        widest = max(draw.textlength(line, font=font) for line in lines)
        if block_h <= inner_h and widest <= inner_w:
            break
        size -= 1
    y = (height - block_h) / 2
    for line in lines:
        draw.text((width / 2, y + line_h / 2), line, font=font, fill=text_color, anchor="mm")
        y += line_h
    return img
