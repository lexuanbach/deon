"""Stress tests of the conformal layer (RQ5 and RQ6 of the extended version).

The camera-ready reports RQ1 to RQ3 and mentions a few of these results in one
paragraph of Sect. 7 (label noise, the tie-break, monitor cost). The extended version
reports all of them in its RQ5 and RQ6 subsections. Every experiment here is
model-free and seeded. The code names them R1 to R8, and the table gives the
research question of each and, where one applies, the assumption of Sect. 4 that it stresses. The results
are stored under the key of each function in results/stress_results.json, which
make_stress_figures.py turns into fig_rq5.pdf and fig_rq6.pdf.

  R1 r1_label_noise        RQ5. A fraction rho of the calibration labels is flipped
                           and the realised pass-through, PAC sound fraction and
                           utility are measured against rho. Errors in the
                           calibration labels bear on A4.
  R2 r2_small_nv           RQ5. The number of calibration violations n_v is swept.
                           For small n_v the PAC rank drops to 0, which puts tau below
                           every violation and the guard refuses almost everything.
  R3 r3_ties               RQ5. A coarse detector whose scores tie. Admitting ties
                           deterministically over-admits, and the randomised
                           tie-break of Sect. 5 restores the target.
  R4 r4_miscalibration     RQ5. A biased and noisier detector. A recalibrated
                           threshold tracks the target and a fixed cutoff does not.
  R5 r5_drift_rolling      RQ5. A stream with slow benign drift, compared under static
                           calibration, drift-triggered recalibration, and
                           recalibration with two groups.
  R6 r6_abstention_recovery RQ5. Task completion with the recovery ladder of Sect. 5
                           (restricted retry, rollback, escalation). This is a
                           Monte Carlo model with fixed branch probabilities and does
                           not run the guard on a real service catalogue.
  R7 r7_sequential_dependence RQ6. Scores of the steps of one trace are correlated,
                           which breaks the exchangeability that Thm. 2 needs at the
                           step level (A4). Calibrating on one summary score per trace
                           restores the guarantee.
  R8 r8_scorer_evolution   RQ6. A versioned scorer whose score mapping shifts across
                           releases, with and without a hysteresis band that stops an
                           adversary from forcing recalibrations back and forth.

Each function draws its own seeded generators (a base seed plus the trial index), so
a run is reproducible bit for bit. main() runs all eight and writes the JSON file.
Intervals are percentile bootstrap intervals over the per-seed values.
"""
from __future__ import annotations
import json, os, time, math
import numpy as np
from artifact_paths import RESULTS, ensure_dir

from core import (calibrate_threshold, calibrate_randomized_threshold,
                  randomized_admit, _pac_rank)
import bench
import content


def _boot_ci(x, n_boot=4000, alpha=0.05, seed=0):
    x = np.asarray(x, float)
    if len(x) == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(axis=1)
    lo, hi = np.quantile(m, [alpha / 2, 1 - alpha / 2])
    return float(x.mean()), float(lo), float(hi)


def _ci(x):
    m, lo, hi = _boot_ci(x)
    return {"mean": round(m, 4), "ci": [round(lo, 4), round(hi, 4)]}


# R1: label noise in the calibration data (RQ5)
def r1_label_noise(alpha=0.10, delta=0.05, rhos=(0.0, 0.05, 0.10, 0.20, 0.30),
                   trials=200, n_cal=3000, n_eval=20000, sep=2.6, seed0=101):
    """Flip each calibration label with probability rho (in both directions) before tau
    is chosen. The evaluation labels stay clean. The function reports the realised
    pass-through for the marginal and the PAC rank, the PAC sound fraction (the share
    of draws with pass-through at most alpha) and the utility, for each rho. Benign
    examples that are relabelled as violations enter the violation sample with low
    scores and pull its low quantiles down, and tau falls. Noise therefore trades
    utility for safety, and the pass-through drops below alpha as the utility drops."""
    out = []
    for rho in rhos:
        pt_m, pt_p, sound_p, util = [], [], [], []
        for t in range(trials):
            rng = np.random.default_rng(seed0 + t)
            s_c, y_c = bench.build_risk_pool(rng, n_cal, separation=sep)
            yn = y_c.copy()
            if rho > 0:
                flip = rng.random(len(yn)) < rho
                yn[flip] = 1 - yn[flip]              # symmetric label noise
            tau_m = calibrate_threshold(s_c, yn, alpha=alpha)
            tau_p = calibrate_threshold(s_c, yn, alpha=alpha, delta=delta, pac=True)
            s_e, y_e = bench.build_risk_pool(rng, n_eval, separation=sep)
            pt_m.append(bench.violation_passthrough_rate(s_e, y_e, tau_m))
            pt_p.append(bench.violation_passthrough_rate(s_e, y_e, tau_p))
            sound_p.append(bench.violation_passthrough_rate(s_e, y_e, tau_p) <= alpha + 1e-9)
            util.append(bench.benign_admit_rate(s_e, y_e, tau_p))
        out.append({"rho": rho,
                    "passthrough_marginal": round(float(np.mean(pt_m)), 4),
                    "passthrough_pac": round(float(np.mean(pt_p)), 4),
                    "pac_sound_frac": round(float(np.mean(sound_p)), 4),
                    "utility_pac": round(float(np.mean(util)), 4)})
    return {"alpha": alpha, "delta": delta, "sep": sep, "trials": trials, "curve": out}


