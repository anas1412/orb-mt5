"""The run context: which spec, which files, which numbers.

Every pipeline script imports this instead of carrying its own literals. With
ORB_SPEC unset it resolves to the published configuration and today's paths, so
the existing report is reproduced exactly. With ORB_SPEC=strategies/x.toml the
same scripts read that spec, keep their files under research/out/<name>/, put
charts in trades-<name>/ and write the report the spec names.
"""
import os, sys, datetime as dt
# This module lives in research/lib, so HERE is that folder: the research tree
# is one level up and the repo two. Getting it wrong silently writes the report
# somewhere nobody looks.
HERE     = os.path.dirname(os.path.abspath(__file__))   # research/lib
RESEARCH = os.path.dirname(HERE)                        # research
REPO     = os.path.dirname(RESEARCH)                    # the repo
DATA     = os.path.join(RESEARCH, "data")               # generated json
sys.path.insert(0, HERE); sys.path.insert(0, RESEARCH)
import spec as S
from mt5paths import COMMON as D

SPEC_PATH = os.environ.get("ORB_SPEC")
DEFAULT   = SPEC_PATH is None
SPEC      = S.load(SPEC_PATH or os.path.join(REPO, "strategies", "asia-gold.toml"))

NAME    = SPEC["name"]
SYMBOL  = SPEC["symbol"]
RR      = float(SPEC["rules"]["rr"])
HOLD    = int(SPEC["session"]["hold_min"])
DEPOSIT = float(SPEC["risk"]["deposit"])
_r = SPEC["risk"]
RISK = float(_r["per_trade"]) if _r["mode"] == "percent" else 100.0 * float(_r["per_trade"]) / DEPOSIT
RISK_MONEY = DEPOSIT * RISK / 100.0

FROM = SPEC["dates"]["from"]
TO   = (dt.date.today() + dt.timedelta(days=1)) if SPEC["dates"]["to"] == "today" else SPEC["dates"]["to"]
def in_range(t):
    d = t.date() if isinstance(t, dt.datetime) else t
    return FROM <= d < TO
def row_in_range(row):
    return in_range(dt.datetime.strptime(row["entry_time"], "%Y.%m.%d %H:%M"))
_last = TO - dt.timedelta(days=1)
PERIOD = str(FROM.year) if FROM.year == _last.year else "%d\u2013%d" % (FROM.year, _last.year)

_b = S.BENCHMARKS[SPEC["report"]["benchmark"]]
_label, _text = S.BENCH_TEXT[SPEC["report"]["benchmark"]]
BENCH = dict(key=SPEC["report"]["benchmark"], label=_label, text=_text,
             p1=_b[0] if _b else None, p2=_b[1] if _b else None,
             maxloss=_b[2] if _b else None, daily=_b[3] if _b else None, mindays=_b[4] if _b else 0)

# Everything a run produces lives inside the repo, once. The pipeline used to
# write into ~/orb and then copy into the repo for GitHub Pages, which left two
# of every report and two of every chart and no way to tell which was current.
if DEFAULT:
    OUT_DIR      = DATA
    CSV_LIVE     = os.path.join(D, "live_cp0.50.csv")
    CSV_ALL      = os.path.join(D, "live_cp0.00.csv")
    TRADES_DIR   = os.path.join(REPO, "trades")
    TRADES_WEB   = "trades"
    REPORT_PAGES = os.path.join(REPO, "index.html")      # the GitHub Pages landing page
    REPORT_LOCAL = None
else:
    OUT_DIR      = os.path.join(RESEARCH, "out", NAME)
    CSV_LIVE     = os.path.join(OUT_DIR, "live_cp0.50.csv")
    CSV_ALL      = os.path.join(OUT_DIR, "live_cp0.00.csv")
    # Drawn straight into the folder the page links to. They used to be written
    # under research/out and the page pointed at the repo root, so every gallery
    # image on a spec report was a broken link.
    TRADES_WEB   = "trades-" + NAME
    TRADES_DIR   = os.path.join(REPO, TRADES_WEB)
    REPORT_LOCAL = None
    REPORT_PAGES = os.path.join(REPO, SPEC["report"]["output"] or NAME + "-full-report.html")
    os.makedirs(TRADES_DIR, exist_ok=True)
DATA_JSON   = os.path.join(OUT_DIR, "report_data.json")
INDEX_JSON  = os.path.join(OUT_DIR, "trade_index.json")
HALVES_JSON = os.path.join(OUT_DIR, "halves.json")
TITLE = SPEC["report"]["title"]

RISK_TXT = "%g%%" % RISK
RR_TXT   = "%gR" % RR
RR_WORD  = "Twice" if RR == 2 else "%g\u00d7" % RR
