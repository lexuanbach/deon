"""Run selected experiments of experiments_core.py one at a time.

Usage: python3 _run_core_staged.py e2_conformal_coverage [e5_scalability ...]

The arguments are the stage keys in STAGES below, which are the same keys that
experiments_core.main() writes. Each stage is run in this process and its result is
merged into results/core_results.json under that key, and the file is rewritten after
every stage. This makes it possible to regenerate a single slow block (the 300-trial
coverage sweep of RQ1 or the timing loop of the scalability measurement) without
repeating the others. Every stage is seeded inside experiments_core.py, and a stage
produces the same numbers here as in a full run. Timing values (e5_scalability) vary
with the machine.

Stage to paper map: e1, e2, e3 back RQ1, e4 backs the mixed-stream result of RQ2,
e6 backs RQ3, e7 and e8 back RQ4 (extended version), e5 is the timing result.
"""
import sys, os, json
import experiments_core as e
from artifact_paths import RESULTS, ensure_dir

STAGES = {
    "e1_monitor_soundness": e.e1_monitor_soundness,
    "e2_conformal_coverage": e.e2_conformal_coverage,
    "e3_risk_utility": e.e3_risk_utility,
    "e4_attack_synth": e.e4_attack_synth,
    "e6_content_egress": e.e6_content_egress,
    "e7_ensemble_egress": e.e7_ensemble_egress,
    "e8_mondrian_shift": e.e8_mondrian_shift,
    "e5_scalability": e.e5_scalability,
}

path = os.path.join(ensure_dir(RESULTS), "core_results.json")


def load():
    try:
        return json.load(open(path))
    except Exception:
        return {}


def main():
    keys = sys.argv[1:]
    res = load()
    for k in keys:
        print("running", k, flush=True)
        res[k] = STAGES[k]()
        json.dump(res, open(path, "w"), indent=2)
        print("  wrote", k, flush=True)


if __name__ == "__main__":
    main()
