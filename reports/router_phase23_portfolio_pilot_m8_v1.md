# Phase23 Portfolio Mid-Arm Pilot (v1)

This pilot prototypes 2–3 candidate `mid` arms and checks if any yields a non-dominated tradeoff under the frozen protocol semantics.

## Setup
- Date: `2026-03-03`
- Cases: `300` (pilot subset)
- RNG seed: `7`
- `epsilon_rel`: `0.015`
- `alpha`: `0.05`
- `T_ref` (median slow calib): `2.330295 ms`
- `beta` (risk-aware, from calib): `25.833333`

## Candidate Mid Arms
- `mid_lowres_ds2 (downsampled inference + A* w=1)`
- `mid_crop_m8 (corridor crop inference + euclidean outside + A* w=1)`
- `mid_wastar_w1.50 (Weighted A* with euclidean heuristic, no inference)`

## Aggregate Points (test subset)
| arm              |   avg_latency_ms |   avg_delta_l_rel |   avg_delta_l_rel_pos |   violation_rate |     J_mean |
|:-----------------|-----------------:|------------------:|----------------------:|-----------------:|-----------:|
| always_fast      |         0.491434 |        0.0152183  |            0.0290168  |       0.27       |   0.96049  |
| mid_lowres_ds2   |         6.92162  |       11.5284     |           11.5423     |       0.88       | 301.146    |
| mid_crop_m8      |         6.49361  |       -0.00472707 |            0.00552847 |       0.0666667  |   2.92942  |
| mid_wastar_w1.50 |         0.216954 |       -0.548448   |            0.00149399 |       0.00666667 |   0.131696 |
| always_slow_ref  |         2.6423   |        0          |            0          |       0          |   1.13389  |

## Dominance Summary
- `always_fast` dominates `mid_lowres_ds2`
- `mid_crop_m8` dominates `mid_lowres_ds2`
- `mid_wastar_w1.50` dominates `always_fast`
- `mid_wastar_w1.50` dominates `mid_lowres_ds2`
- `mid_wastar_w1.50` dominates `mid_crop_m8`
- `always_slow_ref` dominates `mid_lowres_ds2`
- `always_slow_ref` dominates `mid_crop_m8`

## Oracle Complementarity (lower is better)
| oracle_set                                 |   J_oracle_mean |   share_fast |   share_slow |   share_mid_lowres |   share_mid_crop |   share_mid_wastar |
|:-------------------------------------------|----------------:|-------------:|-------------:|-------------------:|-----------------:|-------------------:|
| {fast,slow}                                |       0.435616  |   0.826667   |     0.173333 |                nan |      nan         |         nan        |
| {fast,mid_lowres,slow}                     |       0.435616  |   0.826667   |     0.173333 |                  0 |      nan         |         nan        |
| {fast,mid_crop,slow}                       |       0.435525  |   0.826667   |     0.156667 |                nan |        0.0166667 |         nan        |
| {fast,mid_wastar,slow}                     |       0.0953148 |   0.00666667 |     0        |                nan |      nan         |           0.993333 |
| {fast,mid_lowres,mid_crop,mid_wastar,slow} |       0.0953148 |   0.00666667 |     0        |                  0 |        0         |           0.993333 |

## Artifacts
- `pilot_mid_counterfactual_test_parquet`: `outputs/router_phase23_portfolio_pilot_m8_v1/pilot_mid_counterfactual_test.parquet`