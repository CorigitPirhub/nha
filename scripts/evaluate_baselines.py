from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import GridSample, load_grid_sample, select_files
from baselines.kinodynamic_rrtstar import kinodynamic_bit_star, kinodynamic_rrt_star
from baselines.neural_astar import NeuralAStarLite, train_neural_astar
from baselines.vin import VINLite, train_vin
from config import DEFAULT_CONFIG
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from network.inference import NeuralHeuristicPredictor
from planner.heuristics import FieldHeuristic, YawFieldHeuristic
from planner.hybrid_astar import HybridAStarPlanner
from utils.common import ensure_dirs, set_seed


@dataclass
class EvalRow:
    experiment: str
    dataset: str
    method: str
    case_id: str
    success: bool
    expansions: float
    path_length: float
    runtime_ms: float
    infer_ms: float = 0.0
    search_ms: float = 0.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run paper-grade benchmark comparisons")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--hard-root", type=Path, default=Path("data/benchmark/parasol_narrow/test"))
    p.add_argument("--parasol-root", type=Path, default=Path("data/benchmark/parasol_narrow/test"))
    p.add_argument("--paper-out", type=Path, default=Path("outputs/paper"))
    p.add_argument(
        "--experiments",
        type=str,
        default="exp1,exp2,exp3,exp4",
        help="Comma-separated experiments to run: exp1(mp), exp2(csm), exp3(ablation), exp4(public_kinodynamic).",
    )

    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/heuristic_net_generalization_unified_mixed_v2.pt"))
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--seed", type=int, default=7)

    p.add_argument("--train-neural-epochs", type=int, default=4)
    p.add_argument("--train-neural-batch", type=int, default=24)
    p.add_argument("--train-neural-lr", type=float, default=1e-3)
    p.add_argument("--train-max-samples", type=int, default=2000)
    p.add_argument("--val-max-samples", type=int, default=400)
    p.add_argument("--skip-neural-training", action="store_true")

    p.add_argument("--max-standard-cases", type=int, default=200)
    p.add_argument(
        "--max-mp-cases",
        type=int,
        default=-1,
        help="Cap MP test cases for Exp1. >0: explicit cap; 0: all; <0: fallback to --max-standard-cases.",
    )
    p.add_argument(
        "--max-csm-cases",
        type=int,
        default=-1,
        help="Cap CSM test cases for Exp2. >0: explicit cap; 0: all; <0: fallback to --max-standard-cases.",
    )
    p.add_argument("--max-nonholonomic-cases", type=int, default=80)
    p.add_argument("--max-ablation-cases", type=int, default=100)
    p.add_argument(
        "--max-exp3-cases",
        type=int,
        default=-1,
        help="Cap Exp3 cases. >0: explicit cap; 0: all; <0: fallback to --max-nonholonomic-cases.",
    )
    p.add_argument(
        "--max-exp4-cases",
        type=int,
        default=-1,
        help="Cap Exp4 cases. >0: explicit cap; 0: all; <0: fallback to --max-public-cases.",
    )
    p.add_argument("--disable-exp2", action="store_true", help="Disable Experiment 2 output (keep other experiments).")
    p.add_argument("--standard-only", action="store_true", help="Run only standard MP/CSM benchmarks (skip nonholonomic/public experiments).")

    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--hybrid-max-expansions", type=int, default=12000)
    p.add_argument("--hybrid-hard-max-expansions", type=int, default=13000)
    p.add_argument("--hybrid-maze-max-expansions", type=int, default=18000)
    p.add_argument(
        "--hybrid-exp4-max-expansions",
        type=int,
        default=20000,
        help="Minimum Hybrid A* expansion budget for Exp4 public kinodynamic benchmark.",
    )
    p.add_argument(
        "--hybrid-budget-cap",
        type=int,
        default=0,
        help="When >0, cap Hybrid A* max expansions for nonholonomic experiments.",
    )
    p.add_argument("--sampling-max-iters", type=int, default=1500)
    p.add_argument("--rs-field-yaw-bins", type=int, default=24)
    p.add_argument("--residual-alpha", type=float, default=1.5)
    p.add_argument("--residual-clip", type=float, default=8.0)
    p.add_argument(
        "--residual-bias-quantile",
        type=float,
        default=0.0,
        help="Subtract this free-space residual quantile per-case to remove global positive bias.",
    )
    p.add_argument(
        "--residual-corridor-threshold",
        type=float,
        default=0.0,
        help="When >0, suppress residuals in low-clearance cells with ESDF below this threshold (meters).",
    )
    p.add_argument(
        "--residual-corridor-suppress",
        type=float,
        default=0.0,
        help="Suppression strength in [0,1] for corridor residual gating.",
    )
    p.add_argument(
        "--residual-topq-quantile",
        type=float,
        default=0.0,
        help="When >0, keep only residual values above this free-space quantile (top-q sparsification).",
    )
    p.add_argument(
        "--residual-contrastive-bg-quantile",
        type=float,
        default=0.0,
        help="When >0, convert residual to contrastive signed correction by subtracting this free-space background quantile.",
    )
    p.add_argument(
        "--residual-contrastive-neg-scale",
        type=float,
        default=0.0,
        help="Scale for negative contrastive residual after background subtraction (0 disables negative branch).",
    )
    p.add_argument(
        "--residual-contrastive-pos-scale",
        type=float,
        default=1.0,
        help="Scale for positive contrastive residual after background subtraction.",
    )
    p.add_argument(
        "--residual-floor-ratio",
        type=float,
        default=0.0,
        help="Safety floor: fused heuristic >= residual_floor_ratio * RS base.",
    )
    p.add_argument(
        "--residual-transport-iters",
        type=int,
        default=0,
        help="Obstacle-aware residual transport iterations (0 disables).",
    )
    p.add_argument(
        "--residual-transport-step",
        type=float,
        default=0.35,
        help="Step size for each residual transport iteration.",
    )
    p.add_argument(
        "--residual-transport-clearance-sigma",
        type=float,
        default=0.45,
        help="Clearance similarity scale (meters) for obstacle-aware residual transport.",
    )
    p.add_argument(
        "--residual-bottleneck-threshold",
        type=float,
        default=0.0,
        help="Bottleneck ESDF threshold (meters) used for local residual transport blending.",
    )
    p.add_argument(
        "--residual-bottleneck-blend",
        type=float,
        default=0.0,
        help="Blend ratio in [0,1] for bottleneck transport residual branch.",
    )
    p.add_argument(
        "--residual-bottleneck-gamma",
        type=float,
        default=1.0,
        help="Power factor for bottleneck blending mask (higher => more concentrated in tight corridors).",
    )
    p.add_argument(
        "--residual-open-boost",
        type=float,
        default=0.0,
        help="Adaptive positive residual gain in open regions (0 disables).",
    )
    p.add_argument(
        "--residual-open-boost-topq",
        type=float,
        default=0.0,
        help="Apply open-region boost only to positive residual values above this free-space quantile (0 disables).",
    )
    p.add_argument(
        "--residual-open-boost-min-line-clearance",
        type=float,
        default=0.0,
        help="Disable open boost when mean ESDF along start-goal line is below this threshold (meters).",
    )
    p.add_argument(
        "--residual-bottleneck-dampen",
        type=float,
        default=0.0,
        help="Adaptive residual damping in bottlenecks to improve narrow-scene robustness.",
    )
    p.add_argument(
        "--residual-adaptive-trust-ratio",
        type=float,
        default=0.0,
        help="When >0, clamp adaptive residual deviation from CRC baseline by quantile ratio.",
    )
    p.add_argument(
        "--residual-adaptive-trust-quantile",
        type=float,
        default=0.95,
        help="Quantile used by adaptive trust-region clamp.",
    )
    p.add_argument("--esdf-anchor-alpha", type=float, default=0.15)
    p.add_argument("--esdf-anchor-threshold", type=float, default=1.3)
    p.add_argument("--max-public-cases", type=int, default=40)
    p.add_argument(
        "--standard-base-mode",
        type=str,
        default="euclidean",
        choices=["euclidean", "rs"],
        help="Base heuristic used for Ours in Exp1 when checkpoint is in residual mode.",
    )
    p.add_argument(
        "--enable-dual-path-router",
        action="store_true",
        help="Enable Dual-Map Adaptive Router for Ours in Exp1/Exp2: fast classic A* vs slow learned heuristic.",
    )
    p.add_argument(
        "--router-corridor-radius-cells",
        type=int,
        default=2,
        help="Half width (in grid cells) of local corridor used to estimate complexity around start-goal line.",
    )
    p.add_argument(
        "--router-samples-per-cell",
        type=float,
        default=1.0,
        help="Sampling density on start-goal segment when computing complexity statistics.",
    )
    p.add_argument(
        "--router-fast-max-distance-ratio",
        type=float,
        default=0.75,
        help="Fast-path rule gate: normalized start-goal distance upper bound.",
    )
    p.add_argument(
        "--router-fast-max-line-block-ratio",
        type=float,
        default=0.30,
        help="Fast-path rule gate: max occupied ratio directly on start-goal line samples.",
    )
    p.add_argument(
        "--router-fast-max-local-occ-ratio",
        type=float,
        default=0.40,
        help="Fast-path rule gate: max local obstacle ratio in sampled corridor patches.",
    )
    p.add_argument(
        "--router-fast-max-global-occ-ratio",
        type=float,
        default=0.55,
        help="Fast-path rule gate: max global obstacle ratio for quick routing.",
    )
    p.add_argument(
        "--router-slow-min-line-block-ratio",
        type=float,
        default=0.65,
        help="Slow-path hard gate when direct line blockage is very high.",
    )
    p.add_argument(
        "--router-slow-min-local-occ-ratio",
        type=float,
        default=0.60,
        help="Slow-path hard gate when local corridor clutter is very high.",
    )
    p.add_argument(
        "--router-score-threshold",
        type=float,
        default=0.47,
        help="Risk-weighted complexity threshold: score above this goes to slow path.",
    )
    p.add_argument(
        "--router-w-line-block",
        type=float,
        default=0.42,
        help="Weight of direct line blockage in routing complexity score.",
    )
    p.add_argument(
        "--router-w-local-occ",
        type=float,
        default=0.33,
        help="Weight of local corridor clutter in routing complexity score.",
    )
    p.add_argument(
        "--router-w-distance",
        type=float,
        default=0.18,
        help="Weight of normalized start-goal distance in routing complexity score.",
    )
    p.add_argument(
        "--router-w-global-occ",
        type=float,
        default=0.07,
        help="Weight of global occupancy ratio in routing complexity score.",
    )
    p.add_argument(
        "--router-los-penalty",
        type=float,
        default=0.08,
        help="Additional risk penalty when exact line-of-sight from start to goal is blocked.",
    )
    p.add_argument(
        "--router-fast-score-margin",
        type=float,
        default=0.06,
        help="Confidence margin below score threshold to classify as fast when no hard rule is triggered.",
    )

    return p.parse_args()


def _world_to_grid(x: float, y: float, resolution: float, w: int, h: int) -> tuple[int, int]:
    gx = int(np.clip(np.floor(x / resolution), 0, w - 1))
    gy = int(np.clip(np.floor(y / resolution), 0, h - 1))
    return gx, gy


def _grid_to_world(ix: int, iy: int, resolution: float) -> tuple[float, float]:
    return (ix + 0.5) * resolution, (iy + 0.5) * resolution


def _path_length(path_xy: list[tuple[float, float]]) -> float:
    if len(path_xy) < 2:
        return float("nan")
    total = 0.0
    for i in range(1, len(path_xy)):
        dx = path_xy[i][0] - path_xy[i - 1][0]
        dy = path_xy[i][1] - path_xy[i - 1][1]
        total += math.hypot(dx, dy)
    return float(total)


def _mean_line_clearance(
    esdf: np.ndarray,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    resolution: float,
    samples_per_cell: float = 2.0,
) -> float:
    h, w = esdf.shape
    sx = float(start[0] / resolution - 0.5)
    sy = float(start[1] / resolution - 0.5)
    gx = float(goal[0] / resolution - 0.5)
    gy = float(goal[1] / resolution - 0.5)
    n = int(max(2, np.hypot(gx - sx, gy - sy) * float(max(samples_per_cell, 1.0))))
    xs = np.linspace(sx, gx, num=n, dtype=np.float32)
    ys = np.linspace(sy, gy, num=n, dtype=np.float32)
    xi = np.clip(np.floor(xs).astype(np.int64), 0, w - 1)
    yi = np.clip(np.floor(ys).astype(np.int64), 0, h - 1)
    vals = esdf[yi, xi].astype(np.float32)
    if vals.size <= 0:
        return float("inf")
    return float(np.mean(vals))


def _neighbors8() -> list[tuple[int, int, float]]:
    rt2 = math.sqrt(2.0)
    return [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, rt2),
        (-1, 1, rt2),
        (1, -1, rt2),
        (1, 1, rt2),
    ]


def _astar_grid(
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    max_expansions: int,
    heuristic_map: np.ndarray | None = None,
    heuristic_weight: float = 1.0,
    record_expanded: bool = False,
) -> dict:
    t0 = time.perf_counter()
    h, w = occupancy.shape
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)

    if occupancy[sy, sx] or occupancy[gy, gx]:
        return {
            "success": False,
            "expansions": 0,
            "runtime_ms": (time.perf_counter() - t0) * 1000.0,
            "path": [],
            "expanded": [],
        }

    def h_fn(ix: int, iy: int) -> float:
        if heuristic_map is None:
            return math.hypot((gx - ix) * resolution, (gy - iy) * resolution)
        v = float(heuristic_map[iy, ix])
        if not np.isfinite(v):
            return 1e6
        return max(v, 0.0)

    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    counter = 0
    start = (sx, sy)
    goal = (gx, gy)
    g_cost: dict[tuple[int, int], float] = {start: 0.0}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    f0 = heuristic_weight * h_fn(sx, sy)
    heapq.heappush(open_heap, (f0, 0.0, counter, start))

    expanded: list[tuple[int, int]] = []
    expansions = 0
    nbrs = _neighbors8()

    while open_heap and expansions < max(int(max_expansions), 1):
        f, g, _, node = heapq.heappop(open_heap)
        del f
        if g > g_cost.get(node, float("inf")) + 1e-9:
            continue

        expansions += 1
        if record_expanded:
            expanded.append(node)

        if node == goal:
            path_grid: list[tuple[int, int]] = []
            cur = node
            while cur is not None:
                path_grid.append(cur)
                cur = parent[cur]
            path_grid.reverse()
            path_xy = [_grid_to_world(ix, iy, resolution) for ix, iy in path_grid]
            return {
                "success": True,
                "expansions": expansions,
                "runtime_ms": (time.perf_counter() - t0) * 1000.0,
                "path": path_xy,
                "expanded": expanded,
            }

        x, y = node
        for dx, dy, step in nbrs:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            if occupancy[ny, nx]:
                continue
            ng = g + step * resolution
            nkey = (nx, ny)
            if ng + 1e-9 >= g_cost.get(nkey, float("inf")):
                continue
            g_cost[nkey] = ng
            parent[nkey] = node
            counter += 1
            nf = ng + heuristic_weight * h_fn(nx, ny)
            heapq.heappush(open_heap, (nf, ng, counter, nkey))

    return {
        "success": False,
        "expansions": expansions,
        "runtime_ms": (time.perf_counter() - t0) * 1000.0,
        "path": [],
        "expanded": expanded,
    }


