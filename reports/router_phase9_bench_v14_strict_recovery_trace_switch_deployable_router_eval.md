# Router Phase8 Strict V2 Report

## Summary
- Seeds: `[7, 11, 19, 23, 31]`
- Runtime: `0.021 h`
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
|      7 |             0.0316967 |              0.0383301 |          0.399938 |                    -0.496797 |                            4.84682 |                       0.936542 |
|     11 |             0.0264139 |              0.0325446 |          0.378496 |                    -0.067167 |                           12.6453  |                       0.936222 |
|     19 |             0.031386  |              0.0379912 |          0.396209 |                     0.209672 |                            4.61895 |                       0.934576 |
|     23 |             0.0270354 |              0.033228  |          0.393412 |                    -0.203303 |                            4.53733 |                       0.934567 |
|     31 |             0.0320075 |              0.038669  |          0.392169 |                     0.302702 |                            0       |                       0.905912 |

## Artifacts
- `outputs/router_phase9_bench_v14_strict_recovery_trace_switch_deployable/router_eval/stats.json`
- `outputs/router_phase9_bench_v14_strict_recovery_trace_switch_deployable/router_eval/seed_runs.csv`
- `outputs/router_phase9_bench_v14_strict_recovery_trace_switch_deployable/router_eval/seeds`