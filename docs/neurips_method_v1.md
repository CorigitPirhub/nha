# Phase21 — NeurIPS/ICML Method Framing (V1)

Status: `v1-draft`  
Date: `2026-03-04`  
Scope: Dual-Path Router (Fast/Slow) mainline — *method-level* framing without changing the underlying design logic.

---

## 1. Problem: Risk-Bounded Adaptive Computation (RBAC)

We formalize dual-path routing as a **risk-bounded portfolio selection** problem.

For each query/sample \(x\), we must choose one of two compute actions (or “arms”):

- **fast**: low latency, may incur quality loss;
- **slow**: higher latency, treated as the *reference-quality* action.

Let the per-query outcomes be:

- latency \(T_{\texttt{fast}}(x),T_{\texttt{slow}}(x)\) (ms),
- quality proxy \(L_{\texttt{fast}}(x),L_{\texttt{slow}}(x)\) (e.g., expansions / path-cost proxy).

Define relative quality loss (slow is reference):
\[
\Delta L_{\text{rel}}(x)=\frac{L_{\texttt{fast}}(x)-L_{\texttt{slow}}(x)}{\max(L_{\texttt{slow}}(x),10^{-6})}.
\]

### Risk event (protocol)
For a router policy \(\pi(x)\in\{\texttt{fast},\texttt{slow}\}\), define the violation indicator
\[
Z_\pi(x)=\mathbf 1\{\pi(x)=\texttt{fast}\land \Delta L_{\text{rel}}(x)>\epsilon_{\text{rel}}\}.
\]
The violation probability is \(V(\pi)=\mathbb E[Z_\pi]\), with a fixed budget \(\alpha\).

This repo’s frozen default is:
- \(\epsilon_{\text{rel}}=1.5\%\),
- \(\alpha=5\%\),
see `docs/router_protocol_v1.md`.

### Objective (compute–quality tradeoff)
We use the same “normalized latency + quality penalty” style objective as Phase8/Phase11:
\[
J_\pi(x)=\frac{T_{\pi(x)}(x)}{T_{\text{ref}}}+\beta\cdot\max(\Delta L_{\text{rel}}(x),0),
\]
where \(T_{\text{ref}}\) is a reference latency scale (e.g., \(\text{median}(T_{\texttt{slow}})\)) and \(\beta\) maps quality loss into time units.

**Goal:**
\[
\min_\pi\ \mathbb E[J_\pi(x)]
\quad\text{s.t.}\quad
V(\pi)\le \alpha.
\]

---

## 2. C2D-RBAC: Counterfactual-to-Deployment RBAC Framework

This project’s key framing is a *systematic* workflow that connects:

1) **Counterfactual offline protocol** (frozen tables + risk definition),  
2) **A risk-bounded decision policy** (learned + calibrated),  
3) **A deployable artifact** (hash-tracked policy bundle),  
4) **Deployment alignment checks** (offline policy == system policy).

We call this pipeline **C2D-RBAC** (Counterfactual-to-Deployment Risk-Bounded Adaptive Computation).

### Offline counterfactual table
We assume an offline dataset where each row corresponds to a query \(x\), and contains *both* arms’ outcomes:
\[
\big(T_{\texttt{fast}}(x),L_{\texttt{fast}}(x),T_{\texttt{slow}}(x),L_{\texttt{slow}}(x)\big),
\]
plus features \(\phi(x)\) (static) and optional probe features \(\psi(x)\).

This is the core reason the method is not “just engineering”:
it enables **policy learning + certification + ablations** under an immutable metric definition, with deterministic manifests.

### Related-work alignment note (Phase22)
The **static routing** stage below is intentionally written in a way that is *directly comparable* to CDT/CRC-style conformal decision/risk-control methods. Phase22 implements those direct baselines and documents what portion of the performance gap they explain:
- `reports/router_phase22_direct_baselines_v1.md`
- `paper/related_work_neurips_alignment.md`

---

