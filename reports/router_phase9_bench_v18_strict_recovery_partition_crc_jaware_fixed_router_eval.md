# Router Phase8 Strict V2 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.047 h`
- Backoff count total: `0`

## Gate Check
- `five_seeds_completed`: `True`
- `backoff_count_zero`: `True`
- `strict_violation_rate_le_target`: `True`
- `strict_violation_ci95_upper_le_target`: `True`
- `probe_og_improve_ge_target`: `False`
- `probe_hard_pos_improve_ge_target`: `False`

## Seed Metrics
|   seed |   conf_violation_rate |   conf_violation_ci_up |   conf_fast_ratio |   probe_og_improve_vs_p5_pct |   probe_hard_pos_improve_vs_p5_pct |   probe_latency_extra_vs_p5_ms |
|-------:|----------------------:|-----------------------:|------------------:|-----------------------------:|-----------------------------------:|-------------------------------:|
|      7 |             0.0372902 |              0.0444076 |          0.364512 |                      0       |                             0      |                       0.907999 |
|     11 |             0.0366687 |              0.0437345 |          0.36762  |                      0       |                             0      |                       0.907999 |
|     19 |             0.0354257 |              0.0423866 |          0.356743 |                      0       |                             0      |                       0.907999 |
|     23 |             0.0348042 |              0.0417119 |          0.377564 |                     13.7887  |                            59.6117 |                       1.46446  |
|     31 |             0.0372902 |              0.0444076 |          0.381914 |                      8.86027 |                            61.2655 |                       1.12051  |

## Artifacts
- `outputs/router_phase9_bench_v18_strict_recovery_partition_crc_jaware_fixed/router_eval/stats.json`
- `outputs/router_phase9_bench_v18_strict_recovery_partition_crc_jaware_fixed/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v18_strict_recovery_partition_crc_jaware_fixed/router_eval/seeds`