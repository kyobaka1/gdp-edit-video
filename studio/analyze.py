"""Phân tích video: tìm chữ Trung trên khung (Gemini) → gom thành sự kiện có khung giờ + ô pixel;
chép lời thoại tiếng Trung (Gemini audio). Ghi analysis.json + edl.json nháp (text_vi để trống).
"""

import json
import math
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import numpy as np
from google.genai import types
from PIL import Image

from studio import codex, gemini, media

FRAME_WIDTH = 720  # khung gửi Gemini (toạ độ chuẩn hoá nên không mất độ chính xác đáng kể)
BATCH = 10

BOX_SCHEMA = {
    "type": "object",
    "properties": {"frames": {"type": "array", "items": {"type": "object", "properties": {
        "frame_index": {"type": "integer"},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "text": {"type": "string"},
            "box_2d": {"type": "array", "items": {"type": "integer"}},
            "kind": {"type": "string", "enum": ["overlay", "scene"]},
            "left": {"type": "array", "items": {"type": "integer"}},
            "right": {"type": "array", "items": {"type": "integer"}},
        }, "required": ["text", "box_2d", "kind", "left", "right"]}},
    }, "required": ["frame_index", "items"]}}},
    "required": ["frames"],
}
BOX_PROMPT = (
    "Bạn nhận {n} khung hình đánh số 0..{last} theo thứ tự. Với MỖI khung, liệt kê mọi cụm chữ Trung Quốc "
    "(Hán tự) nhìn thấy được. Mỗi cụm (một dòng hoặc một khối liền) là một mục: text = chữ đọc được, "
    "box_2d = [ymin, xmin, ymax, xmax] chuẩn hoá 0-1000, bao TRỌN chữ và cả nền/khung trang trí ôm sát chữ "
    "nếu có. kind = \"overlay\" nếu là chữ ĐỒ HOẠ chèn khi dựng video (phụ đề, tiêu đề, nhãn tính năng, "
    "chú thích, giá, chữ trên màn hình đen/đồ hoạ); kind = \"scene\" nếu là chữ IN SẴN trên vật thể có thật "
    "trong cảnh quay (sản phẩm, bao bì, nhãn dán, chai lọ, hộp, phụ kiện, đạo cụ). left = [y, x] điểm GIỮA "
    "cạnh trái (đầu dòng chữ), right = [y, x] điểm GIỮA cạnh phải (cuối dòng), chuẩn hoá 0-1000. "
    "Một dòng chữ xoay chéo liền mạch là MỘT mục (đừng cắt đôi). Không có chữ Hán → items rỗng. "
    "Bỏ qua chữ Latin/số đứng riêng."
)


def _angle(it: dict, aspect: float) -> float:
    """Góc dòng chữ (độ, dương = đi lên trái→phải) từ 2 đầu dòng. Hỏi Gemini số góc trực tiếp thì nó dùng
    trục ảnh (y xuống) → ngược dấu (đo 20/10: báo −18° cho dòng đi lên); toạ độ 2 điểm thì không nhập nhằng."""
    try:
        (ly, lx), (ry, rx) = it["left"], it["right"]
    except (KeyError, TypeError, ValueError):
        return 0.0
    dx, dy = (rx - lx), (ry - ly) * aspect  # quy về cùng thang pixel (aspect = H/W)
    if abs(dx) < 1:
        return 0.0
    return -math.degrees(math.atan2(dy, dx))

TRANSCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "has_speech": {"type": "boolean"},
        "segments": {"type": "array", "items": {"type": "object", "properties": {
            "start": {"type": "number"}, "end": {"type": "number"}, "zh": {"type": "string"},
        }, "required": ["start", "end", "zh"]}},
    },
    "required": ["has_speech", "segments"],
}
TRANSCRIPT_PROMPT = (
    "Đây là audio của một video sản phẩm. Chép lại LỜI NÓI tiếng Trung (bỏ qua nhạc nền, tiếng động). "
    "Chia theo câu ngắn, mỗi câu có start/end tính bằng GIÂY (số thập phân) từ đầu file. "
    "Không có lời nói → has_speech=false, segments rỗng."
)


_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


def has_cjk(text: str) -> bool:
    """Gemini đôi khi liệt kê cả chữ Việt/Latin dù được dặn chỉ lấy Hán tự → lọc cứng bằng dải Unicode."""
    return bool(_CJK.search(text or ""))


