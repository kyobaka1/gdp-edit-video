---
name: gdp-image-listing
description: Hoàn thiện ẢNH LISTING Shopee cho các shop Gia Dụng Plus (PHALEDO, LTENG, GIADUNGPLUS…) bằng GDP Image Studio chạy local (repo gdp-video-studio, thư mục image-studio/, Windows / Mac) — nhân sự chỉ XOÁ CHỮ TRUNG rồi upload ảnh sạch lên app PluSor; Claude tải ảnh sạch về, phủ MỘT LỚP HTML lên ảnh (ảnh là nền cuối): chữ bán hàng tiếng Việt, nhãn, chú thích, bảng thông số, logo, watermark đúng NHẬN DIỆN SHOP (font, màu, kiểu nhãn — dùng chung assets/shops/ với video studio), bố cục theo mục đích từng ảnh (bìa / sản phẩm / mô tả / phân loại), QA tự động (chữ đè sản phẩm, chìm nền, tràn, quá nhỏ, sót chữ Hán) rồi nộp final lên app. Dùng khi Sếp nói "làm ảnh listing <id>", "gắn chữ / logo cho ảnh đã xoá text", "phủ chữ lên ảnh sạch", "dựng ảnh bìa / ảnh mô tả theo branding shop", "nhân sự xoá chữ xong rồi, làm tiếp", "làm ảnh listing nhiều shop song song", hoặc đưa ảnh đã xoá chữ + ảnh Trung gốc cần ra bản final. KHÔNG dùng để xoá chữ Trung / sửa nền ảnh (việc của nhân sự), viết tên + mô tả + plan nội dung (skill gdp-listing-plan), chấm điểm kết quả (skill gdp-listing-review), hay Việt hoá video (skill gdp-video-localize).
---

# GDP Image Listing — phủ chữ + nhận diện shop lên ảnh đã xoá chữ

Giao tiếp với Sếp bằng tiếng Việt. Công cụ: `image-studio/ims.py` trong repo `gdp-video-studio`.

## Phân vai (Sếp chốt 11/11)

| Ai | Làm gì |
|---|---|
| **Nhân sự** | Xoá chữ Trung trên ảnh cho sạch, gọn → upload ảnh sạch lên app PluSor (ảnh kết quả của item trên trang `/marketing/listing/<id>/edit/`). Hết. |
| **Claude (skill này)** | Tải ảnh sạch + ảnh Trung gốc về → viết chữ Việt + chọn bố cục theo mục đích ảnh → phủ lớp HTML đúng nhận diện shop → QA → Sếp duyệt → nộp final lên app. |

Nguyên lý: **ảnh là nền cuối cùng, không bị sửa**. Mọi thứ thêm vào (chữ, nhãn, lớp tối dần, logo, watermark) là một lớp
HTML chụp bằng Chrome. Muốn đổi → sửa `layout.json` rồi render lại, vài giây một ảnh.

## Lệnh

```powershell
Set-Location C:\Users\Admin\gdp-video-studio\image-studio; $env:PYTHONIOENCODING='utf-8'
..\.venv\Scripts\python.exe ims.py pull <listing_id>              # tải ảnh sạch + Trung gốc + ngữ cảnh → jobs\listing-<id>\
..\.venv\Scripts\python.exe ims.py new <job> --shop <shop> <ảnh…> --kind cover [--src <ảnh Trung gốc…>]   # ảnh có sẵn trên máy
..\.venv\Scripts\python.exe ims.py sheet <job>                    # ảnh so: Trung gốc | đã xoá chữ | FINAL
..\.venv\Scripts\python.exe ims.py grid <job> [key…]              # lưới toạ độ % + vùng trống / vùng bận của từng ảnh
..\.venv\Scripts\python.exe ims.py grid <job> <key> --zoom 20,84,80,100   # phóng to một vùng, vạch mỗi 2% — đo ô icon / chi tiết nhỏ
..\.venv\Scripts\python.exe ims.py render <job> [key…]            # layout.json → out\<key>.jpg + QA (qa\<key>.jpg, qa\<key>.json)
..\.venv\Scripts\python.exe ims.py push <job> [key…] --yes [--review]   # nộp final lên app — CHỈ khi Sếp đã duyệt
..\.venv\Scripts\python.exe ims.py kit show <shop>                # nhận diện ảnh của shop (màu, font, nhãn, logo, luật chữ)
..\.venv\Scripts\python.exe ims.py kit demo <shop>                # ảnh mẫu MỌI khối của shop trên nền tối + sáng
..\.venv\Scripts\python.exe ims.py kit sync <shop> --listing <id> # lấy lại brand kit từ app (khi Sếp đổi kit / shop mới)
..\.venv\Scripts\python.exe ..\tools\test_image_studio.py         # test bộ dựng + bộ QA (không cần app)
```

