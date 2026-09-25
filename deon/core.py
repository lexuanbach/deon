"""Core of Deon: the deontic policy automaton and the conformal execution guard.

The paper (Sect. 2 and Sect. 5) places two runtime checks between an untrusted
proposer and the executor. This module implements both in plain Python with numpy.
scipy is optional and only speeds up the binomial tail.

Sound layer (Sect. 2, Def. 1 and Def. 2, Thm. 1). Action mirrors an action of Def. 1:
the fields it reads and writes, an optional egress sink with a clearance level, and an
optional metered resource. Policy holds the deontic policy Pi: prohibited operations,
permission preconditions (require_before, with the propositions granted by earlier
actions), quotas, obligations, and the default field labelling lambda_0 over the
lattice public < internal < pii < secret. DPAState is the monitor state
q = (sigma, u, Omega, lambda), stored as props, used, pending and field_level.
DeonticPolicyAutomaton.step is the transition function delta. It checks the four
clauses of Def. 2 in order: forbidden operation, permission precondition, explicit or
laundered flow to a sink, quota. finalize is the predicate fin (no pending
obligation). A step is a bounded number of dictionary and set lookups that read only
the state and the policy. A trace of length m therefore costs O(m), which is the
near-linear timing reported in Sect. 7.

Statistical layer (Sect. 5, Thm. 2). calibrate_threshold selects the admission
threshold tau as an order statistic of the violation scores in a labelled calibration
sample. The marginal rank is k = floor(alpha (n_v + 1)) and the PAC rank is the
largest k' with P[Bin(n_v, alpha) >= k'] >= 1 - delta. The rule "admit iff score <=
tau" then bounds the pass-through P[admit | violation] when calibration and deployment
violation scores are exchangeable (assumption A4). For tied scores,
calibrate_randomized_threshold and randomized_admit implement the paper's exact
augmented-score rule with independent uniform variates.

Guard.decide combines the two layers into the verdict of Sect. 2: block if the
automaton refuses, abstain if the score exceeds tau, admit otherwise. The experiment
scripts apply the same threshold rule directly to arrays of scores. Guard documents
the interface and is not exercised by the reported measurements.

Everything here is deterministic. All randomness lives in the callers, which pass
seeded numpy generators (see bench.py and experiments_*.py). The directory and the
module names keep the former project name policyshield.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Callable
import math
import numpy as np

# Totally ordered privacy lattice public < internal < pii < secret. The join of two
# labels is their maximum, which is what the label propagation in step() uses.
LEVELS = {"public": 0, "internal": 1, "pii": 2, "secret": 3}
_LEVEL_NAME = {v: k for k, v in LEVELS.items()}   # inverse map, turns a join back into a label


# Deontic policy and deontic policy automaton (Sect. 2, Def. 1 and Def. 2)
@dataclass
class Action:
    """An action in the sense of Def. 1: a service invocation proposed by the agent.

    The read and write sets carry the field names whose labels the flow rule tracks.
    A sink makes the action an egress with the given clearance. The default "secret"
    means that a sink with no stated clearance accepts every label. In the paper these
    fields come from the catalogue owner (assumption A1) and never from the proposer.
    `text` is a free-text rendering for score-based detectors and the automaton
    ignores it.
    """
    name: str                              # DPA event label / operation id
    reads: Set[str] = field(default_factory=set)      # data fields consumed
    writes: Set[str] = field(default_factory=set)     # data fields produced
    sink: Optional[str] = None             # if an egress, the sink name
    sink_clearance: str = "secret"         # clearance level the sink is cleared for
    resource: Optional[str] = None         # quota-metered resource id
    text: str = ""                         # raw NL rendering (for the risk scorer)


@dataclass
class Policy:
    """A deontic policy Pi = (permit, forbid, oblig) as in Def. 2.

    prohibited_actions : operations that are never permitted (part of forbid)
    field_level        : default label lambda_0 of each field, used by the explicit
                         flow ban (part of forbid)
    require_before     : action -> propositions that must already hold, the permission
                         preconditions (permit), for example 'authenticated'
    grants             : action -> propositions it establishes once executed
    obligations        : trigger action -> the one action that must occur later in the
                         trace (oblig). Pending obligations are Boolean eventualities:
                         repeated triggers coalesce rather than create counted or
                         transaction-correlated instances.
    quota              : resource -> maximum number of invocations in one trace (part
                         of forbid)
    """
    prohibited_actions: Set[str] = field(default_factory=set)
    field_level: Dict[str, str] = field(default_factory=dict)
    require_before: Dict[str, Set[str]] = field(default_factory=dict)
    grants: Dict[str, Set[str]] = field(default_factory=dict)
    obligations: Dict[str, str] = field(default_factory=dict)
    quota: Dict[str, int] = field(default_factory=dict)


@dataclass
class DPAState:
    """Monitor state q = (sigma, u, Omega, lambda) of Def. 1.

    The automaton never mutates a state. step() builds a fresh object for the
    successor and hands back the old one unchanged when it refuses an action.
    """
    props: Set[str] = field(default_factory=set)          # established propositions
    used: Dict[str, int] = field(default_factory=dict)    # resource -> invocations
    pending: Set[str] = field(default_factory=set)         # obligation-actions owed
    field_level: Dict[str, str] = field(default_factory=dict)


class DeonticPolicyAutomaton:
    """The deontic policy automaton M_Pi of Def. 2, run as an online monitor.

    step() returns (permitted, reason, next_state) for a candidate action in the
    current state. `reason` names the failed clause and is empty on success.
    finalize() returns (compliant, reason) at the end of a trace and lists every
    obligation that is still pending. Admission depends only on the policy and the
    executed prefix and never on what the proposer says about the action, which is
    what Thm. 1 needs together with A1 to A3. `init_props` and `init_level` seed
    sigma and lambda for a session that starts with facts already established.
    """

    def __init__(self, policy: Policy, init_props: Optional[Set[str]] = None,
                 init_level: Optional[Dict[str, str]] = None):
        self.p = policy
        self.init_props = set(init_props or set())
        self.init_level = dict(init_level or {})

    def start(self) -> DPAState:
        return DPAState(props=set(self.init_props), used={}, pending=set(),
                        field_level=dict(self.init_level, **self.p.field_level))

    def step(self, st: DPAState, a: Action) -> Tuple[bool, str, DPAState]:
        """The transition delta(q, a) of Def. 2. The clauses run in the order (i) to
        (iv) of the paper and the first failing one is reported."""
        # clause (i): forbidden operation
        if a.name in self.p.prohibited_actions:
            return False, f"prohibited action '{a.name}'", st
        # clause (ii): permission precondition (sequencing)
        need = self.p.require_before.get(a.name, set())
        missing = need - st.props
        if missing:
            return False, f"'{a.name}' requires {sorted(missing)} first", st
        # clause (iii): a field labelled above the sink clearance may not reach it
        if a.sink is not None:
            clr = LEVELS.get(a.sink_clearance, 3)
            for f in a.reads:
                lvl = LEVELS.get(st.field_level.get(f, "public"), 0)
                if lvl > clr:
                    return False, (f"field '{f}' ({st.field_level.get(f,'public')})"
                                   f" flows to sink '{a.sink}' ({a.sink_clearance})"), st
        # clause (iv): quota on the metered resource
        if a.resource is not None and a.resource in self.p.quota:
            if st.used.get(a.resource, 0) + 1 > self.p.quota[a.resource]:
                return False, f"quota exceeded on '{a.resource}'", st
        # The action is permitted. Build the successor state.
        ns = DPAState(props=set(st.props), used=dict(st.used),
                      pending=set(st.pending), field_level=dict(st.field_level))
        ns.props |= self.p.grants.get(a.name, set())
        # Label propagation of Sect. 2: a written field takes the join of its default
        # label and the labels of everything the action read. Without this rule a
        # copy of a pii field would carry the default label of the new field and
        # could reach a sink cleared only for internal data (laundering). The rule
        # works at the granularity of whole fields.
        read_lvl = max((LEVELS.get(st.field_level.get(r, "public"), 0)
                        for r in a.reads), default=0)
        for f in a.writes:
            default_lvl = LEVELS.get(self.p.field_level.get(f, "internal"), 1)
            ns.field_level[f] = _LEVEL_NAME[max(default_lvl, read_lvl)]
        if a.resource is not None:
            ns.used[a.resource] = ns.used.get(a.resource, 0) + 1
        # Discharge an obligation owed by the old prefix before registering any
        # obligation triggered by this action.  This order gives "later" its literal
        # meaning when an action obliges another occurrence of itself.
        ns.pending.discard(a.name)
        if a.name in self.p.obligations:
            ns.pending.add(self.p.obligations[a.name])
        return True, "", ns

    def finalize(self, st: DPAState) -> Tuple[bool, str]:
        if st.pending:
            return False, f"undischarged obligation(s) {sorted(st.pending)}"
        return True, ""

    def monitor_trace(self, trace: List[Action]) -> Tuple[bool, str]:
        """Run a whole trace. True iff every step is permitted and fin holds at the
        end, which is the acceptance condition of Def. 2 ("M_Pi admits pi")."""
        st = self.start()
        for a in trace:
            ok, reason, st = self.step(st, a)
            if not ok:
                return False, reason
        return self.finalize(st)


# Conformal execution guard (Sect. 5, Thm. 2)
# Upper standard-normal quantiles z_{1-delta} for the Wilson bound below. Only the
# listed deltas are tabulated and any other value falls back to delta = 0.10. The
# exact-PAC rank (_pac_rank) does not use this table.
_Z = {0.20: 0.8416, 0.10: 1.2816, 0.05: 1.6449, 0.01: 2.3263}


def _z(delta: float) -> float:
    return _Z.get(round(delta, 2), 1.2816)


def wilson_ucb(k: int, m: int, delta: float) -> float:
    """One-sided Wilson-score upper confidence bound on a Bernoulli rate. With
    probability about 1 - delta the true rate is below the returned value. The
    interval is closed-form and tighter than Hoeffding at low rates. It returns 1.0
    (vacuous) when m = 0. This bound is not used by the reported results, which
    control the pass-through with calibrate_threshold, and is kept for estimating
    the violation rate among admitted actions."""
    if m == 0:
        return 1.0
    z = _z(delta)
    p = k / m
    denom = 1.0 + z * z / m
    centre = p + z * z / (2 * m)
    half = z * math.sqrt(p * (1 - p) / m + z * z / (4 * m * m))
    return min(1.0, (centre + half) / denom)


def hoeffding_ucb(k: int, m: int, delta: float) -> float:
    """One-sided distribution-free Hoeffding upper bound: with probability at least
    1 - delta the true rate is at most k/m + sqrt(ln(1/delta) / (2m)). Like
    wilson_ucb it is an auxiliary estimator and does not enter the paper's results."""
    if m == 0:
        return 1.0
    return min(1.0, k / m + math.sqrt(math.log(1.0 / delta) / (2.0 * m)))


