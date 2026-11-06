"""Tạo ảnh cho asset còn thiếu (cảnh minh hoạ bối cảnh, nền, miếng cắt dán, icon, sticker) qua Codex CLI local —
đăng nhập ChatGPT (gói Pro của Sếp), công cụ `image_generation` của Codex, KHÔNG tốn tiền API.

Sếp chốt 05/11: thiếu source/asset → ưu tiên Codex local; Codex hỏng/hết usage → Claude lái chatgpt.com trên Chrome
(đã đăng nhập sẵn) rồi lưu ảnh về (skill gdp-video-edit, mục "Thiếu source / asset").
Đo 05/11 (gpt-5.6-luna, effort low): ảnh dọc 1024x1536 chân thực ~60s · nền trong suốt RGBA sạch (thân ~253/255) ·
ảnh tham chiếu phong cách qua `-i` được. Codex lưu ảnh ở $CODEX_HOME/generated_images/<thread_id>/ — mỗi lần gọi một
thư mục riêng nên chạy song song không lẫn; một lần gọi có thể ra 2 bản (giữ bản cuối làm chính, bản kia làm phương án).

⛔ Ảnh AI chỉ để minh hoạ BỐI CẢNH / Ý (góc bếp bừa, phố vắng, giấy, mũi tên…) — KHÔNG vẽ sản phẩm đang bán thay cho
ảnh thật, KHÔNG làm bằng chứng (trước–sau, doanh thu, đánh giá). Mỗi ảnh kèm file .json ghi nguồn AI để QA nhắc.
"""

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from studio import codex

SIZES = {"doc": "dọc 1024x1536 (khung 2:3, dùng cho video 9:16)", "vuong": "vuông 1024x1024",
         "ngang": "ngang 1536x1024"}


class ImageGenError(RuntimeError):
    pass


def codex_home() -> Path:
    return Path(os.getenv("CODEX_HOME") or Path.home() / ".codex")


def _prompt(text: str, size: str, alpha: bool, refs: list[Path]) -> str:
    parts = ["Dùng công cụ tạo ảnh (image generation) tạo đúng MỘT ảnh, khổ " + SIZES[size] + "."]
    if alpha:
        parts.append("NỀN TRONG SUỐT (PNG có kênh alpha), chỉ có vật thể, không nền giấy/bàn phía sau, không bóng đổ "
                     "ra nền.")
    if refs:
        parts.append("Ảnh đính kèm chỉ là THAM CHIẾU (phong cách, màu, chất liệu) — không chép chữ, logo, khuôn mặt "
                     "trong đó.")
    parts.append("Nội dung: " + text.strip())
    parts.append("Không có chữ, số, logo, watermark trong ảnh trừ khi nội dung yêu cầu rõ. Không chạy lệnh nào khác, "
                 "không sửa file. Trả lời 1 dòng: đã tạo ảnh.")
    return "\n".join(parts)


def generate(text: str, out: Path, size: str = "doc", alpha: bool = False, refs: list[Path] | None = None,
             model: str = codex.MODEL, timeout: int = 480) -> dict:
    """Tạo ảnh → `out` (.png) + `out`.json (nguồn AI). Trả meta. Lỗi Codex → codex.CodexUnavailable (dùng Chrome)."""
    if size not in SIZES:
        raise ImageGenError(f"size '{size}' không có (dùng {', '.join(SIZES)})")
    refs = [Path(r).resolve() for r in (refs or [])]
    for r in refs:
        if not r.exists():
            raise ImageGenError(f"không thấy ảnh tham chiếu {r}")
    if os.getenv("CODEX_DISABLE"):
        raise codex.CodexUnavailable("CODEX_DISABLE bật")
    exe = shutil.which("codex")
    if not exe:
        raise codex.CodexUnavailable("không tìm thấy lệnh codex (npm i -g @openai/codex rồi codex login)")
    prompt = _prompt(text, size, alpha, refs)
    with tempfile.TemporaryDirectory(prefix="vs_imagegen_") as tmp:
        # --ignore-user-config: không bật MCP/plugin của config Sếp; read-only: model chỉ được tạo ảnh, không đụng file.
        cmd = [exe, "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config",
               "--enable", "image_generation", "-s", "read-only", "-m", model,
               "-c", 'model_reasoning_effort="low"', "-C", tmp]
        for r in refs:
            cmd += ["-i", str(r)]
        cmd.append("-")
        try:
            r = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise codex.CodexUnavailable(f"codex tạo ảnh quá {timeout}s")
    events = [json.loads(ln) for ln in r.stdout.decode("utf-8", "replace").splitlines() if ln.startswith("{")]
    thread = next((e.get("thread_id") for e in events if e.get("type") == "thread.started"), None)
    err = r.stderr.decode("utf-8", "replace")
    folder = codex_home() / "generated_images" / thread if thread else None
    files = sorted(folder.glob("*.png"), key=lambda p: p.stat().st_mtime) if folder and folder.exists() else []
    if r.returncode or not files:
        tail = " ".join(ln for ln in err.splitlines() if "ERROR" in ln and "skill" not in ln)[-300:]
        said = " ".join(e["item"].get("text", "") for e in events if e.get("type") == "item.completed")[-200:]
        if any(k in err.lower() for k in ("usage limit", "rate limit", "429", "login", "unauthorized")):
            raise codex.CodexUnavailable(f"codex hết usage / chưa đăng nhập: {tail}")
        raise codex.CodexUnavailable(f"codex không ra ảnh (exit {r.returncode}): {tail or said}")
    out = Path(out).with_suffix(".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    variants = []
    for i, f in enumerate(reversed(files)):  # bản cuối = chính
        dst = out if i == 0 else out.with_name(f"{out.stem}_v{i + 1}.png")
        info = _save(f, dst, alpha)
        variants.append({"file": dst.name, **info})
    meta = {"engine": "codex", "model": model, "kind": "ai", "prompt": text.strip(), "size": size, "alpha": alpha,
            "refs": [str(p) for p in refs], "thread": thread, "created": f"{datetime.now():%Y-%m-%d %H:%M}",
            "variants": variants,
            "note": "ẢNH AI — chỉ minh hoạ bối cảnh/ý; không thay ảnh sản phẩm thật, không làm bằng chứng"}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def _save(src: Path, dst: Path, alpha: bool) -> dict:
    im = Image.open(src)
    if alpha:
        if im.mode != "RGBA":
            raise ImageGenError(f"{src.name}: cần nền trong suốt nhưng ảnh ra {im.mode} (thử lại / Chrome)")
        a = np.array(im)
        clear = float((a[:, :, 3] == 0).mean())
        if clear < 0.05:
            raise ImageGenError(f"{src.name}: gần như không có vùng trong suốt ({clear:.0%}) — thử lại")
        a[:, :, 3] = np.where(a[:, :, 3] >= 250, 255, a[:, :, 3])  # thân miếng giấy ~253 → đặc hẳn
        Image.fromarray(a, "RGBA").save(dst)
        return {"w": im.width, "h": im.height, "mode": "RGBA", "clear": round(clear, 3)}
    im.convert("RGB").save(dst)
    return {"w": im.width, "h": im.height, "mode": "RGB"}
