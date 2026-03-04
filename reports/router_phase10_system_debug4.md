# Router Phase10 System V1 Report

## Summary
- Runtime: `0.000 h`
- Platforms: `x86_rtx4090, jetson_orin`
- Episodes per platform target: `30`

## Gate Check
- `platform_count_ge_2`: `True`
- `episodes_per_platform_ge_200`: `False`
- `success_ge_97pct_each`: `True`
- `catastrophic_collision_zero_each`: `True`
- `p95_latency_le_50ms_each`: `True`
- `p99_latency_le_80ms_each`: `True`

## Platform Metrics
| platform | episodes | success | catastrophic collisions | P95 latency (ms) | P99 latency (ms) | fast call ratio |
|---|---:|---:|---:|---:|---:|---:|
| x86_rtx4090 | 30 | 1.0000 | 0 | 2.938 | 3.422 | 0.9000 |
| jetson_orin | 30 | 1.0000 | 0 | 5.661 | 6.614 | 0.8710 |

## Artifacts
- `selected_cases_csv`: `outputs/router_phase10_system_debug4/selected_cases.csv`
- `report_md`: `reports/router_phase10_system_debug4.md`
- `x86_rtx4090_episodes_csv`: `outputs/router_phase10_system_debug4/platforms/x86_rtx4090/episodes.csv`
- `x86_rtx4090_cycles_csv`: `outputs/router_phase10_system_debug4/platforms/x86_rtx4090/cycles.csv`
- `jetson_orin_episodes_csv`: `outputs/router_phase10_system_debug4/platforms/jetson_orin/episodes.csv`
- `jetson_orin_cycles_csv`: `outputs/router_phase10_system_debug4/platforms/jetson_orin/cycles.csv`