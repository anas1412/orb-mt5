import csv, os, statistics, math, random
from mt5paths import COMMON as D
random.seed(2222)
def pr(Rs,t,md,paths=25000):
    ok=0;dd=[]
    for _ in range(paths):
        eq=100.0;n=0
        while n<2000:
            n+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and n>=md: ok+=1;dd.append(n);break
    return 100*ok/paths,(statistics.median(dd) if dd else 0)
CFG=[("13:15 UTC  RR1  SL 100% (full range)","ny_1315_rr1"),
     ("13:15 UTC  RR2  SL  50% (midpoint)  ","ny_1315_rr2"),
     ("15:30 UTC  RR1  SL 100% (full range)","ny_1530_rr1"),
     ("15:30 UTC  RR2  SL  50% (midpoint)  ","ny_1530_rr2")]
DAYS26=163.0
print("MT5 REAL TICKS -- New York variants, XAUUSD, Friday INCLUDED, close-position filter OFF")
print("stop move +0.5R -> -0.5R, 60-min hold, 2%% risk, 2026 only\n")
print("  config                                  n     EV      +/-SE    WR      sd(R)  total R   pass both  ~days")
for lab,f in CFG:
    p=os.path.join(D,f+".csv")
    if not os.path.exists(p): print("  %s  MISSING" % lab); continue
    rows=[r for r in csv.DictReader(open(p)) if r['entry_time'][:4]=='2026']
    R=[float(r['R']) for r in rows]
    if len(R)<10: print("  %s  only %d trades" % (lab,len(R))); continue
    ev=sum(R)/len(R); se=statistics.pstdev(R)/math.sqrt(len(R))
    w=100.0*len([x for x in R if x>0])/len(R)
    p1,m1=pr(R,8,3); p2,m2=pr(R,5,3); freq=len(R)/DAYS26
    print("  %s  %3d   %+.3f   %.3f  %4.1f%%   %.2f   %+7.2f    %5.1f%%     %3.0f"
          % (lab,len(R),ev,se,w,statistics.pstdev(R),sum(R),p1*p2/100,(m1+m2)/max(freq,.01)))
print("\n  for reference, the live Asia configuration (Mon-Thu, close-pos filter on):")
rows=[r for r in csv.DictReader(open(os.path.join(D,"final_nofriday.csv"))) if r['entry_time'][:4]=='2026']
R=[float(r['R']) for r in rows]
p1,m1=pr(R,8,3); p2,m2=pr(R,5,3)
print("  Asia 00:00 UTC  RR2  SL 50%%             %3d   %+.3f   %.3f  %4.1f%%   %.2f   %+7.2f    %5.1f%%     %3.0f"
      % (len(R),sum(R)/len(R),statistics.pstdev(R)/math.sqrt(len(R)),
         100.0*len([x for x in R if x>0])/len(R),statistics.pstdev(R),sum(R),
         p1*p2/100,(m1+m2)/max(len(R)/130.0,.01)))
