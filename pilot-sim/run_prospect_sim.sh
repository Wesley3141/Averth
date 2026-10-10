#!/bin/bash
# Prospect simulation: prove `averth trace` works from a clean install,
# exactly as a prospect would run it. Fresh venv, install from GitHub,
# run all three trace formats, verify the receipts.
set -u
SIMDIR="$(cd "$(dirname "$0")" && pwd)"
TRACES="$SIMDIR/sim-traces"
VENV=/tmp/prospect-sim-venv

echo "=== 1. fresh environment ==="
rm -rf "$VENV"
python3 -m venv "$VENV" || exit 1

echo "=== 2. install from GitHub (as a prospect would) ==="
"$VENV/bin/pip" install -q "git+https://github.com/Wesley3141/Averth.git" || exit 1
"$VENV/bin/averth" --help >/dev/null 2>&1 || { echo "FAIL: averth CLI missing"; exit 1; }
echo "install ok"

echo "=== 3. generate fake production traces ==="
python3 "$SIMDIR/gen_traces.py" "$TRACES"

pass=0; fail=0
run_case() {
  local fmt="$1" file="$2"
  echo "--- format: $fmt ---"
  out=$("$VENV/bin/averth" trace "$file" --format "$fmt" --agent acme-support 2>&1)
  code=$?
  [ $code -eq 0 ] || { echo "FAIL: exit $code"; echo "$out" | head -5; fail=$((fail+1)); return; }
  echo "$out" | grep -q "Data quality" || { echo "FAIL: no Data quality section"; fail=$((fail+1)); return; }
  echo "$out" | grep -q "Vendor-supplied (billed)" || { echo "FAIL: no billed bucket"; fail=$((fail+1)); return; }
  echo "$out" | grep -q "The five layers" || { echo "FAIL: no five layers"; fail=$((fail+1)); return; }
  # unknown bucket must be flagged when present (langfuse + langsmith have unknowns)
  if [ "$fmt" != "otel" ]; then
    echo "$out" | grep -qi "unknown" || { echo "FAIL: unknown bucket not flagged"; fail=$((fail+1)); return; }
  fi
  # key numbers for the human-readable proof
  echo "$out" | grep -E "^(Attempts|Total cost|Cost per successful)" | head -3
  echo "$out" | grep -A4 "Data quality" | head -5
  pass=$((pass+1))
}

run_case langfuse "$TRACES/langfuse.json"
run_case langsmith "$TRACES/langsmith.json"
run_case otel "$TRACES/otel.json"

echo "=== result: $pass passed, $fail failed ==="
rm -rf "$VENV"
[ "$fail" -eq 0 ]
