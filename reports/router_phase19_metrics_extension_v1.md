# Router Phase19 Metrics Extension V1 Report

## Summary
- Runtime: `0.001 h`
- Secondary metric added: `clearance_min_*` (distance-to-obstacle along planned path; min over path)
- Seeds: `[7, 11, 19, 23, 31]`
- Methods: `['conformal_strict_v2', 'probe_strict_v2']`

## Gate Check
- `secondary_metric_added`: `True`
- `secondary_results_reported_all_seeds`: `True`
- `router_not_worse_on_secondary`: `True`
- `proxy_validity_explained`: `True`

## Frozen Thresholds (Non-Inferiority)
- `clearance_noninferiority_margin_m`: `0.250`
- Decision rule: require `CI95_low(mean(Δclearance)) >= -margin` (paired bootstrap, pooled across 5 seeds)

## Secondary Results (Test)
| method | pooled mean Δclearance (m) | 95% CI | p_boot(mean <= -margin) | noninferior |
|---|---:|---|---:|---|
| conformal_strict_v2 | +0.000000 | [+0.000000, +0.000000] | 0.000e+00 | True |
| probe_strict_v2 | +0.000000 | [+0.000000, +0.000000] | 0.000e+00 | True |

## Primary Metrics (Test, sanity)
| method | J_mean (mean±std over seeds) | V (mean±std over seeds) | use_fast_ratio (mean±std) |
|---|---:|---:|---:|
| conformal_strict_v2 | 0.728567±0.008780 | 0.060667±0.003201 | 0.548667±0.004675 |
| probe_strict_v2 | 0.709274±0.011777 | 0.056444±0.003960 | 0.542444±0.004187 |

## Proxy Validity (Expansions vs Clearance)
- We report Spearman correlation between `L_slow` (expansions) and `clearance_min_slow` on the test split.
- Interpretation: negative ρ implies harder search (more expansions) tends to occur in lower-clearance environments.

| group (ood_family) | n | Spearman ρ | p-value |
|---|---:|---:|---:|
| 0 | 600 | -0.555289 | 7.834e-50 |
| 1 | 300 | -0.506109 | 6.423e-21 |

### Notes on Applicability / Failure Modes (Frozen)
- clearance_min is computed from a 2D occupancy grid via Euclidean distance transform (in meters), sampled at A* path cell-centers; it is sensitive to map discretization (resolution=0.5 m in router_mixed_v1).
- Expansions (L_slow) correlates with low-clearance structure in corridor-like maps; correlation can weaken in open areas where path length dominates but clearance stays high.
- This secondary analysis is diagnostic only and does not replace the frozen primary objective/risk protocol (docs/router_protocol_v1.md).

## Artifacts
- `counterfactual_test_parquet`: `outputs/router_phase19_metrics_extension_v1/common/counterfactual_test.parquet`
- `counterfactual_test_report_json`: `outputs/router_phase19_metrics_extension_v1/common/counterfactual_test_report.json`
- `counterfactual_calib_parquet`: `outputs/router_phase19_metrics_extension_v1/common/counterfactual_calib.parquet`
- `counterfactual_calib_report_json`: `outputs/router_phase19_metrics_extension_v1/common/counterfactual_calib_report.json`
- `seed_level_csv`: `outputs/router_phase19_metrics_extension_v1/tables/seed_level_secondary_metrics.csv`
- `proxy_corr_by_ood_family_csv`: `outputs/router_phase19_metrics_extension_v1/tables/proxy_validity_corr_by_ood_family.csv`
- `paper_table_csv`: `paper/tables_router_v6/table_secondary_metrics.csv`
- `paper_fig_delta_svg`: `paper/figures_router_v6/fig_secondary_metrics_clearance_delta.svg`
- `paper_fig_delta_png`: `paper/figures_router_v6/fig_secondary_metrics_clearance_delta.png`
- `paper_fig_proxy_svg`: `paper/figures_router_v6/fig_secondary_metrics_proxy_validity.svg`
- `paper_fig_proxy_png`: `paper/figures_router_v6/fig_secondary_metrics_proxy_validity.png`
