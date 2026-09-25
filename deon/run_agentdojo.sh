#!/usr/bin/env bash
# run_agentdojo.sh: the external test of Sect. 7 (RQ2) on the AgentDojo banking suite.
#
# Runs agentdojo_deon.py for nine conditions on 16 user tasks crossed with five
# injection tasks under the important_instructions attack. The conditions are the
# undefended agent, the three prompt-level defenses that AgentDojo ships
# (spotlighting, repeat_user_prompt, tool_filter), four transformer detectors
# (the ProtectAI DeBERTa pi_detector, deepset_detector, testsavant_detector and
# promptguard, which is Prompt-Guard-86M), and the Deon tool-call guard. The script
# writes results/agentdojo_results.json, which holds the benign utility and the
# attack success rate of each condition and is checked by check_results.py. The
# proposer runs stochastically, which means that a rerun gives close but not identical rates. The
# committed file is the snapshot that the paper reports.
#
# Requires a local `ollama serve` with the proposer model pulled, and the optional
# packages of requirements-agentdojo.txt, which the script expects in .venv_ad
# (set PYTHON to use another interpreter).
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${1:-qwen2.5:7b}"
PY="${PYTHON:-.venv_ad/bin/python}"
[ -x "$PY" ] || PY=python3

echo "[agentdojo] model=$MODEL suite=banking attack=important_instructions"
# Five injection tasks are used. They cover data exfiltration through a transfer
# subject (0 and 3), redirection of a recurring payment (4), money theft (5) and a
# credential change (7).
"$PY" agentdojo_deon.py \
  --model "$MODEL" \
  --suite banking \
  --attack important_instructions \
  --defenses none,spotlighting,repeat_user_prompt,tool_filter,pi_detector,deepset_detector,testsavant_detector,promptguard,deon \
  --max-iters 5 \
  --injection-tasks injection_task_0,injection_task_3,injection_task_4,injection_task_5,injection_task_7 \
  --logdir /tmp/ad_full_runs \
  --out results/agentdojo_results.json
echo "[agentdojo] done -> results/agentdojo_results.json"
