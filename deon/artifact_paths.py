"""Locations of the result and figure directories used by every script.

The artifact is meant to run from a stand-alone checkout of this directory. The
defaults are results/ and figures/ next to this file. The environment variables
POLICYSHIELD_RESULTS and POLICYSHIELD_FIGURES redirect them, which is useful when a
run must not touch the committed result files. (The directory and the variable names
keep the former project name policyshield. The framework in the paper is called
Deon.) The module has no counterpart in the paper.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.environ.get("POLICYSHIELD_RESULTS", os.path.join(HERE, "results"))
FIGURES = os.environ.get("POLICYSHIELD_FIGURES", os.path.join(HERE, "figures"))


def ensure_dir(path):
    """Create `path` if needed and return it, which lets callers wrap a path inline."""
    os.makedirs(path, exist_ok=True)
    return path
