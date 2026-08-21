import json, statistics, random, math
from sweep import load, setups, evaluate, stats
random.seed(7)
ss = setups(load())
rows = json.load(open("grid.json"))
def get(sl,rr,ma,mt):
    for r in rows:
        if abs(r['sl']-sl)<1e-9 and abs(r['rr']-rr)<1e-9 and abs(r['move_at']-ma)<1e-9 and abs(r['move_to']-mt)<1e-9:
            return r
def only26(sl,rr,ma,mt):
    res=[r for r in evaluate(ss,sl,rr,ma,mt) if r[0]==2026]
    return stats(res)

print("### A. STOP-LOSS PLACEMENT   (RR=2, stop-move 0.5 -> -0.5)")
print("  SL as fraction of range     EV       WR      2024    2025    2026    2026 WR")
for sl in [0.25,0.375,0.5,0.625,0.75,1.0]:
    r=get(sl,2.0,0.5,-0.5); s26=only26(sl,2.0,0.5,-0.5)
    print("   %.3f  (%s)%s %+.3f   %4.1f%%   %+.3f  %+.3f  %+.3f   %4.1f%%"
          % (sl, "midpoint" if sl==0.5 else ("far side" if sl==1.0 else "      "),
             "        " if sl in (0.5,1.0) else "         ",
             r['ev'],r['wr'],r['y24'],r['y25'],r['y26'],s26['wr']))
print()
print("### B. REWARD:RISK   (stop-move 0.5 -> -0.5)")
for sl in (0.5,1.0):
    print("  SL = %.2f of range" % sl)
    print("    RR      EV       WR      2024    2025    2026    2026 WR")
    for rr in [1.0,1.25,1.5,1.75,2.0,2.5,3.0]:
        r=get(sl,rr,0.5,-0.5); s26=only26(sl,rr,0.5,-0.5)
        print("   %.2f   %+.3f   %4.1f%%   %+.3f  %+.3f  %+.3f   %4.1f%%"
              % (rr,r['ev'],r['wr'],r['y24'],r['y25'],r['y26'],s26['wr']))
    print()
print("### C. STOP-MOVE GRID   (SL=0.5, RR=2)  cells are overall EV / 2026 EV")
print("   trigger |   to -0.5R      to -0.25R     to breakeven")
r=get(0.5,2.0,0.0,0.0); s=only26(0.5,2.0,0.0,0.0)
print("   off     |  %+.3f / %+.3f  (no move at all)" % (r['ev'],s['ev']))
for ma in (0.25,0.5,0.75,1.0):
    cells=[]
    for mt in (-0.5,-0.25,0.0):
        r=get(0.5,2.0,ma,mt); s=only26(0.5,2.0,ma,mt)
        cells.append("%+.3f / %+.3f" % (r['ev'],s['ev']))
    print("   %.2fR    |  %s  %s  %s" % (ma,cells[0],cells[1],cells[2]))
print()
print("### D. BEST FOR 2026 ALONE (betting the regime persists)")
best=[]
for r in rows:
    s=only26(r['sl'],r['rr'],r['move_at'],r['move_to'])
    best.append((s['ev'],s['wr'],s['n'],r))
best.sort(key=lambda x:-x[0])
print("   SL     RR    move          2026 EV   2026 WR")
for ev,wr,n,r in best[:8]:
    mv="off" if r['move_at']==0 else "%.2f->%+.2f"%(r['move_at'],r['move_to'])
    print("  %.3f  %.2f  %-12s   %+.3f    %4.1f%%" % (r['sl'],r['rr'],mv,ev,wr))
print()
def passrate(Rs,target,mindays,risk=2.0,paths=40000):
    ok=0;days=[]
    for _ in range(paths):
        eq=100.0;d=0
        while d<900:
            d+=1;eq+=risk*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+target and d>=mindays: ok+=1;days.append(d);break
    return 100*ok/paths,(statistics.median(days) if days else 0)
print("### E. FUNDINGPIPS PASS RATE, 2% risk, 2026 distribution")
cands=[("current  SL 0.50 RR 2.0 move 0.5->-0.5",0.5,2.0,0.5,-0.5),
       ("best-26  %s"%("SL %.2f RR %.2f move %.2f->%+.2f"%(best[0][3]['sl'],best[0][3]['rr'],best[0][3]['move_at'],best[0][3]['move_to'])),
        best[0][3]['sl'],best[0][3]['rr'],best[0][3]['move_at'],best[0][3]['move_to']),
       ("robust   SL 1.00 RR 3.0 move 0.5->-0.5",1.0,3.0,0.5,-0.5)]
for name,sl,rr,ma,mt in cands:
    R=[r for y,r in evaluate(ss,sl,rr,ma,mt) if y==2026]
    p1,m1=passrate(R,8,3); p2,m2=passrate(R,5,3)
    print("   %-44s BOTH %5.1f%%  median %2.0f days" % (name,p1*p2/100,m1+m2))
