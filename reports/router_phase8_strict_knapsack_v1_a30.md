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
- `probe_hard_pos_improve_ge_10pct`: `False`

## Seed Metrics
|   seed |   conf_violation_rate |   conf_violation_ci_up |   conf_fast_ratio |   probe_og_improve_vs_p5_pct |   probe_hard_pos_improve_vs_p5_pct |   probe_latency_extra_vs_p5_ms |
|-------:|----------------------:|-----------------------:|------------------:|-----------------------------:|-----------------------------------:|-------------------------------:|
|      7 |              0.193909 |               0.207931 |          0.821318 |                     -4.01946 |                           12.3171  |                      0.263584  |
|     11 |              0.183654 |               0.197407 |          0.800497 |                    -15.8554  |                           13.5122  |                      0.394308  |
|     19 |              0.191112 |               0.205062 |          0.816656 |                      0.45145 |                            7.13762 |                      0.0762024 |
|     23 |              0.182411 |               0.19613  |          0.795525 |                      2.61972 |                           11.3322  |                      0.0563162 |
|     31 |              0.188626 |               0.202511 |          0.804537 |                     -3.31107 |                           12.6248  |                      0.242163  |

## Artifacts
- `outputs/router_phase8_strict_knapsack_v1_a30/stats.json`
- `outputs/router_phase8_strict_knapsack_v1_a30/seed_runs.csv`
- `outputs/router_phase8_strict_knapsack_v1_a30/seeds`