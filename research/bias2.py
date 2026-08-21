"""Plain contingency: where the 00:14 candle closed vs where price went 60 min later."""
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
obs=[]
for d,b in sorted(days.items()):
    if d.weekday()>4: continue
    st=off(d)*60
    w=[b[m] for m in range(st,st+15) if m in b]
    if len(w)<15: continue
    hi=max(x[0] for x in w); lo=min(x[1] for x in w); rng=hi-lo
    if rng<=0: continue
    anchor=w[-1][2]; later=st+15+59
    if later not in b: continue
    obs.append(((anchor-lo)/rng, b[later][2]-anchor))
print("2026 Asia, %d sessions. Where the 00:14 candle closed vs price 60 min after the range closed.\n" % len(obs))
print("  where 00:14 closed        n     went UP      went DOWN    matches the close?")
for lo,hi,lab in [(0.00,0.25,"bottom quarter  0-25%"),(0.25,0.50,"lower middle   25-50%"),
                  (0.50,0.75,"upper middle   50-75%"),(0.75,1.01,"top quarter   75-100%")]:
    g=[r for cp,r in obs if lo<=cp<hi]
    if not g: continue
    u=len([r for r in g if r>0]); d_=len(g)-u
    match = (u if lo>=0.5 else d_)
    print("  %s  %3d   %3d (%4.1f%%)  %3d (%4.1f%%)   %4.1f%%"
          % (lab,len(g),u,100.0*u/len(g),d_,100.0*d_/len(g),100.0*match/len(g)))
print()
for lo,hi,lab in [(0.00,0.50,"bottom half    0-50%"),(0.50,1.01,"top half     50-100%")]:
    g=[r for cp,r in obs if lo<=cp<hi]
    u=len([r for r in g if r>0]); d_=len(g)-u
    match = (u if lo>=0.5 else d_)
    print("  %s   %3d   %3d (%4.1f%%)  %3d (%4.1f%%)   %4.1f%%"
          % (lab,len(g),u,100.0*u/len(g),d_,100.0*d_/len(g),100.0*match/len(g)))
u=len([r for cp,r in obs if r>0])
print("\n  all sessions:            %3d   %3d (%4.1f%%)  %3d (%4.1f%%)" % (len(obs),u,100.0*u/len(obs),len(obs)-u,100.0*(len(obs)-u)/len(obs)))
