import statistics, random, math
from sweep import load, setups, evaluate, stats
random.seed(303)
ss = setups(load())
print("setups with a 120-minute window: %d\n" % len(ss))
lates=[s['late'] for s in ss]
print("when the break happens, minutes after the range closes:")
for lo,hi in [(0,5),(5,10),(10,15),(15,20),(20,30),(30,45),(45,60),(60,90),(90,120)]:
    n=len([x for x in lates if lo<=x<hi])
    print("   %3d-%3d min  %3d setups (%4.1f%%)" % (lo,hi,n,100.0*n/len(ss)))
def pr(Rs,target,mindays,risk=2.0,paths=20000):
    ok=0;days=[]
    for _ in range(paths):
        eq=100.0;d=0
        while d<1200:
            d+=1;eq+=risk*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+target and d>=mindays: ok+=1;days.append(d);break
    return 100*ok/paths,(statistics.median(days) if days else 0)
CUT=[5,10,15,20,30,45,60,90,120]
HOLD=[15,30,45,60,90,120,180]
print("\n=== 2026 only: EV per trade (n = setups that qualify) ===")
print("  cutoff |" + "".join("  hold %3d " % h for h in HOLD))
best=[]
for c in CUT:
    row=[]
    for h in HOLD:
        res=[r for y,r in evaluate(ss,0.5,2.0,0.5,-0.5,hold=h,cutoff=c) if y==2026]
        if not res: row.append("    -    "); continue
        ev=sum(res)/len(res); row.append(" %+.3f  " % ev)
        best.append((ev,c,h,len(res),100.0*len([x for x in res if x>0])/len(res)))
    n=len([s for s in ss if s['late']<c and s['date'].year==2026])
    print("  %3d min (n=%3d) |%s" % (c,n,"".join(row)))
best.sort(key=lambda x:-x[0])
print("\ntop 8 by 2026 EV:")
print("   cutoff  hold    n     EV      WR")
for ev,c,h,n,wr in best[:8]:
    print("   %3d     %3d   %3d   %+.3f   %4.1f%%" % (c,h,n,ev,wr))
print("\n=== pass rate, 2%% risk, 2026 distribution ===")
print("   cutoff  hold    n     EV      WR     PASS BOTH  median days")
seen=set()
for ev,c,h,n,wr in best[:10]:
    if (c,h) in seen: continue
    seen.add((c,h))
    R=[r for y,r in evaluate(ss,0.5,2.0,0.5,-0.5,hold=h,cutoff=c) if y==2026]
    p1,m1=pr(R,8,3); p2,m2=pr(R,5,3)
    # opportunities per calendar day: only qualifying days trade
    days26=len(set(s['date'] for s in ss if s['date'].year=='' or s['date'].year==2026))
    freq=n/165.0   # ~165 trading days in 2026 sample
    print("   %3d     %3d   %3d   %+.3f   %4.1f%%   %5.1f%%      %4.0f" % (c,h,n,ev,wr,p1*p2/100,(m1+m2)/max(freq,0.01)))
