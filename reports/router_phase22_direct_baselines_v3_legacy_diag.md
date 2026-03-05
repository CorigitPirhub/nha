# Router Phase22 Direct Baselines V1 Report

## Summary
- Runtime: `0.001 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Best direct baseline: `cdt_worstcase_j_v1`

## Gate Check
- `direct_baselines_ge_2`: `True`
- `same_protocol_and_budget`: `True`
- `either_win_or_reframe`: `True`
- `main_result_significant`: `True`

## Main Metrics (vs best direct baseline)
- `J_improve_mean`: `2.609%`
- `risk_delta_mean_pct`: `-0.516`
- `pooled_delta_j_ci95`: `[0.009846825661253564, 0.03904512820592677]`
- `pooled_p_value_bootstrap_gt0`: `1.300000e-03`
- `seed_level_p_value_wilcoxon`: `3.125000e-02`
- `ours_vs_best_direct_significant_p_lt_0_01`: `True`

## Direct Baseline Strength (vs P5)
- `best_direct_vs_p5_J_improve_mean`: `1.374%`
- `best_direct_vs_p5_pooled_ci95`: `[0.007441446134389481, 0.02052797935325076]`
- `best_direct_vs_p5_p_value_bootstrap_gt0`: `0.000000e+00`
- `best_direct_vs_p5_significant_p_lt_0_01`: `True`


## Artifacts
- `out_dir`: `outputs/router_phase22_direct_baselines_v3_legacy_diag`
- `seed_metrics_csv`: `outputs/router_phase22_direct_baselines_v3_legacy_diag/tables/seed_metrics.csv`
- `method_summary_csv`: `outputs/router_phase22_direct_baselines_v3_legacy_diag/tables/method_summary.csv`
- `significance_csv`: `outputs/router_phase22_direct_baselines_v3_legacy_diag/tables/significance.csv`
- `paper_table_csv`: `paper/tables_router_v8_legacy_diag/table_phase22_direct_baselines.csv`
- `report_md`: `reports/router_phase22_direct_baselines_v3_legacy_diag.md`