## 3. Algorithm 1 (Static): Conformal Cost-Aware Routing

### Inputs
- calibration table \(D_{\text{cal}}\), test table \(D_{\text{test}}\),
- protocol \((\epsilon_{\text{rel}},\alpha)\),
- a group key \(g(x)\) (default: difficulty bucket),
- models:
  - \(p_\theta(x)\): predicted violation probability under fast,
  - \(c_\eta(x)\): predicted compute gap \(c(x)=T_{\texttt{slow}}(x)-T_{\texttt{fast}}(x)\ge 0\),
- hyperparameters \(a,b>0\) for a compute-normalized score.

### Steps
1. **Fit risk model** on calibration:
   \[
   \hat y(x)=\mathbf 1\{\Delta L_{\text{rel}}(x)>\epsilon_{\text{rel}}\},
   \quad
   \hat p(x)=p_\theta(x)\approx \mathbb P(\hat y=1\mid \phi(x)).
   \]
2. **Split-conformalize** into an upper predictor \(\hat p^{\text{up}}(x)\) per group:
   \[
   \hat p^{\text{up}}(x)=\mathrm{clip}\big(\hat p(x)+q_{g(x)},0,1\big),
   \]
   where \(q_{g}\) is a one-sided split conformal quantile from \(D_{\text{cal}}\).
3. **Fit compute-gap model** on calibration:
   \[
   \hat c(x)=c_\eta(x)\approx \mathbb E[T_{\texttt{slow}}-T_{\texttt{fast}}\mid \phi(x)].
   \]
4. **Compute score** (risk-per-compute):
   \[
   u(x)=\frac{(\hat p^{\text{up}}(x))^a}{(\hat c_{\text{norm}}(x))^b},
   \quad \hat c_{\text{norm}}=\hat c / \mathrm{median}(\hat c).
   \]
5. **Route** by groupwise threshold \(\tau_g\):
   \[
   \pi(x)=\texttt{fast}\ \text{iff}\ u(x)\le \tau_{g(x)};\quad\text{else slow.}
   \]

In this repo, \(\tau_g\) can be selected by:
- fixed top-\(k\) slow flips per group (budget-equivalent), or
- calibration-time search to meet a risk gate (e.g., Wilson upper bound \(\le \alpha\)).

Implementation: `utils/router_method_core.py:ConformalStageRouter`.

### Extension (Phase23): Algorithm 1' (Portfolio, K≥3 arms)

To avoid being tied to a single fast/slow pair, we extend the static stage to a **portfolio** \(\mathcal A\) of \(K\ge 3\) arms (e.g., \(\{\texttt{fast},\texttt{mid},\texttt{slow}\}\)), keeping the same frozen risk semantics (\(\epsilon_{\mathrm{rel}}\), \(\alpha\)) with \(\texttt{slow}\) as reference.

Practical instantiation used in Phase23:
1. For each non-reference arm \(a\in\mathcal A\setminus\{\texttt{slow}\}\), fit a predictor on calibration for a *quality-loss proxy*
   \[
   y^{(a)}(x)=\max(\Delta L_{\mathrm{rel}}^{(a)}(x),0),
   \quad
   \hat y^{(a)}(x)\approx \mathbb E[y^{(a)}\mid \phi(x)].
   \]
2. Apply **groupwise one-sided split conformal** to obtain an upper predictor
   \[
   u^{(a)}(x)=\hat y^{(a)}(x)+q^{(a)}_{g(x)}.
   \]
3. Choose thresholds \((\tau_{\texttt{fast}},\tau_{\texttt{mid}},\dots)\) on the calibration split to satisfy a frozen risk gate (Wilson upper bound \(\le\alpha\)), and optionally add a small safety margin for distribution shift.
4. Route by monotone upgrade:
   \[
   \pi(x)=
   \begin{cases}
   \texttt{fast}, & u^{(\texttt{fast})}(x)\le \tau_{\texttt{fast}}\\
   \texttt{mid},  & u^{(\texttt{mid})}(x)\le \tau_{\texttt{mid}}\\
   \texttt{slow}, & \text{otherwise.}
   \end{cases}
   \]

