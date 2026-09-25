"""Model-free experiments of the Deon evaluation (Sect. 7): monitor, calibration, stream.

Every experiment here is deterministic given its seed and needs neither a language
model nor the network. The code labels them E1 to E8. The paper labels the same work
by research question, and the table below connects the two. The result of each
experiment is a JSON object under the key of its function name in
results/core_results.json.

  E1 e1_monitor_soundness    RQ1. Agreement of the automaton of Def. 2 with the planted
                             ground truth of the 900-trace monitor suite, with recall
                             per violation class. Backs Thm. 1 (safety part) and the
                             "100%" of Sect. 7.
  E2 e2_conformal_coverage   RQ1. For each target alpha, the mean pass-through and the
                             share of calibration draws that hold pass-through <= alpha,
                             for the marginal rank and the exact-PAC rank. Backs Thm. 2
                             and Fig. 3a.
  E3 e3_risk_utility         RQ1. The alpha versus utility frontier, and the sweep over
                             detector quality that compares the calibrated threshold
                             with a fixed cutoff. Backs the "across detector quality"
                             sentence of Sect. 7.
  E4 e4_attack_synth         RQ2. The mixed stream in which explicit violations are
                             blocked by the automaton and latent ones are scored.
                             Backs the layer decomposition (unguarded, automaton only,
                             Deon).
  E6 e6_content_egress       RQ3. Content-dependent egress scored by a real detector,
                             under exchangeable and adaptive obfuscated leaks. Backs
                             Cor. 1(b), the 0.089 to 0.328 contrast, and Fig. 3b.
  E7 e7_ensemble_egress      RQ4 (extended version), drawn in Fig. 3c. Three detectors
                             and their max-ensemble under exchangeable, obfuscated
                             and naturalised payloads.
  E8 e8_mondrian_shift       RQ4 (extended version). Marginal against per-group
                             (Mondrian) calibration under a shift of the group mix.
  E5 e5_scalability          Monitor time per trace against trace length (RQ5 timing
                             in the extended version, the microsecond-scale overhead
                             of the abstract).

E5 is listed last because main() runs it last. Interval estimates are percentile bootstrap intervals over the
per-seed values. main() writes results/core_results.json, which is read by
make_real_figures.py, make_camera_figures.py and check_results.py.
"""
from __future__ import annotations
import json, os, time
import numpy as np
from artifact_paths import RESULTS, ensure_dir

from core import (calibrate_threshold, hoeffding_ucb)
import bench
import content


def _boot_ci(x, n_boot=5000, alpha=0.05, seed=0):
    """Percentile bootstrap interval of the mean of `x`, one entry per seed, with a
    fixed resampling seed. Returns (mean, lower, upper), or zeros for an empty list."""
    x = np.asarray(x, float)
    if len(x) == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(axis=1)
    lo, hi = np.quantile(m, [alpha / 2, 1 - alpha / 2])
    return float(x.mean()), float(lo), float(hi)


# E1: monitor agreement with ground truth (RQ1)
def e1_monitor_soundness(n=900, seed=0):
    """Run the automaton on the n traces of bench.build_monitor_suite and compare its
    verdict with the label. `accuracy` is the percentage of traces with the right
    verdict. per_class_recall is the percentage of planted violations of each class
    that the automaton rejects. A perfect run has 100.0 everywhere, which Thm. 1
    predicts when the suite satisfies A1 to A3 (the generator supplies the labels)."""
    rng = np.random.default_rng(seed)
    suite = bench.build_monitor_suite(rng, n)
    correct = 0
    n_adm = n_bad = 0
    per_class = {c: [0, 0] for c in bench.VIOLATION_CLASSES}   # [caught, total]
    for trace, dpa, label, vtype in suite:
        compliant, _ = dpa.monitor_trace(trace)
        pred = compliant
        if label:
            n_adm += 1
        else:
            n_bad += 1
            per_class[vtype][1] += 1
            if not pred:
                per_class[vtype][0] += 1
        if pred == label:
            correct += 1
    return {"n": n, "accuracy": round(100.0 * correct / n, 2),
            "n_admissible": n_adm, "n_violating": n_bad,
            "per_class_recall": {c: round(100.0 * a / max(t, 1), 1)
                                 for c, (a, t) in per_class.items()}}


