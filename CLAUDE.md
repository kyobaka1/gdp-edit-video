# GDP Video Studio — hướng dẫn cho Claude Code

Giao tiếp với Sếp bằng tiếng Việt. **Quy trình + luật đầy đủ: skill `gdp-video-localize`**
(trong repo này: `.claude/skills/gdp-video-localize/SKILL.md`; bản sao ở repo giadungplus `skills/gdp-video-localize/`).
**Máy khác / Mac:** lệnh dưới viết kiểu Windows PowerShell — trên Mac / Linux chạy trong thư mục repo bằng
`.venv/bin/python vs.py …` (`\` → `/`). Cài máy mới: `SETUP.md` (mục 8 = Mac); skill có sẵn trong `.claude/skills/`.
Plan/trạng thái: repo giadungplus `docs/plans/2026-10-20-gdp-video-studio-viet-hoa-video.md`.

## Lệnh nhanh

```powershell
Set-Location C:\Users\Admin\gdp-video-studio; $env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe vs.py new inbox\<file>.mp4 --id <brand>-<slug>
.\.venv\Scripts\python.exe vs.py analyze <id>            # --regroup: không tốn token
#   → viết jobs\<id>\direct.py (mẫu: jobs\gdp-ke-nha-tam-01\direct.py) → chạy nó ra edl.json
#   ⭐ Việt hoá V2 (Sếp 11/11, mặc định job mới — mẫu tools\localize_v2_example.py + localize_v2_example_badge.py):
#   edl.clean tự chọn cách lấp chữ Trung theo vị trí + cỡ (sát mép & cắt ≤ 17% H = khung dải · phụ đề nằm sâu = thanh
#   phụ đề · tiêu đề lớn / khối / nhãn nhỏ = badge · sticker nghiêng = badge xoay · phủ > 22% khung = hỏi Sếp);
#   chỉ hiện lúc có chữ Trung + edl.caps (chữ Việt động, "pN" bám lời)
#   + narration.tempo + outro shop LUÔN bật → skill gdp-video-localize mục "Việt hoá V2"
#   Bộ nhận diện chữ / badge / khung dải theo SHOP = assets\shops\<shop>\shop.json mục `caps` (direct.py không ghi màu);
#   soát bằng ẢNH, không render video: .\.venv\Scripts\python.exe tools\caps_previews.py <job…> --at 3.2,4.9,6.9
.\.venv\Scripts\python.exe vs.py music <id>              # nhạc Lyria không lời
.\.venv\Scripts\python.exe vs.py narrate <id>            # thuyết minh liền mạch, 1 lượt TTS vclip (Sếp 11/11; giọng = shop.json voice.vclip)
.\.venv\Scripts\python.exe tools\vclip_voices.py         # giọng vclip của Sếp + shop nào đang dùng (key VCLIP_API_KEY/KEY_TTS trong .env)
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
.\.venv\Scripts\python.exe vs.py edit ingest <id>         # Whisper GPU: lời có mốc từng từ + ảnh lưới + tiếng động (sheets\<key>.sound.jpg)
#   → viết jobs\<id>\cut.py (mẫu: jobs\test-vlog-bac-kinh\cut.py) → vs.py edit cut <id>
#   video KHÔNG LỜI (POV/ASMR): c.sound(key, "#1", "#3") cắt theo cụm tiếng động · c.cap(…, at=giây) · ra gấp: c.auto_caps()
.\.venv\Scripts\python.exe vs.py edit render <id> --draft   # NHÁP ~11s: chỉ trục dựng + tiếng → chốt mối cắt trước khi làm chữ/đồ hoạ
.\.venv\Scripts\python.exe vs.py edit render <id> [--final]; .\.venv\Scripts\python.exe vs.py edit qa <id> [--final]
#   QA kèm qa_<bản>_cuts.jpg (mỗi mối cắt: khung trước|sau + độ to) · báo đứng hình do nguồn hết sớm · mép lời còn tiếng to
.\.venv\Scripts\python.exe vs.py edit capcut <id> --wait  # bản nháp CapCut (CapCut phải tắt) — giọng / nhạc / tiếng động TRACK RIÊNG
.\.venv\Scripts\python.exe tools\test_sound.py             # test phân tích tiếng động + bám mép + auto_caps (không cần GPU/API)
# Thiếu ảnh/asset → THƯ VIỆN DÙNG CHUNG assets/library/ (Sếp 05/11: xây 1 lần, dùng nhiều lần — không tạo lẻ từng video)
.\.venv\Scripts\python.exe vs.py lib find <từ…>           # tìm trước; có thì `vs.py edit add <id> lib:<chủ-đề>/<tên> --key g01`
.\.venv\Scripts\python.exe vs.py lib kit <bộ>             # tạo phần thiếu của BỘ asset 1 kiểu animation (Codex local → hỏng thì chatgpt.com Chrome + lib import)
# Scene Library assets/scenes/ (cảnh dựng sẵn: theme GDP/PHALEDO × preset micro/standard/full) → c.graphic("scene-<family>", …) trong cut.py
#   có: scene-chapter-card (C02 thẻ chương) · scene-keyword-burst (C01 từ khoá to, tự nằm SAU người — mặt nạ RVM assets/models/, chạy máy) · scene-pinned-title (C03 tiêu đề ghim cả chương + nhãn con theo lời, chữ động chạy tiếp) · scene-count-reveal (C04 đếm + lật từng mục) · scene-a-vs-b (C05 2 phe + chốt; ảnh src:<clip>@<giây> = khung cắt từ clip) · scene-detail-spotlight (C09 khoanh/chỉ/kính lúp) · scene-evidence-frame (C08 bằng chứng thật: ảnh/clip phát trong khung) · scene-problem-solution (C06 vấn đề → giải pháp) · scene-number-impact (C07 số đếm lên / từ → đến / biểu đồ) · scene-timeline (C10 các bước theo lời; micro = thanh tiến độ) · scene-quote (C11 câu nói đắt thành thẻ). C12 outro bỏ (đã có sẵn)
.\.venv\Scripts\python.exe tools\scene_previews.py <family>   # render kiểm mọi theme × preset + ảnh preview
# THƯ VIỆN HIỆU ỨNG hieu-ung.html (mã + tên gọi + demo; nguồn assets/effects/catalog.json) — chọn hiệu ứng = BẢNG PHÂN CẢNH, ít mà tinh (skill gdp-video-edit)
.\.venv\Scripts\python.exe tools\effects_page.py              # dựng lại trang (+ clip demo / ảnh thu nhỏ còn thiếu); --html chỉ dựng trang
.\.venv\Scripts\python.exe vs.py edit frame <id> <giây>     # khung RA đúng bản dựng + lưới toạ độ 0,1 (chọn x,y cho Scene)
# PHONG CÁCH (Sếp 07/11, học mẫu khoá "Edit Video Pro" — docs/2026-11-07-hoc-hoi-khoa-skill-edit-video-pro.md): c.style("<id>") trong cut.py
#   S1 gdp-ban-hang · S2 gdp-giai-thich · S3 phaledo-tap-chi · S4 san-pham-thuan (assets/styles/<id>/style.json + demo.jpg)
.\.venv\Scripts\python.exe vs.py styles                       # danh sách phong cách + dùng cho gì
.\.venv\Scripts\python.exe tools\style_previews.py [id]       # ảnh mẫu da phụ đề / màn chữ của phong cách
#   thẻ GIAO DIỆN C13 list-motion · C14 feature-chips · C15 label-zoom · C16 data-card · C17 cta-close (theme ui_dark/ui_light, font+màu theo shop)
.\.venv\Scripts\python.exe tools\ui_scenes_sync.py [family]   # sửa assets/scenes/_uikit/uikit.js hoặc template C13+ xong → chạy, rồi scene_previews
```

Animation thương hiệu (Sếp 23/10, Motion Director V2): skill **`gdp-video-motion`** + `assets/motion/README.md`. Job
mới khai `edl["motion"] = {"mode": "auto"}` → brand reveal + accent (trong budget) + logo THƯỜNG TRỰC (chỉ tạm ẩn đúng
khoảng reveal chạy) + watermark động (xuất hiện → chìm dần → trượt đổi chỗ mỗi ~6s như cũ). `vs.py motion plan <id>` giải thích
chọn/bỏ; `vs.py motion storyboard <id>` ảnh soát. Thêm animation mới = `vs.py motion import`, không sửa code.

Chữ hiện dần + khối nhấn + ảnh bìa + tiếng khẽ (Sếp 29/10, học từ skill brag): job mới khai `edl.reveal = {"mode": "auto"}`,
`edl.poster = {"mode": "auto"}`, `audio.sfx: true`; `*cụm từ*` trong `text_vi` = khối nhấn màu shop. Render cảnh báo
`⚠ chữ hiện ngắn` → rút bản dịch. Luật đầy đủ: skill `gdp-video-localize`. Test: `tools\test_reveal.py`.

## Ảnh listing (Image Studio — Sếp 11/11)

Nhân sự chỉ XOÁ CHỮ TRUNG rồi upload ảnh sạch lên app; Claude phủ chữ Việt + logo + watermark đúng nhận diện shop bằng MỘT
LỚP HTML trên ảnh (ảnh là nền cuối, không sửa nền). Quy trình + luật: skill **`gdp-image-listing`**; công cụ `image-studio/ims.py`.

```powershell
Set-Location C:\Users\Admin\gdp-video-studio\image-studio; $env:PYTHONIOENCODING='utf-8'
..\.venv\Scripts\python.exe ims.py pull <listing_id>          # ảnh sạch + ảnh Trung gốc + ngữ cảnh → jobs\listing-<id>\
..\.venv\Scripts\python.exe ims.py sheet <job>                # ảnh so: Trung gốc | đã xoá chữ | FINAL
..\.venv\Scripts\python.exe ims.py grid <job> [key…]          # lưới toạ độ % + vùng trống
#   → điền jobs\<job>\layout.json (mẫu: examples\layout-phaledo-bia-mo-ta.json; trường: skill → references\layout.md)
..\.venv\Scripts\python.exe ims.py render <job> [key…]        # → out\<key>.jpg + QA (phải ĐẠT) → soát MẮT từng ảnh
..\.venv\Scripts\python.exe ims.py push <job> --yes           # nộp lên app — CHỈ khi Sếp đã duyệt ảnh
..\.venv\Scripts\python.exe ims.py vpull [--shop <shop>]       # ẢNH PHÂN LOẠI giao trên trang /marketing/variant-images/ → job theo (shop, sản phẩm)
..\.venv\Scripts\python.exe ims.py kit show <shop>            # nhận diện ảnh của shop; `kit demo` = ảnh mẫu khối + bộ font; `kit sync` = lấy lại từ app
..\.venv\Scripts\python.exe ..\tools\test_image_studio.py     # test bộ dựng + QA
```

XOÁ CHỮ TRUNG GIỮ NỀN (Sếp 13/11): ảnh được giao CÒN chữ Trung mới làm, ảnh đã sạch thì bỏ qua — skill **`gdp-image-remove-text`**:
Photoshop web (Chrome của Sếp) → Tools → Lasso ôm sát chữ (đường bao tính từ pixel: `image-studio\ps_remove\text_polys.py`, vẽ bằng
`lasso.js`) → chọn HẾT các cụm rồi **Remove MỘT lần** → xuất PNG qua Adobe cloud → kéo về `clean\` → **đóng tab Chrome ngay**
(Photoshop web nặng máy). Adobe MCP không có Remove.

Nhận diện dùng chung `assets/shops/<shop>/`: `shop.json` (+ mục `image`: bộ font, viền chữ, logo…) và `image/kit.json` (brand kit
lấy từ app, không sửa tay). Bộ font: PHALEDO = Averta (ExtraBold / Regular) · GDP chữ lớn = UTM HelvetIns · UTM Avo ưu tiên cấp 1 ·
Poppins / PS Young để đổi gió. Layout không ghi mã màu, không che sản phẩm (`keep`), không thêm tuyên bố ngoài nguồn.
KHÔNG CHỈNH MÀU ẢNH (Sếp 12/11): chỉ thêm chữ + logo, không lớp tối dần / lớp phủ màu. MOBILE FIRST: chữ nhỏ → nâng cỡ rồi tách 2 dòng / rút gọn.
ẢNH ĐẠI DIỆN (Sếp 12/11) làm để tăng CTR: hook TO ở nửa trên, KHÔNG chữ / logo ở góc dưới-trái x ≤ 42%, y ≥ 88% (khung Shopee 11.11 / voucher che — QA báo lỗi; dải đáy bên phải vẫn đặt chữ được),
soát bằng `qa\<key>.tem.jpg` (bìa như khách thấy, cỡ tem). Luật + số liệu prod: skill → mục "Ảnh đại diện" + `references\cover-ctr.md`.
ẢNH PHÂN LOẠI (Sếp 12/11): cả bộ phân loại của một sản phẩm CHUNG một thiết kế (`layout.json → variant_set`), ảnh ra vuông; ảnh chưa có khung → dựng
khung phân biệt `bottom` (sản phẩm ngang, khung ≤ 20% chiều cao) / `right` (sản phẩm dọc); ảnh đã có khung → `fill` điền chữ. Đồ LTENG ghi lắp đặt đã gồm
(`included`: keo-dan · oc-vit · mieng-dan · coc-hut — PNG ở `image-studio/asset/`). Mẫu: `examples\layout-lteng-vn-phan-loai.json`; luật: skill → mục "Ảnh phân loại".
LTENG HCM: đen / trắng / đỏ (dải đỏ + dải đen chữ trắng). LTENG VN: tấm navy chữ trắng / chữ navy viền trắng. GDP (Sếp 12/11): tông ĐEN / ĐỎ / TRẮNG theo nền (nền sáng chữ đen, nền
tối chữ trắng), nhãn đỏ+trắng hoặc trắng+đỏ bo góc nhẹ, viền chữ mảnh — brand kit app lệch thì đo màu ảnh thật, ghi đè ở `shop.json → image`.

## 5 luật không được quên

1. Chữ trong cảnh (sản phẩm/nhãn/phụ kiện) giữ nguyên; chỉ đè chữ đồ hoạ, bằng MẪU có sẵn của SHOP
   (`assets/shops/<shop>/templates/`, `edl.shop`). Tài nguyên shop theo chuẩn `assets/shops/README.md`.
2. Dòng chữ xoay chéo → một ô xoay cùng góc.
3. Thuyết minh = một bài liền mạch bám cảnh, có chuyển ý — không đọc lại phụ đề; một lượt TTS (một giọng).
4. TTS gửi đúng văn bản, không chỉ dẫn giọng điệu; cổng kiểm ngược bắt buộc.
5. Nhạc nền luôn có, nhỏ nhưng nghe thấy (giọng −14 LUFS, nhạc −25 LUFS); không thêm tuyên bố sản phẩm chưa có trong nguồn.
