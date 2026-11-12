# Ảnh đại diện (bìa) — làm gì để tăng CTR, theo SỐ THẬT của các shop GDP

> Điều tra ngày **12/11/2026** qua MCP `gdp-bridge` trên prod giadungplus.store: CTR thẻ sản phẩm 30 ngày
> (`marketing_shopeeproductdailyperformance`), 9 thử nghiệm đổi bìa của Cover Intelligence (`marketing_cover_experiment` +
> `marketing_cover_evaluation`, tool `cover_lessons` / `cover_opportunities`), và NHÌN TRỰC TIẾP 32 ảnh bìa (16 CTR cao nhất,
> 16 thấp nhất, mã ≥ 8.000 lượt hiện) sau khi đè khung Shopee mẫu lên. Bổ sung cho — không thay — playbook nội dung ở skill
> `gdp-listing-plan` → `prompts/ctr-playbook.md` (bậc thang hook, luật thị giác, luật sự thật).
>
> Độ tin: tương quan trên mẫu nhỏ + thử nghiệm đang ở mức "sơ bộ" (chưa đủ ngày). Dùng làm ĐỊNH HƯỚNG thiết kế, không
> hứa con số. **Hạn dùng: 12/01/2027** — quá hạn thì chạy lại câu lệnh ở cuối file rồi mới trích số.

## 1. Mốc CTR 30 ngày (đến 12/11/2026, mã ≥ 2.000 lượt hiện) — bìa mới nhắm ≥ p75 của shop

| Shop | Số mã | CTR chung | p25 (đáy) | p50 | p75 (nhắm) | p90 |
|---|---|---|---|---|---|---|
| giadungplus_official | 102 | 4,31% | 3,07% | 3,69% | **4,52%** | 5,35% |
| phaledo_official | 46 | 4,94% | 3,98% | 4,74% | **5,28%** | 5,70% |
| lteng_vn | 51 | 3,60% | 2,65% | 3,45% | **3,86%** | 4,97% |
| lteng_hcm | 30 | 3,78% | 3,26% | 3,80% | **4,67%** | 5,21% |
| phaledo (mẫu nhỏ) | 7 | 6,25% | 4,50% | 5,12% | 6,21% | 6,68% |

Đọc cặp (CTR, tỉ lệ thêm giỏ): CTR thấp + thêm giỏ cao = **bìa là nút thắt** (vào xem là mua, chỉ là ít người bấm) → đáng
làm lại bìa nhất. Ví dụ đang có: móc treo dạng thanh cốc hút GDP `53905413825` CTR 2,67% / thêm giỏ 34,9%; móc treo chậu
`6332583072` 3,08% / 39,5%; đế cao su PHALEDO `18585600614` 3,07% / 36,6%.

## 2. Khung Shopee đè lên ảnh bìa — VÙNG CẤM

Shopee tự dán khung chiến dịch lên ảnh bìa trong lưới tìm kiếm / trang shop: nhãn **11.11**, **VOUCHER XTRA**, **SHOPEE HOME**
ở đáy-trái và nút ▶ video ở đáy-phải. Khung mẫu Sếp đưa (`image-studio/ui/shopee-frame.png`, 320×320) chiếm x 0–41%,
y 88–100%; trên trang shop dải này kéo tới ~62% bề ngang. Chiến dịch đổi thì nhãn đổi, chỗ không đổi.

**Luật: không đặt chữ, nhãn, logo trong 13% đáy ảnh bìa (y ≥ 87%), trên TOÀN bề ngang.** Bộ kiểm báo LỖI nếu vi phạm
(`image.cover_frame_pct` trong `shop.json` nếu cần đổi mức). Watermark được nằm trong vùng này.

Vì sao nghiêm: trong 16 bìa CTR thấp nhất có **7** bìa để chữ trong dải đáy (3–4 bìa bị khung che thẳng vào chữ), trong 16
bìa cao nhất chỉ **3**. Thử nghiệm CX-0007 (LTENG VN, kệ 0744, 03–08/11 — đúng đợt 11.11): bìa mới đặt cả hai dòng hook
"KỆ NHÔM KHÔNG GỈ" + "DÁN KEO / KHOAN TƯỜNG" ở sát đáy → CTR 3,17% → 1,86% (−41%), thêm giỏ giảm một nửa, Sếp cho khôi phục.
(Ảnh đó còn đổi nền + màu nên không quy hết cho vị trí chữ — nhưng chữ bị che là lỗi tránh được 100%.)

Góc trên-trái đôi khi cũng bị Shopee dán nhãn nhỏ (vd "Try-On") — đừng đặt chữ nhỏ quan trọng sát góc đó.

## 3. Điều nhìn thấy ở nhóm CTR cao (16 bìa, 5,4–7,8%)