Bash (Git Bash / Mac / Linux): `cd image-studio && PYTHONIOENCODING=utf-8 ../.venv/Scripts/python.exe ims.py …` (Mac:
`../.venv/bin/python`). Script Python tự viết để đọc file của job cũng cần `PYTHONIOENCODING=utf-8` (console Windows mặc
định cp1252 → lỗi `UnicodeEncodeError`). Cần Chrome + `playwright` (đã có trong `requirements.txt`).
Kết nối app dùng chung token của `plusor.py` (`PLUSOR_BASE_URL` / `PLUSOR_TOKEN` trong `.env` của studio, hoặc biến
`PLUSOR_ENV_FILE` trỏ tới `.env` của plusor-pipeline — mặc định `~/Desktop/Codex Workflow/plusor-pipeline/.env`).

## Quy trình tới final (8 bước)

1. **Tải việc** — `ims.py pull <listing_id>`. Được: `clean/` (ảnh sạch), `src/` (ảnh Trung gốc đã ghép cặp), `brief.json`
   (tên, mô tả, phân loại, ghi chú Sếp), `job.json`, `layout.json` (mỗi ảnh một khung; nếu app đã có design plan thì có sẵn
   khối NHÁP `_nhap_tu_plan`). Đọc các dòng cảnh báo của lệnh:
   - `⚠ đã qua Editor trên app` = ảnh kết quả có thể ĐÃ có chữ (làm theo kiểu cũ), không phải ảnh sạch → soát ở bước 2.
   - `⏳ chưa có bản sạch` = nhân sự chưa xoá chữ / chưa upload → báo Sếp, KHÔNG tự lấy ảnh Trung làm nền. Ảnh gốc vốn
     không có chữ thì `pull --allow-source`.
2. **Soát đầu vào bằng mắt** — `ims.py sheet <job>` rồi ĐỌC ảnh sheet. Với từng ảnh: nền đã sạch chưa (còn chữ Hán, vết
   xoá loang, khung / biển chữ sót)? Cặp gốc ↔ sạch có đúng ảnh không? Ảnh chưa sạch → ghi lại số item báo Sếp trả nhân sự;
   **không tự vá nền, không lấy chữ che vết bẩn** (trừ khi một khối chữ đằng nào cũng nằm đúng chỗ đó).
   Ngưỡng: còn chữ Hán / mảng loang / khung chữ sót → DỪNG ảnh đó, trả nhân sự. Vết li ti (vài điểm ảnh) → làm tiếp, ghi
   vào báo cáo cho Sếp (toạ độ %), và kiểm vết KHÔNG rơi sát chữ (một chấm cạnh chữ đọc thành dấu câu) — dời chữ tránh nó.
3. **Đọc "plan" của bản Trung** — mở ảnh trong `src/`: ảnh này nói gì, mấy nhóm chữ, nhóm nào to, nằm đâu, gắn với chi tiết
   nào của sản phẩm. Đó là bản thiết kế gốc: giữ **thứ bậc + vị trí tương đối**, thay chữ bằng tiếng Việt bán hàng.
   Kèm `brief.json` + `job.json → images.<key>.plan` (chữ đã soạn trên app). Chưa có nội dung → viết theo mục
   "Nội dung chữ" bên dưới.
