import csv, os, glob, statistics, math, random
random.seed(1313)
from mt5paths import COMMON as D
def pr(Rs,t,md,paths=20000):
    ok=0;dd_=[]
    for _ in range(paths):
        eq=100.0;dd=0
        while dd<1500:
            dd+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and dd>=md: ok+=1;dd_.append(dd);break
    return 100*ok/paths,(statistics.median(dd_) if dd_ else 0)
print("MT5 REAL TICKS -- range 00:00-00:14, entries 00:15-00:29, SL midpoint, 60-min hold, 2% risk")
print("session times resolved by TimeZones.mqh (TZ_UTC / TZ_LONDON / TZ_NEWYORK)\n")
print("  session    RR   move   n(2026)   EV 2026   +/-SE    WR     pass both  days   EV all   2024     2025")
for name in ("Asia","London","NewYork"):
    for rr in ("1.0","2.0"):
        for mv in ("on","off"):
            f=os.path.join(D,"mt5_%s_rr%s_%s.csv"%(name,rr,mv))
            if not os.path.exists(f): continue
            rows=list(csv.DictReader(open(f)))
            for r in rows: r['R']=float(r['R']); r['y']=r['entry_time'][:4]
            R26=[r['R'] for r in rows if r['y']=='2026']
            Rall=[r['R'] for r in rows]
            if len(R26)<20: continue
            ev=sum(R26)/len(R26); se=statistics.pstdev(R26)/math.sqrt(len(R26))
            p1,m1=pr(R26,8,3); p2,m2=pr(R26,5,3); freq=len(R26)/163.0
            per={y:[r['R'] for r in rows if r['y']==y] for y in ('2024','2025')}
            print("  %-9s  %s  %-4s   %3d     %+.3f   %.3f  %4.1f%%    %5.1f%%    %3.0f   %+.3f  %+.3f  %+.3f"
                  % (name,rr,mv,len(R26),ev,se,100.0*len([x for x in R26 if x>0])/len(R26),
                     p1*p2/100,(m1+m2)/max(freq,.01),sum(Rall)/len(Rall),
                     sum(per['2024'])/len(per['2024']),sum(per['2025'])/len(per['2025'])))
    print()
