"""Candidate entry filters, each with a mechanism rather than just a knob.

Measured on the whole 2024-2026 sample for DIRECTION of effect, then on 2026 for
magnitude. 119 trades in 2026 will hand you a false positive if you only look
there."""
import csv, datetime as dt, statistics, math, os, random
from mt5paths import bars as barsfile
random.seed(2026)
POINT=0.01; COMM=3.04; CONTRACT=100.0
SPREAD={2024:21.0,2025:28.0,2026:52.0}
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
        days.setdefault(t.date(),{})[t.hour*60+t.minute]=(
            float(row["open"]),float(row["high"]),float(row["low"]),
            float(row["close"]),int(row["ticks"]))

# daily reference close: last bar we recorded each day (18:59 broker)
dref={}
for d,b in days.items():
    ks=[k for k in b if k<=18*60+59]
    if ks: dref[d]=b[max(ks)][3]
dates=sorted(dref)
dpos={d:i for i,d in enumerate(dates)}

def build(sl_frac=0.5, rr=2.0, mat=0.5, mto=-0.5, hold=60):
    out=[]
    for d in sorted(days):
        if d.weekday()>4: continue
        b=days[d]; st=off(d)*60
        w=[b[m] for m in range(st,st+15) if m in b]
        if len(w)<15: continue
        hi=max(x[1] for x in w); lo=min(x[2] for x in w)
        if hi<=lo: continue
        sig=None
        for k in range(st+15, st+30):
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
            o,h,l,c,_=b[j]
            adv=l if buy else h; fav=h if buy else l
            if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; break
            if mat>0 and not moved and (fav-e)*sgn>=mat*risk:
                moved=True; sl=e+sgn*mto*risk
                if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; break
            if (fav-tp)*sgn>=0: R=rr; break
            last=c
        if R is None: R=(last-e)*sgn/risk
        R -= (SPREAD[d.year]*POINT)/risk + 2*COMM/(risk*CONTRACT)

        rng=hi-lo
        # --- candidate filter features, all knowable at entry ---
        # 1 trend alignment: range midpoint vs the mean of the last 10 daily closes
        i=dpos.get(d); trend=None
        if i is not None and i>=10:
            ref=sum(dref[dates[j]] for j in range(i-10,i))/10.0
            trend = 1 if ((hi+lo)/2 - ref)*sgn > 0 else 0
        # 2 break strength: how far past the level the signal candle closed
        strength = abs(b[k][3]-lvl)/rng
        # 3 volume: signal-candle ticks vs the range's median
        med=statistics.median([x[4] for x in w])
        volr = b[k][4]/med if med>0 else 0
        # 4 range efficiency: net displacement over total path inside the range
        path=sum(x[1]-x[2] for x in w)
        eff = rng/path if path>0 else 0
        # 5 close position: where the last range bar closed inside the range,
        #   oriented so 1.0 means "closed at the end it then broke"
        cp=(w[-1][3]-lo)/rng
        cpos = cp if buy else 1-cp
        out.append(dict(y=d.year,R=R,trend=trend,strength=strength,vol=volr,eff=eff,cpos=cpos))
    return out

tr=build()
print("baseline: %d trades, EV %+.3f, 2026 EV %+.3f\n"
      % (len(tr), sum(t['R'] for t in tr)/len(tr),
         statistics.mean([t['R'] for t in tr if t['y']==2026])))

def report(name, key, cuts, fmt="%.2f"):
    print("=== %s ===" % name)
    print("   bucket            n     EV all   +/-SE    WR      2026 n   2026 EV")
    for lo,hi in cuts:
        g=[t for t in tr if t[key] is not None and lo<=t[key]<hi]
        if len(g)<25: continue
        R=[t['R'] for t in g]; g26=[t['R'] for t in g if t['y']==2026]
        print(("   "+fmt+" - "+fmt+"   %3d   %+.3f   %.3f  %4.1f%%    %3d    %+.3f")
              % (lo,hi,len(g),sum(R)/len(R),statistics.pstdev(R)/math.sqrt(len(R)),
                 100.0*len([x for x in R if x>0])/len(R),len(g26),
                 sum(g26)/len(g26) if g26 else 0))
    print()

report("1. trend alignment (0 = against drift, 1 = with it)","trend",[(0,1),(1,2)],"%.0f")
report("2. break strength, close past the level as a share of range","strength",
       [(0,0.02),(0.02,0.05),(0.05,0.10),(0.10,0.20),(0.20,9)],"%.3f")
report("3. volume on the break candle vs range median","vol",
       [(0,0.8),(0.8,1.2),(1.2,1.8),(1.8,3.0),(3.0,99)],"%.2f")
report("4. range efficiency, net over path","eff",
       [(0,0.25),(0.25,0.35),(0.35,0.45),(0.45,0.60),(0.60,9)],"%.2f")
report("5. close position, 1.0 = closed at the end it broke","cpos",
       [(0,0.25),(0.25,0.50),(0.50,0.75),(0.75,1.01)],"%.2f")

print("\n############ candidate rules ############\n")
def pr(Rs,t,md,paths=20000):
    ok=0;dd_=[]
    for _ in range(paths):
        eq=100.0;dd=0
        while dd<1500:
            dd+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and dd>=md: ok+=1;dd_.append(dd);break
    return 100*ok/paths,(statistics.median(dd_) if dd_ else 0)
RULES=[
 ("no filter",                 lambda t: True),
 ("close pos >= 0.50",         lambda t: t['cpos']>=0.50),
 ("close pos >= 0.75",         lambda t: t['cpos']>=0.75),
 ("volume >= 0.80",            lambda t: t['vol']>=0.80),
 ("close >= 0.50 AND vol >= 0.80", lambda t: t['cpos']>=0.50 and t['vol']>=0.80),
 ("close >= 0.75 AND vol >= 0.80", lambda t: t['cpos']>=0.75 and t['vol']>=0.80),
 ("close >= 0.50 AND eff >= 0.25",  lambda t: t['cpos']>=0.50 and t['eff']>=0.25),
]
print("  rule                            n    kept   EV all  +/-SE   2024    2025    2026   2026 n  2026 WR  pass  days")
for name,f in RULES:
    g=[t for t in tr if f(t)]
    if len(g)<40: continue
    R=[t['R'] for t in g]
    per={y:[t['R'] for t in g if t['y']==y] for y in (2024,2025,2026)}
    R26=per[2026]
    p1,m1=pr(R26,8,3); p2,m2=pr(R26,5,3); freq=len(R26)/163.0
    print("  %-31s %3d  %4.0f%%  %+.3f  %.3f  %+.3f  %+.3f  %+.3f   %3d   %4.1f%%  %5.1f%%  %3.0f"
          % (name,len(g),100.0*len(g)/len(tr),sum(R)/len(R),
             statistics.pstdev(R)/math.sqrt(len(R)),
             sum(per[2024])/len(per[2024]),sum(per[2025])/len(per[2025]),
             sum(R26)/len(R26),len(R26),
             100.0*len([x for x in R26 if x>0])/len(R26),p1*p2/100,(m1+m2)/max(freq,.01)))
