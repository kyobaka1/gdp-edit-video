# Ảnh phụ kiện LẮP ĐẶT — dùng cho ô "ĐÃ GỒM" của ảnh phân loại (Image Studio)

Sếp cung cấp ảnh PNG **nền trong suốt** (lề thừa không sao — bộ dựng tự cắt sát vật). Đặt đúng tên:

| File | Là gì | Mã trong `layout.json → variant_set.included.items` |
|---|---|---|
| `keo-dan.png` | tuýp keo dán | `keo-dan` (viết tắt `keo`) |
| `oc-vit.png` | vít + tắc kê nở | `oc-vit` (`vit`, `vit-no`) |
| `mieng-dan.png` | miếng dán | `mieng-dan` |
| `coc-hut.png` | cốc hút (chưa có) | `coc-hut` |

Shop dùng phụ kiện khác hình → đặt bản riêng ở `assets/shops/<shop>/image/install/<mã>.png` (thắng bản chung).
Chưa có file → bộ dựng vẽ HÌNH TẠM và cảnh báo; ảnh còn hình tạm không được nộp.
Luật: skill `gdp-image-listing` → mục "Ảnh phân loại".
