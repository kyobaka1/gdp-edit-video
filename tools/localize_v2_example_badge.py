"""MẪU direct.py Việt hoá V2 dạng BADGE NHÓM (bản lưu git của jobs/phaledo-0374/direct.py — chép vào jobs/<id>/direct.py
rồi sửa; không chạy trực tiếp trong tools/). Skill gdp-video-localize mục "Chọn CÁCH LẤP chữ Trung".

0374 — hũ đựng hạt cà phê nắp gỗ có van xả khí một chiều, VIỆT HOÁ V2 (PHALEDO).

Dạng chữ Trung của video này (khác 0379): TIÊU ĐỀ LỚN ở vùng trên (0–3,4s) · khối 2 dòng + nhãn nhỏ giữa cảnh (3,4–5,5s) ·
phụ đề 1 dòng ở 15–23% chiều cao suốt phần còn lại. Phủ khung dải đỉnh sẽ cắt ~29% khung (> 17%) → clean.py tự chuyển
sang BADGE NHÓM: G1 tiêu đề · G2 khối 2 dòng · G3 nhãn lẻ · G4 + G5 thanh phụ đề (mỗi thanh giữ liền, chỉ đổi chữ).
Sự thật sản phẩm CHỈ lấy từ chữ trong video gốc: van xả khí một chiều · xả CO2 do hạt sinh ra · nắp gỗ keo · ấn tay để
xả khí · đóng kín, giữ tươi (làm mềm) · hạn chế ẩm / oxy hoá (làm mềm) · miệng rộng đưa tay vào vệ sinh · nhiều kích cỡ.
"""
import json
from pathlib import Path

d = Path(__file__).resolve().parent
meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
edl = json.loads((d / "edl.draft.json").read_text(encoding="utf-8"))
edl["shop"], edl["brand"] = "phaledo_official", "PHALEDO"
DUR = meta["duration"]
by_id = {o["id"]: o for o in edl["overlays"]}
for s in edl["subtitles"]:
    s["skip"] = True

# ── 1) XOÁ / LẤP chữ Trung — máy tự chọn cách theo vị trí + cỡ (xem `clean.json`: groups, notes) ──
edl["clean"] = {"mode": "auto"}
# dòng 2 của khối tiêu đề kết thúc bằng "CO₂" (chữ Latin) — ô phân tích chỉ ôm phần chữ Hán → nới sang phải cho bao cả đuôi
by_id["o3"]["clean"] = {"box": [84, 176, 600, 100]}

# ── 2) Thuyết minh: một bài liền mạch, ~4 âm tiết/giây, đọc nhanh 10%; câu chốt thương hiệu đọc TRÊN outro.
#       Không viết đoạn cụt < ~1,5s ("Cách dùng rất gọn." 0,9s: cổng nghe lại không ổn định — lần khớp 0,5, lần 0,9). ──
script = [
    (0.0, "Hạt cà phê rang xong vẫn tiếp tục nhả khí."),                    # p0
    (3.4, "Hũ PHALEDO có van một chiều cho khí thoát ra."),                 # p1
    (6.9, "Đổ hạt vào hũ, đậy nắp lại là xong."),                           # p2
    (11.1, "Nắp gỗ keo tích hợp van xả khí một chiều."),                    # p3
    (13.6, "Muốn xả nhanh, chỉ cần ấn nhẹ lên van."),                       # p4
    (16.9, "Nắp đóng kín, giúp giữ hương vị lâu hơn."),                     # p5
    (20.4, "Hạt nằm yên trong hũ kín suốt thời gian bảo quản."),            # p6
    (25.5, "Kín để hạn chế ẩm, hạn chế hạt bị oxy hóa."),                   # p7
    (28.3, "Miệng hũ rộng, đưa cả bàn tay vào lau rửa."),                   # p8
    (31.6, "Nhiều dung tích để chọn theo lượng cà phê nhà mình."),          # p9
    (34.2, "Xem đủ kích cỡ trong giỏ hàng nhé."),                           # p10
    (DUR + 0.15, "PHALEDO, giữ hương cho từng hạt cà phê."),                # p11 — trên outro
]
edl["narration"] = {"tempo": 1.1, "paragraphs": [{"at": at, "text": text} for at, text in script]}

# ── 3) Chữ Việt: `over` = vào badge của nhóm chứa ô đó · khối bám lời ("pN") không ghi y tự vào thanh phụ đề đang hiện.
#       Thanh phụ đề: MỖI KHỐI 1 DÒNG ≤ 5 từ (thanh cao theo khối cao nhất — một khối 2 dòng làm cả thanh to lên). ──
edl["caps"] = {
    "items": [
        {"over": "o1", "text": "!Hũ cà phê van một chiều"},                      # G1 tiêu đề lớn (0–3,4s): 1 dòng to
        {"over": "o2", "text": "Chế độ ủ hạt / !xả khí CO2"},                    # G2 khối 2 dòng (3,4–5,5s)
        {"over": "o4", "text": "Mở van"},                                        # G3 nhãn nhỏ giữa cảnh
        {"at": "p2", "text": "Đổ hạt vào hũ"},                                   # G4 thanh phụ đề 5,5–22,4s (khối đầu tự
        {"at": "p2+1.25", "text": "!Đậy nắp là xong"},                           #   kéo về lúc thanh hiện)
        {"at": "p3", "text": "Nắp gỗ keo có van"},
        {"at": "p4", "text": "!Ấn nhẹ để xả khí"},
        {"at": "p5", "text": "!^Đóng kín, giữ hương"},
        {"at": "p6", "text": "Bảo quản kín"},
        {"at": "p7", "text": "!Hạn chế ẩm, oxy hóa"},                           # G5 thanh phụ đề 25,4–36,1s
        {"at": "p8", "text": "Miệng rộng, dễ lau rửa"},
        {"at": "p9", "text": "!Nhiều dung tích"},
        {"at": "p10", "text": "!^Xem cỡ ở giỏ hàng"},
    ],
}

edl["audio"] = {"mode": "narration", "music": "music.mp3", "voice_lufs": -14, "music_lufs": -27, "sfx": True}
edl["logo"] = {"enabled": True, "position": "top-left"}
edl["outro"] = {"enabled": True}
edl["motion"] = {"mode": "auto"}
edl["poster"] = {"mode": "auto"}
(d / "edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=2), encoding="utf-8")
(d / "caption.txt").write_text(
    "Hũ thủy tinh PHALEDO nắp gỗ keo có van xả khí một chiều, giữ hạt cà phê rang trong không gian kín.\n"
    "#PHALEDO #PhaledoOfficial #HuCaPhe #HatCaPhe #GianBepGon\n", encoding="utf-8")
print(f"{d.name}: {len(edl['overlays'])} ô chữ Trung, {len(edl['caps']['items'])} khối chữ Việt, {len(script)} đoạn thuyết minh")
