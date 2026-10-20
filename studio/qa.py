"""Kiểm video đã dựng: còn sót chữ Hán không? Lấy khung tại MỌI thời điểm từng thấy chữ Trung ở video
gốc + mỗi giây một khung, hỏi Gemini. Ghi qa.json + contact.jpg (ảnh ghép để người/Claude soát mắt)."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from studio import config, media
from studio.analyze import detect_text


def contact_sheet(frames: list[tuple[float, Path]], out: Path, cols: int = 6, thumb_w: int = 240) -> Path:
    if not frames:
        return out
    first = Image.open(frames[0][1])
    thumb_h = round(first.height * thumb_w / first.width)
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + 28)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(config.FONT_BOLD), 18)
    for i, (t, p) in enumerate(frames):
        im = Image.open(p).convert("RGB").resize((thumb_w, thumb_h))
        x, y = (i % cols) * thumb_w, (i // cols) * (thumb_h + 28)
        sheet.paste(im, (x, y + 28))
        draw.text((x + 6, y + 4), f"{t:.2f}s", fill="black", font=font)
    sheet.save(out, quality=85)
    return out


def run(job_dir: Path, final: bool = False) -> dict:
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    video = job_dir / ("final.mp4" if final else "preview.mp4")
    if not video.exists():
        raise FileNotFoundError(f"Chưa render: {video.name}")
    analysis = json.loads((job_dir / "analysis.json").read_text(encoding="utf-8"))
    dur = meta["duration"]

    times = {round(d["t"], 2) for d in analysis["detections"] if d["items"]}
    times |= {round(min(t + 0.05, dur - 0.05), 2) for t in range(int(dur) + 1)}
    times = sorted(t for t in times if 0 <= t < dur)

    qa_dir = job_dir / "qa"
    for old in qa_dir.glob("*.jpg") if qa_dir.exists() else []:
        old.unlink()
    detections = detect_text(video, times, qa_dir, job_dir / "usage.jsonl")
    residual = [{"t": d["t"], **it} for d in detections for it in d["items"]]

    frames = sorted(qa_dir.glob("f_*.jpg"))
    picked = frames if len(frames) <= 24 else frames[:: max(1, len(frames) // 24)][:24]
    sheet = contact_sheet([(float(p.stem.split("_")[1]), p) for p in picked], job_dir / "contact.jpg")

    report = {"video": video.name, "frames_checked": len(times), "residual_chinese": residual,
              "pass": not residual, "contact_sheet": sheet.name}
    (job_dir / "qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
