"""GDP Image Studio — phủ lớp HTML (chữ / logo / nhãn theo nhận diện SHOP) lên ảnh listing đã xoá chữ Trung.

Ảnh là nền cuối cùng; mọi thứ thêm vào là một lớp HTML chụp bằng Chrome. Quy trình + luật: skill `gdp-image-listing`.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent.parent      # image-studio/
ROOT = HERE.parent                                 # gdp-video-studio/
JOBS = HERE / "jobs"
UI = HERE / "ui"
SHOPS = ROOT / "assets" / "shops"
FONTS = ROOT / "assets" / "fonts"

KINDS = {"cover": "ảnh bìa", "product_image": "ảnh sản phẩm", "description_image": "ảnh mô tả",
         "variant_image": "ảnh phân loại"}
