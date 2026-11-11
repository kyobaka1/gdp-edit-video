"""0379 — hũ thuỷ tinh vuông nắp tre, bản VIỆT HOÁ V2 (PHALEDO): xoá chữ Trung (edl.clean) + chữ Việt động (edl.caps).
Mẫu đủ bộ cho quy trình V2 — skill gdp-video-localize, mục "Việt hoá V2". (Bản lưu git của
jobs/phaledo-0379-v2/direct.py — chép vào jobs/<id>/direct.py rồi sửa; file này không chạy trực tiếp trong tools/.)

Khác bản cũ (jobs/phaledo-0379): không còn viên đen 720×134 che phụ đề; chữ Trung được nội suy nền / nhoè mép mềm,
chữ Việt nhỏ gọn nhiều độ đậm, đổi ~2s/khối, lời đọc dày hơn (tempo 1,08).
Sự thật sản phẩm CHỈ lấy từ video gốc: hũ kín · nhiều cỡ · nắp tre gioăng silicone · chống ẩm (làm mềm) · thân dày ·
miệng rộng đựng gia vị / trà hoa / ngũ cốc · kèm thìa gỗ · dáng vuông xếp chồng · borosilicate chịu nóng lạnh.
"""
import json
from pathlib import Path

d = Path(__file__).resolve().parent
meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
edl = json.loads((d / "edl.draft.json").read_text(encoding="utf-8"))
edl["shop"], edl["brand"] = "phaledo_official", "PHALEDO"

# nguồn đã cắt 0,5s đầu (hiệu ứng bật quá to của NCC) + outro NCC → mốc phân tích lùi 0,5s, bỏ ô nằm ngoài
SHIFT, DUR = 0.5, meta["duration"]
keep = []
for o in edl["overlays"]:
    o["start"], o["end"] = max(0.0, round(o["start"] - SHIFT, 3)), round(min(DUR, o["end"] - SHIFT), 3)
    if o["start"] < DUR - 0.05 and o["end"] > o["start"]:
        keep.append(o)
edl["overlays"] = keep
for s in edl["subtitles"]:
    s["skip"] = True

# ── 1) XOÁ chữ Trung: mọi ô `overlay` (đồ hoạ) — phụ đề đáy nội suy nền, 3 dòng hook to nghiêng nhoè mép mềm.
#       Ô `scene` (chữ trên bao bì) giữ nguyên. Không điền text_vi → ô chỉ là vùng xoá, không vẽ nhãn. ──
edl["clean"] = {"mode": "auto"}   # màu khung dải + badge + chữ tự theo bộ nhận diện của shop (shop.json `caps`)

# ── 2) Thuyết minh: một bài liền mạch, dày (~4 âm tiết/giây), đọc nhanh hơn 8% ──
script = [
    (0.0, "Túi gia vị mỗi nơi một ít, lúc cần lại tìm mãi không ra?"),
    (4.0, "PHALEDO gom tất cả vào bộ hũ thủy tinh vuông, nhìn là thấy ngay."),
    (7.7, "Nhiều kích cỡ, món nào cũng có chỗ riêng."),
    (10.0, "Nắp tre có gioăng silicone, đậy kín, giúp hạn chế ẩm."),
    (13.1, "Thân thủy tinh dày dặn, chắc chắn."),
    (15.2, "Miệng rộng, đổ hạt, trà hoa hay ngũ cốc đều gọn."),
    (18.6, "Thìa gỗ gài sẵn bên hũ, cần là lấy."),
    (22.3, "Dáng vuông xếp chồng, tiết kiệm diện tích kệ."),
    (25.3, "Thủy tinh borosilicate trong suốt, chịu nóng lạnh tốt."),
    (28.5, "Xem đủ kích cỡ trong giỏ hàng nhé."),
    (DUR + 0.15, "PHALEDO, gọn đẹp từ gian bếp."),   # câu chốt đọc TRÊN outro của shop
]
edl["narration"] = {"tempo": 1.1, "paragraphs": [{"at": at, "text": text} for at, text in script]}

# ── 3) Chữ Việt ĐỘNG: không bám mốc chữ Trung — bám lời ("pN" = lúc đoạn N bắt đầu đọc), ~2s đổi một khối.
#       Dòng thường + `!` cụm khoá đậm + `^` hộp nhấn (thưa). Hook đặt trên 3 mảng đã nhoè (over = id ô chữ Trung). ──
edl["caps"] = {
    "items": [
        # 3 dòng hook to nghiêng giữa khung → badge nền che kín đúng vùng chữ Trung (không ghi at = theo chữ Trung)
        {"over": "o2", "text": "!Bếp bừa bộn?"},
        {"over": "o3", "text": "!Tìm gì cũng khó"},
        {"over": "o4", "text": "!Túi để khắp nơi"},
        # từ đây: chữ trên KHUNG DẢI đáy — clean.py tự phủ khung trong lúc có phụ đề Trung (từ ~3,8s); không ghi y
        {"at": "p1", "text": "!PHALEDO / Hũ thủy tinh vuông"},
        {"at": "p1+1.9", "text": "Gom gọn, / !^nhìn là thấy"},
        {"at": "p2", "text": "!Nhiều kích cỡ / Mỗi món một chỗ"},
        {"at": "p3", "text": "Nắp tre / !gioăng silicone"},
        {"at": "p3+1.6", "text": "!^Hạn chế ẩm"},
        {"at": "p4", "text": "!Thủy tinh dày dặn"},
        {"at": "p5", "text": "!Miệng rộng"},
        {"at": "p5+1.3", "text": "Hạt, trà hoa, / ngũ cốc"},
        {"at": "p6", "text": "!Thìa gỗ / gài sẵn"},
        {"at": "p6+1.9", "until": 22.1, "text": "Cần là lấy"},
        {"at": "p7", "text": "!^Xếp chồng / gọn diện tích kệ"},
        {"at": "p8", "text": "!Borosilicate / trong suốt"},
        {"at": "p8+1.45", "text": "Chịu nóng lạnh tốt"},
        {"at": "p9", "until": DUR - 0.1, "text": "Xem đủ kích cỡ / !^ở giỏ hàng", "exit": "fade"},
    ],
}

edl["audio"] = {"mode": "narration", "music": "music.mp3", "voice_lufs": -14, "music_lufs": -27, "sfx": True}
edl["logo"] = {"enabled": True, "position": "top-left"}
edl["outro"] = {"enabled": True}   # outro có sẵn của shop (assets/shops/<shop>/outro/) — luôn bật
edl["motion"] = {"mode": "auto"}
edl["poster"] = {"at": 7.3}
(d / "edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=2), encoding="utf-8")
(d / "caption.txt").write_text(
    "Hũ thủy tinh PHALEDO kết hợp nắp tre và thìa gỗ, mang vẻ gọn gàng, trong trẻo đến góc lưu trữ nguyên liệu.\n"
    "#PHALEDO #PhaledoOfficial #HuThuyTinh #GianBepGon\n", encoding="utf-8")
print(f"{d.name}: xoá {sum(1 for o in keep if o.get('kind') != 'scene')} ô chữ Trung đồ hoạ, "
      f"{len(edl['caps']['items'])} khối chữ Việt động, {len(script)} đoạn thuyết minh")
