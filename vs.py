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
  hear <file audio>            chép lại lời Việt trong audio (Gemini; hết tiền → tokenrouter gpt-audio-mini)
  motion <việc> …              thư viện animation thương hiệu (Claude Design → overlay alpha), chi tiết: assets/motion/README.md
      list [--shop S] [--role R] [--all]      danh sách (theo shop: chỉ animation đúng brand)
      scan <thư mục>                          phân loại file tải từ Claude Design (nguồn/preview/thiếu asset…), không nhập
      import <file|thư mục|zip> [--id ID] [--brand B] [--shop S] [--role R] [--name N] [--entry F] [--no-render]
      info <id> · versions <id> · use <id> <phiên bản> · enable <id> · disable <id>
      render <id> [--variant V] [--param k=v] [--force] [--footage ảnh]   render alpha (cache) + ảnh soát 3 nền
      check <id|all>                          render (nếu chưa) + kiểm alpha
      export <id> --out file.mov|.webm [--variant V]   xuất clip alpha cho CapCut/Premiere
      plan <job> [--update]                   kế hoạch: animation chọn/bỏ + lý do, budget, logo thường trực hiện khi nào,
                                              vòng đời watermark (intro/mờ/giữ/đổi chỗ) → motion_plan.json
      storyboard <job> [--final] [--before video_cũ.mp4]   ảnh soát các mốc (trước/giữa/sau reveal, logo tiếp quản,
                                              watermark mờ/giữ/đổi chỗ, trước/trong outro) → motion_storyboard.jpg
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
    mj = d / "motion_plan.json"
    if mj.exists() and mj.stat().st_mtime >= t0:
        _print_motion_plan(json.loads(mj.read_text(encoding="utf-8")))


