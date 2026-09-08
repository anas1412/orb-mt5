#!/bin/bash
# Test a spec on real ticks and build its full report.
#
#   bash research/report.sh strategies/1step-gold-2r.toml 2026.01.01 2026.09.09
#
# Leaves the trade files under research/out/<name>/, the charts in
# trades-<name>/ and the report at whatever the spec's [report] output names.
# The live pipeline (update.sh) is untouched: its marker, its CSVs, its report.
set -eu
SPEC=$(realpath "${1:?usage: report.sh SPEC FROM TO}"); FROM=${2:?}; TO=${3:?}
HERE=$(cd "$(dirname "$0")" && pwd)
D="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
NAME=$(cd "$HERE" && python3 -c "import spec,sys; print(spec.load(sys.argv[1])['name'])" "$SPEC")
mkdir -p "$HERE/out/$NAME"
( cd "$HERE" && SPEC="$SPEC" bash run_window.sh "$FROM" "$TO" )
cp -f "$D/new_cp0.50.csv" "$HERE/out/$NAME/live_cp0.50.csv"
cp -f "$D/new_cp0.00.csv" "$HERE/out/$NAME/live_cp0.00.csv"
cd "$HERE" && export ORB_SPEC="$SPEC"
python3 report_data.py && python3 all_trades.py && python3 build_report.py && python3 check_charts.py
