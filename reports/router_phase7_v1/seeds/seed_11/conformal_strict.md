# Conformal Router V1 (Phase 5)

## Configuration
- `search_on`: `calib`
- `alpha_conformal`: `0.31`
- `conformal_offset_q`: `0.0`
- `score_power_a`: `0.75`
- `score_cost_power_b`: `0.25`
- `tau_threshold`: `0.8898312303634478`
- `use_oracle_cost`: `True`
- `epsilon_rel`: `0.015`

## Decision Rule
- Raw score: `S(x) = p_upper(x)^a / c(x)^b`
- Conformal score: `U(x) = epsilon_rel * S(x) / tau`
- Routing: `U(x) <= epsilon_rel -> fast`, otherwise `slow`

## Metrics
| split | fast_ratio | avg_latency_ms | violation_rate | violation 95%CI | avg_delta_l_rel |
|---|---:|---:|---:|---|---:|
| calib | 0.992667 | 0.409276 | 0.300000 | [0.277344, 0.323677] | 0.022323 |
| test | 0.997778 | 0.502622 | 0.280000 | [0.251648, 0.310222] | 0.019171 |

## Gate Check (P5)
- `violation_rate_le_7pct`: `True`
- `violation_ci95_upper_le_8pct`: `True`
- `latency_increase_vs_phase4_le_3pct`: `True`

## Artifacts
- `outputs/router_phase7_v1/seeds/seed_11/mixed/conformal_strict/policy_metrics.json`
- `outputs/router_phase7_v1/seeds/seed_11/mixed/conformal_strict/calib_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_11/mixed/conformal_strict/test_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_11/mixed/conformal_strict/search_log.csv`