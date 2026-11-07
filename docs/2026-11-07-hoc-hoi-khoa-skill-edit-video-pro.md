# Học cách xây "Skill Edit Video Pro" (mikelikedesign) → tách thành skill + template cho GDP

> Nguồn: trang bán Canva của mikelikedesign + **5 video mẫu** Sếp tải về `example/` (phân tích 07/11/2026).
> **Không mua** — chỉ học cách họ xây, rồi làm bản của mình.
> Ảnh từng giây + lời có mốc từng từ của mỗi video: `example/_phan-tich/<video>/` (`sheet_*.jpg`, `asr.json`).
> Trạng thái: **NHÁP — chờ Sếp chốt** mục 6.

---

## 1. Họ xây sản phẩm thế nào (kiến trúc rút ra)

```
                ┌───────────── LÕI DÙNG CHUNG ─────────────┐
 video gốc ──►  │ chép lời → cắt lặng/vấp → phụ đề → vùng an toàn │ ──► render (Remotion)
 + footage      │ chèn footage theo CÂU NÓI → QA → sửa từng cảnh │      │
 + yêu cầu      └───────────────────────────────────────────────┘      ▼
                         ▲ chọn 1 "PHONG CÁCH"                      CỬA SỔ EDITOR
                 s1 · m1/m2 · Blue 1 (mỗi gói = 1 bộ hình riêng)    (sửa chữ/đồ hoạ, không tốn token)
```

1. **Một lõi, nhiều "phong cách"**: s1, m1/m2, Blue 1 là **cùng một lõi** (cắt lời, phụ đề, vùng an toàn, chèn
   footage, QA), chỉ khác **bộ hình**: màu, phông, cách đặt phụ đề, kho đồ hoạ. Họ bán từng phong cách như một
   sản phẩm riêng, mỗi cái kèm video demo.
2. **Cửa sổ Editor**: AI dựng xong thì mở một giao diện có timeline và từng lớp (chữ, đồ hoạ, footage) để người tự
   sửa, khỏi phải ra lệnh từng chi tiết, không tốn token. Họ nói rõ trong video m2: AI làm khoảng 30 phút, người
   chỉnh tay thêm 5–10 phút.
3. **Chèn footage bằng câu nói**: người dùng thả footage và chỉ "đoạn nói câu X", không cần tìm giây.
4. **Sửa đúng cảnh lỗi**, không dựng lại cả video.
5. **Hướng dẫn quay** đi kèm: người ngồi giữa, mặt không quá to, chừa trống trên và dưới để đặt hình, nói theo kịch bản.
6. **Video quảng cáo chính là sản phẩm**: cả 5 video mẫu đều dựng bằng chính skill đó và nói về chính skill đó.
7. Ngoài ra có skill phụ "Kinetic Motion" (video chỉ có chữ động) và cuốn cẩm nang tặng kèm.

→ Mình **đã có lõi** (gdp-video-edit: Whisper mốc từng từ, cắt lặng giữ hơi thở, chữ động, Scene Library, QA,
CapCut). Thứ mình **thiếu là lớp "phong cách" đóng gói sẵn, kho đồ hoạ dày hơn và Editor**.

---

## 2. Phân tích 5 video

| File | Gói | Dài | Nguồn hình | Tiếng |
|---|---|---|---|---|
| `de1df44f…` → `s1` | Edit Video Pro **s1** | 76s | người nói + màn infographic toàn khung | giọng thật, 4,96 từ/giây, độ to −25 LUFS (nhỏ, chưa chuẩn) |
| `2ba8c93a…` → `m2_nguoi` | Edit Video **m2** (có người) | 49s | người nói + quay màn hình + đồ hoạ | giọng thật, 4,85 từ/giây, −14 LUFS |
| `9fafd4d9…` → `blue1` | Edit Video **Blue 1** | 98s | người nói + quay màn hình + **review sản phẩm tài trợ** | giọng thật, 5,09 từ/giây, −14 LUFS |
| `898b15c0…` → `m2_sp_a` | **m2 không người** (thuốc kẽm) | 49s | tay cầm hộp, vỉ ống, tờ hướng dẫn | **giọng AI**, 4,35 từ/giây, −16 LUFS |
| `fb1c3d87…` → `m2_sp_b` | **m2 không người** (điện mặt trời) | 52s | **flycam** khu nhà | **giọng AI**, 4,25 từ/giây, −14 LUFS |

