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
Mẫu Sếp đưa (05/11): `example/` = 3 video TikTok cùng kênh "chuquancaphe" (Nguyễn Hiển): M1 81,8s → số đo
`references/mau-phan-tich.md`; M2 "Mô hình 3C" + M3 "6 bước mở quán" (2,5 phút) → `references/mau-phan-tich-2.md` +
ảnh 10 kỹ thuật `references/mau-2-ky-thuat.jpg`. Đọc mục "Kịch bản & nhịp giữ chân" dưới đây TRƯỚC khi soạn/duyệt plan.
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

## Kịch bản & nhịp giữ chân (đo 3 mẫu, 05/11 — áp khi soạn plan / viết cut.py)

Hai sườn mẫu đã đo (chi tiết giây ở `mau-phan-tich-2.md`):
- **Bài nhiều bước** (M3): câu hứa → thẻ series → số liệu chứng minh → gỡ phản đối → lộ trình N bước → mỗi bước (thẻ
  tiêu đề bước → người nói + tiêu đề ghim dựng dần → minh hoạ) → uy tín → cú lật tự soi → hẹn tập sau → hình thương hiệu.
- **Khái niệm + chuyện thật** (M2): hook ngược đời → thẻ series → khái niệm → đặt tên (ghim) → chuyện thật có xung
  đột/rủi ro → lựa chọn → **bằng chứng** (quay màn hình số thật) → mở vòng → hẹn tập sau → hình thương hiệu.

Luật rút ra — Claude kiểm PLAN theo danh sách này, **thiếu thì GỢI Ý cho Sếp** (không tự bịa số/tuyên bố — luật 5):
1. **Giây 0 = nội dung**: lời bắt đầu ở 0,00s, từ khoá lớn hiện ≤0,6s. Không chào hỏi / logo mở đầu.
2. **Câu hứa có số + thời gian** trong 10s đầu ("từ 1,5tr lên 10tr/ngày qua 9 tháng", "6 bước"), rồi chứng minh ngay.
3. **Series**: tên series + chương/tập cố định khuôn; cuối bài "ở những tập sau…" → lý do theo dõi kênh.
4. **Vòng mở**: nói trước có N bước/N ý → người xem chờ đủ N. Ý nặng lý thuyết → **gỡ phản đối** trước khi người xem bỏ.
5. **Biển chỉ đường**: tiêu đề ghim "Bước k" suốt chương; mỗi chương mở bằng thẻ đồ hoạ.
6. **Hình đổi ~2,5–3s/lần** — không nhất thiết cắt: từ khoá lớn, số liệu, nhãn con dựng dần đều tính. Người nói được
   giữ tới 16s nếu chữ trên đó thay đều. Khoảng nghỉ giữa câu 0,35–0,5s vẫn ổn cho giọng giảng (M1 nói nhanh: 0,1–0,3s).
7. **Bằng chứng thật** (màn hình doanh thu/đơn hàng, trước–sau, đánh giá khách) sau câu chuyện, trước câu chốt — chỉ
   dùng số/ảnh Sếp đưa.
8. **Cú lật tự soi** gần cuối ("bạn thường bắt đầu từ bước 4") → người xem tự đối chiếu, dễ bình luận.
9. **Kết trên hình thương hiệu** (sản phẩm được đặt xuống / cửa hàng) + logo + hẹn tập sau; không kết bằng mặt người nói.
10. **Tắt tiếng vẫn hiểu**: phụ đề liền suốt bài + từ khoá lớn; bật tiếng có "vút/bùm" làm nhịp (thấp hơn giọng ~20 dB).

Áp cho video sản phẩm GDP: series "mẹo nhà gọn — tập N" · câu hứa có số ("12 hũ, 10 phút, tủ bếp hết bừa") · bằng chứng
trước–sau / thử chịu lực / màn hình đánh giá thật · kết trên sản phẩm + logo shop + "tập sau: tủ lạnh".

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
c.graphic("scene-chapter-card", at="Bước hai", until="nhóm khách", title="Bước 2: S-T-P",
          sub="Chia nhỏ thị trường", eyebrow="Bước 2")  # Scene C02: theme theo shop, preset theo thời lượng
