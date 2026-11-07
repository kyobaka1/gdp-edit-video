# Prompt Claude Design — GDP Video Studio / Quản trị jobs

Sao chép toàn bộ phần bên dưới vào Claude Design, kèm ảnh tham chiếu giao diện mà Sếp đã cung cấp.

---

Thiết kế và tạo **một trang HTML độc lập `index.html` để quản trị jobs và thư viện video final của GDP Video Studio**, dành cho người vận hành Việt Nam. Tôi cần một công cụ làm việc thực tế: mở trang là biết video nào còn việc, xem được final ngay trên giao diện và xác nhận việc sử dụng từng video. Không chỉ vẽ dashboard tĩnh.

## 1. Kết quả cần giao

- Một file HTML hoàn chỉnh, CSS và JavaScript nhúng trong file, mở thử được ngay. Không React build, npm, framework bắt buộc, CDN, font mạng hay dịch vụ cloud. Font hệ thống hỗ trợ đủ dấu tiếng Việt; icon SVG inline.
- Hai chế độ chính dùng chung bộ dữ liệu, bộ lọc, lựa chọn và trạng thái: **Lướt video** dạng thư viện thẻ như ảnh tham chiếu và **Danh sách** dạng bảng để xử lý nhiều jobs.
- Một drawer chi tiết job có player video, tiến trình sản xuất, bằng chứng kiểm tra và hai xác nhận **Đăng SP / Shopee Video**.
- Có chế độ demo tương tác đẹp, đủ tình huống; có lớp đọc/ghi file local tách rõ để kết nối dữ liệu thật. Những chức năng không được môi trường hỗ trợ phải thông báo rõ, không giả thành công.
- Không cần tạo website marketing, màn đăng nhập, phân quyền SaaS hay chức năng upload lên Shopee. Giao diện có chất lượng sản phẩm SaaS chuyên nghiệp nhưng phục vụ một Studio local.

## 2. Bối cảnh và cấu trúc thật — dùng làm hợp đồng thiết kế

Studio mặc định: `C:\Users\Admin\gdp-video-studio`.

```text
gdp-video-studio/
  index.html                         # file giao diện mới được đề xuất
  dashboard.settings.json            # file cấu hình giao diện mới được đề xuất
  inbox/                             # video nguồn
  jobs/
    <job_id>/
      meta.json                      # id, source, origin, width, height, fps, duration, has_audio
      analysis.json                  # kết quả phân tích nguồn
      edl.draft.json                  # bản nháp
      direct.py                      # chỉ dẫn dựng của người/agent
      edl.json                       # shop, brand, overlays, narration, audio, motion...
      music.mp3
      narration.json                 # model, voice, match, pieces, warnings...
      narration.wav
      preview.mp4                    # có thể không có
      final.mp4                      # có thể không có
      qa.json                        # video, pass, frames_checked, residual_chinese, motion...
      contact.jpg                    # ảnh ghép kiểm tra, không phải poster video
      logo.json
      motion_plan.json               # nếu job dùng motion
      layers.json
      DELIVERY.md                    # chỉ một số job có
      final-check.json               # chỉ một số job có; có thể chứa sha256, checked_at...
      final-audiocheck.txt            # tên/file bằng chứng không thống nhất ở mọi job
      final-heard.txt
      final-visual-review.txt
      management.json                # metadata quản trị mới được đề xuất
    _delivery-*/                     # gói giao hàng, có thể có bản sao final/báo cáo
    _probe/, _doctor/, ...            # thư mục phụ trợ
    source-*/                        # có job nguồn chia sẻ phân tích giữa nhiều shop
    demo-motion-*/                   # có job thử nghiệm motion
  assets/
    shops/<shop>/shop.json           # hồ sơ shop, title, brand, palette, logo, voice...
    motion/                          # thư viện animation thương hiệu
    fonts/
  studio/config.py                   # đường dẫn và cấu hình pipeline hiện hành
  vs.py                              # CLI pipeline
  .env                               # cấu hình nhạy cảm, tuyệt đối không đọc ra UI
```

