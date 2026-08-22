#!/bin/bash
# US100.cash: let the opening auction pass, then build the range.
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
sed -i 's|^Symbol=.*|Symbol=US100.cash|' "$INI"
si InpTimeZone 2                      # TZ_NEWYORK, own DST
si InpRangeMinutes 15; si InpSignalTF 1
si InpNoEntryAfterMin 15; si InpMaxHoldMinutes 60; si InpForceCloseMin 360
si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5
si InpRangeLookback 0; si InpMinClosePos 0; si InpRiskPercent 2.0
si InpTradeMon true; si InpTradeTue true; si InpTradeWed true; si InpTradeThu true; si InpTradeFri true
for S in "0945 9 45" "1000 10 0" "1030 10 30"; do
  set -- $S; TAG=$1; H=$2; M=$3
  si InpStartHour "$H"; si InpStartMinute "$M"
  for C in "sl100 2.0 100" "sl50 2.0 50"; do
    set -- $C; CT=$1; RR=$2; SLP=$3
    si InpRR "$RR"; si InpSLPercentOfRange "$SLP"
    OUT="$D/us100d_${TAG}_${CT}.csv"
    rm -f "$D/ORB_US100.cash_20260821_tester.csv"
    ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
    mv "$D/ORB_US100.cash_20260821_tester.csv" "$OUT" 2>/dev/null
    echo "range starts ${H}:${M} NY  RR${RR} SL${SLP}%  -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
  done
done
sed -i 's|^Symbol=.*|Symbol=XAUUSD|' "$INI"
si InpTimeZone 0; si InpStartHour 0; si InpStartMinute 0
si InpRR 2.0; si InpSLPercentOfRange 50; si InpMinClosePos 0.25; si InpTradeFri false
echo ALLDONE
