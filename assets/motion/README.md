# Thư viện animation thương hiệu (Motion Identity)

Animation Sếp thiết kế bằng Claude Design (logo lăn vào, watermark sống, ló ra từ mép…) → Studio render **một lần** ra
clip **alpha** (ProRes 4444) → ghép vào video theo job. Thêm / sửa / bỏ animation **không cần sửa code**.

```
assets/motion/                     ← dùng chung theo BRAND (shop cùng brand tự dùng được)
├── <id>/
│   ├── motion.json                ← metadata (import sinh nháp, sửa tay được)
│   ├── src/                       ← nguồn chép NGUYÊN VĂN từ Claude Design (html + js + assets/…) — không sửa tay
│   └── _versions/v<N>/            ← bản cũ tự cất khi import đè (job đã chốt bản cũ vẫn render lại được)
└── _cache/                        ← clip alpha đã render theo hash (không đưa git; xoá thoải mái, tự render lại)
assets/shops/<shop>/motion/<id>/   ← (tuỳ chọn) animation RIÊNG một shop, cùng cấu trúc
```

Cách DÙNG theo từng shop nằm ở `assets/shops/<shop>/shop.json` → khối `motion` + `watermark.motion` (bên dưới).

## Thêm animation mới (Sếp tải từ Claude Design về)

```powershell
.\.venv\Scripts\python.exe vs.py motion scan <thư mục tải về>          # nguồn nào render được, file nào là preview/thiếu ảnh
.\.venv\Scripts\python.exe vs.py motion import <file.html|thư mục|zip> --id <brand>-<tên> --brand <BRAND> --role brand_reveal
#  → chép nguồn + mọi file nó tham chiếu (gdp-assets.js, assets/*.png…), sinh motion.json nháp, render thử + kiểm alpha
.\.venv\Scripts\python.exe vs.py motion render <id> [--variant on_light]   # xem ảnh soát 3 nền (tối / sáng / footage)
#  → sửa motion.json: roles, tags, priority, placement, variants (bảng dưới) → render lại → dùng trong job
.\.venv\Scripts\python.exe vs.py motion list --shop <shop>               # animation shop đó dùng được
```

Sửa animation đã có: import lại cùng `--id` → bản cũ vào `_versions/`, `version` +1, cache tự đổi theo hash.
Bỏ: `vs.py motion disable <id>` (AUTO không chọn nữa; job đã chốt vẫn render được). Quay bản cũ: `vs.py motion use <id> <N>`.

## Hợp đồng nguồn (Claude Design xuất sẵn — nhắc khi đặt thiết kế mới)

- **HTML**: `window.setTime(giây)` vẽ ĐỒNG BỘ đúng khung tại t (không phụ thuộc giờ thật) · nền `html/body/stage`
  **trong suốt** · `?render=1` tắt autoplay · tuỳ chọn `window.<X>_MOTION = {duration, width, height, ready, name, scenes}`
  (`ready` = Promise chờ ảnh/font) · **không CDN / không Internet** (font, ảnh để cạnh file hoặc nhúng data URI).
  Tham số qua query string (`?variant=white&width=0.2`) → khai trong `params` / `variants`.
  Studio từ chối: không có setTime (không chụp theo thời gian thực), vẽ lại cùng t ra khung khác, gọi Internet, thiếu
  file, font lỗi, nền đục, mọi khung trong suốt.
- **Chuỗi PNG RGBA** (thư mục, ≥8 khung đánh số cùng tiền tố, cùng kích thước) — `source.kind: "frames"`, khai `fps`.
- **Video CÓ alpha**: ProRes 4444 `.mov`, WebM VP9 alpha, mov png/qtrle. ⛔ MP4 H.264 không có alpha → từ chối.
- File `*.dc.html` / có `support.js` = trang PREVIEW của Claude Design (nền + khung xem thử) — không phải nguồn.
  File `*.src.html` có chuỗi `__X__` = bản nguồn chưa đóng gói — dùng bản `.html` đầy đủ.
- Hiệu ứng "khúc xạ" phải tự vẽ trong RGBA (như PHALEDO Refraction Sweep). Studio KHÔNG bẻ cong footage bên dưới.

## motion.json