4. **Đo ảnh** — `ims.py grid <job> <key>`: in bảng ô 5% (`#` bận = sản phẩm / vật thể, `.` trống nền tối, `:` trống nền
   sáng) + ảnh `qa/<key>.grid.jpg` có lưới x / y (vạch đậm 10%, vạch mảnh 5%). `#` gồm cả hậu cảnh (kệ, cây, chai lọ) —
   `keep` do bạn ƯỚC BẰNG MẮT trên ảnh lưới: chỉ bao SẢN PHẨM CHÍNH (kèm phần đang bán: nắp, thìa…), không bao khay / đạo
   cụ / hậu cảnh. Cần đo chính xác ô icon, chi tiết nhỏ → `grid --zoom x0,y0,x1,y1` (vạch mỗi 2%).
5. **Viết `layout.json`** — mỗi ảnh: `kind`, `keep`, `blocks`. Trường + ví dụ: `references/layout.md`;
   mẫu thật: `image-studio/examples/layout-phaledo-bia-mo-ta.json`. Chỉ khai *khối gì, chữ gì, ở đâu, to cỡ nào* —
   **không ghi mã màu / font** (shop quyết).
6. **Render + QA** — `ims.py render <job>`. Phải **ĐẠT (0 lỗi)**. Sửa theo bảng "QA báo gì → sửa gì".
7. **Soát mắt final** — ĐỌC từng `out/<key>.jpg` (và `qa/<key>.jpg` khi cần xem khung). QA đạt chưa chắc đẹp: xem cân
   đối, chữ có "thở" không, có che chi tiết đắt giá của sản phẩm không, logo / watermark có vô duyên không, cả bộ ảnh có
   cùng một giọng không. Sửa → render lại. Dựng `ims.py sheet <job>` lần cuối để gửi Sếp ảnh so trước / sau.
8. **Sếp duyệt → nộp** — gửi Sếp ảnh final (hoặc sheet). Sếp OK mới `ims.py push <job> --yes` (ghi đè ảnh kết quả của item
   trên app; `--review` = xin duyệt mục bìa / sản phẩm / mô tả). Chưa có lời duyệt của Sếp trong phiên → KHÔNG push.

## 9 luật không được quên

1. **Không sửa ảnh nền, KHÔNG CHỈNH MÀU ẢNH (Sếp 12/11).** Chỉ THÊM chữ, nhãn, logo, watermark lên ảnh đã cung cấp; giữ
   nguyên màu + độ sáng ảnh. Không có lớp tối dần / lớp phủ màu / tấm nền rộng (`scrims` đã bỏ, `panels` > 25% ảnh bị từ
   chối). Chữ khó đọc → cho CHÍNH CHỮ một nền riêng (dải `plate` / `plate-dark`, nhãn, `bg` ôm chữ, viền `outline`) hoặc dời
   sang vùng nền đều màu. Ảnh ra giữ nguyên kích thước ảnh sạch.
2. **Không che sản phẩm.** Mọi ảnh có sản phẩm phải khai `keep`; chữ không được đè `keep` (QA báo LỖI). Cố ý đặt lên vật
   thể (nhãn trong ô icon, chú thích sát chi tiết) → khối đó `"over": true`. Ngoại lệ có chủ ý: **watermark** nằm TRÊN
   sản phẩm (chống lấy cắp ảnh — phải xoá cả sản phẩm mới gỡ được), rất mờ. Sản phẩm trắng / sáng bị watermark màu làm ám
   màu → hạ `opacity` (0.08–0.12), thu `w`, dời sang phần sẫm hơn của sản phẩm — vẫn phải chạm sản phẩm; nêu trong báo cáo.