c.graphic("scene-keyword-burst", at="hành trình", word="Hành trình")   # Scene C01: từ khoá to, tự nằm SAU người nếu được
c.graphic("scene-pinned-title", at="Bước hai", until="định vị", title="S-T-P", eyebrow="Bước 2/6",
          items=[("phân nhóm", "Segmentation", "phân nhóm thị trường"), ("định vị", "Positioning")])  # C03: ghim cả chương
c.graphic("scene-count-reveal", at="có ba lý do", until="dễ vệ sinh", title="3 lý do nên dùng",
          items=[("thủy tinh", "Thủy tinh dày"), ("nắp gỗ", "Nắp gỗ sồi"), ("dễ vệ sinh", "Dễ vệ sinh")])  # C04: đếm + lật
c.graphic("scene-a-vs-b", at="hộp nhựa", until="không ám mùi", a="Nhựa", b="Thủy tinh", photo_a="src:c04@2.0",
          photo_b="src:c05@1.5", items=[("ám mùi", "a", "Dễ ám mùi")], winner="b", win_at="thủy tinh thì")  # C05
c.graphic("scene-detail-spotlight", at="cái móc này", until="inox", x=0.62, y=0.48, label="Móc inox 304")  # C09
c.graphic("scene-evidence-frame", at="đây là doanh thu", until="một tháng", title="Doanh thu thật", clip="c09@3.0",
          zoom=1.4, zx=0.5, zy=0.35, figure="342.992.500đ", figure_at="ba trăm", caption="Quay màn hình app")  # C08
c.graphic("scene-problem-solution", at="khoan tường", until="năm phút", problem="Khoan tường", problem_note="nứt gạch",
          solution="Dán keo", solution_note="5 phút xong", switch_at="chỉ cần")  # C06: vấn đề → giải pháp
c.graphic("scene-number-impact", at="từ một rưỡi", until="mười triệu", from_value="1,5tr", from_label="từ",
          to_value="10tr", to_label="lên hơn", to_at="mười triệu")       # C07: số đếm lên (1 số: value="15 kg")
c.graphic("scene-timeline", at="đầu tiên", until="treo đồ", title="4 bước dán móc",
          items=[("lau sạch", "Lau sạch tường"), ("bóc", "Bóc lớp keo"), ("ép", "Ép thật chặt"), ("treo", "Treo đồ")])  # C10
c.graphic("scene-quote", at="đồ tốt", until="phải nghĩ", quote="Đồ tốt là đồ *dùng mỗi ngày không phải nghĩ*",
          by="Anh Vương · GIADUNGPLUS")                                  # C11: câu nói đắt thành thẻ riêng
c.theme("phaledo_warm")                                  # (tuỳ) ép theme Scene Library cả video
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
- `graphic(<id motion>, at, until|dur, **tham số)` = cảnh dựng sẵn từ **Scene Library** (`assets/scenes/`, hồ sơ
  `scene.json` — đọc `use_when`/`avoid_when` trước khi chèn) hoặc animation motion thường; lời vẫn chạy, chữ động tự
  tắt trong lúc đồ hoạ hiện (KHÔNG viết `cap()` cho lời đoạn đó — khối sau tự nhảy qua). Scene: **theme** tự theo shop
  của `c.logo()` (GDP → `gdp_red`, PHALEDO → `phaledo_dark`) hoặc `c.theme()`/`theme=` · **preset** tự theo thời lượng
  (<1,6s `micro` nhãn đè lên footage · <2,8s `standard` · còn lại `full`) · chuyển cảnh vào theo theme (GDP loé, PHALEDO
  tự mờ vào) · thẻ phủ khung ra bằng nhoè về trong suốt (lớp kế tự dời lên nằm dưới) · tiếng hiệu ứng tự chèn (giấy vút
  / kính ting / giấy trượt, dưới giọng). `photo="lib:<id>"` = ảnh thư viện — SẢN PHẨM phải là ảnh THẬT (`vs.py lib import
  --engine photo`); ảnh AI trong theme PHALEDO → cảnh báo. Lần đầu mỗi bộ chữ render 0,5–2 phút (cache ProRes ở
  `assets/motion/_cache/`, xoá thoải mái); CapCut: thẻ phủ khung = MP4, micro = MOV trong suốt, track "graphics".
