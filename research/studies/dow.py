"""Day-of-week breakdown, 2026 Asia, live configuration."""
import csv, os, datetime as dt, statistics, math, random
from mt5paths import COMMON as D
random.seed(5050)
f=os.path.join(D,"cp_0.25.csv")
rows=[r for r in csv.DictReader(open(f)) if r['entry_time'][:4]=='2026']
for r in rows:
    r['R']=float(r['R'])
    r['dow']=dt.datetime.strptime(r['entry_time'],"%Y.%m.%d %H:%M").weekday()
NAMES=["Monday","Tuesday","Wednesday","Thursday","Friday"]
print("2026 Asia, live config (SL midpoint, RR2, stop move +0.5R->-0.5R, close-pos 0.25)")
print("%d trades\n" % len(rows))
print("  day         n     EV      +/-SE    WR      total R   best    worst")
tot=[]
for i,name in enumerate(NAMES):
    g=[r['R'] for r in rows if r['dow']==i]
    if not g: continue
    ev=sum(g)/len(g); se=statistics.pstdev(g)/math.sqrt(len(g))
    tot.append((name,len(g),ev,se,sum(g)))
    print("  %-10s %3d   %+.3f   %.3f  %4.1f%%   %+7.2f   %+.2f   %+.2f"
          % (name,len(g),ev,se,100.0*len([x for x in g if x>0])/len(g),sum(g),max(g),min(g)))
allR=[r['R'] for r in rows]
print("  %-10s %3d   %+.3f   %.3f  %4.1f%%   %+7.2f"
      % ("ALL",len(allR),sum(allR)/len(allR),statistics.pstdev(allR)/math.sqrt(len(allR)),
         100.0*len([x for x in allR if x>0])/len(allR),sum(allR)))

print("\n  is any day distinguishable from the rest?")
for name,n,ev,se,t in tot:
    others=[r['R'] for r in rows if NAMES[r['dow']]!=name]
    oev=sum(others)/len(others); ose=statistics.pstdev(others)/math.sqrt(len(others))
    d=ev-oev; sed=math.sqrt(se**2+ose**2)
    print("    %-10s vs the other four:  %+.3f  (t = %+.2f)  %s"
          % (name,d,d/sed if sed>0 else 0,"SIGNIFICANT" if abs(d/sed)>2 else "no"))

def pr(Rs,t,md,paths=20000):
    ok=0;dd_=[]
    for _ in range(paths):
        eq=100.0;dd=0
        while dd<1500:
            dd+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and dd>=md: ok+=1;dd_.append(dd);break
    return 100*ok/paths,(statistics.median(dd_) if dd_ else 0)
print("\n  what dropping the worst day would do:")
worst=min(tot,key=lambda x:x[2])
for lab,Rs,days in (("keep all 5 days",allR,163),
                    ("drop %s"%worst[0],[r['R'] for r in rows if NAMES[r['dow']]!=worst[0]],130)):
    p1,m1=pr(Rs,8,3); p2,m2=pr(Rs,5,3); freq=len(Rs)/float(days)
    print("    %-16s n=%3d  EV %+.3f  pass %5.1f%%  ~%3.0f days"
          % (lab,len(Rs),sum(Rs)/len(Rs),p1*p2/100,(m1+m2)/max(freq,.01)))
