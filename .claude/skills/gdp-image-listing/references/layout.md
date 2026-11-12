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
| `logo` | `true` / `false` / `{"x", "y", "w", "placement", "file"}`. `w` = bề rộng phần logo nhìn thấy (%). `file`: tên trong `ims.py kit show` (`kit`, `kit-ink`, `primary`, `on_dark`, `on_light`). Không khai = bộ dựng tự chọn bản rõ nhất trên nền thật. **Logo linh hoạt:** không khai `x` / `placement` thì logo vướng chữ ở chỗ mặc định sẽ TỰ DỜI (giữa → trên-trái → trên-phải, tránh chữ rồi tránh `keep`); khai `x` hoặc `placement` = ghim, tắt tự dời |
| `watermark` | (shop dùng dải CHỮ như GDP: `{"y", "opacity", "size"}`, `y` = tâm dải, mặc định giữa `keep`) · `true` / `false` / dải ngang `{"y", "w", "opacity"}` (`y` = mép TRÊN của dải, mặc định 79; `w` 105) / biểu tượng `{"x", "y", "w", "opacity"}` (`x`, `y` = TÂM; mặc định tâm hộp `keep` đầu tiên — cố ý nằm trên sản phẩm; `w` mặc định theo shop, thường 24). `opacity` 0–1, số NHỎ = mờ hơn; mặc định xem `ims.py kit show` → "độ đục mặc định" (đã nhân hệ số làm mờ 0,6 của Sếp — vd LTENG 0.12, GDP ≈ 0.22, dải PHALEDO 0.6). Chỉ khai `opacity` khi cần MỜ HƠN nữa (sản phẩm trắng bị ám màu), không khai để làm rõ lên. Watermark sáng trên nền sáng tự chuyển bản đậm mờ |

**Ảnh bìa (`kind: cover`):** GÓC DƯỚI-TRÁI (x ≤ 42%, y ≥ 88%) là vùng khung Shopee che — khối chữ và logo không được chạm
góc này: đáy khối ≤ y 88% (`anchor: "bottom-…"` thì `y` ≤ 87.5), hoặc mép trái khối ≥ x 42%. Phía phải của dải đáy đặt chữ được. Hook lớn nhất nên có tâm trên y 62%. Lý do + số liệu: `references/cover-ctr.md`.

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
| `stat` | **CON SỐ TO** — nhãn nhỏ phía trên + số rất lớn, chung một tấm màu shop (bìa: "CHỊU LỰC / 30KG", "DUNG TÍCH / 9L") | `label`, `value`, `variant`: `solid` · `invert` · `dark`; `rule: true` = gạch mảnh ngăn nhãn với số; `even: true` = hai dòng CÙNG CỠ (vd `"label": "DÁN TƯỜNG", "value": "KHOAN VÍT", "even": true, "rule": true` — tấm 2 cách lắp có gạch ngăn, cỡ gợi ý 44–50); `foot` = dải chân MÀU KHÁC gắn liền đáy thẻ cho thông số phụ ("NHÔM DÀY 1.2MM"), `foot_note` = dòng nhỏ dưới nó; màu dải = `pop: {"bg", "text"}` khai ở cấp ảnh hoặc `shop.json → image.pop` (không khai = bản đảo của nhãn); `size` = cỡ của SỐ (nhãn tự bằng 0,4 lần) | 80–120 (bìa) |
| `badge` | một nhãn đơn | `text` (còn lại như `pills`) | 28–40 |
| `callout` | chú thích có đường chỉ tới chi tiết sản phẩm | `text`, `note`, `to: [x, y]` (điểm được chỉ — thường nằm trong `keep`, chữ thì nằm ngoài) | 26–32 |
| `dim` | đường kích thước hai đầu chặn + con số ở giữa | `text: "12 cm"`, `from: [x, y]`, `to: [x, y]` (không cần x / y) | 26–30 |
| `spec` | bảng thông số | `title`, `rows: [["Chất liệu", "Thuỷ tinh borosilicate"], …]`, nên kèm `w` + `bg` | 26–30 |
| `list` | danh sách lợi ích / các bước | `items: ["…", {"text": "…", "note": "…"}]`, `marker`: `check` · `number` · `dot`, `start` (số đầu tiên khi `number` — chia 2 cột vẫn đánh số liền) | 26–30 |

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

## Ví dụ: ảnh bìa đối đầu đối thủ (LTENG VN, kệ nhôm 0744 — ảnh nền kín sản phẩm)

Đối thủ ghi "KỆ NHÔM · DÁN TƯỜNG 20KG" rất to ở đáy-trái. Bìa mình: keyword 2 dòng trên tấm navy ở khoảng trống trên-phải, con
số 30KG phóng to nhất bìa ở khoảng trống dưới-trái, đáy thẻ số dừng TRÊN vùng khung Shopee (thẻ nằm bên trái nên đáy ≤ y 88%).

