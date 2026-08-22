"""Trades still open at 01:00 UTC -- does what follows stop them out or pay them?"""
import csv, datetime as dt, statistics, sys
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
        float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))
rows=[]
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
    if (cp if buy else 1-cp)<0.25: continue
    if k+1 not in b: continue
    e=b[k+1][0]; lvl=hi if buy else lo
    sl=lvl-rng*0.5 if buy else lvl+rng*0.5
    risk=abs(e-sl)
    if risk<=0: continue
    tp=e+2*risk if buy else e-2*risk
    sgn=1 if buy else -1; moved=False; R=None; how=None; exitmin=None
    for j in range(k+1,k+1+61):
        if j not in b: break
        o,h,l,c=b[j]
        adv=l if buy else h; fav=h if buy else l
        if (adv-sl)*sgn<=0:
            R=(sl-e)*sgn/risk; how="moved stop" if moved else "full stop"; exitmin=j; break
        if not moved and (fav-e)*sgn>=0.5*risk:
            moved=True; sl=e+sgn*(-0.5)*risk
            if (adv-sl)*sgn<=0: R=(sl-e)*sgn/risk; how="moved stop"; exitmin=j; break
        if (fav-tp)*sgn>=0: R=2.0; how="target"; exitmin=j; break
        last=c; exitmin=j
    if R is None: R=(last-e)*sgn/risk; how="60-min cap"
    cost=(SPREAD*POINT)/risk + 2*COMM/(risk*CONTRACT)
    onehr = st+60                       # 01:00 UTC in broker minutes
    rows.append(dict(d=d,R=R-cost,how=how,exit=exitmin,open_at_0100=(exitmin>onehr),
                     onehr=onehr,k=k))
late=[r for r in rows if r['open_at_0100']]
early=[r for r in rows if not r['open_at_0100']]
print("Gold Asia 2026, Mon-Thu, cp 0.25. %d trades.\n" % len(rows))
print("  %d trades were already closed by 01:00 UTC   avg %+.3f R" % (len(early),sum(r['R'] for r in early)/len(early)))
print("  %d trades were still open at 01:00 UTC       avg %+.3f R" % (len(late),sum(r['R'] for r in late)/len(late)))
print("\n  how the 19 still-open trades finished AFTER 01:00:")
from collections import Counter
c=Counter(r['how'] for r in late)
for how,n in c.most_common():
    g=[r['R'] for r in late if r['how']==how]
    print("    %-12s %2d  (%4.1f%%)   avg %+.3f R" % (how,n,100.0*n/len(late),sum(g)/len(g)))
print("\n  same breakdown for the trades that finished BEFORE 01:00:")
c=Counter(r['how'] for r in early)
for how,n in c.most_common():
    g=[r['R'] for r in early if r['how']==how]
    print("    %-12s %2d  (%4.1f%%)   avg %+.3f R" % (how,n,100.0*n/len(early),sum(g)/len(g)))
sl_late=100.0*len([r for r in late if r['how'] in ("full stop","moved stop")])/len(late)
sl_early=100.0*len([r for r in early if r['how'] in ("full stop","moved stop")])/len(early)
print("\n  stopped out:  before 01:00 %.1f%%   after 01:00 %.1f%%" % (sl_early,sl_late))
