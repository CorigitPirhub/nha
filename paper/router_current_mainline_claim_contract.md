# Current Mainline Claim Contract (Step 13)

Status: `paper-facing-contract`  
Date: `2026-03-06`

Protocol references:
- frozen protocol source of truth: `docs/router_protocol_v1.md`
- current-mainline protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`

This file freezes the **current paper-facing main claim and evaluation contract**.
It is a documentation-only Step 13 deliverable:
- it does **not** change protocol values, splits, code paths, or result files;
- it exists to prevent the method narrative from drifting back to the historical probe-router claim.

---

## 1. Exact current main claim

The current paper-facing claim is:

> Under the frozen Protocol V1 strict semantics, our current main method is **Risk-Calibrated Single-Search Compute Shaping**, implemented as a **Weighted-Search Tree Portfolio** (`O / TreeWeightPortfolio`). On the current public strict benchmarks (`csm`, `mp`, `parasol`), this zero-probe method significantly improves the strict objective `J` over the strongest same-protocol baseline and over the matched direct-baseline family.

Short title form allowed in the paper:
- **Risk-Calibrated Single-Search Compute Shaping**
- **Weighted-Search Tree Portfolio**

---

## 2. Evaluation contract that makes the claim valid

The above claim is valid only under the following contract:

1. **Protocol version**
   - `docs/router_protocol_v1.md` is the frozen protocol source of truth.
2. **Method/protocol mapping**
   - `docs/router_protocol_v1_current_mainline_note.md` explains why the method changed but the protocol did not.
3. **Strict split semantics**
   - all fitting / search / model selection must stay inside `calib_train/calib_val`;
   - `test` is used only once for final evaluation.
4. **Statistical semantics**
   - at least `5` seeds;
   - paired bootstrap with `N = 10000`;
   - paired Wilcoxon signed-rank test;
   - positive main claims require `p < 0.01` and a `95% CI` that does not cross zero.
5. **Primary metric semantics**
   - primary objective is Protocol V1 `J`;
   - primary quality proxy is `L = node expansions`;
   - path-length / path-cost checks are auxiliary audits, not the main protocol quantity.
6. **Current benchmark scope**
   - current public strict benchmark sources are `csm`, `mp`, and `parasol`.
7. **Current authoritative artifact chain**
   - screening / selection: `reports/router_phase29_step12r4_trials_v1.md`
   - successor screening status: `reports/router_phase30_step14_trials_v1.md`, `reports/router_phase31_step14_fresh_trials_v1.md`, `reports/router_phase32_step14_tarp_line_v1.md`, `reports/router_phase32_step14_tarp_line_f2b_hgb_v1.md`, `reports/router_phase33_step14_rcwsb_trials_v1.md`, and `reports/router_phase33_step14_rcwsb_b1_followup_v1.md` (no replacement promoted)
   - strongest-baseline result: `reports/router_phase13_sota_v10_strict_weighted_tree_o.md`
   - direct-baseline result: `reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md`
   - effect-source audit: `reports/router_effect_source_audit_v3.md`

---

## 3. What is historical background, not the current main claim

The following are still important, but are **not** the current positive main result:
- the historical `Dual-Path Probe Router (P5 -> P6)` line;
- probe monotone-safety as the main performance claim;
- legacy V1/V2/V3 strict-negative bundles for the old probe-router line;
- old direct-baseline comparisons under `fast -> slow` flip-budget parity.

Historical negative-evidence roots:
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`
- `outputs/final_v5_strict/manifest.json`

---

## 4. Non-claims that must remain explicit

The current paper must **not** claim:
1. that the old probe-router claim survived strict audit;
2. that Protocol V1 itself has changed;
3. that the current result proves universally better path quality or path optimality;
4. that the shallow tree selector is the dominant source of the gain;
5. that `Phase22` still uses the old `fast -> slow` flip-budget parity.

Instead, the required caveats are:
- most of the current gain comes from the weighted-search arm family itself, with only a small extra gain from the tree selector;
- the main result is a win under Protocol V1 with `L = expansions` plus auxiliary path audit;
- the current `Phase22` comparison uses `weighted_search_slow_fallback_cap` parity.

---

## 5. Paper-writing rules

When writing the main paper text:
1. use **Risk-Calibrated Single-Search Compute Shaping** as the canonical method description;
2. mention **Weighted-Search Tree Portfolio** as the current implementation form;
3. refer to the old probe-router line only as **historical mainline / audit line / framework background**;
4. if discussing `Phase22`, explicitly mention the parity change to `weighted_search_slow_fallback_cap`;
5. if discussing quality, distinguish clearly between:
   - Protocol V1 primary `L = expansions`, and
   - auxiliary path-length / path-cost audits.
6. if mentioning Step 14 / successor methods, state explicitly that the 2026-03-06/07 strict screenings (`phase30`, `phase31`, the `phase32` TARP-line continuation, and the `phase33` RCWS-B sprint) did **not** promote a replacement for `O / TreeWeightPortfolio`.

If a future Step 14+ method replaces `O / TreeWeightPortfolio` as the current best method, this file should be superseded only after the new method passes the **same strict contract**.