3. **Nhận diện theo SHOP, không tự chế.** Font, màu chữ, kiểu nhãn, logo, watermark lấy từ `assets/shops/<shop>/`
   (`ims.py kit show`). Layout không ghi `#hex`; cần màu khác dùng tên trong bảng màu (`heading`, `ink`, `accent`,
   `primary`, `dark`, `on_dark`, `on_light`). Font chỉ chọn trong các BỘ FONT shop được dùng (mục "Bộ font").
4. **Logo + watermark do bộ dựng tự đặt** theo kit (logo đúng file nhân sự dùng trên app, tự đổi bản đậm khi nền sáng).
   Chỉ can thiệp khi vướng: `"logo": false`, `"logo": {"y": …}`, `"watermark": {"y": …}`. Đặt chữ phải NÉ logo.
5. **Chữ bám nội dung thật của TỪNG ảnh** (bản Trung nói gì thì Việt hoá đúng ý đó, gọn hơn) — không quay vòng một danh
   sách lợi ích, không thêm tuyên bố / khuyến mãi / số liệu không có trong nguồn. Bìa được dựng hook mới nhưng phải là
   cam kết / số liệu CÓ THẬT.
6. **Việt hoá ĐỦ nhóm chữ có nghĩa** của bản Trung (tiêu đề, dòng phụ, nhãn, từng bước, từng dòng bảng, số đo). Rút gọn
   là câu ngắn hơn, không phải bớt nhóm. Bỏ: watermark / tên shop gốc, khuyến mãi sàn Trung, QR / SĐT.
7. **MOBILE FIRST (Sếp 11/11).** Khách xem ảnh trên điện thoại (ảnh rộng cỡ 390px màn hình → 1pt ≈ 0,39px). Chữ nhỏ là
   chữ chết: **nâng cỡ rồi tách 2 dòng, hoặc rút gọn chữ** — không giữ một dòng dài cỡ bé. Tối thiểu: mọi chữ ≥ 26pt
   (dưới 20pt là LỖI), dòng phụ ≥ 32pt, tiêu đề ảnh mô tả / sản phẩm 48–68pt, tiêu đề bìa 56–72pt, nhãn bìa ≥ 40pt.
   Vd dòng phụ một dòng 27pt "Hũ đường thuỷ tinh nắp gỗ keo, thêm nét ấm cho gian bếp" → 2 dòng 37pt
   "Hũ thuỷ tinh nắp gỗ keo / thêm nét ấm cho gian bếp"; chữ trong ô icon "Kín khí chống ẩm" 19pt → "Kín khí" 27pt.
   Tông chữ theo nền thật: để `tone` tự động (nền tối → chữ sáng, nền sáng → chữ đậm); nền loang lổ thì cho chữ nền riêng
   (dải, nhãn, `bg` ôm chữ) — không phủ màu lên ảnh.
8. **QA phải ĐẠT + phải nhìn bằng mắt** trước khi báo xong. Không báo "đã xong" khi chưa đọc ảnh final.
9. **Push là việc ghi production** — chỉ sau khi Sếp duyệt ảnh trong phiên; không `--force` khi QA còn lỗi mà Sếp chưa
   chấp nhận lỗi đó.

## Bố cục theo mục đích ảnh

| Loại (`kind`) | Mục tiêu | Chữ | Gợi ý bố cục |
|---|---|---|---|
| `cover` ảnh bìa (1:1) | CTR — 2 giây hiểu ngay | 1 tiêu đề RẤT lớn (≤ 5 từ / dòng, ≤ 2 dòng) + 1–2 nhãn cam kết / số liệu thật. Không nhồi | Tiêu đề + nhãn ở khoảng trống phía trên (hoặc dưới) sản phẩm; nền loang → tiêu đề dạng dải / viền, KHÔNG phủ màu lên ảnh. Sản phẩm chiếm ≥ 50% ảnh, không bị chữ lấn |
| `product_image` | Chuyển đổi — mỗi ảnh MỘT ý | 1 tiêu đề (48–64pt) + 1 dòng phụ (≥ 32pt, dài thì 2 dòng); có chi tiết cần chỉ → 1–3 `callout` có đường chỉ | Chữ về một phía, sản phẩm phía còn lại; chú thích đặt cạnh đúng chi tiết |
| `description_image` (3:4 / dọc dài) | Thông tin — bám sát bản Trung | Tiêu đề khối + dòng phụ + đủ nhãn / bước / bảng / số đo | Soi lại vị trí từng nhóm chữ của bản Trung; ô icon → `text` đặt trong ô (`over: true` nếu ô nằm trong `keep`); bảng → `spec`; các bước → `list` kiểu `number`; số đo → `dim` |
| `variant_image` | Chọn đúng phân loại | 1 nhãn tên / dung tích phân loại (lấy từ `job.json → variant`). Không tiêu đề | Nhãn ở góc trống, cỡ lớn dễ đọc ở ảnh thu nhỏ |

