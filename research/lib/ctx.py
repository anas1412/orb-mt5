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

# --- the session window, in the clock the bar files use -------------------
# Bars are stamped in broker time; the spec names the session in UTC. The
# research scripts used to assume midnight UTC, so every 13:30 chart drew the
# Asia range and called it the range -- wrong box, wrong high/low, wrong half.
SES       = SPEC["session"]
RANGE_MIN = int(SES["range_min"])
ENTRY_MIN = int(SES["entry_window_min"])
if SES["tz"] != "UTC":
    raise SystemExit("ctx: session.tz %s -- the research scripts only know the "
                     "broker's offset from UTC" % SES["tz"])
_sh, _sm  = (int(x) for x in SES["start"].split(":"))
START     = _sh * 60 + _sm                    # minutes past midnight, session tz

def _nth(y, m, dow, n):
    if n > 0:
        d = dt.date(y, m, 1); return d + dt.timedelta(days=(dow - d.weekday() - 1) % 7 + (n - 1) * 7)
    d = dt.date(y, m, 28)
    while (d + dt.timedelta(days=1)).month == m: d += dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() + 1 - dow) % 7)

def broker_offset(d):
    """Broker is UTC+3 on US daylight-saving dates, UTC+2 otherwise."""
    return 3 if _nth(d.year, 3, 0, 2) <= d < _nth(d.year, 11, 0, 1) else 2

def session_start(d):
    """Minute-of-day in the bar file's clock where this spec's range opens."""
    return START + broker_offset(d) * 60

def clock(mins_after_open):
    """Wall clock in the session's own timezone, N minutes after it opens."""
    t = (START + mins_after_open) % 1440
    return "%02d:%02d" % (t // 60, t % 60)

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
