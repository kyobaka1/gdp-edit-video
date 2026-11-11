---
name: gdp-video-localize
description: Việt hoá video sản phẩm tiếng Trung (Taobao/1688/Douyin/NCC) cho brand Gia Dụng Plus (PHALEDO, LTENG, GIADUNGPLUS…) bằng GDP Video Studio chạy local (repo gdp-video-studio, Windows / Mac) — che chữ Trung đồ hoạ bằng ô chữ Việt theo MẪU brand (HTML), giữ nguyên chữ trên sản phẩm/phụ kiện, lồng thuyết minh tiếng Việt liền mạch (Gemini TTS) + nhạc nền (Lyria), QA tự động 0 chữ Hán sót. Dùng khi Sếp nói "Việt hoá video", "dịch video tiếng Trung", "làm video này sang tiếng Việt", "che chữ Trung trong video", "lồng tiếng Việt cho video", "thả video vào inbox rồi chạy", "render final video", hoặc đưa file .mp4 tiếng Trung cần làm cho brand. KHÔNG dùng cho video Shopee Video upload/gán sản phẩm (module marketing/shopee_video) hay dựng video từ ảnh.
---

# GDP Video Localize — Việt hoá video TQ (Claude Code điều khiển)

Studio: `C:\Users\Admin\gdp-video-studio` (git riêng). Plan/trạng thái: repo giadungplus
`docs/plans/2026-10-20-gdp-video-studio-viet-hoa-video.md`. Chạy mọi lệnh bằng PowerShell:

```powershell
Set-Location C:\Users\Admin\gdp-video-studio; $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe vs.py <lệnh> …
```