| Trường | Ý nghĩa | Mặc định |
|---|---|---|
| `id` | tên ổn định, chữ thường-gạch (`gdp-roll-smile`) | bắt buộc |
| `name`, `notes` | tên hiển thị, ghi chú | |
| `version` | tự tăng khi import đè | 1 |
| `brands` / `shops` | brand (theo `shop.json.brand`) hoặc mã shop được dùng; `["*"]` = mọi shop | bắt buộc 1 trong 2 |
| `roles` | `brand_reveal` · `watermark` · `accent` · `corner_signature` · `transition` · `outro` · `custom` — **mở**, đặt tên mới tuỳ ý | `["custom"]` |
| `tags` | mô tả tính cách (`thân thiện`, `kỹ thuật`, `cao cấp`…) — khớp `shop.json.motion.prefer_tags` | `[]` |
| `priority` | AUTO ưu tiên số lớn | 50 |
| `enabled` | tắt = AUTO bỏ qua, chèn tay báo lỗi | true |
| `source` | `{kind: html\|frames\|video, entry: "src/…", origin}` | |
| `canvas`, `fps`, `duration` | khung thiết kế, fps render, thời lượng (đọc từ trang nếu có) | 1080×1920, 30 |
| `params` | tham số query khi render (ảnh hưởng điểm ảnh) | `{}` |
| `variants` | biến thể màu `{on_dark: {…}, on_light: {…}}` — AUTO chọn theo độ sáng vùng đặt; chỉ có `on_dark` = chỉ dùng trên nền tối | `{}` = mọi nền |
| `default_variant` | biến thể khi không chọn | |
| `placement` | chỗ đặt (bảng "Chỗ đặt" dưới) | `x,y = design`, `scale 1` |
| `placement_by_role` | chỗ đặt riêng khi dùng ở vai trò khác: `{"accent": {"x": "center", "candidates": […]}}` | |
| `replaces` | lớp TẠM THAY trong lúc animation chạy: `["logo"]` → logo thường trực ẩn đúng khoảng đó rồi hiện lại | brand_reveal: `["logo"]` |
| `hold_time` | (watermark) giây của khung giữ; không khai → khung cuối nếu còn hình, không thì khung logo đặc nhất (tự kiểm) | |
| `z` | `below_text` (dưới ô chữ — mặc định, chữ luôn đọc được) · `top` | `below_text` |
| `ends_transparent` | khung cuối phải trong suốt (không để overlay thừa) — watermark giữ thì `false` | true (watermark: false) |
| `hold` | `last` = giữ khung cuối (watermark sống) | |
| `opaque` | animation phủ kín khung (chuyển cảnh) — bỏ kiểm "nền đục" | false |

Vai trò AUTO chỉ xử lý theo dữ liệu: `replaces`, `roles`, `tags`, `priority`, `placement`, `variants` — code không biết
tên brand / tên animation nào.

### Chỗ đặt (`placement`) — Motion Director V2

| Trường | Ý nghĩa |
|---|---|
| `width_pct` | bề rộng PHẦN THẤY / bề rộng video — số hoặc theo tỉ lệ khung `{"9:16": 0.34, "3:4": 0.32, "1:1": 0.28, "16:9": 0.2}` (lấy khoá gần nhất) |
| `scale` | thay `width_pct`: 1 = khung thiết kế phủ đúng bề ngang video |
| `max_height_pct` | khống chế chiều cao (theo tỉ lệ khung được) |
| `x` | `left` · `right` · `center` · `logo_side` (cùng phía logo thường trực) · `design` · số 0–1 (tâm) |
| `y` | `top` · `bottom` · `center` · `design` · số 0–1 (tâm) |
| `margin_x_pct` / `margin_y_pct` | lề ngang (×bề rộng, mặc định 0,04) / lề dọc (×chiều cao, mặc định 0,035). Animation lăn/ló từ mép: `margin_x_pct: 0` |
| `region` | `[x0, y0, x1, y1]` px khung thiết kế (null = không giới hạn): vùng thấy được TỐI ĐA — cắt clip, mép bị cắt mờ `feather_px` → chuyển động gói gọn gần neo, không chạy từ mép xa của cả khung |
| `play_until` + `fade_out` | chỉ phát tới giây đó rồi mờ ra (vd GDP Roll & Smile dừng ở logo đầy đủ 3,3s, bỏ đoạn lăn ra) |
| `handoff` | logo thường trực bắt đầu hiện lại trước khi animation hết bao nhiêu giây (chuyển giao, mặc định 0,3) |
| `candidates` | danh sách biến thể chỗ đặt cho AUTO thử (mỗi cái có thể kèm `params` render, vd `side: right`) |

Thứ tự ghép: mặc định vai trò của shop (`shop.json.motion.defaults.<role>.placement`) < `placement` của animation <
`placement_by_role` < `shop.json.motion.overrides.<id>.placement` < chèn tay trong edl. Không sửa nguồn animation để đổi
cỡ/chỗ — compositor co giãn + cắt vùng.

