# Router Method Framing (V1, Dual-Layer)

Status: `living-doc`  
Date: `2026-03-06`

This file now uses a **dual-layer narrative**:
1. **Current strict mainline**: `Risk-Calibrated Single-Search Compute Shaping / Weighted-Search Tree Portfolio`.
2. **Historical mainline**: `Dual-Path Probe Router (P5 -> P6)`.

The reason for this split is empirical, not cosmetic:
- under the fully audited strict semantics, the old **probe-router** claim no longer holds as the main positive claim;
- the new **zero-probe single-search weighted-search** line *does* pass `Phase29 -> Phase13 -> Phase22` end-to-end.

Current evidence roots:
- `reports/router_phase29_step12r4_trials_v1.md`
- `reports/router_phase13_sota_v10_strict_weighted_tree_o.md`
- `reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md`
- `TASK.md`
- `reports/router_phase30_step14_trials_v1.md` (Step 14 successor-family screening, phase30 `A/B/C/D`; no replacement promoted)
- `reports/router_phase31_step14_fresh_trials_v1.md` (Step 14 successor-family screening, phase31 `E/F/G/H`; no replacement promoted)
- `reports/router_phase32_step14_tarp_line_v1.md` (Step 14 continuation along the `14-F / TARP-WA` response-regime line; no replacement promoted)
- `reports/router_phase32_step14_tarp_line_f2b_hgb_v1.md` (targeted higher-capacity follow-up for `TARP-RRMIX`; still no replacement promoted)
- `reports/router_phase33_step14_rcwsb_trials_v1.md` (final Step 14 sprint along the `RCWS-B` line; no replacement promoted)
- `reports/router_phase33_step14_rcwsb_b1_followup_v1.md` (higher-capacity follow-up for `RCWS-B-Direct`; still no replacement promoted)
- `TASK.md` now treats `P0-CX` as the active RS-grounded base-model innovation line; after the `CX34-A` recheck audit, the accepted paper-facing RS branch switched from refined `RS-HPG` to `RS + CX34-A / Subtype-Specific Macro Rescue` (`paper/rs_cx_current_claim_contract.md`). The canonical public evidence root is `reports/rs_p0cx34_round1_summary.md`, the recheck / merge audit is `reports/rs_p0cx34_recheck_audit_v1.md`, the full-support invariance audit remains `reports/rs_p0cx34_standard_audit_v1.md`, and the frozen hard-test eval is `reports/rs_p0cx34_a_hard_eval_v1.md`. The branch now has positive hard-test evidence overall, but it still carries high runtime overhead and unresolved family/path caveats. Separately, the leading fusion candidate is now `RS + CX34-A + CX42-B / Query Compatibility Release`, tracked in `paper/rs_cx_fusion_candidate_contract.md`; after the unified public rerun `reports/rs_p0cx42_public_compare_v1.md`, it should be treated as a hard-runtime compatibility candidate rather than a confirmed public upgrade over `CX34-A`.

