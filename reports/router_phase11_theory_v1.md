# Router Phase11 Theory V1 Report

## Summary
- Runtime: `0.000 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Epsilon: `0.015`
- Alpha: `0.05`

## Gate Check
- `five_seeds_completed`: `True`
- `theory_bound_gap_le_2pct`: `True`
- `empirical_le_theory_upper_all_seeds`: `True`
- `probe_monotone_safety_all_seeds`: `True`
- `probe_fast_subset_of_conformal_all_seeds`: `True`
- `probe_og_improve_positive_all_seeds`: `True`
- `error_decomposition_lhs_le_rhs_all_seeds`: `True`

## Key Numbers
- `probe_violation_rate_mean`: `0.056444`
- `probe_theory_upper_mean`: `0.073484`
- `max_probe_bound_gap_pct`: `1.747%`
- `probe_monotone_safety_all`: `True`

## Seed Metrics
|   seed |   num_cases |   conf_violation_rate |   probe_violation_rate |   conf_theory_upper |   probe_theory_upper |   probe_bound_gap | probe_monotone_safety   | probe_fast_subset_of_conf   |   probe_og_improve_vs_p5_pct |   probe_target_prior_violation_rate |   selection_shift_target_minus_eval |   decomp_safety_gain_conf_minus_probe |   decomp_finite_sample_slack |   decomp_rhs_upper |   decomp_lhs_target_risk |
|-------:|------------:|----------------------:|-----------------------:|--------------------:|---------------------:|------------------:|:------------------------|:----------------------------|-----------------------------:|------------------------------------:|------------------------------------:|--------------------------------------:|-----------------------------:|-------------------:|-------------------------:|
|      7 |         900 |             0.0566667 |              0.0511111 |           0.0737412 |            0.0675023 |         0.0163912 | True                    | True                        |                     10.3651  |                           0.0438036 |                         -0.00730751 |                            0.00555556 |                    0.0163912 |          0.0748098 |                0.0438036 |
|     11 |         900 |             0.0633333 |              0.0588889 |           0.0811759 |            0.0762253 |         0.0173364 | True                    | True                        |                      7.05259 |                           0.0477004 |                         -0.0111885  |                            0.00444444 |                    0.0173364 |          0.0874138 |                0.0477004 |
|     19 |         900 |             0.0633333 |              0.06      |           0.0811759 |            0.0774651 |         0.0174651 | True                    | True                        |                      6.7642  |                           0.0475834 |                         -0.0124166  |                            0.00333333 |                    0.0174651 |          0.0898817 |                0.0475834 |
|     23 |         900 |             0.0622222 |              0.0588889 |           0.0799404 |            0.0762253 |         0.0173364 | True                    | True                        |                      6.28459 |                           0.0554516 |                         -0.00343726 |                            0.00333333 |                    0.0173364 |          0.0796626 |                0.0554516 |
|     31 |         900 |             0.0577778 |              0.0533333 |           0.074984  |            0.070003  |         0.0166696 | True                    | True                        |                      7.41645 |                           0.0509799 |                         -0.00235343 |                            0.00444444 |                    0.0166696 |          0.0723564 |                0.0509799 |

## Difficulty-Shift Correction
|   seed | difficulty   |   target_prior |   eval_prior |   conf_violation_rate_d |   probe_violation_rate_d |
|-------:|:-------------|---------------:|-------------:|------------------------:|-------------------------:|
|      7 | easy         |       0.13207  |     0.333333 |               0.0733333 |                0.0733333 |
|      7 | hard         |       0.389062 |     0.333333 |               0.0633333 |                0.0466667 |
|      7 | medium       |       0.478869 |     0.333333 |               0.0333333 |                0.0333333 |
|     11 | easy         |       0.13207  |     0.333333 |               0.09      |                0.09      |
|     11 | hard         |       0.389062 |     0.333333 |               0.0766667 |                0.0633333 |
|     11 | medium       |       0.478869 |     0.333333 |               0.0233333 |                0.0233333 |
|     19 | easy         |       0.13207  |     0.333333 |               0.0966667 |                0.0966667 |
|     19 | hard         |       0.389062 |     0.333333 |               0.0666667 |                0.0566667 |
|     19 | medium       |       0.478869 |     0.333333 |               0.0266667 |                0.0266667 |
|     23 | easy         |       0.13207  |     0.333333 |               0.0633333 |                0.0633333 |
|     23 | hard         |       0.389062 |     0.333333 |               0.09      |                0.08      |
|     23 | medium       |       0.478869 |     0.333333 |               0.0333333 |                0.0333333 |
|     31 | easy         |       0.13207  |     0.333333 |               0.0566667 |                0.0566667 |
|     31 | hard         |       0.389062 |     0.333333 |               0.08      |                0.0666667 |
|     31 | medium       |       0.478869 |     0.333333 |               0.0366667 |                0.0366667 |

## Artifacts
- `seed_metrics_csv`: `outputs/router_phase11_theory_v1/seed_metrics.csv`
- `difficulty_shift_metrics_csv`: `outputs/router_phase11_theory_v1/difficulty_shift_metrics.csv`
- `report_md`: `reports/router_phase11_theory_v1.md`