- `scene-chapter-card` (C02): `title` (GDP ≤18 ký tự = 1 dòng to; PHALEDO ≤5 từ/dòng, ≤2 dòng; `|` ép xuống dòng) ·
  `sub` ≤34 · `eyebrow` ("Bước 2", "Chương 02") · `photo` · `bg` (gdp: default|kraft) · `seed` · `theme` · `preset`.
  Ảnh preview 9 tổ hợp: `assets/scenes/chapter-card/previews/`. (`cat-dan-mo-chuong` = bản cũ chỉ GDP full, giữ cho job cũ.)
- `scene-keyword-burst` (C01): một từ khoá / con số TO bật lên đúng lời, ĐÈ footage (không phủ khung, logo giữ).
  `word` (≤16 ký tự, ≤2 từ đẹp nhất, tự IN HOA, `|` xuống dòng — PHẢI là lời đã nói hoặc rút gọn đúng lời) · `lead` dòng
  dẫn nhỏ ("Bước 3", "từ") · `side` center|left|right · `y` (bỏ trống!) · `accent=1` màu nhấn · `behind` auto|True|False.
  Không ghi until/dur = 1,2s; at là cụm lời → tự hiện sớm 0,1–0,45s (mẫu). Preset: <0,95s micro (không lead — có lead
  thì tự nâng standard) · <1,7s standard · full (bóng mờ báo trước). **Chữ sau người** (mặt nạ RVM `assets/models/`,
  chạy máy): `behind="auto"` → máy đo mặt nạ người × NÉT chữ thật lúc chữ vừa vào đủ, dời chữ dọc tìm chỗ người che
  ~22% nét (đầu chìm sau đáy chữ, ≤ 35%); cận mặt / đầu sát mép trên → chữ TRƯỚC người và tự dời né vùng đầu; không có
  người → giữ chỗ (QA ghi lý do + % che đo từng khung; soát ô `g` trong `qa_*.jpg`). Muốn chữ sau người chắc ăn: từ
  NGẮN 1 dòng (≤ 2 từ), cảnh vừa người (đầu ở ~20–35% khung), ép `y=` thì máy chỉ đo. Nhịp mẫu: ~1 từ khoá / 2,5–3s trên cảnh
  người nói, không 2 cái < 2s. CapCut: MOV trong suốt đủ khung, chữ sau người đã khoét sẵn theo mặt nạ.
- `scene-pinned-title` (C03): tiêu đề GHIM ở tầm đầu cả một chương (5–20s, at → until) + nhãn con hiện đúng lúc nhắc tới
  (mục đang nói nổi bật, mục đã qua mờ). `title` ≤ 22 · `eyebrow` ("Bước 2/6") · `items=[(cụm lời | giây, "Nhãn"[, "ghi
  chú"]), …]` ≤ 6, theo thứ tự lời, nhãn = đúng ý đã nói (hiện sớm 0,15s) · `layout` auto|list|sides · `y` (bỏ trống).
  Preset theo nội dung: có ghi chú → full (nhãn 2 dòng) · có nhãn → standard · `preset="micro"` = chip ghim góc gọn
  ("BƯỚC 2 · S-T-P", không nhãn). **Chữ động KHÔNG tắt** (vẫn viết `cap()` cho lời chương đó) và tự né vùng tiêu đề
  (hạ xuống ~56%); logo tạm ẩn. Máy đo người mỗi 2,5s: bố cục theo KHOẢNG TRỐNG (2 bên trống → nhãn 2 bên đầu, không
  thì cột phía trống); tiêu đề to được nằm SAU đầu (≤ 30%), nhãn con / dòng nhỏ / dấu nặng luôn TRƯỚC và không được đè
  đầu. QA "⛔ vẫn ĐÈ VÙNG ĐẦU" (cảnh cận mặt) → đổi `preset="micro"` / cảnh khác. Không đặt từ khoá C01 trùng lúc
  (chồng chữ — cutlib báo). CapCut: 1 MOV trong suốt dài (~13MB/giây).
