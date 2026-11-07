# Đánh giá hiệu quả video studio đăng lên listing Shopee

Câu hỏi của Sếp: video sản phẩm đã edit (studio này) đăng lên listing Shopee có (1) tăng traffic / khởi động lại
sản phẩm, (2) tăng tỉ lệ chuyển đổi không? Lần đo 1: 26/10/2026. Lần đo 2: hẹn 04/11/2026 (scheduled task
`do-lai-hieu-qua-video-shopee`).

## Kết quả lần 1 (số liệu tới 25/10, mới 3–5 ngày sau đăng)

- 29 listing có video mới (GDP 9, LTENG HCM 11, LTENG VN 9); Phaledo Official + Phaledo **0**. Đo được 26 (3 listing đăng 25/10).
- So với 91 listing cùng ngành (nhà tắm/móc/kệ) không đổi video, trước 12–19/10, sau 22–25/10:
  UV +18%, đơn +32%, **CR (đơn/UV) +12%**, ATC/UV +6%, CTR −6%.
- Traffic KHÔNG bền: bỏ 2 listing top (GDP 25075915554, 42379971521) → UV −3% (bỏ thêm 25/10 → −11%);
  đổi cửa sổ sau 21–24/10 → +4%; placebo 12–15 vs 16–19 nhóm video đã kém đối chứng −9% (hồi quy về trung bình).
  Listing nhỏ (<20 UV/ngày) UV −12% → KHÔNG khởi động lại.
- CR +8%…+14% ở mọi biến thể nhưng z≈1,7 (chưa đủ 95%); cùng SKU kệ nhà tắm 5 listing có video vs 4 listing anh em
  không video: UV −4%, CR +1%.
- Nhiễu đã loại: Flash Sale DỪNG từ sau 10/10 (10.10 siêu sale, 11/10 còn dư âm) → cửa sổ trước bắt đầu 12/10;
  đổi tên hàng loạt 13/10; sửa hàng loạt 19/10 13:10; giá 24519926142 tăng từ 16/10, 44422762378 tăng 19–20/10;
  3 thùng rác Besan nhỏ tăng ads 3–10× (không phải video).

## Phương pháp (làm lại y hệt)

### 1. Xác định listing có video mới + giờ đăng (DB KHÔNG lưu video)
- Gợi ý ứng viên: modify_time trong snapshot hằng giờ, bỏ mốc hàng loạt (19/10 13:09–13:11):
  ```sql
  select shop_name, item_id, string_agg(to_char(to_timestamp(mt) at time zone 'Asia/Ho_Chi_Minh','MMDD HH24:MI'), ';' order by mt) mts
  from (select distinct shop_name, item_id, (raw_payload_json->>'modify_time')::bigint mt
        from marketing_shopeempskuproductsnapshot where captured_at >= '2026-10-14') x
  where to_timestamp(mt) >= '2026-10-20' group by 1,2
  ```
- Xác nhận bằng Shopee (Claude in Chrome, tab của Sếp):
  - Shop đang login Seller Centre (thường giadungplus_official): trong tab `banhang.shopee.vn`
    `fetch('/api/v3/product/get_product_info?product_id=<item>&is_draft=false')` → `data.product_info.video_list[].vid/duration`.
  - Mọi shop: trong tab `shopee.vn` `fetch('/api/v4/pdp/get_pc?item_id=<item>&shop_id=<seller_shop_id>')`
    → `data.product_images.video.mms_data` (chuỗi JSON) → `create_time` = giờ upload chính xác.
    shop_id: GDP 241961702 · lteng_vn 1612223456 · lteng_hcm 1638634407 · phaledo_official 1009027554 · phaledo 15064699.
  - ⚠️ PDP: TUẦN TỰ, cách nhau ≥3,5 giây, mỗi lần gọi ≤9 item. Gọi 3 song song/0,4s đã bị Shopee chặn
    (`shopee.vn/verify/traffic/error`) ngày 26/10. Chỉ kiểm ứng viên, không quét cả shop.
  - Video mới = `create_time` ≥ 20/10/2026. Thời lượng Shopee = thời lượng final studio + ~4s outro.
