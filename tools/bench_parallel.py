"""Đo tài nguyên khi chạy N lệnh vs.py song song (vd 3 render): thời gian, RAM đỉnh (tổng tiến trình con), CPU.
Chạy: python tools/bench_parallel.py render gdp-ke-nha-tam-01 lteng-vn-ke-nha-tam-01 lteng-hcm-ke-nha-tam-01"""

import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
cmd, jobs = sys.argv[1].split(), sys.argv[2:]  # vd "render --final"
py = sys.executable
psutil.cpu_percent(None)
t0 = time.time()
procs = [subprocess.Popen([py, str(ROOT / "vs.py"), cmd[0], j, *cmd[1:]], cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT) for j in jobs]
peak_rss, cpu_samples = 0, []
while any(p.poll() is None for p in procs):
    rss = 0
    for p in procs:
        try:
            root = psutil.Process(p.pid)
            for q in [root] + root.children(recursive=True):
                rss += q.memory_info().rss
        except psutil.Error:
            pass
    peak_rss = max(peak_rss, rss)
    cpu_samples.append(psutil.cpu_percent(None))
    time.sleep(0.3)
dt = time.time() - t0
for j, p in zip(jobs, procs):
    out = p.stdout.read().decode("utf-8", "replace").strip().splitlines()
    print(f"{j}: exit {p.returncode} · {out[0] if out else ''}")
vm = psutil.virtual_memory()
print(f"N={len(jobs)} · {dt:.1f}s · RAM đỉnh (tiến trình con) {peak_rss / 2**30:.2f} GB · CPU đỉnh {max(cpu_samples or [0]):.0f}% "
      f"trung bình {sum(cpu_samples) / max(1, len(cpu_samples)):.0f}% · máy {psutil.cpu_count()} luồng, RAM {vm.total / 2**30:.1f} GB")
