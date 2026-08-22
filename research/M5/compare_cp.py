"""Close-position 0.25 vs 0.50, judged on pass rate rather than profitability.

Live configuration: gold Asia 00:00 UTC, 15-min range, M1 signal, entry window
to 00:29, SL at the range midpoint, 2R target, stop moved to -0.5R at +0.5R,
60-minute hold, Friday off, 2% risk."""
import csv, os, statistics, math, random, datetime as dt
from mt5paths import COMMON as D
random.seed(31337)

def load(cp):
    rows=[r for r in csv.DictReader(open(os.path.join(D,"live_cp%s.csv"%cp)))
          if r['entry_time'][:4]=='2026']
    for r in rows:
        r['R']=float(r['R'])
        r['t']=dt.datetime.strptime(r['entry_time'],"%Y.%m.%d %H:%M")
    rows.sort(key=lambda r:r['t'])
    return rows

def runs(R):
    wl=ll=cw=cl=0
    for r in R:
        if r>0: cw+=1; cl=0
        else:   cl+=1; cw=0
        wl=max(wl,cw); ll=max(ll,cl)
    return wl,ll

def maxdd(R,risk=2.0):
    eq=100.0; peak=100.0; dd=0.0
    for r in R:
        eq += risk*r*eq/100.0
        peak=max(peak,eq); dd=max(dd,100.0*(peak-eq)/peak)
    return dd, eq

def passrate(R,risk=2.0,paths=40000):
    def ph(t):
        ok=0; days=[]
        for _ in range(paths):
            eq=100.0; d=0
            while d<2000:
                d+=1; eq += risk*random.choice(R)*eq/100.0
                if eq<=90.0: break
                if eq>=100+t and d>=3: ok+=1; days.append(d); break
        return 100.0*ok/paths,(statistics.median(days) if days else 0)
    p1,m1=ph(8.0); p2,m2=ph(5.0)
    return p1,p2,p1*p2/100.0,m1+m2

print("Gold Asia 2026 | RR2 | stop -> -0.5R | 2% risk | Mon-Thu | entries to 00:29\n")
print("  metric                       cp 0.25        cp 0.50")
store={}
for cp in ("0.25","0.50"):
    rows=load(cp); R=[r['R'] for r in rows]; store[cp]=(rows,R)
line=lambda name,f: print("  %-26s   %-14s %-14s" % (name,f("0.25"),f("0.50")))
line("trades",              lambda c:"%d"%len(store[c][1]))
line("win rate",            lambda c:"%.1f%%"%(100.0*len([x for x in store[c][1] if x>0])/len(store[c][1])))
line("EV per trade",        lambda c:"%+.3f R"%(sum(store[c][1])/len(store[c][1])))
line("  +/- standard error",lambda c:"%.3f"%(statistics.pstdev(store[c][1])/math.sqrt(len(store[c][1]))))
line("total R",             lambda c:"%+.1f R"%sum(store[c][1]))
line("sd(R)  variance",     lambda c:"%.2f"%statistics.pstdev(store[c][1]))
line("longest win streak",  lambda c:"%d"%runs(store[c][1])[0])
line("longest loss streak", lambda c:"%d"%runs(store[c][1])[1])
line("worst drawdown @2%",  lambda c:"%.1f%%"%maxdd(store[c][1])[0])
line("equity from 100",     lambda c:"%.0f"%maxdd(store[c][1])[1])
res={c:passrate(store[c][1]) for c in ("0.25","0.50")}
line("phase 1 pass",        lambda c:"%.1f%%"%res[c][0])
line("phase 2 pass",        lambda c:"%.1f%%"%res[c][1])
line("BOTH phases",         lambda c:"%.1f%%"%res[c][2])
line("median trades",       lambda c:"%.0f"%res[c][3])
line("~calendar days",      lambda c:"%.0f"%(res[c][3]/ (len(store[c][1])/130.0)))
print("\n  quarterly")
print("  quarter          cp 0.25                        cp 0.50")
print("                   n    EV      WR     total     n    EV      WR     total")
for q,(a,b) in enumerate([(1,3),(4,6),(7,9),(10,12)],1):
    cells=[]
    for cp in ("0.25","0.50"):
        g=[r['R'] for r in store[cp][0] if a<=r['t'].month<=b]
        cells.append("%3d  %+.3f  %4.1f%%  %+6.1f" % (len(g),sum(g)/len(g),
                     100.0*len([x for x in g if x>0])/len(g),sum(g)) if g else "  -                        ")
    print("  Q%d %-13s %s   %s" % (q,"(%d-%d)"%(a,b),cells[0],cells[1]))
print("\n  monthly EV -- is the edge improving or decaying?")
print("  month     cp 0.25            cp 0.50")
for m in range(1,9):
    cells=[]
    for cp in ("0.25","0.50"):
        g=[r['R'] for r in store[cp][0] if r['t'].month==m]
        cells.append("n=%2d %+.3f" % (len(g),sum(g)/len(g)) if g else "     -    ")
    print("  2026-%02d   %s        %s" % (m,cells[0],cells[1]))
for cp in ("0.25","0.50"):
    R=store[cp][1]; h=len(R)//2
    print("\n  cp %s: first half EV %+.3f (n=%d), second half %+.3f (n=%d)"
          % (cp,sum(R[:h])/h,h,sum(R[h:])/(len(R)-h),len(R)-h))
