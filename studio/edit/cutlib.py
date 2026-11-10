"""Thư viện cho jobs/<id>/cut.py — Claude ghi QUYẾT ĐỊNH DỰNG ở đây, chạy ra edit.json (mẫu: tools/edit_cut_example.py).

    from studio.edit.cutlib import Cut
    c = Cut(__file__)
    c.style("gdp-ban-hang")                                # (tuỳ) phong cách: chữ, màu hình, nền màn chữ, theme Scene
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
        self.pieces, self.covers, self.cards, self.caps, self.graphics = [], [], [], [], []
        self.audio_cfg = {"voice_lufs": -14.0, "music": None, "music_lufs": -30.0, "clean": True}
        self.logo_cfg = None
        self.punches = []
        self.kinetic_page = "cinematic"
        self.grade_cfg = "cinematic"   # chỉnh màu như mẫu (tối viền, nén vùng sáng); None = giữ màu gốc
        self.theme_cfg = None          # theme Scene Library cả video (None = theo shop của logo)
        self.style_raw = None          # phong cách (assets/styles/<id>/style.json) — c.style()
        self._grade_set = False
        self._audio_set = set()

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

    def style(self, style_id: str):
        """Phong cách dựng (Style Pack, `vs.py styles`): kiểu chữ động, cao độ chữ, chỉnh màu, nền màn chữ (kính mờ),
        theme Scene, nhịp cắt, mức nhạc. Gọi TRƯỚC c.say(). Font + màu nhấn vẫn theo thương hiệu của c.logo(shop)."""
        from studio.edit import styles
        try:
            self.style_raw = styles.load(style_id)
        except styles.StyleError as exc:
            raise CutError(str(exc))
        if self.pieces:
            raise CutError("c.style() phải gọi trước c.say() (nhịp cắt lời theo phong cách)")
        return self

    def _style_get(self, *path, default=None):
        d = self.style_raw or {}
        for k in path:   # khoá có mặt với giá trị null = cố ý tắt (vd san-pham-thuan: tighten null = không cắt lặng)
            if not isinstance(d, dict) or k not in d:
                return default
            d = d[k]
        return d

    def say(self, key: str, a, b=None, *, frame=None, push: float = 0.0, focus=None,
            tighten: float | None | str = "style", pad: tuple[float, float] = (0.05, 0.10)):
        """Thêm một đoạn lời vào trục chính. a/b = cụm chữ (đầu / cuối đoạn) hoặc giây trong nguồn.
        tighten = cắt khoảng lặng giữa đoạn dài hơn X giây (giữ 0,12s) như mẫu nói liền ~4 âm tiết/giây; None = giữ nguyên.
        frame = "wide"|"medium"|"tight"|số zoom (chỉ nguồn có hình); push = zoom thêm dần trong đoạn (mẫu mở đầu +0,14)."""
        if tighten == "style":   # mặc định 0,35s; phong cách có thể cắt chặt hơn (mẫu m2/Blue 1: không khoảng > 0,3s)
            tighten = self._style_get("pacing", "tighten", default=0.35)
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

    def card(self, at, until=None, *, dur: float | None = None, bg: str | None = None, trans: str | None = None):
        """Màn chữ (mở đầu / câu chốt / câu tuyên bố): chữ đứng giữa, dòng cũ tối đi khi dòng mới vào.
        bg: black (màn đen) | glass (KÍNH MỜ — hình vẫn chạy, nhoè + tối, mẫu Blue 1); không ghi = theo phong cách."""
        bg = bg or self._style_get("card_bg", default="black")
        if bg not in ("black", "glass", "glass_light"):
            raise CutError(f"card bg '{bg}' không có (dùng black | glass | glass_light)")
        trans = trans or ("cut" if bg in ("glass", "glass_light") else "dip")   # kính mờ tự nhoè vào/ra 0,2s
        self.cards.append({"at": at, "until": until, "dur": dur, "bg": bg, "trans": trans})
        return self

    def theme(self, name: str):
        """Theme Scene Library cho cả video (gdp_red | phaledo_dark | phaledo_warm). Không gọi = theo shop của c.logo()."""
        self.theme_cfg = name
        return self

    def graphic(self, motion_id: str, at, until=None, *, dur: float | None = None, trans: str | None = None,
                behind=None, **params):
        """Đồ hoạ từ thư viện motion, đè lên hình, lời vẫn chạy. Scene Library (`scene-chapter-card`,
        `scene-keyword-burst`…, hồ sơ assets/scenes/<family>/scene.json): theme tự theo shop (c.logo/c.theme), preset
        micro/standard/full tự theo thời lượng at→until (không ghi until/dur = `default_dur` của hồ sơ), chuyển cảnh vào
        theo theme, `photo="lib:<id>"` = ảnh thư viện (sản phẩm phải là ảnh THẬT). at là cụm lời → hiện sớm `lead_in`
        giây (từ khoá). behind = chữ nằm SAU người ("auto" mặc định của family có hỗ trợ | True | False).
        Animation thường (vd 'cat-dan-mo-chuong'): phủ khung, ≥2,2s, vào bằng loé. params = tham số animation (title, sub,
        eyebrow, word, lead, side, y, accent, photo, bg, seed, theme, preset…); dur tự đặt; seed mặc định = số thứ tự.
        Đồ hoạ hiện thì chữ động tắt (tiêu đề đồ hoạ thay chữ) → KHÔNG viết cap() cho lời đoạn đó."""
        from studio import motionlib, scenes
        a = motionlib.get(motion_id)
        if a["problems"] or not a["enabled"]:
            raise CutError(f"animation '{motion_id}' chưa dùng được: {'; '.join(a['problems']) or a.get('disabled_reason')}")
        if trans is not None and trans not in TRANS:
            raise CutError(f"Chuyển cảnh '{trans}' không có (dùng {', '.join(sorted(TRANS))})")
        prof = scenes.for_motion(motion_id)
        auto_hold = False
        if until is None and dur is None and prof and prof.get("default_dur"):
            if isinstance(at, str) and prof.get("hold_after") is not None:
                until, auto_hold = at, True   # đứng tới hết cụm at + hold_after (từ khoá theo đúng lời, không nuốt câu sau)
            else:
                dur = float(prof["default_dur"])
        if behind not in (None, "auto", True, False):
            raise CutError(f"behind={behind!r} — dùng 'auto' | True | False")
        if behind not in (None, False) and not (prof and prof.get("behind")):
            raise CutError(f"'{motion_id}' không hỗ trợ chữ sau người (behind) — chỉ family có khai 'behind' trong scene.json")
        items = params.pop("items", None)
        if items is not None:
            if not (prof and prof.get("items")):
                raise CutError(f"'{motion_id}' không có nhãn con (items) — chỉ family khai 'items' trong scene.json")
            norm_items = []
            sided = bool(prof["items"].get("sided"))
            for it in items:
                it = (it,) if isinstance(it, str) else tuple(it)
                if sided:   # A vs B: (cụm lời | giây, 'a' | 'b', 'Ý'[, 'ghi chú'])
                    if len(it) < 3 or str(it[1]).lower() not in ("a", "b"):
                        raise CutError(f"items: mỗi ý là (cụm lời | giây, 'a'|'b', 'Ý'[, 'ghi chú']) — sai: {it!r}")
                    norm_items.append({"at": it[0], "s": str(it[1]).lower(), "x": str(it[2]),
                                       "n": str(it[3]) if len(it) > 3 and it[3] else ""})
                    continue
                if len(it) < 2:
                    raise CutError(f"items: mỗi mục là (cụm lời | giây, 'Nhãn'[, 'ghi chú']) — sai: {it!r}")
                norm_items.append({"at": it[0], "x": str(it[1]), "n": str(it[2]) if len(it) > 2 and it[2] else ""})
            items = norm_items
        layout_auto = params.get("layout") in (None, "auto") and bool(((prof or {}).get("behind") or {}).get("auto_layout"))
        if params.get("layout") == "auto":
            params.pop("layout")
        self.graphics.append({"id": motion_id, "at": at, "until": until, "dur": dur, "trans": trans, "behind": behind,
                              "auto_hold": auto_hold, "items": items, "layout_auto": layout_auto,
                              "params": {k: v for k, v in params.items() if v is not None}})
        return self

    def cap(self, markup: str, *, exit: str | None = None, pos: str = "auto", y: float | None = None,
            hold: float = 0.45, morph: bool = True):
        """Khối chữ. Dòng cách nhau " / "; đầu dòng: `!` cụm khoá IN HOA đậm · `!!` khoá nghiêng · `~` chữ mảnh to ·
        `.` dòng phụ nhỏ · không dấu = dòng đang nói; thêm `^` = tô màu nhấn (vàng). Mẫu: ".không có mặt bằng nào / !HOÀN HẢO HẾT".
        exit: words (rút từng từ) | rise (trôi lên) | fade (không ghi = theo phong cách). pos: auto | center | left | right."""
        exit = exit or self._style_get("captions", "exit", default="words")
        if exit not in EXITS:
            raise CutError(f"exit '{exit}' không có (dùng {', '.join(sorted(EXITS))})")
        self.caps.append({"markup": markup, "exit": exit, "pos": pos, "y": y, "hold": hold, "morph": morph})
        return self

    def audio(self, **kw):
        """voice_lufs (−14), music (đường file hoặc None — mẫu không có nhạc), music_lufs (−30), clean (lọc + nén giọng)."""
        self.audio_cfg.update(kw)
        self._audio_set |= set(kw)
        return self

    def grade(self, kind: str | None = "cinematic"):
        """Chỉnh màu: cinematic (mẫu vlog) | toi-vang (hạ bão hoà, tối 4 góc — mẫu m2) | sach (sáng, nhẹ viền) | None."""
        from studio.edit.build import GRADES
        if kind is not None and kind not in GRADES:
            raise CutError(f"grade '{kind}' không có (dùng {', '.join(GRADES)} | None)")
        self.grade_cfg = kind
        self._grade_set = True
        return self

    def punch(self, at, *, amp: float = 0.18, shake: float = 1.0, sfx: bool = True):
        """GIẬT (mẫu Blue 1 58,6s): đúng lúc nói cụm `at` khung zoom cận ĐỘT NGỘT (+amp, vào 0,1s có vượt nhẹ) + rung tắt
        dần 0,3s (shake = độ rung, 0 = không rung) + tiếng "bụp" khẽ; giữ cận tới lần cắt kế tiếp. ~1 lần / 8–10s."""
        self.punches.append({"at": at, "amp": float(amp), "shake": float(shake), "sfx": bool(sfx)})
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

    def _captions(self, words: list[dict], cards: list[dict],
                  skip: list[tuple[float, float]] = ()) -> tuple[list[dict], list[str]]:
        """skip = khoảng đồ hoạ phủ khung: lời trong đó không có chữ động → khối sau được nhảy qua."""
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
                    if hit is None and skip and first_idx is None:   # nhảy qua lời nằm trong đồ hoạ
                        j = cur
                        while j < len(words) and any(a - 0.05 <= words[j]["t0"] < b for a, b in skip):
                            j += 1
                        if j > cur:
                            hit = next((i for i in range(j, min(len(words), j + 9)) if keys[i] == want), None)
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
            card = next((k for k, cd in enumerate(cards) if cd["t0"] - 0.05 <= t_first < cd["t1"] - 0.25), None)
            if card is None:   # khối mới chen vào ĐUÔI màn chữ (until + giữ lại) → màn kết thúc ngay trước chữ đầu khối
                for cd in cards:   # (07/11: chữ ngoài màn bị tô kiểu màn kính sáng — xanh đậm trên footage)
                    if cd["t1"] - 0.25 <= t_first < cd["t1"] and t_first - 0.02 > cd["t0"]:
                        cd["t1"] = round(t_first - 0.02, 3)
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
        g_starts = sorted(a for a, _ in skip)
        for k, b in enumerate(blocks):
            nxt = blocks[k + 1]["first"] - 0.06 if k + 1 < len(blocks) else 1e9
            g_next = next((a for a in g_starts if a >= b["first"] + 0.05), None)   # đồ hoạ vào giữa khối cũng tính
            if g_next is not None:   # đồ hoạ phủ khung sắp vào → rút chữ xong trước đó
                nxt = min(nxt, g_next - 0.02)
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

    def _src_frame(self, ref: str, g: dict) -> str:
        """'src:<clip>@<giây>' → ảnh JPG cắt từ clip đã quay (jobs/<id>/assets/frames/) → file:/// cho trang scene."""
        from studio import media
        try:
            key, sec = ref[4:].split("@")
            sec = float(sec)
        except ValueError:
            raise CutError(f"đồ hoạ {g['id']}: ảnh '{ref}' — viết src:<clip>@<giây>, vd src:c03@13.0")
        if key not in self.src or not self.src[key].get("has_video"):
            raise CutError(f"đồ hoạ {g['id']}: ảnh '{ref}' — không có clip hình '{key}' (có: {', '.join(self.src)})")
        out = self.d / "assets" / "frames" / f"{key}_{sec:07.2f}.jpg"
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            media.extract_frame(self.d / self.src[key]["file"], sec, out, width=1080)
        return out.resolve().as_uri()

    def _scene_setup(self, graphics: list[dict], words: list[dict], total: float) -> list[str]:
        """Scene Library: theme (shop/c.theme), preset (thời lượng), phủ khung hay không, chuyển cảnh vào, ảnh lib:."""
        from studio import scenes
        from studio.edit import styles
        warns = []
        for g in graphics:
            prof = scenes.for_motion(g["id"])
            p = g["params"]
            g["scene"] = prof["id"] if prof else None
            if not prof:   # animation thường (thẻ cắt dán cũ): phủ khung, ≥2,2s, vào bằng loé
                g.pop("at_phrase", None)
                g.pop("auto_hold", None)
                g.pop("layout_auto", None)
                if g.pop("items", None):
                    raise CutError(f"'{g['id']}' không có nhãn con (items)")
                g["behind"] = False
                g["min_dur"] = 2.2
                g["trans"] = g["trans"] or "flash"
                continue
            try:
                th = (p.get("theme") or (None if self.theme_cfg else styles.prefers_theme(self.style_cfg, prof))
                      or scenes.theme_for(prof, (self.logo_cfg or {}).get("shop"), self.theme_cfg))
            except scenes.SceneError as exc:
                raise CutError(str(exc))
            if prof.get("brand_param"):   # family mới (C13+): font + màu nhấn theo thương hiệu của shop
                p.setdefault("brand", (self.style_cfg or {}).get("brand") or scenes.brand_of((self.logo_cfg or {}).get("shop"))
                             or "GIADUNGPLUS")
                acc = ((self.style_cfg or {}).get("skin") or {}).get("accent") or scenes.accent_of((self.logo_cfg or {}).get("shop"))
                if acc:
                    p.setdefault("accent", acc)
            avoid = ((self.style_cfg or {}).get("scenes") or {}).get("avoid") or []
            if prof["id"] in avoid:
                warns.append(f"đồ hoạ {g['id']}: phong cách {self.style_cfg['id']} TRÁNH '{prof['id']}' "
                             f"({((self.style_cfg or {}).get('scenes') or {}).get('why', {}).get(prof['id'], 'xem style.json')})")
            if th not in prof["themes"]:
                raise CutError(f"{prof['id']}: không có theme '{th}' (có: {', '.join(prof['themes'])})")
            if g.pop("auto_hold", False):   # until = chính cụm at (+0,12s) → đổi thành + hold_after
                g["t1"] = round(min(total, g["t1"] - 0.12 + float(prof["hold_after"])), 3)
            if p.get("preset"):
                pr = p["preset"]
            elif prof.get("preset_auto") == "content":   # tiêu đề ghim: có ghi chú → full, còn lại standard
                pr = "full" if any(it["n"] for it in g.get("items") or []) else "standard"
            else:
                pr = scenes.preset_for(prof, g["t1"] - g["t0"])
            if pr not in prof["presets"]:
                raise CutError(f"{prof['id']}: không có preset '{pr}' (có: {', '.join(prof['presets'])})")
            hid = [k for k in prof["presets"][pr].get("hides", []) if p.get(k)]
            if hid and not p.get("preset"):   # preset tự chọn mà giấu mất tham số đã ghi (micro không có lead) → nâng
                d = g["t1"] - g["t0"]
                up = next((n for n, c in prof["presets"].items() if not any(p.get(k) for k in c.get("hides", []))
                           and c["dur"][0] <= d + (prof.get("lead_in") or {}).get(n, 0.0) + 1e-6), None)
                if up:
                    pr = up
                else:
                    warns.append(f"đồ hoạ {g['id']} {g['t0']:.2f}s preset {pr} không hiện {', '.join(hid)} (đoạn quá ngắn)")
            p["theme"], p["preset"] = th, pr
            lead = (prof.get("lead_in") or {}).get(pr, 0.0)
            if lead and g.pop("at_phrase", False):   # từ khoá hiện sớm hơn lời một chút (mẫu: sớm 0,3–0,5s)…
                prev = [w["t1"] for w in words if w["t0"] < g["t0"]]
                # …nhưng không sớm hơn lúc từ liền trước nói xong (chữ động câu trước không bị cắt giữa chừng)
                g["t0"] = round(max(0.0, g["t0"] - lead, min(g["t0"], prev[-1] - 0.02) if prev else 0.0), 3)
            g.pop("at_phrase", None)
            bh = prof.get("behind")
            g["behind"] = (g.get("behind") if g.get("behind") is not None else bh.get("default", "auto")) if bh else False
            if g["behind"] and "y" in p:
                g["y_fixed"] = True   # ép y → máy không tự đặt chữ ngang đầu, chỉ đo % bị che
            g["covers"] = prof["presets"][pr].get("covers", True)
            if g["covers"]:   # thẻ phủ khung: không có chuyện chữ nằm sau người
                g["behind"] = False
                g.pop("y_fixed", None)
            pcfg = prof["presets"][pr]   # preset được ghi đè riêng (timeline micro = thanh tiến độ giữ chữ động)
            g["captions_keep"] = pcfg.get("captions", prof.get("captions")) == "keep"   # tiêu đề ghim: chữ động vẫn chạy bên dưới
            g["hide_logo"] = bool(pcfg.get("hide_logo", prof.get("hide_logo")))
            its = g.pop("items", None)
            if not its and (prof.get("items") or {}).get("required"):
                raise CutError(f"đồ hoạ {g['id']}: thiếu items=[(cụm lời | giây, 'Nhãn'[, 'ghi chú']), …] "
                               f"(xem assets/scenes/{prof['id']}/scene.json)")
            if its:
                cfg = prof.get("items") or {}
                if len(its) > cfg.get("max", 6):
                    raise CutError(f"đồ hoạ {g['id']}: {len(its)} nhãn con (tối đa {cfg.get('max', 6)})")
                out, after = [], g["t0"] - 0.6
                for k, it in enumerate(its):
                    ta = self._when(words, it["at"], after)
                    after = ta
                    rel = round(max(float(cfg.get("min_t", 0.6)), ta - float(cfg.get("lead", 0.15)) - g["t0"]), 3)   # min_t: intro được hiện từ 0s
                    last = g["t1"] - g["t0"] - float(cfg.get("tail", 0.9))   # mục phải hiện đủ lâu trước khi thẻ tan
                    if rel > last + 0.5:
                        raise CutError(f"đồ hoạ {g['id']}: nhãn con {k + 1} '{it['x']}' ở {ta:.2f}s — quá sát/ngoài khoảng "
                                       f"{g['t0']:.2f}–{g['t1']:.2f}s (kéo until ra sau hoặc bỏ mục)")
                    if rel > last:   # thiếu ≤ 0,5s → hiện sớm hơn lời một chút (mẫu: sớm 0,3–0,5s)
                        warns.append(f"đồ hoạ {g['id']} nhãn con {k + 1} '{it['x']}' hiện sớm {rel - last:.2f}s so với lời "
                                     "(sát cuối thẻ)")
                        rel = round(max(float(cfg.get("min_t", 0.6)), last), 3)
                    for key, lim in (("x", cfg.get("term_max", 22)), ("n", cfg.get("note_max", 30))):
                        if len(it[key]) > lim:
                            warns.append(f"đồ hoạ {g['id']} nhãn con {k + 1} '{it[key]}' dài {len(it[key])} ký tự (> {lim})")
                    out.append({"t": rel, "x": it["x"], "n": it["n"], **({"s": it["s"]} if "s" in it else {})})
                if pr == "micro" and not cfg.get("micro"):
                    warns.append(f"đồ hoạ {g['id']} preset micro không hiện nhãn con")
                p["items"] = json.dumps(out, ensure_ascii=False)
            for k, v in prof.get("params", {}).items():   # tham số "when": cụm lời | giây tuyệt đối → giây tính từ đầu thẻ
                if v.get("when") and p.get(k) not in (None, ""):
                    ta = self._when(words, p[k], g["t0"] - 0.6)
                    p[k] = round(min(max(0.4, ta - g["t0"]), g["t1"] - g["t0"] - 0.6), 3)
            g["min_dur"] = prof["presets"][pr]["dur"][0]
            g["trans"] = g["trans"] or (prof["themes"][th].get("trans", "flash") if g["covers"] else "cut")
            miss = [k for k, v in prof.get("params", {}).items() if v.get("required") and p.get(k) in (None, "")]
            if miss:
                raise CutError(f"đồ hoạ {g['id']}: thiếu tham số bắt buộc {', '.join(miss)} (xem assets/scenes/{prof['id']}/scene.json)")
            for k, lim in ((k, v.get("max_chars")) for k, v in prof.get("params", {}).items()):
                if lim and len(str(p.get(k, ""))) > lim:
                    warns.append(f"đồ hoạ {g['id']} {k} dài {len(str(p[k]))} ký tự (> {lim}): '{p[k]}' — rút gọn")
            for pk in [k for k in list(p) if k.startswith("photo") and not k.endswith("_v")]:
                ref = str(p[pk])
                if ref.startswith("src:"):
                    p.update({pk: self._src_frame(ref, g), f"{pk}_v": ref[4:]})
                    continue
                if not ref.startswith("lib:"):
                    continue
                try:
                    ph = scenes.photo_param(ref)
                except Exception as exc:
                    raise CutError(f"đồ hoạ {g['id']}: ảnh {ref} — {exc}")
                if ph.pop("_photo_ai", False) and prof["themes"][th].get("brand") == "PHALEDO":
                    warns.append(f"đồ hoạ {g['id']} dùng ẢNH AI {ph.get('_photo_id')} trong theme PHALEDO — chỉ được là "
                                 "bối cảnh/nguyên liệu, KHÔNG phải sản phẩm (sản phẩm = ảnh thật)")
                ph.pop("_photo_id", None)
                p.update({pk: ph["photo"], f"{pk}_v": ph["photo_v"]})
            if prof.get("proof_clip") and p.get("clip"):   # C08: clip THẬT phát trong khung (build ProofPainter)
                ref = str(p.pop("clip"))
                try:
                    key, sec = ref.split("@")
                    sec = float(sec)
                except ValueError:
                    raise CutError(f"đồ hoạ {g['id']}: clip '{ref}' — viết '<clip>@<giây bắt đầu>', vd 'c06@0.3'")
                if key not in self.src or not self.src[key].get("has_video") or self.src[key].get("still"):
                    raise CutError(f"đồ hoạ {g['id']}: clip '{key}' không phải clip hình (có: {', '.join(self.src)})")
                p.update({"poster": self._src_frame(f"src:{key}@{sec}", g), "poster_v": ref, "live": 1,
                          "media_w": self.src[key]["width"], "media_h": self.src[key]["height"]})
                g["proof_clip"] = {"src": key, "s0": sec}
                need = (g["t1"] - g["t0"]) - 0.5
                if sec + need > self.src[key]["duration"] + 0.05:
                    warns.append(f"đồ hoạ {g['id']}: clip {key} từ {sec:.1f}s chỉ còn {self.src[key]['duration'] - sec:.1f}s < "
                                 f"{need:.1f}s cần → khung cuối đứng yên")
            elif prof.get("proof_clip"):   # ảnh: ghi tỉ lệ khung cho trang dựng ô đúng hình
                ph = str(p.get("photo", ""))
                if ph.startswith("file:"):
                    from urllib.parse import unquote, urlparse
                    from PIL import Image
                    try:
                        with Image.open(unquote(urlparse(ph).path).lstrip("/")) as im:
                            p["media_w"], p["media_h"] = im.size
                    except OSError:
                        pass
            for src_k, dst_k in (prof.get("time_params") or {}).items():   # vd win_at (cụm lời chốt) → win_t (giây từ lúc vào)
                if src_k in p:
                    ta = self._when(words, p.pop(src_k), g["t0"] - 0.6)
                    rel = round(ta - g["t0"], 3)
                    if not 0 <= rel < g["t1"] - g["t0"]:
                        raise CutError(f"đồ hoạ {g['id']}: {src_k} ở {ta:.2f}s nằm ngoài {g['t0']:.2f}–{g['t1']:.2f}s")
                    p[dst_k] = rel
        return warns

    def save(self) -> dict:
        if not self.pieces:
            raise CutError("Chưa có đoạn lời nào (c.say)")
        self.style_cfg = None
        if self.style_raw:   # phong cách → cấu hình cụ thể theo shop (font / màu nhấn của thương hiệu)
            from studio.edit import styles
            self.style_cfg = styles.resolve(self.style_raw, (self.logo_cfg or {}).get("shop"))
            self.kinetic_page = self.style_cfg["page"]
            if not self._grade_set:
                self.grade_cfg = self.style_cfg["grade"]
            for k, v in (self.style_cfg.get("audio") or {}).items():
                if k not in self._audio_set:
                    self.audio_cfg[k] = v
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
        graphics, after = [], -1.0
        for k, g in enumerate(self.graphics):
            t0, t1 = self._span(words, g, after, total)
            # seed mặc định = thứ tự trong CÙNG loại đồ hoạ (thẻ chương thứ 2 = seed 2) — chèn thêm từ khoá không làm
            # đổi bố cục / mất cache các thẻ chương đã render
            seed = sum(1 for x in self.graphics[:k] if x["id"] == g["id"]) + 1
            graphics.append({"id": g["id"], "t0": t0, "t1": t1, "trans": g["trans"], "params": {"seed": seed, **g["params"]},
                             "covers": True, "behind": g.get("behind"), "at_phrase": _seconds_or_none(g["at"]) is None,
                             "auto_hold": g.get("auto_hold", False), "items": g.get("items"),
                             "layout_auto": g.get("layout_auto", False)})
            after = t0
        scene_warns = self._scene_setup(graphics, words, total)
        # khe ngắn (≤0,6s, thường là khoảng thở cuối câu) giữa 2 lớp hình đè → kéo lớp trước tới lớp sau, khỏi chớp hình nền
        layers = sorted(cards + covers + [g for g in graphics if g["covers"]], key=lambda x: x["t0"])
        for x, y in zip(layers, layers[1:]):
            if 0 < y["t0"] - x["t1"] <= 0.6:
                x["t1"] = y["t0"]
        for g in [g for g in graphics if g["covers"]]:
            # đồ hoạ RA bằng nhoè về trong suốt (0,28s cuối) → lớp hình kế tiếp phải nằm sẵn bên dưới, không thì lộ
            # khung nền (giọng đọc riêng = đen). Lớp kế bắt đầu ngay chỗ đồ hoạ hết → dời lên 0,3s, bỏ chuyển cảnh vào.
            for x in covers + cards:
                if g["t1"] - 0.05 <= x["t0"] <= g["t1"] + 0.05:
                    x["t0"], x["trans"] = round(g["t1"] - 0.3, 3), "cut"
                    if "src_in" in x:
                        x["src_in"] = max(0.0, x["src_in"] - 0.3 * x.get("speed", 1.0))
        seq = sorted([g for g in graphics if not g.get("captions_keep")], key=lambda x: x["t0"])
        pairs = list(zip(seq, seq[1:]))
        for gid in {g["id"] for g in graphics if g.get("captions_keep")}:   # thẻ ghim cùng loại nối nhau (số chương 1→2→3)
            same = sorted([g for g in graphics if g["id"] == gid], key=lambda x: x["t0"])
            pairs += list(zip(same, same[1:]))
        for x, y in pairs:   # 2 thẻ nối nhau (until cụm cuối + giữ lại) chồng giờ → thẻ trước nhường thẻ sau
            if x["t1"] > y["t0"] > x["t0"]:
                if x["t1"] - y["t0"] > 0.4:
                    scene_warns.append(f"đồ hoạ {x['id']} {x['t0']:.2f}–{x['t1']:.2f}s chồng {y['id']} "
                                       f"{x['t1'] - y['t0']:.2f}s → cắt thẻ trước tại {y['t0']:.2f}s")
                x["t1"] = y["t0"]
        for g in graphics:   # thời lượng animation = khoảng đã chốt (sau khi nối khe)
            if g["t1"] - g["t0"] < g["min_dur"] - 1e-3:
                raise CutError(f"đồ hoạ {g['id']} {g['t0']:.2f}–{g['t1']:.2f}s ngắn hơn {g['min_dur']}s"
                               + (f" (preset {g['params'].get('preset')})" if g.get("scene") else
                                  " (cần đủ giấy bay vào + đứng đọc)"))
            g["params"]["dur"] = round(g["t1"] - g["t0"], 2)
        blocks, warns = self._captions(words, cards, [(g["t0"], g["t1"]) for g in graphics if not g.get("captions_keep")])
        for g in [g for g in graphics if g.get("captions_keep")]:   # tiêu đề ghim + đồ hoạ khác cùng lúc = chồng chữ
            for o in graphics:
                if o is not g and o["t0"] < g["t1"] and o["t1"] > g["t0"] and not o.get("covers"):
                    warns.append(f"đồ hoạ {o['id']} {o['t0']:.2f}s trùng tiêu đề ghim {g['t0']:.2f}–{g['t1']:.2f}s — chồng chữ ở "
                                 "tầm đầu; dời / bỏ")
        warns += scene_warns
        for b in blocks:  # mẫu: đồ hoạ hiện thì không đặt chữ động (tiêu đề đồ hoạ thay chữ)
            for g in [g for g in graphics if not g.get("captions_keep")]:
                g_end = g["t1"] - 0.3   # build tắt chữ động t0 → t1−0,3
                if b["first"] >= g_end - 0.15 or b["end"] <= g["t0"]:
                    continue   # chỉ chạm mép (khối sau vào khi đồ hoạ đang tan) — không đáng báo
                hidden = min(b["end"], g_end) - max(b["first"], g["t0"])
                if b["first"] >= g["t0"] - 0.05 or hidden > 0.3:
                    warns.append(f"khối chữ {b['id']} trùng đồ hoạ {g['id']} {g['t0']:.2f}–{g['t1']:.2f}s — bỏ cap() "
                                 f"đoạn này: {b['markup']}")
        # nguồn chỉ có tiếng (giọng đọc riêng) mà không có cảnh đè → màn đen: báo lỗi trước khi render
        holes = []
        for p in self.pieces:
            if self.src[p["src"]].get("has_video"):
                continue
            t = p["t0"]
            for a, b in sorted((x["t0"], x["t1"]) for x in covers + cards + [g for g in graphics if g["covers"]]):
                if a > t + 0.04 and a < p["t1"]:
                    holes.append((t, min(a, p["t1"])))
                if b > t:
                    t = max(t, b)
            if t < p["t1"] - 0.04:
                holes.append((t, p["t1"]))
        if holes:
            raise CutError("Đoạn giọng đọc không có hình: " + ", ".join(f"{a:.2f}–{b:.2f}s" for a, b in holes)
                           + " → thêm c.cover(...) cho các khoảng này")
        edit = {"out": self.meta["out"], "style": self.kinetic_page, "style_pack": (self.style_cfg or {}).get("id"),
                "style_cfg": self.style_cfg, "grade": self.grade_cfg, "duration": round(total, 3),
                "pieces": self.pieces,
                "covers": covers, "cards": cards, "graphics": graphics, "captions": blocks, "words": words,
                "audio": self.audio_cfg,
                "punches": [{"t": round(self._when(words, p["at"], 0.0), 3), "amp": p["amp"], "shake": p["shake"],
                             "sfx": p["sfx"]} for p in self.punches],
                "logo": self.logo_cfg, "warnings": warns}
        (self.d / "edit.json").write_text(json.dumps(edit, ensure_ascii=False, indent=1), encoding="utf-8")
        self._report(edit)
        return edit

    def _report(self, e: dict) -> None:
        print(f"edit.json · {e['duration']:.2f}s · {len(e['pieces'])} đoạn lời · {len(e['covers'])} cảnh đè · "
              f"{len(e['cards'])} màn chữ · {len(e['captions'])} khối chữ"
              + (f" · phong cách {e['style_pack']} (màu {e['grade']})" if e.get("style_pack") else ""))
        for p in e["pieces"]:
            fr = f" khung {p['frame']}" + (f" push+{p['push']}" if p.get("push") else "") if p.get("zoom") else ""
            print(f"  lời  {p['t0']:6.2f}–{p['t1']:6.2f}  {p['src']} {p['in']:.2f}–{p['out']:.2f}{fr}")
        for c in e["cards"]:
            print(f"  màn  {c['t0']:6.2f}–{c['t1']:6.2f}  {c['bg']} ({c['trans']})")
        for c in e["covers"]:
            print(f"  đè   {c['t0']:6.2f}–{c['t1']:6.2f}  {c['src']} từ {c['src_in']:.2f}s ({c['trans']}→{c['trans_out']})")
        for g in e["graphics"]:
            print(f"  đồ hoạ {g['t0']:6.2f}–{g['t1']:6.2f}  {g['id']} " + json.dumps(
                {k: v for k, v in g["params"].items() if k != "dur"}, ensure_ascii=False)
                + (f"  [sau người: {g['behind']}]" if g.get("behind") else ""))
        for b in e["captions"]:
            print(f"  chữ  {b['first']:6.2f}–{b['end']:6.2f}  {b['markup']}" + ("  [màn chữ]" if b["card"] else ""))
        for w in e["warnings"]:
            print(f"  ⚠ {w}")
