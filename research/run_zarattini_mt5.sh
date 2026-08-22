#!/bin/bash
# Published ORB shape on US100: 5-min opening interval, trade its direction at
# its close, stop at the interval extreme, far target, hold to the cash close.
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/blackbox/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
sed -i 's|^Symbol=.*|Symbol=US100.cash|' "$INI"
si InpTimeZone 2; si InpStartHour 9; si InpStartMinute 30
si InpRangeMinutes 5                 # the 09:30-09:34 interval
si InpEntryMode 3                    # ENTRY_FIRST_CANDLE
si InpNoEntryAfterMin 0
si InpMaxHoldMinutes 0               # no per-trade cap
si InpForceCloseMin 385              # 09:35 + 385 min = 16:00 NY cash close
si InpStopMoveAtR 0                  # published version does not move the stop
si InpRangeLookback 0; si InpMinClosePos 0; si InpRiskPercent 2.0
si InpTradeMon true; si InpTradeTue true; si InpTradeWed true; si InpTradeThu true; si InpTradeFri true
for RR in 5.0 10.0 20.0; do
  si InpRR "$RR"
  OUT="$D/zar_rr${RR}.csv"
  rm -f "$D/ORB_US100.cash_20260821_tester.csv"
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
  mv "$D/ORB_US100.cash_20260821_tester.csv" "$OUT" 2>/dev/null
  echo "RR ${RR} -> $(wc -l < "$OUT" 2>/dev/null || echo 0) rows"
done
# restore the live Asia gold configuration
sed -i 's|^Symbol=.*|Symbol=XAUUSD|' "$INI"
si InpTimeZone 0; si InpStartHour 0; si InpStartMinute 0
si InpRangeMinutes 15; si InpEntryMode 0; si InpNoEntryAfterMin 15
si InpMaxHoldMinutes 60; si InpForceCloseMin 360
si InpStopMoveAtR 0.5; si InpRR 2.0; si InpMinClosePos 0.25; si InpTradeFri false
echo ALLDONE
