# Claim matrix

Every quantitative claim of the camera-ready paper (`paper/camera-ready.pdf`) and the
headline claims and tables of the extended version (`paper/extended.pdf`), with the file
and key that back each one. Section, table and figure numbers follow these current PDFs.
In the camera-ready, Table 1 is the proposer ladder and Fig. 3 is the three-panel results
figure. The extended version numbers the same ladder Table 3 and the same figure Fig. 4.

`python3 scripts/check-claims.py` checks all 239 rows below and prints the same table
with `--markdown`. A row passes when the artifact value agrees with the printed value up
to the paper's rounding.

| Status on the committed results | Camera-ready | Extended | Total |
|---|---|---|---|
| PASS | 117 | 122 | 239 |
| FAIL | 0 | 0 | 0 |
| Total | 117 | 122 | 239 |

## Where each source comes from

| Source prefix in the tables | File | Regenerate with | Deterministic |
|---|---|---|---|
| `core ...` | `deon/results/core_results.json` | `bash scripts/run-full.sh` (step 2, `experiments_core.py`) | yes, apart from `e5_scalability` timing |
| `stress ...` | `deon/results/stress_results.json` | `bash scripts/run-full.sh` (step 3, `experiments_stress.py`) | yes, apart from `calibration_ms_per_recal` timing |
| `llm_summary_*.json ...` | `deon/results/llm_summary_<model>.json` | `cd deon && bash run_ladder.sh 6` (Ollama) | no |
| `agentdojo ...` | `deon/results/agentdojo_results.json` | `cd deon && bash run_agentdojo.sh` (AgentDojo and Ollama) | no |
| `... (recomputed)` | none. `check-claims.py` recomputes the value from the seeded generator | `python3 scripts/check-claims.py` | yes |
| `experiments_core.eN default ...`, `catalog ...`, `llm.propose ...`, `sqrt(...)` | a parameter in the code, or a value derived from parameters | read the code | yes |

Figures: camera-ready Fig. 3 (extended Fig. 4) comes from
`deon/make_camera_figures.py`, extended Figs. 3 and 5 from `deon/make_real_figures.py`,
extended Figs. 6 and 7 from `deon/make_stress_figures.py`. Camera-ready Figs. 1 and 2
(extended Figs. 1 and 2) are LaTeX diagrams without data. Tables: camera-ready Table 1
and extended Tables 3, 4, 5 and 9 are printed by `python3 scripts/make-tables.py`.
Extended Tables 1, 2 and 8 hold no measured values beyond those checked below.

## Corrections applied in this release

A consistency check between the papers and this artifact found the mismatches below.
All are resolved. The paper
sources were edited and both PDFs rebuilt (camera-ready still 10 pages, extended still
45 pages), and `stress_results.json` and extended Fig. 6 were regenerated with the
released code (C7).

| ID | Paper, location | Old text | New text | Evidence |
|---|---|---|---|---|
| C1 | camera-ready Sect. 7 RQ3 | a naturalised payload defeats all three at 1.00 | a naturalised payload evades the ensemble at 1.00 | core `e7_ensemble_egress/adaptive_evade_all`: lexical 1.00, numeric 1.00, ensemble 1.00, structural 0.068 at 0.09 utility. The extended Sect. 9.4 already stated this |
| C2 | camera-ready Sect. 7, extended Sects. 9.5 and 11.1 | 0.76 us per action | 0.75 us per action | least-squares slope 0.7546 of core `e5_scalability`, which stores us per trace |
| C3 | camera-ready Sect. 7 RQ2, extended Sect. 9.2 | 9 to 10% | 9.2 to 10.5% | agentdojo `repeat_user_prompt` 9.21%, `spotlighting` 10.53% |
| C4 | extended Sect. 9.5, Table 6 | fixed cutoff 0.014 to 0.185, 13x | 0.005 to 0.185, 40x | stress `r4_miscalibration/grid` |
| C5 | extended Table 6 | small-n_v utility 0.998 to 1.000 | 0.000 at k'=0, else 0.996 to 1.000 | stress `r2_small_nv` (with C7) |
| C6 | extended Fig. 6 caption | (b) Small-n_v PAC keeps sound-fraction >= 1 - delta | (b) Small-n_v PAC pass-through and sound fraction | stress `r2_small_nv`: 0.91 to 0.96 for n_v >= 80 |
| C7 | extended Sect. 9.5, Sect. 9.6, Table 6, Fig. 6 | Mondrian utility under drift 0.72, n_v = 20 PAC pass-through 0.048, "refusing everything above the minimum calibration score", 0.06 ms per recalibration | 0.25, 0.000, "the guard abstains on every score", 0.04 ms | `stress_results.json` regenerated with the released `core.py` (rank 0 or an empty group abstains on every score) and the executable tie-break (mean 0.0997, printed 0.100). The recalibration time is a new measurement |
| C8 | extended Sect. 9.5, Fig. 6 caption, Sect. 10 | the recovery ladder reported as measured | "In a Monte Carlo model of the safe-fallback ladder ... with fixed branch probabilities", panel (d) marked as a Monte Carlo model | `experiments_stress.r6_abstention_recovery` |
| C9 | camera-ready Sect. 7 RQ2, extended Sect. 9.2 and App. C | abstaining on the 2 of 16 benign tasks | blocking calls in the 2 of 16 benign tasks | `deon/agentdojo_deon.py` refuses through a prohibition (a Block of Def. 2) |
| C10 | extended Sect. 9.5 | Hardware, repetitions, and interval estimates are recorded in the artifact | Repetitions and standard deviations are recorded in the artifact | core `e5_scalability` stores 5 repetitions and an sd per length |
| C11 | extended Sect. 8.2 | n_v 1177 to 1253 over 20 independent draws | n_v about 1200 (binomial, standard deviation 29) | n_cal = 4000, base rate 0.30 |

Notes without a numeric mismatch:
- Camera-ready Sect. 5 prescribes the augmented-score tie-break. The RQ3 content-egress
  run (`e6`) uses the deterministic rule s <= tau on tied detector scores (extended
  App. B says so, the camera-ready does not). The ensemble run (`e7`) adds a uniform
  perturbation of size 1e-6 to calibration and test scores, which matches the augmented
  ranking except where two distinct scores lie closer than 1e-6.
- The AgentDojo guard labels its refusal message ABSTAIN and routes it to human
  confirmation. The papers call these refusals blocks (C9).
