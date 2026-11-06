"""QA video dựng (skill gdp-video-edit) — phải ĐẠT hết mới giao. Đo bằng số, không nhìn cảm tính:

  lời      nguồn có lời đã đối chiếu văn bản chuẩn (kịch bản / Gemini) · từ xác suất thấp chưa đối chiếu
  cắt      không cắt giữa một từ (mép đoạn lời nằm trong từ > 30ms)
  chữ      mọi chữ là lời đã nói (cutlib cảnh báo) · không đè mặt (≤3% khối) · trong vùng an toàn TikTok
  hình     đúng cỡ/fps/thời lượng · không có khung đen ngoài màn chữ
  tiếng    cả bản −14 ±0,5 LUFS, đỉnh thật ≤ −1 dBTP
Kèm qa_sheet.jpg: mỗi khối chữ một ảnh lúc đủ chữ (soát mắt bằng Read hoặc vs.py look).
"""

import json
import re

import cv2
import numpy as np

from studio import config, media
from studio.edit import project


def _loudness(path) -> tuple[float | None, float | None]:
    out = media.subprocess.run([config.FFMPEG, "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128=peak=true",
                                "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    s = out[out.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", s)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", s)
    return (float(i.group(1)) if i else None), (float(p.group(1)) if p else None)


def run(job_id: str, final: bool = False) -> dict:
    job = project.job_path(job_id)
    e = json.loads((job / "edit.json").read_text(encoding="utf-8"))
    name = "final" if final else "preview"
    rep = json.loads((job / f"render_{name}.json").read_text(encoding="utf-8"))
    src = project.load_sources(job)
    video = job / rep["output"]
    fails, warns = [], list(e.get("warnings", []))

    # lời
    used = {p["src"] for p in e["pieces"]}
    for k in used:
        s = src[k]
        if s.get("speech", 0) > 0.5 and not s.get("reference"):
            fails.append(f"lời {k} CHƯA đối chiếu văn bản chuẩn (vs.py edit fix {job_id} {k} --hear | --text file)")
    low = [w for w in e["words"] if w.get("p", 1) < 0.45 and not src[e["pieces"][w["piece"]]["src"]].get("reference")]
    if low:
        warns.append("từ nghe chưa chắc: " + ", ".join(f"{w['w']}@{w['t0']:.1f}s" for w in low[:12]))

    # cắt giữa từ
    for p in e["pieces"]:
        for w in project.words(job, p["src"], src):
            for edge in (p["in"], p["out"]):
                if w["start"] + 0.03 < edge < w["end"] - 0.03:
                    fails.append(f"cắt giữa từ '{w['w']}' ({p['src']} {edge:.2f}s, từ {w['start']:.2f}–{w['end']:.2f})")

    # chữ
    if not rep.get("face_check", True):  # Sếp chọn không tải bộ dò mặt (05/11) → né mặt bằng soát mắt ảnh khối chữ
        warns.append(f"không dò mặt tự động — SOÁT MẮT qa_{name}.jpg: chữ đè mặt / sản phẩm thì ép pos/y trong cut.py")
    for pl in rep["placements"]:
        if pl["face_overlap"] > 0.03:
            fails.append(f"chữ {pl['id']} đè mặt {pl['face_overlap']:.0%}: {pl['markup']}")
        if pl.get("graphic_overlap", 0) > 0.05:
            warns.append(f"chữ {pl['id']} chồng tiêu đề ghim {pl['graphic_overlap']:.0%}: {pl['markup']} — ép y= thấp hơn")
        if pl["outside_safe"] > 0.01:
            fails.append(f"chữ {pl['id']} ra ngoài vùng an toàn {pl['outside_safe']:.0%}: {pl['markup']}")
    for b in e["captions"]:
        # lời nói liền (mẫu ~4 âm tiết/s) nên khối thường rút ngay khi nói xong — chỉ cảnh báo khi CỤM KHOÁ hiện < 0,45s
        keys = [ln["words"][0]["t"] for ln in b["lines"] if ln["role"] == "key"]
        if keys and b["end"] - min(keys) < 0.45:
            warns.append(f"cụm khoá {b['id']} chỉ hiện {b['end'] - min(keys):.2f}s — nên giữ lâu hơn / tách khối: {b['markup']}")

    # hình
    pr = media.probe(video)
    W, H = rep["size"]
    if (pr["width"], pr["height"]) != (W, H):
        fails.append(f"cỡ khung {pr['width']}x{pr['height']} ≠ {W}x{H}")
    if abs(pr["duration"] - e["duration"]) > 0.15:
        fails.append(f"thời lượng {pr['duration']:.2f}s ≠ {e['duration']:.2f}s")
    cards = [(c["t0"], c["t1"]) for c in e["cards"]]
    cap = cv2.VideoCapture(str(video))
    for s in rep["shots"]:
        if s["kind"] == "card":
            continue
        t = (s["t0"] + s["t1"]) / 2
        if any(a <= t < b for a, b in cards):
            continue
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if ok and float(f.mean()) < 6:
            fails.append(f"khung đen ngoài màn chữ ở {t:.2f}s ({s['kind']} {s.get('src')})")

    for g in rep.get("graphics", []):   # Scene Library: chữ trong thẻ phải vừa khung, font tiếng Việt tải được
        tq = g.get("text_qa") or {}
        if tq.get("overflow"):
            fails.append(f"chữ tràn trong đồ hoạ {g['id']} {g['t0']:.2f}s ({', '.join(tq['overflow'])}) — rút gọn title/sub")
        if tq.get("errors"):
            fails.append(f"đồ hoạ {g['id']} {g['t0']:.2f}s lỗi trang: {'; '.join(tq['errors'])[:200]}")
        for w in tq.get("warn") or []:
            warns.append(f"đồ hoạ {g['id']} {g['t0']:.2f}s: {w}")
        b = g.get("behind")
        if b:   # chữ sau người: báo quyết định + % chữ bị che (đo thật từng khung lúc render)
            if b.get("use"):
                om = b.get("occlusion_max")
                warns.append(f"đồ hoạ {g['id']} {g['t0']:.2f}s chữ SAU người — che TB {b.get('occlusion_mean') or 0:.0%}, "
                             f"tối đa {om or 0:.0%}" + (f", tự đặt y={b['y']}" if b.get("y") is not None else ""))
                if om is not None and om > 0.6:
                    fails.append(f"đồ hoạ {g['id']} {g['t0']:.2f}s: người che {om:.0%} từ khoá — đổi y/side hoặc behind=False")
            else:
                warns.append(f"đồ hoạ {g['id']} {g['t0']:.2f}s chữ TRƯỚC người: {b.get('reason')}")
                if (b.get("head_overlap") or 0) > 0.15:   # cận mặt: dời hết mức vẫn đè vùng đầu
                    warns.append(f"⛔ đồ hoạ {g['id']} {g['t0']:.2f}s vẫn ĐÈ VÙNG ĐẦU {b['head_overlap']:.0%} sau khi dời — cảnh cận "
                                 "mặt: đổi preset='micro' (chip góc) / dời sang cảnh khác / bỏ")
    for g in e.get("graphics", []):   # đồ hoạ nhoè ra phải lộ cảnh sau, không lộ nền đen
        for t in (g["t0"] + 0.5, g["t1"] - 0.08):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, f = cap.read()
            if ok and float(f.mean()) < 6:
                fails.append(f"khung đen ở {t:.2f}s (đồ hoạ {g['id']} {g['t0']:.2f}–{g['t1']:.2f}s): "
                             "dưới đoạn nhoè ra không có cảnh")
    ai = sorted({c["src"] for c in e.get("covers", []) if src.get(c["src"], {}).get("ai")})
    if ai:  # Sếp 05/11: thiếu cảnh thì tạo ảnh AI, nhưng chỉ minh hoạ bối cảnh — không thay sản phẩm thật / bằng chứng
        warns.append(f"dùng ảnh AI làm cảnh: {', '.join(ai)} — soát: chỉ minh hoạ bối cảnh/ý, KHÔNG phải sản phẩm "
                     "đang bán, KHÔNG làm bằng chứng (trước–sau, doanh thu, đánh giá)")

    # tiếng
    lufs, peak = _loudness(video)
    target = float(e["audio"].get("voice_lufs", -14.0))
    if lufs is None or abs(lufs - target) > 0.5:
        fails.append(f"độ to {lufs} LUFS (cần {target} ±0,5)")
    if peak is not None and peak > -1.0:
        fails.append(f"đỉnh thật {peak} dBTP (cần ≤ −1)")

    # ảnh soát các khối chữ lúc đủ chữ
    tiles = []
    for b in e["captions"]:
        last_t = max(w["t"] for ln in b["lines"] for w in ln["words"])
        t = min(last_t + 0.14, b["end"])   # từ cuối vừa vào xong (vào 0,16s, sớm 0,06s) = lúc đủ chữ
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        f = cv2.resize(f, (270, 480))
        cv2.putText(f, f"{b['id']} {t:.1f}s", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(f)
    for k, g in enumerate(rep.get("graphics", [])):   # đồ hoạ lúc chữ vừa vào đủ (soát: che mặt? sau người đẹp chưa?)
        tq = g.get("text_qa") or {}
        t = min(g["t1"] - 0.1, g["t0"] + (float(tq["full_at"]) + 0.3 if tq.get("full_at") else float(tq.get("land") or 0.5) + 0.12))
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        f = cv2.resize(f, (270, 480))
        cv2.putText(f, f"g{k + 1} {t:.1f}s", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1, cv2.LINE_AA)
        tiles.append(f)
    cap.release()
    sheet = None
    if tiles:
        cols = 6
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        sheet = job / f"qa_{name}.jpg"
        cv2.imwrite(str(sheet), np.vstack([np.hstack(tiles[r:r + cols]) for r in range(0, len(tiles), cols)]),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])

    res = {"ok": not fails, "fails": fails, "warnings": warns, "lufs": lufs, "true_peak": peak,
           "duration": pr["duration"], "size": [pr["width"], pr["height"]], "sheet": sheet.name if sheet else None}
    (job / f"qa_{name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res
