# Router Phase10 System V1 Report

## Summary
- Runtime: `0.006 h`
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
| x86_rtx4090 | 30 | 0.6333 | 5 | 19.042 | 20.744 | 0.5780 |
| jetson_orin | 30 | 0.7667 | 3 | 8.362 | 25.015 | 0.9333 |

## Artifacts
- `selected_cases_csv`: `outputs/router_phase10_system_debug2/selected_cases.csv`
- `report_md`: `reports/router_phase10_system_debug2.md`
- `x86_rtx4090_episodes_csv`: `outputs/router_phase10_system_debug2/platforms/x86_rtx4090/episodes.csv`
- `x86_rtx4090_cycles_csv`: `outputs/router_phase10_system_debug2/platforms/x86_rtx4090/cycles.csv`
- `jetson_orin_episodes_csv`: `outputs/router_phase10_system_debug2/platforms/jetson_orin/episodes.csv`
- `jetson_orin_cycles_csv`: `outputs/router_phase10_system_debug2/platforms/jetson_orin/cycles.csv`