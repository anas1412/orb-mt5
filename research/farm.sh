#!/bin/bash
# Run several backtests at once, one container per slot.
#
#   bash research/farm.sh --slots 3 --env accounts/ftmo.env SPEC...
#   bash research/farm.sh --dry-run --slots 3 strategies/*.toml
#
# MetaTrader keeps its tester lock and its agent's private history copy inside
# Tester/, so two terminals sharing that directory fight and one of them exits
# without saying why -- the failure run_window.sh already guards against. Each
# slot therefore gets its OWN Bases/, Tester/ and Config/ volume and never sees
# another slot's. Bases is seeded once from this machine's terminal, because a
# fresh volume makes the tester re-import every month of ticks from the broker.
#
# The repo is bind-mounted, so a change to a spec or a script takes effect
# without rebuilding the 7 GB image. Rebuild only when the Dockerfile or the
# staged MetaTrader binaries change.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/.." && pwd)
IMAGE=${IMAGE:-orb-mt5}
SLOTS=3; ENVFILE=""; DRY=no; FROM=""; TO=""; SPECS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --slots)   SLOTS="${2:?}"; shift 2 ;;
    --env)     ENVFILE="${2:?}"; shift 2 ;;
    --from)    FROM="${2:?}"; shift 2 ;;
    --to)      TO="${2:?}"; shift 2 ;;
    --dry-run) DRY=yes; shift ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *)  SPECS+=("$1"); shift ;;
  esac
done
[ "${#SPECS[@]}" -gt 0 ] || { echo "usage: farm.sh [--slots N] [--env FILE] [--from D --to D] SPEC..." >&2; exit 2; }
MT5H="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5"
CT="/root/.wine_mt5/drive_c/Program Files/MetaTrader 5"
CTC="/root/.wine_mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
HOSTC="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
OUT="$REPO/research/out/farm"; mkdir -p "$OUT"

# Each spec names its own window unless the caller overrides it, so a farm can
# mix a 2026 spec with a 2024-2026 one.
win () {   # SPEC -> "FROM TO"
  ( cd "$HERE" && python3 - "$1" <<'PY'
import sys, spec, datetime as dt
s=spec.load(sys.argv[1]); d=s["dates"]
to=(dt.date.today()+dt.timedelta(days=1)) if d["to"]=="today" else d["to"]
print(d["from"].strftime("%Y.%m.%d"), to.strftime("%Y.%m.%d"))
PY
  )
}

seed () {   # SLOT -- create the three volumes, and fill Bases once
  local i="$1"
  for v in bases tester config common; do docker volume create "orb-$v-$i" >/dev/null; done
  if [ -z "$(docker run --rm -v "orb-bases-$i:/b" "$IMAGE" sh -c 'ls -A /b 2>/dev/null | head -1')" ]; then
    echo "  slot $i: seeding Bases from this machine (once)"
    docker run --rm -v "orb-bases-$i:/b" -v "$MT5H/Bases:/src:ro" \
      "$IMAGE" sh -c 'cp -a /src/. /b/' >/dev/null
  fi
}

run_one () {   # SLOT SPEC
  local i="$1" sp="$2" name id f t
  name=$(cd "$HERE" && python3 -c "import spec,sys;print(spec.load(sys.argv[1])['name'])" "$sp")
  read -r f t <<<"$(win "$sp")"
  [ -n "$FROM" ] && f="$FROM"; [ -n "$TO" ] && t="$TO"
  id="$name-$(date +%H%M%S)-s$i"
  local args=(--rm --name "orb-farm-$i" --cpus 1.5 --memory 2g
    -v "orb-bases-$i:$CT/Bases" -v "orb-tester-$i:$CT/Tester" -v "orb-config-$i:$CT/Config"
    -v "orb-common-$i:$CTC" -v "$HOSTC:/bars:ro"
    -v "$REPO:/root/orb/strategy" -v "$OUT:/out")
  [ -n "$ENVFILE" ] && args+=(--env-file "$ENVFILE")
  if [ "$DRY" = yes ]; then
    printf '  slot %s  %-22s %s..%s  id=%s\n' "$i" "$name" "$f" "$t" "$id"; return 0
  fi
  docker run "${args[@]}" "$IMAGE" \
    bash research/report.sh --id "$id" "/root/orb/strategy/${sp#"$REPO/"}" "$f" "$t" \
    >"$OUT/$id.container.log" 2>&1 && echo "  slot $i: $name OK" \
    || echo "  slot $i: $name FAILED (see research/out/farm/$id.container.log)"
}

echo "farm: ${#SPECS[@]} spec(s), $SLOTS slot(s), image $IMAGE${ENVFILE:+, account $(basename "$ENVFILE" .env)}"
[ "$DRY" = yes ] || for i in $(seq 1 "$SLOTS"); do seed "$i"; done
n=0
for sp in "${SPECS[@]}"; do
  sp=$(realpath "$sp")
  while [ "$(jobs -rp | wc -l)" -ge "$SLOTS" ]; do wait -n; done
  n=$((n+1)); slot=$(( (n-1) % SLOTS + 1 ))
  run_one "$slot" "$sp" &
done
wait
if [ "$DRY" = no ]; then
  # container-written files are root-owned; hand them back
  command -v sudo >/dev/null && sudo chown -R "$(id -u):$(id -g)" "$OUT" 2>/dev/null || true
  echo; python3 "$HERE/farm_stats.py" --last "${#SPECS[@]}" || true
fi
