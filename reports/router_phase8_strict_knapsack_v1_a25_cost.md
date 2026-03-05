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
- `probe_og_improve_ge_5pct`: `True`
- `probe_hard_pos_improve_ge_10pct`: `True`

## Seed Metrics
|   seed |   conf_violation_rate |   conf_violation_ci_up |   conf_fast_ratio |   probe_og_improve_vs_p5_pct |   probe_hard_pos_improve_vs_p5_pct |   probe_latency_extra_vs_p5_ms |
|-------:|----------------------:|-----------------------:|------------------:|-----------------------------:|-----------------------------------:|-------------------------------:|
|      7 |              0.193909 |               0.207931 |          0.821318 |                     10.9286  |                            15.6108 |                      0.0675788 |
|     11 |              0.183654 |               0.197407 |          0.800497 |                      9.57962 |                            11.6711 |                      0.0648507 |
|     19 |              0.191112 |               0.205062 |          0.816656 |                      9.66719 |                            13.1671 |                      0.0651739 |
|     23 |              0.182411 |               0.19613  |          0.795525 |                     11.3211  |                            18.6572 |                      0.062672  |
|     31 |              0.188626 |               0.202511 |          0.804537 |                      9.51732 |                            15.3176 |                      0.0694558 |

## Artifacts
- `outputs/router_phase8_strict_knapsack_v1_a25_cost/stats.json`
- `outputs/router_phase8_strict_knapsack_v1_a25_cost/seed_runs.csv`
- `outputs/router_phase8_strict_knapsack_v1_a25_cost/seeds`