**Máy khác / Mac:** thư mục studio = nơi đã clone / chép repo (máy Sếp: `C:\Users\Admin\gdp-video-studio`). Mac / Linux chạy bằng bash trong thư mục đó: `export PYTHONIOENCODING=utf-8; .venv/bin/python vs.py …` (thay `.\.venv\Scripts\python.exe` → `.venv/bin/python`, `\` → `/` ở mọi lệnh bên dưới). Cài máy mới: `SETUP.md` (mục 8 = Mac). Skill này nằm sẵn trong repo `.claude/skills/` — máy khác KHÔNG cần `sync_skill.py`.

Gemini key riêng của Sếp trong `.env` (KHÔNG đọc/in ra). Không chạy model nặng local. Kiểm môi trường: `doctor.py`.
Cài trên máy mới / cấu hình chạy 3 video song song: `SETUP.md` trong thư mục studio (có số đo thật).
**Nguồn skill này = `studio\.claude\skills\gdp-video-localize\`** (đi theo thư mục). Sửa skill → sửa bản đó → chạy
`tools\sync_skill.py install` (cài cho Claude `~\.claude\skills` + Codex `~\.codex\skills`) → đẩy bản sao lên repo
giadungplus `skills/gdp-video-localize/`.
**Animation thương hiệu** (logo động, watermark động, nhập animation Claude Design): skill **`gdp-video-motion`** +
`assets/motion/README.md`. Skill này chỉ ghi phần dùng trong job Việt hoá.

## Chi phí: ai xem / nghe bằng gì (Sếp 22/10 — Gemini từng tốn 344k/ngày)

- Gói ChatGPT Pro của Sếp = Codex CLI local, không tốn tiền API → **việc SOÁT ẢNH đi Codex model rẻ; Gemini API chỉ dự
  phòng** (Codex hỏng / hết usage / chưa cài). Model `gpt-5.6-luna` (đổi bằng `CODEX_MODEL` trong `.env`; tài khoản
  ChatGPT KHÔNG gọi được gpt-6-luna/gpt-6-sol). Đo 22/10 trên 82 job: `detect` = 13,4M token prompt (qa ~61%, analyze
  ~39%); nghe lại audio <2%.
  · `vs.py qa` tự soát bằng Codex; chỉ khung Codex báo còn chữ đồ hoạ mới gửi Gemini xác nhận (ô chính xác cho `patch`).
    Bản final sạch → 0 token Gemini (đo: 95 khung, 36s). Độ nhạy: video gốc chưa che → bắt 18/18 sự kiện chữ đồ hoạ.
    `qa.json.screen` ghi số lô Codex / lô rơi về Gemini (+ lý do).
  · `vs.py analyze` VẪN Gemini: ô Codex chỉ phủ 63–100% ô thật, lệch giữa các lần chạy → che lộ chữ. Chạy 1 lần / video
    nguồn, `--regroup` không tốn token, không analyze lại từng shop.
  · Soát mắt ảnh (khung ±0,4s quanh mốc, góc logo, `contact.jpg`, ảnh so sánh): `vs.py look <ảnh…> -q "câu hỏi"` (Codex rẻ).
  · Âm thanh: Codex KHÔNG nhận audio → `vs.py hear <file>` (Gemini ~32 token/giây; Gemini hết tiền → tokenrouter). Cổng kiểm ngược trong `narrate` đã
    nghe từng mảnh → chỉ nghe lại bản final 1 lần. ⛔ KHÔNG tự viết script gọi Gemini để "review" thêm (đã thấy
    `audit_audio.py`, `check_music.py`, `recheck_pieces.py`, `final_mix_audio_review`… trong `jobs/_delivery*`).
- **Ai đang lái phiên:**
  · Claude lái → xem ảnh bằng Read được (tính vào gói Claude); muốn tiết kiệm thì dùng `vs.py look`.
  · **ChatGPT/Codex model xịn lái (vd GPT-6.1-Sol, GPT-6-Astra) → KHÔNG tự mở ảnh / nghe audio bằng model đó.** Xem ảnh
    giao `vs.py look` hoặc subagent Codex model rẻ (`codex exec -m gpt-5.6-luna -i <ảnh> "<câu hỏi>"`), nghe giao
    `vs.py hear`; model xịn chỉ đọc kết luận dạng chữ rồi quyết định. Giao cả job cho subagent thì cũng chọn model rẻ;
    người điều phối chấm lại bằng số đo + `look`.
- Gemini báo `402 … prepayment credits are depleted` = hết tiền nạp → báo Sếp nạp ở AI Studio. Khi đó `qa` vẫn chạy bằng
  Codex (`gemini_confirm_error` khác rỗng → ô sót là ô Codex thô, patch xong soát mắt); TTS tự sang gpt-audio-mini;
  `narrate` / `hear` tự sang **tokenrouter gpt-audio-mini để nghe** + định vị đoạn **ước theo độ dài chữ**
  (`narration.json.align`). `analyze` + nhạc Lyria vẫn đứng tới khi nạp.
  ⚠️ Dự phòng nghe CHỈ để không đứng việc, chất lượng kém Gemini (đo 22/10, LTENG HCM, TTS + nghe đều dự phòng):
  cả bài khớp 0,93; 7/8 mảnh 0,81–0,89 (Gemini ~1,0); đặt đúng cảnh. gpt-audio-mini là model HỘI THOẠI: mảnh ngắn
  <~2,5s hay bị TỪ CHỐI ("vui lòng cung cấp audio…") → tự gửi lại bản đệm lặng; vẫn từ chối thì mảnh ghi
  **"CHƯA KIỂM được"** = phải nghe tay, KHÔNG coi là đạt. Bản đọc bằng dự phòng: báo Sếp rõ, ưu tiên chờ Gemini rồi
  xoá `narration/take_*` đọc lại. Mẫu nhận diện từ chối: `tools/test_hear_refusal.py` (16/16, nhầm 0/525).

## ⭐ Việt hoá V2 — XOÁ chữ Trung + chữ Việt ĐỘNG (Sếp 11/11 — MẶC ĐỊNH cho job mới)

Sếp chê bản cũ (0379): ô chữ Việt vừa CHE vừa HIỂN THỊ nên phải đục và to bằng cả dải (phụ đề Trung cao ~40px bị thay
bằng viên đen 720×134), một kiểu chữ, một độ đậm, đổi chữ chậm, bám 100% câu Trung. V2 tách hai việc:
**`studio/clean.py` lo XOÁ / LẤP chữ Trung** · **`studio/vcaps.py` lo CHỮ VIỆT** (bộ chữ động + Phong cách của skill
`gdp-video-edit`: nhiều độ đậm trong một khối, từng từ mờ-trồi vào, hộp nhấn màu shop, đặt tự do theo khung).
Mẫu đủ bộ (bản lưu git): `tools/localize_v2_example.py` (0379 — phụ đề sát đáy + sticker hook nghiêng: khung dải +
badge xoay) · `tools/localize_v2_example_badge.py` (0374 — tiêu đề lớn + phụ đề ở vùng trên nhưng thấp: badge nhóm).
Job cũ không khai `edl.clean` / `edl.caps` render y như trước.

### Chọn CÁCH LẤP chữ Trung — theo VỊ TRÍ + CỠ (Sếp chốt 11/11 qua 0379 và 0374; máy tự chọn, in ra khi render)

Nguyên tắc Sếp: **badge nền che phủ + xoá chữ linh hoạt, tinh tế**; khung dải chỉ dùng khi phần phải cắt NHỎ; chữ càng
to thì càng phải cân nhắc, không phủ bừa. Máy đo từng dòng chữ Trung (hộp ôm NÉT thật, không phải ô Gemini) rồi quyết:

| # | Dạng chữ Trung | Điều kiện máy đo | Cách lấp | Chữ Việt |
|---|---|---|---|---|
| 1 | Phụ đề / dải chữ **sát mép** đáy hoặc đỉnh | dòng ngang, tâm > 78% H hoặc < 22% H, **và** phủ dải chỉ cắt ≤ **17% H** (`panel_max`) | **KHUNG DẢI** phủ cả dải (nền = phần hình kề bên lật gương, nhoè mạnh + tối, mép sắc) | trên khung, tự phóng ~70% chiều cao khung; không ghi `y` |
| 2 | Phụ đề **chạy suốt cùng một chỗ** nhưng nằm sâu (0374: 15–23% H) hoặc ở giữa khung | các dòng ngang nối tiếp nhau (khe ≤ 0,8s), cùng chỗ, cùng cỡ — không đạt #1 | **THANH PHỤ ĐỀ** (nhóm `bar`): MỘT badge bo góc phủ hộp chung của cả chuỗi, giữ liền, chỉ đổi chữ bên trong | khối bám lời (`"pN"`) không ghi `y` tự vào thanh; **1 dòng, ≤ 5 từ / khối** |
| 3 | **Tiêu đề lớn** / khối nhiều dòng (0374: 1 dòng rộng 88% × cao 11% H; 2 dòng 75% × 17% H) | 1 dòng lẻ, hoặc các dòng hiện cùng lúc xếp chồng (nhóm `single` / `block`) | **BADGE KHỐI** phủ đúng hộp của dòng / cả khối | `{"over": "<id một ô của khối>", "text": …}`; khối 1 dòng → 1 dòng chữ TO, khối 2 dòng → dẫn + cụm khoá |
| 4 | **Nhãn nhỏ** giữa cảnh (chú thích chỉ vào vật, < 3% khung) | nhóm `single` nhỏ | **CHIP**: badge mini đúng chỗ nhãn | chỉ nhận chữ qua `over` (1–3 từ) |
| 5 | **Sticker nghiêng** (hook xoay ≥ 4°) | dòng xoay | nhoè trong hình chữ nhật xoay ôm nét + **BADGE XOAY** cùng góc; quãng chữ bật / nảy vào: giữ hình sạch khung trước | `{"over": "<id ô>", "text": …}`, chữ tự phóng vừa badge |
| 6 | Chữ **quá lớn** — một nhóm phủ > **22% khung** (`cover_max`) | render in `⚠ nhóm … phủ x% khung` | ⛔ KHÔNG tự phủ badge to: hỏi Sếp — cắt bỏ đoạn đó / đổi cảnh khác / thẻ phủ khung (`scene-chapter-card` của skill edit) | — |
| 7 | Chữ có **sẵn nền** (sticker nền màu, nhãn hộp) | ô phân tích phải ôm cả nền | BADGE phủ cả nền gốc (nới `overlay["clean"] = {"box": […]}` cho bao hết nền) | như #3 / #4 |
| — | Không có chữ Trung (chữ CHÈN MỚI) | — | — | `x`, `y` tự do + bóng tối mềm sau chữ (`scrim`) |

- **Vì sao 17%**: 0379 phụ đề sát đáy → dải 15,7% H, Sếp duyệt. 0374 phụ đề ở 15–23% H → dải phải cắt 29% H: "chỗ cắt
  phần text và phía dưới quá lớn thì không được" → máy tự rớt xuống #2 / #3 và in `ℹ khung dải top: … → dùng BADGE che`.
  Ô nào nằm sâu quá ngưỡng bị loại riêng; các ô sát mép còn lại vẫn vào khung dải. Đổi ngưỡng (chỉ khi Sếp bảo):
  `edl.clean = {"panel_max": 0.2, "cover_max": 0.25, "lane_gap": 1.5}` (`lane_gap` = khe tối đa để thanh phụ đề giữ liền).
- **Dưới badge vẫn XOÁ chữ Trung** (nội suy nền / nhoè) — badge có lệch 1–2 khung cũng không lộ chữ Hán. Badge phủ kín
  hộp nét của cả nhóm, đục 100% suốt lúc có chữ Trung, bật / tắt đúng mối cắt cảnh sát mốc.
- **Hình badge nhóm** tự tính: rộng = max(hộp chữ Trung, chữ Việt dài nhất + đệm) ≤ 94% W; cao = max(hộp chữ Trung, 6,4% H
  cho 1 dòng / 10% H nếu có khối 2 dòng); chữ Việt phóng / thu theo chiều cao badge (0,72–1,7×). Render in từng badge:
  `badge G4 [bar] 5.50–22.40s · 469×80px (5% khung) · 6 khối chữ` → đọc cột % để biết badge có to quá không.
- ⛔ **Badge không được đứng TRỐNG**: khối đầu của nhóm tự kéo về lúc badge hiện; trong thanh phụ đề chữ cũ đứng tới đúng
  lúc chữ mới vào rồi tắt gọn (không mờ chéo, không "trôi lên" ra ngoài badge); khối cuối đứng tới lúc badge tắt. Nhóm
  không có khối chữ nào → render báo `⚠ nhóm … KHÔNG có chữ Việt` (không vẽ badge, chữ Trung chỉ được vá nền) → thêm chữ.
- **Trong thanh phụ đề: mỗi khối 1 dòng** — thanh cao theo khối cao nhất, một khối 2 dòng làm cả thanh to lên. Muốn 2
  tầng (dẫn + cụm khoá) thì chia thành 2 khối nối tiếp. Xen dòng thường với dòng `!`, hộp `^` thưa.
- Khe không có chữ Trung giữa hai thanh (0374: 22,4–25,4s) → không badge (đúng luật "chỉ hiện khi có chữ Trung"); lời
  đọc vẫn chạy, đừng nhét chữ trần vào khe ngắn.
- `clean.json` ghi `groups` (id, kind, members, box, t0–t1, % khung) + `notes`; mỗi ô có `group`. Xem trước không cần
  render: `tools\caps_previews.py <job> --at …`.

- ⛔ **Khung dải + badge chỉ hiện ĐÚNG LÚC có chữ Trung** (Sếp: "không lock từ đầu tới cuối"). Máy dò nét chữ từng
  khung → khung dải vào sớm 0,25s trước dòng đầu (sát đó có mối cắt cảnh thì bật / tắt ĐÚNG mối cắt), giữ liền qua khe
  < 0,8s giữa hai dòng, mờ ra khi dòng cuối tắt; badge đục 100% suốt khoảng chữ Trung của ô đó, mờ vào TRƯỚC và mờ ra
  SAU khoảng đó (trên hình sạch — không bao giờ lộ mảng nhoè), mép trùng mối cắt cảnh thì chữ + badge tắt cứng. Khoá suốt video chỉ khi Sếp yêu cầu: `edl.clean.panel = {"hold": true}`.
- ⛔ **Outro của shop LUÔN bật** (`edl.outro = {"enabled": true}`) khi thư mục `assets/shops/<shop>/outro/` có video —
  cả PHALEDO (`PHALEDO Outro v2.mp4`, 3,7s). Câu chốt brand đặt `at` ≥ thời lượng video chính để đọc TRÊN outro.
- Chữ trong cảnh (`kind: scene` — bao bì, nhãn) vẫn giữ nguyên như luật cũ.

**Khai trong direct.py** (thay cho việc điền `text_vi` / `template` từng ô):

```python
edl["clean"] = {"mode": "auto"}                    # màu khung dải tự theo shop (shop.json `caps.panel`)
edl["narration"] = {"tempo": 1.1, "paragraphs": [{"at": 0.0, "text": "…"}, …]}       # tempo 1,0–1,15: đọc nhanh, giữ cao độ
edl["caps"] = {"items": [                          # chữ + badge tự theo bộ nhận diện của shop (shop.json `caps`)
    {"over": "o2", "text": "!Bếp bừa bộn?"},                    # badge lấp chữ Trung ô o2 (không ghi at = theo chữ Trung)
    {"at": "p1", "text": "!PHALEDO / Hũ thủy tinh vuông"},       # "p1" = lúc đoạn thuyết minh 1 bắt đầu đọc
    {"at": "p1+1.9", "text": "Gom gọn, / !^nhìn là thấy"},       # 2 tầng: dòng dẫn thường + cụm khoá; ^ = hộp nhấn
    {"at": "p9", "until": DUR - 0.1, "text": "Xem đủ kích cỡ / !^ở giỏ hàng", "exit": "fade"},
]}
edl["outro"] = {"enabled": True}
```

- Ô che chữ Trung KHÔNG điền `text_vi` = chỉ là vùng xoá. Ô vụn (Gemini bắt 1–2 ký tự lúc chữ đang bay vào) cứ để —
  nằm trong khung dải thì vô hại. Ép cách xoá từng ô: `overlay["clean"] = "fill" | "blur" | "none"` hoặc
  `{"method", "box", "start", "end", "detect": false}`; không dùng khung dải: `edl.clean = {"bottom": "fill"}`.
- **Markup chữ** (như `cap()` của cut.py): dòng cách nhau ` / `; `!` cụm khoá đậm · `.` dòng phụ mảnh · `~` chữ mảnh to ·
  không dấu = dòng thường; thêm `^` = hộp nhấn màu shop (THƯA: ~1 hộp / 3–4 khối). Mỗi khối 1–2 dòng, ≤ 6 từ.
- **Mốc**: giây, hoặc `"p3"` / `"p3+1.5"` (bám đoạn thuyết minh — chạy `narrate` trước `render`), `"p3e"` = lúc đọc xong.
  Không ghi `until` = đứng tới sát khối kế (màn hình luôn có chữ — tắt tiếng vẫn hiểu).
- **Bộ nhận diện theo SHOP** (Sếp 11/11 "làm lại bộ nhận diện animation, text, badge … phối màu tinh tế và chuẩn") —
  khai MỘT lần trong `assets/shops/<shop>/shop.json` mục **`caps`** (`style` · `skin` chữ · `plate` badge · `panel`
  khung dải), `vcaps.py` + `clean.py` tự đọc (shop phụ mượn qua `templates_from`). ⛔ direct.py KHÔNG ghi `style` /
  `skin` / `plate` / `panel` — chỉ ghi đè khi Sếp yêu cầu riêng cho video đó (`edl.caps.plate`, `edl.clean.panel`).
  Màu đo từ pixel logo từng shop (không ước lượng). **Sếp DUYỆT bộ GDP / LTENG VN / LTENG HCM 11/11** (xem ảnh demo
  trên nguồn 0379) — đừng tự đổi màu / phông / kiểu vào; muốn đổi thì làm ảnh demo mới gửi Sếp duyệt lại. Ảnh demo: `assets/shops/_caps-preview.jpg` (chữ / badge / khung dải)
  + `_caps-motion.jpg` (badge đang vào).

  | Shop | Chữ | Badge (lấp chữ Trung giữa khung) | Badge vào | Hộp nhấn `^` | Khung dải |
  |---|---|---|---|---|---|
  | `giadungplus_official` | UTM Avo: dòng dẫn Regular + cụm khoá Bold | đỏ logo chuyển màu #d32b2d → #b01419, bo tròn 0,36h như logo, viền trắng mảnh, bóng mềm | **bật nảy** (pop) | vàng #f6c634 / chữ đỏ sậm #7a1010 | đỏ rượu #6e0f12 + nét vàng |
  | `lteng_vn` | UTM Avo Regular + Bold | navy chuyển màu như logo #1274b6 → #04204a, góc 0,16h, viền cyan mảnh | **quét ngang** (wipe) theo dòng chữ | trắng / chữ navy #062955 | navy #04214a + nét cyan #3aa6e8 |
  | `lteng_hcm` | dòng dẫn UTM Avo + cụm khoá **UTM HelvetIns IN HOA** | đen #171717, góc 0,12h, **thanh đỏ** #c0392b đầu dòng | **trượt** dọc dòng chữ (slide) | đỏ gạch #b8302c / chữ trắng | đen + nét đỏ |
  | `phaledo_official` | Averta (phong cách `phaledo-tap-chi`) | tối #161616, viền vàng đồng #b89a6a | mờ vào (fade) | vàng đồng / chữ đen | nền hình nhoè tối + nét vàng đồng |

  Khoá của `plate`: `bg` (+ `bg2` chuyển màu dọc dòng chữ) · `alpha` · `radius` (× chiều cao) · `line` + `line_alpha`
  (viền trong) · `bar {color, w}` (thanh nhấn đầu dòng) · `shadow` · `motion` pop | wipe | slide | fade. Của `panel`:
  `tint` + `tint_mix` (màu phủ lên nền nhoè) · `dim` · `line` + `line_alpha`. Của `skin` (thêm cho V2): `liveWeight: 400`
  (dòng dẫn nét thường) · `keyFont: "helvetins"` · `lineGap` (em — UTM Avo đặt dấu nặng rất thấp, dòng sát nhau thì dấu
  "ụ ạ ệ" rơi vào đầu chữ dòng dưới: "Gia Dụng Plus / Hũ thủy tinh" từng ra dấu nặng nằm trên chữ t) · `box` / `boxText`.
  Badge vào XONG trước lúc chữ Trung xuất hiện (0,24s, trên hình sạch) rồi chữ Việt mới hiện từng từ; mép trùng mối cắt
  cảnh / đầu video thì bật cứng (không chạy hiệu ứng).
- **Soát bộ nhận diện bằng ẢNH, không render video** (Sếp 11/11: "chỉ cần demo lên ảnh"):
  `tools\caps_previews.py <job> [<job> …] --at 3.2,4.9,6.9 [--width 720] [--out file.jpg]` — mỗi job một hàng khung (nguồn
  đã xoá chữ Trung + lớp chữ Việt, ~20s/job, không logo / tiếng). Sửa `shop.json` mục `caps` → chạy lại là thấy. Dải khung
  dày quanh `t0` của một badge (`--at 0.63,0.68,0.73,0.78,0.86`) = xem hiệu ứng vào. Soát ở cỡ thật (`--width 720`) rồi
  phóng to vùng chữ: dấu tiếng Việt, mép badge, độ tương phản chữ / khung dải.
  Shop mới / đổi màu: đo màu logo → khai `caps` → ảnh demo → gửi Sếp duyệt TRƯỚC khi dùng cho video giao.
- Cỡ chữ: `caps.scale` / `scale` từng khối.
- Render in `⚠ chữ Việt: …` khi: khối đứng ngắn hơn ~0,2s/từ (rút chữ / dời khối kế) · badge lấn khối khác (dời `x`)
  · khối không ghi `y` rơi vào lúc khung dải không hiện (bỏ khối / đặt `y` trên hình). Sửa hết cảnh báo trước khi giao.

**Nội dung — không cần bám 100% bản Trung (Sếp 11/11):**
- Được viết lại cách dẫn dắt, thêm câu chuyển ý / câu kêu gọi ("Xem đủ kích cỡ trong giỏ hàng nhé"), đổi thứ tự nhấn
  cho hợp cảnh. ⛔ Vẫn KHÔNG thêm công dụng / thông số / cam kết không có trong video gốc hoặc dữ liệu SKU (luật 5).
- **Nhịp nhanh hơn bản cũ**: lời đọc ~4 âm tiết/giây, không để lặng > 0,8s giữa các đoạn (0379 cũ: 8 đoạn ≈ 70 âm
  tiết / 31s → V2: 11 đoạn ≈ 115 âm tiết + `tempo` 1,1). Chữ đổi mỗi 1,5–2,5s: một đoạn lời dài chia 2 khối
  (`"p3"` rồi `"p3+1.5"`). `narrate` báo trễ > 0,5s → tăng `tempo` (không tốn lượt TTS mới) rồi mới rút chữ.
- Chữ trên hình = ý ĐẮT của câu đang đọc (không chép nguyên câu): danh từ / lợi ích ở dòng `!`, phần dẫn ở dòng thường.

**Quy trình V2** (thay bước 3–5 của quy trình cũ bên dưới; các bước khác giữ nguyên):
1. `new` → `analyze` như cũ → viết `direct.py` theo mẫu: `clean` + kịch bản + `outro`/`logo`/`motion`.
2. `vs.py narrate <id>` → xem mốc từng đoạn → viết `caps.items` bám `"pN"` → chạy lại `direct.py`.
3. `vs.py render <id>` → đọc `clean.json` (mỗi ô: `mode` "dò nét" / "ô tĩnh" / "khung dải", `seen_ratio`, `t0–t1`;
   `panels[].spans` = lúc khung dải hiện). Ô báo **"ô tĩnh"** (chữ Trung không phải kiểu sáng-viền-tối → máy không dò
   được nét) = xoá theo ô + mốc Gemini → PHẢI soát khung ±0,4s quanh mốc như luật cũ.
4. `vs.py qa <id>` phải ĐẠT sót 0 (QA vẫn là lưới cuối bắt chữ Hán lọt) + `audiocheck` + soát mắt: khung chuyển
   (lúc khung dải / badge vào – ra), badge có che kín vùng nhoè không, chữ có bị logo đè không; **mỗi ô sticker soát
   dày 0,07s quanh lúc chữ Trung vào** (mục "Chữ Trung BẬT / NẢY / CHỚP" bên dưới — QA không thay được bước này).
5. Gửi Sếp ảnh so sánh + preview; duyệt → `--final` + `qa --final` + `hear`.

**Chữ Trung BẬT / NẢY / CHỚP lúc vào** (sticker hook — đo từng khung 0379: chữ CHỚP đúng 1 khung ở 0,833s và 2,200s,
tắt / phóng to nhoè 3 khung, rồi vào lại và nảy ~0,3s; dòng 3 còn "nhân bản" mảnh chữ ra sát mép trái, phải, đáy khung):
hình chữ nhật cuối + badge không che nổi quãng này. Máy tự xử lý: tìm khung đầu tiên số nét trong ô bao rộng vọt khỏi
mức nền → cả quãng tới lúc chữ đứng yên **giữ hình SẠCH của khung ngay trước đó** trên vùng ô bao rộng (không nhoè, không
lộ chữ; vùng đó đứng hình 0,3–0,45s), badge + chữ Việt bật lên đúng lúc chữ Trung gốc bật lên. `clean.json` ghi mỗi ô
`pre` (số khung giữ hình) + `held` (có khung sạch không; chữ vào đúng mối cắt cảnh → `held: false` → nhoè vùng rộng).
⛔ **QA lấy mẫu 0,5s KHÔNG bắt được quãng này** (bản QA "ĐẠT sót 0" vẫn lộ nguyên một dòng chữ Trung 5 khung) → với
MỖI ô sticker phải cắt khung dày **mỗi 0,07s trong ±0,5s quanh `t0`** của nó (và quanh `t1`), xem ở cỡ thật, đối chiếu
với cùng khung của nguồn. Lệch thì in số đo của bộ dò (số nét từng khung) rồi mới sửa — đoán mò 2 vòng không ra.

Bẫy V2 đã gặp (11/11, job 0374 — badge nhóm):
- **Dòng Trung có đuôi chữ Latin / số** ("…产出的CO₂", "304不锈钢", "5L"): ô phân tích chỉ ôm phần chữ Hán → phần đuôi
  nằm ngoài vùng dò → xoá hụt, còn lơ lửng "O₂" cạnh badge. QA chữ Hán KHÔNG bắt (không phải chữ Hán). Nới ô trong
  direct.py: `by_id["o3"]["clean"] = {"box": [x, y, w rộng hơn, h]}` rồi soát khung.
- **Hai dòng nối tiếp cùng chỗ "thấy" nét của nhau** → mốc xoá chồng ~1s, không gom được thành thanh. Máy giờ chia ranh
  theo dòng nào khớp nét hơn + dừng ở mối cắt cảnh sát mốc phân tích; nếu `clean.json` vẫn ra nhiều nhóm `single` chồng
  giờ ở cùng một chỗ → xem lại `start` / `end` các ô đó.
- **Nhãn nhỏ giữa cảnh nhiều chi tiết** (hạt cà phê, vải) — nét cảnh giống nét chữ → từng bị xoá sớm 0,47s lên cảnh trước;
  đã chặn theo mối cắt cảnh. Vẫn phải soát khung trước / sau mối cắt của ô đó.
- **Đoạn thuyết minh cụt < ~1,5s** ("Cách dùng rất gọn." 0,9s): cổng nghe lại không ổn định (lần khớp 0,5 vì nghe ra cả
  câu bịa, lần 0,9) và hay bị cắt dính sang đoạn bên → gộp vào câu kế, đừng nới ngưỡng. Câu kết bằng dấu phẩy nối sang
  đoạn sau cũng bị cắt lệch → mỗi đoạn là một câu trọn.
- Từ dễ nghe nhầm tr / ch ("trọn hương" → "chọn hương") cộng tên brand ở câu chốt ngắn → mảnh rớt dưới 0,8 → đổi từ.

Bẫy V2 đã gặp (11/11, job 0379):
- Sticker to bật vào làm cả khung đổi mạnh → từng bị coi là "mối cắt cảnh" rồi chặn nhầm thời điểm xoá; giờ mối cắt đo
  NGOÀI vùng chữ đang hoạt động. Vùng giữ hình / vùng xoá chạm biên khung thì mép đó phải đục (mép mềm 10px từng để lọt
  mảnh chữ sát mép khung).
- Vá nền từng dòng phụ đề (nội suy + nhoè) sạch chữ nhưng **vẫn thấy vệt mờ** → Sếp không duyệt; chỉ dùng `fill`
  khi Sếp chủ ý không muốn khung dải. Chữ Việt không nền đặt trên mảng nhoè của hook cũng bị chê → luôn có badge.
- Chữ Trung **bay vào / bật từng chữ** nằm lệch chỗ dòng chính vài khung; ô Gemini dư tới 2–3 lần chiều cao chữ thật →
  máy dò nét từng khung, đừng nới ô tay.
- Vùng nhoè to (sticker) "thấy nét" của cảnh kế → máy tự dừng ở mối cắt cảnh sát mốc; nếu badge còn dính sang cảnh
  sau, ghi `overlay["clean"] = {"end": <giây>}`.
- Badge nghiêng có thể thò xuống khung dải → render báo "bị badge … lấn" → dời `x` khối dưới hoặc cho hiện sau.
- `preview.mp4` / `final.mp4` đang mở ở trình xem (Sếp đang coi) → ffmpeg báo `Permission denied`: render bản còn
  lại (`--final` ↔ preview) hoặc nhờ Sếp đóng file; đừng xoá file.
- ⚠ Mới chạy thật 2 job giao (PHALEDO 3:4: 0379 khung dải + badge xoay · 0374 badge nhóm). Dạng #6 (chữ quá lớn) và
  #7 (chữ có sẵn nền) mới có LUẬT, chưa gặp video thật. GDP / LTENG VN / LTENG HCM mới có ẢNH DEMO bộ nhận diện trên nguồn 0379
  (job thử `_skin-*`, chưa có bản giao nào dùng bộ mới — bản `gdp-0379-v2` render TRƯỚC khi có bộ nhận diện, phải render
  lại). Chưa thử: chữ Trung ở ĐỈNH, nguồn 9:16 → lần đầu gặp phải soát kỹ và báo Sếp.

## Quy trình một video (bản cũ — ô mẫu shop; vẫn dùng khi Sếp muốn nhãn theo mẫu HTML của shop)

1. `vs.py new inbox\<file>.mp4 --id <brand>-<slug>` → `jobs/<id>/`.
2. `vs.py analyze <id>` — Gemini quét khung mỗi 0,5s: chữ Hán + ô + `kind` (overlay = đồ hoạ hậu kỳ /
   scene = in trên vật thể) + góc nghiêng (tính từ 2 đầu dòng) + chép lời Trung → `edl.draft.json`.
   Gom lại không tốn token: `--regroup`.
3. **Đạo diễn = viết `jobs/<id>/direct.py`** (mẫu đủ bộ: `jobs/gdp-ke-nha-tam-01/direct.py`) sinh `edl.json`:
   - `edl.shop` = mã shop (`marketing_shop.name`, vd `phaledo_official`) → tài nguyên `assets/shops/<shop>/`
     (mẫu chữ, màu, logo…). Hỏi Sếp video làm cho shop nào nếu chưa rõ. `vs.py templates <shop>` xem mẫu + `_preview.png`.
   - Mỗi ô đồ hoạ: `template` (chọn từ manifest: caption / hook / badge / info…), `text_vi`, `sub_vi`.
     **Chọn mẫu có sẵn, không tự sáng tạo kiểu mới.** Shop chưa có mẫu (`vs.py shops` báo THIẾU) → báo Sếp, đừng bịa.
   - Gemini hay tách 1 dòng thành nhiều ô → `merge()`; tra ô bằng `find()` khớp gần đúng (chữ gốc lệch giữa các lần chạy).
   - `narration.paragraphs = [{at, text}]` — kịch bản thuyết minh (luật bên dưới).
   - `audio = {mode: "narration", music: "music.mp3", voice_lufs: -14, music_lufs: -27}` · `edl.logo = {"enabled": true}`
     · `edl.outro = {"enabled": true}` nếu shop có video outro.
   - `edl.motion = {"mode": "auto"}` (Sếp 23/10, mặc định job mới, chỉ 1 dòng): AUTO lập kế hoạch nhận diện động —
     1 brand reveal đúng brand (gọn ở dải trên) + accent trong budget nếu có quãng trống; **logo thường trực nhỏ ở góc hiện
     suốt video chính, chỉ tạm ẩn ĐÚNG KHOẢNG animation thay logo chạy rồi tiếp quản**; watermark chữ → **watermark động**
     (xuất hiện → chìm dần → trượt đổi chỗ mỗi ~6s như cũ). Chèn tay / tắt: skill `gdp-video-motion`. Job cũ không khai = flow cũ.
   - `edl.reveal = {"mode": "auto"}` + `edl.poster = {"mode": "auto"}` + `audio.sfx: true` (Sếp 29/10, mặc định job
     mới): chữ hiện dần + khối nhấn `*...*` + ảnh bìa + tiếng khẽ — luật ở mục "Chữ hiện dần, khối nhấn, ảnh bìa". Job cũ
     không khai = render y như trước. Mẫu đủ bộ: `jobs/gdp-taobao-0416-fx/direct.py`.
   - **Chốt HOOK trước** (2 giây đầu quyết định người xem có ở lại): ô chữ đầu + câu thuyết minh đầu nói ngay sản phẩm
     là gì / giải quyết gì, đừng mở bằng câu chung chung.
4. `vs.py music <id>` (Lyria 3.5, không lời; nghi có lời hát thì `vs.py hear music.mp3` 1 lần) → `vs.py narrate <id>`.
5. `vs.py render <id>` (preview) → `vs.py qa <id>` (Codex soát) phải **ĐẠT (sót 0)**; chưa đạt → `vs.py patch <id>` → render/qa lại.
   Job có `edl.motion`: render in kế hoạch (animation chọn/bỏ + lý do, logo hiện khoảng nào, watermark từng pha —
   `motion_plan.json`); `qa` thêm mục **animation** (số đo: clip alpha đạt, logo thường trực liên tục, watermark đúng vòng
   đời, không 2 logo chồng / 2 watermark, chồng chữ ≤4%, thời lượng + tiếng) — phải đạt cả hai. Soát mắt nhanh:
   `vs.py motion storyboard <id>` (ảnh các mốc reveal / logo tiếp quản / watermark / outro).
6. `vs.py audiocheck <id>`: cả bản −14 ±0,5 LUFS (render TỰ bù sau khi trộn: đo ebur128 → bù dB → chặn đỉnh 0,75
   `level=0`, tối đa 3 vòng), đỉnh ≤ −1 dBFS, nhạc ở khoảng không giọng ≈ −21…−25 LUFS (mặc định `music_lufs: -27`).
7. Gửi Sếp (SendUserFile) ảnh so sánh + preview. Sếp duyệt → `render --final` + `qa --final` + `audiocheck --final`
   + nghe lại `final` MỘT lần bằng `vs.py hear` (đủ lời, 1 giọng, không tiếng Trung, không đè/cụt) + soát khung bằng
   `vs.py look` — không viết thêm script review gọi Gemini.
8. Viết `jobs/<id>/caption.txt` (Sếp 29/10): 1–2 câu đăng kèm video (Shopee/TikTok) + 3–5 hashtag, đúng giọng shop,
   CHỈ dùng sự thật có trong video gốc / SKU (không "giảm giá", không thông số bịa), không "Hãy cùng khám phá…".
   Gửi Sếp cùng final + `final.jpg` (ảnh bìa — tải lên làm cover khi sàn cho chọn).

## Chữ hiện dần, khối nhấn, ảnh bìa (Sếp 29/10 — học từ skill brag)

- **Hiện dần** (`edl.reveal = {"mode": "auto"}`, từng ô ép `"reveal": true/false`): NỀN ô vào/che chữ Trung y như cũ,
  chỉ CHỮ bên trong hiện lần lượt (từng chữ; câu dài 2–3 chữ/bước; xong trong ≤0,7s). Badge/callout không hiện dần
  (bật cả khối). **Đọc trước, hiệu ứng sau**: ô không đủ ~0,25s/âm tiết (tối thiểu 0,8s) sau khi hiện xong → tự hiện cả
  câu ngay. Ô vào với nền TRỐNG rồi mới ra chữ → không còn mờ chéo hai câu thành một khung nhoè.
- **Khối nhấn** `*cụm từ*` trong `text_vi`/`sub_vi`: nền màu `manifest.highlight` của shop (GDP vàng/đỏ sậm, badge GDP
  đỏ/trắng · LTENG VN trắng/xanh · LTENG HCM trắng/đỏ · PHALEDO vàng gỗ/đen), chữ nghiêng nhẹ, "bật" 1,08× một nhịp
  0,12s khi hiện. THƯA: ~1 khối / 2–3 ô, chỉ cụm đắt nhất (công dụng, chất liệu, điểm khác biệt) — nhấn mọi ô = không nhấn
  gì. Dấu câu dính liền sau khối (`*bừa bộn*,`) tự dính, không chèn khoảng trắng. Không dùng `*` cho việc khác.
- **Tiếng hiệu ứng** `audio.sfx: true` (chỉ mode narration): "thịch" ấm khi hook/badge/callout vào + "tách" nhỏ khi khối
  nhấn bật; ≥0,3s cách nhau, ≤16 tiếng/video, nằm dưới nhạc (file Kenney CC0 `assets/sfx/`). Đo 29/10: cả bản vẫn
  −14,2 LUFS, đỉnh −2,1 dBFS.
- **Chữ hiện ngắn**: render in `⚠ chữ hiện ngắn: '…' đọc được Xs, cần ~Ys` (+ `layers.json.read_warnings`) → rút bản
  dịch / gộp ô, KHÔNG kéo dài ô (mốc theo chữ Trung). Đo 22–29/10: 7% ô của 40/94 job dính.
- **Ảnh bìa** (`edl.poster = {"mode": "auto"}`; `{"at": giây}` chọn tay): khung đã ghép lúc chữ đứng yên của
  ô hook (không có thì badge, rồi ô đầu) → `final.jpg`/`preview.jpg` + THAY khung 0 của mp4 (sàn/Zalo lấy khung 0 làm ảnh
  chờ; thay 1 khung, độ dài + tiếng giữ nguyên). `layers.json.poster` ghi giây + lý do; chưa đẹp thì chọn tay.

## Luật chữ (Sếp chốt 20/10)

- ⛔ Chữ TRONG CẢNH (sản phẩm, bao bì, nhãn, chai lọ, phụ kiện, đạo cụ) **giữ nguyên** — không đè, không mờ.
- Chữ đồ hoạ → đè ô đục 100% theo mẫu brand. Dòng chữ xoay chéo → **MỘT ô xoay cùng góc** (mẫu `nowrap`), không chia đôi.
- Chữ Việt ≥ 3% chiều cao khung. Renderer KHÔNG để trình duyệt tự bẻ dòng (Sếp chê "…khoan, Chịu / lực tốt"):
  một dòng không đủ cỡ → câu CÓ dấu ngắt (`·` `.` `!` `?` `;` `:` `,`) tách 2 dòng tại dấu gần giữa nhất, bỏ dấu nối,
  viết hoa đầu dòng 2 ("Kệ treo tường không cần khoan" / "Chịu lực tốt"); câu KHÔNG dấu ngắt → nới ngang trước
  (≤92% khung), hết cỡ mới chia đôi cân theo từ (≥5 từ). Tự quyết chỗ xuống dòng: ghi `\n` trong `text_vi`.
- Mẫu có đệm trái/phải ≈0,45–0,6× chiều cao ô, trên/dưới ≈0,12–0,16× (Sếp 20/10: chữ không được sát viền).
  Ô sticker quá vuông → "không vừa mẫu": cách xử lý ở "Bẫy đã gặp". Mốc `start`/`end` sticker phải kiểm khung ±0,4s.
- Dịch theo nghĩa bán hàng, ngắn hơn bản gốc. KHÔNG thêm công dụng/thông số không có trong video gốc hoặc dữ liệu SKU;
  câu tuyệt đối làm mềm ("hạn chế gỉ sét" thay "không gỉ") và liệt kê cho Sếp xác nhận.

## 1 video → nhiều shop (Sếp chốt 20/10)

- Phân tích MỘT lần (job gốc). Mỗi shop một job riêng `<shop-ngắn>-<slug>`: chép `source.mp4`, `meta.json` (đổi `id`),
  `analysis.json`, `edl.draft.json`, `music.mp3` từ job gốc — KHÔNG analyze lại. Viết `direct.py` riêng cho shop.
- **Đa dạng nội dung**: cùng SỰ THẬT sản phẩm (chỉ lấy từ video gốc/SKU) và cùng mốc cảnh, nhưng câu chữ, cách hành văn,
  phong cách PHẢI khác giữa các shop (không cần khác quá rõ, nhưng không được chép lại): câu mở đầu (hook), câu chuyển ý,
  cách liệt kê công dụng, câu kêu gọi mua, nhịp câu (ngắn dứt khoát vs mềm mại) — theo `shop.json.tone`:
  · GIADUNGPLUS: thân thiện, gần gũi, đời thường (nói chuyện như người nhà).
  · LTENG (VN + HCM): bán hàng, dứt khoát, nhấn lợi ích chịu lực / lắp nhanh / bền; VN và HCM cũng phải khác nhau.
  · PHALEDO: cao cấp, tinh tế, tối giản; nhấn chất liệu, sự gọn đẹp.
  Chữ đè (text_vi) cũng nên đổi cách nói cho hợp tone (vẫn ngắn). Trước khi narrate: `vs.py siblings <id>` → độ giống
  thuyết minh với mọi bản khác < ~0,5 và không trùng câu mở đầu / câu chốt.
  `siblings` còn liệt kê **từng câu trùng ≥0,75** (⚠) — câu trùng 100% giữa 2 shop cùng brand phải viết lại; câu fact
  ngắn gần giống (0,75–0,9) chấp nhận được. Thuật ngữ được phép đổi cách gọi nhưng phải rõ nghĩa (vd 上墙辅助贴 =
  "miếng dán cố định tạm" / "miếng giữ tạm" / "miếng hỗ trợ"); video có thao tác tuần tự thì đánh "Bước 1/2/3" được.
- Làm song song được: mỗi shop giao 1 subagent **Sonnet** với brief: job id, shop, job nguồn để chép, "dùng skill
  gdp-video-localize", KHÔNG commit git, KHÔNG sửa `studio/` / `assets/` / job khác, gặp lỗi code thì dừng báo lại,
  báo số đo (narrate khớp/trễ/tràn, qa sót, audiocheck LUFS, logo góc, siblings) + toàn văn thuyết minh/chữ đè + chỗ skill
  mơ hồ. Đã thử 20/10 (2 bản LTENG VN + HCM song song): mỗi bản ~150k token, 5–9 phút, đạt mọi cổng, không phạm luật,
  văn phong khác nhau rõ. Người điều phối PHẢI tự chấm lại: `siblings` sau khi cả hai xong (agent song song không thấy
  bản kia hoàn chỉnh → còn câu trùng), soát ảnh khung (`vs.py look`), nghe lại 1 lần (`vs.py hear`), rồi mới gửi Sếp.
- **Cách điều phối chốt (4 video × 3 shop, 20/10)**: **1 subagent Sonnet / 1 VIDEO làm cả 3 shop**, chạy 3 video song song
  (~15–30 phút, 165–285k token mỗi agent). Giữ văn phong khác nhau giữa shop tốt hơn kiểu 1 agent/shop (agent thấy cả 3
  bản nên chủ động tránh trùng). Người điều phối vẫn PHẢI tự: soát ảnh khung (đủ mốc ±0,4s, xem "Bẫy đã gặp"), phóng góc
  logo xem đè dấu, chạy `siblings`, rồi mới gửi Sếp.
- Job chép nguồn không cần Sếp duyệt bản nháp → render thẳng `--final` được; vẫn qa/audiocheck/soát khung đầy đủ.
- TTS mỗi lượt dài ngắn lệch ~±1s → mỗi đoạn chừa ~10% thời lượng cảnh; báo trễ/tràn thì rút chữ đoạn trước.

## Giọng đọc theo shop (`shop.json.voice`, Sếp chốt 20/10)

- GIADUNGPLUS = Kore (nữ, chắc — giọng đang dùng) · LTENG VN = Puck (nam, tươi) · LTENG HCM = Charon (nam, chắc, khác
  VN) · PHALEDO = Sulafat (nữ, ấm). `narrate` tự lấy giọng shop; ép tay bằng `edl.narration.voice`. Đừng ghi `voice`
  trong direct.py trừ khi Sếp yêu cầu giọng khác.

## Luật thuyết minh (Sếp chốt 20/10)

- KHÔNG đọc lại từng câu phụ đề. Viết **một bài liền mạch** bám cảnh / lời Trung: mở bằng vấn đề của khách →
  giới thiệu brand + sản phẩm → công dụng theo đúng thứ tự cảnh, có câu chuyển ý → hướng dẫn (nếu video có) → câu chốt brand.
- Mỗi đoạn một `at` = giây bắt đầu cảnh tương ứng. Ngân sách ≈ 3,4 âm tiết/giây của khoảng cảnh; `narrate` báo
  "trễ"/"tràn" → gộp/rút đoạn hoặc lùi `at` (Sếp chấp nhận lệch ≤ ~0,5s).
- Đọc MỘT lượt TTS cho cả bài (một giọng, một tông) → cắt tại khoảng lặng thật → đặt theo `at`. Không ghép nhiều lượt TTS.
- ⛔ TTS gửi ĐÚNG văn bản, không kèm chỉ dẫn giọng điệu: có chỉ dẫn là model đọc tiếp/bịa (đã bịa "khoan bê tông",
  "miễn phí vận chuyển"). Cổng kiểm ngược (cả bài ≥0,9, từng mảnh ≥0,8) bắt buộc — không nới.
- Số viết chữ số ("48 đến 72 giờ").
- Tên brand: viết bình thường trong kịch bản (PHALEDO…); `studio/voice.spoken()` tự đổi sang cách đọc Sếp chốt
  trong `assets/pronunciation.json` trước khi gửi TTS: **PHALEDO → "Pha lê đô" · GIADUNGPLUS → "Gia Dụng Pờ Lớt" ·
  LTENG → "Lờ teng"**. Brand/tên riêng mới → hỏi Sếp cách đọc rồi thêm vào file đó.
- TTS mỗi lượt đọc hơi khác (tốc độ, cách nhấn tên riêng). Lượt đọc được cache theo nội dung (`narration/take_<hash>.wav`):
  lượt nào đạt thì giữ, chỉnh mốc `at` không làm đọc lại; đổi chữ kịch bản = đọc lượt mới → kiểm lại từ đầu.
- **TTS dự phòng (21/10)** — `voice.TTS_CHAIN`, tự nhảy, không cần lệnh riêng: 3.1-flash-tts-preview (chỉ 100 req/24h)
  → gemini-3.8-flash-tts → tokenrouter `openai/gpt-audio-mini` → `openai/gpt-audio` (đang bị nhà cung cấp chặn 403).
  Hết quota ngày/402/403 → bỏ model cả lượt chạy; 429 theo phút → đợi 61s thử lại. Giọng gpt-audio = `voice.openai`
  trong shop.json (GDP coral · LTENG VN verse · LTENG HCM cedar · PHALEDO marin). `narration.json.model` ghi model đã
  đọc; khác model chính → `narrate` cảnh báo **"model DỰ PHÒNG"** → phải nghe lại trước khi giao. Đo 21/10:
  gpt-audio-mini đọc tiếng Việt kém Gemini (cả bài khớp 0,90 vs 0,998; câu ngắn có brand chỉ 0,73, từng nuốt
  "Lên đơn ngay!") → mảnh <0,8 thì viết câu chốt dài hơn / tách brand khỏi câu cụt, hoặc chờ quota Gemini hồi
  (đầu ngày theo giờ Mỹ ≈ 14–15h VN) rồi xoá `narration/take_*` để đọc lại.

## Tài nguyên theo SHOP (`assets/shops/<shop>/`, chuẩn: `assets/shops/README.md`)

- Theo SHOP, không theo brand (2 shop cùng brand có thể khác màu/logo). Mỗi shop: `shop.json` (brand, bảng màu, giọng
  văn, `templates_from`, logo/intro/outro, nguồn prod) · `logo/` (logo.png, logo-white.png, logo-dark.png, icon.png,
  logo.svg) · `intro/intro.mp4` · `outro/outro.mp4` · `templates/` (mẫu HTML + manifest) · `music/` · `watermark/` ·
  `fonts/` · `reference/` · `motion/` (tuỳ chọn, animation riêng shop). `vs.py shops` = bảng tình trạng. Shop mới:
  `tools/init_shop.py <mã>`. Animation chung theo brand: `assets/motion/`, cách dùng riêng shop: `shop.json.motion`.
- Shop chưa có mẫu riêng mượn qua `templates_from` (3 shop PHALEDO phụ mượn `phaledo_official`; lteng_tiktok chưa có).
- Nhận diện Sếp chốt 20/10 (đã có mẫu caption/hook/badge/info, `shop.json.fonts` + `style`):
  · `giadungplus_official`: đỏ/trắng, **UTM Avo** Bold+Regular mọi chỗ; thêm `outline-black` / `outline-red`.
  · `phaledo_official` (+ `phaledo`): tone tối, chữ trắng bóng nhẹ, **Averta** mọi chỗ.
  · `lteng_vn`: xanh dương gradient (brand kit prod 40°), **UTM Avo**.
  · `lteng_hcm`: đen/đỏ sậm, tiêu đề **UTM HelvetIns**, chữ thường **UTM Avo**; thêm `outline-black` / `outline-red`.
- Mẫu `covers: false` (chữ viền, KHÔNG nền) chỉ để CHÈN CHỮ MỚI (CTA, nhấn ý) — renderer chặn nếu dùng che chữ Trung.
- `manifest.replace`: UTM Avo/HelvetIns thiếu `· – — •` → renderer thay ` · ` → ` - ` (thay `, ` từng ra "tường, Chịu").
- ✅ **MẶC ĐỊNH CHO MỌI VIDEO (Sếp duyệt 20/10):** hiệu ứng ô chữ (tự bật) + watermark trôi (theo `shop.json`) + logo chính
  + outro có sẵn của shop. KHÔNG tắt những thứ này trừ khi Sếp yêu cầu. Lower third / callout là TUỲ CHỌN: thêm khi có cảnh
  hợp (lower third 1 lần ở cảnh giới thiệu; callout 1–2 cái ở cảnh máy đứng yên, chỉ vào công dụng có trong video).
  **Từ 23/10 thêm `edl.motion = {"mode": "auto"}`**: brand reveal (điểm nhấn) + logo THƯỜNG TRỰC (luôn có, chỉ tạm ẩn
  trong lúc reveal) + watermark động (thay chữ: xuất hiện → chìm dần → trượt đổi chỗ như cũ) + accent khi có quãng trống.
- **Hiệu ứng ô chữ** (`studio/motion.py`, tự động): mặc định caption/info = trượt lên, hook/badge/callout = bật phóng,
  lower third = trượt ngang; ép bằng `anim` ("fade" | "slide-up" | "slide-right" | "pop" | "none") trên overlay/extra.
  ⛔ Luật che phủ: ô che chữ Trung VÀO SỚM 0,25s để đục 100% đúng lúc chữ Trung hiện; ô bắt đầu ~0s không có hiệu ứng vào
  (không thể mà không lộ). Chuyển nhãn cùng chỗ = nhãn mới đè lên nhãn cũ (KHÔNG mờ chéo — lộ ~25% chữ Trung). Mờ dần khi
  tắt chỉ khi không có nhãn khác vào thay chỗ. Morph co giãn khung: KHÔNG làm (tốn công, lợi ích nhỏ).
- **Phần tử CHÈN MỚI** `edl.extras` (mẫu `covers:false`, không bao giờ dùng che chữ Trung):
  `{"template": "lower-third", "text", "sub", "start", "end", "position": "lower-left"|"upper-left"}` ·
  `{"template": "callout-left"|"callout-right", "text", "target": [x, y], "start", "end"}` — `target` = điểm trên sản phẩm
  (pixel khung gốc; cắt khung kèm lưới toạ độ để chọn). Render đo ORB xem CAMERA có làm điểm dời không (> ~2% khung → ⚠);
  đồ được thêm/tay cử động trong cảnh không tính. Callout chỉ đặt ở cảnh máy đứng yên; 1–2 callout/video là đủ.
- **Watermark chống lấy cắp** (`studio/watermark.py`, theo `shop.json.watermark`: BẬT cho cả 5 shop — GDP, LTENG
  VN/HCM, Phaledo (Sếp bật Phaledo 20/10 dù brand kit prod tắt cho ảnh); `edl.watermark` ghi đè): chữ thương hiệu mờ 12–15%, rộng 40% khung (Phaledo 30% — Sếp chê to; chỉnh `width_pct`), đổi chỗ êm mỗi ~6s trong vùng giữa, né ô chữ +
  góc logo, nằm DƯỚI ô chữ, không có trên outro. Nói thật với Sếp: không watermark nhìn thấy nào chống tuyệt đối (công cụ
  xoá AI vẫn xoá được) — chỉ làm khó: logo dán tĩnh/cắt góc không che hết; muốn xoá phải bám từng khung.
  `watermark/watermark.png` của shop (nếu có) dùng thay chữ. **Job có `edl.motion`** → watermark ĐỘNG theo
  `shop.json.watermark.motion` (GDP `gdp-ghost-smile`, LTENG `lteng-ghost-signature`, PHALEDO `phaledo-refraction-sweep`
  giữ tại 2,45s) thay chữ: xuất hiện → chìm dần → trượt êm đổi chỗ mỗi `period` ~6s như chữ cũ (chỉ sau khi chìm xong) →
  mờ hẳn trước outro, xa logo góc; `edl.motion.watermark = false` để giữ chữ trôi cũ.
- **QA / soát mắt BỎ QUA OUTRO**: `qa` chỉ kiểm phần video chính (`meta.duration`, báo cáo `outro_skipped`); khi soát
  khung đừng lấy mốc nằm trong outro (video có sẵn của shop, không cần kiểm lại).
- **Logo chính** (Sếp 20/10: đã đưa logo thì phải có trên video): `edl.logo = {"enabled": true}` → `studio/logo.py`
  đặt logo `shop.json.logo.files.primary` rộng 22% khung, cách mép 3%, suốt phần video chính (KHÔNG đè outro), vẽ trên
  cùng. Góc trên-trái/trên-phải MÁY TỰ CHỌN theo video: điểm = chồng ô chữ (đè + trong cảnh, diện tích × thời gian) ×10
  + độ rối Canny trên 12 khung; render in lý do, lưu `logo.json`. Ép tay: `position`, đổi file: `file_key`, mờ: `opacity`.
  Mặc định BẬT cho mọi job có shop đã có logo. **Job có `edl.motion` (V2, Sếp 23/10)**: logo THƯỜNG TRỰC nhỏ hơn + sát mép
  trên hơn (`shop.json.logo.persistent`: GDP 15% · LTENG 18–19% · PHALEDO 20% bề rộng khung 3:4, lề trên 3% chiều cao, đo
  phần logo thấy được); brand reveal (vd Roll & Smile) chạy thì logo chỉ TẠM ẨN đúng khoảng đó rồi hiện lại tới hết video
  chính — ⛔ không tắt logo cả video. `edl.motion.keep_logo = true` = không ẩn cả lúc reveal.
- **Outro = video Sếp đưa sẵn** trong `assets/shops/<shop>/outro/` (⛔ KHÔNG tự dựng outro — Sếp chốt 20/10).
  `edl.outro = {"enabled": true}` → `studio/outro.py` lấy `shop.json.outro.file`, không có thì file video đầu tiên trong
  thư mục; không có file → báo lỗi, đừng tự làm. Nối sau video chính (scale giữ tỉ lệ, viền đen nếu lệch). Đang có
  (20/10): GDP `GDP Outro v2.mp4` (1080×1440, 3,8s) · LTENG VN + LTENG HCM `LTENG Outro.mp4` (1440×1920, 3,7s) — đều
  3:4, KHÔNG tiếng · PHALEDO `PHALEDO Outro v2.mp4` (1440×1920, 3,7s — 11/11: bản 0379 cũ tắt nhầm, Sếp nhắc "vẫn có
  outro theo shop chứ không bỏ"). Thuyết minh/nhạc tự kéo qua outro → câu chốt brand đặt `at` ≥
  thời lượng video để đọc TRÊN outro. Outro có tiếng riêng: hiện CHƯA trộn — làm khi gặp. Đổi cùng video sang shop khác: chép job (source, analysis, edl.draft, music, direct.py) + sửa
  `shop` / tên brand trong thuyết minh — không cần phân tích lại (vd `lteng-vn-ke-nha-tam-01`, `lteng-hcm-ke-nha-tam-01` chép từ `gdp-ke-nha-tam-01`).
- Logo: tên file theo Sếp đặt, khai trong `shop.json.logo.files` (`primary` dùng mọi nền; `on_dark` cho nền tối; `on_light`; `icon`).
- Kiểm font tiếng Việt: `tools/check_font_vi.py` (Averta, BeVietnamPro, UTM Avo, UTM HelvetIns đều đủ dấu).
- Hợp đồng HTML (`#label` `--w/--h`, `#text/#sub` `{{text}}/{{sub}}`, `--fs`, nền đục, font local `../../../fonts/`,
  không JS, `nowrap`). Renderer = Chrome đã cài qua Playwright (`channel="chrome"`).
