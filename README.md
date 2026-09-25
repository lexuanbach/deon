# Deon: artifact for the ICSOC 2026 paper

This package accompanies the paper **Deon: Runtime Guards for Policy-Safe Agentic Service
Composition under Attack** (ICSOC 2026). It holds the implementation of the deontic policy
automaton (DPA) and the conformal execution guard, the Deon-Bench generators, every
experiment script, the committed result files, the figures, and the two papers:

- `paper/camera-ready.pdf`: the 10-page ICSOC 2026 paper (RQ1 to RQ3).
- `paper/extended.pdf`: the 45-page extended version (RQ1 to RQ6, proofs, appendices).

Public repository: https://github.com/lexuanbach/deon

Table, figure and section numbers in this package follow the current PDFs above. In the
camera-ready, Table 1 is the proposer ladder and Fig. 3 is the three-panel results figure.
In the extended version the same ladder is Table 3 and the same figure is Fig. 4.

## Contents

| Path | What it holds |
|---|---|
| `deon/` | Python implementation and experiments. `deon/README.md` describes every file. |
| `deon/results/` | Committed result files: `core_results.json`, `stress_results.json`, `agentdojo_results.json`, six `llm_summary_*.json`, `ladder.log` |
| `deon/figures/` | Figures generated from the committed results |
| `paper/` | The two PDFs |
| `scripts/verify.sh` | Manifest, hygiene, and claim checks on the committed results (2 s) |
| `scripts/run-smoke.sh` | Unit tests, a rerun of the core experiments, and the claim checks (21 s) |
| `scripts/run-full.sh` | Reruns every model-free experiment and figure into a separate folder and compares the output with the committed results (35 s) |
| `scripts/check-claims.py` | Checks 239 numbers of the two papers against the result files |
| `scripts/compare-results.py` | Compares regenerated result files with the committed ones |
| `scripts/make-tables.py` | Prints camera-ready Table 1 and extended Tables 3, 4, 5 and 9 from the result files |
| `CLAIM_MATRIX.md` | Every quantitative claim, its source file and key, the command, and its status |
| `EXPECTED_RESULTS.md` | What each command prints when it succeeds |
| `REPRODUCIBILITY.md` | Environment, runtimes, seeds, and the runs that need external resources |
| `MANIFEST.sha256` | SHA-256 of every file |

## Requirements

- Operating system: tested on macOS 26.5 on an Apple M5 Max (arm64, 64 GB RAM). The code is
  plain Python with no platform-specific calls. Linux was not tested for this release.
- Python 3.13 or 3.14 (tested with 3.13.5 and 3.14.6).
- Python packages: NumPy, SciPy and Matplotlib. `requirements-lock.txt` pins the tested
  versions (numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2). SciPy is optional. Without it
  `core.py` uses an exact fallback that gives the same PAC ranks.
- Hardware: any recent laptop. The model-free experiments use one CPU core and less than
  1 GB of memory.
- `pdfinfo` (poppler) is optional. `verify.sh` uses it to check the page count.
- No network access, GPU, API key or LLM server is needed for the steps in this README
  up to "Runs that need external resources".

## Install

Create the virtual environment outside the artifact folder. The hygiene check fails on a
`.venv` or `venv` folder inside it.

```bash
cd Deon-ICSOC2026
python3 -m venv ../deon-venv
. ../deon-venv/bin/activate
python3 -m pip install -r requirements-lock.txt
```

## Quick start

```bash
bash scripts/verify.sh       # 2 s. Manifest, hygiene, 29-check gate, 239 paper claims
bash scripts/run-smoke.sh    # 21 s. Unit tests, core experiments rerun in a temp folder, claims
bash scripts/run-full.sh     # 35 s. All model-free experiments, figures and tables, then comparisons
```

The first call in a new environment takes about 15 s longer while macOS and Python load
the new packages. The scripts set `PYTHONDONTWRITEBYTECODE=1`. If you run Python in `deon/` yourself, set
it too or delete `deon/__pycache__` afterwards. Otherwise `verify.sh` reports the cache
folder as an unmanifested file. `run-full.sh` writes to `$DEON_OUT`, or to
`${TMPDIR:-/tmp}/deon-full-run` when `DEON_OUT` is unset, and never modifies
`deon/results` or `deon/figures`. `EXPECTED_RESULTS.md` shows the expected output of each
command.

## Reproducing each result

Commands run from the artifact root. `scripts/check-claims.py` compares every committed
value below with both papers. The "Regenerate with" column gives the command that
produces the value again from code. Runtimes are for an Apple M5 Max.

