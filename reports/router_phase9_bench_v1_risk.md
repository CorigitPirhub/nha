# Router Risk V1 (Phase 4)

## Core Setup
- `selected_lambda`: `19.000000`
- `T_ref` (median slow latency on calib): `2.330295 ms`
- `beta`: `25.833333` (calibrated by median-scale match)
- `q_pos_median` (calib): `0.038710`

## Objective
- `J = mean(T / T_ref + beta * max(delta_l_rel, 0))`
- `delta_l_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`

## Metrics
| split | avg_delta_l_rel | avg_latency_ms | J | J improve vs current_v2 | J improve vs default_router | easy fast | medium fast | hard fast |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| calib | -0.004915 | 0.879689 | 0.531598 | 50.148% | 56.471% | 0.7945 | 0.7607 | 0.7673 |
| test | 0.006015 | 0.948808 | 0.817507 | 23.898% | 32.541% | 0.7741 | 0.7781 | 0.7596 |

## Gate Check (P4)
- `avg_delta_l_rel_le_1_5pct`: `True`
- `J_improve_ge_5pct`: `True`
- `stratified_fast_ratio_target`: `True`
- `exp3_exp4_abs_dE_drift_le_0_5pct`: `True`

## Artifacts
- `outputs/router_phase9_bench_v1/common/risk/policy_metrics.json`
- `outputs/router_phase9_bench_v1/common/risk/calib_sweep.csv`
- `outputs/router_phase9_bench_v1/common/risk/calib_decisions.parquet`
- `outputs/router_phase9_bench_v1/common/risk/test_decisions.parquet`