# E2: conformal coverage (RQ1, Fig. 3a)
def e2_conformal_coverage(alphas=(0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30),
                          trials=300, n_cal=4000, n_eval=20000, seed=1):
    """Measure the conformal bound of Thm. 2 on the latent-risk pool.

    For each target alpha and each of `trials` calibration draws (n_cal examples), tau
    is selected with the marginal rank and with the exact-PAC rank. The pass-through
    P[admit | violation] and the utility are then estimated on an independent
    evaluation pool of n_eval examples, large enough that the estimation error is
    small next to the variation between calibration draws. A draw is "sound" if its
    realised pass-through is at most alpha. Marginal calibration only promises that
    the mean pass-through is at most alpha, and its sound fraction is therefore about one half.
    Exact-PAC promises a sound fraction of at least 1 - delta, and this is the
    comparison of Fig. 3a. Reports the mean and sd of the pass-through, the two sound
    fractions and the mean utility per alpha."""
    rng = np.random.default_rng(seed)
    delta = 0.05
    curve = []
    for a in alphas:
        pt, util, sound = [], [], []       # marginal-mode pass-through / utility
        pt_pac, sound_pac = [], []         # PAC-mode pass-through / per-draw sound
        for _ in range(trials):
            s_c, y_c = bench.build_risk_pool(rng, n_cal)
            s_e, y_e = bench.build_risk_pool(rng, n_eval)
            tau = calibrate_threshold(s_c, y_c, alpha=a)
            p = bench.violation_passthrough_rate(s_e, y_e, tau)
            pt.append(p); util.append(bench.benign_admit_rate(s_e, y_e, tau))
            sound.append(p <= a + 1e-9)
            tau_pac = calibrate_threshold(s_c, y_c, alpha=a, delta=delta, pac=True)
            p2 = bench.violation_passthrough_rate(s_e, y_e, tau_pac)
            pt_pac.append(p2); sound_pac.append(p2 <= a + 1e-9)
        pt = np.array(pt); util = np.array(util)
        curve.append({"alpha": a,
                      "passthrough": round(float(pt.mean()), 4),
                      "passthrough_sd": round(float(pt.std()), 4),
                      "sound_frac_marginal": round(float(np.mean(sound)), 4),
                      "passthrough_pac": round(float(np.mean(pt_pac)), 4),
                      "sound_frac_pac": round(float(np.mean(sound_pac)), 4),
                      "utility": round(float(util.mean()), 4)})
    return {"curve": curve, "trials": trials, "delta": delta,
            "mean_pass_le_alpha": bool(all(c["passthrough"] <= c["alpha"] + 1e-4
                                           for c in curve)),
            "overall_sound_frac_pac": round(
                float(np.mean([c["sound_frac_pac"] for c in curve])), 4)}


# E3: risk-utility frontier and detector quality (RQ1)
def e3_risk_utility(alphas=(0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30),
                    seps=(1.0, 1.5, 2.0, 2.6, 3.2), trials=200,
                    n_cal=4000, n_eval=20000, alpha0=0.10, fixed_tau=0.5, seed=2):
    """Two views of the calibrated threshold.

    frontier: with the default detector, the trade-off between the target alpha, the
    realised pass-through and the utility. An operator picks a point on it.

    detector sweep: at a fixed target alpha0 the detector quality (the separation of
    bench.build_risk_pool) is swept. The calibrated threshold is recomputed for each
    detector and holds the pass-through near alpha0. A fixed cutoff (admit iff the
    score is at most fixed_tau) is not recomputed, and its pass-through moves away
    from the target as the detector weakens. This is the "w/o calibration" ablation
    of Sect. 7. Marginal calibration is used in both views."""
    rng = np.random.default_rng(seed)
    frontier = []
    for a in alphas:
        pt, util = [], []
        for _ in range(trials):
            s_c, y_c = bench.build_risk_pool(rng, n_cal)
            tau = calibrate_threshold(s_c, y_c, alpha=a)
            s_e, y_e = bench.build_risk_pool(rng, n_eval)
            pt.append(bench.violation_passthrough_rate(s_e, y_e, tau))
            util.append(bench.benign_admit_rate(s_e, y_e, tau))
        frontier.append({"alpha": a, "passthrough": round(float(np.mean(pt)), 4),
                         "utility": round(float(np.mean(util)), 4)})
    robustness = []
    for sep in seps:
        cpt, cut, fpt, fut = [], [], [], []
        for _ in range(trials):
            s_c, y_c = bench.build_risk_pool(rng, n_cal, separation=sep)
            s_e, y_e = bench.build_risk_pool(rng, n_eval, separation=sep)
            tau = calibrate_threshold(s_c, y_c, alpha=alpha0)
            cpt.append(bench.violation_passthrough_rate(s_e, y_e, tau))
            cut.append(bench.benign_admit_rate(s_e, y_e, tau))
            fpt.append(bench.violation_passthrough_rate(s_e, y_e, fixed_tau))
            fut.append(bench.benign_admit_rate(s_e, y_e, fixed_tau))
        robustness.append({"separation": sep,
                           "conformal_passthrough": round(float(np.mean(cpt)), 4),
                           "conformal_utility": round(float(np.mean(cut)), 4),
                           "fixed_passthrough": round(float(np.mean(fpt)), 4),
                           "fixed_utility": round(float(np.mean(fut)), 4)})
    return {"frontier": frontier, "alpha0": alpha0, "fixed_tau": fixed_tau,
            "robustness": robustness}


