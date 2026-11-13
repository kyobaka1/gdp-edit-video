---
name: gdp-image-remove-text
description: XOÁ CHỮ TRUNG trên ảnh sản phẩm mà GIỮ NGUYÊN NỀN bằng nút Remove của Photoshop web (photoshop.adobe.com) qua Claude in Chrome — Lasso ôm sát nét chữ (đường bao tính từ pixel ảnh gốc bằng image-studio/ps_remove), chọn HẾT các cụm rồi Remove MỘT lần, xuất PNG qua Adobe cloud rồi kéo về máy. Dùng khi Sếp nói "xoá chữ Trung", "remove chữ trên ảnh", "xoá text giữ nền", "làm sạch ảnh Trung", hoặc khi làm ảnh listing (skill gdp-image-listing) mà ảnh được giao CÒN chữ Trung / nhân sự chưa xoá. Ảnh đã sạch chữ → BỎ QUA skill này. KHÔNG dùng Adobe MCP để xoá chữ (MCP không có Remove / Generative Fill; Remove Background của MCP xoá cả cảnh).
---

# Xoá chữ Trung giữ nền — Photoshop web Remove (Sếp chốt 13/11/2026)

Giao tiếp với Sếp bằng tiếng Việt. Công cụ: `image-studio/ps_remove/` (repo gdp-video-studio) + Chrome của Sếp
(đã đăng nhập Adobe) qua Claude in Chrome (đọc skill `anthropic-skills:chrome-browser` trước khi dùng).

## Khi nào làm (luật Sếp 13/11)

- **Ảnh còn chữ Trung đồ hoạ thì mới làm; ảnh đã xoá rồi thì BỎ QUA**, đi thẳng sang phủ chữ Việt (skill `gdp-image-listing`).
- Trong việc listing: sau `ims.py pull` + `ims.py sheet`, soát từng ảnh (cột "đã xoá chữ"):
  - ảnh sạch → không làm gì ở skill này;
  - ảnh nhân sự upload mà CÒN chữ Hán / khung chữ / biển chữ sót → xoá nốt phần sót bằng skill này;
  - ô `⏳ chưa có bản sạch` (nhân sự chưa làm) → `ims.py pull <id> --allow-source` lấy ảnh Trung làm nền, xoá chữ bằng
    skill này, rồi GHI ĐÈ file `jobs/<job>/clean/<key>.*` bằng ảnh đã xoá (giữ tên file). Nêu trong báo cáo cho Sếp ảnh nào
    Claude tự xoá.
- Chỉ xoá **chữ đồ hoạ** (tiêu đề, dòng phụ, nhãn, biển chữ, chữ trong ô icon, watermark chữ của shop Trung). Chữ in trên
  sản phẩm / phụ kiện trong cảnh: GIỮ (luật 1 của studio). Icon, khung ô, số đo vẽ sẵn: giữ, trừ khi Sếp bảo bỏ.

## Nguyên lý Remove (Sếp giải thích)

Remove ≈ content-aware fill thông minh: nhìn vùng được chọn so với phần còn lại để vẽ lại nền. Vì vậy:

1. **Chọn càng SÁT nét chữ càng tốt** — vùng thừa ít thì có nhiều nền thật xung quanh để so.
2. **Không chọn quá lớn**: khung chữ nhật lấn icon / mép ô làm Remove "vẽ thêm" (thử 13/11: vệt đỏ, cốc nhân đôi).
   **Lasso** chính xác hơn Marquee.
3. **Chọn TẤT CẢ cụm chữ của ảnh rồi Remove MỘT lần** — vừa tối ưu vừa nhanh. Không Remove từng cụm.
4. Remove xong còn sót → lasso NHỎ đúng chỗ sót → Remove tiếp. Lượt sau tệ hơn → Ctrl+Z (hoặc tắt layer lượt đó).
5. Chỉ dùng **Remove** (không tốn credit AI). KHÔNG bấm Generative fill / AI markup (tốn credit) trừ khi Sếp bảo.

Kết quả mẫu (ảnh hũ đường PHALEDO `jobs/test-phaledo`): Lasso sát chữ + 1 lần Remove → sạch 100%, tường liền, icon nguyên.

## Quy trình

Lệnh Python chạy từ thư mục repo: `.\.venv\Scripts\python.exe` (Mac: `.venv/bin/python`); script đọc file nên thêm `-I`.

1. **Khoanh hộp từng dòng chữ** trên ảnh gốc (toạ độ pixel ảnh): xem ảnh / `ims.py grid <job> <key>` rồi ghi
   `regions.json` (mẫu `image-studio/ps_remove/regions-example-hu-duong.json`):
   `{"name", "box": [x0,y0,x1,y1], "kind": "dark"|"light"|"badge", "thr"}` — `dark` chữ tối hơn nền (L < thr),
   `light` chữ sáng hơn nền, `badge` = cả tấm nhãn màu (xoá trọn biển + dây treo). Hộp vừa đủ dòng chữ, KHÔNG lấn icon /
   sản phẩm (mask chỉ tính trong hộp — đây là chỗ giữ icon an toàn).
