"""Figures of the extended version that come from core_results.json and the ladder files.

The script reads results/core_results.json and results/llm_summary_*.json and computes
nothing beyond a linear fit for the scalability panel. It writes into figures/
(redirect with POLICYSHIELD_FIGURES). The E-labels are those of experiments_core.py
and the research questions are those of the paper.

  fig_monitor.pdf   RQ1. Recall of the automaton per violation class on the 900-trace
                    monitor suite (E1). Used by the extended version.
  fig_coverage.pdf  RQ1. Mean pass-through against the target alpha for the marginal
                    and the PAC threshold, with the safe region below the diagonal
                    (E2). Used by the extended version.
  fig_egress.pdf    RQ3. Leak pass-through of the automaton alone, Deon and a fixed
                    cutoff under exchangeable and adaptive leaks (E6), and the target
                    control against detector quality (E3). Used by the extended
                    version.
  fig_guard.pdf     RQ1 detector-quality sweep (E3) and the monitor time against trace
                    length with a linear fit (E5). Written for completeness. Neither
                    manuscript source includes this file.
  fig_attack.pdf    RQ2. Layer decomposition on the mixed stream (E4) and the
                    six-model proposer ladder (llm_summary files, Table 1). Written for
                    completeness. Neither manuscript source includes this file.

The camera-ready's own results figure is made by make_camera_figures.py and the stress
tests by make_stress_figures.py. Only numpy and matplotlib are needed.
"""
import json, os, glob
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from artifact_paths import FIGURES, RESULTS, ensure_dir

mpl.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"], "font.size": 11,
    "axes.linewidth": 0.8, "axes.grid": True, "grid.color": "0.85",
    "grid.linewidth": 0.6, "figure.dpi": 200,
})
C = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
     "red": "#D55E00", "purple": "#CC79A7", "gray": "#7A7A7A"}

HERE = os.path.dirname(os.path.abspath(__file__))
RES = ensure_dir(RESULTS)
FIG = ensure_dir(FIGURES)
R = json.load(open(os.path.join(RES, "core_results.json")))


# fig_monitor.pdf: per-class recall of the automaton (E1, RQ1).
e1 = R["e1_monitor_soundness"]
classes = list(e1["per_class_recall"].keys())
recall = np.array([e1["per_class_recall"][k] for k in classes])

fig, ax = plt.subplots(figsize=(3.55, 1.8))
y = np.arange(len(classes))
ax.barh(y, recall, color=C["blue"], edgecolor="black", linewidth=0.5)
ax.set_yticks(y)
ax.set_yticklabels(classes, fontsize=7.5)
ax.set_xlabel("Recall (%)")
ax.set_xlim(0, 105)
ax.set_xticks([0, 50, 100])
ax.set_title(f"900 traces: {e1['accuracy']:.1f}% accuracy", fontsize=9)
for yy, v in zip(y, recall):
    ax.text(min(v + 1.2, 104), yy, f"{v:.0f}", va="center", fontsize=7.5)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_monitor.pdf"), bbox_inches="tight")
plt.close(fig)


# fig_coverage.pdf: pass-through against alpha (E2, RQ1).
cur = R["e2_conformal_coverage"]["curve"]
a = np.array([c["alpha"] for c in cur])
pm = np.array([c["passthrough"] for c in cur])
pm_sd = np.array([c["passthrough_sd"] for c in cur])
pp = np.array([c["passthrough_pac"] for c in cur])
fig, ax = plt.subplots(figsize=(3.55, 1.8))
lim = float(a.max()) * 1.08
ax.plot([0, lim], [0, lim], color=C["gray"], ls="--", lw=1.0, label="$y=x$ (target $\\alpha$)")
# The safe region is pass-through <= alpha, which lies below the diagonal.
ax.fill_between([0, lim], 0, [0, lim], color=C["green"], alpha=0.08)
ax.errorbar(a, pm, yerr=pm_sd, fmt="o", color=C["blue"], ms=5, capsize=2.5,
            mec="black", mew=0.5, label="marginal (mean)")
ax.plot(a, pp, "s", color=C["orange"], ms=4.5, mec="black", mew=0.5,
        label="PAC ($\\delta{=}0.05$)")
