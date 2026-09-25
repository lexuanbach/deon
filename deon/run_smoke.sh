#!/usr/bin/env bash
# run_smoke.sh: quick check of the Deon artifact.
#
# Regenerates the model-free core results of experiments_core.py in about 20 seconds
# (RQ1 monitor agreement and calibration, the RQ2 mixed stream, RQ3 content egress,
# the RQ4 ensemble and Mondrian studies, and the monitor timing) and then runs
# check_results.py on them. It does not run the proposer ladder of RQ2, which needs
# a local Ollama installation (see run_ladder.sh), nor the stress tests of RQ5 and
# RQ6 (experiments_stress.py). The timing check depends on the machine and can
# fail on a much slower or faster one.
#
# For the full study use run_full.sh.
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/2] Reproducing deterministic core experiments (~20s) ..."
# experiments_core.py is seeded and rewrites results/core_results.json with the same
# numbers apart from the timings. The committed file is copied first and restored at the end.
mkdir -p results
cp results/core_results.json results/core_results.json.bak
python3 experiments_core.py > /dev/null

echo "[2/2] Verifying regenerated numbers against the manuscript ..."
if python3 check_results.py; then
    status=0
else
    status=1
fi

# Restore the committed results.
mv results/core_results.json.bak results/core_results.json
exit $status