# R2: few calibration violations (RQ5)
def r2_small_nv(alpha=0.10, delta=0.05,
                nvs=(20, 40, 80, 160, 320, 640, 1280), trials=400,
                n_eval=20000, sep=2.6, base_rate=0.30, seed0=201):
    """Sweep the number n_v of calibration violations. For each value the calibration
    pool holds exactly n_v violations plus benign examples in the ratio implied by
    `base_rate`. The function reports the PAC rank k', the realised pass-through and
    the sound fraction of the marginal and PAC thresholds, and the utility. For small
    n_v the rank floors at 0, tau falls below every violation and the utility
    is low. The control and the utility improve as n_v grows. This backs the remark
    in Sect. 7 that exact-PAC needs of the order of 10^2 labelled violations."""
    out = []
    for n_v in nvs:
        n_ben = int(round(n_v * (1 - base_rate) / base_rate))
        krank = _pac_rank(n_v, alpha, delta)
        pt_m, pt_p, sound_p, sound_m, util_m, util_p = [], [], [], [], [], []
        for t in range(trials):
            rng = np.random.default_rng(seed0 + t)
            # A calibration pool with exactly n_v violations.
            sv = _draw_scores(rng, n_v, 1, sep)
            sb = _draw_scores(rng, n_ben, 0, sep)
            s_c = np.concatenate([sv, sb])
            y_c = np.concatenate([np.ones(n_v, int), np.zeros(n_ben, int)])
            tau_m = calibrate_threshold(s_c, y_c, alpha=alpha)
            tau_p = calibrate_threshold(s_c, y_c, alpha=alpha, delta=delta, pac=True)
            s_e, y_e = bench.build_risk_pool(rng, n_eval, base_rate=base_rate, separation=sep)
            pm = bench.violation_passthrough_rate(s_e, y_e, tau_m)
            pp = bench.violation_passthrough_rate(s_e, y_e, tau_p)
            pt_m.append(pm); pt_p.append(pp)
            sound_m.append(pm <= alpha + 1e-9); sound_p.append(pp <= alpha + 1e-9)
            util_m.append(bench.benign_admit_rate(s_e, y_e, tau_m))
            util_p.append(bench.benign_admit_rate(s_e, y_e, tau_p))
        out.append({"n_v": n_v, "pac_rank": krank,
                    "passthrough_marginal": round(float(np.mean(pt_m)), 4),
                    "passthrough_pac": round(float(np.mean(pt_p)), 4),
                    "sound_frac_marginal": round(float(np.mean(sound_m)), 4),
                    "sound_frac_pac": round(float(np.mean(sound_p)), 4),
                    "utility_marginal": round(float(np.mean(util_m)), 4),
                    "utility_pac": round(float(np.mean(util_p)), 4)})
    return {"alpha": alpha, "delta": delta, "sep": sep, "trials": trials, "curve": out}


def _draw_scores(rng, n, y, sep):
    """Draw n scores of class y (1 for a violation) from the detector model of
    bench.build_risk_pool. With it a pool can hold an exact number of violations."""
    mu = (0.5 + sep * 0.25) if y == 1 else (0.5 - sep * 0.25)
    raw = rng.normal(mu, 0.25, size=n)
    return 1.0 / (1.0 + np.exp(-4.0 * (raw - 0.5)))


