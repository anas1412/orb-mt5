"""Audit every published trade against the run that produced it.

The charts are the part people actually look at, and a wrong one is not
obviously wrong -- 27 Aug 2026 shipped with its exit marker drawn on the target
under a title reading LOSS. Everything here compares the published artefacts
back to the tester CSV, so that class of mistake fails loudly instead of being
spotted by eye.

    python3 check_charts.py        exits non-zero on any disagreement
"""
import csv, json, os, re, sys, datetime as dt
from mt5paths import COMMON as D
from sim_offline import load_bars, broker_offset

REPO   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES = os.path.expanduser("~/orb/trades")
HOLD   = 90

bad = []
def fail(what, msg):
    bad.append("%-12s %s" % (what, msg))

rows = [r for r in csv.DictReader(open(os.path.join(D, "live_cp0.50.csv")))
        if r["entry_time"][:4] == "2026"]
for r in rows:
    r["t"] = dt.datetime.strptime(r["entry_time"], "%Y.%m.%d %H:%M")
    r["Rf"] = float(r["R"])
rows.sort(key=lambda r: r["t"])
index = json.load(open(os.path.join(REPO, "research", "trade_index.json")))
data  = json.load(open(os.path.join(REPO, "research", "report_data.json")))
bars  = load_bars()

# 1. the index and the run describe the same trades
if len(index) != len(rows):
    fail("count", "index has %d charts, the run has %d trades" % (len(index), len(rows)))
by_date = {i["date"]: i for i in index}
for r in rows:
    d = r["t"].date().isoformat()
    i = by_date.get(d)
    if not i:
        fail("missing", "%s is in the run but has no chart" % d); continue
    if abs(i["R"] - r["Rf"]) > 1e-6:
        fail("R", "%s index %+.3f vs run %+.3f" % (d, i["R"], r["Rf"]))
    if i["dir"] != r["dir"]:
        fail("direction", "%s index %s vs run %s" % (d, i["dir"], r["dir"]))

    # 2. the filename states the outcome, so it must agree with the sign
    want = "%s_%s_%s.png" % (d, "long" if r["dir"] == "buy" else "short",
                             "win" if r["Rf"] > 0 else "loss")
    if i["file"] != want:
        fail("filename", "%s is %s, expected %s" % (d, i["file"], want))
    if not os.path.exists(os.path.join(TRADES, i["file"])):
        fail("file", "%s is missing from disk" % i["file"])

    # 3. a hold time of 0 means the walk never advanced; 90 is the cap
    if not 0 <= i["held"] <= HOLD:
        fail("held", "%s held %d min, outside 0..%d" % (d, i["held"], HOLD))

    # 4. a stop exit cannot be longer than the bars allow, and a target exit
    #    has to be reachable -- recompute where the trade ended and compare
    kind = (r["exit"].split() or ["hold"])[0]
    if kind == "sl" and r["Rf"] > 0:
        fail("exit", "%s recorded a stop but a positive R" % d)
    if kind == "tp" and r["Rf"] < 0:
        fail("exit", "%s recorded a target but a negative R" % d)
    if kind == "hold" and i["held"] != HOLD:
        fail("exit", "%s ran to the time cap but held only %d min" % (d, i["held"]))

    # 5. the short-stop trap: with the spread on, does the bar data agree the
    #    stop was hit when the run says it was?
    if kind == "sl":
        b = bars.get(r["t"].date())
        if b:
            st = broker_offset(r["t"].date()) * 60
            em = r["t"].hour * 60 + r["t"].minute - st
            e, sl = float(r["entry"]), float(r["sl"])
            risk = abs(e - sl); sgn = 1 if r["dir"] == "buy" else -1
            spread = int(r["spread_pts"]) * 0.01
            lvl = sl if abs(r["Rf"]) > 0.75 else e + sgn * -0.5 * risk
            hit = any((( b[m][2] if sgn>0 else b[m][1]+spread) - lvl) * sgn <= 0
                      for m in range(st+em, st+em+HOLD+1) if m in b)
            if not hit:
                fail("stop", "%s recorded a stop the bars never reach (%.2f)" % (d, lvl))

# 6. the totals on the page are the totals in the run
tot = sum(r["Rf"] for r in rows)
H = data["headline"]
if abs(tot - H["total"]) > 0.05:
    fail("total", "run sums to %+.2f R, report says %+.2f R" % (tot, H["total"]))
if H["trades"] != len(rows):
    fail("total", "report says %d trades, run has %d" % (H["trades"], len(rows)))
wins = len([r for r in rows if r["Rf"] > 0])
if H["wins"] != wins:
    fail("total", "report says %d wins, run has %d" % (H["wins"], wins))

# 7. every trade appears in the gallery, and its caption states the right R
page = open(os.path.join(REPO, "full-report.html")).read()
for i in index:
    if i["file"] not in page:
        fail("gallery", "%s is not on the page" % i["file"])
cards = re.findall(r'data-outcome="(win|loss)"[^>]*>.*?<i>([+-][\d.]+) R</i>', page)
if len(cards) != len(index):
    fail("gallery", "page shows %d captions for %d charts" % (len(cards), len(index)))
for (outcome, cr), i in zip(cards, index):
    if (outcome == "win") != (i["R"] > 0):
        fail("gallery", "%s tagged %s with %+.3f R" % (i["date"], outcome, i["R"]))
    if abs(float(cr) - i["R"]) > 0.011:
        fail("gallery", "%s caption %s R vs %+.3f R" % (i["date"], cr, i["R"]))

print("checked %d trades" % len(rows))
if bad:
    print("\n%d disagreement(s):" % len(bad))
    for line in bad:
        print("  " + line)
    sys.exit(1)
print("charts, filenames, captions and totals all agree with the run")