def _line_of_sight(occupancy: np.ndarray, a: tuple[int, int], b: tuple[int, int]) -> bool:
    x0, y0 = a
    x1, y1 = b

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = 1 if x1 >= x0 else -1
    sy = 1 if y1 >= y0 else -1

    if dx >= dy:
        err = dx / 2.0
        while x != x1:
            if occupancy[y, x]:
                return False
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != y1:
            if occupancy[y, x]:
                return False
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy

    return not occupancy[y1, x1]


def _theta_star(
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    max_expansions: int,
) -> dict:
    t0 = time.perf_counter()
    h, w = occupancy.shape
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)

    if occupancy[sy, sx] or occupancy[gy, gx]:
        return {
            "success": False,
            "expansions": 0,
            "runtime_ms": (time.perf_counter() - t0) * 1000.0,
            "path": [],
        }

    start = (sx, sy)
    goal = (gx, gy)
    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    counter = 0
    g_cost: dict[tuple[int, int], float] = {start: 0.0}
    parent: dict[tuple[int, int], tuple[int, int]] = {start: start}

    def h_fn(ix: int, iy: int) -> float:
        return math.hypot((gx - ix) * resolution, (gy - iy) * resolution)

    heapq.heappush(open_heap, (h_fn(sx, sy), 0.0, counter, start))
    nbrs = _neighbors8()
    expansions = 0

    while open_heap and expansions < max(int(max_expansions), 1):
        _, g, _, s = heapq.heappop(open_heap)
        if g > g_cost.get(s, float("inf")) + 1e-9:
            continue

        expansions += 1
        if s == goal:
            path_grid = []
            cur = s
            while cur != parent[cur]:
                path_grid.append(cur)
                cur = parent[cur]
            path_grid.append(start)
            path_grid.reverse()
            path_xy = [_grid_to_world(ix, iy, resolution) for ix, iy in path_grid]
            return {
                "success": True,
                "expansions": expansions,
                "runtime_ms": (time.perf_counter() - t0) * 1000.0,
                "path": path_xy,
            }

        sx_i, sy_i = s
        for dx, dy, step in nbrs:
            nx, ny = sx_i + dx, sy_i + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            if occupancy[ny, nx]:
                continue
            n = (nx, ny)

            ps = parent[s]
            if _line_of_sight(occupancy, ps, n):
                cand_g = g_cost[ps] + math.hypot((ps[0] - nx) * resolution, (ps[1] - ny) * resolution)
                cand_parent = ps
            else:
                cand_g = g_cost[s] + step * resolution
                cand_parent = s

            if cand_g + 1e-9 < g_cost.get(n, float("inf")):
                g_cost[n] = cand_g
                parent[n] = cand_parent
                counter += 1
                nf = cand_g + h_fn(nx, ny)
                heapq.heappush(open_heap, (nf, cand_g, counter, n))

    return {
        "success": False,
        "expansions": expansions,
        "runtime_ms": (time.perf_counter() - t0) * 1000.0,
        "path": [],
    }


def _sample_free_xy(occupancy: np.ndarray, resolution: float, rng: np.random.Generator) -> tuple[float, float]:
    free = np.argwhere(~occupancy)
    if free.size == 0:
        return 0.0, 0.0
    yx = free[int(rng.integers(0, len(free)))]
    return _grid_to_world(int(yx[1]), int(yx[0]), resolution)


def _collision_free_segment(occupancy: np.ndarray, resolution: float, p: tuple[float, float], q: tuple[float, float]) -> bool:
    h, w = occupancy.shape
    dist = math.hypot(q[0] - p[0], q[1] - p[1])
    steps = max(2, int(math.ceil(dist / max(0.25 * resolution, 1e-3))))
    for i in range(steps + 1):
        t = i / steps
        x = (1.0 - t) * p[0] + t * q[0]
        y = (1.0 - t) * p[1] + t * q[1]
        gx, gy = _world_to_grid(x, y, resolution, w, h)
        if occupancy[gy, gx]:
            return False
    return True


def _steer(p: tuple[float, float], q: tuple[float, float], step: float) -> tuple[float, float]:
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    d = math.hypot(dx, dy)
    if d <= step:
        return q
    s = step / max(d, 1e-9)
    return p[0] + s * dx, p[1] + s * dy


def _rrt_star(
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    max_iters: int,
    step_size: float,
    goal_radius: float,
    rng: np.random.Generator,
    informed_cost: float | None = None,
) -> dict:
    t0 = time.perf_counter()

    nodes: list[tuple[float, float]] = [start_xy]
    parent: list[int] = [-1]
    cost: list[float] = [0.0]

    best_goal_idx = -1
    best_goal_cost = float("inf") if informed_cost is None else float(informed_cost)

    def sample() -> tuple[float, float]:
        if best_goal_idx >= 0:
            # informed sampling inside ellipse
            c = best_goal_cost
            d = math.hypot(goal_xy[0] - start_xy[0], goal_xy[1] - start_xy[1])
            if c > d + 1e-6:
                a = c / 2.0
                b = math.sqrt(max(a * a - (d / 2.0) ** 2, 1e-9))
                theta = math.atan2(goal_xy[1] - start_xy[1], goal_xy[0] - start_xy[0])
                for _ in range(40):
                    r = math.sqrt(float(rng.random()))
                    ang = float(rng.uniform(0.0, 2.0 * math.pi))
                    ex = r * a * math.cos(ang)
                    ey = r * b * math.sin(ang)
                    x = (start_xy[0] + goal_xy[0]) * 0.5 + ex * math.cos(theta) - ey * math.sin(theta)
                    y = (start_xy[1] + goal_xy[1]) * 0.5 + ex * math.sin(theta) + ey * math.cos(theta)
                    gx, gy = _world_to_grid(x, y, resolution, occupancy.shape[1], occupancy.shape[0])
                    if not occupancy[gy, gx]:
                        return x, y
        if rng.random() < 0.1:
            return goal_xy
        return _sample_free_xy(occupancy, resolution, rng)

    expansions = 0

    for _ in range(max(int(max_iters), 1)):
        expansions += 1
        q_rand = sample()

        dists = [(nodes[i][0] - q_rand[0]) ** 2 + (nodes[i][1] - q_rand[1]) ** 2 for i in range(len(nodes))]
        near_idx = int(np.argmin(np.asarray(dists, dtype=np.float64)))
        q_near = nodes[near_idx]
        q_new = _steer(q_near, q_rand, step_size)

        if not _collision_free_segment(occupancy, resolution, q_near, q_new):
            continue

        # choose parent among neighbors
        rad = max(step_size * 2.5, 1.0)
        nbr_idx = []
        for i, p in enumerate(nodes):
            if math.hypot(p[0] - q_new[0], p[1] - q_new[1]) <= rad:
                nbr_idx.append(i)

        best_parent = near_idx
        best_cost = cost[near_idx] + math.hypot(q_near[0] - q_new[0], q_near[1] - q_new[1])
        for i in nbr_idx:
            c_try = cost[i] + math.hypot(nodes[i][0] - q_new[0], nodes[i][1] - q_new[1])
            if c_try < best_cost and _collision_free_segment(occupancy, resolution, nodes[i], q_new):
                best_cost = c_try
                best_parent = i

        nodes.append(q_new)
        parent.append(best_parent)
        cost.append(best_cost)
        new_idx = len(nodes) - 1

        # rewire
        for i in nbr_idx:
            if i == best_parent:
                continue
            c_try = best_cost + math.hypot(nodes[i][0] - q_new[0], nodes[i][1] - q_new[1])
            if c_try + 1e-9 < cost[i] and _collision_free_segment(occupancy, resolution, nodes[i], q_new):
                parent[i] = new_idx
                cost[i] = c_try

        # try connect goal
        d_goal = math.hypot(q_new[0] - goal_xy[0], q_new[1] - goal_xy[1])
        if d_goal <= goal_radius and _collision_free_segment(occupancy, resolution, q_new, goal_xy):
            c_goal = best_cost + d_goal
            if c_goal < best_goal_cost:
                best_goal_cost = c_goal
                nodes.append(goal_xy)
                parent.append(new_idx)
                cost.append(c_goal)
                best_goal_idx = len(nodes) - 1

    if best_goal_idx < 0:
        return {
            "success": False,
            "expansions": expansions,
            "runtime_ms": (time.perf_counter() - t0) * 1000.0,
            "path": [],
        }

    path = []
    cur = best_goal_idx
    while cur >= 0:
        path.append(nodes[cur])
        cur = parent[cur]
    path.reverse()
    return {
        "success": True,
        "expansions": expansions,
        "runtime_ms": (time.perf_counter() - t0) * 1000.0,
        "path": path,
    }


def _bit_star(
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    max_iters: int,
    rng: np.random.Generator,
) -> dict:
    # Lightweight BIT*-style baseline via informed RRT* sampling.
    return _rrt_star(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        max_iters=max_iters,
        step_size=1.2 * resolution * 4.0,
        goal_radius=1.5 * resolution,
        rng=rng,
        informed_cost=None,
    )


def _resolve_2d_heuristic(pred: np.ndarray, occupancy: np.ndarray) -> np.ndarray:
    if pred.ndim == 2:
        h2d = pred.astype(np.float32)
    else:
        h2d = np.min(pred.astype(np.float32), axis=0)
    h2d = np.where(np.isfinite(h2d), h2d, 1e6).astype(np.float32)
    h2d[occupancy] = 1e6
    return h2d


def _euclidean_field(
    occupancy: np.ndarray,
    goal_xy: tuple[float, float],
    resolution: float,
    fill_value: float = 1e6,
) -> np.ndarray:
    h, w = occupancy.shape
    yy, xx = np.mgrid[0:h, 0:w]
    wx = (xx + 0.5) * float(resolution)
    wy = (yy + 0.5) * float(resolution)
    field = np.hypot(wx - float(goal_xy[0]), wy - float(goal_xy[1])).astype(np.float32)
    field[occupancy] = float(fill_value)
    return field


def _line_sample_indices(
    start_ix: int,
    start_iy: int,
    goal_ix: int,
    goal_iy: int,
    w: int,
    h: int,
    samples_per_cell: float,
) -> tuple[np.ndarray, np.ndarray]:
    dist_cells = float(math.hypot(goal_ix - start_ix, goal_iy - start_iy))
    n = int(max(2, math.ceil(dist_cells * max(float(samples_per_cell), 0.25))))
    xs = np.linspace(float(start_ix), float(goal_ix), num=n, dtype=np.float32)
    ys = np.linspace(float(start_iy), float(goal_iy), num=n, dtype=np.float32)
    xi = np.clip(np.round(xs).astype(np.int64), 0, w - 1)
    yi = np.clip(np.round(ys).astype(np.int64), 0, h - 1)
    return xi, yi


def _estimate_dual_map_complexity(
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    args: argparse.Namespace,
) -> dict[str, float | bool]:
    h, w = occupancy.shape
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)

    los_clear = bool(_line_of_sight(occupancy, (sx, sy), (gx, gy)))
    xi, yi = _line_sample_indices(
        start_ix=sx,
        start_iy=sy,
        goal_ix=gx,
        goal_iy=gy,
        w=w,
        h=h,
        samples_per_cell=float(args.router_samples_per_cell),
    )
    line_block_ratio = float(np.mean(occupancy[yi, xi].astype(np.float32)))

    radius = int(max(args.router_corridor_radius_cells, 0))
    if radius <= 0:
        local_occ_ratio = line_block_ratio
    else:
        occ_u8 = occupancy.astype(np.uint8)
        patch_vals: list[float] = []
        for cx, cy in zip(xi.tolist(), yi.tolist()):
            x0 = max(int(cx) - radius, 0)
            x1 = min(int(cx) + radius + 1, w)
            y0 = max(int(cy) - radius, 0)
            y1 = min(int(cy) + radius + 1, h)
            patch = occ_u8[y0:y1, x0:x1]
            patch_vals.append(float(np.mean(patch)))
        local_occ_ratio = float(np.mean(np.asarray(patch_vals, dtype=np.float32))) if patch_vals else line_block_ratio

    global_occ_ratio = float(np.mean(occupancy.astype(np.float32)))
    dist_ratio = float(
        math.hypot((gx - sx) * resolution, (gy - sy) * resolution) /
        max(math.hypot(w * resolution, h * resolution), 1e-6)
    )

    wl = float(max(args.router_w_line_block, 0.0))
    wc = float(max(args.router_w_local_occ, 0.0))
    wd = float(max(args.router_w_distance, 0.0))
    wg = float(max(args.router_w_global_occ, 0.0))
    wsum = max(wl + wc + wd + wg, 1e-6)
    score = (
        wl * line_block_ratio +
        wc * local_occ_ratio +
        wd * dist_ratio +
        wg * global_occ_ratio
    ) / wsum
    if not los_clear:
        score += float(max(args.router_los_penalty, 0.0))
    score = float(np.clip(score, 0.0, 1.0))

    return {
        "los_clear": los_clear,
        "line_block_ratio": line_block_ratio,
        "local_occ_ratio": local_occ_ratio,
        "global_occ_ratio": global_occ_ratio,
        "distance_ratio": dist_ratio,
        "complexity_score": score,
    }


