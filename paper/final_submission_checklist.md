# Final Submission Checklist (V3)

## Gate Status
- `cold_start_runtime_le_48h`: `True`
- `hash_consistency_100pct`: `True`
- `claim_coverage_100pct`: `True`
- `audit_blocker_zero`: `True`

## Claim-to-Evidence
| claim_id | pass | metric | target | evidence |
|---|---:|---|---|---|
| C01 | True | True | True | outputs/router_phase12_realworld_v1/stats.json |
| C02 | True | {'success': True, 'collision': True, 'p95': True, 'p99': True} | all True | outputs/router_phase12_realworld_v1/stats.json, reports/router_phase12_realworld_v1.md |
| C03 | True | 7 | >=6 | outputs/router_phase13_sota_v1/stats.json, paper/tables_router_v3/table_phase13_external_sota_summary.csv |
| C04 | True | 5.710% | >=3% | outputs/router_phase13_sota_v1/stats.json |
| C05 | True | {'p': 0.0, 'ci95': [0.04395226184856901, 0.07064381485170529]} | p<0.01 and ci_low>0 | outputs/router_phase13_sota_v1/stats.json |
| C06 | True | -0.578 | <=0.5 | outputs/router_phase13_sota_v1/stats.json |
| C07 | True | {'types': True, 'cases': True} | both True | outputs/router_phase14_stress_v1/stats.json, outputs/router_phase14_stress_v1/stress_profile_summary.csv |
| C08 | True | {'worst10': 0.9666666666666667, 'recovery': 0.9794450154162384} | >=0.92 and >=0.95 | outputs/router_phase14_stress_v1/stats.json |
| C09 | True | 0 | 0 | outputs/router_phase14_stress_v1/stats.json |
| C10 | True | True | True | outputs/router_phase12_realworld_v1/stats.json |
| C11 | True | True | True | outputs/router_phase11_theory_v1/stats.json |
| C12 | True | {'baseline_family_count_ge_3': True, 'same_protocol_and_budget': True} | both True | outputs/router_phase16_related_baselines_v1/stats.json, reports/router_phase16_related_baselines_v1.md |
| C13 | True | {'J_improve_vs_best_related_ge_3pct': True, 'risk_not_worse_deltaV_le_0_5pct': True, 'pooled_p_lt_0_01_and_ci_no_cross_0': True} | all True | outputs/router_phase16_related_baselines_v1/stats.json |
| C14 | True | {'policy_single_source_of_truth': True, 'policy_vs_rule_no_regression_large': True} | both True | outputs/router_phase17_policy_alignment_v1/stats.json, reports/router_phase17_policy_alignment_v1.md, artifacts/router_policy_v1/policy.json, artifacts/router_policy_v1/POLICY.sha256 |
| C15 | True | {'secondary_metric_added': True, 'secondary_results_reported_all_seeds': True, 'router_not_worse_on_secondary': True, 'proxy_validity_explained': True} | all True | outputs/router_phase19_metrics_extension_v1/stats.json, reports/router_phase19_metrics_extension_v1.md, paper/tables_router_v6/table_secondary_metrics.csv |
| C16 | True | {'demo_runs_under_10s': True, 'probe_is_monotone_safe': True} | both True | outputs/router_phase21_neurips_positioning_v1/stats.json, reports/router_phase21_neurips_positioning_v1.md, docs/neurips_method_v1.md, utils/router_method_core.py |
| C17 | True | {'direct_baselines_ge_2': True, 'same_protocol_and_budget': True, 'either_win_or_reframe': True, 'main_result_significant': True} | all True | outputs/router_phase22_direct_baselines_v1/stats.json, reports/router_phase22_direct_baselines_v1.md, paper/tables_router_v7/table_phase22_direct_baselines.csv |
| C18 | True | {'num_arms_ge_3': True, 'pareto_improve_vs_best_arm': True, 'risk_constraint_hold_all_seeds': True} | all True | outputs/router_phase23_portfolio_v1/stats.json, reports/router_phase23_portfolio_v1.md, paper/tables_router_v7/table_phase23_portfolio.csv, paper/figures_router_v7/fig_portfolio_tradeoff.svg, outputs/router_phase23_midnet_arm_full_tiny_b64_v1/stats.json |
| C19 | True | {'bound_gap_reasonable': True, 'empirical_checks_all_hold': True, 'theory_v3_nontrivial': True} | all True | outputs/router_phase24_theory_v3/stats.json, reports/router_phase24_theory_v3.md, docs/router_theory_v3.md, docs/router_theory_v3_appendix.md, outputs/router_phase24_theory_v3/seed_checks.csv, outputs/router_phase24_theory_v3/shift_bounds.csv |
| C20 | True | {'new_settings_ge_2': True, 'risk_control_holds_in_new_settings': True, 'trend_consistent': True} | all True | outputs/router_phase25_generalization_v1/stats.json, reports/router_phase25_generalization_v1.md, paper/figures_router_v7/fig_generalization_mp.svg, paper/figures_router_v7/fig_generalization_csm.svg |

## Reproduction
- One-command: `bash artifacts/router_camera_ready_v3/reproduce_main_tables_figures.sh`
- Container: `docker build -t router-camera-ready-v3 -f artifacts/router_camera_ready_v3/Dockerfile .`
- Estimated cold-start runtime: `3.456 h` (target <= 48 h)

## Hash Audit
- Hash consistency: `100.00%` (65 / 65)
- Manifest: `artifacts/router_camera_ready_v3/MANIFEST.sha256`

## Notes
- Step3 (real-hardware longrun) is excluded from NeurIPS/ICML readiness; required for Top-Journal.

## Blockers
- `None (0 blocker)`
