"""Dựng video từ edl.json: vẽ ô chữ PNG (Pillow) rồi ghép bằng ffmpeg overlay theo khung giờ."""

import json
from pathlib import Path

from studio import config, media
from studio.overlay import render_label


class EdlError(ValueError):
    pass


def _srt_time(t: float) -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def validate(edl: dict, meta: dict, allow_empty: bool) -> list[dict]:
    """Trả danh sách lớp phủ cần vẽ (ô chữ + phụ đề), mỗi lớp {start,end,x,y,w,h,text,style}."""
    W, H, dur = meta["width"], meta["height"], meta["duration"]
    style = edl.get("style", {})
    layers, problems = [], []
    for o in edl.get("overlays", []):
        if o.get("skip"):
            continue
        x, y, w, h = (int(v) for v in o["box"])
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > W or y + h > H:
            problems.append(f"{o['id']}: ô {o['box']} ra ngoài khung {W}x{H}")
        if not (0 <= o["start"] < o["end"] <= dur + 0.05):
            problems.append(f"{o['id']}: khung giờ {o['start']}–{o['end']} sai (video {dur}s)")
        text = (o.get("text_vi") or "").strip()
        if not text and not allow_empty:
            problems.append(f"{o['id']}: chưa có text_vi (chữ gốc: {o.get('zh')})")
        layers.append({"start": o["start"], "end": o["end"], "x": x, "y": y, "w": w, "h": h,
                       "text": text, "style": {**style, **o.get("style", {})}})
    sb = edl.get("subtitle_box", {"y_pct": 0.78, "h_pct": 0.075, "w_pct": 0.9})
    sw, sh = round(W * sb["w_pct"]), round(H * sb["h_pct"])
    sx, sy = (W - sw) // 2, round(H * sb["y_pct"])
    for i, s in enumerate(edl.get("subtitles", []), 1):
        text = (s.get("text_vi") or "").strip()
        if s.get("skip") or not text:
            continue
        if not (0 <= s["start"] < s["end"] <= dur + 0.05):
            problems.append(f"phụ đề {i}: khung giờ {s['start']}–{s['end']} sai")
        layers.append({"start": s["start"], "end": s["end"], "x": sx, "y": sy, "w": sw, "h": sh,
                       "text": text, "style": {**style, **edl.get("subtitle_style", {})}})
    if problems:
        raise EdlError("edl.json chưa hợp lệ:\n  - " + "\n  - ".join(problems))
    return layers


def run(job_dir: Path, final: bool = False, allow_empty: bool = False) -> Path:
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    edl_path = job_dir / "edl.json"
    if not edl_path.exists():
        raise EdlError("Chưa có edl.json (copy từ edl.draft.json rồi điền text_vi)")
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    layers = validate(edl, meta, allow_empty)

    labels_dir = job_dir / "labels"
    labels_dir.mkdir(exist_ok=True)
    for old in labels_dir.glob("*.png"):
        old.unlink()
    inputs = ["-i", str(job_dir / meta["source"])]
    chain, prev = [], "0:v"
    for i, L in enumerate(layers, 1):
        st = L["style"]
        png = labels_dir / f"l{i:03}.png"
        render_label(L["text"] or " ", L["w"], L["h"], bg=st.get("bg", "#FFFFFF"),
                     border=st.get("border", "#D7262E"), text_color=st.get("text", "#1A1A1A")).save(png)
        inputs += ["-i", str(png)]
        out = f"v{i}"
        chain.append(f"[{prev}][{i}:v]overlay={L['x']}:{L['y']}:enable='between(t,{L['start']:.3f},{L['end']:.3f})'[{out}]")
        prev = out
    scale = ",scale=-2:960" if not final else ""
    chain.append(f"[{prev}]format=yuv420p{scale}[vout]")

    audio = edl.get("audio", {})
    mode = audio.get("mode", "keep")
    a_args: list[str]
    n_in = len(layers) + 1
    if mode == "keep" and meta["has_audio"]:
        a_args = ["-map", "0:a:0", "-c:a", "aac", "-b:a", "160k"]
    elif mode == "music":
        music = Path(audio.get("music") or "")
        if not music.is_absolute():
            music = config.ROOT / music
        if not music.exists():
            raise EdlError(f"audio.mode=music nhưng không thấy file nhạc: {music}")
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        chain.append(f"[{n_in}:a]volume={audio.get('music_volume', 0.25)}[aout]")
        a_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
    else:  # mute: track im lặng để sàn không từ chối video thiếu audio
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        a_args = ["-map", f"{n_in}:a", "-c:a", "aac", "-b:a", "96k"]

    out_path = job_dir / ("final.mp4" if final else "preview.mp4")
    filter_file = job_dir / "filter.txt"
    filter_file.write_text(";\n".join(chain), encoding="utf-8")
    v_args = ["-c:v", "libx264", "-preset", "medium" if final else "veryfast", "-crf", "18" if final else "26"]
    media.run([config.FFMPEG, "-y", "-v", "error", *inputs, "-/filter_complex", str(filter_file),
               "-map", "[vout]", *v_args, *a_args, "-t", f"{meta['duration']:.3f}",
               "-movflags", "+faststart", str(out_path)])

    subs = [s for s in edl.get("subtitles", []) if (s.get("text_vi") or "").strip() and not s.get("skip")]
    if subs:
        srt = "\n".join(f"{i}\n{_srt_time(s['start'])} --> {_srt_time(s['end'])}\n{s['text_vi'].strip()}\n"
                        for i, s in enumerate(subs, 1))
        out_path.with_suffix(".srt").write_text(srt, encoding="utf-8")
    return out_path
