# Router Phase8 Strict V2 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.017 h`
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
|      7 |             0.031386  |              0.0379912 |          0.357676 |                  -0.00175507 |                           0        |                       0.893824 |
|     11 |             0.0320075 |              0.038669  |          0.348042 |                  -0.0034274  |                           0.797996 |                       0.895773 |
|     19 |             0.0394655 |              0.04676   |          0.334369 |                   0          |                           0        |                       0.892023 |
|     23 |             0.0344935 |              0.0413744 |          0.368863 |                  -0.00342986 |                           0.278925 |                       0.895822 |
|     31 |             0.032629  |              0.0393462 |          0.358919 |                  -0.00156001 |                           0.898928 |                       0.893893 |

## Artifacts
- `outputs/router_phase9_bench_v10_strict_recovery_boundary/router_eval/stats.json`
- `outputs/router_phase9_bench_v10_strict_recovery_boundary/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v10_strict_recovery_boundary/router_eval/seeds`