# E4: layer decomposition on a mixed attack stream (RQ2)
def e4_attack_synth(alpha=0.10, trials=400, n=4000, delta=0.05, seed=3,
                    frac_explicit=0.35):
    """The mixed stream of Sect. 7. Each trial has n proposed actions. A share
    `frac_explicit` are explicit violations that the automaton refuses. The remaining
    actions are drawn from the latent-risk pool, where y = 1 is a disguised violation
    that only the score can flag. The reported rate is the fraction of attack actions
    (explicit plus latent violations) that execute under three configurations:
    unguarded, automaton only, and the full Deon guard with threshold tau calibrated
    on a separate pool of 4000 examples. tau uses the marginal rank at level alpha
    (`delta` is recorded in the output and unused by this rank), and the latent
    scores are exchangeable with the calibration scores by construction. The key
    policyshield_asr keeps the former project name and holds the Deon value."""
    rng = np.random.default_rng(seed)
    unguarded, dpaonly, full = [], [], []
    for _ in range(trials):
        s_cal, y_cal = bench.build_risk_pool(rng, 4000)
        tau = calibrate_threshold(s_cal, y_cal, alpha=alpha, delta=delta)
        # Latent part of the stream: benign and disguised-violation actions from the pool.
        n_soft = int(n * (1 - frac_explicit))
        s, y = bench.build_risk_pool(rng, n_soft)          # y=1 latent violation
        n_expl = n - n_soft                                 # explicit violations, refused by the automaton
        # Benign latent actions (y = 0) are not attacks and are excluded from the denominator.
        n_latent = int((y == 1).sum())
        n_attack = n_expl + n_latent
        if n_attack == 0:
            continue
        # Unguarded: every attack executes.
        unguarded.append((n_expl + n_latent) / n_attack)
        # Automaton only: explicit attacks are refused and every latent one executes.
        dpaonly.append(n_latent / n_attack)
        # Full guard: a latent violation executes only if its score is at most tau.
        exec_latent = int(((y == 1) & (s <= tau)).sum())
        full.append(exec_latent / n_attack)
    return {"alpha": alpha, "delta": delta, "frac_explicit": frac_explicit,
            "unguarded_asr": round(float(np.mean(unguarded)), 4),
            "dpa_only_asr": round(float(np.mean(dpaonly)), 4),
            "policyshield_asr": round(float(np.mean(full)), 4)}


