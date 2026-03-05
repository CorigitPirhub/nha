# Router Phase9 Bench V1 Report

## Summary
- Runtime: `0.000 h`
- Public benchmarks: `3`
- Public test cases: `3218`
- OOD map families (test): `21`

## Gate Check
- `public_benchmarks_ge_3`: `True`
- `public_cases_ge_3000`: `True`
- `ood_map_families_ge_2`: `True`
- `direction_consistent_per_benchmark`: `True`
- `pooled_p_lt_0_01`: `True`
- `exp3_exp4_drift_abs_le_0_5pct`: `False`

## Main Statistics
- `pooled_mean_delta_j`: `0.025883`
- `pooled_mean_delta_j_95ci`: `[0.018572, 0.033589]`
- `pooled_p_value_bootstrap_gt0`: `0.000000e+00`
- `pooled_p_value_wilcoxon`: `2.616642e-07`

## Artifacts
- `manifest_json`: `data/router_phase9_public_v1/manifest.json`
- `counterfactual_calib_parquet`: `outputs/router_phase9_bench_v6_strict_knapsack/common/router_counterfactual_calib.parquet`
- `counterfactual_test_parquet`: `outputs/router_phase9_bench_v6_strict_knapsack/common/router_counterfactual_test.parquet`
- `router_eval_out`: `outputs/router_phase9_bench_v6_strict_knapsack/router_eval`
- `seed_runs_csv`: `paper/tables_router_v11_strict_knapsack/table_phase9_seed_mean_delta_j.csv`
- `seed_dataset_csv`: `paper/tables_router_v11_strict_knapsack/table_phase9_seed_dataset_delta_j.csv`
- `dataset_summary_csv`: `paper/tables_router_v11_strict_knapsack/table_phase9_dataset_summary.csv`
- `significance_csv`: `paper/tables_router_v11_strict_knapsack/table_phase9_significance.csv`
- `split_table_csv`: `paper/tables_router_v11_strict_knapsack/table_phase9_split_counts.csv`
- `external_baselines_csv`: `paper/tables_router_v11_strict_knapsack/table_phase9_external_baselines.csv`
- `report_md`: `reports/router_phase9_bench_v6_strict_knapsack.md`