def _print_motion_plan(mp: dict, full: bool = False) -> None:
    lib = mp.get("library") or {}
    print(f"  animation ({mp['mode']}) · thư viện {lib.get('total', '?')} · dùng được cho shop {mp.get('shop')}: "
          f"{lib.get('usable', '?')} · budget {mp.get('budget') or '-'} · chọn {len(mp['items'])}")
    for it in mp["items"]:
        print(f"    {it['start']:6.2f}–{it['end']:6.2f}s  {it['id']} v{it['version']} [{it['role']}] {it['w']}x{it['h']} "
              f"tại ({it['x']},{it['y']}) · scale {it.get('scale', '-')} · mờ {it['opacity']:.0%} — {it['reason']}")
    lg = mp.get("logo") or {}
    if lg.get("enabled"):
        vis = ", ".join(f"{a:.2f}–{b:.2f}s" for a, b in lg["visible"])
        print(f"    logo thường trực {lg['rect']} hiện {vis} ({lg.get('visible_ratio', 1):.0%} video chính) — {lg['reason']}")
    elif lg:
        print(f"    logo thường trực: không — {lg.get('reason')}")
    w = mp.get("watermark")
    if w:
        ph = w["phases"]
        segs = " → ".join(f"({s['x']},{s['y']}) {s['start']:.1f}–{s['end']:.1f}s" for s in w["segments"])
        print(f"    watermark động {w['id']} v{w['version']} {w['w']}x{w['h']}: intro {ph['intro'][0]:.1f}–{ph['intro'][1]:.1f}s"
              + (f" · mờ {ph['dim'][0]:.1f}–{ph['dim'][1]:.1f}s về {w['opacity']:.0%}" if ph.get("dim") else "")
              + f" · giữ {ph['hold'][0]:.1f}–{ph['hold'][1]:.1f}s · chỗ: {segs} · mờ hẳn {ph['exit'][0]:.1f}s")
        print(f"      {w['reason']}")
    if full or mp["mode"] == "auto":
        for s in mp.get("skipped", []):
            print(f"    – bỏ {s['id']}: {s['reason']}")
    for n in mp.get("notes", []):
        print(f"    · {n}")
    for wn in mp.get("warnings", []):
        print(f"    ⚠ {wn}")


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
    from studio import motiondirector, outro
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    edl = json.loads((d / "edl.json").read_text(encoding="utf-8"))
    mq = motiondirector.qa(d, d / ("final.mp4" if a.final else "preview.mp4"), outro.total_duration(edl, meta))
    if mq is not None:  # kiểm phần animation bằng số đo (không AI); lỗi → QA chưa đạt
        rep["motion"] = mq
        rep["pass"] = rep["pass"] and mq["ok"]
        (d / "qa.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        lg = mq["logo"] or {}
        print(f"  animation: {'đạt' if mq['ok'] else 'CHƯA ĐẠT'} · {', '.join(mq['items']) or 'không chèn'}"
              f" · watermark động {mq['watermark'] or '-'} · logo thường trực "
              + (f"hiện {lg.get('visible_ratio', 1):.0%} video chính" if lg.get("enabled") else "không"))
        for p in mq["problems"]:
            print(f"    ⚠ {p}")
        for i in mq["info"]:
            print(f"    · {i}")
        if not mq["ok"]:
            print("  → TỔNG: CHƯA ĐẠT (lỗi animation)")
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
    from studio import voice as v
    print(v.hear(Path(a.audio)))
    print("[tokenrouter gpt-audio-mini — Gemini hết tiền/lỗi]" if v.gemini_dead() else "[Gemini]")


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
    print(f"  đọc: {rep['model']} · định vị đoạn: {rep.get('align', 'gemini')}")
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
    from studio import motionlib
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
        anims = motionlib.catalog(d.name)
        wm = (s.get("watermark") or {}).get("motion") or "chữ"
        print(f"  {d.name:22} {s.get('brand', ''):12} màu {'✓' if s.get('configured') else 'mặc định'} · mẫu {tpl:22}"
              f" · logo {','.join(logos) or 'THIẾU'} · intro {intro} · outro {outro} · nhạc {music}"
              f" · animation {len(anims)} · watermark {wm}")


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


def _kv(pairs: list[str] | None) -> dict:
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def cmd_motion(a) -> None:
    """Thư viện animation thương hiệu: nhập từ Claude Design, render alpha, kiểm, chọn cho job."""
    from studio import motionlib as ml
    act, args = a.action, a.args

    def need(n: int, what: str) -> None:
        if len(args) < n:
            sys.exit(f"Thiếu {what}: vs.py motion {act} {what}")

    def row(x: dict) -> str:
        st = "TẮT" if not x["enabled"] else ("LỖI" if x["problems"] else "bật")
        scope = f"shop {x['shop_scope']}" if x.get("shop_scope") else ",".join(x["brands"])
        dur = f"{x.get('duration') or '?'}s"
        return (f"  {x['id']:26} v{x['version']:<2} {st:4} {scope:12} {','.join(x['roles']):16} {dur:6} "
                f"ưu tiên {x['priority']:<3} {x.get('name', '')}")

    try:
        if act == "list":
            role = a.role[0] if a.role else None
            rows = ml.catalog(a.shop, role, include_disabled=a.all) if a.shop or role or not a.all else ml.discover()
            if a.all and not (a.shop or role):
                rows = sorted(rows, key=lambda x: (",".join(x["brands"]), x["id"]))
            print(f"Thư viện: {ml.LIB} · {len(rows)} animation" + (f" dùng được cho shop {a.shop}" if a.shop else ""))
            for x in rows:
                print(row(x))
                for p in x["problems"]:
                    print(f"      ⚠ {p}")
        elif act == "scan":
            need(1, "<thư mục>")
            for r in ml.scan(Path(args[0])):
                print(f"  {'✓' if r['ok'] else '·'} {r['path'].name:40} {r['kind']:9} {r['note']}")
        elif act == "import":
            need(1, "<file|thư mục|zip>")
            res = ml.import_source(Path(args[0]), anim_id=a.id, brands=a.brand, roles=a.role, name=a.name,
                                   shop=a.shop, entry=a.entry, test_render=not a.no_render)
            x = res["anim"]
            print(f"Đã nhập {x['id']} v{x['version']} → {x['dir']}" + (f" (bản cũ cất ở {res['archived']})" if res["archived"] else ""))
            print(row(x))
            for p in x["problems"]:
                print(f"  ⚠ {p}")
            if res["info"]:
                _print_render(res["info"])
            print(f"  → sửa metadata (roles, tags, placement, variants…) trong {x['dir'] / 'motion.json'} — xem assets/motion/README.md")
        elif act == "info":
            need(1, "<id>")
            x = ml.get(args[0])
            print(json.dumps({k: v for k, v in x.items() if k not in ("dir",)}, ensure_ascii=False, indent=2, default=str))
            print(f"thư mục: {x['dir']} · hash nguồn {ml.source_hash(x)}")
            for c in ml.cached_renders(x["id"]):
                print(f"  cache {c['key']} (nguồn {c['src_hash'][:8]}, biến thể {c['spec']['variant']}, tham số {c['spec']['params']}) "
                      f"{c['frames']} khung → {c['mov']}")
        elif act in ("render", "check"):
            need(1, "<id|all>")
            targets = ml.discover() if args[0] == "all" else [ml.get(args[0])]
            bad = 0
            for x in targets:
                if not x["enabled"] and args[0] == "all":
                    continue
                try:
                    vars_ = [a.variant] if a.variant else ([None] if act == "render" else (list(x["variants"]) or [None]))
                    for v in vars_:
                        info = ml.render(x, v, _kv(a.param), force=a.force,
                                         footage=Path(a.footage) if a.footage else None)
                        print(f"{x['id']} {'(' + v + ')' if v else ''}")
                        _print_render(info)
                        bad += bool(info["check"]["warn"])
                except ml.MotionError as exc:
                    bad += 1
                    print(f"{x['id']}: ✗ {exc}")
            if act == "check":
                print("KIỂM: " + ("ĐẠT" if not bad else f"{bad} animation có lỗi/cảnh báo"))
        elif act in ("enable", "disable"):
            need(1, "<id>")
            x = ml.set_enabled(args[0], act == "enable")
            print(row(x))
        elif act == "versions":
            need(1, "<id>")
            x = ml.get(args[0])
            for v in ml.versions(x):
                print(f"  v{v['version']} {'(hiện hành)' if v['current'] else ''} nguồn {v['src_hash']}")
        elif act == "use":
            need(2, "<id> <phiên bản>")
            x = ml.use_version(args[0], int(str(args[1]).lstrip("v")))
            print(f"Đã chuyển {x['id']} về v{x['version']}")
        elif act == "export":
            need(1, "<id>")
            if not a.out:
                sys.exit("Cần --out <file.mov|file.webm>")
            info = ml.render(ml.get(args[0]), a.variant, _kv(a.param))
            out = Path(a.out)
            if out.suffix.lower() == ".webm":
                media.run([config.FFMPEG, "-y", "-v", "error", "-i", info["mov"], "-c:v", "libvpx-vp9", "-pix_fmt",
                           "yuva420p", "-b:v", "0", "-crf", "18", "-auto-alt-ref", "0", str(out)])
            else:
                shutil.copyfile(info["mov"], out)
            print(f"→ {out} ({info['bbox'][2]}x{info['bbox'][3]}, {info['duration']}s, alpha)")
        elif act == "plan":
            need(1, "<job>")
            from studio import motiondirector, render as rd
            d = job_dir(args[0])
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            edl = json.loads((d / "edl.json").read_text(encoding="utf-8"))
            if a.update:
                edl.setdefault("motion", {"mode": "auto"})
                if isinstance(edl["motion"], dict):
                    edl["motion"]["update"] = True
            if "motion" not in edl:
                print("Job chưa khai edl.motion → flow cũ (logo tĩnh + watermark chữ). Thêm edl[\"motion\"] = "
                      "{\"mode\": \"auto\"} trong direct.py để dùng animation.")
                return
            from studio import logo as lg_mod
            boxes = rd.label_boxes(d, edl, meta)
            lp = lg_mod.plan(d, edl, meta, boxes, persistent=True)
            _print_motion_plan(motiondirector.plan(d, edl, meta, boxes, (lp["x"], lp["y"], lp["w"], lp["h"]) if lp else None),
                               full=True)
            print(f"→ {d / 'motion_plan.json'} (vùng chữ ước lượng — render thật dùng ô đã vẽ)")
        elif act == "storyboard":
            need(1, "<job>")
            from studio import motiondirector
            d = job_dir(args[0])
            video = d / ("final.mp4" if a.final else "preview.mp4")
            if not (d / "motion_plan.json").exists() or not video.exists():
                sys.exit("Cần render trước (vs.py render <job>) — job phải khai edl.motion")
            out = motiondirector.storyboard(d, video, d / "motion_storyboard.jpg", Path(a.before) if a.before else None)
            print(f"→ {out}")
        else:
            sys.exit(f"Không có việc '{act}' (list | scan | import | info | render | check | enable | disable | "
                     f"versions | use | export | plan | storyboard)")
    except ml.MotionError as exc:
        sys.exit(f"✗ {exc}")


def _print_render(info: dict) -> None:
    c = info["check"]
    print(f"  ✓ alpha {info['bbox'][2]}x{info['bbox'][3]} (trên khung {info['canvas'][0]}x{info['canvas'][1]}, chạm mép "
          f"{','.join(c['touches_edge']) or '-'}) · {info['frames']} khung {info['fps']:g}fps = {info['duration']}s · "
          f"khung đầu α{c['first_alpha_max']} · khung cuối α{c['last_alpha_max']} · halo {c['halo']}")
    for w in c["warn"]:
        print(f"  ⚠ {w}")
    print(f"  clip: {info['mov']}")
    print(f"  soát 3 nền (tối/sáng/footage): {Path(info['dir']) / 'sheet.jpg'}")


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
    s = sub.add_parser("motion"); s.add_argument("action"); s.add_argument("args", nargs="*")
    s.add_argument("--shop"); s.add_argument("--role", action="append", help="vai trò (import: lặp lại được)")
    s.add_argument("--all", action="store_true")
    s.add_argument("--id"); s.add_argument("--brand", action="append"); s.add_argument("--name"); s.add_argument("--entry")
    s.add_argument("--no-render", action="store_true"); s.add_argument("--variant"); s.add_argument("--param", action="append")
    s.add_argument("--force", action="store_true"); s.add_argument("--footage"); s.add_argument("--out")
    s.add_argument("--update", action="store_true"); s.add_argument("--final", action="store_true")
    s.add_argument("--before", help="storyboard: video bản cũ để so cùng mốc giờ"); s.set_defaults(fn=cmd_motion)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
