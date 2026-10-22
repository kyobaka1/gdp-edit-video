"""Hỏi ảnh qua Codex CLI local (đăng nhập ChatGPT — Sếp có gói Pro, không tốn tiền API) bằng model rẻ.

Dùng cho việc SOÁT (qa, soát mắt khung hình). Gemini API chỉ là dự phòng khi Codex không chạy / hết usage.
Đo 22/10 (tools/probe_codex_vision.py, 10 khung thật): gpt-5.6-luna đọc đúng 8/8 cụm chữ đồ hoạ, kind đúng 8/8,
0 thừa, ~10s/lô 10 khung — nhưng ô chữ chỉ phủ 63–100% ô Gemini, lệch giữa các lần chạy → KHÔNG dùng ô của
Codex để đặt ô che (analyze vẫn Gemini). Tài khoản ChatGPT không gọi được gpt-6-luna/gpt-6-sol (400).
Codex không nhận audio → nghe lại vẫn Gemini.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

MODEL = os.getenv("CODEX_MODEL", "").strip() or "gpt-5.6-luna"
EFFORT = os.getenv("CODEX_EFFORT", "").strip() or "low"
_dead: str | None = None  # lý do Codex hỏng/hết usage trong tiến trình này → các lần sau đi thẳng Gemini


class CodexUnavailable(RuntimeError):
    pass


def strict(schema: dict) -> dict:
    """Structured outputs của OpenAI: mọi object phải additionalProperties=false + required đủ mọi khoá."""
    s = dict(schema)
    if s.get("type") == "object":
        s["properties"] = {k: strict(v) for k, v in s["properties"].items()}
        s["required"] = list(s["properties"])
        s["additionalProperties"] = False
    if s.get("type") == "array":
        s["items"] = strict(s["items"])
    return s


def _run(images: list[Path], prompt: str, schema: dict | None, model: str, timeout: int) -> str:
    global _dead
    if os.getenv("CODEX_DISABLE"):
        raise CodexUnavailable("CODEX_DISABLE bật")
    if _dead:
        raise CodexUnavailable(_dead)
    exe = shutil.which("codex")
    if not exe:
        _dead = "không tìm thấy lệnh codex (npm i -g @openai/codex rồi codex login)"
        raise CodexUnavailable(_dead)
    with tempfile.TemporaryDirectory(prefix="vs_codex_") as tmp:
        out = Path(tmp) / "out.txt"
        # --ignore-user-config: không bật MCP/plugin của config Sếp (chậm + có cả bridge prod); auth vẫn dùng
        # CODEX_HOME. read-only + thư mục tạm: model chỉ được NHÌN ảnh, không chạy lệnh đụng studio.
        cmd = [exe, "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config", "-s", "read-only",
               "-m", model, "-c", f'model_reasoning_effort="{EFFORT}"', "-o", str(out), "-C", tmp]
        if schema is not None:
            (Path(tmp) / "schema.json").write_text(json.dumps(strict(schema)), encoding="utf-8")
            cmd += ["--output-schema", str(Path(tmp) / "schema.json")]
        for p in images:
            cmd += ["-i", str(Path(p).resolve())]
        try:
            r = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise CodexUnavailable(f"codex quá {timeout}s")
        err = r.stderr.decode("utf-8", "replace")
        if r.returncode or not out.exists():
            tail = " ".join(ln for ln in err.splitlines() if "ERROR" in ln and "skill" not in ln)[-300:]
            low = err.lower()
            if any(k in low for k in ("usage limit", "rate limit", "429", "not supported", "login", "unauthorized")):
                _dead = f"codex hết usage / không dùng được: {tail}"  # không thử lại nữa trong lượt chạy
            raise CodexUnavailable(f"codex exit {r.returncode}: {tail}")
        return out.read_text(encoding="utf-8")


def ask_json(images: list[Path], prompt: str, schema: dict, model: str = MODEL, timeout: int = 300) -> dict:
    text = _run(images, prompt + "\nChỉ trả JSON đúng schema, không chạy lệnh nào.", schema, model, timeout)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise CodexUnavailable(f"codex trả JSON hỏng: {text[-200:]!r}")


def ask_text(images: list[Path], prompt: str, model: str = MODEL, timeout: int = 300) -> str:
    return _run(images, prompt + "\nKhông chạy lệnh nào, chỉ trả lời.", None, model, timeout).strip()
