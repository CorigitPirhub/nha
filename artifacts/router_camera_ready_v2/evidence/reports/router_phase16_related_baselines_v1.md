# Router Phase16 Related Baselines V1 Report

## Summary
- Runtime: `0.000 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Best related baseline: `conformal_switch_static_v1`

## Gate Check
- `baseline_family_count_ge_3`: `True`
- `same_protocol_and_budget`: `True`
- `J_improve_vs_best_related_ge_3pct`: `True`
- `risk_not_worse_deltaV_le_0_5pct`: `True`
- `pooled_p_lt_0_01_and_ci_no_cross_0`: `True`

## Main Metrics (vs best related baseline)
- `J_improve_mean`: `4.307%`
- `risk_delta_mean_pct`: `-0.329`
- `pooled_delta_j_ci95`: `[0.030184, 0.056812]`
- `pooled_p_value_bootstrap_gt0`: `0.000000e+00`
- `seed_level_p_value_wilcoxon`: `3.125000e-02`

## Methods (mean over seeds)
| method | family | info | J_mean | V | use_fast | total_lat_ms |
|---|---:|---|---:|---:|---:|---:|
| ours_probe_strict_v2 | ours | probe+conformal | 0.574468 | 0.193536 | 0.817091 | 1.544688 |
| conformal_switch_static_v1 | B | static_features_only | 0.600344 | 0.196830 | 0.817091 | 0.852890 |
| meta_quit_probe_v1 | C | probe_features_only | 0.606055 | 0.198384 | 0.817091 | 1.546997 |
| rational_static_v1 | A | static_features_only | 0.609235 | 0.198695 | 0.817091 | 0.854418 |
| p5_conformal_strict_v2 | p5 | conformal_only | 0.609262 | 0.199316 | 0.827284 | 0.832585 |

## Seed Metrics (ours vs best related)
| seed | best related | J improve | risk delta (pct) |
|---:|---|---:|---:|
| 7 | conformal_switch_static_v1 | 4.875% | -0.249 |
| 11 | conformal_switch_static_v1 | 4.845% | -0.435 |
| 19 | conformal_switch_static_v1 | 4.883% | -0.342 |
| 23 | conformal_switch_static_v1 | 3.127% | -0.342 |
| 31 | conformal_switch_static_v1 | 3.804% | -0.280 |

## Artifacts
- `out_dir`: `outputs/router_phase16_related_baselines_v1`
- `seed_metrics_csv`: `outputs/router_phase16_related_baselines_v1/tables/seed_metrics.csv`
- `method_summary_csv`: `outputs/router_phase16_related_baselines_v1/tables/method_summary.csv`
- `seed_benchmark_direction_csv`: `outputs/router_phase16_related_baselines_v1/tables/seed_benchmark_direction.csv`
- `significance_csv`: `outputs/router_phase16_related_baselines_v1/tables/significance.csv`
- `budget_caps_csv`: `outputs/router_phase16_related_baselines_v1/tables/budget_caps.csv`
- `budget_checks_csv`: `outputs/router_phase16_related_baselines_v1/tables/budget_checks.csv`
- `paper_table_csv`: `paper/tables_router_v5/table_phase16_related_baselines.csv`
- `appendix_md`: `paper/appendix_related_baselines.md`
- `report_md`: `reports/router_phase16_related_baselines_v1.md`