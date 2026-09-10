#!/bin/bash
# Test a spec on real ticks, build its report, and record what MetaTrader did.
#
#   bash research/report.sh strategies/asia-gold.toml 2026.01.01 2026.09.10
#   bash research/report.sh --account accounts/ftmo.env SPEC FROM TO
#   bash research/report.sh --id sweep-3 SPEC FROM TO
#
# Leaves the trade files under research/out/<name>/, the charts in trades-<name>/
# and the report at whatever the spec's [report] output names. The live pipeline
# (update.sh) is untouched: its marker, its CSVs, its report.
#
# Also writes research/runs/<id>.json. A container run is invisible from outside
# unless it says what it did, and "the tester silently clamped the dates" or
# "a second terminal was still closing" are the two failures that look like
# success. The record carries the range the tester ACTUALLY covered, the trade
# count per configuration, the time each step took, and any journal line worth
# reading.
set -eu
ACCOUNT=""; ID=""; POS_SPEC=""; POS_FROM=""; POS_TO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --account) ACCOUNT="${2:?--account needs a file}"; shift 2 ;;
    --id)      ID="${2:?--id needs a value}"; shift 2 ;;
    -*)        echo "unknown option: $1" >&2; exit 2 ;;
    *)         if   [ -z "$POS_SPEC" ]; then POS_SPEC="$1"
               elif [ -z "$POS_FROM" ]; then POS_FROM="$1"
               else POS_TO="$1"; fi; shift ;;
  esac
done
SPEC=$(realpath "${POS_SPEC:?usage: report.sh [--account FILE] [--id ID] SPEC FROM TO}")
FROM="${POS_FROM:?usage: report.sh [--account FILE] [--id ID] SPEC FROM TO}"
TO="${POS_TO:?usage: report.sh [--account FILE] [--id ID] SPEC FROM TO}"
HERE=$(cd "$(dirname "$0")" && pwd)
D="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
MT5DIR="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"

# The account file is plain KEY=value, sourced the way update.sh sources it so
# it works from any shell. Only the LABEL is ever recorded -- the password lands
# in a temporary run.ini inside the terminal folder and nowhere else.
LABEL="saved session"
if [ -n "$ACCOUNT" ]; then
  [ -f "$ACCOUNT" ] || { echo "no such account file: $ACCOUNT" >&2; exit 1; }
  set -a; . "$ACCOUNT"; set +a
  LABEL=$(basename "$ACCOUNT" .env)
elif [ -n "${MT5_LOGIN:-}" ]; then
  # A container gets them from --env-file, so there is no file to name. The
  # server is enough to tell two runs apart and carries no secret.
  LABEL="env:${MT5_SERVER:-unknown}"
fi

NAME=$(cd "$HERE" && python3 -c "import spec,sys; print(spec.load(sys.argv[1])['name'])" "$SPEC")
SYMBOL=$(cd "$HERE" && python3 -c "import spec,sys; print(spec.load(sys.argv[1])['symbol'])" "$SPEC")
ID="${ID:-$NAME-$(date +%Y%m%d-%H%M%S)}"
RUNS="$HERE/runs"; mkdir -p "$RUNS" "$HERE/out/$NAME"
LOG="$RUNS/$ID.log"
JOURNAL="$MT5DIR/logs/$(date +%Y%m%d).log"
JMARK=$(stat -c%s "$JOURNAL" 2>/dev/null || echo 0)
T0=$(date +%s)

record () {   # STATUS  [MESSAGE]
  local status="$1" msg="${2:-}"
  ID="$ID" NAME="$NAME" SYMBOL="$SYMBOL" LABEL="$LABEL" SPECPATH="$SPEC" \
  FROM="$FROM" TO="$TO" STATUS="$status" MSG="$msg" \
  T0="$T0" T_TEST="${T_TEST:-}" T_BUILD="${T_BUILD:-}" \
  D="$D" HERE="$HERE" JOURNAL="$JOURNAL" JMARK="$JMARK" LOG="$LOG" \
  python3 - <<'PY' > "$RUNS/$ID.json"
import os, json, csv, datetime as dt, subprocess
E=os.environ
def rows(p):
    try:
        with open(p) as fh: return max(sum(1 for _ in fh)-1, 0)
    except OSError: return None
def num(k):
    v=E.get(k) or ""
    return int(v) if v.isdigit() else None
now=int(dt.datetime.now().timestamp())
# Every journal line since the launch mark, kept only if it says something: the
# history range the tester settled on, a login failure, an error.
notable=[]
try:
    out=subprocess.run(["tail","-c","+%d"%(int(E["JMARK"])+1),E["JOURNAL"]],
                       capture_output=True).stdout.decode("utf-16-le","ignore")
    for ln in out.splitlines():
        s=" ".join(ln.split())
        NOISE=("Virtual Hosting","MQL5.community","Data Folder","Network 'MetaQuotes'")
        if any(k in s for k in NOISE): continue
        if any(k in s for k in ("history synchronized","authorization on","not specified",
                                "no history","error","failed","Experts")) and len(s)<300:
            notable.append(s)
except Exception:
    pass
# The CSVs and tested_through.txt are left behind by whatever ran last. Reading
# them after a failed tester step reported 144 trades from someone else's run,
# which is worse than reporting nothing.
ran = bool(E.get("T_TEST"))
actual=None
if ran:
    try: actual=open(os.path.join(E["D"],"tested_through.txt")).read().strip() or None
    except OSError: pass
j=dict(id=E["ID"], spec=E["NAME"], spec_path=E["SPECPATH"], symbol=E["SYMBOL"],
       account=E["LABEL"], asked_from=E["FROM"], asked_to=E["TO"],
       tester_reported_to=actual, status=E["STATUS"], message=E["MSG"] or None,
       started=int(E["T0"]), finished=now, seconds=now-int(E["T0"]),
       seconds_tester=num("T_TEST"), seconds_build=num("T_BUILD"),
       trades=(dict(cp050=rows(os.path.join(E["D"],"new_cp0.50.csv")),
                    cp000=rows(os.path.join(E["D"],"new_cp0.00.csv"))) if ran else None),
       log=os.path.basename(E["LOG"]), journal=notable[-12:])
print(json.dumps(j, indent=1))
PY
}
fail () { record failed "$1"; echo "STOPPED: $1" >&2; exit 1; }
trap 'fail "interrupted or a step exited non-zero"' ERR

# Everything below is logged AND shown. Piping the block into tee would run it
# in a subshell, which loses the step timings and hides the exit status -- both
# of which the record needs.
exec > >(tee "$LOG") 2>&1

echo "== $ID =="
echo "spec $NAME on $SYMBOL, account: $LABEL, $FROM..$TO"

S=$(date +%s)
( cd "$HERE" && SPEC="$SPEC" bash run_window.sh "$FROM" "$TO" )
T_TEST=$(( $(date +%s) - S ))

cp -f "$D/new_cp0.50.csv" "$HERE/out/$NAME/live_cp0.50.csv"
cp -f "$D/new_cp0.00.csv" "$HERE/out/$NAME/live_cp0.00.csv"

# check_charts exits 1 when anything disagrees, so set -e and the ERR trap turn
# a bad audit into a failed record rather than a published report.
S=$(date +%s)
( cd "$HERE" && export ORB_SPEC="$SPEC"
  python3 report_data.py && python3 all_trades.py \
    && python3 build_report.py && python3 check_charts.py )
T_BUILD=$(( $(date +%s) - S ))

trap - ERR
record ok
echo "  record: research/runs/$ID.json"
