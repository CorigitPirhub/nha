# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.045 h`
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
|      7 |              0.111871 |               0.123227 |          0.615911 |                      7.48062 |                            20.3335 |                      0.285844  |
|     11 |              0.117775 |               0.129371 |          0.633623 |                     15.6578  |                            36.7701 |                      0.131778  |
|     19 |              0.11964  |               0.131309 |          0.637352 |                     15.8782  |                            31.5364 |                      0.0938485 |
|     23 |              0.11995  |               0.131631 |          0.643257 |                     13.1228  |                            25.6882 |                      0.047854  |
|     31 |              0.110628 |               0.121933 |          0.606899 |                      7.30019 |                            13.4274 |                      0.0178585 |

## Artifacts
- `outputs/router_phase9_bench_v3_legacy_diag/router_eval/stats.json`
- `outputs/router_phase9_bench_v3_legacy_diag/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v3_legacy_diag/router_eval/seeds`