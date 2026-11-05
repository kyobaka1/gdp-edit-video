---
name: gdp-video-edit
description: Dựng video từ SOURCE QUAY SẴN (clip điện thoại/máy quay CÓ TIẾNG — người nói trước máy, vlog, cảnh minh hoạ, quay màn hình) theo PLAN của Sếp bằng GDP Video Studio local (C:\Users\Admin\gdp-video-studio) — Claude xem lại source (chép lời có mốc TỪNG TỪ bằng Whisper GPU + ảnh lưới từng clip), cắt theo lời (bỏ lặng, bỏ câu hỏng), chèn cảnh minh hoạ đúng câu, đổi cỡ khung người nói, màn đen chữ mở đầu/câu chốt, CHỮ ĐỘNG hiện theo từng từ kiểu TikTok "cinematic" (cụm khoá IN HOA đậm + dòng mảnh, rút từng từ), chuyển cảnh loé sáng/tối dần/quét, chỉnh màu, chuẩn tiếng −14 LUFS, QA (chữ khớp lời, né mặt, vùng an toàn TikTok). Dùng khi Sếp nói "dựng video này theo plan", "edit video quay sẵn", "cắt ghép vlog", "làm video talking head", "chèn chữ động theo lời", "làm phụ đề kiểu TikTok", "dựng lại theo mẫu example", hoặc thả thư mục clip + plan.md cần dựng 9:16. KHÔNG dùng cho Việt hoá video tiếng Trung (skill gdp-video-localize) hay animation logo/watermark (skill gdp-video-motion).
---

# GDP Video Edit — dựng video quay sẵn theo PLAN (Claude Code điều khiển)

Studio `C:\Users\Admin\gdp-video-studio`, code `studio/edit/`, bộ chữ `assets/kinetic/cinematic/index.html`.
Chạy mọi lệnh bằng PowerShell:

```powershell
Set-Location C:\Users\Admin\gdp-video-studio; $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe vs.py edit <việc> …
```

