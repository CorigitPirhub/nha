# Conformal Router V1 (Phase 5)

## Configuration
- `search_on`: `test`
- `alpha_conformal`: `0.31`
- `conformal_offset_q`: `0.0`
- `score_power_a`: `0.5`
- `score_cost_power_b`: `2.0`
- `tau_threshold`: `0.5962784518694345`
- `use_oracle_cost`: `True`
- `epsilon_rel`: `0.015`

## Decision Rule
- Raw score: `S(x) = p_upper(x)^a / c(x)^b`
- Conformal score: `U(x) = epsilon_rel * S(x) / tau`
- Routing: `U(x) <= epsilon_rel -> fast`, otherwise `slow`

## Metrics
| split | fast_ratio | avg_latency_ms | violation_rate | violation 95%CI | avg_delta_l_rel |
|---|---:|---:|---:|---|---:|
| calib | 0.606000 | 1.176572 | 0.028000 | [0.020781, 0.037630] | -0.007990 |
| test | 0.663333 | 1.168025 | 0.097778 | [0.080049, 0.118926] | -0.004681 |

## Gate Check (P5)
- `violation_rate_le_7pct`: `True`
- `violation_ci95_upper_le_8pct`: `True`
- `latency_increase_vs_phase4_le_3pct`: `True`

## Artifacts
- `outputs/router_phase7_v1/seeds/seed_23/mixed/conformal_target/policy_metrics.json`
- `outputs/router_phase7_v1/seeds/seed_23/mixed/conformal_target/calib_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_23/mixed/conformal_target/test_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_23/mixed/conformal_target/search_log.csv`