"""Stress-test figures of the extended version, from results/stress_results.json.

Writes figures/fig_rq5.pdf and figures/fig_rq6.pdf (redirect with
POLICYSHIELD_FIGURES). The script only reads the JSON written by experiments_stress.py
and applies no computation to it. The R-labels are those of that file, and the
research questions are those of the extended version.

  fig_rq5.pdf   RQ5, four panels. (a) label noise (R1), (b) small numbers of
                calibration violations (R2), (c) benign drift with static, rolling
                and rolling-plus-Mondrian calibration (R5), (d) abstention recovery
                (R6). Backs the label-noise and small-n_v paragraphs and the drift
                and recovery paragraphs of the RQ5 subsection.
  fig_rq6.pdf   RQ6, two panels. (a) PAC sound fraction against the intra-trace
                correlation (R7), (b) scorer evolution and adversarial oscillation
                (R8). Backs the two paragraphs of the RQ6 subsection.

None of these figures appears in the camera-ready. The style follows
make_real_figures.py. Only numpy and matplotlib are needed.
"""
import json, os
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
R = json.load(open(os.path.join(RES, "stress_results.json")))
alpha = R["r1_label_noise"]["alpha"]

r1 = R["r1_label_noise"]["curve"]
rho = np.array([c["rho"] for c in r1])
pt1 = np.array([c["passthrough_pac"] for c in r1])
ut1 = np.array([c["utility_pac"] for c in r1])
r2 = R["r2_small_nv"]["curve"]
nv = np.array([c["n_v"] for c in r2])
pt_m = np.array([c["passthrough_marginal"] for c in r2])
pt_p = np.array([c["passthrough_pac"] for c in r2])
sf_p = np.array([c["sound_frac_pac"] for c in r2])
r5 = R["r5_drift_rolling"]
r6 = R["r6_abstention_recovery"]

fig, axes = plt.subplots(2, 2, figsize=(6.6, 3.4))
(axa, axb), (axc, axd) = axes

# (a) R1: label noise.
axa.axhline(alpha, ls="--", lw=0.9, color=C["gray"])
axa.text(rho[-1], alpha + 0.03, r"$\alpha$", color=C["gray"], fontsize=8, ha="right")
axa.plot(rho, pt1, "o-", color=C["blue"], ms=4, label="pass-through")
axa.plot(rho, ut1, "s--", color=C["orange"], ms=4, label="utility")
axa.set_xlabel("label-noise $\\rho$", fontsize=8.5)
axa.set_ylim(-0.03, 1.08)
axa.set_title("(a) Label noise (PAC)", fontsize=9)
axa.legend(fontsize=6.6, loc="center right", frameon=True)

# (b) R2: few calibration violations. The right axis shows the PAC sound fraction.
axb.axhline(alpha, ls="--", lw=0.9, color=C["gray"])
axb.text(nv[0], alpha + 0.005, r"$\alpha$", color=C["gray"], fontsize=8)
axb.semilogx(nv, pt_m, "o-", color=C["red"], ms=4, label="marginal")
axb.semilogx(nv, pt_p, "s-", color=C["blue"], ms=4, label="PAC")
axb.set_xlabel("calib. violations $n_v$", fontsize=8.5)
axb.set_ylim(0, 0.14)
axb.set_title("(b) Small-$n_v$", fontsize=9)
axb.legend(fontsize=6.6, loc="lower right", frameon=True)
ax2 = axb.twinx()
ax2.semilogx(nv, sf_p, "^:", color=C["green"], ms=3.5)
ax2.axhline(1 - R["r2_small_nv"]["delta"], ls=":", lw=0.7, color=C["green"])
ax2.set_ylabel("sound-frac", color=C["green"], fontsize=7)
ax2.set_ylim(0.8, 1.02)
ax2.tick_params(axis="y", labelcolor=C["green"], labelsize=6)
ax2.grid(False)

# (c) R5: benign drift with rolling recalibration.
regimes = ["static", "rolling", "mondrian"]
labels = ["static", "rolling", "roll+\nMond."]
pt = [r5[k]["passthrough"]["mean"] for k in regimes]
ut = [r5[k]["utility"]["mean"] for k in regimes]
x = np.arange(len(regimes)); w = 0.38
axc.bar(x - w / 2, pt, w, color=C["blue"], label="pass-thru")
axc.bar(x + w / 2, ut, w, color=C["orange"], label="utility")
for xs, vals in ((x - w / 2, pt), (x + w / 2, ut)):
    for xx, vv in zip(xs, vals):
        axc.text(xx, vv + 0.025, f"{vv:.2f}", ha="center", va="bottom",
                 fontsize=6.3)
axc.axhline(alpha, ls="--", lw=0.9, color=C["gray"])
alpha_shift = mtransforms.ScaledTranslation(5 / 72, 0, fig.dpi_scale_trans)
axc.text(x[-1] + 0.33, alpha + 0.02, r"$\alpha$", color=C["gray"], fontsize=8,
         transform=axc.transData + alpha_shift)
axc.set_xticks(x); axc.set_xticklabels(labels, fontsize=7.5)
axc.set_ylim(0, 1.08)
axc.set_title("(c) Benign drift + recal.", fontsize=9)
axc.legend(fontsize=6.6, loc="upper center", bbox_to_anchor=(0.5, -0.27),
           ncol=2, frameon=True, borderaxespad=0.0)