- `scene-count-reveal` (C04): "3 lý do / 3 bước / tổng kết" — số đếm TO + từng mục bật ra đúng lúc nói, đọng lại thành
  bảng tóm tắt. Thẻ ngắn 2–6s: < 2s `micro` (chip đếm đè footage, giữ logo) · < 4,2s `standard` phủ khung · còn lại
  `full` phủ khung, mục có ghi chú 2 dòng. `title` ≤ 26 (dài tự 2 dòng) · `eyebrow` · `items` 2–5 (≤ 26 / ghi chú ≤ 34)
  · `count` (mặc định số mục) · `bg`. Mục cuối nói sát cuối thẻ → tự hiện sớm ≤ 0,5s (cảnh báo), hơn nữa → lỗi, kéo
  `until`. GDP: tờ giấy xé + tem đỏ, mục mới tô dạ vàng · Dark: 01/02/03 mảnh + nét kẻ, số đếm khổng lồ chìm phía sau ·
  Warm: trang sổ tay, ô trống có sẵn, tick tay khi nói tới. Phủ khung → chữ động tắt, lớp cảnh sau tự dời xuống dưới
  đoạn tan (như thẻ chương). Lần đầu mỗi bộ chữ phủ khung render ~2 phút.
- `scene-a-vs-b` (C05): 2 phương án đối lập — mỗi phe nhãn (`a`, `b` ≤ 16) + ảnh (`photo_a`/`photo_b`) + ý con theo lời
  (`items=[(cụm lời, "a"|"b", "Ý"[, "ghi chú"]), …]` ≤ 3/phe), "VS" giữa; `winner` + `win_at` (cụm lời CHỐT) → phe thắng
  đóng dấu ✓, phe thua xám (+ gạch chéo đỏ ở GDP). `layout` sides (mặc định, 2 cột — ảnh dọc) | split (trên/dưới). Không
  ảnh → thẻ chữ, nhãn to. Preset theo thời lượng: < 2s micro (băng "A VS B" đè footage) · < 4,2s standard · full (ý 2
  dòng) — standard/full phủ khung. ⛔ Không chê thương hiệu khác đích danh / không so sánh ngoài lời; ảnh sản phẩm = THẬT.
- **Ảnh cho mọi Scene** (`photo`, `photo_a`, `photo_b`): `lib:<id>` (ảnh thư viện — sản phẩm phải là ảnh thật) hoặc
  **`src:<clip>@<giây>` = khung cắt thẳng từ clip đã quay** (tự lưu `jobs/<id>/assets/frames/`) — soát ảnh lưới
  `sheets/<clip>.jpg` để chọn giây có hình rõ.
- `scene-detail-spotlight` (C09): chỉ đúng MỘT chi tiết nhìn thấy trong cảnh — khoanh + mũi tên / đường chỉ dẫn tới
  `label` (+ `note`), ngoài vòng tối nhẹ; bản full có KÍNH LÚP phóng to vùng đó (build tự cắt khung RA giữa đoạn, `zoom`
  mặc định 2,2). **`x`, `y` bắt buộc** (tỉ lệ khung RA) — đọc bằng **`vs.py edit frame <id> <giây>`** (ảnh khung đúng như
  bản dựng + lưới 0,1, lưu `jobs/<id>/frames/`); `r` bán kính (0,09). Preset theo thời lượng: < 1,4s micro (chỉ khoanh)
  · < 2,4s standard (+ nhãn) · full (+ kính lúp). Đoạn chỉ phải nằm trọn trong 1 cảnh, cảnh tương đối yên (vòng không bám
  vật chạy); không khoanh mặt; nhãn đúng lời. Soát ô `g` trong `qa_*.jpg`: vòng có trúng chi tiết không.
- `scene-evidence-frame` (C08): BẰNG CHỨNG THẬT đóng khung — `clip="<clip>@<giây>"` = **clip đang chạy** phát trong khung
  (trang chừa ô cửa sổ, build `ProofPainter` phát clip vào, CapCut ghép sẵn ở 1080) hoặc `photo="src:…"|"lib:…"` (ảnh
  thật); `zoom` + `zx`,`zy` phóng dần tới chi tiết (toạ độ trong ảnh/clip — đọc bằng `vs.py edit frame`); `figure` (+
  `figure_label`, `figure_at` cụm lời) số liệu ĐÚNG như trong bằng chứng; `caption` dòng nguồn. Preset theo thời lượng:
  < 2s micro (khung nhỏ góc màn hình, `side`) · < 4,2s standard · full — standard/full phủ khung. Đặt sau câu chuyện,
  trước câu chốt (mẫu M2). ⛔ Ảnh AI KHÔNG làm bằng chứng; che thông tin riêng tư của khách trong ảnh chụp màn hình.
