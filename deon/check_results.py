#!/usr/bin/env python3
"""Compare the committed result files with the numbers stated in the paper.

The script reads results/core_results.json, results/stress_results.json and
results/agentdojo_results.json and checks a list of headline values against the
figures quoted in the camera-ready paper and in the extended version. Each check has
a label, the value measured in the file, the value claimed in the text and an absolute
tolerance. It prints PASS or FAIL per check, a summary line, and exits with status 0
only if every check passes. It reads files only. It runs in well under a second and
needs neither Ollama nor AgentDojo, and a reader can therefore confirm that the quoted numbers
are backed by the released data without rerunning any experiment.

Coverage. The RQ1 and RQ3 checks (monitor accuracy, PAC sound fraction, content
egress under exchangeable and adaptive leaks) back the camera-ready. The remaining
checks (detector ensemble and Mondrian calibration, the scalability fit, ties, and the
dependence and scorer-evolution stress tests) back results that appear in the
extended version, and one sentence of Sect. 7 cites some of them. The AgentDojo checks
back the RQ2 external test. Because that run is stochastic (see agentdojo_deon.py)
the checks compare the frozen snapshot. The ladder summaries of Table 1 are checked
by scripts/check-claims.py at the top of the artifact, which also covers every other
camera-ready number. The labels printed by this script use the research-question
numbering of the extended version.

    python3 check_results.py
"""
import json
import os
import sys
from artifact_paths import RESULTS

HERE = os.path.dirname(os.path.abspath(__file__))
JSON = os.path.join(RESULTS, "core_results.json")


def _get(d, path):
    for k in path.split("/"):
        d = d[k]
    return d


