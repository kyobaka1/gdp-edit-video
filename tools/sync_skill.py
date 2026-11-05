"""Đồng bộ skill của studio (nguồn: .claude/skills/ trong studio — đi theo thư mục khi chép sang máy khác).

  python tools/sync_skill.py install   # studio → %USERPROFILE%\\.claude\\skills + %USERPROFILE%\\.codex\\skills
                                       #   (Claude Code + Codex dùng skill từ MỌI thư mục, vd repo giadungplus)
  python tools/sync_skill.py collect   # %USERPROFILE%\\.claude\\skills → studio (sau khi sửa skill ở bản cài máy)
  python tools/sync_skill.py status    # so các bản: giống / khác / thiếu
  python tools/sync_skill.py install --force   # ghi đè cả khi bản cài máy MỚI hơn studio

Chống bản cũ ghi đè bản mới: install/collect DỪNG nếu bên đích có file khác nội dung mà mới hơn bên nguồn (đã sửa ở đó
mà chưa collect) — xem `status`, gộp tay rồi chạy lại hoặc thêm --force.
Bản sao thứ 3 cho prod/máy chủ: repo giadungplus `skills/<tên>/` (Claude điều phối đẩy lên khi đổi skill)."""

import filecmp
import shutil
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent / ".claude" / "skills"
TARGETS = {"claude": Path.home() / ".claude" / "skills", "codex": Path.home() / ".codex" / "skills"}
SKILLS = ["gdp-video-localize", "gdp-video-motion", "gdp-video-edit"]  # skill liên quan studio


def files(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()} if root.exists() else set()


def newer_conflicts(src: Path, dst: Path) -> list[str]:
    """File có ở cả 2 bên, nội dung khác, bên đích sửa sau bên nguồn → copy sẽ làm mất sửa đổi mới hơn."""
    out = []
    for f in files(src) & files(dst):
        a, b = src / f, dst / f
        if not filecmp.cmp(a, b, shallow=False) and b.stat().st_mtime > a.stat().st_mtime + 1:
            out.append(f)
    return out


def main(mode: str, force: bool) -> None:
    for name in SKILLS:
        a = STUDIO / name
        if mode == "status":
            fa = files(a)
            for tname, root in TARGETS.items():
                b = root / name
                fb = files(b)
                diff = [f for f in fa & fb if not filecmp.cmp(a / f, b / f, shallow=False)]
                print(f"{name} [{tname}]: studio {len(fa)} file · máy {len(fb)} file · khác {diff or 'không'} · "
                      f"chỉ studio {sorted(fa - fb) or '-'} · chỉ máy {sorted(fb - fa) or '-'}"
                      + (f" · ⚠ máy MỚI hơn: {newer_conflicts(a, b)}" if newer_conflicts(a, b) else ""))
            continue
        pairs = [(a, root / name) for root in TARGETS.values()] if mode == "install" else [(TARGETS["claude"] / name, a)]
        for src, dst in pairs:
            if not src.exists():
                raise SystemExit(f"Không có {src}")
            clash = newer_conflicts(src, dst)
            if clash and not force:
                raise SystemExit(f"DỪNG: {dst} có file sửa SAU bản nguồn ({', '.join(clash)}) — collect/gộp tay trước, "
                                 f"hoặc --force để ghi đè")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"{name}: {src} → {dst}")


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(args[0] if args else "status", "--force" in sys.argv)
