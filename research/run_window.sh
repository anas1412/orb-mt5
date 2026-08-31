#!/bin/bash
# Run both configurations over one date window and leave the rows in
# new_cp0.00.csv / new_cp0.50.csv for merging.
#
#   run_window.sh FROM TO      both YYYY.MM.DD; TO is the day AFTER the last wanted
#
# A window of a few days tests in under a second. The whole 2024-2026 range
# takes about ninety seconds per configuration and re-imports every month of
# ticks, so only ask for that when rebuilding from scratch.
set -eu
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
FROM="${1:?usage: run_window.sh FROM TO}"
TO="${2:?usage: run_window.sh FROM TO}"

si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
sed -i 's|^Symbol=.*|Symbol=XAUUSD|' "$INI"
si FromDate "$FROM"; si ToDate "$TO"
si InpTimeZone 0; si InpStartHour 0; si InpStartMinute 0
si InpRangeMinutes 15; si InpSignalTF 1; si InpEntryMode 0
si InpNoEntryAfterMin 15; si InpMaxHoldMinutes 90; si InpForceCloseMin 360
si InpSLPercentOfRange 50; si InpRR 2.0
si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5
si InpRangeLookback 0; si InpRiskPercent 2.0
si InpTradeMon true; si InpTradeTue true; si InpTradeWed true; si InpTradeThu true
si InpTradeFri false

# An empty result file is a legitimate answer -- a window can genuinely hold no
# trades -- so row count cannot tell a real run from one that never started. A
# second terminal launching while one is still shutting down exits immediately
# and silently, which is how a window once reported "0 trades" without testing
# anything. Read the tester's own log instead.
#
# Match only the FROM date. The tester CLAMPS ToDate to what its history covers
# and reports the clamped value, so requiring the requested end to come back
# fails every run that includes today -- which is every run.
LOG="$MT5/Tester/logs/$(date +%Y%m%d).log"
started () {
  iconv -f UTF-16LE -t UTF-8 "$LOG" 2>/dev/null |
    grep -oE "testing of Experts.ORB\\.ex5 from $FROM 00:00 to [0-9.]+" | tail -1
}

for CP in 0.00 0.50; do
  si InpMinClosePos "$CP"        # 0.00 keeps every break, for the half-vs-half table
  rm -f "$D"/ORB_XAUUSD_*_tester.csv
  : > "$LOG" 2>/dev/null || true
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
  # Without the guard, set -e kills the script on a failed command
  # substitution and the message below never prints -- the run just stops.
  LINE=$(started || true)
  if [ -z "$LINE" ]; then
    echo "the tester never ran the window starting $FROM -- is another terminal still open?" >&2
    exit 1
  fi
  ACTUAL=${LINE##* }
  mv "$D"/ORB_XAUUSD_*_tester.csv "$D/new_cp${CP}.csv" 2>/dev/null || \
    printf 'entry_time,range_pts,spread_pts,mins_after_range,dir,entry,sl,risk_money,profit_money,R,exit,close_pos\n' > "$D/new_cp${CP}.csv"
  echo "  close-pos $CP  $FROM..$ACTUAL -> $(( $(wc -l < "$D/new_cp${CP}.csv") - 1 )) trades"
done

# The clamped end is the honest record of what has actually been tested, and it
# is what the next incremental run resumes from.
echo "$ACTUAL" > "$D/tested_through.txt"
if [ "$ACTUAL" != "$TO" ]; then
  echo "  note: asked for $TO, the tester would only go to $ACTUAL"
fi
si InpMinClosePos 0.50
