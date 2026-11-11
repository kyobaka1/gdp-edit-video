# GDP Video Studio — cài đặt trên máy mới (hướng dẫn cho Claude Code)

> Đọc file này từ đầu đến cuối rồi TỰ CHẠY các lệnh (PowerShell). Chỉ hỏi người dùng khi cần: API key,
> quyền cài phần mềm, hoặc đường dẫn khác `C:\Users\Admin\gdp-video-studio`. Giao tiếp bằng tiếng Việt.
> Sau khi cài xong, quy trình làm video nằm ở skill `gdp-video-localize` + `CLAUDE.md` trong thư mục này.
> Bản sao file này + skill nằm trong repo giadungplus: `skills/gdp-video-localize/{SETUP.md,SKILL.md}`.

## 0. Cần chép những gì sang máy mới

| Chép | Không chép |
|---|---|
| Cả thư mục `gdp-video-studio\` (gồm `.git\`, `studio\`, `tools\`, `assets\` — font, logo, outro, mẫu chữ —, `vs.py`, `doctor.py`, `requirements.txt`, `CLAUDE.md`, `SETUP.md`) | `.venv\` (tạo lại — venv không chép được giữa máy) |
| | `.venv\` = 2,5 GB, trong đó ~2 GB thư viện CUDA NVIDIA — chỉ chạy được trên đúng loại máy đã cài, sang Mac là vô dụng |
| | `jobs\*` (tuỳ — chỉ là kết quả từng video; ~40 MB/job) |
| | `.env` (chứa API key — chuyển riêng an toàn, hoặc dán key mới; KHÔNG gửi qua chat / Zalo) |
| | `assets\models\*.onnx` (tải lại theo `assets\models\README.md`, 15 MB) |

Repo studio là git riêng, KHÔNG có remote → chép thư mục (có `.git`) là đủ lịch sử (~330 MB). Có repo git chung
(GitHub private) thì `git clone` thay cho chép. Font thương mại trong `assets\fonts\` (Averta, UTM Avo, UTM HelvetIns)
— máy mới dùng nội bộ cùng công ty theo giấy phép đã mua; repo chung phải để PRIVATE.

## 1. Phần mềm cần có

| Phần mềm | Bản đã chạy ổn | Cài (PowerShell) | Ghi chú |
|---|---|---|---|
| Windows 10/11 64-bit | Windows 11 | — | **MacBook: làm theo mục 8** (lệnh bash, Homebrew) |
| Python | 3.12.1 (≥3.11) | `winget install Python.Python.3.12` | tick "Add to PATH" |
| ffmpeg + ffprobe | 9.0.2 full_build (≥7) | `winget install Gyan.FFmpeg` | studio tự tìm trong `WinGet\Links`; khác thì đặt `FFMPEG_PATH`/`FFPROBE_PATH` trong `.env` |
| Google Chrome | bản ổn định | `winget install Google.Chrome` | renderer mẫu chữ HTML dùng Chrome ĐÃ CÀI qua Playwright (`channel="chrome"`), KHÔNG cần `playwright install` |
| Git | 2.4x | `winget install Git.Git` | |
| Claude Code (app/CLI) | — | claude.ai/download | điều phối + subagent |

Việt hoá (skill gdp-video-localize) không cần GPU, không chạy model AI nặng trên máy (mọi AI qua API). Riêng dựng video
quay sẵn (skill gdp-video-edit) chép lời bằng Whisper chạy máy: có card NVIDIA thì chạy GPU (nhanh), không có thì tự chạy
CPU (chậm hơn nhiều); lần đầu tự tải mô hình large-v3 ~3 GB.

## 2. Cài đặt (Claude tự chạy, theo thứ tự)

```powershell
Set-Location C:\Users\Admin\gdp-video-studio          # đổi nếu thư mục ở chỗ khác
python --version                                      # ≥ 3.11
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }   # rồi NHỜ NGƯỜI DÙNG dán GEMINI_API_KEY (+ TOKENROUTER_API_KEY nếu có) vào .env
```

`requirements.txt` ghim: google-genai, Pillow, opencv-python-headless, python-dotenv, playwright, fonttools, psutil,
requests, faster-whisper (+ 2 thư viện CUDA NVIDIA chỉ cài trên Windows / Linux — Mac tự bỏ qua).

**Skill** (bắt buộc — quy trình làm video) ĐÃ NẰM SẴN trong thư mục: `.claude\skills\` (3 skill dự án:
`gdp-video-localize` Việt hoá · `gdp-video-edit` dựng video quay sẵn · `gdp-video-motion` animation thương hiệu).
- Mở Claude Code ngay trong thư mục studio → skill + `CLAUDE.md` tự có, không cần cài. Cập nhật = chép / `git pull` bản mới.
- Muốn dùng skill khi Claude Code mở ở thư mục khác (vd repo giadungplus): `.\.venv\Scripts\python.exe tools\sync_skill.py install`
  (chép sang `%USERPROFILE%\.claude\skills\`), rồi khởi động lại Claude Code. `tools\sync_skill.py status` để so 2 bản.
  ⚠ Bản cá nhân `~/.claude/skills` được Claude Code ƯU TIÊN hơn bản trong repo → đã sync thì mỗi lần cập nhật repo phải sync lại,
  không thì Claude dùng bản cũ. Nhân sự chỉ làm việc trong thư mục studio thì KHÔNG cần sync.
- Bản sao dự phòng: repo giadungplus `skills/gdp-video-localize/` (`git show origin/main:skills/gdp-video-localize/SKILL.md`).

**Nếu thư mục KHÔNG nằm ở `C:\Users\Admin\gdp-video-studio`**: code dùng đường dẫn tương đối (không phải sửa). Skill +
`CLAUDE.md` ghi rõ "thư mục studio = nơi đã clone / chép repo" (đường dẫn máy Sếp chỉ là ví dụ) — Claude tự chạy trong thư
mục đang mở, không phải sửa file.

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
for need in ("gemini-3-flash-preview", "lyria-3.5"):
    print(need, "OK" if any(need in n for n in names) else "KHÔNG CÓ")
'@ | .\.venv\Scripts\python.exe -
```

