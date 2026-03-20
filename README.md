# TrajectoryPlanning/distill — Repository Entry Points

This repo contains multiple research tracks. The **current strict submission mainline** is the router track, but its main claim has changed: the live claim is now **Risk-Calibrated Single-Search Compute Shaping / Weighted-Search Tree Portfolio**, while the earlier **Dual-Path Probe Router** is retained only as a historical baseline / audit line.

## Router Mainline — Risk-Calibrated Compute Shaping (Weighted-Search Tree Portfolio)

Given a planning query on a grid map, the current router no longer spends extra compute on an external probe and then flips `fast -> slow`. Instead, it keeps the **same A* search skeleton** and routes over **internal compute levels** by choosing a heuristic weight `w(x)`:
- `fast` / `w=1.0`: standard A*
- `wa_w105 ... wa_w135`: weighted A* arms with different compute-quality tradeoffs
- `slow`: reference-quality arm (kept as optional fallback in `P`, but not used by the final best policy)

The current deployable strict-mainline policy is:
- **`O / TreeWeightPortfolio`**: shallow tree partition over `static + fastgeom + difficulty`, with one weighted-search arm per leaf
- **`P / TreeWeightSlowFallback`**: same family with optional `slow` fallback; under current strict data it is numerically identical to `O`, because no seed actually uses `slow`

### Current strict status (2026-03-06)

Under the fully audited **strict** semantics (frozen `alpha=0.05`, `calib_train/calib_val/test` separation, probe/runtime honest accounting, no dataset-ID leakage, sha256-bound parquet inputs), the old **probe-router** claim does **not** survive, but the new **zero-probe single-search compute-shaping** claim **does** survive end-to-end:
- Step12-R4 screening: `reports/router_phase29_step12r4_trials_v1.md`
- Phase13 strict SOTA run (O): `reports/router_phase13_sota_v10_strict_weighted_tree_o.md`
- Phase22 strict direct-baseline run (O): `reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md`
- Task-book status + honest caveats: `TASK.md`
- Step14 successor-family screening (`A/B/C/D` in `phase30`, `E/F/G/H` in `phase31`, the `14-F`-line TARP refinements in `phase32`, and the final `RCWS-B` sprint in `phase33`) still did not produce a replacement for `O`; see `reports/router_phase30_step14_trials_v1.md`, `reports/router_phase31_step14_fresh_trials_v1.md`, `reports/router_phase32_step14_tarp_line_v1.md`, and `reports/router_phase33_step14_rcwsb_trials_v1.md`

Current strict conclusion, in one sentence:
- **Yes, the strict main conclusion is recovered end-to-end — but only for the new zero-probe single-search compute-shaping method, not for the old dual-path probe-router claim.**

### Frozen paper claim contract (Step 13)

