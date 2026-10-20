"""Dựng video từ edl.json: vẽ ô chữ PNG (Pillow) rồi ghép bằng ffmpeg overlay theo khung giờ."""

import json
import math
from pathlib import Path

from PIL import Image

from studio import config, media
from studio.overlay import grow_to_min_font, render_label
from studio.templates import TemplateRenderer


class EdlError(ValueError):
    pass


def _srt_time(t: float) -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def rotated_rect(w: int, h: int, angle: float) -> tuple[int, int]:
    """Từ ô bao ngang (w×h) của một dòng chữ nghiêng `angle` độ → kích thước khung xoay ôm dòng chữ.
    Giải W = a·cos + b·sin, H = a·sin + b·cos. Gần 45° (định thức ~0) thì không xoay được → trả nguyên."""
    t = math.radians(abs(angle))
    c, s = math.cos(t), math.sin(t)
    det = c * c - s * s
    if det < 0.35:  # > ~35° — giải không ổn định
        return w, h
    a = (w * c - h * s) / det
    b = (h * c - w * s) / det
    b = max(b, 0.12 * a, 24)  # đừng để khung quá mỏng vì sai số ô bao
    return max(24, round(a)), max(24, round(b))


def _draw_label(L: dict, renderer, W: int, H: int) -> tuple[Image.Image, int, int]:
    """Vẽ một ô chữ (mẫu brand nếu có, không thì Pillow), xoay theo góc chữ gốc. Trả (ảnh, x, y) để overlay."""
    min_px = round(H * 0.03)  # chữ Việt ≥ 3% chiều cao khung cho dễ đọc trên điện thoại
    angle = L["angle"]
    w, h = rotated_rect(L["w"], L["h"], angle) if angle else (L["w"], L["h"])
    max_w = round(W * 0.92) if not angle else round(w * 1.25)
    if renderer is not None and L.get("template"):
        img, w, h = renderer.render(L["template"], L["text"] or " ", w, h, sub=L["sub"], min_px=min_px,
                                    max_w=max(max_w, w), max_h=h * 3)
    else:
        st = L["style"]
        _, _, w, h = grow_to_min_font(L["text"], 0, 0, w, h, max(max_w, w), H, min_px)
        img = render_label(L["text"] or " ", w, h, bg=st.get("bg", "#FFFFFF"),
                           border=st.get("border", "#D7262E"), text_color=st.get("text", "#1A1A1A"))
    if angle:
        img = img.rotate(angle, expand=True, resample=Image.BICUBIC)  # PIL: dương = ngược chiều kim đồng hồ
    cx, cy = L["x"] + L["w"] / 2, L["y"] + L["h"] / 2
    ox, oy = round(cx - img.width / 2), round(cy - img.height / 2)
    if not angle:  # ô ngang nới rộng thì giữ trong khung
        ox = max(0, min(W - img.width, ox))
        oy = max(0, min(H - img.height, oy))
    return img, ox, oy


