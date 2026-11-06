# Scene Library — cảnh dựng sẵn, chỉ thay nội dung (05/11/2026)

Hệ thống 4 tầng (đề xuất ChatGPT, Sếp duyệt làm 05/11) — **xây 1 lần, dùng cho video thứ 100**:

| Tầng | Ở đâu | Là gì |
|---|---|---|
| Asset Library | `assets/library/` (`vs.py lib`) | vật liệu: ảnh, giấy, miếng cắt dán, nền, (SFX `assets/sfx/`) |
| Motion Engine | `studio/motionlib.py` + `assets/motion/` (`vs.py motion`) | render HTML `setTime` → clip alpha, cache theo hash |
| **Scene Library** | `assets/scenes/<family>/` | **Scene Family** = 1 kiểu cảnh có bố cục + vào/đứng/ra hoàn chỉnh, nhiều THEME, nhiều PRESET thời lượng, mọi chữ/ảnh là tham số |
| **Story Library** | `assets/scenes/stories.json` | cấu trúc kể chuyện: chuỗi family theo tình huống kịch bản (S01–S08) |

Theme hiện có: `gdp_red` (Red Paper Lab — giấy xé, pop/snap, UTM Avo) · `phaledo_dark` (Dark Glass Editorial — nền than,
nét mảnh champagne, fade/reveal/ánh sáng quét, Averta) · `phaledo_warm` (Warm Kitchen Journal — giấy be, sổ tay, polaroid,
trượt nhẹ, Averta). Font theo `shop.json` (GDP: UTM Avo · PHALEDO: Averta mọi trường hợp — không dùng serif dù đề xuất
có nhắc, vì luật thương hiệu đã chốt). Không được "đổi nền đỏ thành đen" để ra PHALEDO: mỗi theme một cách chuyển động.

## Một Scene Family gồm

```
assets/scenes/<family>/
  scene.json        hồ sơ sử dụng: code (C02…), version, motion_id, mục đích, DÙNG KHI / KHÔNG DÙNG KHI, preset
                    (`hides` = tham số preset không hiện → tự nâng preset), `default_dur`, `lead_in` (hiện sớm hơn lời),
                    `behind` (chữ sau người), `sample` (chữ mẫu preview), `word_at`/`land_at` (mốc tiếng hiệu ứng)
                    `captions: keep` (chữ động chạy tiếp), `hide_logo`, `items` (nhãn con theo lời), `preset_auto: content`
                    `items.sided` (ý theo phe A/B), `time_params` (cụm lời → giây, vd win_at → win_t)
                    `proof_clip` (clip thật trong ô cửa sổ — qa.window/live_t), `media_dims`, `loupe` (kính lúp)
                    (micro/standard/full + khoảng thời lượng), theme, tham số (giới hạn chữ), SFX, QA, ví dụ cut.py
  src/<family>.html template `setTime` (Claude viết) — theme + preset + nội dung đều qua query, không hardcode chữ
  src/themes.js     token từng theme (màu, font, nền, bộ miếng giấy…)
  src/assets/ src/assets.js src/fonts/   bản nhẹ của asset thư viện (`library.export_web`) + font cạnh file
  previews/         ảnh soát mỗi theme × preset (đầu – giữa – cuối)
```

Nhập vào Motion Engine: `vs.py motion import assets/scenes/<family>/src/<family>.html --id scene-<family> --brand '*'
--role scene --no-render` → khai `opaque`, `params` trong motion.json → `vs.py motion render`.
Dùng trong dựng video: `c.graphic("scene-<family>", at=…, until=…, title=…, …)` — theme tự theo shop của job
(`c.logo(shop)` / `c.theme(...)`), preset tự theo thời lượng at→until (hoặc ép `preset=`).

## Quy tắc bắt buộc (10)

