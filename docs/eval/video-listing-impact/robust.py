import sys, re, math; sys.stdout.reconfigure(encoding="utf-8")
src=open("final.py", encoding="utf-8").read().split('report("vs cùng ngành')[0]
exec(src)
def did(T,C,PRE,POST):
    npre=(PRE[1]-PRE[0]).days+1; npost=(POST[1]-POST[0]).days+1
    tp,tq,cp,cq=tot(T,PRE),tot(T,POST),tot(C,PRE),tot(C,POST)
    g=lambda f:((tq[f]/npost)/(tp[f]/npre))/((cq[f]/npost)/(cp[f]/npre))-1
    cr=(tq["ord"]/tq["uv"])/(tp["ord"]/tp["uv"])/((cq["ord"]/cq["uv"])/(cp["ord"]/cp["uv"]))-1
    return f"UV {g('uv'):+.0%} | đơn {g('ord'):+.0%} | doanh số {g('sales'):+.0%} | CR {cr:+.0%}"
P=(dt.date(2026,10,12),dt.date(2026,10,19))
print("post 22-25        :", did(T,C,P,(dt.date(2026,10,22),dt.date(2026,10,25))))
print("post 22-24 (bỏ 25):", did(T,C,P,(dt.date(2026,10,22),dt.date(2026,10,24))))
print("post 21-24        :", did(T,C,P,(dt.date(2026,10,21),dt.date(2026,10,24))))
for drop in ["25075915554","42379971521","24519926142"]:
    T2=[k for k in T if k[1]!=drop]
    print(f"bỏ {drop}  :", did(T2,C,P,(dt.date(2026,10,22),dt.date(2026,10,25))))
T3=[k for k in T if k[1] not in ("25075915554","42379971521")]
print("bỏ cả 2 listing top:", did(T3,C,P,(dt.date(2026,10,22),dt.date(2026,10,25))), "| bỏ 25/10:", did(T3,C,P,(dt.date(2026,10,22),dt.date(2026,10,24))))
# family kệ nhà tắm dán tường (cùng SKU giá 130k): treated vs untreated siblings
fam_t=[k for k in T if k[1] in ("25075915554","9235734302","43568211253","27642545401","44172762471")]
fam_c=[k for k in data if k[1] in ("9664441853","29921593494","42619128590","42772762687")]
print("HỌ kệ nhà tắm: có video vs anh em không video:", did(fam_t,fam_c,P,(dt.date(2026,10,22),dt.date(2026,10,25))))
mt=[k for k in T if k[1] in ("24519926142","44422762378","42771265985","41122758324")]
mc=[k for k in data if k[1] in ("41914999580",)]
print("HỌ thanh móc sau cửa: có video vs anh em:", did(mt,mc,P,(dt.date(2026,10,22),dt.date(2026,10,25))))
# daily per listing top
for it in ["25075915554","42379971521","9235734302","43568211253","24519926142","44422762378"]:
    k=[k for k in data if k[1]==it][0]
    print(it, [int(data[k].get(dt.date(2026,10,d),{}).get("uv",0)) for d in range(12,26)], "ord", [int(data[k].get(dt.date(2026,10,d),{}).get("ord",0)) for d in range(12,26)])
