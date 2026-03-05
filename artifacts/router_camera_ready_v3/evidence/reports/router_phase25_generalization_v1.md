# Phase25 Generalization (v1)

## Summary
- `runtime_hours`: `0.0035474720622167095`
- `seeds`: `[7, 11, 19, 23, 31]`
- `settings`: `['mp', 'csm']`
- `gate_check`: `{'new_settings_ge_2': True, 'risk_control_holds_in_new_settings': True, 'trend_consistent': True}`
- `artifacts`: `{'out_dir': 'outputs/router_phase25_generalization_v1', 'report_md': 'reports/router_phase25_generalization_v1.md', 'fig_dir': 'paper/figures_router_v7', 'per_setting_stats': {'mp': 'outputs/router_phase25_generalization_v1/settings/mp', 'csm': 'outputs/router_phase25_generalization_v1/settings/csm'}}`

## Per-setting Gates and Deltas (test, mean over seeds)
- `best_feasible_*` is the best (min `J_mean`) point in the aligned sweep grid among rows with `risk_hold_all_seeds=True`.
- `selected_*` is the mean of the policy selected by the calibration-time grid search (same logic as Phase23).
| setting   |   num_test | baseline_best_arm   |   baseline_J_mean |   baseline_latency_ms |   baseline_violation_rate |   selected_J_mean |   selected_latency_ms |   selected_violation_rate |   best_feasible_J_mean |   best_feasible_latency_ms |   best_feasible_violation_rate | risk_hold_all_seeds   | pareto_strict   | bestJ_not_worse   |    dJ_mean |   dLatency_mean_ms |   dRisk_mean |
|:----------|-----------:|:--------------------|------------------:|----------------------:|--------------------------:|------------------:|----------------------:|--------------------------:|-----------------------:|---------------------------:|-------------------------------:|:----------------------|:----------------|:------------------|-----------:|-------------------:|-------------:|
| mp        |       2300 | always_mid          |          0.702837 |               1.26563 |                 0.0382609 |           0.74346 |               1.42036 |                0.0335652  |               0.702158 |                    1.26694 |                      0.038087  | True                  | False           | True              |  0.0406236 |           0.154725 |  -0.00469565 |
| csm       |        900 | always_slow         |          1.13448  |               3.43579 |                 0         |           1.07318 |               3.13496 |                0.00666667 |               0.982241 |                    2.43874 |                      0.0322222 | True                  | False           | True              | -0.0613026 |          -0.300832 |   0.00666667 |

## Artifacts
- `fig_dir`: `paper/figures_router_v7`
- `out_dir`: `outputs/router_phase25_generalization_v1`
- `per_setting_stats`: `{'mp': 'outputs/router_phase25_generalization_v1/settings/mp', 'csm': 'outputs/router_phase25_generalization_v1/settings/csm'}`
- `report_md`: `reports/router_phase25_generalization_v1.md`