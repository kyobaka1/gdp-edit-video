"""Hiệu ứng ô chữ (Sếp 20/10): xuất hiện (in), chuyển giữa các nhãn, biến mất — KHÔNG được để lộ chữ Trung.

Luật che phủ:
- Ô che chữ Trung VÀO SỚM `lead` giây (mặc định 0,25s) → lúc chữ Trung hiện, ô đã đục 100%. Ô bắt đầu ở ~0s (chữ Trung có
  ngay từ khung đầu) KHÔNG có hiệu ứng vào (không thể làm mà không lộ).
- Chuyển nhãn cùng chỗ: nhãn mới vào đè LÊN nhãn cũ (nhãn cũ vẫn đục tới khi hết) — không mờ chéo cả hai (giữa chừng mỗi
  ô ~50% đục → lộ ~25% chữ Trung). Morph co giãn khung: chưa làm (dựng nhiều khung trung gian, lợi ích nhỏ).
- Biến mất mờ dần SAU khi chữ Trung đã tắt; nếu ngay sau có nhãn khác đè cùng chỗ thì tắt gọn (nhãn mới đã che).
"""

from pathlib import Path

LEAD = 0.25     # thời gian hiệu ứng vào
FADE_OUT = 0.18
DEFAULT_ANIM = {"caption": "slide-up", "hook": "pop", "badge": "pop", "info": "slide-up",
                "lower-third": "slide-right", "callout-left": "pop", "callout-right": "pop"}

# Chữ hiện dần + khối nhấn (Sếp 29/10, học từ skill brag). NỀN ô vẫn vào/che y như trên — chỉ CHỮ bên trong hiện
# lần lượt, nên luật che chữ Trung không đổi. Đọc trước, nhịp sau: hiện dần bị rút/bỏ nếu ăn vào thời gian đọc.
STEP = 0.09          # mỗi bước hiện thêm chữ
REVEAL_MAX = 0.7     # cả câu hiện xong trong tối đa 0,7s
PUNCH = 0.12         # khối nhấn "bật" phóng 1,08× rồi về cỡ thường
READ_PER_SYL = 0.25  # thời gian đọc: 0,25s / âm tiết (≈4 âm tiết/giây), tối thiểu 0,8s — tính từ lúc đủ chữ
READ_MIN = 0.8
NO_REVEAL = {"badge", "callout-left", "callout-right"}  # nhãn ngắn: bật cả khối là đủ


def read_floor(text: str) -> float:
    n = len(text.replace("*", " ").split())
    return max(READ_MIN, READ_PER_SYL * n) if n else 0.0


def reveal_steps(units: list[bool]) -> list[int]:
    """Số khối hiện sau mỗi bước: từng chữ (câu dài thì 2–3 chữ/bước); khối nhấn luôn là một bước riêng."""
    n = len(units)
    g = 1 if n <= 6 else 2 if n <= 12 else 3
    steps, k = [], 0
    while k < n:
        nxt = k + 1 if units[k] else min(n, k + g)
        nxt = next((i for i in range(k + 1, nxt) if units[i]), nxt)
        steps.append(nxt)
        k = nxt
    return steps


def schedule(it: dict) -> None:
    """Sau plan_layers: lịch ảnh cho lớp có `fx` (ảnh từng bước) → it["seq"] = [(png, giây)…] phủ s0..e1,
    it["full_at"] (lúc đủ chữ), it["punch_at"] (các mốc khối nhấn bật)."""
    it["full_at"], it["punch_at"] = it["s0"] + (LEAD if it["anim_in"] != "none" else 0.0), []
    fx = it.get("fx")
    if not fx:
        return
    shots, punch = fx["shots"], fx["punch"]
    t0 = it["s0"] + (LEAD * 0.6 if it["anim_in"] != "none" else 0.0)  # ô gần vào xong mới hiện chữ
    n = len(shots) - 1
    total = 0.0
    if fx.get("reveal") and n > 1:
        total = min(REVEAL_MAX, STEP * n, it["end"] - t0 - it["floor"] - PUNCH * len(punch))
        total = total if total >= 0.2 else 0.0  # không đủ chỗ → hiện cả câu ngay (đọc quan trọng hơn hiệu ứng)
    seq, t = [], it["s0"]
    it["revealed"] = bool(total)
    if total:
        dt = total / n
        seq.append((shots[0], t0 - t))
        t = t0
        for j in range(1, n + 1):
            if j in punch:
                seq.append((punch[j], PUNCH))
                it["punch_at"].append(round(t, 3))
                t += PUNCH
            seq.append((shots[j], dt))
            t += dt
    else:  # không đủ chỗ hiện dần: ô vào với nền TRỐNG rồi mới ra cả câu (brag: "cũ ra rồi mới vào" — mờ chéo
        # hai ô đầy chữ thành một khung nhoè); có khối nhấn thì bật một nhịp
        if t0 > t:
            seq.append((shots[0], t0 - t))
            t = t0
        if fx.get("punch_full"):
            seq.append((fx["punch_full"], PUNCH))
            it["punch_at"].append(round(t, 3))
            t += PUNCH
        if not seq:
            return
    rest = max(0.04, it["e1"] - t)  # ảnh đủ chữ giữ tới hết lớp
    if seq[-1][0] == shots[n]:
        seq[-1] = (shots[n], seq[-1][1] + rest)
    else:
        seq.append((shots[n], rest))
    it["seq"] = seq
    it["full_at"] = round(max(it["full_at"], t), 3)


