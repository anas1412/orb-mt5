"""Equity and risk diagnostics. Fixed 2% of the INITIAL balance per trade, so
each R is worth a constant 2 percentage points and the curve is not compounded."""
import csv, os, datetime as dt, statistics, math
from collections import Counter
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mt5paths import COMMON as D
INK="#1b1a18"; MUT="#6b6660"; POS="#1f6b45"; NEG="#a33a2c"; ACC="#8a6d3b"; LINE="#d9d4ca"
RISK=2.0
def load(cp):
    rows=[r for r in csv.DictReader(open(os.path.join(D,"live_cp%s.csv"%cp)))
          if r['entry_time'][:4]=='2026']
    for r in rows:
        r['R']=float(r['R']); r['t']=dt.datetime.strptime(r['entry_time'],"%Y.%m.%d %H:%M")
    rows.sort(key=lambda r:r['t']); return rows
A=load("0.50")
fig=plt.figure(figsize=(14,9.5),dpi=110)
gs=fig.add_gridspec(3,2,height_ratios=[1.5,1,1],hspace=.45,wspace=.22)

# --- equity, fixed fractional ---
ax=fig.add_subplot(gs[0,:])
ax2=ax.twinx()
for rows,lab,col in ((A,"close-pos 0.50",POS),):
    pct=[0.0]; cum=0.0
    for r in rows: cum+=r['R']; pct.append(RISK*cum)
    ax.plot([rows[0]['t']]+[r['t'] for r in rows],pct,lw=2.0,color=col,
            label="%s  —  %+.0f%%  (%+.1f R, %d trades)"%(lab,pct[-1],cum,len(rows)))
ax.axhline(0,color=MUT,lw=.9,ls=":")
ax.set_ylabel("cumulative return  (%, 2% of initial balance per trade)",fontsize=9,color=MUT)
lo,hi=ax.get_ylim(); ax2.set_ylim(lo/RISK,hi/RISK)
ax2.set_ylabel("cumulative R",fontsize=9,color=MUT)
ax.set_title("Cumulative return — gold Asia 2026, close-pos 0.50, Mon–Thu, fixed 2% risk",
             fontsize=13,color=INK,weight="bold",loc="left",pad=12)
ax.legend(frameon=False,fontsize=9.5,loc="upper left")
for s in ("top",): ax.spines[s].set_visible(False); ax2.spines[s].set_visible(False)
ax.grid(axis="y",color=LINE,lw=.6)

# --- outcome distribution ---
ax=fig.add_subplot(gs[1,0])
R=[r['R'] for r in A]
ax.hist(R,bins=22,color=POS,alpha=.75,edgecolor="white",lw=.6)
ax.axvline(0,color=MUT,lw=1)
ax.axvline(statistics.mean(R),color=NEG,lw=1.6,label="mean %+.2f R"%statistics.mean(R))
ax.set_title("Outcome distribution",fontsize=11,color=INK,weight="bold",loc="left")
ax.set_xlabel("R per trade",fontsize=9,color=MUT); ax.legend(frameon=False,fontsize=9)
for s in ("top","right"): ax.spines[s].set_visible(False)

# --- drawdown, fixed fractional ---
ax=fig.add_subplot(gs[1,1])
cum=0.0; peak=0.0; dd=[]
for r in A:
    cum+=RISK*r['R']; peak=max(peak,cum); dd.append(cum-peak)
ax.fill_between([r['t'] for r in A],dd,0,color=NEG,alpha=.5)
ax.axhline(-10,color=NEG,lw=1,ls="--")
ax.text(A[0]['t'],-10,"  prop limit −10%",color=NEG,fontsize=8.5,va="bottom")
ax.set_title("Drawdown from peak (worst %.1f%%)"%abs(min(dd)),fontsize=11,color=INK,weight="bold",loc="left")
ax.set_ylabel("% below peak",fontsize=9,color=MUT)
ax.set_ylim(min(-11,min(dd)*1.2),0.6)
for s in ("top","right"): ax.spines[s].set_visible(False)
ax.grid(axis="y",color=LINE,lw=.6)

# --- monthly EV ---
ax=fig.add_subplot(gs[2,0])
mo=sorted({r['t'].month for r in A}); w=.38
vals=[statistics.mean([r['R'] for r in A if r['t'].month==m]) for m in mo]
ax.bar(mo,vals,width=.6,color=[POS if v>0 else NEG for v in vals],alpha=.85)
ax.axhline(0,color=MUT,lw=1)
ax.set_xticks(mo); ax.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug"][:len(mo)],fontsize=9)
ax.set_title("Monthly EV — strengthening through the year",fontsize=11,color=INK,weight="bold",loc="left")
ax.set_ylabel("R per trade",fontsize=9,color=MUT)
for s in ("top","right"): ax.spines[s].set_visible(False)
ax.grid(axis="y",color=LINE,lw=.6)

# --- losing streaks vs the limit ---
ax=fig.add_subplot(gs[2,1])
seq=[];cur=0
for r in A:
    if r['R']<=0: cur+=1
    else:
        if cur: seq.append(cur)
        cur=0
if cur: seq.append(cur)
c=Counter(seq); ks=sorted(c)
cols=[NEG if k*RISK>=10 else (ACC if k*RISK>=6 else MUT) for k in ks]
ax.bar(ks,[c[k] for k in ks],color=cols,alpha=.85)
for k in ks: ax.text(k,c[k]+.15,"%.0f%%"%(k*RISK),ha="center",fontsize=8,color=MUT)
ax.axvline(5,color=NEG,lw=1.2,ls="--")
ax.text(5.08,max(c.values())*.85,"5 losses = −10%\nthe entire limit",color=NEG,fontsize=8.5,va="top")
ax.set_title("Losing streaks and what each costs at 2% risk",fontsize=11,color=INK,weight="bold",loc="left")
ax.set_xlabel("consecutive losses",fontsize=9,color=MUT); ax.set_ylabel("times it happened",fontsize=9,color=MUT)
ax.set_xticks(ks)
for s in ("top","right"): ax.spines[s].set_visible(False)
ax.grid(axis="y",color=LINE,lw=.6)

fig.savefig("edge_2026_cp050.png",bbox_inches="tight",facecolor="white")
print("cp0.50 saved. worst drawdown %.1f%%, longest losing run %d (= %.0f%%)"%(abs(min(dd)),max(seq),max(seq)*RISK))
