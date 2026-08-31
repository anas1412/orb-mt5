"""One chart per trade, into ~/orb/trades/. Labels de-collided, x-axis clipped
to the trade's actual life.

Only redraws what changed. Each chart carries a signature over the trade row,
that day's bars, its position in the year and this file's own contents, so a
new trade costs one drawing rather than seventy-six. Pass --all to force the
lot, which is what an unrelated style change needs.
"""
import csv, hashlib, os, sys, datetime as dt, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mt5paths import COMMON as D, bars as barsfile

HOLD = 90   # InpMaxHoldMinutes -- must match the run that produced the CSV
FORCE = "--all" in sys.argv
# Hashing this file means a change to the drawing code redraws everything by
# itself, so the cache can never serve a chart the current code would not draw.
CODE = hashlib.sha1(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:12]
OUT=os.path.expanduser("~/orb/trades"); os.makedirs(OUT,exist_ok=True)
INK="#141310"; MUT="#8a837a"; POS="#12694a"; NEG="#a8352a"; ACC="#8a6d3b"; GRID="#ece7dd"
def nth(y,m,dow,n):
    if n>0:
        d=dt.date(y,m,1); return d+dt.timedelta(days=(dow-d.weekday()-1)%7+(n-1)*7)
    d=dt.date(y,m,28)
    while (d+dt.timedelta(days=1)).month==m: d+=dt.timedelta(days=1)
    return d-dt.timedelta(days=(d.weekday()+1-dow)%7)
def off(d): return 3 if nth(d.year,3,0,2)<=d<nth(d.year,11,0,1) else 2
bars={}
for src in ("bars_XAUUSD.csv","bars_XAUUSD_extra.csv"):
    p=os.path.join(D,src)
    if not os.path.exists(p): continue
    for row in csv.DictReader(open(p)):
        t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
        bars.setdefault(t.date(),{})[t.hour*60+t.minute]=(
            float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))
rows=[r for r in csv.DictReader(open(os.path.join(D,"live_cp0.50.csv"))) if r['entry_time'][:4]=='2026']
for r in rows:
    r['t']=dt.datetime.strptime(r['entry_time'],"%Y.%m.%d %H:%M"); r['R']=float(r['R'])
rows.sort(key=lambda r:r['t'])

def place(levels, span):
    """Nudge labels apart vertically. levels = [(y,colour,text,weight)]."""
    gap=span*0.052
    items=sorted(levels,key=lambda z:z[0])
    ys=[it[0] for it in items]
    for i in range(1,len(ys)):
        if ys[i]-ys[i-1] < gap: ys[i]=ys[i-1]+gap
    return [(items[i][0],ys[i])+items[i][1:] for i in range(len(items))]

def signature(tr, daybars, i):
    h=hashlib.sha1(CODE.encode())
    h.update(repr([tr[k] for k in ('entry_time','dir','entry','sl','R','exit',
                                   'close_pos','spread_pts','range_pts')]).encode())
    h.update(repr(sorted(daybars.items())).encode())
    h.update(b"%d" % i)          # the subtitle carries the trade's position
    return h.hexdigest()[:16]

old={}
if os.path.exists("trade_index.json"):
    for e in json.load(open("trade_index.json")):
        old[e['date']]=e

