# Router Risk V1 (Phase 4)

## Core Setup
- `selected_lambda`: `16.500000`
- `T_ref` (median slow latency on calib): `512.879160 ms`
- `beta`: `25.833333` (calibrated by median-scale match)
- `q_pos_median` (calib): `0.038710`

## Objective
- `J = mean(T / T_ref + beta * max(delta_l_rel, 0))`
- `delta_l_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`

## Metrics
| split | avg_delta_l_rel | avg_latency_ms | J | J improve vs current_v2 | J improve vs default_router | easy fast | medium fast | hard fast |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| calib | -0.004072 | 46.927254 | 0.204485 | 77.027% | 79.876% | 0.8950 | 0.5809 | 0.4394 |
| test | 0.002709 | 18.470933 | 0.318448 | 63.225% | 62.209% | 0.8612 | 0.6204 | 0.4417 |

## Gate Check (P4)
- `avg_delta_l_rel_le_1_5pct`: `True`
- `J_improve_ge_5pct`: `True`
- `stratified_fast_ratio_target`: `True`
- `exp3_exp4_abs_dE_drift_le_0_5pct`: `True`

## Artifacts
- `outputs/router_phase9_bench_v18_strict_recovery_partition_crc_jaware_fixed/common/risk/policy_metrics.json`
- `outputs/router_phase9_bench_v18_strict_recovery_partition_crc_jaware_fixed/common/risk/calib_sweep.csv`
- `outputs/router_phase9_bench_v18_strict_recovery_partition_crc_jaware_fixed/common/risk/calib_decisions.parquet`
- `outputs/router_phase9_bench_v18_strict_recovery_partition_crc_jaware_fixed/common/risk/test_decisions.parquet`