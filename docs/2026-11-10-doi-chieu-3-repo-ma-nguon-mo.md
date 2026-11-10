# Đối chiếu 3 repo mã nguồn mở với GDP Video Studio

Ngày 10/11/2026. Ba repo tải về `C:\Users\Admin\THAMKHAO\video-oss\` (chỉ đọc, không chạy code của họ):

| Repo | Giấy phép | Bản | Soi với phần nào của studio |
|---|---|---|---|
| `browser-use/video-use` | MIT | 08/10/2026 | `studio/edit/` (dựng video quay sẵn) |
| `Vincentwei1021/video-shotcraft` | Apache-2.0 | 09/11/2026 | Scene Library, thư viện hiệu ứng, tiếng động, xuất CapCut |
| `kajisho5/ffmpeg-skill` | MIT | 07/11/2026 | mọi lệnh ffmpeg của studio |

Cách làm: mỗi repo một subagent Sonnet 5.5 đọc code của họ và code studio tương ứng, so từng khâu.
Các phát hiện ở nhóm A và B1, B2 đã được mở code studio kiểm lại (cột "Kiểm").

## 1. Kết luận

**Lõi của họ không nhanh hơn hay hay hơn lõi studio.** Cả ba subagent kết luận độc lập như vậy:

- video-use chỉ có khoảng 2.100 dòng Python; phần lớn "luật" nằm trong văn bản hướng dẫn cho AI, không có code ép.
  Studio ép bằng code (`cutlib.py`, `qa.py`).
- video-shotcraft: 124 công thức là file Markdown, không có schema. Đồng bộ nhịp nhạc và storyboard tự động
  chỉ là tài liệu, không có code chạy.
- ffmpeg-skill: tham số mã hoá của họ (CRF 20) thấp hơn studio (CRF 18). Họ không có đường NVENC.

**Chỗ họ hơn thật là kinh nghiệm với đầu vào "bẩn" và vài chi tiết âm thanh.** Họ đã vấp và xử lý những ca studio
chưa gặp: clip iPhone HDR, video xoay, khung hình đứng, màu lệch khi mã hoá. Giá trị mang về gồm:

- 8 bản vá phòng lỗi, đều nhỏ (nhóm A)
- 6 nâng cấp chất lượng dựng (nhóm B)
- 1 tính năng mới: dựng video không lời (nhóm C)

Không có lý do nào để đổi nền hay nhúng nguyên repo nào vào studio.

## 2. Nhóm A — vá lỗi tiềm ẩn (nhỏ, rủi ro thấp)

| # | Việc | Chỗ sửa | Vì sao | Nguồn học | Kiểm |
|---|---|---|---|---|---|
| A1 | Sửa vòng lặp đọc góc xoay | `studio/media.py:23-25` | Vòng lặp chạy qua mọi mục `side_data_list`; mục cuối không có `rotation` sẽ ghi đè về 0, khung dọc bị hiểu thành ngang. `project._probe` đã viết đúng, `media.probe` thì chưa. | ffmpeg-skill `scripts/_common/probe.py:299-302` | Đã đọc code, logic lỗi chắc chắn. Chưa tái hiện bằng clip thật. |
| A2 | Gắn ma trận + tag màu bt709 cho bộ ghi video | `studio/edit/build.py:987-990`, `studio/edit/capcut.py:289-293` | Khung `bgr24` đổi sang YUV bằng ma trận BT.601 và file không gắn tag. Đo trên màu rực: lệch Y 18,45 → 0,87 sau khi sửa. Trên cảnh quay thật khác biệt nhỏ. Ảnh hưởng chủ yếu tới logo, chữ màu shop, đồ hoạ. | ffmpeg-skill `scripts/_common/color.py:12-31` | Đã đọc code. Số đo do subagent chạy ffmpeg. |
| A3 | Chuyển HDR về SDR khi đọc nguồn | `studio/edit/build.py:38-40` (`Reader`), `studio/edit/project.py:54` (ghi `color_transfer`) | iPhone mặc định quay HLG. Studio đọc thẳng nên hình sẽ bệt màu hoặc cháy sáng, không cảnh báo. Hiện mọi clip trong `inbox/` và `jobs/` đều là SDR nên chưa xảy ra. | video-use `helpers/render.py:123-146`; ffmpeg-skill `color.py:201-213` | Đã kiểm: `studio/` không có dòng tone-map nào; ffmpeg 9.0.2 trên máy có `zscale` + `tonemap`. |
| A4 | Thêm dò khung đứng + đoạn đen vào QA | `studio/edit/qa.py`, `studio/qa.py` | `Reader.read` giữ nguyên khung cuối khi nguồn hết sớm, video đứng hình mà không báo. `freezedetect=n=-60dB:d=0.5`, `blackdetect=d=0.1:pix_th=0.10`. | ffmpeg-skill `probe.py:980-1060` | Đã đọc `Reader.read`. Chưa đo tần suất thật. |
| A5 | Thêm giới hạn thời gian cho lệnh ffmpeg | `studio/media.py:11-15` (`run`) | Một ffmpeg treo sẽ treo cả job. Họ đặt mặc định 1800 giây và huỷ tiến trình con. | ffmpeg-skill `scripts/_common/runner.py` | Đã đọc code. |
| A6 | Bỏ đường dẫn font Windows gắn cứng | `studio/edit/project.py:227` | `fontfile='C\:/Windows/Fonts/arial.ttf'` sẽ lỗi trên Mac. | ffmpeg-skill `decision.py:308-345` | Đã đọc code. Chưa chạy trên Mac. |
| A7 | Gộp hai hàm probe, thêm cờ VFR | `studio/media.py:22`, `studio/edit/project.py:64` | Một hàm dùng `avg_frame_rate`, một hàm dùng `r_frame_rate`. Dữ liệu studio có clip VFR thật (ví dụ 30/1 so với 1275/43). Nhánh Việt hoá ép outro về fps lẻ khi nối. | ffmpeg-skill `decision.py:444-451` | Subagent đo trên `inbox/` và `jobs/*/sources/`. |
| A8 | Lùi mốc seek 1 giây cho nguồn HEVC | `studio/edit/build.py:38` | Seek thẳng trên HEVC có B-frame từng bắt đầu trễ 0,1 giây. | ffmpeg-skill `cut.py:856-858` | Chỉ dựa trên ghi chú của họ. |

## 3. Nhóm B — nâng chất lượng dựng

| # | Việc | Chỗ sửa | Lợi ích | Công sức | Nguồn học | Kiểm |
|---|---|---|---|---|---|---|
| B1 | Căn đỉnh âm từng file tiếng động | `studio/edit/build.py:391-398` | Hiện tiếng đặt từ đầu file. Tiếng có đỉnh trễ (giấy xé, gió vút) rơi chậm hơn hình. Đo đỉnh từng file rồi đặt tại `at − đỉnh`. | Nhỏ | video-shotcraft `references/sound-design.md` §4.6, `assets/scripts/sfx-source.py` (`analyze`) | Đã đọc code studio. |
| B2 | Xuất giọng, nhạc, tiếng động thành track riêng sang CapCut | `studio/edit/capcut.py:491-495`, `studio/edit/build.py:352-401` | Hiện track "voice" lấy từ `final.mp4`, tức đã trộn cả nhạc và tiếng động. Dựng viên không chỉnh riêng nhạc được. | Vừa | video-shotcraft `jianying-export/aifl_promo.py` | Đã đọc code studio. Cần thử trên CapCut. |
| B3 | Chế độ render nháp chỉ để chốt điểm cắt | `studio/edit/build.py:943` (`run`) | Preview 40 giây hiện mất 48–148 giây, chữ động chiếm tới 80 giây ở một job. Nháp bỏ chữ + đồ hoạ sẽ ra trong vài giây. | Vừa | video-use `helpers/render.py:288-293` | Số giây lấy từ `render_*.json` trong `jobs/`. |
| B4 | Soát mối cắt trên bản đã dựng | `studio/edit/qa.py`, `studio/edit/project.py:223` | QA hiện không nhìn mối cắt trên bản ra. Thêm ảnh dải khung + sóng âm quanh từng mối cắt, và đo gai biên độ để bắt tiếng "tách". | Vừa | video-use `helpers/timeline_view.py:68-112, 184-330` | Chỉ subagent đọc. |
| B5 | Tự gom chữ làm phụ đề nhanh | `studio/edit/cutlib.py` (thêm `auto_caps`) | Video cần ra gấp không phải viết tay từng khối chữ. Luật: ngắt theo dấu câu, khoảng lặng ≥ 0,3 giây, cụm hiện dưới 0,35 giây thì gộp. | Nhỏ | video-use `helpers/render.py:433-465` + test | Chỉ subagent đọc. |
| B6 | Tăng fade tiếng ở mối cắt từ 8 ms lên 15–30 ms | `studio/edit/build.py:358` | An toàn hơn khi mối cắt rơi vào tiếng liên tục. Fade dài có thể cắt mất âm đầu từ, phải thử bằng tai. | Nhỏ | video-use `helpers/render.py:285-286` | Đã đọc dòng 358. |

## 4. Nhóm C — tính năng mới: dựng video không lời (POV / ASMR)

Cả ba repo đều **không** giải quyết được việc này; video-use còn vẽ sai (coi toàn bộ clip không lời là "lặng").
Nhưng ghép các mảnh lại thì studio tự xây được:

1. **Dò lúc tiếng bật lên** (nước bắt đầu rót, đá chạm ly) thay vì dò mức im lặng tuyệt đối. Thuật toán:
   hiệu bậc nhất của log-RMS bước 10 ms, lấy đỉnh vượt trung vị + k·MAD, có khoảng trơ.
   Nguồn: ffmpeg-skill `scripts/_common/decision.py:1151-1175`. Chép sang numpy được trong vài chục dòng.
2. **Danh sách "cụm tiếng động"** thay cho lời: đảo ngược `asr.pauses` (`studio/edit/asr.py:100`) vốn đã đo
   khoảng lặng bằng RMS 10 ms. Đưa vào `project.describe` khi nguồn không có lời.
3. **Ảnh dải khung + sóng âm** để AI nhìn thấy tiếng động khi chọn điểm cắt (dùng chung với B4).
4. Tắt hoặc đặt lại ngưỡng `tighten`: với ASMR, khoảng lặng giữa hai tiếng là một phần của nhịp.
5. `silencedetect` mặc định −35 dB không hợp: nó coi tiếng rót khẽ là im lặng.

Công sức: lớn. Đây là lỗ hổng thật duy nhất về tính năng mà đợt soi này tìm ra.

## 5. Không làm, hoặc để sau

| Việc | Quyết định | Lý do |
|---|---|---|
| Đổi sang mã hoá GPU (NVENC) | Không làm | Đo trên RTX 4060, 10 giây 1080×1920: x264 1,24 giây, NVENC 1,38 giây, file NVENC lớn hơn 54%. Chỗ chậm là Python xử lý khung, không phải mã hoá. |
| Đồng bộ điểm cắt theo nhịp nhạc | Để sau | Chỉ có ích khi làm montage cắt theo nhạc. Video có lời cắt theo từ là đúng. Shotcraft chỉ có tài liệu (`references/music-beat-sync.md`), không có code. |
| Công cụ tải tiếng động từ Freesound | Để sau | Quét HTML của trang, dễ hỏng; file tải là MP3 xem thử, không phải bản gốc. |
| Tự chỉnh màu theo từng clip | Để sau | Có thể làm lệch LUT của phong cách đã chỉnh theo mẫu. Chỉ nên là tuỳ chọn. Nguồn: video-use `helpers/grade.py:78-271`. |
| Bộ easing dùng chung cho cảnh HTML | Để sau | Phải đọc `assets/scenes/_uikit/uikit.js` trước, có thể đã có. Nguồn: shotcraft `demos/_fixtures/Polish.tsx:12-60`. |
| Ghi "ngưỡng hỏng" vào `scene.json` | Làm khi duyệt công thức | Là kiến thức đáng giá nhất của Shotcraft (cột thứ ba bảng `参数表` trong từng thẻ), nhưng phải đọc tay từng thẻ. |
| Đổi vùng an toàn TikTok | Không đổi mù | Họ đặt cạnh dưới 0,22, studio 0,12. Họ tự ghi số của mình là "rộng rãi", studio đặt theo thử thật 05/11. So lại bằng ảnh chụp giao diện TikTok nếu cần. |
| Chụp khung animation song song | Để sau | Chưa đo mức tăng tốc; có rủi ro mất tính tái lập. |
| Giảm nhạc tự động theo giọng (ducking) | Không làm | Studio đã thử và bỏ có chủ ý (`studio/render.py:507-508`). |

## 6. Chỗ studio đã ngang hoặc hơn (khỏi làm lại)

- Bám điểm cắt vào ranh giới từ bằng code, QA bắt lỗi cắt giữa từ. video-use chỉ nhắc bằng chữ.
- Phiên âm Whisper local, cache theo hash nội dung, kéo mốc từ theo năng lượng tiếng. video-use dùng ElevenLabs trả phí.
- Mã hoá một lần duy nhất. video-use mã hoá hai lần khi có phụ đề.
- Chữ động theo từng từ, né mặt, vùng an toàn. Cả ba repo không có gì tương đương.
- Chuẩn âm lượng đo–bù–đo lại. Shotcraft nhân hệ số bằng tay.
- `scene.json` + `catalog.json` có điều kiện dùng và ngân sách điểm. Shotcraft chỉ có 10 thư mục và lọc chuỗi.
- Bản nháp CapCut giữ clip gốc + lớp đè alpha. Shotcraft chỉ có một tấm nền đã nướng sẵn.
- Kiểm tái lập khi chụp khung animation (`studio/motionlib.py`). Shotcraft không có.

## 7. Danh mục chuyển động của video-shotcraft (để duyệt sau)

- **124 công thức, 150 kiểu**: `references/shots/<nhóm>/<tên>.md` (Markdown tiếng Trung).
- **Chỉ mục máy đọc**: `gallery/api/library.json`, mỗi thẻ có `name`, `summary`, `use`, `duration`, `energy`, `category`, `styles[]`.
- **Số thẻ theo nhóm**: typography 22 · ui-entrance 21 · effects 15 · transition 15 · interaction 11 · opening 11 ·
  camera 10 · rhythm 8 · outro 6 · data 5.
- **Code từng thẻ**: `demos/<nhóm>/<tên>/*.tsx` (Remotion/React; giá trị đã chỉnh thật nằm cứng trong đây).
- **150 clip xem thử không nằm trong repo**: ở release `gallery-media` trên GitHub, tải bằng `gallery/fetch-media.sh`. Chưa tải.
  Xem trực tuyến: `https://vincentwei1021.github.io/video-shotcraft/`.
- Nhạc trong `assets/audio/bgm` có một bài chưa rõ nguồn gốc bản quyền, không chép sang.

## 8. Đã triển khai (10/11, nhánh `hoc-oss-va-loi-nang-cap`, chưa commit)

Thử trên ba bản sao job (`jobs/_thu-oss-bac-kinh`, `_thu-oss-qa`, `_thu-oss-khong-loi`): cắt → nháp → preview → QA đều
ĐẠT. Test: `test_sound` 32/32 · `test_reveal` 20/20 · `test_motion` 73/73 · `test_font_gate` chặn đúng.

| Mục | Kết quả | Số đo |
|---|---|---|
| A1 góc xoay | Đã vá `media.probe` | Mô phỏng clip Dolby Vision dọc: ra đúng 1080×1920 |
| A2 tag màu | Đã vá (`media.BT709_OUT`, dùng ở `build.py` + `capcut.py`) | Màu rực qua trình phát: lệch 6,0 → 1,6 mức; bản dựng có tag `tv,bt709,bt709,bt709` |
| A3 HDR → SDR | Đã vá (`media.sdr_filter`, áp ở `Reader` + ảnh lưới) | Clip HLG thử: sáng 76 → 113 (gốc 115). Dùng `mobius` thay `hable` (hable làm tối cả khung). Chưa thử clip iPhone thật |
| A4 đứng hình | Làm khác đề xuất: đếm khung nguồn không trả ngay trong `Reader`, QA báo lỗi khi > 3 khung; `cut` cảnh báo sớm | Bắt được lỗi thật: mẫu Bắc Kinh cảnh `c10` đứng hình 12 khung (0,4 s) |
| A5 giới hạn thời gian | Đã vá `media.run`, mặc định 30 phút | — |
| A6 font Mac | Đã vá, dùng font trong repo | Chưa chạy trên Mac |
| A7 gộp probe | **Không sửa** | Nhánh dựng đã ép fps cố định; nhánh Việt hoá đang chạy ổn, đổi fps có rủi ro mà không rõ lợi |
| A8 seek HEVC | **Không sửa** | Thử 10 mốc: H.264 và HEVC cho kết quả giống hệt nhau, khác biệt chỉ là quy ước làm tròn 1 khung. Lỗi họ mô tả không tái hiện trên ffmpeg 9.0.2 |
| B1 căn đỉnh tiếng động | Thư viện hiện tại **không bị lỗi**: tiếng "chạm" đỉnh ≈ 0 s, tiếng "vuốt" gắn vào lúc bắt đầu chuyển động là đúng. Chỉ thêm tuỳ chọn `"align": "peak"` trong `scene.json` | Đỉnh đo: click/ting 0,00–0,01 s · whoosh 0,09–0,15 s · swell 0,49 s |
| B2 track tiếng riêng CapCut | Đã làm: giọng · nhạc · tiếng gốc · từng tiếng động | Tổng các track = bản dựng (−14,3 LUFS, −1,4 dBTP). **Chưa mở bằng CapCut thật** |
| B3 render nháp | Đã làm: `vs.py edit render <id> --draft` | 10,0 s cho job 41 s (preview 49 s); 30,4 s cho job 54 s có 5 đồ hoạ (preview 160 s) |
| B4 soát mối cắt | Đã làm: `qa_<bản>_cuts.jpg` + cảnh báo "mép còn tiếng to" | Tìm ra hai lỗi bên dưới |
| B5 phụ đề nhanh | Đã làm: `c.auto_caps()` | Chưa tách được từ ghép tiếng Việt, đôi lúc ngắt gãy |
| B6 fade 8 → 30 ms | **Không đổi** cho lời; đoạn không lời dùng 30 ms | Lỗi thật không nằm ở độ dài fade mà ở hai lỗi bên dưới |
| C video không lời | Đã làm: `studio/edit/sound.py`, `c.sound()`, `cap(at=…)`, ảnh `sheets/<key>.sound.jpg` | Dò tiếng bật trên tiếng tổng hợp: 8/8, báo nhầm 0, sai số trung bình 0,2 ms. **Chưa có clip ASMR thật** |

Hai lỗi có sẵn trong studio mà B4 làm lộ ra, đã vá:

- **Tiếng "nấc" mỗi lần đổi cỡ khung.** Hai đoạn lời nối liền (chỉ đổi khung hình) vẫn bị vuốt 8 ms hai đầu, tạo lõm
  16–19 dB giữa lời đang nói. `build_audio` giờ đọc các đoạn liền một lần. Sau vá: độ lõm ở 8 mối của job thử bằng đúng
  dao động tự nhiên của tiếng nguồn.
- **Cắt cụt đuôi từ 40–60 ms.** Whisper báo hết từ sớm hơn tiếng thật ("robot" hết 24,40 s, tiếng tới 24,57 s).
  `c.say` giờ dời mép tới chỗ tiếng tắt (`sound.settle`). Trên hai job thử: 9 mép dời +35…+170 ms, các mối liền vẫn
  liền, không đoạn nào chồng nhau, QA hết cảnh báo.

Còn lại chưa làm: chồng-trộn (crossfade) cho mối cắt giữa tiếng kéo dài của video không lời — chờ có clip ASMR thật để
nghe rồi quyết.

## 9. Mức độ chắc chắn (lúc viết bản đối chiếu, trước khi triển khai)

- **Đã mở code studio kiểm lại**: A1, A2, A3, A5, A6, B1, B2, B6 và `Reader.read` của A4.
- **Subagent đo bằng ffmpeg thật**: màu lệch (A2), NVENC so với x264, clip VFR trong dữ liệu studio (A7).
- **Chỉ suy ra, chưa có bằng chứng thật**: A1 và A3 chưa tái hiện vì studio chưa có clip iPhone HDR / Dolby Vision nào;
  A8 chỉ theo ghi chú của họ; ba cái bẫy CapCut trên Mac (`jianying-export/mac_draft.py:1-20`) chưa đối chiếu.
- **Chưa làm**: không chạy code hay bộ test nào của ba repo; chưa sửa dòng code nào của studio.