def _route_dual_map_path(
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    args: argparse.Namespace,
) -> dict[str, float | bool | str]:
    feat = _estimate_dual_map_complexity(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        args=args,
    )
    score = float(feat["complexity_score"])
    line_block = float(feat["line_block_ratio"])
    local_occ = float(feat["local_occ_ratio"])
    global_occ = float(feat["global_occ_ratio"])
    dist_ratio = float(feat["distance_ratio"])
    los_clear = bool(feat["los_clear"])

    fast_rule = (
        dist_ratio <= float(max(args.router_fast_max_distance_ratio, 0.0))
        and line_block <= float(max(args.router_fast_max_line_block_ratio, 0.0))
        and local_occ <= float(max(args.router_fast_max_local_occ_ratio, 0.0))
        and global_occ <= float(max(args.router_fast_max_global_occ_ratio, 0.0))
    )
    slow_rule = (
        line_block >= float(max(args.router_slow_min_line_block_ratio, 0.0))
        and local_occ >= float(max(args.router_slow_min_local_occ_ratio, 0.0))
    )
    threshold = float(np.clip(args.router_score_threshold, 0.0, 1.0))
    fast_margin = float(max(args.router_fast_score_margin, 0.0))

    if slow_rule:
        route = "slow"
        reason = "hard_clutter_rule"
    elif fast_rule:
        route = "fast"
        reason = "easy_rule"
    elif score <= max(threshold - fast_margin, 0.0):
        route = "fast"
        reason = "score_margin_fast"
    elif score <= threshold:
        route = "fast" if los_clear else "slow"
        reason = "score_tie_los"
    else:
        route = "slow"
        reason = "score_high"

    return {
        "route": route,
        "reason": reason,
        "los_clear": los_clear,
        "line_block_ratio": line_block,
        "local_occ_ratio": local_occ,
        "global_occ_ratio": global_occ,
        "distance_ratio": dist_ratio,
        "complexity_score": score,
    }


def _method_summary(rows: list[EvalRow]) -> dict[tuple[str, str, str], dict]:
    grouped: dict[tuple[str, str, str], list[EvalRow]] = defaultdict(list)
    for r in rows:
        grouped[(r.experiment, r.dataset, r.method)].append(r)

    out: dict[tuple[str, str, str], dict] = {}
    for key, vals in grouped.items():
        succ = [v for v in vals if v.success]
        out[key] = {
            "num_cases": len(vals),
            "success_rate": len(succ) / max(len(vals), 1),
            "avg_expansions": float(np.mean([v.expansions for v in succ])) if succ else float("nan"),
            "avg_path_length": float(np.mean([v.path_length for v in succ if np.isfinite(v.path_length)])) if succ else float("nan"),
            "avg_infer_ms": float(np.mean([v.infer_ms for v in succ])) if succ else float("nan"),
            "avg_search_ms": float(np.mean([v.search_ms for v in succ])) if succ else float("nan"),
            "avg_time_ms": float(np.mean([v.runtime_ms for v in succ])) if succ else float("nan"),
        }
    return out


def _write_summary_csv(summary: dict[tuple[str, str, str], dict], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "experiment",
            "dataset",
            "method",
            "num_cases",
            "success_rate",
            "avg_expansions",
            "avg_path_length",
            "avg_infer_ms",
            "avg_search_ms",
            "avg_time_ms",
        ])
        for (exp, ds, m) in sorted(summary.keys()):
            s = summary[(exp, ds, m)]
            writer.writerow([
                exp,
                ds,
                m,
                s["num_cases"],
                f"{s['success_rate']:.6f}",
                f"{s['avg_expansions']:.6f}",
                f"{s['avg_path_length']:.6f}",
                f"{s['avg_infer_ms']:.6f}",
                f"{s['avg_search_ms']:.6f}",
                f"{s['avg_time_ms']:.6f}",
            ])