Historical strict negative evidence:
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`
- `outputs/final_v5_strict/manifest.json`

Protocol references:
- frozen protocol source of truth: `docs/router_protocol_v1.md`
- current-mainline companion note: `docs/router_protocol_v1_current_mainline_note.md`
- frozen paper-facing claim contract: `paper/router_current_mainline_claim_contract.md`

## Frozen paper claim contract

For paper writing, the claim contract is frozen in `paper/router_current_mainline_claim_contract.md`.
Use that file when you need:
- the exact current main claim sentence,
- the exact scope of validity,
- the required non-claims and caveats.

Use this file for the **method decomposition and positioning details**, not to override the paper-facing contract.

---

## 1. Shared Problem: Risk-Bounded Adaptive Computation (RBAC)

For each planning query/sample `x`, the protocol exposes one or more candidate compute actions (“arms”) `a in A`, each with:
- latency `T_a(x)` in ms,
- quality proxy `L_a(x)`,
- a frozen reference arm `slow`.

Relative quality loss w.r.t. `slow` is:
\[
\Delta L_{\mathrm{rel}}^{(a)}(x)=\frac{L_a(x)-L_{\texttt{slow}}(x)}{\max(L_{\texttt{slow}}(x),10^{-6})}.
\]

Protocol risk event:
\[
Z_\pi(x)=\mathbf 1\{\pi(x)\neq \texttt{slow}\ \land\ \Delta L_{\mathrm{rel}}^{(\pi(x))}(x)>\epsilon_{\mathrm{rel}}\},
\]
with frozen default:
- `epsilon_rel = 0.015`
- `alpha = 0.05`

Objective:
\[
J_\pi(x)=\frac{T_{\pi(x)}(x)}{T_{\mathrm{ref}}}+\beta\cdot\max\bigl(\Delta L_{\mathrm{rel}}^{(\pi(x))}(x),0\bigr).
\]

Important protocol note from `docs/router_protocol_v1.md`:
- `L` is a **search-quality proxy**;
- default `L` in this repo is **node expansions**;
- when expansions are unavailable, path-cost proxy is the fallback.

This detail matters for interpreting the current positive result: the new weighted-search line wins under the **frozen protocol as implemented**, where `L` is expansions plus a path-length audit, not pure path cost.

---

## 2. Current Mainline: Risk-Calibrated Compute Shaping

### 2.1 Core idea

The current method no longer spends extra compute on an external probe and then flips `fast -> slow`.
Instead, it keeps the **same A* search skeleton** and chooses an internal compute level `w(x)`:
\[
\pi(x)\in \{\texttt{fast},\texttt{wa\_w105},\ldots,\texttt{wa\_w135},\texttt{slow}\}.
\]

For weighted A*, the search score is:
\[
f_w(n)=g(n)+w\,h(n),\qquad w\ge 1.
\]

The deployable best policy is currently:
- **`O / TreeWeightPortfolio`**: a shallow tree over `static + fastgeom + difficulty`, with one arm assigned to each leaf;
- **`P / TreeWeightSlowFallback`**: same family with optional `slow` fallback, but under the current strict data it is numerically identical to `O`.

Repo mapping:
- arm-table generation: `scripts/run_router_phase29_step12r4_trials_v1.py:_build_weight_tables`
- fastgeom features: `scripts/run_router_phase29_step12r4_trials_v1.py:_make_fastgeom_tables`
- tree selector: `scripts/run_router_phase29_step12r4_trials_v1.py:_run_tree_portfolio`
- deployable per-seed policy artifacts: `outputs/router_phase29_o_tree_weight_v1/seeds/seed_*/`

### 2.2 Why this is methodologically different from the old probe line

The key change is where adaptive computation happens:
- **old line**: compute `probe(x)` first, then decide whether to switch planner arm;
- **current line**: the main planner itself is the adaptive object, via `w(x)`.

So the strict latency semantics change from
\[
T_{\mathrm{total}}=T_{\pi(x)}+T_{\mathrm{probe}}
\]
to
\[
T_{\mathrm{total}}=T_{w(x)}.
\]

This removes the additive `+ T_probe` term that dominated the old strict audit failure.

### 2.3 What is actually doing the work in the current positive result

Empirically, the gain comes from **two nested levels**, with very different magnitudes:
1. **Big gain**: introducing the weighted-search arm family itself.
2. **Small gain**: choosing among those arms with a tree partition.

From `outputs/router_phase29_step12r4_trials_v1/summary.json`:
- `M / WAStarConst`: pooled `mean_delta_j ≈ 15.442559`
- `N / DifficultyWeightPortfolio`: pooled `mean_delta_j ≈ 15.443174`
- `O / TreeWeightPortfolio`: pooled `mean_delta_j ≈ 15.443633`

So the tree selector is only a **small refinement** over a constant/difficulty-level weight choice.
This should be stated honestly in any paper version:
- the dominant innovation is **zero-probe compute shaping with weighted-search arms**;
- the tree portfolio is the cleanest deployable selector on top of that family, but not the sole source of the gain.

### 2.4 Current strict evidence that is actually supported

Under the fully audited strict semantics, the following statement is supported by the code + outputs:

> A zero-probe single-search compute-shaping policy, implemented as a weighted-search tree portfolio and selected on `calib_train/calib_val`, significantly improves the frozen strict objective `J` over the strongest same-protocol baseline and over the matched direct-baseline family.

Evidence:
- Phase29 screening: `reports/router_phase29_step12r4_trials_v1.md`
- Phase13 strongest-baseline result: `outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`
- Phase22 direct-baseline result: `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`

### 2.5 Honest caveats for the current line

1. The current positive claim is **not** “the old probe router survived strict auditing.”
2. The current protocol uses `L = node expansions` as the primary quality proxy, with path-length only as an auxiliary audit.
3. `Phase22` now uses `weighted_search_slow_fallback_cap` parity; for the realized best policy the cap is `0`, so CRC/CDT collapse to `P5` under that parity.
4. Therefore the strongest honest phrasing is:
   - the new single-search weighted-search compute-shaping family beats `P5` and the matched direct-baseline family **under the frozen strict protocol**.

---

## 3. Historical Mainline: Dual-Path Probe Router (Retained as Audit/Background)

### 3.1 Stage-1 (`P5`): Conformal Cost-Aware Routing

The historical static stage uses deployable static features `phi(x)` to estimate:
- violation probability under `fast`,
- compute gap between `slow` and `fast`.

Score:
\[
u(x)=\frac{(\hat p^{\mathrm{up}}(x))^a}{(\hat c_{\mathrm{norm}}(x))^b}.
\]

Route by groupwise threshold `tau_g`:
\[
\pi_{P5}(x)=\texttt{fast}\iff u(x)\le \tau_{g(x)}.
\]

Repo mapping:
- strict implementation: `scripts/run_router_phase8_strict.py:_run_conformal_seed`
- abstraction: `utils/router_method_core.py:ConformalStageRouter`

### 3.2 Stage-2 (`P6`): Probe flip-to-slow

The historical second stage adds a limited probe and only allows `fast -> slow` upgrades.

Signed gain target:
\[
g(x)=J_{\texttt{fast}}(x)-J_{\texttt{slow}}(x).
\]

Strict deployment version uses a one-sided LCB and budgeted selection.

Repo mapping:
- strict runner: `scripts/run_router_phase8_strict.py:_run_probe_seed`
- abstraction: `utils/router_method_core.py:ProbeFlipRouter`

### 3.3 What still remains valid from the historical line

The historical line is still valuable for:
- the RBAC framing itself,
- deployable conformal routing abstractions,
- monotone safety theory for upgrade-only probe policies,
- negative evidence about why additive probe cost breaks the old `J` claim in strict mode.

### 3.4 What is no longer valid as the current main claim

This statement is **not** supported anymore as the main strict claim:

> Probe routing (`P6`) significantly improves `J` over the conformal baseline (`P5`) under the fully audited strict semantics.

See:
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`
- `outputs/final_v5_strict/manifest.json`

