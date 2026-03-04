# Conformal Router V1 (Phase 5)

## Configuration
- `search_on`: `calib`
- `alpha_conformal`: `0.31`
- `conformal_offset_q`: `0.0`
- `score_power_a`: `0.5`
- `score_cost_power_b`: `0.25`
- `tau_threshold`: `0.9317049287331673`
- `use_oracle_cost`: `True`
- `epsilon_rel`: `0.015`

## Decision Rule
- Raw score: `S(x) = p_upper(x)^a / c(x)^b`
- Conformal score: `U(x) = epsilon_rel * S(x) / tau`
- Routing: `U(x) <= epsilon_rel -> fast`, otherwise `slow`

## Metrics
| split | fast_ratio | avg_latency_ms | violation_rate | violation 95%CI | avg_delta_l_rel |
|---|---:|---:|---:|---|---:|
| calib | 0.992667 | 0.409066 | 0.300000 | [0.277344, 0.323677] | 0.022041 |
| test | 0.998889 | 0.500310 | 0.282222 | [0.253791, 0.312505] | 0.019355 |

## Gate Check (P5)
- `violation_rate_le_7pct`: `True`
- `violation_ci95_upper_le_8pct`: `True`
- `latency_increase_vs_phase4_le_3pct`: `True`

## Artifacts
- `outputs/router_phase7_v1/seeds/seed_7/mixed/conformal_strict/policy_metrics.json`
- `outputs/router_phase7_v1/seeds/seed_7/mixed/conformal_strict/calib_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_7/mixed/conformal_strict/test_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_7/mixed/conformal_strict/search_log.csv`