- Mẫu mới: Sếp thiết kế bằng Claude Design → xuất HTML → Claude sửa cho đúng hợp đồng → `assets/shops/<shop>/templates/`
  + manifest → `vs.py templates <shop>` soát ảnh trước khi dùng. Màu lấy từ `shop.json` (chép từ `marketing_shop.brand_kit` prod).
- Logo/watermark gốc nằm trên prod (`shop.json.prod.brand_logo`, đường `shop/brand-kit/...`) nhưng KHÔNG phục vụ qua
  `https://giadungplus.store/media/` (404) → Sếp thả file vào `logo/`, đừng đoán URL.

## Bẫy đã gặp

- Gemini báo số góc theo trục ảnh → ngược dấu; dùng 2 đầu dòng (`left/right`) để tính góc.
- Gemini liệt kê cả chữ Việt vào "chữ Trung" → lọc cứng dải Unicode Hán tự (`has_cjk`).
- QA Gemini không ổn định với chữ nhỏ/mờ (cùng chỗ đọc ra chuỗi khác) → dựa vào `kind` + ngưỡng cỡ chữ ≤2,5% khung.
- `patch` chỉ ghép khi CÙNG chữ gốc (từng kéo ô hook hiện tới 39s vì nhãn nhỏ "nằm gọn" trong ô lớn).
- Sidechain ducking nén nhạc gần như mất → trộn theo LUFS cố định, không ducking.
- Taobao CDN trả HTTP 490 (chống hotlink) → không lách; video do Sếp/NCC đưa.
- Font: `assets/fonts/<Họ font>/` (BeVietnamPro, Averta, UTM Avo, UTM HelvetIns — Sếp sắp 20/10). Chrome thiếu font sẽ
  LẶNG LẼ thay font khác → renderer ép tải mọi @font-face, lỗi là dừng (`tools/test_font_gate.py` kiểm cổng này).
  Averta là font Latin — kiểm đủ dấu tiếng Việt trước khi dùng cho chữ Việt; UTM Avo từng thiếu glyph •/—.
