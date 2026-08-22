"""M5 line of research: the published ORB shape (5-min opening interval,
trade its direction, stop at the interval extreme, far target, hold to close).

Reported the way a prop challenge actually cares: expectancy, win rate, streaks,
and pass rate at several risk sizes -- because a far target means a low win rate
and long losing runs, and the drawdown limit is what kills you, not the average."""
import csv, os, statistics, math, random, sys
from mt5paths import COMMON as D
random.seed(7777)

def streaks(R):
    worst=cur=0; bestw=curw=0
    for r in R:
        if r<=0: cur+=1; bestw=max(bestw,cur); curw=0
        else:    curw+=1; best=max(bestw,cur); cur=0
    w=0; run=0
    for r in R:
        if r>0: run+=1; w=max(w,run)
        else: run=0
    return bestw,w

def passrate(R,risk,target1=8.0,target2=5.0,mindays=3,paths=30000):
    def phase(t):
        ok=0; days=[]
        for _ in range(paths):
            eq=100.0; d=0
            while d<3000:
                d+=1
                eq += risk*random.choice(R)*eq/100.0
                if eq<=90.0: break
                if eq>=100+t and d>=mindays: ok+=1; days.append(d); break
        return 100.0*ok/paths, (statistics.median(days) if days else 0)
    p1,m1=phase(target1); p2,m2=phase(target2)
    return p1*p2/100.0, m1+m2

def load(tag):
    p=os.path.join(D,"zar_rr%s.csv"%tag)
    if not os.path.exists(p): return None
    rows=[r for r in csv.DictReader(open(p)) if r['entry_time'][:4]=='2026']
    return [float(r['R']) for r in rows]

print("US100.cash -- published ORB shape, New York cash open, MT5 real ticks, 2026")
print("5-min interval 09:30-09:34, enter its direction at 09:35, stop at the interval")
print("extreme, no stop move, flat at the 16:00 cash close.\n")
print("  target   n    EV      +/-SE     WR     worst losing run   best R   sd(R)")
data={}
for tag in ("5.0","10.0","20.0"):
    R=load(tag)
    if not R: continue
    data[tag]=R
    lw,ww=streaks(R)
    print("  %5sR  %3d  %+.3f   %.3f   %4.1f%%        %2d          %+.1f    %.2f"
          % (tag.rstrip('0').rstrip('.'),len(R),sum(R)/len(R),
             statistics.pstdev(R)/math.sqrt(len(R)),
             100.0*len([x for x in R if x>0])/len(R),lw,max(R),statistics.pstdev(R)))
print("\n  FundingPips 2-step pass rate by risk per trade")
print("  (10% max loss, so 2% risk survives 5 straight full losses, 1% survives 10)")
print("\n  target   risk   pass both   median trades   worst run costs")
for tag in ("5.0","10.0","20.0"):
    if tag not in data: continue
    R=data[tag]; lw,_=streaks(R)
    for risk in (0.5,1.0,2.0):
        p,d=passrate(R,risk)
        print("  %5sR   %.1f%%    %5.1f%%        %4.0f            %5.1f%% of the account"
              % (tag.rstrip('0').rstrip('.'),risk,p,d,lw*risk))
    print()
