"""Replay the EA over raw M1 bars, for the one day the Strategy Tester cannot see.

MetaTrader's history server only serves bars up to the last COMPLETED trading
day. Today's bars exist only in the live chart series, so the tester silently
clamps its date range and the current session is simply missing. Everything
here reads the same bar file the tester would have used, so the only thing this
adds is the ability to include today.

Run it with no arguments to check it against the tester: it replays every 2026
session and compares trade for trade. Pass a date to print that one session.
"""
import csv, os, sys, datetime as dt
from mt5paths import COMMON as D

RANGE_MIN   = 15     # InpRangeMinutes
ENTRY_MIN   = 15     # InpNoEntryAfterMin, so bars 15..29 after the open
HOLD        = 90     # InpMaxHoldMinutes
MOVE_AT     = 0.5    # InpStopMoveAtR
MOVE_TO     = -0.5   # InpStopMoveToR
RR          = 2.0    # InpRR
SPREAD      = 0.50   # dollars; the tester CSV averages about 50 points


def nth(y, m, dow, n):
    if n > 0:
        d = dt.date(y, m, 1)
        return d + dt.timedelta(days=(dow - d.weekday() - 1) % 7 + (n - 1) * 7)
    d = dt.date(y, m, 28)
    while (d + dt.timedelta(days=1)).month == m:
        d += dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() + 1 - dow) % 7)


def broker_offset(d):
    """Broker is UTC+3 on US daylight saving dates, UTC+2 otherwise."""
    return 3 if nth(d.year, 3, 0, 2) <= d < nth(d.year, 11, 0, 1) else 2


def load_bars():
    bars = {}
    for src in ("bars_XAUUSD.csv", "bars_XAUUSD_extra.csv"):
        p = os.path.join(D, src)
        if not os.path.exists(p):
            continue
        for row in csv.DictReader(open(p)):
            t = dt.datetime.strptime(row["time"], "%Y.%m.%d %H:%M")
            bars.setdefault(t.date(), {})[t.hour * 60 + t.minute] = (
                float(row["open"]), float(row["high"]),
                float(row["low"]),  float(row["close"]))
    return bars


def session(bars, d, half_filter=True, require_closed=True):
    """Return the trade for one date, or a string saying why there wasn't one.

    require_closed refuses a trade the bars have not carried to an exit. Without
    it, running this mid-session publishes an open position as though it had
    finished. It asks whether the trade RESOLVED, not whether 90 minutes have
    passed -- a stop at minute five is a finished trade, and waiting out the
    cap before admitting it is what made the tool say "up to date" while a loss
    sat on the account.
    """
    if d.weekday() > 3:                       # Monday to Thursday only
        return "not a trading day"
    b = bars.get(d)
    if not b:
        return "no bars"
    st = broker_offset(d) * 60                # 00:00 UTC in broker minutes
    rng = [b[m] for m in range(st, st + RANGE_MIN) if m in b]
    if len(rng) < RANGE_MIN:
        return "incomplete range (%d of %d bars)" % (len(rng), RANGE_MIN)

    hi = max(x[1] for x in rng)
    lo = min(x[2] for x in rng)
    mid = (hi + lo) / 2.0
    close_pos = (rng[-1][3] - lo) / (hi - lo)
    allow_buy = close_pos >= 0.5              # the half the 00:14 candle closed in

    sig = None
    for m in range(st + RANGE_MIN, st + RANGE_MIN + ENTRY_MIN):
        if m not in b:
            continue
        c = b[m][3]
        if c > hi:
            sig = (m, True)
            break
        if c < lo:
            sig = (m, False)
            break
    if sig is None:
        return "no break by 00:29"
    m, buy = sig
    if half_filter and buy != allow_buy:
        # The EA does not wait for a break the other way; the day is over.
        return "broke the wrong half (closed %.2f, broke %s)" % (
            close_pos, "up" if buy else "down")
    if m + 1 not in b:
        return "no bar to enter on"

    sgn   = 1 if buy else -1
    entry_min = m + 1 - st                           # minutes past the session open
    entry = b[m + 1][0] + (SPREAD if buy else 0.0)   # market: ask to buy, bid to sell
    risk  = abs(entry - mid)
    sl    = mid
    tp    = entry + sgn * RR * risk

    moved, cur, ran_out = False, sl, False
    for k in range(m + 1, m + 1 + HOLD + 1):
        if k not in b:
            # Out of bars before the clock ran out. Whether this matters depends
            # on why: a stop or a target already returned above, so reaching
            # here means the trade is genuinely still open.
            ran_out = True
            break
        o, h, l, c = b[k]
        # A short's stop sits on the ask while the candle draws the bid.
        adv = l if buy else h + SPREAD
        fav = h if buy else l
        if (adv - cur) * sgn <= 0:
            return dict(d=d, buy=buy, entry=entry, sl=sl, tp=tp, close_pos=close_pos,
                        rng=hi - lo, entry_min=entry_min, held=k - m - 1, exit="sl", price=cur,
                        R=(cur - entry) * sgn / risk, allowed=allow_buy)
        if not moved and (fav - entry) * sgn >= MOVE_AT * risk:
            moved = True
            cur = entry + sgn * MOVE_TO * risk
            if (adv - cur) * sgn <= 0:
                return dict(d=d, buy=buy, entry=entry, sl=sl, tp=tp, close_pos=close_pos,
                            rng=hi - lo, entry_min=entry_min, held=k - m - 1, exit="sl", price=cur,
                            R=(cur - entry) * sgn / risk, allowed=allow_buy)
        if (fav - tp) * sgn >= 0:
            return dict(d=d, buy=buy, entry=entry, sl=sl, tp=tp, close_pos=close_pos,
                        rng=hi - lo, entry_min=entry_min, held=k - m - 1, exit="tp", price=tp, R=RR,
                        allowed=allow_buy)
        last = c
        last_k = k
    if require_closed and ran_out:
        return "still open, bars stop %d min into a %d min trade" % (
            last_k - m - 1, HOLD)
    return dict(d=d, buy=buy, entry=entry, sl=sl, tp=tp, close_pos=close_pos,
                rng=hi - lo, entry_min=entry_min, held=last_k - m - 1, exit="hold", price=last,
                R=(last - entry) * sgn / risk, allowed=allow_buy)


