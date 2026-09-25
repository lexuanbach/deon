#!/usr/bin/env python3
"""Compare regenerated result files with the committed ones.

Usage: python3 scripts/compare-results.py COMMITTED_DIR REGENERATED_DIR

Both folders hold core_results.json and stress_results.json. The script walks both JSON
trees and prints every value that differs. Wall-clock timing keys are skipped because
they depend on the host (the e5_scalability timings and
r5_drift_rolling/calibration_ms_per_recal).

With the released code every other value is expected to match bit for bit.
`stress_results.json` was regenerated with the released code for this release. KNOWN
lists keys that are allowed to differ, and it is empty.
Every difference outside KNOWN is labelled UNEXPECTED and makes the script exit with
status 1.
"""
import json
import sys
from pathlib import Path

TIMING = ("/e5_scalability", "/r5_drift_rolling/calibration_ms_per_recal")
KNOWN = ()   # key prefixes that may differ. None in this release

if len(sys.argv) != 3:
    sys.exit(__doc__)
old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])
counts = {"KNOWN": 0, "UNEXPECTED": 0}


def walk(a, b, path):
    if path.startswith(TIMING):
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                report(f"{path}/{k}", a.get(k, "<missing>"), b.get(k, "<missing>"))
            else:
                walk(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]")
    elif a != b:
        report(path, a, b)


def report(path, a, b):
    tag = "KNOWN" if KNOWN and path.startswith(KNOWN) else "UNEXPECTED"
    counts[tag] += 1
    print(f"  {tag:10s} {path}: committed {a}, regenerated {b}")


for name in ("core_results.json", "stress_results.json"):
    print(f"== {name}")
    with open(old_dir / name) as f:
        old = json.load(f)
    with open(new_dir / name) as f:
        new = json.load(f)
    walk(old, new, "")

print()
print(f"{counts['KNOWN']} known differences, {counts['UNEXPECTED']} unexpected differences "
      "(timing keys skipped)")
sys.exit(1 if counts["UNEXPECTED"] else 0)
