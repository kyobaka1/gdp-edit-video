"""Kiểm môi trường GDP Video Studio. Chạy: .venv\\Scripts\\python.exe doctor.py

In OK / LỖI / CHỜ cho từng mục, thoát mã 1 nếu có LỖI. Không bao giờ in API key.
"""

import subprocess
import sys

from studio import config

results: list[tuple[str, str, str]] = []


def check(name: str, status: str, detail: str = "") -> None:
    results.append((status, name, detail))


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


# 1. Python + thư viện
check("Python >= 3.11", "OK" if sys.version_info >= (3, 11) else "LỖI", sys.version.split()[0])
for mod in ("google.genai", "PIL", "cv2", "dotenv"):
    try:
        __import__(mod)
        check(f"thư viện {mod}", "OK")
    except ImportError as exc:
        check(f"thư viện {mod}", "LỖI", str(exc))

# 2. ffmpeg / ffprobe + filter cần dùng
for label, path in (("ffmpeg", config.FFMPEG), ("ffprobe", config.FFPROBE)):
    if not path:
        check(label, "LỖI", "không tìm thấy (winget install Gyan.FFmpeg)")
        continue
    first = run([path, "-hide_banner", "-version"]).stdout.splitlines()[:1]
    check(label, "OK", first[0] if first else path)
if config.FFMPEG:
    filters = run([config.FFMPEG, "-hide_banner", "-filters"]).stdout
    for f in ("overlay", "scale", "amix"):
        check(f"ffmpeg filter {f}", "OK" if f" {f} " in filters else "LỖI")

# 3. Font tiếng Việt
for font in (config.FONT_REGULAR, config.FONT_BOLD, config.FONT_EXTRABOLD):
    check(f"font {font.name}", "OK" if font.exists() else "LỖI")

# 4. Ghép thử: video mẫu 2s + ô chữ Việt che từ 0,5s đến 1,5s → pixel giữa ô phải là màu nền
if config.FFMPEG and config.FONT_BOLD.exists():
    import cv2

    from studio.overlay import render_label

    work = config.JOBS / "_doctor"
    work.mkdir(parents=True, exist_ok=True)
    src, png, out = work / "src.mp4", work / "label.png", work / "out.mp4"
    label = render_label("Thủy tinh chịu nhiệt — đóng mở 1 chạm", 600, 140, bg="#FFD400")
    label.save(png)
    run([config.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=2",
         "-pix_fmt", "yuv420p", str(src)])
    proc = run([config.FFMPEG, "-y", "-v", "error", "-i", str(src), "-i", str(png), "-filter_complex",
                "[0:v][1:v]overlay=240:900:enable='between(t,0.5,1.5)'", "-pix_fmt", "yuv420p", str(out)])
    if proc.returncode != 0:
        check("ghép thử ô chữ", "LỖI", proc.stderr.strip()[-300:])
    else:
        cap = cv2.VideoCapture(str(out))
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
        ok, frame = cap.read()
        cap.release()
        # điểm (x=270, y=970): trong ô, mép trái, chắc chắn không dính chữ
        b, g, r = (int(v) for v in frame[970, 270]) if ok else (0, 0, 0)
        covered = ok and r > 200 and g > 180 and b < 80
        check("ghép thử ô chữ (che kín)", "OK" if covered else "LỖI",
              f"pixel BGR=({b},{g},{r}) · xem {out}")
        if ok:
            cv2.imwrite(str(work / "frame_1s.jpg"), frame)

# 5. Gemini
if not config.GEMINI_API_KEY:
    check("Gemini API key", "CHỜ", "chưa có GEMINI_API_KEY trong .env (Sếp tự dán)")
else:
    import time

    from google import genai

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    last = None
    for attempt in range(3):  # 503 UNAVAILABLE của Google là nhất thời (gặp khi kiểm SETUP 20/10) → thử lại
        try:
            resp = client.models.generate_content(model=config.GEMINI_MODEL, contents="Trả lời đúng một chữ: OK")
            text = (resp.text or "").strip()
            check(f"Gemini ({config.GEMINI_MODEL})", "OK" if text else "LỖI", f"trả về: {text[:40]!r}")
            break
        except Exception as exc:  # báo lỗi mạng/quyền/model sai, không lộ key
            last = exc
            time.sleep(3 * (attempt + 1))
    else:
        check(f"Gemini ({config.GEMINI_MODEL})", "LỖI", f"{type(last).__name__}: {str(last)[:200]}")

width = max(len(n) for _, n, _ in results)
for status, name, detail in results:
    print(f"[{status:^4}] {name:<{width}}  {detail}")
failed = [n for s, n, _ in results if s == "LỖI"]
waiting = [n for s, n, _ in results if s == "CHỜ"]
print(f"\nTổng: {len(results)} mục · {len(failed)} lỗi · {len(waiting)} chờ")
sys.exit(1 if failed else 0)
