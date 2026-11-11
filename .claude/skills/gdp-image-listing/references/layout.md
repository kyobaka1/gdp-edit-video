# `layout.json` — khai lớp phủ cho từng ảnh (`gdp_image_layout@1`)

Một job một file `image-studio/jobs/<job>/layout.json`. Toạ độ là **% của ảnh** (x theo bề rộng, y theo chiều cao, 0–100).
Cỡ chữ `size` là **pt**: 1pt = bề rộng ảnh / 1000 (ảnh rộng 1440px → 60pt = 86px) — cùng đơn vị với Editor trên app.

```jsonc
{
  "schema": "gdp_image_layout@1",
  "shop": "phaledo_official",
  "images": {
    "7440": {                                   // key = id item trên app (job `pull`) hoặc tên file (job `new`)
      "kind": "cover",                          // cover | product_image | description_image | variant_image
      "base": "clean/7440.jpg",                 // ảnh sạch làm nền — không đổi
      "keep": [[22, 35, 76, 78]],               // hộp bao sản phẩm [x0, y0, x1, y1] — chữ không được đè
      "logo": true,                             // mặc định theo shop; false = tắt; {"y": 2, "w": 18, "file": "kit"} = chỉnh
      "watermark": {"y": 80},                   // mặc định theo shop; false = tắt
      "blocks": [
        {"id": "headline", "type": "headline", "text": "BẢO HÀNH BỂ VỠ", "x": 50, "y": 17.5, "w": 90, "size": 68, "lines": 1},
        {"id": "cam-ket", "type": "pills", "items": ["1 ĐỔI 1", "180 NGÀY"], "x": 50, "y": 28, "size": 48, "gap": 44}
      ]
    }
  }
}
```

## Trường cấp ảnh

| Trường | Nghĩa |
|---|---|
| `font` | Bộ font cho cả ảnh (một tên trong `ims.py kit show` → "bộ font"). Không khai = bộ mặc định của shop |
| `keep` | Danh sách hộp `[x0, y0, x1, y1]` bao sản phẩm / chi tiết phải thấy. Chữ đè vào → QA báo LỖI. Watermark dạng biểu tượng tự đặt giữa hộp đầu tiên |
| ~~`scrims`~~ | ĐÃ BỎ (Sếp 12/11: không chỉnh màu ảnh — chỉ thêm chữ, logo). Khai `scrims` là bộ dựng từ chối |
| `panels` | Tấm nền tự do: `{"x", "y", "w", "h", "fill": "dark", "opacity": 0.55, "radius": 18, "glass": true}` (x, y = góc trên-trái; `"fill": "brand"` = màu nhãn của shop). Chỉ làm nền cho chữ — tấm phủ > 25% ảnh bị từ chối (không chỉnh màu ảnh). Muốn tấm ôm vừa chữ thì dùng `bg` của khối thay vì tự đo |
| `logo` | `true` / `false` / `{"x", "y", "w", "placement", "file"}`. `w` = bề rộng phần logo nhìn thấy (%). `file`: tên trong `ims.py kit show` (`kit`, `kit-ink`, `primary`, `on_dark`, `on_light`). Không khai = bộ dựng tự chọn bản rõ nhất trên nền thật |
| `watermark` | (shop dùng dải CHỮ như GDP: `{"y", "opacity", "size"}`, `y` = tâm dải, mặc định giữa `keep`) · `true` / `false` / dải ngang `{"y", "w", "opacity"}` (`y` = mép TRÊN của dải, mặc định 79; `w` 105) / biểu tượng `{"x", "y", "w", "opacity"}` (`x`, `y` = TÂM; mặc định tâm hộp `keep` đầu tiên — cố ý nằm trên sản phẩm; `w` mặc định theo shop, thường 24). `opacity` 0–1, số NHỎ = mờ hơn; mặc định xem `ims.py kit show` → "độ đục mặc định" (vd GDP 0.2, dải PHALEDO 1 vì file đã mờ sẵn). Watermark sáng trên nền sáng tự chuyển bản đậm mờ |

