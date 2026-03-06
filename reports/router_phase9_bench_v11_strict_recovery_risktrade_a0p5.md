# Router Phase9 Bench V1 Report

## Summary
- Runtime: `0.023 h`
- Public benchmarks: `3`
- Public test cases: `3218`
- OOD map families (test): `21`

## Gate Check
- `public_benchmarks_ge_3`: `True`
- `public_cases_ge_3000`: `True`
- `ood_map_families_ge_2`: `True`
- `direction_consistent_per_benchmark`: `False`
- `pooled_p_lt_0_01`: `True`
- `exp3_exp4_drift_abs_le_0_5pct`: `False`

## Main Statistics
- `pooled_mean_delta_j`: `2.070837`
- `pooled_mean_delta_j_95ci`: `[1.802795, 2.343373]`
- `pooled_p_value_bootstrap_gt0`: `0.000000e+00`
- `pooled_p_value_wilcoxon`: `1.000000e+00`

## Decomposition (strict accounting)
- `pooled_mean_delta_j_route_only`: `2.200932`
- `pooled_mean_probe_overhead_norm`: `0.130095`
- `pooled_probe_trigger_rate`: `1.000000`

## Artifacts
- `manifest_json`: `data/router_phase9_public_v1/manifest.json`
- `counterfactual_calib_parquet`: `outputs/router_phase9_bench_v11_strict_recovery_risktrade_a0p5/common/router_counterfactual_calib.parquet`
- `counterfactual_test_parquet`: `outputs/router_phase9_bench_v11_strict_recovery_risktrade_a0p5/common/router_counterfactual_test.parquet`
- `router_eval_out`: `outputs/router_phase9_bench_v11_strict_recovery_risktrade_a0p5/router_eval`
- `seed_runs_csv`: `paper/tables_router_v16_strict_recovery_risktrade_a0p5/table_phase9_seed_mean_delta_j.csv`
- `seed_dataset_csv`: `paper/tables_router_v16_strict_recovery_risktrade_a0p5/table_phase9_seed_dataset_delta_j.csv`
- `dataset_summary_csv`: `paper/tables_router_v16_strict_recovery_risktrade_a0p5/table_phase9_dataset_summary.csv`
- `significance_csv`: `paper/tables_router_v16_strict_recovery_risktrade_a0p5/table_phase9_significance.csv`
- `split_table_csv`: `paper/tables_router_v16_strict_recovery_risktrade_a0p5/table_phase9_split_counts.csv`
- `external_baselines_csv`: `paper/tables_router_v16_strict_recovery_risktrade_a0p5/table_phase9_external_baselines.csv`
- `report_md`: `reports/router_phase9_bench_v11_strict_recovery_risktrade_a0p5.md`