"""Hiệu ứng ô chữ (Sếp 20/10): xuất hiện (in), chuyển giữa các nhãn, biến mất — KHÔNG được để lộ chữ Trung.

Luật che phủ:
- Ô che chữ Trung VÀO SỚM `lead` giây (mặc định 0,25s) → lúc chữ Trung hiện, ô đã đục 100%. Ô bắt đầu ở ~0s (chữ Trung có
  ngay từ khung đầu) KHÔNG có hiệu ứng vào (không thể làm mà không lộ).
- Chuyển nhãn cùng chỗ: nhãn mới vào đè LÊN nhãn cũ (nhãn cũ vẫn đục tới khi hết) — không mờ chéo cả hai (giữa chừng mỗi
  ô ~50% đục → lộ ~25% chữ Trung). Morph co giãn khung: chưa làm (dựng nhiều khung trung gian, lợi ích nhỏ).
- Biến mất mờ dần SAU khi chữ Trung đã tắt; nếu ngay sau có nhãn khác đè cùng chỗ thì tắt gọn (nhãn mới đã che).
"""

LEAD = 0.25     # thời gian hiệu ứng vào
FADE_OUT = 0.18
DEFAULT_ANIM = {"caption": "slide-up", "hook": "pop", "badge": "pop", "info": "slide-up",
                "lower-third": "slide-right", "callout-left": "pop", "callout-right": "pop"}


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