def validate(edl: dict, meta: dict, allow_empty: bool) -> list[dict]:
    """Trả danh sách lớp phủ cần vẽ (ô chữ + phụ đề), mỗi lớp {start,end,x,y,w,h,text,style}."""
    W, H, dur = meta["width"], meta["height"], meta["duration"]
    style = edl.get("style", {})
    layers, problems = [], []
    for o in edl.get("overlays", []):
        if o.get("skip") or o.get("mode") == "keep":  # keep = chữ trong cảnh, giữ nguyên
            continue
        x, y, w, h = (int(v) for v in o["box"])
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > W or y + h > H:
            problems.append(f"{o['id']}: ô {o['box']} ra ngoài khung {W}x{H}")
        if not (0 <= o["start"] < o["end"] <= dur + 0.05):
            problems.append(f"{o['id']}: khung giờ {o['start']}–{o['end']} sai (video {dur}s)")
        mode = o.get("mode", "label")
        text = (o.get("text_vi") or "").strip()
        if mode == "label" and not text and not allow_empty:
            problems.append(f"{o['id']}: chưa có text_vi (chữ gốc: {o.get('zh')}) — hoặc đặt mode=blur / skip")
        if mode not in ("label", "blur"):
            problems.append(f"{o['id']}: mode '{mode}' không hỗ trợ (label | blur | keep)")
        layers.append({"start": o["start"], "end": o["end"], "x": x, "y": y, "w": w, "h": h,
                       "text": text, "sub": (o.get("sub_vi") or "").strip(), "mode": mode,
                       "angle": float(o.get("angle") or 0.0), "template": o.get("template"),
                       "style": {**style, **o.get("style", {})}})
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
                       "text": text, "sub": "", "mode": "label", "angle": 0.0, "template": "caption",
                       "style": {**style, **edl.get("subtitle_style", {})}})
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
    W, H = meta["width"], meta["height"]
    shop = edl.get("shop") or ""
    needs = any(L.get("template") for L in layers if L["mode"] == "label")
    if needs and not shop:
        raise EdlError("edl.json có ô dùng `template` nhưng chưa khai `shop` (mã shop trong assets/shops/)")
    renderer = TemplateRenderer(shop).__enter__() if needs else None
    try:
        drawn = {id(L): _draw_label(L, renderer, W, H) for L in layers if L["mode"] == "label"}
    finally:
        if renderer is not None:
            renderer.__exit__(None, None, None)

    inputs = ["-i", str(job_dir / meta["source"])]
    chain, prev, n_png = [], "0:v", 0
    # blur vẽ trước (nằm dưới), ô chữ vẽ sau để luôn nổi trên cùng
    for i, L in enumerate(sorted(layers, key=lambda L: L["mode"] != "blur"), 1):
        out = f"v{i}"
        enable = f"enable='between(t,{L['start']:.3f},{L['end']:.3f})'"
        if L["mode"] == "blur":
            # bán kính ≤ nửa cạnh ngắn; kênh màu yuv420 chỉ bằng nửa kích thước → bán kính màu chia đôi
            bw, bh = L["w"] // 2 * 2, L["h"] // 2 * 2
            r = max(2, min(bw, bh) // 5)
            chain.append(f"[{prev}]split[s{i}a][s{i}b]")
            chain.append(f"[s{i}b]crop={bw}:{bh}:{L['x']}:{L['y']},"
                         f"boxblur=luma_radius={r}:luma_power=3:chroma_radius={max(1, r // 2)}:chroma_power=3[b{i}]")
            chain.append(f"[s{i}a][b{i}]overlay={L['x']}:{L['y']}:{enable}[{out}]")
        else:
            img, ox, oy = drawn[id(L)]
            n_png += 1
            png = labels_dir / f"l{n_png:03}.png"
            img.save(png)
            inputs += ["-i", str(png)]
            chain.append(f"[{prev}][{n_png}:v]overlay={ox}:{oy}:{enable}[{out}]")
        prev = out
    scale = ",scale=-2:960" if not final else ""
    chain.append(f"[{prev}]format=yuv420p{scale}[vout]")

    audio = edl.get("audio", {})
    mode = audio.get("mode", "keep")
    a_args: list[str]
    n_in = n_png + 1
    if mode == "keep" and meta["has_audio"]:
        a_args = ["-map", "0:a:0", "-c:a", "aac", "-b:a", "160k"]
    elif mode == "narration":
        # Thuyết minh liền mạch (narration.wav, 1 lượt đọc) + nhạc nền chuẩn hoá theo độ to cảm nhận (LUFS).
        # Bản 20/10 trước dùng sidechain ducking → nhạc bị nén gần như mất, Sếp nghe "chưa có nhạc".
        npath = job_dir / "narration.json"
        if not npath.exists():
            raise EdlError("audio.mode=narration nhưng chưa có narration.json — chạy `vs.py narrate <id>` trước")
        nrep = json.loads(npath.read_text(encoding="utf-8"))
        if any("tràn" in w for w in nrep.get("warnings", [])):
            raise EdlError("Thuyết minh tràn quá cuối video:\n  - " + "\n  - ".join(nrep["warnings"]))
        dur = meta["duration"]
        voice_lufs = audio.get("voice_lufs", -16)
        music_lufs = audio.get("music_lufs", -27)
        inputs += ["-i", str(job_dir / "narration.wav")]
        chain.append(f"[{n_in}:a]aresample=48000,loudnorm=I={voice_lufs}:TP=-2:LRA=11,apad,atrim=0:{dur:.3f}[vo]")
        music = Path(audio.get("music") or job_dir / "music.mp3")
        if not music.is_absolute():
            music = job_dir / music
        if music.exists():
            inputs += ["-stream_loop", "-1", "-i", str(music)]
            chain.append(f"[{n_in + 1}:a]atrim=0:{dur:.3f},aresample=48000,loudnorm=I={music_lufs}:TP=-8:LRA=11,"
                         f"afade=t=in:d=0.4,afade=t=out:st={max(0.0, dur - 1.8):.3f}:d=1.8[bg]")
            chain.append("[vo][bg]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[aout]")
        else:
            chain.append("[vo]alimiter=limit=0.95[aout]")
        a_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    elif mode == "voice":
        # giọng Việt (voice.json, đã qua kiểm ngược) + nhạc nền tự hạ khi có giọng, mờ dần cuối video
        vpath = job_dir / "voice.json"
        if not vpath.exists():
            raise EdlError("audio.mode=voice nhưng chưa có voice.json — chạy `vs.py voice <id>` trước")
        vrep = json.loads(vpath.read_text(encoding="utf-8"))
        if vrep.get("too_long"):
            raise EdlError("Có câu đọc quá dài so với khung:\n  - " + "\n  - ".join(vrep["too_long"]))
        dur = meta["duration"]
        k = n_in
        vo_labels = []
        for j, ln in enumerate(vrep["lines"]):
            inputs += ["-i", str(job_dir / "voice" / ln["file"])]
            ms = round(ln["start"] * 1000)
            tempo = f"atempo={ln['tempo']}," if ln["tempo"] > 1.0 else ""
            chain.append(f"[{k}:a]{tempo}adelay={ms}|{ms}[vo{j}]")
            vo_labels.append(f"[vo{j}]")
            k += 1
        chain.append(f"{''.join(vo_labels)}amix=inputs={len(vo_labels)}:normalize=0,apad[vomix]")
        music = Path(audio.get("music") or job_dir / "music.mp3")
        if not music.is_absolute():
            music = job_dir / music
        if music.exists():
            inputs += ["-stream_loop", "-1", "-i", str(music)]
            chain.append(f"[{k}:a]atrim=0:{dur:.3f},volume={audio.get('music_volume', 0.25)},"
                         f"afade=t=out:st={max(0.0, dur - 1.5):.3f}:d=1.5[bg]")
            chain.append("[vomix]asplit[vo_a][vo_b]")
            chain.append("[bg][vo_a]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=350[bgd]")
            chain.append("[bgd][vo_b]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[aout]")
        else:
            chain.append(f"[vomix]atrim=0:{dur:.3f},alimiter=limit=0.95[aout]")
        a_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
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
