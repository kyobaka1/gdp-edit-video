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
  lib <việc> …                 THƯ VIỆN ASSET DÙNG CHUNG (assets/library/ — xây 1 lần, dùng nhiều video; Sếp 05/11)
      find [từ…] [--kind K] [--theme T]       tìm asset có sẵn — LUÔN tìm trước khi tạo
      list [--theme T]                        danh mục (+ job đã dùng)
      gen <chủ-đề>/<tên> --prompt "…" [--kind canh|nen|cat-dan|icon] [--alpha] [--size doc|vuong|ngang] [--tag t]…
                                              tạo qua Codex local (~60s, không tốn API); ĐÃ CÓ thì dùng lại (--force mới tạo lại)
      kit <bộ> [--only id]…                   tạo phần còn THIẾU của bộ asset cho 1 kiểu animation (assets/library/kits/<bộ>.json)
      sheet <chủ-đề|bộ>                       ảnh soát (nền ca-rô cho asset trong suốt)
      import <file> <chủ-đề>/<tên> --prompt "…" [--kind K] [--engine chatgpt-web|photo]   nạp ảnh tạo trên chatgpt.com
                                              (Codex hỏng) / ảnh Sếp đưa
      ⛔ ảnh AI chỉ minh hoạ bối cảnh/ý — không vẽ sản phẩm đang bán thay ảnh thật, không làm bằng chứng
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
  edit <việc> …                dựng video từ source QUAY SẴN theo PLAN (skill gdp-video-edit, studio/edit/)
      new <thư mục|file…> --id ID --capcut co|khong [--plan plan.md]   tạo job, chép clip vào sources/ (c01, c02…)
                                              ⚠ chưa rõ CÓ/KHÔNG dùng CapCut thì DỪNG hỏi Sếp (Sếp chốt 05/11)
      mode <id> co|khong                      đổi chế độ: co = giao bản nháp CapCut · khong = giao final.mp4
      add <id> <file|lib:chủ-đề/tên> --key g01 [--text kịch_bản.txt]  thêm giọng đọc riêng / clip / ảnh tĩnh
                                              (ảnh → clip 15s cho cover; lib: = asset thư viện chung, ghi job đã dùng)
      ingest <id>                             chép lời có mốc từng từ (Whisper GPU) + ảnh lưới từng clip
      fix <id> <key> (--hear | --text file)   đối chiếu lời với Gemini / kịch bản: giữ mốc, sửa chữ
      words <id>                              in lời từng nguồn (có giây) để viết cut.py
      cut <id>                                chạy jobs/<id>/cut.py → edit.json (in trục dựng)
      render <id> [--final|--draft]           preview 540x960 / final 1080x1920 / nháp 360x640 chốt điểm cắt (chỉ
                                              trục dựng + tiếng đủ, in mốc mối cắt → draft.mp4, render_draft.json)
      qa <id> [--final]                       cổng kiểm (lời, cắt, chữ né mặt + vùng an toàn, hình, tiếng) + ảnh soát
      capcut <id> [--name N] [--until S] [--fmt pngmov|prores] [--wait]   xuất BẢN NHÁP CapCut desktop để dựng viên
                                              sửa tiếp (clip gốc + chữ động trong suốt + chữ CapCut ẩn + logo + tiếng)
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


