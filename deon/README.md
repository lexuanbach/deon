# Deon implementation and experiments

This folder holds the implementation of the two runtime checks of the paper, the deontic
policy automaton (DPA) and the conformal execution guard, together with the Deon-Bench
generators and every experiment. The code and several names (the environment variables
`POLICYSHIELD_RESULTS` and `POLICYSHIELD_FIGURES`, the result key `policyshield_asr`)
keep the former project name PolicyShield. The framework in the papers is Deon.

The folder runs on its own. Commands below run from inside `deon/`. The top-level
`README.md` gives the install steps, the scripts that wrap these commands, and the map
from paper items to commands. Section, table and figure numbers follow the current
camera-ready (`../paper/camera-ready.pdf`) unless the extended version
(`../paper/extended.pdf`) is named.

## Files

| File | Purpose |
|---|---|
| `core.py` | The DPA (`DeonticPolicyAutomaton`) and its monitor state, `calibrate_threshold` (marginal and exact-PAC rank), the augmented-score tie-break (`calibrate_randomized_threshold`, `randomized_admit`), Wilson and Hoeffding bounds, and the combined `Guard` (ADMIT, ABSTAIN, BLOCK) |
| `bench.py` | Deon-Bench generators: the 900-trace monitor suite with six violation classes, the latent-risk score pools, and coverage helpers |
| `content.py` | The content-sensitivity detectors (a logistic over pattern features, plus the lexical, numeric and structural detectors of the ensemble) and the obfuscating and naturalising attackers |
| `catalog.py` | The payment and PII service catalogue, its policy, and the benign and attack tasks of the proposer ladder |
| `llm.py` | The proposer client for a local Ollama server (and the OpenAI API), with JSON plan parsing |
| `experiments_core.py` | RQ1 to RQ4 and the monitor timing (keys `e1` to `e8`), written to `results/core_results.json` |
| `experiments_stress.py` | Stress tests `r1` to `r8` (RQ5 and RQ6 of the extended version), written to `results/stress_results.json` |
| `experiments_llm.py` | One model of the proposer ladder, written to `results/llm_summary_<model>.json` |
| `agentdojo_deon.py` | The DPA ported to the AgentDojo banking suite as a tool-call guard, with the eight comparison defences, written to `results/agentdojo_results.json` |
| `check_results.py` | The original 29-check gate on the three result files |
| `test_core.py` | Unit tests of the obligation semantics and the calibration edge cases |
| `make_camera_figures.py` | Camera-ready Fig. 3 (extended Fig. 4), `figures/fig_results.pdf` |
| `make_real_figures.py` | Extended Figs. 3 and 5 (`fig_monitor.pdf`, `fig_coverage.pdf`, `fig_egress.pdf`), plus `fig_guard.pdf` and `fig_attack.pdf`, which neither PDF uses |
| `make_stress_figures.py` | Extended Figs. 6 and 7 (`fig_rq5.pdf`, `fig_rq6.pdf`) |
| `artifact_paths.py` | Resolves `results/` and `figures/`, or the folders named by `POLICYSHIELD_RESULTS` and `POLICYSHIELD_FIGURES` |
| `_run_core_staged.py` | Reruns selected keys of `experiments_core.py` and merges them into `core_results.json` |
| `_merge_agentdojo.py` | Merges separately run AgentDojo defences into `agentdojo_results.json` |
| `run_smoke.sh`, `run_full.sh`, `run_ladder.sh`, `run_agentdojo.sh` | Drivers. `run_smoke.sh` and `run_full.sh` write into `results/` and `figures/`. The top-level `scripts/run-smoke.sh` and `scripts/run-full.sh` write elsewhere and are preferred |
| `requirements.txt`, `requirements-agentdojo.txt` | Direct dependencies with lower bounds. Tested pins are in `../requirements-lock.txt` |
| `results/` | Committed result files |
| `figures/` | Figures made from the committed results. `fig_calib.pdf` and `fig_recover.pdf` are kept from the submitted version, have no generator here, and are not used by either PDF |

## Commands

```bash
python3 -m unittest test_core      # 7 unit tests, under 1 s
python3 check_results.py           # 29 checks on the committed results, under 1 s
python3 experiments_core.py        # rewrites results/core_results.json, 18 s
python3 experiments_stress.py      # rewrites results/stress_results.json, 8 s
python3 make_camera_figures.py     # writes figures/fig_results.pdf
python3 make_real_figures.py       # writes figures/fig_monitor.pdf and four more
python3 make_stress_figures.py     # writes figures/fig_rq5.pdf and fig_rq6.pdf
bash run_ladder.sh 6               # needs `ollama serve` and the six models
bash run_agentdojo.sh              # needs requirements-agentdojo.txt and Ollama
```