**Nhịp chung**: lời vào ngay từ giây 0–0,19 (không có khoảng chết mở đầu). Ở video người nói, không còn khoảng
lặng nào dài quá 0,3s. Cứ **2–4 giây lại có một thứ mới hiện lên trên hình**: thẻ, chip, mục danh sách, con số.

### 2.1 s1: "Navy giải thích" (video kiến thức, công nghệ)
- Màu: nền xanh navy đậm, nhấn xanh ngọc và vàng; **icon 3D kiểu đất sét** (hộp, bóng đèn, đồng hồ).
- Tiêu đề góc trên: icon 3D, chữ đậm xanh ngọc, dòng phụ nghiêng nhỏ, gạch chân vàng; đổi bên trái/phải theo lời.
- Phụ đề: **1 dòng nhỏ, chữ trắng đậm, chừng 78% chiều cao**, từ khoá tô màu xanh ngọc.
- **Màn infographic toàn khung** (21–27s, 37–42s, 46–57s): lời vẫn chạy, hình người được thay bằng **avatar tròn
  phát sáng ở góc phải trên**. Bên dưới là eyebrow nhỏ ("TỪ FOOTAGE GỐC"), tiêu đề ("EDIT TỪNG LỚP"), rồi **các
  thẻ bước 01-02-03 dựng dần theo lời** (thẻ 01 có cả hình sóng âm). Có điện thoại giả minh hoạ vùng an toàn và
  ảnh chụp màn hình ChatGPT.
- **Thẻ ra mắt tên sản phẩm** (1:04): nền tím nhạt, người nói nằm trong khung bo góc, tên sản phẩm "EDIT VIDEO PRO"
  hiện lên từng phần.

### 2.2 m2 người nói: "Vàng–đen TikTok" (bán hàng, review)
- Màu hình **hạ bão hoà, tối, có viền tối 4 góc**; nhấn **vàng chanh** và trắng.
- Phụ đề **2 tầng**: một dòng trắng (ý dẫn) và **một dòng nhấn nền vàng chữ đen** (cụm khoá); đặt khoảng giữa khung,
  có lúc nhảy lên trên đầu.
- Đồ hoạ dạng **"đạo cụ giao diện"**:
  - 5 ngôi sao bật lần lượt; nút avatar "Mike → edit video → AI" nối bằng đường kẻ.
  - **Chip tính năng xếp lưới 2×2 dựng dần**: Typography / Graphic / Motion / Âm thanh.
  - **Ô nhập prompt** có chữ đang gõ, rồi chữ bị gạch ngang.
  - **Danh sách gạch dần** từng dòng (Prompt sửa từng chi tiết / Tốn thời gian / Tốn token).
  - Chữ "token" có **khung chọn kiểu phần mềm thiết kế** (4 núm kéo, con trỏ, kích thước).
  - Dải timeline vàng, góc quay "REC 00:21".
  - Điện thoại trồi lên, chữ "tiện!" to kèm lấp lánh.
  - **Kết: ô bình luận giả** (avatar, "tham khảo", tim đỏ, nút Đăng) để gọi người xem comment.
- Màn đen toàn khung ở chỗ chuyển ý (25–30s, 41–42s).

### 2.3 Blue 1: "Xanh kính mờ, chữ lai" (series kiến thức, phong cách tạp chí)
- **Chữ lai**: sans đậm trộn **serif nghiêng** ("gõ lệnh *ở đó*", "dùng *công cụ*"); từ khoá có hộp nền xanh.
- **Mở đầu series**: nhãn "series", dòng "những điều cần biết khi dùng", chữ "AI" to ghép "edit video".
- **Thẻ kính mờ toàn khung** cho câu tuyên bố ("thì đây là *4 điều*", "hãy setup thành *skill*").
- **Số chương to** 1–2–3–4 có vạch đứng mảnh, viết nghiêng ("1 | thứ nhất, chọn *đúng công cụ*").
- **Dãy ảnh nỗi đau xếp dần** (ba ảnh nhỏ: "video ra rất lỏ", "prompt từng bước", "vừa lâu vừa tốn token").
- **Logo xếp hạng** (Claude 1 · Manus 1 · ChatGPT 2), **checklist tick xanh dựng dần**.
- **Bố cục chia đôi nền sáng**: ảnh chụp màn hình GitHub ở trên, người nói trong khung bên dưới, chip "auto cut /
  bỏ khoảng lặng / chèn phụ đề".