# E6: content-dependent egress (RQ3, Fig. 3b)
def e6_content_egress(alpha=0.10, delta=0.05, seeds=30, n_cal=3000, n_eval=4000,
                      seed0=6):
    """RQ3. An egress action that the automaton permits leaks iff its text is
    sensitive. content.content_score scores the text and tau is calibrated with the
    exact-PAC rank on plaintext leaks. For each of `seeds` independent seeds the
    function reports the leak pass-through P[admit | leak] of three guards on a fresh
    plaintext test set and on an obfuscated one. The automaton alone is blind to
    content, and its pass-through is 1 by definition. Deon uses the calibrated tau, and
    the fixed-threshold baseline admits iff the score is at most 0.5. Plaintext
    leaks are exchangeable with the calibration leaks (assumption A4), and the
    obfuscated ones are not. The bound of Thm. 2 is therefore expected to hold in the first
    case and to fail in the second (Cor. 1(b)). The benign utility of both
    thresholds is recorded for the exchangeable case."""
    dpa_ex, ps_ex, fx_ex, util_ex, fx_util = [], [], [], [], []
    dpa_ad, ps_ad, fx_ad = [], [], []
    fixed_tau = 0.5
    for s in range(seeds):
        rng = np.random.default_rng(seed0 + s)
        # Calibrate on plaintext leaks with the exact-PAC rank, which controls the single draw.
        _, sc_c, y_c = content.build_content_pool(rng, n_cal)
        tau = calibrate_threshold(sc_c, y_c, alpha=alpha, delta=delta, pac=True)
        # Exchangeable test set.
        _, sx, yx = content.build_content_pool(rng, n_eval)
        leak = yx == 1
        dpa_ex.append(1.0)                                   # the automaton permits every such egress
        ps_ex.append(float((sx[leak] <= tau).mean()))        # conformal pass-through
        fx_ex.append(float((sx[leak] <= fixed_tau).mean()))  # external fixed guard
        util_ex.append(float((sx[~leak] <= tau).mean()))     # conformal benign utility
        fx_util.append(float((sx[~leak] <= fixed_tau).mean()))  # fixed benign utility
        # Adaptive test set: the leaks are obfuscated.
        _, sa, ya = content.build_content_pool(rng, n_eval, adaptive=True)
        la = ya == 1
        dpa_ad.append(1.0)
        ps_ad.append(float((sa[la] <= tau).mean()))
        fx_ad.append(float((sa[la] <= fixed_tau).mean()))
    def ci(x):
        m, lo, hi = _boot_ci(x)
        return {"mean": round(m, 4), "ci": [round(lo, 4), round(hi, 4)]}
    return {"alpha": alpha, "delta": delta, "seeds": seeds,
            "detector": "real keyword/pattern content-sensitivity detector",
            "exchangeable": {"dpa_only": ci(dpa_ex), "policyshield": ci(ps_ex),
                             "fixed_threshold": ci(fx_ex), "benign_utility": ci(util_ex),
                             "fixed_utility": ci(fx_util)},
            "adaptive": {"dpa_only": ci(dpa_ad), "policyshield": ci(ps_ad),
                         "fixed_threshold": ci(fx_ad)}}


# E7: detector ensemble on content egress (RQ4, extended version)
def e7_ensemble_egress(alpha=0.10, delta=0.05, seeds=30, n_cal=3000, n_eval=4000,
                       seed0=7):
    """Single detectors against their max-ensemble on the content-egress class.

    The three detectors of content.py are each calibrated on plaintext leaks with the
    exact-PAC rank. The ensemble score is the maximum of the three raw detector
    scores (content.ensemble_score). An action is scored as safe only if every
    detector agrees, and it is calibrated in the same way. The function reports the
    leak pass-through P[admit | leak] of each detector and of the ensemble under three
    test sets: plaintext leaks (exchangeable, with at most alpha expected),
    _obfuscate leaks (tuned against the lexical detector, which the other two should
    still see), and _naturalize leaks (built to evade all three). The protocol is
    the one of e6: `seeds` seeds and bootstrap intervals over them."""
    names = [n for n, _ in content.DETECTORS]
    D = len(names)
    # The template detectors of content.py are coarse and produce tied scores, whereas
    # a deployed neural detector emits continuous logits. Adding an i.i.d. uniform
    # perturbation of size 1e-6 to calibration and evaluation scores alike breaks the
    # ties at random, which is the randomised tie-break of Sect. 5, and the size is far
    # below the score granularity.
    EPS = 1e-6
    def jit(x, rng):
        return x + rng.uniform(0.0, EPS, size=np.shape(x))
    # One list per detector and one for the ensemble, each holding a mean per seed.
    ex_single = [[] for _ in range(D)]; ex_ens = []
    ad_single = [[] for _ in range(D)]; ad_ens = []
    nat_single = [[] for _ in range(D)]; nat_ens = []
    ex_util_single = [[] for _ in range(D)]; ex_util_ens = []
    for s in range(seeds):
        rng = np.random.default_rng(seed0 + s)
        # Calibrate every detector and the ensemble on plaintext leaks (exact-PAC).
        _, Sc, yc = content.build_multi_content_pool(rng, n_cal)
        Scj = jit(Sc, rng)
        taus = [calibrate_threshold(Scj[:, d], yc, alpha=alpha, delta=delta, pac=True)
                for d in range(D)]
        ens_c = jit(content.ensemble_score(Sc), rng)           # max over detectors
        tau_e = calibrate_threshold(ens_c, yc, alpha=alpha, delta=delta, pac=True)

        def passthrough(attack):
            _, S, y = content.build_multi_content_pool(rng, n_eval, attack=attack)
            Sj = jit(S, rng)
            leak = y == 1
            ps = [float((Sj[leak, d] <= taus[d]).mean()) for d in range(D)]
            ens = jit(content.ensemble_score(S), rng)
            pe = float((ens[leak] <= tau_e).mean())
            util = [float((Sj[~leak, d] <= taus[d]).mean()) for d in range(D)]
            ue = float((ens[~leak] <= tau_e).mean())
            return ps, pe, util, ue

        ps, pe, util, ue = passthrough("none")
        for d in range(D):
            ex_single[d].append(ps[d]); ex_util_single[d].append(util[d])
        ex_ens.append(pe); ex_util_ens.append(ue)
        ps, pe, _, _ = passthrough("obf")
        for d in range(D):
            ad_single[d].append(ps[d])
        ad_ens.append(pe)
        ps, pe, _, _ = passthrough("naturalize")
        for d in range(D):
            nat_single[d].append(ps[d])
        nat_ens.append(pe)

    def ci(x):
        m, lo, hi = _boot_ci(x)
        return {"mean": round(m, 4), "ci": [round(lo, 4), round(hi, 4)]}
    return {
        "alpha": alpha, "delta": delta, "seeds": seeds, "detectors": names,
        "combine": "max over detectors (safe iff all agree), randomised tie-break",
        "exchangeable": {
            "single": {names[d]: ci(ex_single[d]) for d in range(D)},
            "ensemble": ci(ex_ens),
            "single_utility": {names[d]: ci(ex_util_single[d]) for d in range(D)},
            "ensemble_utility": ci(ex_util_ens)},
        "adaptive_obf": {
            "single": {names[d]: ci(ad_single[d]) for d in range(D)},
            "ensemble": ci(ad_ens)},
        "adaptive_evade_all": {
            "single": {names[d]: ci(nat_single[d]) for d in range(D)},
            "ensemble": ci(nat_ens)}}


