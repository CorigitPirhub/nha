# Phase23 Mid-Net Arm Pilot (v1)

This pilot evaluates a smaller neural planner arm (`mid`) against the frozen Phase-9 fast/slow counterfactual tables.

## Setup
- Date: `2026-03-03`
- Mid checkpoint: `outputs/router_phase23_midnet_tinyunet_b32_ctx_v1/checkpoints/heuristic_net.pt`
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
| always_fast     |         0.474854 |        0.0242409  |             0.035608  |           0.3075 |  1.12365 |
| always_midnet   |         1.74114  |        0.00571975 |             0.0352424 |           0.38   |  1.6576  |
| always_slow_ref |         2.61762  |        0          |             0         |           0      |  1.1233  |

## Mid Arm Diagnostics
- `mid_success_rate`: `1.0`
- `mid_infer_ms_mean`: `1.0938458782038651`
- `mid_search_ms_mean`: `0.6472969538299367`
- `mid_path_len_ratio_vs_fast_mean`: `1.0`
- `mid_path_len_ratio_vs_fast_p99`: `1.0000000000000002`
- `mid_violation_ci95`: `[0.3337874943779953, 0.4284954562622359]`

## Oracle Complementarity (lower is better)
| oracle_set      |   J_oracle_mean |   share_fast |   share_mid |   share_slow |
|:----------------|----------------:|-------------:|------------:|-------------:|
| {fast,slow}     |        0.469609 |     nan      |     nan     |     nan      |
| {fast,mid,slow} |        0.436793 |       0.7375 |       0.095 |       0.1675 |

## Artifacts
- `pilot_midnet_counterfactual_test_parquet`: `outputs/router_phase23_midnet_arm_pilot_v1/pilot_midnet_counterfactual_test.parquet`