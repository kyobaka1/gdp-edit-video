"""Kiểm video đã dựng: còn sót chữ Hán không? Lấy khung tại MỌI thời điểm từng thấy chữ Trung ở video
gốc + mỗi giây một khung, hỏi Gemini. Ghi qa.json + contact.jpg (ảnh ghép để người/Claude soát mắt)."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from studio import config, media
from studio.analyze import _iou, _px, _same_text, detect_text, has_cjk, pad_box


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


def _screen_stats(usage: Path, mark: int) -> dict:
    """Lượt qa này: bao nhiêu lô khung Codex soát được, bao nhiêu lô phải rơi về Gemini (+ lý do đầu tiên)."""
    with usage.open("rb") as fh:
        fh.seek(mark)
        rows = [json.loads(ln) for ln in fh.read().decode("utf-8").splitlines() if ln.strip()]
    cx = [r for r in rows if r.get("engine") == "codex"]
    fb = [r for r in cx if r.get("fallback")]
    return {"codex_batches": len(cx) - len(fb), "gemini_fallback_batches": len(fb),
            "fallback_reason": fb[0]["error"] if fb else ""}


def run(job_dir: Path, final: bool = False) -> dict:
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    video = job_dir / ("final.mp4" if final else "preview.mp4")
    if not video.exists():
        raise FileNotFoundError(f"Chưa render: {video.name}")
    analysis = json.loads((job_dir / "analysis.json").read_text(encoding="utf-8"))
    # Chỉ kiểm PHẦN VIDEO CHÍNH (meta.duration): outro nối sau là video có sẵn của shop → bỏ qua, không tốn
    # token kiểm lại mỗi lần (Sếp chốt 20/10). Logo/watermark cũng không đặt trên outro.
    dur = meta["duration"]

    times = {round(d["t"], 2) for d in analysis["detections"] if d["items"]}
    times |= {round(min(t + 0.05, dur - 0.05), 2) for t in range(int(dur) + 1)}
    times = sorted(t for t in times if 0 <= t < dur)

    qa_dir = job_dir / "qa"
    for old in qa_dir.glob("*.jpg") if qa_dir.exists() else []:
        old.unlink()
    usage = job_dir / "usage.jsonl"
    mark = usage.stat().st_size if usage.exists() else 0
    # Soát bằng Codex/ChatGPT trước (Sếp 22/10: Gemini tốn ~344k/ngày, qa chiếm ~61% số token detect). Codex đọc
    # chữ tốt nhưng ô thô → khung nào Codex báo còn chữ đồ hoạ thì Gemini XÁC NHẬN lại đúng khung đó (lọc báo
    # nhầm + ô chính xác cho `patch`). Codex hỏng/hết usage → detect_text tự rơi về Gemini cho cả lượt.
    detections = detect_text(video, times, qa_dir, usage, engine="codex")
    flagged = sorted({d["t"] for d in detections for it in d["items"]
                      if it.get("src") == "codex" and it.get("kind") != "scene" and abs(it["box_2d"][2] - it["box_2d"][0]) > 25})
    confirm_error = ""
    if flagged:
        try:
            confirmed = {d["t"]: d["items"] for d in detect_text(video, flagged, qa_dir / "confirm", usage)}
            detections = [{**d, "items": confirmed[d["t"]]} if d["t"] in confirmed else d for d in detections]
        except Exception as exc:  # Gemini hết tiền/lỗi → giữ kết quả Codex (ô thô), vẫn đánh CHƯA ĐẠT nếu có sót
            confirm_error = str(exc)[:200]
    all_found = [{"t": d["t"], **it} for d in detections for it in d["items"]]
    # chữ in trên sản phẩm/bao bì/phụ kiện trong cảnh được GIỮ NGUYÊN (Sếp chốt 20/10) → không tính là sót
    scene = [it for it in all_found if it.get("kind") == "scene"]
    found = [it for it in all_found if it.get("kind") != "scene"]
    # Ô chữ cao < 2,5% khung (vd nhãn in trên chai đạo cụ, chữ ~10px/960) không đọc được trên điện thoại
    # → báo trong tiny_ignored, không đánh trượt. Sếp muốn khắt hơn thì hạ ngưỡng này.
    def _tall(it: dict) -> bool:
        y0, _, y1, _ = it["box_2d"]
        return abs(y1 - y0) > 25
    residual = [it for it in found if _tall(it)]
    tiny = [it for it in found if not _tall(it)]

    frames = sorted(qa_dir.glob("f_*.jpg"))
    picked = frames if len(frames) <= 24 else frames[:: max(1, len(frames) // 24)][:24]
    sheet = contact_sheet([(float(p.stem.split("_")[1]), p) for p in picked], job_dir / "contact.jpg")

    report = {"video": video.name, "frames_checked": len(times), "checked_until": dur, "outro_skipped": True,
              "screen": _screen_stats(usage, mark), "gemini_confirmed_frames": flagged,
              "gemini_confirm_error": confirm_error,  # khác rỗng = chỗ sót là ô Codex (thô), patch xong phải soát mắt
              "residual_chinese": residual,
              "tiny_ignored": tiny, "scene_kept": scene, "pass": not residual, "contact_sheet": sheet.name}
    (job_dir / "qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def patch(job_dir: Path, margin: float = 0.5) -> list[str]:
    """Đưa chỗ sót của qa.json vào edl.json: cùng chữ gốc + trùng ô cũ (IoU ≥ 0,3 hoặc nằm gọn trong ô) → nới
    khung giờ ô đó ±margin; không trùng → thêm ô mới mode=blur, needs_review (Claude/Sếp quyết lại)."""
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    W, H, dur = meta["width"], meta["height"], meta["duration"]
    rep = json.loads((job_dir / "qa.json").read_text(encoding="utf-8"))
    edl_path = job_dir / "edl.json"
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    log: list[str] = []
    for r in rep["residual_chinese"]:
        if not has_cjk(r.get("text", "")):
            continue
        x0, y0, x1, y1 = _px(r["box_2d"], W, H)
        t = r["t"]
        best, best_score = None, 0.0
        for o in edl["overlays"]:
            # bắt buộc CÙNG chữ gốc: ô lớn (vd câu mở đầu) có thể trùm vị trí một nhãn nhỏ khác hẳn
            if o.get("skip") or not _same_text(o.get("zh", ""), r["text"]):
                continue
            ox, oy, ow, oh = o["box"]
            ob = [ox, oy, ox + ow, oy + oh]
            inside = x0 >= ob[0] - 4 and y0 >= ob[1] - 4 and x1 <= ob[2] + 4 and y1 <= ob[3] + 4
            score = max(_iou(ob, [x0, y0, x1, y1]), 1.0 if inside else 0.0)
            if score >= 0.3 and score > best_score:
                best, best_score = o, score
        if best is not None:
            old = (best["start"], best["end"])
            best["start"] = round(max(0.0, min(best["start"], t - margin)), 3)
            best["end"] = round(min(dur, max(best["end"], t + margin)), 3)
            if (best["start"], best["end"]) != old:
                log.append(f"{best['id']}: nới {old[0]}–{old[1]} → {best['start']}–{best['end']} (sót {r['text']} @ {t}s)")
        else:
            nid = f"q{sum(1 for o in edl['overlays'] if o['id'].startswith('q')) + 1}"
            box = pad_box([x0, y0, x1, y1], W, H)
            edl["overlays"].append({
                "id": nid, "start": round(max(0.0, t - margin), 3), "end": round(min(dur, t + margin), 3),
                "box": box, "zh": r["text"], "text_vi": "", "mode": "blur", "needs_review": True,
            })
            log.append(f"{nid}: ô MỚI blur {box} {t - margin:.2f}–{t + margin:.2f}s ({r['text']}) — cần xem")
    edl_path.write_text(json.dumps(edl, ensure_ascii=False, indent=2), encoding="utf-8")
    return log
