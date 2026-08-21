import json, statistics, random, math
from sweep import load, setups, evaluate, stats
random.seed(202)
ss = setups(load()); rows = json.load(open("grid.json"))
def pr(Rs,target,mindays,risk=2.0,paths=15000):
    ok=0;days=[]
    for _ in range(paths):
        eq=100.0;d=0
        while d<900:
            d+=1;eq+=risk*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+target and d>=mindays: ok+=1;days.append(d);break
    return 100*ok/paths,(statistics.median(days) if days else 0)
out=[]
for r in rows:
    R=[x for y,x in evaluate(ss,r['sl'],r['rr'],r['move_at'],r['move_to']) if y==2026]
    if not R: continue
    ev=sum(R)/len(R)
    if ev < 0.10: continue                       # no point simulating losers
    w=[x for x in R if x>0]
    p1,m1=pr(R,8,3); p2,m2=pr(R,5,3)
    out.append(dict(sl=r['sl'],rr=r['rr'],ma=r['move_at'],mt=r['move_to'],ev=ev,
                    wr=100.0*len(w)/len(R),both=p1*p2/100,days=m1+m2,
                    sd=statistics.pstdev(R)))
out.sort(key=lambda x:-x['both'])
print("ranked by PASS RATE, 2026 distribution, 2%% risk, 1 trade/day  (%d configs simulated)\n" % len(out))
print("   SL     RR    move          EV      WR     sd(R)   PASS BOTH   median days")
for o in out[:14]:
    mv="off" if o['ma']==0 else "%.2f->%+.2f"%(o['ma'],o['mt'])
    print("  %.3f  %.2f  %-12s  %+.3f  %4.1f%%  %.2f     %5.1f%%      %2.0f"
          % (o['sl'],o['rr'],mv,o['ev'],o['wr'],o['sd'],o['both'],o['days']))
print("\n   ... worst of those simulated:")
for o in out[-4:]:
    mv="off" if o['ma']==0 else "%.2f->%+.2f"%(o['ma'],o['mt'])
    print("  %.3f  %.2f  %-12s  %+.3f  %4.1f%%  %.2f     %5.1f%%      %2.0f"
          % (o['sl'],o['rr'],mv,o['ev'],o['wr'],o['sd'],o['both'],o['days']))
json.dump(out,open("passrate.json","w"))
