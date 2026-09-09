"""The run context: which spec, which files, which numbers.

Every pipeline script imports this instead of carrying its own literals. With
ORB_SPEC unset it resolves to the published configuration and today's paths, so
the existing report is reproduced exactly. With ORB_SPEC=strategies/x.toml the
same scripts read that spec, keep their files under research/out/<name>/, put
charts in trades-<name>/ and write the report the spec names.
"""
import os, sys, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
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

if DEFAULT:
    OUT_DIR      = HERE
    CSV_LIVE     = os.path.join(D, "live_cp0.50.csv")
    CSV_ALL      = os.path.join(D, "live_cp0.00.csv")
    TRADES_DIR   = os.path.expanduser("~/orb/trades")
    TRADES_WEB   = "trades"
    REPORT_LOCAL = os.path.expanduser("~/orb/ORB-asia-report.html")
    REPORT_PAGES = os.path.join(REPO, "index.html")      # the GitHub Pages landing page
else:
    OUT_DIR      = os.path.join(HERE, "out", NAME)
    CSV_LIVE     = os.path.join(OUT_DIR, "live_cp0.50.csv")
    CSV_ALL      = os.path.join(OUT_DIR, "live_cp0.00.csv")
    TRADES_DIR   = os.path.join(OUT_DIR, "trades")
    TRADES_WEB   = "trades-" + NAME
    REPORT_LOCAL = os.path.join(OUT_DIR, "report.html")
    REPORT_PAGES = os.path.join(REPO, SPEC["report"]["output"] or NAME + "-full-report.html")
    os.makedirs(TRADES_DIR, exist_ok=True)
DATA_JSON   = os.path.join(OUT_DIR, "report_data.json")
INDEX_JSON  = os.path.join(OUT_DIR, "trade_index.json")
HALVES_JSON = os.path.join(OUT_DIR, "halves.json")
TITLE = SPEC["report"]["title"]

RISK_TXT = "%g%%" % RISK
RR_TXT   = "%gR" % RR
RR_WORD  = "Twice" if RR == 2 else "%g\u00d7" % RR
