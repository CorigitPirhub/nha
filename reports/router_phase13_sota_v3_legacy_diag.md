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
- `J_improve_vs_strongest_baseline_mean`: `3.943%`
- `risk_delta_vs_strongest_mean_pct`: `-0.733`
- `pooled_delta_j_ci95`: `[0.022670, 0.053717]`
- `pooled_p_value_bootstrap_gt0`: `0.000000e+00`
- `pooled_p_value_wilcoxon`: `3.125000e-02`

## Seed Metrics
| seed | strongest baseline | J improve | risk delta (pct) |
|---:|---|---:|---:|
| 7 | conformal_strict_v2 | 2.504% | -1.057 |
| 11 | conformal_strict_v2 | 5.116% | -1.119 |
| 19 | conformal_strict_v2 | 5.447% | -0.777 |
| 23 | conformal_strict_v2 | 4.236% | -0.466 |
| 31 | conformal_strict_v2 | 2.413% | -0.249 |

## Benchmark Direction
| benchmark | mean delta_j | min | max | consistent |
|---|---:|---:|---:|---:|
| csm | 0.070608 | 0.026688 | 0.138263 | True |
| mp | 0.030457 | -0.008853 | 0.051341 | True |
| parasol | 0.000000 | 0.000000 | 0.000000 | True |

## Artifacts
- `seed_metrics_csv`: `paper/tables_router_v8_legacy_diag/table_phase13_seed_metrics.csv`
- `benchmark_direction_csv`: `paper/tables_router_v8_legacy_diag/table_phase13_benchmark_direction.csv`
- `significance_csv`: `paper/tables_router_v8_legacy_diag/table_phase13_significance.csv`
- `strongest_counts_csv`: `paper/tables_router_v8_legacy_diag/table_phase13_strongest_baseline_counts.csv`
- `external_sota_summary_csv`: `paper/tables_router_v8_legacy_diag/table_phase13_external_sota_summary.csv`
- `report_md`: `reports/router_phase13_sota_v3_legacy_diag.md`