- Exact current paper-facing claim and non-claims: `paper/router_current_mainline_claim_contract.md`
- Frozen protocol source: `docs/router_protocol_v1.md`
- Current-mainline protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`
- Current valid scope: Protocol V1 strict semantics, `L = expansions` + path audit, public strict benchmarks `csm/mp/parasol`

### Main evidence to read first

- Strict source root: `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak`
- Phase29 weighted-search screening summary: `outputs/router_phase29_step12r4_trials_v1/summary.json`
- Best policy artifacts (O): `outputs/router_phase29_o_tree_weight_v1/`
- Phase13 strict downstream result (O): `outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`
- Phase22 strict downstream result (O): `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`
- Legacy strict audit for the abandoned probe-router claim: `reports/router_strict_audit_v2.md`

### Reproducing the current strict mainline

- **Step12-R4 weighted-search family screening:**
  ```bash
  python scripts/run_router_phase29_step12r4_trials_v1.py
  ```
- **Phase13 strict downstream evaluation (best policy O):**
  ```bash
  python scripts/run_router_phase13_sota.py \
    --phase9-root outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak \
    --ours-root outputs/router_phase29_o_tree_weight_v1 \
    --ours-policy-dirname ignored \
    --ours-arm-table-test outputs/router_phase29_step12r4_trials_v1/common/router_counterfactual_test_wastar.parquet \
    --out-dir outputs/router_phase13_sota_v10_strict_weighted_tree_o \
    --report-md reports/router_phase13_sota_v10_strict_weighted_tree_o.md \
    --tables-dir paper/tables_router_v24_strict_weighted_tree_o \
    --no-enforce-gate
  ```
- **Phase22 strict direct-baseline evaluation (best policy O):**
  ```bash
  python scripts/run_router_phase22_direct_baselines.py \
    --phase9-root outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak \
    --ours-root outputs/router_phase29_o_tree_weight_v1 \
    --ours-policy-dirname ignored \
    --ours-arm-table-test outputs/router_phase29_step12r4_trials_v1/common/router_counterfactual_test_wastar.parquet \
    --out-dir outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o \
    --report-md reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md \
    --tables-dir paper/tables_router_v25_strict_weighted_tree_o \
    --no-enforce-gate
  ```

### Honest caveat for Phase22

`Phase22` now evaluates budget parity under `weighted_search_slow_fallback_cap` rather than the old `fast -> slow` flip budget. In the realized best policy, the cap is `0` for all difficulties, so CRC/CDT collapse to the same decision rule as `P5`. This does **not** invalidate the new result, but it means the supporting claim is:
- **the weighted-search tree portfolio beats both P5 and the matched direct-baseline family under the zero-probe compute-shaping budget semantics**,
not
- “the old probe router still wins after strict auditing”.

### Where to look (outputs)

- Step12-R4 report: `reports/router_phase29_step12r4_trials_v1.md`
- Phase13 strict report (O): `reports/router_phase13_sota_v10_strict_weighted_tree_o.md`
- Phase22 strict report (O): `reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md`
- Phase13 strict report (P, tie with O): `reports/router_phase13_sota_v10_strict_weighted_tree_p.md`
- Phase22 strict report (P, tie with O): `reports/router_phase22_direct_baselines_v10_strict_weighted_tree_p.md`
- Legacy strict audit bundle for the old probe-router line: `outputs/final_v5_strict/manifest.json`
- Phase reports: `reports/`
- Paper assets: `paper/tables_router_v*/`, `paper/figures_router_v*/`

### Notes

- `docs/router_protocol_v1.md` remains the frozen protocol source of truth.
- `docs/router_protocol_v1_current_mainline_note.md` explains how the **current weighted-search mainline** maps onto that unchanged frozen protocol.
- `docs/neurips_method_v1.md` and `docs/router_theory_v3.md` are now **dual-layer** docs; use `paper/router_current_mainline_claim_contract.md` as the frozen paper-facing claim contract, and use those docs for method/theory detail.
- Step 3 (real-hardware longrun) is still a **Top-Journal** requirement, but it is orthogonal to the current strict method claim.
- `paper/router_current_mainline_claim_contract.md` is the frozen paper-facing claim entry for the current strict mainline.

---

## Nonholonomic Neural Heuristic for Hybrid A* (Ackermann)

### Current RS-grounded status (2026-03-17)

Within the nonholonomic track, the currently accepted RS-grounded branch is:
- **`RS + CX34-A / Subtype-Specific Macro Rescue`**

Current leading fusion candidate:
- **`RS + CX34-A + CX42-B / Query Compatibility Release`**

Honest current reading:
- this branch is the first one on the `P0-CX` line that makes public `parasol_misc` non-negative while keeping `maze = 0.0`;
- on the canonical stored artifact, it preserves the `CX33-B` head-family gains (`flange = +1421.0`, `narrow_passage = +99.75`) and lifts overall public `exp_delta` to `+420.389`;
- a frozen hard-test verification on `rs_root_hard_v2/test` is now complete on the locked `cuda` artifact: vs `CX3-D`, `success_delta_pp = +2.740` and `exp_delta = +196.548`, see `reports/rs_p0cx34_a_hard_eval_v1.md`;
- exact public numbers remain frozen to `outputs/rs_p0cx34_a_pilot_v1`, while exact hard-test numbers are frozen to `outputs/rs_p0cx34_a_hard_eval_cuda_v1`;
- it is still **not** a final deployable answer: runtime remains high, and hard-test still shows family-specific regressions on `deadend_labyrinth`, `flange`, and `parasol_misc`.

Fusion-candidate reading:
- `CX42-B` is currently the strongest **hard-runtime fusion candidate** for the RS track;
- on the unified public rerun `reports/rs_p0cx42_public_compare_v1.md`, it is tied with `CX34-A` on success / expansions and is slightly slower on average (`mean_time_overhead_ratio = +0.010346`), so its public advantage is not currently confirmed;
- on the frozen `rs_root_hard_v2/test` artifact it preserves `CX34-A` exactly on success / expansions / path length while reducing runtime (`mean_time_overhead_ratio = -0.289825`);
- despite this, the paper-facing accepted branch remains `CX34-A`; `CX42-B` should currently be treated as a **compatibility-layer candidate**, not yet as the frozen accepted claim.

Read these files first for the current RS-grounded branch:
- paper-facing claim contract: `paper/rs_cx_current_claim_contract.md`
- fusion-candidate contract: `paper/rs_cx_fusion_candidate_contract.md`
- canonical accepted summary: `reports/rs_p0cx34_round1_summary.md`
- recheck / merge audit: `reports/rs_p0cx34_recheck_audit_v1.md`
- frozen hard-test eval: `reports/rs_p0cx34_a_hard_eval_v1.md`
- canonical pilot report: `reports/rs_p0cx34_a_pilot_v1.md`
- fusion candidate public report: `reports/rs_p0cx42_b_pilot_v1.md`
- fusion candidate hard-test report: `reports/rs_p0cx42_b_hard_eval_v1.md`
- full-support audit: `reports/rs_p0cx34_standard_audit_v1.md`
- previous parent branch summary: `reports/rs_p0cx33_round1_summary.md`
- task-book status, acceptance scope and next-step rationale: `TASK.md`

This project implements a full prototype for TRO-style iterative research:

1. Stage-1 diagnosis of 2D teacher limitations.
2. Stage-2 nonholonomic teacher redesign (Dubins-distilled yaw-aware field).
3. Stage-3 fixed benchmark (Type A/B/C) with 3-way baseline comparisons.

## Core Pipeline

- Planner: `Hybrid A*` over `(x, y, yaw)` with Ackermann motion primitives.
- Environment: random / narrow / parking / deadend maps + ESDF.
- Teacher:
  - `teacher_2d`: obstacle-aware 2D Dijkstra field.
  - `teacher_3d`: yaw-aware nonholonomic field distilled from Dubins + heading proxy.
- Network:
  - Tiny-UNet, input channels: `occupancy, ESDF, goal_gaussian, sin(theta_g), cos(theta_g)`.
  - output channels: yaw bins (`teacher_yaw_bins`, default 24).
- Heuristic injection:
  - Bilinear/trilinear interpolation for 2D/3D fields.
  - Baselines and ours are evaluated under identical maps and start/goal.

## Project Structure

- `config.py`: all central configs.
- `env/`: map generation, ESDF, Dubins module, teacher generation, dataset builder.
- `planner/`: Hybrid A*, heuristic interfaces, benchmark evaluator.
- `network/`: dataset, model, train, inference.
- `scripts/`: diagnosis / build / train / evaluate / end-to-end demo.
- `utils/`: common utilities + visualization.

## Install

```bash
python -m pip install -r requirements.txt
```

## Stage-1 Diagnosis

```bash
python scripts/diagnose_stage1.py --data data_benchmark/test --checkpoint outputs/checkpoints/heuristic_net.pt --device cuda
```

Outputs:

- `outputs/figures/stage1_diagnosis_heatmaps.png`
- `outputs/logs/stage1_diagnosis.json`

## Quick Start (Best Residual Setup)

```bash
python scripts/run_demo.py --seed 7 --device cuda --use-rs-cache
```

This uses the best validated defaults:

- residual learning (`prediction_mode=residual`)
- planner-consistent hybrid RS teacher (`teacher_mode=hybrid_rs_consistent_esdf`)
- residual gain `alpha=1.1`
- RS cache enabled for repeated evaluation runs

## Build Fixed Benchmark (Type A/B/C)

```bash
python scripts/build_benchmark.py --output data_benchmark --seed 7 --train-counts 18 18 18 --val-counts 6 6 6 --test-counts 8 8 8 --precompute-rs-cache
```

## Train (GPU, Best Hyperparameters)

```bash
python scripts/train.py --data data_costaware --seed 7 --prediction-mode residual --epochs 60 --lr 2e-4 --under-weight 1.0 --type-c-weight 1.0 --device cuda
```

## Evaluate (4-way + Time Breakdown + Optional RS Cache)

```bash
python scripts/evaluate.py --data data_benchmark --seed 7 --checkpoint outputs/checkpoints/heuristic_net_residual_costaware_scratch_u1_lr2e4.pt --residual-alpha 1.1 --device cuda
python scripts/evaluate.py --data data_benchmark --seed 7 --checkpoint outputs/checkpoints/heuristic_net_residual_costaware_scratch_u1_lr2e4.pt --residual-alpha 1.1 --use-rs-cache --device cuda

