"""Build a spec's trade CSVs from another spec's, applying rules.min_range_pct.

The range filter only ever REMOVES sessions, so the filtered variant of a run is
a subset of it -- no second tester pass needed. Money columns are re-derived,
because position size compounds and dropping a trade changes every balance after
it; R does not depend on size, so nothing published moves.

    ORB_SPEC=strategies/asia-gold-minrange.toml python3 apply_range_filter.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import csv
import ctx
from mt5paths import COMMON as D

SRC_LIVE = os.path.join(D, "live_cp0.50.csv")
SRC_ALL  = os.path.join(D, "live_cp0.00.csv")
PCT = ctx.MIN_RANGE_PCT   # 0 copies the run through unchanged, which is a variant too

def pct_of_price(row):
    """The range as a share of price. range_pts is in points; entry is the fill."""
    return 100.0 * (int(row["range_pts"]) * 0.01) / float(row["entry"])

os.makedirs(ctx.OUT_DIR, exist_ok=True)
for src, dst in ((SRC_LIVE, ctx.CSV_LIVE), (SRC_ALL, ctx.CSV_ALL)):
    rows = list(csv.DictReader(open(src)))
    cols = list(rows[0].keys())
    kept = [r for r in rows if PCT <= 0 or pct_of_price(r) >= PCT]
    bal = ctx.DEPOSIT
    for r in kept:
        rm = bal * ctx.RISK / 100.0
        pm = float(r["R"]) * rm
        bal += pm
        r["risk_money"] = round(rm, 2)
        r["profit_money"] = round(pm, 2)
    with open(dst, "w", newline="") as fh:
        w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(kept)
    print("  %-22s %d of %d sessions (%s)"
          % (os.path.basename(dst), len(kept), len(rows),
             "range >= %g%% of price" % PCT if PCT > 0 else "no range filter"))
