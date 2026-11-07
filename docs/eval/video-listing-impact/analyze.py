import sys; sys.stdout.reconfigure(encoding="utf-8")
import json, datetime as dt
from collections import defaultdict

D = lambda s: dt.date(2026, int(s[:2]), int(s[2:]))
LAST = dt.date(2026, 10, 25)

# shop, item, upload VN "MMDD HH:MM", duration, vid (verified Seller API / PDP create_time)
TREATED = [
    ("giadungplus_official", "25075915554", "1020 16:41", 51),
    ("giadungplus_official", "9235734302", "1020 16:42", 51),
    ("giadungplus_official", "24519926142", "1020 23:49", 22),
    ("giadungplus_official", "51165127447", "1021 10:26", 21),
    ("giadungplus_official", "53665109125", "1021 10:26", 54),
    ("giadungplus_official", "47715129690", "1021 10:27", 50),
    ("giadungplus_official", "47015430146", "1021 10:28", 57),
    ("giadungplus_official", "42379971521", "1021 10:32", 28),
    ("giadungplus_official", "19948060117", "1025 21:53", 49),
    ("lteng_hcm", "40922770934", "1025 22:40", 49),
    ("lteng_hcm", "41122758324", "1020 23:39", 22),
    ("lteng_hcm", "42028468295", "1020 23:40", 30),
    ("lteng_hcm", "44172762471", "1020 16:43", 51),
    ("lteng_hcm", "44422762378", "1020 23:39", 22),
    ("lteng_hcm", "46762816984", "1020 23:37", 30),
    ("lteng_hcm", "49962802411", "1020 17:47", 30),
    ("lteng_hcm", "50305883331", "1020 23:38", 30),
    ("lteng_hcm", "50863927634", "1020 16:43", 51),
    ("lteng_hcm", "51512280656", "1020 23:36", 39),
    ("lteng_hcm", "51807151714", "1022 17:04", 34),
    ("lteng_vn", "24246802161", "1025 22:39", 49),
    ("lteng_vn", "27642545401", "1020 16:43", 51),
    ("lteng_vn", "42771265985", "1020 23:45", 22),
    ("lteng_vn", "43568211253", "1020 16:42", 51),
    ("lteng_vn", "45363497841", "1020 23:43", 30),
    ("lteng_vn", "47813502769", "1020 23:42", 34),
    ("lteng_vn", "51063485049", "1020 23:44", 39),
    ("lteng_vn", "51613474056", "1020 23:45", 30),
    ("lteng_vn", "53963467646", "1020 23:43", 30),
]
TSET = {(s, i) for s, i, *_ in TREATED}
F = ["imp", "clk", "uv", "atc", "ord", "units", "sales", "conf"]

perf = json.load(open("perf.json", encoding="utf-8"))["rows"]
data = {}  # (shop,item) -> {date: dict}
names = {}
for r in perf:
    k = (r["shop_name"], r["item_id"])
    names[k] = r["name"]
    days = {}
    for part in r["d"].split(";"):
        p = part.split(",")
        days[D(p[0])] = dict(zip(F, map(float, p[1:])))
    data[k] = days

old = {r["item_id"]: r for r in json.load(open("oldsnap.json", encoding="utf-8"))["rows"]}

conn = {159755: "giadungplus_official", 155938: "lteng_hcm", 159753: "lteng_vn", 155687: "phaledo", 134366: "phaledo_official"}
ads = {}
for r in json.load(open("ads.json", encoding="utf-8"))["rows"]:
    days = {}
    for part in r["d"].split(";"):
        p = part.split(",")
        days[D(p[0])] = dict(cost=float(p[1]), aimp=float(p[2]), aclk=float(p[3]))
    ads[(conn[r["connection_id"]], r["item_id"])] = days


def agg(k, start, end):
    s = defaultdict(float); n = 0
    d = start
    while d <= end:
        x = data.get(k, {}).get(d)
        if x:
            for f in F: s[f] += x[f]
        a = ads.get(k, {}).get(d)
        if a:
            for f, v in a.items(): s[f] += v
        n += 1
        d += dt.timedelta(days=1)
    return s, n


def windows(d0):
    pre = (dt.date(2026, 10, 12), d0 - dt.timedelta(days=1))
    post = (d0 + dt.timedelta(days=1), LAST)
    return pre, post


def ratio(a, b):
    return a / b if b else float("nan")


rows = []
for shop, item, up, dur in TREATED:
    d0 = dt.date(2026, int(up[:2]), int(up[2:4]))
    k = (shop, item)
    (ps, pe), (qs, qe) = windows(d0)
    if qs > qe:
        rows.append(dict(shop=shop, item=item, name=names.get(k, ""), up=up, dur=dur, post_days=0))
        continue
    pre, npre = agg(k, ps, pe)
    post, npost = agg(k, qs, qe)
    # control = other items same shop, same windows, active in pre
    cpre = defaultdict(float); cpost = defaultdict(float)
    for ck in data:
        if ck[0] != shop or ck in TSET:
            continue
        a, _ = agg(ck, ps, pe)
        if a["uv"] < 20:
            continue
        b, _ = agg(ck, qs, qe)
        for f in F: cpre[f] += a[f]; cpost[f] += b[f]
    o = old.get(item)
    rows.append(dict(
        shop=shop, item=item, name=names.get(k, ""), up=up, dur=dur, post_days=npost,
        had_old_video=(o["video_count"] if o else None),
        pre={f: pre.get(f,0) for f in F+['cost']}, post={f: post.get(f,0) for f in F+['cost']}, npre=npre, npost=npost,
        cpre=dict(cpre), cpost=dict(cpost),
    ))