Cả bộ ảnh một listing: cùng một cách gọi tính năng, cùng cỡ tiêu đề cho ảnh cùng loại, cùng vị trí logo.

## Nội dung chữ (khi app chưa có design plan cho ảnh đó)

Nguồn theo thứ tự: `job.json → images.<key>.plan` (design plan của skill `gdp-listing-plan`) → chữ trên ảnh Trung gốc →
`brief.json` (tên, mô tả, phân loại, ghi chú Sếp). Luật viết đầy đủ ở skill `gdp-listing-plan`
(`prompts/design-plan-schema.md`, `prompts/ctr-playbook.md`); tóm tắt:

- Viết như người bán Việt nói với khách: ngắn, cụ thể, có số thật ("CHỊU LỰC 50KG", không "CHỊU LỰC TỐT"); tránh câu dịch
  từng chữ, tính từ rỗng ("CAO CẤP", "CỰC XỊN"), câu hai nghĩa.
- Tiêu đề bìa: chọn theo bậc thang — cam kết khử rủi ro thật ("BỂ VỠ 1 ĐỔI 1") → số gắn đúng nỗi lo → bằng chứng xã hội
  thật → tình huống dùng cụ thể. Không lấy tên sản phẩm làm tiêu đề.
- Theo luật chữ của shop (`ims.py kit show` → "luật chữ header / sub / badge") và giọng văn của shop. **Luật chữ của shop
  THẮNG gợi ý chung của skill** về số dòng / số từ của tiêu đề BÌA (vd GDP: 1 hàng, 6–8 từ; PHALEDO: ≤ 5 từ / hàng, ≤ 2 hàng).
  Ảnh mô tả / sản phẩm thì bám cấu trúc bản Trung (tiêu đề 2 dòng thì giữ 2 dòng).
- `*cụm từ*` trong chữ = nhấn bằng màu accent của shop (dùng ≤ 1 lần / ảnh). Accent có thể chìm vào nền (vd vàng GDP trên
  nền bếp sáng): QA báo riêng "cụm nhấn … chìm vào nền" → bỏ dấu `*`, hoặc tiêu đề `"style": "outline"` / `"plate"`.

Muốn Editor trên app cũng có bản chữ này (để nhân sự chỉnh tay về sau): đẩy design plan bằng skill `gdp-listing-plan`.

## Nhận diện shop — dùng chung với video studio

`assets/shops/<shop>/` (mã shop = `marketing_shop.name` trên app):

| Nguồn | Chứa gì | Ai sửa |
|---|---|---|
| `shop.json` | bảng màu, font, logo sẵn có, giọng văn (hồ sơ chung với video) | Sếp / Claude |
| `image/kit.json` + `image/logo.*` + `image/watermark.*` | brand kit lấy từ app (Shop Manager): kiểu bìa, màu tiêu đề, nhãn, logo + watermark nhân sự đang dùng | **không sửa tay** — `ims.py kit sync` |
| `shop.json` mục `"image"` | tinh chỉnh riêng cho ảnh (THẮNG kit app): `colors` / `badge` / `ink` (ghi đè màu khi kit lệch ảnh thật), `heading_gradient` (false = chữ tiêu đề một màu phẳng), `pill_shape`, `watermark_mode` (image · text), `fonts` (các bộ font được dùng), `edge` / `bolder` (viền nhẹ + đậm thêm cho tiêu đề), `tone`, `ink` (`auto` = mực hoà tông ảnh), `headline` (plain / outline / plate), `pill`, bật-tắt logo / watermark theo loại ảnh, `logo_placement`, `logo_width_pct`, `watermark_width_pct` | Claude theo ý Sếp |
| `image/_demo.jpg`, `image/_fonts.jpg` | ảnh mẫu mọi khối trên nền tối + sáng · ảnh so các bộ font (`ims.py kit demo`) — XEM trước khi làm shop lạ | tự sinh |

