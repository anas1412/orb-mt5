#!/bin/bash
# Two ways to time the exit, on the same live configuration:
#   A) per-trade hold, counted from the fill      -> InpMaxHoldMinutes
#   B) a fixed clock, counted from the range close -> InpForceCloseMin, hold off
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
sed -i 's|^ToDate=.*|ToDate=2026.08.22|' "$INI"
si InpMinClosePos 0.50; si InpTradeFri false; si InpRR 2.0
si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5; si InpSLPercentOfRange 50
run () {  # $1 = output tag
  rm -f "$D"/ORB_XAUUSD_*_tester.csv
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
  mv "$D"/ORB_XAUUSD_*_tester.csv "$D/$1.csv" 2>/dev/null
  echo "$1 -> $(wc -l < "$D/$1.csv" 2>/dev/null || echo 0) rows"
}
si InpForceCloseMin 360
for H in 60 75 90 105 120; do si InpMaxHoldMinutes "$H"; run "xa_$H"; done
si InpMaxHoldMinutes 0
for F in 60 75 90 105 120 150; do si InpForceCloseMin "$F"; run "xb_$F"; done
si InpMaxHoldMinutes 90; si InpForceCloseMin 360
echo ALLDONE
