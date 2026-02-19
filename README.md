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

## Build Fixed Benchmark (Type A/B/C)

```bash
python scripts/build_benchmark.py --output data_benchmark --train-counts 18 18 18 --val-counts 6 6 6 --test-counts 8 8 8
```

## Train (GPU)

```bash
python scripts/train.py --data data_benchmark --epochs 12 --batch-size 8 --device cuda
```

## Evaluate (3-way)

```bash
python scripts/evaluate.py --data data_benchmark --checkpoint outputs/checkpoints/heuristic_net.pt --device cuda
```

Compared methods:

- `Hybrid A* + Euclidean` (Baseline 1)
- `Hybrid A* + Dubins` (Baseline 2, clipped analytic nonholonomic heuristic)
- `Hybrid A* + Ours` (learned nonholonomic neural heuristic)

Generated figures:

- `outputs/figures/nonholonomic_field_compare.png`
- `outputs/figures/search_tree_type_c_compare.png`
- `outputs/figures/training_curve.png`

## One-Command Demo

```bash
python scripts/run_demo.py --seed 7 --train-counts 18 18 18 --val-counts 6 6 6 --test-counts 8 8 8 --epochs 12 --batch-size 8 --device cuda
```

## Latest Run Snapshot

From the latest benchmark run (`24` test cases total):

- Euclidean: success `0.917`, avg expansions `10165.5`
- Dubins: success `0.917`, avg expansions `4820.5`
- Ours: success `0.917`, avg expansions `10828.3`
- Ours vs Euclidean (overall): expansion reduction `+1.14%`
- Type C (parking/deadend):
  - Euclidean avg expansions `15000.6`
  - Ours avg expansions `12502.4` (notable reduction)

## Notes

- Stage-1 shows 2D teacher improves obstacle guidance, but does not encode yaw-state dependency.
- Stage-2 introduces yaw-aware nonholonomic supervision and GPU training.
- Stage-3 uses fixed seeds and fixed splits for reproducible benchmark tables/figures.
