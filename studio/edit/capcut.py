"""Xuất job dựng (edit.json) thành BẢN NHÁP CapCut desktop để dựng viên sửa tiếp trên timeline (thử 05/11).

CapCut không có định dạng nhập chính thức. Bản nháp = thư mục JSON trong
%LOCALAPPDATA%\\CapCut\\User Data\\Projects\\com.lveditor.draft\\<tên>\\ (CapCut quốc tế KHÔNG mã hoá — Jianying TQ mới mã
hoá). Cách an toàn nhất (cộng đồng + đo trên máy): NHÂN BẢN đoạn/chất liệu từ bản nháp do chính CapCut tạo, chỉ thay
đường dẫn / mốc giờ / id. Khuôn trích 1 lần từ bản nháp CapCut 3.5 của Sếp → assets/capcut/templates.json; CapCut 9.8
mở bản nháp kiểu 3.5 thì tự nâng cấp (đã thấy với bản "1105").

Lớp đưa lên timeline:
  track video chính   clip GỐC cắt đúng giờ (sửa lại chỗ cắt được) + màn đen (black.mp4) cho màn chữ
  track lớp đè        mỗi khối chữ động = 1 clip nền trong suốt (đổi giờ/xoá được, KHÔNG sửa được chữ)
  track chữ           (tuỳ chọn) chữ thường của CapCut cho dòng muốn sửa trong CapCut
  track tiếng         giọng đã ghép + chuẩn −14 LUFS
"""

import copy
import json
import os
import shutil
import time
import uuid
from pathlib import Path

import cv2
import numpy as np

from studio import config, media
from studio.edit import project
from studio.edit.kinetic import Kinetic

