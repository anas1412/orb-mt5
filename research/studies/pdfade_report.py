"""The previous-day level fade: every 2026 trade, its chart, and the report.

Standalone. It does not touch the ORB pipeline -- different rules, different
data, its own page and its own trade folder.

    entry    price sweeps yesterday's high or low, an M5 candle CLOSES back
             inside, and you take that close at market
    skip     if that close landed more than 600 points past the level
    stop     yesterday's range / 3, beyond the level
    target   RR x risk (2.5)
    exit     the day's close if neither is hit
    hours    00:00-08:00 UTC, Tuesday to Friday

    python3 studies/pdfade_report.py [--all]
"""
import os, sys, csv, json, math, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE); REPO = os.path.dirname(RESEARCH)
sys.path.insert(0, RESEARCH); sys.path.insert(0, os.path.join(RESEARCH, "lib"))
from sim_offline import broker_offset
from mt5paths import COMMON as D
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from collections import defaultdict
import statistics as st

YEAR      = 2026
TF        = 5          # confirmation candle
WINDOW    = (0, 480)   # UTC minutes: Asia 00:00-08:00
SL_FRAC   = 0.33       # of yesterday's range, beyond the level
RR        = 2.5
MAX_DEPTH = 6.00       # 600 points; skip a close that ran further back inside
# Monday is out. Its levels come from FRIDAY, with a whole weekend in between,
# so the high and low it fades are three days stale. Measured: Monday returned
# -0.050 R a trade against +0.527 for the rest, and dropping it lifts the
# simulated pass rate from 82.0% to 84.2% while halving the failure rate.
DAYS      = (1, 2, 3, 4)   # Tue-Fri, as Python weekdays
SPREAD    = 0.50
OUT_DIR   = os.path.join(REPO, "trades-pdfade")
OUT_WEB   = "trades-pdfade"
PAGE      = os.path.join(REPO, "pdfade.html")
INK="#141310"; MUT="#8a837a"; POS="#12694a"; NEG="#a8352a"; ACC="#8a6d3b"; GRID="#ece7dd"


def load_bars():
    days = defaultdict(list)
    for src in ("bars_XAUUSD.csv", "bars_XAUUSD_extra.csv"):
        p = os.path.join(D, src)
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p)):
            t = dt.datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
            days[t.date()].append((t.hour*60+t.minute, float(r["open"]),
                                   float(r["high"]), float(r["low"]), float(r["close"])))
    # A short day is a holiday or a feed gap; its high and low are not the
    # day's range and would hand the next session a level built from nothing.
    return {d: sorted(v) for d, v in days.items() if len(v) >= 600}


def find_trades(days, ds):
    out = []
    for i in range(1, len(ds)):
        c, p = ds[i], ds[i-1]
        if c.year != YEAR or c.weekday() not in DAYS:
            continue
        ph = max(x[2] for x in days[p]); pl = min(x[3] for x in days[p])
        rg = ph - pl
        if rg <= 0:
            continue
        off = broker_offset(c) * 60
        w = (WINDOW[0] + off, WINDOW[1] + off)
        for lvl, sgn in ((pl, -1), (ph, 1)):
            d_ = -sgn                      # sweep up -> sell, sweep down -> buy
            state = 0; ei = None; sweep_i = None; extreme = None
            for k, (mi, o, h, l, cl) in enumerate(days[c]):
                if not (w[0] <= mi < w[1]):
                    continue
                if state == 0:
                    if (h >= lvl if sgn > 0 else l <= lvl):
                        state = 1; sweep_i = k; extreme = h if sgn > 0 else l
                    continue
                extreme = max(extreme, h) if sgn > 0 else min(extreme, l)
                if (mi + 1) % TF == 0 and (cl < lvl if sgn > 0 else cl > lvl):
                    ei = k; entry = cl + (SPREAD if d_ > 0 else 0.0); break
            if ei is None:
                continue
            depth = abs(entry - lvl)
            if depth > MAX_DEPTH:
                continue
            sl = lvl + sgn * SL_FRAC * rg
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + d_ * RR * risk
            R = None; xi = len(days[c]) - 1; xp = None
            for j in range(ei + 1, len(days[c])):
                mi, o, h, l, cl = days[c][j]
                adv = l if d_ > 0 else h + SPREAD
                fav = h if d_ > 0 else l
                if (adv - sl) * d_ <= 0:
                    R = -1.0; xi = j; xp = sl; break
                if (fav - tp) * d_ >= 0:
                    R = RR; xi = j; xp = tp; break
            if R is None:
                xp = days[c][-1][4]; R = (xp - entry) * d_ / risk
            out.append(dict(date=c, prev=p, buy=d_ > 0, lvl=lvl, ph=ph, pl=pl, rg=rg,
                            entry=entry, sl=sl, tp=tp, risk=risk, R=R, depth=depth,
                            ei=ei, xi=xi, xp=xp, sweep_i=sweep_i, extreme=extreme,
                            kind=("tp" if abs(R-RR) < 1e-9 else "sl" if R <= -0.999 else "eod")))
    out.sort(key=lambda t: (t["date"], t["ei"]))
    return out


