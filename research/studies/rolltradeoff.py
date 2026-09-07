import statistics, random, math
from sweep import load, setups, evaluate, stats
random.seed(505)
ss, hist = setups(load(), want_history=True)
ss = [s for s in ss if s['late'] < 15]
hist.sort(); hdates=[d for d,_ in hist]; hrng=[r for _,r in hist]
idx={d:i for i,d in enumerate(hdates)}
N=20
def ratio(s):
    i=idx.get(s['date'])
    if i is None or i<N: return None
    ref=statistics.median(hrng[i-N:i])
    return (s['hi']-s['lo'])/ref if ref>0 else None
def pr(Rs,target,mindays,paths=20000):
    ok=0;days=[]
    for _ in range(paths):
        eq=100.0;d=0
        while d<1500:
            d+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+target and d>=mindays: ok+=1;days.append(d);break
    return 100*ok/paths,(statistics.median(days) if days else 0)
DAYS26=165.0
print("lookback N=20. 'days' = calendar trading days to pass both phases in 2026,")
print("accounting for days the filter sits out.\n")
print(" thresh  trades  kept%  2026 n   2026 EV  +/-SE   2026 WR  2026 pass  days  pooled EV  pooled pass")
for th in (0.0,0.9,1.0,1.1,1.2,1.25,1.3,1.4,1.5,1.75):
    keep=[s for s in ss if th==0.0 or (lambda r: r is not None and r>=th)(ratio(s))]
    if len(keep)<30: continue
    res=evaluate(keep,0.5,2.0,0.5,-0.5)
    R26=[r for y,r in res if y==2026]; Rall=[r for _,r in res]
    if len(R26)<20: continue
    ev26=sum(R26)/len(R26); se=statistics.pstdev(R26)/math.sqrt(len(R26))
    wr=100.0*len([x for x in R26 if x>0])/len(R26)
    q1,n1=pr(R26,8,3); q2,n2=pr(R26,5,3)
    p1,_=pr(Rall,8,3); p2,_=pr(Rall,5,3)
    freq=len(R26)/DAYS26
    print(" %5s   %3d   %4.1f%%   %3d    %+.3f  %.3f   %4.1f%%    %5.1f%%   %4.0f    %+.3f    %5.1f%%"
          % ("none" if th==0 else "%.2f"%th, len(keep),100.0*len(keep)/len(ss),len(R26),
             ev26,se,wr,q1*q2/100,(n1+n2)/max(freq,.01),sum(Rall)/len(Rall),p1*p2/100))
