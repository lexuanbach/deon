#!/usr/bin/env bash
# Regenerate every model-free result and every figure into a separate output folder,
# then check them against the papers and compare them with the committed results.
#
# The committed files in deon/results and deon/figures are not modified. The output
# folder is $DEON_OUT, or ${TMPDIR:-/tmp}/deon-full-run when DEON_OUT is unset.
# About 35 s on an Apple M5 Max (core experiments 18 s, stress tests 8 s, figures 3 s).
#
# Optional, non-deterministic parts (not run by default):
#   RUN_OPTIONAL_LLM=1  also runs the six-model Ollama ladder (needs `ollama serve` and
#                       the six models, not timed). Its summaries go to the output
#                       folder and replace the copies of the committed ones there.
#   AgentDojo           is never started from here. See README.md, section "Runs that
#                       need external resources".
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${TMPDIR:-/tmp}"
OUT="${DEON_OUT:-${BASE%/}/deon-full-run}"
OUT="${OUT%/}"
mkdir -p "$OUT/results" "$OUT/figures"
export PYTHONDONTWRITEBYTECODE=1
export POLICYSHIELD_RESULTS="$OUT/results" POLICYSHIELD_FIGURES="$OUT/figures"

# The LLM and AgentDojo results cannot be regenerated deterministically. Copy the
# committed snapshots so that the checks below see a complete results folder.
cp "$ROOT"/deon/results/agentdojo_results.json "$ROOT"/deon/results/llm_summary_*.json \
   "$ROOT"/deon/results/ladder.log "$OUT/results/"

cd "$ROOT/deon"
echo "[1/7] unit tests of the automaton and calibration edge cases"
python3 -m unittest -q test_core
echo "[2/7] core experiments (RQ1, RQ2 mixed stream, RQ3, RQ4, timing) -> $OUT/results/core_results.json"
python3 experiments_core.py > "$OUT/core.log"
echo "[3/7] stress tests (RQ5, RQ6 of the extended version) -> $OUT/results/stress_results.json"
python3 experiments_stress.py > "$OUT/stress.log"
if [[ "${RUN_OPTIONAL_LLM:-0}" == "1" ]]; then
  if command -v ollama >/dev/null 2>&1; then
    echo "[opt] Ollama ladder, six models"
    bash run_ladder.sh 6 | tee "$OUT/results/ladder.log"
  else
    echo "[opt] UNAVAILABLE: ollama not found, the committed ladder summaries are used"
  fi
else
  echo "[opt] SKIPPED: Ollama ladder (set RUN_OPTIONAL_LLM=1 to run it)"
fi
echo "[4/7] figures -> $OUT/figures"
python3 make_camera_figures.py
python3 make_real_figures.py
python3 make_stress_figures.py
echo "[5/7] tables"
python3 "$ROOT/scripts/make-tables.py" --results "$OUT/results" > "$OUT/tables.txt"
echo "  wrote $OUT/tables.txt"
echo "[6/7] claim checks on the regenerated results"
status=0
python3 "$ROOT/scripts/check-claims.py" --results "$OUT/results" > "$OUT/check-claims.txt" || status=1
tail -n 4 "$OUT/check-claims.txt"
echo "[7/7] regenerated results against the committed ones"
python3 "$ROOT/scripts/compare-results.py" "$ROOT/deon/results" "$OUT/results" || status=1
if python3 -c "import agentdojo" >/dev/null 2>&1; then
  echo "NOTE: AgentDojo is installed. Run deon/run_agentdojo.sh yourself for a new (non-deterministic) run."
else
  echo "NOTE: AgentDojo not installed. The committed snapshot deon/results/agentdojo_results.json is used."
fi
echo "Output folder: $OUT"
exit $status