```json
{"kind": "cover", "base": "clean/0744-lteng-vn.jpg",
 "keep": [[5, 12, 30, 53], [30, 13, 42, 64], [42, 17, 52, 73], [52, 22, 66, 85], [66, 29.5, 82, 86], [82, 34, 100, 88]],
 "blocks": [
  {"id": "tu-khoa", "type": "headline", "text": "KỆ NHÔM\nDÁN TƯỜNG", "x": 96.5, "y": 2.7, "anchor": "top-right", "align": "center",
   "size": 72, "lines": 2, "bg": {"fill": "brand", "pad": 12, "radius": 14}},
  {"id": "so", "type": "stat", "label": "CHỊU LỰC", "value": "30KG", "rule": true, "font": "poppins",
   "x": 3.2, "y": 84.6, "anchor": "bottom-left", "size": 110}]}
```

Sản phẩm nằm CHÉO → khai `keep` bằng nhiều hộp bậc thang bám theo mép sản phẩm (một hộp bao trọn sẽ phủ cả khoảng trống).
Chữ nhiều dòng trong một tấm → `"align": "center"` (khối neo phải mặc định căn phải, hai dòng lệch nhau trông vụng — Sếp 12/11).
Mẫu đầy đủ: `image-studio/examples/layout-lteng-vn-bia-0744.json` (bản đề xuất + các biến thể đã so: 2 nhãn, có / không gạch, phối font).

## Ảnh phân loại — `variant_set` (cấp job) + `variant` (từng ảnh)

Luật + quy trình: SKILL.md mục "Ảnh phân loại". Một sản phẩm = một job = một `variant_set`.

```jsonc
{
  "shop": "lteng_vn",
  "variant_set": {                      // THIẾT KẾ CHUNG của cả bộ phân loại
    "style": "bottom",                  // bottom = khung bên dưới · right / left = khung bên cạnh · fill = ảnh đã có khung (xem dưới)
    "panel": 20,                        // % cạnh ảnh dành cho khung — bottom 14–20 (mặc định 20) · right / left 24–32 (mặc định 30)
    // 3 dòng dưới KHÔNG cần khai khi shop đã chốt ở shop.json → image.variant (vd lteng_vn) — khai ở đây là ghi đè cho riêng job
    "tone": "brand",                    // brand = tấm màu nhãn shop, chữ sáng · invert = tấm sáng chữ màu shop · dark = tấm đen
    "name_font": "poppins",             // bộ font cho TÊN phân loại + con số bảo hành (trong danh sách của shop); `font` = phần còn lại
    "sub_style": "box",                 // ô kiểu: box · plain · pop
    "chips": ["NHÔM KHÔNG GỈ", "BẢN DÀY 1.2MM"],
    "included": {"items": ["keo-dan", "oc-vit", "mieng-dan"], "label": "KEO - ỐC VÍT
ĐI KÈM"},   // ≤ 2 món: nhãn tự ghép; từ 3 món BẮT BUỘC khai `label`; `title` = dòng trên ảnh
    "warranty": {"label": "BẢO HÀNH", "value": "10", "unit": "NĂM"}
  },
  "images": {
    "50cm-thanh-treo": {
      "kind": "variant_image", "base": "clean/50cm-thanh-treo.jpg",
      "keep": [[12, 15, 90, 62]],                                         // % của ẢNH NGUỒN — sản phẩm + số đo, không gồm đạo cụ
      "variant": {"name": "50CM", "sub": "THANH TREO + MÓC"}             // điểm phân biệt; thêm "zoom" / "focus" nếu cần
    }
  }
}
```

| Trường | Nghĩa |
|---|---|
| `size` | cạnh ảnh ra (px), mặc định 1000 (app cần > 700) |
| `variant.name` | số + đơn vị ("50CM", "1.2L", "3 TẦNG") → tự dựng số to, đơn vị nhỏ; chữ thường ("XÁM", "TRẮNG KEM") giữ nguyên |
| `variant.sub` | chữ trong ô kiểu; một dòng nếu vừa (≤ ~16 ký tự ở khung dưới, ~12 ở khung bên cạnh), dài hơn tự chia 2 dòng cân nhau (ưu tiên ngắt trước `+`); `\n` = tự ngắt. Bộ có một phân loại 2 dòng thì MỌI ô kiểu cao bằng nhau |
| `sub_style` | `box` (mặc định — hộp sáng viền mảnh) · `plain` (chữ trơn, tên to thêm một chút) · `pop` (thẻ màu nhấn phụ — tranh chú ý với bảo hành, tránh dùng) |
| `included.items` | 1–3 món. Mã `keo-dan` · `oc-vit` (vít nở) · `mieng-dan` · `coc-hut` (ảnh ở `image-studio/asset/` hoặc `assets/shops/<shop>/image/install/`), hoặc `{"img": "assets/phu-kien.png", "label": "5 MÓC"}` = ảnh riêng nằm trong job |
| `sizes` | ghi đè cỡ chữ mong muốn (pt): `{"name", "sub", "chip", "inc", "war"}` — bộ dựng vẫn tự co cho vừa ô |
| `variant.zoom` / `variant.focus` | phóng ảnh nguồn thêm (1–1.4) / điểm của ảnh nguồn (%) đặt vào giữa vùng ảnh — không khai = tự căn theo `keep` |
| `logo`, `watermark` (ở ảnh) | như ảnh thường; khung bên cạnh thì logo tự treo giữa VÙNG ẢNH |