1. Template độc lập nội dung — không hardcode tiêu đề/sản phẩm/số liệu.  2. Asset tách khỏi motion (tham chiếu theo
tên).  3. Theme = cấu hình.  4. Biến thể (`seed`, preset, theme) không sinh ảnh mới.  5. Render tất định: cùng tham số +
seed → cùng khung (Motion Engine kiểm, Chrome vẽ CPU `--disable-gpu`; ⚠ không dùng CSS `will-change`).  6. Cache theo hash nguồn + tham số.
7. Phủ lên footage phải có alpha thật (khung cuối trong suốt).  8. CapCut: track riêng, đúng giờ/thứ tự lớp.
9. Không che mặt/sản phẩm: chữ trong vùng an toàn TikTok (ngang 6–84%, dọc 12–76%).  10. QA tự động: khung đen, font
tiếng Việt, chữ tràn, khung lệch.

## Cách Claude chọn cảnh (đọc trước khi viết cut.py)

- Đọc lời đã chép → tìm chỗ thoả **điều kiện** trong `scene.json.use_when`; không thoả thì KHÔNG chèn (không vì đẹp mà
  nhét). Một video có người nói: đồ hoạ hỗ trợ lời, không thay hết hình thật.
- Chọn Story trong `stories.json` theo dạng kịch bản; family nào `status` chưa "ready" thì dùng cách khác (cap, cover…).
- Ảnh sản phẩm trong cảnh = ảnh/footage THẬT đã duyệt (`photo="lib:<id>"` ảnh nhập bằng `vs.py lib import --engine photo`).
  Ảnh AI chỉ minh hoạ bối cảnh/nguyên liệu; PHALEDO tuyệt đối không dựng lại sản phẩm bằng AI.
- Logo không vào sớm làm gãy hook (giây đầu là nội dung).

## Family

| Code | Family | Thư mục | Trạng thái |
|---|---|---|---|
| C02 | Chapter Card — thẻ mở chương | `chapter-card/` | ✅ v1.0 — 3 theme × micro/standard/full |
| C01 | Keyword Burst — từ khoá bật to, đè footage | `keyword-burst/` | ✅ v1.0 — 3 theme × micro/standard/full, chữ SAU người (mặt nạ RVM, build.py) |
| C03 | Pinned Title — tiêu đề ghim + nhãn con theo lời | `pinned-title/` | ✅ v1.0 — 3 theme × micro/standard/full, bố cục tự né người, chữ động chạy tiếp |
| C04 | Count & Reveal — số đếm + từng mục bật theo lời | `count-reveal/` | ✅ v1.0 — 3 theme × micro/standard/full (standard/full phủ khung) |
| C05 | A vs B — 2 phe + VS + chốt phe thắng | `a-vs-b/` | ✅ v1.0 — 3 theme × micro/standard/full, ảnh `lib:` / khung từ clip `src:<clip>@<giây>` |
| C09 | Detail Spotlight — khoanh / chỉ / phóng to chi tiết | `detail-spotlight/` | ✅ v1.0 — 3 theme × micro/standard/full (kính lúp), x,y từ `vs.py edit frame` |
| C08 | Evidence Frame — bằng chứng thật đóng khung | `evidence-frame/` | ✅ v1.0 — 3 theme × micro/standard/full, ảnh hoặc CLIP thật phát trong khung (build ProofPainter) |
| C06 | Problem → Solution — vấn đề → chuyển ý → giải pháp | `problem-solution/` | ✅ v1.0 — 3 theme × micro/standard/full (standard/full phủ khung, mốc chuyển `switch_at`) |
| C07 | Number Impact — số đếm lên / từ → đến / biểu đồ | `number-impact/` | ✅ v1.0 — 3 theme × micro/standard/full (micro/standard đè footage, có thể SAU người; full biểu đồ) |
| C10 | Timeline / Process — các bước / mốc nối nhau theo lời | `timeline/` | ✅ v1.0 — 3 theme × micro/standard/full (micro = thanh tiến độ giữ chữ động — ghi đè `captions`/`hide_logo` theo preset) |
| C11 | Quote / Insight — câu nói đắt thành thẻ riêng | `quote/` | ✅ v1.0 — 3 theme × micro/standard/full (full + ảnh thật) |
| C12 | Brand Outro | — | ⛔ bỏ (Sếp 06/11: outro / intro đã có sẵn) |
| G01–G12 / P01–P10 | riêng GDP / PHALEDO (đề xuất) | — | ⏳ đợt 2 |
