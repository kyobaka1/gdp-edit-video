"""GDP Video Studio CLI. Chạy bằng .venv\\Scripts\\python.exe vs.py <lệnh> …

  new <video> [--id ID]        tạo job từ video nguồn (copy vào jobs/<id>/)
  analyze <id> [--interval S] [--regroup]  Gemini tìm chữ Trung + chép lời → analysis.json, edl.draft.json
                               (--regroup: gom lại từ kết quả đã lưu, không tốn token)
  render <id> [--final] [--allow-empty]   dựng preview.mp4 (960p) hoặc final.mp4 từ edl.json
  qa <id> [--final]            kiểm còn sót chữ Hán → qa.json + contact.jpg
  patch <id>                   đưa chỗ sót của qa.json vào edl.json (nới giờ ô cũ / thêm ô blur cần xem)
  music <id> [--prompt P]      tạo nhạc nền không lời bằng Lyria → jobs/<id>/music.mp3
  voice <id>                   (cũ) đọc rời từng câu — KHÔNG dùng nữa, thay bằng narrate
  narrate <id>                 thuyết minh liền mạch edl.narration: 1 lượt TTS, kiểm ngược, đặt đoạn theo cảnh
  audiocheck <id> [--final]    đo LUFS cả bản + nhạc ở khoảng không giọng
  templates <shop>             liệt kê mẫu chữ của shop + ảnh xem trước
  shops                        tình trạng tài nguyên từng shop (màu, mẫu, logo, intro/outro, nhạc)
  siblings <id>                các bản khác cùng video nguồn (shop, thuyết minh, chữ đè, độ giống) — chống lặp nội dung
  cost <id>                    tổng token Gemini của job
  look <ảnh…> -q "câu hỏi"     soát mắt ảnh bằng model RẺ qua Codex/ChatGPT (không tốn Gemini) — agent dùng thay
                               vì tự mở ảnh bằng model đắt; Codex hỏng/hết usage → Gemini
  hear <file audio>            chép lại lời Việt trong audio (Gemini — Codex không nhận audio)
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
    lj = d / "logo.json"
    if lj.exists() and lj.stat().st_mtime >= t0:
        info = json.loads(lj.read_text(encoding="utf-8"))
        print(f"  logo {info['corner']} {info['w']}x{info['h']} tại ({info['x']},{info['y']}) — {info['reason']}")


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
    sc = rep.get("screen") or {}
    print(f"  soát: Codex {sc.get('codex_batches', 0)} lô · Gemini dự phòng {sc.get('gemini_fallback_batches', 0)} lô"
          f" · Gemini xác nhận {len(rep.get('gemini_confirmed_frames', []))} khung"
          + (f" (lý do dự phòng: {sc['fallback_reason'][:120]})" if sc.get("fallback_reason") else ""))
    if rep.get("gemini_confirm_error"):
        print(f"  ⚠ Gemini KHÔNG xác nhận được ({rep['gemini_confirm_error'][:100]}) → ô sót là ô Codex (thô): patch xong soát mắt")
    print(f"→ {d / 'qa.json'} · {d / rep['contact_sheet']}")


def cmd_look(a) -> None:
    from studio import codex, gemini
    imgs = [Path(x) for x in a.images]
    try:
        print(codex.ask_text(imgs, a.q))
        print(f"[codex {codex.MODEL}]")
    except codex.CodexUnavailable as exc:
        from google.genai import types
        parts = [types.Part.from_bytes(data=p.read_bytes(), mime_type="image/png" if p.suffix.lower() == ".png"
                                       else "image/jpeg") for p in imgs]
        print(gemini.client().models.generate_content(model=gemini.config.GEMINI_MODEL, contents=[*parts, a.q]).text)
        print(f"[Gemini dự phòng — codex: {str(exc)[:120]}]")


def cmd_hear(a) -> None:
    from studio import gemini
    from google.genai import types
    p = Path(a.audio)
    mime = {".wav": "audio/wav", ".mp3": "audio/mp3", ".m4a": "audio/mp4"}.get(p.suffix.lower(), "audio/wav")
    print(gemini.client().models.generate_content(model=gemini.config.GEMINI_MODEL, contents=[
        types.Part.from_bytes(data=p.read_bytes(), mime_type=mime),
        "Chép lại nguyên văn lời nói tiếng Việt trong audio, không thêm gì khác."]).text)


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


def cmd_narrate(a) -> None:
    from studio import narration
    d = job_dir(a.id)
    t0 = time.time()
    rep = narration.build(d)
    print(f"Xong {time.time() - t0:.1f}s · 1 lượt đọc {rep['take_seconds']}s · khớp {rep['match']} · giọng {rep['voice']}")
    for p in rep["pieces"]:
        flag = f"  (trễ {p['drift']}s)" if p["drift"] > 0.3 else ""
        print(f"  {p['start']:6.2f}–{p['end']:6.2f}s  [cảnh {p['at']}] khớp {p.get('match')}{flag}  {p['text'][:60]}")
    for w in rep["warnings"]:
        print(f"  ⚠ {w}")


def cmd_audiocheck(a) -> None:
    """Đo độ to: cả bản, riêng nhạc ở các khoảng không có giọng (phải nghe thấy, ~-30…-24 LUFS)."""
    d = job_dir(a.id)
    video = d / ("final.mp4" if a.final else "preview.mp4")
    rep = json.loads((d / "narration.json").read_text(encoding="utf-8"))
    ff = config.FFMPEG

    def lufs(args: list[str]) -> str:
        out = media.subprocess.run([ff, "-hide_banner", *args, "-af", "ebur128", "-f", "null", "-"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
        tail = out[out.rfind("Summary:"):]
        m = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
        return m.group(1) if m else "?"

    print(f"Cả bản: {lufs(['-i', str(video), '-vn'])} LUFS")
    gaps, prev = [], 0.0
    for p in rep["pieces"]:
        if p["start"] - prev >= 1.0:
            gaps.append((prev + 0.2, p["start"] - 0.2))
        prev = p["end"]
    for s, e in gaps[:6]:
        print(f"  nhạc không giọng {s:5.1f}–{e:5.1f}s: {lufs(['-ss', f'{s:.2f}', '-to', f'{e:.2f}', '-i', str(video), '-vn'])} LUFS")


def cmd_music(a) -> None:
    d = job_dir(a.id)
    out = voice.make_music(d, a.prompt)
    print(f"→ {out}")


def cmd_templates(a) -> None:
    from studio.templates import manifest, preview_sheet, template_dir
    man = manifest(a.shop)
    print(f"Mẫu của {a.shop} lấy từ: {template_dir(a.shop)}")
    for slot, spec in man["slots"].items():
        print(f"  {slot:8} {spec['file']:14} {spec['use']}")
    print(f"→ {preview_sheet(a.shop)}")


def cmd_shops(a) -> None:
    """Bảng tình trạng tài nguyên từng shop: màu, mẫu chữ, logo, intro/outro, nhạc."""
    from studio.templates import SHOPS, shop_profile, template_dir
    for d in sorted(p for p in SHOPS.iterdir() if (p / "shop.json").exists()):
        s = shop_profile(d.name)
        try:
            t = template_dir(d.name)
            tpl = "riêng" if t.parent == d else f"mượn {t.parent.name}"
        except FileNotFoundError:
            tpl = "THIẾU"
        logos = [k for k, f in s["logo"]["files"].items() if (d / f).exists()]
        intro = "có" if (d / s["intro"]["file"]).exists() else "-"
        outro = "có" if (d / s["outro"]["file"]).exists() else "-"
        music = len(list((d / "music").glob("*.mp3"))) + len(list((d / "music").glob("*.wav")))
        print(f"  {d.name:22} {s.get('brand', ''):12} màu {'✓' if s.get('configured') else 'mặc định'} · mẫu {tpl:22}"
              f" · logo {','.join(logos) or 'THIẾU'} · intro {intro} · outro {outro} · nhạc {music}")


def cmd_siblings(a) -> None:
    """Các bản khác CÙNG video nguồn (meta.origin): shop, thuyết minh, chữ đè + độ giống với bản này.
    Dùng khi làm 1 video cho nhiều shop: câu chữ phải khác nhau (luật đa dạng nội dung, Sếp 20/10)."""
    from difflib import SequenceMatcher
    d = job_dir(a.id)
    me = json.loads((d / "meta.json").read_text(encoding="utf-8"))

    def texts(j: Path) -> tuple[str, str, str]:
        p = j / "edl.json"
        if not p.exists():
            return "", "", ""
        e = json.loads(p.read_text(encoding="utf-8"))
        nar = " ".join(x["text"] for x in (e.get("narration") or {}).get("paragraphs", []))
        cap = " | ".join(o.get("text_vi", "") for o in e.get("overlays", []) if o.get("text_vi") and not o.get("skip"))
        return e.get("shop", "?"), nar, cap

    _, my_nar, my_cap = texts(d)

    def sentences(s: str) -> list[str]:
        return [x.strip() for x in re.split(r"[.!?|:]\s*", s) if len(x.strip()) > 8]

    for j in sorted(p for p in config.JOBS.iterdir() if (p / "meta.json").exists() and p != d):
        m = json.loads((j / "meta.json").read_text(encoding="utf-8"))
        if Path(m.get("origin", "")).name != Path(me.get("origin", "")).name:
            continue
        shop, nar, cap = texts(j)
        sn = SequenceMatcher(None, my_nar, nar).ratio() if my_nar and nar else None
        sc = SequenceMatcher(None, my_cap, cap).ratio() if my_cap and cap else None
        print(f"== {j.name} (shop {shop}) · giống thuyết minh {sn if sn is None else round(sn, 2)} · giống chữ đè {sc if sc is None else round(sc, 2)}")
        print(f"   thuyết minh: {nar}")
        print(f"   chữ đè: {cap}")
        # câu gần như trùng (≥0,75) giữa bản này và bản kia — phải viết lại
        theirs = sentences(nar) + sentences(cap)
        for s in sentences(my_nar) + sentences(my_cap):
            best = max(theirs, key=lambda t: SequenceMatcher(None, s, t).ratio(), default="")
            r = SequenceMatcher(None, s, best).ratio() if best else 0
            if r >= 0.75:
                print(f"   ⚠ câu trùng {r:.2f}: «{s}» ≈ «{best}»")


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
    s = sub.add_parser("templates"); s.add_argument("shop"); s.set_defaults(fn=cmd_templates)
    s = sub.add_parser("shops"); s.set_defaults(fn=cmd_shops)
    s = sub.add_parser("siblings"); s.add_argument("id"); s.set_defaults(fn=cmd_siblings)
    s = sub.add_parser("narrate"); s.add_argument("id"); s.set_defaults(fn=cmd_narrate)
    s = sub.add_parser("audiocheck"); s.add_argument("id"); s.add_argument("--final", action="store_true"); s.set_defaults(fn=cmd_audiocheck)
    s = sub.add_parser("voice"); s.add_argument("id"); s.set_defaults(fn=cmd_voice)
    s = sub.add_parser("music"); s.add_argument("id"); s.add_argument("--prompt"); s.set_defaults(fn=cmd_music)
    s = sub.add_parser("cost"); s.add_argument("id"); s.set_defaults(fn=cmd_cost)
    s = sub.add_parser("look"); s.add_argument("images", nargs="+"); s.add_argument("-q", required=True); s.set_defaults(fn=cmd_look)
    s = sub.add_parser("hear"); s.add_argument("audio"); s.set_defaults(fn=cmd_hear)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
