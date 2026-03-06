# Router Phase13 SOTA V1 Report

## Summary
- Runtime: `0.000 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Strongest baseline (same protocol): `conformal_strict_v2`
- External strong baselines counted: `7`

## Gate Check
- `external_strong_baselines_ge_6`: `True`
- `direction_consistent_per_benchmark`: `False`
- `pooled_p_lt_0_01`: `False`
- `pooled_ci95_not_cross_0`: `False`
- `j_improve_vs_strongest_ge_3pct`: `False`
- `risk_not_worse_deltaV_le_0_5pct`: `True`
- `exp3_exp4_drift_abs_le_0_5pct`: `True`

## Main Metrics
- `J_improve_vs_strongest_baseline_mean`: `-20.734%`
- `risk_delta_vs_strongest_mean_pct`: `-3.014`
- `pooled_delta_j_ci95`: `[-0.222277, -0.192840]`
- `pooled_p_value_bootstrap_gt0`: `1.000000e+00`
- `pooled_p_value_wilcoxon`: `1.000000e+00`

## Seed Metrics
| seed | strongest baseline | J improve | risk delta (pct) |
|---:|---|---:|---:|
| 7 | conformal_strict_v2 | -20.830% | -2.766 |
| 11 | conformal_strict_v2 | -21.068% | -2.766 |
| 19 | conformal_strict_v2 | -20.829% | -3.543 |
| 23 | conformal_strict_v2 | -19.995% | -3.045 |
| 31 | conformal_strict_v2 | -20.951% | -2.952 |

## Benchmark Direction
| benchmark | mean delta_j | min | max | consistent |
|---|---:|---:|---:|---:|
| csm | -1.998612 | -2.220692 | -1.860743 | False |
| mp | -0.167219 | -0.175183 | -0.158902 | False |
| parasol | -0.614112 | -0.927515 | -0.466976 | False |

## Artifacts
- `seed_metrics_csv`: `paper/tables_router_v14_strict_recovery_risktrade/table_phase13_seed_metrics.csv`
- `benchmark_direction_csv`: `paper/tables_router_v14_strict_recovery_risktrade/table_phase13_benchmark_direction.csv`
- `significance_csv`: `paper/tables_router_v14_strict_recovery_risktrade/table_phase13_significance.csv`
- `strongest_counts_csv`: `paper/tables_router_v14_strict_recovery_risktrade/table_phase13_strongest_baseline_counts.csv`
- `external_sota_summary_csv`: `paper/tables_router_v14_strict_recovery_risktrade/table_phase13_external_sota_summary.csv`
- `report_md`: `reports/router_phase13_sota_v7_strict_recovery_risktrade.md`