- `.NET` trong PowerShell hiểu đường dẫn tương đối theo thư mục UNC của phiên → dùng Edit tool hoặc đường dẫn tuyệt đối.

Bẫy làm thật 4 video × 3 shop (20/10) — đều phải tự soát trong `direct.py`, agent không soát là lỗi lọt:

- **Mốc `start`/`end` của sticker lệch vài trăm ms**: Gemini hay báo `start` muộn / `end` sớm → chữ Trung lộ lúc nhãn Việt
  vào/tắt (qa trên khung 0,5s không bắt hết). Cắt khung nguồn **±0,4s quanh MỖI mốc** của từng ô sticker, xem bằng mắt rồi
  chỉnh `start`/`end` trong `direct.py` (vd `jobs/gdp-gia-treo-dep-01` o5 `end` 4,22 → 4,6).
- **Logo góc trên đè DẤU tiếng Việt** của nhãn sát góc (logo cao ~22..94px, logo HCM đáy 94px; từng ra "ĐỔI" → "ĐÔI").
  Soát từng nhãn nằm sát góc logo trên khung đã phóng. Sửa: thu `box` về sát chữ Hán thật (soát lưới toạ độ) để chữ hạ
  xuống dưới logo, hoặc dịch tâm ô sang phải; đừng để dấu nằm trong vùng logo.
