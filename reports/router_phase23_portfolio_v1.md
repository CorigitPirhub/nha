# Phase23 Portfolio Router (v1)

## Summary
- `runtime_hours`: `0.0034010318583265566`
- `seeds`: `[7, 11, 19, 23, 31]`
- `t_ref_ms`: `2.3302950139623135`
- `beta`: `25.833333333333332`
- `baseline_best_arm`: `always_mid`
- `selection`: `{'calib_train_frac': 0.6, 'risk_safety_margin': 0.005, 'risk_ci95_hi_max_on_calib': 0.045000000000000005}`
- `sweep`: `{'sweep_levels': 15, 'sweep_csv': 'outputs/router_phase23_portfolio_v1/common/sweep_grid_mean_over_seeds.csv', 'pareto_candidate': {'fast_level': 'q=0.071', 'mid_level': 'q=0.929', 'J_mean': 0.7872585895098922, 'latency_ms': 1.5554620010339562, 'violation_rate': 0.037663144810441265, 'ratio_fast': 0.07470478558110627, 'ratio_mid': 0.8439403356121815, 'ratio_slow': 0.08135487880671229, 'risk_hold_all_seeds': True}}`
- `ours_vs_always_mid`: `{'dJ_mean': -0.007283519874344302, 'dJ_ci95': [-0.03389680266042101, 0.029754006587761637], 'dJ_boot_p_one_sided': 0.2997, 'dJ_wilcoxon_p': 0.625, 'dLatency_mean_ms': 0.04383399567075972, 'dLatency_ci95': [-0.030999543276836006, 0.1384186839479073], 'dLatency_boot_p_one_sided': 0.799, 'dRisk_mean': -0.0029832193909260394, 'dRisk_ci95': [-0.006960845245494093, 0.0008701056556867634], 'dRisk_boot_p_one_sided': 0.0733}`
- `gate_check`: `{'num_arms_ge_3': True, 'risk_constraint_hold_all_seeds': True, 'pareto_improve_vs_best_arm': True}`
- `artifacts`: `{'out_dir': 'outputs/router_phase23_portfolio_v1', 'report_md': 'reports/router_phase23_portfolio_v1.md', 'table_csv': 'paper/tables_router_v7/table_phase23_portfolio.csv', 'fig_path': 'paper/figures_router_v7/fig_portfolio_tradeoff.svg', 'sweep_csv': 'outputs/router_phase23_portfolio_v1/common/sweep_grid_mean_over_seeds.csv'}`

## Seed Metrics (test)
|   seed |   tau_fast |   tau_mid |   test_J_mean |   test_latency_ms |   test_violation_rate |   test_violation_ci95_hi |   ratio_fast |   ratio_mid |   ratio_slow | calib_decisions_parquet                                                   | decisions_parquet                                                        |
|-------:|-----------:|----------:|--------------:|------------------:|----------------------:|-------------------------:|-------------:|------------:|-------------:|:--------------------------------------------------------------------------|:-------------------------------------------------------------------------|
|      7 |   0.235568 | 0.0870858 |      0.776324 |           1.55745 |             0.0360472 |                0.0430608 |    0.0540709 |    0.897452 |    0.0484773 | outputs/router_phase23_portfolio_v1/seeds/seed_7/calib_decisions.parquet  | outputs/router_phase23_portfolio_v1/seeds/seed_7/test_decisions.parquet  |
|     11 |   0.301126 | 0.253716  |      0.766074 |           1.49941 |             0.0403978 |                0.0477664 |    0.0944686 |    0.843381 |    0.0621504 | outputs/router_phase23_portfolio_v1/seeds/seed_11/calib_decisions.parquet | outputs/router_phase23_portfolio_v1/seeds/seed_11/test_decisions.parquet |
|     19 |   0.256078 | 0.126828  |      0.793055 |           1.57071 |             0.0385333 |                0.0457525 |    0.0556246 |    0.885333 |    0.0590429 | outputs/router_phase23_portfolio_v1/seeds/seed_19/calib_decisions.parquet | outputs/router_phase23_portfolio_v1/seeds/seed_19/test_decisions.parquet |
|     23 |   0.015    | 0.175398  |      0.799882 |           1.63433 |             0.031386  |                0.0379912 |    0         |    0.940025 |    0.0599751 | outputs/router_phase23_portfolio_v1/seeds/seed_23/calib_decisions.parquet | outputs/router_phase23_portfolio_v1/seeds/seed_23/test_decisions.parquet |
|     31 |   0.256078 | 0.111503  |      0.872158 |           1.7967  |             0.0282784 |                0.0345924 |    0.143567  |    0.449969 |    0.406464  | outputs/router_phase23_portfolio_v1/seeds/seed_31/calib_decisions.parquet | outputs/router_phase23_portfolio_v1/seeds/seed_31/test_decisions.parquet |