def _detect_batch(paths: list[Path], usage: Path, label: str, engine: str = "gemini") -> list[list[dict]]:
    data = None
    if engine == "codex":  # soát bằng Codex/ChatGPT (không tốn tiền API); hỏng/hết usage → Gemini như cũ
        prompt = "".join(f"Khung {i} là ảnh đính kèm thứ {i + 1}. " for i in range(len(paths)))
        try:
            data = codex.ask_json(paths, prompt + BOX_PROMPT.format(n=len(paths), last=len(paths) - 1), BOX_SCHEMA)
            entry = {"label": label, "engine": "codex", "model": codex.MODEL}
        except codex.CodexUnavailable as exc:
            entry = {"label": label, "engine": "codex", "fallback": "gemini", "error": str(exc)[:200]}
        with usage.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if data is None:
        contents: list = []
        for i, p in enumerate(paths):
            contents += [f"Khung {i}:", gemini.image_part(p)]
        contents.append(BOX_PROMPT.format(n=len(paths), last=len(paths) - 1))
        try:
            data = gemini.generate_json(contents, BOX_SCHEMA, usage_log=usage, label=label)
        except RuntimeError:
            # đo 12/11 (ke0490): một lô 10 khung làm Gemini lặp khoảng trắng tới hết token → JSON hỏng cả 3 lần, lần
            # chạy lại vẫn y vậy → chia đôi lô rồi hỏi lại (lô 1 khung vẫn hỏng thì báo lỗi như cũ)
            if len(paths) < 2:
                raise
            h = len(paths) // 2
            return (_detect_batch(paths[:h], usage, f"{label}a", engine)
                    + _detect_batch(paths[h:], usage, f"{label}b", engine))
    with Image.open(paths[0]) as im:
        aspect = im.height / im.width
    out: list[list[dict]] = [[] for _ in paths]
    for fr in data.get("frames", []):
        idx = fr.get("frame_index")
        if isinstance(idx, int) and 0 <= idx < len(paths):
            out[idx] = [{**it, "angle": round(_angle(it, aspect), 1), **({"src": "codex"} if engine == "codex" and
                         "fallback" not in entry else {})} for it in fr.get("items", [])
                        if len(it.get("box_2d", [])) == 4 and has_cjk(it.get("text", ""))]
    return out


def detect_text(video: Path, times: list[float], frames_dir: Path, usage: Path, engine: str = "gemini") -> list[dict]:
    """Trả [{t, items:[{text, box_2d}]}] theo thứ tự thời gian. engine="codex" chỉ dùng để SOÁT (qa): ô Codex
    thô (phủ 63–100% ô thật, đo 22/10) → analyze đặt ô che phải giữ Gemini."""
    paths = media.extract_frames(video, times, frames_dir, width=FRAME_WIDTH)
    batches = [list(range(i, min(i + BATCH, len(paths)))) for i in range(0, len(paths), BATCH)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(
            lambda b: _detect_batch([paths[i] for i in b], usage, f"detect[{b[0]}..{b[-1]}]", engine), batches))
    detections = []
    for b, res in zip(batches, results):
        for i, items in zip(b, res):
            detections.append({"t": times[i], "items": items})
    return detections


def _px(box_2d: list[int], w: int, h: int) -> list[int]:
    y0, x0, y1, x1 = box_2d
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    return [round(x0 * w / 1000), round(y0 * h / 1000), round(x1 * w / 1000), round(y1 * h / 1000)]


def _iou(a: list[int], b: list[int]) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _same_text(a: str, b: str) -> bool:
    a, b = a.replace(" ", ""), b.replace(" ", "")
    if not a or not b:
        return False
    # Gemini hay đọc thiếu/thừa vài chữ (上墙 ↔ 上墙辅助贴) → chuỗi này nằm trong chuỗi kia cũng tính là cùng
    if min(len(a), len(b)) >= 2 and (a in b or b in a):
        return True
    return a == b or SequenceMatcher(None, a, b).ratio() >= 0.6