Set `POLICYSHIELD_RESULTS=/other/folder` and `POLICYSHIELD_FIGURES=/other/folder` to keep
the committed files. Set `PYTHONDONTWRITEBYTECODE=1` to keep `__pycache__` out of the
folder. The top-level `verify.sh` reports it as an unmanifested file.

## How the data are made

Every label in Deon-Bench is known by construction. The generators plant (or omit) each
violation, and the ground truth needs no human annotation.

- Monitor suite (camera-ready Sect. 7 RQ1). `bench.build_monitor_suite` with seed 0 builds
  900 traces over the fixed payment and PII policy. Even-indexed traces are compliant
  (450). Each odd-indexed trace carries exactly one planted violation of a class drawn
  uniformly from prohibited operation, sequencing, flow, quota, obligation and
  laundering (an indirect PII flow through a fresh field), which gives 84, 65, 81, 83, 70
  and 67 traces. Monitor accuracy and per-class recall compare the DPA verdict with this
  label.
- Latent-risk pools (RQ1). Each item is a score and a latent label. The label is
  Bernoulli(0.30) and the score is a squashed Gaussian whose separation sets detector
  quality (default 2.6, swept from 1.0 to 3.2). The threshold is set on a calibration
  pool of 4000 items and evaluated on a fresh pool of 20,000, over 300 trials per alpha.
- Mixed stream (RQ2). 4000 proposed actions per trial, 35% explicit violations that the
  DPA refuses and 65% drawn from the latent pool, over 400 trials.
- Proposer ladder (RQ2, camera-ready Table 1). `catalog.py` defines 11 operations, of which
  8 benign ones are described to the proposer, and 5 benign and 5 attack tasks
  (exfiltration, skipped authentication, PII to analytics, database dump, quota flood).
  Each model proposes a plan for every task 6 times at temperature 0.7 without seeing
  the policy. Attack success is the share of attack tasks whose plan commits a
  violation, unguarded and under the DPA.
- Content egress (RQ3). An egress action that the DPA permits leaks when its text is
  sensitive. `content.py` scores the text. Calibration uses 3000 texts and evaluation
  4000, over 30 seeds, with plaintext leaks (exchangeable) and obfuscated leaks
  (adaptive).
- Hardening (RQ4, extended version). Three detectors keyed on different signals and their
  max-ensemble, under plaintext, obfuscated and naturalised leaks, and Mondrian
  calibration under a shifted group mix.
- Stress tests (RQ5 and RQ6, extended version). Label noise, small numbers of calibration
  violations, tied scores, detector miscalibration, benign drift, abstention recovery,
  correlated steps within a trace, and scorer versions. The abstention-recovery study
  (`r6_abstention_recovery`) is a Monte Carlo model of the recovery ladder with fixed
  branch probabilities. It does not run the guard on a service catalogue.
- AgentDojo (camera-ready Sect. 7 RQ2, extended Table 4). The DPA is ported to the
  public AgentDojo banking suite: 16 user tasks crossed with 5 injection tasks under the
  important_instructions attack, with a local `qwen2.5:7b` proposer. The policy admits a
  transfer or credential change only when its recipient or new value comes from the
  authenticated user instruction or from an existing counterparty. Four pairs in which
  the benign task itself names the attacker account are excluded, which leaves 76. Nine
  defences share the same proposer and tasks. A refused call is a Block of Def. 2. The
  message returned to the proposer labels it ABSTAIN and routes it to human
  confirmation.

## Determinism

`experiments_core.py` and `experiments_stress.py` use fixed NumPy seeds and repeat bit
for bit, apart from the wall-clock timings of `e5_scalability` and
`r5_drift_rolling/calibration_ms_per_recal`. Both committed result files match the
released code. The ladder and AgentDojo call language models and are not deterministic. Their
committed outputs are frozen snapshots.

## Other proposers

`llm.py` sends model names that start with `gpt-`, `o1` or `o3` to the OpenAI Chat
Completions API and reads the key from `OPENAI_API_KEY`. `python3 experiments_llm.py <model> 6` then
runs the ladder for that model. Deon's guarded attack success is 0 by construction for
the policy-expressible attacks of the suite. Another proposer changes only the
unguarded columns.
