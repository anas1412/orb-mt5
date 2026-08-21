"""Optimal stop distance at RR = 1, live config (2026, Mon-Thu, close-pos filter 0.25)."""
import statistics, math, random
exec(open('structsl.py').read().split('ss=setups()')[0])
random.seed(1234)
ss=setups()
def pr(Rs,t,md,paths=25000):
    ok=0;dd=[]
    for _ in range(paths):
        eq=100.0;n=0
        while n<2000:
            n+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and n>=md: ok+=1;dd.append(n);break
    return 100*ok/paths,(statistics.median(dd) if dd else 0)
def row(lab,frac,rr,mat,mto):
    R=[simulate(s,frac,rr=rr,mat=mat,mto=mto) for s in ss]
    R=[x for x in R if x is not None]
    ev=sum(R)/len(R); se=statistics.pstdev(R)/math.sqrt(len(R))
    w=100.0*len([x for x in R if x>0])/len(R)
    p1,m1=pr(R,8,3); p2,m2=pr(R,5,3)
    return (lab,len(R),ev,se,w,statistics.pstdev(R),p1*p2/100,(m1+m2)/max(len(R)/130.0,.01))
print("2026 Asia, Mon-Thu, close-position filter 0.25. %d setups. 2%% risk.\n" % len(ss))
print("  RR = 1.0, stop move +0.5R -> -0.5R")
print("    SL fraction     n     EV      +/-SE    WR     sd(R)  pass both  ~days")
best=None
for f in (0.50,0.625,0.75,0.875,1.00,1.25,1.50):
    r=row("%.3f"%f,f,1.0,0.5,-0.5)
    print("      %s       %2d   %+.3f   %.3f  %4.1f%%   %.2f   %5.1f%%     %3.0f" % (r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7]))
    if best is None or r[2]>best[2]: best=r
print("\n  RR = 1.0, no stop move")
print("    SL fraction     n     EV      +/-SE    WR     sd(R)  pass both  ~days")
for f in (0.50,0.75,1.00,1.25,1.50):
    r=row("%.3f"%f,f,1.0,0.0,0.0)
    print("      %s       %2d   %+.3f   %.3f  %4.1f%%   %.2f   %5.1f%%     %3.0f" % (r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7]))
print("\n  for comparison, other targets at their best stop:")
print("    config                      n     EV      +/-SE    WR     sd(R)  pass both  ~days")
for lab,f,rr in (("RR 1.0  SL %.3f"%best[0] if False else ("RR 1.0  SL "+best[0]),float(best[0]),1.0),
                 ("RR 1.5  SL 0.500",0.50,1.5),
                 ("RR 2.0  SL 0.500  <- live",0.50,2.0),
                 ("RR 2.0  SL 0.750",0.75,2.0),
                 ("RR 3.0  SL 0.500",0.50,3.0)):
    r=row(lab,f,rr,0.5,-0.5)
    print("    %-26s %2d   %+.3f   %.3f  %4.1f%%   %.2f   %5.1f%%     %3.0f" % (lab,r[1],r[2],r[3],r[4],r[5],r[6],r[7]))