- Danh sách đã xác nhận lần 1: biến `TREATED` trong `analyze.py`.

### 2. Kéo số liệu prod (bridge `db_read`, kết quả lớn tự lưu file → chép vào thư mục data mới)
- Hiệu quả listing × ngày (đổi khoảng ngày):
  ```sql
  select shop_name, item_id, max(product_name) name, string_agg(to_char(report_date,'MMDD')||','||coalesce(product_card_impressions,0)||','||coalesce(product_card_clicks,0)||','||coalesce(uv,0)||','||coalesce(add_to_cart_buyers,0)||','||coalesce(placed_orders,0)||','||coalesce(placed_units,0)||','||coalesce(placed_sales,0)||','||coalesce(confirmed_orders,0), ';' order by report_date) d
  from marketing_shopeeproductdailyperformance
  where report_date between '2026-09-14' and '<ngày cuối>' and connection_id in (159755,155938,159753,155687,134366) group by 1,2
  ```
  → `perf.json`
- Ads theo item × ngày → `ads.json`:
  ```sql
  select connection_id, shopee_item_id::text item_id, string_agg(to_char(report_date,'MMDD')||','||cost||','||impression||','||click||','||broad_order, ';' order by report_date) d
  from (select connection_id, shopee_item_id, report_date, sum(cost) cost, sum(impression) impression, sum(click) click, sum(broad_order) broad_order
        from finance_shopeeadscampaignitemdailyreport where report_date between '2026-09-14' and '<ngày cuối>'
        and connection_id in (159755,155938,159753,155687,134366) group by 1,2,3) x group by 1,2
  ```
- `oldsnap.json` (video tháng 5–7) dùng lại bản trong `data-20261026/`.
- Kiểm Flash Sale có chạy lại không (nếu có → loại ngày FS khỏi cửa sổ hoặc ghi rõ nhiễu):
  `select (start_at at time zone 'Asia/Ho_Chi_Minh')::date d, count(*), sum(item_count) from marketing_flash_sale_sapo_mirror where start_at >= '2026-10-11' and removed_from_remote_at is null group by 1 order by 1`
- Kiểm đổi giá/tên: `marketing_shopeeproductchangeevent` (changed_at ≥ 20/10) + `selling_price_min` theo ngày trong `marketing_shopeempskuproductsnapshot`.

### 3. Chạy phân tích
Script đọc file theo đường dẫn tương đối → chép 4 file `.py` vào thư mục data mới rồi chạy ở đó bằng
`C:\Users\Admin\gdp-video-studio\.venv\Scripts\python.exe -I final.py` (và `robust.py`). Cần sửa trước khi chạy:
- `analyze.py`: `LAST` = ngày cuối có số liệu; thêm listing mới (kể cả Phaledo) vào `TREATED`.
- `final.py`: `POST` = (22/10, LAST), `npost` = số ngày; giữ `PRE` = 12–19/10; thêm `phaledo_official`, `phaledo`
  vào `SHOPS` nếu có listing Phaledo. Listing đăng muộn (≥22/10) phải có cửa sổ riêng: trước = 14 ngày liền trước
  (không dính FS), sau = từ ngày kế tiếp ngày đăng.
- `robust.py`: cửa sổ trong các dòng `did(...)` theo LAST.

### 4. Tiêu chí kết luận
- Traffic: chỉ nói "có tác dụng" khi chênh lệch UV so với đối chứng cùng ngành vẫn dương sau khi bỏ 2 listing top
  VÀ dương ở họ sản phẩm (listing có video vs listing anh em không video).
- Chuyển đổi: z ≥ 2 cho CR nhóm video VÀ chênh lệch CR so với đối chứng dương ở mọi biến thể.
- Khởi động lại: nhóm listing <20 UV/ngày phải tăng UV rõ so với đối chứng.
