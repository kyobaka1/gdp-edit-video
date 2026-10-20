# GDP Video Studio — hướng dẫn cho Claude Code

Giao tiếp với Sếp bằng tiếng Việt. Plan + trạng thái: repo giadungplus
`docs/plans/2026-10-20-gdp-video-studio-viet-hoa-video.md` (đọc STATUS + RESUME BRIEF).

## Quy trình một video (Claude điều khiển, Sếp duyệt)

Mọi lệnh chạy bằng `.venv\Scripts\python.exe vs.py …` trong thư mục này (PowerShell, đặt `$env:PYTHONIOENCODING='utf-8'`).

1. `vs.py new inbox\<file>.mp4 --id <slug>` — tạo `jobs/<slug>/`.
2. `vs.py analyze <slug>` — Gemini tìm chữ Trung theo khung (mỗi 0,5s) + chép lời → `edl.draft.json`.
3. **Claude làm đạo diễn:** copy `edl.draft.json` → `edl.json`, điền `text_vi` cho từng ô + từng câu thoại.
   Xem `jobs/<slug>/frames/*.jpg` để hiểu ngữ cảnh. Ô `needs_review` hoặc ô không cần che → `"skip": true`.
4. `vs.py render <slug>` → `preview.mp4` (960p) · `vs.py qa <slug>` → phải **ĐẠT (sót 0)**.
   Gửi Sếp `contact.jpg` (SendUserFile) + đường dẫn preview.
5. Sếp sửa bằng lời → chỉ sửa `edl.json` → render + qa lại (KHÔNG analyze lại).
6. Sếp duyệt → `vs.py render <slug> --final` + `vs.py qa <slug> --final` → `final.mp4` (+ `.srt` nếu có thoại).

## Luật dịch / chữ đè

- ⛔ **Chữ TRONG CẢNH giữ nguyên** (Sếp chốt 20/10): chữ in trên sản phẩm, bao bì, nhãn dán, chai lọ, phụ
  kiện, đạo cụ là một phần của video → KHÔNG đè, KHÔNG làm mờ. Gemini gắn `kind: scene` → nháp đặt
  `mode: "keep"`; QA không tính chúng là sót. Chỉ đè chữ ĐỒ HOẠ hậu kỳ (`kind: overlay`: phụ đề, tiêu đề,
  nhãn tính năng, chữ trên màn hình đồ hoạ). `mode: "blur"` vẫn có nhưng chỉ dùng khi Sếp yêu cầu.
- Mỗi job để quyết định đạo diễn trong `jobs/<slug>/direct.py` (bảng dịch zh→vi, skip) để chạy lại được.
- Câu Việt bị bẻ dòng mồ côi 1 chữ → RÚT GỌN câu, đừng chỉnh kỹ thuật. Render tự nới ô (ngang trước,
  ≤92% khung, rồi dọc) để chữ ≥ 3% chiều cao khung.
- QA chưa đạt: `vs.py patch <slug>` (cùng chữ gốc → nới giờ ô cũ; lạ → thêm ô cần xem) rồi render + qa lại.
  Phân tích lại cách gom mà không tốn token: `vs.py analyze <slug> --regroup`.
- Dịch theo NGHĨA bán hàng cho người mua Việt, ngắn hơn bản gốc; ô hẹp thì rút gọn, đừng nhồi.
- Chữ trên ô: tối đa ~2 dòng; tiêu đề/tính năng có thể VIẾT HOA; giá, khuyến mãi TQ (限时特价, ¥…) → bỏ (`skip`) hoặc thay câu trung tính, KHÔNG dịch giá tệ.
- KHÔNG thêm tuyên bố sản phẩm không có trong dữ liệu SKU thật (tải trọng, bảo hành, chứng nhận…). Không chắc → hỏi Sếp.
- Tên thương hiệu TQ / logo chữ TQ → che, thay bằng tên brand GDP nếu Sếp chỉ định, không thì để trống trung tính.
- Phụ đề thoại: ~14–16 ký tự/giây, mỗi câu ≤ 2 dòng; nếu video đã có hardsub trùng lời thoại thì chỉ dịch ô hardsub, bỏ `subtitles`.
- `audio.mode`: `keep` (không có lời Trung) · `mute` (mặc định khi có lời Trung) · `music` (cần file trong `assets/music/`).

## Không làm

- Không chạy model nặng local; không in/đọc ra `GEMINI_API_KEY`.
- Không lách chặn tải (hotlink) của Taobao/Douyin; video lấy từ Sếp hoặc NCC.