# E8: Mondrian against marginal calibration under a group shift (RQ4, extended version)
def e8_mondrian_shift(alpha=0.10, delta=0.05, seeds=30, n_cal=6000, n_eval=12000,
                      seed0=8):
    """Marginal against Mondrian (per-group) calibration when the group mix shifts.

    The latent-risk pool is split into three groups with different detector quality:
    easy (separation 3.0), medium (1.8) and hard (0.8). Calibration data have the group
    mix 0.6, 0.3, 0.1 and the test data are shifted to 0.1, 0.3, 0.6, that is, towards
    the hard group. Marginal calibration pools all groups into one threshold and
    Mondrian calibration uses one threshold per group, both with the exact-PAC rank.
    The function reports the pass-through per group, overall and for the worst group
    in each seed, together with the utility. A single marginal threshold protects the
    average violation and not each group, and it is expected to leak on the hard
    group. Note that the bound of Thm. 2 is a marginal statement, and per-group
    control is the motivation for the Mondrian variant."""
    groups = [("easy", 3.0), ("medium", 1.8), ("hard", 0.8)]
    p_cal = [0.6, 0.3, 0.1]
    p_test = [0.1, 0.3, 0.6]
    G = len(groups)
    marg_group = [[] for _ in range(G)]      # per-group pass-through, marginal tau
    mond_group = [[] for _ in range(G)]      # per-group pass-through, Mondrian tau
    marg_overall, mond_overall = [], []
    marg_util, mond_util = [], []
    for s in range(seeds):
        rng = np.random.default_rng(seed0 + s)
        # Calibration with the source group mix.
        cal_s, cal_y, tau_g = [], [], []
        for g, (_, sep) in enumerate(groups):
            ng = int(round(p_cal[g] * n_cal))
            sg, yg = bench.build_risk_pool(rng, ng, separation=sep)
            cal_s.append(sg); cal_y.append(yg)
            tau_g.append(calibrate_threshold(sg, yg, alpha=alpha, delta=delta, pac=True))
        alls = np.concatenate(cal_s); ally = np.concatenate(cal_y)
        tau_marg = calibrate_threshold(alls, ally, alpha=alpha, delta=delta, pac=True)
        # Test with the shifted group mix.
        v_marg = v_mond = v_tot = 0
        b_marg = b_mond = b_tot = 0
        for g, (_, sep) in enumerate(groups):
            ng = int(round(p_test[g] * n_eval))
            sg, yg = bench.build_risk_pool(rng, ng, separation=sep)
            vio = sg[yg == 1]; ben = sg[yg == 0]
            pm = float((vio <= tau_marg).mean()) if len(vio) else 0.0
            pc = float((vio <= tau_g[g]).mean()) if len(vio) else 0.0
            marg_group[g].append(pm); mond_group[g].append(pc)
            v_marg += int((vio <= tau_marg).sum()); v_mond += int((vio <= tau_g[g]).sum())
            v_tot += len(vio)
            b_marg += int((ben <= tau_marg).sum()); b_mond += int((ben <= tau_g[g]).sum())
            b_tot += len(ben)
        marg_overall.append(v_marg / max(v_tot, 1)); mond_overall.append(v_mond / max(v_tot, 1))
        marg_util.append(b_marg / max(b_tot, 1)); mond_util.append(b_mond / max(b_tot, 1))

    def ci(x):
        m, lo, hi = _boot_ci(x)
        return {"mean": round(m, 4), "ci": [round(lo, 4), round(hi, 4)]}
    gn = [g for g, _ in groups]
    return {
        "alpha": alpha, "delta": delta, "seeds": seeds, "groups": gn,
        "cal_mix": p_cal, "test_mix": p_test,
        "marginal": {"per_group": {gn[g]: ci(marg_group[g]) for g in range(G)},
                     "overall": ci(marg_overall), "utility": ci(marg_util),
                     "worst_group": ci([max(marg_group[g][i] for g in range(G))
                                        for i in range(seeds)])},
        "mondrian": {"per_group": {gn[g]: ci(mond_group[g]) for g in range(G)},
                     "overall": ci(mond_overall), "utility": ci(mond_util),
                     "worst_group": ci([max(mond_group[g][i] for g in range(G))
                                        for i in range(seeds)])}}


