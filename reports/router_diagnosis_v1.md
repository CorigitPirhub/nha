# Router Diagnosis V1 (Phase 3)

## Summary
- `beta` (from calib median scale): `0.178726`
- Current v2 fast ratio (overall): `1.0000`
- Default router fast ratio (overall): `0.8156`
- All-fast bias diagnosis: `configuration_saturation`

## 95% CI Metrics (Required)
| policy | avg_J | J 95%CI | avg_OG | OG 95%CI | violation | V 95%CI |
|---|---:|---|---:|---|---:|---|
| current_v2 | 38.284034 | [35.681806, 41.009259] | 0.000000 | [0.000000, 0.000000] | 0.278889 | [0.250000, 0.307806] |
| default_router | 43.901627 | [40.832624, 47.086682] | 0.140616 | [0.110213, 0.175091] | 0.256667 | [0.228889, 0.285556] |
| all_fast | 38.284034 | [35.681806, 41.009259] | 0.000000 | [0.000000, 0.000000] | 0.278889 | [0.250000, 0.307806] |

## Fast Ratio by Difficulty
| difficulty | current_v2 | default_router |
|---|---:|---:|
| easy | 1.0000 | 0.8967 |
| medium | 1.0000 | 0.7933 |
| hard | 1.0000 | 0.7567 |

## Complexity Correlation with |ΔL|
- Static complexity score: `rho=-0.131463`, `p=7.635071e-05`
- Diagnostic complexity score (probe-informed): `rho=0.587595`, `p=1.168513e-84`

Phase-3 gate target check (`rho>=0.35`, `p<0.01`): PASS

## Pareto Artifacts
- CSV: `/home/zzy/TrajectoryPlanning/distill/reports/router_diagnosis_v1/pareto_curve.csv`
- Figure: `/home/zzy/TrajectoryPlanning/distill/reports/router_diagnosis_v1/pareto_curve_latency_vs_quality.svg`
- Metrics JSON: `/home/zzy/TrajectoryPlanning/distill/reports/router_diagnosis_v1/metrics.json`