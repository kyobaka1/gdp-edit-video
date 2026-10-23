---
name: gdp-video-motion
description: Thư viện animation thương hiệu (Motion Identity) của GDP Video Studio (C:\Users\Admin\gdp-video-studio) — nhập animation Sếp thiết kế bằng Claude Design (HTML có setTime / chuỗi PNG / video alpha) vào thư viện, render một lần ra clip ALPHA ProRes 4444 (cache), kiểm alpha, chọn animation cho job (AUTO theo shop / MANUAL), brand reveal thay logo tĩnh, watermark động thay watermark chữ. Dùng khi Sếp nói "thêm animation mới", "tải animation từ Claude Design về dùng", "import motion", "logo động", "watermark động", "chèn animation logo vào video", "đổi animation của shop", "animation nào shop X dùng được", "render alpha / xuất mov trong suốt", hoặc khi dựng/Việt hoá video cần chèn nhận diện động. Việt hoá video tiếng Trung → skill gdp-video-localize (skill đó gọi sang đây phần animation).
---

# GDP Video Motion — animation thương hiệu (Claude Code / Codex)

Studio `C:\Users\Admin\gdp-video-studio`. Chạy lệnh bằng PowerShell:

```powershell
Set-Location C:\Users\Admin\gdp-video-studio; $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe vs.py motion <việc> …
```

