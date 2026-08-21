"""Fade the NY breakout instead of following it.

Same trigger (an M1 close outside the range) but enter the OTHER way, with the
stop beyond the break and the target back inside. Breakout and fade are both
charged full costs, which is why a -0.18 breakout does not become a +0.18 fade."""
import csv, datetime as dt, statistics, math, random
from mt5paths import bars as barsfile
random.seed(3333)
POINT=0.01; COMM=3.04; CONTRACT=100.0; SPREAD=52.0
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
            float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))

def run(utc_h, utc_m, fade, sl_frac, rr, mat=0.5, mto=-0.5, hold=60):
    out=[]
    for d,b in sorted(days.items()):
        if d.weekday()>4: continue
        st=(utc_h+off(d))*60+utc_m
        w=[b[m] for m in range(st,st+15) if m in b]
        if len(w)<15: continue
        hi=max(x[1] for x in w); lo=min(x[2] for x in w); rng=hi-lo
        if rng<=0: continue
        sig=None
        for k in range(st+15, st+30):
            if k not in b: break
            if b[k][3]>hi: sig=(k,True); break
            if b[k][3]<lo: sig=(k,False); break
        if not sig: continue
        k,brk_up=sig
        if k+1 not in b: continue
        buy = (not brk_up) if fade else brk_up
        e=b[k+1][0]
        # follow: stop inside the range. fade: stop beyond the break extreme.
        if fade:
            ext = b[k][1] if brk_up else b[k][2]      # break candle's extreme
            sl  = ext + rng*sl_frac if not buy else ext - rng*sl_frac
        else:
            lvl = hi if buy else lo
            sl  = lvl - rng*sl_frac if buy else lvl + rng*sl_frac
        risk=abs(e-sl)
        if risk<=0: continue
        tp = e+rr*risk if buy else e-rr*risk
        sgn = 1 if buy else -1; moved=False; R=None
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
        out.append(R - ((SPREAD*POINT)/risk + 2*COMM/(risk*CONTRACT)))
    return out
def pr(Rs,t,md,paths=20000):
    ok=0;dd=[]
    for _ in range(paths):
        eq=100.0;n=0
        while n<2000:
            n+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and n>=md: ok+=1;dd.append(n);break
    return 100*ok/paths,(statistics.median(dd) if dd else 0)
print("2026, XAUUSD, Friday included. FADE = enter opposite the break, stop beyond")
print("the break candle's extreme, target RR from entry. Costs charged both ways.\n")
for lab,h,m in (("NY 13:15 UTC",13,15),("NY cash open 13:30 UTC",13,30)):
    print("  %s" % lab)
    print("    direction  SL frac   RR    n     EV      +/-SE    WR      pass both")
    for fade in (False,True):
        for slf,rr in ((0.25,1.0),(0.25,2.0),(0.50,1.0),(0.50,2.0),(1.00,1.0)):
            R=run(h,m,fade,slf,rr)
            if len(R)<30: continue
            ev=sum(R)/len(R); se=statistics.pstdev(R)/math.sqrt(len(R))
            p1,_=pr(R,8,3); p2,_=pr(R,5,3)
            print("    %-9s  %.2f     %.1f  %3d   %+.3f   %.3f  %4.1f%%    %5.1f%%"
                  % ("FADE" if fade else "follow",slf,rr,len(R),ev,se,
                     100.0*len([x for x in R if x>0])/len(R),p1*p2/100))
    print()
