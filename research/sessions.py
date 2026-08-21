"""Compare the Asia, London and New York opening ranges on gold.

Answers whether London still carries the widest ranges and heaviest activity,
which was asserted from priors in the roadmap rather than measured."""
import csv, datetime as dt, statistics, os

BARS=os.path.expanduser("~/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files/bars_XAUUSD.csv")
def nth_dow(y,m,dow,nth):
    if nth>0:
        d=dt.date(y,m,1); return d+dt.timedelta(days=(dow-d.weekday()-1)%7+(nth-1)*7)
    d=dt.date(y,m,28)
    while (d+dt.timedelta(days=1)).month==m: d+=dt.timedelta(days=1)
    return d-dt.timedelta(days=(d.weekday()+1-dow)%7)
def offset(d):
    return 3 if nth_dow(d.year,3,0,2) <= d < nth_dow(d.year,11,0,1) else 2

days={}
with open(BARS) as f:
    for row in csv.DictReader(f):
        t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
        days.setdefault(t.date(),{})[t.hour*60+t.minute]=(
            float(row["high"]),float(row["low"]),float(row["close"]),int(row["ticks"]))

SESSIONS=[("Asia",0,0),("London",7,0),("New York",13,30)]
res={s[0]:{} for s in SESSIONS}
for d,bars in days.items():
    if d.weekday()>4: continue
    off=offset(d)
    for name,uh,um in SESSIONS:
        start=(uh+off)*60+um
        win=[bars[m] for m in range(start,start+15) if m in bars]
        if len(win)<15: continue
        hi=max(b[0] for b in win); lo=min(b[1] for b in win)
        if hi<=lo: continue
        res[name].setdefault(d.year,[]).append((hi-lo, win[-1][2], sum(b[3] for b in win)))

print("Gold 15-minute opening range by session -- measured, 2024-2026")
print("range in points (1 pt = $0.01); ticks = M1 tick count over the 15 minutes\n")
for y in (2024,2025,2026):
    print("  %d" % y)
    print("    session     days   median range   as %% of price   median ticks")
    for name,_,_ in SESSIONS:
        g=res[name].get(y,[])
        if not g: continue
        rng=statistics.median([x[0] for x in g])/0.01
        pct=statistics.median([100.0*x[0]/x[1] for x in g])
        tk=statistics.median([x[2] for x in g])
        print("    %-10s  %4d      %6.0f          %.3f%%         %6.0f"
              % (name,len(g),rng,pct,tk))
    print()
print("  2026 only -- ratio to Asia:")
a=res["Asia"].get(2026,[])
ar=statistics.median([x[0] for x in a]); at=statistics.median([x[2] for x in a])
for name,_,_ in SESSIONS:
    g=res[name].get(2026,[])
    if not g: continue
    print("    %-10s range %.2fx    ticks %.2fx"
          % (name, statistics.median([x[0] for x in g])/ar, statistics.median([x[2] for x in g])/at))
