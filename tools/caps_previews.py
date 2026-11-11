"""Ảnh DEMO bộ nhận diện Việt hoá V2 (chữ động + badge + khung dải) — KHÔNG render video (Sếp 11/11: "chỉ cần demo lên
ảnh, không cần video render phiền phức").

    python tools/caps_previews.py <job> [<job> …] [--at 3.2,4.9,6.9] [--out file.jpg] [--width 432]

Mỗi job một hàng: khung nguồn đã xoá chữ Trung (`source-clean.mp4`, tự dựng / dùng cache) + lớp chữ Việt (`caps.mov`, dựng
lại mỗi lần chạy, ~15s) ghép tại các mốc `--at`. Không có logo / watermark / animation thương hiệu / tiếng — chỉ để soát
màu, phông, badge, khung dải của shop. Sửa `assets/shops/<shop>/shop.json` mục `caps` rồi chạy lại là thấy.
Job cần có edl.json (chạy direct.py) và narration.json nếu `caps.items` dùng mốc "pN".
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studio import clean, config, vcaps  # noqa: E402


def frames(job: str, ts: list[float], width: int) -> list[np.ndarray]:
    d = ROOT / "jobs" / job
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    edl = json.loads((d / "edl.json").read_text(encoding="utf-8"))
    src = clean.build(d, edl, meta) or d / meta["source"]
    vc = vcaps.build(d, edl, meta, src, clean.report(d))
    W, H = meta["width"], meta["height"]
    cap = cv2.VideoCapture(str(src))
    out = []
    for t in ts:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        if vc:
            raw = subprocess.run([config.FFMPEG, "-v", "error", "-ss", f"{t:.3f}", "-i", str(vc["mov"]), "-frames:v", "1",
                                  "-f", "rawvideo", "-pix_fmt", "bgra", "-"], capture_output=True).stdout
            if len(raw) == W * H * 4:
                ov = np.frombuffer(raw, np.uint8).reshape(H, W, 4).astype(np.float32) / 255
                f = (ov[..., :3] * 255 * ov[..., 3:] + f * (1 - ov[..., 3:])).astype(np.uint8)
        out.append(cv2.resize(f, (width, round(width * H / W)), interpolation=cv2.INTER_AREA))
    cap.release()
    return out


def main() -> None:
    args = sys.argv[1:]
    opt = {"--at": "3.2,4.9,6.9,12.6,23.4", "--out": "", "--width": "432"}
    jobs = []
    while args:
        a = args.pop(0)
        if a in opt:
            opt[a] = args.pop(0)
        else:
            jobs.append(a)
    if not jobs:
        sys.exit(__doc__)
    ts = [float(x) for x in opt["--at"].split(",")]
    rows = []
    for job in jobs:
        tiles = frames(job, ts, int(opt["--width"]))
        row = np.hstack(tiles)
        bar = np.full((34, row.shape[1], 3), 24, np.uint8)
        edl = json.loads((ROOT / "jobs" / job / "edl.json").read_text(encoding="utf-8"))
        cv2.putText(bar, f"{edl.get('shop', job)}", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (235, 235, 235), 2, cv2.LINE_AA)
        rows += [bar, row]
    out = Path(opt["--out"]) if opt["--out"] else ROOT / "jobs" / jobs[0] / "caps_preview.jpg"
    cv2.imwrite(str(out), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"→ {out}")


if __name__ == "__main__":
    main()
