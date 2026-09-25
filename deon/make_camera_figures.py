"""Fig. 3 of the camera-ready paper: three panels, drawn from the committed results.

Writes figures/fig_results.pdf (redirect with POLICYSHIELD_FIGURES). The figure is one
row of three panels at the final printed size, with the LNCS text width of 12.2 cm and
all text at least 7 pt. It reads results/core_results.json and computes nothing beyond
a factor of 100 for percentages.

  (a) RQ1. For each target alpha, the share of the 300 calibration draws whose
      violation pass-through is at most alpha, for marginal and for exact-PAC
      calibration, against the 1 - delta target. Source: key e2_conformal_coverage.
      Backs the statement of Sect. 7 that about half of the marginal draws miss the
      target while exact-PAC meets it.
  (b) RQ3. Leak pass-through of the automaton alone and of Deon on content egress,
      under exchangeable and adaptive obfuscated leaks. Source: e6_content_egress.
      Backs Cor. 1(b) and the 0.089 to 0.328 result.
  (c) Hardening. The lexical detector alone against the max-ensemble, under
      exchangeable, obfuscated and naturalised payloads. Source: e7_ensemble_egress.
      The paper labels this study RQ4 and reports it in the extended version, with
      the panel in the camera-ready.

The Okabe-Ito palette is used and every colour is paired with a marker, a line style or
a hatch. The panels therefore remain readable in grayscale print.
Usage: python3 make_camera_figures.py
"""
import json, os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from artifact_paths import FIGURES, RESULTS, ensure_dir

PT = 7.5  # base font size in points at final printed size
mpl.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,
    # Computer Modern matches the LNCS body text.
    "font.family": "serif", "font.serif": ["cmr10"], "mathtext.fontset": "cm",
    "axes.formatter.use_mathtext": True, "axes.unicode_minus": False,
    "font.size": PT, "axes.labelsize": PT, "axes.titlesize": PT,
    "xtick.labelsize": PT - 0.5, "ytick.labelsize": PT - 0.5,
    "legend.fontsize": PT - 0.5,
    "axes.linewidth": 0.6, "lines.linewidth": 1.0, "lines.markersize": 3.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "xtick.major.pad": 2, "ytick.major.pad": 2, "axes.labelpad": 2,
    "axes.grid": True, "axes.axisbelow": True,
    "grid.color": "0.88", "grid.linewidth": 0.4,
    "axes.spines.top": False, "axes.spines.right": False,
    "hatch.linewidth": 0.6, "patch.linewidth": 0.5,
})
# Okabe-Ito
BLUE, VERM, ORANGE, GRAY = "#0072B2", "#D55E00", "#E69F00", "#555555"
# One encoding per traffic condition, shared by panels (b) and (c).
COND = {
    "exch": dict(label="exchangeable", color=BLUE, hatch=""),
    "obf": dict(label="adaptive obfuscation", color=VERM, hatch="////"),
    "nat": dict(label="naturalised payload", color=ORANGE, hatch="...."),
}

R = json.load(open(os.path.join(ensure_dir(RESULTS), "core_results.json")))
FIG = ensure_dir(FIGURES)

CM = 1 / 2.54
fig, axes = plt.subplots(1, 3, figsize=(12.2 * CM, 4.1 * CM),
                         gridspec_kw={"width_ratios": [1.0, 0.85, 1.15]})
axa, axb, axc = axes


def ref_line(ax, y, text, x_text, ha="left", dy=0.0):
    ax.axhline(y, color=GRAY, ls=(0, (1.2, 1.2)), lw=0.8, zorder=1)
    ax.text(x_text, y + dy, text, color=GRAY, ha=ha, va="bottom", fontsize=PT - 0.5)


def bars(ax, groups, series, width):
    """Draw grouped bars. `series` is a list of (condition key, one value per group)
    and the bar width is `width`. Returns the group positions."""
    x = np.arange(len(groups))
    k = len(series)
    for i, (ck, vals) in enumerate(series):
        c = COND[ck]
        ax.bar(x + (i - (k - 1) / 2) * width, vals, width, color=c["color"],
               hatch=c["hatch"], edgecolor="black", linewidth=0.5, zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="x", visible=False)
    return x


def fmt(v):
    """Format a bar value: '1.00' for full pass-through and '.xxx' otherwise, without a
    leading zero, which keeps adjacent labels from colliding."""
    return f"{v:.2f}" if v >= 1 else f"{v:.3f}"[1:]


VAL_PT = PT - 2.0  # value labels sit close together and are set smaller than the tick labels


def val(ax, x, y, s, ha="center", floor=None):
    """Write the value above a bar. A bar shorter than `floor` (the alpha line) is
    labelled just above that line so the text does not sit on the dashed reference."""
    base = max(y, floor) if floor is not None else y
    ax.text(x, base + 0.02, s, ha=ha, va="bottom", fontsize=VAL_PT)