# R3: tied scores (RQ5)
def r3_ties(alpha=0.10, delta=0.05, levels=6, trials=400, n_cal=3000,
            n_eval=20000, sep=2.6, seed0=301):
    """Compare three admission rules at one conformal threshold when the detector is
    coarse. Scores are rounded to `levels` values, and many violations tie with tau.
    det_le admits ties (score <= tau) and over-admits. det_lt rejects them (score <
    tau) and is conservative. The randomised rule admits a tied violation with
    an independent augmented uniform rank. The calibration and test uniforms are
    sampled before seeing evaluation outcomes, so the third row exercises the
    deployable rule rather than choosing a boundary probability from test labels."""
    def quantise(s):
        return np.round(s * (levels - 1)) / (levels - 1)
    pt_le, pt_lt, pt_rand = [], [], []
    for t in range(trials):
        rng = np.random.default_rng(seed0 + t)
        s_c, y_c = bench.build_risk_pool(rng, n_cal, separation=sep)
        s_c = quantise(s_c)
        tau = calibrate_threshold(s_c, y_c, alpha=alpha)         # deterministic comparison
        aug_tau = calibrate_randomized_threshold(s_c, y_c, alpha, rng)
        s_e, y_e = bench.build_risk_pool(rng, n_eval, separation=sep)
        s_e = quantise(s_e)
        v = s_e[y_e == 1]
        pt_le.append(float((v <= tau).mean()))
        pt_lt.append(float((v < tau).mean()))
        pt_rand.append(float(np.mean([randomized_admit(float(x), aug_tau, rng)
                                     for x in v])))
    return {"alpha": alpha, "levels": levels, "trials": trials,
            "det_admit_le": _ci(pt_le), "det_admit_lt": _ci(pt_lt),
            "randomised_tiebreak": _ci(pt_rand)}


# R4: a biased or noisier detector (RQ5)
def r4_miscalibration(alpha=0.10, delta=0.05, trials=200, n_cal=3000, n_eval=20000,
                      biases=(-0.15, -0.05, 0.0, 0.05, 0.15),
                      extra_noise=(0.0, 0.15, 0.30), sep=2.0, seed0=401):
    """Add a logit bias and extra label-independent Gaussian noise to the raw detector
    score, then squash as before. Calibration and evaluation see the same distorted
    detector. The data then stay exchangeable. Recalibration re-derives tau from the
    observed scores and therefore tracks the target under any monotone distortion. A
    fixed cutoff of 0.5 does not. The grid over (bias, extra noise) reports the
    pass-through and utility of the calibrated threshold and the pass-through of the
    fixed cutoff."""
    def biased_pool(rng, n, bias, noise):
        y = (rng.random(n) < 0.30).astype(int)
        mu = np.where(y == 1, 0.5 + sep * 0.25, 0.5 - sep * 0.25)
        raw = rng.normal(mu, 0.25) + bias + rng.normal(0, noise, n)
        s = 1.0 / (1.0 + np.exp(-4.0 * (raw - 0.5)))
        return s, y
    grid = []
    for b in biases:
        for nz in extra_noise:
            cpt, fpt, cut = [], [], []
            for t in range(trials):
                rng = np.random.default_rng(seed0 + t)
                s_c, y_c = biased_pool(rng, n_cal, b, nz)
                tau = calibrate_threshold(s_c, y_c, alpha=alpha, delta=delta, pac=True)
                s_e, y_e = biased_pool(rng, n_eval, b, nz)
                cpt.append(bench.violation_passthrough_rate(s_e, y_e, tau))
                cut.append(bench.benign_admit_rate(s_e, y_e, tau))
                fpt.append(bench.violation_passthrough_rate(s_e, y_e, 0.5))
            grid.append({"bias": b, "extra_noise": nz,
                         "conformal_passthrough": round(float(np.mean(cpt)), 4),
                         "conformal_utility": round(float(np.mean(cut)), 4),
                         "fixed_passthrough": round(float(np.mean(fpt)), 4)})
    return {"alpha": alpha, "delta": delta, "sep": sep, "grid": grid}


