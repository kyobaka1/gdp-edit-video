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