- Khung ngắm mặt (4 góc), vạch ngang chỉ vùng trống "cả trên".
- **Đoạn review sản phẩm tài trợ (sạc UGREEN, 1:15–1:35)**: tên sản phẩm và số "150W → 160W" đếm lên, **đường dẫn
  chỉ thông số vào đúng cổng sạc**, chip thiết bị (MacBook / iPad / iPhone / Pocket 3), **thẻ đọc số công suất**
  (Tổng 71,9W · Cổng C2 69,3W). Đây đúng là thứ video sản phẩm GDP cần.
- Kết: 2 nút CTA ("link repo", "bộ skill").

### 2.4 m2 không người, sản phẩm cầm tay (thuốc kẽm)
- Footage điện thoại: tay xoay hộp, mở vỉ ống, lật tờ hướng dẫn. Không có người nói, giọng AI đọc kịch bản.
- **Cắt vùng nhãn thật thành thẻ nổi**: lấy đúng mảng bảng thành phần trên tờ hướng dẫn, phóng lên thành thẻ, **tô
  vàng dòng đang đọc**, kèm số to bên dưới ("50mg vitamin C", "tương đương **5,16mg kẽm**"). Nền phía sau tối và mờ.
- **Công tắc kiểu iPhone bật dần**: Miễn dịch, Vị giác, Phát triển của trẻ, Lành thương.
- Gạch một dòng ("một lợi ích đơn lẻ") để phủ định; nhãn tròn "2 dưỡng chất thiết yếu".
- Thẻ đối tượng/liều dùng cắt từ tờ hướng dẫn: "1–9 tuổi · 5ml một ngày" rồi "trên 9 tuổi · 5ml ngày 2 lần".
- **Kết: tên thương hiệu hiện từng chữ kiểu bảng đèn LED** trên nền thùng hàng xếp kín.

### 2.5 m2 không người, flycam (điện mặt trời)
- **Mở bằng câu hỏi**: nửa trên là thẻ sáng "Mỗi tháng nhà bạn trả bao nhiêu **tiền điện?**", nửa dưới là flycam.
- **Chữ lật kiểu bảng ga tàu** ("1 TRIỆU").
- **Biểu đồ cột lớn dần**: 2tr/1 tháng → 24tr/1 năm → 120tr/5 năm. **Thẻ hoá đơn** (Mỗi tháng 5 triệu, 5 năm,
  TỔNG 300 TRIỆU).
- **Vòng tròn vẽ tay và mũi tên chỉ vào mái nhà** trên footage thật ("áp mái").
- **Đồng hồ vòng tròn** "giảm khoảng 80", "70–80% mỗi tháng", chip ghi chú "tuỳ nhu cầu".
- **3 bước có icon nối nhau**: Tư vấn → Thiết kế → Thi công.
- Danh sách gạch ("Hoá đơn tháng này / tháng sau") rồi chốt bằng chip "Tiết kiệm nhiều năm tới".
- **Kết: tên thương hiệu phát sáng, có tia sáng và lấp lánh**, kèm dòng "tư vấn ngay hôm nay".

---

## 3. Ngữ pháp chung đáng học (áp được cho mọi video GDP)

1. **Đồ hoạ cũng dựng theo lời**, không chỉ có chữ: sao bật 1→5, chip 1→4, công tắc bật dần, danh sách gạch dần,
   cột biểu đồ lớn dần. Mỗi lần nhắc tới một ý là thêm đúng một phần tử.
