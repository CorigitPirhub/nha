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
- `J_improve_vs_strongest_baseline_mean`: `-0.841%`
- `risk_delta_vs_strongest_mean_pct`: `0.000`
- `pooled_delta_j_ci95`: `[-0.008469, -0.008347]`
- `pooled_p_value_bootstrap_gt0`: `1.000000e+00`
- `pooled_p_value_wilcoxon`: `1.000000e+00`

## Seed Metrics
| seed | strongest baseline | J improve | risk delta (pct) |
|---:|---|---:|---:|
| 7 | conformal_strict_v2 | -0.841% | 0.000 |
| 11 | conformal_strict_v2 | -0.846% | 0.000 |
| 19 | conformal_strict_v2 | -0.839% | 0.000 |
| 23 | conformal_strict_v2 | -0.835% | 0.000 |
| 31 | conformal_strict_v2 | -0.842% | 0.000 |

## Benchmark Direction
| benchmark | mean delta_j | min | max | consistent |
|---|---:|---:|---:|---:|
| csm | -0.171944 | -0.181939 | -0.166434 | False |
| mp | -0.005827 | -0.005879 | -0.005790 | True |
| parasol | -0.001776 | -0.002101 | -0.001695 | True |

## Artifacts
- `seed_metrics_csv`: `paper/tables_router_v12_strict_alpha05_probeT_noleak_rerun1/table_phase13_seed_metrics.csv`
- `benchmark_direction_csv`: `paper/tables_router_v12_strict_alpha05_probeT_noleak_rerun1/table_phase13_benchmark_direction.csv`
- `significance_csv`: `paper/tables_router_v12_strict_alpha05_probeT_noleak_rerun1/table_phase13_significance.csv`
- `strongest_counts_csv`: `paper/tables_router_v12_strict_alpha05_probeT_noleak_rerun1/table_phase13_strongest_baseline_counts.csv`
- `external_sota_summary_csv`: `paper/tables_router_v12_strict_alpha05_probeT_noleak_rerun1/table_phase13_external_sota_summary.csv`
- `report_md`: `reports/router_phase13_sota_v5_strict_alpha05_probeT_noleak_rerun1.md`