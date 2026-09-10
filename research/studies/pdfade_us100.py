"""The previous-day level fade on US100.cash at the New York cash open.

Same code as the gold study, only the symbol, the spread and the session window
change. The window is given in BROKER minutes because broker time is New York
plus seven hours all year -- both switch on US dates -- so a broker window needs
no daylight-saving handling at all.
"""
import csv, os, sys, datetime as dt, statistics as st
from collections import defaultdict
D = os.path.expanduser("~/.wine_mt5/drive_c/users/%s/AppData/Roaming/MetaQuotes"
                       "/Terminal/Common/Files" % os.environ["USER"])

def load(fn, minbars):
    days = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(D, fn))):
        t = dt.datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
        days[t.date()].append((t.hour*60+t.minute, float(r["open"]), float(r["high"]),
                               float(r["low"]), float(r["close"])))
    return {d: sorted(v) for d, v in days.items() if len(v) >= minbars}

def run(days, ds, tf, win, slf, rr, spread, depth_frac=None, year=2026):
    out = []
    for i in range(1, len(ds)):
        c, p = ds[i], ds[i-1]
        if c.year != year: continue
        ph = max(x[2] for x in days[p]); pl = min(x[3] for x in days[p]); rg = ph - pl
        if rg <= 0: continue
        for lvl, sgn in ((pl, -1), (ph, 1)):
            d_ = -sgn; state = 0; ei = None; entry = None
            for k, (mi, o, h, l, cl) in enumerate(days[c]):
                if not (win[0] <= mi < win[1]): continue
                if state == 0:
                    if (h >= lvl if sgn > 0 else l <= lvl): state = 1
                    continue
                if (mi+1) % tf == 0 and (cl < lvl if sgn > 0 else cl > lvl):
                    ei = k; entry = cl + (spread if d_ > 0 else 0.0); break
            if ei is None: continue
            if depth_frac is not None and abs(entry-lvl) > depth_frac*rg: continue
            sl = lvl + sgn*slf*rg; risk = abs(entry-sl)
            if risk <= 0: continue
            tp = entry + d_*rr*risk
            R = None
            for mi, o, h, l, cl in days[c][ei+1:]:
                adv = l if d_ > 0 else h + spread
                fav = h if d_ > 0 else l
                if (adv-sl)*d_ <= 0: R = -1.0; break
                if (fav-tp)*d_ >= 0: R = rr; break
            if R is None: R = (days[c][-1][4]-entry)*d_/risk
            out.append((c, R))
    return out

def line(lab, t, B=0.10):
    R = [x[1] for x in t]
    if len(R) < 25: print("  %-34s only %d trades" % (lab, len(R))); return None
    w = [x for x in R if x > B]; l = [x for x in R if x < -B]
    if not w or not l: return None
    aw = sum(w)/len(w); al = sum(l)/len(l); need = 100/(1+aw/abs(al))
    wr = 100*len(w)/(len(w)+len(l))
    mo = defaultdict(list)
    for c, x in t: mo[c.strftime("%b")].append(x)
    pos = len([1 for v in mo.values() if sum(v) > 0])
    pk = r = dd = 0
    for x in R:
        r += x; pk = max(pk, r); dd = max(dd, pk-r)
    se = st.pstdev(R)/len(R)**0.5
    print("  %-34s %3d %2d/%2d/%2d %5.1f%% %4.1f%% %+5.1f %+.3f %+6.1f %d/%d %4.1f %+.2f"
          % (lab, len(R), len(w), len(l), len(R)-len(w)-len(l), wr, need, wr-need,
             sum(R)/len(R), sum(R), pos, len(mo), dd, (sum(R)/len(R))/se))
    return sum(R)/len(R)

U = load("bars_US100.cash.csv", 400)
ds = sorted(U)
n = [len(v) for v in U.values()]
print("US100.cash: %d days kept, %s .. %s, bars/day median %d (min %d, max %d)\n"
      % (len(U), ds[0], ds[-1], st.median(n), min(n), max(n)))
SP = 1.45          # 145 points, the median spread FINDINGS section 13 measured
NY = (16*60+30, 23*60)     # broker minutes = New York 09:30-16:00
print("NY cash open, broker 16:30-23:00. Spread 145 pts. 2026.")
print("  config                              n  W/ L/BE    WR    need cush   EV   total +mth maxDD    t")
best = None
for tf in (1, 3, 5, 15, 30):
    for slf in (0.15, 0.25, 0.33, 0.50):
        for rr in (1.5, 2.0):
            e = line("M%-2d  %.2f x range  RR%.1f" % (tf, slf, rr),
                     run(U, ds, tf, NY, slf, rr, SP))
            if e is not None and (best is None or e > best[0]): best = (e, tf, slf, rr)
print("\n  best: M%d, %.2f x range, RR %.1f -> %+.3f R per trade" % (best[1], best[2], best[3], best[0]))
print("\nSame best config, with the depth filter and in other windows:")
print("  config                              n  W/ L/BE    WR    need cush   EV   total +mth maxDD    t")
_, tf, slf, rr = best
for df, lab in ((None, "no depth filter"), (0.10, "depth <= 0.10 x range"),
                (0.06, "depth <= 0.06 x range"), (0.03, "depth <= 0.03 x range")):
    line("NY  %-28s" % lab, run(U, ds, tf, NY, slf, rr, SP, df))
for w, lab in (((0, 1440), "all day"), ((0, 16*60+30), "before the cash open"),
               ((16*60+30, 20*60), "first 3.5h of NY")):
    line("%-32s" % lab, run(U, ds, tf, w, slf, rr, SP))
