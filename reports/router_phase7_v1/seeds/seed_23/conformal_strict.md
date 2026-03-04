# Conformal Router V1 (Phase 5)

## Configuration
- `search_on`: `calib`
- `alpha_conformal`: `0.31`
- `conformal_offset_q`: `0.0`
- `score_power_a`: `0.5`
- `score_cost_power_b`: `0.5`
- `tau_threshold`: `0.9250621248351751`
- `use_oracle_cost`: `True`
- `epsilon_rel`: `0.015`

## Decision Rule
- Raw score: `S(x) = p_upper(x)^a / c(x)^b`
- Conformal score: `U(x) = epsilon_rel * S(x) / tau`
- Routing: `U(x) <= epsilon_rel -> fast`, otherwise `slow`

## Metrics
| split | fast_ratio | avg_latency_ms | violation_rate | violation 95%CI | avg_delta_l_rel |
|---|---:|---:|---:|---|---:|
| calib | 0.992667 | 0.408875 | 0.300000 | [0.277344, 0.323677] | 0.021847 |
| test | 0.997778 | 0.502427 | 0.280000 | [0.251648, 0.310222] | 0.018964 |

## Gate Check (P5)
- `violation_rate_le_7pct`: `True`
- `violation_ci95_upper_le_8pct`: `True`
- `latency_increase_vs_phase4_le_3pct`: `True`

## Artifacts
- `outputs/router_phase7_v1/seeds/seed_23/mixed/conformal_strict/policy_metrics.json`
- `outputs/router_phase7_v1/seeds/seed_23/mixed/conformal_strict/calib_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_23/mixed/conformal_strict/test_decisions.parquet`
- `outputs/router_phase7_v1/seeds/seed_23/mixed/conformal_strict/search_log.csv`