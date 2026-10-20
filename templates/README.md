# Thư viện mẫu chữ đè theo brand — HỢP ĐỒNG HTML

Mỗi brand một thư mục `templates/<brand>/` (chữ thường, vd `phaledo`), gồm `manifest.json` + các file `.html`.
Claude (đạo diễn) CHỈ chọn mẫu có sẵn cho từng ô (`"template": "<slot>"` trong `edl.json`), không tự sáng tạo.

## Thiết kế mẫu mới bằng Claude Design

1. Thiết kế trong Claude Design (hoặc bất kỳ đâu) một khung chữ — xuất **1 file HTML độc lập** cho mỗi kiểu.
2. Sửa cho đúng hợp đồng dưới đây (Claude Code sửa giúp được), đặt vào `templates/<brand>/<slot>.html`.
3. Khai báo trong `manifest.json`. Chạy `vs.py templates <brand>` để xem bảng mẫu (`templates/<brand>/_preview.png`).

## Hợp đồng (renderer dựa vào đúng mấy điểm này)

- Phần tử gốc `id="label"`: kích thước **do renderer đặt** qua biến CSS `--w` / `--h` (px). Dùng
  `width: var(--w); height: var(--h); box-sizing: border-box;`. Nền phải **đục 100%** (che kín chữ Trung bên dưới).
- Chữ chính trong phần tử `id="text"`, nội dung là `{{text}}`. Có dòng phụ thì `id="sub"` với `{{sub}}`
  (renderer ẩn `#sub` khi không có).
- Cỡ chữ: dùng `font-size: var(--fs)`; renderer tự dò cỡ lớn nhất vừa khung trong khoảng
  `--fs-min`…`--fs-max` (khai trong manifest, đơn vị = % chiều cao `--h`).
- `body` nền trong suốt (`background: transparent; margin: 0`). Không JS, không ảnh/font từ Internet —
  font để trong `assets/fonts/` và gọi bằng đường dẫn tương đối `../../assets/fonts/...`.
- Không tự xoay: renderer xoay PNG theo góc chữ gốc (`angle` trong edl).

- Tuỳ chọn manifest `"nowrap": true`: chữ luôn MỘT dòng (cỡ chữ tự co) — dùng cho mẫu xoay chéo / tiêu đề.

## manifest.json

```json
{
  "brand": "PHALEDO",
  "slots": {
    "caption": {"file": "caption.html", "use": "phụ đề / câu ngắn ở đáy", "fs_min": 30, "fs_max": 62},
    "hook":    {"file": "hook.html",    "use": "câu mở đầu lớn, có thể xoay", "fs_min": 34, "fs_max": 66}
  }
}
```
