#!/usr/bin/env python3
"""Merge extra AgentDojo defense runs into results/agentdojo_results.json.

Usage: python3 _merge_agentdojo.py extra1.json [extra2.json ...]

agentdojo_deon.py can be run once per subset of defenses, for example when a slow
detector is added after the main sweep. This helper folds such a file back into the
base result file that Sect. 7 (RQ2, external test on the AgentDojo banking suite) and
check_results.py read. An extra file is accepted only if its model, suite and attack
name equal those of the base file, otherwise it is skipped with a message. Every
defense in an accepted file is copied into the base file, and a defense with the same
name replaces the base entry. The internal "_complete" resume flag is removed from
all entries before the base file is rewritten. The script then prints the merged
head-to-head table (benign utility and attack success rate per defense).

The script does no sampling and needs neither Ollama nor AgentDojo.
"""
import json, sys, pathlib
from artifact_paths import RESULTS

base_path = pathlib.Path(RESULTS) / "agentdojo_results.json"
base = json.loads(base_path.read_text())

for extra in sys.argv[1:]:
    e = json.loads(pathlib.Path(extra).read_text())
    if (e.get("model"), e.get("suite"), e.get("attack")) != (
            base.get("model"), base.get("suite"), base.get("attack")):
        print(f"[skip] {extra}: model/suite/attack mismatch "
              f"({e.get('model')},{e.get('suite')},{e.get('attack')}) "
              f"vs base ({base.get('model')},{base.get('suite')},{base.get('attack')})")
        continue
    for name, v in e.get("defenses", {}).items():
        v.pop("_complete", None)
        base["defenses"][name] = v
        print(f"[merge] {name}: util={v.get('benign_utility'):.4f} "
              f"ASR={v.get('asr_under_injection'):.4f} "
              f"(n_benign={v.get('n_benign')}, n_combos={v.get('n_attack_combos')})")

for v in base["defenses"].values():
    v.pop("_complete", None)
base_path.write_text(json.dumps(base, indent=2))
print("\nwrote", base_path)
print(f"\n{'defense':22} {'benign_util':>11} {'ASR':>8} {'n_benign':>9} {'n_combos':>9}")
for name, v in base["defenses"].items():
    print(f"{name:22} {v.get('benign_utility'):>11.4f} {v.get('asr_under_injection'):>8.4f} "
          f"{v.get('n_benign'):>9} {v.get('n_attack_combos'):>9}")
