# Router Strict Audit Report (Phase27, v1)

> ⚠️ **Deprecated (superseded by v2):** After fixing the remaining threats to validity (α alignment, probe runtime counted in \(T\), no oracle per-sample cost, no dataset-ID features),
> the strict mainline result flips and the performance gates fail. Use `reports/router_strict_audit_v2.md` (and `reports/router_validity_audit_v2.md`) as the current strict single source of truth.

## Protocol
- Strict: select/search only on `calib_train/calib_val`; `test` is used once for final evaluation.
- Legacy (diagnostic): allows `test`-set tuning in Phase-8 (conformal/probe). **Not** valid for main claims.

## Strict Results
- Phase9 pooled mean ΔJ (P5 - router): `0.025883`
- Phase9 pooled 95% CI: `[0.018572, 0.033589]`
- Phase9 p_boot(gt0): `0.000000e+00`
- Phase13 mean J-improve vs strongest baseline: `3.283%`
- Phase22 mean J-improve vs best direct baseline: `1.610%` (best direct=`cdt_worstcase_j_v1`)

## Gate Summary (Strict)
- `phase9_gain_significant`: `True`
- `phase13_sota_significant`: `True`
- `phase22_main_result_significant`: `True`

## Leakage A/B (Legacy vs Strict)
- Strict tables: `paper/tables_router_v11_strict_knapsack`
- Legacy tables: `paper/tables_router_v8_legacy_diag`

| phase   | metric                               |    strict |   legacy_diag |   strict_minus_legacy |
|:--------|:-------------------------------------|----------:|--------------:|----------------------:|
| phase9  | pooled_mean_delta_j                  | 0.0258834 |     0.0316585 |           -0.00577503 |
| phase9  | p_value_bootstrap_gt0                | 0         |     0         |            0          |
| phase13 | j_improve_vs_strongest_baseline_mean | 0.0328285 |     0.0394329 |           -0.00660437 |
| phase13 | pooled_p_value_bootstrap_gt0         | 0         |     0         |            0          |
| phase22 | j_improve_vs_best_direct_mean_pct    | 1.61011   |     2.60881   |           -0.998696   |
| phase22 | pooled_p_value_bootstrap_gt0         | 0.001     |     0.0013    |           -0.0003     |

## Notes
- If strict gates fail, main paper claims must be reframed to match strict evidence.
- This report is the single source of truth for strict vs legacy audit status.
