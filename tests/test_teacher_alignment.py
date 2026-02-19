from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.reeds_shepp import RSConsistentCostConfig, shortest_path_cost_consistent_with_path
from planner.hybrid_astar import HybridAStarPlanner


def _segment_dir(seg) -> int:
    d = float(getattr(seg, "direction", 0.0))
    l = float(getattr(seg, "length", 0.0))
    if abs(d) > 1e-6:
        return -1 if d < 0.0 else 1
    if abs(l) > 1e-6:
        return -1 if l < 0.0 else 1
    return 1


def _segment_len(seg) -> float:
    return abs(float(getattr(seg, "length", 0.0)))


def _segment_steer(seg, wheel_base: float, turn_radius: float, max_steer_rad: float) -> float:
    t = str(getattr(seg, "type", "straight")).lower()
    if t == "left":
        sign = 1.0
    elif t == "right":
        sign = -1.0
    else:
        return 0.0
    steer = math.atan2(wheel_base, max(turn_radius, 1e-6))
    return sign * min(steer, max_steer_rad)


def _planner_replay_cost(planner: HybridAStarPlanner, path_obj, turn_radius: float) -> float:
    prev_steer = 0.0
    total = 0.0
    for seg in path_obj.segments:
        seg_len = _segment_len(seg)
        if seg_len <= 1e-9:
            continue
        direction = _segment_dir(seg)
        steer = _segment_steer(seg, planner.vehicle_cfg.wheel_base, turn_radius, planner.max_steer)
        n_steps = max(1, int(np.ceil(seg_len / planner.cfg.step_size)))
        ds = seg_len / n_steps
        for _ in range(n_steps):
            total += planner._edge_cost(ds, steer, prev_steer, direction)  # noqa: SLF001
            prev_steer = steer
    return float(total)


def test_teacher_alignment_cases() -> None:
    cfg = DEFAULT_CONFIG
    cost_cfg = RSConsistentCostConfig.from_configs(cfg.vehicle, cfg.planner)
    turn_radius = float(cfg.vehicle.min_turn_radius)

    # Empty map: teacher and replay cost should align closely.
    occupancy = np.zeros((96, 96), dtype=bool)
    planner = HybridAStarPlanner(
        occupancy=occupancy,
        resolution=cfg.map.resolution,
        vehicle_cfg=cfg.vehicle,
        planner_cfg=cfg.planner,
        esdf=None,
    )

    cases = [
        ((5.0, 5.0, 0.0), (25.0, 5.0, 0.0)),  # straight forward
        ((10.0, 10.0, 0.0), (12.0, 12.0, math.pi)),  # strong turn-around, likely with reverse
        ((20.0, 8.0, -math.pi / 2.0), (8.0, 18.0, math.pi / 2.0)),  # mixed turn directions
        ((16.0, 16.0, math.pi), (14.0, 16.5, 0.0)),  # short near-in-place heading change
    ]

    for idx, (start, goal) in enumerate(cases):
        h_teacher, path_obj = shortest_path_cost_consistent_with_path(
            start=start,
            goal=goal,
            rho=turn_radius,
            cost_cfg=cost_cfg,
            step_size=cfg.dataset.teacher_rs_step_size,
            backend="rsplan",
        )
        assert path_obj is not None, f"case {idx}: failed to get RS path"
        g_replay = _planner_replay_cost(planner, path_obj, turn_radius=turn_radius)

        abs_err = abs(h_teacher - g_replay)
        rel_err = abs_err / max(g_replay, 1e-6)

        print(
            f"[align case {idx}] h_teacher={h_teacher:.4f} "
            f"g_replay={g_replay:.4f} abs_err={abs_err:.4f} rel_err={100.0 * rel_err:.2f}%"
        )
        assert abs_err < 0.25 or rel_err < 0.02, f"case {idx}: teacher/planner misaligned"


if __name__ == "__main__":
    test_teacher_alignment_cases()
    print("teacher alignment test passed")
