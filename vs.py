"""GDP Video Studio CLI. Chạy bằng .venv\\Scripts\\python.exe vs.py <lệnh> …

  new <video> [--id ID]        tạo job từ video nguồn (copy vào jobs/<id>/)
  analyze <id> [--interval S] [--regroup]  Gemini tìm chữ Trung + chép lời → analysis.json, edl.draft.json
                               (--regroup: gom lại từ kết quả đã lưu, không tốn token)
  render <id> [--final] [--allow-empty]   dựng preview.mp4 (960p) hoặc final.mp4 từ edl.json
  qa <id> [--final]            kiểm còn sót chữ Hán → qa.json + contact.jpg
  patch <id>                   đưa chỗ sót của qa.json vào edl.json (nới giờ ô cũ / thêm ô blur cần xem)
  music <id> [--prompt P]      tạo nhạc nền không lời bằng Lyria → jobs/<id>/music.mp3
  voice <id>                   giọng Việt Gemini TTS cho edl.voiceover (kiểm ngược từng câu) → voice.json
  cost <id>                    tổng token Gemini của job
"""

import argparse
import json
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from studio import analyze, config, media, qa, render, voice


def job_dir(job_id: str) -> Path:
    d = config.JOBS / job_id
    if not (d / "meta.json").exists():
        sys.exit(f"Không thấy job {job_id} ({d})")
    return d


def cmd_new(a) -> None:
    src = Path(a.video).resolve()
    if not src.exists():
        sys.exit(f"Không thấy file {src}")
    jid = a.id or f"{datetime.now():%Y%m%d-%H%M}-{re.sub(r'[^A-Za-z0-9_-]+', '-', src.stem)[:40]}"
    d = config.JOBS / jid
    d.mkdir(parents=True, exist_ok=False)
    dst = d / f"source{src.suffix.lower()}"
    shutil.copy2(src, dst)
    meta = {"id": jid, "source": dst.name, "origin": str(src), **media.probe(dst)}
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


def cmd_analyze(a) -> None:
    d = job_dir(a.id)
    t0 = time.time()
    draft = analyze.run(d, interval=a.interval, regroup=a.regroup)
    print(f"Xong {time.time() - t0:.1f}s · {len(draft['overlays'])} ô chữ · {len(draft['subtitles'])} câu thoại")
    for o in draft["overlays"]:
        flag = " ⚠ cần xem" if o["needs_review"] else (" (chạy)" if o["moving"] else "")
        tag = "giữ (trong cảnh)" if o["mode"] == "keep" else "đè"
        print(f"  {o['id']}: {o['start']:6.2f}–{o['end']:6.2f}s  [{tag}] ô {o['box']}  {o['zh']}{flag}")
    for s in draft["subtitles"]:
        print(f"  thoại {s['start']:6.2f}–{s['end']:6.2f}s  {s['zh']}")
    print(f"→ {d / 'edl.draft.json'}")


def cmd_render(a) -> None:
    d = job_dir(a.id)
    t0 = time.time()
    try:
        out = render.run(d, final=a.final, allow_empty=a.allow_empty)
    except render.EdlError as exc:
        sys.exit(str(exc))
    print(f"Xong {time.time() - t0:.1f}s → {out}")


def cmd_qa(a) -> None:
    d = job_dir(a.id)
    rep = qa.run(d, final=a.final)
    print(f"{'ĐẠT' if rep['pass'] else 'CHƯA ĐẠT'} · {rep['frames_checked']} khung · sót {len(rep['residual_chinese'])}")
    for r in rep["residual_chinese"]:
        print(f"  {r['t']:6.2f}s  {r['text']}  box_2d={r['box_2d']}")
    if rep.get("scene_kept"):
        texts = sorted({r["text"] for r in rep["scene_kept"]})
        print(f"  (giữ nguyên {len(rep['scene_kept'])} chữ trong cảnh: {', '.join(texts)})")
    if rep.get("tiny_ignored"):
        texts = sorted({r["text"] for r in rep["tiny_ignored"]})
        print(f"  (bỏ qua {len(rep['tiny_ignored'])} chữ rất nhỏ ≤2,5% khung: {', '.join(texts)})")
    print(f"→ {d / 'qa.json'} · {d / rep['contact_sheet']}")


def cmd_voice(a) -> None:
    d = job_dir(a.id)
    t0 = time.time()
    rep = voice.build(d)
    print(f"Xong {time.time() - t0:.1f}s · {len(rep['lines'])} câu · giọng {rep['voice']}")
    for ln in rep["lines"]:
        flag = f" ×{ln['tempo']}" if ln["tempo"] > 1.0 else ""
        print(f"  {ln['start']:6.2f}s  {ln['duration']:.2f}s/{ln['slot']:.2f}s{flag}  khớp {ln['match']}  {ln['text']}")
    for msg in rep["too_long"]:
        print(f"  ⚠ {msg}")


def cmd_music(a) -> None:
    d = job_dir(a.id)
    out = voice.make_music(d, a.prompt)
    print(f"→ {out}")


def cmd_patch(a) -> None:
    d = job_dir(a.id)
    log = qa.patch(d)
    print("\n".join(log) if log else "Không có gì để vá (qa.json sạch).")


def cmd_cost(a) -> None:
    d = job_dir(a.id)
    rows = [json.loads(line) for line in (d / "usage.jsonl").read_text(encoding="utf-8").splitlines() if line]
    tot = {k: sum((r.get(k) or 0) for r in rows) for k in ("prompt", "output", "thoughts", "total")}
    print(f"{len(rows)} lần gọi · {tot}")


def main() -> None:
    p = argparse.ArgumentParser(description="GDP Video Studio")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new"); s.add_argument("video"); s.add_argument("--id"); s.set_defaults(fn=cmd_new)
    s = sub.add_parser("analyze"); s.add_argument("id"); s.add_argument("--interval", type=float, default=0.5); s.add_argument("--regroup", action="store_true", help="gom lại từ analysis.json, không gọi Gemini"); s.set_defaults(fn=cmd_analyze)
    s = sub.add_parser("render"); s.add_argument("id"); s.add_argument("--final", action="store_true"); s.add_argument("--allow-empty", action="store_true"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("qa"); s.add_argument("id"); s.add_argument("--final", action="store_true"); s.set_defaults(fn=cmd_qa)
    s = sub.add_parser("patch"); s.add_argument("id"); s.set_defaults(fn=cmd_patch)
    s = sub.add_parser("voice"); s.add_argument("id"); s.set_defaults(fn=cmd_voice)
    s = sub.add_parser("music"); s.add_argument("id"); s.add_argument("--prompt"); s.set_defaults(fn=cmd_music)
    s = sub.add_parser("cost"); s.add_argument("id"); s.set_defaults(fn=cmd_cost)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