**Nguồn skill = `studio\.claude\skills\gdp-video-edit\`** → sửa xong chạy `tools\sync_skill.py install`.
Mẫu gốc Sếp đưa (05/11): `example/` (video TikTok "Nguyễn Hiển - CQCP" + 9 ảnh) — số đo ở `references/mau-phan-tich.md`.
Job thử đủ bộ: `jobs/test-vlog-bac-kinh/cut.py` (bản lưu git: `tools/edit_cut_example.py`) — 11 clip vlog + giọng AI + 1 câu tiếng gốc, QA ĐẠT.

## Khác gì Việt hoá (gdp-video-localize)

| | Việt hoá TQ | Dựng quay sẵn (skill này) |
|---|---|---|
| Nguồn | 1 video TQ đã dựng | nhiều clip thô CÓ tiếng + PLAN |
| Tiếng | thuyết minh AI mới | **giọng gốc là chính** (hoặc giọng đọc riêng Sếp/AI có kịch bản) |
| Chữ | ô che chữ Hán theo mẫu shop | **chữ động theo từng từ đã nói**, không ô nền |
| Khung | 3:4 Shopee | **9:16 TikTok** (GĐ1); 3:4 làm sau |

## ⛔ Bước 0 — chốt chế độ TRƯỚC KHI EDIT (Sếp chốt 05/11)

Mỗi video PHẢI rõ một trong hai, chưa rõ thì **DỪNG, hỏi Sếp** (AskUserQuestion), không tự đoán, không mặc định:

| | **KHÔNG dùng CapCut** | **CÓ dùng CapCut** |
|---|---|---|
| Ai hoàn thiện | Studio làm hết | Studio dựng sườn, dựng viên hoàn thiện trong CapCut |
| Giao | `final.mp4` (+ `final.jpg`, bản nén nếu >30MB) | bản nháp CapCut (`vs.py edit capcut <id> --wait`) |
| Chỉnh màu, chuyển cảnh, zoom đẩy | Studio làm (render) | dựng viên làm bằng hiệu ứng CapCut (không mang sang) |
| Chữ động | nướng vào video | lớp trong suốt từng khối + chữ CapCut ẩn để sửa câu |
| Render | preview → duyệt → `--final` → qa → hear | preview → qa → Sếp duyệt nội dung → xuất CapCut (không cần `--final`) |
| Xuất video cuối | Studio | dựng viên xuất từ CapCut |

- Khai bằng `vs.py edit new … --capcut co|khong`, hoặc dòng `CapCut: có|không` trong `plan.md`. Thiếu cả hai → lệnh
  `new` từ chối chạy. Đổi ý giữa chừng: `vs.py edit mode <id> co|khong` (`render` / `capcut` đều kiểm chế độ).
- Câu Sếp có sẵn chữ "CapCut", "timeline", "để dựng viên sửa" → CÓ; "xuất video", "làm xong luôn", "giao file" → KHÔNG.
  Mơ hồ (chỉ nói "edit video này") → vẫn hỏi.

## Quy trình một video

1. `vs.py edit new <thư mục clip> --id <id> --capcut co|khong --plan plan.md` → `jobs/<id>/sources/c01…`. Giọng đọc
   riêng: `vs.py edit add <id> giong.wav --key vo --text kich_ban.txt` (có kịch bản = chữ chuẩn 100%).
   Chưa có PLAN mà Sếp bảo tự làm → Claude soạn `plan.md` theo `plan-template.md`, ghi rõ "Claude soạn".
2. `vs.py edit ingest <id>` — Whisper large-v3 trên GPU (RTX 4060, ~15s cho 80s lời) chép lời **có mốc từng từ** +
   `sheets/<key>.jpg` (8 khung có giây). In bảng lời từng nguồn. Xem ảnh lưới bằng Read (Claude lái) hoặc `vs.py look`.
3. Lời giọng thật (không có kịch bản) → `vs.py edit fix <id> <key> --hear` (Gemini nghe lại, ~32 token/giây) để sửa
   chữ (Whisper sai ~2%: "tính tiền lợi", "danh thu", "phổ Coffee"). Mốc vẫn của Whisper. Chỗ in `⚠ nghe tay` = Gemini
   thêm nhiều từ Whisper không nghe ra (tiếng đám đông) → không dùng đoạn đó làm chữ, hoặc nghe tay rồi `--text`.
4. **Đạo diễn = viết `jobs/<id>/cut.py`** (API ở dưới) → `vs.py edit cut <id>` in trục dựng + cảnh báo.
5. `vs.py edit render <id>` (540×960, ~45s cho 40s video) → `vs.py edit qa <id>` phải **ĐẠT**; xem `qa_preview.jpg`
   (mỗi khối chữ 1 ảnh lúc đủ chữ) — soát chữ đọc được, không đè mặt/sản phẩm, cảnh đúng câu.
6. Gửi Sếp `preview.mp4` + ảnh soát để duyệt nội dung (cắt, cảnh, chữ). Sau đó theo chế độ đã chốt ở bước 0:
   - **KHÔNG dùng CapCut**: `render --final` (1080×1920) + `qa --final` + `vs.py hear final.mp4` → gửi `final.mp4` +
     `final.jpg`. File > 30MB không tới được điện thoại → gửi kèm bản nén `-crf 25` (`final_xem.mp4`).
   - **CÓ dùng CapCut**: `vs.py edit capcut <id> --wait` (dùng bản preview được) → báo Sếp đóng/mở lại CapCut, mở bản
     nháp "GDP <id>"; nêu rõ phần dựng viên tự làm (chuyển cảnh, màu, zoom đẩy, xuất video).

## Xuất sang CapCut để dựng viên sửa tiếp (studio/edit/capcut.py — thử 05/11 trên CapCut 9.8.0)

- Bản nháp = thư mục JSON trong `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\<tên>\`. CapCut quốc tế
  KHÔNG mã hoá (Jianying TQ mới mã hoá). Không có định dạng chính thức → **nhân bản đoạn/chất liệu** từ bản nháp CapCut
  thật (`assets/capcut/templates.json`, trích từ bản nháp 3.5 "0321" + "0320 (1)" của Sếp; mất thì
  `capcut.build_templates("<bản nháp có đủ track video, chữ, lớp đè, tiếng>")`). CapCut 9.8 mở bản nháp kiểu 3.5 rồi
  TỰ NÂNG CẤP (thêm `Timelines/`, new_version 193) — Sếp mở + xuất thử được 05/11.
- Timeline gồm: track chính = **clip GỐC** cắt đúng giờ (kéo lại chỗ cắt được) + `black.mp4` cho màn chữ · track đè
  = mỗi khối chữ động 1 clip nền trong suốt (dời giờ / xoá được, KHÔNG sửa được chữ) · logo · track **chữ thường
  CapCut ẨN sẵn** (đúng lời từng khối — muốn đổi câu: bật đoạn đó, ẩn clip chữ động) · track tiếng đã chuẩn −14 LUFS.
- KHÔNG mang sang: chỉnh màu, chuyển cảnh loé/tối/quét, zoom đẩy dần (dựng viên dùng hiệu ứng có sẵn của CapCut).
- Đo 05/11: **PNG-trong-MOV và ProRes 4444 giữ nền trong suốt, WebM VP9 ra khung ĐEN** → mặc định `pngmov`
  (~3MB/khối). Khối chồng giờ chung 1 track → CapCut đẩy clip sau ra sau → chữ trễ dồn (0,7s) → bộ xuất xếp vào track
  trống đầu tiên (2 track đè). Sau sửa: Sếp mở bản nháp đủ 40,7s (`test-vlog-bac-kinh`) — **khớp giờ** (05/11).
- ⚠ **CapCut đang mở sẽ ghi đè danh sách dự án** (`root_meta_info.json`, đã sao lưu `.gdp-backup`) và xoá mục mới →
  `--wait` tự chờ CapCut tắt rồi ghi; Sếp mở lại CapCut là thấy. CapCut tự cập nhật có thể đổi định dạng (cộng đồng
  báo bản 10.x từ chối bản nháp do công cụ ghi) → mở lỗi thì trích lại khuôn từ bản nháp do bản mới tạo.

## cut.py — API (studio/edit/cutlib.py)

```python
from studio.edit.cutlib import Cut
c = Cut(__file__)
c.say("c03", "tôi nói thẳng", "hoàn hảo hết")          # đoạn lời: cụm đầu → hết cụm cuối (tự né lẹm từ kề)
c.say("c03", 12.4, 18.0, frame="tight", push=0.12)    # theo giây; frame wide|medium|tight|số; push = zoom dần
c.say("vo", "Năm ngày", "cảnh đẹp")                     # giọng đọc riêng → BẮT BUỘC có cover/card che hình
c.cover("c07", at="tiếp khách", until="tiện lợi cao", src_in=2.0, trans="flash", speed=0.8, push=0.05)
c.card(at=0.0, until="16 năm")                          # màn đen chữ (mở đầu / câu chốt), tự tối dần vào/ra
c.cap("!NHƯNG NHƯỢC ĐIỂM LÀ / .giá thuê của nó / rất là / ~CAO")
c.audio(music=None)        # mẫu KHÔNG có nhạc nền rõ; có nhạc thì music_lufs −30 (dưới giọng xa)
c.logo("giadungplus_official")   # tuỳ video: logo nhỏ góc trên-trái, dưới thanh tab TikTok; KHÔNG watermark
c.save()
```

- `say` cắt khoảng lặng > 0,35s trong đoạn, **giữ khoảng thở**: hết câu 0,25s · phẩy 0,16s · còn lại 0,12s (mẫu nói
  liền ~4 âm tiết/giây). `tighten=None` = giữ nguyên. Đoạn có hình tự đổi cỡ khung giữa các lần quay lại người nói
  (vừa → chặt → rộng, như mẫu) và lấy mặt làm tâm khi zoom.
- `cover`/`card`: `at`/`until` = cụm chữ trong **lời đã dựng** (tìm lần lượt) hoặc giây đầu ra. Khe ≤0,6s giữa hai
  lớp đè tự nối (khỏi chớp nền). `trans` vào / `trans_out` ra: `cut` · `flash` (1–2 khung loé sáng mất màu, mẫu dùng
  quanh đồ hoạ) · `dip` (tối dần, mặc định màn chữ) · `wipe` (vạch đen quét ngang). Thiếu hình cho giọng đọc → `save` báo lỗi.
- `ambient=0.3` giữ chút tiếng gốc cảnh minh hoạ (mặc định tắt).

## Luật chữ động (đo từ mẫu — `references/mau-phan-tich.md`)

- `cap()` = MỘT khối; dòng cách nhau ` / `. Đầu dòng: **`!` cụm khoá IN HOA rất đậm** · `!!` khoá nghiêng ·
  `~` chữ mảnh cỡ to ("2010", "CAO") · `.` dòng phụ mảnh nhỏ · không dấu = dòng đang nói (thường, nét vừa) · thêm `^` =
  màu nhấn vàng (mẫu chỉ 1 cụm vàng: "16 NĂM") — dùng THƯA, ~1 khối / 4–5 khối.
- **Chữ = lời đã nói**, khớp lần lượt (được bỏ từ đệm: ờ, thì, là, mà…). `1=một` hiện "1" khớp lời "một".
  `{chữ}` = chữ không có trong lời → QA cảnh báo; tránh dùng. Không thêm tuyên bố sản phẩm không có trong lời/PLAN.
- Cụm khoá = ý đắt nhất của câu (danh từ/tính từ kết luận: "NHƯỢC ĐIỂM", "QUAY VÒNG NHANH", "MIỄN PHÍ"); phần còn
  lại để dòng mảnh. Dòng đang nói đứng TRƯỚC cụm khoá tự co thành dòng dẫn nhỏ khi cụm khoá vào (mẫu 17,1s).
- Khối 2–4 dòng, ≤ ~10 từ. Dòng dài tự thu cỡ (≤74% bề ngang). `exit`: `words` (mặc định, rút từng từ trái→phải,
  cả khối ≤0,42s) · `rise` (trôi lên — dùng cho câu mở/khép) · `fade` (mờ dần — câu đệm, cuối màn chữ).
- Vị trí `pos="auto"`: máy chọn giữa / trái / phải × cao 40–56% để nằm trong **vùng an toàn TikTok** (ngang 6–84%,
  dọc 12–76% — mẫu để chữ "TỐT" lọt dưới nút tim). Màn chữ luôn ở giữa. **Né mặt = Claude SOÁT MẮT `qa_*.jpg`**
  (Sếp chọn không tải bộ dò mặt, 05/11): khối nào đè mặt / sản phẩm → ép `pos="left"|"right"` hoặc `y=0.40|0.56`
  trong `cap()` rồi render lại. (Đặt file YuNet `assets/models/face_detection_yunet_2023mar.onnx` thì máy tự né.)
- Khi đang có đồ hoạ tiêu đề (GĐ2) thì không đặt chữ (tiêu đề đồ hoạ thay chữ) — như mẫu.

## Số đo QA (vs.py edit qa)

Lời giọng thật đã đối chiếu · không cắt giữa từ (>30ms) · chữ ngoài vùng an toàn ≤1% · cụm khoá hiện ≥0,45s ·
đúng cỡ/thời lượng · không khung đen ngoài màn chữ · cả bản −14 ±0,5 LUFS · đỉnh ≤ −1 dBTP. Chữ đè mặt: soát mắt
`qa_*.jpg` (máy chỉ đo khi có file YuNet, ngưỡng ≤3% khối). Bản final: nghe lại 1 lần `vs.py hear final.mp4` (đủ lời,
không cụt chữ ở chỗ nối).

## Chi phí

Whisper chạy local GPU = 0 đồng (Sếp duyệt ngoại lệ luật "không chạy model nặng local", 05/11). Gemini chỉ khi
`fix --hear` (vài nghìn token/video) và TTS khi cần giọng đọc (`studio.voice.synthesize`, chuỗi dự phòng như Việt hoá).
Chữ động render bằng Chrome local; khung chữ đứng yên dùng lại ảnh (đo: chụp 908/1220 khung, 21s).

## Bẫy đã gặp (05/11)

- **Whisper bịa câu trên tiếng nền/nhạc**: "Hãy subscribe cho kênh La La School…", "Cảm ơn các bạn đã theo dõi…" →
  `asr._hallucination` lọc (danh sách câu + no_speech + xác suất từ); `ingest` in "bỏ câu bịa" để biết.
- **Whisper gộp khoảng lặng vào đầu từ** ("Tôi" 2,86s, tiếng thật 3,46s) → chữ hiện sớm. `asr._tighten` dời đầu từ
  qua khoảng lặng thật (RMS 10ms). Đo lại: lệch còn ~10ms.
- **Gemini nghe lại cũng không ổn định** (clip đám đông: lần 1 "Xin chào tất cả mọi người", lần 2 "Mọi người ơi, hiện
  tại") → `fix --hear` chỉ sửa chỗ thay 1:1 / lệch ≤1 từ; chỗ thêm nhiều từ giữ Whisper + "nghe tay".
- faster-whisper 1.2.1 + PyAV 19: `av.open(metadata_errors=…)` lỗi → `asr.py` tự đọc WAV thành mảng.
- **OpenCV 5 đã bỏ Haar `CascadeClassifier`** → dò mặt tự động chỉ còn `cv2.FaceDetectorYN` (YuNet) cần file mô
  hình ngoài; Sếp chọn KHÔNG tải (05/11) → né mặt bằng soát mắt, QA chỉ nhắc.
- Khoảng thở giữa câu làm lộ khung nền giữa 2 cảnh minh hoạ của giọng đọc → `save` tự nối khe ≤0,6s.
- Khối nhiều từ rút chữ lâu (11 từ × 0,083s = 0,9s) đè khối sau → giới hạn cả khối rút ≤0,3s + 0,12s.

## Chưa làm (GĐ2)

Đồ hoạ cắt dán (bản đồ giấy, nhãn tiêu đề rơi, mũi tên tự vẽ, tem, sticker ảnh) + thẻ tập sau "#2": Sếp thiết kế
bằng Claude Design (HTML có `setTime`, như animation logo) theo hướng dẫn Claude viết, mỗi mẫu có ô thay tiêu đề /
ảnh / mũi tên → thêm `c.graphic(...)`. Tự gợi ý cảnh minh hoạ. Xuất thêm 3:4.
