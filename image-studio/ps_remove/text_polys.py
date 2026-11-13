"""Đường lasso ôm sát chữ cho nút Remove của Photoshop web (Sếp 13/11/2026).

Tính mask chữ ngay trên ẢNH GỐC (pixel thật), nới `dilate` px, lấy đường bao từng cụm -> polygon theo TOẠ ĐỘ ẢNH (px).
`lasso.js` đổi sang toạ độ màn hình bằng hiệu chỉnh `__cal(x0, y0, scale)` đo trong tab — nên tính trước được, không
phụ thuộc zoom. Nhiều ảnh một lúc: dùng `batch.py` (gọi hàm `polys_for` ở đây).

    python text_polys.py <anh> <regions.json> <out_dir> [--dilate 9]

regions.json: [{"name": "tieu-de", "box": [x0, y0, x1, y1], "kind": "dark", "thr": 150}, ...]
  kind "dark"  = chữ tối hơn nền (ngưỡng độ sáng L < thr, thang 0-255)
  kind "light" = chữ sáng hơn nền (L > thr)
  kind "badge" = cả tấm nhãn màu (bão hoà cao) + lấp lỗ — xoá trọn khối nhãn
  kind "red"   = cả tấm nhãn ĐỎ (chữ trắng trong nhãn được lấp lỗ) — khi nền quanh nhãn cũng bão hoà (gỗ…)
  badge / red tự nới hộp thêm `pad` (mặc định 30 px) để không hụt mép nhãn.
Hộp `box` khoanh vừa dòng chữ, KHÔNG lấn icon / sản phẩm bên cạnh (mask chỉ tính trong hộp).
dilate: ~6 px cho ảnh 800 px, ~9 px cho ảnh 1440 px (bù sai lệch vẽ + viền mờ của chữ).

Ra: <out_dir>/polys.json ([[tên, [[x, y], …]], …] toạ độ ảnh) + <out_dir>/polys_prev.jpg (hồng = vùng sẽ xoá).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np


def polys_for(img, regions, dilate=9):
    """img: ảnh BGR. Trả (polys toạ độ ảnh, mask tổng)."""
    H, W = img.shape[:2]
    L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.int16)
    HSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    SAT = HSV[:, :, 1]
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dilate + 1, 2 * dilate + 1))
    polys, full = [], np.zeros((H, W), np.uint8)
    for r in regions:
        x0, y0, x1, y1 = r["box"]
        kind, thr = r.get("kind", "dark"), r.get("thr", 150)
        if kind in ("badge", "red"):   # nhãn: nới hộp để không hụt mép (13/11 hụt 16px mép trái nhãn đỏ → sót vệt)
            pad = r.get("pad", 30)
            x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
        roi = (slice(y0, y1), slice(x0, x1))
        m = np.zeros((H, W), np.uint8)
        if kind == "dark":
            m[roi] = (L[roi] < thr) * 255
        elif kind == "light":
            m[roi] = (L[roi] > thr) * 255
        else:
            if kind == "red":
                hue, val = HSV[:, :, 0], HSV[:, :, 2]
                m[roi] = (((hue[roi] < 10) | (hue[roi] > 170)) & (SAT[roi] > 120) & (val[roi] > 70)) * 255
            else:
                m[roi] = (((SAT[roi] > 90) & (L[roi] < 200)) | (L[roi] < 120)) * 255
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            m[:] = 0
            cv2.drawContours(m, [c for c in cnts if cv2.contourArea(c) > 30], -1, 255, -1)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        m = cv2.dilate(m, kern)
        full |= m
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cnts:
            if cv2.contourArea(c) < 60:
                continue
            pts = cv2.approxPolyDP(c, 1.2, True).reshape(-1, 2)
            polys.append([r["name"], pts.tolist()])
    return polys, full


def preview(img, full):
    over = img.copy()
    over[full > 0] = (255, 0, 255)
    return cv2.addWeighted(over, 0.45, img, 0.55, 0)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    src, regions, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    dil = int(sys.argv[sys.argv.index("--dilate") + 1]) if "--dilate" in sys.argv else 9
    img = cv2.imread(src)
    polys, full = polys_for(img, json.load(open(regions, encoding="utf-8")), dil)
    out.mkdir(parents=True, exist_ok=True)
    (out / "polys.json").write_text(json.dumps(polys, separators=(",", ":")), encoding="utf-8")
    H, W = img.shape[:2]
    cv2.imwrite(str(out / "polys_prev.jpg"), cv2.resize(preview(img, full), (W // 2, H // 2)))
    print(f"{len(polys)} polygons, area {100 * full.mean() / 255:.2f}% -> {out / 'polys.json'}")
