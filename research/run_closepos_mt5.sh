#!/bin/bash
# Close-position filter threshold sweep, Asia session only, real ticks.
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
si InpTimeZone 0; si InpStartHour 0; si InpStartMinute 0
si InpRangeMinutes 15; si InpSignalTF 1; si InpNoEntryAfterMin 15
si InpMaxHoldMinutes 60; si InpForceCloseMin 360
si InpSLPercentOfRange 50; si InpRR 2.0
si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5
si InpRangeLookback 0; si InpRiskPercent 2.0
for TH in 0.00 0.10 0.20 0.25 0.35 0.50 0.75; do
  si InpMinClosePos "$TH"
  OUT="$D/cp_${TH}.csv"
  rm -f "$D/ORB_XAUUSD_20260821_tester.csv"
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
  mv "$D/ORB_XAUUSD_20260821_tester.csv" "$OUT" 2>/dev/null
  echo "close_pos >= $TH -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
done
si InpMinClosePos 0.25
echo ALLDONE
