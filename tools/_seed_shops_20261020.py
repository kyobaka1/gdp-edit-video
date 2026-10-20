"""Một lần (20/10/2026): tạo 8 shop từ ảnh chụp prod marketing_shop (db_read qua bridge). Chạy lại an toàn (không ghi đè)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from init_shop import init  # noqa: E402

KIT = "shop/brand-kit"
PROD = [
    # id, mã, tiêu đề, sàn, brand, palette (None = mặc định trung tính chưa cấu hình), tone, có file brand-kit?, logo Shopee
    (1, "giadungplus_official", "Gia Dụng Plus +", "shopee", "GIADUNGPLUS",
     {"dark": "#7a1010", "accent": "#f1c40f", "primary": "#c01818", "text_on_dark": "#ffffff", "text_on_light": "#c01818"},
     "", ("7f9f1e9264ef463b8c9bd3f952dc0abe.png", "ac96a7139c0f449db1ea331fc72c29a6.png", "ddcbcb60482c435d99858fb5d6bbad3f.jpg"),
     "https://cf.shopee.vn/file/vn-11134216-7r98o-lscja178b4pl14"),
    (2, "phaledo", "Phaledo Glassware", "shopee", "PHALEDO", None, "", None,
     "https://cf.shopee.vn/file/vn-11134216-820l4-mgnua2w5rrbi5c"),
    (3, "lteng_vn", "LTENG VN", "shopee", "LTENG",
     {"dark": "#001026", "accent": "#0b649c", "primary": "#062955", "text_on_dark": "#ffffff", "text_on_light": "#002b5c"},
     "thân thiện, bán hàng, dứt khoát — nhấn lợi ích (chịu lực, lắp nhanh, bền)",
     ("6a7a5bfc41f34581a90351d007ffbc0b.png", "52b07ec349664f4b83573c0148d5a1e9.png", "b97889a6b9e6488da77ecc22c3836863.jpg"),
     "https://cf.shopee.vn/file/vn-11134004-7ras8-mdk5uvpn75ipe8"),
    (4, "lteng_hcm", "LTENG HCM", "shopee", "LTENG",
     {"dark": "#5a1410", "accent": "#c0392b", "primary": "#a83030", "text_on_dark": "#ffffff", "text_on_light": "#a83030"},
     "thân thiện, bán hàng, dứt khoát — nhấn lợi ích (chịu lực, lắp nhanh, bền)",
     ("58eae4939a0345808a0eeeb5aa645f5a.png", "3b86fd560e64418fa454fb604e18bde1.png", "fb11af67d81c48da8d47959e85a4e699.jpg"),
     "https://cf.shopee.vn/file/vn-11134216-820l4-mh5xexzwtdzh50"),
    (5, "phaledo_official", "Phaledo Official", "shopee", "PHALEDO",
     {"dark": "#161616", "accent": "#b89a6a", "primary": "#c0b7a6", "text_on_dark": "#ececec", "text_on_light": "#161616"},
     "cao cấp, tinh tế, tối giản — nhấn chất liệu, độ bền, sang trọng",
     ("fc8a85ddb4074f92aae847616c19fc6f.png", "5c843d4ebbcd4f09a00da04ecb0325d7.png", "9d507936d4bd403bbe44c4ddb8b05fe8.jpg"),
     "https://cf.shopee.vn/file/vn-11134216-820l4-mentszzpt2px7e"),
    (6, "phaledo_tiktok", "TikTok PHALEDO", "tiktok", "PHALEDO", None, "", None, None),
    (7, "lteng_tiktok", "TikTok LTENG", "tiktok", "LTENG", None, "", None, None),
    (8, "phaledo_vn_tiktok", "Phaledo Việt Nam", "tiktok", "PHALEDO", None, "", None, None),
]
# Shop chưa có nhận diện riêng mượn mẫu của shop cùng brand đã cấu hình (Sếp đổi được trong shop.json)
BORROW = {"PHALEDO": "phaledo_official", "LTENG": None, "GIADUNGPLUS": None}

for sid, code, title, platform, brand, palette, tone, files, shopee_logo in PROD:
    prod = {"marketing_shop_id": sid}
    if shopee_logo:
        prod["shopee_logo_url"] = shopee_logo
    if files:
        prod.update({"brand_logo": f"{KIT}/{code}/{files[0]}", "watermark_image": f"{KIT}/{code}/{files[1]}",
                     "font_reference": f"{KIT}/{code}/{files[2]}"})
    data = {"title": title, "platform": platform, "configured": palette is not None, "tone": tone, "prod": prod}
    if palette:
        data["palette"] = palette
    tf = None if code == "phaledo_official" else BORROW.get(brand)
    if palette is None:
        data["notes"] = ("Prod chưa cấu hình nhận diện riêng (bảng màu mặc định trung tính). "
                         + (f"Tạm mượn mẫu của {tf}." if tf else "Chưa có mẫu chữ — cần thiết kế."))
    elif not tf and code != "phaledo_official":
        data["notes"] = "Đã có bảng màu trên prod nhưng CHƯA có mẫu chữ HTML — cần thiết kế (Claude Design → templates/)."
    print(init(code, brand, tf, data))
