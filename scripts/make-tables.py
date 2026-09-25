#!/usr/bin/env python3
"""Print the results tables of both papers from the result files.

Usage: python3 scripts/make-tables.py [--results DIR]

Tables printed, with the numbering of the current PDFs:
  camera-ready Table 1 (= extended Table 3)  six-model proposer ladder, from
                                             llm_summary_*.json
  extended Table 4                           AgentDojo head-to-head, from
                                             agentdojo_results.json
  extended Table 5                           detectors and max-ensemble, from
                                             core_results.json (e7_ensemble_egress)
  extended Table 9                           AgentDojo per-task benign completion
Values are rounded the way the papers print them. The script only reads files.
"""
import argparse
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--results", default=str(ROOT / "deon" / "results"))
RES = Path(ap.parse_args().results)

SIZES = {"gemma2:2b": "2B", "llama3.2:3b": "3B", "qwen2.5-coder:7b": "7B",
         "qwen2.5-coder:32b": "32B", "command-r:35b": "35B", "mixtral:8x7b": "47B"}
ladder = {}
for fp in glob.glob(str(RES / "llm_summary_*.json")):
    d = json.loads(Path(fp).read_text())
    ladder[d["model"]] = d

print("Camera-ready Table 1 / extended Table 3: six-model proposer ladder")
print(f"{'Proposer':20s} {'size':>5s} | benign success (%): {'unguarded':>9s} {'Deon':>5s} |"
      f" ASR (%): {'unguarded':>9s} {'Deon':>5s}")
for model, size in SIZES.items():
    m = ladder[model]
    print(f"{model:20s} {size:>5s} | {'':20s}{m['benign_success_unguarded']:9.0f} "
          f"{m['benign_success_policyshield']:5.0f} | {'':9s}{m['asr_unguarded']:9.0f} "
          f"{m['asr_policyshield']:5.0f}")
print("(30 benign and 30 attack runs per model: 5 tasks x", ladder["gemma2:2b"]["reps"], "reps)")

ad = json.loads((RES / "agentdojo_results.json").read_text())
names = [("none", "Undefended"), ("promptguard", "Detector: Meta Prompt-Guard-86M"),
         ("spotlighting", "Spotlighting (prompt delimiting)"),
         ("repeat_user_prompt", "Repeat-prompt (re-assert)"),
         ("testsavant_detector", "Detector: TestSavant-large"),
         ("pi_detector", "Detector: ProtectAI DeBERTa"),
         ("deepset_detector", "Detector: deepset DeBERTa"),
         ("tool_filter", "Tool-filter (LLM tool-pruning)"), ("deon", "Deon (DPA guard)")]
print()
print(f"Extended Table 4: AgentDojo banking, {ad['model']}, "
      f"{ad['defenses']['deon']['n_attack_combos']} task-injection pairs")
print(f"{'Defence':34s} {'benign util. (%)':>17s} {'ASR (%)':>8s}")
for key, label in names:
    d = ad["defenses"][key]
    # The paper prints one decimal and rounds 31.25 down to 31.2 (round half to even).
    print(f"{label:34s} {100 * d['benign_utility']:17.1f} {100 * d['asr_under_injection']:8.1f}")

e7 = json.loads((RES / "core_results.json").read_text())["e7_ensemble_egress"]
print()
print("Extended Table 5: leak pass-through of three detectors and their max-ensemble "
      f"(alpha={e7['alpha']}, {e7['seeds']} seeds)")
print(f"{'Detector':16s} {'exch. pass':>10s} {'utility':>8s} {'obfusc.':>8s} {'evade-all':>9s}")
for det in e7["detectors"]:
    print(f"{det:16s} {e7['exchangeable']['single'][det]['mean']:10.3f} "
          f"{e7['exchangeable']['single_utility'][det]['mean']:8.2f} "
          f"{e7['adaptive_obf']['single'][det]['mean']:8.3f} "
          f"{e7['adaptive_evade_all']['single'][det]['mean']:9.3f}")
print(f"{'ensemble (max)':16s} {e7['exchangeable']['ensemble']['mean']:10.3f} "
      f"{e7['exchangeable']['ensemble_utility']['mean']:8.2f} "
      f"{e7['adaptive_obf']['ensemble']['mean']:8.3f} "
      f"{e7['adaptive_evade_all']['ensemble']['mean']:9.3f}")

print()
print("Extended Table 9: AgentDojo per-task benign completion (x = completed)")
none_t = ad["defenses"]["none"]["utility_per_task"]
deon_t = ad["defenses"]["deon"]["utility_per_task"]
for t in ad["user_tasks"]:
    print(f"{t:14s} undefended {'x' if none_t[t] else '-'}   Deon {'x' if deon_t[t] else '-'}")