# (a) RQ1: share of calibration draws with pass-through <= alpha.
e2 = R["e2_conformal_coverage"]
cur = e2["curve"]
a = np.array([c["alpha"] for c in cur])
sm = 100 * np.array([c["sound_frac_marginal"] for c in cur])
sp = 100 * np.array([c["sound_frac_pac"] for c in cur])
delta = e2["delta"]
ref_line(axa, 100 * (1 - delta), rf"target $1-\delta={1 - delta:.2f}$", 0.305,
         ha="right", dy=0.8)
axa.plot(a, sp, "-s", color=BLUE, mec="black", mew=0.4, label="exact-PAC", zorder=3)
axa.plot(a, sm, "--o", color=VERM, mec="black", mew=0.4, label="marginal", zorder=3)
axa.set_xlabel(r"target level $\alpha$")
axa.set_ylabel(r"draws with pass-through $\leq\alpha$ (%)")
axa.set_xlim(0, 0.315)
axa.set_xticks([0, 0.1, 0.2, 0.3])
axa.set_ylim(40, 105)
axa.set_yticks([40, 60, 80, 100])
axa.legend(loc="center right", bbox_to_anchor=(1.0, 0.58), frameon=False,
           handlelength=2.2, borderaxespad=0.2)

# (b) RQ3: content egress. The automaton is blind to it and the conformal layer is not.
e6 = R["e6_content_egress"]
alpha = e6["alpha"]
keys = ["dpa_only", "policyshield"]
ex = [e6["exchangeable"][k]["mean"] for k in keys]
ad = [e6["adaptive"][k]["mean"] for k in keys]
w = 0.36
x = bars(axb, ["DPA-only", "Deon"], [("exch", ex), ("obf", ad)], w)
for xi, e, d in zip(x, ex, ad):
    val(axb, xi - w / 2, e, fmt(e), floor=alpha)
    val(axb, xi + w / 2, d, fmt(d), floor=alpha)
axb.set_ylabel("leak pass-through (fraction)")

# (c) Hardening: the single lexical detector against the max-ensemble.
e7 = R["e7_ensemble_egress"]
lex = [e7["exchangeable"]["single"]["lexical"]["mean"],
       e7["adaptive_obf"]["single"]["lexical"]["mean"],
       e7["adaptive_evade_all"]["single"]["lexical"]["mean"]]
ens = [e7["exchangeable"]["ensemble"]["mean"],
       e7["adaptive_obf"]["ensemble"]["mean"],
       e7["adaptive_evade_all"]["ensemble"]["mean"]]
w = 0.27
x = bars(axc, ["lexical only", "max-ensemble"],
         [("exch", [lex[0], ens[0]]), ("obf", [lex[1], ens[1]]),
          ("nat", [lex[2], ens[2]])], w)
for gi, xi in enumerate(x):
    for off, series in ((-w, (lex[0], ens[0])), (0.0, (lex[1], ens[1])), (w, (lex[2], ens[2]))):
        v = series[gi]
        val(axc, xi + off, v, fmt(v), floor=alpha)

for ax in (axb, axc):
    ax.set_ylim(0, 1.18)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", ".25", ".50", ".75", "1"])
    # The alpha line is labelled with its value, read from e6_content_egress, in the
    # right margin because the bars fill the plot area.
    ax.axhline(alpha, color=GRAY, ls=(0, (1.2, 1.2)), lw=0.8, zorder=3)
    ax.text(1.015, alpha, rf"$\alpha={alpha:.2f}$", transform=ax.get_yaxis_transform(),
            color=GRAY, ha="left", va="center", fontsize=PT - 0.5, clip_on=False)
axc.set_yticklabels([])

for ax, letter in zip(axes, "abc"):
    ax.set_title(f"({letter})", loc="left", fontweight="bold", pad=3,
                 x=-0.02 if letter != "a" else -0.02)

# One legend for the traffic conditions of (b) and (c).
handles = [Patch(facecolor=c["color"], hatch=c["hatch"], edgecolor="black",
                 linewidth=0.5, label=c["label"]) for c in COND.values()]
fig.legend(handles=handles, loc="upper right", ncol=3, frameon=False,
           bbox_to_anchor=(1.0, 1.02), handlelength=1.6, columnspacing=1.0,
           handletextpad=0.4, borderaxespad=0.0)

# The right margin and wspace leave room for the alpha labels of (b) and (c).
fig.subplots_adjust(left=0.075, right=0.918, bottom=0.2, top=0.80, wspace=0.40)
out = os.path.join(FIG, "fig_results.pdf")
fig.savefig(out)
plt.close(fig)
print(f"wrote {out}")
