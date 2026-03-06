# Phase23 Portfolio Router (v1)

## Summary
- `runtime_hours`: `0.0021148360936139297`
- `seeds`: `[7, 11, 19, 23, 31]`
- `t_ref_ms`: `2.3302950139623135`
- `beta`: `25.833333333333332`
- `baseline_best_arm`: `always_mid`
- `selection`: `{'calib_train_frac': 0.6, 'risk_safety_margin': 0.005, 'risk_ci95_hi_max_on_calib': 0.045000000000000005}`
- `sweep`: `{'sweep_levels': 15, 'sweep_csv': 'outputs/router_phase23_portfolio_v2_strict/common/sweep_grid_mean_over_seeds.csv', 'pareto_candidate': None}`
- `ours_vs_always_mid`: `{'dJ_mean': -0.03078530085880351, 'dJ_ci95': [-0.07620098571588467, 0.009195931052707041], 'dJ_boot_p_one_sided': 0.0603, 'dJ_wilcoxon_p': 0.3125, 'dLatency_mean_ms': -0.0069218009950232865, 'dLatency_ci95': [-0.11924583363350227, 0.10705130057038384], 'dLatency_boot_p_one_sided': 0.449, 'dRisk_mean': -0.000559353635798631, 'dRisk_ci95': [-0.0072715972653822234, 0.005842137973896833], 'dRisk_boot_p_one_sided': 0.4509}`
- `gate_check`: `{'num_arms_ge_3': True, 'risk_constraint_hold_all_seeds': False, 'pareto_improve_vs_best_arm': False}`
- `artifacts`: `{'out_dir': 'outputs/router_phase23_portfolio_v2_strict', 'report_md': 'reports/router_phase23_portfolio_v2_strict.md', 'table_csv': 'paper/tables_router_v17_phase23_portfolio_strict/table_phase23_portfolio_strict.csv', 'fig_path': 'paper/figures_router_v17_phase23_portfolio_strict/fig_portfolio_tradeoff_strict.svg', 'sweep_csv': 'outputs/router_phase23_portfolio_v2_strict/common/sweep_grid_mean_over_seeds.csv'}`

## Seed Metrics (test)
|   seed |   tau_fast |   tau_mid |   test_J_mean |   test_latency_ms |   test_violation_rate |   test_violation_ci95_hi |   ratio_fast |   ratio_mid |   ratio_slow | calib_decisions_parquet                                                          | decisions_parquet                                                               |
|-------:|-----------:|----------:|--------------:|------------------:|----------------------:|-------------------------:|-------------:|------------:|-------------:|:---------------------------------------------------------------------------------|:--------------------------------------------------------------------------------|
|      7 |   0.24931  | 0.0539687 |      0.703837 |           1.38756 |             0.0478558 |                0.0557854 |    0.178993  |    0.744251 |    0.0767557 | outputs/router_phase23_portfolio_v2_strict/seeds/seed_7/calib_decisions.parquet  | outputs/router_phase23_portfolio_v2_strict/seeds/seed_7/test_decisions.parquet  |
|     11 |   0.270634 | 0.253514  |      0.751744 |           1.45586 |             0.0422623 |                0.0497764 |    0.128651  |    0.813238 |    0.0581106 | outputs/router_phase23_portfolio_v2_strict/seeds/seed_11/calib_decisions.parquet | outputs/router_phase23_portfolio_v2_strict/seeds/seed_11/test_decisions.parquet |
|     19 |   0.260196 | 0.214322  |      0.792795 |           1.57202 |             0.0385333 |                0.0457525 |    0.0366687 |    0.92542  |    0.0379117 | outputs/router_phase23_portfolio_v2_strict/seeds/seed_19/calib_decisions.parquet | outputs/router_phase23_portfolio_v2_strict/seeds/seed_19/test_decisions.parquet |
|     23 |   0.015    | 0.175399  |      0.793338 |           1.62465 |             0.0316967 |                0.0383301 |    0         |    0.948415 |    0.0515848 | outputs/router_phase23_portfolio_v2_strict/seeds/seed_23/calib_decisions.parquet | outputs/router_phase23_portfolio_v2_strict/seeds/seed_23/test_decisions.parquet |
|     31 |   0.247373 | 0.111921  |      0.848269 |           1.76473 |             0.0264139 |                0.0325446 |    0.0994406 |    0.570851 |    0.329708  | outputs/router_phase23_portfolio_v2_strict/seeds/seed_31/calib_decisions.parquet | outputs/router_phase23_portfolio_v2_strict/seeds/seed_31/test_decisions.parquet |

