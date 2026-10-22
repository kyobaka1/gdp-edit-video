r"""So codex exec (ChatGPT, model rẻ) với Gemini trên đúng bước detect: 10 khung thật đã có kết quả Gemini trong
analysis.json → hỏi codex cùng prompt/schema → so ô (IoU) + chữ + kind. Chạy:
.venv\Scripts\python.exe tools\probe_codex_vision.py <job_id> [model] [effort]"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config, media  # noqa: E402
from studio.analyze import BOX_PROMPT, BOX_SCHEMA, FRAME_WIDTH, _iou, _same_text, has_cjk  # noqa: E402


def strict(s):
    """Structured outputs của OpenAI: mọi object phải additionalProperties=false + required đủ mọi khoá."""
    s = dict(s)
    if s.get("type") == "object":
        s["properties"] = {k: strict(v) for k, v in s["properties"].items()}
        s["required"] = list(s["properties"])
        s["additionalProperties"] = False
    if s.get("type") == "array":
        s["items"] = strict(s["items"])
    return s


job = config.JOBS / sys.argv[1]
model = sys.argv[2] if len(sys.argv) > 2 else "gpt-6-luna"
effort = sys.argv[3] if len(sys.argv) > 3 else "low"
an = json.loads((job / "analysis.json").read_text(encoding="utf-8"))
dets = an["detections"]
pick = [d for d in dets if d["items"]][::6][:8] + [d for d in dets if not d["items"]][:2]
pick.sort(key=lambda d: d["t"])
tmp = Path(tempfile.mkdtemp(prefix="cx_"))
paths = media.extract_frames(job / "source.mp4", [d["t"] for d in pick], tmp, width=FRAME_WIDTH)
(tmp / "schema.json").write_text(json.dumps(strict(BOX_SCHEMA)), encoding="utf-8")
prompt = "".join(f"Khung {i} là ảnh đính kèm thứ {i + 1}. " for i in range(len(paths)))
prompt += BOX_PROMPT.format(n=len(paths), last=len(paths) - 1) + " Chỉ trả JSON, không chạy lệnh nào."
cmd = [shutil.which("codex"), "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config", "-s", "read-only",
       "-m", model, "-c", f'model_reasoning_effort="{effort}"', "--output-schema", str(tmp / "schema.json"),
       "-o", str(tmp / "out.json"), "-C", str(tmp)]
for p in paths:
    cmd += ["-i", str(p)]
t0 = time.time()
r = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, timeout=600)
secs = time.time() - t0
print(f"codex {model}/{effort}: exit {r.returncode}, {secs:.0f}s")
if r.returncode:
    print(r.stderr.decode("utf-8", "replace")[-1500:])
    sys.exit(1)
tail = r.stderr.decode("utf-8", "replace").splitlines()
print("  ", [ln for ln in tail if "tokens" in ln.lower()][-2:])
got = json.loads((tmp / "out.json").read_text(encoding="utf-8"))
hit = miss = extra = kind_ok = 0
ious = []
for fr in got["frames"]:
    i = fr["frame_index"]
    if not 0 <= i < len(pick):
        continue
    gem = pick[i]["items"]
    cx = [it for it in fr["items"] if has_cjk(it["text"])]
    used = set()
    for g in gem:
        best, bj = 0.0, None
        for j, c in enumerate(cx):
            if j in used:
                continue
            v = _iou(g["box_2d"], c["box_2d"])
            if v > best:
                best, bj = v, j
        if bj is not None and (best > 0.2 or _same_text(g["text"], cx[bj]["text"])):
            used.add(bj)
            hit += 1
            ious.append(best)
            kind_ok += g["kind"] == cx[bj]["kind"]
            gb, cb = g["box_2d"], cx[bj]["box_2d"]
            cov = _iou(gb, [max(gb[0], cb[0]), max(gb[1], cb[1]), min(gb[2], cb[2]), min(gb[3], cb[3])]) if min(gb[2], cb[2]) > max(gb[0], cb[0]) and min(gb[3], cb[3]) > max(gb[1], cb[1]) else 0
            print(f"  t={pick[i]['t']:5.2f} IoU {best:.2f} phủ {cov:.2f} | G {gb} | C {cb}")
        else:
            miss += 1
            print(f"  t={pick[i]['t']:5.2f} SÓT  {g['kind']:7} G {g['text'][:20]}  box {g['box_2d']}")
    for j, c in enumerate(cx):
        if j not in used:
            extra += 1
            print(f"  t={pick[i]['t']:5.2f} THỪA {c['kind']:7} C {c['text'][:20]}  box {c['box_2d']}")
ious.sort()
print(f"KẾT QUẢ: khớp {hit} · sót {miss} · thừa {extra} · kind đúng {kind_ok}/{hit} · IoU trung vị "
      f"{ious[len(ious) // 2] if ious else 0:.2f} · thấp nhất {ious[0] if ious else 0:.2f}")
shutil.rmtree(tmp, ignore_errors=True)
