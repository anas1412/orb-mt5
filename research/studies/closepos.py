"""Close-position filter, MT5 real ticks, Asia session, threshold sweep."""
import csv, os, statistics, math, random
from mt5paths import COMMON as D
random.seed(4040)
def pr(Rs,t,md,paths=25000):
    ok=0;dd_=[]
    for _ in range(paths):
        eq=100.0;dd=0
        while dd<1500:
            dd+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and dd>=md: ok+=1;dd_.append(dd);break
    return 100*ok/paths,(statistics.median(dd_) if dd_ else 0)
TH=["0.00","0.10","0.20","0.25","0.35","0.50","0.75"]
rows={}
for t in TH:
    f=os.path.join(D,"cp_%s.csv"%t)
    if not os.path.exists(f): continue
    rs=list(csv.DictReader(open(f)))
    for r in rs: r['R']=float(r['R']); r['y']=r['entry_time'][:4]
    rows[t]=rs
base=len(rows["0.00"])
print("MT5 REAL TICKS -- Asia 00:00 UTC, 15min/M1, SL midpoint, RR2, move +0.5R->-0.5R, 2% risk")
print("2026 ONLY (%d trading days)\n" % 163)
print("  min close pos   trades  kept    n26   EV 2026   +/-SE    WR      sd(R)  pass both  days   fees/pass")
best=None
for t in TH:
    if t not in rows: continue
    R26=[r['R'] for r in rows[t] if r['y']=='2026']
    if len(R26)<20: continue
    ev=sum(R26)/len(R26); se=statistics.pstdev(R26)/math.sqrt(len(R26))
    p1,m1=pr(R26,8,3); p2,m2=pr(R26,5,3); both=p1*p2/100
    freq=len(R26)/163.0; days=(m1+m2)/max(freq,.01)
    print("      %s        %3d   %4.0f%%   %3d   %+.3f   %.3f  %4.1f%%   %.2f   %5.1f%%    %3.0f      %.2f"
          % (t,len(rows[t]),100.0*len(rows[t])/base,len(R26),ev,se,
             100.0*len([x for x in R26 if x>0])/len(R26),statistics.pstdev(R26),both,days,100.0/both))
print("\n  all three years, for reference:")
print("  min close pos    EV all    2024      2025      2026")
for t in TH:
    if t not in rows: continue
    per={y:[r['R'] for r in rows[t] if r['y']==y] for y in ('2024','2025','2026')}
    allR=[r['R'] for r in rows[t]]
    print("      %s        %+.3f   %+.3f   %+.3f   %+.3f"
          % (t,sum(allR)/len(allR),
             sum(per['2024'])/len(per['2024']),sum(per['2025'])/len(per['2025']),
             sum(per['2026'])/len(per['2026'])))
print("\n  what each step removes, 2026:")
prev=None
for t in TH:
    if t not in rows: continue
    ids={r['entry_time'] for r in rows[t] if r['y']=='2026'}
    if prev is not None:
        gone=[r for r in rows[prevt] if r['y']=='2026' and r['entry_time'] not in ids]
        if gone:
            g=[r['R'] for r in gone]
            print("      %s -> %s   cut %2d trades, they averaged %+.3f R" % (prevt,t,len(g),sum(g)/len(g)))
    prev, prevt = ids, t
