"""Compare the two ways of timing the exit.

A) per-trade hold from the fill      InpMaxHoldMinutes
B) one fixed clock from 00:15        InpForceCloseMin, hold off

Same 2026 live configuration otherwise. Pass rate is the FundingPips two-step
barrier crossing at 2% risk, same Monte Carlo the report uses.
"""
import csv, statistics, math, random, os, sys
from mt5paths import COMMON as D
RISK=2.0

def load(tag):
    p=os.path.join(D,tag+".csv")
    if not os.path.exists(p): return None
    return [float(r['R']) for r in csv.DictReader(open(p)) if r['entry_time'][:4]=='2026']

def passrate(R, paths=20000):
    random.seed(31337)
    def ph(t):
        ok=0
        for _ in range(paths):
            eq=0.0; d=0
            while d<2000:
                d+=1; eq+=RISK*random.choice(R)
                if eq<=-10.0: break
                if eq>=t and d>=3: ok+=1; break
        return 100.0*ok/paths
    return ph(8.0)*ph(5.0)/100.0

def profile(R):
    eq=0.0; peak=0.0; dd=0.0; run=0; worst=0
    for x in R:
        eq+=RISK*x; peak=max(peak,eq); dd=max(dd,peak-eq)
        if x<=0: run+=1; worst=max(worst,run)
        else: run=0
    return dd, worst

def row(lab, R):
    w=len([x for x in R if x>0]); n=len(R)
    dd,st=profile(R)
    return (lab, n, w, 100.0*w/n, sum(R)/n,
            statistics.pstdev(R)/math.sqrt(n), sum(R), RISK*sum(R), passrate(R), dd, st)

def show(title, rows):
    print("\n"+title)
    print("  %-22s  n   W   WR      EV       ±SE    total R  total %%   pass    DD    run"%"")
    best=max(rows,key=lambda r:r[8])
    for r in rows:
        mark=" <-" if r is best else ""
        print("  %-22s %3d %3d  %.1f%%  %+.3f  %.3f   %+6.1f  %+6.1f%%  %.1f%%  %.1f%%  %d%s"
              % (r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],mark))

A=[("hold %d min from fill"%h, load("xa_%d"%h)) for h in (60,75,90,105,120)]
B=[("flat at %02d:%02d UTC"%((15+f)//60,(15+f)%60), load("xb_%d"%f)) for f in (60,75,90,105,120,150)]
show("A) per-trade hold, counted from your fill",
     [row(l,R) for l,R in A if R])
show("B) one fixed clock, counted from 00:15",
     [row(l,R) for l,R in B if R])
missing=[l for l,R in A+B if not R]
if missing: print("\nnot yet run:", ", ".join(missing))
