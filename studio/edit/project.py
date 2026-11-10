"""Job dựng video từ source quay sẵn: jobs/<id>/ với meta.json kind="edit".

  sources/<key>.<ext>     clip (hình + tiếng) hoặc file giọng riêng (chỉ tiếng); key ngắn c01, c02… / vo
  sources.json            thông số + đường gốc + chép lời (words có mốc) + ảnh lưới từng nguồn
  asr/<key>.json          kết quả Whisper (cache) · asr/<key>.fixed.json lời đã đối chiếu văn bản chuẩn
  sheets/<key>.jpg        ảnh lưới 8 khung có mốc giây — Claude xem để chọn đoạn minh hoạ
  sound/<key>.json        tiếng động (sound.py, cache): cụm tiếng #n, mốc bật, điểm lặng — cắt clip KHÔNG LỜI (c.sound)
  sheets/<key>.sound.jpg  ảnh soát: dải khung 0,5s + sóng âm cùng trục, vạch giây, cụm #n, mốc bật, điểm lặng
  plan.md                 PLAN của Sếp (hoặc Claude soạn khi Sếp bảo "tự làm") — ý, thứ tự, cảnh, chữ nhấn
  cut.py → edit.json      Claude viết cut.py (studio/edit/cutlib.py) = quyết định dựng
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from studio import config, media
from studio.edit import asr, sound

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
STILL_SEC = 15.0  # ảnh tĩnh → clip 15s để làm cảnh minh hoạ (cover push = zoom đẩy cho ảnh "sống")
OUT = {"w": 1080, "h": 1920, "fps": 30}  # GĐ1: 9:16 TikTok (Sếp chốt 05/11); 3:4 Shopee làm sau


def job_path(job_id: str) -> Path:
    d = config.JOBS / job_id
    meta = d / "meta.json"
    if not meta.exists() or json.loads(meta.read_text(encoding="utf-8")).get("kind") != "edit":
        raise SystemExit(f"Không thấy job dựng {job_id} (cần meta.json kind=edit ở {d})")
    return d


def mode(d: Path) -> bool | None:
    return json.loads((d / "meta.json").read_text(encoding="utf-8")).get("capcut")


def set_mode(job_id: str, capcut: bool) -> None:
    d = job_path(job_id)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    meta["capcut"] = capcut
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_sources(d: Path) -> dict:
    p = d / "sources.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_sources(d: Path, src: dict) -> None:
    (d / "sources.json").write_text(json.dumps(src, ensure_ascii=False, indent=1), encoding="utf-8")


def _probe(p: Path) -> dict:
    out = media.run([config.FFPROBE, "-v", "error", "-show_entries",
                     "format=duration:stream=codec_type,width,height,r_frame_rate:stream_side_data=rotation",
                     "-of", "json", str(p)]).stdout
    info = json.loads(out)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    a = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    res = {"duration": round(float(info["format"]["duration"]), 3), "has_audio": a, "has_video": bool(v)}
    if v:
        num, den = (v.get("r_frame_rate") or "30/1").split("/")
        rot = next((abs(int(sd.get("rotation", 0))) for sd in v.get("side_data_list", []) if "rotation" in sd), 0)
        w, h = (v["height"], v["width"]) if rot in (90, 270) else (v["width"], v["height"])
        res.update(width=w, height=h, fps=round(float(num) / float(den or 1), 3))
        if media.is_hdr(p):   # build.Reader + ảnh lưới tự đưa về SDR; ghi lại để Claude biết mà soát màu
            res["hdr"] = True
    return res


MODES = {"co": True, "có": True, "yes": True, "capcut": True, "khong": False, "không": False, "no": False, "mp4": False}
MODE_TEXT = {True: "CÓ dùng CapCut (giao bản nháp CapCut, dựng viên hoàn thiện + xuất trong CapCut)",
             False: "KHÔNG dùng CapCut (Studio làm hết, giao final.mp4)"}


def parse_mode(v) -> bool | None:
    return None if v is None else MODES.get(str(v).strip().lower())


def plan_mode(plan: Path | None) -> bool | None:
    """Dòng `CapCut: có|không` (hoặc `- CapCut: …`) trong plan.md."""
    if not plan or not plan.exists():
        return None
    for line in plan.read_text(encoding="utf-8").splitlines():
        s = line.strip().lstrip("-* ").strip()
        if s.lower().startswith("capcut:"):
            word = s.split(":", 1)[1].strip().split()[0].strip(".,;()") if s.split(":", 1)[1].strip() else ""
            return parse_mode(word)
    return None


def new(job_id: str, inputs: list[Path], plan: Path | None = None, capcut: bool | None = None) -> Path:
    # Sếp chốt 05/11: TRƯỚC khi dựng phải rõ CÓ hay KHÔNG dùng CapCut — chưa rõ thì dừng, hỏi Sếp, không tự đoán.
    mode = capcut if capcut is not None else plan_mode(plan)
    if mode is None:
        raise SystemExit("DỪNG: chưa rõ chế độ dựng. Hỏi Sếp trước khi edit:\n"
                         f"  • {MODE_TEXT[False]}\n  • {MODE_TEXT[True]}\n"
                         "rồi chạy lại với --capcut khong | --capcut co (hoặc ghi dòng `CapCut: có|không` trong plan.md)")
    files = []
    for p in inputs:
        files += sorted(q for q in p.iterdir() if q.suffix.lower() in VIDEO_EXT | AUDIO_EXT | IMAGE_EXT) \
            if p.is_dir() else [p]
    if not files:
        raise SystemExit("Không có file video/tiếng nào")
    d = config.JOBS / job_id
    if d.exists():
        raise SystemExit(f"Job {job_id} đã có ({d})")
    (d / "sources").mkdir(parents=True)
    meta = {"id": job_id, "kind": "edit", "created": f"{datetime.now():%Y-%m-%d %H:%M}", "out": OUT, "capcut": mode}
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if plan:
        shutil.copy2(plan, d / "plan.md")
    src = {}
    for i, f in enumerate(files, 1):
        ext = f.suffix.lower()
        _add(d, src, f, f"c{i:02d}" if ext in VIDEO_EXT else f"i{i:02d}" if ext in IMAGE_EXT else f"a{i:02d}")
    save_sources(d, src)
    return d


def _add(d: Path, src: dict, f: Path, key: str) -> None:
    dst = d / "sources" / f"{key}{f.suffix.lower()}"
    shutil.copy2(f, dst)
    if f.suffix.lower() in IMAGE_EXT:
        src[key] = _still(d, f, dst, key)
        return
    src[key] = {"file": f"sources/{dst.name}", "origin": str(f.resolve()), **_probe(dst)}


def _still(d: Path, f: Path, img: Path, key: str) -> dict:
    """Ảnh tĩnh (chụp thật hoặc ảnh AI của `vs.py gen`) → clip STILL_SEC giây để `cover()` dùng như cảnh quay."""
    from PIL import Image
    im = Image.open(img)
    if im.mode in ("RGBA", "LA") and min(im.getchannel("A").getextrema()) < 250:
        raise SystemExit(f"{f.name}: ảnh nền trong suốt là miếng đồ hoạ (cắt dán/sticker), không làm cảnh minh hoạ "
                         "được — dùng ảnh có nền")
    clip = d / "sources" / f"{key}.mp4"
    media.run([config.FFMPEG, "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-t", f"{STILL_SEC}", "-i",
               str(img), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p", "-c:v", "libx264",
               "-preset", "veryfast", "-crf", "16", "-tune", "stillimage", str(clip)])
    info = {"file": f"sources/{clip.name}", "image": f"sources/{img.name}", "origin": str(f.resolve()),
            "still": True, **_probe(clip)}
    side = f.with_suffix(".json")  # vs.py gen ghi kèm nguồn AI
    if side.exists():
        meta = json.loads(side.read_text(encoding="utf-8"))
        if meta.get("kind") == "ai":
            info["ai"] = {k: meta.get(k) for k in ("engine", "model", "prompt", "created")}
    return info


def add(job_id: str, f: Path, key: str, ref_text: Path | None = None) -> dict:
    d = job_path(job_id)
    src = load_sources(d)
    if key in src:
        raise SystemExit(f"Đã có nguồn {key}")
    _add(d, src, f, key)
    if ref_text:
        src[key]["reference"] = ref_text.read_text(encoding="utf-8").strip()
    save_sources(d, src)
    return src[key]


def hint(d: Path) -> str:
    """Tên riêng trong plan.md (dòng `Từ khoá:` / `Tên riêng:`) → gợi ý chính tả cho Whisper."""
    p = d / "plan.md"
    if not p.exists():
        return ""
    for line in p.read_text(encoding="utf-8").splitlines():
        low = line.lower()
        if low.startswith(("từ khoá:", "từ khóa:", "tên riêng:", "- từ khoá:", "- tên riêng:")):
            return line.split(":", 1)[1].strip()
    return ""


def ingest(job_id: str) -> dict:
    """Chép lời (có lời) + ảnh lưới (có hình) mọi nguồn. Nguồn đã có văn bản chuẩn (`reference`) → tự đối chiếu."""
    d = job_path(job_id)
    src = load_sources(d)
    (d / "asr").mkdir(exist_ok=True)
    (d / "sheets").mkdir(exist_ok=True)
    h = hint(d)
    for key, s in src.items():
        f = d / s["file"]
        if s.get("has_video"):
            s["sheet"] = f"sheets/{key}.jpg"
            contact_sheet(f, s["duration"], d / s["sheet"], key)
        if s.get("has_audio"):
            r = asr.transcribe(f, d / "asr" / f"{key}.json", hint=h)
            s["speech"] = r["speech"]
            s["dropped"] = r["dropped"]
            fixed = d / "asr" / f"{key}.fixed.json"
            if s.get("reference") and fixed.exists() and fixed.stat().st_mtime >= (d / "asr" / f"{key}.json").stat().st_mtime \
                    and json.loads(fixed.read_text(encoding="utf-8")).get("reference") == s["reference"]:
                s["words_file"] = f"asr/{key}.fixed.json"   # đã đối chiếu, lời Whisper không đổi → giữ nguyên (10/11: ingest
                # lại từng đối chiếu lại kiểu tin hết văn bản, làm hỏng bản `fix --hear` — c01 thêm "Mọi người ơi" 0–0,36s)
            elif s.get("reference"):
                fix(job_id, key, s["reference"], src=src)
            else:
                s.setdefault("words_file", f"asr/{key}.json")
            _sound(d, key, s)
    save_sources(d, src)
    return src


def no_speech(s: dict) -> bool:
    """Nguồn KHÔNG LỜI (hoặc lời rất ít: < 1s, hay < 10% thời lượng) → cắt theo tiếng động thay cho lời."""
    sp = float(s.get("speech") or 0.0)
    return sp < 1.0 or sp < 0.1 * float(s.get("duration") or 0.0)


def _sound(d: Path, key: str, s: dict) -> dict:
    """Phân tích tiếng động (cache sound/<key>.json) + ảnh soát sheets/<key>.sound.jpg (làm lại khi phân tích đổi)."""
    f = d / s["file"]
    info, fresh = sound.analyze(f, d / "sound" / f"{key}.json")
    sheet = d / "sheets" / f"{key}.sound.jpg"
    if fresh or not sheet.exists():
        sheet.parent.mkdir(exist_ok=True)
        sound.sheet(f, info, sheet, key, {"width": s["width"], "height": s["height"]} if s.get("has_video") and not s.get("still")
                    else None)
    s["sound"] = {"file": f"sound/{key}.json", "sheet": f"sheets/{key}.sound.jpg", "clusters": len(info["clusters"]),
                  "onsets": len(info["onsets"]), "floor_db": info["floor_db"]}
    return info


def sound_info(d: Path, key: str, src: dict | None = None) -> dict:
    """Kết quả tiếng động của nguồn `key` — chưa ingest (job cũ) thì phân tích ngay (nhanh, numpy)."""
    s = (src or load_sources(d))[key]
    p = d / (s.get("sound") or {}).get("file", f"sound/{key}.json")
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return sound.analyze(d / s["file"], d / "sound" / f"{key}.json")[0]


def fix(job_id: str, key: str, reference: str, src: dict | None = None, heard: bool = False) -> list[dict]:
    """Đối chiếu lời nguồn `key` với văn bản chuẩn → asr/<key>.fixed.json (giữ mốc Whisper, chữ chuẩn).
    heard=True: văn bản là Gemini nghe lại (có thể nghe nhầm/thêm) → không tin chỗ thêm nhiều từ."""
    d = job_path(job_id)
    own = src is None
    src = src or load_sources(d)
    raw = json.loads((d / "asr" / f"{key}.json").read_text(encoding="utf-8"))
    words, changes = asr.correct(raw["words"], reference, trust=not heard)
    out = d / "asr" / f"{key}.fixed.json"
    out.write_text(json.dumps({"reference": reference, "changes": changes, "words": words}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    src[key]["reference"] = reference
    src[key]["words_file"] = f"asr/{key}.fixed.json"
    src[key]["fixes"] = len(changes)
    if own:
        save_sources(d, src)
    return changes


def words(d: Path, key: str, src: dict | None = None) -> list[dict]:
    s = (src or load_sources(d))[key]
    wf = s.get("words_file")
    return json.loads((d / wf).read_text(encoding="utf-8"))["words"] if wf else []


def contact_sheet(video: Path, duration: float, out: Path, label: str, n: int = 8) -> Path:
    font = config.FONT_REGULAR.as_posix().replace(":", "\\:")   # font đi kèm repo (trước gắn cứng Arial của Windows → lỗi trên Mac)
    sdr = media.sdr_filter(video)
    vf = (f"fps={n / max(duration, 0.1):.5f},scale=-2:300," + (f"{sdr}," if sdr else "") +
          "drawtext=text='%{pts\\:flt}':x=6:y=6:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.65:"
          f"fontfile='{font}',"
          f"tile={n}x1:padding=3")
    media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(video), "-vf", vf, "-frames:v", "1", str(out)])
    return out


def describe_sound(info: dict, key: str, sheet: str | None = None, limit: int = 40) -> list[str]:
    """Bảng cụm tiếng động có mốc giây (thay cho lời) — để Claude viết c.sound(key, "#n" | giây, …)."""
    cs, qs = info.get("clusters") or [], info.get("quiet") or []
    out = [f"     KHÔNG LỜI → cắt theo tiếng: c.sound({key!r}, \"#1\", \"#3\") | c.sound({key!r}, giây, giây) · "
           f"chữ: c.cap(\"…\", at=\"{key}#n\") · ảnh soát {sheet or '—'}",
           f"     nền {info['floor_db']:.0f} dB · ngưỡng cụm {info['thr_db']:.0f} dB · {len(cs)} cụm · "
           f"{len(info.get('onsets') or [])} mốc bật"]
    if not cs:
        out.append("     (không có tiếng động nào nổi trên nền — clip yên lặng / chỉ tiếng nền đều)")
        return out
    contrast = info["top_db"] - info["floor_db"]
    cover = sum(c["dur"] for c in cs) / max(0.1, float(info["duration"]))
    if contrast < 12 or cover > 0.75:   # quạt / xe / máy bay: "cụm" chỉ là nền dao động → đừng tin điểm cắt theo tiếng
        out.append(f"     ⚠ tiếng nền ĐỀU (đỉnh chỉ hơn nền {contrast:.0f} dB, cụm phủ {cover:.0%} thời lượng) — cụm tiếng ít ý "
                   "nghĩa, chọn điểm cắt theo HÌNH (ảnh soát); mép cắt vẫn vuốt 30ms")
    out.append("        #    từ       đến     dài    đỉnh   kiểu      mốc bật (giây nguồn)")
    for c in cs[:limit]:
        ons = ", ".join(f"{t:.2f}" for t in c["onsets"][:6]) + (" …" if len(c["onsets"]) > 6 else "")
        out.append(f"      {'#' + str(c['n']):>4} {c['t0']:6.2f} – {c['t1']:6.2f}  {c['dur']:5.2f}s  {c['peak_db']:5.0f}dB  "
                   f"{c['kind']:<8}  {ons or '—'}")
    if len(cs) > limit:
        out.append(f"      … còn {len(cs) - limit} cụm (xem {sheet or 'sound/' + key + '.json'})")
    good = [q for q in qs if q["hi"] - q["lo"] >= 0.15]
    if good:
        out.append("     điểm lặng (cắt an toàn): " + " · ".join(f"{q['t']:.2f}" for q in good[:24])
                   + (" …" if len(good) > 24 else ""))
    return out


def describe(job_id: str) -> str:
    """Bảng tóm tắt cho Claude: từng nguồn — loại, thời lượng, lời (có mốc) — để viết cut.py."""
    d = job_path(job_id)
    src = load_sources(d)
    m = mode(d)
    lines = [f"Chế độ: {MODE_TEXT[m]}" if m is not None else
             "Chế độ: CHƯA RÕ — hỏi Sếp có/không dùng CapCut rồi `vs.py edit mode <id> co|khong`"]
    for key, s in src.items():
        kind = ("ẢNH AI" if s.get("ai") else "ảnh tĩnh") if s.get("still") else "clip" if s.get("has_video") else "tiếng"
        meta = f"{s['width']}x{s['height']} {s['fps']}fps" if s.get("has_video") else ""
        meta += " · nguồn HDR (tự đưa về SDR — soát màu ảnh lưới)" if s.get("hdr") else ""
        ws = words(d, key, src)
        lines.append(f"[{key}] {kind} {s['duration']:.1f}s {meta} · lời {s.get('speech', 0):.1f}s"
                     + (f" · đã đối chiếu ({s.get('fixes', 0)} chỗ sửa)" if s.get("reference") else
                        (" · CHƯA đối chiếu (vs.py edit fix … --hear)" if ws else "")))
        for dr in s.get("dropped", []):
            lines.append(f"     bỏ câu bịa {dr['start']}–{dr['end']}s: {dr['text'][:60]} ({dr['why']})")
        sp = s.get("sound") or {}
        if sp and (d / sp["file"]).exists():
            if s.get("has_audio") and no_speech(s):
                lines += describe_sound(json.loads((d / sp["file"]).read_text(encoding="utf-8")), key, sp.get("sheet"))
            else:
                lines.append(f"     tiếng động: {sp['clusters']} cụm, {sp['onsets']} mốc bật, nền {sp['floor_db']:.0f} dB "
                             f"({sp['file']} · ảnh {sp.get('sheet')})")
        if ws:
            row, t0 = [], ws[0]["start"]
            for i, w in enumerate(ws):
                row.append(f"{w['w']}{w.get('punct', '')}")
                if w.get("punct") in (".", "?", "!") or len(row) >= 14 or i == len(ws) - 1:
                    lines.append(f"     {t0:6.2f}–{w['end']:6.2f}  {' '.join(row)}")
                    row = []
                    if i + 1 < len(ws):
                        t0 = ws[i + 1]["start"]
    return "\n".join(lines)
