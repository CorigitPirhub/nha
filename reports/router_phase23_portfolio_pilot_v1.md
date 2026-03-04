# Phase23 Portfolio Mid-Arm Pilot (v1)

This pilot prototypes 2–3 candidate `mid` arms and checks if any yields a non-dominated tradeoff under the frozen protocol semantics.

## Setup
- Date: `2026-03-03`
- Cases: `120` (pilot subset)
- RNG seed: `7`
- `epsilon_rel`: `0.015`
- `alpha`: `0.05`
- `T_ref` (median slow calib): `2.330295 ms`
- `beta` (risk-aware, from calib): `25.833333`

## Candidate Mid Arms
- `mid_lowres_ds2 (downsampled inference + A* w=1)`
- `mid_crop_m48 (corridor crop inference + euclidean outside + A* w=1)`
- `mid_wastar_w1.50 (Weighted A* with euclidean heuristic, no inference)`

## Aggregate Points (test subset)
| arm              |   avg_latency_ms |   avg_delta_l_rel |   avg_delta_l_rel_pos |   violation_rate |      J_mean |
|:-----------------|-----------------:|------------------:|----------------------:|-----------------:|------------:|
| always_fast      |         0.390285 |       0.0333899   |             0.0489996 |         0.383333 |   1.43331   |
| mid_lowres_ds2   |         6.69629  |       9.37556     |             9.39011   |         0.941667 | 245.451     |
| mid_crop_m48     |         3.16315  |      -3.51617e-05 |             0         |         0        |   1.3574    |
| mid_wastar_w1.50 |         0.173085 |      -0.567144    |             0         |         0        |   0.0742759 |
| always_slow_ref  |         2.50566  |       0           |             0         |         0        |   1.07526   |

## Dominance Summary
- `always_fast` dominates `mid_lowres_ds2`
- `mid_crop_m48` dominates `mid_lowres_ds2`
- `mid_wastar_w1.50` dominates `always_fast`
- `mid_wastar_w1.50` dominates `mid_lowres_ds2`
- `mid_wastar_w1.50` dominates `mid_crop_m48`
- `mid_wastar_w1.50` dominates `always_slow_ref`
- `always_slow_ref` dominates `mid_lowres_ds2`
- `always_slow_ref` dominates `mid_crop_m48`

## Oracle Complementarity (lower is better)
| oracle_set                                 |   J_oracle_mean |   share_fast |   share_slow |   share_mid_lowres |   share_mid_crop |   share_mid_wastar |
|:-------------------------------------------|----------------:|-------------:|-------------:|-------------------:|-----------------:|-------------------:|
| {fast,slow}                                |       0.485885  |   0.716667   |     0.283333 |                nan |          nan     |         nan        |
| {fast,mid_lowres,slow}                     |       0.485885  |   0.716667   |     0.283333 |                  0 |          nan     |         nan        |
| {fast,mid_crop,slow}                       |       0.483047  |   0.708333   |     0.116667 |                nan |            0.175 |         nan        |
| {fast,mid_wastar,slow}                     |       0.0738247 |   0.00833333 |     0        |                nan |          nan     |           0.991667 |
| {fast,mid_lowres,mid_crop,mid_wastar,slow} |       0.0738247 |   0.00833333 |     0        |                  0 |            0     |           0.991667 |

## Artifacts
- `pilot_mid_counterfactual_test_parquet`: `outputs/router_phase23_portfolio_pilot_v1/pilot_mid_counterfactual_test.parquet`