# R5: benign drift and rolling recalibration (RQ5)
def r5_drift_rolling(alpha=0.10, delta=0.05, seeds=30, T=40, batch=600,
                     drift=0.9, window=3, drift_thresh=0.06, seed0=501):
    """A deployment stream of T batches over which the benign score distribution
    drifts by `drift` in total while the violation distribution stays fixed. Three
    policies are compared.
      static   : calibrate on batch 0 and never update.
      rolling  : track the mean benign score and recalibrate on a sliding window of
                 `window` batches when it moves by more than `drift_thresh` from the
                 value at the last calibration.
      mondrian : two thresholds, one for each half of the window split at its median
                 score.
    Reports the mean realised pass-through and utility over the stream, the number of
    recalibrations, and the time of one calibration in milliseconds. The drift monitor
    reads benign labels of the current batch, which a deployment would have to
    obtain by sampling or delayed feedback."""
    def batch_pool(rng, n, shift):
        y = (rng.random(n) < 0.30).astype(int)
        # The benign mean moves by `shift`. The violation mean stays fixed.
        mu = np.where(y == 1, 0.5 + 2.6 * 0.25, 0.5 - 2.6 * 0.25 + shift)
        raw = rng.normal(mu, 0.25)
        s = 1.0 / (1.0 + np.exp(-4.0 * (raw - 0.5)))
        return s, y

    static_pt, roll_pt, mond_pt = [], [], []
    static_ut, roll_ut, mond_ut = [], [], []
    recals = []
    cal_ms = []
    for sd in range(seeds):
        rng = np.random.default_rng(seed0 + sd)
        shifts = np.linspace(0.0, drift, T)
        # initial calibration (batch 0)
        s0, y0 = batch_pool(rng, batch, shifts[0])
        t0 = time.perf_counter()
        tau_static = calibrate_threshold(s0, y0, alpha=alpha, delta=delta, pac=True)
        cal_ms.append((time.perf_counter() - t0) * 1e3)
        tau_roll = tau_static
        cal_benign_mean = s0[y0 == 0].mean()
        recent_s, recent_y = [s0], [y0]
        n_recal = 0
        sp, rp, mp, su, ru, mu = [], [], [], [], [], []
        for t in range(T):
            s, y = batch_pool(rng, batch, shifts[t])
            # static
            sp.append(bench.violation_passthrough_rate(s, y, tau_static))
            su.append(bench.benign_admit_rate(s, y, tau_static))
            # rolling drift monitor on benign mean
            cur_benign_mean = s[y == 0].mean()
            if abs(cur_benign_mean - cal_benign_mean) > drift_thresh:
                win_s = np.concatenate(recent_s[-window:] + [s])
                win_y = np.concatenate(recent_y[-window:] + [y])
                tau_roll = calibrate_threshold(win_s, win_y, alpha=alpha, delta=delta, pac=True)
                cal_benign_mean = cur_benign_mean
                n_recal += 1
            rp.append(bench.violation_passthrough_rate(s, y, tau_roll))
            ru.append(bench.benign_admit_rate(s, y, tau_roll))
            # Mondrian arm: two score regimes, cut at the median, one tau for each.
            if abs(cur_benign_mean - cal_benign_mean) > drift_thresh or t == 0:
                pass
            med = np.median(s)
            lo_mask = s <= med
            # Each regime threshold comes from the same rolling window, cut at its own median.
            win_s = np.concatenate(recent_s[-window:] + [s])
            win_y = np.concatenate(recent_y[-window:] + [y])
            gm = np.median(win_s)
            tlo = calibrate_threshold(win_s[win_s <= gm], win_y[win_s <= gm],
                                      alpha=alpha, delta=delta, pac=True)
            thi = calibrate_threshold(win_s[win_s > gm], win_y[win_s > gm],
                                      alpha=alpha, delta=delta, pac=True)
            adm = np.where(lo_mask, s <= tlo, s <= thi)
            v = y == 1
            mp.append(float(adm[v].mean()) if v.any() else 0.0)
            mu.append(float(adm[~v].mean()) if (~v).any() else 0.0)
            recent_s.append(s); recent_y.append(y)
        static_pt.append(np.mean(sp)); roll_pt.append(np.mean(rp)); mond_pt.append(np.mean(mp))
        static_ut.append(np.mean(su)); roll_ut.append(np.mean(ru)); mond_ut.append(np.mean(mu))
        recals.append(n_recal)
    return {"alpha": alpha, "delta": delta, "T": T, "batch": batch, "drift": drift,
            "window": window, "drift_thresh": drift_thresh, "seeds": seeds,
            "static": {"passthrough": _ci(static_pt), "utility": _ci(static_ut)},
            "rolling": {"passthrough": _ci(roll_pt), "utility": _ci(roll_ut),
                        "recalibrations": _ci(np.array(recals, float))},
            "mondrian": {"passthrough": _ci(mond_pt), "utility": _ci(mond_ut)},
            "calibration_ms_per_recal": round(float(np.mean(cal_ms)), 3)}


