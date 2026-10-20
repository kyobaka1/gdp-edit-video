"""Thao tác ffmpeg/ffprobe: đọc thông tin video, cắt khung, tách audio."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from studio import config


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"Lệnh lỗi ({proc.returncode}): {' '.join(cmd[:6])} …\n{proc.stderr[-800:]}")
    return proc


def probe(video: Path) -> dict:
    out = run([config.FFPROBE, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(video)])
    info = json.loads(out.stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    num, den = (int(x) for x in v.get("avg_frame_rate", "30/1").split("/"))
    rotation = 0
    for sd in v.get("side_data_list", []) or []:
        rotation = int(sd.get("rotation", 0) or 0)
    w, h = int(v["width"]), int(v["height"])
    if abs(rotation) in (90, 270):
        w, h = h, w
    return {
        "width": w,
        "height": h,
        "fps": round(num / den, 3) if den else 30.0,
        "duration": round(float(info["format"]["duration"]), 3),
        "has_audio": any(s["codec_type"] == "audio" for s in info["streams"]),
    }


def extract_frame(video: Path, t: float, out: Path, width: int | None = None) -> Path:
    vf = ["-vf", f"scale={width}:-2"] if width else []
    run([config.FFMPEG, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
         *vf, "-q:v", "3", str(out)])
    return out


def extract_frames(video: Path, times: list[float], out_dir: Path, width: int | None = None,
                   prefix: str = "f") -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{prefix}_{t:08.3f}.jpg" for t in times]
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda tp: extract_frame(video, tp[0], tp[1], width), zip(times, paths)))
    return paths


def extract_audio(video: Path, out: Path) -> Path:
    run([config.FFMPEG, "-y", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "libmp3lame", "-b:a", "48k", str(out)])
    return out