- `scene-problem-solution` (C06): 2 pha trong 1 thẻ — VẤN ĐỀ (`problem` ≤ 18 + `problem_note`, dấu SAI / gạch) → đúng
  `switch_at` (cụm lời CHUYỂN Ý: "nhưng", "chỉ cần") sang GIẢI PHÁP (`solution` + `solution_note`, dấu ĐÚNG). Ảnh
  `photo_problem` / `photo_solution` (`src:`/`lib:` — sản phẩm ảnh THẬT); `stamp_problem`/`stamp_solution` đổi chữ dấu.
  GDP xé đôi giấy đỏ lộ giấy vàng · Dark vệt sáng mở giải pháp · Warm lật trang sổ. Preset: < 2s micro (2 dòng đè
  footage, không ảnh/ghi chú) · < 4,2s standard · full — standard/full phủ khung. ⛔ Vấn đề là CÁCH LÀM / thói quen,
  không chê đích danh đối thủ; giải pháp đúng lời.
- `scene-number-impact` (C07): con số TO tự đếm lên (giữ cách viết số Việt: "342.992.500đ", "1,5tr", "+30%") — 1 số
  (`value` + `label`) hoặc cặp `from_value` → `to_value` (+ `from_label`/`to_label`, `to_at` = cụm lời nói số đến; cùng đơn
  vị thì đếm tiếp từ số cũ). Preset: < 1,6s micro · < 4,2s standard (đè footage, số to có thể nằm SAU người — `behind`
  auto như C01, nhãn nhỏ luôn trước) · full = thẻ phủ khung biểu đồ 2 cột + mức tăng tự tính (`change` auto|chữ|none).
  ⛔ Số đúng lời / nguồn, không làm tròn đẹp hơn; 2 số khác đơn vị không tính mức tăng.
- `scene-timeline` (C10): quy trình / hành trình có THỨ TỰ — `items=[(cụm lời, "Nhãn bước" ≤ 18[, "mốc thời gian" ≤ 16]),
  …]` 2–6 (bắt buộc), mỗi mốc hiện đúng lời, đường nối chạy mốc → mốc, mốc đang nói nổi bật, mốc đã qua mờ (full: tick).
  `title` ≤ 24. Preset theo NỘI DUNG: có ghi chú → full · không → standard (cả 2 phủ khung, timeline dọc) ·
  `preset="micro"` = **thanh tiến độ ngang** tầm trên (12% khung) + chip "2/4 · Nhãn" — đè footage, **chữ động KHÔNG
  tắt** (vẫn viết `cap()`), logo tạm ẩn; hợp đoạn demo dài người làm từng bước. Ý không thứ tự → C04 / C03.
- `scene-quote` (C11): câu nói đắt thành MỘT THẺ RIÊNG — `quote` ≤ 110 (đẹp 6–16 từ, `*cụm khoá*` nổi màu + gạch chân tự
  vẽ) · `by` người nói / nguồn · `eyebrow` ("Ghi nhớ", "Khách nói") · `photo` (full). Chữ hiện từng từ rồi đứng đọc.
  Preset: < 1,8s micro (thẻ gọn đè footage vùng phụ đề, `y` 0,66) · còn lại standard phủ khung · có `photo` → tự nâng full
  (≥ 3s). QA "đứng đọc ngắn" → kéo dài thẻ / rút câu. ⛔ Câu NGUYÊN VĂN, người nói / lời khách có thật (không bịa lời chứng
  thực, không thêm tuyên bố sản phẩm).

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
- M2/M3 khác M1: chữ lớn đặt **ngang tầm / trên đầu (15–35% H)**, hiện đúng hoặc sớm 0,3–0,5s so với lời, còn lời đầy
  đủ nằm ở **phụ đề liền** mảnh cố định ~55% H. Muốn kiểu này trước khi có `subs()`: dùng `cap(..., y=0.25)` cho từ khoá.

## Bộ hiệu ứng — có / chưa có (05/11)