# R6: recovery after an abstention (RQ5)
def r6_abstention_recovery(alpha=0.10, delta=0.05, seeds=40, n_tasks=500,
                           catalog=24, seed0=601):
    """A Monte Carlo model of the recovery ladder of Sect. 5. Each of `n_tasks` tasks
    is attacked with probability 0.5, half of the attacks being explicit and half
    latent. The branch probabilities are fixed constants in
    this function. An explicit violation is refused by the automaton, and
    the ladder then either finishes with a restricted tool set or, if the refused tool
    was critical to the goal (probability 0.35), escalates to a human. A latent
    violation is drawn from the risk pool and executes if its score is at most tau,
    otherwise the guard abstains and the ladder rolls back (0.7) or escalates.
    Reported are the autonomous completion rate, the completion rate with fallbacks,
    the raw abstain rate, the mix of fallbacks, the recovery latency in extra steps and
    the rate of unsafe executions. Because the probabilities are assumptions, the
    figures show how the ladder converts abstentions into completions and are not a
    measurement of a real service. The `catalog` argument is only recorded in the
    output."""
    # A conformal tau calibrated on a pool of the default detector.
    rng0 = np.random.default_rng(seed0)
    s_c, y_c = bench.build_risk_pool(rng0, 4000, separation=2.6)
    tau = calibrate_threshold(s_c, y_c, alpha=alpha, delta=delta, pac=True)

    comp_auto, comp_fb, abstain_raw = [], [], []
    fb_restrict, fb_rollback, fb_human = [], [], []
    rec_latency, unsafe_expl, unsafe_latent = [], [], []
    for sd in range(seeds):
        rng = np.random.default_rng(seed0 + 1000 + sd)
        ca = cf = ab = 0
        fr = fb = fh = 0
        lat = []
        ue = ul = 0
        n_expl = n_latent = 0
        for _ in range(n_tasks):
            L = int(rng.integers(3, 9))
            attacked = rng.random() < 0.5
            kind = None
            if attacked:
                kind = "explicit" if rng.random() < 0.5 else "latent"
            steps = 0
            done = True
            if kind == "explicit":
                n_expl += 1
                # The automaton refuses the explicit action. Fallback 1 removes the
                # offending tool, which is enough unless the goal needed that tool.
                needed = rng.random() < 0.35   # was the refused tool critical to the goal?
                if not needed:
                    cf += 1; fr += 1; lat.append(int(rng.integers(1, 3))); done = True
                else:
                    # A rollback cannot recover a goal-critical tool, and the task goes to a human.
                    fh += 1; cf += 1; lat.append(int(rng.integers(2, 5)))
                # An explicit violation never executes, and ue stays 0.
            elif kind == "latent":
                n_latent += 1
                # The latent violation is drawn from the risk pool and executes iff its score is at most tau.
                sv = _draw_scores(rng, 1, 1, 2.6)[0]
                if sv <= tau:
                    ul += 1        # slipped through, which alpha bounds in expectation
                    ca += 1        # the task completes with the admitted violation
                else:
                    ab += 1        # the guard abstains on the latent action
                    # Fallback 2 rolls the step back and compensates, otherwise a human takes over.
                    if rng.random() < 0.7:
                        fb += 1; cf += 1; lat.append(int(rng.integers(1, 4)))
                    else:
                        fh += 1; cf += 1; lat.append(int(rng.integers(2, 6)))
            else:
                ca += 1            # a benign task completes autonomously
        comp_auto.append(ca / n_tasks)
        comp_fb.append((ca + cf) / n_tasks)
        abstain_raw.append(ab / n_tasks)
        tot_fb = max(fr + fb + fh, 1)
        fb_restrict.append(fr / tot_fb); fb_rollback.append(fb / tot_fb); fb_human.append(fh / tot_fb)
        rec_latency.append(np.mean(lat) if lat else 0.0)
        unsafe_expl.append(ue / max(n_expl, 1))
        unsafe_latent.append(ul / max(n_latent, 1))
    return {"alpha": alpha, "delta": delta, "seeds": seeds, "n_tasks": n_tasks,
            "catalog_size": catalog, "tau": round(float(tau), 4),
            "completion_autonomous": _ci(comp_auto),
            "completion_with_fallback": _ci(comp_fb),
            "abstain_rate_raw": _ci(abstain_raw),
            "fallback_mix": {"restricted_retry": _ci(fb_restrict),
                             "rollback_compensate": _ci(fb_rollback),
                             "human_escalation": _ci(fb_human)},
            "recovery_latency_steps": _ci(rec_latency),
            "unsafe_explicit": _ci(unsafe_expl),
            "unsafe_latent": _ci(unsafe_latent)}