def main():
    bars = load_bars()
    if len(sys.argv) > 1:
        d = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        r = session(bars, d)
        if isinstance(r, str):
            print("%s  no trade: %s" % (d, r))
        else:
            print("%s  %s  entry %.2f  stop %.2f  target %.2f  range $%.2f  "
                  "closed %.0f%% up the range\n         exit %s at %.2f after %d min  "
                  "= %+.3f R" % (d, "BUY" if r["buy"] else "SELL", r["entry"], r["sl"],
                                 r["tp"], r["rng"], r["close_pos"] * 100, r["exit"],
                                 r["price"], r["held"], r["R"]))
        return

    # Check against the tester over the year it can see.
    ref = {}
    for row in csv.DictReader(open(os.path.join(D, "live_cp0.50.csv"))):
        t = dt.datetime.strptime(row["entry_time"], "%Y.%m.%d %H:%M")
        if t.year == 2026:
            ref[t.date()] = float(row["R"])

    days = sorted(set(bars) & set(dt.date(2026, 1, 1) + dt.timedelta(days=i)
                                  for i in range(400)))
    mine = {}
    for d in days:
        r = session(bars, d)
        if isinstance(r, dict):
            mine[d] = r["R"]

    both = sorted(set(ref) & set(mine))
    only_ref = sorted(set(ref) - set(mine))
    only_mine = sorted(set(mine) - set(ref))
    close = [d for d in both if abs(mine[d] - ref[d]) <= 0.10]
    print("tester trades   %d" % len(ref))
    print("simulated       %d" % len(mine))
    print("same days       %d   (agree within 0.10 R: %d)" % (len(both), len(close)))
    print("tester total    %+.2f R" % sum(ref.values()))
    print("sim total       %+.2f R" % sum(mine.values()))
    if only_ref:
        print("tester only:", ", ".join(str(d) for d in only_ref))
    if only_mine:
        print("sim only:   ", ", ".join(str(d) for d in only_mine))
    bad = [(d, ref[d], mine[d]) for d in both if abs(mine[d] - ref[d]) > 0.10]
    for d, a, c in bad[:15]:
        print("   %s tester %+.3f  sim %+.3f" % (d, a, c))
    print("   ... %d more" % (len(bad) - 15) if len(bad) > 15 else "")


if __name__ == "__main__":
    main()
