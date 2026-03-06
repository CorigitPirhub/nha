# Router Strict Audit Report (Phase27, v2)

## Protocol
- Strict: select/search only on `calib_train/calib_val`; `test` is used once for final evaluation.
- Legacy (diagnostic): allows `test`-set tuning in Phase-8 (conformal/probe). **Not** valid for main claims.

## Strict Results
- Phase9 pooled mean ΔJ (P5 - router): `-0.130400`
- Phase9 pooled 95% CI: `[-0.131355, -0.129469]`
- Phase9 p_boot(gt0): `1.000000e+00`
- Phase13 mean J-improve vs strongest baseline: `-0.841%`
- Phase22 mean J-improve vs best direct baseline: `-0.852%` (best direct=`cdt_worstcase_j_v1`)

## Gate Summary (Strict)
- `phase9_gain_significant`: `False`
- `phase13_sota_significant`: `False`
- `phase22_main_result_significant`: `False`

## Leakage A/B (Legacy vs Strict)
- Strict tables: `paper/tables_router_v12_strict_alpha05_probeT_noleak_rerun1`
- Legacy tables: `paper/tables_router_v8_legacy_diag_rerun1`

| phase   | metric                               |      strict |   legacy_diag |   strict_minus_legacy |
|:--------|:-------------------------------------|------------:|--------------:|----------------------:|
| phase9  | pooled_mean_delta_j                  | -0.1304     |    -0.104333  |            -0.0260665 |
| phase9  | p_value_bootstrap_gt0                |  1          |     1         |             0         |
| phase13 | j_improve_vs_strongest_baseline_mean | -0.00840732 |    -0.0527798 |             0.0443725 |
| phase13 | pooled_p_value_bootstrap_gt0         |  1          |     1         |             0         |
| phase22 | j_improve_vs_best_direct_mean_pct    | -0.851875   |    -6.61473   |             5.76285   |
| phase22 | pooled_p_value_bootstrap_gt0         |  1          |     1         |             0         |

## Notes
- Strict semantics: frozen protocol \(\alpha=0.05\); probe runtime is counted in latency \(T\) for probe-based policies; routing uses predicted cost \(\hat c(x)\) (no oracle per-sample `c`) and excludes dataset-ID features.
- If strict gates fail, main paper claims must be reframed to match strict evidence.
- This report is the single source of truth for strict vs legacy audit status.

