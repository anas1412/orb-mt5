"""Rolling range filter: trade only when today's range clears a multiple of the
median range of the last N sessions.

The yardstick uses only sessions strictly before the trade date, so unlike the
within-year ranking used earlier there is no lookahead."""
import statistics, random
from sweep import load, setups, evaluate, stats
random.seed(404)

ss, hist = setups(load(), want_history=True)
ss = [s for s in ss if s['late'] < 15]
hist.sort()
hdates = [d for d, _ in hist]; hrng = [r for _, r in hist]
idx = {d: i for i, d in enumerate(hdates)}

def ratio(s, N):
    """today's range / median of the previous N sessions. None if not enough history."""
    i = idx.get(s['date'])
    if i is None or i < N: return None
    ref = statistics.median(hrng[i-N:i])
    return (s['hi'] - s['lo']) / ref if ref > 0 else None

def pr(Rs, target, mindays, risk=2.0, paths=15000):
    ok = 0; days = []
    for _ in range(paths):
        eq = 100.0; d = 0
        while d < 1200:
            d += 1; eq += risk*random.choice(Rs)*eq/100.0
            if eq <= 90.0: break
            if eq >= 100+target and d >= mindays: ok += 1; days.append(d); break
    return 100*ok/paths, (statistics.median(days) if days else 0)

base = evaluate(ss, 0.5, 2.0, 0.5, -0.5)
print("no filter:  all %d trades  EV %+.3f   2026 EV %+.3f\n"
      % (len(base), stats(base)['ev'], stats([r for r in base if r[0]==2026])['ev']))

print("EV per trade by lookback and threshold  (pooled / 2026)   [kept = share of days traded]")
print("  thresh |" + "".join("      N=%-2d      " % N for N in (10,20,30,50)))
best=[]
for th in (0.6,0.8,0.9,1.0,1.1,1.25,1.5):
    cells=[]
    for N in (10,20,30,50):
        keep=[s for s in ss if (lambda r: r is not None and r>=th)(ratio(s,N))]
        if len(keep)<40: cells.append("      -       "); continue
        res=evaluate(keep,0.5,2.0,0.5,-0.5)
        a=stats(res); b=stats([r for r in res if r[0]==2026])
        cells.append("%+.3f/%+.3f " % (a['ev'], b['ev'] if b else 0))
        best.append((a['ev'], b['ev'] if b else 0, th, N, len(keep), a, res))
    print("   %.2f  |%s" % (th,"".join(cells)))
print()
for label,key in (("pooled 2024-26",0),("2026 only",1)):
    print("top 5 by %s EV:" % label)
    print("   thresh  N    trades  kept%   pooled EV   2026 EV   pooled WR")
    for ev,ev26,th,N,n,a,res in sorted(best,key=lambda x:-x[key])[:5]:
        print("   %.2f    %2d    %3d    %4.1f%%    %+.3f      %+.3f     %4.1f%%"
              % (th,N,n,100.0*n/len(ss),ev,ev26,a['wr']))
    print()
print("pass rate for the leading candidates (2%% risk, days adjusted for skipped setups):")
print("   filter              trades  kept%   pooled pass  2026 pass  ~calendar days (2026)")
cands=[(None,None)]+[(th,N) for ev,ev26,th,N,n,a,res in sorted(best,key=lambda x:-x[0])[:3]]
for th,N in cands:
    keep = ss if th is None else [s for s in ss if (lambda r: r is not None and r>=th)(ratio(s,N))]
    res=evaluate(keep,0.5,2.0,0.5,-0.5)
    Rall=[r for _,r in res]; R26=[r for y,r in res if y==2026]
    p1,m1=pr(Rall,8,3); p2,m2=pr(Rall,5,3)
    q1,n1=pr(R26,8,3); q2,n2=pr(R26,5,3)
    kept=len(keep)/len(ss)
    days=(n1+n2)/max(len([s for s in keep if s['date'].year==2026])/165.0,.01)
    name="none" if th is None else "range >= %.2f x med(%d)"%(th,N)
    print("   %-20s %3d   %4.1f%%    %5.1f%%      %5.1f%%       %4.0f"
          % (name,len(keep),100*kept,p1*p2/100,q1*q2/100,days))
