#!/usr/bin/env bash
# Headless backtest on Linux/Wine using tester.ini.
#
# MT5 refuses a second instance on the same data directory, so close the GUI
# terminal first. tester.ini sets ShutdownTerminal=1, so this exits on its own.
set -uo pipefail

MT5_DIR="${MT5_DIR:-$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5}"
WINEPREFIX="${WINEPREFIX:-$HOME/.wine_mt5}"
CFG="${1:-tester.ini}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

[ -d "$MT5_DIR" ] || { echo "No terminal at $MT5_DIR -- set MT5_DIR"; exit 1; }
[ -f "$HERE/$CFG" ] || { echo "No $CFG in $HERE"; exit 1; }

# note the bracket: keeps this script's own command line from matching
if pgrep -f 'terminal6[4].exe' >/dev/null; then
  echo "A terminal is already running -- close it first (MT5 allows one instance per data dir)"
  exit 1
fi

cp "$HERE/$CFG" "$MT5_DIR/$CFG"
cd "$MT5_DIR" || exit 1
WINEPREFIX="$WINEPREFIX" WINEDEBUG=-all wine terminal64.exe /portable /config:"$CFG" 2>/dev/null

COMMON="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
echo
echo "Trade log:"
ls -1 "$COMMON"/ORB_*_tester.csv 2>/dev/null || echo "  none found -- check the tester journal"
echo
iconv -f UTF-16LE -t UTF-8 "$MT5_DIR/Tester/logs/"*.log 2>/dev/null \
  | grep -E "final balance|Test passed" | tail -2