## Sweep (top feasible points, mean over seeds, test)
| fast_level   | mid_level   |   J_mean |   latency_ms |   violation_rate |   ratio_fast |   ratio_mid |   ratio_slow | risk_hold_all_seeds   |
|:-------------|:------------|---------:|-------------:|-----------------:|-------------:|------------:|-------------:|:----------------------|
| q=0.071      | q=0.929     | 0.787259 |      1.55546 |        0.0376631 |    0.0747048 |    0.84394  |  0.0813549   | True                  |
| q=0.000      | q=0.929     | 0.796405 |      1.58935 |        0.035115  |    0.046675  |    0.87197  |  0.0813549   | True                  |
| q=0.071      | q=0.857     | 0.804457 |      1.62946 |        0.0338098 |    0.0747048 |    0.777004 |  0.148291    | True                  |
| -inf         | q=1.000     | 0.808523 |      1.56875 |        0.0377874 |    0         |    0.999192 |  0.000807955 | True                  |
| -inf         | +inf        | 0.808782 |      1.56789 |        0.0379117 |    0         |    1        |  0           | True                  |
| q=0.000      | q=0.857     | 0.813632 |      1.66341 |        0.0312617 |    0.046675  |    0.804972 |  0.148353    | True                  |
| -inf         | q=0.929     | 0.813649 |      1.65849 |        0.031821  |    0         |    0.918024 |  0.0819764   | True                  |
| q=0.071      | q=0.786     | 0.825631 |      1.69315 |        0.0317589 |    0.0747048 |    0.719329 |  0.205966    | True                  |
| -inf         | q=0.857     | 0.831372 |      1.73373 |        0.0279677 |    0         |    0.849969 |  0.150031    | True                  |
| q=0.000      | q=0.786     | 0.835195 |      1.72801 |        0.0292107 |    0.046675  |    0.746489 |  0.206837    | True                  |
| q=0.071      | q=0.714     | 0.849197 |      1.75922 |        0.0298322 |    0.0747048 |    0.659664 |  0.265631    | True                  |
| -inf         | q=0.786     | 0.853657 |      1.80002 |        0.0259167 |    0         |    0.789994 |  0.210006    | True                  |
| q=0.000      | q=0.714     | 0.859099 |      1.79497 |        0.0272219 |    0.046675  |    0.686016 |  0.267309    | True                  |
| q=0.071      | q=0.643     | 0.871219 |      1.81842 |        0.0282784 |    0.0747048 |    0.606588 |  0.318707    | True                  |
| -inf         | q=0.714     | 0.87864  |      1.86948 |        0.0239279 |    0         |    0.727284 |  0.272716    | True                  |
| q=0.000      | q=0.643     | 0.881512 |      1.85508 |        0.0256681 |    0.046675  |    0.632132 |  0.321193    | True                  |
| q=0.143      | q=0.500     | 0.887768 |      1.84987 |        0.0332505 |    0.142511  |    0.444313 |  0.413176    | True                  |
| q=0.071      | q=0.571     | 0.896728 |      1.88189 |        0.0269111 |    0.0747048 |    0.54941  |  0.375886    | True                  |
| -inf         | q=0.643     | 0.902385 |      1.93306 |        0.022312  |    0         |    0.670292 |  0.329708    | True                  |
| q=0.143      | q=0.429     | 0.906291 |      1.90083 |        0.0317589 |    0.142511  |    0.399627 |  0.457862    | True                  |
| q=0.000      | q=0.571     | 0.907459 |      1.91972 |        0.0242387 |    0.046675  |    0.573897 |  0.379428    | True                  |
| q=0.071      | q=0.500     | 0.911557 |      1.94947 |        0.0236793 |    0.0747048 |    0.489497 |  0.435799    | True                  |
| q=0.000      | q=0.500     | 0.923653 |      1.99057 |        0.0210068 |    0.046675  |    0.511063 |  0.442262    | True                  |
| -inf         | q=0.571     | 0.929297 |      2       |        0.0208825 |    0         |    0.609944 |  0.390056    | True                  |
| q=0.071      | q=0.429     | 0.930802 |      2.00212 |        0.0221877 |    0.0747048 |    0.443319 |  0.481976    | True                  |
| q=0.143      | q=0.357     | 0.933509 |      2.01773 |        0.0262275 |    0.142511  |    0.295836 |  0.561653    | True                  |
| q=0.000      | q=0.429     | 0.94312  |      2.04377 |        0.0195152 |    0.046675  |    0.464388 |  0.488937    | True                  |
| -inf         | q=0.500     | 0.946278 |      2.07592 |        0.01734   |    0         |    0.542449 |  0.457551    | True                  |
| q=0.143      | q=0.286     | 0.958883 |      2.08529 |        0.0243008 |    0.142511  |    0.234866 |  0.622623    | True                  |
| q=0.071      | q=0.357     | 0.95961  |      2.12352 |        0.0164077 |    0.0747048 |    0.335488 |  0.589807    | True                  |

## Paper Table (mean over seeds, test)
| method              |   avg_latency_ms |   violation_rate |   J_mean |   oracle_gap |   ratio_fast |   ratio_mid |   ratio_slow |
|:--------------------|-----------------:|-----------------:|---------:|-------------:|-------------:|------------:|-------------:|
| always_fast         |          0.49025 |        0.288689  | 1.07422  |      1.98697 |    1         |    0        |     0        |
| always_mid          |          1.56789 |        0.0379117 | 0.808782 |      1.24889 |    0         |    1        |     0        |
| always_slow         |          2.68644 |        0         | 1.15283  |      2.20556 |    0         |    0        |     1        |
| portfolio_router_v1 |          1.61172 |        0.0349285 | 0.801499 |      1.22864 |    0.0695463 |    0.803232 |     0.127222 |