- AgentDojo's `OpenAILLM` uses temperature 0.0 by default. The run is unseeded and was
  done once.

## Claims that are not numbers

| Claim | Status | Evidence |
|---|---|---|
| DPA transition order, refusal leaves q unchanged, obligation discharge before registration, self-trigger needs a later occurrence (camera-ready Def. 2, Fig. 1) | Tested | `deon/test_core.py` (7 tests), `deon/core.py` |
| Rank zero or an empty violation pool abstains on all finite scores (camera-ready Sect. 5) | Tested | `deon/test_core.py`, `core.calibrate_threshold` |
| Augmented-score tie-break (camera-ready Sect. 5) | Implemented | `core.calibrate_randomized_threshold`, `core.randomized_admit`, used by `experiments_stress.r3_ties` |
| Linear-time monitor (camera-ready Sect. 2) | Measured | `core e5_scalability`, R^2 = 0.987 |
| Eventual obligation discharge | Not claimed | the monitor reports pending obligations at the end of a trace and cannot force a future action |
| PAC guarantee outside the exchangeability and independence assumptions | Not claimed | limitations in both PDFs |
| Security against a scorer the attacker can fully evade | Not claimed | the evade-all failure is measured (C1, extended Table 5) |
| AgentDojo: the 2 tasks where Deon blocks calls take a critical value from an untrusted file | Partly traceable | the per-task outcomes are in `agentdojo_results.json` (user_task_0 and user_task_4). The guard's refusal log was not saved |
| Rego/OPA mapping of the deny fragment (camera-ready Sect. 5, extended App. D) | Not executed | the listing is written by hand. No OPA run is part of the artifact |

## Known limitations

- The ladder and AgentDojo results are single unseeded LLM runs. Their raw plans, the
  Ollama version, the model digests, the episode logs, the refusal log and the AgentDojo
  package versions were not recorded.
- The host of the committed `e5_scalability` timings was not recorded. Timing values of
  a rerun depend on the host and its load.

## Camera-ready claims

