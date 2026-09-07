# Shared by update.sh and run_window.sh. Source it, do not run it.

# Build the config MetaTrader is launched with: the template (tester.ini,
# dump.ini, sync.ini) plus, when MT5_LOGIN is set, a [Common] block so the
# terminal logs into that account rather than the one it last used. Written as
# a real file inside the terminal folder -- never into the repo, it may carry a
# password -- and the caller removes it after the run.
mt5_config () {   # SRC DST
  cp -f "$1" "$2"
  if [ -n "${MT5_LOGIN:-}" ]; then
    printf '\n[Common]\nLogin=%s\nPassword=%s\nServer=%s\n' \
      "$MT5_LOGIN" "${MT5_PASSWORD:?MT5_PASSWORD is not set}" "${MT5_SERVER:?MT5_SERVER is not set}" >> "$2"
  fi
}

# The terminal journal is one file per day, so a failure from an EARLIER launch
# is still in it. Mark where the journal ends before launching, then judge only
# what was appended. It is UTF-16LE, hence iconv.
MT5_JOURNAL="$MT5/logs/$(date +%Y%m%d).log"
mt5_mark () { MT5_JMARK=$(stat -c%s "$MT5_JOURNAL" 2>/dev/null || echo 0); }
mt5_since_mark () { tail -c +$(( ${MT5_JMARK:-0} + 1 )) "$MT5_JOURNAL" 2>/dev/null | iconv -f UTF-16LE -t UTF-8 2>/dev/null; }
# Looks like:  Network  '12345': authorization on X failed (Invalid account)
mt5_login_failed () { mt5_since_mark | grep -q "authorization on .* failed"; }

MT5_EXE="terminal6""4.exe"        # split so pgrep -f never matches a script mentioning it
MT5_AGENT="metatester6""[4].exe"  # the tester agent, as a pattern that cannot match itself

# The terminal runs the Strategy Tester in a separate agent process. It survives
# a kill of the terminal and holds the tester lock. Its file name is 16
# characters and the kernel truncates process names to 15, so `pkill -x` can
# never match it -- hence -f with a bracket, so the pattern cannot match a
# script that merely mentions it. Every line tolerates "nothing to kill": the
# callers run under set -e, and a pkill that found nothing must not abort the
# reset half-way and leave Wine dirty for the next launch.
mt5_reset () {
  pkill -9 -x "$MT5_EXE" 2>/dev/null || true
  pkill -9 -f "$MT5_AGENT" 2>/dev/null || true
  sleep 1; WINEPREFIX="$HOME/.wine_mt5" wineserver -k 2>/dev/null || true; sleep 2
}

# Launch MetaTrader with a config from the terminal folder and wait for it.
# Watches the journal while it runs: after a FAILED login the terminal still
# starts the tester on cached data, then hangs for ever waiting for a server it
# never reached -- so the failure is read from the journal and the terminal is
# killed, rather than waited out. A hard kill leaves Wine unable to start the
# next terminal (it exits 0 and logs nothing), so every kill resets wineserver.
# Returns 0 when the terminal exited on its own, 1 on login failure or timeout.
mt5_run () {   # CONFIG  [TIMEOUT_SECS]
  local cfg="$1" secs="${2:-900}" t=0 pid
  # Nothing running means a clean reset is free, and it is the cure for the
  # "exits 0, logs nothing" state Wine is left in after any hard kill.
  pgrep -x "$MT5_EXE" >/dev/null || mt5_reset
  mt5_mark
  # setsid + closed stdio: nothing Wine spawns may inherit the caller's pipe,
  # or a `| tail` on the caller keeps waiting long after the script has exited.
  ( cd "$MT5" && exec setsid env WINEPREFIX="$HOME/.wine_mt5" WINEDEBUG=-all wine "$MT5_EXE" /portable /config:"$cfg" ) </dev/null >/dev/null 2>&1 &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    if mt5_login_failed; then
      mt5_reset; wait "$pid" 2>/dev/null || true
      echo "MetaTrader could not log in${MT5_LOGIN:+ as $MT5_LOGIN on ${MT5_SERVER:-?}} -- check accounts/*.env" >&2
      return 1
    fi
    if [ "$t" -ge "$secs" ]; then
      mt5_reset; wait "$pid" 2>/dev/null || true
      echo "MetaTrader did not finish within ${secs}s -- killed" >&2
      return 1
    fi
    sleep 2; t=$((t+2))
  done
  wait "$pid" 2>/dev/null || true; return 0
}