def cmd_lib(a) -> None:
    """Thư viện asset dùng chung (studio/library.py)."""
    from studio import codex, imagegen, library
    act, args = a.action, a.args

    def show(rows):
        for r in rows:
            used = f" · dùng ở {len(r.get('used_by', []))} job" if r.get("used_by") else ""
            kits = f" · bộ {','.join(r['kits'])}" if r.get("kits") else ""
            print(f"  {r['id']:38s} {r.get('kind', ''):8s} {'trong suốt ' if r.get('alpha') else ''}"
                  f"{r.get('engine') or ''}{kits}{used}\n      {library.path(r['id'])}\n      {r.get('prompt', '')[:110]}")
        print(f"{len(rows)} asset")
    try:
        if act in ("find", "list"):
            show(library.find(" ".join(args), kind=a.kind, theme=a.theme))
        elif act == "gen":
            if not args or not a.prompt:
                sys.exit('vs.py lib gen <chủ-đề>/<tên> --prompt "…" [--kind canh|nen|cat-dan|icon] [--alpha] [--size doc]')
            t0 = time.time()
            r, made = library.gen(args[0], a.prompt, kind=a.kind or "canh", alpha=a.alpha, size=a.size or "doc",
                                  tags=a.tag or [], refs=[Path(x) for x in a.ref or []], force=a.force)
            print(("Tạo mới" if made else "ĐÃ CÓ — dùng lại, không tạo") + f" {args[0]} ({time.time() - t0:.0f}s)")
            show([{"id": args[0], **r}])
        elif act == "kit":
            if not args:
                kits = sorted(p.stem for p in library.KITS.glob("*.json"))
                sys.exit("vs.py lib kit <bộ> — có: " + (", ".join(kits) or "(chưa có bộ nào)"))
            st = library.kit_status(args[0])
            print(f"Bộ {args[0]}: có {sum(x['have'] for x in st)}/{len(st)} — tạo phần thiếu (song song 3 lượt Codex)…")
            t0 = time.time()
            res = library.kit_gen(args[0], only=a.only)
            out = library.KITS / f"{args[0]}.jpg"
            library.sheet([x["id"] for x in library.kit_status(args[0])], out)
            print(f"Xong {time.time() - t0:.0f}s · mới {len(res['made'])} · có sẵn {len(res['kept'])} · hỏng "
                  f"{len(res['failed'])} → ảnh soát {out}")
            if res["failed"]:
                print("  chạy lại `vs.py lib kit` để tạo lại phần hỏng; Codex hết usage → chatgpt.com + `vs.py lib import`")
        elif act == "sheet":
            ids = [x["id"] for x in library.kit_status(args[0])] if (library.KITS / f"{args[0]}.json").exists() \
                else [r["id"] for r in library.find(theme=args[0])]
            print(library.sheet(ids, (library.KITS if (library.KITS / f"{args[0]}.json").exists() else library.LIB / args[0]) / f"_soat_{args[0]}.jpg"))
        elif act == "import":
            if len(args) < 2 or not a.prompt:
                sys.exit('vs.py lib import <file> <chủ-đề>/<tên> --prompt "…" [--kind K] [--engine chatgpt-web|photo]')
            r = library.import_file(Path(args[0]), args[1], a.prompt, a.kind or "canh", a.tag or [],
                                    engine=a.engine or "chatgpt-web", force=a.force)
            show([{"id": args[1], **r}])
        else:
            sys.exit(f"Không có việc '{act}' (find · list · gen · kit · sheet · import)")
    except codex.CodexUnavailable as exc:
        sys.exit(f"Codex không tạo được ảnh: {exc}\n→ cách 2: Claude lái chatgpt.com trên Chrome (đã đăng nhập), lưu "
                 "ảnh về rồi `vs.py lib import` (skill gdp-video-edit, mục 'Thư viện asset dùng chung')")
    except (library.LibraryError, imagegen.ImageGenError) as exc:
        sys.exit(str(exc))


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


def cmd_styles(a) -> None:
    """Phong cách dựng (assets/styles/): kiểu chữ, màu hình, Scene ưu tiên — dùng trong cut.py: c.style("<id>")."""
    from studio.edit import styles
    for s in styles.summary():
        d = styles.load(s["id"])
        print(f"  {s['id']:18} {d.get('code', ''):3} {s['name']}")
        print(f"      dùng cho: {'; '.join(s['use_for'])}")
        print(f"      học từ: {s['learned_from'][:150]}")
        print(f"      chữ y≈{d.get('captions', {}).get('y')} · màu {d.get('grade')} · màn chữ {d.get('card_bg')} · "
              f"Scene ưu tiên: {', '.join(d.get('scenes', {}).get('prefer', []))}")


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


