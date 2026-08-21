#!/bin/bash
# range length x signal timeframe, Asia and New York, RR2 with the stop move.
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
si InpSLPercentOfRange 50; si InpRR 2.0; si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5
si InpRangeLookback 0; si InpRiskPercent 2.0; si InpForceCloseMin 600
for S in "Asia 0 0 0" "NewYork 2 9 30"; do
  set -- $S; NAME=$1; TZ=$2; H=$3; M=$4
  si InpTimeZone "$TZ"; si InpStartHour "$H"; si InpStartMinute "$M"
  # range | signalTF | entrywindow | hold
  for C in "15 1 15 60" "30 3 30 120" "60 5 60 240"; do
    set -- $C; RNG=$1; TF=$2; WIN=$3; HOLD=$4
    si InpRangeMinutes "$RNG"; si InpSignalTF "$TF"
    si InpNoEntryAfterMin "$WIN"; si InpMaxHoldMinutes "$HOLD"
    OUT="$D/tf_${NAME}_r${RNG}_tf${TF}.csv"
    rm -f "$D/ORB_XAUUSD_20260821_tester.csv"
    ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
    mv "$D/ORB_XAUUSD_20260821_tester.csv" "$OUT" 2>/dev/null
    echo "$NAME range=${RNG}m tf=M${TF} win=${WIN} hold=${HOLD} -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
  done
done
si InpTimeZone 0; si InpStartHour 0; si InpStartMinute 0
si InpRangeMinutes 15; si InpSignalTF 1; si InpNoEntryAfterMin 15
si InpMaxHoldMinutes 60; si InpForceCloseMin 360
echo ALLDONE