DRAFTS = Path(os.getenv("LOCALAPPDATA", "")) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
TEMPLATES = config.ROOT / "assets" / "capcut" / "templates.json"
US = 1_000_000
ALPHA = {   # định dạng clip nền trong suốt — CapCut desktop đọc alpha định dạng nào thì phải THỬ trên máy
    "prores": (".mov", ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16"]),
    "qtrle": (".mov", ["-c:v", "qtrle", "-pix_fmt", "argb"]),
    "pngmov": (".mov", ["-c:v", "png", "-pix_fmt", "rgba"]),
    "webm": (".webm", ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30", "-auto-alt-ref", "0"]),
}


def uid() -> str:
    return str(uuid.uuid4()).upper()


def us(t: float) -> int:
    return int(round(t * US))


# ───────────────────────────── khuôn (trích 1 lần từ bản nháp CapCut thật) ─────────────────────────────
def build_templates(video_draft: str = "0321", audio_draft: str = "0320 (1)") -> Path:
    """Trích đoạn mẫu (video chính, lớp đè, chữ, tiếng) + chất liệu + chất liệu phụ nó tham chiếu → templates.json."""
    def load(name):
        return json.loads((DRAFTS / name / "draft_content.json").read_text(encoding="utf-8"))

    def pack(j, seg):
        idx = {o["id"]: (k, o) for k, v in j["materials"].items() if isinstance(v, list)
               for o in v if isinstance(o, dict) and "id" in o}
        mk, mat = idx[seg["material_id"]]
        # bỏ "effects" (hoa chữ / hiệu ứng trỏ tới cache máy cũ) — giữ phần khung bắt buộc (tốc độ, canvas, kênh tiếng…)
        refs = [{"list": idx[r][0], "obj": idx[r][1]} for r in seg["extra_material_refs"]
                if r in idx and idx[r][0] != "effects"]
        for r in refs:   # bỏ hiệu ứng vào/ra trỏ tới cache hiệu ứng của máy cũ
            if r["list"] == "material_animations":
                r["obj"] = {**r["obj"], "animations": []}
        return {"segment": seg, "material_list": mk, "material": mat, "refs": refs}

    v = load(video_draft)
    tr = {(t["type"], t.get("flag", 0)): t for t in reversed(v["tracks"])}
    a = load(audio_draft)
    aidx = {o["id"]: o for o in a["materials"]["audios"]}
    aseg = next(s for t in a["tracks"] if t["type"] == "audio" for s in t["segments"]
                if aidx.get(s["material_id"], {}).get("type") == "extract_music")
    skeleton = {k: val for k, val in v.items() if k not in ("tracks",)}
    skeleton["materials"] = {k: ([] if isinstance(val, list) else val) for k, val in v["materials"].items()}
    tpl = {"source": f"CapCut 3.5 drafts '{video_draft}' + '{audio_draft}' (trích {time.strftime('%Y-%m-%d')})",
           "skeleton": skeleton,
           "video": pack(v, tr[("video", 0)]["segments"][0]),
           "overlay": pack(v, tr[("video", 2)]["segments"][0]),
           "text": pack(v, tr[("text", 0)]["segments"][0]),
           "audio": pack(a, aseg),
           "meta": json.loads((DRAFTS / "1104" / "draft_meta_info.json").read_text(encoding="utf-8")),
           "root_entry": next(e for e in json.loads((DRAFTS / "root_meta_info.json").read_text(encoding="utf-8"))
                              ["all_draft_store"] if e.get("draft_name") == "1104")}
    TEMPLATES.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES.write_text(json.dumps(tpl, ensure_ascii=False, indent=1), encoding="utf-8")
    return TEMPLATES


class Draft:
    def __init__(self, name: str, W: int, H: int, fps: float):
        self.T = json.loads(TEMPLATES.read_text(encoding="utf-8"))
        self.d = copy.deepcopy(self.T["skeleton"])
        self.d.update(id=uid(), name=name, fps=float(fps), canvas_config={"height": H, "ratio": "original", "width": W},
                      create_time=int(time.time()), update_time=int(time.time()))
        self.name, self.W, self.H = name, W, H
        self.tracks = {}

    def track(self, key: str, kind: str, flag: int, attribute: int) -> list:
        if key not in self.tracks:
            self.tracks[key] = {"attribute": attribute, "flag": flag, "id": uid(), "is_default_name": True, "name": "",
                                "segments": [], "type": kind}
        return self.tracks[key]["segments"]

    def _seg(self, kind: str, material_patch: dict, seg_patch: dict) -> dict:
        t = self.T[kind]
        mat = copy.deepcopy(t["material"])
        mat.update(material_patch, id=uid())
        self.d["materials"].setdefault(t["material_list"], []).append(mat)
        refs = []
        for r in t["refs"]:
            o = copy.deepcopy(r["obj"])
            o["id"] = uid()
            if r["list"] == "speeds" and "speed" in seg_patch:
                o["speed"] = seg_patch["speed"]
            self.d["materials"].setdefault(r["list"], []).append(o)
            refs.append(o["id"])
        seg = copy.deepcopy(t["segment"])
        seg.update(id=uid(), material_id=mat["id"], extra_material_refs=refs, common_keyframes=[], keyframe_refs=[])
        for k, v in seg_patch.items():
            if isinstance(v, dict) and isinstance(seg.get(k), dict):
                seg[k] = {**seg[k], **v}
            else:
                seg[k] = v
        return seg

    def video(self, key: str, path: Path, info: dict, src_in: float, dur: float, at: float, speed: float = 1.0,
              scale: float = 1.0, tx: float = 0.0, ty: float = 0.0, volume: float = 0.0, overlay: bool = False,
              render_index: int = 0) -> None:
        kind = "overlay" if overlay else "video"
        seg = self._seg(kind, {"path": path.as_posix(), "material_name": path.name, "duration": us(info["duration"]),
                               "width": info["width"], "height": info["height"], "has_audio": info.get("has_audio", False),
                               "local_material_id": str(uuid.uuid4()), "type": "video"},
                        {"source_timerange": {"start": us(src_in), "duration": us(dur * speed)},
                         "target_timerange": {"start": us(at), "duration": us(dur)}, "speed": speed, "volume": volume,
                         "clip": {"scale": {"x": scale, "y": scale}, "transform": {"x": tx, "y": ty}},
                         "render_index": render_index})
        self.track(key, "video", 2 if overlay else 0, 0 if overlay else 1).append(seg)

    def audio(self, key: str, path: Path, dur_file: float, src_in: float, dur: float, at: float) -> None:
        seg = self._seg("audio", {"path": path.as_posix(), "name": path.name, "duration": us(dur_file),
                                  "local_material_id": str(uuid.uuid4()), "music_id": str(uuid.uuid4())},
                        {"source_timerange": {"start": us(src_in), "duration": us(dur)},
                         "target_timerange": {"start": us(at), "duration": us(dur)}, "speed": 1.0, "volume": 1.0})
        self.track(key, "audio", 0, 0).append(seg)

    def text(self, key: str, content: str, at: float, dur: float, ty: float, size: float = 9.0,
             visible: bool = True) -> None:
        t = self.T["text"]["material"]
        style = json.loads(t["content"])
        st = style["styles"][0]
        st.update(size=size, range=[0, len(content)])
        st["fill"] = {"content": {"solid": {"color": [1, 1, 1]}}}
        st["strokes"] = [{"content": {"solid": {"color": [0, 0, 0]}}, "width": 0.06}]
        seg = self._seg("text", {"content": json.dumps({"text": content, "styles": [st]}, ensure_ascii=False),
                                 "font_size": size, "text_color": "#FFFFFF"},
                        {"target_timerange": {"start": us(at), "duration": us(dur)}, "visible": visible,
                         "clip": {"transform": {"x": 0.0, "y": ty}, "scale": {"x": 1.0, "y": 1.0}}})
        self.track(key, "text", 0, 0).append(seg)

    def save(self, duration: float, media_files: list[Path]) -> Path:
        folder = DRAFTS / self.name
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        order = sorted(self.tracks.values(), key=lambda t: {"video0": 0, "video2": 1, "text": 2, "audio": 3}[
            t["type"] + (str(t["flag"]) if t["type"] == "video" else "")])
        for i, t in enumerate(order):
            for s in t["segments"]:
                s["track_render_index"] = i
        self.d["tracks"] = order
        self.d["duration"] = us(duration)
        body = json.dumps(self.d, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
        for fname in ("draft_content.json", "template-2.tmp"):
            (folder / fname).write_text(body, encoding="utf-8")
        now = int(time.time() * 1_000_000)
        meta = copy.deepcopy(self.T["meta"])
        meta.update(draft_fold_path=folder.as_posix(), draft_id=self.d["id"], draft_name=self.name,
                    draft_root_path=str(DRAFTS), tm_draft_create=now, tm_draft_modified=now, tm_duration=us(duration),
                    draft_cover="draft_cover.jpg", draft_materials=[{"type": 0, "value": []}],
                    draft_timeline_materials_size_=sum(p.stat().st_size for p in media_files if p.exists()))
        (folder / "draft_meta_info.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        self._register(folder, now, duration)
        return folder

    def _register(self, folder: Path, now: int, duration: float) -> None:
        """Ghi bản nháp vào danh sách màn hình chính của CapCut (root_meta_info.json; sao lưu trước khi sửa)."""
        root = DRAFTS / "root_meta_info.json"
        shutil.copy2(root, root.with_suffix(".json.gdp-backup"))
        r = json.loads(root.read_text(encoding="utf-8"))
        r["all_draft_store"] = [e for e in r["all_draft_store"] if e.get("draft_name") != self.name]
        e = copy.deepcopy(self.T["root_entry"])
        e.update(draft_cover=(folder / "draft_cover.jpg").as_posix(), draft_fold_path=folder.as_posix(),
                 draft_id=self.d["id"], draft_json_file=(folder / "draft_content.json").as_posix(),
                 draft_name=self.name, draft_root_path=DRAFTS.as_posix(), tm_draft_create=now, tm_draft_modified=now,
                 tm_duration=us(duration))
        r["all_draft_store"].insert(0, e)
        root.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")


def capcut_running() -> bool:
    import psutil
    return any((p.info.get("name") or "").lower() == "capcut.exe" for p in psutil.process_iter(["name"]))


def register(name: str) -> None:
    """Ghi (lại) bản nháp đã có vào danh sách màn hình chính. ⚠ CapCut ĐANG MỞ sẽ ghi đè root_meta_info.json và xoá
    mục mới (thấy 05/11) → chỉ ghi khi CapCut đã tắt; `vs.py edit capcut <id> --wait` tự chờ CapCut tắt rồi ghi."""
    folder = DRAFTS / name
    d = json.loads((folder / "draft_content.json").read_text(encoding="utf-8"))
    dr = Draft.__new__(Draft)
    dr.T, dr.d, dr.name = json.loads(TEMPLATES.read_text(encoding="utf-8")), d, name
    dr._register(folder, int(time.time() * 1_000_000), d.get("duration", 0) / US)


def wait_and_register(names: list[str], timeout: float = 900) -> bool:
    t0 = time.time()
    while capcut_running():
        if time.time() - t0 > timeout:
            return False
        time.sleep(2)
    time.sleep(1.5)
    for n in names:
        register(n)
    return True


# ───────────────────────────── xuất lớp ─────────────────────────────
def _block_clip(kin: Kinetic, jb: dict, b: dict, fps: float, W: int, H: int, out: Path, fmt: str) -> dict:
    """Chụp riêng 1 khối chữ (nền trong suốt) suốt vòng đời → cắt gọn vùng có chữ → clip alpha."""
    kin.load([jb])
    nw = sum(len(ln["words"]) for ln in b["lines"])
    stag = b.get("stagger") or min(0.083, 0.3 / max(1, nw - 1))   # khớp stagger() trong bộ chữ
    span = {"words": (nw - 1) * stag + 0.12, "rise": 0.33, "fade": 0.45}[b["exit"]]
    t0 = min(w["t"] for ln in b["lines"] for w in ln["words"]) - 0.08
    t1 = b["end"] + span + 0.04
    tmp = out.parent / f"_{out.stem}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    frames = []
    for k in range(int(np.ceil((t1 - t0) * fps))):
        p = tmp / f"f{k:04d}.png"
        kin.page.evaluate("t => window.KINETIC.setTime(t)", t0 + k / fps)
        kin.page.screenshot(path=str(p), omit_background=True)
        frames.append(p)
    imgs = [cv2.imread(str(p), cv2.IMREAD_UNCHANGED) for p in frames]
    a = np.max(np.stack([im[:, :, 3] for im in imgs]), axis=0)
    ys, xs = np.nonzero(a > 2)
    x0, y0 = int(max(0, xs.min() - 4)) // 2 * 2, int(max(0, ys.min() - 4)) // 2 * 2
    x1, y1 = int(min(W, xs.max() + 6)) // 2 * 2, int(min(H, ys.max() + 6)) // 2 * 2
    for p, im in zip(frames, imgs):
        cv2.imwrite(str(p), im[y0:y1, x0:x1])
    ext, args = ALPHA[fmt]
    dst = out.with_suffix(ext)
    media.run([config.FFMPEG, "-y", "-v", "error", "-framerate", str(fps), "-i", str(tmp / "f%04d.png"), *args, str(dst)])
    shutil.rmtree(tmp, ignore_errors=True)
    return {"path": dst, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0, "t0": t0, "dur": len(frames) / fps,
            "info": {"duration": len(frames) / fps, "width": x1 - x0, "height": y1 - y0}}


def export(job_id: str, name: str | None = None, until: float | None = None, formats: list[str] | None = None,
           text_lines: list[str] | None = None) -> dict:
    job = project.job_path(job_id)
    e = json.loads((job / "edit.json").read_text(encoding="utf-8"))
    # job CÓ dùng CapCut không cần render final: vị trí chữ (tỉ lệ khung), trục cảnh, tiếng đã chuẩn −14 LUFS ở bản
    # preview y như final; clip chữ vẫn chụp đủ 1080×1920 (cỡ ra của edit.json)
    rj = next((p for p in (job / "render_final.json", job / "render_preview.json") if p.exists()), None)
    if rj is None:
        raise SystemExit(f"Chưa render — chạy `vs.py edit render {job_id}` (preview) trước khi xuất CapCut")
    rep = json.loads(rj.read_text(encoding="utf-8"))
    src = project.load_sources(job)
    W, H, fps = e["out"]["w"], e["out"]["h"], e["out"]["fps"]
    T = min(e["duration"], until or e["duration"])
    out = job / "capcut"
    out.mkdir(exist_ok=True)
    name = name or f"GDP {job_id}"
    if not TEMPLATES.exists():
        build_templates()
    dr = Draft(name, W, H, fps)
    files = []

    # 1) track chính: clip gốc + màn đen
    black = out / "black.mp4"
    media.run([config.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps}:d=30",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", str(black)])
    files.append(black)
    for s in rep["shots"]:
        if s["t0"] >= T:
            break
        dur = min(s["t1"], T) - s["t0"]
        if s["kind"] == "card":
            dr.video("main", black, {"duration": 30, "width": W, "height": H}, 0.0, dur, s["t0"])
            continue
        si = src[s["src"]]
        z = float(s.get("z0", 1.0))
        fx, fy = s.get("focus", [0.5, 0.5])
        lim = max(0.0, z - 1)
        tx = max(-lim, min(lim, -(fx - 0.5) * 2 * z))
        ty = max(-lim, min(lim, (fy - 0.5) * 2 * z))
        path = (job / si["file"]).resolve()
        dr.video("main", path, si, s["s0"], dur, s["t0"], speed=float(s.get("speed", 1.0)), scale=z, tx=tx, ty=ty)
        files.append(path)

    # 2) lớp đè: mỗi khối chữ một clip alpha. Đo 05/11 trên CapCut 9.8 (Sếp xuất thử): PNG-trong-MOV + ProRes 4444
    #    giữ nền trong suốt, WebM VP9 ra KHUNG ĐEN → mặc định pngmov (nhẹ nhất ~3MB/khối).
    from studio.edit.build import _js_blocks
    js = {b["id"]: b for b in _js_blocks(e)}
    place = {p["id"]: p for p in rep["placements"]}
    fmts = formats or ["pngmov"]
    clips, lanes = [], []   # lanes[i] = mốc hết của clip cuối trên track đè i
    with Kinetic(e.get("style", "cinematic"), W, H) as kin:
        for k, b in enumerate([b for b in e["captions"] if b["first"] < T]):
            jb = {**js[b["id"]], "align": place[b["id"]]["pos"], "x": place[b["id"]]["x"], "y": place[b["id"]]["y"]}
            fmt = fmts[k % len(fmts)]
            c = _block_clip(kin, jb, b, fps, W, H, out / f"{b['id']}_{fmt}", fmt)
            fit = min(W / c["w"], H / c["h"])
            cx, cy = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
            at, dur = max(0.0, c["t0"]), min(c["dur"], T - c["t0"])
            # khối chồng giờ (khối cũ đang rút khi khối mới vào) KHÔNG được chung track: CapCut đẩy clip sau ra sau
            # clip trước → chữ trễ dồn (đo 05/11: trễ 0,7s từ giây 7,3) → xếp vào track trống đầu tiên
            lane = next((i for i, end in enumerate(lanes) if end <= at + 1e-3), len(lanes))
            if lane == len(lanes):
                lanes.append(0.0)
            lanes[lane] = at + dur
            dr.video(f"captions{lane}", c["path"], c["info"], 0.0, dur, at, scale=1 / fit,
                     tx=(cx - W / 2) / (W / 2), ty=-(cy - H / 2) / (H / 2), overlay=True, render_index=k + 1)
            files.append(c["path"])
            clips.append({"id": b["id"], "format": fmt, "file": c["path"].name, "markup": b["markup"], "track": lane})

    # 3) logo (nếu job có) = clip alpha tĩnh suốt video, không có trên màn chữ thì dựng viên tự cắt
    if e.get("logo"):
        from studio.edit.build import _logo
        lg = _logo(e, W, H)
        if lg is not None:
            arr, lx, ly = lg
            png = out / "logo.png"
            cv2.imwrite(str(png), arr)
            mov = out / "logo.mov"
            media.run([config.FFMPEG, "-y", "-v", "error", "-loop", "1", "-framerate", str(fps), "-t", f"{T:.3f}",
                       "-i", str(png), *ALPHA["pngmov"][1], str(mov)])
            h, w = arr.shape[:2]
            fit = min(W / w, H / h)
            dr.video("logo", mov, {"duration": T, "width": w, "height": h}, 0.0, T, 0.0, scale=1 / fit,
                     tx=(lx + w / 2 - W / 2) / (W / 2), ty=-(ly + h / 2 - H / 2) / (H / 2), overlay=True, render_index=900)
            files.append(mov)

    # 4) chữ thường CapCut, ẨN sẵn: mỗi khối 1 đoạn chữ đúng lời — dựng viên muốn đổi câu chữ thì bật đoạn này lên,
    #    ẩn clip chữ động tương ứng (chữ động không sửa được nội dung trong CapCut)
    for b in [b for b in e["captions"] if b["first"] < T]:
        if text_lines is not None and not any(l in b["markup"] for l in text_lines):
            continue
        words = " ".join(w["text"] for ln in b["lines"] for w in ln["words"])
        p = place[b["id"]]
        dr.text("text", words, b["first"], max(0.4, min(b["end"], T) - b["first"]), ty=-(p["y"] - 0.5) * 2,
                visible=text_lines is not None)

    # 4) tiếng: giọng đã chuẩn (lấy từ final.mp4)
    voice = out / "voice.m4a"
    media.run([config.FFMPEG, "-y", "-v", "error", "-i", str(job / rep["output"]), "-vn", "-c:a", "copy", str(voice)])
    files.append(voice)
    dr.audio("voice", voice, e["duration"], 0.0, T, 0.0)

    folder = dr.save(T, files)
    res = {"draft": str(folder), "name": name, "duration": T, "clips": clips,
           "tracks": {k: len(v["segments"]) for k, v in dr.tracks.items()}}
    (out / "export.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res
