# GDP Video Studio — cài đặt trên máy mới (hướng dẫn cho Claude Code)

> Đọc file này từ đầu đến cuối rồi TỰ CHẠY các lệnh (PowerShell). Chỉ hỏi người dùng khi cần: API key,
> quyền cài phần mềm, hoặc đường dẫn khác `C:\Users\Admin\gdp-video-studio`. Giao tiếp bằng tiếng Việt.
> Sau khi cài xong, quy trình làm video nằm ở skill `gdp-video-localize` + `CLAUDE.md` trong thư mục này.
> Bản sao file này + skill nằm trong repo giadungplus: `skills/gdp-video-localize/{SETUP.md,SKILL.md}`.

## 0. Cần chép những gì sang máy mới

| Chép | Không chép |
|---|---|
| Cả thư mục `gdp-video-studio\` (gồm `.git\`, `studio\`, `tools\`, `assets\` — font, logo, outro, mẫu chữ —, `vs.py`, `doctor.py`, `requirements.txt`, `CLAUDE.md`, `SETUP.md`) | `.venv\` (tạo lại — venv không chép được giữa máy) |
| | `jobs\*` (tuỳ — chỉ là kết quả từng video; ~40 MB/job) |
| | `.env` (chứa API key — chuyển riêng an toàn, hoặc dán key mới) |

Repo studio là git riêng, KHÔNG có remote → chép thư mục (có `.git`) là đủ lịch sử. Font thương mại trong
`assets\fonts\` (Averta, UTM Avo, UTM HelvetIns) — máy mới dùng nội bộ cùng công ty theo giấy phép đã mua.

## 1. Phần mềm cần có

| Phần mềm | Bản đã chạy ổn | Cài (PowerShell) | Ghi chú |
|---|---|---|---|
| Windows 10/11 64-bit | Windows 11 | — | macOS/Linux chưa thử (xem mục 8) |
| Python | 3.12.1 (≥3.11) | `winget install Python.Python.3.12` | tick "Add to PATH" |
| ffmpeg + ffprobe | 9.0.2 full_build (≥7) | `winget install Gyan.FFmpeg` | studio tự tìm trong `WinGet\Links`; khác thì đặt `FFMPEG_PATH`/`FFPROBE_PATH` trong `.env` |
| Google Chrome | bản ổn định | `winget install Google.Chrome` | renderer mẫu chữ HTML dùng Chrome ĐÃ CÀI qua Playwright (`channel="chrome"`), KHÔNG cần `playwright install` |
| Git | 2.4x | `winget install Git.Git` | |
| Claude Code (app/CLI) | — | claude.ai/download | điều phối + subagent |

Không cần GPU, không cần Node.js, không chạy model AI nặng trên máy (mọi AI qua API).

## 2. Cài đặt (Claude tự chạy, theo thứ tự)

```powershell
Set-Location C:\Users\Admin\gdp-video-studio          # đổi nếu thư mục ở chỗ khác
python --version                                      # ≥ 3.11
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }   # rồi NHỜ NGƯỜI DÙNG dán GEMINI_API_KEY vào .env
```

`requirements.txt` ghim: google-genai, Pillow, opencv-python-headless, python-dotenv, playwright, fonttools, psutil.

**Skill** (bắt buộc — quy trình làm video): chép `SKILL.md` từ repo giadungplus (`skills/gdp-video-localize/SKILL.md`,
lấy bằng `git show origin/main:skills/gdp-video-localize/SKILL.md`) hoặc từ máy cũ vào
`%USERPROFILE%\.claude\skills\gdp-video-localize\SKILL.md`, rồi khởi động lại Claude Code.

**Nếu thư mục KHÔNG nằm ở `C:\Users\Admin\gdp-video-studio`**: code dùng đường dẫn tương đối (không phải sửa), nhưng
phải thay đường dẫn tuyệt đối trong `SKILL.md` và `CLAUDE.md`:
`Select-String -Path $env:USERPROFILE\.claude\skills\gdp-video-localize\SKILL.md, .\CLAUDE.md -Pattern 'Admin\\gdp-video-studio'`.

## 3. Kiểm tra sau cài (phải xanh hết mới làm video)

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe doctor.py                  # 15 mục, 0 lỗi (mục Gemini cần key)
.\.venv\Scripts\python.exe tools\test_font_gate.py    # phải in "CHẶN ĐÚNG" (Chrome + cổng font hoạt động)
.\.venv\Scripts\python.exe tools\check_font_vi.py     # mọi font "ĐỦ tiếng Việt"
.\.venv\Scripts\python.exe vs.py shops                # 5 shop Shopee có mẫu + logo; GDP/LTENG có outro
.\.venv\Scripts\python.exe vs.py templates giadungplus_official   # mở ảnh _preview.png soát mắt
```