This yields a risk-controlled **portfolio selection under a fixed protocol**, and enables Pareto analyses over \((J,\text{risk},\text{latency})\).

Implementation: `scripts/run_router_phase23_portfolio_v1.py`.

---

## 4. Algorithm 2 (Probe): Monotone Safe Flip-to-Slow

Static features \(\phi(x)\) can miss “hard-to-plan” dynamics. We introduce a *limited probe* computation that extracts \(\psi(x)\) (e.g., early expansion behavior, stagnation, bottleneck signals).

Starting from the static router \(\pi_c\), define a probe router \(\pi_p\) that is only allowed to **flip fast→slow**:
\[
\{x:\pi_p(x)=\texttt{fast}\}\subseteq \{x:\pi_c(x)=\texttt{fast}\}.
\]

Practical instantiation:
1. Fit a gain model on calibration:
   \[
   \hat g(x)\approx g(x)=J_{\texttt{fast}}(x)-J_{\texttt{slow}}(x).
   \]
2. Conformalize a **one-sided lower confidence bound (LCB)** on the signed gain (groupwise by difficulty):
   \[
   \mathrm{LCB}(x)=\hat g(x)-q_{g(x)}\quad\text{so that}\quad \mathbb P(g(x)\ge \mathrm{LCB}(x))\gtrsim 1-\alpha.
   \]
3. Under a mean-latency budget \(B\) (ms), select a subset of \(\pi_c\)-fast cases to flip to slow by a budgeted rule.
   A simple strict-audit-stable instantiation is a greedy knapsack on **LCB gain per cost**:
   \[
   s(x)=\frac{\mathrm{LCB}(x)}{c(x)}\quad (c=T_{\texttt{slow}}-T_{\texttt{fast}}),
   \]
   then flip the top-\(k\) by \(s(x)\) (per difficulty bucket), with \(k\) chosen on `calib_val` only.

Implementation:
- core abstraction: `utils/router_method_core.py:ProbeFlipRouter`.
- strict end-to-end runner: `scripts/run_router_phase8_strict.py` with `--probe-selection-mode knapsack_lcb` (writes `probe_strict_v4_knapsack_lcb`).

---

## 5. Minimal Guarantees (What We Can Prove in V1)

### Proposition 1 (Monotone safety)
If probe only flips \(\texttt{fast}\to\texttt{slow}\), then violation probability cannot increase:
\[
V(\pi_p)\le V(\pi_c).
\]

**Proof.** For any \(x\), if \(\pi_p(x)=\texttt{fast}\) then \(\pi_c(x)=\texttt{fast}\). Therefore
\[
Z_{\pi_p}(x)\le Z_{\pi_c}(x)\quad \forall x.
\]
Taking expectations yields \(V(\pi_p)\le V(\pi_c)\). ∎

### Proposition 2 (Score threshold as a Lagrangian optimum)
Consider a surrogate where slow has zero violations and only adds compute gap \(c(x)\ge 0\), and fast incurs risk proxy \(r(x)\in[0,1]\).
The constrained problem
\[
\min\ \mathbb E[c(x)\mathbf 1\{\pi(x)=\texttt{slow}\}]
\quad\text{s.t.}\quad
\mathbb E[r(x)\mathbf 1\{\pi(x)=\texttt{fast}\}]\le \alpha
\]
has a Lagrangian relaxation that decomposes pointwise: for some \(\lambda\ge 0\),
\[
\pi^\*(x)=\texttt{fast}\ \text{iff}\ \frac{r(x)}{c(x)}\le \frac{1}{\lambda}.
\]