## Sweep (top feasible points, mean over seeds, test)
| fast_level   | mid_level   |   J_mean |   latency_ms |   violation_rate |   ratio_fast |   ratio_mid |   ratio_slow | risk_hold_all_seeds   |
|:-------------|:------------|---------:|-------------:|-----------------:|-------------:|------------:|-------------:|:----------------------|
| q=0.071      | q=0.929     | 0.773551 |      1.52941 |        0.0382225 |    0.0830329 |    0.841641 |   0.0753263  | True                  |
| q=0.000      | q=0.929     | 0.792125 |      1.58966 |        0.0348042 |    0.0371659 |    0.887383 |   0.0754506  | True                  |
| q=0.000      | q=1.000     | 0.793112 |      1.50753 |        0.0408328 |    0.0371659 |    0.961715 |   0.00111871 | True                  |
| q=0.000      | +inf        | 0.793835 |      1.50632 |        0.0410193 |    0.0371659 |    0.962834 |   0          | True                  |
| q=0.071      | q=0.857     | 0.795354 |      1.61077 |        0.0349285 |    0.0830329 |    0.768241 |   0.148726   | True                  |
| -inf         | q=0.929     | 0.807158 |      1.6521  |        0.0316346 |    0         |    0.923741 |   0.0762585  | True                  |
| -inf         | q=1.000     | 0.808059 |      1.5691  |        0.0377253 |    0         |    0.998881 |   0.00111871 | True                  |
| -inf         | +inf        | 0.808782 |      1.56789 |        0.0379117 |    0         |    1        |   0          | True                  |
| q=0.000      | q=0.857     | 0.814081 |      1.67165 |        0.0314481 |    0.0371659 |    0.813424 |   0.14941    | True                  |
| q=0.071      | q=0.786     | 0.815611 |      1.6725  |        0.0328776 |    0.0830329 |    0.712617 |   0.204351   | True                  |
| -inf         | q=0.857     | 0.830018 |      1.7362  |        0.0282784 |    0         |    0.848726 |   0.151274   | True                  |
| q=0.000      | q=0.786     | 0.834967 |      1.73484 |        0.0293971 |    0.0371659 |    0.756495 |   0.206339   | True                  |
| q=0.071      | q=0.714     | 0.840827 |      1.73872 |        0.0311995 |    0.0830329 |    0.653139 |   0.263828   | True                  |
| -inf         | q=0.786     | 0.851793 |      1.80149 |        0.0262275 |    0         |    0.789932 |   0.210068   | True                  |
| q=0.000      | q=0.714     | 0.862079 |      1.80554 |        0.0277191 |    0.0371659 |    0.692977 |   0.269857   | True                  |
| q=0.071      | q=0.643     | 0.865489 |      1.80021 |        0.0297079 |    0.0830329 |    0.597763 |   0.319204   | True                  |
| -inf         | q=0.714     | 0.87903  |      1.8744  |        0.0244873 |    0         |    0.724487 |   0.275513   | True                  |
| q=0.071      | q=0.571     | 0.88196  |      1.84621 |        0.0283406 |    0.0830329 |    0.556308 |   0.360659   | True                  |
| q=0.143      | q=0.429     | 0.883758 |      1.85081 |        0.0348664 |    0.159354  |    0.399192 |   0.441454   | True                  |
| q=0.000      | q=0.643     | 0.88829  |      1.87078 |        0.0261653 |    0.0371659 |    0.634245 |   0.328589   | True                  |
| q=0.071      | q=0.500     | 0.888958 |      1.90344 |        0.0246116 |    0.0830329 |    0.504786 |   0.412181   | True                  |
| q=0.143      | q=0.357     | 0.900886 |      1.93682 |        0.0300186 |    0.159354  |    0.322312 |   0.518334   | True                  |
| -inf         | q=0.643     | 0.90626  |      1.94205 |        0.0229335 |    0         |    0.66358  |   0.33642    | True                  |
| q=0.000      | q=0.571     | 0.908592 |      1.92678 |        0.0244251 |    0.0371659 |    0.583592 |   0.379242   | True                  |
| q=0.000      | q=0.500     | 0.916056 |      1.98519 |        0.0206339 |    0.0371659 |    0.531013 |   0.431821   | True                  |
| q=0.071      | q=0.429     | 0.918046 |      1.98248 |        0.0224363 |    0.0830329 |    0.434058 |   0.482909   | True                  |
| -inf         | q=0.571     | 0.92935  |      2.00474 |        0.0211311 |    0         |    0.606961 |   0.393039   | True                  |
| q=0.143      | q=0.286     | 0.930583 |      2.01433 |        0.0282163 |    0.159354  |    0.253387 |   0.587259   | True                  |
| q=0.071      | q=0.357     | 0.935977 |      2.0708  |        0.0175264 |    0.0830329 |    0.355065 |   0.561902   | True                  |
| -inf         | q=0.500     | 0.937761 |      2.06538 |        0.01734   |    0         |    0.552331 |   0.447669   | True                  |

## Paper Table (mean over seeds, test)
| method              |   avg_latency_ms |   violation_rate |   J_mean |   oracle_gap |   ratio_fast |   ratio_mid |   ratio_slow |
|:--------------------|-----------------:|-----------------:|---------:|-------------:|-------------:|------------:|-------------:|
| always_fast         |          0.49025 |        0.288689  | 1.07422  |      1.98697 |    1         |    0        |     0        |
| always_mid          |          1.56789 |        0.0379117 | 0.808782 |      1.24889 |    0         |    1        |     0        |
| always_slow         |          2.68644 |        0         | 1.15283  |      2.20556 |    0         |    0        |     1        |
| portfolio_router_v1 |          1.56096 |        0.0373524 | 0.777997 |      1.16329 |    0.0887508 |    0.800435 |     0.110814 |