## Trường chung của mọi khối

| Trường | Nghĩa | Mặc định |
|---|---|---|
| `type` | loại khối (bảng dưới) | bắt buộc |
| `id` | tên khối — hiện trong QA và ảnh soát; đặt tên có nghĩa | `<type><số thứ tự>` |
| `x`, `y` | điểm neo (%) | bắt buộc (trừ `dim`) |
| `anchor` | điểm neo là góc / cạnh nào của khối: `center`, `top-left`, `top-center`, `top-right`, `center-left`, `center-right`, `bottom-left`, `bottom-center`, `bottom-right` | `center` |
| `w` | bề rộng khối (%) — chữ tự xuống dòng trong khung này; chữ dài hơn → tự co cỡ (QA cảnh báo nếu co > 14%) | vừa chữ |
| `size` | cỡ chữ (pt) | theo loại |
| `lines` | số dòng tối đa (1 = không xuống dòng) | headline 2, sub 1 |
| `align` | left / center / right | theo `anchor` |
| `tone` | `auto` (đo nền thật: nền tối → chữ sáng của shop, nền sáng → mực đậm) · `light` · `dark` | `auto` |
| `color` | ép màu bằng TÊN trong bảng màu shop: `heading`, `sub`, `ink`, `accent`, `primary`, `dark`, `on_dark`, `on_light` (ghi `#hex` được nhưng QA ghi chú) | theo `tone` |
| `bg` | nền lót ngay dưới khối: `true` hoặc `{"fill": "dark", "opacity": 0.6, "pad": 22, "radius": 18, "glass": true}`. `"fill": "brand"` = tấm ĐẶC màu nhãn của shop (giữ dải màu) — tấm tự ôm vừa chữ | không |
| `note` | dòng phụ nhỏ nằm CHUNG khối (dưới chữ chính; cỡ = nửa cỡ tiêu đề với `headline`, 0.78 với `text` / `callout`). Tiêu đề + `note` + `bg` = TẤM TIÊU ĐỀ (kiểu LTENG VN) | không |
| `font` | bộ font riêng cho khối này (trong danh sách của shop) — vd tiêu đề `poppins`, phần còn lại theo ảnh | theo ảnh |
| `edge` | viền nhẹ màu tương phản quanh TIÊU ĐỀ giúp chữ nổi khỏi ảnh: `none` · `soft` · `bold` hoặc số em (0.045 = nhẹ) | theo shop (`soft`) |
| `bolder` | làm tiêu đề đậm thêm (em, 0–0.03) | theo shop (0.012) |
| `caps` | in HOA | false |
| `bold` | chữ đậm (cho `text`, `sub`) | false |
| `display` | khối chữ thường (`text`, `callout`…) dùng FONT CHỮ LỚN của bộ font — vd HelvetIns nén của GDP để chữ vừa ô hẹp mà vẫn to | false |
| `over` | cố ý đặt lên vùng `keep` (không tính lỗi đè sản phẩm) | false |

Trong `text`: `\n` = xuống dòng · `*cụm từ*` = nhấn màu accent của shop.

## Các loại khối

