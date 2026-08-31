#!/bin/bash
# Bring the published study up to date: fetch the new bars, test the new days,
# rebuild every page, audit, commit, push.
#
#   bash update.sh                 everything since the last run
#   bash update.sh --full          re-test 2024 onward from scratch (~20 min)
#   bash update.sh 2026.09.05      stop after 4 Sep (ToDate is exclusive)
#   bash update.sh --push          skip the confirmation before pushing
#
# Incremental by default, because each session is independent: one trade,
# opened and closed inside 90 minutes, carrying nothing into the next. Testing
# a few new days takes seconds; testing 2024 onward takes about ninety seconds
# per configuration and re-imports every month of tick data.
#
# The audit is the point. It stops the run rather than publishing a chart that
# disagrees with its own data, which has happened.
set -euo pipefail

MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
REPO="$HOME/orb/strategy"
D="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
EXE="terminal6""4.exe"          # split so pgrep -f never matches this script
BROKER=FTMO-Demo
SYMBOL=XAUUSD
EPOCH=2024.01.01

TO=""; PUSH=ask; FULL=no
for a in "$@"; do
  case "$a" in
    --push)    PUSH=yes ;;
    --no-push) PUSH=no ;;
    --full)    FULL=yes ;;
    *)         TO="$a" ;;
  esac
done
# The tester stops at the START of ToDate, so it must be the day after the last
# one wanted. It clamps this to whatever history it has and says so.
TO="${TO:-$(date -d tomorrow +%Y.%m.%d)}"

say  () { printf '\n\033[1m== %s\033[0m\n' "$1"; }
die  () { printf '\n\033[31mSTOPPED: %s\033[0m\n' "$1" >&2; exit 1; }

# A config with no [Tester] section does not error -- MetaTrader opens the GUI
# and sits there until something kills it, which reads as a slow step rather
# than a broken one. Check before launching, and never launch without a
# timeout.
run_mt5 () {
  local ini="$1" secs="$2"
  grep -q '^\[Tester\]\|^\[StartUp\]' "$REPO/$ini" ||
    die "$ini has no [Tester] or [StartUp] section. MetaTrader would hang on it."
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all \
      timeout "$secs" wine "$EXE" /portable /config:"$ini" >/dev/null 2>&1 ) || true
}

cd "$REPO"

say "1/9  terminal must be closed"
if pgrep -x "$EXE" >/dev/null; then
  die "MetaTrader is running. Close it first -- a second terminal exits immediately and silently."
fi
# A hard kill leaves Wine holding state that makes MetaTrader refuse to start:
# it exits 0, writes nothing to its log, and every step downstream then reports
# no data as though the market were closed. Clearing the server costs nothing
# when nothing is running.
WINEPREFIX="$HOME/.wine_mt5" wineserver -k 2>/dev/null || true
sleep 2
echo "  ok"

say "2/9  today's bars, from a live chart"
# MetaTrader's history server only serves bars up to the last COMPLETED trading
# day. Today exists only in a live chart, where CopyRates pulls from the server.
# Do NOT write to "$MT5/<name>.ini": every one is a symlink back into this
# repo, so a redirect truncates its own input. Edit the repo copy in place.
rm -f "$D/sync_$SYMBOL.csv"
run_mt5 sync.ini 300
if [ -s "$D/sync_$SYMBOL.csv" ]; then
  echo "  live chart reached $(tail -1 "$D/sync_$SYMBOL.csv" | cut -d, -f1) (broker time)"
else
  echo "  no live bars (offline?), carrying on with what is cached"
fi

say "3/9  bars for the days we do not have"
# Keep the master under a second name: the dump writes bars_SYMBOL.csv, so an
# interrupted run would otherwise destroy 2.5 years of data.
if [ -f "$D/bars_$SYMBOL.csv" ]; then cp -f "$D/bars_$SYMBOL.csv" "$D/bars_main.csv"; fi
if [ "$FULL" = yes ]; then
  BAR_FROM=$EPOCH
  rm -f "$D/bars_main.csv"
else
  BAR_FROM=$(tail -1 "$D/bars_main.csv" 2>/dev/null | cut -d, -f1 | cut -d' ' -f1)
  BAR_FROM=${BAR_FROM:-$EPOCH}
fi
echo "  dumping $BAR_FROM .. $TO"
sed -i -e "s|^FromDate=.*|FromDate=$BAR_FROM|" -e "s|^ToDate=.*|ToDate=$TO|" dump.ini
rm -f "$D/bars_$SYMBOL.csv"
run_mt5 dump.ini 900
( cd research && python3 merge_bars.py bars_main.csv "sync_$SYMBOL.csv" "bars_$SYMBOL.csv" )

