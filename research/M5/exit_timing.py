"""Does closing before or after 01:00 UTC change the edge?

Entries run to 00:29 and the hold cap is 90 minutes, so trades can live until
about 01:29. This asks whether a hard flat-by-clock rule at various times beats
letting the per-trade cap decide."""
import csv, datetime as dt, statistics, math, sys
sys.path.insert(0,"..")
from mt5paths import bars as barsfile
POINT=0.01; COMM=3.04; CONTRACT=100.0; SPREAD=52.0
def nth(y,m,dow,n):
    if n>0:
        d=dt.date(y,m,1); return d+dt.timedelta(days=(dow-d.weekday()-1)%7+(n-1)*7)
    d=dt.date(y,m,28)
    while (d+dt.timedelta(days=1)).month==m: d+=dt.timedelta(days=1)
    return d-dt.timedelta(days=(d.weekday()+1-dow)%7)
def off(d): return 3 if nth(d.year,3,0,2)<=d<nth(d.year,11,0,1) else 2
days={}
for row in csv.DictReader(open(barsfile("XAUUSD"))):
    t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
    if t.year!=2026: continue
    days.setdefault(t.date(),{})[t.hour*60+t.minute]=(
        float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]),int(row["ticks"]))

def run(min_cp=0.25, hold=60, hard_utc=None):
    """hard_utc: flat at this UTC minute-of-day regardless of the hold cap."""
    out=[]
    for d,b in sorted(days.items()):
        if d.weekday()>3: continue
        st=off(d)*60
        w=[b[m] for m in range(st,st+15) if m in b]
        if len(w)<15: continue
        hi=max(x[1] for x in w); lo=min(x[2] for x in w); rng=hi-lo
        if rng<=0: continue
        cp=(w[-1][3]-lo)/rng
        sig=None
        for k in range(st+15,st+30):
            if k not in b: break
            if b[k][3]>hi: sig=(k,True); break
            if b[k][3]<lo: sig=(k,False); break
        if not sig: continue
        k,buy=sig
        if (cp if buy else 1-cp) < min_cp: continue
        if k+1 not in b: continue
        e=b[k+1][0]; lvl=hi if buy else lo
        sl=lvl-rng*0.5 if buy else lvl+rng*0.5
        risk=abs(e-sl)
        if risk<=0: continue
        tp=e+2.0*risk if buy else e-2.0*risk
        sgn=1 if buy else -1; moved=False; R=None
        stop_at = k+1+hold
        if hard_utc is not None:
            stop_at = min(stop_at, off(d)*60 + hard_utc)
        for j in range(k+1, stop_at+1):
            if j not in b: break
            o,h,l,c,_=b[j]
            adv=l if buy else h; fav=h if buy else l
            if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; break
            if not moved and (fav-e)*sgn>=0.5*risk:
                moved=True; sl=e+sgn*(-0.5)*risk
                if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; break
            if (fav-tp)*sgn>=0: R=2.0; break
            last=c; last_min=j
        if R is None:
            R=(last-e)*sgn/risk
        out.append((d,R,k+1-(st+15)))
    return out

print("Gold Asia 2026, Mon-Thu, close-pos 0.25. Entries run to 00:29.\n")
print("  exit rule                         n     EV      +/-SE    WR      total R")
base=run(0.25,60,None)
def show(lab,res):
    R=[r[1] for r in res]
    print("  %-32s %3d   %+.3f   %.3f  %4.1f%%   %+6.1f"
          % (lab,len(R),sum(R)/len(R),statistics.pstdev(R)/math.sqrt(len(R)),
             100.0*len([x for x in R if x>0])/len(R),sum(R)))
show("60-min cap (live)",base)
for hu,lab in ((45,"flat at 00:45 UTC"),(60,"flat at 01:00 UTC"),
               (75,"flat at 01:15 UTC"),(90,"flat at 01:30 UTC")):
    show(lab,run(0.25,60,hu))
for hold,lab in ((90,"90-min cap"),(120,"120-min cap"),(240,"240-min cap")):
    show(lab,run(0.25,hold,None))

print("\n  where trades actually are at 01:00 UTC, and what happens after")
res=run(0.25,60,None); res60=run(0.25,60,60)
d60={d:r for d,r,_ in res60}
still=[(d,r) for d,r,_ in res if abs(d60.get(d,r)-r)>1e-9]
print("    %d of %d trades were still open at 01:00" % (len(still),len(res)))
if still:
    before=[d60[d] for d,_ in still]; after=[r for _,r in still]
    print("    closing them at 01:00 :  avg %+.3f R" % (sum(before)/len(before)))
    print("    letting them run      :  avg %+.3f R" % (sum(after)/len(after)))
    print("    difference            :  %+.3f R per affected trade" % ((sum(after)-sum(before))/len(still)))

print("\n  volatility around 01:00 -- median tick count per M1 bar, by UTC minute block")
for lo,hi in ((0,15),(15,30),(30,45),(45,60),(60,75),(75,90),(90,120)):
    v=[]
    for d,b in days.items():
        if d.weekday()>3: continue
        st=off(d)*60
        v += [b[m][4] for m in range(st+lo,st+hi) if m in b]
    if v: print("    %02d:%02d-%02d:%02d UTC   median %4.0f ticks/min" % (lo//60,lo%60,hi//60,hi%60,statistics.median(v)))
