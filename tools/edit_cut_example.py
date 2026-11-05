"""Bản THỬ GĐ1 skill gdp-video-edit (05/11): vlog 5 ngày Bắc Kinh — 11 clip Sếp quay + giọng AI đọc kịch bản Claude
tự viết (Sếp: "tự bịa nội dung bằng voice AI"), xen 1 câu tiếng gốc selfie c01 "tôi đang ở Bắc Kinh".
Chạy: vs.py edit cut test-vlog-bac-kinh  (bản lưu git của jobs/test-vlog-bac-kinh/cut.py — jobs/ không vào git)"""
from studio.edit.cutlib import Cut

c = Cut(__file__)

# ── trục lời: giọng đọc vo, chèn 1 câu tiếng gốc c01 (người nói selfie) ──
c.say("vo", "Năm ngày ở Bắc Kinh", "khắp nơi")
c.say("c01", "tôi đang ở", "Bắc Kinh", frame="tight", push=0.08, tighten=None)
c.say("vo", "Bữa tối có cả", "cho mình nhé")

# ── hình ──
c.card(at=0.0, until="cảnh đẹp")                                         # mở đầu: màn đen chữ
c.cover("c08", at="Cả nhóm", until="háo hức", src_in=6.0)                 # selfie trên máy bay, vẫy tay
c.cover("c11", at="Vừa đáp xuống", until="cả chân", src_in=0.0, trans="flash")   # sân bay
c.cover("c05", at="Đường về", until="tới mức", src_in=0.0)               # xe trên cao tốc
c.cover("c06", at="có người", until="quên luôn", src_in=0.3)              # ngủ quên trên xe
c.card(at="Và đây mới là", until="bất ngờ nhất")                          # câu chốt giữa bài
c.cover("c03", at="Ở khách sạn", until="lên phòng", src_in=0.5)           # robot đi trong sảnh
c.cover("c03", at="là một chú", until="robot", src_in=12.6, trans="flash")  # mặt robot cười
c.cover("c04", at="Cà phê", until="tuỳ thích", src_in=0.0)                # máy cà phê → bình nước ép
c.cover("c07", at="Buổi sáng", until="tập trung", src_in=0.0, speed=0.75, trans="wipe")   # văn phòng (chậm lại)
c.cover("c02", at="Tối đến", until="lên đèn", src_in=0.0, trans="flash")   # cổng phố cổ lên đèn
c.cover("c10", at="các bạn trẻ", until="khắp nơi", src_in=0.0, speed=0.8)  # Hán phục
c.cover("c09", at="Bữa tối", until="nhà hàng", src_in=2.0, trans="flash")  # múa truyền thống
c.cover("c11", at="Chuyến đi", until="cho mình nhé", src_in=7.6)          # sân bay ra về

# ── chữ động (đúng lời đã nói, theo thứ tự) ──
c.cap("!NĂM NGÀY Ở / ~^BẮC KINH", exit="rise")
c.cap("thứ làm tôi / !BẤT NGỜ NHẤT / .không phải là / !^CẢNH ĐẸP", exit="fade")
c.cap("cả nhóm lên máy bay / .từ sáng sớm", y=0.64)          # selfie: mặt ở giữa khung → hạ chữ (soát mắt)
c.cap("!!AI CŨNG HÁO HỨC", y=0.64)
c.cap("vừa đáp xuống / .sân bay rộng tới mức / !ĐI BỘ MỎI CẢ CHÂN")
c.cap("đường về khách sạn / !THẲNG TẮP")
c.cap(".xe chạy êm tới mức / có người / !!NGỦ QUÊN LUÔN", y=0.66)   # né mặt người ngủ
c.cap("và đây mới là / thứ làm tôi / !^BẤT NGỜ NHẤT", exit="fade")
c.cap(".ở khách sạn / người mang đồ lên phòng / !^MỘT CHÚ ROBOT")
c.cap("cà phê nước ép ở sảnh / !MIỄN PHÍ")
c.cap(".uống bao nhiêu / tuỳ thích", exit="fade")
c.cap("buổi sáng chúng tôi ghé / .văn phòng một đối tác")
c.cap(".ai cũng làm việc / !!RẤT NHANH / .và tập trung")
c.cap("tối đến / !PHỐ CỔ LÊN ĐÈN")
c.cap(".các bạn trẻ mặc / !^HÁN PHỤC / .dạo phố khắp nơi")
c.cap("tôi đang ở / !BẮC KINH", exit="rise", y=0.6)
c.cap("bữa tối có cả / !MÀN MÚA TRUYỀN THỐNG / .ngay giữa nhà hàng")
c.cap("chuyến đi ngắn thôi / !!NHƯNG NHỚ MÃI")
c.cap("bạn muốn xem / !TẬP TIẾP THEO / .ở đâu")
c.cap("!^BÌNH LUẬN / .cho mình nhé", exit="fade")

c.logo("giadungplus_official")   # thử đường logo nhỏ góc trên (vlog thật thì Sếp chọn có/không)
c.save()
