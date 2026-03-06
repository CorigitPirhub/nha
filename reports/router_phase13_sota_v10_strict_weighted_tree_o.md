# Router Phase13 SOTA V1 Report

## Summary
- Runtime: `0.000 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Strongest baseline (same protocol): `conformal_strict_v2`
- External strong baselines counted: `7`

## Gate Check
- `external_strong_baselines_ge_6`: `True`
- `direction_consistent_per_benchmark`: `True`
- `pooled_p_lt_0_01`: `True`
- `pooled_ci95_not_cross_0`: `True`
- `j_improve_vs_strongest_ge_3pct`: `True`
- `risk_not_worse_deltaV_le_0_5pct`: `True`
- `exp3_exp4_drift_abs_le_0_5pct`: `True`

## Main Metrics
- `J_improve_vs_strongest_baseline_mean`: `99.770%`
- `risk_delta_vs_strongest_mean_pct`: `-3.282`
- `pooled_delta_j_ci95`: `[0.966303, 1.029449]`
- `pooled_p_value_bootstrap_gt0`: `0.000000e+00`
- `pooled_p_value_wilcoxon`: `3.125000e-02`

## Seed Metrics
| seed | strongest baseline | J improve | risk delta (pct) |
|---:|---|---:|---:|
| 7 | conformal_strict_v2 | 99.775% | -3.045 |
| 11 | conformal_strict_v2 | 99.756% | -3.045 |
| 19 | conformal_strict_v2 | 99.781% | -3.853 |
| 23 | conformal_strict_v2 | 99.784% | -3.356 |
| 31 | conformal_strict_v2 | 99.754% | -3.108 |

## Benchmark Direction
| benchmark | mean delta_j | min | max | consistent |
|---|---:|---:|---:|---:|
| csm | 0.939631 | 0.929895 | 0.946287 | True |
| mp | 0.998649 | 0.998588 | 0.998702 | True |
| parasol | 0.998762 | 0.998517 | 0.998844 | True |

## Artifacts
- `seed_metrics_csv`: `paper/tables_router_v24_strict_weighted_tree_o/table_phase13_seed_metrics.csv`
- `benchmark_direction_csv`: `paper/tables_router_v24_strict_weighted_tree_o/table_phase13_benchmark_direction.csv`
- `significance_csv`: `paper/tables_router_v24_strict_weighted_tree_o/table_phase13_significance.csv`
- `strongest_counts_csv`: `paper/tables_router_v24_strict_weighted_tree_o/table_phase13_strongest_baseline_counts.csv`
- `external_sota_summary_csv`: `paper/tables_router_v24_strict_weighted_tree_o/table_phase13_external_sota_summary.csv`
- `report_md`: `reports/router_phase13_sota_v10_strict_weighted_tree_o.md`