def calibrate_threshold(scores: np.ndarray, labels: np.ndarray,
                        alpha: float, delta: float = 0.05,
                        pac: bool = False) -> float:
    """Select the admission threshold tau of the conformal guard (Sect. 5, Thm. 2).

    scores[i] is the nonconformity score of example i (higher means more violation
    like) and labels[i] is 1 for a true violation and 0 otherwise. The test-time rule
    is to admit an action iff its score is at most tau. Only the violation scores
    are used. With v_(1) <= ... <= v_(n_v) the sorted violation scores, tau = v_(k).

    Marginal mode (pac=False) takes k = floor(alpha (n_v + 1)). If a fresh violation
    score is exchangeable with the calibration violation scores (A4) and untied, the
    probability that it scores at most tau, that is, the pass-through, is at most
    alpha (Thm. 2(i)). This holds on average over calibration draws, and an individual
    draw can therefore miss the target, as the RQ1 coverage measurement shows.

    PAC mode (pac=True) is the training-conditional variant of Thm. 2(ii). The
    coverage F(v_(k)) of an order statistic of i.i.d. continuous scores follows
    Beta(k, n_v + 1 - k), and P[F(v_(k)) <= alpha] = P[Bin(n_v, alpha) >= k]. We take
    the largest k whose binomial survival is at least 1 - delta. The realised
    pass-through is at most alpha with probability at least 1 - delta over the
    calibration draw. The statement is exact for finite n_v and uses no normal
    approximation.

    Edge cases. We define v_(0) = -inf. With no calibration violation or with a
    certified rank below 1, the admitted score region is therefore empty. Ties among
    scores are not broken here; use calibrate_randomized_threshold and
    randomized_admit for the executable augmented-score rule.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between 0 and 1")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must lie strictly between 0 and 1")
    v = np.sort(scores[labels == 1])
    n_v = len(v)
    if n_v == 0:
        return -math.inf                       # conservative all-abstain fallback
    if pac:
        k = _pac_rank(n_v, alpha, delta)       # exact binomial-tail rank
    else:
        k = int(math.floor(alpha * (n_v + 1)))  # marginal conformal rank
    if k < 1:
        return -math.inf                       # v_(0): empty admitted region
    k = min(k, n_v)
    return float(v[k - 1])


def calibrate_randomized_threshold(scores: np.ndarray, labels: np.ndarray,
                                   alpha: float, rng: np.random.Generator,
                                   delta: float = 0.05,
                                   pac: bool = False) -> Tuple[float, float]:
    """Return the augmented threshold ``(score, u)`` for tied/discrete scores.

    Each calibration violation receives an independent ``U ~ Uniform(0,1)`` and
    pairs are ordered lexicographically. A test violation receives its own independent
    uniform variate and is admitted exactly when its pair is at most the returned
    pair. This is an executable randomized-rank rule, not an evaluation-oracle split
    computed from the test population.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between 0 and 1")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must lie strictly between 0 and 1")
    v = np.asarray(scores[labels == 1], dtype=float)
    n_v = len(v)
    if n_v == 0:
        return -math.inf, 0.0
    k = _pac_rank(n_v, alpha, delta) if pac else int(math.floor(alpha * (n_v + 1)))
    if k < 1:
        return -math.inf, 0.0
    u = rng.random(n_v)
    order = np.lexsort((u, v))
    idx = order[min(k, n_v) - 1]
    return float(v[idx]), float(u[idx])


