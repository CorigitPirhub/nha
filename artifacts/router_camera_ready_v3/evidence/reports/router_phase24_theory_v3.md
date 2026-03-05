# Router Theory V3 Report (Phase24)

## Summary
- Runtime: `0.000 h`
- Seeds: `[11, 19, 23, 31, 7]`
- Theorems: `3`

## Gate Check
- `theory_v3_nontrivial`: `True`
- `empirical_checks_all_hold`: `True`
- `bound_gap_reasonable`: `True`

## Seed Checks (Phase23)
|   seed |   test_violation_rate |   regret_mean |   regret_ucb |   regret_slack | decisions_test                                                           | decisions_calib                                                           |
|-------:|----------------------:|--------------:|-------------:|---------------:|:-------------------------------------------------------------------------|:--------------------------------------------------------------------------|
|      7 |             0.0360472 |      0.416688 |     0.634621 |       0.217933 | outputs/router_phase23_portfolio_v1/seeds/seed_7/test_decisions.parquet  | outputs/router_phase23_portfolio_v1/seeds/seed_7/calib_decisions.parquet  |
|     11 |             0.0403978 |      0.406438 |     0.627176 |       0.220739 | outputs/router_phase23_portfolio_v1/seeds/seed_11/test_decisions.parquet | outputs/router_phase23_portfolio_v1/seeds/seed_11/calib_decisions.parquet |
|     19 |             0.0385333 |      0.433419 |     0.653258 |       0.219838 | outputs/router_phase23_portfolio_v1/seeds/seed_19/test_decisions.parquet | outputs/router_phase23_portfolio_v1/seeds/seed_19/calib_decisions.parquet |
|     23 |             0.031386  |      0.440246 |     0.657086 |       0.216841 | outputs/router_phase23_portfolio_v1/seeds/seed_23/test_decisions.parquet | outputs/router_phase23_portfolio_v1/seeds/seed_23/calib_decisions.parquet |
|     31 |             0.0282784 |      0.512522 |     0.631462 |       0.11894  | outputs/router_phase23_portfolio_v1/seeds/seed_31/test_decisions.parquet | outputs/router_phase23_portfolio_v1/seeds/seed_31/calib_decisions.parquet |

## Shift Certificates (Phase23, by OOD family)
|   seed |   ood_family |   n_calib |   n_test |   emp_risk_test |   bound_from_calib |      slack | hold   |   p_test_easy |   p_test_medium |   p_test_hard |   u_calib_easy |   u_calib_medium |   u_calib_hard |
|-------:|-------------:|----------:|---------:|----------------:|-------------------:|-----------:|:-------|--------------:|----------------:|--------------:|---------------:|-----------------:|---------------:|
|      7 |            0 |       720 |     2577 |       0.032596  |          0.0465868 | 0.0139908  | True   |     0.16104   |       0.573923  |      0.265037 |      0.0409356 |        0.0448715 |      0.0537351 |
|      7 |            1 |       720 |      641 |       0.049922  |          0.0526781 | 0.00275608 | True   |     0.0156006 |       0.0967239 |      0.887676 |      0.0409356 |        0.0448715 |      0.0537351 |
|     11 |            0 |       720 |     2577 |       0.0407451 |          0.0512468 | 0.0105017  | True   |     0.16104   |       0.573923  |      0.265037 |      0.0856273 |        0.0417085 |      0.0510113 |
|     11 |            1 |       720 |      641 |       0.0390016 |          0.0506515 | 0.01165    | True   |     0.0156006 |       0.0967239 |      0.887676 |      0.0856273 |        0.0417085 |      0.0510113 |
|     19 |            0 |       720 |     2577 |       0.0368646 |          0.0428035 | 0.00593895 | True   |     0.16104   |       0.573923  |      0.265037 |      0.0427582 |        0.0293695 |      0.0719218 |
|     19 |            1 |       720 |      641 |       0.0452418 |          0.067351  | 0.0221092  | True   |     0.0156006 |       0.0967239 |      0.887676 |      0.0427582 |        0.0293695 |      0.0719218 |
|     23 |            0 |       720 |     2577 |       0.0279395 |          0.0569071 | 0.0289676  | True   |     0.16104   |       0.573923  |      0.265037 |      0.0987005 |        0.0455791 |      0.056043  |
|     23 |            1 |       720 |      641 |       0.0452418 |          0.0556964 | 0.0104546  | True   |     0.0156006 |       0.0967239 |      0.887676 |      0.0987005 |        0.0455791 |      0.056043  |
|     31 |            0 |       720 |     2577 |       0.0267753 |          0.0639616 | 0.0371862  | True   |     0.16104   |       0.573923  |      0.265037 |      0.0469378 |        0.080847  |      0.0377409 |
|     31 |            1 |       720 |      641 |       0.0343214 |          0.0420537 | 0.00773237 | True   |     0.0156006 |       0.0967239 |      0.887676 |      0.0469378 |        0.080847  |      0.0377409 |

## Probe Monotonicity (Phase9)
|   seed | monotone_hold   |   monotone_violate_cases |   risk_base |   risk_probe | risk_nonincrease_hold   | base_path                                                                                                                  | probe_path                                                                                                             |
|-------:|:----------------|-------------------------:|------------:|-------------:|:------------------------|:---------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------|
|      7 | True            |                        0 |    0.194531 |     0.194531 | True                    | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_7/mixed/conformal_strict_v2/test_decisions.parquet  | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_7/mixed/probe_strict_v2/test_decisions.parquet  |
|     11 | True            |                        0 |    0.193288 |     0.193288 | True                    | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_11/mixed/conformal_strict_v2/test_decisions.parquet | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_11/mixed/probe_strict_v2/test_decisions.parquet |
|     19 | True            |                        0 |    0.192356 |     0.192356 | True                    | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_19/mixed/conformal_strict_v2/test_decisions.parquet | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_19/mixed/probe_strict_v2/test_decisions.parquet |
|     23 | True            |                        0 |    0.19422  |     0.19422  | True                    | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_23/mixed/conformal_strict_v2/test_decisions.parquet | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_23/mixed/probe_strict_v2/test_decisions.parquet |
|     31 | True            |                        0 |    0.193909 |     0.193909 | True                    | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_31/mixed/conformal_strict_v2/test_decisions.parquet | outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/seeds/seed_31/mixed/probe_strict_v2/test_decisions.parquet |

## Artifacts
- `out_dir`: `outputs/router_phase24_theory_v3`
- `report_md`: `reports/router_phase24_theory_v3.md`
- `seed_csv`: `outputs/router_phase24_theory_v3/seed_checks.csv`
- `shift_csv`: `outputs/router_phase24_theory_v3/shift_bounds.csv`
- `probe_csv`: `outputs/router_phase24_theory_v3/probe_monotone.csv`