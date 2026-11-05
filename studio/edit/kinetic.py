"""Chữ động: chạy trang HTML assets/kinetic/<style>/index.html trong Chrome ẩn (Playwright, Chrome đã cài — như
templates.py / motionlib.py), tua từng khung bằng setTime(t), chụp NỀN TRONG SUỐT vùng có chữ.
Khung không có chuyển động (chữ đứng yên) dùng lại ảnh trước → chỉ chụp lúc chữ đang vào/ra (đo: ~40–60% khung)."""

import json
from pathlib import Path

from studio import config

KINETIC = config.ROOT / "assets" / "kinetic"

_STEP = """async (t) => {
  window.KINETIC.setTime(t);
  await new Promise(r => requestAnimationFrame(() => r()));
  return [!!window.__animating, window.KINETIC.visibleBox()];
}"""


class Kinetic:
    def __init__(self, style: str, W: int, H: int):
        self.entry = KINETIC / style / "index.html"
        if not self.entry.exists():
            raise FileNotFoundError(f"Không có bộ chữ {style} ({self.entry})")
        self.W, self.H = W, H
        self.errors: list[str] = []

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(channel="chrome", headless=True)
        self.page = self._browser.new_page(viewport={"width": self.W, "height": self.H}, device_scale_factor=1)
        self.page.route("**/*", lambda r: r.abort() if r.request.url.startswith(("http://", "https://")) else r.continue_())
        self.page.on("pageerror", lambda e: self.errors.append(f"lỗi JS: {e}"))
        self.page.goto(self.entry.resolve().as_uri())
        self.page.wait_for_function("() => window.KINETIC && window.KINETIC.ready")
        bad = self.page.evaluate("""async () => { await window.KINETIC.ready;
            const f = [...document.fonts]; await Promise.allSettled(f.map(x => x.load()));
            return f.filter(x => x.status === 'error').map(x => x.family + ' ' + x.weight + ' ' + x.style); }""")
        if bad:  # Chrome thiếu font sẽ lặng lẽ thay font khác → dừng hẳn (bài học templates.py)
            raise RuntimeError(f"Font chữ động không tải được: {', '.join(bad)}")
        return self

    def __exit__(self, *exc):
        if getattr(self, "_browser", None):
            self._browser.close()
        if getattr(self, "_pw", None):
            self._pw.stop()

    def load(self, blocks: list[dict]) -> list[dict]:
        """Nạp các khối chữ (đã có x/y/align) → khung bao từng khối ở trạng thái đủ chữ."""
        data = {"W": self.W, "H": self.H, "blocks": blocks}
        boxes = self.page.evaluate("d => window.KINETIC.load(d)", json.loads(json.dumps(data)))
        if self.errors:
            raise RuntimeError("; ".join(self.errors[:3]))
        return boxes

    def frames(self, total: float, fps: float, out_dir: Path) -> list:
        """Chụp mọi khung 0..total → index[i] = (tên file, x, y) hoặc None (không có chữ). Ảnh lưu out_dir."""
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("*.png"):
            old.unlink()
        n = int(round(total * fps))
        index, last_sig, last_entry, shots = [], None, None, 0
        for i in range(n):
            t = i / fps
            anim, box = self.page.evaluate(_STEP, t)
            if not box:
                index.append(None)
                last_sig, last_entry = None, None
                continue
            sig = (box["x"], box["y"], box["w"], box["h"])
            if not anim and sig == last_sig and last_entry is not None:
                index.append(last_entry)
                continue
            name = f"k{i:05d}.png"
            self.page.screenshot(path=str(out_dir / name), omit_background=True,
                                 clip={"x": box["x"], "y": box["y"], "width": box["w"], "height": box["h"]})
            shots += 1
            last_entry = (name, box["x"], box["y"])
            last_sig = sig if not anim else None
            index.append(last_entry)
        self.captured = shots
        return index

    def still(self, t: float, out: Path) -> None:
        """Ảnh cả khung tại t (soát nhanh một khối chữ)."""
        self.page.evaluate(_STEP, t)
        self.page.screenshot(path=str(out), omit_background=True)
