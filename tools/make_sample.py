"""Sinh video mẫu 1080x1920 có chữ Trung ở vị trí/thời điểm BIẾT TRƯỚC để kiểm pipeline bằng số.

Ghi `inbox/sample_synthetic.mp4` + `inbox/sample_synthetic.truth.json` (sự thật: chữ, khung giờ, ô pixel).
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config  # noqa: E402

FONT = "C\\:/Windows/Fonts/msyhbd.ttc"  # Microsoft YaHei Bold, có sẵn trên Windows
OUT = config.INBOX / "sample_synthetic.mp4"

# (chữ, start, end, x, y, cỡ, di chuyển?)
TRUTH = [
    {"text": "高硼硅玻璃", "start": 1.0, "end": 4.0, "x": 140, "y": 260, "size": 110, "moving": False},
    {"text": "一键开合 防滴漏设计", "start": 2.5, "end": 6.0, "x": 120, "y": 1560, "size": 80, "moving": False},
    {"text": "限时特价", "start": 4.5, "end": 7.5, "x": 100, "y": 900, "size": 90, "moving": True},
]


def main() -> None:
    draws = []
    for t in TRUTH:
        x = f"{t['x']}+(t-{t['start']})*60" if t["moving"] else str(t["x"])
        draws.append(
            f"drawtext=fontfile='{FONT}':text='{t['text']}':fontsize={t['size']}:fontcolor=white:"
            f"box=1:boxcolor=red@0.85:boxborderw=18:x={x}:y={t['y']}:"
            f"enable='between(t,{t['start']},{t['end']})'"
        )
    vf = ",".join(["format=yuv420p"] + draws)
    cmd = [
        config.FFMPEG, "-y", "-v", "error",
        "-f", "lavfi", "-i", "gradients=size=1080x1920:rate=30:duration=8:speed=0.02",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=8",
        "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(OUT),
    ]
    subprocess.run(cmd, check=True)
    OUT.with_suffix(".truth.json").write_text(
        json.dumps(TRUTH, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(OUT)


if __name__ == "__main__":
    main()