| # | Location | Claim | Paper | Artifact | Source | Status |
|---|---|---|---|---|---|---|
| CR-1 | Abstract, Sect. 7 RQ1 | automaton agrees with ground truth (%) | 100 | 100 | `core e1_monitor_soundness/accuracy` | PASS |
| CR-2 | Abstract, Sect. 7 | monitor-suite traces | 900 | 900 | `core e1_monitor_soundness/n` | PASS |
| CR-3 | Abstract, Sect. 7 | violation classes | 6 | 6 | `core e1_monitor_soundness/per_class_recall` | PASS |
| CR-4 | Abstract, Sect. 7 RQ3 | leaks admitted, exchangeable (%) | 8.9 | 8.86 | `core e6_content_egress/exchangeable/policyshield/mean` | PASS |
| CR-5 | Abstract, Sect. 7 RQ3 | target alpha (%) | 10 | 10 | `core e6_content_egress/alpha` | PASS |
| CR-6 | Abstract, Sect. 7 RQ3 | leaks admitted, adaptive obfuscation (%) | 32.8 | 32.81 | `core e6_content_egress/adaptive/policyshield/mean` | PASS |
| CR-7 | Abstract, Sect. 1, Sect. 7 RQ2 | proposer models | 6 | 6 | `llm_summary_*.json (count)` | PASS |
| CR-8 | Abstract, Sect. 1, Sect. 7 RQ2 | unguarded ASR, lowest (%) | 87 | 86.7 | `llm_summary_*.json asr_unguarded (min)` | PASS |
| CR-9 | Abstract, Sect. 1, Sect. 7 RQ2 | unguarded ASR, highest (%) | 100 | 100 | `llm_summary_*.json asr_unguarded (max)` | PASS |
| CR-10 | Abstract, Sect. 7 RQ2 | guarded ASR, all models (%) | 0 | 0 | `llm_summary_*.json asr_policyshield (max)` | PASS |
| CR-11 | Abstract | microsecond-scale overhead: every trace of 2 to 12 actions under 10 us | yes | yes | `core e5_scalability/*/us_mean (max)` | PASS |
| CR-12 | Sect. 7 setup | compliant traces | 450 | 450 | `core e1_monitor_soundness/n_admissible` | PASS |
| CR-13 | Sect. 7 setup | traces with one planted violation | 450 | 450 | `core e1_monitor_soundness/n_violating` | PASS |
| CR-14 | Sect. 7 setup | traces of class prohibited at the released seed | 84 | 84 | `bench.build_monitor_suite(seed 0, 900) (recomputed)` | PASS |
| CR-15 | Sect. 7 setup | traces of class sequencing at the released seed | 65 | 65 | `bench.build_monitor_suite(seed 0, 900) (recomputed)` | PASS |
| CR-16 | Sect. 7 setup | traces of class flow at the released seed | 81 | 81 | `bench.build_monitor_suite(seed 0, 900) (recomputed)` | PASS |
| CR-17 | Sect. 7 setup | traces of class quota at the released seed | 83 | 83 | `bench.build_monitor_suite(seed 0, 900) (recomputed)` | PASS |
| CR-18 | Sect. 7 setup | traces of class obligation at the released seed | 70 | 70 | `bench.build_monitor_suite(seed 0, 900) (recomputed)` | PASS |
| CR-19 | Sect. 7 setup | traces of class laundering at the released seed | 67 | 67 | `bench.build_monitor_suite(seed 0, 900) (recomputed)` | PASS |
| CR-20 | Sect. 7 setup | calibration draws n | 4000 | 4000 | `experiments_core.e2 default n_cal` | PASS |
| CR-21 | Sect. 7 setup | calibration violations n_v (approx.) | 1200 | 1200 | `n_cal x bench.build_risk_pool base_rate (expected value)` | PASS |
| CR-22 | Sect. 7 setup | evaluation draws n | 20000 | 20000 | `experiments_core.e2 default n_eval` | PASS |
| CR-23 | Sect. 7 setup | trials per alpha | 300 | 300 | `core e2_conformal_coverage/trials` | PASS |
| CR-24 | Sect. 7 setup | mixed stream: actions per trial | 4000 | 4000 | `experiments_core.e4 default n` | PASS |
| CR-25 | Sect. 7 setup | mixed stream: explicit share (%) | 35 | 35 | `core e4_attack_synth/frac_explicit` | PASS |
| CR-26 | Sect. 7 setup | ladder catalogue operations | 11 | 11 | `catalog.CATALOG` | PASS |
| CR-27 | Sect. 7 setup | operations described to the proposer | 8 | 8 | `catalog.catalogue_desc()` | PASS |
| CR-28 | Sect. 7 setup, Sect. 7 RQ2 | AgentDojo non-degenerate pairs | 76 | 76 | `agentdojo defenses/deon/n_attack_combos` | PASS |
| CR-29 | Sect. 7 setup | fixed-threshold cutoff | 0.5 | 0.5 | `core e3_risk_utility/fixed_tau` | PASS |
| CR-30 | Sect. 7 setup, Table 1 | benign runs per model | 30 | 30 | `llm_summary_*.json n_benign` | PASS |
| CR-31 | Sect. 7 setup, Table 1 | attack runs per model | 30 | 30 | `llm_summary_*.json n_attack` | PASS |
| CR-32 | Sect. 7 setup | repetitions per task | 6 | 6 | `llm_summary_*.json reps` | PASS |
| CR-33 | Sect. 7 setup | benign and attack tasks | 5 | 5 | `catalog tasks` | PASS |
| CR-34 | Sect. 7 setup | proposer temperature | 0.7 | 0.7 | `llm.propose default temperature` | PASS |
| CR-35 | Sect. 7 RQ1 | recall, lowest class (%) | 100 | 100 | `core e1_monitor_soundness/per_class_recall (min)` | PASS |
| CR-36 | Sect. 7 RQ1 | marginal mean pass-through, lowest alpha | 0.020 | 0.0196 | `core e2_conformal_coverage/curve/*/passthrough (min)` | PASS |
| CR-37 | Sect. 7 RQ1 | marginal mean pass-through, highest alpha | 0.299 | 0.2988 | `core e2_conformal_coverage/curve/*/passthrough (max)` | PASS |
| CR-38 | Sect. 7 RQ1 | marginal utility, lowest (%) | 100 | 99.91 | `core e2_conformal_coverage/curve/*/utility (min)` | PASS |
| CR-39 | Sect. 7 RQ1, Fig. 3a | marginal draws holding target, lowest (%) | 51 | 50.67 | `core e2_conformal_coverage/curve/*/sound_frac_marginal (min)` | PASS |
| CR-40 | Sect. 7 RQ1, Fig. 3a | marginal draws holding target, highest (%) | 56 | 55.67 | `core e2_conformal_coverage/curve/*/sound_frac_marginal (max)` | PASS |
| CR-41 | Sect. 7 RQ1, Fig. 3a | exact-PAC draws holding target, lowest (%) | 93 | 92.67 | `core e2_conformal_coverage/curve/*/sound_frac_pac (min)` | PASS |
| CR-42 | Sect. 7 RQ1, Fig. 3a | exact-PAC draws holding target, highest (%) | 96 | 96.33 | `core e2_conformal_coverage/curve/*/sound_frac_pac (max)` | PASS |
| CR-43 | Sect. 7 RQ1, Fig. 3a | 1 - delta | 0.95 | 0.95 | `core e2_conformal_coverage/delta` | PASS |
| CR-44 | Sect. 7 RQ1 | Deon pass-through across detector quality, lowest | 0.098 | 0.0984 | `core e3_risk_utility/robustness/*/conformal_passthrough (min)` | PASS |
| CR-45 | Sect. 7 RQ1 | Deon pass-through across detector quality, highest | 0.100 | 0.1002 | `core e3_risk_utility/robustness/*/conformal_passthrough (max)` | PASS |
| CR-46 | Sect. 7 RQ1 | Deon utility at the weakest detector | 0.76 | 0.7625 | `core e3_risk_utility/robustness/0/conformal_utility` | PASS |
| CR-47 | Sect. 7 RQ1 | Deon utility at the strongest detector | 1.00 | 1 | `core e3_risk_utility/robustness/-1/conformal_utility` | PASS |
| CR-48 | Sect. 7 RQ1 | fixed cutoff leak at the weakest detector | 0.158 | 0.1581 | `core e3_risk_utility/robustness/0/fixed_passthrough` | PASS |
| CR-49 | Table 1 | gemma2:2b benign_success_unguarded | 100 | 100 | `llm_summary_gemma2_2b.json benign_success_unguarded` | PASS |
| CR-50 | Table 1 | gemma2:2b benign_success_policyshield | 100 | 100 | `llm_summary_gemma2_2b.json benign_success_policyshield` | PASS |
| CR-51 | Table 1 | gemma2:2b asr_unguarded | 100 | 100 | `llm_summary_gemma2_2b.json asr_unguarded` | PASS |
| CR-52 | Table 1 | gemma2:2b asr_policyshield | 0 | 0 | `llm_summary_gemma2_2b.json asr_policyshield` | PASS |
| CR-53 | Table 1 | llama3.2:3b benign_success_unguarded | 97 | 96.7 | `llm_summary_llama3.2_3b.json benign_success_unguarded` | PASS |
| CR-54 | Table 1 | llama3.2:3b benign_success_policyshield | 100 | 100 | `llm_summary_llama3.2_3b.json benign_success_policyshield` | PASS |
| CR-55 | Table 1 | llama3.2:3b asr_unguarded | 100 | 100 | `llm_summary_llama3.2_3b.json asr_unguarded` | PASS |
| CR-56 | Table 1 | llama3.2:3b asr_policyshield | 0 | 0 | `llm_summary_llama3.2_3b.json asr_policyshield` | PASS |
| CR-57 | Table 1 | qwen2.5-coder:7b benign_success_unguarded | 100 | 100 | `llm_summary_qwen2.5-coder_7b.json benign_success_unguarded` | PASS |
| CR-58 | Table 1 | qwen2.5-coder:7b benign_success_policyshield | 100 | 100 | `llm_summary_qwen2.5-coder_7b.json benign_success_policyshield` | PASS |
| CR-59 | Table 1 | qwen2.5-coder:7b asr_unguarded | 87 | 86.7 | `llm_summary_qwen2.5-coder_7b.json asr_unguarded` | PASS |
| CR-60 | Table 1 | qwen2.5-coder:7b asr_policyshield | 0 | 0 | `llm_summary_qwen2.5-coder_7b.json asr_policyshield` | PASS |
| CR-61 | Table 1 | qwen2.5-coder:32b benign_success_unguarded | 100 | 100 | `llm_summary_qwen2.5-coder_32b.json benign_success_unguarded` | PASS |
| CR-62 | Table 1 | qwen2.5-coder:32b benign_success_policyshield | 100 | 100 | `llm_summary_qwen2.5-coder_32b.json benign_success_policyshield` | PASS |
| CR-63 | Table 1 | qwen2.5-coder:32b asr_unguarded | 100 | 100 | `llm_summary_qwen2.5-coder_32b.json asr_unguarded` | PASS |
| CR-64 | Table 1 | qwen2.5-coder:32b asr_policyshield | 0 | 0 | `llm_summary_qwen2.5-coder_32b.json asr_policyshield` | PASS |
| CR-65 | Table 1 | command-r:35b benign_success_unguarded | 100 | 100 | `llm_summary_command-r_35b.json benign_success_unguarded` | PASS |
| CR-66 | Table 1 | command-r:35b benign_success_policyshield | 100 | 100 | `llm_summary_command-r_35b.json benign_success_policyshield` | PASS |
| CR-67 | Table 1 | command-r:35b asr_unguarded | 100 | 100 | `llm_summary_command-r_35b.json asr_unguarded` | PASS |
| CR-68 | Table 1 | command-r:35b asr_policyshield | 0 | 0 | `llm_summary_command-r_35b.json asr_policyshield` | PASS |
| CR-69 | Table 1 | mixtral:8x7b benign_success_unguarded | 100 | 100 | `llm_summary_mixtral_8x7b.json benign_success_unguarded` | PASS |
| CR-70 | Table 1 | mixtral:8x7b benign_success_policyshield | 100 | 100 | `llm_summary_mixtral_8x7b.json benign_success_policyshield` | PASS |
| CR-71 | Table 1 | mixtral:8x7b asr_unguarded | 100 | 100 | `llm_summary_mixtral_8x7b.json asr_unguarded` | PASS |
| CR-72 | Table 1 | mixtral:8x7b asr_policyshield | 0 | 0 | `llm_summary_mixtral_8x7b.json asr_policyshield` | PASS |
| CR-73 | Sect. 7 RQ2 | llama3.2:3b benign success unguarded (the 97) | 97 | 96.7 | `llm_summary_llama3.2_3b.json benign_success_unguarded` | PASS |
| CR-74 | Sect. 7 RQ2 | mixed stream, unguarded executed violations (%) | 100 | 100 | `core e4_attack_synth/unguarded_asr` | PASS |
| CR-75 | Sect. 7 RQ2 | mixed stream, Deon (%) | 3.6 | 3.55 | `core e4_attack_synth/policyshield_asr` | PASS |
| CR-76 | Sect. 7 RQ2 | mixed stream, DPA only (%) | 35.7 | 35.69 | `core e4_attack_synth/dpa_only_asr` | PASS |
| CR-77 | Sect. 7 RQ2 | AgentDojo undefended utility (%) | 50.0 | 50 | `agentdojo defenses/none/benign_utility` | PASS |
| CR-78 | Sect. 7 RQ2 | AgentDojo undefended ASR (%) | 11.8 | 11.8421 | `agentdojo defenses/none/asr_under_injection` | PASS |
| CR-79 | Sect. 7 RQ2 | prompt-level defences, lower end (repeat-prompt) ASR (%) | 9.2 | 9.2105 | `agentdojo defenses/repeat_user_prompt/asr_under_injection` | PASS |
| CR-80 | Sect. 7 RQ2 | prompt-level defences, upper end (spotlighting) ASR (%) | 10.5 | 10.5263 | `agentdojo defenses/spotlighting/asr_under_injection` | PASS |
| CR-81 | Sect. 7 RQ2 | deepset detector ASR (%) | 0 | 0 | `agentdojo defenses/deepset_detector/asr_under_injection` | PASS |
| CR-82 | Sect. 7 RQ2 | deepset detector utility (%) | 31.2 | 31.25 | `agentdojo defenses/deepset_detector/benign_utility` | PASS |
| CR-83 | Sect. 7 RQ2 | tool-filter ASR (%) | 0 | 0 | `agentdojo defenses/tool_filter/asr_under_injection` | PASS |
| CR-84 | Sect. 7 RQ2 | tool-filter utility (%) | 25.0 | 25 | `agentdojo defenses/tool_filter/benign_utility` | PASS |
| CR-85 | Sect. 7 RQ2 | Deon ASR on AgentDojo (%) | 0 | 0 | `agentdojo defenses/deon/asr_under_injection` | PASS |
| CR-86 | Sect. 7 RQ2 | Deon utility on AgentDojo (%) | 37.5 | 37.5 | `agentdojo defenses/deon/benign_utility` | PASS |
| CR-87 | Sect. 7 RQ2 | benign tasks Deon loses relative to undefended | 2 | 2 | `agentdojo defenses/{none,deon}/utility_per_task` | PASS |
| CR-88 | Sect. 7 RQ2 | benign AgentDojo tasks | 16 | 16 | `agentdojo defenses/deon/n_benign` | PASS |
| CR-89 | Sect. 7 RQ3, Fig. 3b | DPA-only pass-through, exchangeable | 1.00 | 1 | `core e6_content_egress/exchangeable/dpa_only/mean` | PASS |
| CR-90 | Fig. 3b | DPA-only pass-through, adaptive | 1.00 | 1 | `core e6_content_egress/adaptive/dpa_only/mean` | PASS |
| CR-91 | Sect. 7 RQ3 | seeds | 30 | 30 | `core e6_content_egress/seeds` | PASS |
| CR-92 | Sect. 7 RQ3, Fig. 3b | Deon pass-through, exchangeable | 0.089 | 0.0886 | `core e6_content_egress/exchangeable/policyshield/mean` | PASS |
| CR-93 | Sect. 7 RQ3 | Deon utility, exchangeable (%) | 100 | 100 | `core e6_content_egress/exchangeable/benign_utility/mean` | PASS |
| CR-94 | Sect. 7 RQ3, Fig. 3b | Deon pass-through, adaptive | 0.328 | 0.3281 | `core e6_content_egress/adaptive/policyshield/mean` | PASS |
| CR-95 | Sect. 7 RQ3, Fig. 3c | max-ensemble, obfuscated | 0.097 | 0.0974 | `core e7_ensemble_egress/adaptive_obf/ensemble/mean` | PASS |
| CR-96 | Sect. 7 RQ3, Fig. 3c | lexical alone, obfuscated | 0.835 | 0.8354 | `core e7_ensemble_egress/adaptive_obf/single/lexical/mean` | PASS |
| CR-97 | Fig. 3c | lexical alone, exchangeable | 0.083 | 0.0831 | `core e7_ensemble_egress/exchangeable/single/lexical/mean` | PASS |
| CR-98 | Fig. 3c | max-ensemble, exchangeable | 0.082 | 0.0818 | `core e7_ensemble_egress/exchangeable/ensemble/mean` | PASS |
| CR-99 | Fig. 3c | naturalised payload vs lexical detector | 1.00 | 1 | `core e7_ensemble_egress/adaptive_evade_all/single/lexical/mean` | PASS |
| CR-100 | Sect. 7 RQ3, Fig. 3c | naturalised payload evades the ensemble | 1.00 | 1 | `core e7_ensemble_egress/adaptive_evade_all/ensemble/mean` | PASS |
| CR-101 | Sect. 7 stress tests | Mondrian study: marginal worst group | 0.441 | 0.4407 | `core e8_mondrian_shift/marginal/worst_group/mean` | PASS |
| CR-102 | Sect. 7 stress tests | marginal worst group in units of alpha | 4.4 | 4.407 | `core e8_mondrian_shift (worst_group / alpha)` | PASS |
| CR-103 | Sect. 7 stress tests | Mondrian worst group | 0.091 | 0.0911 | `core e8_mondrian_shift/mondrian/worst_group/mean` | PASS |
| CR-104 | Sect. 7 stress tests | utility, marginal | 0.95 | 0.954 | `core e8_mondrian_shift/marginal/utility/mean` | PASS |
| CR-105 | Sect. 7 stress tests | utility, Mondrian | 0.71 | 0.712 | `core e8_mondrian_shift/mondrian/utility/mean` | PASS |
| CR-106 | Sect. 7 stress tests | label noise rho=0: PAC pass-through | 0.085 | 0.0846 | `stress r1_label_noise/curve/0/passthrough_pac` | PASS |
| CR-107 | Sect. 7 stress tests | label noise rho=0.3: PAC pass-through | 0.000 | 0 | `stress r1_label_noise/curve/-1/passthrough_pac` | PASS |
| CR-108 | Sect. 7 stress tests | label noise rho=0: utility | 1.00 | 0.9999 | `stress r1_label_noise/curve/0/utility_pac` | PASS |
| CR-109 | Sect. 7 stress tests | label noise rho=0.3: utility | 0.17 | 0.1725 | `stress r1_label_noise/curve/-1/utility_pac` | PASS |
| CR-110 | Sect. 7 stress tests | ties: deterministic <= leaks | 0.343 | 0.3433 | `stress r3_ties/det_admit_le/mean` | PASS |
| CR-111 | Sect. 7 stress tests | ties: augmented-score tie-break mean | 0.100 | 0.0997 | `stress r3_ties/randomised_tiebreak/mean` | PASS |
| CR-112 | Sect. 7 stress tests | PAC rank at n_v=20 | 0 | 0 | `stress r2_small_nv/curve/0/pac_rank` | PASS |
| CR-113 | Sect. 7 stress tests | automaton cost per action (us, slope over lengths 2 to 12) | 0.75 | 0.7546 | `core e5_scalability (least-squares slope)` | PASS |
| CR-114 | Sect. 7 stress tests | linear-fit R^2 | 0.99 | 0.9871 | `core e5_scalability (R^2)` | PASS |
| CR-115 | Sect. 7 stress tests | shortest and longest trace length | 2-12 | 2-12 | `core e5_scalability/*/length` | PASS |
| CR-116 | Sect. 7 stress tests | traces per timing batch | 20000 | 20000 | `experiments_core.e5 default reps` | PASS |
| CR-117 | Sect. 7 stress tests | timing batches per length | 5 | 5 | `experiments_core.e5_scalability source` | PASS |

