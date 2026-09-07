#!/bin/bash
# 3 sessions x RR{1,2} x stop-move{on,off} on real ticks.
# Session times go through TimeZones.mqh: TZ_UTC/TZ_LONDON/TZ_NEWYORK, so each
# zone's own DST rule applies and broker offset is handled by the EA.
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
set_ini () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
set_ini InpRangeMinutes 15
set_ini InpNoEntryAfterMin 15
set_ini InpMaxHoldMinutes 60
set_ini InpSLPercentOfRange 50
set_ini InpRangeLookback 0
set_ini InpRiskPercent 2.0
for S in "Asia 0 0 0" "London 1 8 0" "NewYork 2 9 30"; do
  set -- $S; NAME=$1; TZ=$2; H=$3; M=$4
  set_ini InpTimeZone "$TZ"; set_ini InpStartHour "$H"; set_ini InpStartMinute "$M"
  for RR in 1.0 2.0; do
    set_ini InpRR "$RR"
    for MV in on off; do
      if [ "$MV" = on ]; then set_ini InpStopMoveAtR 0.5; else set_ini InpStopMoveAtR 0; fi
      OUT="$D/mt5_${NAME}_rr${RR}_${MV}.csv"
      rm -f "$D/ORB_XAUUSD_20260821_tester.csv"
      ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
      mv "$D/ORB_XAUUSD_20260821_tester.csv" "$OUT" 2>/dev/null
      echo "$NAME rr=$RR move=$MV -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
    done
  done
done
# restore
set_ini InpTimeZone 0; set_ini InpStartHour 0; set_ini InpStartMinute 0
set_ini InpRR 2.0; set_ini InpStopMoveAtR 0.5
echo ALLDONE
