"""Thao tác ffmpeg/ffprobe: đọc thông tin video, cắt khung, tách audio."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from studio import config


RUN_TIMEOUT = 1800.0   # giây — một ffmpeg treo không được treo cả job (hết hạn: tiến trình con bị dừng, báo lỗi rõ)

# Bộ ghi nhận khung RGB (rawvideo bgr24) → x264: ffmpeg mặc định đổi sang YUV bằng ma trận BT.601 và không gắn tag,
# trình phát HD lại giải theo BT.709 → màu rực (logo, chữ màu shop) lệch (đo 10/11: 6,0 → 1,6 mức sau khi gắn).
# Gắn bằng x264-params (đủ cả 3 tag); cờ -colorspace chỉ ghi được ma trận. Lưu ý: OpenCV đọc lại bỏ qua tag (ảnh soát
# QA lệch màu nhẹ) — sản phẩm giao thì đúng.
BT709_OUT = ["-vf", "scale=out_color_matrix=bt709:out_range=tv",
             "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709"]

# Nguồn HDR (iPhone mặc định quay HLG; PQ = HDR10/Dolby Vision): đọc thẳng ra khung 8-bit thì hình tối + bệt màu
# (đo 10/11 trên clip HLG thử: sáng 115 → 76, bão hoà 111 → 87). Chuỗi dưới đưa về SDR BT.709; `mobius` giữ nguyên
# vùng sáng thường, chỉ nén mềm phần chói (hable làm tối cả khung). Chưa thử trên clip iPhone thật — gặp thì soát mắt.
HDR_TRANSFERS = {"arib-std-b67", "smpte2084"}
TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def run(cmd: list[str], timeout: float | None = RUN_TIMEOUT) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Lệnh chạy quá {timeout:.0f}s, đã dừng: {' '.join(cmd[:6])} …") from None
    if proc.returncode != 0:
        raise RuntimeError(f"Lệnh lỗi ({proc.returncode}): {' '.join(cmd[:6])} …\n{proc.stderr[-800:]}")
    return proc


@lru_cache(maxsize=512)
def _transfer(path: str, mtime: float) -> str:
    try:
        out = subprocess.run([config.FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=color_transfer", "-of", "csv=p=0", path], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.strip().split("\n")[0].strip().strip(",")


def is_hdr(video: Path) -> bool:
    p = Path(video)
    return p.exists() and _transfer(str(p), p.stat().st_mtime) in HDR_TRANSFERS


def sdr_filter(video: Path) -> str:
    """Chuỗi lọc đưa nguồn HDR về SDR (nối vào -vf); nguồn SDR / ảnh / file tiếng → ''."""
    return TONEMAP if is_hdr(video) else ""


def probe(video: Path) -> dict:
    out = run([config.FFPROBE, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(video)])
    info = json.loads(out.stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    num, den = (int(x) for x in v.get("avg_frame_rate", "30/1").split("/"))
    # chỉ mục side data CÓ khoá rotation (Display Matrix); mục khác đứng sau (Dolby Vision, …) không được ghi đè về 0
    rotation = next((int(sd["rotation"] or 0) for sd in v.get("side_data_list") or [] if "rotation" in sd), 0)
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
    # duration lấy từ container; luồng tiếng dài hơn luồng hình (vd hình 17,000s / file 17,02s) thì mốc cuối
    # rơi sau khung hình cuối → ffmpeg không ra ảnh. Lùi dần tối đa ~0,3s.
    for back in (0.0, 0.05, 0.1, 0.2, 0.3):
        try:
            run([config.FFMPEG, "-y", "-v", "error", "-ss", f"{max(0.0, t - back):.3f}", "-i", str(video),
                 "-frames:v", "1", *vf, "-q:v", "3", str(out)])
            return out
        except RuntimeError:
            if back == 0.3:
                raise
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
