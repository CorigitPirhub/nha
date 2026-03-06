# Step12-R4 Trial Report (v1)

Strict source root: `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/`
Candidate weight set: `[1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.35]`
Execution order: `M -> N -> O -> P`

Design family: weighted-search portfolio under strict semantics (zero probe overhead; auxiliary path-length audit to avoid pure metric gaming).

## Scheme M — WAStarConst
- pooled mean ΔJ: `15.442559`
- pooled 95% CI: `[14.957476, 15.934378]`
- bootstrap p(gt0): `0.000000`
- route-only mean ΔJ: `15.442559`
- trigger / non-fast rate: `1.000000`
- gate: `{'pooled_p_lt_0_01': True, 'pooled_ci95_not_cross_0': True, 'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True}`
- example selected policy: `{'selected_arm': 'wa_w135'}`

## Scheme N — DifficultyWeightPortfolio
- pooled mean ΔJ: `15.443174`
- pooled 95% CI: `[14.958293, 15.935723]`
- bootstrap p(gt0): `0.000000`
- route-only mean ΔJ: `15.443174`
- trigger / non-fast rate: `1.000000`
- gate: `{'pooled_p_lt_0_01': True, 'pooled_ci95_not_cross_0': True, 'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True}`
- example selected policy: `{'weights_by_difficulty': {'easy': 'wa_w135', 'medium': 'wa_w135', 'hard': 'wa_w125'}}`

## Scheme O — TreeWeightPortfolio
- pooled mean ΔJ: `15.443633`
- pooled 95% CI: `[14.958535, 15.935957]`
- bootstrap p(gt0): `0.000000`
- route-only mean ΔJ: `15.443633`
- trigger / non-fast rate: `1.000000`
- gate: `{'pooled_p_lt_0_01': True, 'pooled_ci95_not_cross_0': True, 'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True}`
- example selected policy: `{'depth': 2, 'min_samples_leaf': 240, 'leaf_to_arm': {'2': 'wa_w135', '3': 'wa_w135', '5': 'wa_w135', '6': 'wa_w125'}}`

## Scheme P — TreeWeightSlowFallback
- pooled mean ΔJ: `15.443633`
- pooled 95% CI: `[14.958535, 15.935957]`
- bootstrap p(gt0): `0.000000`
- route-only mean ΔJ: `15.443633`
- trigger / non-fast rate: `1.000000`
- gate: `{'pooled_p_lt_0_01': True, 'pooled_ci95_not_cross_0': True, 'risk_ci95_upper_le_alpha_all_seeds': True, 'path_audit_hold_all_seeds': True}`
- example selected policy: `{'depth': 2, 'min_samples_leaf': 240, 'leaf_to_arm': {'2': 'wa_w135', '3': 'wa_w135', '5': 'wa_w135', '6': 'wa_w125'}}`

## Downstream Integration Follow-up (`2026-03-06`)
- `O / TreeWeightPortfolio` has been integrated into `Phase13` and `Phase22` via `outputs/router_phase13_sota_v10_strict_weighted_tree_o/` and `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/`.
- `P / TreeWeightSlowFallback` is numerically identical to `O` in downstream runs because no seed actually uses the `slow` arm; the realized arm set is only `{wa_w125, wa_w135}`.
- Under the new zero-probe weighted-search semantics, `Phase13` and `Phase22` gates both pass. The strict main conclusion is therefore recovered end-to-end for the **weighted-search compute-shaping** claim.
- Honest caveat: in `Phase22`, the parity mode is `weighted_search_slow_fallback_cap`, and the cap is `0` for all difficulties, so CRC/CDT collapse to `P5`; the strong result is still valid, but it supports the new compute-shaping claim rather than the old probe-router claim.

