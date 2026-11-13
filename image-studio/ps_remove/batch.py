"""Chuẩn bị XOÁ CHỮ HÀNG LOẠT trong Photoshop web (Sếp 13/11/2026).

Một lệnh cho cả lô: chia ảnh theo KÍCH THƯỚC (mỗi nhóm = 1 file Photoshop: mở ảnh đầu, các ảnh sau DÁN thành layer),
tính đường lasso từng ảnh, đổi tên file ngắn để nạp vào trang, ra 1 ảnh soát duy nhất cho cả lô.

    python batch.py <regions.json> <thư mục ra> [--dilate 6]

regions.json = {"<đường dẫn ảnh>": [vùng…], …}   (vùng: xem text_polys.py; ảnh SẠCH sẵn thì để [] — tự bỏ qua)
Ra <thư mục ra>/:
  manifest.json   {"groups": {"800x800": [{"n": "i01", "src": …, "img": "i01.jpg", "polys": "i01.json"}, …]}, …}
  i01.jpg, i01.json, …   ảnh (tên ngắn) + polygon toạ độ ảnh — nạp vào trang bằng file_upload
  _soat.jpg       mọi ảnh thu nhỏ, hồng = vùng sẽ xoá → ĐỌC trước khi mở Photoshop
"""
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from text_polys import polys_for, preview  # noqa: E402

if len(sys.argv) < 3:
    sys.exit(__doc__)
regions = json.load(open(sys.argv[1], encoding="utf-8"))
out = Path(sys.argv[2])
dil = int(sys.argv[sys.argv.index("--dilate") + 1]) if "--dilate" in sys.argv else 6
out.mkdir(parents=True, exist_ok=True)

groups, thumbs, skipped = {}, [], []
for i, (src, regs) in enumerate(regions.items(), 1):
    if not regs:
        skipped.append(src)
        continue
    img = cv2.imread(src)
    if img is None:
        sys.exit(f"không đọc được ảnh: {src}")
    H, W = img.shape[:2]
    n = f"i{i:02d}"
    polys, full = polys_for(img, regs, dil)
    ext = Path(src).suffix.lower().replace(".jpeg", ".jpg")
    shutil.copy2(src, out / f"{n}{ext}")
    (out / f"{n}.json").write_text(json.dumps(polys, separators=(",", ":")), encoding="utf-8")
    groups.setdefault(f"{W}x{H}", []).append({"n": n, "src": src, "img": f"{n}{ext}", "polys": f"{n}.json",
                                               "area_pct": round(100 * full.mean() / 255, 2)})
    t = cv2.resize(preview(img, full), (300, round(300 * H / W)))
    cv2.putText(t, f"{n} {W}x{H}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
    cv2.putText(t, f"{n} {W}x{H}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    thumbs.append(t)

json.dump({"groups": groups, "skipped_clean": skipped}, open(out / "manifest.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
if thumbs:
    cols = min(4, len(thumbs))
    hmax = max(t.shape[0] for t in thumbs)
    rows = [thumbs[k:k + cols] for k in range(0, len(thumbs), cols)]
    sheet = np.full((hmax * len(rows), 300 * cols, 3), 255, np.uint8)
    for r, row in enumerate(rows):
        for c, t in enumerate(row):
            sheet[r * hmax:r * hmax + t.shape[0], c * 300:(c + 1) * 300] = t
    cv2.imwrite(str(out / "_soat.jpg"), sheet)
for k, v in groups.items():
    print(f"nhóm {k}: {len(v)} ảnh → 1 file Photoshop ({', '.join(x['n'] for x in v)})")
if skipped:
    print(f"bỏ qua {len(skipped)} ảnh đã sạch")
print(f"soát: {out / '_soat.jpg'}")