Hợp đồng đầy đủ (motion.json, shop.json, edl.motion, luật xung đột): **`assets/motion/README.md`** — đọc khi cần chi tiết.
Code: `studio/motionlib.py` (thư viện, render alpha, kiểm, cache) · `studio/motiondirector.py` (chọn + đặt + xung đột,
filter ffmpeg, QA) · nối vào `render.py` / `watermark.py`. **Nguồn skill = `studio\.claude\skills\gdp-video-motion\`**
→ sửa xong chạy `tools\sync_skill.py install` (cài cho Claude + Codex).

## Luật Sếp chốt (23/10 — Motion Director V2)

1. **3 hệ thống phối hợp, không triệt tiêu nhau**: brand reveal (điểm nhấn ngắn) · logo THƯỜNG TRỰC ở góc (luôn nhận ra
   thương hiệu) · watermark động (mờ, chống sao chép). ⛔ KHÔNG tắt logo cả video vì có reveal (lỗi bản V1): logo chỉ TẠM ẨN
   trong KHOẢNG animation `replaces: ["logo"]` chạy, mờ ra 0,25s / hiện lại trong 0,3s cuối (chuyển giao), rồi duy trì tới
   hết video chính (không đè outro). Reveal giữa video → logo có từ đầu, ẩn đúng đoạn, hiện lại.
2. **Watermark chữ → animation** của shop (`shop.json.watermark.motion`): XUẤT HIỆN → CHÌM DẦN → ĐỔI CHỖ như cũ (trượt êm
   mỗi `watermark.period` ~6s, CHỈ bắt đầu sau khi đã chìm xong — Sếp 23/10 giữ kiểu này) → mờ hẳn trước outro. Tuỳ chọn
   `lifecycle.relocate_mode: "fade"` (đứng lâu rồi mờ ra/hiện lại) hoặc `relocate: false`. Không bao giờ 2 watermark; xa logo góc.
2b. **Nhỏ, gọn, sát mép trên**: logo thường trực GDP 15% · LTENG 18–19% · PHALEDO 20% bề rộng (khung 3:4; theo tỉ lệ khung,
   đo phần logo thấy được), lề trên 3% chiều cao. Reveal ~26–36% bề rộng ở dải trên, chuyển động gói trong vùng gần neo.
3. Thư viện mở: thêm/sửa/bỏ animation **không sửa Python**. ⛔ Không cứng tên brand / tên animation / tên file trong code.
4. Animation thuộc BRAND; mỗi shop có cấu hình RIÊNG cách dùng (`shop.json.motion`). Không chép file animation thành nhiều
   bản cho shop cùng brand — chỉ khác cấu hình (LTENG VN / HCM dùng chung thư viện LTENG).
5. Không đè outro, không đè ô chữ (≤4%), không đổi kịch bản / thuyết minh / thông tin sản phẩm để chiều animation.
6. Không gọi AI để render hay chọn animation (AUTO = luật + số đo, tất định theo job id). Soát mắt chỉ khi cần: `vs.py look`.

## Thư viện hiện có (23/10 — `vs.py motion list --all` xem bản mới nhất)

| id | brand | vai trò | ghi chú |
|---|---|---|---|
| `gdp-roll-smile` | GIADUNGPLUS | brand_reveal (ưu tiên 60) | GDP 01: lăn vào từ mép trái, cười, chữ — dừng 3,3s (logo đủ) rồi chuyển giao logo góc |
| `gdp-orbit-settle` | GIADUNGPLUS | brand_reveal | GDP 08: quỹ đạo vào, cười, chữ — 3.5s |
| `gdp-peek-a-boo` | GIADUNGPLUS | accent, micro_animation | GDP 03: ló ra từ mép trái/phải — 2.5s |
| `gdp-ghost-smile` | GIADUNGPLUS | watermark | GDP 02: hiện, cười, mờ xuống ~13% rồi giữ |
| `lteng-precision-assembly` | LTENG | brand_reveal | LTENG 01: dựng nét — artwork trắng → chỉ nền tối |
| `lteng-rail-glide` | LTENG | brand_reveal | LTENG 02: trượt ray (white/navy) — 3s |
| `lteng-magenta-signal` | LTENG | brand_reveal, accent | LTENG 03: vạch magenta mở chữ — 2s |
| `lteng-ghost-signature` | LTENG | watermark | LTENG 04: chữ hiện rồi lắng ~14% |
| `phaledo-crystal-aperture` | PHALEDO | brand_reveal, accent | PHALEDO 01: vòng sáng + chữ mở — 4.2s |
| `phaledo-refraction-sweep` | PHALEDO | brand_reveal, accent (+ watermark `hold_at 2.45`) | PHALEDO 02: dải sáng quét — 3.2s |

Budget AUTO hiện tại (shop.json.motion.auto): GDP / LTENG: 1 reveal + accent [[15s,1],[30s,1],[60s,2]] (+1/30s), cách
nhau ≥2,5s · PHALEDO (quiet luxury): 1 reveal + accent chỉ từ video ≥30s, cách ≥5s. Thêm animation vai trò accent /
micro_animation / corner_signature vào thư viện là AUTO tự dùng — không sửa code.

Nguồn gốc: project Claude Design `554580b5-089f-4f21-941f-26ffd3c26f26` (KHÁC project UI `1b0c70e6…`). Ảnh logo
(`assets/*.png`) nằm cùng project — tải bằng DesignSync `get_file` (base64) khi animation tham chiếu.

## Quy trình A — Sếp có animation mới từ Claude Design

1. Lấy file về một thư mục (DesignSync `get_file` hoặc Sếp tải zip). Kèm đủ file nó tham chiếu (`gdp-assets.js`,
   `assets/*.png`…). Lấy bản `.html` đầy đủ — không lấy `*.dc.html` (preview) hay `*.src.html` có `__X__`.
2. `vs.py motion scan <thư mục>` → xem file nào ✓ render được, thiếu gì.
3. `vs.py motion import <file.html> --id <brand>-<tên-ngắn> --brand <BRAND theo shop.json> --role <vai trò>`
   (vai trò mở: brand_reveal / watermark / accent / corner_signature / transition / … đặt mới tuỳ ý).
   Import tự chép nguồn + phụ thuộc, sinh `motion.json` nháp, render thử, kiểm alpha, in đường dẫn ảnh soát.
4. Mở/đọc `motion.json` + chạy thử với tham số để hiểu animation (đọc comment đầu file HTML + phần `const q = …` liệt kê
   tham số query). Điền: `name`, `tags` (tính cách), `priority`, `params`, `variants` (`on_dark`/`on_light` nếu có bản
   màu cho nền tối/sáng; artwork chỉ một màu sáng → chỉ `on_dark`), `placement` (`width_pct` theo tỉ lệ khung, `x`
   left/right/logo_side, `y: top` + `margin_y_pct ~0.03`, animation chạy từ mép khung → `margin_x_pct: 0`; chuyển động
   quá rộng → `region` cắt vùng + `feather_px`; dừng sớm → `play_until`; `candidates` cho AUTO thử; vai trò phụ →
   `placement_by_role`), `roles` (nhiều vai trò được), `replaces`, `ends_transparent`/`hold`/`hold_time` (watermark).
   Sau khi đặt, chạy 1 job thử + `vs.py motion storyboard` để soát cỡ/chỗ trên video thật.
5. `vs.py motion check <id>` → mọi biến thể ĐẠT, xem `sheet.jpg` (3 nền tối/sáng/footage) bằng `vs.py look` hoặc Read.
6. Muốn shop dùng theo cách riêng → sửa `shop.json.motion` (prefer_tags, exclude, overrides) / `watermark.motion`.
7. Báo Sếp: id, vai trò, biến thể, ảnh soát, shop nào dùng được.

Sửa animation đã có = import lại cùng `--id` (bản cũ tự cất `_versions/`, cache đổi theo hash; job đã dựng vẫn ghim bản
cũ tới khi `edl.motion.update = true`). Bỏ = `vs.py motion disable <id>`. Quay lại = `vs.py motion use <id> <N>`.

## Quy trình B — dùng animation trong job video

- Mặc định job mới (trong `direct.py`) chỉ 1 dòng: `edl["motion"] = {"mode": "auto"}` → AUTO lập kế hoạch đa vai trò:
  1 brand reveal (ưu tiên lúc thuyết minh nhắc tên brand) + accent trong budget (ngay sau chuyển cảnh / khoảng nghỉ
  thuyết minh / vùng trống) + logo thường trực tiếp quản + watermark động theo vòng đời. Không ép đủ loại.
- Chèn tay: `{"mode": "manual" | "auto", "items": [{"id", "start", "role"?, "variant"?, "placement"?, "params"?, "opacity"?}]}`.
  Animation sai brand → render báo lỗi (không âm thầm chèn). Chèn tay đè logo góc → QA báo.
- Giữ watermark chữ: `"watermark": false` · logo không ẩn cả lúc reveal: `"keep_logo": true` · tắt hết: `"mode": "off"`.
- `vs.py motion plan <job>` (xem trước, vùng chữ ước lượng): thư viện/dùng được/budget, animation chọn + vai trò + giờ +
  chỗ + cỡ + độ mờ + lý do, logo hiện khoảng nào, watermark intro/mờ/giữ/đổi chỗ, animation bị bỏ + LÝ DO.
  Render thật in y như vậy, ghi `jobs/<id>/motion_plan.json` + `layers.json` (lớp thật đã ghép).
- `vs.py motion storyboard <job> [--before bản_cũ.mp4]` → `motion_storyboard.jpg`: mốc trước/giữa/cuối reveal, logo tiếp
  quản, accent, giữa video, watermark mờ/giữ/đổi chỗ, trước/trong outro. Xem ảnh (Read hoặc `vs.py look`) trước khi giao.
- `vs.py qa <job>` có mục **animation** (số đo: logo liên tục, watermark đúng vòng đời, không đè logo…): phải ĐẠT cùng
  mục chữ Hán.
- 1 video → nhiều shop: AUTO tự tránh dùng lại animation bản shop khác cùng video nguồn đã dùng.

## Xử lý lỗi thường gặp

| Báo lỗi | Nghĩa / cách xử lý |
|---|---|
| `không có window.setTime(giây)` | HTML chỉ autoplay → nhờ Sếp/Claude Design thêm API setTime vẽ đồng bộ. KHÔNG chụp màn hình theo giờ thật |
| `vẽ lại cùng thời điểm ra khung khác` | setTime không tất định (dùng Date.now / random) → sửa nguồn ở Claude Design |
| `thiếu file: x.png` / `chờ sẵn sàng lỗi` | tải thêm asset cùng project về cạnh file HTML rồi import lại |
| `nguồn gọi Internet` | font/ảnh từ CDN → chép về cục bộ / nhúng data URI |
| `nền KHÔNG trong suốt` | file preview hoặc body có màu nền → lấy bản render (`?render=1`), body transparent |
| `video KHÔNG có kênh alpha` | MP4 H.264 → xin ProRes 4444 / WebM alpha / chuỗi PNG |
| `KHÔNG dùng cho shop …` | animation khác brand → chọn đúng brand (`vs.py motion list --shop <shop>`) |
| `job đã chốt phiên bản … không còn` | thư viện đổi + cache bị xoá → `edl.motion.update = true` rồi dựng lại |
| `AUTO …: không có chỗ trống đủ` | video kín chữ → không chèn là đúng luật; muốn vẫn chèn thì chèn tay chỗ khác |
| `viền TỐI/SÁNG (halo)` | ảnh nguồn premultiplied sai → báo Sếp, xem sheet.jpg trước khi dùng |

## Sửa engine (code) — bắt buộc chạy kiểm thử

`.venv\Scripts\python.exe tools\test_motion.py` (≈20 phút, 15 case): A job cũ render giống hệt từng điểm ảnh so với git
HEAD · B alpha trên nền tối/sáng/footage · C tách brand + override shop · D lớp ghép đúng thứ tự, logo thường trực có mặt ·
E phiên bản · F animation mới qua CLI không sửa code · G lỗi nguồn · H reveal đầu → logo tiếp quản · I reveal giữa ·
J không reveal · K watermark xuất hiện→chìm · L đổi chỗ (trượt mặc định / fade tuỳ chọn) · M xung đột logo/animation/watermark · N AUTO đa vai
trò + budget · O cỡ/chỗ theo tỉ lệ 9:16/3:4/16:9. Phải ĐẠT hết. Chạy riêng: `tools\test_motion.py H K`.
Thêm animation (không sửa code) thì KHÔNG cần chạy bộ này — `vs.py motion check <id>` là đủ.

## Giới hạn hiện tại (nói thật với Sếp)

- Né "sản phẩm" bằng độ rối cạnh Canny — không nhận diện vật thể; video kín chữ/kín sản phẩm thì AUTO bỏ qua.
- Nguồn HTML phải có setTime tất định; animation dựa CSS animation/thời gian thực không render khung chính xác được.
- Khúc xạ thật theo footage (bẻ cong hình bên dưới) KHÔNG làm — chỉ overlay RGBA.
- Animation có tiếng (sfx `.wav` trong project) chưa trộn tiếng.
