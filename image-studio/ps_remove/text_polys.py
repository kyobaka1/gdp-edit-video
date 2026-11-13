"""Đường lasso ôm sát chữ cho nút Remove của Photoshop web (Sếp 13/11/2026).

Tính mask chữ ngay trên ẢNH GỐC (pixel thật), nới `--dilate` px, lấy đường bao từng cụm -> polygon theo toạ độ
CSS của tab Photoshop (ảnh đang hiện ở zoom 50%). Dán JSON in ra vào `lasso.js` (window.__POLYS) rồi vẽ.

    python text_polys.py <anh> <regions.json> <out_dir> [--dilate 9] [--x0 613 --y0 128.5 --scale 0.3333]

regions.json: [{"name": "tieu-de", "box": [x0, y0, x1, y1], "kind": "dark", "thr": 150}, ...]
  kind "dark"  = chữ tối hơn nền (ngưỡng độ sáng L < thr, thang 0-255)
  kind "light" = chữ sáng hơn nền (L > thr)
  kind "badge" = cả tấm nhãn màu (bão hoà cao) + lấp lỗ — xoá trọn khối nhãn
Hộp `box` khoanh vừa dòng chữ, KHÔNG lấn icon / sản phẩm bên cạnh (mask chỉ tính trong hộp).

Ra: <out_dir>/polys.json (img + css) và <out_dir>/polys_prev.jpg (soát mắt: hồng = vùng sẽ xoá).
Hiệu chỉnh: đo góc trên-trái + góc dưới-phải của ảnh trên ảnh chụp màn hình (zoom phóng to 2 góc), đổi sang CSS
px (x innerWidth / bề rộng ảnh chụp) → --x0 --y0 = góc trên-trái, --scale = bề rộng ảnh (CSS) / bề rộng ảnh gốc (px).
Mặc định đo 13/11/2026: tab 1707×842 CSS, dpr 1.5, zoom 50%, panel Layers mở → (613, 128.5, 1/3).
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("image")
ap.add_argument("regions")
ap.add_argument("out_dir")
ap.add_argument("--dilate", type=int, default=9)
ap.add_argument("--x0", type=float, default=613.0)
ap.add_argument("--y0", type=float, default=128.5)
ap.add_argument("--scale", type=float, default=1 / 3)
a = ap.parse_args()

img = cv2.imread(a.image)
H, W = img.shape[:2]
L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.int16)
SAT = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1]
kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.dilate + 1, 2 * a.dilate + 1))

polys, full = [], np.zeros((H, W), np.uint8)
for r in json.load(open(a.regions, encoding="utf-8")):
    x0, y0, x1, y1 = r["box"]
    roi = (slice(y0, y1), slice(x0, x1))
    m = np.zeros((H, W), np.uint8)
    kind, thr = r.get("kind", "dark"), r.get("thr", 150)
    if kind == "dark":
        m[roi] = (L[roi] < thr) * 255
    elif kind == "light":
        m[roi] = (L[roi] > thr) * 255
    else:  # badge
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
        polys.append([r["name"], [[round(a.x0 + x * a.scale, 2), round(a.y0 + y * a.scale, 2)] for x, y in pts]])

out = Path(a.out_dir)
out.mkdir(parents=True, exist_ok=True)
(out / "polys.json").write_text(json.dumps(polys, separators=(",", ":")), encoding="utf-8")
over = img.copy()
over[full > 0] = (255, 0, 255)
prev = cv2.addWeighted(over, 0.45, img, 0.55, 0)
cv2.imwrite(str(out / "polys_prev.jpg"), cv2.resize(prev, (W // 2, H // 2)))
print(f"{len(polys)} polygons, area {100 * full.mean() / 255:.2f}% -> {out / 'polys.json'}")