### Bộ font (Sếp chốt 11/11) — đa dạng nhưng trong khuôn của shop

Mỗi bộ font có `display` (chữ LỚN: tiêu đề, nhãn) + `body` (chữ thường). Shop khai các bộ ĐƯỢC DÙNG ở `shop.json → image.fonts`
(cái đầu = mặc định); layout chọn bộ khác cho cả ảnh (`"font": "poppins"` cấp ảnh) hoặc riêng một khối (`"font"` trong khối).
Ngoài danh sách của shop → bộ dựng từ chối.

| Bộ | Chữ lớn / chữ thường | Dùng |
|---|---|---|
| `utm-avo` | UTM Avo Bold / UTM Avo | ưu tiên cấp 1 cho mọi shop — tròn, hiện đại |
| `averta` | Averta ExtraBold / Averta Regular | **mặc định PHALEDO** |
| `helvetins` | UTM HelvetIns / UTM Avo | **mặc định chữ lớn GDP** — nén, rất đậm, kiểu bán hàng |
| `poppins` | Poppins ExtraBold / Poppins Regular | chữ lớn đậm đà — đổi gió cho tiêu đề |
| `young` | PS Young Regular / Averta | nét mảnh thanh — để thử cho tiêu đề PHALEDO |

Đang khai: `phaledo_official` = averta, utm-avo, poppins, young · `giadungplus_official` = helvetins, utm-avo, poppins ·
`lteng_vn`, `lteng_hcm` = utm-avo, poppins. Xem cùng một câu trên mọi bộ: `assets/shops/<shop>/image/_fonts.jpg`.
Cách dùng: cả BỘ ẢNH một listing giữ một bộ font chính (mặc định của shop); đổi bộ cho ảnh bìa hoặc một tiêu đề cần cá
tính khác — không trộn quá 2 bộ trong một ảnh. Thêm bộ mới: `FONT_SETS` trong `image-studio/imslib/kit.py`.

Tiêu đề mặc định **đậm thêm một chút + viền nhẹ màu tương phản** để chữ nổi khỏi ảnh (`image.bolder`, `image.edge`, đơn vị em).
Chỉnh riêng một khối: `"edge": "none" | "soft" | "bold"` (hoặc số em), `"bolder": 0.02`.

Đã cấu hình (11/11): `phaledo_official` (tối giản cao cấp: chữ kem, nhãn kính mờ, mực nâu hoà tông trên nền sáng, watermark
dải ngang), `giadungplus_official` (tông ĐEN / ĐỎ / TRẮNG đo từ ảnh thật của shop — xem bảng dưới),
`lteng_vn`, `lteng_hcm` (bảng dưới). Shop chưa có kit
(`phaledo`, các shop TikTok) tự mượn shop khai ở `templates_from`, không thì shop cùng brand.

### Tông màu GDP (Sếp chốt 12/11 — đo trên ảnh thật, `assets/shops/giadungplus_official/reference/`)

