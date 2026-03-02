# Router Probe V1 (Phase 6)

## Selected Config
- `gain_power`: `1.0`
- `w_hard`: `0.0`
- `w_bottleneck`: `0.0`
- `w_deadend`: `0.0`
- `w_stall`: `0.0`
- `tau`: `3.389761258470248`
- `k_slow_extra_search`: `5`
- `score_formula`: `S=gain_hat^gain_power*(1+w_hard*I_hard+w_bottleneck*B+w_deadend*D+w_stall*Stall)`
- `route_rule`: `start from phase5 route; for phase5-fast cases, if S>=tau then route=slow`

## Decision Rule
- Stage-1 (probe): bounded fast A* probe extracts online signals.
- Stage-2 (commit): score `S = gain_hat^a * (1 + w_hard*I_hard + w_bottle*B + w_dead*D + w_stall*Stall)`.
- Start from Phase-5 route, then flip top-risk fast cases to slow under latency budget.

## Metrics
| split | total_latency_ms | oracle_gap | OG improve vs P5 | hard ΔL_rel | hard ΔL_rel improve vs P5 | latency extra vs P5 (ms) |
|---|---:|---:|---:|---:|---:|---:|
| calib | 10.802945 | 0.834093 | 6.909% | -0.003601 | 49.981% | 0.078048 |
| test | 10.751529 | 0.825819 | 16.129% | -0.000592 | 112.345% | 0.263958 |

## Gate Check (P6)
- `oracle_gap_improve_ge_15pct`: `True`
- `hard_delta_l_rel_improve_ge_20pct`: `True`
- `latency_extra_vs_p5_le_1ms`: `True`

## Artifacts
- `outputs/router_probe_v1/policy_metrics.json`
- `outputs/router_probe_v1/search_log.csv`
- `outputs/router_probe_v1/calib_decisions.parquet`
- `outputs/router_probe_v1/test_decisions.parquet`