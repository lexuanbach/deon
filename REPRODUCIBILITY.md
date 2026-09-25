# Reproducibility

This file gives the tested environment, the exact commands with measured runtimes, the
seeds, and the runs that need external resources. `README.md` maps every paper item to a
command and `CLAIM_MATRIX.md` lists every number.

## Tested environment

| Item | Value |
|---|---|
| Operating system | macOS 26.5 (build 25F84), arm64 |
| Hardware | Apple M5 Max, 64 GB RAM. One CPU core is used. |
| Python | 3.14.6 and 3.13.5 (both pass every step below) |
| Packages | `requirements-lock.txt`: numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2 and their dependencies |
| Optional tools | `pdfinfo` from poppler, used by `verify.sh` for the page count |

Linux was not tested. The code uses only the Python standard library, NumPy, SciPy and
Matplotlib, and the shell scripts use bash.

## Steps and measured runtimes

Run from the artifact root after the install of `README.md`. Wall-clock times were
measured on the machine above in a fresh copy of the artifact.

| Step | Command | Runtime | Writes |
|---|---|---|---|
| Install | `python3 -m venv ../deon-venv && . ../deon-venv/bin/activate && python3 -m pip install -r requirements-lock.txt` | 8 s with a warm pip cache | `../deon-venv` |
| Verify | `bash scripts/verify.sh` | 1.3 s (15 to 21 s on the first call after the install) | nothing |
| Smoke | `bash scripts/run-smoke.sh` | 21 s | a temporary folder, removed at the end |
| Full model-free rerun | `bash scripts/run-full.sh` | 35 s (a few seconds more on the first Matplotlib run, which builds its font cache) | `$DEON_OUT` or `${TMPDIR:-/tmp}/deon-full-run` |
| Claims only | `python3 scripts/check-claims.py` | 1.2 s | nothing |
| Tables only | `python3 scripts/make-tables.py` | under 1 s | nothing |
| Ladder (optional) | `cd deon && bash run_ladder.sh 6` | not timed, needs Ollama | `deon/results/llm_summary_*.json` |
| AgentDojo (optional) | `cd deon && PYTHON=python3 bash run_agentdojo.sh` | not timed, needs Ollama and AgentDojo | `deon/results/agentdojo_results.json` |

Per-experiment times inside the full rerun: `e1` under 1 s, `e2` 2 s, `e3` 1 s, `e4` under
1 s, `e5` 5 s, `e6` 3 s, `e7` 7 s, `e8` under 1 s, and 8 s for all eight studies of
`experiments_stress.py`.

To regenerate a single core experiment, run
`cd deon && POLICYSHIELD_RESULTS=/some/folder python3 _run_core_staged.py e7_ensemble_egress`
(the key names are those of `core_results.json`).

## What is deterministic

- `experiments_core.py`: every experiment draws from a fixed NumPy seed (`e1` seed 0,
  `e2` seed 1, `e3` seed 2, `e4` seed 3, `e5` seed 4, and base seeds 6, 7 and 8 plus the
  seed index for `e6`, `e7` and `e8`). With the tested packages the rerun reproduces the
  committed `core_results.json` bit for bit, apart from the `e5_scalability` timings.
  `scripts/run-smoke.sh` and `scripts/run-full.sh` check this with
  `scripts/compare-results.py`.
- `experiments_stress.py`: every study uses base seed 101, 201, ..., 801 plus the trial
  index. The committed `stress_results.json` was regenerated with the released code
  for this release (`README.md`, "Corrections made for this release"). A rerun
  reproduces it bit for bit, apart from the `calibration_ms_per_recal` timing.
- `bench.build_monitor_suite` with seed 0 yields the class counts 84/65/81/83/70/67 of
  camera-ready Sect. 7. `check-claims.py` recomputes them.
- Timing (`e5_scalability`, `r5_drift_rolling/calibration_ms_per_recal`) depends on the
  host and on its load. The committed `e5_scalability` values do not record the host
  they were measured on. The committed `calibration_ms_per_recal` (0.037 ms) was
  measured on the machine above. A rerun of `e5_scalability` on that machine gave a slope
  of 0.61 us per action and R^2 = 0.985, against 0.755 us and R^2 = 0.987 in the
  committed file. On a busy machine the R^2 of a rerun can drop to about 0.84.
  `check-claims.py` reports timing values from a rerun as INFO.
- The proposer ladder samples at temperature 0.7 with no seed (`deon/llm.py`). The
  AgentDojo run uses the default temperature of AgentDojo's `OpenAILLM` (0.0 in
  agentdojo 0.1.35) through Ollama's OpenAI-compatible endpoint, also with no seed. The
  code and the papers treat both runs as non-deterministic, and neither was repeated.

## Runs that need external resources

| Run | Needs | Committed stand-in | Checked by |
|---|---|---|---|
| Proposer ladder, camera-ready Table 1 | Ollama server with the six models of `deon/run_ladder.sh` | `deon/results/llm_summary_*.json` (one per model) and `deon/results/ladder.log` | `check-claims.py` (every cell of Table 1) |
| AgentDojo banking suite, camera-ready Sect. 7 RQ2, extended Table 4 and Table 9 | `deon/requirements-agentdojo.txt`, Ollama with `qwen2.5:7b`, four Hugging Face detector models | `deon/results/agentdojo_results.json` with per-task and per-pair outcomes | `deon/check_results.py` and `check-claims.py` |

What the committed files do not contain: the raw plans proposed by each model in the
ladder, the Ollama version and model digests, the AgentDojo episode logs (written to
`/tmp/ad_full_runs` at run time), the per-call refusal log of the Deon guard in AgentDojo,
and the package versions of the AgentDojo run. `README.md` gives the setup commands.

To rerun either one without touching the committed files, point `POLICYSHIELD_RESULTS`
to another folder, or use `RUN_OPTIONAL_LLM=1 bash scripts/run-full.sh` for the ladder.
Then compare the new summaries with the committed ones by hand or with
`python3 scripts/check-claims.py --results <folder>`. Expect close but not identical
rates. The guarded attack success of the ladder and of Deon on AgentDojo is 0 by
construction whenever the catalogue labels are correct (Cor. 1(a)).

## Fresh-copy test of this release

Done on the machine above in an empty folder, starting from the archive
`Deon-ICSOC2026.zip`, with no network access needed after the pip install:

| Step | Command | Outcome | Wall time |
|---|---|---|---|
| 1 | `shasum -a 256 -c Deon-ICSOC2026.zip.sha256 && unzip -q Deon-ICSOC2026.zip && cd Deon-ICSOC2026` | OK | under 1 s |
| 2 | `python3 -m venv ../deon-venv && . ../deon-venv/bin/activate && python3 -m pip install -r requirements-lock.txt` | installed | 8 s |
| 3 | `bash scripts/verify.sh` | PASS, 239 of 239 claims | 15 to 21 s (first call) |
| 4 | `bash scripts/run-smoke.sh` | PASS, 0 differences in the rerun core results | 21 s |
| 5 | `bash scripts/verify.sh` | PASS, the smoke run left no files behind | 1.3 s |
| 6 | `bash scripts/run-full.sh` | PASS, rerun results equal the committed ones apart from timing | 35 s |
| 7 | `python3 scripts/check-claims.py` and `python3 scripts/make-tables.py` | PASS, tables printed | 1.2 s |
| 8 | `bash scripts/verify.sh` | PASS | 1.3 s |

The same eight steps passed with Python 3.13.5.
