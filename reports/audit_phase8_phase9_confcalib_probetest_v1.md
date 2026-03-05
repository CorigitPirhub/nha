# Router Phase8 Strict V1 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.036 h`
- Backoff count total: `0`

## Gate Check
- `five_seeds_completed`: `True`
- `backoff_count_zero`: `True`
- `strict_violation_rate_le_8pct`: `False`
- `strict_violation_ci95_upper_le_9pct`: `False`
- `probe_og_improve_ge_5pct`: `True`
- `probe_hard_pos_improve_ge_10pct`: `True`

## Seed Metrics
|   seed |   conf_violation_rate |   conf_violation_ci_up |   conf_fast_ratio |   probe_og_improve_vs_p5_pct |   probe_hard_pos_improve_vs_p5_pct |   probe_latency_extra_vs_p5_ms |
|-------:|----------------------:|-----------------------:|------------------:|-----------------------------:|-----------------------------------:|-------------------------------:|
|      7 |              0.204786 |               0.219076 |          0.850839 |                      5.3991  |                            11.3752 |                      0.0277608 |
|     11 |              0.205718 |               0.220031 |          0.850839 |                      5.47483 |                            16.0961 |                      0.0198255 |
|     19 |              0.205096 |               0.219395 |          0.853947 |                      6.88931 |                            18.6413 |                      0.0204901 |
|     23 |              0.20665  |               0.220985 |          0.853325 |                      6.45437 |                            13.1285 |                      0.0279577 |
|     31 |              0.204786 |               0.219076 |          0.853947 |                      6.10111 |                            16.593  |                      0.0205177 |

## Artifacts
- `outputs/audit_phase8_phase9_confcalib_probetest_v1/stats.json`
- `outputs/audit_phase8_phase9_confcalib_probetest_v1/seed_runs.csv`
- `outputs/audit_phase8_phase9_confcalib_probetest_v1/seeds`