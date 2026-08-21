"""Chart a single ORB session: range, entry, stop, target, outcome, and the
close-position quadrant. Renders the trade as it was actually taken."""
import csv, datetime as dt, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mt5paths import COMMON as D

DAY = dt.date(*map(int, sys.argv[1].split("-"))) if len(sys.argv)>1 else dt.date(2026,8,20)
SL_FRAC, RR, MOVE_AT, MOVE_TO, HOLD = 0.50, 2.0, 0.5, -0.5, 60

bars={}
for src in ("bars_XAUUSD.csv","bars_XAUUSD_extra.csv"):
    p=os.path.join(D,src)
    if not os.path.exists(p): continue
    for row in csv.DictReader(open(p)):
        t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
        if t.date()!=DAY: continue
        bars[t.hour*60+t.minute]=(float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))
if not bars:
    raise SystemExit("no bars for %s in either file" % DAY)
st=3*60
w=[bars[m] for m in range(st,st+15)]
hi=max(x[1] for x in w); lo=min(x[2] for x in w); rng=hi-lo
cp=(w[-1][3]-lo)/rng
sig=None
for k in range(st+15, st+30):
    if bars[k][3]>hi: sig=(k,True); break
    if bars[k][3]<lo: sig=(k,False); break
k,buy=sig
score = cp if buy else 1-cp
e=bars[k+1][0]; lvl=hi if buy else lo
sl0=lvl-rng*SL_FRAC if buy else lvl+rng*SL_FRAC
risk=abs(e-sl0); tp=e+RR*risk if buy else e-RR*risk
sgn=1 if buy else -1
sl=sl0; moved=False; R=None; exit_i=None; exit_px=None; reason=""
move_i=None
for j in range(k+1,k+1+HOLD+1):
    if j not in bars: break
    o,h,l,c=bars[j]
    adv=l if buy else h; fav=h if buy else l
    if (adv-sl)*sgn<=0:
        R=(sl-e)*sgn/risk; exit_i, exit_px = j, sl
        reason="stop moved to -0.5R" if moved else "stop loss"; break
    if MOVE_AT>0 and not moved and (fav-e)*sgn>=MOVE_AT*risk:
        moved=True; move_i=j; sl=e+sgn*MOVE_TO*risk
        if (adv-sl)*sgn<=0:
            R=(sl-e)*sgn/risk; exit_i, exit_px = j, sl; reason="stop moved to -0.5R"; break
    if (fav-tp)*sgn>=0:
        R=RR; exit_i, exit_px = j, tp; reason="target"; break
    last_i, last_c = j, c
if R is None:
    R=(last_c-e)*sgn/risk; exit_i, exit_px = last_i, last_c; reason="60-min hold cap"

win = R>0
ACC, POS, NEG, INK, MUT = "#8a6d3b", "#1f6b45", "#a33a2c", "#1b1a18", "#6b6660"
fig = plt.figure(figsize=(13,7.4), facecolor="white")
gs  = fig.add_gridspec(1,2,width_ratios=[3.15,1],wspace=0.22)
ax  = fig.add_subplot(gs[0]); qx = fig.add_subplot(gs[1])

lastx = (exit_i or k+30) + 8
xs = [m for m in sorted(bars) if st-3 <= m <= lastx]
for m in xs:
    o,h,l,c = bars[m]
    up = c>=o
    col = POS if up else NEG
    ax.plot([m,m],[l,h], color=col, lw=.8, solid_capstyle="butt", alpha=.85)
    ax.add_patch(Rectangle((m-.34, min(o,c)), .68, max(abs(c-o),rng*0.002),
                           facecolor=col if up else "white", edgecolor=col, lw=.8))

ax.add_patch(Rectangle((st-0.5, lo), 15, rng, facecolor=ACC, alpha=.10, edgecolor="none"))
ax.axhline(hi, color=INK, lw=1.1, alpha=.55); ax.axhline(lo, color=INK, lw=1.1, alpha=.55)
ax.text(st-3.4, hi, "high %.2f"%hi, va="bottom", ha="left", fontsize=8.5, color=MUT)
ax.text(st-3.4, lo, "low %.2f"%lo, va="top", ha="left", fontsize=8.5, color=MUT)
ax.axvline(st+14.5, color=ACC, lw=1, ls=":", alpha=.8)
ax.text(st+7, hi+rng*.10, "15-min range", ha="center", fontsize=9.5, color=ACC, fontweight="bold")

