# Router Risk V1 (Phase 4)

## Core Setup
- `selected_lambda`: `27.500000`
- `T_ref` (median slow latency on calib): `7.492581 ms`
- `beta`: `25.833333` (calibrated by median-scale match)
- `q_pos_median` (calib): `0.038710`

## Objective
- `J = mean(T / T_ref + beta * max(delta_l_rel, 0))`
- `delta_l_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`

## Metrics
| split | avg_delta_l_rel | avg_latency_ms | J | J improve vs current_v2 | J improve vs default_router | easy fast | medium fast | hard fast |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| calib | -0.002659 | 2.347306 | 0.527794 | 46.422% | 61.318% | 0.8539 | 0.7775 | 0.8181 |
| test | 0.008907 | 2.559096 | 0.833646 | 13.845% | 38.891% | 0.8376 | 0.8138 | 0.8347 |

## Gate Check (P4)
- `avg_delta_l_rel_le_1_5pct`: `True`
- `J_improve_ge_5pct`: `True`
- `stratified_fast_ratio_target`: `True`
- `exp3_exp4_abs_dE_drift_le_0_5pct`: `True`

## Artifacts
- `outputs/router_phase9_bench_v12_strict_recovery_prefixreuse/common/risk/policy_metrics.json`
- `outputs/router_phase9_bench_v12_strict_recovery_prefixreuse/common/risk/calib_sweep.csv`
- `outputs/router_phase9_bench_v12_strict_recovery_prefixreuse/common/risk/calib_decisions.parquet`
- `outputs/router_phase9_bench_v12_strict_recovery_prefixreuse/common/risk/test_decisions.parquet`