# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.017 h`
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
|      7 |              0.193909 |               0.207931 |          0.821318 |                     -17.6048 |                            8.45469 |                       0.419271 |
|     11 |              0.183654 |               0.197407 |          0.800497 |                     -27.4155 |                           13.0192  |                       0.607749 |
|     19 |              0.191112 |               0.205062 |          0.816656 |                     -17.4511 |                            7.59121 |                       0.426248 |
|     23 |              0.182411 |               0.19613  |          0.795525 |                     -22.3229 |                           19.4577  |                       0.592629 |
|     31 |              0.188626 |               0.202511 |          0.804537 |                     -26.1266 |                            7.43679 |                       0.593972 |

## Artifacts
- `outputs/router_phase9_bench_v4_strict_costaware/router_eval/stats.json`
- `outputs/router_phase9_bench_v4_strict_costaware/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v4_strict_costaware/router_eval/seeds`