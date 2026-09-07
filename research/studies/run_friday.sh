#!/bin/bash
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
sed -i 's|^Symbol=.*|Symbol=XAUUSD|' "$INI"
si InpTimeZone 0; si InpStartHour 0; si InpStartMinute 0
si InpRangeMinutes 15; si InpSignalTF 1; si InpEntryMode 0
si InpNoEntryAfterMin 15; si InpMaxHoldMinutes 60; si InpForceCloseMin 360
si InpSLPercentOfRange 50; si InpRR 2.0
si InpStopMoveAtR 0.5
si InpRangeLookback 0; si InpMinClosePos 0.50; si InpRiskPercent 2.0
si InpTradeMon true; si InpTradeTue true; si InpTradeWed true; si InpTradeThu true
si InpTradeFri true                      # Friday BACK IN
for MTO in -0.5 0.0; do
  si InpStopMoveToR "$MTO"
  OUT="$D/fri_move${MTO}.csv"
  rm -f "$D/ORB_XAUUSD_20260821_tester.csv"
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
  mv "$D/ORB_XAUUSD_20260821_tester.csv" "$OUT" 2>/dev/null
  echo "stop moves to ${MTO}R -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
done
si InpStopMoveToR -0.5; si InpTradeFri false
echo ALLDONE
