# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.038 h`
- Backoff count total: `0`

## Gate Check
- `five_seeds_completed`: `True`
- `backoff_count_zero`: `True`
- `strict_violation_rate_le_8pct`: `True`
- `strict_violation_ci95_upper_le_9pct`: `True`
- `probe_og_improve_ge_5pct`: `False`
- `probe_hard_pos_improve_ge_10pct`: `True`

## Seed Metrics
|   seed |   conf_violation_rate |   conf_violation_ci_up |   conf_fast_ratio |   probe_og_improve_vs_p5_pct |   probe_hard_pos_improve_vs_p5_pct |   probe_latency_extra_vs_p5_ms |
|-------:|----------------------:|-----------------------:|------------------:|-----------------------------:|-----------------------------------:|-------------------------------:|
|      7 |             0.0544444 |              0.0712507 |          0.53     |                      1.85461 |                            38.9109 |                     0.00422795 |
|     11 |             0.0444444 |              0.0599545 |          0.528889 |                      1.47199 |                            37.1706 |                     0.0129437  |
|     19 |             0.06      |              0.0774651 |          0.527778 |                     14.1012  |                            45.5081 |                     0.0317066  |
|     23 |             0.0577778 |              0.074984  |          0.53     |                      1.60692 |                            36.6179 |                     0.00422237 |
|     31 |             0.0566667 |              0.0737412 |          0.553333 |                     19.6282  |                            56.2509 |                     0.0294646  |

## Artifacts
- `outputs/router_phase8_strict_v2_calibsplit/stats.json`
- `outputs/router_phase8_strict_v2_calibsplit/seed_runs.csv`
- `outputs/router_phase8_strict_v2_calibsplit/seeds`