**Proof.** The Lagrangian is
\[
\mathcal L(\pi,\lambda)=\mathbb E[c\mathbf 1\{\pi=\texttt{slow}\}]+\lambda\Big(\mathbb E[r\mathbf 1\{\pi=\texttt{fast}\}]-\alpha\Big).
\]
Dropping the constant \(-\lambda\alpha\), the per-\(x\) choice compares
- choose slow: cost \(c(x)\),
- choose fast: cost \(\lambda r(x)\).
Pick fast iff \(\lambda r(x)\le c(x)\), i.e. \(r(x)/c(x)\le 1/\lambda\). ∎

This explains why “risk-per-compute” ranking is a natural primitive; exponents \(a,b\) implement a simple robustness/shape control.

### Theorem 1 (One-sided split conformal upper bound)
Let \(y\) be any real-valued target and \(\hat y\) a predictor fit on training data.
Define nonconformity \(s_i=\max(y_i-\hat y_i,0)\) on an exchangeable calibration set of size \(n\), and let
\[
q=\mathrm{Quantile}_{\lceil (n+1)(1-\alpha)\rceil/n}(s;\ \texttt{higher}).
\]
Then for an independent test point, with probability at least \(1-\alpha\),
\[
y\le \hat y + q.
\]

This is the standard split conformal guarantee specialized to one-sided upper prediction.
In this repo we apply it groupwise (e.g., by difficulty).

Implementation: `utils/router_method_core.py:split_conformal_upper_q`.

---

## 6. Minimal Demo (Toy)

Run:
```bash
python scripts/run_router_phase21_minimal_demo.py
```

Artifacts:
- `outputs/router_phase21_neurips_positioning_v1/stats.json`

The demo constructs a synthetic counterfactual table and shows:
- forced-fast violates risk heavily,
- static conformal routing meets risk budget,
- probe flips can reduce \(J\) without increasing risk on this toy example (monotone safety); in real tasks, monotone safety does **not** imply \(J\) improves.

---

## 7. Mapping to This Repo’s Mainline (No Logic Change)

This framing does **not** change existing system logic. It provides:
- a method-level description (what is the algorithm, what are its guarantees),
- a minimal API for baselines/extensions,
- a minimal runnable demo for reviewers.

Key implementation entry points:
- frozen protocol: `docs/router_protocol_v1.md`
- deployable policy artifact: `artifacts/router_policy_v1/`
- core method API (Phase21): `utils/router_method_core.py`

---

## 8. Related Directions (for NeurIPS/ICML positioning; non-exhaustive)

This work sits at the intersection of:
- conformal decision-making / cost-aware conformal routing,
- conformal risk control / selective decision under risk,
- adaptive computation / budgeted prediction / algorithm portfolios,
- meta-reasoning (“when to compute more”) with monotone-safe escalation.

Pointers to align against in Step 7 (direct baselines):

### Conformal decision-making / risk control
- Conformal Decision Theory (CDT): https://arxiv.org/abs/2310.05921  
- Conformal Risk Control (CRC): https://research.google/pubs/conformal-risk-control/  

### Selective prediction / abstention (with and without cost)
- SelectiveNet (deep selective classification): https://arxiv.org/abs/1901.09192  
- Conformal prediction sets for classification (background; many variants): https://arxiv.org/abs/2107.07511  

### Adaptive computation / budgeted prediction
- Adaptive Computation Time (ACT): https://arxiv.org/abs/1603.08983  

### Algorithm selection / portfolios (broad background)
- Algorithm Selection problem (classical formulation): Rice, J. R. “The Algorithm Selection Problem”, *Advances in Computers*, 1976.

---

## 9. Limitations (must be stated explicitly)

1. The risk event only covers \(\Delta L_{\text{rel}}>\epsilon_{\text{rel}}\) as defined by the frozen protocol; it is not “all safety”.
2. Split conformal requires exchangeability (or explicit shift handling); robust shift certificates require extra assumptions (see `docs/router_theory_v2.md`).
3. Probe monotone safety only holds if probe never flips slow→fast.
4. Probe is a **risk-safe escalation** mechanism; it may increase latency and therefore may not improve \(J\) unless the flipped cases avoid sufficiently large quality penalties.