| `type` | Dùng cho | Trường riêng | Cỡ gợi ý (pt) |
|---|---|---|---|
| `headline` | tiêu đề | `text`; `style`: `plain` · `outline` (viền tương phản đậm — nền rối) · `plate` (chữ trắng trên dải màu shop) · `plate-dark` (chữ trắng trên dải ĐEN) — mặc định theo shop | bìa 56–72 · sản phẩm / mô tả 48–68 |
| `sub` | dòng phụ dưới tiêu đề | `text` | 32–40 (dài → 2 dòng) |
| `text` | nhãn / chú thích tự do, chữ trong ô icon | `text`, `note` (dòng nhỏ bên dưới), `bold` | 26–32 |
| `pills` | hàng nhãn (cam kết, số liệu) | `items: ["…", {"text": "…", "variant": "invert"}]` (từng nhãn tự chọn kiểu), `gap` (pt), `dir: "col"` (xếp dọc), `variant`: `solid` (màu nhãn của shop) · `invert` (đảo: nền = màu chữ nhãn, chữ = màu nền nhãn) · `dark` (đen chữ trắng) · `glass` (kính mờ) · `line` (chỉ viền); `shape`: `round` · `square` (mặc định theo shop) | 40–50 (bìa) · 28–38 |
| `badge` | một nhãn đơn | `text` (còn lại như `pills`) | 28–40 |
| `callout` | chú thích có đường chỉ tới chi tiết sản phẩm | `text`, `note`, `to: [x, y]` (điểm được chỉ — thường nằm trong `keep`, chữ thì nằm ngoài) | 26–32 |
| `dim` | đường kích thước hai đầu chặn + con số ở giữa | `text: "12 cm"`, `from: [x, y]`, `to: [x, y]` (không cần x / y) | 26–30 |
| `spec` | bảng thông số | `title`, `rows: [["Chất liệu", "Thuỷ tinh borosilicate"], …]`, nên kèm `w` + `bg` | 26–30 |
| `list` | danh sách lợi ích / các bước | `items: ["…", {"text": "…", "note": "…"}]`, `marker`: `check` · `number` · `dot` | 26–30 |

**Mobile first:** cỡ trên là cho ảnh xem trên điện thoại (1pt ≈ 0,39px màn hình). QA báo LỖI khi chữ < 20pt, CẢNH BÁO khi
< 26pt (dòng phụ < 32pt). Không đủ chỗ cho cỡ đó → tách 2 dòng hoặc rút gọn chữ, đừng hạ cỡ.
| `html` | khối tự do khi chưa có loại phù hợp | `html: "<div class=\"tx\">…</div>"`, `css` — chữ PHẢI nằm trong phần tử class `tx` để QA đo được; màu dùng biến shop: `var(--c-heading)`, `var(--c-ink)`, `var(--c-accent)`, `var(--c-primary)`, `var(--badge-solid)`, `var(--badge-text)`; kích thước `calc(var(--u) * <pt>)` | — |

Xem mọi khối vẽ ra thế nào với shop đang làm: `assets/shops/<shop>/image/_demo.jpg` (`ims.py kit demo <shop>`).

## Ví dụ: ảnh mô tả 3:4 nền sáng (PHALEDO)

(Ví dụ để hiểu cách khai — toạ độ là của ĐÚNG ảnh này; ảnh khác phải tự đo bằng `grid` / `grid --zoom`.)

Bản Trung: tiêu đề 2 dòng + dòng phụ ở trên, biển tên nhỏ bên trái, 3 ô icon có chữ ở đáy. Ảnh sạch giữ lại 3 ô icon.

```json
{
  "kind": "description_image",
  "base": "clean/test-anh-mo-ta-3-4.jpg",
  "keep": [[32, 42, 69, 80]],
  "blocks": [
    {"id": "headline", "type": "headline", "text": "MỘT THÌA LÀ VỪA\nNGỌT NGÀO TRỌN VỊ", "x": 50, "y": 14.5, "w": 88, "size": 66, "lines": 2},
    {"id": "sub", "type": "sub", "text": "Hũ thuỷ tinh nắp gỗ keo\nthêm nét ấm cho gian bếp", "x": 50, "y": 25.4, "w": 80, "size": 37, "lines": 2},
    {"id": "ten-hu", "type": "badge", "text": "HŨ ĐỰNG ĐƯỜNG", "x": 25, "y": 34.2, "size": 37},
    {"id": "tile-1", "type": "text", "text": "Kín khí", "x": 29.9, "y": 95.0, "w": 12.8, "size": 27, "bold": true, "lines": 1},
    {"id": "tile-2", "type": "text", "text": "Kèm thìa", "x": 49.0, "y": 95.0, "w": 12.8, "size": 27, "bold": true, "lines": 1},
    {"id": "tile-3", "type": "text", "text": "An toàn", "x": 68.4, "y": 95.0, "w": 12.8, "size": 27, "bold": true, "lines": 1}
  ]
}
```

