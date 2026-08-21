"""Does the 00:14 candle's close position predict Asia's direction?

Ground truth: sign of the return 60 minutes after the range closes, measured
from the 00:14 close. Every session with a valid range counts -- not only the
days that produced a breakout -- so there is no selection effect.

Note the score here is RAW (0 = closed at the range low, 1 = at the high), not
flipped to face a break direction as in the filter study. There is no break yet."""
import csv, datetime as dt, statistics, math
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
        days.setdefault(t.date(),{})[t.hour*60+t.minute]=(
            float(row["high"]),float(row["low"]),float(row["close"]))

HORIZON=60
obs=[]
for d,b in sorted(days.items()):
    if d.weekday()>4: continue
    st=off(d)*60
    w=[b[m] for m in range(st,st+15) if m in b]
    if len(w)<15: continue
    hi=max(x[0] for x in w); lo=min(x[1] for x in w)
    rng=hi-lo
    if rng<=0: continue
    anchor=w[-1][2]                       # 00:14 close
    later=st+15+HORIZON-1                 # bar closing 60 min after the range closes
    if later not in b: continue
    fut=b[later][2]
    obs.append(dict(cp=(anchor-lo)/rng, ret=fut-anchor, rng=rng))

n=len(obs)
up=len([o for o in obs if o['ret']>0])
base=100.0*up/n
print("Asia session, 2026. %d sessions with a complete range and a +%dmin follow-through.\n" % (n,HORIZON))
print("BASE RATE: price is higher 60 min after the range closes on %.1f%% of sessions" % base)
print("           (so a coin flip predicting UP every day scores %.1f%%)\n" % base)

Q=[(0.00,0.25,"0-25%   strong bearish","down"),
   (0.25,0.50,"25-50%  bearish       ","down"),
   (0.50,0.75,"50-75%  bullish       ","up"),
   (0.75,1.01,"75-100% strong bullish","up")]
print("  quadrant                 n    predicted   correct   hit rate   base    LIFT     avg move")
for lo,hi,lab,pred in Q:
    g=[o for o in obs if lo<=o['cp']<hi]
    if not g: continue
    ok=len([o for o in g if (o['ret']>0)==(pred=="up")])
    hit=100.0*ok/len(g)
    # base rate for THIS prediction direction
    bd = base if pred=="up" else 100.0-base
    # signed move in the predicted direction, as a share of the range
    mv=statistics.mean([(o['ret'] if pred=="up" else -o['ret'])/o['rng'] for o in g])
    print("  %s  %3d      %-5s     %3d      %5.1f%%   %5.1f%%  %+5.1f pp   %+.2f x range"
          % (lab,len(g),pred,ok,hit,bd,hit-bd,mv))

print("\n  collapsed to two halves:")
for lo,hi,lab,pred in [(0.0,0.5,"bottom half (bearish)","down"),(0.5,1.01,"top half (bullish)","up")]:
    g=[o for o in obs if lo<=o['cp']<hi]
    ok=len([o for o in g if (o['ret']>0)==(pred=="up")])
    hit=100.0*ok/len(g); bd = base if pred=="up" else 100.0-base
    se=100.0*math.sqrt(0.25/len(g))
    mv=statistics.mean([(o['ret'] if pred=="up" else -o['ret'])/o['rng'] for o in g])
    print("  %-22s n=%3d  hit %5.1f%%  base %5.1f%%  lift %+5.1f pp  (+/-%.1f)  avg %+.2f x range"
          % (lab,len(g),hit,bd,hit-bd,se,mv))

r=statistics.correlation([o['cp'] for o in obs],[o['ret']/o['rng'] for o in obs])
print("\n  correlation between close position and the 60-min move: r = %+.3f" % r)
print("  (r^2 = %.3f, so the signal explains %.1f%% of the variation)" % (r*r,100*r*r))
