#!/usr/bin/env python3
"""Check every number of the camera-ready paper that comes from a result file.

Usage:
    python3 scripts/check-claims.py                  # committed results in deon/results
    python3 scripts/check-claims.py --results DIR    # results regenerated into DIR

The script first runs deon/check_results.py (the original 29-check gate) on the same
results folder. It then checks the camera-ready paper (paper/camera-ready.pdf) claim by
claim, followed by the headline claims and tables of the extended version
(paper/extended.pdf). Every check names its location in the current PDFs (Abstract,
Sect., Table, Fig.), the value printed in the paper, the value in the result file and
the file and key it comes from. A value matches when it agrees with the printed value
up to the paper's rounding (half a unit of the last printed digit).

Status words:
  PASS       the value matches the paper
  FAIL       the value does not match. The script exits with status 1.
  DEVIATION  a known difference between the paper text and the artifact that is
             documented in CLAIM_MATRIX.md. It does not fail the gate. No check of this
             release is marked this way.
  INFO       a wall-clock timing value checked against regenerated results. Timing
             depends on the host, so it is printed and not judged.

A few claims are properties of the generators rather than of a result file (the class
counts of the monitor suite, trace lengths, PAC ranks, the tie statistics of App. B).
The script recomputes those from the seeded code in deon/ in about a second.
"""
import argparse
import glob
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEON = ROOT / "deon"
COMMITTED = DEON / "results"

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("--results", default=str(COMMITTED),
                help="folder with core_results.json, stress_results.json, "
                     "agentdojo_results.json and llm_summary_*.json")
ap.add_argument("--skip-gate", action="store_true",
                help="do not run deon/check_results.py first")
ap.add_argument("--markdown", action="store_true",
                help="print the checks as Markdown tables (used for CLAIM_MATRIX.md)")
args = ap.parse_args()
RES = Path(args.results).resolve()
REGENERATED = RES != COMMITTED.resolve()

os.environ["POLICYSHIELD_RESULTS"] = str(RES)
sys.path.insert(0, str(DEON))
sys.dont_write_bytecode = True

