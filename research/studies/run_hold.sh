#!/bin/bash
# Max hold sweep on the live configuration, 2026 data through 08.21.
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
EXE="terminal6""4.exe"
si () { sed -i "s|^$1=.*|$1=$2|" "$INI"; }
sed -i 's|^ToDate=.*|ToDate=2026.08.22|' "$INI"
si InpMinClosePos 0.50; si InpTradeFri false; si InpRR 2.0
si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5; si InpSLPercentOfRange 50
for H in "$@"; do
  si InpMaxHoldMinutes "$H"
  rm -f "$D"/ORB_XAUUSD_*_tester.csv
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$EXE" /portable /config:tester.ini >/dev/null 2>&1 )
  mv "$D"/ORB_XAUUSD_*_tester.csv "$D/hold_${H}.csv" 2>/dev/null
  echo "hold ${H} min -> $(wc -l < "$D/hold_${H}.csv" 2>/dev/null || echo 0) rows"
done
si InpMaxHoldMinutes 60
