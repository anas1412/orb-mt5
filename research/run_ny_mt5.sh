#!/bin/bash
# NY session variants: 13:15 and 15:30 UTC, RR1/full-range SL and RR2/midpoint SL.
# Friday included. Close-position filter off (it was tuned on Asia).
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
si InpTimeZone 0                 # plain UTC, no zone conversion
si InpRangeMinutes 15; si InpSignalTF 1
si InpNoEntryAfterMin 15; si InpMaxHoldMinutes 60; si InpForceCloseMin 360
si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5
si InpRangeLookback 0; si InpMinClosePos 0
si InpRiskPercent 2.0
si InpTradeMon true; si InpTradeTue true; si InpTradeWed true; si InpTradeThu true
si InpTradeFri true               # Friday IN for these runs
for S in "1315 13 15" "1530 15 30"; do
  set -- $S; TAG=$1; H=$2; M=$3
  si InpStartHour "$H"; si InpStartMinute "$M"
  for C in "rr1 1.0 100" "rr2 2.0 50"; do
    set -- $C; RTAG=$1; RR=$2; SLP=$3
    si InpRR "$RR"; si InpSLPercentOfRange "$SLP"
    OUT="$D/ny_${TAG}_${RTAG}.csv"
    rm -f "$D/ORB_XAUUSD_20260821_tester.csv"
    ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
    mv "$D/ORB_XAUUSD_20260821_tester.csv" "$OUT" 2>/dev/null
    echo "${H}:${M} UTC  RR${RR} SL${SLP}%  -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
  done
done
# restore the live Asia configuration
si InpStartHour 0; si InpStartMinute 0
si InpRR 2.0; si InpSLPercentOfRange 50; si InpMinClosePos 0.25; si InpTradeFri false
echo ALLDONE
