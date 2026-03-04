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
|      7 |             0.0566667 |              0.0737412 |          0.541111 |                     10.3651  |                            59.0344 |                      0.0107663 |
|     11 |             0.0633333 |              0.0811759 |          0.551111 |                      7.05259 |                            34.0236 |                      0.0129597 |
|     19 |             0.0633333 |              0.0811759 |          0.547778 |                      6.7642  |                            40.6439 |                      0.0106459 |
|     23 |             0.0622222 |              0.0799404 |          0.55     |                      6.28459 |                            29.4391 |                      0.0128684 |
|     31 |             0.0577778 |              0.074984  |          0.553333 |                      7.41645 |                            34.9512 |                      0.0128837 |

## Artifacts
- `outputs/router_phase8_strict_v1/stats.json`
- `outputs/router_phase8_strict_v1/seed_runs.csv`
- `outputs/router_phase8_strict_v1/seeds`