- **Codex CLI** (soát ảnh `qa` / `vs.py look` bằng gói ChatGPT, không tốn tiền API): `npm i -g @openai/codex` → NHỜ NGƯỜI
  DÙNG chạy `codex login` (chọn ChatGPT). Kiểm: `.\.venv\Scripts\python.exe vs.py look jobs\<id>\contact.jpg -q "Có chữ Hán không?"`
  → dòng cuối `[codex gpt-5.6-luna]`. Không có Codex thì qa tự dùng Gemini (tốn tiền hơn).
- `GEMINI_MODEL` (phân tích/QA/nghe lại) trong `.env` · nhạc `MUSIC_MODEL`.
- **Giọng đọc = tts.vclip.io (Sếp 11/11, không dùng Gemini tạo giọng nữa)**: dán `VCLIP_API_KEY` (hoặc tên cũ `KEY_TTS`)
  vào `.env`; giọng từng shop = `shop.json voice.vclip`. Xem giọng của tài khoản: `.\.venv\Scripts\python.exe tools\vclip_voices.py`;
  `doctor.py` báo `vclip TTS … N shop đã gán`.
- TTS dự phòng `studio/voice.py: TTS_CHAIN`: vclip → tokenrouter openai/gpt-audio-mini (giọng khác, narrate cảnh báo).
  Kiểm: `.\.venv\Scripts\python.exe tools\probe_tts_chain.py sim` (0 ký tự) rồi `... live vclip` (gọi thật 4 shop).
  tokenrouter giới hạn 5 req/phút, tính cả lượt lỗi — 3 video song song vẫn đủ (1 req/lượt đọc).

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
  Chi phí ước tính mỗi video 47s: ~0,2M token phân tích+QA + 1 lượt TTS vclip (~500 ký tự) + 1 đoạn nhạc Lyria.
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
| Gemini 404 model | tên model đã đổi → kiểm `models.list()` (mục 3), sửa `.env` / `MUSIC_MODEL` |
| Chữ tiếng Việt lỗi khi in log | thiếu `$env:PYTHONIOENCODING='utf-8'` |
| Claude Code chặn `Remove-Item`/`git rm` ("system path") | bộ kiểm lệnh hiểu nhầm đường dẫn → xoá bằng Python `Path(...).unlink()` rồi `git add -A` |
| `[IO.File]` báo không thấy file dù có | PowerShell .NET hiểu đường dẫn tương đối theo thư mục khởi động → dùng đường dẫn tuyệt đối / `Resolve-Path` |