1. **Hook ở NỬA TRÊN ảnh:** 11/16 đặt chữ chính ở trên hoặc trên-phải; 3/16 gần như không chữ (sản phẩm tự nói: thùng gạo
   xuất Nhật 5,44%, kệ góc LTENG 6,07%, hộp giấy 6,28%); chỉ 1/16 đặt chữ chính ở đáy. → Bộ kiểm CẢNH BÁO khi tiêu đề lớn nhất
   có tâm dưới 62% chiều cao.
2. **Chữ to, thẳng hàng ngang, ít:** 1 hook + tối đa 2 nhãn. Con số được phóng to nhất ("9L", "50KG", "20KG", "180°C", "550ML").
3. **Sản phẩm to, một chủ thể:** sản phẩm chiếm phần lớn khung, nền tách bạch (PHALEDO nền tối + chữ kem; GDP nền sáng + chữ đen / đỏ).
4. **Cam kết / số thật làm hook:** "BỂ VỠ 1 ĐỔI 1 · 6 THÁNG" (6,94%), "BẢO HÀNH BỂ VỠ · 1 ĐỔI 1 · 180 NGÀY" (5,71% trên
   216.000 lượt hiện), "CHỊU LỰC 20KG + TẶNG KÈM KEO + Đã bán 300.000" (6,12%), "CÓ RUỘT · 9L" (6,40%).

## 4. Điều nhìn thấy ở nhóm CTR thấp (16 bìa, 2,6–3,3%)

1. **Chữ ở đáy ảnh** (mục 2) — 7/16.
2. **Tên sản phẩm làm hook:** "THANH MÓC TREO ĐỒ", "MÓC TREO THAU", "GIÁ TREO DÉP CỐC HÚT", "HŨ QUAI XÁCH THUỶ TINH",
   "DECAL GIA VỊ", "ĐẾ CAO SU BẢO VỆ" — khách đã thấy món gì rồi, chữ không cho thêm lý do bấm.
3. **Chữ chìm vào nền:** chữ navy trên tường xám / be (3 mã LTENG VN ở đáy bảng, trong đó kệ `43568211253` 222.000 lượt hiện
   chỉ 3,27%); nhãn mờ chữ nhạt ("ĐẾ CAO SU BẢO VỆ"); chữ đỏ viền trắng trên nền rối.
4. **Chữ nghiêng / uốn:** cùng thông điệp "CHỊU LỰC 20KG · TẶNG KÈM KEO" — bìa chữ thẳng, sản phẩm cận cảnh, có "Đã bán
   300.000" đạt 6,12% (`7095067387`); bìa chữ nghiêng chéo, 4 móc nhỏ rải rác chỉ 2,87% (`19353654836`).
5. **Nhiều chủ thể, nền lộn xộn:** cùng là tem nhãn gia vị — PHALEDO trải tem kín khung trên nền đen 7,78%; GDP ghép tay + lọ +
   bảng tem trên nền bếp sáng 2,64%.

## 5. Bài học từ thử nghiệm đổi bìa (Cover Intelligence, mức sơ bộ)

| Mã | Đổi gì | Kết quả | Rút ra |
|---|---|---|---|
| CX-0001 | PHALEDO chai gia vị: tay rót dầu → 4 chai **dán nhãn** Nước mắm / Giấm / Dầu ăn / Nước tương | 3,44% → 4,40% (+28%), tín hiệu dương | Nhãn chữ NẰM TRÊN SẢN PHẨM cho thấy công dụng ngay ở cỡ tem |
| CX-0002 | PHALEDO hũ gia vị: thêm nhãn Muối / Ớt khô / Hạt nêm + tiêu đề công dụng | 3,64% → 4,50% (+24%), tín hiệu dương | như trên |
| CX-0003 | PHALEDO hũ nắp inox: nhãn gia vị + "NẮP INOX 304" | 3,60% → 4,11% (+14%), chưa kết luận | hướng đúng, cần thêm ngày |
| CX-0004 | Bìa đang thắng nhóm, thêm nhãn "DẦU ĂN" | 5,12% → 4,97%, chưa kết luận | bìa đã tốt thì sửa nhỏ không tạo khác biệt |
| CX-0006 | PHALEDO 7 lọ rỗng nền đen → lọ đựng đồ khô nhiều màu trên bếp gỗ ấm | 5,39% → 3,63% (−33%) | đồ nhiều màu + nền ấm cùng tông làm thuỷ tinh hết nổi; hook bảo hành bị loãng. Đang thử lại nền tối + chữ to (CX-0009) |
| CX-0007 | LTENG VN kệ 0744: bìa mới nền xanh + hook ở đáy | 3,17% → 1,86% (−41%), khôi phục | xem mục 2; đổi nhận diện mạnh tay không tự kéo CTR |