2. **Mở ảnh trong Photoshop web**: tab mới → `https://photoshop.adobe.com/` → làm theo `image-studio/ps_remove/picker.js`
   (ô tải tạm + `file_upload` + thay `showOpenFilePicker`) → Upload → Upload from computer. Chuyển chế độ **Tools**
   (không phải Assisted), đóng bảng AI markup nếu tự mở. Để zoom mặc định (vừa khung, thường 50%).
3. **Đo vị trí ảnh trên màn hình**: chụp màn hình, phóng to 2 góc ảnh (`zoom`), đổi sang CSS px (× `innerWidth` / bề rộng
   ảnh chụp — lấy `innerWidth` bằng `javascript_tool`). Mặc định đã đo: x0 613, y0 128.5, scale 1/3 (tab 1707×842, dpr 1.5).
4. **Tính đường lasso**:
   `python -I image-studio/ps_remove/text_polys.py <ảnh gốc> <regions.json> <thư mục ra> [--dilate 9] [--x0 --y0 --scale]`
   → `polys.json` + `polys_prev.jpg`. **ĐỌC `polys_prev.jpg`**: hồng phải phủ kín mọi nét chữ, không chạm icon / sản phẩm.
   Sửa hộp / `thr` / `--dilate` tới khi đúng (dilate 9 px ở ảnh 1440 px là vừa: bù sai lệch vẽ ~3 px + viền mờ của chữ).
5. **Vẽ lasso**: Select → **Lasso** → bấm **Select more** (sau Ctrl+D nó tự về "Create new selection" — phải bấm lại) →
   `javascript_tool`: dán `lasso.js`, gán `window.__POLYS = <polys.json>`, `await window.__drawAll()`. Kéo chuột của tool
   chỉ ra đường thẳng nên phải vẽ bằng pointer event như vậy. Phóng to ảnh chụp kiểm: đường kiến bò ôm từng chữ, đủ mọi cụm.
6. **Remove MỘT lần** (thanh nổi dưới ảnh) → đợi ~10 giây (ra layer mới) → phóng to soát từng cụm. Sót → bước 4–5 cho riêng
   chỗ sót (`__drawAll(['tên-cụm'])`, hộp nhỏ hơn) → Remove tiếp.
7. **Xuất**: Download → **Adobe cloud storage** (KHÔNG chọn "Download on computer" — nó mở hộp lưu hệ thống, Claude không
   bấm được) → tên file `claude-xoa-chu-<job>-<key>` → PNG → mở "Your files" (nút Export mới bật) → Export.
   Kéo về: Adobe MCP `adobe_mandatory_init` → `asset_search` (CCAsset, query = tên file, mediaType image/png) →
   `asset_get_presigned_urls` → `curl -L -o <file>`. Ảnh ra cùng kích thước ảnh gốc.
8. **Soát + giao**: ghép ảnh gốc | đã xoá cạnh nhau, đọc bằng mắt (chữ sót, vệt, icon méo, nền loang). Đạt → đặt vào
   `jobs/<job>/clean/` (việc listing) rồi tiếp skill `gdp-image-listing` từ bước 2.
9. **Đóng tab Chrome ngay khi xong (Sếp 13/11 — Photoshop web rất nặng)**: ảnh đã kéo về máy là `tabs_close_mcp` mọi tab
   Claude đã mở cho việc này (file Photoshop tự lưu trên cloud, không mất gì). Nhiều ảnh thì xoá lần lượt trong CÙNG một
   tab, xong cả lô mới đóng — không để tab Photoshop treo sau khi báo cáo.

## Bẫy đã gặp

- `find` không thấy ô file của Photoshop (nó dùng `showOpenFilePicker`) → bắt buộc dùng `picker.js`.
- Object selection kéo khung trên chữ nhỏ báo "Couldn't find an object"; bấm hình thumbnail đối tượng ở bảng Select thì
  chọn được khối lớn (tiêu đề, biển) nhưng không ôm sát bằng lasso tính từ pixel.
- Marquee ở Tools đôi khi vẽ TỪ TÂM (điểm bắt đầu kéo = tâm khung).
- Bấm thumbnail đối tượng có thể chọn nhầm mặt bàn → Ctrl+Z.
- Ảnh trên Adobe cloud (PNG xuất + file `.psdc` Photoshop tự lưu) nằm lại trong "Your files" của Sếp — nêu trong báo cáo;
  Claude không tự xoá file trên cloud.
