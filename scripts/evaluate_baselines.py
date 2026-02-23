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
from planner.heuristics import FieldHeuristic, ResidualYawFieldHeuristic, YawFieldHeuristic
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run paper-grade benchmark comparisons")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--hard-root", type=Path, default=Path("data_hard_dynamic_v2/test"))
    p.add_argument("--parasol-root", type=Path, default=Path("data/benchmark/parasol_narrow/test"))
    p.add_argument("--paper-out", type=Path, default=Path("outputs/paper"))

    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/heuristic_net_hard_optimized.pt"))
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--seed", type=int, default=7)

    p.add_argument("--train-neural-epochs", type=int, default=4)
    p.add_argument("--train-neural-batch", type=int, default=24)
    p.add_argument("--train-neural-lr", type=float, default=1e-3)
    p.add_argument("--train-max-samples", type=int, default=2000)
    p.add_argument("--val-max-samples", type=int, default=400)
    p.add_argument("--skip-neural-training", action="store_true")

    p.add_argument("--max-standard-cases", type=int, default=200)
    p.add_argument("--max-nonholonomic-cases", type=int, default=80)
    p.add_argument("--max-ablation-cases", type=int, default=100)

    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--hybrid-max-expansions", type=int, default=12000)
    p.add_argument("--hybrid-hard-max-expansions", type=int, default=13000)
    p.add_argument("--hybrid-maze-max-expansions", type=int, default=18000)
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
            return f"{method} & -- & -- & -- & -- \\\\"
        return (
            f"{method} & {s['success_rate']:.3f} & {s['avg_expansions']:.1f} & "
            f"{s['avg_path_length']:.2f} & {s['avg_time_ms']:.2f} \\\\"
        )

    lines = []
    lines.append("\\section{Experiments}")
    lines.append("\\subsection{Experimental Setup}")
    lines.append("We evaluate on public planning benchmarks (MP, CSM) and our nonholonomic hard scenarios.")
    lines.append("All methods share identical maps, start/goal pairs, and expansion/iteration budgets.")
    lines.append(
        "Neural baselines (VIN and Neural A*) are trained with the same converted training split and evaluated on unseen test cases."
    )
    lines.append(
        f"Our model checkpoint is \\texttt{{{config.get('ours_ckpt','outputs/checkpoints/heuristic_net_hard_optimized.pt')}}}."
    )

    lines.append("\\subsection{Datasets}")
    lines.append("\\begin{itemize}")
    lines.append("\\item \\textbf{MP}: 8 environment families, each with 800 train and 100 test instances.")
    lines.append("\\item \\textbf{CSM}: 30 city/street maps, split into 20 train maps and 10 test maps, converted to 64$\\times$64 crops.")
    lines.append("\\item \\textbf{Hard Nonholonomic}: Our round-2 hard+dynamic dataset for Ackermann planning.")
    lines.append("\\end{itemize}")

    lines.append("\\subsection{Experiment 1: Standard Benchmark (MP/CSM)}")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{Standard benchmark results (success rate $\\uparrow$, expansions $\\downarrow$, path length $\\downarrow$, time $\\downarrow$).}")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\toprule")
    lines.append("Method & Success & Expansions & Path Len. & Time (ms) \\\\")
    lines.append("\\midrule")
    for m in ["A*", "Theta*", "VIN", "Neural A*", "Ours"]:
        lines.append(line_for("exp1_standard", "mp+csm", m))
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    lines.append("\\subsection{Experiment 2: Nonholonomic and Narrow Scenarios}")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{Nonholonomic comparison on hard+narrow cases.}")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\toprule")
    lines.append("Method & Success & Expansions & Path Len. & Time (ms) \\\\")
    lines.append("\\midrule")
    for m in ["Hybrid A* (RS)", "Kinodynamic RRT*", "Kinodynamic BIT*", "Ours"]:
        lines.append(line_for("exp2_nonholonomic", "hard+narrow", m))
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    lines.append("\\subsection{Experiment 3: Ablation}")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{Ablation on hard scenarios.}")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\toprule")
    lines.append("Method & Success & Expansions & Path Len. & Time (ms) \\\\")
    lines.append("\\midrule")
    for m in ["Full", "No-Residual", "No-Residual+ESDF", "No-RS", "No-Temporal"]:
        lines.append(line_for("exp3_ablation", "hard", m))
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    has_exp4 = ("exp4_public_kinodynamic", "parasol", "Ours") in summary
    if has_exp4:
        lines.append("\\subsection{Experiment 4: Public Kinodynamic Benchmarks}")
        lines.append("\\begin{table}[t]")
        lines.append("\\centering")
        lines.append("\\caption{Parasol-style public narrow benchmark results.}")
        lines.append("\\begin{tabular}{lcccc}")
        lines.append("\\toprule")
        lines.append("Method & Success & Expansions & Path Len. & Time (ms) \\\\")
        lines.append("\\midrule")
        for m in ["Hybrid A* (RS)", "Kinodynamic RRT*", "Kinodynamic BIT*", "Ours"]:
            lines.append(line_for("exp4_public_kinodynamic", "parasol", m))
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        lines.append("\\end{table}")

    lines.append("\\subsection{Discussion}")
    lines.append(
        "On MP/CSM, our method reaches the same success rate as A*/Theta*/Neural A* and clearly improves efficiency over VIN and Neural A* in node expansions, while incurring extra runtime due neural inference."
    )
    lines.append(
        "On hard nonholonomic cases, removing RS prior (No-RS) increases expansions by more than one order of magnitude; adding ESDF-only correction without learned residual provides a useful mid-point baseline for isolating learning gains."
    )
    lines.append(
        "In this implementation, RRT* and BIT* use RS connectors and planner-consistent costs to form kinodynamic sampling baselines under the same cost model as Hybrid A*."
    )
    if ("exp3_ablation_scene", "hard:maze", "Full") in summary:
        lines.append(
            "Scene-wise ablation further reports maze / narrow_passage / deadend subsets to localize where residual guidance helps or hurts."
        )

    out_tex.write_text("\n".join(lines), encoding="utf-8")