# R7: dependence between the steps of one trace (RQ6)
def _corr_trace_scores(rng, n_traces, steps, sep, rho, y=1):
    """Draw the scores of `n_traces` traces of `steps` steps each for class y. Within a
    trace the latent noise follows an AR(1) process with correlation `rho` between
    consecutive steps, and traces are independent. rho = 0 gives i.i.d. steps and
    rho near 1 makes the risk almost constant inside a trace. Returns an array of
    shape (n_traces, steps) with scores squashed into (0, 1)."""
    mu = (0.5 + sep * 0.25) if y == 1 else (0.5 - sep * 0.25)
    # AR(1) recursion e_t = rho e_{t-1} + sqrt(1 - rho^2) z_t keeps the variance at 1.
    z = rng.normal(0.0, 1.0, size=(n_traces, steps))
    e = np.empty_like(z)
    e[:, 0] = z[:, 0]
    for t in range(1, steps):
        e[:, t] = rho * e[:, t - 1] + math.sqrt(max(1e-12, 1 - rho * rho)) * z[:, t]
    raw = mu + 0.25 * e
    return 1.0 / (1.0 + np.exp(-4.0 * (raw - 0.5)))


def r7_sequential_dependence(alpha=0.10, delta=0.05,
                             rhos=(0.0, 0.3, 0.6, 0.9, 0.99),
                             trials=400, n_cal_traces=80, steps=6,
                             n_eval_traces=20000, sep=2.6, seed0=701):
    """Coverage of the PAC threshold when the calibration scores come from a fixed
    number of correlated traces.

    Thm. 2(ii) needs the calibration violation scores to be i.i.d. If they are the
    steps of only a few traces, the effective sample size is closer to the number of
    traces than to the number of steps, and pooling the steps overstates the data.
    With the number of calibration traces fixed at n_cal_traces, three regimes are
    compared as the correlation rho grows.
      step_iid  : the same number of scores drawn independently (rho = 0), the
                  baseline for which the theorem applies.
      step_corr : the pooled correlated steps, calibrated at the step level as if
                  they were exchangeable. This is expected to lose coverage.
      trace_corr: one summary score per trace (its highest-risk step), calibrated
                  at the trace level. The exchangeable unit is then the trace.
    Evaluation always uses fresh correlated traces. For the step regimes the metric is
    the per-step pass-through and for the trace regime it is the probability that a
    violating trace's maximum step is admitted. The function reports the mean
    pass-through and the PAC sound fraction of each regime."""
    out = []
    for rho in rhos:
        # Step-level metric: P[admit | violating step] on fresh correlated steps.
        # Trace-level metric: P[the trace's highest-risk step is admitted] on fresh traces.
        pt_iid, pt_scorr, pt_tcorr = [], [], []
        sf_iid, sf_scorr, sf_tcorr = [], [], []
        for t in range(trials):
            rng = np.random.default_rng(seed0 + t)
            # Calibration data: a fixed number of traces of `steps` correlated steps each.
            iid_cal = _corr_trace_scores(rng, n_cal_traces, steps, sep, 0.0)   # rho=0
            corr_cal = _corr_trace_scores(rng, n_cal_traces, steps, sep, rho)  # rho
            s_iid = iid_cal.ravel()
            s_scorr = corr_cal.ravel()
            s_tcorr = corr_cal.max(axis=1)                     # one summary score per trace
            tau_iid = calibrate_threshold(s_iid, np.ones(len(s_iid), int),
                                          alpha=alpha, delta=delta, pac=True)
            tau_scorr = calibrate_threshold(s_scorr, np.ones(len(s_scorr), int),
                                            alpha=alpha, delta=delta, pac=True)
            tau_tcorr = calibrate_threshold(s_tcorr, np.ones(len(s_tcorr), int),
                                            alpha=alpha, delta=delta, pac=True)
            # Evaluation on fresh correlated traces, as in deployment.
            ev = _corr_trace_scores(rng, n_eval_traces, steps, sep, rho)
            ev_steps = ev.ravel()                              # for the per-step metric
            ev_trace = ev.max(axis=1)                          # for the per-trace metric
            p_iid = float((ev_steps <= tau_iid).mean())
            p_scorr = float((ev_steps <= tau_scorr).mean())
            p_tcorr = float((ev_trace <= tau_tcorr).mean())
            pt_iid.append(p_iid); pt_scorr.append(p_scorr); pt_tcorr.append(p_tcorr)
            sf_iid.append(p_iid <= alpha + 1e-9)
            sf_scorr.append(p_scorr <= alpha + 1e-9)
            sf_tcorr.append(p_tcorr <= alpha + 1e-9)
        out.append({"rho": rho,
                    "passthrough_step_iid": round(float(np.mean(pt_iid)), 4),
                    "passthrough_step_corr": round(float(np.mean(pt_scorr)), 4),
                    "passthrough_trace_corr": round(float(np.mean(pt_tcorr)), 4),
                    "sound_frac_step_iid": round(float(np.mean(sf_iid)), 4),
                    "sound_frac_step_corr": round(float(np.mean(sf_scorr)), 4),
                    "sound_frac_trace_corr": round(float(np.mean(sf_tcorr)), 4)})
    return {"alpha": alpha, "delta": delta, "steps": steps, "sep": sep,
            "n_cal_traces": n_cal_traces, "trials": trials, "curve": out}