def randomized_admit(score: float, threshold: Tuple[float, float],
                      rng: np.random.Generator) -> bool:
    """Apply the randomized augmented-score admission rule to one test score."""
    tau, tau_u = threshold
    test_u = float(rng.random())
    return score < tau or (score == tau and test_u <= tau_u)


def _binom_pmf_log(j: int, n: int, p: float) -> float:
    """log P[Bin(n,p) = j], exact via lgamma and safe for large n (no overflow)."""
    if p <= 0.0:
        return 0.0 if j == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if j == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
            + j * math.log(p) + (n - j) * math.log1p(-p))


def _binom_sf(k: int, n: int, p: float) -> float:
    """Exact binomial survival P[Bin(n, p) >= k] without scipy. The log-space pmf is
    summed over the shorter tail for numerical stability at large n. calibrate_threshold
    does not call it, because _pac_rank has its own vectorised version. It serves
    as an independent reference for checking that rank."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if k > n - k:                              # right tail is shorter
        return sum(math.exp(_binom_pmf_log(j, n, p)) for j in range(k, n + 1))
    return 1.0 - sum(math.exp(_binom_pmf_log(j, n, p)) for j in range(0, k))


def _pac_rank(n_v: int, alpha: float, delta: float) -> int:
    """Largest rank k in [1, n_v] with P[Bin(n_v, alpha) >= k] >= 1 - delta, or 0 if
    no rank qualifies. This is the PAC rank k' of Sect. 5. Because
    P[Bin(n_v, alpha) >= k] equals P[F(v_(k)) <= alpha] for the order-statistic
    coverage F(v_(k)) ~ Beta(k, n_v + 1 - k), the choice gives the training-conditional
    guarantee of Thm. 2(ii). It uses scipy.stats.binom when scipy is installed. The
    fallback sums the same exact pmf in log space, and both paths return identical
    ranks."""
    try:
        from scipy.stats import binom
        ks = np.arange(1, n_v + 1)
        sf = binom.sf(ks - 1, n_v, alpha)      # P[Bin(n_v, alpha) >= k]
        ok = np.where(sf >= 1.0 - delta)[0]
        return int(ks[ok.max()]) if len(ok) else 0
    except Exception:
        # Scipy-free path. Build the whole pmf in log space with lgamma, form the
        # survival by a reverse cumulative sum, and take the largest rank with
        # survival >= 1 - delta.
        j = np.arange(0, n_v + 1)
        lg = np.array([math.lgamma(x + 1) for x in j])          # log of j factorial
        logpmf = (lg[n_v] - lg - lg[::-1]                       # log C(n,j)
                  + j * math.log(alpha) + (n_v - j) * math.log1p(-alpha))
        pmf = np.exp(logpmf)
        # The survival at k is P[Bin >= k], the sum of pmf[j] over j >= k, a reverse cumulative sum.
        surv = np.cumsum(pmf[::-1])[::-1]                        # surv[k]=P[Bin>=k]
        ks = np.arange(1, n_v + 1)
        sf = surv[ks]                                           # P[Bin(n,alpha)>=k]
        ok = np.where(sf >= 1.0 - delta)[0]
        return int(ks[ok.max()]) if len(ok) else 0


# The three verdicts of Sect. 2.
ADMIT, ABSTAIN, BLOCK = "admit", "abstain", "block"


@dataclass
class Guard:
    """The Deon guard: the automaton (sound layer) followed by the score threshold.

    tau comes from calibrate_threshold and `scorer` maps an action and the current
    state to a nonconformity score. decide() returns one of three verdicts. BLOCK
    means the automaton refused the action, with a typed reason and the state
    unchanged. ABSTAIN means the automaton permitted it but the score exceeds tau, so
    the action is not certified and is not executed. ADMIT means the action executes
    and the state advances.
    """
    dpa: DeonticPolicyAutomaton
    tau: float
    scorer: Callable[[Action, DPAState], float]

    def decide(self, st: DPAState, a: Action) -> Tuple[str, str, DPAState]:
        permitted, reason, ns = self.dpa.step(st, a)
        if not permitted:
            return BLOCK, reason, st           # refusal leaves q unchanged (self-loop in Fig. 1)
        if self.scorer(a, st) > self.tau:
            return ABSTAIN, "conformal score above certified threshold", st
        return ADMIT, "", ns