Ảnh chụp dữ liệu tại thời điểm khảo sát: 91 thư mục có `meta.json`, 73 có `final.mp4`, 11 có `preview.mp4`; 14 thư mục khác không có `meta.json`. Các con số này chỉ là bối cảnh, **không hardcode làm số liệu chạy thật**. 91 thư mục không đồng nghĩa 91 video thương mại đã hoàn tất.

Các shop thực tế gồm `giadungplus_official`, `lteng_vn`, `lteng_hcm`, `lteng_tiktok`, `phaledo_official`, `phaledo`, `phaledo_tiktok`, `phaledo_vn_tiktok`. Lấy danh sách và tên từ `assets/shops/*/shop.json`; nhận diện shop của job bằng `edl.shop`, không đoán từ tên thư mục. Có shop chưa đủ tài nguyên hoặc chưa có job.

`meta.json` hiện không có hợp đồng title sản phẩm, ngày tạo hay trạng thái tổng. Nếu thiếu tên hiển thị, dùng job ID, cho bổ sung tên thân thiện trong `management.json`. Ngày lấy từ file phải ghi rõ đó là thời gian sửa file, không bịa ngày tạo job.

Repo hiện **chưa có file settings JSON quản trị ở gốc, chưa có trạng thái kết thúc thống nhất và chưa có tracking Đăng SP / Shopee Video**. Hai file JSON mới phía trên là đề xuất cho tính năng này, không phải dữ liệu đã tồn tại. Tái sử dụng dữ liệu/config sẵn có, không yêu cầu người dùng khai lại shop và đường dẫn từng video.

## 3. Điểm quan trọng nhất: trạng thái phải nói đúng việc còn lại

Tách ba nhóm thông tin, không gộp thành một dấu xanh:

**A. Sản xuất video — đọc bằng chứng từ pipeline**

Các bước hiển thị gọn trong drawer: Nguồn → Phân tích → Biên tập → Nhạc & giọng → Render final → Kiểm tra → Duyệt sử dụng.

- File tồn tại chỉ xác nhận có artifact; không đủ để khẳng định bước đã đạt hoặc đang chạy.
- Có `final.mp4` = “Đã xuất final”, chưa đồng nghĩa “Video sẵn sàng”.
- QA hình chỉ đạt cho final khi `qa.video` là `final.mp4`, kết quả pass và bằng chứng còn phù hợp với bản final hiện tại. QA của preview không được nâng thành QA final.
- QA có thể bị ghi đè khi kiểm preview hoặc final; cần hiển thị đúng đối tượng đã kiểm. QA cũ hơn final = “Cần kiểm lại”; thiếu/không xác định = “Chưa đủ bằng chứng”. Mtime chỉ là chỉ báo freshness tối thiểu, không chứng minh toàn bộ revision.
- Kiểm tra hình, âm thanh, nghe lời đọc và duyệt sử dụng là các mục riêng. `narration.match` chỉ chứng minh đối chiếu giọng đọc, không tự chứng minh chất lượng âm thanh final.
- Hiện `vs.py audiocheck` chủ yếu in kết quả ra terminal; không giả định mọi job đều có báo cáo âm thanh JSON. File TXT/MD cũ chỉ là tài liệu tham khảo nếu chưa có bộ đọc và liên kết revision rõ ràng. Cho xem bằng chứng gốc và ghi nhận kiểm tra thủ công có thời điểm/bản final.
- Bằng chứng kiểm tra phải gắn với đúng bản final. Khi có hash trong `final-check.json`, đối chiếu hash; không coi một chuỗi `passed` cũ là chứng nhận hiện tại. Thiếu dữ liệu thì giữ chưa xác định. Ưu tiên hiển thị lý do cụ thể như “QA đang kiểm preview”, “Final đã đổi sau lần duyệt”, “Chưa ghi nhận nghe bản final”.
- Không đánh lỗi chỉ vì thiếu motion: job cũ có thể không bật motion. Nếu có motion và bằng chứng tương ứng thì hiển thị kết quả; chữ in trên sản phẩm được giữ nguyên không phải lỗi chữ đồ họa còn sót.
- Không suy ra “Đang render” hay phần trăm tiến độ từ sự tồn tại của file. Không có telemetry tiến trình thực thì hiển thị “Chưa rõ tiến trình đang chạy”. Stepper thể hiện bằng chứng các bước; không dùng animation đếm % giả.

