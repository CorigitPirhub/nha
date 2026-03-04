# Phase23 Mid-Net Arm Pilot (v1)

This pilot evaluates a smaller neural planner arm (`mid`) against the frozen Phase-9 fast/slow counterfactual tables.

## Setup
- Date: `2026-03-03`
- Mid checkpoint: `outputs/router_phase23_midnet_tinyunet_b64_ctx_v1/checkpoints/heuristic_net.pt`
- Cases: `400` (pilot subset)
- RNG seed: `7`
- Device: `cuda`
- `epsilon_rel`: `0.015`
- `alpha`: `0.05`
- `T_ref` (median slow calib): `2.330295 ms`
- `beta` (risk-aware, from calib): `25.833333`

## Aggregate Points (test subset)
| arm             |   avg_latency_ms |   avg_delta_l_rel |   avg_delta_l_rel_pos |   violation_rate |   J_mean |
|:----------------|-----------------:|------------------:|----------------------:|-----------------:|---------:|
| always_fast     |         0.474854 |         0.0242409 |            0.035608   |           0.3075 | 1.12365  |
| always_midnet   |         1.73946  |        -0.090111  |            0.00693827 |           0.0375 | 0.925693 |
| always_slow_ref |         2.61762  |         0         |            0          |           0      | 1.1233   |

## Mid Arm Diagnostics
- `mid_success_rate`: `1.0`
- `mid_infer_ms_mean`: `1.1277248803526163`
- `mid_search_ms_mean`: `0.6117335986346006`
- `mid_path_len_ratio_vs_fast_mean`: `1.0`
- `mid_path_len_ratio_vs_fast_p99`: `1.0000000000000002`
- `mid_violation_ci95`: `[0.022855029814710864, 0.06094384244451338]`

## Oracle Complementarity (lower is better)
| oracle_set      |   J_oracle_mean |   share_fast |   share_mid |   share_slow |
|:----------------|----------------:|-------------:|------------:|-------------:|
| {fast,slow}     |        0.469609 |     nan      |    nan      |      nan     |
| {fast,mid,slow} |        0.358938 |       0.7025 |      0.2725 |        0.025 |

## Artifacts
- `pilot_midnet_counterfactual_test_parquet`: `outputs/router_phase23_midnet_arm_pilot_tiny_b64_v1/pilot_midnet_counterfactual_test.parquet`