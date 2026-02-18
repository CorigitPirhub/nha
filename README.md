# Neural-Guided Hybrid A* (Ackermann) Demo

This repository contains a full prototype for:

1. Generating diverse 2D obstacle maps (`random`, `narrow passage`, `parking`).
2. Computing ESDF and a teacher heuristic field (2D Dijkstra distance-to-goal).
3. Training a CNN (Tiny-UNet) to predict heuristic guidance fields.
4. Injecting the predicted field into a Hybrid A* planner with Ackermann kinematics.
5. Comparing baseline vs neural-guided search on identical maps/start-goal pairs.

## Core Idea

- **Planner state:** `(x, y, yaw)` with nonholonomic Ackermann motion primitives.
- **Teacher signal:** shortest 2D geometric distance field (ignoring heading), used as supervision.
- **Neural heuristic injection:** predicted 2D field is queried with **bilinear interpolation**.
- **Optimality guard:** planner keeps an admissible anchor heuristic (Euclidean lower bound) for lower-bound termination, while using neural field for queue ordering.

## Project Structure

- `config.py`: centralized experiment/configuration dataclasses.
- `env/`: map generation, ESDF, teacher field, dataset build.
- `planner/`: Hybrid A*, heuristics, evaluation.
- `network/`: dataset loader, Tiny-UNet, train/inference.
- `utils/`: utilities and visualization.
- `scripts/`: runnable entrypoints.

## Quick Start

```bash
python -m pip install -r requirements.txt
python scripts/run_demo.py --device cpu --epochs 6 --train-size 80 --val-size 16 --test-size 12
```

This will generate:

- `outputs/checkpoints/heuristic_net.pt`
- `outputs/logs/demo_summary.json`
- `outputs/logs/eval_geometric_cases.csv`
- `outputs/logs/eval_blind_cases.csv`
- `outputs/figures/training_curve.png`
- `outputs/figures/example_fields.png`
- `outputs/figures/example_paths.png`

## Individual Steps

```bash
python scripts/generate_dataset.py --train 120 --val 24 --test 20
python scripts/train.py --epochs 8 --device cpu
python scripts/evaluate.py --device cpu --checkpoint outputs/checkpoints/heuristic_net.pt
```

`evaluate.py` prints two tables:

- `geometric heuristic (Euclidean)` vs `neural-guided`
- `blind search (h=0)` vs `neural-guided`

## Notes

- The teacher field is 2D (no heading), so the learned heuristic captures obstacle-aware geometry and strongly guides Hybrid A* expansion.
- In this prototype, neural guidance matches geometric-heuristic expansion counts and significantly outperforms blind search (`h=0`) in node expansions and runtime.
- Path feasibility is guaranteed by Ackermann forward simulation + collision checks against ESDF.
- The demo is intentionally lightweight; increase map size, dataset size, and epochs for stronger results.
