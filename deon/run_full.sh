#!/usr/bin/env bash
# run_full.sh: full reproduction of the Deon study (the directory keeps the former
# name policyshield).
#
# Step 1 runs the model-free experiments of experiments_core.py (RQ1 monitor
# agreement and calibration, the RQ2 mixed stream, RQ3 content egress, the RQ4
# ensemble and Mondrian studies and the monitor timing). Step 2 runs the stress
# tests of experiments_stress.py (RQ5 and RQ6 of the extended version). Step 3 runs
# the six-model proposer ladder of RQ2 (Table 1), which needs a local `ollama serve`
# and is skipped with a message if ollama is absent, in which case the committed
# llm_summary_*.json files are used. Step 4 rebuilds the figures from the results
# and step 5 compares them with the numbers quoted in the paper. The AgentDojo test
# is not part of this script because it needs its own environment and is run
# separately with run_agentdojo.sh.
#
# For a quick check use run_smoke.sh, which needs no Ollama and takes about 20 s.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p results figures

echo "[1/5] Deterministic core experiments (RQ1/RQ2/RQ3/RQ6 timing) ..."
python3 experiments_core.py

echo "[2/5] Hardening + calibration-stress experiments (RQ4/RQ5/RQ6) ..."
python3 experiments_stress.py

echo "[3/5] Six-model attack ladder (RQ2/RQ3; requires 'ollama serve') ..."
if command -v ollama >/dev/null 2>&1; then
  bash run_ladder.sh 6
else
  echo "  ollama not found; skipping the LLM ladder (bundled llm_summary_*.json used)."
fi

echo "[4/5] Regenerating manuscript figures ..."
python3 make_real_figures.py
python3 make_stress_figures.py

echo "[5/5] Verifying regenerated numbers against the manuscript ..."
python3 check_results.py

echo "DONE. Results in results/, figures in figures/."
