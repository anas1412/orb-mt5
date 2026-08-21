"""Offline parameter sweep for the ORB engine.

Replays recorded M1 bars so stop distance, target and stop-move rules can be
evaluated without re-running the Strategy Tester once per combination.

Validated against MT5: the configuration the tester actually ran must
reproduce its per-year EV and win rate before any sweep result is trusted.
"""
import csv, datetime as dt, statistics, math, sys, json

BARS = "/home/blackbox/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files/bars_XAUUSD.csv"
POINT = 0.01
# Median spread per year, measured from the live trade log. Charged once per
# trade: entry crosses the spread, the exit sits on the other side.
SPREAD_PTS = {2024: 21.0, 2025: 28.0, 2026: 52.0}
# Commission, measured from the deal log: ~$3.04 per lot per side on gold.
# In R it depends only on the stop distance, since lots scale inversely:
#   lots = risk_money / (risk_price * 100)   ->   comm_R = 6.08 / (risk_price * 100)
COMM_PER_LOT_SIDE = 3.04
CONTRACT = 100.0

def nth_dow(year, month, dow, nth):
    if nth > 0:
        d = dt.date(year, month, 1)
        return d + dt.timedelta(days=(dow - d.weekday() - 1) % 7 + (nth - 1) * 7)
    d = dt.date(year, month, 28)
    while (d + dt.timedelta(days=1)).month == month: d += dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() + 1 - dow) % 7)

def broker_offset(d):
    """Broker sits +2 in winter, +3 on US DST dates. Mirrors TimeZones.mqh."""
    start = nth_dow(d.year, 3, 0, 2)      # 2nd Sunday March
    end   = nth_dow(d.year, 11, 0, 1)     # 1st Sunday November
    return 3 if start <= d < end else 2

def load():
    days = {}
    with open(BARS) as f:
        for row in csv.DictReader(f):
            t = dt.datetime.strptime(row["time"], "%Y.%m.%d %H:%M")
            days.setdefault(t.date(), []).append(
                (t, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])))
    return days

def setups(days, range_min=15, window_min=120, want_history=False):
    """One setup per day: the range, then the first close outside it.

    With want_history, also returns every session's range in date order,
    including days that never broke out. The rolling filter needs that full
    series -- restricting the yardstick to days that happened to trade would
    quietly raise it."""
    out = []
    hist = []
    for d, bars in sorted(days.items()):
        if d.weekday() > 4: continue
        bars.sort()
        h0 = broker_offset(d)                       # session opens 00:00 UTC
        rng = [b for b in bars if b[0].hour == h0 and b[0].minute < range_min]
        if len(rng) < range_min: continue
        hi = max(b[2] for b in rng); lo = min(b[3] for b in rng)
        if hi <= lo: continue
        hist.append((d, hi - lo))
        start = dt.datetime.combine(d, dt.time(h0, 0))
        w0, w1 = start + dt.timedelta(minutes=range_min), start + dt.timedelta(minutes=range_min+window_min)
        after = [b for b in bars if b[0] >= w0]
        sig = None
        for i, b in enumerate(after):
            if b[0] >= w1: break
            if b[4] > hi: sig = (i, True);  break
            if b[4] < lo: sig = (i, False); break
        if sig is None: continue
        i, is_buy = sig
        if i + 1 >= len(after): continue
        path = after[i+1:i+1+241]                   # entry bar plus a long hold window
        if not path: continue
        mins_late = int((after[i][0] - w0).total_seconds()//60)   # break bar, minutes after range close
        out.append(dict(date=d, hi=hi, lo=lo, is_buy=is_buy, late=mins_late,
                        entry=path[0][1], path=[(b[2], b[3], b[4]) for b in path]))
    return (out, hist) if want_history else out

def run(s, sl_frac, rr, move_at, move_to, hold=60):
    rng = s["hi"] - s["lo"]
    lvl = s["hi"] if s["is_buy"] else s["lo"]
    sl  = lvl - rng*sl_frac if s["is_buy"] else lvl + rng*sl_frac
    e   = s["entry"]
    risk = abs(e - sl)
    if risk <= 0: return None
    tp = e + rr*risk if s["is_buy"] else e - rr*risk
    moved = False
    sgn = 1 if s["is_buy"] else -1
    for k, (h, l, c) in enumerate(s["path"][:hold+1]):
        adverse   = l if s["is_buy"] else h
        favorable = h if s["is_buy"] else l
        # conservative intrabar order: stop first, then the move, then target
        if (adverse - sl)*sgn <= 0:
            return (sl - e)*sgn/risk
        if move_at > 0 and not moved and (favorable - e)*sgn >= move_at*risk:
            moved = True
            sl = e + sgn*move_to*risk
            if (adverse - sl)*sgn <= 0:
                return (sl - e)*sgn/risk
        if (favorable - tp)*sgn >= 0:
            return rr
        last = c
    return (last - e)*sgn/risk

def evaluate(ss, sl_frac, rr, move_at, move_to, hold=60, cutoff=None):
    res = []
    for s in ss:
        if cutoff is not None and s['late'] >= cutoff: continue
        r = run(s, sl_frac, rr, move_at, move_to, hold)
        if r is None: continue
        rng = s["hi"] - s["lo"]
        risk_price = abs(s["entry"] - ((s["hi"] if s["is_buy"] else s["lo"])
                        + (-1 if s["is_buy"] else 1)*rng*sl_frac))
        if risk_price <= 0: continue
        cost  = (SPREAD_PTS[s["date"].year]*POINT)/risk_price          # spread, once
        cost += 2*COMM_PER_LOT_SIDE/(risk_price*CONTRACT)              # commission, both sides
        res.append((s["date"].year, r - cost))
    return res

def stats(res):
    R = [r for _, r in res]
    if not R: return None
    w = [r for r in R if r > 0]
    return dict(n=len(R), ev=sum(R)/len(R), wr=100.0*len(w)/len(R),
                total=sum(R), sd=statistics.pstdev(R),
                se=statistics.pstdev(R)/math.sqrt(len(R)))

if __name__ == "__main__":
    ss = setups(load())
    print("setups found: %d  (%s .. %s)" % (len(ss), ss[0]["date"], ss[-1]["date"]))
    res = evaluate(ss, 0.5, 2.0, 0.5, -0.5)
    print("\n--- validation: the configuration MT5 actually ran ---")
    print("            python sim          MT5 tester")
    for y in (2024, 2025, 2026):
        st = stats([r for r in res if r[0] == y])
        print("  %d   n=%3d EV %+.3f WR %4.1f%%" % (y, st["n"], st["ev"], st["wr"]))
    allst = stats(res)
    print("  all   n=%3d EV %+.4f WR %4.1f%%   (MT5: n=455 EV -0.0045 WR 31.6%%)"
          % (allst["n"], allst["ev"], allst["wr"]))