2. **Mật độ**: cứ 2–4 giây có một thứ mới trên hình. Video của mình hiện thưa hơn (theo luật "ít mà tinh").
   Cách dung hoà: **giữ ít loại hiệu ứng** (2–3 loại mỗi video) nhưng **cho chúng dựng nhiều bước**.
3. **Ba tầng vị trí cố định**: tiêu đề hoặc thẻ ở vùng trên đầu; phụ đề ở giữa-dưới; người hoặc sản phẩm ở giữa.
   Hướng dẫn quay của họ sinh ra từ chính bố cục này.
4. **Nền tối và mờ khi thẻ hiện** (để thẻ nổi, đọc được trên mọi footage).
5. **Phụ đề 2 tầng**: dòng dẫn nhỏ màu trắng và dòng nhấn to màu nhấn. Mình đã có cú pháp `.` / `!` trong `c.cap`;
   cần thêm kiểu "nền vàng chữ đen" và kiểu "serif nghiêng".
6. **Đạo cụ giao diện** (ô nhập, công tắc, khung chọn, ô bình luận, hoá đơn, REC, điện thoại giả) làm ý trừu tượng dễ
   hiểu ngay, và dễ làm bằng HTML/CSS.
7. **Lấy chính sản phẩm và bao bì thật làm đồ hoạ**: cắt vùng nhãn thành thẻ, kẻ đường chỉ thông số vào đúng bộ
   phận, khoanh vẽ tay lên footage. Hợp với luật GDP "không bịa, bằng chứng thật".
8. **Kết bằng thương hiệu**: tên brand phát sáng hoặc hiện từng chữ, CTA giả giao diện (ô bình luận, nút).
9. **Định dạng series**: "series · phần 1", số chương to. Trùng với ý tưởng "Thẻ series Tập N" đã ghi trong
   `hieu-ung.html`.

---

## 4. Đối chiếu với kho GDP hiện có

| Họ dùng | GDP đã có | Cần làm |
|---|---|---|
| Tiêu đề góc có icon + gạch chân (s1) | C03 Tiêu đề ghim | thêm biến thể `icon` (icon 3D/đất sét) |
| Số chương to 1–4 (Blue 1) | C02 Thẻ chương | thêm preset `numeral` (số to + vạch + chữ nghiêng) |
| Thẻ kính mờ câu tuyên bố | C01 Từ khoá bật / C11 Câu trích | thêm nền `glass` (làm mờ footage toàn khung) |
| Danh sách tick / gạch / công tắc dựng dần | C04 Đếm & lật (một phần) | **làm mới: C13 Danh sách động** |
| Chip tính năng lưới 2×2 / chip thiết bị | không có | **làm mới: C14 Chip tính năng** |
| Cắt vùng nhãn thật + tô dòng | C08 Khung bằng chứng (ảnh trong khung) | **làm mới: C15 Soi nhãn** (crop, highlight dòng, số to) |
| Đường chỉ thông số vào bộ phận | C09 Soi chi tiết (1 điểm) | **mở rộng C09: nhiều nhãn chỉ** (= ý tưởng "Feature Spotlight") |
| Vòng vẽ tay + mũi tên trên footage | C09 (khoanh) | thêm kiểu nét `vẽ tay` |
| Cột lớn dần / đồng hồ % / hoá đơn tổng | C07 Con số nhảy | **mở rộng C07: `bars`, `gauge`, `receipt`** (= ý tưởng "Bóc tách con số") |
| 3 bước có icon nối nhau | C10 Các bước | thêm icon từng bước |
| Câu hỏi mở đầu nửa khung | không có | **C16 Câu hỏi mở màn** (= ý tưởng "Question Hook") |
| Dãy ảnh nỗi đau xếp dần / logo xếp hạng | C05 Hai phe (2 ảnh) | **C17 Dãy ảnh** (2–4 ảnh hoặc logo, xếp dần, có nhãn hoặc hạng) |
| Màn infographic toàn khung + avatar tròn | không có | **C18 Bảng giải thích** (eyebrow, tiêu đề, thẻ 01-02-03 dựng dần, avatar người nói) |
| Chia đôi: ảnh màn hình trên, người trong khung dưới | C08 (một phần) | thêm bố cục `split` cho C08 |
| Đạo cụ giao diện (ô nhập gõ chữ, khung chọn, ô bình luận, REC) | không có | **C19 Đạo cụ UI** (nhiều kiểu trong 1 family) |
| Tên thương hiệu phát sáng / LED, CTA | Logo động mở màn, Outro shop | **C20 Chốt thương hiệu** (dùng *trong* video, trước outro) |
| Phụ đề 2 tầng nền vàng / serif nghiêng | `c.cap` có `.` `!` `~` `^` | thêm 2 kiểu nhấn: `nền` và `serif` |
| Chữ lật bảng ga tàu | không có | để sau |
| Màu hạ bão hoà + viền tối | Chỉnh màu điện ảnh | thêm preset màu `toi-vang` |
| Video kiểu m2 không người (footage + giọng AI) | mảnh rời: TTS liền mạch (localize) + edit | **skill mới** (mục 5) |
| Cửa sổ Editor | CapCut nháp | **làm mới** (mục 5) |

