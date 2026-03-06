# Router Protocol V1 — Current Mainline Note

Status: `companion-note`  
Date: `2026-03-06`  
Applies to: the **current strict-positive router mainline**  
Frozen protocol source of truth: `docs/router_protocol_v1.md`

---

## 1. Purpose

This note exists to clarify an important distinction:
- `docs/router_protocol_v1.md` remains the **frozen evaluation protocol** and must not be edited retroactively;
- the **current router mainline** has changed from the historical **Dual-Path Probe Router** to the new **Risk-Calibrated Single-Search Compute Shaping / Weighted-Search Tree Portfolio** mainline.

In other words:
- **protocol stays the same**;
- **method framing and main artifacts have changed**.

This file is therefore a **current-mainline companion note for Protocol V1**, not a replacement for the frozen protocol.

---

## 2. What remains unchanged from Protocol V1

The following items are still inherited directly from `docs/router_protocol_v1.md` and remain the judging standard for the current mainline:

1. **Primary objective**
   - `J = T_norm + beta * L_norm`
2. **Relative quality-loss definition**
   - `delta_l_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`
3. **Risk budget**
   - `epsilon_rel = 0.015`
   - `alpha = 0.05`
4. **Statistical protocol**
   - at least `5` seeds
   - paired bootstrap with `N = 10000`
   - paired Wilcoxon signed-rank test
   - main positive claims require `p < 0.01` and a `95% CI` that does not cross zero
5. **strict split semantics**
   - all fitting / search / selection must stay inside calibration splits
   - test is used only once for final evaluation
6. **change control**
   - any actual protocol modification requires a new protocol version and rerunning affected validations

Therefore, this note does **not** change protocol values, thresholds, significance criteria, or acceptance rules.

---

## 3. What has changed at the method level

### 3.1 Historical mainline (no longer the current positive claim)

The earlier mainline was:
- **Dual-Path Probe Router**
- static conformal router (`P5`) + probe-based upgrade router (`P6`)

Under the fully audited strict semantics, the old probe-router `J`-improvement claim no longer serves as the current positive main result.

Reference negative-evidence / audit files:
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`
- `outputs/final_v5_strict/manifest.json`

### 3.2 Current mainline (the live strict-positive claim)

The current mainline is:
- **Risk-Calibrated Single-Search Compute Shaping**
- implemented as a **Weighted-Search Tree Portfolio**
- best current deployable policy: **`O / TreeWeightPortfolio`**

The key change is structural:
- the old line used **extra external compute** (`probe`) before final routing;
- the new line performs **adaptive computation inside a single Weighted A*** search by choosing a heuristic weight `w(x)`.

So the live action space is no longer just `{fast, slow}`;
it now includes weighted-search arms such as:
- `fast`
- `wa_w105 ... wa_w135`
- optional `slow` fallback

This is a **method-level change**, not a protocol change.

---

## 4. How the current mainline maps back to Protocol V1

The current weighted-search mainline still obeys Protocol V1 because:

1. **Same frozen objective and risk definition**
   - all current evaluations are still reported with the same `J`, `delta_l_rel`, `epsilon_rel`, and `alpha`
2. **Same statistical standards**
   - the current downstream reports still use the frozen significance rules
3. **Same strict philosophy**
   - `calib_train/calib_val` are used for fitting and model selection
   - `test` is reserved for one-shot final reporting
4. **Same traceability requirements**
   - downstream outputs record input parquet hashes

What changes is only the policy class:
\[
\pi(x) \in \{\texttt{fast}, \texttt{wa\_w105}, \ldots, \texttt{wa\_w135}, \texttt{slow}\}
\]
instead of the historical binary or probe-augmented decision rule.

---

## 5. Current authoritative artifacts under Protocol V1

For the **current** router mainline, the primary artifacts to use are:

### 5.1 Screening / method-selection layer
- `scripts/run_router_phase29_step12r4_trials_v1.py`
- `outputs/router_phase29_step12r4_trials_v1/summary.json`
- `reports/router_phase29_step12r4_trials_v1.md`

### 5.2 Best-policy artifacts
- `outputs/router_phase29_o_tree_weight_v1/`
- `outputs/router_phase29_p_tree_weight_slow_v1/`

Current practical note:
- `P` is numerically identical to `O` under the present strict data because no seed actually uses `slow`
- therefore the current mainline should be treated as `O / TreeWeightPortfolio`

### 5.3 Downstream strict chain
- `outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`
- `reports/router_phase13_sota_v10_strict_weighted_tree_o.md`
- `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`
- `reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md`

### 5.4 Task-book / narrative source of truth
- `TASK.md`
- `README.md`
- `INTRO.md`
- `docs/neurips_method_v1.md`
- `docs/router_theory_v3.md`
- `paper/router_current_mainline_claim_contract.md`

---

## 6. Claim-scope note that must be preserved

Using Protocol V1 with the current method does **not** mean the old claim is restored unchanged.

The honest current claim is:

> Under the frozen Protocol V1 strict semantics, a zero-probe single-search compute-shaping policy (`TreeWeightPortfolio`) significantly improves the strict objective `J` over the strongest same-protocol baseline and over the matched direct-baseline family.

The following stronger or different claims are **not** implied by this note:
- that the old probe-router claim survived strict audit;
- that Protocol V1 has been redefined;
- that the gain is a proof of universally better path quality;
- that all historical direct-baseline comparisons retain identical parity semantics.

In particular, for the current weighted-search mainline:
- the direct-baseline comparison in `Phase22` uses `weighted_search_slow_fallback_cap` parity,
- not the old `fast -> slow` flip-budget parity.

---

## 7. Usage guidance

Use `docs/router_protocol_v1.md` when you need:
- the frozen metrics,
- thresholds,
- significance criteria,
- acceptance rules,
- protocol change-control.

Use this file when you need:
- the current mainline framing under that same protocol,
- the current authoritative strict-positive artifacts,
- a clean explanation of why the protocol did not change even though the main method did.

Use `paper/router_current_mainline_claim_contract.md` when you need:
- the exact paper-facing main claim sentence,
- the explicit non-claims,
- the writing contract that Step 13 froze for the current submission line.

---

## 8. Non-goal

This file is **not** a new protocol version.
If protocol semantics themselves need to change, create a new versioned protocol file (for example `router_protocol_v2.md`) and rerun all affected validations as required by `docs/router_protocol_v1.md`.