**B. Hai xác nhận sử dụng video — người vận hành bấm độc lập**

1. **Đăng SP:** “Chưa xác nhận” / “Đã xác nhận”. Nghĩa là người vận hành xác nhận đã dùng video này cho trang sản phẩm.
2. **Shopee Video:** “Chưa xác nhận” / “Đã xác nhận”. Nghĩa là người vận hành xác nhận đã đăng video lên Shopee Video.

- Hai nút/trạng thái luôn nhìn thấy trên thẻ và trên hai cột riêng của bảng. Không bắt mở drawer để biết còn thiếu gì.
- Không liên thông hai xác nhận; đánh dấu mục này không tự đánh dấu mục kia. Không gọi API upload Shopee.
- Bấm xác nhận mở popover ngắn: tên video/shop, loại việc, người xác nhận, thời điểm tự điền; URL/mã sản phẩm/mã bài đăng và ghi chú là tùy chọn. Nhãn chính “Xác nhận đã đăng”.
- Chưa có record nghĩa là “Chưa xác nhận”, không suy ra chắc chắn chưa từng đăng. Nếu chưa có final hoặc final chưa đủ điều kiện sẵn sàng, không cho xác nhận mới và nêu việc cần làm trước.
- Cho hủy xác nhận với lý do, lưu lịch sử. Xác nhận gắn với revision final bằng SHA-256 tính khi cần, không hash toàn bộ thư viện mỗi lượt lọc.
- Final thay đổi: giữ lịch sử đăng của bản cũ, hiện “Đã xác nhận bản trước · cần xác nhận bản hiện tại”; không tự xác nhận bản mới và không xóa lịch sử.

**C. Kết thúc job — hành động có chủ ý**

- Nhãn dễ hiểu: “Đang xử lý”, “Chờ kiểm tra / duyệt”, “Chờ đăng”, “Đủ điều kiện kết thúc”, “Đã kết thúc”. Kèm cảnh báo riêng khi có lỗi/thiếu bằng chứng.
- “Đã kết thúc” chỉ xuất hiện sau khi người vận hành bấm **Kết thúc job**, với final hiện tại sẵn sàng và cả hai xác nhận hợp lệ. Không tự đóng job chỉ vì có final hoặc đã đủ hai tick.
- Có “Mở lại job”; lưu người, thời điểm, lý do. Khi final đổi sau khi đóng, đánh dấu cần xử lý lại bản hiện tại và giữ lịch sử lần đóng cũ.
- Có “Lưu trữ” riêng cho demo, bản bỏ hoặc job không còn dùng; lưu trữ không nghĩa là hoàn tất, không xóa thư mục/video. Có thể bỏ lưu trữ.

## 4. Bố cục và hướng hình ảnh

Tham khảo ảnh đính kèm ở **cách lướt một thư viện nhiều video**: video là trọng tâm, bộ lọc phía trên, các thẻ xếp hàng. Không sao chép toàn bộ navigation Marketing của ảnh, vì đây là ứng dụng quản trị local riêng.

- Header gọn: logo/wordmark “GDP Video Studio”, tên trang “Quản trị jobs”, trạng thái nguồn dữ liệu, thời điểm quét, nút “Làm mới” và “Thiết lập”.
- Sidebar nhỏ, có thể thu gọn: Tất cả jobs, Cần xử lý, Thư viện final, Đã kết thúc, Lưu trữ; bên dưới danh sách shop lấy từ hồ sơ hiện có. Không thêm menu không hoạt động.
- Phong cách chuyên nghiệp, gọn, tương phản tốt: nền ứng dụng trắng ngà/xám rất nhạt, khu video nền tối; màu đỏ GDP cho thao tác chính, xanh lục thành công, hổ phách chờ xử lý, đỏ lỗi. Badge shop dùng màu shop tiết chế. Không glassmorphism, gradient tràn lan hoặc nhiều KPI trang trí.
- Đầu trang có dải thống kê gọn, click được để lọc: Đang mở, Cần kiểm tra, Chờ Đăng SP, Chờ Shopee Video, Đã kết thúc. Các nhóm có thể chồng lấp; không trình bày như các phần cộng thành tổng.
- Toolbar sticky: tìm tên/ID/nguồn; lọc shop, trạng thái job, có final/chưa final, kiểm tra, hai xác nhận; sắp xếp theo lần cập nhật hoặc tên; nút chuyển “Lướt video / Danh sách”. Có chip bộ lọc đang áp dụng và Xóa lọc.
- Có lọc loại “Video theo shop / Nguồn phân tích / Thử nghiệm / Chưa phân loại”. Prefix source-/demo- chỉ gợi ý loại nếu không có metadata xác nhận, không tự loại mất dữ liệu. Thư mục phụ trợ và bản sao trong `_delivery-*` không biến thành video final trùng trong thư viện chính. Báo số mục bị bỏ qua/lỗi đọc thay vì âm thầm biến mất.
- Một nguồn có thể sinh nhiều shop, các job vẫn độc lập. Cho xem “Các phiên bản cùng nguồn” khi có hash nguồn hoặc liên kết đã xác minh; không gộp chỉ vì cùng tên file nguồn hay cùng vài số trong job ID.

