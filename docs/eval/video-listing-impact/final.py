import sys, re, math; sys.stdout.reconfigure(encoding="utf-8")
exec(open("analyze.py", encoding="utf-8").read().split("rows = []")[0])
PRE=(dt.date(2026,10,12),dt.date(2026,10,19)); POST=(dt.date(2026,10,22),dt.date(2026,10,25))
npre=8; npost=4
SHOPS={"giadungplus_official","lteng_hcm","lteng_vn"}
cat=re.compile(r"tắm|móc|kệ|giá treo|giá để|thanh treo|treo|dán tường|cốc hút", re.I)
T=[(s,i) for s,i,u,_ in TREATED if u[:4] in ("1020","1021")]
C=[k for k in data if k[0] in SHOPS and k not in TSET and cat.search(names[k]) and agg(k,*PRE)[0]["uv"]>=8*3]
Call=[k for k in data if k[0] in SHOPS and k not in TSET and agg(k,*PRE)[0]["uv"]>=8*3]
def tot(keys,w):
    s=defaultdict(float)
    for k in keys:
        a,_=agg(k,*w)
        for f in F: s[f]+=a[f]
    return s
def report(label,T,C):
    tp,tq,cp,cq=tot(T,PRE),tot(T,POST),tot(C,PRE),tot(C,POST)
    print(f"== {label}: T={len(T)} C={len(C)}")
    for f in ["imp","clk","uv","atc","ord","sales"]:
        t=(tq[f]/npost)/(tp[f]/npre)-1; c=(cq[f]/npost)/(cp[f]/npre)-1
        print(f"  {f:5}: T {tp[f]/npre:10.1f}->{tq[f]/npost:10.1f} ({t:+.1%}) | C ({c:+.1%}) | DiD {(1+t)/(1+c)-1:+.1%}")
    for nm,a,b in [("CTR","clk","imp"),("ATC/UV","atc","uv"),("CR","ord","uv")]:
        r=lambda s: s[a]/s[b]
        # z for treated change
        p1,p2,n1,n2=r(tp),r(tq),tp[b],tq[b]
        se=math.sqrt(p1*(1-p1)/n1+p2*(1-p2)/n2)
        q1,q2=r(cp),r(cq)
        print(f"  {nm:6}: T {p1:.2%}->{p2:.2%} (z={(p2-p1)/se:+.1f}) | C {q1:.2%}->{q2:.2%} | rel DiD {(p2/p1)/(q2/q1)-1:+.1%}")
report("vs cùng ngành (nhà tắm/móc/kệ)",T,C)
report("vs toàn shop",T,Call)
big=[k for k in T if agg(k,*PRE)[0]["uv"]/8>=20]
report("chỉ listing lớn (≥20 UV/ngày) vs cùng ngành",big,C)
small=[k for k in T if k not in big]
report("listing nhỏ (<20 UV/ngày) vs cùng ngành",small,C)
# placebo: fake event, pre 12-15 vs post 16-19
PRE,POST,npre,npost=(dt.date(2026,10,12),dt.date(2026,10,15)),(dt.date(2026,10,16),dt.date(2026,10,19)),4,4
report("PLACEBO (chưa có video) 12-15 vs 16-19",T,C)
