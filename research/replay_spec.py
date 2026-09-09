"""Replay a spec over raw M1 bars and write the trade CSVs the pipeline reads.

The Strategy Tester is the source of truth for a published report -- real ticks,
real spreads. This is the alternative for a spec the tester cannot run: a stop
placed at a candle's extreme, or any study where re-running the tester is not
worth it. It writes the same columns `run_window.sh` produces, so
report_data.py / all_trades.py / build_report.py / check_charts.py all work
unchanged.

    ORB_SPEC=strategies/x.toml python3 replay_spec.py

Costs: the spread is applied to the adverse price the same way `sim_offline`
and `check_charts` apply it -- a short's stop sits on the ASK while the candles
draw the BID -- and the commission is taken off the R afterwards. Doing it any
other way makes check_charts disagree about whether a stop was reached.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import csv, datetime as dt
import ctx, spec as S
from mt5paths import bars as barsfile

SPREAD = 0.50          # dollars, the tester CSV averages about 50 points
COMM   = 0.10          # $/oz round turn: $10 per 100-oz lot, swap-free metals
TF     = S.TF[ctx.SIGNAL_TF]
DIR    = ctx.DIRECTION
SLPCT  = float(ctx.SPEC["rules"]["sl_pct_of_range"])
MOVE_AT = float(ctx.SPEC["rules"]["stop_move_at_r"])
MOVE_TO = float(ctx.SPEC["rules"]["stop_move_to_r"])

bars = {}
for row in csv.DictReader(open(barsfile(ctx.SYMBOL))):
    t = dt.datetime.strptime(row["time"], "%Y.%m.%d %H:%M")
    bars.setdefault(t.date(), {})[t.hour * 60 + t.minute] = (
        float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]))


def candle(b, s, n):
    """The n-minute candle starting at minute s, or None if a bar is missing."""
    if any(m not in b for m in range(s, s + n)):
        return None
    return (b[s][0], max(b[m][1] for m in range(s, s + n)),
            min(b[m][2] for m in range(s, s + n)), b[s + n - 1][3])


def session(d):
    """One day's trade, or None. Mirrors ORB.mq5's order of decisions."""
    if d.weekday() not in ctx.WEEKDAYS:
        return None
    b = bars.get(d)
    if not b:
        return None
    st = ctx.session_start(d)
    rc = candle(b, st, ctx.RANGE_MIN)
    if not rc:
        return None
    hi, lo = rc[1], rc[2]
    if hi <= lo:
        return None
    close_pos = (rc[3] - lo) / (hi - lo)

    # the break: the first signal-timeframe candle to CLOSE outside the box,
    # checked on candles that start after the range and close inside the window
    sig = None
    k = ctx.RANGE_MIN
    while k + TF <= ctx.RANGE_MIN + ctx.ENTRY_MIN:
        cc = candle(b, st + k, TF)
        if not cc:
            break
        if cc[3] > hi:
            sig = (k + TF, True); break
        if cc[3] < lo:
            sig = (k + TF, False); break
        k += TF
    if sig is None:
        return None
    off, buy = sig                       # off = minutes after the range OPEN
    if ctx.HALF_FILTER and buy != (close_pos >= 0.50):
        return None                      # wrong half, and that ends the day
    if DIR == "long" and not buy:
        return None
    if DIR == "short" and buy:
        return None
    if st + off not in b:
        return None

    g = 1 if buy else -1
    e = b[st + off][0]
    sl = (hi - SLPCT / 100.0 * (hi - lo)) if buy else (lo + SLPCT / 100.0 * (hi - lo))
    risk = (e - sl) * g
    if risk <= SPREAD:
        return None                      # a stop inside the spread is not a trade
    tp = e + g * ctx.RR * risk

    cur, armed, res, kind, lvl = sl, False, None, None, sl
    gap = None
    for m in range(st + off, st + off + ctx.HOLD + 1):
        if m not in b:
            # The bars ran out before a level was reached. Close there and say
            # so, rather than dropping the trade -- dropping only the ones that
            # had not resolved keeps the fast winners and is how a 87%-win-rate
            # setup got invented once already.
            gap = m - 1
            break
        o, h, l, c = b[m]
        adv = l if buy else h + SPREAD   # a short's stop sits on the ask
        fav = h if buy else l
        if (adv - cur) * g <= 0:
            res, kind, lvl = (cur - e) * g / risk, "sl", cur; break
        if MOVE_AT and not armed and (fav - e) * g >= MOVE_AT * risk:
            armed, cur = True, e + g * MOVE_TO * risk
            if (adv - cur) * g <= 0:
                res, kind, lvl = MOVE_TO, "sl", cur; break
        if (fav - tp) * g >= 0:
            res, kind, lvl = ctx.RR, "tp", tp; break
    if res is None:
        last = gap if gap is not None else st + off + ctx.HOLD
        if last not in b or last <= st + off:
            return None
        lvl = b[last][3]
        res, kind = (lvl - e) * g / risk, "hold"
    return dict(t=dt.datetime.combine(d, dt.time(0, 0)) + dt.timedelta(minutes=st + off),
                dir="buy" if buy else "sell", entry=e, sl=sl, risk=risk,
                R=res - COMM / risk, exit="%s %.2f" % (kind, lvl),
                range_pts=int(round((hi - lo) / 0.01)), close_pos=close_pos,
                mins=off - ctx.RANGE_MIN)


rows = [t for t in (session(d) for d in sorted(bars) if ctx.in_range(d)) if t]
kinds = {}
for r in rows:
    kinds[r["exit"].split()[0]] = kinds.get(r["exit"].split()[0], 0) + 1
bal = ctx.DEPOSIT
out = []
for r in rows:
    rm = bal * ctx.RISK / 100.0
    pm = r["R"] * rm
    bal += pm
    out.append(dict(entry_time=r["t"].strftime("%Y.%m.%d %H:%M"), range_pts=r["range_pts"],
                    spread_pts=int(round(SPREAD / 0.01)), mins_after_range=r["mins"],
                    dir=r["dir"], entry=round(r["entry"], 2), sl=round(r["sl"], 2),
                    risk_money=round(rm, 2), profit_money=round(pm, 2), R=round(r["R"], 3),
                    exit=r["exit"], close_pos=round(r["close_pos"], 3)))

os.makedirs(ctx.OUT_DIR, exist_ok=True)
cols = ["entry_time", "range_pts", "spread_pts", "mins_after_range", "dir", "entry", "sl",
        "risk_money", "profit_money", "R", "exit", "close_pos"]
for path in (ctx.CSV_LIVE, ctx.CSV_ALL):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(out)
print("replayed %s: %d trades, %+.1f R, %s .. %s"
      % (ctx.NAME, len(out), sum(r["R"] for r in out),
         out[0]["entry_time"][:10] if out else "-", out[-1]["entry_time"][:10] if out else "-"))
print("  exits: " + ", ".join("%s %d" % kv for kv in sorted(kinds.items())))
print("  wrote %s" % ctx.CSV_LIVE)