# E5: monitor time against trace length (timing result)
def e5_scalability(lengths=range(2, 13), reps=20000, seed=4):
    """Wall-clock time of the automaton alone (no detector, no score) over a trace of
    each length in `lengths`, in microseconds per whole trace. A trace is built by
    repeating the search and getProfile actions of a monitor-suite trace, which all
    pass. Each length is timed in 5 repetitions of `reps` runs, and the mean and sd
    over the repetitions are stored. check_results.py fits a line to the means and
    reports R^2, the near-linear cost claimed in Sect. 7 for the O(m) monitor.
    The values depend on the machine, unlike every other result in this file."""
    import core
    rng = np.random.default_rng(seed)
    out = []
    for m in lengths:
        suite = bench.build_monitor_suite(rng, 2)
        trace, dpa, _, _ = suite[0]
        # Pad or truncate to length m by repeating actions that the policy permits.
        base = [a for a in trace if a.name in ("search", "getProfile")] or trace
        tr = (base * (m // max(len(base), 1) + 1))[:m]
        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            for _ in range(reps):
                st = dpa.start()
                for a in tr:
                    ok, _, st = dpa.step(st, a)
            times.append((time.perf_counter() - t0) / reps * 1e6)   # us/trace
        times = np.array(times)
        out.append({"length": int(m), "us_mean": round(float(times.mean()), 3),
                    "us_sd": round(float(times.std()), 3)})
    return out


def main():
    """Run every experiment in the order below and write results/core_results.json."""
    outdir = ensure_dir(RESULTS)
    res = {}
    print("E1 monitor soundness ...");   res["e1_monitor_soundness"] = e1_monitor_soundness()
    print("E2 conformal coverage ...");  res["e2_conformal_coverage"] = e2_conformal_coverage()
    print("E3 risk-utility ...");        res["e3_risk_utility"] = e3_risk_utility()
    print("E4 attack (synthetic) ...");  res["e4_attack_synth"] = e4_attack_synth()
    print("E6 content egress (latent) ..."); res["e6_content_egress"] = e6_content_egress()
    print("E7 ensemble-of-scorers ...");  res["e7_ensemble_egress"] = e7_ensemble_egress()
    print("E8 Mondrian vs marginal shift ..."); res["e8_mondrian_shift"] = e8_mondrian_shift()
    print("E5 scalability ...");         res["e5_scalability"] = e5_scalability()
    with open(os.path.join(outdir, "core_results.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: (v if not isinstance(v, dict) or "curve" not in v else
                          {"overall_sound_frac": v.get("overall_sound_frac")})
                     for k, v in res.items()}, indent=2))


if __name__ == "__main__":
    main()
