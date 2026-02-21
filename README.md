# Nonholonomic Neural Heuristic for Hybrid A* (Ackermann)

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
