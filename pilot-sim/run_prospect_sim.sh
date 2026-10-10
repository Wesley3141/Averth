#!/bin/bash
# Prospect simulation: prove `averth trace` works from a clean install,
# exactly as a prospect would run it. Fresh venv, uncached install from
# GitHub, all three trace formats, NUMERIC receipt assertions.
set -u
SIMDIR="$(cd "$(dirname "$0")" && pwd)"
TRACES="$SIMDIR/sim-traces"
VENV=/tmp/prospect-sim-venv

echo "=== 1. fresh environment ==="
rm -rf "$VENV"
python3 -m venv "$VENV" || exit 1

echo "=== 2. install from GitHub, no cache (as a prospect would) ==="
"$VENV/bin/pip" install -q --no-cache-dir \
  "git+https://github.com/Wesley3141/Averth.git" || exit 1
"$VENV/bin/averth" --help >/dev/null 2>&1 \
  || { echo "FAIL: averth CLI missing"; exit 1; }
echo "install ok"

echo "=== 3. generate fake production traces ==="
python3 "$SIMDIR/gen_traces.py" "$TRACES"

echo "=== 4. numeric receipt checks ==="
fail=0
"$VENV/bin/python" "$SIMDIR/check_receipt.py" "$VENV/bin/averth" \
  langfuse "$TRACES/langfuse.json" 5 || fail=1
"$VENV/bin/python" "$SIMDIR/check_receipt.py" "$VENV/bin/averth" \
  langsmith "$TRACES/langsmith.json" 5 || fail=1
"$VENV/bin/python" "$SIMDIR/check_receipt.py" "$VENV/bin/averth" \
  otel "$TRACES/otel.json" 0 || fail=1

echo "=== 5. cleanup ==="
rm -rf "$VENV"

if [ "$fail" -eq 0 ]; then
  echo "RESULT: all prospect-simulation checks passed"
else
  echo "RESULT: FAILURES above"
fi
exit "$fail"
