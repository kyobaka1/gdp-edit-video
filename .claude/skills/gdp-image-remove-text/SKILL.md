---
name: gdp-image-remove-text
description: XOÁ CHỮ TRUNG trên ảnh sản phẩm mà GIỮ NGUYÊN NỀN bằng nút Remove của Photoshop web (photoshop.adobe.com) qua Claude in Chrome — làm HÀNG LOẠT trong MỘT file Photoshop cho mỗi kích thước ảnh (mở ảnh đầu, các ảnh sau dán thành layer), Lasso ôm sát nét chữ (đường bao tính từ pixel ảnh gốc bằng image-studio/ps_remove), chọn HẾT các cụm rồi Remove MỘT lần, xuất PNG qua Adobe cloud rồi kéo về máy, xong đóng tab. Dùng khi Sếp nói "xoá chữ Trung", "remove chữ trên ảnh", "xoá text giữ nền", "làm sạch ảnh Trung", thả thư mục ảnh Trung cần xoá chữ, hoặc khi làm ảnh listing / ảnh phân loại (skill gdp-image-listing) mà ảnh được giao CÒN chữ Trung. Ảnh đã sạch chữ → BỎ QUA. KHÔNG dùng Adobe MCP để xoá chữ (MCP không có Remove / Generative Fill; Remove Background của MCP xoá cả cảnh).
---

# Xoá chữ Trung giữ nền — Photoshop web Remove, làm hàng loạt (Sếp chốt 13/11/2026)

Giao tiếp với Sếp bằng tiếng Việt. Công cụ `image-studio/ps_remove/` (repo gdp-video-studio) + Chrome của Sếp (đã đăng
nhập Adobe) qua Claude in Chrome — đọc skill `anthropic-skills:chrome-browser` trước, nạp tool Chrome bằng MỘT ToolSearch
(`tabs_context_mcp, navigate, computer, find, file_upload, javascript_tool, browser_batch, tabs_close_mcp`).

## Khi nào làm

- **Ảnh còn chữ Trung đồ hoạ thì mới làm; ảnh đã xoá rồi thì BỎ QUA** (để `[]` trong regions.json → `batch.py` tự bỏ).
- Việc listing (skill `gdp-image-listing`): ảnh nhân sự xoá còn sót → xoá nốt; ô chưa có bản sạch → `ims.py pull --allow-source`
  rồi xoá; ảnh xong GHI ĐÈ `jobs/<job>/clean/<key>.*` (giữ tên); báo Sếp ảnh nào Claude tự xoá.
- Chỉ xoá **chữ đồ hoạ** (tiêu đề, dòng phụ, nhãn, biển chữ, chữ trong ô icon). Chữ in trên sản phẩm / phụ kiện: GIỮ.
  Icon, khung ô, số đo vẽ sẵn: giữ. Watermark chéo mờ của shop Trung (vd "蓝藤版权 盗版必究" rải khắp ảnh, đè lên cả sản
  phẩm): KHÔNG tự xoá (Remove đè lên sản phẩm dễ hỏng) — báo Sếp vị trí, Sếp quyết.

## Nguyên lý Remove (Sếp giải thích)

Remove ≈ content-aware fill thông minh: so vùng được chọn với phần còn lại để vẽ lại nền →
1. **Chọn càng SÁT nét chữ càng tốt, không chọn quá lớn** — khung chữ nhật lấn icon làm Remove vẽ thêm icon (thử 13/11).
2. **Chọn TẤT CẢ cụm chữ của ảnh rồi Remove MỘT lần.** Còn sót → lasso NHỎ đúng chỗ sót → Remove tiếp. Tệ hơn → Ctrl+Z.
3. Chỉ bấm **Remove** (không tốn credit). KHÔNG Generative fill / AI markup trừ khi Sếp bảo.

## Hàng loạt: MỘT file Photoshop cho mỗi kích thước (Sếp 13/11)

Không mở đi mở lại từng file. Mỗi NHÓM cùng kích thước (vd ảnh phân loại 1:1 800×800, ảnh mô tả 3:4 / 1:1): mở ảnh đầu →
xoá → xuất; **dán ảnh tiếp theo vào thành layer trên cùng** (cùng kích thước nên tự khít khung, không phải chỉnh size) → xoá
→ xuất → … Hiệu chỉnh vị trí đo MỘT lần cho cả nhóm. Khác kích thước → nhóm khác (file khác).

## Quy trình (tối ưu token)

**A. Chuẩn bị trên máy — không mở trình duyệt**
1. ĐỌC từng ảnh MỘT lần (Read), khoanh hộp từng dòng chữ (toạ độ px ảnh) → viết `regions.json` cho CẢ LÔ:
   `{"<đường dẫn ảnh>": [{"name", "box": [x0,y0,x1,y1], "kind": "dark"|"light"|"badge"|"red", "thr"}, …], …}` (kind: xem
   `text_polys.py`; ảnh sạch = `[]`). Hộp vừa đủ dòng chữ, không lấn icon / sản phẩm; nhãn màu dùng `badge` / `red`
   (tự nới 30 px). Mẫu: `image-studio/source/COVER_IMAGE_JOB/regions.json`, `ps_remove/regions-example-hu-duong.json`.
2. `python image-studio/ps_remove/batch.py <regions.json> <thư mục lô> [--dilate 6]` (Windows: `$env:PYTHONIOENCODING='utf-8'`)
   → `manifest.json` (nhóm theo kích thước), `i01.jpg` + `i01.json` …, `_soat.jpg`. **ĐỌC `_soat.jpg`** (một ảnh cho cả lô):
   hồng phủ kín mọi nét chữ, không chạm icon / sản phẩm. Sai → sửa hộp / `thr` → chạy lại. `--dilate` ≈ 6 (ảnh 800 px),
   9 (ảnh 1440 px).

