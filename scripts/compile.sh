#!/usr/bin/env bash
# Compile an MQL5 source on Linux/Wine.
#
# MetaEditor needs a path RELATIVE to the terminal directory and you must be
# standing in that directory -- an absolute C:\... path makes it exit silently
# with no .ex5 and no log. It also returns 1 on a clean compile, so success is
# judged from the log, never from the exit code.
set -uo pipefail

MT5_DIR="${MT5_DIR:-$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5}"
WINEPREFIX="${WINEPREFIX:-$HOME/.wine_mt5}"
TARGET="${1:-MQL5\\Experts\\ORB.mq5}"

[ -d "$MT5_DIR" ] || { echo "No terminal at $MT5_DIR -- set MT5_DIR"; exit 1; }

cd "$MT5_DIR" || exit 1
WINEPREFIX="$WINEPREFIX" WINEDEBUG=-all wine MetaEditor64.exe /compile:"$TARGET" /log 2>/dev/null

LOG="${TARGET//\\//}"; LOG="${LOG%.mq5}.log"
if [ -f "$MT5_DIR/$LOG" ]; then
  iconv -f UTF-16LE -t UTF-8 "$MT5_DIR/$LOG" 2>/dev/null | grep -iE "error|warning|^Result" | tail -5
else
  echo "No log at $LOG -- the path was probably absolute, or MetaEditor never ran"
  exit 1
fi
