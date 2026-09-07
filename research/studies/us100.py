import csv, os, statistics, math, random, datetime as dt
from mt5paths import COMMON as D
random.seed(4444)
def pr(Rs,t,md,paths=25000):
    ok=0;dd=[]
    for _ in range(paths):
        eq=100.0;n=0
        while n<2000:
            n+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and n>=md: ok+=1;dd.append(n);break
    return 100*ok/paths,(statistics.median(dd) if dd else 0)
CFG=[("RR 1  SL 100% (far side)","us100_rr1sl100"),
     ("RR 1  SL  50% (midpoint)","us100_rr1sl50"),
     ("RR 2  SL 100% (far side)","us100_rr2sl100"),
     ("RR 2  SL  50% (midpoint)","us100_rr2sl50")]
print("US100.cash -- New York cash open 09:30 local, MT5 real ticks, 2026")
print("15-min range, M1 signal, 15-min entry window, 60-min hold, stop move +0.5R -> -0.5R")
print("Friday included, close-position filter off, 2%% risk\n")
print("  config                      n     EV      +/-SE    WR      sd(R)  total R   pass both  ~days")
rowsall={}
for lab,f in CFG:
    p=os.path.join(D,f+".csv")
    if not os.path.exists(p): print("  %-26s MISSING" % lab); continue
    rows=[r for r in csv.DictReader(open(p)) if r['entry_time'][:4]=='2026']
    rowsall[lab]=rows
    R=[float(r['R']) for r in rows]
    if len(R)<10: continue
    ev=sum(R)/len(R); se=statistics.pstdev(R)/math.sqrt(len(R))
    p1,m1=pr(R,8,3); p2,m2=pr(R,5,3); freq=len(R)/163.0
    print("  %-26s %3d   %+.3f   %.3f  %4.1f%%   %.2f   %+7.2f    %5.1f%%     %3.0f"
          % (lab,len(R),ev,se,100.0*len([x for x in R if x>0])/len(R),
             statistics.pstdev(R),sum(R),p1*p2/100,(m1+m2)/max(freq,.01)))
best=max(rowsall.items(), key=lambda kv: sum(float(r['R']) for r in kv[1])/len(kv[1]))
print("\n  best config by day of week -- %s" % best[0])
NAMES=["Monday","Tuesday","Wednesday","Thursday","Friday"]
for i,nm in enumerate(NAMES):
    g=[float(r['R']) for r in best[1]
       if dt.datetime.strptime(r['entry_time'],"%Y.%m.%d %H:%M").weekday()==i]
    if not g: continue
    print("    %-10s n=%2d  EV %+.3f  WR %4.1f%%" % (nm,len(g),sum(g)/len(g),
          100.0*len([x for x in g if x>0])/len(g)))
r=rowsall.get(best[0],[])
if r:
    rng=[float(x['range_pts']) for x in r]
    sp=[float(x['spread_pts']) for x in r]
    print("\n  median range %.0f pts   median spread %.0f pts   spread as %% of risk %.1f%%"
          % (statistics.median(rng),statistics.median(sp),
             100.0*statistics.median(sp)/(statistics.median(rng)*0.5)))
