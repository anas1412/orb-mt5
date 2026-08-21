"""Range 00:00-00:15 inclusive (16 bars), entries 00:16-00:30 (15 bars).

Session opens convert to broker time (+2 winter / +3 summer on US dates).
London and New York anchor to their own local clock and DST rule."""
import csv, datetime as dt, statistics, math, os, random
random.seed(1111)
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
def broker_off(d): return 3 if us_dst(d) else 2
def utc_open(name,d):
    if name=="Asia":     return 0
    if name=="London":   return (7 if eu_dst(d) else 8)*60
    if name=="New York": return (13 if us_dst(d) else 14)*60+30
days={}
with open(BARS) as f:
    for row in csv.DictReader(f):
        t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
        days.setdefault(t.date(),{})[t.hour*60+t.minute]=(
            float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))
RANGE_BARS=16      # 00:00 .. 00:15 inclusive
ENTRY_BARS=15      # 00:16 .. 00:30 inclusive
def run(name,sl_frac=0.5,rr=2.0,mat=0.5,mto=-0.5,hold=60,
        rbars=RANGE_BARS,ebars=ENTRY_BARS):
    out=[]
    for d,b in sorted(days.items()):
        if d.weekday()>4: continue
        st=utc_open(name,d)+broker_off(d)*60
        w=[b[m] for m in range(st,st+rbars) if m in b]
        if len(w)<rbars: continue
        hi=max(x[1] for x in w); lo=min(x[2] for x in w)
        if hi<=lo: continue
        sig=None
        for k in range(st+rbars, st+rbars+ebars):
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
        out.append((d.year, R-((SPREAD[d.year]*POINT)/risk + 2*COMM/(risk*CONTRACT)), (hi-lo)/POINT))
    return out
def pr(Rs,t,md,paths=20000):
    ok=0;dd_=[]
    for _ in range(paths):
        eq=100.0;dd=0
        while dd<1500:
            dd+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and dd>=md: ok+=1;dd_.append(dd);break
    return 100*ok/paths,(statistics.median(dd_) if dd_ else 0)
if __name__=="__main__":
    print("2026 ONLY  |  range 00:00-00:15 (16 bars), entries 00:16-00:30 (15 bars)")
    print("SL at range midpoint, 60-min hold, 2%% risk, one trade per day\n")
    print("  session      RR   stop move      n     EV      +/-SE    WR     pass both  days")
    for name in ("Asia","London","New York"):
        for rr in (1.0,2.0):
            for mat,mto,mv in ((0.5,-0.5,"0.5 -> -0.5"),(0.0,0.0,"none       ")):
                res=[r for r in run(name,rr=rr,mat=mat,mto=mto) if r[0]==2026]
                R=[r[1] for r in res]
                if len(R)<20: continue
                ev=sum(R)/len(R); se=statistics.pstdev(R)/math.sqrt(len(R))
                p1,m1=pr(R,8,3); p2,m2=pr(R,5,3)
                freq=len(R)/163.0
                print("  %-11s  %.1f  %s  %3d   %+.3f   %.3f  %4.1f%%    %5.1f%%    %3.0f"
                      % (name,rr,mv,len(R),ev,se,
                         100.0*len([x for x in R if x>0])/len(R),p1*p2/100,(m1+m2)/max(freq,.01)))
        print()