## 6. Ý tưởng tăng CTR — xếp theo độ chắc

**Làm ngay (có số đỡ lưng)**
1. Dời mọi chữ ra khỏi 13% đáy; hook lên nửa trên. Bìa đang chạy có chữ ở đáy = ứng viên sửa đầu tiên.
2. Hook = cam kết khử rủi ro hoặc con số trả lời câu khách tự hỏi trước khi bấm (chịu mấy kg, mấy lít, bảo hành ra sao). Bỏ
   tên sản phẩm khỏi vị trí hook; tên sản phẩm (nếu cần) thành nhãn nhỏ.
3. Phóng con số: số là phần to nhất bìa (tách riêng thành nhãn hoặc dòng riêng cỡ lớn hơn chữ còn lại).
4. Chữ thẳng, đậm, tương phản tuyệt đối với nền ngay dưới nó (đen trên sáng, trắng trên tối, hoặc nhãn nền đặc). Kiểm ở cỡ tem.
5. Ưu tiên làm lại bìa cho mã CTR < p25 mà thêm giỏ cao (mục 1) — cùng lượt hiện, CTR 2,7% → 4,5% là thêm ~2/3 lượt vào trang.

**Đáng thử (tín hiệu dương, mẫu còn nhỏ)**
6. Dán nhãn công dụng lên chính sản phẩm (tên gia vị trên hũ, "NHÀ TẮM" / "BẾP" theo cảnh) — CX-0001 / 0002. Việc này thuộc
   ảnh nền (nhân sự / ảnh chụp), không phải lớp chữ → đề xuất với Sếp khi chọn ảnh nền.
7. Nhãn bằng chứng xã hội có thật ("Đã bán 300.000") ở góc trên-phải — chỉ khi số thật, làm tròn xuống.
8. Mũi tên / đường chỉ (`callout`) vào đúng cơ chế khác biệt ("CÓ RUỘT ←") thay cho một dòng chữ mô tả.
9. Bìa không chữ cho sản phẩm tự là bằng chứng (hàng có tem, bộ sản phẩm đẹp) — vẫn đặt logo.

**Đừng làm (đã thấy thua)**
10. Hook ở đáy ảnh. 11. Chữ nghiêng / uốn. 12. Nhiều chủ thể / ghép ô. 13. Đổi nền / nhận diện mạnh tay chỉ vì "theo brand"
(CX-0007). 14. Thêm đồ nhiều màu làm sản phẩm trong suốt hết nổi (CX-0006). 15. Chữ navy / xám trên tường xám.

Những ý thuộc ẢNH NỀN (góc chụp, đồ trong lọ, nền sáng / tối, bàn tay) nằm ngoài quyền của skill này — skill chỉ thêm chữ +
logo. Thấy ảnh nền là nút thắt thì NÊU với Sếp khi trình duyệt, đừng tự sửa nền.

## 7. Điều tra lại (MCP `gdp-bridge`, chỉ đọc)

- `cover_opportunities(limit=20)` — mã đang tụt CTR / thấp hơn nhóm, xếp theo lượt bấm có thể lấy lại mỗi ngày.
- `cover_lessons(limit=40)` — bài học đã chốt. `cover_listing_get(connection_id, item_id)` — CTR theo ngày + các phiên bản bìa
  của một mã. `cover_results_get(code)` — kết quả một thử nghiệm.
- Bảng xếp hạng + mốc phần tư (đổi `30 days` / ngưỡng lượt hiện tuỳ quy mô):

```sql
WITH agg AS (
  SELECT shop_name, item_id, MAX(product_name) AS name, MAX(product_image) AS img,
         SUM(product_card_impressions) AS imp,
         ROUND((100.0*SUM(product_card_clicks)/NULLIF(SUM(product_card_impressions),0))::numeric,2) AS ctr,
         ROUND((100.0*SUM(add_to_cart_buyers)/NULLIF(SUM(uv),0))::numeric,2) AS atc
  FROM marketing_shopeeproductdailyperformance
  WHERE report_date >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY shop_name, item_id HAVING SUM(product_card_impressions) >= 8000)
(SELECT 'TOP' g, * FROM agg ORDER BY ctr DESC LIMIT 16)
UNION ALL (SELECT 'BOT' g, * FROM agg ORDER BY ctr ASC LIMIT 16);
```

Ảnh bìa thật: `https://down-vn.img.susercontent.com/file/<img>` — tải về, đè `image-studio/ui/shopee-frame.png` lên rồi NHÌN.
Thử nghiệm: `SELECT code, shop_name, item_name, stage, decision, hypothesis FROM marketing_cover_experiment` nối
`marketing_cover_evaluation` (`baseline_ctr`, `after_ctr`, `relative_uplift`, `verdict`).
