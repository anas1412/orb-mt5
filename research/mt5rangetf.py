import csv, os, statistics, math, random
random.seed(1414)
from mt5paths import COMMON as D
def pr(Rs,t,md,paths=25000):
    ok=0;dd_=[]
    for _ in range(paths):
        eq=100.0;dd=0
        while dd<2000:
            dd+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and dd>=md: ok+=1;dd_.append(dd);break
    return 100*ok/paths,(statistics.median(dd_) if dd_ else 0)
CFG=[("15","1","15 min / M1"),("30","3","30 min / M3"),("60","5","60 min / M5")]
print("MT5 REAL TICKS -- 2026 only. RR 2.0, stop move +0.5R -> -0.5R, SL at range midpoint, 2% risk")
print("entry window and hold cap scale with the range: 15/30/60 min window, 60/120/240 min hold\n")
print("  session   range / signal   n    median range   EV      +/-SE    WR     sd(R)  pass both  days")
for name in ("Asia","NewYork"):
    for rng,tf,lab in CFG:
        f=os.path.join(D,"tf_%s_r%s_tf%s.csv"%(name,rng,tf))
        if not os.path.exists(f): continue
        rows=[r for r in csv.DictReader(open(f)) if r['entry_time'][:4]=='2026']
        R=[float(r['R']) for r in rows]
        if len(R)<20: continue
        mr=statistics.median([float(r['range_pts']) for r in rows])
        ev=sum(R)/len(R); se=statistics.pstdev(R)/math.sqrt(len(R))
        p1,m1=pr(R,8,3); p2,m2=pr(R,5,3); freq=len(R)/163.0
        print("  %-9s %-15s %3d   %8.0f    %+.3f   %.3f  %4.1f%%  %.2f   %5.1f%%    %3.0f"
              % (name,lab,len(R),mr,ev,se,100.0*len([x for x in R if x>0])/len(R),
                 statistics.pstdev(R),p1*p2/100,(m1+m2)/max(freq,.01)))
    print()