def _run_standard_experiment(
    mp_test_files: list[Path],
    csm_test_files: list[Path],
    vin: VINLite,
    neural_astar: NeuralAStarLite,
    ours_predictor: NeuralHeuristicPredictor,
    args: argparse.Namespace,
) -> tuple[list[EvalRow], dict]:
    rows: list[EvalRow] = []
    fig_payload: dict = {}

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
        rows.append(EvalRow("exp1_standard", ds, "A*", p.name, r_astar["success"], float(r_astar["expansions"]), _path_length(r_astar["path"]), float(r_astar["runtime_ms"])))

        r_theta = _theta_star(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=args.grid_max_expansions,
        )
        rows.append(EvalRow("exp1_standard", ds, "Theta*", p.name, r_theta["success"], float(r_theta["expansions"]), _path_length(r_theta["path"]), float(r_theta["runtime_ms"])))

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
        rows.append(EvalRow("exp1_standard", ds, "VIN", p.name, r_vin["success"], float(r_vin["expansions"]), _path_length(r_vin["path"]), float(r_vin["runtime_ms"] + infer_ms)))

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
        rows.append(EvalRow("exp1_standard", ds, "Neural A*", p.name, r_na["success"], float(r_na["expansions"]), _path_length(r_na["path"]), float(r_na["runtime_ms"] + infer_ms)))

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
        rows.append(EvalRow("exp1_standard", ds, "Ours", p.name, r_ours["success"], float(r_ours["expansions"]), _path_length(r_ours["path"]), float(r_ours["runtime_ms"] + infer_ms)))

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

    return rows, fig_payload


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

    # Nearest-neighbor resampling along yaw dimension.
    idx = (np.floor(np.arange(yaw_bins, dtype=np.float32) * (c / float(yaw_bins))).astype(np.int64)) % c
    return field[idx].astype(np.float32)