def _iou(a: tuple, b: tuple) -> float:
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union else 0.0


def plan_layers(items: list[dict]) -> None:
    """Gắn khung giờ hiển thị thật cho từng lớp: items có x,y,w,h,start,end,covers(bool),anim.
    Ghi thêm: s0 (bắt đầu hiện), e1 (hết hẳn), anim_in (có hiệu ứng vào không), fade_out."""
    for it in items:
        anim = it.get("anim") or "none"
        if it["covers"]:
            can_lead = it["start"] >= LEAD + 0.05
            it["anim_in"] = anim if (anim != "none" and can_lead) else "none"
            it["s0"] = round(it["start"] - LEAD, 3) if it["anim_in"] != "none" else it["start"]
        else:  # chèn chữ mới: không có gì để che → hiệu ứng chạy từ lúc bắt đầu
            it["anim_in"], it["s0"] = anim, it["start"]
    for it in items:
        rect = (it["x"], it["y"], it["w"], it["h"])
        replaced = any(o is not it and abs(o["s0"] - it["end"]) <= 0.35 and _iou(rect, (o["x"], o["y"], o["w"], o["h"])) >= 0.3
                       for o in items)
        it["fade_out"] = not replaced
        it["e1"] = round(it["end"] + (FADE_OUT if it["fade_out"] else 0.0), 3)


def chain(k: int, prev: str, out: str, it: dict, fps: float) -> tuple[list[str], list[str]]:
    """Trả (tham số input ffmpeg, các dòng filter) cho lớp PNG `it` đặt ở input số k."""
    s0, e1, dur = it["s0"], it["e1"], max(0.04, it["e1"] - it["s0"])
    if it.get("seq"):  # chữ hiện dần / khối nhấn: chuỗi ảnh theo lịch (ffconcat) → đều khung bằng fps
        lst = Path(it["png"]).with_suffix(".ffconcat")
        rows = ["ffconcat version 1.0"]
        for png, d in it["seq"]:
            rows += [f"file '{Path(png).resolve().as_posix()}'", f"duration {d:.3f}"]
        rows.append(f"file '{Path(it['seq'][-1][0]).resolve().as_posix()}'")  # concat bỏ duration của ảnh cuối
        lst.write_text("\n".join(rows) + "\n", encoding="utf-8")
        inputs = ["-f", "concat", "-safe", "0", "-t", f"{dur:.3f}", "-i", str(lst)]
        f = [f"fps={fps}", "format=rgba"]
    else:
        inputs = ["-loop", "1", "-framerate", f"{fps}", "-t", f"{dur:.3f}", "-i", str(it["png"])]
        f = ["format=rgba"]
    x, y = str(it["x"]), str(it["y"])
    a = it["anim_in"]
    off_y, off_x = max(8, round(it["h"] * 0.35)), max(12, round(it["w"] * 0.12))
    ease = f"pow(max(0,1-(t-{s0})/{LEAD}),2)"  # 1 → 0 trong LEAD giây (ease-out)
    if a == "fade":
        f.append(f"fade=t=in:st=0:d={LEAD}:alpha=1")
    elif a == "slide-up":
        f.append(f"fade=t=in:st=0:d={LEAD}:alpha=1")
        y = f"{it['y']}+{off_y}*{ease}"
    elif a == "slide-right":
        f.append(f"fade=t=in:st=0:d={LEAD}:alpha=1")
        x = f"{it['x']}-{off_x}*{ease}"
    elif a == "pop":
        f.append(f"fade=t=in:st=0:d={LEAD * 0.6:.3f}:alpha=1")
        f.append(f"scale=w='trunc(iw*(0.86+0.14*min(1,t/{LEAD}))/2)*2':h='trunc(ih*(0.86+0.14*min(1,t/{LEAD}))/2)*2':eval=frame")
        cx, cy = it["x"] + it["w"] / 2, it["y"] + it["h"] / 2
        x, y = f"{cx:.1f}-w/2", f"{cy:.1f}-h/2"
    if it["fade_out"]:
        f.append(f"fade=t=out:st={dur - FADE_OUT:.3f}:d={FADE_OUT}:alpha=1")
    f.append(f"setpts=PTS-STARTPTS+{s0}/TB")
    lines = [f"[{k}:v]{','.join(f)}[a{k}]",
             f"[{prev}][a{k}]overlay=x='{x}':y='{y}':eval=frame:eof_action=pass:enable='between(t,{s0},{e1})'[{out}]"]
    return inputs, lines
