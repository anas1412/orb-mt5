#!/bin/bash
# Friday on a 1R target while Monday-Thursday keep 2R.
#
# The EA has one InpRR, so the blend is composed from two runs rather than
# coded: one trade a day and no cross-day state means each day's result is
# independent, so Mon-Thu rows from the 2R run plus Friday rows from the 1R run
# ARE the mixed strategy, exactly.
set -u
MT5="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
D="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
INI="$HOME/orb/strategy/tester.ini"
si () { grep -q "^$1=" "$INI" || { echo "FATAL: $1 absent from tester.ini"; exit 1; }
        sed -i "s|^$1=.*|$1=$2|" "$INI"; }
run () { rm -f "$D"/ORB_XAUUSD_*_tester.csv
  ( cd "$MT5" && WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine terminal6"4".exe /portable /config:tester.ini >/dev/null 2>&1 )
  mv "$D"/ORB_XAUUSD_*_tester.csv "$D/$1.csv" 2>/dev/null \
    && echo "$1: $(wc -l < "$D/$1.csv") rows" || { echo "FATAL: $1 produced no CSV"; exit 1; }; }

si InpLotMode 1; si InpRiskPercent 2.0; si InpMinClosePos 0.50
si InpMaxHoldMinutes 90; si InpStopMoveAtR 0.5; si InpStopMoveToR -0.5
si InpSLPercentOfRange 50

si InpTradeFri true; si InpRR 1.0;  run fri_rr1     # harvest Fridays from this
si InpTradeFri true; si InpRR 2.0;  run alldays_rr2 # for the comparison
si InpTradeFri false; si InpRR 2.0                  # leave the ini as shipped
