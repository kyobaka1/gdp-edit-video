# Luồng giao việc + dữ liệu trên app PluSor (giadungplus.store) — đọc khi cần hiểu sâu

Mã server: repo `giadungplus` (máy Sếp: `\\wsl.localhost\ubuntu\var\www\giadungplus`), module `marketing/listing_flow/`
(`bot_api.py` = API cho bot, `services/work_service.py` = nghiệp vụ ảnh, `services/push_service.py` = đẩy Shopee,
`selectors.listing_scope` = phạm vi giao). MCP `gdp-bridge` (mã: `gdp_mcp_bridge/`) có `listing_get`, `listing_get_plan`,
`db_read` (chỉ đọc DB prod).

## Một listing gồm gì

- 7 phần: Tên · Mô tả (chữ) · Ảnh bìa (`cover`) · Ảnh sản phẩm (`product_image`) · Ảnh mô tả (`description_image`) · Video ·
  Ảnh phân loại (`variant_image`).
- Mỗi ảnh là một **ô** (`ShopeeListingItem`): `source` (ảnh nguồn Sếp chọn — thường là ảnh Trung) và `result` (ảnh kết quả).
  Trạng thái ô: `todo` Chưa làm → `submitted` Chờ duyệt → `approved` Đã duyệt / `needs_fix` Cần sửa.
- Nhân sự "tải hàng loạt" ảnh đã xoá chữ → server tạo các ô **chỉ có result** (không source), `submitted`, xếp theo thứ tự
  upload. Ô nguồn (chỉ có source) vẫn nằm đó ở `todo`. `ims.py pull` ghép ô kết quả ↔ ô nguồn cùng loại, cùng `position`.

## Phạm vi giao (listing Cải tiến)

`GET /marketing/listing/api/bot/listings/<id>/` → `listing_type` (`update` = Cải tiến) và `scope.sections[]`
(`kind`, `label`, `enabled`, `status_label`: "Cần cải tiến" / "Giữ nguyên"). Phần `enabled: false`:
server tự lấy ảnh đang có trên sàn làm kết quả + tự duyệt, và CHẶN upload vào phần đó ("Phần này không được giao").
Tên / mô tả "Giữ nguyên" = không đẩy trường đó lên Shopee → **không `push-content`** cho listing như vậy.

## Nộp ảnh

`POST /marketing/listing/api/bot/items/<item_id>/upload-result/` (multipart `file`, tuỳ chọn `note`) → `work_service.upload_result`:
ảnh mới thành `result` của ô, ô về `submitted`, **ảnh result cũ bị xoá khỏi kho** nếu không còn ô nào dùng (ảnh sạch nhân
sự upload sẽ mất trên server → giữ bản trong `jobs/<job>/clean/`). `ims.py push` gọi đúng endpoint này cho từng ô.
Quyền: token bot phải là admin hoặc người được giao listing.
Đẩy lên Shopee (`push_service`) là nút của Sếp trên app: lấy ảnh `result` của các ô đã thực thi (ưu tiên đã duyệt).

## Trang Ảnh phân loại `/marketing/variant-images/` (Variant Image Hub) — việc làm ảnh phân loại theo từng shop

Module `marketing/variant_image_hub/` — KHÁC listing: mỗi **ô việc** = một cặp (shop × phân loại Sapo), gom theo **lần giao**
(batch) cho một người; Sếp chọn ảnh nguồn lúc giao (luôn là một asset), nhân sự nộp ảnh → Sếp duyệt → ảnh vào bộ artwork của
shop → Sếp đặt mặc định / áp lên sàn. Ô `variant_image` của một listing là luồng riêng (`ims.py pull`), chỉ chung bộ artwork.

API bot (`variant_image_hub/bot_api.py`, cùng token `PLUSOR_TOKEN`; tài khoản bot cần quyền `variant_image_hub` và phải là
NGƯỜI ĐƯỢC GIAO của batch — admin làm thay được):

| Lệnh | Endpoint |
|---|---|
| `ims.py vpull [--shop S] [--q …] [--state …] [--all] [--list]` | `GET api/bot/queue/` — mặc định việc còn mở (cần làm / bản nháp / cần sửa) giao cho bot; `--all` = `scope=all` (chỉ admin) |
| `ims.py push <job> --yes [--draft] [--note …]` | `POST api/bot/items/<id>/upload-result/` — nộp + gửi duyệt (`submit=0` = nháp). Ảnh phải rộng > 700px |
| — | `GET api/bot/items/<id>/` (kèm trao đổi) · `POST api/bot/items/<id>/comment/` |

`source_url` là link ký sẵn sống 12 giờ → `vpull` tải ngay về `clean/<item_id>.*`. Ô có `output_group` (artwork gộp: nhiều
shop cùng brand dùng chung một ảnh) chỉ cần nộp một ô — `vpull` gom lại, ghi `peers` trong `job.json`. Ghi chú của Sếp:
`request_note` (riêng ô) + `batch_note` (cả lần giao) + `review_note` (lý do "Cần sửa") — đọc trong `brief.json` trước khi làm.
`vpull` báo `HTTP 404 … chưa có API bot` = bản app đang chạy chưa có `bot_api.py` → báo Sếp deploy.

## Tra Kiến thức sản phẩm để chứng thực (MCP `db_read`)

```sql
SELECT d.id, d.status, left(d.search_text, 2500) AS txt
FROM products_product_knowledge_document d
WHERE d.search_text ILIKE '%<SKU hoặc từ khoá tên sản phẩm>%' LIMIT 3;
```

`search_text` chứa: mô tả chung, khách phù hợp, điểm bán hàng, khác biệt theo phân loại (số móc, chiều dài…). SKU lấy từ
`brief.json → variants[].sku` (bỏ phần đuôi phân loại, vd `MOC-0445`). Không thấy tài liệu → chỉ dựa nguồn còn lại, và hỏi Sếp.

## Bài học từ listing 141 (GDP, thanh móc cốc hút — 12/11)

- Listing Cải tiến chỉ giao "Ảnh mô tả": bản pull đầu kéo cả bìa / ảnh sản phẩm / phân loại (ảnh đã có chữ Việt, đã duyệt)
  → đã sửa `pull` đọc `scope`.
- Ảnh mô tả kiểu "tiêu đề góc trên-trái + ảnh bo góc bên dưới": tiêu đề 2 dòng 56pt neo `top-left` tại x 5,5 / y ≈ 8 (ngay
  dưới logo treo giữa), dòng 2 nhấn đỏ. Thanh / ô nhãn màu có sẵn → chữ `text` + `"display": true`, `tone: "light"`.
- Khối không khai `w` nằm sát mép phải từng bị trình duyệt bó hẹp → chữ tự co (đã sửa trong bộ dựng).
- Mẫu: `image-studio/examples/layout-gdp-anh-mo-ta-listing-141.json`.