def group_events(detections: list[dict], w: int, h: int, interval: float) -> list[dict]:
    """Gom ô qua các khung liên tiếp thành sự kiện. Cho phép hụt 1 khung (Gemini đôi khi bỏ sót)."""
    events: list[dict] = []
    open_ev: list[dict] = []
    for det in detections:
        t = det["t"]
        matched_ids: set[int] = set()
        for it in det["items"]:
            box = _px(it["box_2d"], w, h)
            if box[2] - box[0] < 4 or box[3] - box[1] < 4:
                continue
            best, best_score = None, 0.0
            for ev in open_ev:
                if id(ev) in matched_ids:
                    continue
                last = ev["obs"][-1]
                if not _same_text(last["text"], it["text"]):
                    continue  # phụ đề cứng đổi câu tại CÙNG chỗ → sự kiện mới (mỗi câu một bản dịch)
                score = _iou(last["box"], box)
                cx_gap = abs((last["box"][0] + last["box"][2]) - (box[0] + box[2])) / 2 / w
                cy_gap = abs((last["box"][1] + last["box"][3]) - (box[1] + box[3])) / 2 / h
                if cy_gap < 0.05 and cx_gap < 0.3:
                    score = max(score, 0.5)  # chữ chạy ngang: IoU thấp nhưng cùng chữ, cùng hàng
                if score >= 0.3 and score > best_score:
                    best, best_score = ev, score
            if best is None:
                best = {"obs": [], "missed": 0}
                open_ev.append(best)
            best["obs"].append({"t": t, "box": box, "text": it["text"], "kind": it.get("kind", "overlay"),
                                "angle": float(it.get("angle") or 0.0)})
            best["missed"] = 0
            matched_ids.add(id(best))
        still_open = []
        for ev in open_ev:
            if id(ev) not in matched_ids:
                ev["missed"] += 1
            (still_open if ev["missed"] <= 1 else events).append(ev)
        open_ev = still_open
    events.extend(open_ev)

    out = []
    for ev in sorted(events, key=lambda e: e["obs"][0]["t"]):
        obs = ev["obs"]
        boxes = np.array([o["box"] for o in obs])
        union = [int(boxes[:, 0].min()), int(boxes[:, 1].min()), int(boxes[:, 2].max()), int(boxes[:, 3].max())]
        cx, cy = (boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2
        shift = float(max(np.ptp(cx), np.ptp(cy)))
        med_w = float(np.median(boxes[:, 2] - boxes[:, 0]))
        out.append({
            "zh": Counter(o["text"] for o in obs).most_common(1)[0][0],
            "kind": Counter(o.get("kind", "overlay") for o in obs).most_common(1)[0][0],
            "angle": round(float(np.median([o.get("angle", 0.0) for o in obs])), 1),
            "t_first": obs[0]["t"], "t_last": obs[-1]["t"], "n_frames": len(obs),
            "box_union": union,
            # tâm ô dịch > 15% bề rộng ô (và > 2% khung) = chữ chạy; dưới mức đó là nhiễu vị trí của Gemini
            "moving": bool(shift > max(0.15 * med_w, 0.02 * w)),
            "obs": obs,
        })
    return out


def _region_diff(cap: cv2.VideoCapture, t: float, box: list[int], ref: np.ndarray, scale: float) -> float:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    if not ok:
        return 0.0
    x0, y0, x1, y1 = (int(v * scale) for v in box)
    region = frame[max(0, y0):y1, max(0, x0):x1]
    if region.size == 0:  # ô Gemini suy biến (rộng/cao 0 hoặc ngoài khung) → cvtColor sẽ crash
        return 0.0
    crop = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if crop.shape != ref.shape:
        return 0.0
    return float(np.mean(np.abs(crop - ref)))


def refine_timing(video: Path, ev: dict, interval: float, fps: float, duration: float, scale: float) -> tuple[float, float]:
    """Tìm lúc chữ hiện/tắt giữa 2 khung mẫu bằng so điểm ảnh (OpenCV). Không rõ → lấy mốc an toàn (che dư)."""
    cap = cv2.VideoCapture(str(video))
    step = 1.0 / fps

    def ref_at(t: float, box: list[int]) -> np.ndarray | None:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            return None
        x0, y0, x1, y1 = (int(v * scale) for v in box)
        region = frame[max(0, y0):y1, max(0, x0):x1]
        if region.size == 0:  # ô suy biến → boundary() lấy mốc an toàn (che dư)
            return None
        return cv2.cvtColor(region, cv2.COLOR_BGR2GRAY).astype(np.float32)

    def boundary(t_out: float, t_in: float, box: list[int]) -> float:
        ref = ref_at(t_in, box)
        if ref is None or ref.size == 0:
            return t_out
        d_out = _region_diff(cap, t_out, box, ref, scale)
        if d_out < 6:  # vùng gần như không đổi → không phân biệt được, che dư cho chắc
            return t_out
        n = max(1, round(abs(t_in - t_out) / step))
        ts = [t_out + (t_in - t_out) * k / n for k in range(1, n + 1)]
        for tk in ts:  # đi từ phía "không có chữ" sang phía "có chữ"
            if _region_diff(cap, tk, box, ref, scale) <= d_out / 2:
                return tk
        return t_in

    first, last = ev["obs"][0], ev["obs"][-1]
    start = boundary(first["t"] - interval, first["t"], first["box"]) if first["t"] - interval > 0 else 0.0
    end = boundary(min(duration, last["t"] + interval), last["t"], last["box"]) if last["t"] + interval < duration else duration
    cap.release()
    pad = 2 * step
    return max(0.0, round(start - pad, 3)), min(duration, round(end + pad, 3))


def transcribe(video: Path, work: Path, usage: Path) -> dict:
    audio = media.extract_audio(video, work / "audio.mp3")  # mono 48kbps: ~360KB/phút, gửi inline được
    part = types.Part.from_bytes(data=audio.read_bytes(), mime_type="audio/mp3")
    return gemini.generate_json([part, TRANSCRIPT_PROMPT], TRANSCRIPT_SCHEMA, usage_log=usage, label="transcript")


def _extend_motion(ev: dict, interval: float, w: int, h: int) -> list[int]:
    """Kéo ô hợp theo vận tốc chữ thêm 1 nhịp mẫu về 2 phía (chữ còn chạy trước/sau khung quan sát)."""
    first, last = ev["obs"][0], ev["obs"][-1]
    dt = max(last["t"] - first["t"], interval)
    vx = ((last["box"][0] + last["box"][2]) - (first["box"][0] + first["box"][2])) / 2 / dt
    vy = ((last["box"][1] + last["box"][3]) - (first["box"][1] + first["box"][3])) / 2 / dt
    dx, dy = abs(vx) * interval, abs(vy) * interval
    x0, y0, x1, y1 = ev["box_union"]
    return [max(0, round(x0 - dx)), max(0, round(y0 - dy)), min(w, round(x1 + dx)), min(h, round(y1 + dy))]


def pad_box(box: list[int], w: int, h: int) -> list[int]:
    """Nới ô để bù sai số vị trí; trả [x, y, w, h] trong khung."""
    x0, y0, x1, y1 = box
    px = round((x1 - x0) * 0.04) + 8
    py = round((y1 - y0) * 0.08) + 8
    x0, y0 = max(0, x0 - px), max(0, y0 - py)
    x1, y1 = min(w, x1 + px), min(h, y1 + py)
    return [x0, y0, x1 - x0, y1 - y0]


def run(job_dir: Path, interval: float = 0.5, regroup: bool = False) -> dict:
    """regroup=True: dùng lại detections/transcript đã lưu trong analysis.json, KHÔNG gọi Gemini."""
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    video = job_dir / meta["source"]
    w, h, fps, duration = meta["width"], meta["height"], meta["fps"], meta["duration"]
    usage = job_dir / "usage.jsonl"

    if regroup:
        saved = json.loads((job_dir / "analysis.json").read_text(encoding="utf-8"))
        interval, detections, transcript = saved["interval"], saved["detections"], saved["transcript"]
    else:
        n = int(duration / interval)
        times = [round(min(i * interval + 0.05, duration - 0.05), 3) for i in range(n + 1)]
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_det = ex.submit(detect_text, video, times, job_dir / "frames", usage)
            fut_tr = ex.submit(transcribe, video, job_dir, usage) if meta["has_audio"] else None
            detections = fut_det.result()
            transcript = fut_tr.result() if fut_tr else {"has_speech": False, "segments": []}

    events = group_events(detections, w, h, interval)
    cap_w = cv2.VideoCapture(str(video)).get(cv2.CAP_PROP_FRAME_WIDTH) or w
    scale = cap_w / w
    overlays = []
    for i, ev in enumerate(events, 1):
        if ev["moving"]:
            # Chữ chạy: so điểm ảnh không tin được → che dư cả nhịp mẫu ở 2 đầu, nới ô theo hướng chạy.
            start = max(0.0, round(ev["t_first"] - interval, 3))
            end = min(duration, round(ev["t_last"] + interval, 3))
            box = pad_box(_extend_motion(ev, interval, w, h), w, h)
        else:
            start, end = refine_timing(video, ev, interval, fps, duration, scale)
            box = pad_box(ev["box_union"], w, h)
        overlays.append({
            "id": f"o{i}", "start": start, "end": end, "box": box, "zh": ev["zh"], "text_vi": "",
            # chữ in trên sản phẩm/bao bì/phụ kiện trong cảnh → giữ nguyên (Sếp chốt 20/10)
            "kind": ev["kind"], "mode": "keep" if ev["kind"] == "scene" else "label",
            "angle": ev["angle"] if abs(ev["angle"]) >= 4 else 0.0,  # <4° coi như ngang (nhiễu)
            "moving": ev["moving"], "n_frames": ev["n_frames"],
            "needs_review": ev["moving"] and box[2] * box[3] > 0.35 * w * h,
        })

    analysis = {"interval": interval, "detections": detections, "events": events, "transcript": transcript}
    (job_dir / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    draft = {
        "version": 1,
        "style": {"bg": "#FFFFFF", "border": "#D7262E", "text": "#1A1A1A"},
        "overlays": overlays,
        "subtitles": [{"start": s["start"], "end": s["end"], "zh": s["zh"], "text_vi": ""}
                      for s in transcript.get("segments", [])],
        "subtitle_box": {"y_pct": 0.78, "h_pct": 0.075, "w_pct": 0.9},
        "audio": {"mode": "mute" if transcript.get("has_speech") else "keep", "music": None, "music_volume": 0.25},
    }
    (job_dir / "edl.draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    return draft