## Extended version: headline claims and tables

| # | Location | Claim | Paper | Artifact | Source | Status |
|---|---|---|---|---|---|---|
| EXT-1 | Sect. 8.2 | calibration violations n_v: binomial standard deviation | 29 | 28.9828 | `sqrt(n_cal x 0.30 x 0.70)` | PASS |
| EXT-2 | Sect. 8.2, Table 2 | compliant trace length, max | 8 | 8 | `bench.build_monitor_suite(seed 0) (recomputed)` | PASS |
| EXT-3 | Sect. 8.2 | compliant trace length, mean | 4.8 | 4.8267 | `bench.build_monitor_suite(seed 0) (recomputed)` | PASS |
| EXT-4 | Sect. 8.2, Table 2 | violating trace length, max | 11 | 11 | `bench.build_monitor_suite(seed 0) (recomputed)` | PASS |
| EXT-5 | Sect. 8.2 | violating trace length, mean | 6.1 | 6.1422 | `bench.build_monitor_suite(seed 0) (recomputed)` | PASS |
| EXT-6 | Sect. 8.2, Table 2 | mixed-stream trials | 400 | 400 | `experiments_core.e4 default trials` | PASS |
| EXT-7 | Sect. 8.2, Table 2 | content egress n_cal | 3000 | 3000 | `experiments_core.e6 default n_cal` | PASS |
| EXT-8 | Sect. 8.2, Table 2 | content egress n_eval | 4000 | 4000 | `experiments_core.e6 default n_eval` | PASS |
| EXT-9 | Sect. 8.2 | Mondrian n_cal | 6000 | 6000 | `experiments_core.e8 default n_cal` | PASS |
| EXT-10 | Sect. 8.2 | Mondrian n_eval | 12000 | 12000 | `experiments_core.e8 default n_eval` | PASS |
| EXT-11 | Sect. 9.1 | exact-PAC draws holding target, pooled (%) | 94.5 | 94.48 | `core e2_conformal_coverage/overall_sound_frac_pac` | PASS |
| EXT-12 | Sect. 9.1 | fixed cutoff at the strongest detector | 0.001 | 0.0007 | `core e3_risk_utility/robustness/-1/fixed_passthrough` | PASS |
| EXT-13 | Table 4 | none benign utility (%) | 50.0 | 50 | `agentdojo defenses/none/benign_utility` | PASS |
| EXT-14 | Table 4 | none ASR (%) | 11.8 | 11.8421 | `agentdojo defenses/none/asr_under_injection` | PASS |
| EXT-15 | Table 4 | promptguard benign utility (%) | 37.5 | 37.5 | `agentdojo defenses/promptguard/benign_utility` | PASS |
| EXT-16 | Table 4 | promptguard ASR (%) | 14.5 | 14.4737 | `agentdojo defenses/promptguard/asr_under_injection` | PASS |
| EXT-17 | Table 4 | spotlighting benign utility (%) | 43.8 | 43.75 | `agentdojo defenses/spotlighting/benign_utility` | PASS |
| EXT-18 | Table 4 | spotlighting ASR (%) | 10.5 | 10.5263 | `agentdojo defenses/spotlighting/asr_under_injection` | PASS |
| EXT-19 | Table 4 | repeat_user_prompt benign utility (%) | 43.8 | 43.75 | `agentdojo defenses/repeat_user_prompt/benign_utility` | PASS |
| EXT-20 | Table 4 | repeat_user_prompt ASR (%) | 9.2 | 9.2105 | `agentdojo defenses/repeat_user_prompt/asr_under_injection` | PASS |
| EXT-21 | Table 4 | testsavant_detector benign utility (%) | 43.8 | 43.75 | `agentdojo defenses/testsavant_detector/benign_utility` | PASS |
| EXT-22 | Table 4 | testsavant_detector ASR (%) | 7.9 | 7.8947 | `agentdojo defenses/testsavant_detector/asr_under_injection` | PASS |
| EXT-23 | Table 4 | pi_detector benign utility (%) | 31.2 | 31.25 | `agentdojo defenses/pi_detector/benign_utility` | PASS |
| EXT-24 | Table 4 | pi_detector ASR (%) | 6.6 | 6.5789 | `agentdojo defenses/pi_detector/asr_under_injection` | PASS |
| EXT-25 | Table 4 | deepset_detector benign utility (%) | 31.2 | 31.25 | `agentdojo defenses/deepset_detector/benign_utility` | PASS |
| EXT-26 | Table 4 | deepset_detector ASR (%) | 0.0 | 0 | `agentdojo defenses/deepset_detector/asr_under_injection` | PASS |
| EXT-27 | Table 4 | tool_filter benign utility (%) | 25.0 | 25 | `agentdojo defenses/tool_filter/benign_utility` | PASS |
| EXT-28 | Table 4 | tool_filter ASR (%) | 0.0 | 0 | `agentdojo defenses/tool_filter/asr_under_injection` | PASS |
| EXT-29 | Table 4 | deon benign utility (%) | 37.5 | 37.5 | `agentdojo defenses/deon/benign_utility` | PASS |
| EXT-30 | Table 4 | deon ASR (%) | 0.0 | 0 | `agentdojo defenses/deon/asr_under_injection` | PASS |
| EXT-31 | App. C | excluded degenerate pairs | 4 | 4 | `agentdojo excluded_degenerate_combos` | PASS |
| EXT-32 | App. C, Table 9 | benign tasks Deon loses: user_task_0 and user_task_4 | user_task_0,user_task_4 | user_task_0,user_task_4 | `agentdojo defenses/{none,deon}/utility_per_task` | PASS |
| EXT-33 | Fig. 5a | fixed cutoff, exchangeable | 0.05 | 0.0499 | `core e6_content_egress/exchangeable/fixed_threshold/mean` | PASS |
| EXT-34 | Fig. 5a | fixed cutoff, adaptive | 0.21 | 0.2065 | `core e6_content_egress/adaptive/fixed_threshold/mean` | PASS |
| EXT-35 | Table 5 | lexical exchangeable pass-through | 0.083 | 0.0831 | `core e7 exchangeable/single/lexical/mean` | PASS |
| EXT-36 | Table 5 | lexical utility | 1.00 | 1 | `core e7 exchangeable/single_utility/lexical/mean` | PASS |
| EXT-37 | Table 5 | lexical obfuscated pass-through | 0.835 | 0.8354 | `core e7 adaptive_obf/single/lexical/mean` | PASS |
| EXT-38 | Table 5 | lexical evade-all pass-through | 1.00 | 1 | `core e7 adaptive_evade_all/single/lexical/mean` | PASS |
| EXT-39 | Table 5 | numeric exchangeable pass-through | 0.082 | 0.0815 | `core e7 exchangeable/single/numeric/mean` | PASS |
| EXT-40 | Table 5 | numeric utility | 0.62 | 0.6249 | `core e7 exchangeable/single_utility/numeric/mean` | PASS |
| EXT-41 | Table 5 | numeric obfuscated pass-through | 0.124 | 0.124 | `core e7 adaptive_obf/single/numeric/mean` | PASS |
| EXT-42 | Table 5 | numeric evade-all pass-through | 1.00 | 1 | `core e7 adaptive_evade_all/single/numeric/mean` | PASS |
| EXT-43 | Table 5 | structural exchangeable pass-through | 0.088 | 0.0879 | `core e7 exchangeable/single/structural/mean` | PASS |
| EXT-44 | Table 5 | structural utility | 0.09 | 0.0855 | `core e7 exchangeable/single_utility/structural/mean` | PASS |
| EXT-45 | Table 5 | structural obfuscated pass-through | 0.037 | 0.0374 | `core e7 adaptive_obf/single/structural/mean` | PASS |
| EXT-46 | Table 5 | structural evade-all pass-through | 0.068 | 0.0676 | `core e7 adaptive_evade_all/single/structural/mean` | PASS |
| EXT-47 | Table 5 | ensemble exchangeable pass-through | 0.082 | 0.0818 | `core e7 exchangeable/ensemble/mean` | PASS |
| EXT-48 | Table 5 | ensemble utility | 1.00 | 1 | `core e7 exchangeable/ensemble_utility/mean` | PASS |
| EXT-49 | Table 5 | ensemble obfuscated pass-through | 0.097 | 0.0974 | `core e7 adaptive_obf/ensemble/mean` | PASS |
| EXT-50 | Table 5 | ensemble evade-all pass-through | 1.00 | 1 | `core e7 adaptive_evade_all/ensemble/mean` | PASS |
| EXT-51 | Table 5 caption | largest CI half-width is at most 0.006 | yes | yes | `core e7_ensemble_egress/**/ci` | PASS |
| EXT-52 | Sect. 9.4 | ensemble cut against lexical, obfuscated | 8.6 | 8.577 | `core e7 (lexical / ensemble)` | PASS |
| EXT-53 | Sect. 9.4, Table 7 | Mondrian study: marginal overall | 0.303 | 0.3031 | `core e8 marginal/overall/mean` | PASS |
| EXT-54 | Sect. 9.4 | Mondrian overall | 0.071 | 0.0708 | `core e8 mondrian/overall/mean` | PASS |
| EXT-55 | Sect. 9.5, Fig. 6a | label noise rho=0.05: utility | 0.77 | 0.7664 | `stress r1_label_noise/curve/1/utility_pac` | PASS |
| EXT-56 | Sect. 9.5, Fig. 6a | label noise rho=0.1: utility | 0.41 | 0.4138 | `stress r1_label_noise/curve/2/utility_pac` | PASS |
| EXT-57 | Sect. 9.5 | label noise rho=0.05: PAC pass-through | 0 | 0 | `stress r1_label_noise/curve/1/passthrough_pac` | PASS |
| EXT-58 | Sect. 9.5, Table 6 | PAC rank at n_v=1280 | 111 | 111 | `stress r2_small_nv/curve/-1/pac_rank` | PASS |
| EXT-59 | Sect. 9.5, Table 6 | strict < over-corrects to | 0.040 | 0.04 | `stress r3_ties/det_admit_lt/mean` | PASS |
| EXT-60 | Sect. 9.5 | quantisation levels | 6 | 6 | `stress r3_ties/levels` | PASS |
| EXT-61 | Sect. 9.5, Table 6 | miscalibration: conformal pass-through | 0.084 | 0.0844 | `stress r4_miscalibration/grid (min)` | PASS |
| EXT-62 | Sect. 9.5, Table 6 | miscalibration: fixed cutoff, lowest | 0.005 | 0.0046 | `stress r4_miscalibration/grid/*/fixed_passthrough (min)` | PASS |
| EXT-63 | Sect. 9.5, Table 6 | miscalibration: fixed cutoff, highest | 0.185 | 0.1852 | `stress r4_miscalibration/grid/*/fixed_passthrough (max)` | PASS |
| EXT-64 | Sect. 9.5, Table 6 | miscalibration: fixed-cutoff spread (x) | 40 | 40.2609 | `stress r4_miscalibration (max / min)` | PASS |
| EXT-65 | Sect. 9.5, Table 6 | miscalibration: utility, lowest | 0.88 | 0.8806 | `stress r4_miscalibration (min utility)` | PASS |
| EXT-66 | Sect. 9.5, Table 6 | miscalibration: utility, highest | 0.996 | 0.9956 | `stress r4_miscalibration (max utility)` | PASS |
| EXT-67 | Sect. 9.5 | drift stream batches | 40 | 40 | `stress r5_drift_rolling/T` | PASS |
| EXT-68 | Sect. 9.5 | drift threshold | 0.06 | 0.06 | `stress r5_drift_rolling/drift_thresh` | PASS |
| EXT-69 | Sect. 9.5, Fig. 6c | static utility | 0.89 | 0.8911 | `stress r5 static/utility/mean` | PASS |
| EXT-70 | Sect. 9.5, Fig. 6c | rolling utility | 0.91 | 0.9101 | `stress r5 rolling/utility/mean` | PASS |
| EXT-71 | Sect. 9.5, Fig. 6c | rolling pass-through | 0.08 | 0.0786 | `stress r5 rolling/passthrough/mean` | PASS |
| EXT-72 | Sect. 9.5 | recalibrations | 8.0 | 8.0333 | `stress r5 rolling/recalibrations/mean` | PASS |
| EXT-73 | Sect. 9.5 | time per recalibration (ms) | 0.04 | 0.037 | `stress r5 calibration_ms_per_recal` | PASS |
| EXT-74 | Sect. 9.5, Fig. 6c | Mondrian pass-through | 0.076 | 0.0763 | `stress r5 mondrian/passthrough/mean` | PASS |
| EXT-75 | Sect. 9.5, Fig. 6c | Mondrian utility | 0.25 | 0.252 | `stress r5 mondrian/utility/mean` | PASS |
| EXT-76 | Sect. 9.5, Fig. 6d | raw abstain rate (Monte Carlo model) | 0.225 | 0.2254 | `stress r6 abstain_rate_raw/mean` | PASS |
| EXT-77 | Sect. 9.5, Fig. 6d | autonomous completion (Monte Carlo model) | 0.52 | 0.5211 | `stress r6 completion_autonomous/mean` | PASS |
| EXT-78 | Sect. 9.5, Fig. 6d | completion with fallback (Monte Carlo model) | 1.00 | 1 | `stress r6 completion_with_fallback/mean` | PASS |
| EXT-79 | Sect. 9.5, Fig. 6d | extra steps (Monte Carlo model) | 2.2 | 2.238 | `stress r6 recovery_latency_steps/mean` | PASS |
| EXT-80 | Sect. 9.5 | unsafe explicit executions (Monte Carlo model) | 0.000 | 0 | `stress r6 unsafe_explicit/mean` | PASS |
| EXT-81 | Sect. 9.5 | admitted latent violations (Monte Carlo model) | 0.095 | 0.0953 | `stress r6 unsafe_latent/mean` | PASS |
| EXT-82 | Sect. 9.5, Fig. 6d | fallback share restricted_retry (Monte Carlo model) | 0.34 | 0.3431 | `stress r6 fallback_mix/restricted_retry/mean` | PASS |
| EXT-83 | Sect. 9.5, Fig. 6d | fallback share rollback_compensate (Monte Carlo model) | 0.33 | 0.3326 | `stress r6 fallback_mix/rollback_compensate/mean` | PASS |
| EXT-84 | Sect. 9.5, Fig. 6d | fallback share human_escalation (Monte Carlo model) | 0.32 | 0.3243 | `stress r6 fallback_mix/human_escalation/mean` | PASS |
| EXT-85 | Sect. 9.5, Sect. 11.1 | automaton cost per action (us) | 0.75 | 0.7546 | `core e5_scalability (least-squares slope)` | PASS |
| EXT-86 | Table 6 | PAC mean pass-through, lowest alpha | 0.014 | 0.0138 | `core e2 curve/*/passthrough_pac (min)` | PASS |
| EXT-87 | Table 6 | PAC mean pass-through, highest alpha | 0.277 | 0.2771 | `core e2 curve/*/passthrough_pac (max)` | PASS |
| EXT-88 | Table 6 | PAC conservatism at alpha=0.02 | 0.006 | 0.0058 | `core e2 curve/0` | PASS |
| EXT-89 | Table 6 | PAC conservatism at alpha=0.30 | 0.022 | 0.0217 | `core e2 curve/-1` | PASS |
| EXT-90 | Table 6, Sect. 9.6 | marginal rank at n_v=1200 | 120 | 120 | `floor(alpha (n_v + 1))` | PASS |
| EXT-91 | Table 6, Sect. 9.6 | PAC rank at n_v=1200 | 103 | 103 | `core._pac_rank(1200, 0.10, 0.05)` | PASS |
| EXT-92 | Table 6, Sect. 9.6 | marginal draws sound at alpha=0.10 (%) | 53 | 52.67 | `core e2 curve (alpha=0.10)/sound_frac_marginal` | PASS |
| EXT-93 | Table 6, Sect. 9.6 | PAC draws sound at alpha=0.10 (%) | 95 | 95.33 | `core e2 curve (alpha=0.10)/sound_frac_pac` | PASS |
| EXT-94 | Sect. 9.6 | PAC conservatism at alpha=0.10 | 0.014 | 0.0135 | `core e2 curve (alpha=0.10)` | PASS |
| EXT-95 | Table 6, Fig. 6b | small n_v: PAC pass-through at n_v=20 (k'=0, all abstain) | 0.000 | 0 | `stress r2_small_nv/curve/0/passthrough_pac` | PASS |
| EXT-96 | Table 6 | small n_v: PAC pass-through at n_v=1280 | 0.087 | 0.0873 | `stress r2_small_nv/curve/-1/passthrough_pac` | PASS |
| EXT-97 | Table 6 | small n_v: PAC utility at k'=0 | 0.000 | 0 | `stress r2_small_nv/curve/0/utility_pac` | PASS |
| EXT-98 | Table 6 | small n_v: PAC utility for k' >= 1, lowest | 0.996 | 0.9961 | `stress r2_small_nv/curve/*/utility_pac (min over k' >= 1)` | PASS |
| EXT-99 | Table 6 | small n_v: PAC utility, highest | 1.000 | 0.9999 | `stress r2_small_nv/curve/*/utility_pac (max)` | PASS |
| EXT-100 | Sect. 9.6 | PAC rank at n_v=40 | 1 | 1 | `stress r2_small_nv/curve/1/pac_rank` | PASS |
| EXT-101 | Sect. 9.6 | PAC sound fraction at n_v=40 | 0.975 | 0.975 | `stress r2_small_nv/curve/1/sound_frac_pac` | PASS |
| EXT-102 | Table 6 | detector separation: pass-through at 1.0 | 0.0996 | 0.0996 | `core e3 robustness/0/conformal_passthrough` | PASS |
| EXT-103 | Table 6 | detector separation: pass-through at 3.2 | 0.0984 | 0.0984 | `core e3 robustness/-1/conformal_passthrough` | PASS |
| EXT-104 | Table 6 | miscalibration: conformal pass-through, lowest | 0.0844 | 0.0844 | `stress r4 grid (min)` | PASS |
| EXT-105 | Table 6 | miscalibration: conformal pass-through, highest | 0.0846 | 0.0846 | `stress r4 grid (max)` | PASS |
| EXT-106 | Table 7 | row 1: RQ1 PAC pass-through at alpha=0.10 | 0.086 | 0.0857 | `core e2 curve (alpha=0.10)/passthrough_pac` | PASS |
| EXT-107 | Table 7, Sect. 9.7 | scorer evolution: auto-recalibration | 0.086 | 0.0863 | `stress r8 auto/passthrough/mean` | PASS |
| EXT-108 | Table 7, Sect. 9.7 | scorer evolution: locked profile | 0.026 | 0.0261 | `stress r8 locked/passthrough/mean` | PASS |
| EXT-109 | Sect. 9.7 | auto recalibrations | 3.0 | 3 | `stress r8 auto/recalibrations/mean` | PASS |
| EXT-110 | Table 7, Sect. 9.7 | adversarial switches without hysteresis | 47 | 47 | `stress r8 adversarial_no_hysteresis/profile_switches/mean` | PASS |
| EXT-111 | Table 7, Sect. 9.7 | switches with hysteresis | 0 | 0 | `stress r8 adversarial_hysteresis/profile_switches/mean` | PASS |
| EXT-112 | Sect. 9.7 | spurious recalibrations with hysteresis | 0 | 0 | `stress r8 adversarial_hysteresis/recalibrations/mean` | PASS |
| EXT-113 | Sect. 9.7 | batches, versions, hold | 48,4,3 | 48,4,3 | `stress r8 T/n_versions/hold` | PASS |
| EXT-114 | Sect. 9.7 | calibration traces and steps | 80,6 | 80,6 | `stress r7 n_cal_traces/steps` | PASS |
| EXT-115 | Table 7, Sect. 9.7 | step-level PAC sound fraction at rho=0 | 0.958 | 0.9575 | `stress r7 curve/0/sound_frac_step_corr` | PASS |
| EXT-116 | Table 7, Sect. 9.7 | step-level PAC sound fraction at rho=0.99 | 0.777 | 0.7775 | `stress r7 curve/-1/sound_frac_step_corr` | PASS |
| EXT-117 | Table 7, Sect. 9.7 | trace-level PAC sound fraction at rho=0.99 | 0.978 | 0.9775 | `stress r7 curve/-1/sound_frac_trace_corr` | PASS |
| EXT-118 | Sect. 9.7 | i.i.d. baseline sound fraction (approx.) | 0.96 | 0.958 | `stress r7 curve/*/sound_frac_step_iid (mean)` | PASS |
| EXT-119 | Sect. 9.6 | degradation under content obfuscation (x) | 3.7 | 3.7032 | `core e6 (adaptive / exchangeable)` | PASS |
| EXT-120 | App. B | distinct calibration violation scores, lowest (%) | 31 | 31.4693 | `content.build_content_pool, e6 seeds (recomputed)` | PASS |
| EXT-121 | App. B | distinct calibration violation scores, highest (%) | 36 | 36.0775 | `content.build_content_pool, e6 seeds (recomputed)` | PASS |
| EXT-122 | App. B | violation scores tied at the PAC threshold | 3-21 | 3-21 | `content.build_content_pool, e6 seeds (recomputed)` | PASS |
