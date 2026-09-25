#!/usr/bin/env bash
# Proposer ladder of RQ2 (Table 1). Runs the six local Ollama models of the paper, from
# 2B to 47B parameters, through the benign and the injected tasks of catalog.py,
# unguarded and guarded by Deon, by calling experiments_llm.py once per model. Each call
# writes results/llm_summary_<model>.json, and one such file is one row of Table 1.
# Usage: bash run_ladder.sh [reps]   (repetitions per task, default 6)
# The models must already be pulled into the local Ollama server. The script keeps going
# if one model fails, and prints the tail of each run.
set -u
cd "$(dirname "$0")"
REPS="${1:-6}"
MODELS=(
  "gemma2:2b"
  "llama3.2:3b"
  "qwen2.5-coder:7b"
  "command-r:35b"
  "qwen2.5-coder:32b"
  "mixtral:8x7b"
)
echo "=== PolicyShield attack ladder (reps=$REPS) ==="
for m in "${MODELS[@]}"; do
  echo "---- $m ----"
  python3 experiments_llm.py "$m" "$REPS" 2>&1 | tail -12
done
echo "=== done ==="