| Paper item (camera-ready) | Extended version | Source in `deon/results/` | Regenerate with | Runtime | Deterministic |
|---|---|---|---|---|---|
| Sect. 7 RQ1: monitor accuracy, per-class recall, 84/65/81/83/70/67 | Sect. 9.1, Fig. 3 left | `core_results.json` key `e1_monitor_soundness` | `scripts/run-full.sh` (step 2) | under 1 s | yes, seed 0 |
| Sect. 7 RQ1, Fig. 3a: marginal and exact-PAC coverage | Sect. 9.1, Fig. 3 right, Fig. 4a, Table 6 | `e2_conformal_coverage` | same | 2 s | yes, seed 1 |
| Sect. 7 RQ1: detector quality and fixed cutoff | Sect. 9.1, Fig. 5b, Table 6 | `e3_risk_utility` | same | 1 s | yes, seed 2 |
| Sect. 7 RQ2: mixed stream 100% / 35.7% / 3.6% | Sect. 9.2 | `e4_attack_synth` | same | under 1 s | yes, seed 3 |
| Sect. 7 RQ3, Fig. 3b: content egress 0.089 / 0.328 | Sect. 9.3, Fig. 5a | `e6_content_egress` | same | 3 s | yes, seeds 6 to 35 |
| Sect. 7 RQ3, Fig. 3c: ensemble 0.097, lexical 0.835 | Sect. 9.4, Table 5 | `e7_ensemble_egress` | same | 7 s | yes, seeds 7 to 36 |
| Sect. 7 stress tests: Mondrian 0.441 to 0.091 | Sect. 9.4, Table 7 | `e8_mondrian_shift` | same | under 1 s | yes, seeds 8 to 37 |
| Sect. 7 stress tests: monitor cost, R^2 | Sect. 9.5 "Monitor cost" | `e5_scalability` | same | 5 s | no, wall-clock timing |
| Sect. 7 stress tests: label noise, ties, rank k'=0 | Sect. 9.5 to 9.7, Figs. 6 and 7, Tables 6 and 7 | `stress_results.json` | `scripts/run-full.sh` (step 3) | 8 s | yes, base seeds 101 to 801 |
| Table 1: proposer ladder | Table 3 | `llm_summary_*.json`, `ladder.log` | `bash deon/run_ladder.sh 6` (Ollama) | not timed | no, LLM sampling |
| Sect. 7 RQ2: AgentDojo 50.0/11.8, 0% at 37.5% | Sect. 9.2, Table 4, App. C, Table 9 | `agentdojo_results.json` | `bash deon/run_agentdojo.sh` (AgentDojo, Ollama) | not timed | no, LLM sampling |
| Fig. 3 (a, b, c) | Fig. 4 | `core_results.json` | `cd deon && python3 make_camera_figures.py` | 4 s | yes |
| (not in the camera-ready) | Figs. 3, 5 | `core_results.json` | `cd deon && python3 make_real_figures.py` | 1 s | yes |
| (not in the camera-ready) | Figs. 6, 7 | `stress_results.json` | `cd deon && python3 make_stress_figures.py` | 1 s | yes |
| Table 1 | Tables 3, 4, 5, 9 | result files | `python3 scripts/make-tables.py` | 1 s | reads files only |

The figure scripts write into `deon/figures/` unless `POLICYSHIELD_FIGURES` points
elsewhere. Result scripts write into `deon/results/` unless `POLICYSHIELD_RESULTS` points
elsewhere. Figs. 1 and 2 of the camera-ready are diagrams drawn in LaTeX and contain no
data. `deon/figures/fig_guard.pdf` and `fig_attack.pdf` are written by
`make_real_figures.py` and are not used by either PDF. `deon/figures/fig_calib.pdf` and
`fig_recover.pdf` are kept from the submitted version, are not used by either PDF, and
have no generator in this release.

`CLAIM_MATRIX.md` lists every number claim by claim with its file and key.

## Runs that need external resources

Two experiments call language models. Their outputs are stochastic and are committed as
frozen snapshots. `check-claims.py` compares those snapshots with the papers. A rerun
gives close but not identical rates.

**Proposer ladder (camera-ready Table 1).** Needs a local Ollama server
(`ollama serve`, port 11434) with `gemma2:2b`, `llama3.2:3b`, `qwen2.5-coder:7b`,
`qwen2.5-coder:32b`, `command-r:35b` and `mixtral:8x7b` pulled. The two largest models
need about 20 to 26 GB of memory each at Ollama's default quantisation.

```bash
cd deon && bash run_ladder.sh 6     # writes results/llm_summary_<model>.json
```

Run it with `POLICYSHIELD_RESULTS` set to another folder to keep the committed
summaries. `RUN_OPTIONAL_LLM=1 bash scripts/run-full.sh` does this inside the output
folder. The committed files record the model names but not the Ollama version or the
model digests. Only the per-model summaries and the console log were kept. The raw
plans were not stored.