def main():
    with open(JSON) as f:
        d = json.load(f)

    # Each entry is (label, measured value, value claimed in the paper, tolerance).
    checks = [
        ("RQ1 monitor accuracy on 900 traces (100%)",
         _get(d, "e1_monitor_soundness/accuracy"), 100.0, 1e-6),
        ("RQ1 PAC sound-fraction overall (94.5%)",
         _get(d, "e2_conformal_coverage/overall_sound_frac_pac"), 0.9448, 0.005),
        ("RQ3 content-egress: DPA-only leak pass-through (blind, 1.00)",
         _get(d, "e6_content_egress/exchangeable/dpa_only/mean"), 1.0, 1e-9),
        ("RQ3 content-egress: conformal exchangeable (<=alpha, 0.089)",
         _get(d, "e6_content_egress/exchangeable/policyshield/mean"), 0.089, 0.01),
        ("RQ3 content-egress: conformal adaptive (breaks, 0.328)",
         _get(d, "e6_content_egress/adaptive/policyshield/mean"), 0.328, 0.02),
        ("RQ4 ensemble: lexical adaptive leak (0.835)",
         _get(d, "e7_ensemble_egress/adaptive_obf/single/lexical/mean"), 0.835, 0.01),
        ("RQ4 ensemble: max-ensemble adaptive leak (~alpha, 0.097)",
         _get(d, "e7_ensemble_egress/adaptive_obf/ensemble/mean"), 0.097, 0.01),
        ("RQ4 ensemble: exchangeable pass-through (0.082)",
         _get(d, "e7_ensemble_egress/exchangeable/ensemble/mean"), 0.082, 0.01),
        ("RQ4 ensemble: naturalised evade-all defeats ensemble (1.00)",
         _get(d, "e7_ensemble_egress/adaptive_evade_all/ensemble/mean"), 1.0, 0.02),
        ("RQ4 Mondrian: marginal leaks on hard group under shift (0.441)",
         _get(d, "e8_mondrian_shift/marginal/per_group/hard/mean"), 0.441, 0.01),
        ("RQ4 Mondrian: per-group calibration worst-group (<=alpha, 0.091)",
         _get(d, "e8_mondrian_shift/mondrian/worst_group/mean"), 0.091, 0.01),
    ]

    # Scalability: R^2 of a straight line through the released timing points.
    # Wall-clock microbenchmarks vary across hosts, so this check uses a wider
    # tolerance than the seed-fixed outcome checks while still requiring the
    # regenerated curve to remain strongly linear.
    try:
        import numpy as np
        pts = d["e5_scalability"]
        L = np.array([p["length"] for p in pts])
        us = np.array([p["us_mean"] for p in pts])
        r2 = float(np.corrcoef(L, us)[0, 1] ** 2)
        checks.append(("RQ5 monitor cost: linear-fit R^2 (~0.987; timing-sensitive)",
                       r2, 0.987, 0.03))
    except Exception as e:  # pragma: no cover
        print(f"[warn] could not compute scalability R^2: {e}")

    # Headline numbers of the stress tests (ties, sequential dependence, scorer
    # evolution), read from results/stress_results.json.
    rv_path = os.path.join(RESULTS, "stress_results.json")
    if os.path.exists(rv_path):
        with open(rv_path) as f:
            rv = json.load(f)
        r7 = next(c for c in rv["r7_sequential_dependence"]["curve"]
                  if abs(c["rho"] - 0.99) < 1e-6)
        checks += [
            ("RQ5 ties: deterministic rule over-admits (0.343)",
             rv["r3_ties"]["det_admit_le"]["mean"], 0.343, 0.01),
            ("RQ5 ties: randomized tie-break restores (~alpha, 0.100)",
             rv["r3_ties"]["randomised_tiebreak"]["mean"], 0.100, 0.002),
            ("RQ6 dependence: step-level PAC erodes (0.777 at rho=0.99)",
             r7["sound_frac_step_corr"], 0.777, 0.01),
            ("RQ6 dependence: trace-level PAC restores (>=1-delta, 0.978)",
             r7["sound_frac_trace_corr"], 0.978, 0.01),
            ("RQ6 scorer: naive-auto switches under toggling (47)",
             rv["r8_scorer_evolution"]["adversarial_no_hysteresis"]["profile_switches"]["mean"],
             47.0, 0.5),
            ("RQ6 scorer: hysteresis absorbs oscillation (0 switches)",
             rv["r8_scorer_evolution"]["adversarial_hysteresis"]["profile_switches"]["mean"],
             0.0, 1e-9),
        ]

    # Optional: the AgentDojo head-to-head. The snapshot is the one cited by the RQ2
    # paragraph on external validity. It comes from the stochastic LLM run in
    # agentdojo_deon.py, and the checks read the committed numbers and do not regenerate them. The
    # block is skipped when the file is absent.
    ad_path = os.path.join(RESULTS, "agentdojo_results.json")
    if os.path.exists(ad_path):
        with open(ad_path) as f:
            ad = json.load(f)
        dfn = ad["defenses"]
        checks += [
            ("AgentDojo undefended ASR (11.8%)",
             dfn["none"]["asr_under_injection"], 0.118, 0.02),
            ("AgentDojo spotlighting ASR (barely helps, 10.5%)",
             dfn["spotlighting"]["asr_under_injection"], 0.105, 0.02),
            ("AgentDojo repeat-prompt ASR (barely helps, 9.2%)",
             dfn["repeat_user_prompt"]["asr_under_injection"], 0.092, 0.02),
            ("AgentDojo DeBERTa PI-detector ASR (halves, still leaks, 6.6%)",
             dfn["pi_detector"]["asr_under_injection"], 0.066, 0.02),
            ("AgentDojo TestSavant-large detector ASR (still leaks, 7.9%)",
             dfn["testsavant_detector"]["asr_under_injection"], 0.079, 0.02),
            ("AgentDojo Meta Prompt-Guard-86M ASR (no better than undefended, 14.5%)",
             dfn["promptguard"]["asr_under_injection"], 0.145, 0.02),
            ("AgentDojo deepset detector ASR=0 but lower utility (31.2%)",
             dfn["deepset_detector"]["benign_utility"], 0.3125, 0.02),
            ("AgentDojo tool-filter ASR = 0 (but over-prunes)",
             dfn["tool_filter"]["asr_under_injection"], 0.0, 1e-9),
            ("AgentDojo tool-filter benign utility collapses (25%)",
             dfn["tool_filter"]["benign_utility"], 0.25, 0.02),
            ("AgentDojo Deon (DPA) ASR = 0",
             dfn["deon"]["asr_under_injection"], 0.0, 1e-9),
            ("AgentDojo Deon (DPA) benign utility preserved (37.5%)",
             dfn["deon"]["benign_utility"], 0.375, 0.02),
        ]

    ok = True
    for label, actual, claimed, tol in checks:
        passed = abs(float(actual) - float(claimed)) <= tol
        ok = ok and passed
        tag = "PASS" if passed else "FAIL"
        print(f"  [{tag}] {label:60s} | claimed {claimed}, measured {actual:.4f} (tol {tol})")

    print()
    n = len(checks)
    n_ok = sum(1 for l, a, c, t in checks if abs(float(a) - float(c)) <= t)
    print(f"{n_ok}/{n} claims match the manuscript.")
    print("RESULT:", "PASS -- artifact results are consistent with the paper."
          if ok else "FAIL -- a measured value diverges from the manuscript.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
