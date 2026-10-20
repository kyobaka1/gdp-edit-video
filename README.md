# GDP Video Studio

Việt hoá video sản phẩm tiếng Trung cho LTENG / PHALEDO / GIADUNGPLUS, chạy local Windows,
Claude Code điều khiển. Plan + trạng thái: repo giadungplus
`docs/plans/2026-10-20-gdp-video-studio-viet-hoa-video.md`.

## Cài đặt (đã làm ở P0)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env   # rồi dán GEMINI_API_KEY vào .env
.\.venv\Scripts\python.exe doctor.py
```

ffmpeg: `winget install Gyan.FFmpeg` (studio tự tìm trong `WinGet\Links` nếu PATH chưa nạp).

## Thư mục

- `inbox/` — thả video nguồn vào đây (không commit).
- `jobs/<job_id>/` — mọi thứ của một video: analysis, edl.json, ô chữ PNG, preview, final, qa (không commit).
- `assets/fonts/` — Be Vietnam Pro (SIL OFL, xem `OFL.txt`).
- `assets/brands/` — logo/màu từng brand (P2).
- `studio/` — code pipeline (`config.py`, `overlay.py`, …).

## Luật

- Chữ Trung trong hình được CHE KÍN bằng ô chữ Việt có nền + viền, không xoá bằng AI.
- Không chạy model nặng local; phân tích bằng Gemini API (key riêng trong `.env`).
- Không thêm tuyên bố sản phẩm không có trong dữ liệu SKU thật.
