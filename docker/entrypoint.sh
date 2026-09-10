#!/bin/bash
# A display for Wine, then whatever was asked. Results are copied to /out when
# it is mounted, so the caller never has to reach into the Wine prefix.
set -u
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp >/dev/null 2>&1 &
sleep 1
# The M1 bar dumps live in the host's Common/Files, and the report steps read
# them. Common/Files itself has to stay PER SLOT, because run_window.sh writes
# new_cp*.csv there and two slots sharing it would overwrite each other. So the
# host folder comes in read-only at /bars and the inputs are copied across --
# cp -u, so a second run on the same slot costs nothing.
D="/root/.wine_mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
if [ -d /bars ]; then
  mkdir -p "$D"
  cp -u /bars/bars_*.csv /bars/d1_*.csv "$D/" 2>/dev/null
  echo "  seeded $(ls "$D" | grep -c '^bars_\|^d1_') input file(s) from /bars"
fi
"$@"; rc=$?
if [ -d /out ]; then
  D="/root/.wine_mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
  cp -f "$D"/*.csv /out/ 2>/dev/null
  cp -rf research/out /out/ 2>/dev/null
  ls *.html 2>/dev/null | grep -v '^index.html$\|^full-report.html$' | xargs -r -I{} cp {} /out/
fi
exit $rc
