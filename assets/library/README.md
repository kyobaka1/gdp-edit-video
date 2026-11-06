# Thư viện asset dùng chung — xây 1 lần, dùng nhiều lần (Sếp chốt 05/11/2026)

Ảnh, nền, miếng cắt dán, icon cho MỌI video (dựng quay sẵn, Việt hoá, animation thương hiệu). Tạo tốn công một lần,
dùng lâu dài cho nhiều trường hợp. **Không tạo mới cho từng video.**

```powershell
.\.venv\Scripts\python.exe vs.py lib find <từ…> [--kind canh|nen|cat-dan|icon] [--theme T]   # LUÔN tìm trước
.\.venv\Scripts\python.exe vs.py lib kit <bộ>            # tạo phần THIẾU của bộ + ảnh soát kits/<bộ>.jpg
.\.venv\Scripts\python.exe vs.py lib gen <chủ-đề>/<tên> --prompt "…" --kind canh [--alpha] [--size doc|vuong|ngang] --tag t
.\.venv\Scripts\python.exe vs.py lib import <file> <chủ-đề>/<tên> --prompt "…" --kind K [--engine chatgpt-web|photo]
.\.venv\Scripts\python.exe vs.py lib sheet <chủ-đề|bộ>
.\.venv\Scripts\python.exe vs.py edit add <job> lib:<chủ-đề>/<tên> --key g01   # dùng trong job dựng (ghi used_by)
```

## Cấu trúc

- `index.json` — danh mục: id `<chủ-đề>/<tên>` (chữ thường không dấu, nối `-`), loại, tag, prompt, máy tạo, bản phụ,
  bộ chứa nó, job đã dùng. `<chủ-đề>/<tên>.png` + `<tên>.json` (nguồn AI) + `<tên>_v2.png` (bản phụ nếu Codex ra 2).
- Loại: `canh` cảnh minh hoạ/bối cảnh có nền (làm cover, ảnh → clip 15s, `push` zoom đẩy) · `nen` nền/chất liệu phủ
  khung · `cat-dan` miếng cắt dán nền trong suốt · `icon` sticker/biểu tượng nền trong suốt.
- `kits/<bộ>.json` — **BỘ = đủ asset cho MỘT kiểu animation/hiệu ứng**: mục đích, mô tả chuyển động, tham số (chữ, ảnh,
  màu), phong cách chung (nối vào mọi prompt cho đồng bộ), danh sách asset + prompt. `motion_id` = animation đã nhập.

## Quy trình — mỗi lần hoàn thiện TRỌN một kiểu animation

1. Chọn kiểu hiệu ứng cần (vd thẻ cắt dán mở chương) → viết/đọc `kits/<bộ>.json`.
2. `vs.py lib kit <bộ>` → chỉ tạo cái còn thiếu (Codex song song 3, ~60s/ảnh) → soát `kits/<bộ>.jpg` (Claude xem,
   ảnh lỗi thì `vs.py lib gen <id> --prompt … --force`).
3. Dựng animation — **Claude tự làm hết, Sếp không phải làm gì** (Sếp 05/11): `library.export_web` ra
   `kits/<bộ>/assets/*.png` + `assets.js` → Claude viết HTML `setTime` cạnh đó (tham số chữ/ảnh/màu/seed qua query) →
   soát khung → `vs.py motion import … --role … --no-render` → khai `opaque`/`params`/`kit` → `vs.py motion render` →
   ghi `motion_id` vào `kits/<bộ>.json`. Mẫu đã xong: `kits/chuong-cat-dan/cat-dan-mo-chuong.html`.
4. Từ đó mọi video gọi animation đó với tham số mới (`c.graphic(...)` trong cut.py); không tạo ảnh nữa.

## Bộ đã có

| Bộ | Kiểu animation | motion id | Trạng thái |
|---|---|---|---|
| `chuong-cat-dan` | Theme `gdp_red` (giấy đỏ, mảng vàng, người/tay giấy, nhãn, băng keo…) | `cat-dan-mo-chuong` (cũ) · `scene-chapter-card` | ✅ 05/11 — 18 asset |
| `phaledo-dark` | Theme `phaledo_dark` (giấy than, ánh sáng khúc xạ) | `scene-chapter-card` | ✅ 05/11 — 2 asset |
| `phaledo-warm` | Theme `phaledo_warm` (giấy be, trang sổ tay, washi, lá khô, hạt cà phê, muỗng gỗ, gạch chân, ảnh nguyên liệu) | `scene-chapter-card` | ✅ 05/11 — 8 asset |

Bộ asset phục vụ THEME của Scene Library (`assets/scenes/`) — family mới dùng lại cùng bộ, chỉ thêm miếng còn thiếu.

## Máy tạo ảnh (thứ tự ưu tiên)

1. **Codex CLI local** (`studio/imagegen.py`, đăng nhập ChatGPT, không tốn API). Đo 05/11: ảnh 1024×1536 ~40–65s;
   nền trong suốt RGBA sạch; ảnh tham chiếu phong cách `--ref` được. Ảnh nằm ở `~/.codex/generated_images/<phiên>/`.
2. Codex hỏng / hết usage → **chatgpt.com trên Chrome** (đã đăng nhập): Claude soạn prompt, tạo, tải ảnh về rồi
   `vs.py lib import … --engine chatgpt-web`.

## Luật

- ⛔ Ảnh AI chỉ minh hoạ **bối cảnh / ý / chất liệu đồ hoạ**. Không vẽ sản phẩm đang bán thay ảnh thật, không làm bằng
  chứng (trước–sau, doanh thu, đánh giá), không chữ/logo thương hiệu người khác. QA job nhắc khi dùng ảnh AI làm cảnh.
- Không chép thiết kế của kênh khác (mẫu chỉ để học kỹ thuật) — prompt mô tả phong cách chung, không đưa khung hình
  video người khác làm ảnh tham chiếu.
- Tạo xong mà dùng được thì giữ; cần biến thể khác thì tạo tên mới, không ghi đè cái đang có job dùng (`used_by`).
