from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.esdf import compute_esdf
from planner.heuristics import euclidean_heuristic
from planner.hybrid_astar import HybridAStarPlanner


def _add_boundaries(occ: np.ndarray) -> None:
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True


def _carve_rect(occ: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    h, w = occ.shape
    xa = int(np.clip(min(x0, x1), 1, w - 2))
    xb = int(np.clip(max(x0, x1), 1, w - 2))
    ya = int(np.clip(min(y0, y1), 1, h - 2))
    yb = int(np.clip(max(y0, y1), 1, h - 2))
    occ[ya : yb + 1, xa : xb + 1] = False


def _carve_segment(occ: np.ndarray, p0: tuple[int, int], p1: tuple[int, int], corridor_w: int) -> None:
    x0, y0 = p0
    x1, y1 = p1
    hw = max(1, corridor_w // 2)
    if y0 == y1:
        _carve_rect(occ, x0, y0 - hw, x1, y0 + hw)
        return
    if x0 == x1:
        _carve_rect(occ, x0 - hw, y0, x0 + hw, y1)
        return

    # L-shaped carve for non-axis-aligned moves.
    _carve_rect(occ, x0, y0 - hw, x1, y0 + hw)
    _carve_rect(occ, x1 - hw, y0, x1 + hw, y1)


def _build_extreme_case(
    h: int,
    w: int,
    resolution: float,
    min_turn_radius: float,
    corridor_w: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, tuple[float, float, float], tuple[float, float, float], str]:
    occ = np.ones((h, w), dtype=bool)
    _add_boundaries(occ)

    n_turns = int(rng.integers(4, 7))
    margin = max(10, int(np.ceil((min_turn_radius + 1.5) / resolution)))
    x_nodes = np.linspace(margin, w - margin - 1, n_turns + 2).astype(np.int32)
    y_low = max(margin, int(0.22 * h))
    y_high = min(h - margin - 1, int(0.78 * h))
    y_mid = h // 2
    jitter = max(2, h // 16)

    points: list[tuple[int, int]] = []
    points.append((int(x_nodes[0]), int(np.clip(y_mid + int(rng.integers(-jitter, jitter + 1)), margin, h - margin - 1))))
    for i in range(1, n_turns + 1):
        if i % 2 == 1:
            yc = int(np.clip(y_low + int(rng.integers(-jitter, jitter + 1)), margin, h - margin - 1))
        else:
            yc = int(np.clip(y_high + int(rng.integers(-jitter, jitter + 1)), margin, h - margin - 1))
        points.append((int(x_nodes[i]), yc))
    points.append((int(x_nodes[-1]), int(np.clip(y_mid + int(rng.integers(-jitter, jitter + 1)), margin, h - margin - 1))))

    for a, b in zip(points[:-1], points[1:]):
        _carve_segment(occ, a, b, corridor_w)

    # Add turning bays around corners so nonholonomic planner remains feasible.
    bay_r = max(corridor_w + 2, int(np.ceil(1.3 * min_turn_radius / resolution)))
    _carve_rect(occ, points[0][0] - (bay_r + 2), points[0][1] - (bay_r + 2), points[0][0] + (bay_r + 2), points[0][1] + (bay_r + 2))
    _carve_rect(occ, points[-1][0] - (bay_r + 2), points[-1][1] - (bay_r + 2), points[-1][0] + (bay_r + 2), points[-1][1] + (bay_r + 2))
    for x, y in points[1:-1]:
        _carve_rect(occ, x - bay_r, y - bay_r, x + bay_r, y + bay_r)

    # Add dead-end branches.
    n_branches = int(rng.integers(2, 5))
    for _ in range(n_branches):
        k = int(rng.integers(1, len(points) - 1))
        x0, y0 = points[k]
        x_prev, y_prev = points[k - 1]
        x_next, y_next = points[k + 1] if k + 1 < len(points) else points[k]
        dx = x_next - x_prev
        dy = y_next - y_prev
        length = int(rng.integers(5, 10))
        sign = -1 if rng.random() < 0.5 else 1
        if abs(dx) >= abs(dy):
            x1 = x0
            y1 = int(np.clip(y0 + sign * length, margin, h - margin - 1))
        else:
            y1 = y0
            x1 = int(np.clip(x0 + sign * length, margin, w - margin - 1))
        _carve_segment(occ, (x0, y0), (x1, y1), corridor_w)

    # Re-open the principal path after adding branches.
    for a, b in zip(points[:-1], points[1:]):
        _carve_segment(occ, a, b, corridor_w)
    _add_boundaries(occ)

    start_cell = (int(np.clip(points[0][0] + corridor_w, margin, w - margin - 1)), points[0][1])
    goal_cell = (int(np.clip(points[-1][0] - corridor_w, margin, w - margin - 1)), points[-1][1])
    v0 = np.array(points[1], dtype=np.float32) - np.array(points[0], dtype=np.float32)
    vg = np.array(points[-1], dtype=np.float32) - np.array(points[-2], dtype=np.float32)
    start_yaw = float(np.arctan2(v0[1], v0[0]))
    goal_yaw = float(np.arctan2(vg[1], vg[0]))

    start = ((start_cell[0] + 0.5) * resolution, (start_cell[1] + 0.5) * resolution, start_yaw)
    goal = ((goal_cell[0] + 0.5) * resolution, (goal_cell[1] + 0.5) * resolution, goal_yaw)

    occ[start_cell[1], start_cell[0]] = False
    occ[goal_cell[1], goal_cell[0]] = False
    return occ, start, goal, "extreme_hell"


def _is_hybrid_feasible(
    occ: np.ndarray,
    esdf: np.ndarray,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    resolution: float,
) -> bool:
    cfg = DEFAULT_CONFIG
    planner_cfg = replace(cfg.planner, max_expansions=max(800000, cfg.planner.max_expansions))
    planner = HybridAStarPlanner(
        occupancy=occ,
        resolution=resolution,
        vehicle_cfg=cfg.vehicle,
        planner_cfg=planner_cfg,
        esdf=esdf,
    )
    result = planner.plan(
        start=start,
        goal=goal,
        anchor_fn=euclidean_heuristic((goal[0], goal[1])),
        guidance_fn=None,
        main_mode="anchor",
        record_expanded=False,
    )
    return bool(result.success)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build unseen extreme narrow/deadend benchmark cases.")
    p.add_argument("--output", type=Path, default=Path("data_extreme_hell"))
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--seed", type=int, default=20260219)
    p.add_argument(
        "--require-feasible",
        action="store_true",
        help="Require quick Hybrid A* feasibility check during generation (slower, stricter).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG

    test_dir = args.output / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    for f in test_dir.glob("*.npz"):
        f.unlink()

    rng = np.random.default_rng(args.seed)
    corridor_w = max(6, int(np.ceil((cfg.vehicle.width + 1.0) / cfg.map.resolution)))

    created = 0
    max_tries = int(max(args.count * 20, 200))
    tries = 0
    while created < args.count and tries < max_tries:
        tries += 1
        occ, start, goal, scenario = _build_extreme_case(
            h=cfg.map.height,
            w=cfg.map.width,
            resolution=cfg.map.resolution,
            min_turn_radius=cfg.vehicle.min_turn_radius,
            corridor_w=corridor_w,
            rng=rng,
        )
        esdf = compute_esdf(occ, cfg.map.resolution).astype(np.float32)
        if occ.mean() < 0.22:
            continue
        sx = int(np.clip(np.floor(start[0] / cfg.map.resolution), 0, cfg.map.width - 1))
        sy = int(np.clip(np.floor(start[1] / cfg.map.resolution), 0, cfg.map.height - 1))
        gx = int(np.clip(np.floor(goal[0] / cfg.map.resolution), 0, cfg.map.width - 1))
        gy = int(np.clip(np.floor(goal[1] / cfg.map.resolution), 0, cfg.map.height - 1))
        clearance = float(0.35 * cfg.vehicle.width)
        if float(esdf[sy, sx]) <= clearance + 0.2 or float(esdf[gy, gx]) <= clearance + 0.2:
            continue
        if args.require_feasible and not _is_hybrid_feasible(occ, esdf, start, goal, cfg.map.resolution):
            continue

        out = test_dir / f"sample_{created:05d}.npz"
        np.savez_compressed(
            out,
            occupancy=occ.astype(np.uint8),
            esdf=esdf,
            start=np.asarray(start, dtype=np.float32),
            goal=np.asarray(goal, dtype=np.float32),
            resolution=np.float32(cfg.map.resolution),
            scenario=np.array(scenario),
            category=np.array("C"),
            fill_value=np.float32(cfg.dataset.max_teacher_value),
        )
        created += 1

    if created < args.count:
        raise RuntimeError(f"Failed to generate extreme set: {created}/{args.count}")

    meta = {
        "num_samples": created,
        "seed": int(args.seed),
        "corridor_width_cells": int(corridor_w),
        "corridor_width_m": float(corridor_w * cfg.map.resolution),
        "vehicle_width_m": float(cfg.vehicle.width),
        "category": "C",
        "scenario": "extreme_hell",
    }
    with (test_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"generated {created} extreme cases under {test_dir}")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
