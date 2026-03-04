# Router Probe V1 (Phase 6)

## Selected Config
- `gain_power`: `1.0`
- `w_hard`: `0.0`
- `w_bottleneck`: `0.0`
- `w_deadend`: `0.0`
- `w_stall`: `0.0`
- `tau`: `3.2677971287940135`
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
| calib | 1.881358 | 0.282629 | 0.000% | -0.006004 | 0.000% | 0.000000 |
| test | 1.913707 | 0.403937 | 15.131% | -0.003154 | 511.555% | 0.010675 |

## Gate Check (P6)
- `oracle_gap_improve_ge_15pct`: `True`
- `hard_delta_l_rel_improve_ge_20pct`: `True`
- `latency_extra_vs_p5_le_1ms`: `True`

## Artifacts
- `outputs/router_phase7_v1/seeds/seed_31/mixed/probe_target/policy_metrics.json`
- `outputs/router_phase7_v1/seeds/seed_31/mixed/probe_target/search_log.csv`
- `outputs/router_phase7_v1/seeds/seed_31/mixed/probe_target/calib_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_31/mixed/probe_target/test_decisions.parquet`