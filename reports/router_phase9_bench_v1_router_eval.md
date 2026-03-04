# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.025 h`
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
|      7 |              0.199192 |               0.213346 |          0.828154 |                      8.2275  |                            20.1886 |                       0.158784 |
|     11 |              0.199192 |               0.213346 |          0.833437 |                      6.91391 |                            16.3438 |                       0.157745 |
|     19 |              0.196706 |               0.210798 |          0.821007 |                      6.93878 |                            17.0083 |                       0.152487 |
|     23 |              0.199814 |               0.213983 |          0.827533 |                      6.15953 |                            15.8586 |                       0.162486 |
|     31 |              0.197017 |               0.211117 |          0.82629  |                      5.87553 |                            14.2435 |                       0.161009 |

## Artifacts
- `outputs/router_phase9_bench_v1/router_eval/stats.json`
- `outputs/router_phase9_bench_v1/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v1/router_eval/seeds`