"""Đồng bộ skill của studio (nguồn: .claude/skills/ trong studio — đi theo thư mục khi chép sang máy khác).

  python tools/sync_skill.py install   # studio → %USERPROFILE%\\.claude\\skills (dùng skill từ MỌI thư mục, vd repo giadungplus)
  python tools/sync_skill.py collect   # %USERPROFILE%\\.claude\\skills → studio (sau khi sửa skill ở bản cài máy)
  python tools/sync_skill.py status    # so 2 bản: giống / khác / thiếu

Bản sao thứ 3 cho prod/máy chủ: repo giadungplus `skills/<tên>/` (Claude điều phối đẩy lên khi đổi skill)."""

import filecmp
import shutil
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent / ".claude" / "skills"
USER = Path.home() / ".claude" / "skills"
SKILLS = ["gdp-video-localize"]  # skill liên quan studio (soát 20/10: chỉ skill này nhắc tới studio)


def files(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()} if root.exists() else set()


def main(mode: str) -> None:
    for name in SKILLS:
        a, b = STUDIO / name, USER / name
        if mode == "status":
            fa, fb = files(a), files(b)
            diff = [f for f in fa & fb if not filecmp.cmp(a / f, b / f, shallow=False)]
            print(f"{name}: studio {len(fa)} file · máy {len(fb)} file · khác {diff or 'không'} · "
                  f"chỉ studio {sorted(fa - fb) or '-'} · chỉ máy {sorted(fb - fa) or '-'}")
            continue
        src, dst = (a, b) if mode == "install" else (b, a)
        if not src.exists():
            raise SystemExit(f"Không có {src}")
        shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"{name}: {src} → {dst}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "status")
