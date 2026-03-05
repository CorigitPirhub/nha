# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.011 h`
- Backoff count total: `0`

## Gate Check
- `five_seeds_completed`: `True`
- `backoff_count_zero`: `True`
- `strict_violation_rate_le_8pct`: `True`
- `strict_violation_ci95_upper_le_9pct`: `True`
- `probe_og_improve_ge_5pct`: `False`
- `probe_hard_pos_improve_ge_10pct`: `True`

## Seed Metrics
|   seed |   conf_violation_rate |   conf_violation_ci_up |   conf_fast_ratio |   probe_og_improve_vs_p5_pct |   probe_hard_pos_improve_vs_p5_pct |   probe_latency_extra_vs_p5_ms |
|-------:|----------------------:|-----------------------:|------------------:|-----------------------------:|-----------------------------------:|-------------------------------:|
|      7 |              0.193909 |               0.207931 |          0.821318 |                    -11.9496  |                            13.5662 |                       0.444712 |
|     11 |              0.183654 |               0.197407 |          0.800497 |                    -53.8414  |                            14.4084 |                       1.08937  |
|     19 |              0.191112 |               0.205062 |          0.816656 |                    -41.9636  |                            11.679  |                       0.931388 |
|     23 |              0.182411 |               0.19613  |          0.795525 |                     -4.47806 |                            15.1061 |                       0.249924 |
|     31 |              0.188626 |               0.202511 |          0.804537 |                    -28.4733  |                            16.1172 |                       0.778275 |

## Artifacts
- `outputs/router_phase8_strict_knapsack_v1_a35/stats.json`
- `outputs/router_phase8_strict_knapsack_v1_a35/seed_runs.csv`
- `outputs/router_phase8_strict_knapsack_v1_a35/seeds`