## Cấu hình theo shop (`shop.json`)

```json
"logo": {"files": {…}, "persistent": {"width_pct": {"9:16": 0.16, "3:4": 0.15, "1:1": 0.13, "16:9": 0.1},
                                      "margin_x_pct": 0.04, "margin_y_pct": 0.03, "max_height_pct": 0.075}},
"motion": {
  "auto": {
    "brand_reveal": {"budget": [[null, 1]], "window": [0.3, 0.45], "prefer": "early", "brand_mention": true},
    "accent": {"roles": ["accent", "micro_animation", "corner_signature"], "budget": [[15, 1], [30, 1], [60, 2]],
               "per_extra_30s": 1, "window": [2.0, 0.92], "prefer": "middle"}
  },
  "min_gap": 2.5,
  "prefer_tags": ["thân thiện", "vui"], "exclude": [], "pool": null,
  "overrides": {"lteng-rail-glide": {"params": {"direction": "rtl"}, "placement": {"y": "top"}, "variant": "on_dark",
                                    "opacity": 0.9, "z": "top"}}
},
"watermark": {"enabled": true, "opacity": 0.13, "text": "…",
              "motion": "gdp-ghost-smile", "motion_params": {"hold": 0.13}, "motion_width_pct": 0.13, "hold_at": null,
              "period": 6.0,
              "lifecycle": {"relocate_mode": "slide", "settle_pause": 1.0, "dim": 0.8, "relocate": true, "exit": 0.4,
                            "after_reveal": 1.0, "hold": 9, "fade": 0.4}}
```

- `logo.persistent`: cỡ logo THƯỜNG TRỰC (job bật motion) — đo theo phần logo thấy được (bỏ viền trong suốt của file),
  theo tỉ lệ khung; lề trên 3% chiều cao, lề ngang 4% bề rộng. Hiện tại: GDP 15% (3:4) · LTENG VN 19% · LTENG HCM 18% ·
  PHALEDO 20%. Job KHÔNG bật motion giữ cỡ cũ (22%, lề 3% bề rộng).
- `auto.<luật>`: mỗi luật một nhóm vai trò (`roles`, mặc định = tên luật) với **budget theo thời lượng**
  (`budget` = [[giới hạn giây | null, số lần]…] + `per_extra_30s`; hoặc `max` cố định), `window` = [giây sớm nhất, mốc muộn
  nhất (≤1 = tỉ lệ thời lượng)], `prefer` = `early` | `middle`, `brand_mention` = ưu tiên lúc thuyết minh nhắc tên brand.
  Khai brand_reveal TRƯỚC accent. `min_gap` = giây tối thiểu giữa 2 sự kiện (kể cả đoạn intro watermark).
  Mặc định đang dùng: GDP/LTENG accent [[15,1],[30,1],[60,2]] (+1/30s) · PHALEDO [[30,0],[60,1]] (+0,5/30s), gap 5s.
- Shop không khai `motion` → mượn shop `templates_from` (như giọng đọc). Shop cùng brand dùng chung file thư viện.
- `watermark.motion` = animation thay watermark chữ: **XUẤT HIỆN → CHÌM DẦN → ĐỔI CHỖ** (Sếp 23/10: giữ kiểu cũ).
  XUẤT HIỆN = animation gốc tại 1 chỗ, tới khung giữ (khung cuối nếu animation tự mờ xuống, hoặc `hold_at`/`hold_time`,
  hoặc tự suy ra khung logo đặc nhất — có kiểm logo đủ/không cắt) → CHÌM DẦN (`dim` giây về `opacity`, chỉ khi animation
  không tự mờ — opacity áp đúng 1 lần) → ĐỔI CHỖ chỉ sau khi đã chìm xong:
  · `relocate_mode: "slide"` (mặc định, như watermark chữ cũ): TRƯỢT êm (1,4s) sang chỗ mới mỗi `watermark.period` giây
    (6s); lần đầu ở max(chìm xong + `settle_pause`, lúc vào + period).
  · `relocate_mode: "fade"` (tuỳ chọn): đứng yên `hold` giây rồi mờ ra chỗ cũ / hiện ở chỗ mới trong `fade` giây.
  · `relocate: false` = đứng 1 chỗ tới hết. → mờ hẳn `exit` giây trước outro.
  Watermark vào sau brand reveal mở đầu `after_reveal` giây; né ô chữ, animation, cả dải dưới logo góc (~15% chiều cao),
  vùng nhiều chi tiết.

## Trong job (`edl.motion`, viết trong `direct.py`)

