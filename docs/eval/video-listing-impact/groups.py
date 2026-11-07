import sys, re; sys.stdout.reconfigure(encoding="utf-8")
exec(open("analyze.py", encoding="utf-8").read().split("rows = []")[0])
import unicodedata
def norm(s): return unicodedata.normalize("NFC", s).lower()
for k in sorted(data, key=lambda k: names[k]):
    pre,_=agg(k,dt.date(2026,10,12),dt.date(2026,10,20)); post,_=agg(k,dt.date(2026,10,21),dt.date(2026,10,25))
    if pre["uv"]/9 < 3 and post["uv"]/5 < 3: continue
    mark = "*" if k in TSET else " "
    print(f"{mark} {k[0][:10]:10} {k[1]:12} uv {pre['uv']/9:6.1f}->{post['uv']/5:6.1f} ord {pre['ord']/9:5.1f}->{post['ord']/5:5.1f} | {names[k][:70]}")
