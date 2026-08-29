#!/usr/bin/env python3
"""One row per Asia session, 2024-2026, for session-quality modelling.

Every feature is computable at 00:15 UTC, the moment the range closes and
before any entry decision. Nothing here can see the future -- the rolling
columns use prior sessions only. The outcome columns are what happened
afterwards and are labels, not inputs.

    python3 build_sessions.py   ->  research/M5/sessions_2024_2026.csv
"""
import csv, datetime as dt, os, statistics
from collections import defaultdict
from mt5paths import COMMON as D, bars as barsfile

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions_2024_2026.csv")

def nth(y, m, dow, n):
    if n > 0:
        d = dt.date(y, m, 1)
        return d + dt.timedelta(days=(dow - d.weekday() - 1) % 7 + (n - 1) * 7)
    d = dt.date(y, m, 28)
    while (d + dt.timedelta(days=1)).month == m:
        d += dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() + 1 - dow) % 7)

def broker_offset(d):
    """Broker is UTC+3 on US DST dates, UTC+2 otherwise."""
    return 3 if nth(d.year, 3, 0, 2) <= d < nth(d.year, 11, 0, 1) else 2

# --- load M1 bars, keyed by date then minute-of-day (broker time) ---
bars = defaultdict(dict)
for r in csv.DictReader(open(barsfile("XAUUSD"))):
    t = dt.datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
    bars[t.date()][t.hour * 60 + t.minute] = (
        float(r["open"]), float(r["high"]), float(r["low"]),
        float(r["close"]), float(r["ticks"]))

# --- realised R per session, from the backtest with the half-filter OFF, so
#     every break that happened carries its outcome ---
outcome = {}
for r in csv.DictReader(open(os.path.join(D, "live_cp0.00.csv"))):
    t = dt.datetime.strptime(r["entry_time"], "%Y.%m.%d %H:%M")
    outcome[t.date()] = dict(R=float(r["R"]), dirn=r["dir"], exit=r["exit"].strip(),
                             spread=float(r["spread_pts"]))

rows = []
hist = []                    # prior sessions' range_pct, for the rolling columns
for d in sorted(bars):
    if d.weekday() > 4:
        continue
    st = broker_offset(d) * 60          # 00:00 UTC in broker minutes
    win = [bars[d][m] for m in range(st, st + 15) if m in bars[d]]
    if len(win) < 15:
        continue                        # holiday or a data gap: not a session

    hi = max(b[1] for b in win)
    lo = min(b[2] for b in win)
    rng = hi - lo
    ref = win[-1][3]                    # the 00:14 close, the reference price
    if rng <= 0 or ref <= 0:
        continue
    rng_pct = 100.0 * rng / ref
    close_pos = (ref - lo) / rng        # 0 = at the low, 1 = at the high

    # rolling context, prior sessions only
    prev  = hist[-1] if hist else ""
    med5  = statistics.median(hist[-5:])  if len(hist) >= 5  else ""
    med20 = statistics.median(hist[-20:]) if len(hist) >= 20 else ""

    # --- what happened next: the first M1 CLOSE outside the box, by 00:29 ---
    broke, bmin, bdir = 0, "", ""
    for k in range(15, 30):
        m = st + k
        if m not in bars[d]:
            continue
        c = bars[d][m][3]
        if c > hi:  broke, bmin, bdir = 1, k, "up";   break
        if c < lo:  broke, bmin, bdir = 1, k, "down"; break

    same_half = ""
    if broke:
        same_half = 1 if ((close_pos >= 0.5) == (bdir == "up")) else 0

    o = outcome.get(d, {})
    rows.append(dict(
        date=d.isoformat(), dow=d.strftime("%a"),
        range_high=round(hi, 2), range_low=round(lo, 2),
        range_usd=round(rng, 2), price_ref=round(ref, 2),
        range_pct=round(rng_pct, 4),
        close_pos=round(close_pos, 4),
        range_ticks=int(sum(b[4] for b in win)),
        range_dir=round(win[-1][3] - win[0][0], 2),
        prev_range_pct=round(prev, 4) if prev != "" else "",
        med5_range_pct=round(med5, 4) if med5 != "" else "",
        med20_range_pct=round(med20, 4) if med20 != "" else "",
        broke=broke, break_min=bmin, break_dir=bdir, same_half=same_half,
        traded_by_ea=1 if (broke and same_half == 1) else 0,
        R=o.get("R", ""), exit_kind=o.get("exit", ""), spread_pts=o.get("spread", "")))
    hist.append(rng_pct)

cols = list(rows[0].keys())
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print("wrote %s" % OUT)
print("  %d sessions, %s to %s" % (len(rows), rows[0]["date"], rows[-1]["date"]))
by_year = defaultdict(lambda: [0, 0, 0])
for r in rows:
    y = r["date"][:4]
    by_year[y][0] += 1
    by_year[y][1] += r["broke"]
    by_year[y][2] += r["traded_by_ea"]
print("  year  sessions  broke  the EA would trade")
for y in sorted(by_year):
    n, b, t = by_year[y]
    print("  %s    %4d     %4d (%2.0f%%)   %4d (%2.0f%%)" % (y, n, b, 100*b/n, t, 100*t/n))
print("  rows carrying a realised R: %d" % len([r for r in rows if r["R"] != ""]))
print("  columns: %s" % ", ".join(cols))