ax.set_xlabel("Target level $\\alpha$")
ax.set_ylabel("Violation pass-through", fontsize=8)
ax.set_xlim(0, lim); ax.set_ylim(0, lim)
ax.text(0.68 * lim, 0.10 * lim, "safe\nregion",
        fontsize=7, color=C["green"], ha="center")
ax.legend(fontsize=6.6, loc="upper left", frameon=True)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_coverage.pdf"), bbox_inches="tight")
plt.close(fig)


# fig_guard.pdf: detector-quality sweep (E3) and monitor time (E5).
rob = R["e3_risk_utility"]["robustness"]
sep = np.array([c["separation"] for c in rob])
cpt = np.array([c["conformal_passthrough"] for c in rob])
fpt = np.array([c["fixed_passthrough"] for c in rob])
a0 = R["e3_risk_utility"]["alpha0"]
sc = R["e5_scalability"]
L = np.array([s["length"] for s in sc])
us = np.array([s["us_mean"] for s in sc])
us_sd = np.array([s["us_sd"] for s in sc])

fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.6, 2.9))
axa.axhline(a0, color=C["gray"], ls="--", lw=1.0, label=f"target $\\alpha{{=}}{a0:g}$")
axa.plot(sep, cpt, "-o", color=C["blue"], ms=4.5, label="conformal (PolicyShield)")
axa.plot(sep, fpt, "-s", color=C["red"], ms=4.5, label="fixed cutoff (w/o calib.)")
axa.set_xlabel("Detector quality (class separation)")
axa.set_ylabel("Violation pass-through")
axa.set_title("(a) Target control vs detector drift", fontsize=9.5)
axa.legend(fontsize=7.5, loc="upper right")

axb.plot(L, us, "-o", color=C["blue"], ms=4)
axb.fill_between(L, us - us_sd, us + us_sd, color=C["blue"], alpha=0.15)
b1, b0 = np.polyfit(L, us, 1)
r2 = np.corrcoef(L, us)[0, 1] ** 2
axb.plot(L, b1 * L + b0, ls=":", color=C["red"], lw=1.0,
         label=f"linear fit ($R^2$={r2:.3f})")
axb.set_xlabel("Trace length (\\# actions)")
axb.set_ylabel("Monitor time ($\\mu$s)")
axb.set_title("(b) Runtime-monitor scalability", fontsize=9.5)
axb.legend(fontsize=8, loc="upper left")
for ax in (axa, axb):
    ax.spines["top"].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_guard.pdf"), bbox_inches="tight")
plt.close(fig)


# fig_attack.pdf: mixed-stream layers (E4) and the proposer ladder (Table 1, RQ2).
e4 = R["e4_attack_synth"]
lad = []
for fp in sorted(glob.glob(os.path.join(RES, "llm_summary_*.json"))):
    try:
        lad.append(json.load(open(fp)))
    except Exception:
        pass
# Order the ladder by model size, using the fixed list below.
order = ["gemma2_2b", "llama3.2_3b", "qwen2.5-coder_7b", "command-r_35b",
         "qwen2.5-coder_32b", "mixtral_8x7b"]
def _key(d):
    s = d["model"].replace(":", "_")
    return order.index(s) if s in order else 99
lad.sort(key=_key)

if lad:
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.6, 2.9),
                                   gridspec_kw={"width_ratios": [1, 1.5]})
else:
    fig, axa = plt.subplots(figsize=(3.3, 2.9)); axb = None

# (a) The three layers on the synthetic mixed stream.
labels = ["unguarded", "DPA\nonly", "Policy-\nShield"]
vals = [100 * e4["unguarded_asr"], 100 * e4["dpa_only_asr"], 100 * e4["policyshield_asr"]]
bars = axa.bar(labels, vals, color=[C["red"], C["orange"], C["green"]],
               edgecolor="black", linewidth=0.5)
axa.axhline(100 * e4["alpha"], color=C["gray"], ls="--", lw=1.0)
axa.set_ylabel("Attack success rate (\\%)")
axa.set_title("(a) Layered defence (synthetic)", fontsize=9.5)
for b, v in zip(bars, vals):
    axa.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}", ha="center", fontsize=8)
axa.set_ylim(0, 108)

