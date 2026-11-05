"""Thư viện cho jobs/<id>/cut.py — Claude ghi QUYẾT ĐỊNH DỰNG ở đây, chạy ra edit.json (mẫu: tools/edit_cut_example.py).

    from studio.edit.cutlib import Cut
    c = Cut(__file__)
    c.say("vo", "Năm ngày ở Bắc Kinh", "cảnh đẹp")        # đoạn lời: từ cụm đầu → hết cụm cuối (khớp chữ đã chép)
    c.say("c08", 0.35, 1.9, frame="tight")                 # đoạn lời theo giây; clip có hình → hiện người nói
    c.cover("c11", at="Cả nhóm", until="háo hức", src_in=1.0, trans="flash")   # cảnh minh hoạ đè hình, giữ tiếng
    c.card(at="Năm ngày", until="cảnh đẹp")                # màn đen chữ (mở đầu / câu chốt)
    c.cap("!NĂM NGÀY / ở / ~BẮC KINH")                     # khối chữ: dòng cách nhau " / " (luật ở SKILL.md)
    c.save()

Thời điểm `at`/`until` của cover/card là cụm chữ trong LỜI ĐÃ DỰNG (sau khi ghép các đoạn say) hoặc số giây đầu ra.
Chữ trong cap() phải là lời đã nói (khớp lần lượt, được bỏ từ đệm); `1=một` = hiện "1" khớp lời "một";
`{chữ}` = chữ không có trong lời (QA cảnh báo).
"""

import json
import re
from pathlib import Path

from studio.edit import project
from studio.edit.asr import norm

FRAMES = {"wide": 1.0, "medium": 1.16, "tight": 1.34}   # mẫu: chặt → vừa → rộng giữa các lần quay lại người nói
AUTO_FRAMES = ["medium", "tight", "wide"]
TRANS = {"cut", "flash", "dip", "wipe"}
EXITS = {"words", "rise", "fade"}
FILLERS = {"ờ", "ừ", "ừm", "à", "ơ", "ạ", "thì", "mà", "là", "cái", "kiểu", "nhé", "nha", "á"}
EXIT_WORDS = (0.083, 0.12, 0.3)   # stagger, dur, maxTotal — khớp STYLE.exitWords trong assets/kinetic/cinematic/index.html


class CutError(ValueError):
    pass


def _seconds_or_none(v):
    return float(v) if isinstance(v, (int, float)) else None