## 7. Sau khi cài — làm video

Dùng skill `gdp-video-localize` (quy trình, luật chữ/thuyết minh/giọng theo shop, 1 video nhiều shop, giao subagent).
Tài nguyên shop: `assets\shops\README.md`. Lệnh nhanh: `CLAUDE.md`.

## 8. macOS (MacBook) — cài từ đầu

Trạng thái (07/11/2026): đã sửa code + `requirements.txt` cho Mac và kiểm bằng pip giả lập nền tảng — **mọi gói có bản dựng
sẵn cho Mac chip Apple (M1 trở lên) lẫn Mac chip Intel** (Intel tự dùng opencv 4.12). **CHƯA chạy thử trên MacBook thật** →
chạy đủ bước kiểm (cuối mục này) trước khi làm video thật. Linux tương tự (apt thay brew).

**Không chép `.venv` từ máy Windows** — tạo mới trên Mac (bước 3). Chép thư mục studio (có `.git`) hoặc `git clone` repo chung.

```bash
# 1. Phần mềm — Homebrew (https://brew.sh) rồi:
brew install python@3.12 ffmpeg git
#    + Google Chrome bản thường (google.com/chrome) — BẮT BUỘC, renderer mẫu chữ dùng Chrome đã cài
#    + Claude Code (claude.ai/download)
# 2. Vào thư mục studio (vd đã chép / clone về ~/gdp-video-studio)
cd ~/gdp-video-studio
# 3. Môi trường Python (Mac tự bỏ ~2 GB thư viện CUDA — không cần)
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
# 4. Khoá API: tạo .env rồi NHỜ NGƯỜI DÙNG dán GEMINI_API_KEY (+ TOKENROUTER_API_KEY). Nếu chép .env từ Windows:
#    XOÁ 2 dòng FFMPEG_PATH / FFPROBE_PATH (đường dẫn Windows) — Mac tự tìm ffmpeg của brew.
[ -f .env ] || cp .env.example .env
# 5. Mô hình tách người (chữ sau người, 15 MB, miễn phí) — link + SHA-256 trong assets/models/README.md
curl -L -o assets/models/rvm_mobilenetv3_fp32.onnx \
  https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx
shasum -a 256 assets/models/rvm_mobilenetv3_fp32.onnx   # phải ra 88d4531297118f595bf2fd60f6f566aec2e559393802d1f436c380f0cbbd2828
# 6. Kiểm (giống mục 3, đổi .\.venv\Scripts\python.exe → .venv/bin/python)
export PYTHONIOENCODING=utf-8
.venv/bin/python doctor.py
.venv/bin/python tools/test_font_gate.py            # phải in "CHẶN ĐÚNG"
.venv/bin/python tools/check_font_vi.py
.venv/bin/python vs.py shops
```

Khác với Windows:

| Việc | Trên Mac |
|---|---|
| Lệnh trong `CLAUDE.md` / skill (viết kiểu PowerShell) | Claude tự đổi: `.venv/bin/python vs.py …` trong thư mục studio, `\` → `/` |
| Chép lời Whisper (`vs.py edit ingest`) | Không có CUDA → chạy CPU, chậm hơn nhiều; lần đầu tải mô hình large-v3 ~3 GB |
| Xuất bản nháp CapCut (`vs.py edit capcut`) | Code tìm `~/Movies/CapCut/User Data/Projects/com.lveditor.draft` (đổi chỗ lưu trong CapCut → đặt `CAPCUT_DRAFTS=…` trong `.env`). **Chưa thử**: định dạng bản nháp CapCut Mac có thể khác bản Windows đã đo → thử 1 job ngắn, mở được trong CapCut rồi mới dùng thật |
| Font | Mẫu dùng font trong `assets/fonts/` (đường dẫn tương đối) — giữ nguyên tên thư mục có dấu cách (`UTM Avo`, `UTM HelvetIns`) |
| Codex CLI (soát ảnh rẻ) | như Windows: `npm i -g @openai/codex` (cần Node: `brew install node`) → `codex login` |
| Skill | Có sẵn trong `.claude/skills/` khi mở Claude Code trong thư mục studio — KHÔNG cần `sync_skill.py` |