**AgentDojo banking suite (camera-ready Sect. 7 RQ2, extended Table 4).** Needs the
packages in `deon/requirements-agentdojo.txt` in a separate environment, a local Ollama
server with `qwen2.5:7b`, and a first-run download of four Hugging Face detector models
(ProtectAI DeBERTa, deepset DeBERTa, TestSavant, and a public re-upload of Meta
Prompt-Guard-86M, see `deon/agentdojo_deon.py`). The environment present when this
release was packaged had agentdojo 0.1.35, openai 2.44.0, torch 2.12.1 and transformers
5.13.0 under Python 3.14.6. The result file itself does not record package versions.

```bash
python3 -m venv ../deon-venv-ad && . ../deon-venv-ad/bin/activate
python3 -m pip install -r deon/requirements-agentdojo.txt
cd deon && PYTHON=python3 bash run_agentdojo.sh      # writes results/agentdojo_results.json
```

A full pass runs 9 defences on 16 benign tasks and 76 task-injection pairs with up to 5
model calls per episode. It was not timed for this release. Per-episode logs go to
`/tmp/ad_full_runs`.

## Corrections made for this release

A consistency check of this release found eleven places where the paper text and the
artifact disagreed. The papers in `paper/` and the committed results were corrected, and all 239
checked claims now pass. `CLAIM_MATRIX.md` lists each correction (C1 to C11) with the
old and the new text. In short:

- Camera-ready Sect. 7 RQ3 now says the naturalised payload evades the ensemble at 1.00.
  The structural detector alone admits only 0.068 of these leaks, at 0.09 utility
  (extended Table 5).
- The per-action cost is the least-squares slope of the per-trace timings in
  `e5_scalability` and is printed as 0.75 us (camera-ready Sect. 7, extended Sects. 9.5
  and 11.1).
- The prompt-level AgentDojo defences are printed as 9.2 to 10.5%.
- The AgentDojo guard refuses a call through a prohibition, which is a Block of Def. 2.
  The papers now say that Deon blocks calls in 2 of the 16 benign tasks. The message
  that `deon/agentdojo_deon.py` returns to the proposer is still labelled ABSTAIN and
  routes the call to human confirmation.
- `stress_results.json` and extended Fig. 6 were regenerated with the released code. The
  earlier file came from a version of `core.py` that admitted scores below the smallest
  calibration violation when the PAC rank was 0, and that admitted every score in a
  Mondrian group without calibration violations. The released rule abstains on every
  score in both cases (camera-ready Sect. 5). The regenerated file changes the n_v = 20
  row of extended Table 6 (PAC pass-through and utility 0.000) and the Mondrian utility
  under drift (0.25). The tie-break study now runs the executable augmented-score rule
  and gives a mean of 0.0997 (printed 0.100). The recalibration time is a new
  measurement (0.037 ms, printed 0.04 ms).
- Extended version only: the fixed cutoff under miscalibration swings 0.005 to 0.185
  (40x), the Fig. 6 caption and Sect. 9.5 describe the abstention-recovery study as a
  Monte Carlo model with fixed branch probabilities, Sect. 9.5 no longer says the
  hardware is recorded, and Sect. 8.2 gives the binomial standard deviation of n_v (29)
  in place of an untraceable range.

Two notes remain. The RQ3 content-egress experiment (`e6`) calibrates and admits with
the deterministic rule s <= tau on a detector whose scores tie (extended App. B). The
ensemble study (`e7`) adds an independent uniform perturbation of size 1e-6 to
calibration and test scores, which approximates the augmented-score tie-break of
camera-ready Sect. 5.

## Known limitations

- The proposer ladder and the AgentDojo run call language models without a seed. Their
  committed results are single frozen runs. The raw plans, the Ollama version, the model
  digests, the AgentDojo episode logs, the guard's refusal log and the AgentDojo package
  versions were not recorded.
- Timing values (`e5_scalability`, `r5_drift_rolling/calibration_ms_per_recal`) depend
  on the host and its load. The host of the committed `e5_scalability` run was not
  recorded. The committed `calibration_ms_per_recal` was measured on the machine in
  `REPRODUCIBILITY.md`.
- `deon/figures/fig_calib.pdf` and `fig_recover.pdf` have no generator in this release
  and are not used by either PDF.
- Linux was not tested.

## Verifying outputs

`scripts/verify.sh` and `scripts/run-smoke.sh` end with `RESULT: PASS`.
`scripts/check-claims.py` prints one line per claim with the paper value, the artifact
value, and the file and key. `EXPECTED_RESULTS.md` gives the exact summary lines.

## License and citation

Code under Apache-2.0, documentation and data under CC BY 4.0. See `LICENSE`,
`LICENSES/` and `THIRD_PARTY_NOTICES.md`. The PDFs keep their publication terms. Cite
the ICSOC 2026 paper (see `CITATION.cff`).