```python
edl["motion"] = {"mode": "auto"}                       # mặc định job mới: AUTO + watermark động
edl["motion"] = {"mode": "manual", "items": [          # chèn tay
    {"id": "gdp-peek-a-boo", "start": 6.5, "placement": {"params": {"side": "right"}, "y": 0.35}}]}
edl["motion"] = {"mode": "auto", "watermark": False}   # giữ watermark chữ cũ
edl["motion"] = {"mode": "off"}                        # không animation (= không khai)
```

Thêm: `"keep_logo": true` (logo thường trực KHÔNG ẩn cả lúc animation thay logo chạy) · `"update": true` (bỏ phiên bản
đã chốt) · item `"role": "accent"` (dùng animation nhiều vai trò ở vai trò cụ thể).
Không khai `edl.motion` = flow cũ y nguyên (logo cũ + watermark chữ trôi) — job cũ render lại không đổi điểm ảnh nào.

## Luật xung đột (cứng trong engine) — Motion Director V2

1. **Logo thường trực theo KHOẢNG THỜI GIAN**: hiện suốt video chính; animation `replaces: ["logo"]` chạy → logo mờ ra
   0,25s sau khi animation vào, hiện lại trong `handoff` (0,3s) cuối animation; reveal ở giữa video → logo có từ đầu, ẩn
   đúng đoạn, hiện lại; reveal mở đầu video (≤0,05s) → ẩn từ khung đầu. Không có cờ tắt logo cả video; animation lỗi /
   không chọn → logo hiện suốt. Animation KHÔNG thay logo không được đè logo góc (AUTO né, QA bắt nếu chèn tay).
2. Watermark động thay watermark chữ — không bao giờ 2 watermark; vào sau reveal mở đầu; xa logo góc.
3. AUTO chỉ đặt animation ở chỗ chồng ô chữ ≤ 4% (diện tích × thời gian), cách sự kiện khác ≥ `min_gap`, ưu tiên vùng
   ít chi tiết (cạnh Canny ≈ sản phẩm/tay), lúc nhắc tên brand (reveal), ngay sau chuyển cảnh, khoảng nghỉ thuyết minh;
   trong budget từng nhóm vai trò. Không có chỗ / hết ứng viên → KHÔNG ép, ghi lý do (`vs.py motion plan`).
4. Animation ghép TRƯỚC khi nối outro → không bao giờ đè outro; dài quá phần video chính → bị cắt + cảnh báo.
5. Tất định: cùng job + cùng thư viện → cùng quyết định (không gọi AI). Bản khác cùng video nguồn (shop khác) tránh lặp
   animation. Quyết định + phiên bản ghi `jobs/<id>/motion_plan.json`; job đã dựng thì GHIM phiên bản (src hash) —
   thư viện có bản mới vẫn dùng bản cũ cho job đó tới khi `edl.motion.update = true`.

## QA

- Lúc render animation (`vs.py motion render/check`): alpha thật, mép khung trong suốt, khung đầu/cuối, chớp nền, halo
  viền tối/sáng, tái lập khung, đủ khung/fps sau mã hoá + ảnh soát 3 nền `_cache/<id>-<key>/sheet.jpg`.
- `vs.py qa <job>` thêm mục animation (số đo, không AI, đọc `layers.json` = lớp THẬT đã ghép): clip còn + alpha đạt;
  logo thường trực có trong bản dựng, chỉ ẩn trong khoảng animation thay logo; animation không thay logo không đè logo;
  watermark không đổi chỗ khi chưa xuất hiện→chìm xong (kiểu fade: mỗi chặng ≥0,6×hold), tắt relocate thì 1 chỗ; không 2 watermark;
  chồng chữ ≤ 4%; thời lượng + tiếng. Lỗi → QA CHƯA ĐẠT.
- `vs.py motion plan <job>`: thư viện / dùng được / budget / animation chọn (vai trò, giờ, chỗ, cỡ, độ mờ, lý do) / logo
  thường trực hiện khoảng nào / watermark intro-mờ-giữ-đổi chỗ / animation bị bỏ + LÝ DO (sai brand, tắt, hết budget,
  không có chỗ, thiếu tương phản, dùng làm watermark…).
- `vs.py motion storyboard <job> [--before video_cũ.mp4]`: ảnh soát các mốc (trước/giữa/cuối reveal, logo tiếp quản,
  accent, giữa video, watermark mờ/giữ/đổi chỗ, trước/trong outro), hàng SAU + hàng TRƯỚC cùng mốc giờ.
- Soát mắt khi cần: `vs.py look <sheet.jpg|storyboard> -q "…"` (model rẻ).
