# Router Phase8 Strict V2 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.053 h`
- Backoff count total: `0`

## Gate Check
- `five_seeds_completed`: `True`
- `backoff_count_zero`: `True`
- `strict_violation_rate_le_target`: `True`
- `strict_violation_ci95_upper_le_target`: `True`
- `probe_og_improve_ge_target`: `False`
- `probe_hard_pos_improve_ge_target`: `False`

## Seed Metrics
|   seed |   conf_violation_rate |   conf_violation_ci_up |   conf_fast_ratio |   probe_og_improve_vs_p5_pct |   probe_hard_pos_improve_vs_p5_pct |   probe_latency_extra_vs_p5_ms |
|-------:|----------------------:|-----------------------:|------------------:|-----------------------------:|-----------------------------------:|-------------------------------:|
|      7 |              0.192666 |               0.206656 |          0.811374 |                     4.02383  |                            34.625  |                       1.0825   |
|     11 |              0.188005 |               0.201874 |          0.804848 |                     0        |                             0      |                       0.892023 |
|     19 |              0.159105 |               0.172148 |          0.747048 |                     0.63806  |                            13.94   |                       1.05309  |
|     23 |              0.195152 |               0.209205 |          0.811063 |                     3.52937  |                            14.9578 |                       1.10155  |
|     31 |              0.16097  |               0.17407  |          0.759167 |                     0.529315 |                            14.2978 |                       1.03106  |

## Artifacts
- `outputs/router_phase9_bench_v3_legacy_diag_rerun1/router_eval/stats.json`
- `outputs/router_phase9_bench_v3_legacy_diag_rerun1/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v3_legacy_diag_rerun1/router_eval/seeds`