- **"không vừa mẫu"**: mẫu hook/badge có đệm ngang ≈0,5× chiều cao; ô sticker Gemini thường gồm cả tia/sao nên quá vuông.
  Sửa: thu `box` về phần chữ, rút chữ Việt, hoặc `\n` 2 dòng. Ô nghiêng <6° → đặt `angle: 0` để renderer được nới ngang
  (ô xoay chỉ nới tối đa 1,25×).
- **Dấu câu trong caption**: có `,` `.` `?` là renderer tách 2 dòng và nới ô rất rộng. Muốn 1 dòng thì bỏ dấu.
- **Phụ đề là nửa sau của câu** (chữ thường đầu) vẫn hiện riêng trên màn → viết hoa chữ đầu.
- **Gemini trả chữ lỗi mã hoá** (vd "䄀䄀䄀䄀") **hoặc BỊA lời thoại** (video móc treo cửa ra "súng massage"). Khi đó tra ô
  bằng `by_id`, không dùng `find()` (khớp chữ gần đúng sẽ hỏng), và bỏ qua thoại bịa — kịch bản chỉ bám cảnh thật.
- **Lyria trả `candidates=None`** → `TypeError` trong `make_music`: lỗi tạm, chạy lại `vs.py music <id>` là được.
- **TTS đọc sai brand ở câu chốt ngắn** ("Lơ tơ mơ", "Lotte" thay "Lờ teng"): cổng kiểm ngược bắt được → đổi câu
  (dài hơn / đặt brand giữa câu), đừng nới ngưỡng cổng.
- **Đã biết (chưa sửa code)**: bộ chặn đỉnh 0,75 trong `_normalize_loudness` có thể để cả bản −14,6…−14,7 LUFS (thấy với
  giọng Puck/Charon) → `audiocheck` ra ngoài ±0,5. Ghi nhận, báo số đo thật cho Sếp; không tự vá code trong khi làm job.
