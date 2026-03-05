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
- `probe_violation_rate_mean`: `0.048000`
- `probe_theory_upper_mean`: `0.063961`
- `max_probe_bound_gap_pct`: `1.707%`
- `probe_monotone_safety_all`: `True`

## Seed Metrics
|   seed |   num_cases |   conf_violation_rate |   probe_violation_rate |   conf_theory_upper |   probe_theory_upper |   probe_bound_gap | probe_monotone_safety   | probe_fast_subset_of_conf   |   probe_og_improve_vs_p5_pct |   probe_target_prior_violation_rate |   selection_shift_target_minus_eval |   decomp_safety_gain_conf_minus_probe |   decomp_finite_sample_slack |   decomp_rhs_upper |   decomp_lhs_target_risk |
|-------:|------------:|----------------------:|-----------------------:|--------------------:|---------------------:|------------------:|:------------------------|:----------------------------|-----------------------------:|------------------------------------:|------------------------------------:|--------------------------------------:|-----------------------------:|-------------------:|-------------------------:|
|      7 |         900 |             0.0544444 |              0.0533333 |           0.0712507 |            0.070003  |         0.0166696 | True                    | True                        |                      1.85461 |                           0.0554703 |                          0.00213694 |                            0.00111111 |                    0.0166696 |          0.0721399 |                0.0554703 |
|     11 |         900 |             0.0444444 |              0.0422222 |           0.0599545 |            0.0574215 |         0.0151993 | True                    | True                        |                      1.47199 |                           0.0440905 |                          0.00186831 |                            0.00222222 |                    0.0151993 |          0.0592898 |                0.0440905 |
|     19 |         900 |             0.06      |              0.0455556 |           0.0774651 |            0.0612176 |         0.015662  | True                    | True                        |                     14.1012  |                           0.0506339 |                          0.00507838 |                            0.0144444  |                    0.015662  |          0.0662959 |                0.0506339 |
|     23 |         900 |             0.0577778 |              0.0566667 |           0.074984  |            0.0737412 |         0.0170745 | True                    | True                        |                      1.60692 |                           0.0550363 |                         -0.00163041 |                            0.00111111 |                    0.0170745 |          0.0753716 |                0.0550363 |
|     31 |         900 |             0.0566667 |              0.0422222 |           0.0737412 |            0.0574215 |         0.0151993 | True                    | True                        |                     19.6282  |                           0.039508  |                         -0.00271425 |                            0.0144444  |                    0.0151993 |          0.0601357 |                0.039508  |

## Difficulty-Shift Correction
|   seed | difficulty   |   target_prior |   eval_prior |   conf_violation_rate_d |   probe_violation_rate_d |
|-------:|:-------------|---------------:|-------------:|------------------------:|-------------------------:|
|      7 | easy         |       0.13207  |     0.333333 |               0.0566667 |                0.0566667 |
|      7 | hard         |       0.389062 |     0.333333 |               0.02      |                0.0166667 |
|      7 | medium       |       0.478869 |     0.333333 |               0.0866667 |                0.0866667 |
|     11 | easy         |       0.13207  |     0.333333 |               0.04      |                0.04      |
|     11 | hard         |       0.389062 |     0.333333 |               0.0366667 |                0.03      |
|     11 | medium       |       0.478869 |     0.333333 |               0.0566667 |                0.0566667 |
|     19 | easy         |       0.13207  |     0.333333 |               0.0466667 |                0.0366667 |
|     19 | hard         |       0.389062 |     0.333333 |               0.03      |                0.0233333 |
|     19 | medium       |       0.478869 |     0.333333 |               0.103333  |                0.0766667 |
|     23 | easy         |       0.13207  |     0.333333 |               0.07      |                0.07      |
|     23 | hard         |       0.389062 |     0.333333 |               0.0266667 |                0.0233333 |
|     23 | medium       |       0.478869 |     0.333333 |               0.0766667 |                0.0766667 |
|     31 | easy         |       0.13207  |     0.333333 |               0.07      |                0.0566667 |
|     31 | hard         |       0.389062 |     0.333333 |               0.0366667 |                0.0166667 |
|     31 | medium       |       0.478869 |     0.333333 |               0.0633333 |                0.0533333 |

## Artifacts
- `seed_metrics_csv`: `outputs/router_phase11_theory_v2_calibsplit/seed_metrics.csv`
- `difficulty_shift_metrics_csv`: `outputs/router_phase11_theory_v2_calibsplit/difficulty_shift_metrics.csv`
- `report_md`: `reports/router_phase11_theory_v2_calibsplit.md`