| Nền | Chữ | Nhãn |
|---|---|---|
| sáng | **đen `#000`** (tiêu đề đậm + dòng phụ thường), không viền dày | đỏ `#ce0000` chữ trắng (mặc định) · trắng chữ đỏ (`variant: "invert"`) |
| tối | **trắng** | đỏ chữ trắng · đen chữ trắng viền trắng (`variant: "dark"`, kiểu "DÁN KEO / BẮT VÍT") |
| nhấn | `*cụm*` = đỏ; dải đỏ chữ trắng = tiêu đề `style: "plate"` | nhãn chữ nhật bo góc NHẸ (không bo tròn) |

Một hàng nhãn nên phối 2 kiểu cho có nhịp: `"items": ["1 ĐỔI 1", {"text": "180 NGÀY", "variant": "invert"}]`. KHÔNG dùng vàng,
không viền chữ dày, không chữ đỏ cho cả đoạn văn. Watermark GDP = dải chữ "GIA DỤNG PLUS" trắng mờ vắt ngang sản phẩm.
Bài học: brand kit trên app của GDP (nhãn vàng chữ đỏ, chữ đỏ trên nền sáng) lệch ảnh thật → khi Sếp chê màu, **đo màu trên ảnh
thật của shop** rồi ghi đè ở `shop.json → image` (`colors`, `badge`, `ink`, `pill_shape`, `edge`, `watermark_mode`), không sửa `kit.json`.

### Kiểu chữ LTENG (12/11 — đo trên ảnh nhân sự đã làm, `assets/shops/lteng_vn|lteng_hcm/reference/`)

| Shop | Kiểu tiêu đề chính | Kiểu thứ hai | Nhãn · logo · watermark |
|---|---|---|---|
| `lteng_vn` | **TẤM navy bo góc, chữ trắng**, dòng phụ nằm chung tấm: tiêu đề có `note` + `"bg": {"fill": "brand"}` — thường ở đáy ảnh | chữ navy `#002850` viền trắng trên nền sáng (tiêu đề thường, không cần khai gì) | nhãn navy chữ trắng bo góc nhẹ · logo thẻ navy treo giữa mép trên · chữ LTENG mờ giữa sản phẩm |
| `lteng_hcm` — tông **ĐEN / TRẮNG / ĐỎ** (Sếp 12/11) | **DẢI đỏ phẳng `#a83030`, chữ trắng** (mặc định của shop — tiêu đề không khai `style` là ra dải) | **DẢI ĐEN chữ trắng**: `"style": "plate-dark"` — phối với dải đỏ tuỳ trường hợp (vd dải đen tên sản phẩm + dải đỏ điểm bán) | nhãn đỏ chữ trắng + nhãn ĐEN chữ trắng (`"variant": "dark"`); KHÔNG dùng nhãn trắng chữ đỏ · chữ thường nền sáng = đen · logo LTENG\|HCM góc trên-trái · chữ LTENG mờ giữa sản phẩm |

Ảnh sản phẩm LTENG thường KÍN khung (kệ chiếm gần hết ảnh): chữ đi ở đáy / góc dưới-phải, phủ lên khăn - đạo cụ, không phủ lên kệ.
`keep` chỉ bao kệ + móc. Mẫu: `image-studio/examples/layout-lteng-vn.json`, `layout-lteng-hcm.json`.

**Làm shop lạ / shop Sếp chưa duyệt tông:** trước khi dựng, `ims.py pull` MỘT listing shop đó đã làm xong rồi `ims.py sheet` để
xem ảnh nhân sự đã làm (cột giữa) → theo đúng kiểu đó, đo màu pixel nếu thấy lệch `kit show`. Brand kit trên app chỉ là điểm xuất phát.

Shop mới: `tools\init_shop.py <shop>` (hồ sơ) → `ims.py kit sync <shop> --listing <id bất kỳ của shop>` → `ims.py kit demo
<shop>` → xem ảnh mẫu, lệch thì chỉnh `shop.json → image`. Font của kit chưa có trong `assets/fonts/` → xin Sếp file font,
không lấy font khác thay.

## QA báo gì → sửa gì

