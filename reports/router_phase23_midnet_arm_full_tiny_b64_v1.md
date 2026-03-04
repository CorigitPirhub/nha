# Phase23 Mid-Net Arm Pilot (v1)

This pilot evaluates a smaller neural planner arm (`mid`) against the frozen Phase-9 fast/slow counterfactual tables.

## Setup
- Date: `2026-03-03`
- Mid checkpoint: `outputs/router_phase23_midnet_tinyunet_b64_ctx_v1/checkpoints/heuristic_net.pt`
- Cases: `3218` (pilot subset)
- RNG seed: `7`
- Device: `cuda`
- `epsilon_rel`: `0.015`
- `alpha`: `0.05`
- `T_ref` (median slow calib): `2.330295 ms`
- `beta` (risk-aware, from calib): `25.833333`

## Aggregate Points (test subset)
| arm             |   avg_latency_ms |   avg_delta_l_rel |   avg_delta_l_rel_pos |   violation_rate |   J_mean |
|:----------------|-----------------:|------------------:|----------------------:|-----------------:|---------:|
| always_fast     |          0.49025 |         0.0220141 |            0.0334389  |        0.288689  | 1.07422  |
| always_midnet   |          1.55218 |        -0.0900469 |            0.00526276 |        0.0379117 | 0.802041 |
| always_slow_ref |          2.68644 |         0         |            0          |        0         | 1.15283  |

## Mid Arm Diagnostics
- `mid_success_rate`: `1.0`
- `mid_infer_ms_mean`: `0.9096824040423993`
- `mid_search_ms_mean`: `0.6424961619587317`
- `mid_path_len_ratio_vs_fast_mean`: `1.0000010559548902`
- `mid_path_len_ratio_vs_fast_p99`: `1.0000000000000002`
- `mid_violation_ci95`: `[0.031845098474884745, 0.04508030644910946]`

## Oracle Complementarity (lower is better)
| oracle_set      |   J_oracle_mean |   share_fast |   share_mid |   share_slow |
|:----------------|----------------:|-------------:|------------:|-------------:|
| {fast,slow}     |        0.457396 |   nan        |  nan        |  nan         |
| {fast,mid,slow} |        0.357235 |     0.722188 |    0.251709 |    0.0261032 |

## Artifacts
- `pilot_midnet_counterfactual_test_parquet`: `outputs/router_phase23_midnet_arm_full_tiny_b64_v1/pilot_midnet_counterfactual_test.parquet`