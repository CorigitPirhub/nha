# Router Phase7 V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `3.408 h`
- External baseline methods: `7`
- Ablation rows (exclude Full): `16`

## Gate Check
- `five_seeds_completed`: `True`
- `main_claims_p_lt_0_01_and_ci_no_cross_0`: `True`
- `external_baselines_ge_3`: `True`
- `ablations_ge_8`: `True`
- `exp3_exp4_drift_abs_le_0_5pct`: `False`
- `exp1_2_latency_target_le_2ms`: `True`
- `exp1_2_success_not_degraded_vs_astar`: `True`
- `one_command_runtime_le_24h`: `True`

## Main Metrics (Seed Mean ± Std)
- `exp1_standard_time_ms_ours`: `0.478247 ± 0.005293`
- `exp1_standard_success_ours`: `1.000000 ± 0.000000`
- `exp2_time_ms_ours`: `0.798065 ± 0.008873`
- `exp2_success_ours`: `1.000000 ± 0.000000`
- `exp3_dE_full_vs_nores_pct`: `-1.557981 ± 0.000000`
- `exp3_full_success`: `1.000000 ± 0.000000`
- `exp4_dE_ours_vs_hybrid_pct`: `-1.557981 ± 0.000000`
- `exp4_ours_success`: `1.000000 ± 0.000000`
- `exp3_dE_drift_abs_pct`: `7.879053 ± 0.000000`
- `exp4_dE_drift_abs_pct`: `0.015034 ± 0.000000`
- `mixed_strict_og_improve_vs_p5_pct`: `0.000000 ± 0.000000`
- `mixed_strict_hard_improve_vs_p5_pct`: `0.000000 ± 0.000000`
- `mixed_strict_latency_extra_vs_p5_ms`: `0.000000 ± 0.000000`
- `mixed_target_og_improve_vs_p5_pct`: `15.985720 ± 0.705439`
- `mixed_target_hard_improve_vs_p5_pct`: `376.144033 ± 241.865889`
- `mixed_target_latency_extra_vs_p5_ms`: `0.009901 ± 0.001064`

## Main Claims (Bootstrap + Wilcoxon)
| claim | n | mean | 95%CI | p-value | pass |
|---|---:|---:|---|---:|---:|
| exp12_latency_improve_theta_ms | 6000 | 0.749748 | [0.714314, 0.785615] | 0.000000e+00 | True |
| exp3_success_gain_full_vs_no_rs | 90 | 0.555556 | [0.455556, 0.655556] | 7.687299e-13 | True |
| exp4_expansion_gain_ours_vs_hybrid | 90 | 192.722222 | [94.021111, 306.990833] | 9.003681e-04 | True |
| mixed_target_j_improve_vs_p5 | 4500 | 0.035508 | [0.020881, 0.051614] | 1.257930e-05 | True |

## Reproducibility Artifacts
- Seed runs: `outputs/router_phase7_v1/seed_runs.csv`
- Stats: `outputs/router_phase7_v1/stats.json`
- Hash manifest: `outputs/router_phase7_v1/manifest_hash.json`
- Tables: `paper/tables_router_v1`
- Figures: `paper/figures_router_v1`