Nền sáng → bộ dựng tự chọn mực nâu đậm hoà tông ảnh, logo bản đậm, nhãn nền đậm chữ kem — ảnh giữ nguyên màu.
Mobile first: dòng phụ tách 2 dòng cỡ 37pt (bản một dòng chỉ vừa cỡ 27pt — quá nhỏ); chữ trong ô icon rút còn 2 từ để lên 27pt.

## Ví dụ: tấm tiêu đề ở đáy ảnh (LTENG VN) và dải + chữ viền ở góc (LTENG HCM)

```json
{"id": "tam-tieu-de", "type": "headline", "text": "KỆ 2 TẦNG GỌN ĐẸP", "note": "Đựng đồ tắm & treo khăn tiện lợi",
 "x": 50, "y": 96.5, "anchor": "bottom-center", "size": 62, "lines": 1, "bg": {"fill": "brand", "pad": 20, "radius": 20}}
```

```json
{"id": "ten", "type": "headline", "text": "KỆ DÁN TƯỜNG", "x": 96, "y": 86, "anchor": "bottom-right", "size": 50, "lines": 1, "style": "outline"},
{"id": "hook", "type": "headline", "text": "THÁO RỜI", "x": 96, "y": 97.6, "anchor": "bottom-right", "size": 60, "lines": 1}
```

Hai khối xếp chồng: chừa khe ≥ 1,5% chiều cao — dải nền (`plate`) và tấm `bg` cao hơn khung chữ, sát quá QA báo "đè lên khối".

## Mẹo bố cục

- Căn theo trục: tiêu đề, dòng phụ, hàng nhãn cùng `x` (thường 50) → gọn. Khoảng cách dọc giữa các khối ≈ 0,6–1 lần chiều cao chữ.
- Tiêu đề 1 dòng rộng khoảng 55–75% ảnh là đẹp; rộng hơn 90% là quá to, hẹp hơn 40% là quá nhỏ.
- Logo nằm trên cùng; chiều cao khác nhau theo shop và tỉ lệ ảnh (PHALEDO ≈ 7%, thẻ đỏ GDP ≈ 11% trên ảnh 1:1). Render một
  lần rồi đọc `qa/<key>.json → blocks` (id `logo`) để biết đáy logo; đỉnh tiêu đề cách đáy logo ≥ 2% bề rộng (QA cảnh báo
  "chữ sát logo"). Khung chữ QA đo không tính hết dấu thanh và viền chữ — chừa dư ~1%.
- Thứ bậc: hàng nhãn KHÔNG rộng hơn tiêu đề. Font nén (HelvetIns) làm tiêu đề hẹp lại → tăng cỡ tiêu đề (70–80) / giảm cỡ nhãn.
- Chữ tự co khi dài hơn `w` (QA chỉ cảnh báo khi co > 14%); cỡ thật sau co: `qa/<key>.json → blocks[].size_pt`.
- Nền vùng chữ loang (kệ bếp, cây, cửa sổ) → cho chữ nền riêng (dải `plate`, nhãn, `bg` ôm chữ) hoặc `style: outline`. Không phủ màu lên ảnh.
- Chữ trong ô icon: đo ô bằng `grid --zoom` (vạch 2%), đặt `x` giữa ô, `w` nhỏ hơn ô ~1%; ô hẹp thì RÚT CHỮ còn 1–2 từ để giữ
  cỡ ≥ 26pt, hoặc `"display": true` nếu bộ font của shop có chữ lớn dạng nén.
- Sau mỗi lần render, đọc `qa/<key>.json → blocks[].rect_pct` = `[x, y, rộng, cao]` (góc trên-trái + kích thước, %) của từng
  khối — khác `keep` là `[x0, y0, x1, y1]` (hai góc).