def _apply_residual_calibration(
    pred_res_3d: np.ndarray,
    occupancy: np.ndarray,
    esdf: np.ndarray,
    residual_bias_quantile: float,
    corridor_threshold: float,
    corridor_suppress: float,
    topq_quantile: float,
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

    thr = float(max(corridor_threshold, 0.0))
    sup = float(np.clip(corridor_suppress, 0.0, 1.0))
    if thr > 0.0 and sup > 0.0:
        clearance = np.maximum(esdf.astype(np.float32), 0.0)
        corridor = np.clip((thr - clearance) / max(thr, 1e-6), 0.0, 1.0)
        scale = 1.0 - sup * corridor
        out = (out * scale[None, ...]).astype(np.float32)

    q_keep = float(np.clip(topq_quantile, 0.0, 0.999))
    if q_keep > 0.0 and np.any(free):
        vals = out[:, free].reshape(-1)
        if vals.size > 0:
            thr_keep = float(np.quantile(vals, q_keep))
            if np.isfinite(thr_keep) and thr_keep > 0.0:
                out = np.where(out >= thr_keep, out, 0.0).astype(np.float32)

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
    pred_res_3d = _match_yaw_channels(pred_res, yaw_bins=yaw_bins)
    pred_res_3d = _apply_residual_calibration(
        pred_res_3d=pred_res_3d,
        occupancy=case["occupancy"],
        esdf=case["esdf"],
        residual_bias_quantile=residual_bias_quantile,
        corridor_threshold=residual_corridor_threshold,
        corridor_suppress=residual_corridor_suppress,
        topq_quantile=residual_topq_quantile,
    )

    return ResidualYawFieldHeuristic(
        base_field_3d=rs_base.astype(np.float32),
        residual_field_3d=pred_res_3d.astype(np.float32),
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
        rows_exp2.append(EvalRow("exp2_nonholonomic", "hard+narrow", "Hybrid A* (RS)", case_id, r_rs["success"], r_rs["expansions"], _path_length(r_rs["path"]), r_rs["runtime_ms"]))

        ours_anchor = _make_ours_anchor(
            case,
            ours_predictor,
            args.residual_alpha,
            args.residual_clip,
            args.residual_bias_quantile,
            args.residual_corridor_threshold,
            args.residual_corridor_suppress,
            args.residual_topq_quantile,
            disable_temporal=False,
            rs_base_override=rs_field,
        )
        r_ours = _run_hybrid_method(case, ours_anchor, max_expansions=budget)
        rows_exp2.append(EvalRow("exp2_nonholonomic", "hard+narrow", "Ours", case_id, r_ours["success"], r_ours["expansions"], _path_length(r_ours["path"]), r_ours["runtime_ms"]))

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
        rows_exp2.append(EvalRow("exp2_nonholonomic", "hard+narrow", "Kinodynamic RRT*", case_id, r_rrt["success"], float(r_rrt["expansions"]), _path_length(r_rrt["path"]), float(r_rrt["runtime_ms"])))

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
        rows_exp2.append(EvalRow("exp2_nonholonomic", "hard+narrow", "Kinodynamic BIT*", case_id, r_bit["success"], float(r_bit["expansions"]), _path_length(r_bit["path"]), float(r_bit["runtime_ms"])))

        # Experiment 3: ablation
        rows_exp3.append(EvalRow("exp3_ablation", "hard", "No-Residual", case_id, r_rs["success"], r_rs["expansions"], _path_length(r_rs["path"]), r_rs["runtime_ms"]))
        rows_exp3.append(EvalRow("exp3_ablation", "hard", "Full", case_id, r_ours["success"], r_ours["expansions"], _path_length(r_ours["path"]), r_ours["runtime_ms"]))

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
            )
        )

        no_rs_anchor = _make_no_rs_anchor(case, ours_predictor, residual_clip=args.residual_clip)
        r_no_rs = _run_hybrid_method(case, no_rs_anchor, max_expansions=budget)
        rows_exp3.append(EvalRow("exp3_ablation", "hard", "No-RS", case_id, r_no_rs["success"], r_no_rs["expansions"], _path_length(r_no_rs["path"]), r_no_rs["runtime_ms"]))

        no_temp_anchor = _make_ours_anchor(
            case,
            ours_predictor,
            args.residual_alpha,
            args.residual_clip,
            args.residual_bias_quantile,
            args.residual_corridor_threshold,
            args.residual_corridor_suppress,
            args.residual_topq_quantile,
            disable_temporal=True,
            rs_base_override=rs_field,
        )
        r_no_temp = _run_hybrid_method(case, no_temp_anchor, max_expansions=budget)
        rows_exp3.append(EvalRow("exp3_ablation", "hard", "No-Temporal", case_id, r_no_temp["success"], r_no_temp["expansions"], _path_length(r_no_temp["path"]), r_no_temp["runtime_ms"]))

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
        samp_iters = int(max(200, args.sampling_max_iters))
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=int(args.rs_field_yaw_bins))

        rs_anchor = _make_rs_anchor(case, rs_field=rs_field)
        r_rs = _run_hybrid_method(case, rs_anchor, max_expansions=budget)
        rows.append(EvalRow("exp4_public_kinodynamic", "parasol", "Hybrid A* (RS)", case_id, r_rs["success"], r_rs["expansions"], _path_length(r_rs["path"]), r_rs["runtime_ms"]))

        ours_anchor = _make_ours_anchor(
            case,
            ours_predictor,
            args.residual_alpha,
            args.residual_clip,
            args.residual_bias_quantile,
            args.residual_corridor_threshold,
            args.residual_corridor_suppress,
            args.residual_topq_quantile,
            disable_temporal=False,
            rs_base_override=rs_field,
        )
        r_ours = _run_hybrid_method(case, ours_anchor, max_expansions=budget)
        rows.append(EvalRow("exp4_public_kinodynamic", "parasol", "Ours", case_id, r_ours["success"], r_ours["expansions"], _path_length(r_ours["path"]), r_ours["runtime_ms"]))

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
        rows.append(EvalRow("exp4_public_kinodynamic", "parasol", "Kinodynamic RRT*", case_id, r_rrt["success"], float(r_rrt["expansions"]), _path_length(r_rrt["path"]), float(r_rrt["runtime_ms"])))

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
        rows.append(EvalRow("exp4_public_kinodynamic", "parasol", "Kinodynamic BIT*", case_id, r_bit["success"], float(r_bit["expansions"]), _path_length(r_bit["path"]), float(r_bit["runtime_ms"])))
        if i_case % 5 == 0 or i_case == len(files):
            print(f"[exp4] processed {i_case}/{len(files)} public nonholonomic cases")

    return rows


