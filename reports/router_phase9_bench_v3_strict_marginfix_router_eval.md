# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.012 h`
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
|      7 |              0.193909 |               0.207931 |          0.821318 |                     -38.8064 |                            5.24555 |                       0.755342 |
|     11 |              0.183654 |               0.197407 |          0.800497 |                     -53.8872 |                            6.43419 |                       0.927056 |
|     19 |              0.191112 |               0.205062 |          0.816656 |                     -38.0519 |                            8.10037 |                       0.768244 |
|     23 |              0.182411 |               0.19613  |          0.795525 |                     -36.6461 |                            7.43232 |                       0.757486 |
|     31 |              0.188626 |               0.202511 |          0.804537 |                     -56.7738 |                            4.71737 |                       1.12715  |

## Artifacts
- `outputs/router_phase9_bench_v3_strict_marginfix/router_eval/stats.json`
- `outputs/router_phase9_bench_v3_strict_marginfix/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v3_strict_marginfix/router_eval/seeds`