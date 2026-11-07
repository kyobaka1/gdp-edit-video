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

## Quy trình một video

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

## Luật chữ (Sếp chốt 20/10)

- ⛔ Chữ TRONG CẢNH (sản phẩm, bao bì, nhãn, chai lọ, phụ kiện, đạo cụ) **giữ nguyên** — không đè, không mờ.
- Chữ đồ hoạ → đè ô đục 100% theo mẫu brand. Dòng chữ xoay chéo → **MỘT ô xoay cùng góc** (mẫu `nowrap`), không chia đôi.
- Chữ Việt ≥ 3% chiều cao khung. Renderer KHÔNG để trình duyệt tự bẻ dòng (Sếp chê "…khoan, Chịu / lực tốt"):
  một dòng không đủ cỡ → câu CÓ dấu ngắt (`·` `.` `!` `?` `;` `:` `,`) tách 2 dòng tại dấu gần giữa nhất, bỏ dấu nối,
  viết hoa đầu dòng 2 ("Kệ treo tường không cần khoan" / "Chịu lực tốt"); câu KHÔNG dấu ngắt → nới ngang trước
  (≤92% khung), hết cỡ mới chia đôi cân theo từ (≥5 từ). Tự quyết chỗ xuống dòng: ghi `\n` trong `text_vi`.
- Mẫu có đệm trái/phải ≈0,45–0,6× chiều cao ô, trên/dưới ≈0,12–0,16× (Sếp 20/10: chữ không được sát viền).
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
- **Hiệu ứng ô chữ** (`studio/motion.py`, tự động): mặc định caption/info = trượt lên, hook/badge/callout = bật phóng,
  lower third = trượt ngang; ép bằng `anim` ("fade" | "slide-up" | "slide-right" | "pop" | "none") trên overlay/extra.
  ⛔ Luật che phủ: ô che chữ Trung VÀO SỚM 0,25s để đục 100% đúng lúc chữ Trung hiện; ô bắt đầu ~0s không có hiệu ứng vào
  (không thể mà không lộ). Chuyển nhãn cùng chỗ = nhãn mới đè lên nhãn cũ (KHÔNG mờ chéo — lộ ~25% chữ Trung). Mờ dần khi
  tắt chỉ khi không có nhãn khác vào thay chỗ. Morph co giãn khung: KHÔNG làm (tốn công, lợi ích nhỏ).
  **Từ 23/10 thêm `edl.motion = {"mode": "auto"}`**: brand reveal (điểm nhấn) + logo THƯỜNG TRỰC (luôn có, chỉ tạm ẩn
  trong lúc reveal) + watermark động (thay chữ: xuất hiện → chìm dần → trượt đổi chỗ như cũ) + accent khi có quãng trống.
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
  3:4, KHÔNG tiếng. Phaledo chưa có outro. Thuyết minh/nhạc tự kéo qua outro → câu chốt brand đặt `at` ≥
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
