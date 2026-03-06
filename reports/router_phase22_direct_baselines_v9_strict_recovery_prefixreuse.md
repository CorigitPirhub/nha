# Router Phase22 Direct Baselines V1 Report

## Summary
- Runtime: `0.001 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Best direct baseline: `cdt_worstcase_j_v1`

## Gate Check
- `direct_baselines_ge_2`: `True`
- `same_protocol_and_budget`: `True`
- `either_win_or_reframe`: `False`
- `main_result_significant`: `False`

## Main Metrics (vs best direct baseline)
- `J_improve_mean`: `-5.371%`
- `risk_delta_mean_pct`: `-0.056`
- `pooled_delta_j_ci95`: `[-0.05672415734425919, -0.050758218407133876]`
- `pooled_p_value_bootstrap_gt0`: `1.000000e+00`
- `seed_level_p_value_wilcoxon`: `1.000000e+00`
- `ours_vs_best_direct_significant_p_lt_0_01`: `False`

## Direct Baseline Strength (vs P5)
- `best_direct_vs_p5_J_improve_mean`: `-0.043%`
- `best_direct_vs_p5_pooled_ci95`: `[-0.000969425872502327, 0.0002896749238244242]`
- `best_direct_vs_p5_p_value_bootstrap_gt0`: `9.025000e-01`
- `best_direct_vs_p5_significant_p_lt_0_01`: `False`

## Note
- Ours does **not** improve over the best direct baseline in mean `J` under this protocol; claims should be reframed accordingly.
- Claims should be reframed accordingly (see `paper/related_work_neurips_alignment.md`).

## Artifacts
- `out_dir`: `outputs/router_phase22_direct_baselines_v9_strict_recovery_prefixreuse`
- `seed_metrics_csv`: `outputs/router_phase22_direct_baselines_v9_strict_recovery_prefixreuse/tables/seed_metrics.csv`
- `method_summary_csv`: `outputs/router_phase22_direct_baselines_v9_strict_recovery_prefixreuse/tables/method_summary.csv`
- `significance_csv`: `outputs/router_phase22_direct_baselines_v9_strict_recovery_prefixreuse/tables/significance.csv`
- `paper_table_csv`: `paper/tables_router_v19_strict_recovery_prefixreuse/table_phase22_direct_baselines.csv`
- `report_md`: `reports/router_phase22_direct_baselines_v9_strict_recovery_prefixreuse.md`
