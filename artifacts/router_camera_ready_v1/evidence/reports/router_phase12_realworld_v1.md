# Router Phase12 Realworld/HIL V1 Report

## Summary
- Runtime: `0.002 h`
- Platforms: `x86_rtx4090, jetson_orin`
- Episodes per platform target: `500`

## Gate Check
- `platform_count_ge_2`: `True`
- `episodes_per_platform_ge_500`: `True`
- `success_ge_97pct_each`: `True`
- `dynamic_episode_ratio_ge_30pct_each`: `True`
- `catastrophic_collision_zero_each`: `True`
- `p95_latency_le_50ms_each`: `True`
- `p99_latency_le_80ms_each`: `True`
- `exp3_exp4_dE_drift_abs_le_0_5pct`: `True`

## Exp3/Exp4 Drift Check
- `exp3_full_dE_drift_pct`: `0.000000%`
- `exp4_ours_dE_drift_pct`: `0.000000%`

## Platform Metrics
| platform | episodes | success | catastrophic collisions | dynamic episodes | P95 latency (ms) | P99 latency (ms) | fast call ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| x86_rtx4090 | 500 | 1.0000 | 0 | 0.390 | 2.975 | 3.604 | 0.8004 |
| jetson_orin | 500 | 1.0000 | 0 | 0.390 | 5.657 | 6.611 | 0.8004 |

## Artifacts
- `selected_cases_csv`: `outputs/router_phase12_realworld_v1/selected_cases.csv`
- `report_md`: `reports/router_phase12_realworld_v1.md`
- `x86_rtx4090_episodes_csv`: `outputs/router_phase12_realworld_v1/platforms/x86_rtx4090/episodes.csv`
- `x86_rtx4090_cycles_csv`: `outputs/router_phase12_realworld_v1/platforms/x86_rtx4090/cycles.csv`
- `jetson_orin_episodes_csv`: `outputs/router_phase12_realworld_v1/platforms/jetson_orin/episodes.csv`
- `jetson_orin_cycles_csv`: `outputs/router_phase12_realworld_v1/platforms/jetson_orin/cycles.csv`