Kiểm model Gemini mà key dùng được (tên model đổi theo thời gian — đúng tên thì sửa `.env`/code):

```powershell
@'
from studio import gemini
names = [m.name for m in gemini.client().models.list()]
for need in ("gemini-3-flash-preview", "gemini-3.1-flash-tts-preview", "lyria-3.5"):
    print(need, "OK" if any(need in n for n in names) else "KHÔNG CÓ")
'@ | .\.venv\Scripts\python.exe -
```

- `GEMINI_MODEL` (phân tích/QA/nghe lại) trong `.env` · TTS `studio/voice.py: TTS_MODEL` · nhạc `MUSIC_MODEL`.

Chạy thử đầu-cuối không tốn video thật (video mẫu có sự thật biết trước):

```powershell
.\.venv\Scripts\python.exe tools\make_sample.py
.\.venv\Scripts\python.exe vs.py new inbox\sample_synthetic.mp4 --id synth-test
.\.venv\Scripts\python.exe vs.py analyze synth-test    # 3 ô chữ; ô chữ chạy có nhãn (chạy)
```

## 4. Tuỳ chọn

- **Bridge MCP `gdp-bridge`** (đọc DB prod: brand kit, dữ liệu SKU để kiểm tuyên bố sản phẩm) — không bắt buộc để render.
  Cấu hình giống máy cũ (token trong cấu hình MCP của Claude Code, không nằm trong repo này).