say "4/9  test the days we have not tested"
# The tester agent keeps its OWN copy of history and its own preprocessed
# ticks. Neither refreshes itself, so a run after new data silently repeats the
# old one. Only the current year and month need clearing -- wiping all of it
# re-imports every month and costs minutes.
YEAR=${TO%%.*}; MONTH=${TO:0:4}${TO:5:2}
rm -f "$MT5/Tester/bases/$BROKER/history/$SYMBOL/$YEAR.hcs" \
      "$MT5/Tester/bases/$BROKER/ticks/$SYMBOL/$MONTH.tkc" \
      "$MT5"/Tester/cache/ORB."$SYMBOL".*.tst
if [ "$FULL" = yes ]; then
  TEST_FROM=$EPOCH
  rm -f "$D/live_cp0.50.csv" "$D/live_cp0.00.csv"
else
  # Resume from the last tested day. Re-testing it is harmless -- the merge
  # keys on entry_time -- and it covers a day that was only half done.
  TEST_FROM=$(cat "$D/tested_through.txt" 2>/dev/null || true)
  TEST_FROM=${TEST_FROM:-$EPOCH}
  # Back up a few days. The tester refuses a window whose start is already its
  # clamped end, which is exactly the shape of "nothing new has closed yet" --
  # and refusing looks identical to failing. Re-testing a handful of days costs
  # seconds and the merge keys on entry_time, so nothing doubles up.
  if [ "$TEST_FROM" != "$EPOCH" ]; then
    TEST_FROM=$(date -d "${TEST_FROM//./-} -5 days" +%Y.%m.%d)
  fi
fi
echo "  testing $TEST_FROM .. $TO"
( cd research && bash run_window.sh "$TEST_FROM" "$TO" )
COVER=$(cat "$D/tested_through.txt")

# Replayed rows are not tester output. Drop them before merging so a real row
# takes over the moment the tester can see that day.
DROP=$(python3 -c "
import json, os
p = 'research/replayed.json'
print(' '.join(repr(r['entry_time']) for r in json.load(open(p))['rows'])
      if os.path.exists(p) else '')" 2>/dev/null || true)
( cd research && eval python3 merge_trades.py new_cp0.50.csv live_cp0.50.csv $DROP )
( cd research && eval python3 merge_trades.py new_cp0.00.csv live_cp0.00.csv $DROP )

say "5/9  sessions the tester would not test"
# It will not test a day it has not finished, so the current session is absent
# however the range is asked for. Replay it from the bars instead.
( cd research && python3 replay_today.py "$COVER" )

say "6/9  rebuild everything downstream"
cd research
python3 report_data.py
python3 all_trades.py
python3 build_report.py
python3 build_slides.py
python3 build_client.py
python3 build_sessions.py
python3 update_readme.py
cd ..
cp -f "$HOME/orb/ORB-asia-report.html" full-report.html

say "7/9  audit"
( cd research && python3 check_charts.py ) || die "the audit failed. Nothing published. Fix the disagreement above and re-run."

say "8/9  refresh the shipped data files"
cp -f "$D/bars_$SYMBOL.csv"  "research/bars_${SYMBOL}_2024_2026.csv"
cp -f "$D/live_cp0.50.csv"   research/trades_live_config.csv
cp -f "$D/live_cp0.00.csv"   research/trades_all_breaks.csv
python3 - <<'PY'
import json
d = json.load(open('research/report_data.json')); H = d['headline']
print("  %d trades | WR %.1f%% | EV %+.3f | total %+.1f R (%+.0f%%) | PF %.2f | DD %.1f%%"
      % (H['trades'], H['wr'], H['ev'], H['total'], H['ret'], H['pf'], d['maxdd']))
PY

say "9/9  commit"
git add -A
if git diff --cached --quiet; then
  echo "  nothing changed, so nothing to publish"
  exit 0
fi
git status --short | sed 's/^/  /' | head -12
git commit -q -m "Update the study through $(python3 -c "
import json; print(json.load(open('research/report_data.json'))['coverage']['last'])")" \
  -m "$(python3 - <<'PY'
import json
d = json.load(open('research/report_data.json')); H = d['headline']
print("%d trades of %d sessions | win rate %.1f%% | expectancy %+.3f R\n"
      "total %+.1f R = %+.0f%% | profit factor %.2f | worst drawdown %.1f%% | "
      "longest losing run %d\n\nRegenerated from the tester run: report_data, every "
      "trade chart, the report,\nthe deck, the client page, the session dataset, the "
      "three data CSVs and the\nREADME. check_charts.py passed."
      % (H['trades'], H['sessions'], H['wr'], H['ev'], H['total'], H['ret'],
         H['pf'], d['maxdd'], d['streaks']['worst_loss']))
PY
)"
git --no-pager log --oneline -1 | sed 's/^/  /'

if [ "$PUSH" = ask ]; then
  read -rp $'\npush to origin and publish? [y/N] ' a
  [[ "$a" =~ ^[Yy] ]] || { echo "committed but not pushed. 'git push origin main' when ready."; exit 0; }
elif [ "$PUSH" = no ]; then
  echo "committed but not pushed."; exit 0
fi
git push origin main
echo
echo "live in a minute or so: https://anas1412.github.io/orb-mt5/"
