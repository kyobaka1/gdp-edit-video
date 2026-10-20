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

- Dịch theo NGHĨA bán hàng cho người mua Việt, ngắn hơn bản gốc; ô hẹp thì rút gọn, đừng nhồi.
- Chữ trên ô: tối đa ~2 dòng; tiêu đề/tính năng có thể VIẾT HOA; giá, khuyến mãi TQ (限时特价, ¥…) → bỏ (`skip`) hoặc thay câu trung tính, KHÔNG dịch giá tệ.
- KHÔNG thêm tuyên bố sản phẩm không có trong dữ liệu SKU thật (tải trọng, bảo hành, chứng nhận…). Không chắc → hỏi Sếp.
- Tên thương hiệu TQ / logo chữ TQ → che, thay bằng tên brand GDP nếu Sếp chỉ định, không thì để trống trung tính.
- Phụ đề thoại: ~14–16 ký tự/giây, mỗi câu ≤ 2 dòng; nếu video đã có hardsub trùng lời thoại thì chỉ dịch ô hardsub, bỏ `subtitles`.
- `audio.mode`: `keep` (không có lời Trung) · `mute` (mặc định khi có lời Trung) · `music` (cần file trong `assets/music/`).

## Không làm

- Không chạy model nặng local; không in/đọc ra `GEMINI_API_KEY`.
- Không lách chặn tải (hotlink) của Taobao/Douyin; video lấy từ Sếp hoặc NCC.
