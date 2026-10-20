"""Kiểm font có đủ ký tự tiếng Việt (134 chữ có dấu, hoa + thường) + dấu câu hay dùng. Chạy: python tools/check_font_vi.py [thư mục font]"""

import sys
from pathlib import Path

from fontTools.ttLib import TTFont

VI = ("aàảãáạăằẳẵắặâầẩẫấậbcdđeèẻẽéẹêềểễếệfghiìỉĩíịjklmnoòỏõóọôồổỗốộơờởỡớợpqrstuùủũúụưừửữứựvwxyỳỷỹýỵz")
CHARS = set(VI) | set(VI.upper()) | set("0123456789.,:;!?%-–—·•()/+&'\"")
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "assets" / "fonts"
for f in sorted(p for p in root.rglob("*") if p.suffix.lower() in (".ttf", ".otf") and not p.name.startswith("._")):
    try:
        cmap = TTFont(str(f), fontNumber=0).getBestCmap()
    except Exception as exc:
        print(f"{f.relative_to(root)}: LỖI đọc ({exc})")
        continue
    missing = sorted(c for c in CHARS if ord(c) not in cmap)
    vi_missing = [c for c in missing if c.lower() in VI]
    status = "ĐỦ tiếng Việt" if not vi_missing else f"THIẾU {len(vi_missing)} chữ Việt"
    extra = f" · thiếu dấu câu: {''.join(c for c in missing if c not in vi_missing)}" if len(missing) > len(vi_missing) else ""
    print(f"{str(f.relative_to(root)):48} {status}{extra}" + (f" (vd {''.join(vi_missing[:12])})" if vi_missing else ""))