# export planning-process animation (mp4; auto-fallback to gif if ffmpeg unavailable)
python scripts/evaluate.py --data data_benchmark --seed 7 --checkpoint outputs/checkpoints/heuristic_net_residual_costaware_scratch_u1_lr2e4.pt --residual-alpha 1.1 --animation-out outputs/figures/planning_process.mp4 --device cuda
```

Recommended cache reproducibility flow (same `--rs-cache-dir` for both runs):

```bash
# cold run: populate cache (expect low hit rate)
python scripts/evaluate.py --data data_benchmark --seed 7 --checkpoint outputs/checkpoints/heuristic_net_residual_costaware_scratch_u1_lr2e4.pt --residual-alpha 1.1 --use-rs-cache --rs-cache-dir outputs/rs_cache_benchmark_v1 --scatter-out outputs/figures/efficiency_scatter_cache_cold.png --device cuda

# hot run: reuse cache (expect hit_rate ~= 100%)
python scripts/evaluate.py --data data_benchmark --seed 7 --checkpoint outputs/checkpoints/heuristic_net_residual_costaware_scratch_u1_lr2e4.pt --residual-alpha 1.1 --use-rs-cache --rs-cache-dir outputs/rs_cache_benchmark_v1 --scatter-out outputs/figures/efficiency_scatter_cache_hot.png --device cuda
```

Optional build-time cache precompute:

```bash
python scripts/build_benchmark.py --output data_benchmark --seed 7 --train-counts 18 18 18 --val-counts 6 6 6 --test-counts 8 8 8 --precompute-rs-cache --rs-cache-dir outputs/rs_cache_benchmark_v1
```

Compared methods:

- `Hybrid A* + Euclidean` (Baseline 1)
- `Hybrid A* + Dubins` (Baseline 2, clipped analytic nonholonomic heuristic)
- `Hybrid A* + RS-Consistent Analytical` (Baseline 3)
- `Hybrid A* + Ours` (RS + neural residual correction)

Generated figures:

- `outputs/figures/nonholonomic_field_compare.png`
- `outputs/figures/search_tree_type_c_compare.png`
- `outputs/figures/training_curve.png`
- `outputs/figures/efficiency_scatter.png`

## One-Command Demo

```bash
python scripts/run_demo.py --seed 7 --train-counts 18 18 18 --val-counts 6 6 6 --test-counts 8 8 8 --epochs 12 --batch-size 8 --device cuda --use-rs-cache
```

## Reproducibility

All reported results use fixed random seed `7` for scripts. Dataset splits are generated deterministically via offset seeds (`seed + 101/202/303`) in builders, so repeated runs on the same environment should match split composition and metric trends.

## Official Results (Submission Snapshot)

Source logs:

- `outputs/logs/final_efficiency_report.json`
- `outputs/logs/final_submission_table.csv`
- `outputs/logs/benchmark_summary_alpha1.1_nocache_v2.json`
- `outputs/logs/benchmark_summary_alpha1.1_cache_hot_v1.json`

Type-C key result (24 benchmark cases total):

- RS-Consistent: `5719.4` expansions
- Ours: `5700.3` expansions (slight improvement)

No-cache runtime summary (avg total ms):

| Method | Avg Expansions | Avg Total Time (ms) |
|---|---:|---:|
| Euclidean | 10165.5 | 1280.27 |
| Dubins | 4820.5 | 967.27 |
| RS-Consistent | 2783.9 | 10978.05 |
| Ours | 2803.2 | 11087.47 |

Cache-hot runtime summary (`hits=24, misses=0`, avg total ms):

| Method | Avg Expansions | Avg Total Time (ms) |
|---|---:|---:|
| Euclidean | 10165.5 | 1379.97 |
| Dubins | 4820.5 | 1058.08 |
| RS-Consistent | 2783.9 | 571.41 |
| Ours | 2803.2 | 661.52 |

Final efficiency plot (cache hot):

![Efficiency-Quality Scatter (Cache Hot)](outputs/figures/efficiency_scatter_cache_hot.png)

## Notes

- Stage-1 shows 2D teacher improves obstacle guidance, but does not encode yaw-state dependency.
- Stage-2 introduces yaw-aware nonholonomic supervision and GPU training.
- Stage-3 uses fixed seeds and fixed splits for reproducible benchmark tables/figures.