def place(levels, span):
    """Nudge labels apart vertically so two levels a few points apart do not
    print on top of each other. levels = [(y, colour, text, bold)]."""
    gap = span * 0.055
    items = sorted(levels, key=lambda z: z[0])
    ys = [it[0] for it in items]
    for i in range(1, len(ys)):
        if ys[i] - ys[i-1] < gap:
            ys[i] = ys[i-1] + gap
    return [(items[i][0], ys[i]) + items[i][1:] for i in range(len(items))]


def to_m5(bars):
    """M1 into M5, aligned to the clock, because the rule is an M5 CLOSE --
    drawing M1 shows a candle the strategy never looks at."""
    out = {}
    for mi, o, h, l, c in bars:
        k = mi // 5
        if k in out:
            p = out[k]
            out[k] = (p[0], p[1], max(p[2], h), min(p[3], l), c)
        else:
            out[k] = (k*5, o, h, l, c)
    return [out[k] for k in sorted(out)]


def draw(t, bars, n):
    b = bars[t["date"]]
    a = max(0, t["sweep_i"] - 12); z = min(len(b) - 1, t["xi"] + 8)
    m5 = to_m5(b[a:z+1])
    if len(m5) < 4:
        return None
    x0 = m5[0][0]
    mid = (t["ph"] + t["pl"]) / 2.0
    fig, ax = plt.subplots(figsize=(11.8, 5.7), dpi=105)
    # The middle of yesterday's range is what the trade is fading towards, so
    # it is always drawn even when the target overshoots it.
    keep = [t["sl"], t["tp"], t["entry"], mid, t["lvl"]]
    lo_ = min([x[3] for x in m5] + keep)
    hi_ = max([x[2] for x in m5] + keep)
    span = hi_ - lo_
    xr = m5[-1][0] - x0
    step = next(s for s in (15, 30, 60, 120, 180, 240) if xr / s <= 14) if xr > 210 else 15
    for mi, o, h, l, cl in m5:
        x = mi - x0 + 2.5; up = cl >= o; col = POS if up else NEG
        ax.plot([x, x], [l, h], color=col, lw=1.0, solid_capstyle="butt", zorder=2)
        ax.add_patch(Rectangle((x-1.7, min(o, cl)), 3.4, max(abs(cl-o), span*.0025),
                     facecolor=col if up else "white", edgecolor=col, lw=1.0, zorder=3))
    ax.axvspan(b[t["sweep_i"]][0]-x0, b[t["ei"]][0]-x0+5, color=ACC, alpha=.07, zorder=0)
    lv = [(t["entry"], ACC, "entry  %.2f" % t["entry"], True),
          (t["sl"], NEG, "stop  %.2f   \u22121R" % t["sl"], True),
          (t["tp"], POS, "target  %.2f   +%gR" % (t["tp"], RR), True),
          (mid, MUT, "mid of yesterday  %.2f" % mid, False),
          (t["lvl"], INK, "yesterday's %s  %.2f" % ("low" if t["buy"] else "high", t["lvl"]), False)]
    far = t["ph"] if t["buy"] else t["pl"]
    if lo_ - span*.04 <= far <= hi_ + span*.04:
        lv.append((far, MUT, "yesterday's %s  %.2f" % ("high" if t["buy"] else "low", far), False))
    pad = span * .11
    ax.set_ylim(lo_ - pad, hi_ + pad)
    for y0, ytxt, col, lab, bold in place(lv, span):
        ax.plot([-4, xr+4.5], [y0, y0], color=col, ls="--" if bold else "-",
                lw=1.15 if bold else 1.0, alpha=.85, zorder=1)
        ax.plot([xr+5.5, xr+xr*0.035+7], [y0, ytxt], color=col, lw=.7, alpha=.45, zorder=1)
        ax.text(xr + xr*0.045 + 8, ytxt, lab, color=col, fontsize=9, va="center",
                weight="bold" if bold else "normal")
    ax.plot([b[t["ei"]][0]-x0+2.5], [t["entry"]], marker="^" if t["buy"] else "v", ms=12,
            color=ACC, zorder=6, markeredgecolor="white", markeredgewidth=.9)
    win = t["R"] > 0
    ax.plot([b[t["xi"]][0]-x0+2.5], [t["xp"]], marker="X", ms=11, color=POS if win else NEG,
            zorder=6, markeredgecolor="white", markeredgewidth=.9)
    res = "%s   %+.2f R" % ("WIN" if win else "LOSS", t["R"])
    ax.set_title("%s   \u00b7   %s   \u00b7   %s   \u2014   %s"
                 % (t["date"].strftime("%d %B %Y"), t["date"].strftime("%A"),
                    "LONG" if t["buy"] else "SHORT", res),
                 fontsize=14, color=POS if win else NEG, weight="bold", loc="left", pad=16)
    ax.text(0, 1.02, "M5 candles   \u00b7   swept the %s   \u00b7   closed %.0f pts back inside   \u00b7   "
            "yesterday's range %.0f pts   \u00b7   risk %.0f pts   \u00b7   held %d min   \u00b7   trade %d"
            % ("low" if t["buy"] else "high", t["depth"]/0.01, t["rg"]/0.01,
               t["risk"]/0.01, b[t["xi"]][0]-b[t["ei"]][0], n),
            transform=ax.transAxes, fontsize=9, color=MUT)
    off = broker_offset(t["date"]) * 60
    tick = [m for m in range(0, xr+1, step)]
    ax.set_xticks(tick)
    ax.set_xticklabels(["%02d:%02d" % (((x0+m-off)//60) % 24, (x0+m) % 60) for m in tick],
                       fontsize=9)
    ax.set_xlabel("UTC", fontsize=9, color=MUT); ax.set_ylabel("XAUUSD", fontsize=9, color=MUT)
    ax.set_xlim(-5, xr + xr*0.30 + 12)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=.6, zorder=0)
    fn = "%s_%s_%s_%s.png" % (t["date"].isoformat(), "long" if t["buy"] else "short",
                              "win" if win else "loss", "hi" if not t["buy"] else "lo")
    fig.savefig(os.path.join(OUT_DIR, fn), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return fn


def hold_stats(bars, trades):
    """Hold times, the latest exit, and what an 08:00 UTC cut-off would cost."""
    import statistics as _st
    H = []; late = 0; latest = 0; cut_total = 0.0
    for t in trades:
        b = bars[t["date"]]
        h = b[t["xi"]][0] - b[t["ei"]][0]
        H.append((t["kind"], h))
        latest = max(latest, b[t["xi"]][0])
        if b[t["xi"]][0] >= 22*60:
            late += 1
        off = broker_offset(t["date"]) * 60; cut = WINDOW[1] + off
        d_ = 1 if t["buy"] else -1; R = None
        for j in range(t["ei"]+1, len(b)):
            mi, o, hi, lo, cl = b[j]
            if mi >= cut:
                R = (b[j-1][4]-t["entry"])*d_/t["risk"]; break
            adv = lo if d_ > 0 else hi + SPREAD
            fav = hi if d_ > 0 else lo
            if (adv-t["sl"])*d_ <= 0: R = -1.0; break
            if (fav-t["tp"])*d_ >= 0: R = RR; break
        cut_total += R if R is not None else (b[-1][4]-t["entry"])*d_/t["risk"]
    return dict(med=_st.median([h for _, h in H]),
                tp=_st.median([h for k, h in H if k == "tp"]),
                sl=_st.median([h for k, h in H if k == "sl"]),
                last="%02d:%02d" % (latest//60, latest%60),
                late=late, cut=round(cut_total, 1))


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    bars = load_bars(); ds = sorted(bars)
    trades = find_trades(bars, ds)
    print("%d trades in %d" % (len(trades), YEAR))
    for i, t in enumerate(trades, 1):
        t["n"] = i
        t["file"] = draw(t, bars, i)
    trades = [t for t in trades if t["file"]]
    # The page needs the trading calendar too, not just the trades: a week with
    # no trade still has to appear as a row, and "trading days" is days
    # AVAILABLE in the period, not days that produced a trade.
    json.dump(dict(
        trades=[{k: (v.isoformat() if isinstance(v, dt.date) else v)
                 for k, v in t.items() if k in ("date","buy","R","file","n","rg","risk","depth","kind")}
                for t in trades],
        days=[d.isoformat() for d in ds if d.year == YEAR and d.weekday() in DAYS],
        # Measured here rather than typed into the page, so changing RR cannot
        # leave a stale hold time in the prose.
        hold=hold_stats(bars, trades)),
        open(os.path.join(RESEARCH, "data", "pdfade_trades.json"), "w"), indent=1)
    print("drew %d charts into %s" % (len(trades), OUT_WEB))
