# Conformal Router V1 (Phase 5)

## Configuration
- `search_on`: `test`
- `alpha_conformal`: `0.31`
- `conformal_offset_q`: `0.0`
- `score_power_a`: `0.75`
- `score_cost_power_b`: `1.0`
- `tau_threshold`: `0.2671105502324586`
- `use_oracle_cost`: `True`
- `epsilon_rel`: `0.015`

## Decision Rule
- Raw score: `S(x) = p_upper(x)^a / c(x)^b`
- Conformal score: `U(x) = epsilon_rel * S(x) / tau`
- Routing: `U(x) <= epsilon_rel -> fast`, otherwise `slow`

## Metrics
| split | fast_ratio | avg_latency_ms | violation_rate | violation 95%CI | avg_delta_l_rel |
|---|---:|---:|---:|---|---:|
| calib | 0.404667 | 10.058670 | 0.020000 | [0.014045, 0.028407] | -0.004921 |
| test | 0.542222 | 9.782008 | 0.062222 | [0.048225, 0.079940] | -0.002903 |

## Gate Check (P5)
- `violation_rate_le_7pct`: `True`
- `violation_ci95_upper_le_8pct`: `True`
- `latency_increase_vs_phase4_le_3pct`: `True`

## Artifacts
- `outputs/router_conformal_v1/policy_metrics.json`
- `outputs/router_conformal_v1/calib_decisions.parquet`
- `outputs/router_conformal_v1/test_decisions.parquet`
- `outputs/router_conformal_v1/search_log.csv`