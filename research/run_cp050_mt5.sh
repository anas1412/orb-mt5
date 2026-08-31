#!/bin/bash
# Re-run the live configuration on real ticks and keep the trade-by-trade CSV.
# The tester stops at the START of ToDate, so ToDate must be the day AFTER the
# last day you want included. Pass it as $1 to avoid the hardcoded date going
# stale and silently re-running an old window -- which is exactly what happened.
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
sed -i 's|^Symbol=.*|Symbol=XAUUSD|' "$INI"
TO="${1:?usage: run_cp050_mt5.sh YYYY.MM.DD  (the day AFTER the last one you want)}"
sed -i "s|^ToDate=.*|ToDate=$TO|" "$INI"
si InpTimeZone 0; si InpStartHour 0; si InpStartMinute 0
si InpRangeMinutes 15; si InpSignalTF 1; si InpEntryMode 0
si InpNoEntryAfterMin 15; si InpMaxHoldMinutes 90; si InpForceCloseMin 360
si InpSLPercentOfRange 50; si InpRR 2.0
si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5
si InpRangeLookback 0; si InpRiskPercent 2.0
si InpTradeMon true; si InpTradeTue true; si InpTradeWed true; si InpTradeThu true
si InpTradeFri false
for CP in 0.00 0.50; do
  si InpMinClosePos "$CP"
  # cp 0.00 keeps every break, which is what the half-vs-half table needs
  OUT="$D/live_cp${CP}.csv"
  rm -f "$D"/ORB_XAUUSD_*_tester.csv
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
  mv "$D"/ORB_XAUUSD_*_tester.csv "$OUT" 2>/dev/null
  echo "close-pos $CP -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
done
si InpMinClosePos 0.50
echo ALLDONE
