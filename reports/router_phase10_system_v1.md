# Router Phase10 System V1 Report

## Summary
- Runtime: `0.001 h`
- Platforms: `x86_rtx4090, jetson_orin`
- Episodes per platform target: `240`

## Gate Check
- `platform_count_ge_2`: `True`
- `episodes_per_platform_ge_200`: `True`
- `success_ge_97pct_each`: `True`
- `catastrophic_collision_zero_each`: `True`
- `p95_latency_le_50ms_each`: `True`
- `p99_latency_le_80ms_each`: `True`

## Platform Metrics
| platform | episodes | success | catastrophic collisions | dynamic episodes | P95 latency (ms) | P99 latency (ms) | fast call ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| x86_rtx4090 | 240 | 1.0000 | 0 | 0.125 | 2.973 | 3.577 | 0.7884 |
| jetson_orin | 240 | 1.0000 | 0 | 0.125 | 5.656 | 6.628 | 0.7884 |

## Artifacts
- `selected_cases_csv`: `outputs/router_phase10_system_v1/selected_cases.csv`
- `report_md`: `reports/router_phase10_system_v1.md`
- `x86_rtx4090_episodes_csv`: `outputs/router_phase10_system_v1/platforms/x86_rtx4090/episodes.csv`
- `x86_rtx4090_cycles_csv`: `outputs/router_phase10_system_v1/platforms/x86_rtx4090/cycles.csv`
- `jetson_orin_episodes_csv`: `outputs/router_phase10_system_v1/platforms/jetson_orin/episodes.csv`
- `jetson_orin_cycles_csv`: `outputs/router_phase10_system_v1/platforms/jetson_orin/cycles.csv`