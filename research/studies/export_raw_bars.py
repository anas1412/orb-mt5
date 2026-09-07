#!/usr/bin/env python3
"""Export the raw M1 bars around the Asia session, straight from the MT5 dump.

This is the unprocessed input everything else is built from: open, high, low,
close and tick volume per minute, no features, no labels, no opinions. Trimmed
to 00:00-02:00 UTC because that is the window the strategy lives in, which cuts
the file from 39 MB to something a repo can carry.

    python3 export_raw_bars.py   ->  research/bars_asia_m1_2024_2026.csv
"""
import csv, datetime as dt, os
from mt5paths import bars as barsfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "bars_asia_m1_2024_2026.csv")

def nth(y, m, dow, n):
    if n > 0:
        d = dt.date(y, m, 1)
        return d + dt.timedelta(days=(dow - d.weekday() - 1) % 7 + (n - 1) * 7)
    d = dt.date(y, m, 28)
    while (d + dt.timedelta(days=1)).month == m:
        d += dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() + 1 - dow) % 7)

def broker_offset(d):
    """Broker runs UTC+3 on US DST dates, UTC+2 otherwise."""
    return 3 if nth(d.year, 3, 0, 2) <= d < nth(d.year, 11, 0, 1) else 2

rows = []
for r in csv.DictReader(open(barsfile("XAUUSD"))):
    bt = dt.datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
    # Convert to UTC here so nobody downstream has to know the broker's clock.
    # Getting this wrong shifts the whole session by an hour for part of the
    # year, which is the single easiest way to ruin this dataset.
    ut = bt - dt.timedelta(hours=broker_offset(bt.date()))
    if ut.weekday() > 4 or not (0 <= ut.hour < 2):
        continue
    rows.append(dict(
        utc=ut.strftime("%Y-%m-%d %H:%M"),
        broker=bt.strftime("%Y-%m-%d %H:%M"),
        open=r["open"], high=r["high"], low=r["low"], close=r["close"],
        ticks=r["ticks"]))

rows.sort(key=lambda x: x["utc"])
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["utc", "broker", "open", "high", "low", "close", "ticks"])
    w.writeheader()
    w.writerows(rows)

days = {r["utc"][:10] for r in rows}
print("wrote %s  (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))
print("  %d bars, %d days, %s to %s" % (len(rows), len(days), rows[0]["utc"], rows[-1]["utc"]))
per = len(rows) / float(len(days))
print("  %.0f bars a day on average (120 is a full 00:00-02:00 window)" % per)