gate_ok = True
if not args.skip_gate and not args.markdown:
    print(f"== deon/check_results.py on {RES.relative_to(ROOT) if RES.is_relative_to(ROOT) else RES}",
          flush=True)
    r = subprocess.run([sys.executable, "check_results.py"], cwd=DEON, capture_output=True,
                       text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    print(r.stdout, end="", flush=True)
    gate_ok = r.returncode == 0
    failed = [ln for ln in r.stdout.splitlines() if "[FAIL]" in ln]
    if not gate_ok and REGENERATED and failed and all("timing-sensitive" in ln for ln in failed):
        # Wall-clock timings of a rerun depend on the host and its load. They are
        # reported as INFO below, like the timing claims of this script.
        gate_ok = True
        print("NOTE: the only failing gate check is the host-dependent timing fit of a rerun."
              " It is treated as INFO.")
    print(flush=True)


def load(name):
    with open(RES / name) as f:
        return json.load(f)


core = load("core_results.json")
stress = load("stress_results.json")
adojo = load("agentdojo_results.json")
ladder = {}
for fp in sorted(glob.glob(str(RES / "llm_summary_*.json"))):
    with open(fp) as f:
        d = json.load(f)
    ladder[d["model"]] = d
if len(ladder) != 6:
    sys.exit(f"expected six llm_summary files in {RES}, found {len(ladder)}")


def get(d, path):
    for k in path.split("/"):
        d = d[int(k)] if isinstance(d, list) else d[k]
    return d


def tol(printed):
    """Half a unit of the last printed digit of `printed` (a string)."""
    s = printed.lstrip("-")
    dec = len(s.split(".")[1]) if "." in s else 0
    return 0.5 * 10 ** (-dec) + 1e-9


# Derived quantities that come from the seeded generators rather than a result file.
import bench, catalog, content, llm                     # noqa: E402
import experiments_core as ec                           # noqa: E402
from core import _pac_rank, calibrate_threshold         # noqa: E402

_suite = bench.build_monitor_suite(np.random.default_rng(0), 900)
CLASS_COUNTS = [sum(1 for *_, v in _suite if v == c) for c in bench.VIOLATION_CLASSES]
LEN_COMPLIANT = [len(t) for t, _, ok, _ in _suite if ok]
LEN_VIOLATING = [len(t) for t, _, ok, _ in _suite if not ok]
N_DESCRIBED = len([ln for ln in catalog.catalogue_desc().splitlines() if ":" in ln])


def _appb_ties():
    distinct, ties = [], []
    for s in range(30):                                  # e6 protocol: seed0=6, n_cal=3000
        rng = np.random.default_rng(6 + s)
        _, sc, y = content.build_content_pool(rng, 3000)
        v = sc[y == 1]
        distinct.append(len(np.unique(v)) / len(v))
        tau = calibrate_threshold(sc, y, alpha=0.10, delta=0.05, pac=True)
        ties.append(int((v == tau).sum()))
    return min(distinct), max(distinct), min(ties), max(ties)


APPB = _appb_ties()


def default(fn, name):
    return inspect.signature(fn).parameters[name].default


e5 = core["e5_scalability"]
_L = np.array([p["length"] for p in e5], float)
_us = np.array([p["us_mean"] for p in e5], float)
SLOPE = float(np.polyfit(_L, _us, 1)[0])
R2 = float(np.corrcoef(_L, _us)[0, 1] ** 2)

e2c = core["e2_conformal_coverage"]["curve"]
e3r = core["e3_risk_utility"]["robustness"]
e7 = core["e7_ensemble_egress"]
AD = adojo["defenses"]
lost = [t for t, ok in AD["none"]["utility_per_task"].items()
        if ok and not AD["deon"]["utility_per_task"][t]]
gained = [t for t, ok in AD["deon"]["utility_per_task"].items()
          if ok and not AD["none"]["utility_per_task"][t]]
asr_u = [m["asr_unguarded"] for m in ladder.values()]
asr_g = [m["asr_policyshield"] for m in ladder.values()]
r1 = stress["r1_label_noise"]["curve"]
r2 = stress["r2_small_nv"]["curve"]
r4 = stress["r4_miscalibration"]["grid"]
r5 = stress["r5_drift_rolling"]
r6 = stress["r6_abstention_recovery"]
r7 = stress["r7_sequential_dependence"]["curve"]
r8 = stress["r8_scorer_evolution"]
fixed4 = [g["fixed_passthrough"] for g in r4]


def ci_half(node, acc):
    if isinstance(node, dict):
        if "ci" in node and "mean" in node:
            acc.append((node["ci"][1] - node["ci"][0]) / 2)
        for v in node.values():
            ci_half(v, acc)
    return acc


# Each check: (paper, location, claim, printed value, measured value, source, options)
# options: timing=True (host dependent, INFO on regenerated results), exact=True (integer
# or equality check), tolerance=x (override the rounding tolerance), kind="deviation"
# (documented mismatch) and regen="deviation" (differs only when the code is rerun). The
# last two are not used by any check of this release.
C = []


def add(paper, loc, claim, printed, value, source, **o):
    C.append((paper, loc, claim, printed, value, source, o))


pct = lambda x: 100 * x  # noqa: E731

# ---------------------------------------------------------------- camera-ready
CR = "CR"
add(CR, "Abstract, Sect. 7 RQ1", "automaton agrees with ground truth (%)", "100",
    get(core, "e1_monitor_soundness/accuracy"), "core e1_monitor_soundness/accuracy")
add(CR, "Abstract, Sect. 7", "monitor-suite traces", "900",
    get(core, "e1_monitor_soundness/n"), "core e1_monitor_soundness/n", exact=True)
add(CR, "Abstract, Sect. 7", "violation classes", "6",
    len(get(core, "e1_monitor_soundness/per_class_recall")),
    "core e1_monitor_soundness/per_class_recall", exact=True)
add(CR, "Abstract, Sect. 7 RQ3", "leaks admitted, exchangeable (%)", "8.9",
    pct(get(core, "e6_content_egress/exchangeable/policyshield/mean")),
    "core e6_content_egress/exchangeable/policyshield/mean")
add(CR, "Abstract, Sect. 7 RQ3", "target alpha (%)", "10",
    pct(get(core, "e6_content_egress/alpha")), "core e6_content_egress/alpha")
add(CR, "Abstract, Sect. 7 RQ3", "leaks admitted, adaptive obfuscation (%)", "32.8",
    pct(get(core, "e6_content_egress/adaptive/policyshield/mean")),
    "core e6_content_egress/adaptive/policyshield/mean")
add(CR, "Abstract, Sect. 1, Sect. 7 RQ2", "proposer models", "6", len(ladder),
    "llm_summary_*.json (count)", exact=True)
add(CR, "Abstract, Sect. 1, Sect. 7 RQ2", "unguarded ASR, lowest (%)", "87", min(asr_u),
    "llm_summary_*.json asr_unguarded (min)")
add(CR, "Abstract, Sect. 1, Sect. 7 RQ2", "unguarded ASR, highest (%)", "100", max(asr_u),
    "llm_summary_*.json asr_unguarded (max)")
add(CR, "Abstract, Sect. 7 RQ2", "guarded ASR, all models (%)", "0", max(asr_g),
    "llm_summary_*.json asr_policyshield (max)")
add(CR, "Abstract", "microsecond-scale overhead: every trace of 2 to 12 actions under 10 us",
    "yes", "yes" if float(_us.max()) < 10 else "no",
    "core e5_scalability/*/us_mean (max)", exact=True, timing=True)
# Sect. 7, setup paragraph
add(CR, "Sect. 7 setup", "compliant traces", "450",
    get(core, "e1_monitor_soundness/n_admissible"), "core e1_monitor_soundness/n_admissible",
    exact=True)
add(CR, "Sect. 7 setup", "traces with one planted violation", "450",
    get(core, "e1_monitor_soundness/n_violating"), "core e1_monitor_soundness/n_violating",
    exact=True)
for name, printed, got in zip(bench.VIOLATION_CLASSES, "84 65 81 83 70 67".split(),
                              CLASS_COUNTS):
    add(CR, "Sect. 7 setup", f"traces of class {name} at the released seed", printed, got,
        "bench.build_monitor_suite(seed 0, 900) (recomputed)", exact=True)
add(CR, "Sect. 7 setup", "calibration draws n", "4000",
    default(ec.e2_conformal_coverage, "n_cal"), "experiments_core.e2 default n_cal", exact=True)
add(CR, "Sect. 7 setup", "calibration violations n_v (approx.)", "1200",
    default(ec.e2_conformal_coverage, "n_cal") * default(bench.build_risk_pool, "base_rate"),
    "n_cal x bench.build_risk_pool base_rate (expected value)")
add(CR, "Sect. 7 setup", "evaluation draws n", "20000",
    default(ec.e2_conformal_coverage, "n_eval"), "experiments_core.e2 default n_eval",
    exact=True)
add(CR, "Sect. 7 setup", "trials per alpha", "300",
    get(core, "e2_conformal_coverage/trials"), "core e2_conformal_coverage/trials", exact=True)
add(CR, "Sect. 7 setup", "mixed stream: actions per trial", "4000",
    default(ec.e4_attack_synth, "n"), "experiments_core.e4 default n", exact=True)
add(CR, "Sect. 7 setup", "mixed stream: explicit share (%)", "35",
    pct(get(core, "e4_attack_synth/frac_explicit")), "core e4_attack_synth/frac_explicit")
add(CR, "Sect. 7 setup", "ladder catalogue operations", "11", len(catalog.CATALOG),
    "catalog.CATALOG", exact=True)
add(CR, "Sect. 7 setup", "operations described to the proposer", "8", N_DESCRIBED,
    "catalog.catalogue_desc()", exact=True)
add(CR, "Sect. 7 setup, Sect. 7 RQ2", "AgentDojo non-degenerate pairs", "76",
    AD["deon"]["n_attack_combos"], "agentdojo defenses/deon/n_attack_combos", exact=True)
add(CR, "Sect. 7 setup", "fixed-threshold cutoff", "0.5",
    get(core, "e3_risk_utility/fixed_tau"), "core e3_risk_utility/fixed_tau")
add(CR, "Sect. 7 setup, Table 1", "benign runs per model", "30",
    min(m["n_benign"] for m in ladder.values()), "llm_summary_*.json n_benign", exact=True)
add(CR, "Sect. 7 setup, Table 1", "attack runs per model", "30",
    min(m["n_attack"] for m in ladder.values()), "llm_summary_*.json n_attack", exact=True)
add(CR, "Sect. 7 setup", "repetitions per task", "6",
    min(m["reps"] for m in ladder.values()), "llm_summary_*.json reps", exact=True)
add(CR, "Sect. 7 setup", "benign and attack tasks", "5",
    min(len(catalog.BENIGN_TASKS), len(catalog.ATTACK_TASKS)), "catalog tasks", exact=True)
add(CR, "Sect. 7 setup", "proposer temperature", "0.7",
    default(llm.propose, "temperature"), "llm.propose default temperature")
# Sect. 7, RQ1
add(CR, "Sect. 7 RQ1", "recall, lowest class (%)", "100",
    min(get(core, "e1_monitor_soundness/per_class_recall").values()),
    "core e1_monitor_soundness/per_class_recall (min)")
add(CR, "Sect. 7 RQ1", "marginal mean pass-through, lowest alpha", "0.020",
    min(c["passthrough"] for c in e2c), "core e2_conformal_coverage/curve/*/passthrough (min)")
add(CR, "Sect. 7 RQ1", "marginal mean pass-through, highest alpha", "0.299",
    max(c["passthrough"] for c in e2c), "core e2_conformal_coverage/curve/*/passthrough (max)")
add(CR, "Sect. 7 RQ1", "marginal utility, lowest (%)", "100",
    pct(min(c["utility"] for c in e2c)), "core e2_conformal_coverage/curve/*/utility (min)",
    tolerance=0.5)
add(CR, "Sect. 7 RQ1, Fig. 3a", "marginal draws holding target, lowest (%)", "51",
    pct(min(c["sound_frac_marginal"] for c in e2c)),
    "core e2_conformal_coverage/curve/*/sound_frac_marginal (min)", tolerance=0.5)
add(CR, "Sect. 7 RQ1, Fig. 3a", "marginal draws holding target, highest (%)", "56",
    pct(max(c["sound_frac_marginal"] for c in e2c)),
    "core e2_conformal_coverage/curve/*/sound_frac_marginal (max)", tolerance=0.5)
add(CR, "Sect. 7 RQ1, Fig. 3a", "exact-PAC draws holding target, lowest (%)", "93",
    pct(min(c["sound_frac_pac"] for c in e2c)),
    "core e2_conformal_coverage/curve/*/sound_frac_pac (min)")
add(CR, "Sect. 7 RQ1, Fig. 3a", "exact-PAC draws holding target, highest (%)", "96",
    pct(max(c["sound_frac_pac"] for c in e2c)),
    "core e2_conformal_coverage/curve/*/sound_frac_pac (max)")
add(CR, "Sect. 7 RQ1, Fig. 3a", "1 - delta", "0.95",
    1 - get(core, "e2_conformal_coverage/delta"), "core e2_conformal_coverage/delta")
add(CR, "Sect. 7 RQ1", "Deon pass-through across detector quality, lowest", "0.098",
    min(r["conformal_passthrough"] for r in e3r),
    "core e3_risk_utility/robustness/*/conformal_passthrough (min)")
add(CR, "Sect. 7 RQ1", "Deon pass-through across detector quality, highest", "0.100",
    max(r["conformal_passthrough"] for r in e3r),
    "core e3_risk_utility/robustness/*/conformal_passthrough (max)")
add(CR, "Sect. 7 RQ1", "Deon utility at the weakest detector", "0.76",
    e3r[0]["conformal_utility"], "core e3_risk_utility/robustness/0/conformal_utility")
add(CR, "Sect. 7 RQ1", "Deon utility at the strongest detector", "1.00",
    e3r[-1]["conformal_utility"], "core e3_risk_utility/robustness/-1/conformal_utility")
add(CR, "Sect. 7 RQ1", "fixed cutoff leak at the weakest detector", "0.158",
    e3r[0]["fixed_passthrough"], "core e3_risk_utility/robustness/0/fixed_passthrough")
# Table 1
T1 = [("gemma2:2b", "100", "100", "100", "0"), ("llama3.2:3b", "97", "100", "100", "0"),
      ("qwen2.5-coder:7b", "100", "100", "87", "0"),
      ("qwen2.5-coder:32b", "100", "100", "100", "0"),
      ("command-r:35b", "100", "100", "100", "0"), ("mixtral:8x7b", "100", "100", "100", "0")]
keys = ["benign_success_unguarded", "benign_success_policyshield", "asr_unguarded",
        "asr_policyshield"]
for model, *cells in T1:
    fn = "llm_summary_" + model.replace(":", "_").replace("/", "_") + ".json"
    for k, printed in zip(keys, cells):
        add(CR, "Table 1", f"{model} {k}", printed, ladder[model][k], f"{fn} {k}")
# Sect. 7, RQ2
add(CR, "Sect. 7 RQ2", "llama3.2:3b benign success unguarded (the 97)", "97",
    ladder["llama3.2:3b"]["benign_success_unguarded"],
    "llm_summary_llama3.2_3b.json benign_success_unguarded")
add(CR, "Sect. 7 RQ2", "mixed stream, unguarded executed violations (%)", "100",
    pct(get(core, "e4_attack_synth/unguarded_asr")), "core e4_attack_synth/unguarded_asr")
add(CR, "Sect. 7 RQ2", "mixed stream, Deon (%)", "3.6",
    pct(get(core, "e4_attack_synth/policyshield_asr")), "core e4_attack_synth/policyshield_asr")
add(CR, "Sect. 7 RQ2", "mixed stream, DPA only (%)", "35.7",
    pct(get(core, "e4_attack_synth/dpa_only_asr")), "core e4_attack_synth/dpa_only_asr")
add(CR, "Sect. 7 RQ2", "AgentDojo undefended utility (%)", "50.0",
    pct(AD["none"]["benign_utility"]), "agentdojo defenses/none/benign_utility")
add(CR, "Sect. 7 RQ2", "AgentDojo undefended ASR (%)", "11.8",
    pct(AD["none"]["asr_under_injection"]), "agentdojo defenses/none/asr_under_injection")
add(CR, "Sect. 7 RQ2", "prompt-level defences, lower end (repeat-prompt) ASR (%)", "9.2",
    pct(AD["repeat_user_prompt"]["asr_under_injection"]),
    "agentdojo defenses/repeat_user_prompt/asr_under_injection")
add(CR, "Sect. 7 RQ2", "prompt-level defences, upper end (spotlighting) ASR (%)", "10.5",
    pct(AD["spotlighting"]["asr_under_injection"]),
    "agentdojo defenses/spotlighting/asr_under_injection")
add(CR, "Sect. 7 RQ2", "deepset detector ASR (%)", "0",
    pct(AD["deepset_detector"]["asr_under_injection"]),
    "agentdojo defenses/deepset_detector/asr_under_injection")
add(CR, "Sect. 7 RQ2", "deepset detector utility (%)", "31.2",
    pct(AD["deepset_detector"]["benign_utility"]), "agentdojo defenses/deepset_detector/benign_utility",
    tolerance=0.05 + 1e-6)
add(CR, "Sect. 7 RQ2", "tool-filter ASR (%)", "0",
    pct(AD["tool_filter"]["asr_under_injection"]), "agentdojo defenses/tool_filter/asr_under_injection")
add(CR, "Sect. 7 RQ2", "tool-filter utility (%)", "25.0",
    pct(AD["tool_filter"]["benign_utility"]), "agentdojo defenses/tool_filter/benign_utility")
add(CR, "Sect. 7 RQ2", "Deon ASR on AgentDojo (%)", "0",
    pct(AD["deon"]["asr_under_injection"]), "agentdojo defenses/deon/asr_under_injection")
add(CR, "Sect. 7 RQ2", "Deon utility on AgentDojo (%)", "37.5",
    pct(AD["deon"]["benign_utility"]), "agentdojo defenses/deon/benign_utility")
add(CR, "Sect. 7 RQ2", "benign tasks Deon loses relative to undefended", "2",
    len(lost) + len(gained), "agentdojo defenses/{none,deon}/utility_per_task", exact=True)
add(CR, "Sect. 7 RQ2", "benign AgentDojo tasks", "16", AD["deon"]["n_benign"],
    "agentdojo defenses/deon/n_benign", exact=True)
# Sect. 7, RQ3 and Fig. 3b, 3c
add(CR, "Sect. 7 RQ3, Fig. 3b", "DPA-only pass-through, exchangeable", "1.00",
    get(core, "e6_content_egress/exchangeable/dpa_only/mean"),
    "core e6_content_egress/exchangeable/dpa_only/mean")
add(CR, "Fig. 3b", "DPA-only pass-through, adaptive", "1.00",
    get(core, "e6_content_egress/adaptive/dpa_only/mean"),
    "core e6_content_egress/adaptive/dpa_only/mean")
add(CR, "Sect. 7 RQ3", "seeds", "30", get(core, "e6_content_egress/seeds"),
    "core e6_content_egress/seeds", exact=True)
add(CR, "Sect. 7 RQ3, Fig. 3b", "Deon pass-through, exchangeable", "0.089",
    get(core, "e6_content_egress/exchangeable/policyshield/mean"),
    "core e6_content_egress/exchangeable/policyshield/mean")
add(CR, "Sect. 7 RQ3", "Deon utility, exchangeable (%)", "100",
    pct(get(core, "e6_content_egress/exchangeable/benign_utility/mean")),
    "core e6_content_egress/exchangeable/benign_utility/mean")
add(CR, "Sect. 7 RQ3, Fig. 3b", "Deon pass-through, adaptive", "0.328",
    get(core, "e6_content_egress/adaptive/policyshield/mean"),
    "core e6_content_egress/adaptive/policyshield/mean")
add(CR, "Sect. 7 RQ3, Fig. 3c", "max-ensemble, obfuscated", "0.097",
    get(e7, "adaptive_obf/ensemble/mean"), "core e7_ensemble_egress/adaptive_obf/ensemble/mean")
add(CR, "Sect. 7 RQ3, Fig. 3c", "lexical alone, obfuscated", "0.835",
    get(e7, "adaptive_obf/single/lexical/mean"),
    "core e7_ensemble_egress/adaptive_obf/single/lexical/mean")
add(CR, "Fig. 3c", "lexical alone, exchangeable", "0.083",
    get(e7, "exchangeable/single/lexical/mean"),
    "core e7_ensemble_egress/exchangeable/single/lexical/mean")
add(CR, "Fig. 3c", "max-ensemble, exchangeable", "0.082", get(e7, "exchangeable/ensemble/mean"),
    "core e7_ensemble_egress/exchangeable/ensemble/mean")
add(CR, "Fig. 3c", "naturalised payload vs lexical detector", "1.00",
    get(e7, "adaptive_evade_all/single/lexical/mean"),
    "core e7_ensemble_egress/adaptive_evade_all/single/lexical/mean")
add(CR, "Sect. 7 RQ3, Fig. 3c", "naturalised payload evades the ensemble", "1.00",
    get(e7, "adaptive_evade_all/ensemble/mean"),
    "core e7_ensemble_egress/adaptive_evade_all/ensemble/mean")
# Sect. 7, stress-test paragraph
add(CR, "Sect. 7 stress tests", "Mondrian study: marginal worst group", "0.441",
    get(core, "e8_mondrian_shift/marginal/worst_group/mean"),
    "core e8_mondrian_shift/marginal/worst_group/mean")
add(CR, "Sect. 7 stress tests", "marginal worst group in units of alpha", "4.4",
    get(core, "e8_mondrian_shift/marginal/worst_group/mean") / get(core, "e8_mondrian_shift/alpha"),
    "core e8_mondrian_shift (worst_group / alpha)")
add(CR, "Sect. 7 stress tests", "Mondrian worst group", "0.091",
    get(core, "e8_mondrian_shift/mondrian/worst_group/mean"),
    "core e8_mondrian_shift/mondrian/worst_group/mean")
add(CR, "Sect. 7 stress tests", "utility, marginal", "0.95",
    get(core, "e8_mondrian_shift/marginal/utility/mean"),
    "core e8_mondrian_shift/marginal/utility/mean")
add(CR, "Sect. 7 stress tests", "utility, Mondrian", "0.71",
    get(core, "e8_mondrian_shift/mondrian/utility/mean"),
    "core e8_mondrian_shift/mondrian/utility/mean")
add(CR, "Sect. 7 stress tests", "label noise rho=0: PAC pass-through", "0.085",
    r1[0]["passthrough_pac"], "stress r1_label_noise/curve/0/passthrough_pac")
add(CR, "Sect. 7 stress tests", "label noise rho=0.3: PAC pass-through", "0.000",
    r1[-1]["passthrough_pac"], "stress r1_label_noise/curve/-1/passthrough_pac")
add(CR, "Sect. 7 stress tests", "label noise rho=0: utility", "1.00",
    r1[0]["utility_pac"], "stress r1_label_noise/curve/0/utility_pac")
add(CR, "Sect. 7 stress tests", "label noise rho=0.3: utility", "0.17",
    r1[-1]["utility_pac"], "stress r1_label_noise/curve/-1/utility_pac")
add(CR, "Sect. 7 stress tests", "ties: deterministic <= leaks", "0.343",
    get(stress, "r3_ties/det_admit_le/mean"), "stress r3_ties/det_admit_le/mean")
add(CR, "Sect. 7 stress tests", "ties: augmented-score tie-break mean", "0.100",
    get(stress, "r3_ties/randomised_tiebreak/mean"), "stress r3_ties/randomised_tiebreak/mean")
add(CR, "Sect. 7 stress tests", "PAC rank at n_v=20", "0", r2[0]["pac_rank"],
    "stress r2_small_nv/curve/0/pac_rank", exact=True)
add(CR, "Sect. 7 stress tests", "automaton cost per action (us, slope over lengths 2 to 12)",
    "0.75", SLOPE, "core e5_scalability (least-squares slope)", timing=True)
add(CR, "Sect. 7 stress tests", "linear-fit R^2", "0.99", R2, "core e5_scalability (R^2)",
    timing=True)
add(CR, "Sect. 7 stress tests", "shortest and longest trace length", "2-12",
    f"{int(_L.min())}-{int(_L.max())}", "core e5_scalability/*/length", exact=True)
add(CR, "Sect. 7 stress tests", "traces per timing batch", "20000",
    default(ec.e5_scalability, "reps"), "experiments_core.e5 default reps", exact=True)
add(CR, "Sect. 7 stress tests", "timing batches per length", "5",
    5 if "for _ in range(5)" in inspect.getsource(ec.e5_scalability) else -1,
    "experiments_core.e5_scalability source", exact=True)

# ---------------------------------------------------------------- extended version
EX = "EXT"
add(EX, "Sect. 8.2", "calibration violations n_v: binomial standard deviation", "29",
    float(np.sqrt(default(ec.e2_conformal_coverage, "n_cal") * 0.30 * 0.70)),
    "sqrt(n_cal x 0.30 x 0.70)")
add(EX, "Sect. 8.2, Table 2", "compliant trace length, max", "8", max(LEN_COMPLIANT),
    "bench.build_monitor_suite(seed 0) (recomputed)", exact=True)
add(EX, "Sect. 8.2", "compliant trace length, mean", "4.8", float(np.mean(LEN_COMPLIANT)),
    "bench.build_monitor_suite(seed 0) (recomputed)")
add(EX, "Sect. 8.2, Table 2", "violating trace length, max", "11", max(LEN_VIOLATING),
    "bench.build_monitor_suite(seed 0) (recomputed)", exact=True)
add(EX, "Sect. 8.2", "violating trace length, mean", "6.1", float(np.mean(LEN_VIOLATING)),
    "bench.build_monitor_suite(seed 0) (recomputed)")
add(EX, "Sect. 8.2, Table 2", "mixed-stream trials", "400",
    default(ec.e4_attack_synth, "trials"), "experiments_core.e4 default trials", exact=True)
add(EX, "Sect. 8.2, Table 2", "content egress n_cal", "3000",
    default(ec.e6_content_egress, "n_cal"), "experiments_core.e6 default n_cal", exact=True)
add(EX, "Sect. 8.2, Table 2", "content egress n_eval", "4000",
    default(ec.e6_content_egress, "n_eval"), "experiments_core.e6 default n_eval", exact=True)
add(EX, "Sect. 8.2", "Mondrian n_cal", "6000", default(ec.e8_mondrian_shift, "n_cal"),
    "experiments_core.e8 default n_cal", exact=True)
add(EX, "Sect. 8.2", "Mondrian n_eval", "12000", default(ec.e8_mondrian_shift, "n_eval"),
    "experiments_core.e8 default n_eval", exact=True)
add(EX, "Sect. 9.1", "exact-PAC draws holding target, pooled (%)", "94.5",
    pct(get(core, "e2_conformal_coverage/overall_sound_frac_pac")),
    "core e2_conformal_coverage/overall_sound_frac_pac")
add(EX, "Sect. 9.1", "fixed cutoff at the strongest detector", "0.001",
    e3r[-1]["fixed_passthrough"], "core e3_risk_utility/robustness/-1/fixed_passthrough")
# Table 4 (AgentDojo)
T4 = [("none", "50.0", "11.8"), ("promptguard", "37.5", "14.5"), ("spotlighting", "43.8", "10.5"),
      ("repeat_user_prompt", "43.8", "9.2"), ("testsavant_detector", "43.8", "7.9"),
      ("pi_detector", "31.2", "6.6"), ("deepset_detector", "31.2", "0.0"),
      ("tool_filter", "25.0", "0.0"), ("deon", "37.5", "0.0")]
for dname, util, asr in T4:
    add(EX, "Table 4", f"{dname} benign utility (%)", util, pct(AD[dname]["benign_utility"]),
        f"agentdojo defenses/{dname}/benign_utility", tolerance=0.05 + 1e-6)
    add(EX, "Table 4", f"{dname} ASR (%)", asr, pct(AD[dname]["asr_under_injection"]),
        f"agentdojo defenses/{dname}/asr_under_injection")
add(EX, "App. C", "excluded degenerate pairs", "4", len(adojo["excluded_degenerate_combos"]),
    "agentdojo excluded_degenerate_combos", exact=True)
add(EX, "App. C, Table 9", "benign tasks Deon loses: user_task_0 and user_task_4",
    "user_task_0,user_task_4", ",".join(sorted(lost)) if not gained else "mismatch",
    "agentdojo defenses/{none,deon}/utility_per_task", exact=True)
# Fig. 5a
add(EX, "Fig. 5a", "fixed cutoff, exchangeable", "0.05",
    get(core, "e6_content_egress/exchangeable/fixed_threshold/mean"),
    "core e6_content_egress/exchangeable/fixed_threshold/mean")
add(EX, "Fig. 5a", "fixed cutoff, adaptive", "0.21",
    get(core, "e6_content_egress/adaptive/fixed_threshold/mean"),
    "core e6_content_egress/adaptive/fixed_threshold/mean")
# Table 5
T5 = {"lexical": ("0.083", "1.00", "0.835", "1.00"), "numeric": ("0.082", "0.62", "0.124", "1.00"),
      "structural": ("0.088", "0.09", "0.037", "0.068")}
for det, (ex_pt, ex_u, obf, nat) in T5.items():
    add(EX, "Table 5", f"{det} exchangeable pass-through", ex_pt,
        get(e7, f"exchangeable/single/{det}/mean"), f"core e7 exchangeable/single/{det}/mean")
    add(EX, "Table 5", f"{det} utility", ex_u, get(e7, f"exchangeable/single_utility/{det}/mean"),
        f"core e7 exchangeable/single_utility/{det}/mean")
    add(EX, "Table 5", f"{det} obfuscated pass-through", obf,
        get(e7, f"adaptive_obf/single/{det}/mean"), f"core e7 adaptive_obf/single/{det}/mean")
    add(EX, "Table 5", f"{det} evade-all pass-through", nat,
        get(e7, f"adaptive_evade_all/single/{det}/mean"),
        f"core e7 adaptive_evade_all/single/{det}/mean")
add(EX, "Table 5", "ensemble exchangeable pass-through", "0.082",
    get(e7, "exchangeable/ensemble/mean"), "core e7 exchangeable/ensemble/mean")
add(EX, "Table 5", "ensemble utility", "1.00", get(e7, "exchangeable/ensemble_utility/mean"),
    "core e7 exchangeable/ensemble_utility/mean")
add(EX, "Table 5", "ensemble obfuscated pass-through", "0.097",
    get(e7, "adaptive_obf/ensemble/mean"), "core e7 adaptive_obf/ensemble/mean")
add(EX, "Table 5", "ensemble evade-all pass-through", "1.00",
    get(e7, "adaptive_evade_all/ensemble/mean"), "core e7 adaptive_evade_all/ensemble/mean")
add(EX, "Table 5 caption", "largest CI half-width is at most 0.006", "yes",
    "yes" if max(ci_half(e7, [])) <= 0.006 else "no", "core e7_ensemble_egress/**/ci",
    exact=True)
add(EX, "Sect. 9.4", "ensemble cut against lexical, obfuscated", "8.6",
    get(e7, "adaptive_obf/single/lexical/mean") / get(e7, "adaptive_obf/ensemble/mean"),
    "core e7 (lexical / ensemble)")
add(EX, "Sect. 9.4, Table 7", "Mondrian study: marginal overall", "0.303",
    get(core, "e8_mondrian_shift/marginal/overall/mean"), "core e8 marginal/overall/mean")
add(EX, "Sect. 9.4", "Mondrian overall", "0.071",
    get(core, "e8_mondrian_shift/mondrian/overall/mean"), "core e8 mondrian/overall/mean")
# Sect. 9.5 and Fig. 6
for i, printed in [(1, "0.77"), (2, "0.41")]:
    add(EX, "Sect. 9.5, Fig. 6a", f"label noise rho={r1[i]['rho']}: utility", printed,
        r1[i]["utility_pac"], f"stress r1_label_noise/curve/{i}/utility_pac")
add(EX, "Sect. 9.5", "label noise rho=0.05: PAC pass-through", "0", r1[1]["passthrough_pac"],
    "stress r1_label_noise/curve/1/passthrough_pac")
add(EX, "Sect. 9.5, Table 6", "PAC rank at n_v=1280", "111", r2[-1]["pac_rank"],
    "stress r2_small_nv/curve/-1/pac_rank", exact=True)
add(EX, "Sect. 9.5, Table 6", "strict < over-corrects to", "0.040",
    get(stress, "r3_ties/det_admit_lt/mean"), "stress r3_ties/det_admit_lt/mean")
add(EX, "Sect. 9.5", "quantisation levels", "6", get(stress, "r3_ties/levels"),
    "stress r3_ties/levels", exact=True)
add(EX, "Sect. 9.5, Table 6", "miscalibration: conformal pass-through", "0.084",
    min(g["conformal_passthrough"] for g in r4), "stress r4_miscalibration/grid (min)")
add(EX, "Sect. 9.5, Table 6", "miscalibration: fixed cutoff, lowest", "0.005", min(fixed4),
    "stress r4_miscalibration/grid/*/fixed_passthrough (min)")
add(EX, "Sect. 9.5, Table 6", "miscalibration: fixed cutoff, highest", "0.185", max(fixed4),
    "stress r4_miscalibration/grid/*/fixed_passthrough (max)")
add(EX, "Sect. 9.5, Table 6", "miscalibration: fixed-cutoff spread (x)", "40",
    max(fixed4) / min(fixed4), "stress r4_miscalibration (max / min)")
add(EX, "Sect. 9.5, Table 6", "miscalibration: utility, lowest", "0.88",
    min(g["conformal_utility"] for g in r4), "stress r4_miscalibration (min utility)")
add(EX, "Sect. 9.5, Table 6", "miscalibration: utility, highest", "0.996",
    max(g["conformal_utility"] for g in r4), "stress r4_miscalibration (max utility)")
add(EX, "Sect. 9.5", "drift stream batches", "40", r5["T"], "stress r5_drift_rolling/T", exact=True)
add(EX, "Sect. 9.5", "drift threshold", "0.06", r5["drift_thresh"],
    "stress r5_drift_rolling/drift_thresh")
add(EX, "Sect. 9.5, Fig. 6c", "static utility", "0.89", get(r5, "static/utility/mean"),
    "stress r5 static/utility/mean")
add(EX, "Sect. 9.5, Fig. 6c", "rolling utility", "0.91", get(r5, "rolling/utility/mean"),
    "stress r5 rolling/utility/mean")
add(EX, "Sect. 9.5, Fig. 6c", "rolling pass-through", "0.08", get(r5, "rolling/passthrough/mean"),
    "stress r5 rolling/passthrough/mean")
add(EX, "Sect. 9.5", "recalibrations", "8.0", get(r5, "rolling/recalibrations/mean"),
    "stress r5 rolling/recalibrations/mean")
add(EX, "Sect. 9.5", "time per recalibration (ms)", "0.04", r5["calibration_ms_per_recal"],
    "stress r5 calibration_ms_per_recal", timing=True)
add(EX, "Sect. 9.5, Fig. 6c", "Mondrian pass-through", "0.076",
    get(r5, "mondrian/passthrough/mean"), "stress r5 mondrian/passthrough/mean")
add(EX, "Sect. 9.5, Fig. 6c", "Mondrian utility", "0.25", get(r5, "mondrian/utility/mean"),
    "stress r5 mondrian/utility/mean")
add(EX, "Sect. 9.5, Fig. 6d", "raw abstain rate (Monte Carlo model)", "0.225",
    get(r6, "abstain_rate_raw/mean"), "stress r6 abstain_rate_raw/mean")
add(EX, "Sect. 9.5, Fig. 6d", "autonomous completion (Monte Carlo model)", "0.52",
    get(r6, "completion_autonomous/mean"), "stress r6 completion_autonomous/mean")
add(EX, "Sect. 9.5, Fig. 6d", "completion with fallback (Monte Carlo model)", "1.00",
    get(r6, "completion_with_fallback/mean"), "stress r6 completion_with_fallback/mean")
add(EX, "Sect. 9.5, Fig. 6d", "extra steps (Monte Carlo model)", "2.2",
    get(r6, "recovery_latency_steps/mean"), "stress r6 recovery_latency_steps/mean")
add(EX, "Sect. 9.5", "unsafe explicit executions (Monte Carlo model)", "0.000",
    get(r6, "unsafe_explicit/mean"), "stress r6 unsafe_explicit/mean")
add(EX, "Sect. 9.5", "admitted latent violations (Monte Carlo model)", "0.095",
    get(r6, "unsafe_latent/mean"), "stress r6 unsafe_latent/mean")
for k, printed in [("restricted_retry", "0.34"), ("rollback_compensate", "0.33"),
                   ("human_escalation", "0.32")]:
    add(EX, "Sect. 9.5, Fig. 6d", f"fallback share {k} (Monte Carlo model)", printed,
        get(r6, f"fallback_mix/{k}/mean"), f"stress r6 fallback_mix/{k}/mean")
add(EX, "Sect. 9.5, Sect. 11.1", "automaton cost per action (us)", "0.75", SLOPE,
    "core e5_scalability (least-squares slope)", timing=True)
# Table 6 and Sect. 9.6
add(EX, "Table 6", "PAC mean pass-through, lowest alpha", "0.014",
    min(c["passthrough_pac"] for c in e2c), "core e2 curve/*/passthrough_pac (min)")
add(EX, "Table 6", "PAC mean pass-through, highest alpha", "0.277",
    max(c["passthrough_pac"] for c in e2c), "core e2 curve/*/passthrough_pac (max)")
add(EX, "Table 6", "PAC conservatism at alpha=0.02", "0.006",
    e2c[0]["passthrough"] - e2c[0]["passthrough_pac"], "core e2 curve/0")
add(EX, "Table 6", "PAC conservatism at alpha=0.30", "0.022",
    e2c[-1]["passthrough"] - e2c[-1]["passthrough_pac"], "core e2 curve/-1")
add(EX, "Table 6, Sect. 9.6", "marginal rank at n_v=1200", "120", int(np.floor(0.10 * 1201)),
    "floor(alpha (n_v + 1))", exact=True)
add(EX, "Table 6, Sect. 9.6", "PAC rank at n_v=1200", "103", _pac_rank(1200, 0.10, 0.05),
    "core._pac_rank(1200, 0.10, 0.05)", exact=True)
ix = [c["alpha"] for c in e2c].index(0.1)
add(EX, "Table 6, Sect. 9.6", "marginal draws sound at alpha=0.10 (%)", "53",
    pct(e2c[ix]["sound_frac_marginal"]), "core e2 curve (alpha=0.10)/sound_frac_marginal")
add(EX, "Table 6, Sect. 9.6", "PAC draws sound at alpha=0.10 (%)", "95",
    pct(e2c[ix]["sound_frac_pac"]), "core e2 curve (alpha=0.10)/sound_frac_pac")
add(EX, "Sect. 9.6", "PAC conservatism at alpha=0.10", "0.014",
    e2c[ix]["passthrough"] - e2c[ix]["passthrough_pac"], "core e2 curve (alpha=0.10)")
add(EX, "Table 6, Fig. 6b", "small n_v: PAC pass-through at n_v=20 (k'=0, all abstain)", "0.000",
    r2[0]["passthrough_pac"], "stress r2_small_nv/curve/0/passthrough_pac")
add(EX, "Table 6", "small n_v: PAC pass-through at n_v=1280", "0.087", r2[-1]["passthrough_pac"],
    "stress r2_small_nv/curve/-1/passthrough_pac")
add(EX, "Table 6", "small n_v: PAC utility at k'=0", "0.000", r2[0]["utility_pac"],
    "stress r2_small_nv/curve/0/utility_pac")
add(EX, "Table 6", "small n_v: PAC utility for k' >= 1, lowest", "0.996",
    min(c["utility_pac"] for c in r2 if c["pac_rank"] >= 1),
    "stress r2_small_nv/curve/*/utility_pac (min over k' >= 1)")
add(EX, "Table 6", "small n_v: PAC utility, highest", "1.000", max(c["utility_pac"] for c in r2),
    "stress r2_small_nv/curve/*/utility_pac (max)")
add(EX, "Sect. 9.6", "PAC rank at n_v=40", "1", r2[1]["pac_rank"],
    "stress r2_small_nv/curve/1/pac_rank", exact=True)
add(EX, "Sect. 9.6", "PAC sound fraction at n_v=40", "0.975", r2[1]["sound_frac_pac"],
    "stress r2_small_nv/curve/1/sound_frac_pac")
add(EX, "Table 6", "detector separation: pass-through at 1.0", "0.0996",
    e3r[0]["conformal_passthrough"], "core e3 robustness/0/conformal_passthrough")
add(EX, "Table 6", "detector separation: pass-through at 3.2", "0.0984",
    e3r[-1]["conformal_passthrough"], "core e3 robustness/-1/conformal_passthrough")
add(EX, "Table 6", "miscalibration: conformal pass-through, lowest", "0.0844",
    min(g["conformal_passthrough"] for g in r4), "stress r4 grid (min)")
add(EX, "Table 6", "miscalibration: conformal pass-through, highest", "0.0846",
    max(g["conformal_passthrough"] for g in r4), "stress r4 grid (max)")
add(EX, "Table 7", "row 1: RQ1 PAC pass-through at alpha=0.10", "0.086",
    e2c[ix]["passthrough_pac"], "core e2 curve (alpha=0.10)/passthrough_pac")
add(EX, "Table 7, Sect. 9.7", "scorer evolution: auto-recalibration", "0.086",
    get(r8, "auto/passthrough/mean"), "stress r8 auto/passthrough/mean")
add(EX, "Table 7, Sect. 9.7", "scorer evolution: locked profile", "0.026",
    get(r8, "locked/passthrough/mean"), "stress r8 locked/passthrough/mean")
add(EX, "Sect. 9.7", "auto recalibrations", "3.0", get(r8, "auto/recalibrations/mean"),
    "stress r8 auto/recalibrations/mean")
add(EX, "Table 7, Sect. 9.7", "adversarial switches without hysteresis", "47",
    get(r8, "adversarial_no_hysteresis/profile_switches/mean"),
    "stress r8 adversarial_no_hysteresis/profile_switches/mean")
add(EX, "Table 7, Sect. 9.7", "switches with hysteresis", "0",
    get(r8, "adversarial_hysteresis/profile_switches/mean"),
    "stress r8 adversarial_hysteresis/profile_switches/mean")
add(EX, "Sect. 9.7", "spurious recalibrations with hysteresis", "0",
    get(r8, "adversarial_hysteresis/recalibrations/mean"),
    "stress r8 adversarial_hysteresis/recalibrations/mean")
add(EX, "Sect. 9.7", "batches, versions, hold", "48,4,3",
    f"{r8['T']},{r8['n_versions']},{r8['hold']}", "stress r8 T/n_versions/hold", exact=True)
add(EX, "Sect. 9.7", "calibration traces and steps", "80,6",
    f"{stress['r7_sequential_dependence']['n_cal_traces']},{stress['r7_sequential_dependence']['steps']}",
    "stress r7 n_cal_traces/steps", exact=True)
add(EX, "Table 7, Sect. 9.7", "step-level PAC sound fraction at rho=0", "0.958",
    r7[0]["sound_frac_step_corr"], "stress r7 curve/0/sound_frac_step_corr")
add(EX, "Table 7, Sect. 9.7", "step-level PAC sound fraction at rho=0.99", "0.777",
    r7[-1]["sound_frac_step_corr"], "stress r7 curve/-1/sound_frac_step_corr")
add(EX, "Table 7, Sect. 9.7", "trace-level PAC sound fraction at rho=0.99", "0.978",
    r7[-1]["sound_frac_trace_corr"], "stress r7 curve/-1/sound_frac_trace_corr")
add(EX, "Sect. 9.7", "i.i.d. baseline sound fraction (approx.)", "0.96",
    float(np.mean([c["sound_frac_step_iid"] for c in r7])), "stress r7 curve/*/sound_frac_step_iid (mean)",
    tolerance=0.01)
add(EX, "Sect. 9.6", "degradation under content obfuscation (x)", "3.7",
    get(core, "e6_content_egress/adaptive/policyshield/mean")
    / get(core, "e6_content_egress/exchangeable/policyshield/mean"), "core e6 (adaptive / exchangeable)")
add(EX, "App. B", "distinct calibration violation scores, lowest (%)", "31", pct(APPB[0]),
    "content.build_content_pool, e6 seeds (recomputed)")
add(EX, "App. B", "distinct calibration violation scores, highest (%)", "36", pct(APPB[1]),
    "content.build_content_pool, e6 seeds (recomputed)")
add(EX, "App. B", "violation scores tied at the PAC threshold", "3-21", f"{APPB[2]}-{APPB[3]}",
    "content.build_content_pool, e6 seeds (recomputed)", exact=True)

# ---------------------------------------------------------------- evaluation
counts = {"PASS": 0, "FAIL": 0, "DEVIATION": 0, "INFO": 0}
per_paper = {CR: dict(counts), EX: dict(counts)}
current = None
md_paper, md_n = None, 0
for paper, loc, claim, printed, value, source, o in C:
    if paper != current and not args.markdown:
        current = paper
        title = ("camera-ready (paper/camera-ready.pdf)" if paper == CR
                 else "extended version (paper/extended.pdf), headline claims and tables")
        print(f"== {title}")
    if o.get("exact"):
        ok = str(value) == printed if isinstance(value, str) else float(value) == float(printed)
    else:
        t = o.get("tolerance", tol(printed))
        ok = abs(float(value) - float(printed)) <= t
    if ok:
        status = "PASS"
    elif o.get("timing") and REGENERATED:
        status = "INFO"
    elif o.get("kind") == "deviation":
        status = "DEVIATION"
    elif o.get("regen") == "deviation" and REGENERATED:
        status = "DEVIATION"
    else:
        status = "FAIL"
    counts[status] += 1
    per_paper[paper][status] += 1
    shown = value if isinstance(value, str) else f"{float(value):.4f}".rstrip("0").rstrip(".")
    if args.markdown:
        if paper != md_paper:
            md_paper, md_n = paper, 0
            print(f"\n| # | Location | Claim | Paper | Artifact | Source | Status |")
            print("|---|---|---|---|---|---|---|")
        md_n += 1
        print(f"| {paper}-{md_n} | {loc} | {claim} | {printed} | {shown} | `{source}` | {status} |")
        continue
    print(f"  [{status:9s}] {loc:28s} {claim:62s} paper {printed:>10s} | artifact {shown:>10s} | {source}")

if args.markdown:
    sys.exit(0)
print()
for paper, name in ((CR, "camera-ready"), (EX, "extended")):
    c = per_paper[paper]
    print(f"{name}: {sum(c.values())} claims, {c['PASS']} pass, {c['FAIL']} fail, "
          f"{c['DEVIATION']} deviations, {c['INFO']} timing (info)")
print(f"{sum(counts.values())} claims: {counts['PASS']} pass, {counts['FAIL']} fail, "
      f"{counts['DEVIATION']} documented deviations, {counts['INFO']} timing values (info only)")
if counts["DEVIATION"]:
    print("Deviations are listed with a proposed correction in CLAIM_MATRIX.md.")
ok = gate_ok and counts["FAIL"] == 0
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