**B. Photoshop web — mỗi nhóm kích thước một lần**
3. Tab mới → `https://photoshop.adobe.com/` → `javascript_tool` chạy `ps_remove/picker.js` → `find "claude upload slot"` →
   `file_upload` ảnh đầu nhóm → `window.__openName='i01.jpg'` → bấm **Upload** (ô "Drag and drop") → **Upload from computer**.
4. Trong trang sửa (ô tải tạm bị xoá khi đổi trang): chạy lại `picker.js` → `file_upload` MỘT LẦN cả lô
   `[ps_remove/lasso.js, i01.json, i02.jpg, i02.json, …]` → nạp script không tốn token:
   `eval(await [...document.getElementById('claude-file-input').files].find(f=>f.name==='lasso.js').text())`.
   Chuyển chế độ **Tools** nếu đang Assisted.
5. **Hiệu chỉnh (1 lần / nhóm):** ngay sau khi mở, công cụ Move hiện 4 chấm ở góc ảnh → `zoom` 2 góc (trên-trái, dưới-phải)
   → toạ độ ảnh chụp × (`innerWidth` / bề rộng ảnh chụp) = CSS px → `__cal(x0, y0, bề_rộng_CSS / bề_rộng_ảnh_px)`.
   Đo được 13/11: tab 1707 CSS, dpr 1.5, ảnh 800×800 mở ở 100% → `__cal(588.1, 211.4, 0.66667)`.
6. **Mỗi ảnh** (gộp vào `browser_batch`):
   - Ảnh 2 trở đi: chọn công cụ **Move** (ô trên cùng thanh trái — đang ở Type thì Ctrl+V dán thành chữ) →
     `await __toClipboard('i02.jpg')` → `computer key ctrl+v` → layer mới trên cùng, tự khít khung.
   - Select → **Lasso** → `await __loadPolys('i0N.json'); await __drawAll()` (cụm 2+ tự giữ Shift = cộng vùng, khỏi bấm
     "Select more") → `zoom` vùng chữ kiểm đường kiến bò → **Remove** (thanh nổi dưới ảnh) → đợi ~10 s → `ctrl+d` →
     `zoom` kiểm sạch.
   - **Xuất:** Download → **Adobe cloud storage** → gõ tên `<lô>-i0N` → định dạng **PNG** (ô này TỰ VỀ JPEG mỗi lần — chọn
     lại rồi `zoom` kiểm chữ "PNG") → mở "Your files" (nút Export mới bật) → **Export** → đợi thông báo xanh.
     KHÔNG chọn "Download on computer" (mở hộp lưu hệ thống, Claude không bấm được).
7. Xong cả lô → **ĐÓNG TAB NGAY** (`tabs_close_mcp` — Photoshop web nặng máy; file tự lưu trên cloud).

**C. Kéo về + soát**
8. Adobe MCP (một lần cho cả lô): `adobe_mandatory_init` (trả về rất dài — chỉ gọi lúc tải, một lần mỗi phiên) →
   `asset_search` (CCAsset, query = tiền tố tên lô, mediaType image/png, limit đủ lô) → `asset_get_presigned_urls` với MỌI id
   một lần → `curl -L` từng file vào thư mục `clean/` (tên gốc, đuôi .png).
9. Ghép gốc | đã xoá cho cả lô thành 1 ảnh, ĐỌC. Đo pixel nếu nghi sót (vd đếm điểm đỏ còn lại quanh nhãn đỏ). Sót vài
   chục pixel ở mép → lấp tại chỗ (`cv2.inpaint` đúng vùng sót, nêu trong báo cáo); sót lớn → mở lại Photoshop, lasso nhỏ, Remove.

## Tiết kiệm token / bước (rút từ lần chạy 13/11)

- Dữ liệu (ảnh, polygon, chính `lasso.js`) nạp bằng `file_upload` — KHÔNG dán JSON / base64 vào lệnh.
- Chuỗi thao tác nối bằng `browser_batch`; chụp màn hình `scale` 0.4–0.5; kiểm chi tiết bằng `zoom` vùng nhỏ.
- `find` / `read_page` KHÔNG thấy nút của Photoshop (giao diện vẽ trong canvas) → lấy toạ độ từ ảnh chụp; ghi lại toạ độ
  nút (Remove, menu Download, ô định dạng, Export) lần đầu rồi dùng lại cả lô; đổi cỡ cửa sổ → đo lại.
- Hiệu chỉnh + toạ độ nút đo một lần cho cả nhóm kích thước.

## Bẫy đã gặp

- Ô file của Photoshop dùng `showOpenFilePicker` → bắt buộc `picker.js`; ô tải tạm mất khi Photoshop đổi trang.
- Sự kiện `paste` giả: Photoshop KHÔNG đọc dữ liệu đi kèm mà đọc CLIPBOARD THẬT → dán nhầm chữ đang có trong clipboard thành
  layer chữ. Phải `__toClipboard` (ghi clipboard thật, PNG) rồi Ctrl+V thật. Việc này GHI ĐÈ clipboard của Sếp — nói khi báo cáo.
- Phím `l` không chọn Lasso (ra Selection brush) → bấm "Lasso" trong bảng Select.
- Hộp nhãn hụt mép → sót vệt (nhãn đỏ thật từ x=24, hộp từ x=40); đã sửa bằng `pad` tự nới cho badge / red.
- Object selection kéo khung trên chữ nhỏ báo "Couldn't find an object"; Marquee ở Tools đôi khi vẽ TỪ TÂM.
- File trên Adobe cloud (PNG xuất + `.psdc` Photoshop tự lưu) nằm lại "Your files" — nêu trong báo cáo, không tự xoá.