---

## 4. How to cite the method correctly now

### If you are writing the **current main method**
Use:
- **Risk-Calibrated Compute Shaping**
- **Weighted-Search Tree Portfolio**
- **zero-probe single-search adaptive computation**

### If you are writing the **historical background / failed strict line**
Use:
- **Dual-Path Probe Router**
- **Conformal static router + monotone probe upgrade**
- **strict-audited negative result for additive probe cost**

Do **not** mix these two into a single claim sentence.

---

## 5. Minimal theoretical takeaways

### Current mainline
What we currently have is a combination of:
- classical Weighted A* bounded-suboptimality background,
- honest strict accounting (`T_total = T_w`),
- calibration-only model selection,
- strong empirical evidence under the frozen protocol.

### Historical mainline
What we can formally prove more directly is:
- monotone risk safety for upgrade-only probe routing,
- prior-shift risk certificates,
- oracle-regret-style bounds for portfolio settings.

These are important, but they mostly support the **historical** line or the broader RBAC framework, not the full current positive strict claim by themselves.

---

## 6. One-sentence current framing

The most defensible one-sentence paper framing for the router track is:

> We replace additive external probing with **risk-calibrated compute shaping inside a single Weighted A*** search, and implement it as a shallow-tree portfolio over weighted-search arms; under the frozen strict protocol, this zero-probe method significantly outperforms the strongest same-protocol baseline and the matched direct-baseline family.
