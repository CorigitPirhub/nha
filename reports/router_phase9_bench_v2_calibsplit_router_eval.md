# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.022 h`
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
|      7 |             0.0618397 |              0.0706955 |          0.240522 |                     0        |                             0      |                        0       |
|     11 |             0.0609074 |              0.0697057 |          0.239279 |                     0        |                             0      |                        0       |
|     19 |             0.0599751 |              0.0687154 |          0.236793 |                     0        |                             0      |                        0       |
|     23 |             0.0565569 |              0.0650793 |          0.225295 |                     0        |                             0      |                        0       |
|     31 |             0.0605966 |              0.0693757 |          0.330329 |                    -0.725172 |                            21.6383 |                        0.17848 |

## Artifacts
- `outputs/router_phase9_bench_v2_calibsplit/router_eval/stats.json`
- `outputs/router_phase9_bench_v2_calibsplit/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v2_calibsplit/router_eval/seeds`