| Hiệu ứng (mẫu) | Trạng thái | Ghi chú |
|---|---|---|
| Chữ động theo từ (M1), màn đen chữ, loé/tối dần/quét, zoom đẩy, đổi cỡ khung, chỉnh màu, logo | ✅ có | API ở trên |
| Phụ đề liền mảnh cố định ~55% H (M2, M3) | ⏳ đợt 1 | CapCut: dùng luôn track chữ thường (hiện, không ẩn) |
| Từ khoá lớn trên đầu, gradient trắng→trong, vào nhoè+trượt | ✅ Scene C01 Keyword Burst v1.0 (05/11) | `c.graphic("scene-keyword-burst", …)` |
| Tiêu đề ghim + nhãn con dựng dần theo lời ("Bước 2 / S-T-P") | ✅ Scene C03 Pinned Title v1.0 (05/11) | `c.graphic("scene-pinned-title", …)` |
| Số liệu từ→đến 2 bên đầu ("1,5tr" → "10tr"), ý mới đẩy ý cũ | ✅ Scene C07 Number Impact v1.0 (06/11) — số đếm lên, có thể sau người | `c.graphic("scene-number-impact", …)` |
| Thẻ series (chương · tập N · câu hứa + biểu đồ), giọng chạy tiếp | ⏳ đợt 1 khuôn đơn giản | đẹp: Sếp thiết kế Claude Design |
| Tiếng "vút / bùm / tách" theo chữ & thẻ | ✅ theo Scene (thẻ chương, từ khoá) — `tools/make_scene_sfx.py` | chữ động `cap()` chưa có tiếng |
| Minh hoạ trắng đen theo nghĩa, chuyển nhoè 1 khung, kết trên hình thương hiệu | ⏳ đợt 1 | |
| QA chính tả chữ hiện ("danh thu"), đánh số bước khớp lời, khe >6s không đổi hình | ⏳ đợt 1 | |
| Chữ nằm SAU người (tóc/tay che chữ) | ✅ 05/11 — RVM `assets/models/rvm_mobilenetv3_fp32.onnx` (Sếp duyệt tải, miễn phí, CPU ~40ms/khung) | dùng qua Keyword Burst `behind=` |
| Scene C02 Chapter Card — 3 theme (GDP Red Paper / PHALEDO Dark Glass / PHALEDO Warm Journal) × micro/standard/full | ✅ v1.0 (05/11) — `c.graphic("scene-chapter-card", …)` | `assets/scenes/chapter-card/` |
| Scene C01 Keyword Burst — 3 theme × micro/standard/full, chữ sau người tự quyết | ✅ v1.0 (05/11) | `assets/scenes/keyword-burst/` |
| Scene C03 Pinned Title — 3 theme × micro/standard/full, bố cục tự né người, chữ động chạy tiếp | ✅ v1.0 (05/11) | `assets/scenes/pinned-title/` |
| Scene C04 Count & Reveal — 3 theme × micro/standard/full, mục bật theo lời, bảng tổng kết | ✅ v1.0 (05/11) | `assets/scenes/count-reveal/` |
| Scene C05 A vs B — 2 phe (ảnh thật / khung từ clip) + VS + chốt phe thắng | ✅ v1.0 (06/11) | `assets/scenes/a-vs-b/` |
| Scene C09 Detail Spotlight — khoanh / mũi tên / đường chỉ dẫn + kính lúp, toạ độ bằng `vs.py edit frame` | ✅ v1.0 (06/11) | `assets/scenes/detail-spotlight/` |
| Scene C08 Evidence Frame — ảnh / CLIP thật phát trong khung + số liệu + nguồn | ✅ v1.0 (06/11) | `assets/scenes/evidence-frame/` |
| Scene C06 Problem → Solution — vấn đề (SAI) → chuyển ý → giải pháp (ĐÚNG), xé giấy / vệt sáng / lật trang | ✅ v1.0 (06/11) | `assets/scenes/problem-solution/` |
| Scene C07 Number Impact — số đếm lên, cặp từ → đến, full = biểu đồ 2 cột + mức tăng | ✅ v1.0 (06/11) | `assets/scenes/number-impact/` |
| Scene C10 Timeline / Process — mốc theo lời + đường nối; micro = thanh tiến độ giữ chữ động | ✅ v1.0 (06/11) | `assets/scenes/timeline/` |
| Scene C11 Quote / Insight — câu nói đắt thành thẻ riêng, chữ hiện từng từ, cụm khoá gạch chân | ✅ v1.0 (06/11) | `assets/scenes/quote/` |
| Scene C12 Brand Outro | ⛔ bỏ (Sếp 06/11: outro / intro thương hiệu đã có sẵn ở `assets/shops/<shop>/outro/` + Motion) | |

## Scene Library + Story Library (05/11 — đề xuất ChatGPT, Sếp bảo làm)

