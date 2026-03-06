# Router Effect-Source Audit V3

Date: `2026-03-06`
Status: `current strict mainline reviewed`

## 1. Scope

This audit focuses on the **current strict-positive router mainline**:
- method screening: `scripts/run_router_phase29_step12r4_trials_v1.py`
- downstream evaluation: `scripts/run_router_phase13_sota.py`, `scripts/run_router_phase22_direct_baselines.py`
- source root: `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak`
- best current policy: `outputs/router_phase29_o_tree_weight_v1/`
- key outputs:
  - `outputs/router_phase29_step12r4_trials_v1/summary.json`
  - `outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`
  - `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`

Historical strict-negative materials were also checked to ensure current claims are not mixing old and new lines:
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`
- `outputs/final_v5_strict/manifest.json`

## 2. Integrity checks that passed

### 2.1 No obvious test leakage in the current Phase29 selector

`Phase29` uses:
- `p5_cal` only for calibration rows,
- `p5_test` only for final comparison rows,
- `_split_calib_train_val(...)` before model/structure selection,
- `calib_train` for fitting / leaf arm assignment,
- `calib_val` for feasibility + model selection,
- `test` only for final evaluation.

Relevant code path:
- `scripts/run_router_phase29_step12r4_trials_v1.py:_run_tree_portfolio`

No direct use of `test` was found in the structure search or parameter search loops.

### 2.2 Hash-bound inputs are present for downstream strict outputs

Current downstream outputs contain `inputs_parquet_sha256.json` and bind:
- the strict source counterfactual parquets,
- the weighted-arm arm table,
- the per-seed `route_arm` decisions,
- the per-seed `policy_metrics.json`.

Verified outputs:
- `outputs/router_phase13_sota_v10_strict_weighted_tree_o/inputs_parquet_sha256.json`
- `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/inputs_parquet_sha256.json`

### 2.3 Reported downstream numbers match direct recomputation

A direct recomputation from:
- the strict test counterfactual table,
- the weighted-arm arm table,
- the saved `route_arm` decisions,
- the saved `T_ref/beta`
reproduces the reported `Phase13` mean improvement exactly:

- recomputed `j_improve_vs_strongest_baseline_mean = 0.9976992728000766`
- reported `j_improve_vs_strongest_baseline_mean = 0.9976992728000766`

So there is no evidence that the `Phase13` result file is fabricated or inconsistent with the saved decisions.

### 2.4 `Phase22` best-direct selection is internally consistent

`outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/tables/method_summary.csv`
and `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`
are consistent:
- best direct baseline = `cdt_worstcase_j_v1`
- `cdt_worstcase_j_v1`, `crc_static_pupper_v1`, and `p5_conformal_strict_v2` are numerically identical under the realized parity setting.

## 3. What the current positive result is really coming from

## 3.1 The biggest source of gain is the **weighted-search arm family itself**

From `outputs/router_phase29_step12r4_trials_v1/summary.json`:
- `M / WAStarConst`: `mean_delta_j ≈ 15.442559`
- `N / DifficultyWeightPortfolio`: `mean_delta_j ≈ 15.443174`
- `O / TreeWeightPortfolio`: `mean_delta_j ≈ 15.443633`

Differences:
- `O - M ≈ 0.001074`
- `O - N ≈ 0.000459`

Interpretation:
- the overwhelming majority of the gain is from introducing the **zero-probe weighted-search family**;
- the shallow-tree selector contributes only a **small incremental refinement** on top of that family.

Therefore the effect is **not** mainly “a very strong per-instance router”; it is mainly “a better compute-shaping action space, plus a modest deployable selector”.

## 3.2 The protocol uses `L = node expansions`, and weighted A* is directly aligned with that metric

`docs/router_protocol_v1.md` explicitly says:
- `L` is a search-quality proxy,
- default `L` is **node expansions**.

`scripts/run_router_counterfactual.py` confirms that the stored `L_fast`, `L_slow` are:
- `r_fast["expansions"]`
- `r_slow["expansions"]`

`Phase29` reuses the same semantics for weighted arms:
- `L_w = weighted A* expansions`
- `T_w = weighted A* runtime`

This means the current method is winning on a metric where weighted A* is structurally advantaged:
- it reduces runtime,
- it often also reduces expansions,
- therefore it can improve both `T` and `L` simultaneously under the frozen objective.

This is **not a code bug**, but it is a **claim-scope constraint**:
- the current positive result should be described as a win under the frozen strict objective `J` with `L = expansions` plus path audit;
- it should **not** be overstated as a general proof of better path quality or better path optimality.

## 3.3 The auxiliary path audit is real, but it is secondary

Across the current best policy `O`, pooled over seeds:
- realized arms are only `{wa_w125, wa_w135}`;
- positive path-length relative increase occurs on a minority of cases;
- mean path-length increase is small;
- `p95` path-length increase stays within the Phase29 audit cap.

Representative pooled summaries from the current audit recomputation:
- `csm`: `path_rel_mean ≈ 0.00305`, `path_rel_p95 ≈ 0.02313`
- `mp`: `path_rel_mean ≈ 0.00033`, `path_rel_p95 ≈ 0`
- `parasol`: `path_rel_mean ≈ 0.00089`, `path_rel_p95 ≈ 0.00799`

So the positive result is **not** explained by catastrophic path degradation hidden behind a time win.
But the main objective is still expansions-based, so the path audit should remain clearly labeled as an auxiliary safeguard.

## 4. Is this just dataset luck?

Not obviously.

Current weighted-search policy `O` remains strongly positive on all three public benchmark sources:
- `csm`
- `mp`
- `parasol`

and across all three difficulty groups:
- `easy`
- `medium`
- `hard`

The sign does not come from a single narrow subset.

However, there is an important nuance:
- because `M` (constant weight) is already extremely strong,
- the *tree-routing* part may still be partly dataset-specific / low-magnitude.

So the honest reading is:
- **weighted-search compute shaping** is robustly useful on the current public strict benchmark,
- **tree-level adaptive routing** is currently only a mild extra gain.

## 5. Is there evidence of fabricated data?

No direct evidence was found.

Reasons:
1. downstream metrics match recomputation from saved policy artifacts;
2. input hashes are recorded for downstream outputs;
3. per-seed policy artifacts exist for `M/N/O/P` and are consistent with summary files;
4. the current reports and stats are numerically self-consistent.

This does not prove perfect provenance for every historical artifact in the repo, but for the **current strict-positive line** there is no audit evidence of fabricated result files.

## 6. Is there evaluation-protocol inconsistency?

### 6.1 The current strict chain itself is consistent

The current `Phase29 -> Phase13 -> Phase22` chain uses a coherent `route_arm -> T_a/L_a` evaluation path.
This is a meaningful improvement over trying to shoehorn weighted arms into a legacy `use_fast`-only evaluator.

### 6.2 But `Phase22` parity semantics changed, and this must be stated explicitly

For the current weighted-search line, `Phase22` parity is no longer the old
- `fast -> slow` flip-budget parity,

but instead:
- `weighted_search_slow_fallback_cap`.

In the realized best policy, the slow-fallback cap is `0` for all difficulties, so under this parity:
- `CRC`
- `CDT`
- `P5`
all collapse to the same rule.

This does **not** invalidate the current positive result, but it sharply limits what can be claimed:
- we can say the new weighted-search line beats the matched direct-baseline family under its honest parity semantics;
- we should **not** say the old direct-baseline comparison remains identical to the old probe-router setting.

## 7. Bottom-line judgment

### 7.1 What looks real

Under the current frozen strict protocol, the positive advantage of the current router mainline appears to be **real** and **method-driven**, not an obvious artifact of:
- test leakage,
- fabricated outputs,
- downstream aggregation bugs,
- or mismatched route-arm evaluation code.

### 7.2 What that advantage is actually attributable to

The current gain is primarily attributable to:
1. replacing additive external probing with **zero-probe compute shaping inside a single search**;
2. expanding the arm space to include **weighted-search arms** that are highly favorable under the frozen `J` definition;
3. using a shallow-tree selector as a deployable but only mildly incremental routing layer.

### 7.3 What should still be written as a caveat in any paper draft

1. The gain is measured under `L = expansions` (with auxiliary path audit), not under pure path-cost quality.
2. The tree selector itself adds only a small gain over much simpler constant/difficulty-weight baselines.
3. `Phase22` direct-baseline parity is now a weighted-search-specific parity, not the old flip-budget parity.
4. Therefore the safest main claim is:

> The strict-positive result is genuine for the new weighted-search compute-shaping method under the frozen protocol, but it should not be oversold as either (i) a rescued probe-router claim or (ii) a strong proof that adaptive tree routing itself is the dominant source of the gain.
