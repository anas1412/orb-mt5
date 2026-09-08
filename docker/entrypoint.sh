#!/bin/bash
# A display for Wine, then whatever was asked. Results are copied to /out when
# it is mounted, so the caller never has to reach into the Wine prefix.
set -u
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp >/dev/null 2>&1 &
sleep 1
"$@"; rc=$?
if [ -d /out ]; then
  D="/root/.wine_mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
  cp -f "$D"/*.csv /out/ 2>/dev/null
  cp -rf research/out /out/ 2>/dev/null
  ls *.html 2>/dev/null | grep -v '^index.html$\|^full-report.html$' | xargs -r -I{} cp {} /out/
fi
exit $rc
