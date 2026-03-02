# Router Risk V1 (Phase 4)

## Core Setup
- `selected_lambda`: `15.250000`
- `T_ref` (median slow latency on calib): `19.302403 ms`
- `beta`: `29.549915` (calibrated by median-scale match)
- `q_pos_median` (calib): `0.033841`

## Objective
- `J = mean(T / T_ref + beta * max(delta_l_rel, 0))`
- `delta_l_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`

## Metrics
| split | avg_delta_l_rel | avg_latency_ms | J | J improve vs current_v2 | J improve vs default_router | easy fast | medium fast | hard fast |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| calib | -0.002278 | 5.767727 | 0.492768 | 52.101% | 57.478% | 0.8500 | 0.7500 | 0.3500 |
| test | 0.001892 | 10.526428 | 0.882895 | 7.798% | 26.746% | 0.8500 | 0.7500 | 0.3500 |

## Gate Check (P4)
- `avg_delta_l_rel_le_1_5pct`: `True`
- `J_improve_ge_5pct`: `True`
- `stratified_fast_ratio_target`: `True`
- `exp3_exp4_abs_dE_drift_le_0_5pct`: `True`

## Artifacts
- `outputs/router_risk_v1/policy_metrics.json`
- `outputs/router_risk_v1/calib_sweep.csv`
- `outputs/router_risk_v1/calib_decisions.parquet`
- `outputs/router_risk_v1/test_decisions.parquet`