**Chế độ Lướt video**

- Khoảng 4–5 cột trên desktop rộng, 3 cột laptop, 2 cột tablet, 1 cột điện thoại. Video 3:4, 9:16 và ngang đều không bị crop mất nội dung; poster nằm trong khung tối có tỷ lệ thống nhất, `object-fit: contain`.
- Mỗi thẻ: checkbox chọn, poster/player, thời lượng, badge final/preview/chưa final; tên video tối đa hai dòng; shop + job ID; trạng thái chính; hai trạng thái **Đăng SP / Shopee Video**; nút “Xem final” nổi bật và menu phụ.
- Bấm video phát tại thẻ hoặc mở drawer lớn. Chỉ một video phát tại một thời điểm. Mặc định không autoplay, không phát tiếng hàng loạt; có controls và fullscreen.
- Job không có final: “Chưa có final”; nếu có preview thì có nút xem preview với nhãn rõ. Không tráo preview thành final.
- Không lấy `contact.jpg` làm poster một cảnh. Có thể lấy khung video khi người dùng yêu cầu hoặc dùng placeholder có thiết kế tốt. Media lỗi có thông báo và nút thử lại, không spinner vô hạn.

**Chế độ Danh sách**

- Bảng có cột: chọn, thumbnail + tên/ID, shop, trạng thái job, bước còn thiếu, final, kiểm tra, **Đăng SP**, **Shopee Video**, lần cập nhật, thao tác.
- Header sticky, độ cao hàng vừa phải, sort/filter dùng được, có phân trang hoặc tải thêm. Hai cột xác nhận không bị giấu trong tooltip.
- Chọn nhiều hiện thanh thao tác: xác nhận Đăng SP, xác nhận Shopee Video, kết thúc các job đủ điều kiện, lưu trữ, xuất danh sách JSON. Popover tổng kết số được phép/số bị chặn trước khi ghi; báo kết quả từng job nếu có lỗi. Không xóa hàng loạt.

**Drawer chi tiết**

- Player lớn, chuyển Final / Preview / Nguồn nếu file tồn tại. Ưu tiên mở final.
- Tên, shop, ID, loại job, ghi chú; tiến trình theo bằng chứng; lỗi hoặc việc còn thiếu đặt gần nút hành động.
- Khối “Kiểm tra & duyệt”: QA hình, âm thanh, nghe lời, duyệt sử dụng; từng mục có trạng thái, thời điểm, bản video đã kiểm, nút xem bằng chứng nếu có. Cho ghi nhận duyệt thủ công đúng revision; không sửa kết quả QA của pipeline từ UI.
- Khối “Sử dụng video”: hai xác nhận độc lập, link tham chiếu nếu đã nhập, người/thời điểm, lịch sử.
- Nút tải final; sao chép đường dẫn file/thư mục; xem metadata và bằng chứng. Trình duyệt không có quyền mở Explorer trực tiếp thì chỉ hiện thao tác sao chép đường dẫn, không làm nút “Mở thư mục” giả.
- Escape đóng; trả focus về phần tử đã mở; Tab thao tác được; nội dung dài cuộn trong drawer.

