# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.026 h`
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
|      7 |              0.194531 |               0.208568 |          0.828465 |                      5.74049 |                            24.7062 |                       0.238886 |
|     11 |              0.193288 |               0.207293 |          0.828776 |                      5.34469 |                            11.7868 |                       0.191979 |
|     19 |              0.192356 |               0.206337 |          0.8266   |                      5.047   |                            16.8101 |                       0.12783  |
|     23 |              0.19422  |               0.208249 |          0.830951 |                      5.56775 |                            15.4706 |                       0.194613 |
|     31 |              0.193909 |               0.207931 |          0.829708 |                      6.05868 |                            14.5984 |                       0.191172 |

## Artifacts
- `outputs/router_phase9_bench_v1/router_eval_relaxed_hardfocus/stats.json`
- `outputs/router_phase9_bench_v1/router_eval_relaxed_hardfocus/seed_runs.csv`
- `outputs/router_phase9_bench_v1/router_eval_relaxed_hardfocus/seeds`