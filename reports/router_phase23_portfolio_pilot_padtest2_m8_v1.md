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
- `mid_crop_m8_p32 (corridor crop + pad-to-multiple + A* w=1)`
- `mid_crop_m8 (corridor crop (raw) + A* w=1)`
- `mid_wastar_w1.50 (Weighted A* with euclidean heuristic, no inference)`

## Aggregate Points (test subset)
| arm              |   avg_latency_ms |   avg_delta_l_rel |   avg_delta_l_rel_pos |   violation_rate |    J_mean |
|:-----------------|-----------------:|------------------:|----------------------:|-----------------:|----------:|
| always_fast      |         0.390285 |       0.0333899   |           0.0489996   |        0.383333  | 1.43331   |
| mid_crop_m8_p32  |         3.80928  |      -0.000535798 |           0.000573444 |        0.025     | 1.64949   |
| mid_crop_m8      |         7.289    |      -0.00856354  |           0.00468129  |        0.0916667 | 3.24886   |
| mid_wastar_w1.50 |         0.172305 |      -0.567144    |           0           |        0         | 0.0739412 |
| always_slow_ref  |         2.50566  |       0           |           0           |        0         | 1.07526   |

## Dominance Summary
- `mid_crop_m8_p32` dominates `mid_crop_m8`
- `mid_wastar_w1.50` dominates `always_fast`
- `mid_wastar_w1.50` dominates `mid_crop_m8_p32`
- `mid_wastar_w1.50` dominates `mid_crop_m8`
- `mid_wastar_w1.50` dominates `always_slow_ref`
- `always_slow_ref` dominates `mid_crop_m8_p32`
- `always_slow_ref` dominates `mid_crop_m8`

## Oracle Complementarity (lower is better)
| oracle_set                                          |   J_oracle_mean |   share_fast |   share_slow |   share_mid_crop_padded |   share_mid_crop_raw |   share_mid_wastar |
|:----------------------------------------------------|----------------:|-------------:|-------------:|------------------------:|---------------------:|-------------------:|
| {fast,slow}                                         |       0.485885  |   0.716667   |     0.283333 |            nan          |              nan     |         nan        |
| {fast,mid_crop_padded,slow}                         |       0.485853  |   0.716667   |     0.275    |              0.00833333 |              nan     |         nan        |
| {fast,mid_crop_raw,slow}                            |       0.485503  |   0.716667   |     0.258333 |            nan          |                0.025 |         nan        |
| {fast,mid_wastar,slow}                              |       0.0736343 |   0.00833333 |     0        |            nan          |              nan     |           0.991667 |
| {fast,mid_crop_padded,mid_crop_raw,mid_wastar,slow} |       0.0736343 |   0.00833333 |     0        |              0          |                0     |           0.991667 |

## Artifacts
- `pilot_mid_counterfactual_test_parquet`: `outputs/router_phase23_portfolio_pilot_padtest2_m8_v1/pilot_mid_counterfactual_test.parquet`