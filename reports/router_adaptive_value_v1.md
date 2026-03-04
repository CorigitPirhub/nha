# Router Adaptive Value V1 Report

## Summary
- Runtime: `0.001 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Selected policy: `{'feature': 'probe_score', 'tau_easy': 1.8, 'tau_medium': 0.12000000000000001, 'tau_hard': 0.01}`
- Discriminative cases: `794`
- OOD test cases: `43`

## Gate Check
- `fast_ratio_not_degenerate`: `True`
- `stratified_split_valid`: `True`
- `deltaJ_vs_forced_fast_ge_3pct`: `True`
- `latency_vs_forced_slow_improve_ge_10pct`: `True`
- `risk_violation_rate_le_6pct`: `True`
- `risk_ci95_upper_le_8pct`: `True`
- `ood_pooled_deltaJ_gt_0`: `True`
- `ood_p_value_lt_0_01`: `True`
- `effect_size_cliffs_delta_ge_0_147`: `True`

## Strategy Metrics
| strategy           |   n_cases_total |   fast_ratio_mean |   easy_fast_ratio_mean |   hard_fast_ratio_mean |   violation_rate_mean |   violation_ci95_upper_mean |   j_mean |   latency_mean_ms |   delta_j_vs_forced_fast |   latency_improve_vs_forced_slow |   ood_delta_j_vs_strongest |
|:-------------------|----------------:|------------------:|-----------------------:|-----------------------:|----------------------:|----------------------------:|---------:|------------------:|-------------------------:|---------------------------------:|---------------------------:|
| forced_fast        |            1535 |          1        |               1        |              1         |             0.501629  |                  0.548347   |  2.39349 |          0.403391 |               nan        |                       nan        |                  nan       |
| forced_slow        |            1535 |          0        |               0        |              0         |             0         |                  0.00873586 |  2.25509 |         18.6615   |               nan        |                       nan        |                  nan       |
| router             |            1535 |          0.463844 |               0.936842 |              0.0333333 |             0.0410423 |                  0.0639453  |  1.00713 |          6.745    |                 0.579223 |                         0.638561 |                    0.56533 |
| strongest_baseline |            1535 |          0.740717 |               0.923684 |              0.535897  |             0.27557   |                  0.319335   |  1.83103 |          2.74308  |               nan        |                       nan        |                  nan       |

## Statistical Hardening
| test                         |     stat |       p_value |   ci95_low |   ci95_high |
|:-----------------------------|---------:|--------------:|-----------:|------------:|
| bootstrap_mean_diff_gt0      | 1.87539  |   0           |    1.44936 |     2.33618 |
| wilcoxon_paired_greater      | 1.87298  |   1.40936e-21 |  nan       |   nan       |
| permutation_signflip_greater | 1.87298  |   0           |  nan       |   nan       |
| cliffs_delta_base_vs_router  | 0.349054 | nan           |  nan       |   nan       |

## Artifacts
- `discriminative_set_csv`: `outputs/router_adaptive_value_v1/discriminative_set.csv`
- `ood_set_csv`: `outputs/router_adaptive_value_v1/ood_set.csv`
- `policy_selection_log_csv`: `outputs/router_adaptive_value_v1/policy_selection_log.csv`
- `seed_strategy_metrics_csv`: `outputs/router_adaptive_value_v1/seed_strategy_metrics.csv`
- `stats_tests_csv`: `outputs/router_adaptive_value_v1/stats_tests.csv`
- `table_adaptive_value_csv`: `paper/tables_router_v4/table_adaptive_value.csv`
- `table_stats_hardening_csv`: `paper/tables_router_v4/table_stats_hardening.csv`
- `report_md`: `reports/router_adaptive_value_v1.md`