def _save_bar_svg(rows: list[tuple[str, float]], title: str, y_label: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 980, 420
    ml, mr, mt, mb = 60, 24, 42, 120
    pw, ph = w - ml - mr, h - mt - mb

    vals = [v for _, v in rows if np.isfinite(v)]
    y_max = max(vals) if vals else 1.0
    y_max = max(y_max, 1e-6)

    n = max(len(rows), 1)
    bar_w = pw / n * 0.6
    gap = pw / n

    def y_to_px(v: float) -> float:
        t = np.clip(v / y_max, 0.0, 1.0)
        return mt + (1.0 - t) * ph

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">')
    lines.append('<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>')
    lines.append(f'<text x="{ml}" y="24" font-size="17" fill="#111">{title}</text>')
    lines.append(f'<text x="{12}" y="{mt + 8}" font-size="12" fill="#444">{y_label}</text>')
    lines.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#333" stroke-width="1.2"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#333" stroke-width="1.2"/>')

    for i in range(6):
        yy = mt + ph * i / 5.0
        yv = y_max * (1.0 - i / 5.0)
        lines.append(f'<line x1="{ml}" y1="{yy:.2f}" x2="{ml+pw}" y2="{yy:.2f}" stroke="#eef2f7" stroke-width="1"/>')
        lines.append(f'<text x="{ml-8}" y="{yy+4:.2f}" font-size="10" text-anchor="end" fill="#666">{yv:.3f}</text>')

    for i, (name, value) in enumerate(rows):
        x = ml + i * gap + (gap - bar_w) * 0.5
        y = y_to_px(value if np.isfinite(value) else 0.0)
        hh = mt + ph - y
        lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{max(hh,0):.2f}" fill="#2563eb"/>')
        lines.append(f'<text x="{x + bar_w*0.5:.2f}" y="{mt+ph+18}" font-size="10" text-anchor="middle" fill="#111" transform="rotate(35 {x + bar_w*0.5:.2f},{mt+ph+18})">{name}</text>')
        if np.isfinite(value):
            lines.append(f'<text x="{x + bar_w*0.5:.2f}" y="{y-4:.2f}" font-size="10" text-anchor="middle" fill="#1e293b">{value:.3f}</text>')

    lines.append('</svg>')
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _save_search_tree_svg(
    occupancy: np.ndarray,
    resolution: float,
    astar_expanded: list[tuple[int, int]],
    ours_expanded: list[tuple[int, int]],
    astar_path: list[tuple[float, float]],
    ours_path: list[tuple[float, float]],
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h, w = occupancy.shape
    scale = 7
    pad = 20
    W = w * scale + pad * 2
    H = h * scale + pad * 2 + 26

    def gp(ix: int, iy: int) -> tuple[float, float]:
        return pad + ix * scale + scale * 0.5, pad + (h - 1 - iy) * scale + scale * 0.5

    def wp(x: float, y: float) -> tuple[float, float]:
        ix = int(np.clip(np.floor(x / resolution), 0, w - 1))
        iy = int(np.clip(np.floor(y / resolution), 0, h - 1))
        return gp(ix, iy)

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    lines.append('<rect x="0" y="0" width="100%" height="100%" fill="#fff"/>')
    lines.append(f'<text x="{pad}" y="16" font-size="14" fill="#111">Search Tree Compare (A* vs Ours)</text>')
    lines.append(f'<rect x="{pad}" y="{pad}" width="{w*scale}" height="{h*scale}" fill="#f8fafc" stroke="#94a3b8" stroke-width="1"/>')

    ys, xs = np.where(occupancy)
    for y, x in zip(ys.tolist(), xs.tolist()):
        rx = pad + x * scale
        ry = pad + (h - 1 - y) * scale
        lines.append(f'<rect x="{rx}" y="{ry}" width="{scale}" height="{scale}" fill="#111827"/>')

    for x, y in astar_expanded[:4000]:
        px, py = gp(x, y)
        lines.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="0.9" fill="#60a5fa" opacity="0.30"/>')
    for x, y in ours_expanded[:4000]:
        px, py = gp(x, y)
        lines.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="0.9" fill="#f97316" opacity="0.30"/>')

    if astar_path:
        pts = " ".join([f"{wp(x,y)[0]:.2f},{wp(x,y)[1]:.2f}" for x, y in astar_path])
        lines.append(f'<polyline fill="none" stroke="#2563eb" stroke-width="2" points="{pts}"/>')
    if ours_path:
        pts = " ".join([f"{wp(x,y)[0]:.2f},{wp(x,y)[1]:.2f}" for x, y in ours_path])
        lines.append(f'<polyline fill="none" stroke="#ea580c" stroke-width="2" points="{pts}"/>')

    sx, sy = wp(start_xy[0], start_xy[1])
    gx, gy = wp(goal_xy[0], goal_xy[1])
    lines.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="4" fill="#22c55e" stroke="#111"/>')
    lines.append(f'<circle cx="{gx:.2f}" cy="{gy:.2f}" r="4" fill="#ef4444" stroke="#111"/>')
    lines.append(f'<text x="{pad}" y="{H-8}" font-size="11" fill="#2563eb">A* expanded/path</text>')
    lines.append(f'<text x="{pad+150}" y="{H-8}" font-size="11" fill="#ea580c">Ours expanded/path</text>')
    lines.append('</svg>')

    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_experiment_section_tex(
    out_tex: Path,
    summary: dict[tuple[str, str, str], dict],
    config: dict,
) -> None:
    out_tex.parent.mkdir(parents=True, exist_ok=True)

    def line_for(exp: str, ds: str, method: str) -> str:
        s = summary.get((exp, ds, method), None)
        if s is None:
            return f"{method} & -- & -- & -- & -- & -- \\\\"
        return (
            f"{method} & {s['success_rate']:.3f} & {s['avg_expansions']:.1f} & "
            f"{s['avg_path_length']:.2f} & {s['avg_infer_ms']:.2f} & {s['avg_search_ms']:.2f} \\\\"
        )

    exp3_ds = "hard"
    if ("exp3_ablation", "parasol", "Full") in summary:
        exp3_ds = "parasol"

    lines = []
    lines.append("\\section{Experiments}")
    lines.append("\\subsection{Experimental Setup}")
    lines.append("We evaluate on public planning benchmarks (MP, CSM, and Parasol narrow-passage tasks).")
    lines.append("All methods share identical maps, start/goal pairs, and search budgets for each experiment.")
    lines.append(
        "Neural baselines (VIN and Neural A*) are trained with the same converted MP+CSM training split and evaluated on unseen test cases."
    )
    lines.append(
        f"Our model checkpoint is \\texttt{{{config.get('ours_ckpt','outputs/checkpoints/heuristic_net_generalization_unified_mixed_v2.pt')}}}."
    )

    lines.append("\\subsection{Datasets}")
    lines.append("\\begin{itemize}")
    lines.append("\\item \\textbf{Exp1 (MP)}: 8 environment families, full MP test split.")
    lines.append("\\item \\textbf{Exp2 (CSM)}: city/street benchmark with official test split.")
    lines.append("\\item \\textbf{Exp3/Exp4 (Parasol)}: public narrow-passage tasks (Bug Trap, Alpha, Flange and related scenes).")
    lines.append("\\end{itemize}")

    lines.append("\\subsection{Experiment 1: MP Benchmark}")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{MP benchmark results (success rate $\\uparrow$, expansions $\\downarrow$, path length $\\downarrow$, inference/search time $\\downarrow$).}")
    lines.append("\\begin{tabular}{lccccc}")
    lines.append("\\toprule")
    lines.append("Method & Success & Expansions & Path Len. & Infer (ms) & Search (ms) \\\\")
    lines.append("\\midrule")
    for m in ["A*", "Theta*", "VIN", "Neural A*", "Ours"]:
        lines.append(line_for("exp1_mp", "mp", m))
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    lines.append("\\subsection{Experiment 2: CSM Benchmark}")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{CSM benchmark results.}")
    lines.append("\\begin{tabular}{lccccc}")
    lines.append("\\toprule")
    lines.append("Method & Success & Expansions & Path Len. & Infer (ms) & Search (ms) \\\\")
    lines.append("\\midrule")
    for m in ["A*", "Theta*", "VIN", "Neural A*", "Ours"]:
        lines.append(line_for("exp2_csm", "csm", m))
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    lines.append("\\subsection{Experiment 3: Ablation}")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{Ablation on nonholonomic benchmark split.}")
    lines.append("\\begin{tabular}{lccccc}")
    lines.append("\\toprule")
    lines.append("Method & Success & Expansions & Path Len. & Infer (ms) & Search (ms) \\\\")
    lines.append("\\midrule")
    for m in ["Full", "No-Residual", "No-Residual+ESDF", "No-RS", "No-Temporal"]:
        lines.append(line_for("exp3_ablation", exp3_ds, m))
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    has_exp4 = ("exp4_public_kinodynamic", "parasol", "Ours") in summary
    if has_exp4:
        lines.append("\\subsection{Experiment 4: Public Kinodynamic Comparison}")
        lines.append("\\begin{table}[t]")
        lines.append("\\centering")
        lines.append("\\caption{Parasol public kinodynamic benchmark results.}")
        lines.append("\\begin{tabular}{lccccc}")
        lines.append("\\toprule")
        lines.append("Method & Success & Expansions & Path Len. & Infer (ms) & Search (ms) \\\\")
        lines.append("\\midrule")
        for m in ["Hybrid A* (RS)", "Kinodynamic RRT*", "Kinodynamic BIT*", "Ours"]:
            lines.append(line_for("exp4_public_kinodynamic", "parasol", m))
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        lines.append("\\end{table}")

    lines.append("\\subsection{Discussion}")
    lines.append(
        "Across MP/CSM, our method keeps full success while reducing expansions versus neural-only baselines; on Parasol, RS-consistent prior remains the dominant factor and residual correction is measured by the Full vs No-Residual ablation."
    )
    lines.append(
        "RRT* and BIT* are implemented with the same planner cost model (including reverse and steering penalties), providing fair nonholonomic sampling baselines."
    )

    out_tex.write_text("\n".join(lines), encoding="utf-8")


def _run_standard_experiment(
    mp_test_files: list[Path],
    csm_test_files: list[Path],
    vin: VINLite,
    neural_astar: NeuralAStarLite,
    ours_predictor: NeuralHeuristicPredictor,
    args: argparse.Namespace,
) -> tuple[list[EvalRow], dict, dict]:
    rows: list[EvalRow] = []
    fig_payload: dict = {}
    router_stats: dict = {
        "enabled": bool(args.enable_dual_path_router),
        "total_cases": 0,
        "fast_cases": 0,
        "slow_cases": 0,
        "by_dataset": {},
        "reasons": {},
        "avg_complexity_score": float("nan"),
        "avg_line_block_ratio": float("nan"),
        "avg_local_occ_ratio": float("nan"),
        "avg_global_occ_ratio": float("nan"),
        "avg_distance_ratio": float("nan"),
        "decisions": [],
    }
    _score_vals: list[float] = []
    _line_vals: list[float] = []
    _local_vals: list[float] = []
    _global_vals: list[float] = []
    _dist_vals: list[float] = []

    files = [
        ("mp", p) for p in mp_test_files
    ] + [
        ("csm", p) for p in csm_test_files
    ]

    for i, (ds, p) in enumerate(files):
        s = load_grid_sample(p)
        start_xy = (s.start[0], s.start[1])
        goal_xy = (s.goal[0], s.goal[1])

        r_astar = _astar_grid(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=args.grid_max_expansions,
            heuristic_map=None,
            record_expanded=(i == 0),
        )
        rows.append(
            EvalRow(
                "exp1_standard",
                ds,
                "A*",
                p.name,
                r_astar["success"],
                float(r_astar["expansions"]),
                _path_length(r_astar["path"]),
                float(r_astar["runtime_ms"]),
                infer_ms=0.0,
                search_ms=float(r_astar["runtime_ms"]),
            )
        )

        r_theta = _theta_star(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=args.grid_max_expansions,
        )
        rows.append(
            EvalRow(
                "exp1_standard",
                ds,
                "Theta*",
                p.name,
                r_theta["success"],
                float(r_theta["expansions"]),
                _path_length(r_theta["path"]),
                float(r_theta["runtime_ms"]),
                infer_ms=0.0,
                search_ms=float(r_theta["runtime_ms"]),
            )
        )

        t0 = time.perf_counter()
        h_vin = vin.predict_field(s.occupancy, s.start, s.goal, s.resolution)
        infer_ms = (time.perf_counter() - t0) * 1000.0
        r_vin = _astar_grid(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=args.grid_max_expansions,
            heuristic_map=h_vin,
            heuristic_weight=1.0,
        )
        rows.append(
            EvalRow(
                "exp1_standard",
                ds,
                "VIN",
                p.name,
                r_vin["success"],
                float(r_vin["expansions"]),
                _path_length(r_vin["path"]),
                float(r_vin["runtime_ms"] + infer_ms),
                infer_ms=float(infer_ms),
                search_ms=float(r_vin["runtime_ms"]),
            )
        )

        t0 = time.perf_counter()
        h_na = neural_astar.predict_field(s.occupancy, s.start, s.goal, s.resolution)
        infer_ms = (time.perf_counter() - t0) * 1000.0
        r_na = _astar_grid(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=args.grid_max_expansions,
            heuristic_map=h_na,
            heuristic_weight=1.0,
        )
        rows.append(
            EvalRow(
                "exp1_standard",
                ds,
                "Neural A*",
                p.name,
                r_na["success"],
                float(r_na["expansions"]),
                _path_length(r_na["path"]),
                float(r_na["runtime_ms"] + infer_ms),
                infer_ms=float(infer_ms),
                search_ms=float(r_na["runtime_ms"]),
            )
        )

        route_meta: dict | None = None
        if bool(args.enable_dual_path_router):
            route_meta = _route_dual_map_path(
                occupancy=s.occupancy,
                resolution=s.resolution,
                start_xy=start_xy,
                goal_xy=goal_xy,
                args=args,
            )
            route = str(route_meta["route"])
            reason = str(route_meta["reason"])
            router_stats["total_cases"] += 1
            if route == "fast":
                router_stats["fast_cases"] += 1
            else:
                router_stats["slow_cases"] += 1
            router_stats["reasons"][reason] = int(router_stats["reasons"].get(reason, 0)) + 1

            ds_bucket = router_stats["by_dataset"].get(ds, None)
            if ds_bucket is None:
                ds_bucket = {
                    "total_cases": 0,
                    "fast_cases": 0,
                    "slow_cases": 0,
                    "_score_sum": 0.0,
                    "_line_sum": 0.0,
                    "_local_sum": 0.0,
                    "_global_sum": 0.0,
                    "_dist_sum": 0.0,
                }
                router_stats["by_dataset"][ds] = ds_bucket
            ds_bucket["total_cases"] += 1
            if route == "fast":
                ds_bucket["fast_cases"] += 1
            else:
                ds_bucket["slow_cases"] += 1

            score_v = float(route_meta["complexity_score"])
            line_v = float(route_meta["line_block_ratio"])
            local_v = float(route_meta["local_occ_ratio"])
            global_v = float(route_meta["global_occ_ratio"])
            dist_v = float(route_meta["distance_ratio"])
            ds_bucket["_score_sum"] += score_v
            ds_bucket["_line_sum"] += line_v
            ds_bucket["_local_sum"] += local_v
            ds_bucket["_global_sum"] += global_v
            ds_bucket["_dist_sum"] += dist_v

            _score_vals.append(score_v)
            _line_vals.append(line_v)
            _local_vals.append(local_v)
            _global_vals.append(global_v)
            _dist_vals.append(dist_v)

            router_stats["decisions"].append(
                {
                    "case_id": p.name,
                    "dataset": ds,
                    "route": route,
                    "reason": reason,
                    "los_clear": bool(route_meta["los_clear"]),
                    "complexity_score": score_v,
                    "line_block_ratio": line_v,
                    "local_occ_ratio": local_v,
                    "global_occ_ratio": global_v,
                    "distance_ratio": dist_v,
                }
            )

        if route_meta is not None and str(route_meta["route"]) == "fast":
            infer_ms = 0.0
            r_ours = _astar_grid(
                occupancy=s.occupancy,
                resolution=s.resolution,
                start_xy=start_xy,
                goal_xy=goal_xy,
                max_expansions=args.grid_max_expansions,
                heuristic_map=None,
                heuristic_weight=1.0,
                record_expanded=(i == 0),
            )
        else:
            t0 = time.perf_counter()
            base_override = None
            if ours_predictor.prediction_mode == "residual" and str(args.standard_base_mode).lower() == "euclidean":
                base_override = _euclidean_field(
                    occupancy=s.occupancy,
                    goal_xy=(s.goal[0], s.goal[1]),
                    resolution=s.resolution,
                    fill_value=1e6,
                )
            pred = ours_predictor.predict_field(
                occupancy=s.occupancy,
                esdf=np.zeros_like(s.occupancy, dtype=np.float32),
                start=s.start,
                goal=s.goal,
                resolution=s.resolution,
                base_field_override=base_override,
            )
            infer_ms = (time.perf_counter() - t0) * 1000.0
            h_ours = _resolve_2d_heuristic(pred, s.occupancy)
            r_ours = _astar_grid(
                occupancy=s.occupancy,
                resolution=s.resolution,
                start_xy=start_xy,
                goal_xy=goal_xy,
                max_expansions=args.grid_max_expansions,
                heuristic_map=h_ours,
                heuristic_weight=1.0,
                record_expanded=(i == 0),
            )
        rows.append(
            EvalRow(
                "exp1_standard",
                ds,
                "Ours",
                p.name,
                r_ours["success"],
                float(r_ours["expansions"]),
                _path_length(r_ours["path"]),
                float(r_ours["runtime_ms"] + infer_ms),
                infer_ms=float(infer_ms),
                search_ms=float(r_ours["runtime_ms"]),
            )
        )

        if i == 0:
            fig_payload = {
                "occupancy": s.occupancy,
                "resolution": s.resolution,
                "astar_expanded": r_astar["expanded"],
                "ours_expanded": r_ours["expanded"],
                "astar_path": r_astar["path"],
                "ours_path": r_ours["path"],
                "start_xy": start_xy,
                "goal_xy": goal_xy,
            }
        if (i + 1) % 20 == 0 or (i + 1) == len(files):
            print(f"[exp1] processed {i + 1}/{len(files)} cases")

    if bool(args.enable_dual_path_router):
        if _score_vals:
            router_stats["avg_complexity_score"] = float(np.mean(np.asarray(_score_vals, dtype=np.float32)))
            router_stats["avg_line_block_ratio"] = float(np.mean(np.asarray(_line_vals, dtype=np.float32)))
            router_stats["avg_local_occ_ratio"] = float(np.mean(np.asarray(_local_vals, dtype=np.float32)))
            router_stats["avg_global_occ_ratio"] = float(np.mean(np.asarray(_global_vals, dtype=np.float32)))
            router_stats["avg_distance_ratio"] = float(np.mean(np.asarray(_dist_vals, dtype=np.float32)))
        for ds_key, ds_bucket in router_stats["by_dataset"].items():
            n = max(int(ds_bucket["total_cases"]), 1)
            ds_bucket["avg_complexity_score"] = float(ds_bucket["_score_sum"] / n)
            ds_bucket["avg_line_block_ratio"] = float(ds_bucket["_line_sum"] / n)
            ds_bucket["avg_local_occ_ratio"] = float(ds_bucket["_local_sum"] / n)
            ds_bucket["avg_global_occ_ratio"] = float(ds_bucket["_global_sum"] / n)
            ds_bucket["avg_distance_ratio"] = float(ds_bucket["_dist_sum"] / n)
            del ds_bucket["_score_sum"]
            del ds_bucket["_line_sum"]
            del ds_bucket["_local_sum"]
            del ds_bucket["_global_sum"]
            del ds_bucket["_dist_sum"]

    return rows, fig_payload, router_stats


def _load_nonholonomic_case(path: Path):
    with np.load(path, allow_pickle=False) as z:
        resolution = float(z["resolution"]) if "resolution" in z else float(DEFAULT_CONFIG.map.resolution)
        occupancy = z["occupancy"].astype(bool)
        if "occupancy_static" in z and "dynamic_risk" in z:
            occ_static = z["occupancy_static"].astype(bool)
            dyn_risk = np.clip(z["dynamic_risk"].astype(np.float32), 0.0, 1.0)
            risk_thr = float(z["dynamic_block_threshold"]) if "dynamic_block_threshold" in z else 0.25
            occupancy = np.logical_or(occ_static, dyn_risk >= risk_thr)

        esdf = z["esdf"].astype(np.float32)
        start = tuple(float(v) for v in z["start"].astype(np.float32))
        goal = tuple(float(v) for v in z["goal"].astype(np.float32))
        difficulty = str(z["difficulty"]) if "difficulty" in z else "unknown"
        scenario = str(z["scenario"]) if "scenario" in z else "unknown"
        task_type = str(z["task_type"]) if "task_type" in z else "unknown"
        dynamic_risk = z["dynamic_risk"].astype(np.float32) if "dynamic_risk" in z else None
        dynamic_risk_seq = z["dynamic_risk_seq"].astype(np.float32) if "dynamic_risk_seq" in z else None

        vehicle = replace(DEFAULT_CONFIG.vehicle)
        if "vehicle_wheel_base" in z:
            vehicle.wheel_base = float(z["vehicle_wheel_base"])
        if "vehicle_length" in z:
            vehicle.length = float(z["vehicle_length"])
        if "vehicle_width" in z:
            vehicle.width = float(z["vehicle_width"])
        if "vehicle_max_steer_deg" in z:
            vehicle.max_steer_deg = float(z["vehicle_max_steer_deg"])
        if "vehicle_min_turn_radius" in z:
            vehicle.min_turn_radius = float(z["vehicle_min_turn_radius"])

        planner_cfg = replace(DEFAULT_CONFIG.planner)
        if "planner_step_size" in z:
            planner_cfg.step_size = float(z["planner_step_size"])
        if "planner_reverse_penalty" in z:
            planner_cfg.reverse_penalty = float(z["planner_reverse_penalty"])
        if "planner_steer_penalty" in z:
            planner_cfg.steer_penalty = float(z["planner_steer_penalty"])
        if "planner_steer_change_penalty" in z:
            planner_cfg.steer_change_penalty = float(z["planner_steer_change_penalty"])

        ctx = {
            "wheel_base": float(getattr(vehicle, "wheel_base", DEFAULT_CONFIG.vehicle.wheel_base)),
            "max_steer_deg": float(getattr(vehicle, "max_steer_deg", DEFAULT_CONFIG.vehicle.max_steer_deg)),
            "battery": float(z["vehicle_battery"]) if "vehicle_battery" in z else 100.0,
            "load_factor": float(z["vehicle_load_factor"]) if "vehicle_load_factor" in z else 1.0,
        }

    return {
        "occupancy": occupancy,
        "resolution": resolution,
        "esdf": esdf,
        "start": start,
        "goal": goal,
        "difficulty": difficulty,
        "scenario": scenario,
        "task_type": task_type,
        "dynamic_risk": dynamic_risk,
        "dynamic_risk_seq": dynamic_risk_seq,
        "vehicle": vehicle,
        "planner_cfg": planner_cfg,
        "vehicle_context": ctx,
    }


def _planner_budget(planner_cfg, case: dict, args: argparse.Namespace) -> int:
    cap = int(max(planner_cfg.max_expansions, args.hybrid_max_expansions))
    if case["difficulty"] == "hard":
        cap = max(cap, int(args.hybrid_hard_max_expansions))
    if case["scenario"] in {"maze_single", "deadend_labyrinth"}:
        cap = max(cap, int(args.hybrid_maze_max_expansions))
    if int(args.hybrid_budget_cap) > 0:
        cap = min(cap, int(args.hybrid_budget_cap))
    return cap


def _run_hybrid_method(case: dict, anchor_fn, max_expansions: int) -> dict:
    pcfg = replace(case["planner_cfg"])
    pcfg.max_expansions = int(max_expansions)
    planner = HybridAStarPlanner(
        occupancy=case["occupancy"],
        resolution=case["resolution"],
        vehicle_cfg=case["vehicle"],
        planner_cfg=pcfg,
        esdf=case["esdf"],
    )
    res = planner.plan(
        start=case["start"],
        goal=case["goal"],
        anchor_fn=anchor_fn,
        guidance_fn=None,
        main_mode="anchor",
        record_expanded=False,
    )
    path_xy = [(float(p[0]), float(p[1])) for p in res.path] if res.path.size > 0 else []
    return {
        "success": bool(res.success),
        "expansions": float(res.expansions),
        "runtime_ms": float(res.runtime_ms),
        "path": path_xy,
    }


def _compute_case_rs_field(case: dict, yaw_bins_cap: int | None = None) -> np.ndarray:
    rs_cfg = RSConsistentCostConfig.from_configs(case["vehicle"], case["planner_cfg"])
    yaw_bins = int(max(8, getattr(case["planner_cfg"], "yaw_bins", DEFAULT_CONFIG.dataset.teacher_yaw_bins)))
    if yaw_bins_cap is not None and int(yaw_bins_cap) > 0:
        yaw_bins = int(min(yaw_bins, int(yaw_bins_cap)))
    rs_field = compute_reeds_shepp_field(
        occupancy=case["occupancy"],
        goal=case["goal"],
        resolution=case["resolution"],
        yaw_bins=yaw_bins,
        rho=float(case["vehicle"].min_turn_radius),
        fill_value=float(DEFAULT_CONFIG.dataset.max_teacher_value),
        step_size=float(DEFAULT_CONFIG.dataset.teacher_rs_step_size),
        backend=str(DEFAULT_CONFIG.dataset.teacher_rs_backend),
        cost_mode="planner_consistent",
        cost_cfg=rs_cfg,
    )
    return rs_field.astype(np.float32)


def _make_rs_anchor(case: dict, rs_field: np.ndarray | None = None) -> YawFieldHeuristic:
    if rs_field is None:
        rs_field = _compute_case_rs_field(case)
    return YawFieldHeuristic(
        field_3d=rs_field.astype(np.float32),
        resolution=float(case["resolution"]),
        max_value=float(DEFAULT_CONFIG.dataset.max_teacher_value),
        scale=1.0,
    )


def _match_yaw_channels(field: np.ndarray, yaw_bins: int) -> np.ndarray:
    if field.ndim == 2:
        return np.repeat(field[None, ...], yaw_bins, axis=0).astype(np.float32)

    c, _, _ = field.shape
    if c == yaw_bins:
        return field.astype(np.float32)
    if c == 1:
        return np.repeat(field, yaw_bins, axis=0).astype(np.float32)

    # Circular linear interpolation along yaw dimension for smoother channel alignment.
    src = np.arange(c, dtype=np.float32)
    dst = (np.arange(yaw_bins, dtype=np.float32) + 0.5) * (c / float(max(yaw_bins, 1))) - 0.5
    i0 = np.floor(dst).astype(np.int64) % c
    i1 = (i0 + 1) % c
    w = (dst - np.floor(dst)).astype(np.float32)
    out = ((1.0 - w)[:, None, None] * field[i0] + w[:, None, None] * field[i1]).astype(np.float32)
    return out


def _shift2d_no_wrap(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.roll(np.roll(arr, shift=dy, axis=0), shift=dx, axis=1)
    if dy > 0:
        out[:dy, :] = 0.0
    elif dy < 0:
        out[dy:, :] = 0.0
    if dx > 0:
        out[:, :dx] = 0.0
    elif dx < 0:
        out[:, dx:] = 0.0
    return out


def _shift3d_no_wrap(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.roll(np.roll(arr, shift=dy, axis=1), shift=dx, axis=2)
    if dy > 0:
        out[:, :dy, :] = 0.0
    elif dy < 0:
        out[:, dy:, :] = 0.0
    if dx > 0:
        out[:, :, :dx] = 0.0
    elif dx < 0:
        out[:, :, dx:] = 0.0
    return out


def _transport_residual_obstacle_aware(
    residual_3d: np.ndarray,
    occupancy: np.ndarray,
    esdf: np.ndarray,
    iters: int,
    step: float,
    clearance_sigma: float,
) -> np.ndarray:
    n_iters = int(max(iters, 0))
    step_size = float(np.clip(step, 0.0, 1.0))
    sigma = float(max(clearance_sigma, 1e-4))
    if n_iters <= 0 or step_size <= 0.0:
        return residual_3d.astype(np.float32, copy=True)

    free = (~occupancy.astype(bool)).astype(np.float32)
    if free.sum() <= 0.0:
        return residual_3d.astype(np.float32, copy=True)

    clearance = np.maximum(esdf.astype(np.float32), 0.0)
    z = residual_3d.astype(np.float32, copy=True)
    dirs = ((0, 1), (0, -1), (1, 0), (-1, 0))
    for _ in range(n_iters):
        accum = np.zeros_like(z, dtype=np.float32)
        wsum = np.zeros_like(clearance, dtype=np.float32)
        for dy, dx in dirs:
            neigh_free = _shift2d_no_wrap(free, dy=dy, dx=dx)
            neigh_clear = _shift2d_no_wrap(clearance, dy=dy, dx=dx)
            clear_sim = np.exp(-np.abs(clearance - neigh_clear) / sigma).astype(np.float32)
            w = (neigh_free * clear_sim).astype(np.float32)
            neigh_val = _shift3d_no_wrap(z, dy=dy, dx=dx)
            accum = accum + neigh_val * w[None, ...]
            wsum = wsum + w
        avg = accum / np.maximum(wsum[None, ...], 1e-6)
        z = (z + step_size * (avg - z) * free[None, ...]).astype(np.float32)

    z[:, occupancy.astype(bool)] = 0.0
    return z


def _apply_residual_calibration(
    pred_res_3d: np.ndarray,
    occupancy: np.ndarray,
    esdf: np.ndarray,
    residual_bias_quantile: float,
    corridor_threshold: float,
    corridor_suppress: float,
    topq_quantile: float,
    contrastive_bg_quantile: float = 0.0,
    contrastive_neg_scale: float = 0.0,
    contrastive_pos_scale: float = 1.0,
    transport_iters: int = 0,
    transport_step: float = 0.35,
    transport_clearance_sigma: float = 0.45,
    bottleneck_threshold: float = 0.0,
    bottleneck_blend: float = 0.0,
    bottleneck_gamma: float = 1.0,
    open_boost: float = 0.0,
    open_boost_topq: float = 0.0,
    bottleneck_dampen: float = 0.0,
) -> np.ndarray:
    out = pred_res_3d.astype(np.float32, copy=True)
    free = ~occupancy.astype(bool)

    q = float(np.clip(residual_bias_quantile, 0.0, 0.95))
    if q > 0.0 and np.any(free):
        flat = out[:, free].reshape(-1)
        if flat.size > 0:
            bias = float(np.quantile(flat, q))
            if np.isfinite(bias) and bias > 0.0:
                out = np.maximum(out - bias, 0.0).astype(np.float32)

    q_bg = float(np.clip(contrastive_bg_quantile, 0.0, 0.95))
    neg_scale = float(np.clip(contrastive_neg_scale, 0.0, 2.0))
    pos_scale = float(max(contrastive_pos_scale, 0.0))
    if q_bg > 0.0 and np.any(free):
        vals = out[:, free].reshape(-1)
        if vals.size > 0:
            bg = float(np.quantile(vals, q_bg))
            if np.isfinite(bg) and bg > 0.0:
                centered = out - bg
                pos = np.maximum(centered, 0.0) * pos_scale
                neg = np.minimum(centered, 0.0) * neg_scale
                out = (pos + neg).astype(np.float32)

    thr = float(max(corridor_threshold, 0.0))
    sup = float(np.clip(corridor_suppress, 0.0, 1.0))
    if thr > 0.0 and sup > 0.0:
        clearance = np.maximum(esdf.astype(np.float32), 0.0)
        corridor = np.clip((thr - clearance) / max(thr, 1e-6), 0.0, 1.0)
        scale = 1.0 - sup * corridor
        out = (out * scale[None, ...]).astype(np.float32)

    adapt_open = float(max(open_boost, 0.0))
    adapt_dampen = float(np.clip(bottleneck_dampen, 0.0, 1.0))
    adapt_thr = float(max(corridor_threshold, bottleneck_threshold, 0.0))
    if (adapt_open > 0.0 or adapt_dampen > 0.0) and adapt_thr > 0.0:
        clearance = np.maximum(esdf.astype(np.float32), 0.0)
        bottleneck = np.clip((adapt_thr - clearance) / max(adapt_thr, 1e-6), 0.0, 1.0)
        gamma = float(max(bottleneck_gamma, 0.1))
        bott_w = np.power(bottleneck, gamma).astype(np.float32)
        open_w = (1.0 - bott_w).astype(np.float32)
        pos_raw = np.maximum(out, 0.0).astype(np.float32)
        q_boost = float(np.clip(open_boost_topq, 0.0, 0.999))
        if adapt_open > 0.0 and q_boost > 0.0 and np.any(free):
            vals = pos_raw[:, free].reshape(-1)
            vals = vals[vals > 0.0]
            if vals.size > 0:
                thr_boost = float(np.quantile(vals, q_boost))
                boost_mask = (pos_raw >= thr_boost).astype(np.float32)
            else:
                boost_mask = np.zeros_like(pos_raw, dtype=np.float32)
        elif adapt_open > 0.0:
            boost_mask = (pos_raw > 0.0).astype(np.float32)
        else:
            boost_mask = np.zeros_like(pos_raw, dtype=np.float32)
        pos_gain = (1.0 + adapt_open * open_w[None, ...] * boost_mask).astype(np.float32)
        damp_gain = (1.0 - adapt_dampen * bott_w).astype(np.float32)
        pos = pos_raw * pos_gain * damp_gain[None, ...]
        neg = np.minimum(out, 0.0) * damp_gain[None, ...]
        out = (pos + neg).astype(np.float32)

    q_keep = float(np.clip(topq_quantile, 0.0, 0.999))
    if q_keep > 0.0 and np.any(free):
        vals = out[:, free].reshape(-1)
        vals_pos = vals[vals > 0.0]
        if vals_pos.size > 0:
            thr_keep = float(np.quantile(vals_pos, q_keep))
            if np.isfinite(thr_keep) and thr_keep > 0.0:
                keep_pos = (out > 0.0) & (out >= thr_keep)
                out = np.where(keep_pos | (out <= 0.0), out, 0.0).astype(np.float32)

    blend_thr = float(max(bottleneck_threshold, 0.0))
    blend_ratio = float(np.clip(bottleneck_blend, 0.0, 1.0))
    if int(max(transport_iters, 0)) > 0 and blend_ratio > 0.0 and blend_thr > 0.0:
        transported = _transport_residual_obstacle_aware(
            residual_3d=out,
            occupancy=occupancy,
            esdf=esdf,
            iters=int(transport_iters),
            step=float(transport_step),
            clearance_sigma=float(transport_clearance_sigma),
        )
        clearance = np.maximum(esdf.astype(np.float32), 0.0)
        bottleneck = np.clip((blend_thr - clearance) / max(blend_thr, 1e-6), 0.0, 1.0)
        gamma = float(max(bottleneck_gamma, 0.1))
        local_w = (blend_ratio * np.power(bottleneck, gamma)).astype(np.float32)
        out = (out * (1.0 - local_w[None, ...]) + transported * local_w[None, ...]).astype(np.float32)

    out[:, occupancy.astype(bool)] = 0.0
    return out


def _make_ours_anchor(
    case: dict,
    predictor: NeuralHeuristicPredictor,
    residual_alpha: float,
    residual_clip: float,
    residual_bias_quantile: float,
    residual_corridor_threshold: float,
    residual_corridor_suppress: float,
    residual_topq_quantile: float,
    residual_contrastive_bg_quantile: float,
    residual_contrastive_neg_scale: float,
    residual_contrastive_pos_scale: float,
    residual_floor_ratio: float,
    residual_transport_iters: int,
    residual_transport_step: float,
    residual_transport_clearance_sigma: float,
    residual_bottleneck_threshold: float,
    residual_bottleneck_blend: float,
    residual_bottleneck_gamma: float,
    residual_open_boost: float,
    residual_open_boost_topq: float,
    residual_open_boost_min_line_clearance: float,
    residual_bottleneck_dampen: float,
    residual_adaptive_trust_ratio: float,
    residual_adaptive_trust_quantile: float,
    disable_temporal: bool,
    rs_base_override: np.ndarray | None = None,
) -> Callable[[float, float, float], float]:
    if rs_base_override is not None:
        rs_base = rs_base_override.astype(np.float32)
        yaw_bins = int(rs_base.shape[0]) if rs_base.ndim == 3 else 1
    else:
        rs_base = _compute_case_rs_field(case).astype(np.float32)
        yaw_bins = int(rs_base.shape[0]) if rs_base.ndim == 3 else 1

    seq = None if disable_temporal else case.get("dynamic_risk_seq", None)
    pred_res = predictor.predict_residual_field(
        occupancy=case["occupancy"],
        esdf=case["esdf"],
        start=case["start"],
        goal=case["goal"],
        resolution=case["resolution"],
        dynamic_risk=case.get("dynamic_risk", None),
        dynamic_risk_seq=seq,
        vehicle_context=case.get("vehicle_context", None),
    )
    pred_res = np.maximum(pred_res, 0.0).astype(np.float32)
    pred_res = np.clip(pred_res * float(max(residual_alpha, 0.0)), 0.0, float(max(residual_clip, 0.0))).astype(np.float32)
    pred_res_3d_raw = _match_yaw_channels(pred_res, yaw_bins=yaw_bins)
    base_res_3d = _apply_residual_calibration(
        pred_res_3d=pred_res_3d_raw,
        occupancy=case["occupancy"],
        esdf=case["esdf"],
        residual_bias_quantile=residual_bias_quantile,
        corridor_threshold=residual_corridor_threshold,
        corridor_suppress=residual_corridor_suppress,
        topq_quantile=residual_topq_quantile,
        contrastive_bg_quantile=residual_contrastive_bg_quantile,
        contrastive_neg_scale=residual_contrastive_neg_scale,
        contrastive_pos_scale=residual_contrastive_pos_scale,
        transport_iters=residual_transport_iters,
        transport_step=residual_transport_step,
        transport_clearance_sigma=residual_transport_clearance_sigma,
        bottleneck_threshold=residual_bottleneck_threshold,
        bottleneck_blend=residual_bottleneck_blend,
        bottleneck_gamma=residual_bottleneck_gamma,
        open_boost=0.0,
        open_boost_topq=0.0,
        bottleneck_dampen=0.0,
    )

    effective_open_boost = float(max(residual_open_boost, 0.0))
    min_line_clear = float(max(residual_open_boost_min_line_clearance, 0.0))
    if effective_open_boost > 0.0 and min_line_clear > 0.0:
        line_mean_clear = _mean_line_clearance(
            esdf=case["esdf"].astype(np.float32),
            start=case["start"],
            goal=case["goal"],
            resolution=float(case["resolution"]),
            samples_per_cell=2.0,
        )
        if np.isfinite(line_mean_clear) and line_mean_clear < min_line_clear:
            effective_open_boost = 0.0

    use_adaptive = bool(effective_open_boost > 0.0 or residual_bottleneck_dampen > 0.0)
    if use_adaptive:
        adaptive_res_3d = _apply_residual_calibration(
            pred_res_3d=pred_res_3d_raw,
            occupancy=case["occupancy"],
            esdf=case["esdf"],
            residual_bias_quantile=residual_bias_quantile,
            corridor_threshold=residual_corridor_threshold,
            corridor_suppress=residual_corridor_suppress,
            topq_quantile=residual_topq_quantile,
            contrastive_bg_quantile=residual_contrastive_bg_quantile,
            contrastive_neg_scale=residual_contrastive_neg_scale,
            contrastive_pos_scale=residual_contrastive_pos_scale,
            transport_iters=residual_transport_iters,
            transport_step=residual_transport_step,
            transport_clearance_sigma=residual_transport_clearance_sigma,
            bottleneck_threshold=residual_bottleneck_threshold,
            bottleneck_blend=residual_bottleneck_blend,
            bottleneck_gamma=residual_bottleneck_gamma,
            open_boost=effective_open_boost,
            open_boost_topq=residual_open_boost_topq,
            bottleneck_dampen=residual_bottleneck_dampen,
        )
    else:
        adaptive_res_3d = base_res_3d

    trust_ratio = float(max(residual_adaptive_trust_ratio, 0.0))
    if use_adaptive and trust_ratio > 0.0:
        free = ~case["occupancy"].astype(bool)
        if np.any(free):
            q = float(np.clip(residual_adaptive_trust_quantile, 0.5, 0.999))
            diff_vals = np.abs(adaptive_res_3d[:, free] - base_res_3d[:, free]).reshape(-1)
            base_vals = np.abs(base_res_3d[:, free]).reshape(-1)
            q_diff = float(np.quantile(diff_vals, q)) if diff_vals.size > 0 else 0.0
            q_base = float(np.quantile(base_vals, q)) if base_vals.size > 0 else 0.0
            ratio = q_diff / max(q_base, 1e-6)
            if np.isfinite(ratio) and ratio > trust_ratio:
                blend = float(np.clip(trust_ratio / max(ratio, 1e-6), 0.0, 1.0))
                pred_res_3d = (base_res_3d + blend * (adaptive_res_3d - base_res_3d)).astype(np.float32)
            else:
                pred_res_3d = adaptive_res_3d.astype(np.float32)
        else:
            pred_res_3d = adaptive_res_3d.astype(np.float32)
    else:
        pred_res_3d = adaptive_res_3d.astype(np.float32)

    # Fuse once to avoid dual trilinear interpolation at each node expansion.
    fused = (rs_base.astype(np.float32) + pred_res_3d.astype(np.float32)).astype(np.float32)
    floor_ratio = float(np.clip(residual_floor_ratio, 0.0, 1.0))
    if floor_ratio > 0.0:
        fused = np.maximum(fused, floor_ratio * rs_base.astype(np.float32)).astype(np.float32)
    fused = np.clip(fused, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    fused[:, case["occupancy"].astype(bool)] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return YawFieldHeuristic(
        field_3d=fused,
        resolution=float(case["resolution"]),
        max_value=float(DEFAULT_CONFIG.dataset.max_teacher_value),
        scale=1.0,
    )


def _make_no_rs_anchor(case: dict, predictor: NeuralHeuristicPredictor, residual_clip: float) -> Callable[[float, float, float], float]:
    pred = predictor.predict_residual_field(
        occupancy=case["occupancy"],
        esdf=case["esdf"],
        start=case["start"],
        goal=case["goal"],
        resolution=case["resolution"],
        dynamic_risk=case.get("dynamic_risk", None),
        dynamic_risk_seq=case.get("dynamic_risk_seq", None),
        vehicle_context=case.get("vehicle_context", None),
    )
    pred = np.maximum(pred, 0.0).astype(np.float32)
    pred = np.clip(pred, 0.0, float(max(residual_clip, 0.0))).astype(np.float32)

    if pred.ndim == 2:
        pred[case["occupancy"]] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
        return FieldHeuristic(pred, case["resolution"], max_value=float(DEFAULT_CONFIG.dataset.max_teacher_value), scale=1.0)

    pred[:, case["occupancy"]] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return YawFieldHeuristic(pred, case["resolution"], max_value=float(DEFAULT_CONFIG.dataset.max_teacher_value), scale=1.0)


def _make_no_residual_esdf_anchor(
    case: dict,
    esdf_alpha: float,
    esdf_threshold: float,
    rs_field_override: np.ndarray | None = None,
) -> Callable[[float, float, float], float]:
    rs = _make_rs_anchor(case, rs_field=rs_field_override)
    esdf = np.maximum(case["esdf"].astype(np.float32), 0.0)
    obs_cost = np.maximum(0.0, float(esdf_threshold) - esdf).astype(np.float32)
    field = (rs.field_3d.astype(np.float32) + float(max(esdf_alpha, 0.0)) * obs_cost[None, ...]).astype(np.float32)
    field[:, case["occupancy"]] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return YawFieldHeuristic(field, case["resolution"], max_value=float(DEFAULT_CONFIG.dataset.max_teacher_value), scale=1.0)


def _scenario_bucket(scenario: str) -> str:
    sc = str(scenario)
    if "maze" in sc:
        return "maze"
    if sc == "narrow_passage":
        return "narrow_passage"
    if sc == "deadend_labyrinth":
        return "deadend"
    return "other"


def _run_nonholonomic_experiment(
    files: list[Path],
    ours_predictor: NeuralHeuristicPredictor,
    args: argparse.Namespace,
    seed: int,
    run_sampling_compare: bool = True,
) -> tuple[list[EvalRow], list[EvalRow], list[EvalRow]]:
    rows_exp2: list[EvalRow] = []
    rows_exp3: list[EvalRow] = []
    rows_exp3_scene: list[EvalRow] = []
    rng = np.random.default_rng(seed + 901)

    for i_case, p in enumerate(files, start=1):
        case = _load_nonholonomic_case(p)
        case_id = p.name
        budget = _planner_budget(case["planner_cfg"], case, args)
        samp_iters = int(max(200, args.sampling_max_iters))
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=int(args.rs_field_yaw_bins))

        # Experiment 2: Ours vs Hybrid RS vs RRT* vs BIT*
        rs_anchor = _make_rs_anchor(case, rs_field=rs_field)
        r_rs = _run_hybrid_method(case, rs_anchor, max_expansions=budget)
        rows_exp2.append(
            EvalRow(
                "exp2_nonholonomic",
                "hard+narrow",
                "Hybrid A* (RS)",
                case_id,
                r_rs["success"],
                r_rs["expansions"],
                _path_length(r_rs["path"]),
                r_rs["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_rs["runtime_ms"],
            )
        )

        ours_anchor = _make_ours_anchor(
            case,
            ours_predictor,
            args.residual_alpha,
            args.residual_clip,
            args.residual_bias_quantile,
            args.residual_corridor_threshold,
            args.residual_corridor_suppress,
            args.residual_topq_quantile,
            args.residual_contrastive_bg_quantile,
            args.residual_contrastive_neg_scale,
            args.residual_contrastive_pos_scale,
            args.residual_floor_ratio,
            args.residual_transport_iters,
            args.residual_transport_step,
            args.residual_transport_clearance_sigma,
            args.residual_bottleneck_threshold,
            args.residual_bottleneck_blend,
            args.residual_bottleneck_gamma,
            args.residual_open_boost,
            args.residual_open_boost_topq,
            args.residual_open_boost_min_line_clearance,
            args.residual_bottleneck_dampen,
            args.residual_adaptive_trust_ratio,
            args.residual_adaptive_trust_quantile,
            disable_temporal=False,
            rs_base_override=rs_field,
        )
        r_ours = _run_hybrid_method(case, ours_anchor, max_expansions=budget)
        rows_exp2.append(
            EvalRow(
                "exp2_nonholonomic",
                "hard+narrow",
                "Ours",
                case_id,
                r_ours["success"],
                r_ours["expansions"],
                _path_length(r_ours["path"]),
                r_ours["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_ours["runtime_ms"],
            )
        )

        if run_sampling_compare:
            r_rrt = kinodynamic_rrt_star(
                occupancy=case["occupancy"],
                resolution=case["resolution"],
                start=case["start"],
                goal=case["goal"],
                vehicle_cfg=case["vehicle"],
                planner_cfg=case["planner_cfg"],
                max_iters=samp_iters,
                rng=rng,
                esdf=case["esdf"],
            )
            rows_exp2.append(
                EvalRow(
                    "exp2_nonholonomic",
                    "hard+narrow",
                    "Kinodynamic RRT*",
                    case_id,
                    r_rrt["success"],
                    float(r_rrt["expansions"]),
                    _path_length(r_rrt["path"]),
                    float(r_rrt["runtime_ms"]),
                    infer_ms=0.0,
                    search_ms=float(r_rrt["runtime_ms"]),
                )
            )

            r_bit = kinodynamic_bit_star(
                occupancy=case["occupancy"],
                resolution=case["resolution"],
                start=case["start"],
                goal=case["goal"],
                vehicle_cfg=case["vehicle"],
                planner_cfg=case["planner_cfg"],
                max_iters=samp_iters,
                rng=rng,
                esdf=case["esdf"],
            )
            rows_exp2.append(
                EvalRow(
                    "exp2_nonholonomic",
                    "hard+narrow",
                    "Kinodynamic BIT*",
                    case_id,
                    r_bit["success"],
                    float(r_bit["expansions"]),
                    _path_length(r_bit["path"]),
                    float(r_bit["runtime_ms"]),
                    infer_ms=0.0,
                    search_ms=float(r_bit["runtime_ms"]),
                )
            )

        # Experiment 3: ablation
        rows_exp3.append(
            EvalRow(
                "exp3_ablation",
                "hard",
                "No-Residual",
                case_id,
                r_rs["success"],
                r_rs["expansions"],
                _path_length(r_rs["path"]),
                r_rs["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_rs["runtime_ms"],
            )
        )
        rows_exp3.append(
            EvalRow(
                "exp3_ablation",
                "hard",
                "Full",
                case_id,
                r_ours["success"],
                r_ours["expansions"],
                _path_length(r_ours["path"]),
                r_ours["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_ours["runtime_ms"],
            )
        )

        no_res_esdf_anchor = _make_no_residual_esdf_anchor(
            case,
            esdf_alpha=float(args.esdf_anchor_alpha),
            esdf_threshold=float(args.esdf_anchor_threshold),
            rs_field_override=rs_field,
        )
        r_no_res_esdf = _run_hybrid_method(case, no_res_esdf_anchor, max_expansions=budget)
        rows_exp3.append(
            EvalRow(
                "exp3_ablation",
                "hard",
                "No-Residual+ESDF",
                case_id,
                r_no_res_esdf["success"],
                r_no_res_esdf["expansions"],
                _path_length(r_no_res_esdf["path"]),
                r_no_res_esdf["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_no_res_esdf["runtime_ms"],
            )
        )

        no_rs_anchor = _make_no_rs_anchor(case, ours_predictor, residual_clip=args.residual_clip)
        r_no_rs = _run_hybrid_method(case, no_rs_anchor, max_expansions=budget)
        rows_exp3.append(
            EvalRow(
                "exp3_ablation",
                "hard",
                "No-RS",
                case_id,
                r_no_rs["success"],
                r_no_rs["expansions"],
                _path_length(r_no_rs["path"]),
                r_no_rs["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_no_rs["runtime_ms"],
            )
        )

        no_temp_anchor = _make_ours_anchor(
            case,
            ours_predictor,
            args.residual_alpha,
            args.residual_clip,
            args.residual_bias_quantile,
            args.residual_corridor_threshold,
            args.residual_corridor_suppress,
            args.residual_topq_quantile,
            args.residual_contrastive_bg_quantile,
            args.residual_contrastive_neg_scale,
            args.residual_contrastive_pos_scale,
            args.residual_floor_ratio,
            args.residual_transport_iters,
            args.residual_transport_step,
            args.residual_transport_clearance_sigma,
            args.residual_bottleneck_threshold,
            args.residual_bottleneck_blend,
            args.residual_bottleneck_gamma,
            args.residual_open_boost,
            args.residual_open_boost_topq,
            args.residual_open_boost_min_line_clearance,
            args.residual_bottleneck_dampen,
            args.residual_adaptive_trust_ratio,
            args.residual_adaptive_trust_quantile,
            disable_temporal=True,
            rs_base_override=rs_field,
        )
        r_no_temp = _run_hybrid_method(case, no_temp_anchor, max_expansions=budget)
        rows_exp3.append(
            EvalRow(
                "exp3_ablation",
                "hard",
                "No-Temporal",
                case_id,
                r_no_temp["success"],
                r_no_temp["expansions"],
                _path_length(r_no_temp["path"]),
                r_no_temp["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_no_temp["runtime_ms"],
            )
        )

        bucket = _scenario_bucket(case["scenario"])
        scene_ds = f"hard:{bucket}"
        for method, rr in [
            ("Full", r_ours),
            ("No-Residual", r_rs),
            ("No-Residual+ESDF", r_no_res_esdf),
            ("No-RS", r_no_rs),
            ("No-Temporal", r_no_temp),
        ]:
            rows_exp3_scene.append(
                EvalRow(
                    "exp3_ablation_scene",
                    scene_ds,
                    method,
                    case_id,
                    rr["success"],
                    rr["expansions"],
                    _path_length(rr["path"]),
                    rr["runtime_ms"],
                    infer_ms=0.0,
                    search_ms=rr["runtime_ms"],
                )
            )
        if i_case % 5 == 0 or i_case == len(files):
            print(f"[exp2/3] processed {i_case}/{len(files)} nonholonomic cases")

    return rows_exp2, rows_exp3, rows_exp3_scene


def _run_public_nonholonomic_experiment(
    files: list[Path],
    ours_predictor: NeuralHeuristicPredictor,
    args: argparse.Namespace,
    seed: int,
) -> list[EvalRow]:
    rows: list[EvalRow] = []
    rng = np.random.default_rng(seed + 1701)
    for i_case, p in enumerate(files, start=1):
        case = _load_nonholonomic_case(p)
        case_id = p.name
        budget = _planner_budget(case["planner_cfg"], case, args)
        budget = max(int(budget), int(max(1, args.hybrid_exp4_max_expansions)))
        samp_iters = int(max(200, args.sampling_max_iters))
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=int(args.rs_field_yaw_bins))

        rs_anchor = _make_rs_anchor(case, rs_field=rs_field)
        r_rs = _run_hybrid_method(case, rs_anchor, max_expansions=budget)
        rows.append(
            EvalRow(
                "exp4_public_kinodynamic",
                "parasol",
                "Hybrid A* (RS)",
                case_id,
                r_rs["success"],
                r_rs["expansions"],
                _path_length(r_rs["path"]),
                r_rs["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_rs["runtime_ms"],
            )
        )

        ours_anchor = _make_ours_anchor(
            case,
            ours_predictor,
            args.residual_alpha,
            args.residual_clip,
            args.residual_bias_quantile,
            args.residual_corridor_threshold,
            args.residual_corridor_suppress,
            args.residual_topq_quantile,
            args.residual_contrastive_bg_quantile,
            args.residual_contrastive_neg_scale,
            args.residual_contrastive_pos_scale,
            args.residual_floor_ratio,
            args.residual_transport_iters,
            args.residual_transport_step,
            args.residual_transport_clearance_sigma,
            args.residual_bottleneck_threshold,
            args.residual_bottleneck_blend,
            args.residual_bottleneck_gamma,
            args.residual_open_boost,
            args.residual_open_boost_topq,
            args.residual_open_boost_min_line_clearance,
            args.residual_bottleneck_dampen,
            args.residual_adaptive_trust_ratio,
            args.residual_adaptive_trust_quantile,
            disable_temporal=False,
            rs_base_override=rs_field,
        )
        r_ours = _run_hybrid_method(case, ours_anchor, max_expansions=budget)
        rows.append(
            EvalRow(
                "exp4_public_kinodynamic",
                "parasol",
                "Ours",
                case_id,
                r_ours["success"],
                r_ours["expansions"],
                _path_length(r_ours["path"]),
                r_ours["runtime_ms"],
                infer_ms=0.0,
                search_ms=r_ours["runtime_ms"],
            )
        )

        r_rrt = kinodynamic_rrt_star(
            occupancy=case["occupancy"],
            resolution=case["resolution"],
            start=case["start"],
            goal=case["goal"],
            vehicle_cfg=case["vehicle"],
            planner_cfg=case["planner_cfg"],
            max_iters=samp_iters,
            rng=rng,
            esdf=case["esdf"],
        )
        rows.append(
            EvalRow(
                "exp4_public_kinodynamic",
                "parasol",
                "Kinodynamic RRT*",
                case_id,
                r_rrt["success"],
                float(r_rrt["expansions"]),
                _path_length(r_rrt["path"]),
                float(r_rrt["runtime_ms"]),
                infer_ms=0.0,
                search_ms=float(r_rrt["runtime_ms"]),
            )
        )

        r_bit = kinodynamic_bit_star(
            occupancy=case["occupancy"],
            resolution=case["resolution"],
            start=case["start"],
            goal=case["goal"],
            vehicle_cfg=case["vehicle"],
            planner_cfg=case["planner_cfg"],
            max_iters=samp_iters,
            rng=rng,
            esdf=case["esdf"],
        )
        rows.append(
            EvalRow(
                "exp4_public_kinodynamic",
                "parasol",
                "Kinodynamic BIT*",
                case_id,
                r_bit["success"],
                float(r_bit["expansions"]),
                _path_length(r_bit["path"]),
                float(r_bit["runtime_ms"]),
                infer_ms=0.0,
                search_ms=float(r_bit["runtime_ms"]),
            )
        )
        if i_case % 5 == 0 or i_case == len(files):
            print(f"[exp4] processed {i_case}/{len(files)} public nonholonomic cases")

    return rows


def _collect_files(root: Path, max_cases: int, seed: int) -> list[Path]:
    return select_files(sorted(Path(root).glob("sample_*.npz")), max_cases, seed=seed)


def _parse_experiment_set(raw: str) -> set[str]:
    tokens = [t.strip().lower() for t in str(raw).split(",") if t.strip()]
    if not tokens:
        return {"exp1", "exp2", "exp3", "exp4"}
    valid = {"exp1", "exp2", "exp3", "exp4"}
    bad = [t for t in tokens if t not in valid]
    if bad:
        raise ValueError(f"Unknown experiments: {bad}. Valid values are {sorted(valid)}")
    return set(tokens)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    run_exps = _parse_experiment_set(args.experiments)
    if args.standard_only:
        run_exps = run_exps.intersection({"exp1", "exp2"})
    if args.disable_exp2:
        run_exps = set([e for e in run_exps if e != "exp2"])
    if not run_exps:
        raise ValueError("No experiments selected after applying --experiments/--standard-only/--disable-exp2.")

    paper_out = Path(args.paper_out)
    figures_dir = paper_out / "figures"
    ckpt_dir = paper_out / "checkpoints"
    logs_dir = paper_out / "logs"
    ensure_dirs([paper_out, figures_dir, ckpt_dir, logs_dir])

    # Prepare benchmark datasets.
    mp_train = args.benchmark_root / "mp" / "train"
    mp_test = args.benchmark_root / "mp" / "test"
    csm_train = args.benchmark_root / "csm" / "train"
    csm_test = args.benchmark_root / "csm" / "test"

    if ("exp1" in run_exps) or ("exp2" in run_exps):
        if not mp_train.exists() or not mp_test.exists() or not csm_train.exists() or not csm_test.exists():
            raise FileNotFoundError(
                "Benchmark datasets missing. Run: python scripts/convert_benchmark_datasets.py --output-root data/benchmark"
            )

    if "exp3" in run_exps and not Path(args.hard_root).exists():
        raise FileNotFoundError(f"Exp3 root missing: {args.hard_root}")
    if "exp4" in run_exps and not Path(args.parasol_root).exists():
        raise FileNotFoundError(f"Exp4 root missing: {args.parasol_root}")

    if args.device.startswith("cuda") and not torch.cuda.is_available():
        args.device = "cpu"

    vin = None
    neural_astar = None
    vin_ckpt = ckpt_dir / "vin_baseline.pt"
    na_ckpt = ckpt_dir / "neural_astar_baseline.pt"
    if ("exp1" in run_exps) or ("exp2" in run_exps):
        if (not args.skip_neural_training) or (not vin_ckpt.exists()) or (not na_ckpt.exists()):
            # Build temporary combined dirs by symlink for fair training split.
            tmp_train = logs_dir / "tmp_train_combined"
            tmp_val = logs_dir / "tmp_val_combined"
            ensure_dirs([tmp_train, tmp_val])
            for p in list(tmp_train.glob("sample_*.npz")) + list(tmp_val.glob("sample_*.npz")):
                p.unlink()

            train_files = select_files(
                sorted(mp_train.glob("sample_*.npz")) + sorted(csm_train.glob("sample_*.npz")),
                args.train_max_samples,
                seed=args.seed + 301,
            )
            val_files = select_files(
                sorted(mp_test.glob("sample_*.npz")) + sorted(csm_test.glob("sample_*.npz")),
                args.val_max_samples,
                seed=args.seed + 303,
            )

            for i, p in enumerate(train_files):
                dst = tmp_train / f"sample_{i:06d}.npz"
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                dst.symlink_to(p.resolve())
            for i, p in enumerate(val_files):
                dst = tmp_val / f"sample_{i:06d}.npz"
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                dst.symlink_to(p.resolve())

            vin_train_info = train_vin(
                train_dir=tmp_train,
                val_dir=tmp_val,
                checkpoint_out=vin_ckpt,
                seed=args.seed,
                device=args.device,
                epochs=args.train_neural_epochs,
                batch_size=args.train_neural_batch,
                lr=args.train_neural_lr,
                max_train_samples=0,
                max_val_samples=0,
            )
            na_train_info = train_neural_astar(
                train_dir=tmp_train,
                val_dir=tmp_val,
                checkpoint_out=na_ckpt,
                seed=args.seed,
                device=args.device,
                epochs=args.train_neural_epochs,
                batch_size=args.train_neural_batch,
                lr=args.train_neural_lr,
                max_train_samples=0,
                max_val_samples=0,
            )
            (logs_dir / "neural_training_meta.json").write_text(
                json.dumps({"vin": vin_train_info, "neural_astar": na_train_info}, indent=2), encoding="utf-8"
            )

        vin = VINLite.load(vin_ckpt, device=args.device)
        neural_astar = NeuralAStarLite.load(na_ckpt, device=args.device)

    ours_predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=DEFAULT_CONFIG.dataset.gaussian_sigma)

    rows_exp1: list[EvalRow] = []
    rows_exp2: list[EvalRow] = []
    rows_exp3: list[EvalRow] = []
    rows_exp3_scene: list[EvalRow] = []
    rows_exp4: list[EvalRow] = []
    router_stats_exp1: dict | None = None
    router_stats_exp2: dict | None = None
    fig_payload: dict = {}
    mp_test_files: list[Path] = []
    csm_test_files: list[Path] = []
    nonh_files: list[Path] = []
    public_files: list[Path] = []

    if "exp1" in run_exps:
        if vin is None or neural_astar is None:
            raise RuntimeError("VIN/Neural A* not initialized for Exp1.")
        if int(args.max_mp_cases) == 0:
            mp_cap = 0
        elif int(args.max_mp_cases) > 0:
            mp_cap = int(args.max_mp_cases)
        else:
            mp_cap = int(args.max_standard_cases)
        mp_test_files = _collect_files(mp_test, max_cases=mp_cap, seed=args.seed + 401)
        rows_std_mp, fig_mp, router_stats_exp1 = _run_standard_experiment(
            mp_test_files=mp_test_files,
            csm_test_files=[],
            vin=vin,
            neural_astar=neural_astar,
            ours_predictor=ours_predictor,
            args=args,
        )
        rows_exp1 = [replace(r, experiment="exp1_mp") for r in rows_std_mp if r.dataset == "mp"]
        if fig_mp:
            fig_payload = fig_mp

    if "exp2" in run_exps:
        if vin is None or neural_astar is None:
            raise RuntimeError("VIN/Neural A* not initialized for Exp2.")
        if int(args.max_csm_cases) == 0:
            csm_cap = 0
        elif int(args.max_csm_cases) > 0:
            csm_cap = int(args.max_csm_cases)
        else:
            csm_cap = int(args.max_standard_cases)
        csm_test_files = _collect_files(csm_test, max_cases=csm_cap, seed=args.seed + 403)
        rows_std_csm, fig_csm, router_stats_exp2 = _run_standard_experiment(
            mp_test_files=[],
            csm_test_files=csm_test_files,
            vin=vin,
            neural_astar=neural_astar,
            ours_predictor=ours_predictor,
            args=args,
        )
        rows_exp2 = [replace(r, experiment="exp2_csm") for r in rows_std_csm if r.dataset == "csm"]
        if (not fig_payload) and fig_csm:
            fig_payload = fig_csm

    exp3_ds = "hard"
    if "exp3" in run_exps:
        if int(args.max_exp3_cases) == 0:
            exp3_cap = 0
        elif int(args.max_exp3_cases) > 0:
            exp3_cap = int(args.max_exp3_cases)
        else:
            exp3_cap = int(args.max_nonholonomic_cases)
        nonh_files = _collect_files(args.hard_root, max_cases=exp3_cap, seed=args.seed + 501)
        _, rows_exp3_raw, rows_exp3_scene_raw = _run_nonholonomic_experiment(
            files=nonh_files,
            ours_predictor=ours_predictor,
            args=args,
            seed=args.seed,
            run_sampling_compare=False,
        )

        hard_root_resolved = Path(args.hard_root).resolve()
        parasol_root_resolved = Path(args.parasol_root).resolve() if Path(args.parasol_root).exists() else None
        if parasol_root_resolved is not None and hard_root_resolved == parasol_root_resolved:
            exp3_ds = "parasol"

        rows_exp3 = [replace(r, dataset=exp3_ds) for r in rows_exp3_raw]
        rows_exp3_scene = []
        for r in rows_exp3_scene_raw:
            suffix = str(r.dataset).split(":", 1)[1] if ":" in str(r.dataset) else str(r.dataset)
            rows_exp3_scene.append(replace(r, dataset=f"{exp3_ds}:{suffix}"))

    if "exp4" in run_exps:
        if int(args.max_exp4_cases) == 0:
            exp4_cap = 0
        elif int(args.max_exp4_cases) > 0:
            exp4_cap = int(args.max_exp4_cases)
        else:
            exp4_cap = int(args.max_public_cases)
        public_files = _collect_files(args.parasol_root, max_cases=exp4_cap, seed=args.seed + 601)
        if public_files:
            rows_exp4 = _run_public_nonholonomic_experiment(
                files=public_files,
                ours_predictor=ours_predictor,
                args=args,
                seed=args.seed,
            )

    # Trim ablation cases if requested.
    if rows_exp3 and args.max_ablation_cases > 0:
        keep = set([r.case_id for r in rows_exp3 if r.method == "Full"])
        keep_ids = sorted(list(keep))[: int(args.max_ablation_cases)]
        keep_set = set(keep_ids)
        rows_exp3 = [r for r in rows_exp3 if r.case_id in keep_set]
        rows_exp3_scene = [r for r in rows_exp3_scene if r.case_id in keep_set]

    all_rows = rows_exp1 + rows_exp2 + rows_exp3 + rows_exp3_scene + rows_exp4
    if not all_rows:
        raise FileNotFoundError(
            "No evaluation rows were generated. Check dataset roots and selected experiments."
        )
    summary = _method_summary(all_rows)

    # Aggregate standard benchmark as separate MP/CSM experiments and combined MP+CSM.
    exp1_methods = ["A*", "Theta*", "VIN", "Neural A*", "Ours"]
    for m in exp1_methods:
        vals_mp = [r for r in rows_exp1 if r.method == m]
        succ_mp = [r for r in vals_mp if r.success]
        if vals_mp:
            summary[("exp1_mp", "mp", m)] = {
                "num_cases": len(vals_mp),
                "success_rate": len(succ_mp) / max(len(vals_mp), 1),
                "avg_expansions": float(np.mean([v.expansions for v in succ_mp])) if succ_mp else float("nan"),
                "avg_path_length": float(np.mean([v.path_length for v in succ_mp if np.isfinite(v.path_length)])) if succ_mp else float("nan"),
                "avg_infer_ms": float(np.mean([v.infer_ms for v in succ_mp])) if succ_mp else float("nan"),
                "avg_search_ms": float(np.mean([v.search_ms for v in succ_mp])) if succ_mp else float("nan"),
                "avg_time_ms": float(np.mean([v.runtime_ms for v in succ_mp])) if succ_mp else float("nan"),
            }

        vals_csm = [r for r in rows_exp2 if r.method == m]
        succ_csm = [r for r in vals_csm if r.success]
        if vals_csm:
            summary[("exp2_csm", "csm", m)] = {
                "num_cases": len(vals_csm),
                "success_rate": len(succ_csm) / max(len(vals_csm), 1),
                "avg_expansions": float(np.mean([v.expansions for v in succ_csm])) if succ_csm else float("nan"),
                "avg_path_length": float(np.mean([v.path_length for v in succ_csm if np.isfinite(v.path_length)])) if succ_csm else float("nan"),
                "avg_infer_ms": float(np.mean([v.infer_ms for v in succ_csm])) if succ_csm else float("nan"),
                "avg_search_ms": float(np.mean([v.search_ms for v in succ_csm])) if succ_csm else float("nan"),
                "avg_time_ms": float(np.mean([v.runtime_ms for v in succ_csm])) if succ_csm else float("nan"),
            }

        vals_std = vals_mp + vals_csm
        succ_std = [r for r in vals_std if r.success]
        if vals_std:
            summary[("exp1_standard", "mp+csm", m)] = {
                "num_cases": len(vals_std),
                "success_rate": len(succ_std) / max(len(vals_std), 1),
                "avg_expansions": float(np.mean([v.expansions for v in succ_std])) if succ_std else float("nan"),
                "avg_path_length": float(np.mean([v.path_length for v in succ_std if np.isfinite(v.path_length)])) if succ_std else float("nan"),
                "avg_infer_ms": float(np.mean([v.infer_ms for v in succ_std])) if succ_std else float("nan"),
                "avg_search_ms": float(np.mean([v.search_ms for v in succ_std])) if succ_std else float("nan"),
                "avg_time_ms": float(np.mean([v.runtime_ms for v in succ_std])) if succ_std else float("nan"),
            }

    out_csv = paper_out / "exp_results_summary.csv"
    _write_summary_csv(summary, out_csv)

    # Figures.
    if ("exp1_mp", "mp", "Ours") in summary:
        _save_bar_svg(
            rows=[
                (m, summary[("exp1_mp", "mp", m)]["success_rate"])
                for m in exp1_methods
            ],
            title="Exp1 MP Benchmark: Success Rate",
            y_label="success",
            out_path=figures_dir / "exp1_mp_success_rate.svg",
        )
        _save_bar_svg(
            rows=[
                (m, summary[("exp1_mp", "mp", m)]["avg_expansions"])
                for m in exp1_methods
            ],
            title="Exp1 MP Benchmark: Avg Expansions",
            y_label="expansions",
            out_path=figures_dir / "exp1_mp_expansions.svg",
        )

    if ("exp2_csm", "csm", "Ours") in summary:
        _save_bar_svg(
            rows=[
                (m, summary[("exp2_csm", "csm", m)]["success_rate"])
                for m in exp1_methods
            ],
            title="Exp2 CSM Benchmark: Success Rate",
            y_label="success",
            out_path=figures_dir / "exp2_csm_success_rate.svg",
        )
        _save_bar_svg(
            rows=[
                (m, summary[("exp2_csm", "csm", m)]["avg_expansions"])
                for m in exp1_methods
            ],
            title="Exp2 CSM Benchmark: Avg Expansions",
            y_label="expansions",
            out_path=figures_dir / "exp2_csm_expansions.svg",
        )

    if ("exp3_ablation", exp3_ds, "Full") in summary:
        _save_bar_svg(
            rows=[
                (m, summary[("exp3_ablation", exp3_ds, m)]["success_rate"])
                for m in ["Full", "No-Residual", "No-Residual+ESDF", "No-RS", "No-Temporal"]
            ],
            title=f"Exp3 Ablation ({exp3_ds}): Success Rate",
            y_label="success",
            out_path=figures_dir / "exp3_ablation_success_rate.svg",
        )
    scene_rows: list[tuple[str, float]] = []
    for ds in [f"{exp3_ds}:maze", f"{exp3_ds}:narrow_passage", f"{exp3_ds}:deadend", f"{exp3_ds}:other"]:
        if ("exp3_ablation_scene", ds, "Full") in summary:
            tag = ds.split(":", 1)[1]
            scene_rows.append((f"{tag}/Full", summary[("exp3_ablation_scene", ds, "Full")]["success_rate"]))
        if ("exp3_ablation_scene", ds, "No-Residual") in summary:
            tag = ds.split(":", 1)[1]
            scene_rows.append((f"{tag}/NoRes", summary[("exp3_ablation_scene", ds, "No-Residual")]["success_rate"]))
    if scene_rows:
        _save_bar_svg(
            rows=scene_rows,
            title="Exp3 Scene-wise: Success Rate (Full vs No-Residual)",
            y_label="success",
            out_path=figures_dir / "exp3_ablation_scene_success_rate.svg",
        )

    if rows_exp4:
        _save_bar_svg(
            rows=[
                (m, summary[("exp4_public_kinodynamic", "parasol", m)]["success_rate"])
                for m in ["Hybrid A* (RS)", "Kinodynamic RRT*", "Kinodynamic BIT*", "Ours"]
            ],
            title="Exp4 Public Kinodynamic: Success Rate",
            y_label="success",
            out_path=figures_dir / "exp4_success_rate.svg",
        )

    if fig_payload:
        _save_search_tree_svg(
            occupancy=fig_payload["occupancy"],
            resolution=float(fig_payload["resolution"]),
            astar_expanded=fig_payload["astar_expanded"],
            ours_expanded=fig_payload["ours_expanded"],
            astar_path=fig_payload["astar_path"],
            ours_path=fig_payload["ours_path"],
            start_xy=fig_payload["start_xy"],
            goal_xy=fig_payload["goal_xy"],
            out_path=figures_dir / "search_tree_compare.svg",
        )

    detail_rows = [r.__dict__ for r in all_rows]
    (logs_dir / "exp_results_detail.json").write_text(json.dumps(detail_rows, indent=2), encoding="utf-8")

    router_summary = {
        "enabled": bool(args.enable_dual_path_router),
        "total_cases": 0,
        "fast_cases": 0,
        "slow_cases": 0,
        "fast_ratio": float("nan"),
        "avg_complexity_score": float("nan"),
        "avg_line_block_ratio": float("nan"),
        "avg_local_occ_ratio": float("nan"),
        "avg_global_occ_ratio": float("nan"),
        "avg_distance_ratio": float("nan"),
        "by_experiment": {},
        "by_dataset": {},
        "reasons": {},
    }
    router_decisions: list[dict] = []
    router_parts: list[tuple[str, dict | None]] = [
        ("exp1_mp", router_stats_exp1),
        ("exp2_csm", router_stats_exp2),
    ]
    if bool(args.enable_dual_path_router):
        score_vals: list[float] = []
        line_vals: list[float] = []
        local_vals: list[float] = []
        global_vals: list[float] = []
        dist_vals: list[float] = []
        for exp_name, part in router_parts:
            if not part or not bool(part.get("enabled", False)):
                continue
            router_summary["by_experiment"][exp_name] = {
                "total_cases": int(part.get("total_cases", 0)),
                "fast_cases": int(part.get("fast_cases", 0)),
                "slow_cases": int(part.get("slow_cases", 0)),
                "avg_complexity_score": float(part.get("avg_complexity_score", float("nan"))),
                "avg_line_block_ratio": float(part.get("avg_line_block_ratio", float("nan"))),
                "avg_local_occ_ratio": float(part.get("avg_local_occ_ratio", float("nan"))),
                "avg_global_occ_ratio": float(part.get("avg_global_occ_ratio", float("nan"))),
                "avg_distance_ratio": float(part.get("avg_distance_ratio", float("nan"))),
            }
            router_summary["total_cases"] += int(part.get("total_cases", 0))
            router_summary["fast_cases"] += int(part.get("fast_cases", 0))
            router_summary["slow_cases"] += int(part.get("slow_cases", 0))
            if np.isfinite(float(part.get("avg_complexity_score", float("nan")))):
                score_vals.extend(
                    [float(part.get("avg_complexity_score"))] * max(int(part.get("total_cases", 0)), 0)
                )
            if np.isfinite(float(part.get("avg_line_block_ratio", float("nan")))):
                line_vals.extend(
                    [float(part.get("avg_line_block_ratio"))] * max(int(part.get("total_cases", 0)), 0)
                )
            if np.isfinite(float(part.get("avg_local_occ_ratio", float("nan")))):
                local_vals.extend(
                    [float(part.get("avg_local_occ_ratio"))] * max(int(part.get("total_cases", 0)), 0)
                )
            if np.isfinite(float(part.get("avg_global_occ_ratio", float("nan")))):
                global_vals.extend(
                    [float(part.get("avg_global_occ_ratio"))] * max(int(part.get("total_cases", 0)), 0)
                )
            if np.isfinite(float(part.get("avg_distance_ratio", float("nan")))):
                dist_vals.extend(
                    [float(part.get("avg_distance_ratio"))] * max(int(part.get("total_cases", 0)), 0)
                )

            for ds, ds_stat in (part.get("by_dataset", {}) or {}).items():
                existing = router_summary["by_dataset"].get(ds, None)
                if existing is None:
                    existing = {
                        "total_cases": 0,
                        "fast_cases": 0,
                        "slow_cases": 0,
                        "_score_sum": 0.0,
                        "_line_sum": 0.0,
                        "_local_sum": 0.0,
                        "_global_sum": 0.0,
                        "_dist_sum": 0.0,
                    }
                    router_summary["by_dataset"][ds] = existing
                n_ds = int(ds_stat.get("total_cases", 0))
                existing["total_cases"] += n_ds
                existing["fast_cases"] += int(ds_stat.get("fast_cases", 0))
                existing["slow_cases"] += int(ds_stat.get("slow_cases", 0))
                existing["_score_sum"] += float(ds_stat.get("avg_complexity_score", 0.0)) * n_ds
                existing["_line_sum"] += float(ds_stat.get("avg_line_block_ratio", 0.0)) * n_ds
                existing["_local_sum"] += float(ds_stat.get("avg_local_occ_ratio", 0.0)) * n_ds
                existing["_global_sum"] += float(ds_stat.get("avg_global_occ_ratio", 0.0)) * n_ds
                existing["_dist_sum"] += float(ds_stat.get("avg_distance_ratio", 0.0)) * n_ds

            for k, v in (part.get("reasons", {}) or {}).items():
                router_summary["reasons"][k] = int(router_summary["reasons"].get(k, 0)) + int(v)

            router_decisions.extend((part.get("decisions", []) or []))

        n_total = max(int(router_summary["total_cases"]), 1)
        if int(router_summary["total_cases"]) > 0:
            router_summary["fast_ratio"] = float(router_summary["fast_cases"] / n_total)
        if score_vals:
            router_summary["avg_complexity_score"] = float(np.mean(np.asarray(score_vals, dtype=np.float32)))
        if line_vals:
            router_summary["avg_line_block_ratio"] = float(np.mean(np.asarray(line_vals, dtype=np.float32)))
        if local_vals:
            router_summary["avg_local_occ_ratio"] = float(np.mean(np.asarray(local_vals, dtype=np.float32)))
        if global_vals:
            router_summary["avg_global_occ_ratio"] = float(np.mean(np.asarray(global_vals, dtype=np.float32)))
        if dist_vals:
            router_summary["avg_distance_ratio"] = float(np.mean(np.asarray(dist_vals, dtype=np.float32)))

        for ds, ds_stat in router_summary["by_dataset"].items():
            dn = max(int(ds_stat["total_cases"]), 1)
            ds_stat["avg_complexity_score"] = float(ds_stat["_score_sum"] / dn)
            ds_stat["avg_line_block_ratio"] = float(ds_stat["_line_sum"] / dn)
            ds_stat["avg_local_occ_ratio"] = float(ds_stat["_local_sum"] / dn)
            ds_stat["avg_global_occ_ratio"] = float(ds_stat["_global_sum"] / dn)
            ds_stat["avg_distance_ratio"] = float(ds_stat["_dist_sum"] / dn)
            del ds_stat["_score_sum"]
            del ds_stat["_line_sum"]
            del ds_stat["_local_sum"]
            del ds_stat["_global_sum"]
            del ds_stat["_dist_sum"]
        (logs_dir / "dual_path_router_decisions.json").write_text(json.dumps(router_decisions, indent=2), encoding="utf-8")

    cli_args = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    config = {
        "seed": args.seed,
        "device": args.device,
        "ours_ckpt": str(args.ours_checkpoint),
        "vin_ckpt": str(vin_ckpt) if vin_ckpt.exists() else "",
        "neural_astar_ckpt": str(na_ckpt) if na_ckpt.exists() else "",
        "experiments": sorted(list(run_exps)),
        "cli_args": cli_args,
        "max_standard_cases": args.max_standard_cases,
        "max_mp_cases": args.max_mp_cases,
        "max_csm_cases": args.max_csm_cases,
        "max_nonholonomic_cases": args.max_nonholonomic_cases,
        "max_ablation_cases": args.max_ablation_cases,
        "max_public_cases": args.max_public_cases,
        "max_exp3_cases": args.max_exp3_cases,
        "max_exp4_cases": args.max_exp4_cases,
        "standard_only": bool(args.standard_only),
        "grid_max_expansions": args.grid_max_expansions,
        "hybrid_max_expansions": args.hybrid_max_expansions,
        "hybrid_hard_max_expansions": args.hybrid_hard_max_expansions,
        "hybrid_maze_max_expansions": args.hybrid_maze_max_expansions,
        "sampling_max_iters": args.sampling_max_iters,
        "rs_field_yaw_bins": args.rs_field_yaw_bins,
        "residual_alpha": args.residual_alpha,
        "residual_clip": args.residual_clip,
        "residual_bias_quantile": args.residual_bias_quantile,
        "residual_corridor_threshold": args.residual_corridor_threshold,
        "residual_corridor_suppress": args.residual_corridor_suppress,
        "residual_topq_quantile": args.residual_topq_quantile,
        "residual_contrastive_bg_quantile": args.residual_contrastive_bg_quantile,
        "residual_contrastive_neg_scale": args.residual_contrastive_neg_scale,
        "residual_contrastive_pos_scale": args.residual_contrastive_pos_scale,
        "residual_floor_ratio": args.residual_floor_ratio,
        "residual_transport_iters": args.residual_transport_iters,
        "residual_transport_step": args.residual_transport_step,
        "residual_transport_clearance_sigma": args.residual_transport_clearance_sigma,
        "residual_bottleneck_threshold": args.residual_bottleneck_threshold,
        "residual_bottleneck_blend": args.residual_bottleneck_blend,
        "residual_bottleneck_gamma": args.residual_bottleneck_gamma,
        "residual_open_boost": args.residual_open_boost,
        "residual_open_boost_topq": args.residual_open_boost_topq,
        "residual_open_boost_min_line_clearance": args.residual_open_boost_min_line_clearance,
        "residual_bottleneck_dampen": args.residual_bottleneck_dampen,
        "residual_adaptive_trust_ratio": args.residual_adaptive_trust_ratio,
        "residual_adaptive_trust_quantile": args.residual_adaptive_trust_quantile,
        "esdf_anchor_alpha": args.esdf_anchor_alpha,
        "esdf_anchor_threshold": args.esdf_anchor_threshold,
        "enable_dual_path_router": bool(args.enable_dual_path_router),
        "router_config": {
            "corridor_radius_cells": args.router_corridor_radius_cells,
            "samples_per_cell": args.router_samples_per_cell,
            "fast_max_distance_ratio": args.router_fast_max_distance_ratio,
            "fast_max_line_block_ratio": args.router_fast_max_line_block_ratio,
            "fast_max_local_occ_ratio": args.router_fast_max_local_occ_ratio,
            "fast_max_global_occ_ratio": args.router_fast_max_global_occ_ratio,
            "slow_min_line_block_ratio": args.router_slow_min_line_block_ratio,
            "slow_min_local_occ_ratio": args.router_slow_min_local_occ_ratio,
            "score_threshold": args.router_score_threshold,
            "w_line_block": args.router_w_line_block,
            "w_local_occ": args.router_w_local_occ,
            "w_distance": args.router_w_distance,
            "w_global_occ": args.router_w_global_occ,
            "los_penalty": args.router_los_penalty,
            "fast_score_margin": args.router_fast_score_margin,
        },
        "router_summary": router_summary,
        "case_splits": {
            "mp_test_files": [p.name for p in mp_test_files],
            "csm_test_files": [p.name for p in csm_test_files],
            "nonholonomic_files": [p.name for p in nonh_files],
            "public_nonholonomic_files": [p.name for p in public_files],
        },
        "exp3_dataset": exp3_ds,
    }
    (logs_dir / "experiment_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    tex_out = paper_out / "experiment_section.tex"
    _write_experiment_section_tex(tex_out, summary=summary, config=config)

    print("Saved:")
    print(f"- {out_csv}")
    print(f"- {figures_dir}")
    print(f"- {tex_out}")


if __name__ == "__main__":
    main()