| Thông báo | Sửa |
|---|---|
| `chữ đè lên vùng sản phẩm` | dời khối ra vùng trống (xem `grid`), giảm `size` / `w`; cố ý thì `"over": true` |
| `chữ khó đọc: tương phản …` | dời sang vùng nền đều màu; hoặc cho chữ nền riêng: tiêu đề `style` plate / plate-dark / outline, nhãn, `bg` ôm chữ. KHÔNG phủ màu lên ảnh; đừng ghi đè màu chữ trước khi thử các cách này |
| `chữ bị co …pt → …pt` | chữ dài quá khung: rút chữ, tăng `w`, hoặc cho thêm `lines` |
| `chữ xuống N dòng, cho phép M` | rút chữ / nới `w` / tăng `lines` |
| `chữ tràn ra ngoài ảnh`, `sát mép` | dời vào trong (lề an toàn 2,5% bề rộng), đổi `anchor` |
| `đè lên khối '…'` | tách hai khối ra (y khác nhau ≥ chiều cao chữ) |
| `chữ …pt quá nhỏ / nhỏ`, `dòng phụ …pt nhỏ` | mobile first: tăng `size` (chữ ≥ 26, dòng phụ ≥ 32) rồi tách 2 dòng (`\n`, `lines: 2`), hoặc rút gọn chữ cho vừa |
| `còn chữ Hán` | chưa Việt hoá hết → sửa `text` |
| `font shop thiếu chữ cái …` | dùng ký tự khác; đừng để Chrome mượn font |
| `cụm nhấn “…” chìm vào nền` | màu accent không đủ nổi ở chỗ đó: bỏ `*…*`, hoặc tiêu đề `style: outline` / `plate` |
| `chữ sát logo` | hạ `y` của khối xuống (khe ≥ 2% bề rộng); logo cao bao nhiêu xem `qa/<key>.json → blocks` (id `logo`) |
| `logo mờ trên nền này` | `"logo": {"file": "<tên file>"}` (bản sáng / đậm khác), hoặc dời logo sang góc nền đều màu |
| `tiêu đề bìa …pt` | tiêu đề bìa đang < 48pt: rút chữ để to lên. Khoảng đẹp 56–72pt; font nén (HelvetIns của GDP) 70–80pt — không có cảnh báo cận trên, tự nhìn |

Mức: **LỖI** = phải sửa (render trả mã lỗi, `push` từ chối) · **CẢNH BÁO** = nhìn bằng mắt rồi quyết · **GHI CHÚ** = thông tin.
Soát mắt nhiều ảnh mà muốn tiết kiệm: `..\.venv\Scripts\python.exe ..\vs.py look <ảnh…> -q "…"`.

## Nhiều listing / nhiều shop cùng lúc

Mỗi listing là một job độc lập (`jobs/listing-<id>/`, nhận diện tự theo shop của listing) → làm song song được:
mỗi listing giao một subagent chạy đủ bước 1–7 của skill này rồi trả về đường dẫn `sheet.jpg` + báo cáo QA; phiên chính
gom lại, soát mắt, trình Sếp, rồi mới push từng job. Không cho hai agent cùng sửa một `layout.json`; không chạy
`kit sync` / sửa `shop.json` trong lúc job khác của shop đó đang render.

## Sự cố

- `pull` báo 401 / 403: token PluSor hết hạn hoặc thiếu quyền `access_marketing_listing` → báo Sếp cấp lại.
- Ảnh trên app đã bị ghi đè bằng final (đã push) rồi pull lại: `clean/` cũ được GIỮ (không tải đè) — chỉ `pull --refresh`
  khi nhân sự upload lại ảnh sạch mới.
- Render báo không tải được font: kiểm `assets/fonts/<họ font>/`; xem `ims.py kit show`.
- Chrome chưa cài kênh `chrome` cho Playwright: cài Google Chrome (đang dùng `channel="chrome"`).
- Cần khối chưa có (hình khối đặc biệt): dùng khối `html` (xem `references/layout.md`) — vẫn phải dùng biến màu của shop
  (`var(--c-heading)`, `var(--badge-solid)`…), không ghi mã màu.