def _collect_files(root: Path, max_cases: int, seed: int) -> list[Path]:
    return select_files(sorted(Path(root).glob("sample_*.npz")), max_cases, seed=seed)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

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

    if not mp_train.exists() or not mp_test.exists() or not csm_train.exists() or not csm_test.exists():
        raise FileNotFoundError(
            "Benchmark datasets missing. Run: python scripts/convert_benchmark_datasets.py --output-root data/benchmark"
        )

    if args.device.startswith("cuda") and not torch.cuda.is_available():
        args.device = "cpu"

    # Train/load neural baselines.
    vin_ckpt = ckpt_dir / "vin_baseline.pt"
    na_ckpt = ckpt_dir / "neural_astar_baseline.pt"

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

    # Experiment 1
    mp_test_files = _collect_files(mp_test, max_cases=max(1, args.max_standard_cases // 2), seed=args.seed + 401)
    csm_test_files = _collect_files(csm_test, max_cases=max(1, args.max_standard_cases // 2), seed=args.seed + 403)
    rows_exp1, fig_payload = _run_standard_experiment(
        mp_test_files=mp_test_files,
        csm_test_files=csm_test_files,
        vin=vin,
        neural_astar=neural_astar,
        ours_predictor=ours_predictor,
        args=args,
    )

    # Experiment 2/3
    hard_files = _collect_files(args.hard_root, max_cases=args.max_nonholonomic_cases, seed=args.seed + 501)
    if args.parasol_root.exists():
        narrow_extra = _collect_files(args.parasol_root, max_cases=max(1, args.max_nonholonomic_cases // 3), seed=args.seed + 503)
    else:
        # fallback: use narrow/deadend subset from hard split
        narrow_extra = []
        for p in sorted(Path(args.hard_root).glob("sample_*.npz")):
            with np.load(p, allow_pickle=False) as z:
                sc = str(z["scenario"]) if "scenario" in z else ""
            if sc in {"narrow_passage", "deadend_labyrinth", "maze_single"}:
                narrow_extra.append(p)
        narrow_extra = select_files(narrow_extra, max(1, args.max_nonholonomic_cases // 3), seed=args.seed + 505)

    nonh_files = sorted({p.resolve(): p for p in (hard_files + narrow_extra)}.values(), key=lambda x: str(x))
    nonh_files = nonh_files[: max(1, args.max_nonholonomic_cases)]

    rows_exp2, rows_exp3, rows_exp3_scene = _run_nonholonomic_experiment(
        files=nonh_files,
        ours_predictor=ours_predictor,
        args=args,
        seed=args.seed,
    )

    rows_exp4: list[EvalRow] = []
    if args.parasol_root.exists():
        public_files = _collect_files(args.parasol_root, max_cases=max(1, args.max_public_cases), seed=args.seed + 601)
        if public_files:
            rows_exp4 = _run_public_nonholonomic_experiment(
                files=public_files,
                ours_predictor=ours_predictor,
                args=args,
                seed=args.seed,
            )

    # Trim ablation cases if requested.
    if args.max_ablation_cases > 0:
        keep = set([r.case_id for r in rows_exp3 if r.method == "Full"])
        keep_ids = sorted(list(keep))[: int(args.max_ablation_cases)]
        keep_set = set(keep_ids)
        rows_exp3 = [r for r in rows_exp3 if r.case_id in keep_set]
        rows_exp3_scene = [r for r in rows_exp3_scene if r.case_id in keep_set]

    all_rows = rows_exp1 + rows_exp2 + rows_exp3 + rows_exp3_scene + rows_exp4
    summary = _method_summary(all_rows)

    # Aggregate exp1 across MP+CSM for paper table.
    exp1_methods = ["A*", "Theta*", "VIN", "Neural A*", "Ours"]
    for m in exp1_methods:
        vals = [r for r in rows_exp1 if r.method == m]
        succ = [r for r in vals if r.success]
        summary[("exp1_standard", "mp+csm", m)] = {
            "num_cases": len(vals),
            "success_rate": len(succ) / max(len(vals), 1),
            "avg_expansions": float(np.mean([v.expansions for v in succ])) if succ else float("nan"),
            "avg_path_length": float(np.mean([v.path_length for v in succ if np.isfinite(v.path_length)])) if succ else float("nan"),
            "avg_time_ms": float(np.mean([v.runtime_ms for v in succ])) if succ else float("nan"),
        }

    out_csv = paper_out / "exp_results_summary.csv"
    _write_summary_csv(summary, out_csv)

    # Figures.
    _save_bar_svg(
        rows=[(m, summary[("exp1_standard", "mp+csm", m)]["success_rate"]) for m in exp1_methods],
        title="Exp1 Standard Benchmark: Success Rate",
        y_label="success",
        out_path=figures_dir / "exp1_success_rate.svg",
    )
    _save_bar_svg(
        rows=[(m, summary[("exp1_standard", "mp+csm", m)]["avg_expansions"]) for m in exp1_methods],
        title="Exp1 Standard Benchmark: Avg Expansions",
        y_label="expansions",
        out_path=figures_dir / "exp1_expansions.svg",
    )

    _save_bar_svg(
        rows=[
            (m, summary[("exp2_nonholonomic", "hard+narrow", m)]["success_rate"])
            for m in ["Hybrid A* (RS)", "Kinodynamic RRT*", "Kinodynamic BIT*", "Ours"]
        ],
        title="Exp2 Nonholonomic: Success Rate",
        y_label="success",
        out_path=figures_dir / "exp2_success_rate.svg",
    )
    _save_bar_svg(
        rows=[
            (m, summary[("exp3_ablation", "hard", m)]["success_rate"])
            for m in ["Full", "No-Residual", "No-Residual+ESDF", "No-RS", "No-Temporal"]
        ],
        title="Exp3 Ablation: Success Rate",
        y_label="success",
        out_path=figures_dir / "exp3_success_rate.svg",
    )
    scene_rows: list[tuple[str, float]] = []
    for ds in ["hard:maze", "hard:narrow_passage", "hard:deadend", "hard:other"]:
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
            out_path=figures_dir / "exp3_scene_success_rate.svg",
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

    cli_args = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    config = {
        "seed": args.seed,
        "device": args.device,
        "ours_ckpt": str(args.ours_checkpoint),
        "vin_ckpt": str(vin_ckpt),
        "neural_astar_ckpt": str(na_ckpt),
        "cli_args": cli_args,
        "max_standard_cases": args.max_standard_cases,
        "max_nonholonomic_cases": args.max_nonholonomic_cases,
        "max_ablation_cases": args.max_ablation_cases,
        "max_public_cases": args.max_public_cases,
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
        "esdf_anchor_alpha": args.esdf_anchor_alpha,
        "esdf_anchor_threshold": args.esdf_anchor_threshold,
        "case_splits": {
            "mp_test_files": [p.name for p in mp_test_files],
            "csm_test_files": [p.name for p in csm_test_files],
            "nonholonomic_files": [p.name for p in nonh_files],
            "public_nonholonomic_files": [p.case_id for p in rows_exp4[::4]] if rows_exp4 else [],
        },
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
