# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7]`
- Runtime: `0.002 h`
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
|      7 |              0.193909 |               0.207931 |          0.821318 |                    -0.306445 |                                  0 |                     0.00544243 |

## Artifacts
- `outputs/router_phase8_strict_knapsack_seed7/stats.json`
- `outputs/router_phase8_strict_knapsack_seed7/seed_runs.csv`
- `outputs/router_phase8_strict_knapsack_seed7/seeds`