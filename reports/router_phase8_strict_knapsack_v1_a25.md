# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.010 h`
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
|      7 |              0.193909 |               0.207931 |          0.821318 |                    3.35285   |                            6.93887 |                      0.0511938 |
|     11 |              0.183654 |               0.197407 |          0.800497 |                    2.22356   |                            9.83555 |                      0.0462946 |
|     19 |              0.191112 |               0.205062 |          0.816656 |                    0.320022  |                            6.2897  |                      0.0627    |
|     23 |              0.182411 |               0.19613  |          0.795525 |                   -0.0259876 |                            3.67108 |                      0.0341562 |
|     31 |              0.188626 |               0.202511 |          0.804537 |                    2.77601   |                            6.43851 |                      0.0515228 |

## Artifacts
- `outputs/router_phase8_strict_knapsack_v1_a25/stats.json`
- `outputs/router_phase8_strict_knapsack_v1_a25/seed_runs.csv`
- `outputs/router_phase8_strict_knapsack_v1_a25/seeds`