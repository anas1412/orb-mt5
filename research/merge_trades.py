"""Merge a tester run's rows into the master trade file.

Testing 2.5 years to learn what happened yesterday takes about ninety seconds
per configuration and re-imports every month of tick data. Testing just the new
days takes under a second, because each day is independent: one trade, opened
and closed inside 90 minutes, carrying nothing into the next.

What is NOT independent is position size, which compounds off the balance. A
short run restarts from the tester's deposit, so its dollar columns would not
follow on from the rows already in the file. R is unaffected -- it is a ratio,
and it is what every published number is built from -- so R comes from the
tester and the dollars are re-derived here from the continuing balance.

    python3 merge_trades.py new_cp0.50.csv live_cp0.50.csv
"""
import csv, math, os, sys
from mt5paths import COMMON as D

LOT   = 0.01     # broker lot step
CSIZE = 100      # ounces per lot
RISK  = 0.02     # InpRiskPercent


def lots_for(balance, risk_pts):
    """Nearest lot step, matching the EA's rounding."""
    raw = balance * RISK / (risk_pts * CSIZE)
    steps = raw / LOT
    n = round(steps)
    if n < 1 or (steps and n / steps > 1.25):
        n = math.floor(steps)
    return max(n, 1) * LOT


def load(path):
    if not os.path.exists(path):
        return [], None
    rows = list(csv.DictReader(open(path)))
    return rows, (list(rows[0].keys()) if rows else None)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    new_path = os.path.join(D, sys.argv[1])
    dst_path = os.path.join(D, sys.argv[2])
    drop = set(sys.argv[3:])          # entry_times to remove first (replayed rows)

    new, nhdr = load(new_path)
    old, ohdr = load(dst_path)
    hdr = ohdr or nhdr
    if not hdr:
        sys.exit("no rows anywhere: %s and %s are both empty" % (sys.argv[1], sys.argv[2]))

    kept = [r for r in old if r["entry_time"] not in drop]
    if len(kept) != len(old):
        print("  dropped %d replayed row(s)" % (len(old) - len(kept)))

    have = set(r["entry_time"] for r in kept)
    add = [r for r in new if r["entry_time"] not in have]
    if not add:
        print("  %-22s no new trades (%d already on file)" % (sys.argv[2], len(kept)))
        with open(dst_path, "w", newline="") as fh:
            w = csv.DictWriter(fh, hdr); w.writeheader(); w.writerows(kept)
        return

    # Continue the balance the existing rows left off at.
    if kept:
        last = kept[-1]
        balance = float(last["risk_money"]) / RISK + float(last["profit_money"])
    else:
        balance = 10000.0

    add.sort(key=lambda r: r["entry_time"])
    for r in add:
        risk_pts = abs(float(r["entry"]) - float(r["sl"]))
        lots = lots_for(balance, risk_pts)
        risk_money = lots * CSIZE * risk_pts
        profit = float(r["R"]) * risk_money
        r["risk_money"]   = "%.2f" % risk_money
        r["profit_money"] = "%.2f" % profit
        balance += profit
        print("  + %s  %-4s %+.3f R  %s" % (r["entry_time"], r["dir"],
                                            float(r["R"]), r["exit"].strip()))

    out = sorted(kept + [{k: r.get(k, "") for k in hdr} for r in add],
                 key=lambda r: r["entry_time"])
    with open(dst_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, hdr); w.writeheader(); w.writerows(out)
    print("  %-22s %d rows (+%d)" % (sys.argv[2], len(out), len(add)))


if __name__ == "__main__":
    main()