# reward / risk bands
ax.add_patch(Rectangle((k+1, min(e,tp)), lastx-(k+1), abs(tp-e), facecolor=POS, alpha=.11, edgecolor="none"))
ax.add_patch(Rectangle((k+1, min(e,sl0)), lastx-(k+1), abs(e-sl0), facecolor=NEG, alpha=.11, edgecolor="none"))
ax.axhline(e,   color=ACC, lw=1.4)
ax.axhline(sl0, color=NEG, lw=1.3, ls="--")
ax.axhline(tp,  color=POS, lw=1.3, ls="--")
if moved:
    ax.hlines(sl, move_i, exit_i, color=NEG, lw=1.3, alpha=.75)
    ax.text(move_i+.4, sl, " stop -> -0.5R", va="bottom", fontsize=8.5, color=NEG)
for y,lab,col in ((e,"entry %.2f"%e,ACC),(sl0,"stop %.2f  (-1R)"%sl0,NEG),(tp,"target %.2f  (+2R)"%tp,POS)):
    ax.text(lastx+.6, y, " "+lab, va="center", fontsize=9, color=col, fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.6))
ax.plot([k+1],[e], marker="^" if buy else "v", ms=11, color=ACC, zorder=5)
ax.plot([exit_i],[exit_px], marker="X", ms=11, color=POS if win else NEG, zorder=5)
ax.text(exit_i, exit_px + rng*(.09 if win else -.13), reason, ha="center", fontsize=9,
        color=POS if win else NEG, fontweight="bold")

ticks=[m for m in range(st, lastx+1, 10)]
ax.set_xticks(ticks); ax.set_xticklabels(["%02d:%02d"%((m-180)//60,(m-180)%60) for m in ticks], fontsize=9)
ax.set_xlim(st-4, lastx+13); ax.set_ylabel("XAUUSD", fontsize=10, color=MUT)
ax.set_title("%s  %s   Asia 00:00 UTC   %s"
             % (DAY.strftime("%d %B %Y"), DAY.strftime("%A"), "WIN" if win else "LOSS"),
             fontsize=14, fontweight="bold", color=POS if win else NEG, loc="left", pad=14)
ax.text(0,1.005,"", transform=ax.transAxes)
ax.grid(axis="y", alpha=.13); ax.set_axisbelow(True)
for sp in ("top","right"): ax.spines[sp].set_visible(False)
ax.spines["left"].set_color("#ddd"); ax.spines["bottom"].set_color("#ddd")
ax.text(.5,-.115,"times shown in UTC", transform=ax.transAxes, ha="center", fontsize=8.5, color=MUT)

# ---- quadrant panel ----
qx.set_xlim(0,1); qx.set_ylim(-0.03,1.03); qx.axis("off")
qx.text(.5,1.0,"Close-position quadrant", ha="center", fontsize=11, fontweight="bold", color=INK)
labels=[("above 75%",.75,1.0,POS,"+0.529 R   50% WR"),
        ("50 - 75%",.50,.75,MUT,"+0.210 R   36% WR"),
        ("25 - 50%",.25,.50,MUT,"+0.217 R   37% WR"),
        ("below 25%",0,.25,NEG,"-0.816 R    0% WR")]
for lab,a,b_,col,note in labels:
    live = a <= score < b_ or (b_==1.0 and score>=a)
    qx.add_patch(Rectangle((.10, a*.82+.06), .62, (b_-a)*.82,
                 facecolor=col, alpha=.30 if live else .07,
                 edgecolor=col if live else "#ccc", lw=2 if live else .8))
    qx.text(.41, (a+(b_-a)/2)*.82+.06, lab, ha="center", va="center",
            fontsize=10, fontweight="bold" if live else "normal", color=INK)
    qx.text(.41, (a+(b_-a)/2)*.82+.06-.038, note, ha="center", va="center", fontsize=8, color=MUT)
qx.annotate("this session\n%.3f"%score, xy=(.72, score*.82+.06), xytext=(.90, score*.82+.06),
            ha="left", va="center", fontsize=9.5, fontweight="bold", color=ACC,
            arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.6))
qx.text(.41,.015,"filter passes at >= 0.25", ha="center", fontsize=8.5, color=MUT, style="italic")

out=os.path.expanduser("~/orb/strategy/research/trade_%s.png"%DAY.isoformat())
plt.savefig(out, dpi=155, bbox_inches="tight", facecolor="white")
print("%s  %s" % (DAY, DAY.strftime("%A")))
print("  range      %.2f / %.2f  (%.0f pts)" % (hi,lo,rng/0.01))
print("  00:14 close %.2f  -> score %.3f" % (w[-1][3], score))
print("  break %s at %02d:%02d, entry %.2f" % ("UP" if buy else "DOWN",(k+1-180)//60,(k+1-180)%60,e))
print("  stop %.2f   target %.2f   risk %.2f" % (sl0,tp,risk))
print("  exit %.2f at %02d:%02d via %s" % (exit_px,(exit_i-180)//60,(exit_i-180)%60,reason))
print("  RESULT     %s  %+.3f R" % ("WIN" if win else "LOSS", R))
print("  saved      %s" % out)