def cmd_edit(a) -> None:
    """Dựng video từ source quay sẵn theo PLAN (skill gdp-video-edit)."""
    import runpy
    from studio.edit import project
    act, args = a.action, a.args
    if act == "new":
        if not args or not a.id:
            sys.exit("vs.py edit new <thư mục|file…> --id <id> --capcut co|khong [--plan plan.md]")
        if a.capcut is not None and project.parse_mode(a.capcut) is None:
            sys.exit(f"--capcut '{a.capcut}' không hiểu (dùng co | khong)")
        d = project.new(a.id, [Path(x) for x in args], Path(a.plan) if a.plan else None,
                        capcut=project.parse_mode(a.capcut))
        print(f"Tạo {d}\nChế độ: {project.MODE_TEXT[project.mode(d)]}")
        for k, s in project.load_sources(d).items():
            print(f"  [{k}] {Path(s['origin']).name} · {s['duration']:.1f}s · {'ảnh tĩnh' if s.get('still') else 'hình+tiếng' if s.get('has_video') else 'tiếng'}")
        print(f"→ vs.py edit ingest {a.id}")
    elif act == "add":
        if len(args) < 2:
            sys.exit("vs.py edit add <id> <file> --key vo [--text kịch_bản.txt]")
        from studio import library
        f, aid = library.resolve(args[1])
        s = project.add(args[0], f, a.key or "vo", Path(a.text) if a.text else None)
        if aid:
            library.mark_used(aid, args[0])
            print(f"Dùng asset thư viện {aid}" + (" (ẢNH AI — chỉ minh hoạ bối cảnh)" if s.get("ai") else ""))
        print(f"Thêm {a.key or 'vo'}: {s['duration']:.1f}s · {'ảnh tĩnh' if s.get('still') else 'hình+tiếng' if s.get('has_video') else 'tiếng'}"
              + (" · có văn bản chuẩn" if s.get("reference") else ""))
    elif act == "ingest":
        t0 = time.time()
        project.ingest(args[0])
        print(f"Xong {time.time() - t0:.1f}s\n" + project.describe(args[0]))
        print(f"Ảnh lưới từng clip: jobs/{args[0]}/sheets/<key>.jpg")
    elif act == "fix":
        if len(args) < 2 or not (a.text or a.hear):
            sys.exit("vs.py edit fix <id> <key> (--text file | --hear)")
        d = project.job_path(args[0])
        if a.hear:
            src = project.load_sources(d)
            ref = voice.hear(d / src[args[1]]["file"])
        else:
            ref = Path(a.text).read_text(encoding="utf-8")
        for c in project.fix(args[0], args[1], ref, heard=bool(a.hear)):
            print(f"  {c['at']:6.2f}s  '{c['asr']}' → '{c['ref']}'" + (f"  ⚠ {c['note']}" if c.get("note") else ""))
    elif act == "words":
        print(project.describe(args[0]))
    elif act == "frame":
        if len(args) < 2:
            sys.exit("vs.py edit frame <id> <giây> [giây…]   (khung RA đúng như bản dựng + lưới toạ độ 0,1 — chọn x,y cho Scene)")
        from studio.edit import build
        for pth in build.frame_grid(args[0], [float(x) for x in args[1:]]):
            print(pth)
    elif act == "cut":
        d = project.job_path(args[0])
        runpy.run_path(str(d / "cut.py"), run_name="__main__")
    elif act == "mode":
        if len(args) < 2 or project.parse_mode(args[1]) is None:
            sys.exit("vs.py edit mode <id> co|khong   (có / không dùng CapCut — Sếp chốt trước khi edit)")
        project.set_mode(args[0], project.parse_mode(args[1]))
        print(f"Chế độ: {project.MODE_TEXT[project.parse_mode(args[1])]}")
    elif act == "render":
        from studio.edit import build
        m = project.mode(project.job_path(args[0]))
        if m is None:
            sys.exit("DỪNG: job chưa khai chế độ — hỏi Sếp có/không dùng CapCut rồi `vs.py edit mode <id> co|khong`")
        if a.final and m and not a.draft:
            print("ℹ Job CÓ dùng CapCut: không bắt buộc render --final — duyệt preview xong thì `vs.py edit capcut <id> --wait`")
        rep = build.run(args[0], final=a.final, draft=a.draft)
        if a.draft:   # nháp chốt điểm cắt: không chữ / đồ hoạ / logo — in mốc từng mối cắt để tua tới
            tm = rep["timings"]
            print(f"Nháp xong {rep['seconds']}s → jobs/{args[0]}/{rep['output']} · {rep['size'][0]}x{rep['size'][1]} "
                  f"{rep['duration']:.2f}s · {rep['lufs']} LUFS · tiếng {tm['audio']}s · khung {tm['frames']}s · "
                  f"độ to {tm['loudness']}s")
            print(f"  bỏ qua: {', '.join(rep['skipped'])} · {len(rep['sfx'])} tiếng động giữ đúng mốc")
            for c in rep["cuts"]:
                print(f"  {c['t']:7.2f}s" + (f"  hình {c['hinh']}" + (f" [{c['trans']}]" if c["trans"] != "cut" else "")
                                             if c.get("hinh") else "") + (f"  lời {c['loi']}" if c.get("loi") else ""))
            return
        print(f"Xong {rep['seconds']}s → jobs/{args[0]}/{rep['output']} · {rep['size'][0]}x{rep['size'][1]} "
              f"{rep['duration']:.2f}s · {rep['lufs']} LUFS · chữ chụp {rep['caption_frames_captured']}/{rep['frames']} khung "
              f"({rep['caption_seconds']}s)")
        for pl in rep["placements"]:
            flag = (f"  ⚠ đè mặt {pl['face_overlap']:.0%}" if pl["face_overlap"] > 0.03 else "") + \
                   (f"  ⚠ ngoài vùng an toàn {pl['outside_safe']:.0%}" if pl["outside_safe"] > 0.01 else "")
            print(f"  {pl['id']} {pl['pos']:6s} y{pl['y']:.2f}  mặt {len(pl['faces'])}{flag}  {pl['markup']}")
    elif act == "qa":
        from studio.edit import qa as eqa
        res = eqa.run(args[0], final=a.final)
        print(("ĐẠT" if res["ok"] else "CHƯA ĐẠT") + f" · {res['lufs']} LUFS · đỉnh {res['true_peak']} dBTP · "
              f"{res['duration']:.2f}s {res['size'][0]}x{res['size'][1]}")
        for f in res["fails"]:
            print(f"  ✗ {f}")
        for w in res["warnings"]:
            print(f"  ⚠ {w}")
        if res["sheet"]:
            print(f"  ảnh soát khối chữ: jobs/{args[0]}/{res['sheet']}")
        if res.get("cuts_sheet"):
            print(f"  ảnh soát mối cắt (khung trước | sau + độ to, đỏ = mép còn tiếng to): jobs/{args[0]}/{res['cuts_sheet']}")
    elif act == "capcut":
        from studio.edit import capcut
        if project.mode(project.job_path(args[0])) is False:
            sys.exit("Job khai KHÔNG dùng CapCut (giao final.mp4). Sếp đổi ý thì `vs.py edit mode <id> co` rồi chạy lại.")
        if capcut.capcut_running():
            print("⚠ CapCut đang mở: bản nháp vẫn ghi, nhưng danh sách dự án sẽ bị CapCut ghi đè — "
                  + ("chờ Sếp đóng CapCut rồi tự ghi danh sách…" if a.wait else "đóng CapCut rồi chạy lại với --wait"))
        res = capcut.export(args[0], name=a.name, until=a.until, formats=[a.fmt] if a.fmt else None)
        print(f"Bản nháp CapCut: {res['draft']}\n  {res['duration']:.2f}s · track {res['tracks']}")
        if a.wait and capcut.capcut_running():
            ok = capcut.wait_and_register([res["name"]], timeout=1800)
            print("Đã ghi vào danh sách dự án — mở CapCut là thấy" if ok else "Hết 30 phút chờ CapCut tắt — chạy lại sau")
        print("  ⚠ CapCut tự cập nhật có thể đổi định dạng bản nháp; mở không được → báo để xuất lại theo bản mới")
    else:
        sys.exit(f"Không có việc '{act}' (new · mode · add · ingest · fix · words · frame · cut · render · qa · capcut)")


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
    s = sub.add_parser("styles"); s.set_defaults(fn=cmd_styles)
    s = sub.add_parser("siblings"); s.add_argument("id"); s.set_defaults(fn=cmd_siblings)
    s = sub.add_parser("narrate"); s.add_argument("id"); s.set_defaults(fn=cmd_narrate)
    s = sub.add_parser("audiocheck"); s.add_argument("id"); s.add_argument("--final", action="store_true"); s.set_defaults(fn=cmd_audiocheck)
    s = sub.add_parser("voice"); s.add_argument("id"); s.set_defaults(fn=cmd_voice)
    s = sub.add_parser("music"); s.add_argument("id"); s.add_argument("--prompt"); s.set_defaults(fn=cmd_music)
    s = sub.add_parser("cost"); s.add_argument("id"); s.set_defaults(fn=cmd_cost)
    s = sub.add_parser("look"); s.add_argument("images", nargs="+"); s.add_argument("-q", required=True); s.set_defaults(fn=cmd_look)
    s = sub.add_parser("hear"); s.add_argument("audio"); s.set_defaults(fn=cmd_hear)
    s = sub.add_parser("lib"); s.add_argument("action"); s.add_argument("args", nargs="*")
    s.add_argument("--prompt"); s.add_argument("--kind", choices=["canh", "nen", "cat-dan", "icon", "khac"])
    s.add_argument("--theme"); s.add_argument("--alpha", action="store_true")
    s.add_argument("--size", choices=["doc", "vuong", "ngang"]); s.add_argument("--tag", action="append")
    s.add_argument("--ref", action="append", help="ảnh tham chiếu phong cách"); s.add_argument("--force", action="store_true")
    s.add_argument("--only", action="append", help="kit: chỉ tạo các id này"); s.add_argument("--engine")
    s.set_defaults(fn=cmd_lib)
    s = sub.add_parser("motion"); s.add_argument("action"); s.add_argument("args", nargs="*")
    s.add_argument("--shop"); s.add_argument("--role", action="append", help="vai trò (import: lặp lại được)")
    s.add_argument("--all", action="store_true")
    s.add_argument("--id"); s.add_argument("--brand", action="append"); s.add_argument("--name"); s.add_argument("--entry")
    s.add_argument("--no-render", action="store_true"); s.add_argument("--variant"); s.add_argument("--param", action="append")
    s.add_argument("--force", action="store_true"); s.add_argument("--footage"); s.add_argument("--out")
    s.add_argument("--update", action="store_true"); s.add_argument("--final", action="store_true")
    s.add_argument("--before", help="storyboard: video bản cũ để so cùng mốc giờ"); s.set_defaults(fn=cmd_motion)
    s = sub.add_parser("edit"); s.add_argument("action"); s.add_argument("args", nargs="*")
    s.add_argument("--id"); s.add_argument("--plan"); s.add_argument("--key"); s.add_argument("--text")
    s.add_argument("--hear", action="store_true"); s.add_argument("--final", action="store_true")
    s.add_argument("--draft", action="store_true", help="render: bản NHÁP chốt điểm cắt (draft.mp4, không chữ/đồ hoạ/logo)")
    s.add_argument("--name"); s.add_argument("--until", type=float); s.add_argument("--fmt", choices=["pngmov", "prores", "qtrle"])
    s.add_argument("--wait", action="store_true", help="capcut: chờ CapCut tắt rồi ghi danh sách dự án")
    s.add_argument("--capcut", help="new: co | khong — CÓ / KHÔNG dùng CapCut (bắt buộc chốt với Sếp trước khi edit)")
    s.set_defaults(fn=cmd_edit)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