- Nghe thử giọng từng shop: `tools\voice_samples.py` → `jobs\_voices\`.

## 5. Cấu hình máy để chạy ỔN ĐỊNH 3 subagent / 3 video cùng lúc

### Số đo thật (20/10/2026, máy gốc Ryzen 9 7945HX 16 nhân/32 luồng, 31,7 GB RAM, video 720×960 · 47s)

| Thao tác, 3 job song song | Thời gian | RAM đỉnh (tiến trình studio) | CPU |
|---|---|---|---|
| `render --final` (Chrome vẽ ô chữ + ffmpeg x264 medium) | 13,6s | 2,16 GB | đỉnh 99% vài giây, TB 28% |
| `render` preview | 11,0s | 2,13 GB | TB 5% |
| `qa --final` (285 khung, 12 lượt gọi Gemini cùng lúc) | 39,1s | 1,51 GB | TB 10% |
| 1 job `render` preview | 8,5s | 0,71 GB | — |

Đo lại trên máy mới: `.\.venv\Scripts\python.exe tools\bench_parallel.py "render --final" <job1> <job2> <job3>`.
Phần nặng máy duy nhất là render (vài chục giây); analyze/narrate/qa chủ yếu CHỜ API.
Video nguồn 1080×1920 dài ~60s ≈ 4 lần khối lượng mã hoá so với số đo trên.

### Cấu hình khuyến nghị

| | Tối thiểu (3 song song) | Khuyến nghị |
|---|---|---|
| CPU | 8 nhân / 16 luồng (Ryzen 7 5000+, Core i7 gen 12+) | 12–16 nhân (Ryzen 9 / Core i9) |
| RAM | 16 GB | 32 GB |
| Ổ đĩa | SSD, trống ≥ 30 GB | NVMe, trống ≥ 100 GB (nguồn 1080p + nhiều job) |
| GPU | không cần | không cần |
| Mạng | ≥ 30 Mbps, ổn định (upload khung hình/âm thanh lên Gemini) | ≥ 100 Mbps cáp |
| Hệ điều hành | Windows 10/11 64-bit | Windows 11, chế độ nguồn "Best performance", tắt ngủ khi cắm điện |

Ước lượng RAM: ~1 GB cho mỗi job đang render (Chrome ẩn + ffmpeg + Python) + Claude Code ~0,5–1 GB + hệ điều hành.

### Hạn mức dịch vụ (thường là nút cổ chai thật, không phải máy)

- **Gemini API key ở hạng trả phí** (Tier 1 trở lên). Mỗi job gọi tới 4 yêu cầu cùng lúc (lô 10 khung) → 3 job ≈ 12 yêu
  cầu đồng thời; key miễn phí sẽ bị 429 (code có thử lại 3 lần nhưng sẽ chậm/hỏng). Máy gốc chạy 12 đồng thời không lỗi.
  Chi phí ước tính mỗi video 47s: ~0,2M token phân tích+QA + 1 lượt TTS + 1 đoạn nhạc Lyria.
- **Claude**: mỗi subagent Sonnet ~150k token/video (đo 20/10: 5–9 phút/bản) + điều phối (Opus) chấm lại → 3 video
  ≈ 0,5–0,7M token/lượt; nên dùng gói Claude có hạn mức cao (Max).
- Chạy song song an toàn: mỗi job một thư mục riêng; file tạm render đặt tên theo tiến trình (không giẫm nhau).
  KHÔNG cho 2 subagent làm cùng một job id.

## 6. Lỗi thường gặp

| Triệu chứng | Nguyên nhân / cách chữa |
|---|---|
| `doctor`: ffmpeg không tìm thấy | `winget install Gyan.FFmpeg`, mở lại terminal; hoặc `FFMPEG_PATH`/`FFPROBE_PATH` trong `.env` |
| Playwright: `Chromium distribution 'chrome' is not found` | chưa cài Google Chrome (cài Chrome, đừng đổi code sang chromium tải về) |
| `không tải được font` | đường dẫn `url(...)` trong mẫu sai so với `assets\fonts\<Họ font>\` (cổng font chặn có chủ đích) |
| Gemini 429 / quota | key miễn phí hoặc vượt hạn mức → nâng hạng, hoặc chạy ít job song song hơn |
| Gemini 503 UNAVAILABLE | Google quá tải nhất thời (gặp khi kiểm SETUP 20/10) → chờ vài giây chạy lại; code/doctor có thử lại |
| Gemini 404 model | tên model đã đổi → kiểm `models.list()` (mục 3), sửa `.env` / `TTS_MODEL` / `MUSIC_MODEL` |
| Chữ tiếng Việt lỗi khi in log | thiếu `$env:PYTHONIOENCODING='utf-8'` |
| Claude Code chặn `Remove-Item`/`git rm` ("system path") | bộ kiểm lệnh hiểu nhầm đường dẫn → xoá bằng Python `Path(...).unlink()` rồi `git add -A` |
| `[IO.File]` báo không thấy file dù có | PowerShell .NET hiểu đường dẫn tương đối theo thư mục khởi động → dùng đường dẫn tuyệt đối / `Resolve-Path` |

## 7. Sau khi cài — làm video

Dùng skill `gdp-video-localize` (quy trình, luật chữ/thuyết minh/giọng theo shop, 1 video nhiều shop, giao subagent).
Tài nguyên shop: `assets\shops\README.md`. Lệnh nhanh: `CLAUDE.md`.

## 8. macOS / Linux (chưa kiểm chứng)

Code Python chạy được đa nền tảng (đường dẫn tương đối, ffmpeg qua PATH). Cần: `brew install ffmpeg` / `apt install ffmpeg`,
Google Chrome, đổi lệnh PowerShell sang bash (`.venv/bin/python`). Mẫu font dùng đường dẫn tương đối — giữ nguyên tên thư
mục font (có dấu cách: `UTM Avo`, `UTM HelvetIns`). Chạy đủ mục 3 trước khi tin.
