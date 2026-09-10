"""Rewrite DATA.md's counts from the shipped datasets.

Every figure in the reports comes from report_data.json. This keeps the one
remaining hand-written place in step -- DATA.md's row counts and file sizes.

It used to rewrite results tables in the README as well. The README is now about
installing and running the tool: the rules, the results and the limits of a
configuration belong to its report, which is generated rather than typed. Those
substitutions had no `k != 1` check, so once the sections went they would have
gone on succeeding at nothing.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import json, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
d = json.load(open(os.path.join(HERE, "data", "report_data.json")))
H = d["headline"]
def refresh_data_md():
    """The counts in DATA.md drift every run unless something owns them."""
    p = os.path.join(HERE, "DATA.md")
    m = open(p).read()
    import csv, datetime as dt
    bars = os.path.join(HERE, "bars_XAUUSD_2024_2026.csv")
    n_bars = sum(1 for _ in open(bars)) - 1
    last = None
    with open(bars) as fh:
        for line in fh: last = line
    last_day = dt.datetime.strptime(last.split(",")[0], "%Y.%m.%d %H:%M").strftime("%-d %b %Y")
    mb = os.path.getsize(bars) / 1e6
    n_sess = sum(1 for _ in open(os.path.join(HERE, "sessions_2024_2026.csv"))) - 1
    live = list(csv.DictReader(open(os.path.join(HERE, "trades_live_config.csv"))))
    allb = list(csv.DictReader(open(os.path.join(HERE, "trades_all_breaks.csv"))))
    n26 = len([r for r in live if r["entry_time"][:4] == "2026"])
    subs = [
        (r"[\d,]+ one-minute bars, 2 Jan 2024 to [^,]+,", "%s one-minute bars, 2 Jan 2024 to %s," % (format(n_bars, ","), last_day)),
        (r"\d+ MB, plain CSV", "%.0f MB, plain CSV" % mb),
        (r"One row per Asia session, \d+ of them", "One row per Asia session, %d of them" % n_sess),
        (r"\d+ eligible\nsessions, \d+ trades, [\d.]+% win rate, [+-][\d.]+ R per trade, [+-][\d.]+ R total",
         "%d eligible\nsessions, %d trades, %.1f%% win rate, %+.3f R per trade, %+.1f R total"
         % (H["sessions"], H["trades"], H["wr"], H["ev"], H["total"])),
        (r"\d+ trades, the configuration actually traded", "%d trades, the configuration actually traded" % len(live)),
        (r"\d+ of these are 2026", "%d of these are 2026" % n26),
        (r"\d+ trades, same configuration", "%d trades, same configuration" % len(allb)),
    ]
    for pat, rep in subs:
        m, k = re.subn(pat, rep, m, count=1)
        if k != 1:
            sys.exit("DATA.md: pattern no longer matches: %s" % pat)
    open(p, "w").write(m)
    print("DATA.md counts: %s bars to %s, %d sessions, %d / %d trades"
          % (format(n_bars, ","), last_day, n_sess, len(live), len(allb)))

refresh_data_md()
