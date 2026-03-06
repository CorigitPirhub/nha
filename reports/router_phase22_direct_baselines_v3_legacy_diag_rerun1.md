# Router Phase22 Direct Baselines V1 Report

## Summary
- Runtime: `0.001 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Best direct baseline: `cdt_worstcase_j_v1`

## Gate Check
- `direct_baselines_ge_2`: `True`
- `same_protocol_and_budget`: `True`
- `either_win_or_reframe`: `False`
- `main_result_significant`: `True`

## Main Metrics (vs best direct baseline)
- `J_improve_mean`: `-6.615%`
- `risk_delta_mean_pct`: `-0.099`
- `pooled_delta_j_ci95`: `[-0.0687572686358281, -0.0635496260619436]`
- `pooled_p_value_bootstrap_gt0`: `1.000000e+00`
- `seed_level_p_value_wilcoxon`: `1.000000e+00`
- `ours_vs_best_direct_significant_p_lt_0_01`: `False`

## Direct Baseline Strength (vs P5)
- `best_direct_vs_p5_J_improve_mean`: `1.234%`
- `best_direct_vs_p5_pooled_ci95`: `[0.007743318917699172, 0.017193026852338856]`
- `best_direct_vs_p5_p_value_bootstrap_gt0`: `0.000000e+00`
- `best_direct_vs_p5_significant_p_lt_0_01`: `True`

## Note
- Ours does **not** improve over the best direct baseline in mean `J` under this protocol; claims should be reframed accordingly.
- Claims should be reframed accordingly (see `paper/related_work_neurips_alignment.md`).

## Artifacts
- `out_dir`: `outputs/router_phase22_direct_baselines_v3_legacy_diag_rerun1`
- `seed_metrics_csv`: `outputs/router_phase22_direct_baselines_v3_legacy_diag_rerun1/tables/seed_metrics.csv`
- `method_summary_csv`: `outputs/router_phase22_direct_baselines_v3_legacy_diag_rerun1/tables/method_summary.csv`
- `significance_csv`: `outputs/router_phase22_direct_baselines_v3_legacy_diag_rerun1/tables/significance.csv`
- `paper_table_csv`: `paper/tables_router_v8_legacy_diag_rerun1/table_phase22_direct_baselines.csv`
- `report_md`: `reports/router_phase22_direct_baselines_v3_legacy_diag_rerun1.md`
