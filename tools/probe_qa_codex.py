r"""Kiểm qa soát-bằng-Codex trên BẢN SAO job (không đụng job gốc), 2 chiều:
  final  : bản final đã đạt → phải ĐẠT, ít/không gọi Gemini
  source : video gốc chưa che gì → phải CHƯA ĐẠT, bắt được chữ đồ hoạ (đo độ nhạy)
Chạy: .venv\Scripts\python.exe tools\probe_qa_codex.py <job_id> final|source"""

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config, qa  # noqa: E402

src, mode = config.JOBS / sys.argv[1], sys.argv[2]
dst = config.JOBS / "_probe" / f"qa_{mode}_{sys.argv[1]}"
shutil.rmtree(dst, ignore_errors=True)
dst.mkdir(parents=True)
for f in ("meta.json", "analysis.json"):
    shutil.copy2(src / f, dst / f)
shutil.copy2(src / ("final.mp4" if mode == "final" else "source.mp4"), dst / "final.mp4")
t0 = time.time()
rep = qa.run(dst, final=True)
rows = [json.loads(ln) for ln in (dst / "usage.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
gem = sum(r.get("prompt") or 0 for r in rows if r.get("engine") != "codex")
an = json.loads((src / "analysis.json").read_text(encoding="utf-8"))
ov_events = [e for e in an["events"] if e.get("kind", "overlay") != "scene"]
print(f"{mode}: {'ĐẠT' if rep['pass'] else 'CHƯA ĐẠT'} · {rep['frames_checked']} khung · sót {len(rep['residual_chinese'])} · "
      f"{time.time() - t0:.0f}s · screen {rep['screen']} · Gemini xác nhận {len(rep['gemini_confirmed_frames'])} khung "
      f"· token Gemini {gem:,}")
if mode == "source":
    found = {r["text"] for r in rep["residual_chinese"]}
    from studio.analyze import _same_text
    caught = [e for e in ov_events if any(_same_text(e["zh"], f) for f in found)]
    print(f"  bắt được {len(caught)}/{len(ov_events)} sự kiện chữ đồ hoạ của video gốc")
    for e in ov_events:
        if e not in caught:
            print("   SÓT:", e["zh"], e["t_first"], e["t_last"], e["n_frames"], "khung")
