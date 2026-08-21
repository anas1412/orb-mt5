"""Three ways of reading bias from the same 15-minute range, compared.

  A  last-bar close position  -- one candle, what we have been using
  B  mean close position      -- all 15 bars averaged
  C  share of bars closing in the upper half of the range
"""
import csv, datetime as dt, statistics, math
from mt5paths import bars as barsfile
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
        days.setdefault(t.date(),{})[t.hour*60+t.minute]=(float(row["high"]),float(row["low"]),float(row["close"]))
def build(hz):
    out=[]
    for d,b in sorted(days.items()):
        if d.weekday()>4: continue
        st=off(d)*60
        w=[b[m] for m in range(st,st+15) if m in b]
        if len(w)<15: continue
        hi=max(x[0] for x in w); lo=min(x[1] for x in w); rng=hi-lo
        if rng<=0: continue
        pos=[(x[2]-lo)/rng for x in w]
        anchor=w[-1][2]; later=st+15+hz-1
        if later not in b: continue
        out.append(dict(A=pos[-1], B=statistics.mean(pos),
                        C=sum(1 for p in pos if p>0.5)/len(pos),
                        ret=b[later][2]-anchor))
    return out
def score(obs,key,hz):
    """Top and bottom quartile by the chosen measure -> hit rate."""
    s=sorted(obs,key=lambda o:o[key]); q=len(s)//4
    top=s[-q:]; bot=s[:q]
    base=100.0*len([o for o in obs if o['ret']>0])/len(obs)
    hu=100.0*len([o for o in top if o['ret']>0])/len(top)
    hd=100.0*len([o for o in bot if o['ret']<=0])/len(bot)
    se=100.0*math.sqrt(0.25/q)
    return hu,hd,base,q,se
print("2026 Asia. Top and bottom quartile of each measure, hit rate in the implied direction.\n")
for hz in (60,300):
    obs=build(hz)
    base=100.0*len([o for o in obs if o['ret']>0])/len(obs)
    print("  horizon +%dh   (n=%d, base rate up = %.1f%%)" % (hz//60,len(obs),base))
    print("    measure                        top quartile -> UP   bottom quartile -> DOWN   +/-SE")
    for key,lab in (("A","last bar close position "),("B","mean close position     "),("C","share of bars upper half")):
        hu,hd,b,q,se=score(obs,key,hz)
        print("    %s        %5.1f%%              %5.1f%%           %.1f  (n=%d each)"
              % (lab,hu,hd,q and se and se or 0, se, q) if False else
              "    %s        %5.1f%%               %5.1f%%            %.1f  (n=%d each)"
              % (lab,hu,hd,se,q))
    print()
obs=build(60)
for key,lab in (("A","last bar close"),("B","mean position "),("C","share upper   ")):
    r=statistics.correlation([o[key] for o in obs],[o['ret'] for o in obs])
    print("  correlation with the 1h move -- %s : r = %+.3f  (r^2 = %.3f)" % (lab,r,r*r))
