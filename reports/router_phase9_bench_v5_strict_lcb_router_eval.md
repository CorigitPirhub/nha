# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.008 h`
- Backoff count total: `0`

## Gate Check
- `five_seeds_completed`: `True`
- `backoff_count_zero`: `True`
- `strict_violation_rate_le_8pct`: `True`
- `strict_violation_ci95_upper_le_9pct`: `True`
- `probe_og_improve_ge_5pct`: `False`
- `probe_hard_pos_improve_ge_10pct`: `False`

## Seed Metrics
|   seed |   conf_violation_rate |   conf_violation_ci_up |   conf_fast_ratio |   probe_og_improve_vs_p5_pct |   probe_hard_pos_improve_vs_p5_pct |   probe_latency_extra_vs_p5_ms |
|-------:|----------------------:|-----------------------:|------------------:|-----------------------------:|-----------------------------------:|-------------------------------:|
|      7 |              0.193909 |               0.207931 |          0.821318 |                     -109.373 |                            7.01238 |                        2.22085 |
|     11 |              0.183654 |               0.197407 |          0.800497 |                     -142.823 |                            8.21125 |                        2.5483  |
|     19 |              0.191112 |               0.205062 |          0.816656 |                     -118.646 |                            7.59121 |                        2.38037 |
|     23 |              0.182411 |               0.19613  |          0.795525 |                     -105.451 |                           12.9061  |                        2.21506 |
|     31 |              0.188626 |               0.202511 |          0.804537 |                     -109.208 |                            7.43679 |                        2.21376 |

## Artifacts
- `outputs/router_phase9_bench_v5_strict_lcb/router_eval/stats.json`
- `outputs/router_phase9_bench_v5_strict_lcb/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v5_strict_lcb/router_eval/seeds`