# Router Phase10 System V1 Report

## Summary
- Runtime: `0.000 h`
- Platforms: `x86_rtx4090, jetson_orin`
- Episodes per platform target: `30`

## Gate Check
- `platform_count_ge_2`: `True`
- `episodes_per_platform_ge_200`: `False`
- `success_ge_97pct_each`: `False`
- `catastrophic_collision_zero_each`: `False`
- `p95_latency_le_50ms_each`: `True`
- `p99_latency_le_80ms_each`: `True`

## Platform Metrics
| platform | episodes | success | catastrophic collisions | P95 latency (ms) | P99 latency (ms) | fast call ratio |
|---|---:|---:|---:|---:|---:|---:|
| x86_rtx4090 | 30 | 0.9333 | 2 | 2.941 | 4.383 | 0.8293 |
| jetson_orin | 30 | 1.0000 | 0 | 5.642 | 6.478 | 0.9231 |

## Artifacts
- `selected_cases_csv`: `outputs/router_phase10_system_debug/selected_cases.csv`
- `report_md`: `reports/router_phase10_system_debug.md`
- `x86_rtx4090_episodes_csv`: `outputs/router_phase10_system_debug/platforms/x86_rtx4090/episodes.csv`
- `x86_rtx4090_cycles_csv`: `outputs/router_phase10_system_debug/platforms/x86_rtx4090/cycles.csv`
- `jetson_orin_episodes_csv`: `outputs/router_phase10_system_debug/platforms/jetson_orin/episodes.csv`
- `jetson_orin_cycles_csv`: `outputs/router_phase10_system_debug/platforms/jetson_orin/cycles.csv`