4 tầng: Asset (`assets/library/`) → Motion Engine → **Scene** (`assets/scenes/<family>/`: bố cục + vào/đứng/ra hoàn
chỉnh, nhiều theme, nhiều preset, chữ/ảnh là tham số) → **Story** (`assets/scenes/stories.json`: S01–S08 chuỗi family theo
dạng kịch bản). Luật + cách thêm family: `assets/scenes/README.md`. Khi viết cut.py: chọn Story theo dạng bài → chỉ chèn
family đã `ready` và lời thoả `use_when` (không vì đẹp mà nhét); family chưa có → dùng cap/cover/card.
Thêm family mới = 1 thư mục (scene.json + src HTML `setTime` + themes.js + `library.export_web`) → `vs.py motion import …
--id scene-<family> --role scene --no-render` → khai `opaque`/`params`/`scene` → `tools\scene_previews.py <family>` (render
kiểm mọi theme × preset + ảnh preview). Theme PHALEDO theo `shop.json`: Averta, ≤5 từ/dòng — không đổi sang serif.

## Chọn hiệu ứng — THƯ VIỆN HIỆU ỨNG (Sếp 07/11: gọi đúng tên, ít mà tinh)

Trang **`hieu-ung.html`** (gốc repo, mở thẳng bằng Chrome) = thư viện có MÃ + TÊN GỌI + demo thật cho mọi hiệu ứng:
T chữ (T01–T07) · C thẻ cảnh (C01–C11, chạy trực tiếp template, đổi theme/preset/chữ) · X chuyển cảnh · K khung & nhịp ·
A âm thanh · B thương hiệu · I/G/P ý tưởng chưa làm. Nguồn sự thật: **`assets/effects/catalog.json`** (nhóm, mức nặng nhẹ,
liều lượng, vai trò → gợi ý, nguyên tắc, ngân sách); thẻ C lấy chi tiết từ scene.json. Thêm hiệu ứng / family mới → thêm mục
catalog (+ demo) → `.\.venv\Scripts\python.exe tools\effects_page.py` (cắt clip demo 360×640 từ video đã dựng + ảnh thu nhỏ
→ dựng lại trang; `--html` chỉ dựng trang).

**Quy trình** (khi Sếp đưa kịch bản / PLAN): chia đoạn theo VAI TRÒ (hook, chương, từ khoá, liệt kê, các bước, so sánh,
vấn đề → giải pháp, số liệu, bằng chứng, chi tiết, câu chốt, chuyển ý, CTA, kể thường) → trả **BẢNG PHÂN CẢNH** dạng
`N. [vai trò] "lời" → C06 · Vấn đề → Giải pháp — vì sao` (đoạn không cần: `— chỉ chữ động`; cụm bước liền nhau:
`↳ nằm trong C10 (đoạn 4)`) + tổng điểm / ngân sách → Sếp sửa bằng MÃ ("đoạn 4 đổi C05 → C06") → mới viết cut.py.
Sếp cũng có thể tự xếp ở tab "Bảng phân cảnh" của trang rồi chép gửi — đọc đúng định dạng đó.
- **Ít mà tinh (luật cứng):** mặc định KHÔNG thêm gì; mỗi hiệu ứng phải trả lời "người xem nhận thêm được gì". Ngân sách /
  30s: Nhẹ 1 · Vừa 2 · Nặng (phủ khung) 3 điểm — Tối giản ≤ 3, Vừa ≤ 6 (mặc định), Đậm ≤ 9. Thẻ phủ khung cách nhau ≥ 8s,
  2 hiệu ứng bất kỳ ≥ 2,5s, 1 kiểu ≤ 2 lần / video < 60s; ưu tiên vai trò CẤU TRÚC trước nhấn nhẹ; bản nặng không chen được
  → dùng bản **micro** (nhẹ) hoặc để trống. 3 giây đầu là nội dung (thẻ chỉ khi chính nó là hook: C05/C06/C07/C11).
  Chuyển cảnh mặc định cắt thẳng; loé / tối / quét chỉ ở chuyển ý lớn.
- **Bộ ưng ý ★** của Sếp nằm trong trình duyệt của Sếp (Claude không đọc được) — Sếp chép gửi → Claude lưu bộ nhớ, ƯU TIÊN
  khi tự chọn nhưng vẫn giữ ngân sách.

## Thiếu source / asset → THƯ VIỆN DÙNG CHUNG (Sếp chốt 05/11: xây 1 lần, dùng nhiều lần)