# R8: a scorer that changes across releases (RQ6)
def r8_scorer_evolution(alpha=0.10, delta=0.05, seeds=40, T=48, batch=800,
                        version_shift=0.55, hold=3, seed0=801):
    """A versioned scorer whose score mapping drifts across releases. Over a stream of T
    batches the effective version steps through `n_versions` blocks, and each version
    adds a further logit offset (up to `version_shift`) to the raw score. Labels are
    ground truth. Four policies are compared.
      locked : calibrate once for version 0 and never update, which is stale after
               the first release.
      auto   : detect the true version of each batch and, on the first batch of a
               new version, calibrate a profile for it.
      adversarial_no_hysteresis : an adversary toggles the reported version tag
               on every batch, and the guard switches profile whenever the tag changes.
      adversarial_hysteresis : the same toggling, but a change is acted on only after
               it has persisted for `hold` batches.
    Reports the mean pass-through, the number of recalibrations and the number of
    profile switches. The hysteresis band absorbs the toggling and keeps the profile
    stable. In the toggling policies the data still follow the honest version
    schedule, and the reported tag and the data disagree."""
    def batch_pool(rng, n, ver_offset):
        y = (rng.random(n) < 0.30).astype(int)
        mu = np.where(y == 1, 0.5 + 2.6 * 0.25, 0.5 - 2.6 * 0.25)
        raw = rng.normal(mu, 0.25) + ver_offset          # version shifts the mapping
        s = 1.0 / (1.0 + np.exp(-4.0 * (raw - 0.5)))
        return s, y

    # Honest schedule: versions 0 to 3, each a block of the stream, with growing offsets.
    n_ver = 4
    offsets = np.linspace(0.0, version_shift, n_ver)
    true_ver = np.repeat(np.arange(n_ver), int(np.ceil(T / n_ver)))[:T]

    locked_pt, auto_pt, auto_recals = [], [], []
    adv_nohyst_pt, adv_nohyst_switch = [], []
    adv_hyst_pt, adv_hyst_switch, adv_hyst_recals = [], [], []
    for sd in range(seeds):
        rng = np.random.default_rng(seed0 + sd)
        # Cache of calibrated profiles, version -> tau.
        def calib_for(ver, rng_):
            s, y = batch_pool(rng_, 4000, offsets[ver])
            return calibrate_threshold(s, y, alpha=alpha, delta=delta, pac=True)
        tau_locked = calib_for(0, np.random.default_rng(seed0 + 5000 + sd))
        # Honest auto policy: one profile per true version seen so far.
        profiles = {0: tau_locked}
        lp, ap = [], []
        n_recal = 0
        cur_auto_ver = 0
        # State of the two adversarial policies.
        adv_profiles = {0: tau_locked}
        adv_nh_pt, adv_h_pt = [], []
        adv_nh_ver = adv_h_ver = 0
        adv_nh_sw = adv_h_sw = 0
        adv_h_recal = 0
        pending_ver, pending_cnt = 0, 0
        for t in range(T):
            v = int(true_ver[t])
            s, y = batch_pool(rng, batch, offsets[v])
            # Locked policy: always the profile of version 0.
            lp.append(bench.violation_passthrough_rate(s, y, tau_locked))
            # Honest auto policy: calibrate when a genuinely new version appears.
            if v != cur_auto_ver:
                if v not in profiles:
                    profiles[v] = calib_for(v, np.random.default_rng(seed0 + 9000 + sd * 13 + v))
                    n_recal += 1
                cur_auto_ver = v
            ap.append(bench.violation_passthrough_rate(s, y, profiles[cur_auto_ver]))
            # The adversary toggles the reported version tag between 0 and 1 on every batch.
            reported = t % 2                       # the oscillating tag
            # The data still follow the honest version, and the tag and the data disagree.
            # (a) Without hysteresis: switch profile whenever the reported tag changes.
            if reported not in adv_profiles:
                adv_profiles[reported] = calib_for(reported,
                                                   np.random.default_rng(seed0 + 7000 + reported))
            if reported != adv_nh_ver:
                adv_nh_ver = reported; adv_nh_sw += 1
            adv_nh_pt.append(bench.violation_passthrough_rate(s, y, adv_profiles[adv_nh_ver]))
            # (b) With hysteresis: act only once the reported tag has persisted for `hold` batches.
            if reported == pending_ver:
                pending_cnt += 1
            else:
                pending_ver = reported; pending_cnt = 1
            if pending_cnt >= hold and pending_ver != adv_h_ver:
                if pending_ver not in adv_profiles:
                    adv_profiles[pending_ver] = calib_for(pending_ver,
                                                          np.random.default_rng(seed0 + 7000 + pending_ver))
                    adv_h_recal += 1
                adv_h_ver = pending_ver; adv_h_sw += 1
            adv_h_pt.append(bench.violation_passthrough_rate(s, y, adv_profiles[adv_h_ver]))
        locked_pt.append(np.mean(lp)); auto_pt.append(np.mean(ap)); auto_recals.append(n_recal)
        adv_nohyst_pt.append(np.mean(adv_nh_pt)); adv_nohyst_switch.append(adv_nh_sw)
        adv_hyst_pt.append(np.mean(adv_h_pt)); adv_hyst_switch.append(adv_h_sw)
        adv_hyst_recals.append(adv_h_recal)
    return {"alpha": alpha, "delta": delta, "T": T, "batch": batch,
            "version_shift": version_shift, "n_versions": n_ver, "hold": hold,
            "seeds": seeds,
            "locked": {"passthrough": _ci(locked_pt)},
            "auto": {"passthrough": _ci(auto_pt),
                     "recalibrations": _ci(np.array(auto_recals, float))},
            "adversarial_no_hysteresis": {"passthrough": _ci(adv_nohyst_pt),
                                          "profile_switches": _ci(np.array(adv_nohyst_switch, float))},
            "adversarial_hysteresis": {"passthrough": _ci(adv_hyst_pt),
                                       "profile_switches": _ci(np.array(adv_hyst_switch, float)),
                                       "recalibrations": _ci(np.array(adv_hyst_recals, float))}}


def main():
    """Run R1 to R8 and write results/stress_results.json."""
    outdir = ensure_dir(RESULTS)
    res = {}
    print("R1 label noise ...");        res["r1_label_noise"] = r1_label_noise()
    print("R2 small n_v ...");          res["r2_small_nv"] = r2_small_nv()
    print("R3 tie-handling ...");       res["r3_ties"] = r3_ties()
    print("R4 miscalibration ...");     res["r4_miscalibration"] = r4_miscalibration()
    print("R5 drift + rolling ...");    res["r5_drift_rolling"] = r5_drift_rolling()
    print("R6 abstention recovery ..."); res["r6_abstention_recovery"] = r6_abstention_recovery()
    print("R7 sequential dependence ..."); res["r7_sequential_dependence"] = r7_sequential_dependence()
    print("R8 scorer evolution ...");    res["r8_scorer_evolution"] = r8_scorer_evolution()
    with open(os.path.join(outdir, "stress_results.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("wrote stress_results.json")


if __name__ == "__main__":
    main()
