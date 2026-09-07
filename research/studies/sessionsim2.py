"""Sessions anchored to their own LOCAL opening time, with each zone's own DST
rule -- the way TimeZones.mqh does it in the EA.

The earlier fixed-UTC test put London and New York an hour before their real
opens for roughly five months of every year."""
import csv, datetime as dt, statistics, math, os, random
random.seed(1010)
from mt5paths import bars
BARS = bars("XAUUSD")
POINT=0.01; COMM=3.04; CONTRACT=100.0
SPREAD={2024:21.0,2025:28.0,2026:52.0}
def nth(y,m,dow,n):
    if n>0:
        d=dt.date(y,m,1); return d+dt.timedelta(days=(dow-d.weekday()-1)%7+(n-1)*7)
    d=dt.date(y,m,28)
    while (d+dt.timedelta(days=1)).month==m: d+=dt.timedelta(days=1)
    return d-dt.timedelta(days=(d.weekday()+1-dow)%7)
def us_dst(d): return nth(d.year,3,0,2) <= d < nth(d.year,11,0,1)
def eu_dst(d): return nth(d.year,3,0,-1) <= d < nth(d.year,10,0,-1)
def broker_off(d): return 3 if us_dst(d) else 2      # broker follows US dates
def utc_minutes(name, d):
    """Session open in UTC minutes, from its own local clock."""
    if name=="Asia":     return 0*60 + 0                        # 00:00 UTC by spec
    if name=="London":   return (7 if eu_dst(d) else 8)*60      # 08:00 London
    if name=="New York": return (13 if us_dst(d) else 14)*60+30 # 09:30 New York
days={}
with open(BARS) as f:
    for row in csv.DictReader(f):
        t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
        days.setdefault(t.date(),{})[t.hour*60+t.minute]=(
            float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))
def run(name,rng_min=15,win=15,sl_frac=0.5,rr=2.0,mat=0.5,mto=-0.5,hold=60):
    out=[]
    for d,b in sorted(days.items()):
        if d.weekday()>4: continue
        st=utc_minutes(name,d)+broker_off(d)*60
        w=[b[m] for m in range(st,st+rng_min) if m in b]
        if len(w)<rng_min: continue
        hi=max(x[1] for x in w); lo=min(x[2] for x in w)
        if hi<=lo: continue
        sig=None
        for k in range(st+rng_min, st+rng_min+win):
            if k not in b: break
            if b[k][3]>hi: sig=(k,True); break
            if b[k][3]<lo: sig=(k,False); break
        if not sig: continue
        k,buy=sig
        if k+1 not in b: continue
        e=b[k+1][0]; lvl=hi if buy else lo
        sl=lvl-(hi-lo)*sl_frac if buy else lvl+(hi-lo)*sl_frac
        risk=abs(e-sl)
        if risk<=0: continue
        tp=e+rr*risk if buy else e-rr*risk
        sgn=1 if buy else -1; moved=False; R=None
        for j in range(k+1,k+1+hold+1):
            if j not in b: break
            o,h,l,c=b[j]
            adv=l if buy else h; fav=h if buy else l
            if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; break
            if mat>0 and not moved and (fav-e)*sgn>=mat*risk:
                moved=True; sl=e+sgn*mto*risk
                if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; break
            if (fav-tp)*sgn>=0: R=rr; break
            last=c
        if R is None: R=(last-e)*sgn/risk
        out.append((d.year, R-((SPREAD[d.year]*POINT)/risk + 2*COMM/(risk*CONTRACT)),
                    (hi-lo)/POINT, w[-1][3]))
    return out
print("Sessions anchored to their own local open, each zone's own DST rule\n")
print("  session        n    median range   EV all   +/-SE    WR      2024     2025     2026")
for name in ("Asia","London","New York"):
    res=run(name)
    R=[r[1] for r in res]
    per={y:[r[1] for r in res if r[0]==y] for y in (2024,2025,2026)}
    print("  %-11s  %3d      %6.0f      %+.3f   %.3f  %4.1f%%  %+.3f   %+.3f   %+.3f"
          % (name,len(R),statistics.median([r[2] for r in res]),
             sum(R)/len(R),statistics.pstdev(R)/math.sqrt(len(R)),
             100.0*len([x for x in R if x>0])/len(R),
             sum(per[2024])/len(per[2024]),sum(per[2025])/len(per[2025]),
             sum(per[2026])/len(per[2026])))
print("\n  best of 16 settings (SL 0.5/1.0 x RR 1.5-3.0 x move on/off), 2026:")
for name in ("Asia","London","New York"):
    rows=[]
    for sl in (0.5,1.0):
        for rr in (1.5,2.0,2.5,3.0):
            for mat,mto in ((0.5,-0.5),(0.0,0.0)):
                res=run(name,sl_frac=sl,rr=rr,mat=mat,mto=mto)
                r26=[r[1] for r in res if r[0]==2026]
                if len(r26)<30: continue
                rows.append((sum(r26)/len(r26),sl,rr,mat,len(r26)))
    if rows:
        ev,sl,rr,mat,n=max(rows)
        print("   %-11s best 2026 EV %+.3f  (SL %.2f, RR %.1f, move %s, n=%d)"
              % (name,ev,sl,rr,"on" if mat>0 else "off",n))
