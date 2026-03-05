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
|      7 |              0.193909 |               0.207931 |          0.821318 |                   -0.453141  |                            1.81703 |                      0.0314146 |
|     11 |              0.183654 |               0.197407 |          0.800497 |                   -1.43531   |                            1.13129 |                      0.0317852 |
|     19 |              0.191112 |               0.205062 |          0.816656 |                    0.707794  |                            4.4523  |                      0.0318042 |
|     23 |              0.182411 |               0.19613  |          0.795525 |                    0.0791624 |                            3.67108 |                      0.0322802 |
|     31 |              0.188626 |               0.202511 |          0.804537 |                    1.9566    |                            4.21857 |                      0.0478916 |

## Artifacts
- `outputs/router_phase8_strict_knapsack_v1_a20/stats.json`
- `outputs/router_phase8_strict_knapsack_v1_a20/seed_runs.csv`
- `outputs/router_phase8_strict_knapsack_v1_a20/seeds`