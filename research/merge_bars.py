"""Merge bar CSVs into the master file, newest source winning on collisions.

BarDump (tester) and SyncDump (live chart) each write their own slice, and the
tester's slice stops at the last completed day. Merging on the timestamp is
what lets the two cover the whole range without either one clobbering the
other.

    python3 merge_bars.py bars_main.csv sync_XAUUSD.csv -> bars_XAUUSD.csv
"""
import csv, os, sys
from mt5paths import COMMON as D

def main():
    srcs = sys.argv[1:] or ["bars_main.csv", "sync_XAUUSD.csv"]
    rows, hdr = {}, None
    for name in srcs:
        p = name if os.path.isabs(name) else os.path.join(D, name)
        if not os.path.exists(p):
            print("  %-24s absent, skipped" % name)
            continue
        with open(p) as fh:
            r = csv.reader(fh)
            h = next(r)
            hdr = hdr or h
            n = 0
            for row in r:
                if row:
                    rows[row[0]] = row
                    n += 1
        print("  %-24s %7d rows" % (name, n))
    if not rows:
        sys.exit("nothing to merge")
    out = [rows[k] for k in sorted(rows)]
    dest = os.path.join(D, "bars_XAUUSD.csv")
    with open(dest, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(out)
    print("  merged %d bars, %s .. %s" % (len(out), out[0][0], out[-1][0]))

if __name__ == "__main__":
    main()