class Cut:
    def __init__(self, cut_file: str):
        self.d = Path(cut_file).resolve().parent
        self.meta = json.loads((self.d / "meta.json").read_text(encoding="utf-8"))
        self.src = project.load_sources(self.d)
        self.pieces, self.covers, self.cards, self.caps = [], [], [], []
        self.audio_cfg = {"voice_lufs": -14.0, "music": None, "music_lufs": -30.0, "clean": True}
        self.logo_cfg = None
        self.style = "cinematic"
        self.grade_cfg = "cinematic"   # chỉnh màu như mẫu (tối viền, nén vùng sáng); None = giữ màu gốc

    # ───────────────────────── lời (trục thời gian chính) ─────────────────────────
    def _words(self, key: str) -> list[dict]:
        if key not in self.src:
            raise CutError(f"Không có nguồn '{key}' (có: {', '.join(self.src)})")
        return project.words(self.d, key, self.src)

    def _find(self, ws: list[dict], phrase: str, after: float = -1.0, last: bool = False) -> tuple[int, int]:
        toks = [norm(t) for t in phrase.split() if norm(t)]
        keys = [norm(w["w"]) for w in ws]
        for i in range(len(ws) - len(toks) + 1):
            if ws[i]["start"] >= after - 0.01 and keys[i:i + len(toks)] == toks:
                return i, i + len(toks) - 1
        near = " ".join(w["w"] for w in ws if w["start"] >= after - 0.01)[:160]
        raise CutError(f"Không thấy cụm '{phrase}' (sau {after:.2f}s). Lời phía sau: {near}")

    def say(self, key: str, a, b=None, *, frame=None, push: float = 0.0, focus=None,
            tighten: float | None = 0.35, pad: tuple[float, float] = (0.05, 0.10)):
        """Thêm một đoạn lời vào trục chính. a/b = cụm chữ (đầu / cuối đoạn) hoặc giây trong nguồn.
        tighten = cắt khoảng lặng giữa đoạn dài hơn X giây (giữ 0,12s) như mẫu nói liền ~4 âm tiết/giây; None = giữ nguyên.
        frame = "wide"|"medium"|"tight"|số zoom (chỉ nguồn có hình); push = zoom thêm dần trong đoạn (mẫu mở đầu +0,14)."""
        ws = self._words(key)
        dur = self.src[key]["duration"]
        if isinstance(a, str):
            prev = [p for p in self.pieces if p["src"] == key]
            after = prev[-1]["out"] - 0.05 if prev else -1.0
            i0, _ = self._find(ws, a, after)
            _, i1 = self._find(ws, b if isinstance(b, str) else a, ws[i0]["start"])
            t_in, t_out = ws[i0]["start"] - pad[0], ws[i1]["end"] + pad[1]
            # không cắt lẹm vào từ liền trước / liền sau
            if i0 > 0:
                t_in = max(t_in, (ws[i0 - 1]["end"] + ws[i0]["start"]) / 2)
            if i1 + 1 < len(ws):
                t_out = min(t_out, (ws[i1]["end"] + ws[i1 + 1]["start"]) / 2)
        else:
            t_in, t_out = float(a), float(b if b is not None else dur)
        t_in, t_out = max(0.0, t_in), min(dur, t_out)
        if t_out - t_in < 0.2:
            raise CutError(f"Đoạn {key} {t_in:.2f}–{t_out:.2f}s quá ngắn")
        spans = [(t_in, t_out)]
        if tighten:
            inner = [w for w in ws if w["start"] >= t_in - 0.01 and w["end"] <= t_out + 0.01]
            spans, cur = [], t_in
            for w0, w1 in zip(inner, inner[1:]):
                # giữ khoảng thở theo dấu câu: hết câu 0,25s · phẩy 0,16s · còn lại 0,12s (mẫu nói liền ~0,1–0,3s)
                keep = 0.25 if w0.get("punct", "")[-1:] in (".", "?", "!") and w0.get("punct") else \
                    0.16 if w0.get("punct", "")[-1:] in (",", ";", ":") and w0.get("punct") else 0.12
                if w1["start"] - w0["end"] > max(tighten, keep + 0.05):
                    spans.append((cur, w0["end"] + keep / 2))
                    cur = w1["start"] - keep / 2
            spans.append((cur, t_out))
        group = len({p.get("group") for p in self.pieces})
        for s0, s1 in spans:
            self.pieces.append({"src": key, "in": round(s0, 3), "out": round(s1, 3), "group": group,
                                "frame": frame, "push": push, "focus": focus})
        return self

    # ───────────────────────── hình đè / màn chữ ─────────────────────────
    def cover(self, key: str, at, until=None, *, dur: float | None = None, src_in: float = 0.0,
              trans: str = "cut", trans_out: str | None = None, push: float = 0.0, focus=(0.5, 0.5),
              fit: str = "fill", speed: float = 1.0, ambient: float = 0.0):
        """Cảnh minh hoạ / quay màn hình đè lên hình, tiếng lời vẫn chạy. at/until = cụm chữ trong lời đã dựng hoặc
        giây đầu ra; until là cụm thì hết cụm đó mới đổi cảnh. ambient = giữ tiếng gốc của cảnh (0–1, mặc định tắt)."""
        if key not in self.src or not self.src[key].get("has_video"):
            raise CutError(f"Nguồn '{key}' không có hình để làm cảnh minh hoạ")
        for t in (trans, trans_out or "cut"):
            if t not in TRANS:
                raise CutError(f"Chuyển cảnh '{t}' không có (dùng {', '.join(sorted(TRANS))})")
        self.covers.append({"src": key, "at": at, "until": until, "dur": dur, "src_in": src_in, "trans": trans,
                            "trans_out": trans_out or "cut", "push": push, "focus": list(focus), "fit": fit,
                            "speed": speed, "ambient": ambient})
        return self

    def card(self, at, until=None, *, dur: float | None = None, bg: str = "black", trans: str = "dip"):
        """Màn đen chữ (mở đầu / câu chốt): hình tối hẳn, chữ đứng giữa, dòng cũ tối đi khi dòng mới vào."""
        self.cards.append({"at": at, "until": until, "dur": dur, "bg": bg, "trans": trans})
        return self

    def cap(self, markup: str, *, exit: str = "words", pos: str = "auto", y: float | None = None,
            hold: float = 0.45, morph: bool = True):
        """Khối chữ. Dòng cách nhau " / "; đầu dòng: `!` cụm khoá IN HOA đậm · `!!` khoá nghiêng · `~` chữ mảnh to ·
        `.` dòng phụ nhỏ · không dấu = dòng đang nói; thêm `^` = tô màu nhấn (vàng). Mẫu: ".không có mặt bằng nào / !HOÀN HẢO HẾT".
        exit: words (rút từng từ) | rise (trôi lên) | fade. pos: auto | center | left | right."""
        if exit not in EXITS:
            raise CutError(f"exit '{exit}' không có (dùng {', '.join(sorted(EXITS))})")
        self.caps.append({"markup": markup, "exit": exit, "pos": pos, "y": y, "hold": hold, "morph": morph})
        return self

    def audio(self, **kw):
        """voice_lufs (−14), music (đường file hoặc None — mẫu không có nhạc), music_lufs (−30), clean (lọc + nén giọng)."""
        self.audio_cfg.update(kw)
        return self

    def grade(self, kind: str | None = "cinematic"):
        self.grade_cfg = kind
        return self

    def logo(self, shop: str, corner: str = "top-left", width_pct: float = 0.14):
        self.logo_cfg = {"shop": shop, "corner": corner, "width_pct": width_pct}
        return self

    # ───────────────────────── giải thời gian & ghi edit.json ─────────────────────────
    def _timeline(self) -> list[dict]:
        t, prev_group, n_auto = 0.0, None, -1
        for p in self.pieces:
            p["t0"] = round(t, 3)
            t += p["out"] - p["in"]
            p["t1"] = round(t, 3)
            has_v = self.src[p["src"]].get("has_video", False)
            if p["group"] != prev_group:
                n_auto += 1 if has_v else 0
                prev_group = p["group"]
            if has_v and p["frame"] is None:
                p["frame"] = AUTO_FRAMES[n_auto % len(AUTO_FRAMES)] if n_auto >= 0 else "medium"
            if has_v:
                p["zoom"] = FRAMES.get(p["frame"], p["frame"]) if not isinstance(p["frame"], (int, float)) else float(p["frame"])
        out = []
        for k, p in enumerate(self.pieces):
            for w in self._words(p["src"]):
                if w["start"] >= p["in"] - 0.02 and w["end"] <= p["out"] + 0.04:
                    t0 = p["t0"] + max(0.0, w["start"] - p["in"])
                    t1 = min(p["t1"], p["t0"] + (w["end"] - p["in"]))
                    out.append({"w": w["w"], "punct": w.get("punct", ""), "t0": round(t0, 3), "t1": round(t1, 3),
                                "p": w.get("p", 1.0), "piece": k})
        return out

    def _when(self, words: list[dict], v, after: float, end: bool = False) -> float:
        s = _seconds_or_none(v)
        if s is not None:
            return s
        i0, i1 = self._find([{"w": w["w"], "start": w["t0"], "end": w["t1"]} for w in words], v, after)
        return words[i1]["t1"] if end else words[i0]["t0"]

    def _span(self, words: list[dict], item: dict, after: float, total: float) -> tuple[float, float]:
        t0 = max(0.0, self._when(words, item["at"], after) - (0.0 if _seconds_or_none(item["at"]) is not None else 0.04))
        if item.get("until") is not None:
            t1 = self._when(words, item["until"], t0, end=True) + (0.0 if _seconds_or_none(item["until"]) is not None else 0.12)
        elif item.get("dur"):
            t1 = t0 + float(item["dur"])
        else:
            raise CutError(f"Thiếu until hoặc dur cho {item}")
        return round(t0, 3), round(min(t1, total), 3)

    def _parse(self, markup: str) -> list[dict]:
        lines = []
        for raw in [x.strip() for x in markup.split(" / ") if x.strip()]:
            m = re.match(r"^([!~.^]*)\s*(.*)$", raw)
            pre, body = m.group(1), m.group(2)
            role = "key" if "!" in pre else "big" if "~" in pre else "sub" if "." in pre else "live"
            toks = []
            for tok in body.split():
                if tok.startswith("{") and tok.endswith("}"):
                    toks.append({"text": tok[1:-1], "match": None})
                elif "=" in tok and not tok.startswith("="):
                    shown, said = tok.split("=", 1)
                    toks.append({"text": shown, "match": said})
                else:
                    toks.append({"text": tok, "match": tok})
            lines.append({"role": role, "italic": pre.count("!") >= 2, "accent": "^" in pre, "toks": toks})
        return lines

    def _captions(self, words: list[dict], cards: list[dict]) -> tuple[list[dict], list[str]]:
        blocks, warns, cur = [], [], 0
        keys = [norm(w["w"]) for w in words]
        for n, c in enumerate(self.caps):
            lines = self._parse(c["markup"])
            first_idx, last_idx = None, None
            for ln in lines:
                ln["words"] = []
                for tok in ln["toks"]:
                    if tok["match"] is None:   # chữ không có trong lời
                        t = words[last_idx]["t0"] if last_idx is not None else words[cur]["t0"]
                        ln["words"].append({"text": tok["text"], "t": t, "spoken": False})
                        warns.append(f"khối {n + 1}: '{tok['text']}' không có trong lời")
                        continue
                    want = norm(tok["match"])
                    hit = next((i for i in range(cur, min(len(words), cur + 9)) if keys[i] == want), None)
                    if hit is None:
                        ctx = " ".join(w["w"] for w in words[cur:cur + 12])
                        raise CutError(f"Khối chữ {n + 1} '{c['markup']}': không khớp '{tok['match']}' với lời. "
                                       f"Lời tiếp theo ({words[cur]['t0'] if cur < len(words) else 0:.2f}s): {ctx}")
                    skipped = [words[i]["w"] for i in range(cur, hit) if keys[i] not in FILLERS]
                    if skipped and first_idx is not None:
                        warns.append(f"khối {n + 1}: bỏ lời '{' '.join(skipped)}' giữa khối")
                    ln["words"].append({"text": tok["text"], "t": words[hit]["t0"], "t_end": words[hit]["t1"],
                                        "spoken": True, "said": words[hit]["w"]})
                    first_idx = hit if first_idx is None else first_idx
                    last_idx, cur = hit, hit + 1
                del ln["toks"]
            if first_idx is None:
                raise CutError(f"Khối chữ {n + 1} không có chữ nào khớp lời")
            t_first = words[first_idx]["t0"]
            card = next((k for k, cd in enumerate(cards) if cd["t0"] - 0.05 <= t_first < cd["t1"]), None)
            # dòng đang nói đứng trước cụm khoá → co thành dòng dẫn nhỏ khi cụm khoá bắt đầu (mẫu 17,1s)
            if c["morph"] and card is None:
                kpos = next((i for i, ln in enumerate(lines) if ln["role"] == "key"), None)
                if kpos:
                    for ln in lines[:kpos]:
                        if ln["role"] == "live":
                            ln["morph_at"] = lines[kpos]["words"][0]["t"] - 0.06
            blocks.append({"id": f"b{n + 1:02d}", "lines": lines, "exit": c["exit"], "pos": c["pos"],
                           "y": c["y"], "hold": c["hold"], "card": card is not None, "card_idx": card,
                           "first": t_first, "last_end": words[last_idx]["t1"], "markup": c["markup"]})
        # mốc bắt đầu RÚT chữ: giữ đọc `hold` giây sau từ cuối, nhưng rút xong trước khối sau vào
        for k, b in enumerate(blocks):
            nxt = blocks[k + 1]["first"] - 0.06 if k + 1 < len(blocks) else 1e9
            nw = sum(len(ln["words"]) for ln in b["lines"])
            span = (min((nw - 1) * EXIT_WORDS[0], EXIT_WORDS[2]) + EXIT_WORDS[1] if b["exit"] == "words"
                    else 0.33 if b["exit"] == "rise" else 0.45)
            end = min(b["last_end"] + b["hold"], nxt - span - 0.02)
            if b["exit"] == "words" and end < b["last_end"] + 0.12:   # không đủ chỗ → rút nhanh hơn
                room = max(0.18, nxt - b["last_end"] - 0.12)
                b["stagger"] = round(max(0.02, (room - EXIT_WORDS[1]) / max(1, nw - 1)), 3)
                end = b["last_end"] + 0.1
            b["end"] = round(max(end, b["last_end"] + 0.05), 3)
        return blocks, warns

    def save(self) -> dict:
        if not self.pieces:
            raise CutError("Chưa có đoạn lời nào (c.say)")
        words = self._timeline()
        total = self.pieces[-1]["t1"]
        cards, after = [], -1.0
        for cd in self.cards:
            t0, t1 = self._span(words, cd, after, total)
            cards.append({**cd, "t0": t0, "t1": t1})
            after = t0
        covers, after = [], -1.0
        for cv in self.covers:
            t0, t1 = self._span(words, cv, after, total)
            covers.append({**cv, "t0": t0, "t1": t1})
            after = t0
        # khe ngắn (≤0,6s, thường là khoảng thở cuối câu) giữa 2 lớp hình đè → kéo lớp trước tới lớp sau, khỏi chớp hình nền
        layers = sorted(cards + covers, key=lambda x: x["t0"])
        for x, y in zip(layers, layers[1:]):
            if 0 < y["t0"] - x["t1"] <= 0.6:
                x["t1"] = y["t0"]
        blocks, warns = self._captions(words, cards)
        # nguồn chỉ có tiếng (giọng đọc riêng) mà không có cảnh đè → màn đen: báo lỗi trước khi render
        holes = []
        for p in self.pieces:
            if self.src[p["src"]].get("has_video"):
                continue
            t = p["t0"]
            for a, b in sorted((x["t0"], x["t1"]) for x in covers + cards):
                if a > t + 0.04 and a < p["t1"]:
                    holes.append((t, min(a, p["t1"])))
                if b > t:
                    t = max(t, b)
            if t < p["t1"] - 0.04:
                holes.append((t, p["t1"]))
        if holes:
            raise CutError("Đoạn giọng đọc không có hình: " + ", ".join(f"{a:.2f}–{b:.2f}s" for a, b in holes)
                           + " → thêm c.cover(...) cho các khoảng này")
        edit = {"out": self.meta["out"], "style": self.style, "grade": self.grade_cfg, "duration": round(total, 3),
                "pieces": self.pieces,
                "covers": covers, "cards": cards, "captions": blocks, "words": words, "audio": self.audio_cfg,
                "logo": self.logo_cfg, "warnings": warns}
        (self.d / "edit.json").write_text(json.dumps(edit, ensure_ascii=False, indent=1), encoding="utf-8")
        self._report(edit)
        return edit

    def _report(self, e: dict) -> None:
        print(f"edit.json · {e['duration']:.2f}s · {len(e['pieces'])} đoạn lời · {len(e['covers'])} cảnh đè · "
              f"{len(e['cards'])} màn chữ · {len(e['captions'])} khối chữ")
        for p in e["pieces"]:
            fr = f" khung {p['frame']}" + (f" push+{p['push']}" if p.get("push") else "") if p.get("zoom") else ""
            print(f"  lời  {p['t0']:6.2f}–{p['t1']:6.2f}  {p['src']} {p['in']:.2f}–{p['out']:.2f}{fr}")
        for c in e["cards"]:
            print(f"  màn  {c['t0']:6.2f}–{c['t1']:6.2f}  {c['bg']} ({c['trans']})")
        for c in e["covers"]:
            print(f"  đè   {c['t0']:6.2f}–{c['t1']:6.2f}  {c['src']} từ {c['src_in']:.2f}s ({c['trans']}→{c['trans_out']})")
        for b in e["captions"]:
            print(f"  chữ  {b['first']:6.2f}–{b['end']:6.2f}  {b['markup']}" + ("  [màn chữ]" if b["card"] else ""))
        for w in e["warnings"]:
            print(f"  ⚠ {w}")
