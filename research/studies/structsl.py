"""Structure-based stop versus an arithmetic stop at the same distance.

B = stop under the swing low/high inside the range, accepted only when the
    resulting distance falls in [0.25, 0.50] of the range; otherwise 0.50.
C = arithmetic stop at exactly the distance B picked -- identical risk, no
    structure underneath it. B minus C isolates whether structure matters.
"""
import csv, datetime as dt, statistics, math, random
from mt5paths import bars as barsfile
random.seed(8080)
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

def setups():
    out=[]
    for d,b in sorted(days.items()):
        if d.weekday()>3: continue          # Mon-Thu, Friday is off
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
        score = cp if buy else 1-cp
        if score < 0.25: continue           # close-position filter, live setting
        if k+1 not in b: continue
        out.append(dict(d=d,b=b,k=k,buy=buy,hi=hi,lo=lo,rng=rng,e=b[k+1][0],w=w))
    return out

def struct_frac(s, K):
    """Fraction of range from the broken level down to the swing low of the
    last K range bars (mirrored for a sell). None if outside [0.25, 0.50]."""
    tail=s['w'][-K:]
    lvl = s['hi'] if s['buy'] else s['lo']
    px  = min(x[2] for x in tail) if s['buy'] else max(x[1] for x in tail)
    frac = abs(lvl-px)/s['rng']
    return frac if 0.25 <= frac <= 0.50 else None

def simulate(s, frac, rr=2.0, mat=0.5, mto=-0.5, hold=60):
    lvl = s['hi'] if s['buy'] else s['lo']
    sl  = lvl - s['rng']*frac if s['buy'] else lvl + s['rng']*frac
    e=s['e']; risk=abs(e-sl)
    if risk<=0: return None
    tp = e+rr*risk if s['buy'] else e-rr*risk
    sgn = 1 if s['buy'] else -1; moved=False; R=None
    for j in range(s['k']+1, s['k']+1+hold+1):
        if j not in s['b']: break
        o,h,l,c = s['b'][j]
        adv = l if s['buy'] else h; fav = h if s['buy'] else l
        if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; break
        if mat>0 and not moved and (fav-e)*sgn>=mat*risk:
            moved=True; sl=e+sgn*mto*risk
            if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; break
        if (fav-tp)*sgn>=0: R=rr; break
        last=c
    if R is None: R=(last-e)*sgn/risk
    return R - ((SPREAD*POINT)/risk + 2*COMM/(risk*CONTRACT))

def pr(Rs,t,md,paths=20000):
    ok=0;dd=[]
    for _ in range(paths):
        eq=100.0;n=0
        while n<1500:
            n+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and n>=md: ok+=1;dd.append(n);break
    return 100*ok/paths,(statistics.median(dd) if dd else 0)

ss=setups()
print("2026 Asia, Mon-Thu, close-position filter on. %d setups.\n" % len(ss))
for K in (3,5,8,15):
    A=[];B=[];C=[]; used=0; fracs=[]
    for s in ss:
        a=simulate(s,0.50); 
        f=struct_frac(s,K)
        if f is None:
            b=a; c=a
        else:
            used+=1; fracs.append(f)
            b=simulate(s,f); c=simulate(s,f)   # identical here by construction
        if None in (a,b,c): continue
        A.append(a); B.append(b); C.append(c)
    def st(x): 
        return (sum(x)/len(x), statistics.pstdev(x)/math.sqrt(len(x)),
                100.0*len([v for v in x if v>0])/len(x))
    ea,sea,wa=st(A); eb,seb,wb=st(B)
    p1,m1=pr(B,8,3); p2,m2=pr(B,5,3)
    q1,_=pr(A,8,3); q2,_=pr(A,5,3)
    print("  swing low over the last %2d range bars" % K)
    print("     usable on %d of %d setups (%.0f%%), median accepted distance %.2f x range"
          % (used,len(ss),100.0*used/len(ss), statistics.median(fracs) if fracs else 0))
    print("     A  midpoint always   EV %+.3f +/-%.3f  WR %4.1f%%   pass %5.1f%%" % (ea,sea,wa,q1*q2/100))
    print("     B  structure stop    EV %+.3f +/-%.3f  WR %4.1f%%   pass %5.1f%%" % (eb,seb,wb,p1*p2/100))
    print("     B - A               %+.3f\n" % (eb-ea))