`assets/library/` (luật đầy đủ: `assets/library/README.md`, code `studio/library.py` + `studio/imagegen.py`).
1. **Tìm trước**: `vs.py lib find <từ…> [--kind canh|nen|cat-dan|icon]` — có thì dùng:
   `vs.py edit add <job> lib:<chủ-đề>/<tên> --key g01` (ảnh → clip 15s; `c.cover("g01", …, push=0.06–0.1)` cho ảnh "sống";
   key ảnh đặt `g..`, tránh `b..` trùng tên khối chữ).
2. **Thiếu** → KHÔNG tạo lẻ cho một video. Thuộc kiểu hiệu ứng nào thì bổ sung vào BỘ đó (`assets/library/kits/<bộ>.json`)
   và hoàn thiện cả bộ một lần: `vs.py lib kit <bộ>` (chỉ tạo phần thiếu, Codex song song 3) → soát `kits/<bộ>.jpg`.
   Cảnh bối cảnh dùng chung (bếp bừa, phố vắng, văn phòng…) → `vs.py lib gen boi-canh/<tên> --prompt … --tag …`
   đặt tên/tag tổng quát để video khác tìm thấy.
3. **Máy tạo** — ưu tiên **Codex CLI local** (đăng nhập ChatGPT, không tốn API, đo 05/11: ~40–65s/ảnh, nền trong suốt
   được, ảnh tham chiếu được). Codex hỏng/hết usage → **chatgpt.com trên Chrome** (Sếp đã đăng nhập): Claude soạn prompt
   tiếng Việt (nội dung + phong cách bộ + "không chữ/logo" + khổ dọc/vuông, nền trong suốt nếu là miếng cắt dán), tạo,
   tải ảnh về thư mục tạm, rồi `vs.py lib import <file> <id> --prompt "…" --kind … --engine chatgpt-web`.
4. **Dựng animation từ bộ — Claude TỰ làm, Sếp không phải làm gì** (Sếp 05/11): `library.export_web(<id bộ>,
   assets/library/kits/<bộ>/)` (cắt viền + thu nhỏ + `assets.js`) → Claude viết HTML `setTime` cạnh đó (mẫu:
   `kits/chuong-cat-dan/cat-dan-mo-chuong.html` — tham số qua query, chữ tự co/2 dòng, giấy bay nhịp 12 hình/giây,
   seed đổi bố cục) → soát khung bằng Chrome ẩn → `vs.py motion import <html> --id … --brand '*' --role … --no-render`
   → khai `opaque`/`params`/`kit` trong motion.json → `vs.py motion render <id>` → `c.graphic(...)`. ⚠ KHÔNG dùng
   `will-change` trong CSS (Chrome giữ ảnh cũ → vẽ lại cùng t ra khác → Motion Engine từ chối). Motion Engine mở Chrome
   với `--disable-gpu` (05/11: vẽ GPU làm miếng giấy xoay có bóng đổ lệch 67 mức tuỳ khung trước → kiểm tất định
   trượt ngẫu nhiên theo seed) — đừng bỏ cờ này. Lỗi "vẽ lại cùng thời điểm ra khung khác" → tái hiện bằng vòng
   chụp tuần tự rồi chụp lại khung giữa, so màu đã nhân alpha, tìm vùng lệch trước khi sửa template.
- ⛔ Ảnh AI chỉ minh hoạ bối cảnh/ý/chất liệu đồ hoạ — KHÔNG vẽ sản phẩm đang bán thay ảnh thật, KHÔNG làm bằng chứng;
  QA nhắc mỗi khi cảnh là ảnh AI. Không lấy khung hình video kênh khác làm ảnh tham chiếu.

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

## Chưa làm

Đợt 1–3 ở bảng "Bộ hiệu ứng". Đợt 3 = đồ hoạ cắt dán (nhãn tiêu đề rơi, giấy bay vào, mũi tên, tem, sticker ảnh) + thẻ
series + thẻ tập sau: thẻ mở chương XONG 05/11 (`cat-dan-mo-chuong`); còn thẻ series (chương · tập N · câu hứa + biểu
đồ) và thẻ hẹn tập sau — mỗi kiểu một bộ trong `assets/library/kits/` + một HTML, làm như bước 4 mục thư viện.
Ngoài ra: tự gợi ý cảnh minh hoạ, xuất 3:4.
