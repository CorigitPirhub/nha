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
- `J_improve_vs_strongest_baseline_mean`: `-5.416%`
- `risk_delta_vs_strongest_mean_pct`: `-0.062`
- `pooled_delta_j_ci95`: `[-0.057092, -0.051201]`
- `pooled_p_value_bootstrap_gt0`: `1.000000e+00`
- `pooled_p_value_wilcoxon`: `1.000000e+00`

## Seed Metrics
| seed | strongest baseline | J improve | risk delta (pct) |
|---:|---|---:|---:|
| 7 | conformal_strict_v2 | -5.764% | -0.062 |
| 11 | conformal_strict_v2 | -5.121% | -0.062 |
| 19 | conformal_strict_v2 | -5.558% | -0.062 |
| 23 | conformal_strict_v2 | -5.436% | -0.093 |
| 31 | conformal_strict_v2 | -5.203% | -0.031 |

## Benchmark Direction
| benchmark | mean delta_j | min | max | consistent |
|---|---:|---:|---:|---:|
| csm | -0.089893 | -0.096041 | -0.080496 | False |
| mp | -0.036567 | -0.039288 | -0.032611 | False |
| parasol | -0.013709 | -0.017881 | -0.010034 | False |

## Artifacts
- `seed_metrics_csv`: `paper/tables_router_v18_strict_recovery_prefixreuse/table_phase13_seed_metrics.csv`
- `benchmark_direction_csv`: `paper/tables_router_v18_strict_recovery_prefixreuse/table_phase13_benchmark_direction.csv`
- `significance_csv`: `paper/tables_router_v18_strict_recovery_prefixreuse/table_phase13_significance.csv`
- `strongest_counts_csv`: `paper/tables_router_v18_strict_recovery_prefixreuse/table_phase13_strongest_baseline_counts.csv`
- `external_sota_summary_csv`: `paper/tables_router_v18_strict_recovery_prefixreuse/table_phase13_external_sota_summary.csv`
- `report_md`: `reports/router_phase13_sota_v9_strict_recovery_prefixreuse.md`