# (d) R6: abstention recovery. The first bar is task completion and the second the fallback mix.
comp_a = r6["completion_autonomous"]["mean"]
comp_f = r6["completion_with_fallback"]["mean"]
fm = r6["fallback_mix"]
mix = [fm["restricted_retry"]["mean"], fm["rollback_compensate"]["mean"],
       fm["human_escalation"]["mean"]]
axd.bar([0], [comp_a], 0.55, color=C["green"], label="autonomous")
axd.bar([0], [comp_f - comp_a], 0.55, bottom=[comp_a], color=C["blue"], label="via fallback")
bottom = 0.0
for v, col, lb in zip(mix, [C["orange"], C["purple"], C["red"]],
                      ["restrict", "rollback", "escalate"]):
    axd.bar([1], [v], 0.55, bottom=[bottom], color=col, label=lb)
    bottom += v
axd.set_xticks([0, 1]); axd.set_xticklabels(["completion", "fb-mix"], fontsize=7.5)
axd.set_ylim(0, 1.12)
axd.set_title(f"(d) Abstain recovery ({r6['recovery_latency_steps']['mean']:.1f} steps)",
              fontsize=8.5)
axd.legend(fontsize=5.8, loc="upper center", bbox_to_anchor=(0.5, -0.27),
           ncol=3, frameon=True, borderaxespad=0.0)

for ax in (axa, axb, axc, axd):
    ax.spines["top"].set_visible(False)
for ax in (axa, axc, axd):
    ax.spines["right"].set_visible(False)
fig.tight_layout(pad=0.4, rect=(0, 0.08, 1, 1))
fig.subplots_adjust(wspace=0.48)
fig.savefig(os.path.join(FIG, "fig_rq5.pdf"), bbox_inches="tight")
plt.close(fig)
print("wrote fig_rq5.pdf")

# fig_rq6.pdf
r7 = R["r7_sequential_dependence"]["curve"]
r8 = R["r8_scorer_evolution"]
delta = R["r7_sequential_dependence"]["delta"]
rho = np.array([c["rho"] for c in r7])
sf_iid = np.array([c["sound_frac_step_iid"] for c in r7])
sf_scorr = np.array([c["sound_frac_step_corr"] for c in r7])
sf_tcorr = np.array([c["sound_frac_trace_corr"] for c in r7])

fig2, (ax7, ax8) = plt.subplots(1, 2, figsize=(6.6, 2.35))

# (a) R7: PAC sound fraction against the correlation inside a trace.
ax7.axhline(1 - delta, ls="--", lw=0.9, color=C["gray"])
ax7.text(rho[0], 1 - delta + 0.004, r"$1-\delta$", color=C["gray"], fontsize=7.5)
ax7.plot(rho, sf_iid, "o-", color=C["green"], ms=4, label="i.i.d. steps")
ax7.plot(rho, sf_scorr, "s-", color=C["red"], ms=4, label="step-level (corr.)")
ax7.plot(rho, sf_tcorr, "^-", color=C["blue"], ms=4, label="trace-level (fix)")
ax7.set_xlabel("intra-trace correlation $\\rho$", fontsize=8.5)
ax7.set_ylabel("PAC sound-fraction", fontsize=8.5)
ax7.set_ylim(0.72, 1.01)
ax7.set_title("(a) Inter-step dependence", fontsize=9)
ax7.legend(fontsize=6.4, loc="lower left", frameon=True)

# (b) R8: pass-through under each scorer-evolution policy, annotated with recalibrations or profile switches.
policies = ["locked", "auto", "adversarial_no_hysteresis", "adversarial_hysteresis"]
labels = ["locked", "auto", "adv\n(no hyst.)", "adv\n(+hyst.)"]
pt = [r8[k]["passthrough"]["mean"] for k in policies]
sw = [0.0, r8["auto"]["recalibrations"]["mean"],
      r8["adversarial_no_hysteresis"]["profile_switches"]["mean"],
      r8["adversarial_hysteresis"]["profile_switches"]["mean"]]
cols = [C["gray"], C["green"], C["red"], C["blue"]]
x = np.arange(len(policies))
ax8.axhline(R["r8_scorer_evolution"]["alpha"], ls="--", lw=0.9, color=C["gray"])
ax8.text(x[0] - 0.4, R["r8_scorer_evolution"]["alpha"] + 0.004, r"$\alpha$",
         color=C["gray"], fontsize=8)
ax8.bar(x, pt, 0.6, color=cols)
for xi, s in zip(x, sw):
    tag = "0 sw." if s == 0 else (f"{int(round(s))} sw." if xi >= 2 else f"{int(round(s))} rec.")
    ax8.text(xi, pt[xi] + 0.004, tag, ha="center", fontsize=6.2, color="0.25")
ax8.set_xticks(x); ax8.set_xticklabels(labels, fontsize=7.2)
ax8.set_ylabel("leak pass-through", fontsize=8.5)
ax8.set_ylim(0, 0.13)
ax8.set_title("(b) Scorer evolution / oscillation", fontsize=9)

for ax in (ax7, ax8):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
fig2.tight_layout(pad=0.4)
fig2.subplots_adjust(wspace=0.48)
fig2.savefig(os.path.join(FIG, "fig_rq6.pdf"), bbox_inches="tight")
plt.close(fig2)
print("wrote fig_rq6.pdf")