# (b) The proposer ladder.
if lad and axb is not None:
    names = [d["model"] for d in lad]
    ung = [d["asr_unguarded"] for d in lad]
    ps = [d["asr_policyshield"] for d in lad]
    x = np.arange(len(names)); w = 0.38
    axb.bar(x - w / 2, ung, w, color=C["red"], edgecolor="black", linewidth=0.5,
            label="unguarded")
    axb.bar(x + w / 2, ps, w, color=C["green"], edgecolor="black", linewidth=0.5,
            label="PolicyShield")
    axb.set_xticks(x)
    axb.set_xticklabels([n.replace("qwen2.5-coder", "qwen") for n in names],
                        rotation=30, ha="right", fontsize=7)
    axb.set_ylabel("Attack success rate (\\%)")
    axb.set_title("(b) Proposer ladder under attack (measured)", fontsize=9.5)
    axb.legend(fontsize=8, loc="upper right")
    axb.set_ylim(0, 108)
    axb.spines["top"].set_visible(False)
axa.spines["top"].set_visible(False); axa.spines["right"].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_attack.pdf"), bbox_inches="tight")
plt.close(fig)

# fig_egress.pdf: content egress (E6, RQ3) and target control against detector quality (E3).
e6 = R["e6_content_egress"]
rob = R["e3_risk_utility"]["robustness"]
alpha = e6["alpha"]

fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.5, 2.25))

# (a) Leak pass-through by guard, exchangeable against adaptive leaks.
mlabels = ["DPA-only", "Deon", "fixed"]
mkeys = ["dpa_only", "policyshield", "fixed_threshold"]
exch = [e6["exchangeable"][k]["mean"] for k in mkeys]
adap = [e6["adaptive"][k]["mean"] for k in mkeys]
xb = np.arange(len(mlabels)); w = 0.38
axa.bar(xb - w/2, exch, w, label="exchangeable", color=C["blue"])
axa.bar(xb + w/2, adap, w, label="adaptive", color=C["red"])
for xi, (e, a) in enumerate(zip(exch, adap)):
    axa.text(xi - w/2, e + 0.03, f"{e:.2f}", ha="center", fontsize=7)
    axa.text(xi + w/2, a + 0.03, f"{a:.2f}", ha="center", fontsize=7)
axa.axhline(alpha, ls="--", lw=1.0, color=C["gray"])
axa.text(2.5, alpha + 0.02, r"$\alpha$", color=C["gray"], fontsize=10)
axa.set_xticks(xb); axa.set_xticklabels(mlabels, fontsize=9)
axa.set_ylabel("leak pass-through"); axa.set_ylim(0, 1.15)
legend_shift = axa.transAxes + mtransforms.ScaledTranslation(
    10 / 72, 0, fig.dpi_scale_trans)
axa.legend(fontsize=8, frameon=False, loc="upper center",
           bbox_to_anchor=(0.5, 1.0), bbox_transform=legend_shift)
axa.set_title("(a) content-egress", fontsize=9.5)
axa.spines["top"].set_visible(False); axa.spines["right"].set_visible(False)

# (b) Pass-through against detector quality for the calibrated threshold and a fixed cutoff.
sep = [r["separation"] for r in rob]
conf = [r["conformal_passthrough"] for r in rob]
fx = [r["fixed_passthrough"] for r in rob]
axb.plot(sep, conf, "o-", color=C["blue"], label="Deon (conformal)")
axb.plot(sep, fx, "s--", color=C["orange"], label="fixed cutoff")
axb.axhline(alpha, ls="--", lw=1.0, color=C["gray"])
axb.text(sep[0], alpha + 0.013, r"$\alpha$", color=C["gray"], fontsize=9)
axb.set_xlabel("detector separation (quality)")
axb.set_ylabel("leak pass-through"); axb.set_ylim(-0.01, 0.19)
axb.legend(fontsize=8, frameon=False, loc="upper right")
axb.set_title("(b) target control", fontsize=9.5)
axb.spines["top"].set_visible(False); axb.spines["right"].set_visible(False)

fig.tight_layout()
fig.subplots_adjust(wspace=0.48)
fig.savefig(os.path.join(FIG, "fig_egress.pdf"), bbox_inches="tight")
plt.close(fig)

print("wrote fig_monitor.pdf, fig_coverage.pdf, fig_guard.pdf, fig_attack.pdf, fig_egress.pdf")
print(f"  scalability R^2 = {r2:.3f}; ladder models = {[d['model'] for d in lad]}")