## 5. Đọc/ghi file local, không DB

Đây là HTML độc lập. **Không tuyên bố rằng JavaScript có thể tự quét và ghi ổ C chỉ vì biết đường dẫn.**

- Màn kết nối hiển thị Studio mặc định `C:\Users\Admin\gdp-video-studio` và nút **Chọn thư mục Studio**. Dùng File System Access API khi trình duyệt/ngữ cảnh hỗ trợ để người dùng cấp quyền chọn đúng thư mục gốc. Kiểm tra `jobs/` và `assets/shops/`, báo thiếu rõ ràng.
- Không thể ép picker tự chọn một đường dẫn Windows bất kỳ. Nếu chưa được cấp quyền, không tự ghi hoặc báo đã đồng bộ. Sau khi tải lại trang, cho kết nối lại nếu chưa còn quyền/handle.
- Có ba trạng thái nguồn phân biệt rõ: **Dữ liệu thật**, **Demo**, **JSON nhập thủ công**. Không trộn demo vào dữ liệu thật. JSON nhập thủ công không tự ghi ngược vào Studio; chỉnh sửa được xuất bằng nút tải JSON.
- Khi API không hỗ trợ, môi trường Claude Design không truy cập được ổ local hoặc người dùng từ chối quyền: demo vẫn hoạt động; có nhập/xuất JSON và hướng dẫn ngắn. Import JSON không chứa video thì chỉ hiển thị metadata và cho chọn file video tương ứng khi cần.
- Không dùng SQLite, PostgreSQL, Firebase hoặc IndexedDB làm DB quản trị. File JSON là nơi lưu chính. `localStorage` chỉ được lưu tùy chọn hiển thị hoặc bản nháp chưa lưu, không thay cho dữ liệu nghiệp vụ và không hiện “Đã lưu vào Studio” khi chỉ lưu trong browser.
- `dashboard.settings.json` ở gốc lưu tùy chọn quản trị: schema_version, root_path để hiển thị, view mặc định, page size, bộ lọc ưa thích. Không sao chép hay thay `.env`, `studio/config.py`, `shop.json`; không lưu API key.
- `jobs/<id>/management.json` lưu tên hiển thị, loại job đã xác nhận, ghi chú, duyệt thủ công gắn final revision, hai xác nhận, trạng thái kết thúc/lưu trữ và lịch sử. Không ghi đè `meta.json`, `edl.json`, `qa.json` hay các output pipeline.
- Ghi nhận revision final hiện tại khi duyệt/xác nhận/đóng job; lịch sử giữ revision cũ. Dùng schema nhất quán, đơn giản; hỗ trợ thiếu file cũ mà không suy diễn đã hoàn thành.
- Metadata kỹ thuật được quét lại từ file, không duy trì một bản “status” thủ công mâu thuẫn pipeline. Settings không được ghi đè xác nhận nghiệp vụ.
- Trước khi lưu, phát hiện file bị thay đổi bên ngoài so với lần đọc; xung đột thì yêu cầu nạp lại/giữ bản nháp, không ghi đè im lặng. Chỉ hiển thị “Đã lưu” sau khi write/close thành công; lỗi quyền/hết dung lượng/JSON hỏng cần trạng thái lỗi và cho thử lại hoặc xuất bản nháp.
- Giới hạn ghi trong thư mục người dùng đã chọn, qua handle có sẵn; không dùng đường dẫn tùy ý lấy từ JSON để truy cập ngoài thư mục đó.
- Không cần local server cho bản thiết kế này. Tách lớp dữ liệu để coding agent có thể nối adapter Python local sau nếu muốn; không tự thêm server, API giả, daemon hay lệnh shell vào UI.

## 6. Hiệu năng và độ tin cậy