Ảnh ra: khung vuông; ảnh nguồn chỉ được đặt / cắt vào vùng còn lại (không đổi màu). Ảnh nguồn vuông + `bottom`: phần đáy ảnh
nằm dưới khung — sản phẩm phải nằm trong 80% phía trên (bộ dựng tự dịch ảnh lên nếu được).

**Ảnh nguồn đã có khung mô tả → `style: "fill"`**: khai MỘT bộ khối mẫu cho cả bộ, chữ viết `{name}` / `{sub}` / `{khoá bất kỳ
trong variant}`; toạ độ đo bằng `grid --zoom` trên ảnh nguồn (mọi phân loại cùng khung nên cùng toạ độ). Ảnh ra giữ kích thước nguồn.

```json
"variant_set": {"style": "fill", "blocks": [
  {"id": "ten", "type": "text", "text": "{name}", "x": 15.6, "y": 9.5, "w": 26, "size": 62, "display": true, "lines": 1},
  {"id": "kieu", "type": "text", "text": "{sub}", "x": 15.6, "y": 19, "w": 26, "size": 34, "bold": true, "lines": 1},
  {"id": "o-1", "type": "text", "text": "Dán không khoan", "x": 15.6, "y": 41.5, "w": 24, "size": 28, "bold": true, "lines": 1}]}
```

## Mẹo bố cục

- Căn theo trục: tiêu đề, dòng phụ, hàng nhãn cùng `x` (thường 50) → gọn. Khoảng cách dọc giữa các khối ≈ 0,6–1 lần chiều cao chữ.
- Tiêu đề 1 dòng rộng khoảng 55–75% ảnh là đẹp; rộng hơn 90% là quá to, hẹp hơn 40% là quá nhỏ.
- Logo nằm trên cùng; chiều cao khác nhau theo shop và tỉ lệ ảnh (PHALEDO ≈ 7%, thẻ đỏ GDP ≈ 11% trên ảnh 1:1). Đặt chữ
  theo bố cục bản Trung trước — logo tự nhường chỗ (Sếp 12/11: logo linh hoạt theo chữ, không bóp chữ cho né logo). Chỉ khi
  QA còn báo "chữ sát logo" (cả 3 chỗ trên mép trên đều vướng) mới đọc `qa/<key>.json → blocks` (id `logo`) để biết đáy logo
  rồi hạ chữ: đỉnh tiêu đề cách đáy logo ≥ 2% bề rộng. Khung chữ QA đo không tính hết dấu thanh và viền chữ — chừa dư ~1%.
- Thứ bậc: hàng nhãn KHÔNG rộng hơn tiêu đề. Font nén (HelvetIns) làm tiêu đề hẹp lại → tăng cỡ tiêu đề (70–80) / giảm cỡ nhãn.
- Chữ tự co khi dài hơn `w` (QA chỉ cảnh báo khi co > 14%); cỡ thật sau co: `qa/<key>.json → blocks[].size_pt`.
- Nền vùng chữ loang (kệ bếp, cây, cửa sổ) → cho chữ nền riêng (dải `plate`, nhãn, `bg` ôm chữ) hoặc `style: outline`. Không phủ màu lên ảnh.
- Chữ trong ô icon: đo ô bằng `grid --zoom` (vạch 2%), đặt `x` giữa ô, `w` nhỏ hơn ô ~1%; ô hẹp thì RÚT CHỮ còn 1–2 từ để giữ
  cỡ ≥ 26pt, hoặc `"display": true` nếu bộ font của shop có chữ lớn dạng nén.
- Sau mỗi lần render, đọc `qa/<key>.json → blocks[].rect_pct` = `[x, y, rộng, cao]` (góc trên-trái + kích thước, %) của từng
  khối — khác `keep` là `[x0, y0, x1, y1]` (hai góc).
