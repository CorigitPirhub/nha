# Router Phase14 Stress V1 Report

## Summary
- Runtime: `0.009 h`
- Stress types: `10`
- Cases per type (min): `240`
- Worst-10% success: `96.667%`
- Recovery success after trigger: `97.945%`

## Gate Check
- `stress_type_count_ge_10`: `True`
- `cases_per_type_ge_100`: `True`
- `worst10_success_ge_92pct`: `True`
- `recovery_success_ge_95pct_when_triggered`: `True`
- `catastrophic_collision_zero`: `True`

## Per-Stress Metrics
| stress_type | cases | success | catastrophic collisions | triggers | recovered | recovery success |
|---|---:|---:|---:|---:|---:|---:|
| comm_delay_spike | 240 | 1.0000 | 0 | 113 | 113 | 1.0000 |
| control_delay_spike | 240 | 1.0000 | 0 | 110 | 110 | 1.0000 |
| dynamic_corridor_intrusion | 240 | 1.0000 | 0 | 139 | 139 | 1.0000 |
| dynamic_dense_flow | 240 | 1.0000 | 0 | 136 | 136 | 1.0000 |
| heavy_mixed_extreme | 240 | 0.9667 | 0 | 240 | 232 | 0.9667 |
| latency_jitter_spike | 240 | 1.0000 | 0 | 92 | 92 | 1.0000 |
| map_shift_combo | 240 | 0.9667 | 0 | 124 | 116 | 0.9355 |
| sensor_dropout_combo | 240 | 0.9917 | 0 | 7 | 5 | 0.7143 |
| sensor_fn_spike | 240 | 0.9917 | 0 | 7 | 5 | 0.7143 |
| sensor_fp_spike | 240 | 1.0000 | 0 | 5 | 5 | 1.0000 |

## Artifacts
- `selected_cases_csv`: `outputs/router_phase14_stress_v1/selected_cases.csv`
- `stress_profile_summary_csv`: `outputs/router_phase14_stress_v1/stress_profile_summary.csv`
- `stress_episodes_csv`: `outputs/router_phase14_stress_v1/stress_episodes.csv`
- `stress_cycles_csv`: `outputs/router_phase14_stress_v1/stress_cycles.csv`
- `stress_platform_metrics_csv`: `outputs/router_phase14_stress_v1/stress_platform_metrics.csv`
- `report_md`: `reports/router_phase14_stress_v1.md`