---

## 5. Tách thành skill + template cho GDP (đề xuất)

### 5.1 Skill
| Skill | Vai trò | Ứng với của họ |
|---|---|---|
| `gdp-video-edit` (đã có) | **Lõi**: người nói, cắt lời, chữ động, Scene, QA, CapCut. Thêm tham số `style` | lõi s1/m1/Blue 1 |
| **`gdp-video-product`** (mới) | Video **sản phẩm không người**: footage tự quay (tay cầm, cận chi tiết, flycam, kho hàng) + kịch bản → giọng AI liền mạch (dùng lại `narrate`) → dựng theo kịch bản bằng Scene sản phẩm (C15 Soi nhãn, C09 chỉ thông số, C13 công tắc, C07 số, C20 chốt brand) | m2 không người |
| `gdp-video-motion` (đã có) | animation thương hiệu | Kinetic Motion một phần |
| `gdp-video-localize` (đã có) | Việt hoá video TQ | họ không có |

### 5.2 Template "phong cách" (Style Pack): bản GDP của s1 / m2 / Blue 1
Mỗi phong cách là một file `assets/styles/<id>/style.json` khai báo: bảng màu, phông chữ, kiểu phụ đề (vị trí,
1 hay 2 tầng, kiểu nhấn), màu hình, Scene ưu tiên hoặc cấm, nhịp (từ/giây, khoảng nghỉ), tiếng hiệu ứng, kiểu kết.
Trong `cut.py` chỉ cần một dòng `c.style("gdp-ban-hang")`; `plan.md` có dòng `Phong cách: …`. Mỗi phong cách có
**một video demo** trong `hieu-ung.html`, để nhân sự chọn bằng tên như họ bán.

| Style GDP | Học từ | Dùng cho | Nét chính (đổi sang màu shop) |
|---|---|---|---|
| `gdp-ban-hang` | m2 vàng–đen | review, mẹo nhà gọn, chốt đơn TikTok | hình hạ bão hoà + viền tối, phụ đề 2 tầng nền màu GDP, đạo cụ UI, chip, gạch dần |
| `gdp-giai-thich` | s1 navy | hướng dẫn lắp đặt, so sánh chất liệu, kiến thức | nền đậm, tiêu đề góc có icon, màn Bảng giải thích + avatar tròn, thẻ bước 01-02-03 |
| `phaledo-tap-chi` | Blue 1 | PHALEDO cao cấp, series "những điều cần biết" | sans + serif nghiêng, kính mờ, số chương to, khung sáng chia đôi |
| `san-pham-thuan` | m2 không người | `gdp-video-product` | footage sản phẩm + giọng AI, Soi nhãn, chỉ thông số, công tắc, số, chốt brand phát sáng |

