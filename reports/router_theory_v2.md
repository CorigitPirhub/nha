# Router Theory V2 Report

## Summary
- Runtime: `0.000 h`
- Seeds: `[7, 11, 19, 23, 31]`
- Map families: `45`
- Pooled risk gap: `0.518%`
- Pooled risk (empirical/upper): `0.193661` / `0.198836`

## Gate Check
- `new_theorem_count_ge_2`: `True`
- `proof_complete`: `True`
- `empirical_le_theory_upper_all_seeds`: `True`
- `theory_gap_le_1pct`: `True`
- `shift_robust_bound_hold`: `True`
- `min_seed_count_ge_5`: `True`
- `map_family_count_ge_min`: `True`
- `map_empirical_le_theory_upper_all`: `True`

## Step-1 Deliverable Check
- `docs/router_theory_v2.md`: `True`
- `docs/router_theory_v2_appendix.md`: `True`
- `scripts/run_router_theory_v2.py`: `True`
- `outputs/router_theory_v2/stats.json`: `True`
- `reports/router_theory_v2.md`: `True`

## Seed Risk/Regret Metrics
|   seed |   n_cases |   violation_rate |   theory_upper |   theory_gap | empirical_le_upper   |   regret_mean |   regret_upper | regret_bound_hold   |   map_family_count |
|-------:|----------:|-----------------:|---------------:|-------------:|:---------------------|--------------:|---------------:|:--------------------|-------------------:|
|      7 |      3218 |         0.194531 |       0.206263 |    0.0117323 | True                 |      0.398868 |       0.56081  | True                |                 45 |
|     11 |      3218 |         0.193288 |       0.204993 |    0.0117055 | True                 |      0.391334 |       0.55204  | True                |                 45 |
|     19 |      3218 |         0.192356 |       0.204041 |    0.0116853 | True                 |      0.384922 |       0.543828 | True                |                 45 |
|     23 |      3218 |         0.19422  |       0.205946 |    0.0117256 | True                 |      0.401228 |       0.563237 | True                |                 45 |
|     31 |      3218 |         0.193909 |       0.205628 |    0.0117189 | True                 |      0.376132 |       0.53385  | True                |                 45 |

## Map-Family Risk Metrics (Top 20 by support)
| map_id               |   k_vio |   n_cases |   violation_rate |   theory_upper |   theory_gap | empirical_le_upper   |
|:---------------------|--------:|----------:|-----------------:|---------------:|-------------:|:---------------------|
| mp_single_bugtrap    |     284 |      1505 |        0.188704  |       0.205847 |    0.0171429 | True                 |
| mp_alternating_gaps  |     387 |      1485 |        0.260606  |       0.279766 |    0.0191601 | True                 |
| mp_mazes             |     381 |      1470 |        0.259184  |       0.278413 |    0.019229  | True                 |
| mp_multiple_bugtraps |     326 |      1460 |        0.223288  |       0.241717 |    0.0184298 | True                 |
| mp_gaps_and_forest   |     183 |      1430 |        0.127972  |       0.143208 |    0.0152364 | True                 |
| mp_shifting_gaps     |     288 |      1425 |        0.202105  |       0.22016  |    0.0180548 | True                 |
| mp_forest            |     337 |      1365 |        0.246886  |       0.266572 |    0.0196855 | True                 |
| mp_bugtrap_forest    |     292 |      1360 |        0.214706  |       0.233577 |    0.0188715 | True                 |
| packed_002           |      35 |       330 |        0.106061  |       0.137215 |    0.0311546 | True                 |
| packed_008           |      30 |       325 |        0.0923077 |       0.122189 |    0.0298815 | True                 |
| packed_009           |      30 |       315 |        0.0952381 |       0.125992 |    0.030754  | True                 |
| packed_007           |      25 |       310 |        0.0806452 |       0.109859 |    0.0292142 | True                 |
| packed_001           |      75 |       305 |        0.245902  |       0.288576 |    0.0426748 | True                 |
| packed_004           |      45 |       300 |        0.15      |       0.187031 |    0.0370305 | True                 |
| packed_005           |      35 |       290 |        0.12069   |       0.155711 |    0.0350214 | True                 |
| packed_000           |      60 |       285 |        0.210526  |       0.252876 |    0.0423502 | True                 |
| packed_003           |      60 |       275 |        0.218182  |       0.261786 |    0.0436039 | True                 |
| packed_006           |      30 |       275 |        0.109091  |       0.143905 |    0.0348145 | True                 |
| packed_013           |      30 |       180 |        0.166667  |       0.217221 |    0.0505547 | True                 |
| packed_017           |      22 |       170 |        0.129412  |       0.177628 |    0.0482162 | True                 |

## Shift-Robust Checks
|   seed |   nominal_prior_easy |   nominal_prior_medium |   nominal_prior_hard |   candidate_priors |   empirical_worst_shifted_risk |   theory_worst_shifted_upper | shift_robust_hold   |
|-------:|---------------------:|-----------------------:|---------------------:|-------------------:|-------------------------------:|-----------------------------:|:--------------------|
|      7 |              0.13207 |               0.478869 |             0.389062 |                 12 |                       0.195319 |                     0.216542 | True                |
|     11 |              0.13207 |               0.478869 |             0.389062 |                 12 |                       0.195969 |                     0.217279 | True                |
|     19 |              0.13207 |               0.478869 |             0.389062 |                 12 |                       0.192991 |                     0.214127 | True                |
|     23 |              0.13207 |               0.478869 |             0.389062 |                 12 |                       0.196685 |                     0.218005 | True                |
|     31 |              0.13207 |               0.478869 |             0.389062 |                 12 |                       0.19537  |                     0.216607 | True                |

## Artifacts
- `seed_metrics_csv`: `outputs/router_theory_v2/seed_metrics.csv`
- `map_family_metrics_csv`: `outputs/router_theory_v2/map_family_metrics.csv`
- `shift_robust_metrics_csv`: `outputs/router_theory_v2/shift_robust_metrics.csv`
- `report_md`: `reports/router_theory_v2.md`