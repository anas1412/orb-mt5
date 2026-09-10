"""Fading the previous day's high and low: the full parameter search.

    sweep     price trades beyond the previous day's high or low
    confirm   a candle of timeframe TF CLOSES back inside the level
    entry     a limit at the level; price must come back to it
    stop      SL, one of three families -- a fraction of the previous day's
              range, a fixed number of points, or a multiple of daily ATR(14)
    target    RR x the stop distance
    exit      stop, target, or the day's close

Searched on 2024-2025 and then checked on 2026, because a grid this size will
always hand back a winning cell on one period.

Held to the close, flat 50-point spread, one fill per level per day.

    python3 studies/pdsweep.py
"""
import csv, os, sys, datetime as dt, statistics as st
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim_offline import broker_offset

D = os.path.expanduser("~/.wine_mt5/drive_c/users/%s/AppData/Roaming/MetaQuotes"
                       "/Terminal/Common/Files" % os.environ["USER"])
SPREAD  = 0.50
TFS     = (3, 5, 15, 30, 60)
SESS    = {"all day": None, "Asia 00-08": (0, 480), "Asia+London 00-16": (0, 960),
           "London 07-16": (420, 960), "New York 13-21": (780, 1260)}
RRS     = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
# (family, value). range = fraction of the previous day's range; pts = dollars;
# atr = multiple of daily ATR(14). All measured from the level, outward.
SLS     = ([("range", f) for f in (0.15, 0.25, 0.33, 0.50)] +
           [("pts",   v) for v in (3.0, 5.0, 8.0, 12.0)] +
           [("atr",   m) for m in (0.25, 0.50, 0.75, 1.00)])
IN, OUT = (2024, 2025), (2026,)


def load():
    days = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(D, "bars_XAUUSD.csv"))):
        t = dt.datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
        days[t.date()].append((t.hour * 60 + t.minute, float(r["open"]),
                               float(r["high"]), float(r["low"]), float(r["close"])))
    # A short day is a holiday or a feed gap; its high and low are not the day's
    # range and would hand the next session a level built from nothing.
    return {d: v for d, v in days.items() if len(v) >= 600}


def atr14(days, ds):
    """Daily ATR(14), as at the end of each day -- so it is known before the
    session that uses it."""
    out, trs, pc = {}, [], None
    for d in ds:
        b = days[d]
        h = max(x[2] for x in b); l = min(x[3] for x in b); c = b[-1][4]
        trs.append(max(h - l, abs(h - pc), abs(pc - l)) if pc is not None else h - l)
        pc = c
        out[d] = sum(trs[-14:]) / len(trs[-14:])
    return out


def entries(days, ds, tf, window):
    """Every (day, side, level, bar index of the fill) this confirmation and
    session window produces. Independent of the stop, so it is found once."""
    got = []
    for i in range(1, len(ds)):
        p, c = ds[i - 1], ds[i]
        ph = max(x[2] for x in days[p]); pl = min(x[3] for x in days[p])
        if ph - pl <= 0:
            continue
        w = None
        if window:
            off = broker_offset(c) * 60
            w = (window[0] + off, window[1] + off)
        for lvl, sgn in ((pl, -1), (ph, 1)):
            state = 0
            for k, (mi, o, h, l, cl) in enumerate(days[c]):
                if w and not (w[0] <= mi < w[1]):
                    continue
                if state == 0:
                    if (h >= lvl if sgn > 0 else l <= lvl):
                        state = 1
                    continue
                if state == 1:
                    # only a candle that CLOSES the timeframe may confirm
                    if (mi + 1) % tf == 0 and (cl < lvl if sgn > 0 else cl > lvl):
                        state = 2
                    continue
                # The retest runs the SAME way the sweep did. After a high is
                # swept and price closes back below it, a limit sell at that
                # high fills only when price comes back UP to it -- inverting
                # this books a fill at the level while the market is already
                # past it, which is free money and is not available.
                if (h >= lvl if sgn > 0 else l <= lvl):
                    got.append((c, p, lvl, sgn, k))
                    break
    return got


