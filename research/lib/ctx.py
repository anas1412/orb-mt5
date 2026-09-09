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

# --- who this strategy is, in words the template can print ----------------
# template.html used to spell out "the Asia Opening Range", "Monday to
# Thursday" and "00:00 to 00:14 UTC" in its own prose, so every spec report
# described the Asia session whatever spec built it. Identity lives here now.
_DOW      = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4}
_LONGDOW  = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
             "Thu": "Thursday", "Fri": "Friday"}
DAY_NAMES = [d for d in ("Mon", "Tue", "Wed", "Thu", "Fri") if d in SPEC["rules"]["days"]]
WEEKDAYS  = frozenset(_DOW[d] for d in DAY_NAMES)
def _days_txt(long):
    n = [(_LONGDOW if long else dict((k, k) for k in _LONGDOW))[d] for d in DAY_NAMES]
    if len(n) == 1:
        return n[0]
    if [_DOW[d] for d in DAY_NAMES] == list(range(_DOW[DAY_NAMES[0]], _DOW[DAY_NAMES[-1]] + 1)):
        return "%s to %s" % (n[0], n[-1]) if long else "%s–%s" % (n[0], n[-1])
    return ", ".join(n[:-1]) + " and " + n[-1]
DAYS_TXT   = _days_txt(True)                    # "Monday to Thursday"
DAYS_SHORT = _days_txt(False)                   # "Mon-Thu"
DAYS_DASH  = (("%s\u2013%s" % (_LONGDOW[DAY_NAMES[0]], _LONGDOW[DAY_NAMES[-1]]))
              if len(DAY_NAMES) > 1 and [_DOW[d] for d in DAY_NAMES]
                 == list(range(_DOW[DAY_NAMES[0]], _DOW[DAY_NAMES[-1]] + 1))
              else DAYS_TXT)                    # "Monday-Thursday"
OFF_DAYS   = [_LONGDOW[d] for d in ("Mon", "Tue", "Wed", "Thu", "Fri") if d not in DAY_NAMES]

DIRECTION  = SPEC["rules"]["direction"]
DIR_TXT    = {"both":  "either way",
              "long":  "upward breaks only",
              "short": "downward breaks only"}[DIRECTION]
HALF_FILTER = bool(SPEC["rules"]["half_filter"])

TZ_TXT      = SES["tz"]
OPEN_TXT    = "%s %s" % (clock(0), TZ_TXT)                  # "00:00 UTC"
LAST_CANDLE = clock(RANGE_MIN - 1)                          # "00:14"
BOX_DONE    = clock(RANGE_MIN)                              # "00:15"
ENTRY_LAST  = clock(RANGE_MIN + ENTRY_MIN - 1)              # "00:29"
RANGE_TXT   = "%s to %s %s" % (clock(0), LAST_CANDLE, TZ_TXT)
SIGNAL_TF   = SES["signal_tf"]

FROM = SPEC["dates"]["from"]
TO   = (dt.date.today() + dt.timedelta(days=1)) if SPEC["dates"]["to"] == "today" else SPEC["dates"]["to"]
def in_range(t):
    d = t.date() if isinstance(t, dt.datetime) else t
    return FROM <= d < TO
def row_in_range(row):
    return in_range(dt.datetime.strptime(row["entry_time"], "%Y.%m.%d %H:%M"))
_last = TO - dt.timedelta(days=1)
PERIOD = str(FROM.year) if FROM.year == _last.year else "%d\u2013%d" % (FROM.year, _last.year)

# --- the headline and the reasoning, both owned by the spec ----------------
_rep  = SPEC["report"]
_WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 10: "ten",
         15: "fifteen", 20: "twenty", 30: "thirty", 45: "forty-five", 60: "sixty"}
def _word(n):
    return _WORD.get(n, str(n))
RANGE_WORD = _word(RANGE_MIN)
NDAYS_WORD = _word(len(DAY_NAMES))
OFF_TXT    = ("%s off. " % ", ".join(d + "s" for d in OFF_DAYS)) if OFF_DAYS else ""

H1    = _rep["h1"]    or "The %s Opening Range" % OPEN_TXT
H1_EM = _rep["h1_em"] or "on %s" % SYMBOL
SHORT = _rep["short"] or "ORB %s \u2014 %s." % (OPEN_TXT, SYMBOL)
LEDE  = _rep["lede"]  or ("One trade a day, %s, decided in the %s minutes after %s. "
                          "This is the complete rule set, why each rule is there, and "
                          "every trade it produced in %s." % (DAYS_TXT, RANGE_WORD, OPEN_TXT, PERIOD))
WHY   = SPEC["notes"]["why"]

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