### 5.3 Scene mới (template đồ hoạ), theo luật cũ: mỗi family = template + `scene.json` + render kiểm
Ưu tiên cho video sản phẩm GDP trước:
1. **C15 Soi nhãn**: cắt vùng bao bì hoặc tờ hướng dẫn **thật** từ clip, thành thẻ nổi, tô dòng đang đọc, số to bên dưới.
2. **C09 mở rộng: nhiều nhãn chỉ** vào bộ phận (kiểu cổng sạc UGREEN) + nét khoanh vẽ tay.
3. **C13 Danh sách động**: 3 kiểu `tick` / `toggle` / `strike`, mỗi mục bật theo lời.
4. **C14 Chip tính năng**: lưới 2×2 hoặc hàng ngang, có icon, dựng dần.
5. **C07 mở rộng**: `bars` (cột lớn dần), `gauge` (vòng %), `receipt` (hoá đơn tổng).
6. **C20 Chốt thương hiệu**: tên shop phát sáng hoặc hiện từng chữ, CTA giả giao diện (ô bình luận / nút giỏ hàng).
7. **C16 Câu hỏi mở màn**, **C17 Dãy ảnh**, **C18 Bảng giải thích**, **C19 Đạo cụ UI**: đợt sau.

Thêm vào lõi: kiểu nhấn phụ đề `nền` và `serif`; nền `glass` (mờ footage) cho các thẻ; preset màu `toi-vang`.

### 5.4 Công cụ
- **Cửa sổ Editor** `vs.py edit ui <id>`: trang HTML local có timeline theo lời, từng khối chữ / Scene / footage là
  một lớp. Sửa chữ, cụm khoá, vị trí, bật tắt, tham số Scene, rồi lưu `overrides.json` và render lại. Không tốn token.
- **Render từng đoạn**: cache theo câu; sửa một lớp chỉ dựng lại đoạn đó rồi nối.
- **Hướng dẫn quay** cho nhân sự (1 trang): người giữa khung, chừa trên/dưới, nói theo kịch bản, quay thêm cận
  sản phẩm, nhãn, thông số, mở hộp.
- **Đo chi phí mỗi job** (`cost.json`): thời gian, token. Họ khoe "2–3% hạn mức tuần", mình nên có số của mình.

---

## 6. Lộ trình (Sếp chốt 07/11 "Ok, chạy đi. Nhớ tách ra thành các phong cách khác nhau")
- [x] **Đợt 1, khung phong cách** (07/11): `c.style()` (`studio/edit/styles.py`) + kiểu nhấn **hộp màu** và **nghiêng
  mảnh** (không dùng serif: luật thương hiệu PHALEDO = Averta, GDP/LTENG = UTM Avo) + màn chữ `glass` + màu `toi-vang` /
  `sach` + **4 phong cách tách riêng**: `gdp-ban-hang` (S1), `gdp-giai-thich` (S2), `phaledo-tap-chi` (S3),
  `san-pham-thuan` (S4) — `vs.py styles`, ảnh mẫu `assets/styles/<id>/demo.jpg`.
- [x] **Đợt 2, Scene sản phẩm** (07/11), đánh số lại theo thứ tự làm: **C13 Danh sách động** (`list-motion`), **C14 Chip
  tính năng** (`feature-chips`), **C15 Soi nhãn** (`label-zoom`), **C16 Thẻ số liệu** (`data-card`: bars / gauge / receipt —
  làm family riêng thay vì nhồi vào C07), **C17 Chốt kêu gọi** (`cta-close`, = "C20 Chốt thương hiệu" ở trên). Chung
  UI Kit `assets/scenes/_uikit/` + theme `ui_dark` / `ui_light`. Đã render kiểm mọi theme × preset (tất định, khung cuối
  trong suốt) + có trong `hieu-ung.html`.
  Chưa làm: C09 nhiều nhãn chỉ + nét vẽ tay · Câu hỏi mở màn · Dãy ảnh · Bảng giải thích · Đạo cụ UI (đánh số tiếp từ C18).
- [ ] **Chạy thử 1 job thật** với `c.style(...)` + C13–C17 (máy này chưa có job nào — cần Sếp thả clip).
- [ ] **Đợt 3, skill `gdp-video-product`** + `cut.py` mẫu dùng style `san-pham-thuan`.
- [ ] **Đợt 4, Editor + render từng đoạn.**
- [ ] Song song (rẻ): hướng dẫn quay, đo chi phí mỗi job.
