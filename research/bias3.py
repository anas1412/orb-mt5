"""Same test across several horizons: close of 00:14 vs close N minutes later."""
import csv, datetime as dt
from mt5paths import bars as barsfile
def nth(y,m,dow,n):
    if n>0:
        d=dt.date(y,m,1); return d+dt.timedelta(days=(dow-d.weekday()-1)%7+(n-1)*7)
    d=dt.date(y,m,28)
    while (d+dt.timedelta(days=1)).month==m: d+=dt.timedelta(days=1)
    return d-dt.timedelta(days=(d.weekday()+1-dow)%7)
def off(d): return 3 if nth(d.year,3,0,2)<=d<nth(d.year,11,0,1) else 2
days={}
with open(barsfile("XAUUSD")) as f:
    for row in csv.DictReader(f):
        t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
        if t.year!=2026: continue
        days.setdefault(t.date(),{})[t.hour*60+t.minute]=(float(row["high"]),float(row["low"]),float(row["close"]))
Q=[(0.00,0.25,"bottom quarter  0-25%"),(0.25,0.50,"lower middle   25-50%"),
   (0.50,0.75,"upper middle   50-75%"),(0.75,1.01,"top quarter   75-100%")]
H=[60,120,180,240,300]
def build(hz):
    obs=[]
    for d,b in sorted(days.items()):
        if d.weekday()>4: continue
        st=off(d)*60
        w=[b[m] for m in range(st,st+15) if m in b]
        if len(w)<15: continue
        hi=max(x[0] for x in w); lo=min(x[1] for x in w); rng=hi-lo
        if rng<=0: continue
        anchor=w[-1][2]; later=st+15+hz-1
        if later not in b: continue
        obs.append(((anchor-lo)/rng, b[later][2]-anchor))
    return obs
print("2026 Asia. Close of 00:14 vs close N minutes after the range closed.")
print("'matches' = price finished on the same side the 00:14 candle closed.\n")
hdr="  where 00:14 closed        " + "".join("  +%dh      " % (h//60) for h in H)
print(hdr)
for lo,hi,lab in Q:
    cells=[]
    for hz in H:
        obs=build(hz)
        g=[r for cp,r in obs if lo<=cp<hi]
        if not g: cells.append("   -      "); continue
        u=len([r for r in g if r>0]); m=(u if lo>=0.5 else len(g)-u)
        cells.append("%4.1f%% (%2d) " % (100.0*m/len(g),len(g)))
    print("  %s  %s" % (lab,"".join(cells)))
print()
for lo,hi,lab in [(0.00,0.50,"bottom half    0-50%"),(0.50,1.01,"top half     50-100%")]:
    cells=[]
    for hz in H:
        obs=build(hz)
        g=[r for cp,r in obs if lo<=cp<hi]
        u=len([r for r in g if r>0]); m=(u if lo>=0.5 else len(g)-u)
        cells.append("%4.1f%% (%2d) " % (100.0*m/len(g),len(g)))
    print("  %s   %s" % (lab,"".join(cells)))
print("\n  base rate (share of all sessions finishing higher):")
cells=[]
for hz in H:
    obs=build(hz)
    u=len([r for cp,r in obs if r>0])
    cells.append("%4.1f%% (%3d)" % (100.0*u/len(obs),len(obs)))
print("                            "+"  ".join(cells))