- Đọc metadata nhẹ trước; không đọc toàn bộ MP4 hoặc mọi `usage.jsonl` khi mở thư viện. Lazy-load media chỉ ở thẻ cần xem. Dùng File/Object URL cho video local; thu hồi URL khi không còn dùng.
- Quét thủ công bằng “Làm mới”; có chỉ báo đang quét và thời điểm quét thành công. Nếu thêm theo dõi định kỳ thì phải nhẹ và cho tắt; không gọi analyze/render/QA/AI chỉ để cập nhật dashboard.
- Không tạo phần trăm tiến độ giả; không tự chạy pipeline, phát sinh Gemini/TTS/Lyria hoặc thay animation. Các thao tác sản xuất chưa tích hợp không được giả lập như đã thực thi.
- JSON lỗi ở một job không làm hỏng cả thư viện; hiện item lỗi với đường dẫn và lý do. Phân biệt giá trị 0 hợp lệ, chưa có dữ liệu và lỗi đọc.
- Tất cả số đếm và empty state cập nhật theo scope/filter nhất quán. Có “Chưa kết nối”, “Chưa có jobs”, “Không có kết quả”, “Mất quyền đọc/ghi”, “Final bị mất”, “Bằng chứng cũ”, “Thay đổi chưa lưu”, “Lưu thất bại”.
- Không render tiêu đề/ghi chú nhập từ JSON bằng HTML không kiểm soát. Không đọc/hiện `.env`, thông tin đăng nhập hay khóa dịch vụ.

## 7. Dữ liệu demo để kiểm chứng thiết kế

Tạo khoảng 18–24 job mẫu có tên Việt tự nhiên: kệ khăn hai cốc hút, giá treo dép, móc treo cửa, kệ góc nhà tắm, hũ rắc gia vị. Phân bố giữa Gia Dụng Plus, LTENG VN, LTENG HCM, PHALEDO. Có đủ các ca:

1. Có final và đầy đủ bằng chứng, chưa xác nhận hai kênh.
2. Đã xác nhận Đăng SP, còn Shopee Video; và ca ngược lại.
3. Đủ hai xác nhận nhưng chưa bấm kết thúc.
4. Đã kết thúc, có lịch sử người/thời điểm.
5. Có final nhưng QA chỉ kiểm preview.
6. Final mới hơn QA hoặc đã đổi hash sau lần duyệt/đăng.
7. QA hình đạt, âm thanh hoặc duyệt sử dụng còn thiếu bằng chứng.
8. QA không đạt, có lý do cụ thể.
9. Chỉ có preview; mới có nguồn/phân tích; chưa biết shop.
10. Job nguồn dùng chung cho ba shop; demo motion; item lưu trữ.
11. JSON lỗi, final bị mất, lưu bị từ chối.

Demo không có media thật phải ghi “Video minh họa/chưa nạp file” và cho chọn MP4 để thử player, không dùng đường dẫn Internet hoặc tạo spinner giả. Có thể dùng poster SVG minh họa tĩnh, nhưng không giả đó là thumbnail đã trích từ final thật.

## 8. Những thao tác bắt buộc chạy được trong prototype

Chuyển lướt/list; tìm kiếm; lọc kết hợp; xóa lọc; sort; chọn nhiều; mở/đóng drawer; xem video được chọn; xác nhận riêng từng kênh; hủy xác nhận có lý do; kết thúc/mở lại job theo điều kiện; lưu trữ/bỏ lưu trữ; sửa tên/ghi chú; xem lịch sử; nhập/xuất JSON; chọn thư mục nếu môi trường hỗ trợ; thông báo lưu thành công/thất bại đúng thực tế.

Kiểm tra ở 1440px, 1280px và 390px. Desktop cần nhìn được nhiều jobs; mobile vẫn thao tác được hai xác nhận và phát final. Trạng thái không chỉ phân biệt bằng màu; có chữ và icon. Có focus rõ, nhãn nút, tương phản đủ và hỗ trợ giảm chuyển động.

Trước khi giao, tự đi qua ba hành trình: **tìm final của một shop → xem ngay**, **lọc các video còn Shopee Video → xác nhận đúng bản**, **tìm job chưa kết thúc → hiểu việc còn thiếu → đóng khi đủ điều kiện**. Đảm bảo số đếm, thẻ, bảng và drawer đồng bộ.

Hãy giao **một file `index.html` hoàn chỉnh**, có chú thích ngắn cho data adapter và schema JSON, không placeholder code hoặc nút chết. Màn hình mở đầu phải cho thấy ngay một thư viện video được tổ chức tốt và công việc còn lại của từng job.
