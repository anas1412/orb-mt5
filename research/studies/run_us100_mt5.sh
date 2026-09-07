#!/bin/bash
# US100.cash at the New York cash open (09:30 local, DST handled by TimeZones.mqh).
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
sed -i 's|^Symbol=.*|Symbol=US100.cash|' "$INI"
si InpTimeZone 2                  # TZ_NEWYORK -- own DST rule
si InpStartHour 9; si InpStartMinute 30
si InpRangeMinutes 15; si InpSignalTF 1
si InpNoEntryAfterMin 15; si InpMaxHoldMinutes 60; si InpForceCloseMin 360
si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5
si InpRangeLookback 0; si InpMinClosePos 0
si InpRiskPercent 2.0
si InpTradeMon true; si InpTradeTue true; si InpTradeWed true; si InpTradeThu true; si InpTradeFri true
for C in "rr1sl100 1.0 100" "rr2sl50 2.0 50" "rr2sl100 2.0 100" "rr1sl50 1.0 50"; do
  set -- $C; TAG=$1; RR=$2; SLP=$3
  si InpRR "$RR"; si InpSLPercentOfRange "$SLP"
  OUT="$D/us100_${TAG}.csv"
  rm -f "$D/ORB_US100.cash_20260821_tester.csv"
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
  mv "$D/ORB_US100.cash_20260821_tester.csv" "$OUT" 2>/dev/null
  echo "US100 NY cash open  RR${RR} SL${SLP}%  -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
done
# restore the live Asia gold configuration
sed -i 's|^Symbol=.*|Symbol=XAUUSD|' "$INI"
si InpTimeZone 0; si InpStartHour 0; si InpStartMinute 0
si InpRR 2.0; si InpSLPercentOfRange 50; si InpMinClosePos 0.25; si InpTradeFri false
echo ALLDONE
