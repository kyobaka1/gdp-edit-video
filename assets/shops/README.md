# Tài nguyên theo SHOP — chuẩn thư mục

Nhận diện đi theo **shop**, không theo brand: hai shop cùng brand có thể khác màu, logo, giọng văn
(vd `phaledo_official` nền tối viền vàng, còn `phaledo` chưa cấu hình riêng). Mã shop = `marketing_shop.name` trên prod.

```
assets/shops/<mã shop>/
├── shop.json        ← hồ sơ shop: brand, bảng màu, giọng văn, logo dùng ở đâu, intro/outro, nguồn trên prod
├── logo/            ← THẢ LOGO VÀO ĐÂY (PNG nền trong suốt; SVG nếu có)
│   ├── logo.png         logo chính (màu gốc)
│   ├── logo-white.png   bản trắng — đặt trên nền tối / video tối
│   ├── logo-dark.png    bản đen/đậm — đặt trên nền sáng
│   ├── icon.png         biểu tượng vuông (avatar, góc video)
│   └── logo.svg         (tuỳ chọn) bản vector
├── intro/intro.mp4  ← (tuỳ chọn) đoạn mở đầu ≤ 3 giây, dọc 9:16 (1080×1920), có/không tiếng
├── outro/outro.mp4  ← (tuỳ chọn) màn kết: logo + lời kêu gọi mua, ≤ 4 giây, 9:16
├── templates/       ← MẪU CHỮ ĐÈ (HTML) — hợp đồng bên dưới; shop dùng chung mẫu thì khai `templates_from`
├── music/           ← nhạc nền đã duyệt bản quyền cho shop (mp3/wav)
├── watermark/       ← watermark.png (nếu shop dùng)
├── motion/          ← (tuỳ chọn) animation RIÊNG shop này — animation chung theo brand ở assets/motion/
├── fonts/           ← font riêng của shop (nếu có; font chung ở assets/fonts/)
└── reference/       ← ảnh tham chiếu phong cách (mẫu font, ảnh bìa, bài đăng mẫu)
```

Animation thương hiệu (logo động, watermark động — Claude Design): thư viện `assets/motion/` dùng chung theo `brand`;
cách dùng RIÊNG từng shop khai trong `shop.json` → `motion` (luật AUTO, tag ưu tiên, override) + `watermark.motion`.
Chi tiết: `assets/motion/README.md`. `vs.py motion list --shop <mã>` = animation shop dùng được.

Thêm shop mới: `.\.venv\Scripts\python.exe tools\init_shop.py <mã shop>` → sửa `shop.json` → thả logo/mẫu.
Xem shop đã đủ đồ chưa: `vs.py shops`. Xem mẫu chữ của shop: `vs.py templates <mã shop>`.

## Bộ nhận diện Việt hoá V2 (`shop.json` mục `caps`) — 11/11

Chữ Việt động + badge lấp chữ Trung + khung dải đáy / đỉnh của shop khai MỘT lần ở `shop.json`:
`"caps": {"style": <Style Pack>, "skin": {…chữ…}, "plate": {…badge…}, "panel": {…khung dải…}}` — `studio/vcaps.py` và
`studio/clean.py` tự đọc; shop không khai thì theo `templates_from`. Bảng 4 shop + nghĩa từng khoá: skill
`gdp-video-localize` mục "Việt hoá V2". Ảnh demo: `_caps-preview.jpg`, `_caps-motion.jpg` (dựng bằng
`tools/caps_previews.py`, không render video). Màu lấy từ pixel logo của chính shop.

## Hợp đồng mẫu chữ HTML (`templates/`)

Claude (đạo diễn) CHỈ chọn mẫu có sẵn (`"template": "<slot>"` trong `edl.json`), không tự sáng tạo kiểu mới.
Thiết kế mẫu mới bằng Claude Design (hoặc bất kỳ đâu) → xuất **1 file HTML độc lập mỗi kiểu** → sửa cho đúng
hợp đồng (Claude Code sửa giúp được) → đặt vào `templates/` + khai trong `templates/manifest.json`.

- Phần tử gốc `id="label"`: kích thước do renderer đặt qua `--w` / `--h` (px): `width: var(--w); height: var(--h);
  box-sizing: border-box;`. Nền **đục 100%** (che kín chữ Trung bên dưới).
- Chữ chính `id="text"` chứa `{{text}}`; dòng phụ `id="sub"` chứa `{{sub}}` (renderer gỡ `#sub` khi không có).
- Cỡ chữ `font-size: var(--fs)`; renderer dò cỡ lớn nhất vừa khung trong `fs_min`…`fs_max` (% chiều cao `--h`, khai ở manifest).
- `body` nền trong suốt, không JS, không tài nguyên Internet. Font: `url("../../../fonts/<Họ font>/<file>")`
  (font chung, mỗi họ một thư mục con, vd `BeVietnamPro/BeVietnamPro-Bold.ttf`) hoặc `url("../fonts/<file>")`
  (font riêng của shop). Font tải lỗi → renderer dừng và báo (không lặng lẽ thay font khác). Font phải có đủ dấu tiếng Việt.
- Không tự xoay — renderer xoay theo góc chữ gốc. `"nowrap": true` trong manifest = luôn một dòng (mẫu xoay chéo).
- Khối nhấn `*...*` (29/10): màu khai `"highlight": {"bg", "fg"}` ở gốc manifest (mặc định cả shop) và/hoặc trong từng
  slot (mẫu nền khác màu, vd badge nền trắng). Chọn cặp tương phản với NỀN MẪU, không trùng màu nền. Mẫu không cần sửa
  CSS — renderer tự chèn kiểu `.hl` + bọc từng chữ (`.u`) khi hiện dần; đừng đặt CSS cho `#text span` trong mẫu.

```json
{ "slots": {
    "caption": {"file": "caption.html", "use": "phụ đề / câu ngắn ở đáy", "fs_min": 34, "fs_max": 60},
    "hook":    {"file": "hook.html", "use": "câu mở đầu, một dòng, có thể xoay", "fs_min": 30, "fs_max": 64, "nowrap": true}
} }
```
