# Router Risk V1 (Phase 4)

## Core Setup
- `selected_lambda`: `26.000000`
- `T_ref` (median slow latency on calib): `2.297895 ms`
- `beta`: `29.600000` (calibrated by median-scale match)
- `q_pos_median` (calib): `0.033784`

## Objective
- `J = mean(T / T_ref + beta * max(delta_l_rel, 0))`
- `delta_l_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`

## Metrics
| split | avg_delta_l_rel | avg_latency_ms | J | J improve vs current_v2 | J improve vs default_router | easy fast | medium fast | hard fast |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| calib | -0.003445 | 1.131385 | 0.646050 | 45.411% | 49.463% | 0.8500 | 0.6860 | 0.3500 |
| test | 0.002145 | 1.209825 | 0.868486 | 24.751% | 33.491% | 0.8500 | 0.7500 | 0.3500 |

## Gate Check (P4)
- `avg_delta_l_rel_le_1_5pct`: `True`
- `J_improve_ge_5pct`: `True`
- `stratified_fast_ratio_target`: `True`
- `exp3_exp4_abs_dE_drift_le_0_5pct`: `True`

## Artifacts
- `outputs/router_phase7_v1/seeds/seed_19/mixed/risk/policy_metrics.json`
- `outputs/router_phase7_v1/seeds/seed_19/mixed/risk/calib_sweep.csv`
- `outputs/router_phase7_v1/seeds/seed_19/mixed/risk/calib_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_19/mixed/risk/test_decisions.parquet`