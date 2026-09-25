#!/usr/bin/env bash
# Quick check, about 21 s on an Apple M5 Max. No LLM, no network.
#  1. unit tests of the automaton and of the calibration edge cases
#  2. regenerates the seeded core results (RQ1, RQ2 mixed stream, RQ3, RQ4, timing)
#     into a temporary folder and runs the claim checks on them. Timing values of the
#     rerun are reported as INFO because they depend on the host and its load
#  3. compares the regenerated core results with the committed ones (timing skipped)
#  4. checks every camera-ready claim against the committed result files
# The committed files in deon/results are not modified.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
BASE="${TMPDIR:-/tmp}"
TMP="$(mktemp -d "${BASE%/}/deon-smoke.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
cp "$ROOT"/deon/results/*.json "$TMP/"
cd "$ROOT/deon"
echo "[1/4] unit tests"
python3 -m unittest -q test_core
echo "[2/4] core experiments into a temporary folder (about 20 s), then the claim checks on them"
POLICYSHIELD_RESULTS="$TMP" python3 experiments_core.py > /dev/null
python3 "$ROOT/scripts/check-claims.py" --results "$TMP" | tail -n 4
echo "[3/4] regenerated core results against the committed ones"
python3 "$ROOT/scripts/compare-results.py" "$ROOT/deon/results" "$TMP" | tail -n 1
echo "[4/4] camera-ready and extended claims against the committed results"
python3 "$ROOT/scripts/check-claims.py" --skip-gate | tail -n 4