def paths(days, got, rng_of, risk_of):
    """One walk per entry per stop. Records how far the trade ran in favour
    before the stop, so every RR resolves from the same walk instead of
    re-reading the bars once per target."""
    out = []
    for c, p, lvl, sgn, k in got:
        risk = risk_of(c, p)
        if risk <= 0:
            continue
        d_ = -sgn
        entry = lvl + (SPREAD if sgn < 0 else 0.0)
        sl = lvl + sgn * risk
        r = abs(entry - sl)
        mfe, stopped, eod = 0.0, False, 0.0
        for mi, o, h, l, cl in days[c][k:]:
            # a short's stop sits on the ask while the candle draws the bid
            adv = l if d_ > 0 else h + SPREAD
            fav = h if d_ > 0 else l
            if (adv - sl) * d_ <= 0:          # stop checked first, so a bar that
                stopped = True; break         # does both counts as a loss
            mfe = max(mfe, (fav - entry) * d_ / r)
        else:
            eod = (days[c][-1][4] - entry) * d_ / r
        out.append((mfe, stopped, eod))
    return out


def score(pth, rr):
    R = [rr if m >= rr else (-1.0 if s else e) for m, s, e in pth]
    if not R:
        return None
    w = [x for x in R if x > 0]
    return dict(n=len(R), wr=100.0 * len(w) / len(R), tot=sum(R), ev=sum(R) / len(R),
                se=st.pstdev(R) / len(R) ** 0.5)


if __name__ == "__main__":
    days = load(); ds = sorted(days); atr = atr14(days, ds)
    rng = lambda c, p: max(x[2] for x in days[p]) - min(x[3] for x in days[p])
    RISK = {"range": lambda f: (lambda c, p: f * rng(c, p)),
            "pts":   lambda v: (lambda c, p: v),
            "atr":   lambda m: (lambda c, p: m * atr[p])}
    print("XAUUSD M1 %s..%s | search on %s, check on %s | %d cells\n"
          % (ds[0], ds[-1], "+".join(map(str, IN)), OUT[0],
             len(TFS) * len(SESS) * len(SLS) * len(RRS)))
    rows = []
    for tf in TFS:
        for sname, w in SESS.items():
            gi = [g for g in entries(days, ds, tf, w) if g[0].year in IN]
            go = [g for g in entries(days, ds, tf, w) if g[0].year in OUT]
            for fam, val in SLS:
                pi = paths(days, gi, rng, RISK[fam](val))
                po = paths(days, go, rng, RISK[fam](val))
                for rr in RRS:
                    a, b = score(pi, rr), score(po, rr)
                    if a and b and a["n"] >= 80 and b["n"] >= 40:
                        rows.append((a["ev"], tf, sname, fam, val, rr, a, b))
    rows.sort(reverse=True)
    print("TOP 12 BY 2024-2025, WITH 2026 SHOWN COLD")
    print("  conf  session             stop            RR  |  in-sample        "
          "|  2026 out-of-sample")
    for ev, tf, sname, fam, val, rr, a, b in rows[:12]:
        print("  M%-3d  %-18s %-4s %-5.2f     %.1f  |  %4d %+.3f t%+.1f  |  "
              "%4d %+.3f t%+.1f  %+6.1f R"
              % (tf, sname, fam, val, rr, a["n"], a["ev"], a["ev"] / a["se"],
                 b["n"], b["ev"], b["ev"] / b["se"], b["tot"]))
    keep = [r for r in rows[:12] if r[7]["ev"] > 0]
    print("\n  %d of the top 12 stayed positive on 2026." % len(keep))
    print("\nBEST STOP FAMILY (median in-sample EV across every other choice)")
    for fam in ("range", "pts", "atr"):
        v = [r[0] for r in rows if r[3] == fam]
        if v: print("  %-6s %4d cells   median %+.3f   best %+.3f" % (fam, len(v), st.median(v), max(v)))
    print("\nBEST CONFIRMATION TIMEFRAME (median in-sample EV)")
    for tf in TFS:
        v = [r[0] for r in rows if r[1] == tf]
        if v: print("  M%-3d   %4d cells   median %+.3f   best %+.3f" % (tf, len(v), st.median(v), max(v)))
    print("\nBEST SESSION (median in-sample EV)")
    for s in SESS:
        v = [r[0] for r in rows if r[2] == s]
        if v: print("  %-18s %4d cells   median %+.3f   best %+.3f" % (s, len(v), st.median(v), max(v)))
    print("\nBEST RR (median in-sample EV)")
    for rr in RRS:
        v = [r[0] for r in rows if r[5] == rr]
        if v: print("  RR %-4.1f %4d cells   median %+.3f   best %+.3f" % (rr, len(v), st.median(v), max(v)))
