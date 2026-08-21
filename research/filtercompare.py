"""Compare MT5 real-tick runs of the rolling range filter at several thresholds."""
import csv, glob, statistics, math, random, os, json
random.seed(707)
from mt5paths import COMMON as D
def pr(Rs, t, md, paths=25000):
    ok=0; days=[]
    for _ in range(paths):
        eq=100.0; d=0
        while d<1500:
            d+=1; eq += 2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0: break
            if eq>=100+t and d>=md: ok+=1; days.append(d); break
    return 100*ok/paths, (statistics.median(days) if days else 0)
out=[]
for th in ("0.00","1.00","1.25","1.50"):
    f=os.path.join(D,"filter_%s.csv"%th)
    rows=[r for r in csv.DictReader(open(f))]
    for r in rows: r['R']=float(r['R']); r['y']=r['entry_time'][:4]
    R=[r['R'] for r in rows]
    per={}
    for y in ('2024','2025','2026'):
        g=[r['R'] for r in rows if r['y']==y]
        per[y]=(len(g), sum(g)/len(g), statistics.pstdev(g)/math.sqrt(len(g))) if g else (0,0,0)
    R26=[r['R'] for r in rows if r['y']=='2026']
    p1,m1=pr(R,8,3); p2,m2=pr(R,5,3)
    q1,n1=pr(R26,8,3); q2,n2=pr(R26,5,3)
    out.append(dict(th=th,n=len(R),ev=sum(R)/len(R),
                    se=statistics.pstdev(R)/math.sqrt(len(R)),
                    wr=100.0*len([x for x in R if x>0])/len(R),
                    per=per, pooled_pass=p1*p2/100, p26=q1*q2/100,
                    days26=(n1+n2)/max(len(R26)/165.0,.01),
                    daysall=(m1+m2)/max(len(R)/670.0,.01)))
json.dump(out, open("filter_mt5.json","w"), indent=1)
print("MT5 REAL TICKS -- rolling filter, lookback 20 sessions, 2024.01-2026.08\n")
print("  thresh  trades  kept%   EV all   +/-SE    WR      2024      2025      2026    pooled pass  2026 pass  2026 days")
base=out[0]['n']
for o in out:
    lab = "off" if o['th']=="0.00" else o['th']
    print("   %-5s   %3d   %5.1f%%  %+.3f   %.3f  %4.1f%%  %+.3f   %+.3f   %+.3f    %5.1f%%     %5.1f%%      %3.0f"
          % (lab,o['n'],100.0*o['n']/base,o['ev'],o['se'],o['wr'],
             o['per']['2024'][1],o['per']['2025'][1],o['per']['2026'][1],
             o['pooled_pass'],o['p26'],o['days26']))
print("\n  trades per year:")
for o in out:
    lab = "off" if o['th']=="0.00" else o['th']
    print("   %-5s  2024 n=%3d   2025 n=%3d   2026 n=%3d" % (lab,o['per']['2024'][0],o['per']['2025'][0],o['per']['2026'][0]))