json.dump(rows, open("result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def show(label, pre, post, cpre, cpost, npre, npost):
    def per(x, n): return x / n
    out = [label]
    for f in ["imp", "clk", "uv", "atc", "ord", "sales"]:
        t = ratio(per(post[f], npost), per(pre[f], npre)) - 1
        c = ratio(per(cpost[f], npost), per(cpre[f], npre)) - 1
        did = ratio(1 + t, 1 + c) - 1
        out.append(f"{f}: T {per(pre[f],npre):.1f}->{per(post[f],npost):.1f} ({t:+.0%}) | C {c:+.0%} | DiD {did:+.0%}")
    for nm, num, den in [("CTR", "clk", "imp"), ("ATC/UV", "atc", "uv"), ("CR ord/UV", "ord", "uv")]:
        out.append(f"{nm}: T {ratio(pre[num],pre[den]):.2%}->{ratio(post[num],post[den]):.2%} | C {ratio(cpre[num],cpre[den]):.2%}->{ratio(cpost[num],cpost[den]):.2%}")
    print("\n  ".join(out))


# pooled by cohort (same windows inside cohort)
cohorts = defaultdict(list)
for r in rows:
    if r["post_days"]:
        cohorts[(r["up"][:4])].append(r)
allpre = defaultdict(float); allpost = defaultdict(float); acpre = defaultdict(float); acpost = defaultdict(float)
for c, rs in sorted(cohorts.items()):
    pre = defaultdict(float); post = defaultdict(float); cp = defaultdict(float); cq = defaultdict(float)
    for r in rs:
        for f in F:
            pre[f] += r["pre"].get(f, 0); post[f] += r["post"].get(f, 0)
    # control per shop, summed once per shop
    seen = set()
    for r in rs:
        if r["shop"] in seen: continue
        seen.add(r["shop"])
        for f in F: cp[f] += r["cpre"][f]; cq[f] += r["cpost"][f]
    show(f"== cohort {c}: {len(rs)} listing, pre {rs[0]['npre']}d post {rs[0]['npost']}d", pre, post, cp, cq, rs[0]["npre"], rs[0]["npost"])

print()
for r in rows:
    if not r["post_days"]:
        print("NO-POST", r["shop"], r["item"], r["up"], r["name"][:60]); continue
    p, q = r["pre"], r["post"]
    n1, n2 = r["npre"], r["npost"]
    cu = ratio(r["cpost"]["uv"] / n2, r["cpre"]["uv"] / n1) - 1
    print(f"{r['shop'][:8]:8} {r['item']:12} {r['up']} old_vid={r['had_old_video']} | uv/d {p['uv']/n1:6.1f}->{q['uv']/n2:6.1f} ({ratio(q['uv']/n2,p['uv']/n1)-1:+.0%}, ctrl {cu:+.0%}) | imp/d {p['imp']/n1:7.0f}->{q['imp']/n2:7.0f} | CTR {ratio(p['clk'],p['imp']):.2%}->{ratio(q['clk'],q['imp']):.2%} | ord/d {p['ord']/n1:5.2f}->{q['ord']/n2:5.2f} | CR {ratio(p['ord'],p['uv']):.2%}->{ratio(q['ord'],q['uv']):.2%} | ads {p.get('cost',0)/n1/1e5:6.0f}->{q.get('cost',0)/n2/1e5:6.0f} | {r['name'][:50]}")


# ---- placebo / pre-trend: 11-15/10 vs 16-19/10, treated (cohort 20-22/10) vs control
print()
A=(dt.date(2026,10,12),dt.date(2026,10,15)); B=(dt.date(2026,10,16),dt.date(2026,10,19))
for shop in ["giadungplus_official","lteng_hcm","lteng_vn"]:
    tk=[(s,i) for s,i,u,_ in TREATED if s==shop and u[:4]!="1025"]
    ck=[k for k in data if k[0]==shop and k not in TSET and agg(k,*A)[0]["uv"]>=10]
    def tot(keys,w,f):
        return sum(agg(k,*w)[0][f] for k in keys)/((w[1]-w[0]).days+1)
    for f in ["uv","ord"]:
        t=tot(tk,B,f)/tot(tk,A,f)-1; c=tot(ck,B,f)/tot(ck,A,f)-1
        print(f"PRETREND {shop} {f}: treated {t:+.0%} control {c:+.0%}")

# ---- daily series uv & ord (treated cohort 20/21/22 vs control) per shop, index
print()
days=[dt.date(2026,10,1)+dt.timedelta(days=i) for i in range(25)]
for shop in ["giadungplus_official","lteng_hcm","lteng_vn"]:
    tk=[(s,i) for s,i,u,_ in TREATED if s==shop and u[:4]!="1025"]
    ck=[k for k in data if k[0]==shop and k not in TSET]
    line_t=[]; line_c=[]
    for d in days:
        line_t.append(sum(data[k].get(d,{}).get("uv",0) for k in tk if k in data))
        line_c.append(sum(data[k].get(d,{}).get("uv",0) for k in ck))
    print(shop,"T_uv",[int(x) for x in line_t])
    print(shop,"C_uv",[int(x) for x in line_c])
    print(shop,"T_ord",[int(sum(data[k].get(d,{}).get("ord",0) for k in tk if k in data)) for d in days])
    print(shop,"C_ord",[int(sum(data[k].get(d,{}).get("ord",0) for k in ck)) for d in days])
