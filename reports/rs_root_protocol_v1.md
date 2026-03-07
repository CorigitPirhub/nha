# RS Root Protocol V1

Status: `frozen-root-protocol`

This report freezes the **single fair protocol bundle** that is allowed to support the `RS cost field` root claim.

## Primary Reading Rule
- Primary nearest-baseline claim must use `outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv`.
- `Hybrid A* (RS)` is the primary nearest baseline.
- `Kinodynamic BIT* / RRT*` are auxiliary only and must not be used as the main root claim target.

## Block A — Hard-Bundle Necessity (parasol_narrow/test)
- samples: `18`; maps: `17`
- overall success: `Full=0.777778` vs `No-RS=0.166667`
- narrow_passage success: `Full=0.750000` vs `No-RS=0.000000`
- Full vs No-Residual expansions: `-9.437%`
- Full vs No-Residual time: `-9.498%`
- Interpretation: this block supports the **necessity / solvability** side of the RS root claim.

## Block B — Fair Nearest-Baseline Comparison (parasol, exp4_public_kinodynamic)
- frozen fairness: `hybrid_budget_cap=0`, `sampling_max_iters=300`
- success: `Ours=1.000000` vs `Hybrid A* (RS)=1.000000`
- expansions delta vs Hybrid A* (RS): `-1.543%`
- time delta vs Hybrid A* (RS): `-1.592%`
- path-length delta vs Hybrid A* (RS): `-0.032%`
- time delta vs Kinodynamic BIT*: `53.967%`
- time delta vs Kinodynamic RRT*: `39.727%`
- Interpretation: only the comparison to `Hybrid A* (RS)` is allowed to support the **primary nearest-baseline** RS-root claim.

## Block C — Ordinary-Scene Support (auxiliary only)
- mp expansions delta vs A*: `-0.310%`
- mp+csm expansions delta vs A*: `0.828%`
- csm expansions delta vs A*: `1.745%`
- mp+csm time delta vs A*: `5158.090%`
- Interpretation: this block may support a limited statement like 'expansions stay near A* on ordinary maps', but it is **not** the main root claim.

## Allowed Root Claims
- Removing the RS cost field causes a large solvability collapse on the hard parasol_narrow bundle.
- Under the frozen fair kinodynamic comparison, the RS-guided current model improves search effort/time over Hybrid A* (RS) while matching success.
- On ordinary mp/csm maps, expansions stay near A*; this is support evidence, not the main root claim.

## Forbidden Root Claims
- Do not use the older non-fair BIT*/RRT* timing comparison as the primary RS-root claim.
- Do not claim that the RS cost field alone is already a stable overall SOTA across all nearest baselines.
- Do not merge RS-only/root claims with upper-layer residual or router claims without explicitly separating them.

## Expanded Hard Benchmark
- benchmark root: `data/benchmark/rs_root_hard_v1/`
- benchmark audit: `reports/rs_root_hard_benchmark_v1.md`
- benchmark manifest: `outputs/rs_root_hard_benchmark_v1/manifest.json`
- standardized v2 benchmark root: `data/benchmark/rs_root_hard_v2/`
- benchmark card: `docs/rs_root_hard_benchmark_card_v1.md`
- quality audit: `reports/rs_root_hard_benchmark_v2_quality.md`
- anchor-only table: `paper/tables_rs_root_v1/table_rs_root_anchor_only_comparison.csv`
- first P0-C axis-search attempt: `reports/rs_root_p0c_axis_v1.md`
- second P0-C fixed-axis verification: `reports/rs_root_p0c_axis_round2_v1.md`
- round2 paper table: `paper/tables_rs_root_v1/table_rs_root_p0c_round2_fixed_axis.csv`
- third P0-C expansion-focused search: `reports/rs_root_p0c_axis_round3_v1.md`
- round3 paper table: `paper/tables_rs_root_v1/table_rs_root_p0c_round3_expansion_focus.csv`
- fourth P0-C success-under-budget verification: `reports/rs_root_p0c_axis_round4_v1.md`
- round4 paper table: `paper/tables_rs_root_v1/table_rs_root_p0c_round4_success_budget_focus.csv`
- dedicated root-eval script prepared: `scripts/eval_rs_root_hard_v1.py`
- dedicated smoke audit on expanded benchmark: `reports/rs_root_hard_v1_exp3_smoke.md`

## Artifact Chain
- manifest: `outputs/rs_root_protocol_v1/manifest.json`
- report: `reports/rs_root_protocol_v1.md`
- exp3 source: `outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv`
- exp4 fair source: `outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv`
- ordinary support source: `outputs/paper/manual_v11b_exp12/exp_results_summary.csv`
- parasol meta: `data/benchmark/parasol_narrow/meta.json`