index=[]; drawn=0; reused=0
for i,tr in enumerate(rows,1):
    d=tr['t'].date(); b=bars.get(d)
    if not b: continue
    sig=signature(tr,b,i)
    prev=old.get(d.isoformat())
    if not FORCE and prev and prev.get('sig')==sig and \
       os.path.exists(os.path.join(OUT,prev['file'])):
        index.append(prev); reused+=1; continue
    st=off(d)*60
    rng=[b[m] for m in range(st,st+15) if m in b]
    if len(rng)<15: continue
    hi=max(x[1] for x in rng); lo=min(x[2] for x in rng); width=hi-lo
    cp=(rng[-1][3]-lo)/width
    buy = tr['dir']=="buy"
    score = cp if buy else 1-cp
    e=float(tr['entry']); sl=float(tr['sl']); risk=abs(e-sl)
    tp = e+2*risk if buy else e-2*risk
    win = tr['R']>0
    em = tr['t'].hour*60+tr['t'].minute - st

    # The run already recorded HOW the trade ended and what it made, so the
    # only open question is WHEN. Driving the walk from the recorded result
    # instead of re-deriving one means the marker cannot contradict the label
    # above it -- which it did for 27 Aug 2026, drawn on the target while the
    # title read LOSS.
    spread = int(tr['spread_pts'])*0.01
    sgn = 1 if buy else -1
    kind = (tr['exit'].split() or ["hold"])[0]
    # A stop exit near -1R was the original stop; a shallow one was the stop
    # after it moved to -0.5R.
    stop_lvl = sl if abs(tr['R']) > 0.75 else e+sgn*(-0.5)*risk
    exit_p = stop_lvl if kind=="sl" else tp if kind=="tp" else e+sgn*tr['R']*risk

    # The stop only sits at -0.5R after the trade has been +0.5R up, so the
    # moved level cannot be searched for from the entry bar -- do that and a
    # trade "stops" before the move that created the level could have armed.
    armed  = abs(tr['R']) > 0.75          # a full stop is live from the start
    exit_m = em+HOLD
    for m in range(st+em, st+em+HOLD+1):
        if m not in b: break
        o,h,l,c = b[m]
        # A short's stop sits on the ASK while the candles draw the BID.
        adv = l if buy else h+spread
        fav = h if buy else l
        exit_m = m-st
        if kind=="tp":
            if (fav-tp)*sgn >= 0: break
        elif kind=="sl":
            if not armed and (fav-e)*sgn >= 0.5*risk: armed = True
            if armed and (adv-stop_lvl)*sgn <= 0: break


    # Belt and braces: half an R of disagreement means the marker is telling a
    # different story from the number, not rounding.
    drawn_r = (exit_p-e)*sgn/risk
    if abs(drawn_r-tr['R']) > 0.5:
        raise SystemExit("%s: marker at %.2f is %+.2f R but the run recorded "
                         "%+.3f R" % (d, exit_p, drawn_r, tr['R']))

    last = st+exit_m+6
    xs=[m for m in range(st-4,last+1) if m in b]
    if len(xs)<25: continue

    fig,ax=plt.subplots(figsize=(11.8,5.7),dpi=105)
    for m in xs:
        o,h,l,c=b[m]; x=m-st; up=c>=o; col=POS if up else NEG
        ax.plot([x,x],[l,h],color=col,lw=.9,solid_capstyle="butt",zorder=2)
        ax.add_patch(Rectangle((x-.33,min(o,c)),.66,max(abs(c-o),width*.0025),
                    facecolor=col if up else "white",edgecolor=col,lw=.9,zorder=3))
    ax.add_patch(Rectangle((-0.5,lo),15,width,facecolor=ACC,alpha=.08,zorder=1))
    ax.axvline(14.5,color=ACC,ls=":",lw=1.1,zorder=1)
    ax.axvline(29.5,color=MUT,ls=":",lw=.9,zorder=1)

    span=max(hi,sl,tp)-min(lo,sl,tp)
    lv=place([(hi,MUT,"range high",False),(lo,MUT,"range low",False),
              (e,ACC,"entry  %.2f"%e,True),(sl,NEG,"stop  %.2f   −1R"%sl,True),
              (tp,POS,"target  %.2f   +2R"%tp,True)],span)
    xr=xs[-1]-st
    for y0,ytxt,col,lab,bold in lv:
        ax.plot([-4.6,xr+.4],[y0,y0],color=col,ls="--" if bold else "-",
                lw=1.15 if bold else .9,alpha=.85,zorder=1)
        ax.plot([xr+.8,xr+2.2],[y0,ytxt],color=col,lw=.7,alpha=.45,zorder=1)
        ax.text(xr+2.7,ytxt,lab,color=col,fontsize=9,va="center",
                weight="bold" if bold else "normal")
    ax.plot([em],[e],marker="^" if buy else "v",ms=12,color=ACC,zorder=6,
            markeredgecolor="white",markeredgewidth=.9)
    if exit_p is not None:
        ax.plot([exit_m],[exit_p],marker="X",ms=11,color=POS if win else NEG,zorder=6,
                markeredgecolor="white",markeredgewidth=.9)
    ax.text(7,hi+span*.055,"15-min range",color=ACC,fontsize=9.5,ha="center",weight="bold")
    ax.text(22,lo-span*.055,"entries until 00:29",color=MUT,fontsize=8.5,ha="center")

    res = "%s   %+.2f R" % ("WIN" if win else "LOSS", tr['R'])
    ax.set_title("%s   ·   %s   ·   %s   —   %s"
                 % (d.strftime("%d %B %Y"),d.strftime("%A"),
                    "LONG" if buy else "SHORT",res),
                 fontsize=14,color=POS if win else NEG,weight="bold",loc="left",pad=16)
    ax.text(0,1.02,"00:14 closed in the %s half     range %.0f pts     held %d min     trade %d"
            % ("top" if buy else "bottom",width/0.01,exit_m-em,i),
            transform=ax.transAxes,fontsize=9,color=MUT)
    tick=[t_ for t_ in range(0,xr+1,15)]
    ax.set_xticks(tick); ax.set_xticklabels(["%02d:%02d"%(t_//60,t_%60) for t_ in tick],fontsize=9)
    ax.set_xlabel("UTC",fontsize=9,color=MUT); ax.set_ylabel("XAUUSD",fontsize=9,color=MUT)
    ax.set_xlim(-5,xr+15)
    ax.set_ylim(min(lo,sl,tp)-span*.10,max(hi,sl,tp)+span*.13)
    for s_ in ("top","right"): ax.spines[s_].set_visible(False)
    ax.grid(axis="y",color=GRID,lw=.6,zorder=0)
    fn="%s_%s_%s.png"%(d.isoformat(),"long" if buy else "short","win" if win else "loss")
    fig.savefig(os.path.join(OUT,fn),bbox_inches="tight",facecolor="white"); plt.close(fig)
    index.append(dict(n=i,date=d.isoformat(),day=d.strftime("%a"),dir=tr['dir'],
                      R=round(tr['R'],3),score=round(score,3),range_pts=round(width/0.01),
                      held=exit_m-em,file=fn,sig=sig))
    drawn+=1
json.dump(index,open("trade_index.json","w"),indent=1)
print("%d charts: drew %d, reused %d" % (len(index),drawn,reused))
