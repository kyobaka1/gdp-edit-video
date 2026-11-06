# GDP Video Studio — hướng dẫn cho Claude Code

Giao tiếp với Sếp bằng tiếng Việt. **Quy trình + luật đầy đủ: skill `gdp-video-localize`**
(`C:\Users\Admin\.claude\skills\gdp-video-localize\SKILL.md`, bản sao trong repo giadungplus `skills/gdp-video-localize/`).
Plan/trạng thái: repo giadungplus `docs/plans/2026-10-20-gdp-video-studio-viet-hoa-video.md`.

## Lệnh nhanh

```powershell
Set-Location C:\Users\Admin\gdp-video-studio; $env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe vs.py new inbox\<file>.mp4 --id <brand>-<slug>
.\.venv\Scripts\python.exe vs.py analyze <id>            # --regroup: không tốn token
#   → viết jobs\<id>\direct.py (mẫu: jobs\gdp-ke-nha-tam-01\direct.py) → chạy nó ra edl.json
.\.venv\Scripts\python.exe vs.py music <id>              # nhạc Lyria không lời
.\.venv\Scripts\python.exe vs.py narrate <id>            # thuyết minh liền mạch, 1 lượt TTS
.\.venv\Scripts\python.exe vs.py render <id> [--final]
.\.venv\Scripts\python.exe vs.py qa <id> [--final]        # phải ĐẠT (sót 0); chưa → vs.py patch <id>
.\.venv\Scripts\python.exe vs.py audiocheck <id> [--final]
.\.venv\Scripts\python.exe vs.py templates <shop>        # xem mẫu chữ của shop
.\.venv\Scripts\python.exe vs.py shops                   # tình trạng tài nguyên từng shop (assets/shops/)
.\.venv\Scripts\python.exe vs.py look <ảnh…> -q "…"      # soát mắt ảnh bằng Codex model rẻ (không tốn Gemini)
.\.venv\Scripts\python.exe vs.py hear <audio>            # nghe lại lời Việt (Gemini; hết tiền → gpt-audio-mini)
.\.venv\Scripts\python.exe vs.py motion list --shop <shop> # animation thương hiệu shop dùng được (skill gdp-video-motion)
.\.venv\Scripts\python.exe vs.py motion import <file.html|zip> --id <id> --brand <BRAND> --role brand_reveal
.\.venv\Scripts\python.exe vs.py motion plan <id>         # xem animation job sẽ chèn (edl.motion = {"mode": "auto"})
# Dựng video QUAY SẴN theo PLAN (skill gdp-video-edit, studio/edit/) — 9:16 TikTok, chữ động theo từng từ
# ⛔ TRƯỚC KHI EDIT phải chốt với Sếp: CÓ dùng CapCut (giao bản nháp) hay KHÔNG (giao final.mp4) — chưa rõ thì HỎI
.\.venv\Scripts\python.exe vs.py edit new <thư mục clip> --id <id> --capcut co|khong --plan plan.md
.\.venv\Scripts\python.exe vs.py edit ingest <id>         # Whisper GPU: lời có mốc từng từ + ảnh lưới từng clip
#   → viết jobs\<id>\cut.py (mẫu: jobs\test-vlog-bac-kinh\cut.py) → vs.py edit cut <id>
.\.venv\Scripts\python.exe vs.py edit render <id> [--final]; .\.venv\Scripts\python.exe vs.py edit qa <id> [--final]
.\.venv\Scripts\python.exe vs.py edit capcut <id> --wait  # bản nháp CapCut desktop cho dựng viên sửa tiếp (CapCut phải tắt)
# Thiếu ảnh/asset → THƯ VIỆN DÙNG CHUNG assets/library/ (Sếp 05/11: xây 1 lần, dùng nhiều lần — không tạo lẻ từng video)
.\.venv\Scripts\python.exe vs.py lib find <từ…>           # tìm trước; có thì `vs.py edit add <id> lib:<chủ-đề>/<tên> --key g01`
.\.venv\Scripts\python.exe vs.py lib kit <bộ>             # tạo phần thiếu của BỘ asset 1 kiểu animation (Codex local → hỏng thì chatgpt.com Chrome + lib import)
# Scene Library assets/scenes/ (cảnh dựng sẵn: theme GDP/PHALEDO × preset micro/standard/full) → c.graphic("scene-<family>", …) trong cut.py
#   có: scene-chapter-card (C02 thẻ chương) · scene-keyword-burst (C01 từ khoá to, tự nằm SAU người — mặt nạ RVM assets/models/, chạy máy) · scene-pinned-title (C03 tiêu đề ghim cả chương + nhãn con theo lời, chữ động chạy tiếp) · scene-count-reveal (C04 đếm + lật từng mục) · scene-a-vs-b (C05 2 phe + chốt; ảnh src:<clip>@<giây> = khung cắt từ clip) · scene-detail-spotlight (C09 khoanh/chỉ/kính lúp) · scene-evidence-frame (C08 bằng chứng thật: ảnh/clip phát trong khung) · scene-problem-solution (C06 vấn đề → giải pháp) · scene-number-impact (C07 số đếm lên / từ → đến / biểu đồ) · scene-timeline (C10 các bước theo lời; micro = thanh tiến độ) · scene-quote (C11 câu nói đắt thành thẻ). C12 outro bỏ (đã có sẵn)
.\.venv\Scripts\python.exe tools\scene_previews.py <family>   # render kiểm mọi theme × preset + ảnh preview
.\.venv\Scripts\python.exe vs.py edit frame <id> <giây>     # khung RA đúng bản dựng + lưới toạ độ 0,1 (chọn x,y cho Scene)
```

Animation thương hiệu (Sếp 23/10, Motion Director V2): skill **`gdp-video-motion`** + `assets/motion/README.md`. Job
mới khai `edl["motion"] = {"mode": "auto"}` → brand reveal + accent (trong budget) + logo THƯỜNG TRỰC (chỉ tạm ẩn đúng
khoảng reveal chạy) + watermark động (xuất hiện → chìm dần → trượt đổi chỗ mỗi ~6s như cũ). `vs.py motion plan <id>` giải thích
chọn/bỏ; `vs.py motion storyboard <id>` ảnh soát. Thêm animation mới = `vs.py motion import`, không sửa code.

## 5 luật không được quên

1. Chữ trong cảnh (sản phẩm/nhãn/phụ kiện) giữ nguyên; chỉ đè chữ đồ hoạ, bằng MẪU có sẵn của SHOP
   (`assets/shops/<shop>/templates/`, `edl.shop`). Tài nguyên shop theo chuẩn `assets/shops/README.md`.
2. Dòng chữ xoay chéo → một ô xoay cùng góc.
3. Thuyết minh = một bài liền mạch bám cảnh, có chuyển ý — không đọc lại phụ đề; một lượt TTS (một giọng).
4. TTS gửi đúng văn bản, không chỉ dẫn giọng điệu; cổng kiểm ngược bắt buộc.
5. Nhạc nền luôn có, nhỏ nhưng nghe thấy (giọng −14 LUFS, nhạc −25 LUFS); không thêm tuyên bố sản phẩm chưa có trong nguồn.
