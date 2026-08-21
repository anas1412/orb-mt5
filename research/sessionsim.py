"""Run the ORB engine over any session, offline, on recorded bars."""
import csv, datetime as dt, statistics, math, os, random
random.seed(909)
BARS=os.path.expanduser("~/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files/bars_XAUUSD.csv")
POINT=0.01; COMM=3.04; CONTRACT=100.0
# spread scales with price level; measured medians on the Asia open were
# 21/28/52 points for 2024/25/26. Applied to every session -- crude, and it
# penalises NY slightly since liquidity there is deeper than at the Asia open.
SPREAD={2024:21.0,2025:28.0,2026:52.0}
def nth_dow(y,m,dow,nth):
    if nth>0:
        d=dt.date(y,m,1); return d+dt.timedelta(days=(dow-d.weekday()-1)%7+(nth-1)*7)
    d=dt.date(y,m,28)
    while (d+dt.timedelta(days=1)).month==m: d+=dt.timedelta(days=1)
    return d-dt.timedelta(days=(d.weekday()+1-dow)%7)
def offset(d): return 3 if nth_dow(d.year,3,0,2)<=d<nth_dow(d.year,11,0,1) else 2
days={}
with open(BARS) as f:
    for row in csv.DictReader(f):
        t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
        days.setdefault(t.date(),{})[t.hour*60+t.minute]=(
            float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))
def run(uh,um,rng_min=15,win=15,sl_frac=0.5,rr=2.0,mat=0.5,mto=-0.5,hold=60):
    out=[]
    for d,b in sorted(days.items()):
        if d.weekday()>4: continue
        st=(uh+offset(d))*60+um
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
        e=b[k+1][0]
        lvl=hi if buy else lo
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
        cost=(SPREAD[d.year]*POINT)/risk + 2*COMM/(risk*CONTRACT)
        out.append((d.year,R-cost))
    return out
def pr(Rs,t,md,paths=20000):
    ok=0;days_=[]
    for _ in range(paths):
        eq=100.0;dd=0
        while dd<1500:
            dd+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and dd>=md: ok+=1;days_.append(dd);break
    return 100*ok/paths,(statistics.median(days_) if days_ else 0)
print("Same engine, three sessions. Offline sim on recorded bars, 2024-2026.\n")
print("  session       n     EV all  +/-SE    WR      2024      2025      2026   2026 pass  2026 days")
for name,uh,um,ndays in (("Asia 00:00",0,0,163),("London 07:00",7,0,163),("New York 13:30",13,30,163)):
    res=run(uh,um)
    if not res: continue
    R=[r for _,r in res]; ev=sum(R)/len(R); se=statistics.pstdev(R)/math.sqrt(len(R))
    per={y:[r for yy,r in res if yy==y] for y in (2024,2025,2026)}
    R26=per[2026]
    p1,m1=pr(R26,8,3); p2,m2=pr(R26,5,3)
    freq=len(R26)/float(ndays)
    print("  %-14s %3d  %+.3f  %.3f  %4.1f%%  %+.3f   %+.3f   %+.3f    %5.1f%%      %3.0f"
          % (name,len(R),ev,se,100.0*len([x for x in R if x>0])/len(R),
             sum(per[2024])/len(per[2024]), sum(per[2025])/len(per[2025]),
             sum(R26)/len(R26), p1*p2/100, (m1+m2)/max(freq,.01)))

print("\nEach session with its OWN best parameters (not Asia's):")
GRID=[(sl,rr,m) for sl in (0.375,0.5,0.75,1.0) for rr in (1.5,2.0,2.5,3.0)
      for m in ((0.5,-0.5),(1.0,-0.5),(0.0,0.0))]
for name,uh,um in (("Asia 00:00",0,0),("London 07:00",7,0),("New York 13:30",13,30)):
    rows=[]
    for sl,rr,(mat,mto) in GRID:
        res=run(uh,um,sl_frac=sl,rr=rr,mat=mat,mto=mto)
        if len(res)<100: continue
        R=[r for _,r in res]
        per={y:[r for yy,r in res if yy==y] for y in (2024,2025,2026)}
        rows.append(dict(sl=sl,rr=rr,mat=mat,mto=mto,n=len(R),
                         ev=sum(R)/len(R),se=statistics.pstdev(R)/math.sqrt(len(R)),
                         y24=sum(per[2024])/len(per[2024]),
                         y25=sum(per[2025])/len(per[2025]),
                         y26=sum(per[2026])/len(per[2026]),
                         wr=100.0*len([x for x in R if x>0])/len(R)))
    print("\n  %s" % name)
    print("    best by pooled EV:")
    for r in sorted(rows,key=lambda r:-r['ev'])[:3]:
        mv="off" if r['mat']==0 else "%.2f->%+.2f"%(r['mat'],r['mto'])
        print("      SL %.3f  RR %.1f  %-12s  EV %+.3f +/-%.3f  WR %4.1f%%  |  %+.3f %+.3f %+.3f"
              % (r['sl'],r['rr'],mv,r['ev'],r['se'],r['wr'],r['y24'],r['y25'],r['y26']))
    print("    best by 2026 EV:")
    for r in sorted(rows,key=lambda r:-r['y26'])[:3]:
        mv="off" if r['mat']==0 else "%.2f->%+.2f"%(r['mat'],r['mto'])
        print("      SL %.3f  RR %.1f  %-12s  EV %+.3f  WR %4.1f%%  |  %+.3f %+.3f %+.3f"
              % (r['sl'],r['rr'],mv,r['ev'],r['wr'],r['y24'],r['y25'],r['y26']))
