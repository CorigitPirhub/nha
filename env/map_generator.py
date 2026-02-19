from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from config import MapConfig


@dataclass
class Scene:
    occupancy: np.ndarray
    start: Tuple[float, float, float]
    goal: Tuple[float, float, float]
    scenario: str


def _add_boundaries(occ: np.ndarray) -> None:
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True


def _random_rectangles(occ: np.ndarray, rng: np.random.Generator, density_target: float) -> np.ndarray:
    h, w = occ.shape
    max_iters = 500
    for _ in range(max_iters):
        if occ.mean() >= density_target:
            break
        rw = int(rng.integers(max(2, w // 20), max(3, w // 7)))
        rh = int(rng.integers(max(2, h // 20), max(3, h // 7)))
        x0 = int(rng.integers(1, max(2, w - rw - 1)))
        y0 = int(rng.integers(1, max(2, h - rh - 1)))
        occ[y0 : y0 + rh, x0 : x0 + rw] = True
    return occ


def _generate_random_map(cfg: MapConfig, rng: np.random.Generator) -> np.ndarray:
    occ = np.zeros((cfg.height, cfg.width), dtype=bool)
    density = float(rng.uniform(*cfg.obstacle_density_range))
    _add_boundaries(occ)
    _random_rectangles(occ, rng, density)
    return occ


def _generate_narrow_passage_map(cfg: MapConfig, rng: np.random.Generator) -> np.ndarray:
    occ = np.zeros((cfg.height, cfg.width), dtype=bool)
    _add_boundaries(occ)

    wall_thickness = int(rng.integers(2, 5))
    center_x = cfg.width // 2 + int(rng.integers(-cfg.width // 8, cfg.width // 8 + 1))
    gap_h = int(rng.integers(max(4, cfg.height // 10), max(6, cfg.height // 5)))
    gap_y = int(rng.integers(cfg.height // 6, cfg.height - cfg.height // 6 - gap_h))

    x0 = max(1, center_x - wall_thickness // 2)
    x1 = min(cfg.width - 1, x0 + wall_thickness)
    occ[:, x0:x1] = True
    occ[gap_y : gap_y + gap_h, x0:x1] = False

    density = float(rng.uniform(cfg.obstacle_density_range[0], cfg.obstacle_density_range[1] * 0.6))
    _random_rectangles(occ, rng, density)
    _add_boundaries(occ)
    return occ


def _generate_parking_map(cfg: MapConfig, rng: np.random.Generator) -> np.ndarray:
    occ = np.zeros((cfg.height, cfg.width), dtype=bool)
    _add_boundaries(occ)

    lane_h = int(rng.integers(max(4, cfg.height // 10), max(6, cfg.height // 8)))
    car_h = int(rng.integers(3, 5))
    car_w = int(rng.integers(2, 4))

    y = 2
    while y + lane_h + car_h + 2 < cfg.height - 2:
        y_cars_top = y
        y_lane = y + car_h

        x = 2
        while x + car_w + 2 < cfg.width - 2:
            if rng.random() < 0.75:
                occ[y_cars_top : y_cars_top + car_h, x : x + car_w] = True
            if rng.random() < 0.75:
                occ[y_lane + lane_h : y_lane + lane_h + car_h, x : x + car_w] = True
            x += car_w + int(rng.integers(1, 3))

        y += lane_h + 2 * car_h + int(rng.integers(1, 3))

    density = float(rng.uniform(cfg.obstacle_density_range[0] * 0.8, cfg.obstacle_density_range[1]))
    _random_rectangles(occ, rng, density)
    _add_boundaries(occ)
    return occ


def _generate_deadend_map(cfg: MapConfig, rng: np.random.Generator) -> tuple[np.ndarray, Tuple[float, float, float], Tuple[float, float, float]]:
    """Cul-de-sac style map forcing a turn-around maneuver."""
    occ = np.ones((cfg.height, cfg.width), dtype=bool)
    _add_boundaries(occ)

    mid = cfg.height // 2 + int(rng.integers(-2, 3))
    half_w = int(rng.integers(3, 5))
    y0 = max(2, mid - half_w)
    y1 = min(cfg.height - 2, mid + half_w)

    # Main corridor
    x_entry = 2
    x_end = cfg.width - 8
    occ[y0:y1, x_entry:x_end] = False

    # Dead-end bulb where heading change is required.
    bulb_h = int(rng.integers(8, 12))
    by0 = max(2, mid - bulb_h // 2)
    by1 = min(cfg.height - 2, by0 + bulb_h)
    bx0 = cfg.width - 16
    bx1 = cfg.width - 4
    occ[by0:by1, bx0:bx1] = False

    # Add sparse clutter around the corridor.
    clutter = np.zeros_like(occ)
    density = float(rng.uniform(0.01, 0.04))
    _random_rectangles(clutter, rng, density)
    occ = np.logical_or(occ, np.logical_and(clutter, np.ones_like(occ, dtype=bool)))
    occ[y0:y1, x_entry:x_end] = False
    occ[by0:by1, bx0:bx1] = False
    _add_boundaries(occ)

    start = ((x_entry + 2.0) * cfg.resolution, (mid + 0.5) * cfg.resolution, 0.0)
    goal_y = float((by0 + by1) * 0.5) * cfg.resolution
    goal = ((bx1 - 3.0) * cfg.resolution, goal_y, np.pi)
    return occ, start, goal


def sample_start_goal(
    occ: np.ndarray,
    resolution: float,
    min_dist_m: float,
    rng: np.random.Generator,
    max_tries: int = 2000,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    free = np.argwhere(~occ)
    if free.shape[0] < 2:
        raise RuntimeError("No free cells available for start/goal sampling")

    min_dist_cell = min_dist_m / resolution
    for _ in range(max_tries):
        id_a = int(rng.integers(0, free.shape[0]))
        id_b = int(rng.integers(0, free.shape[0]))
        if id_a == id_b:
            continue

        ya, xa = free[id_a]
        yb, xb = free[id_b]
        dist = np.hypot(xa - xb, ya - yb)
        if dist < min_dist_cell:
            continue

        start = ((xa + 0.5) * resolution, (ya + 0.5) * resolution, float(rng.uniform(-np.pi, np.pi)))
        goal = ((xb + 0.5) * resolution, (yb + 0.5) * resolution, float(rng.uniform(-np.pi, np.pi)))
        return start, goal

    raise RuntimeError("Unable to sample valid start/goal with distance constraint")


def scenario_to_category(scenario: str) -> str:
    if scenario == "random":
        return "A"
    if scenario == "narrow":
        return "B"
    return "C"


def generate_scene(
    cfg: MapConfig,
    min_start_goal_dist_m: float,
    rng: np.random.Generator,
    scenario: str | None = None,
) -> Scene:
    scenario_types = ("random", "narrow", "parking", "deadend")
    chosen = scenario if scenario in scenario_types else scenario_types[int(rng.integers(0, len(scenario_types)))]

    if chosen == "random":
        occ = _generate_random_map(cfg, rng)
        start, goal = sample_start_goal(occ, cfg.resolution, min_start_goal_dist_m, rng)
    elif chosen == "narrow":
        occ = _generate_narrow_passage_map(cfg, rng)
        start, goal = sample_start_goal(occ, cfg.resolution, min_start_goal_dist_m, rng)
    elif chosen == "parking":
        occ = _generate_parking_map(cfg, rng)
        start, goal = sample_start_goal(occ, cfg.resolution, min_start_goal_dist_m, rng)
    elif chosen == "deadend":
        occ, start, goal = _generate_deadend_map(cfg, rng)
    else:
        raise ValueError(f"Unknown scenario: {chosen}")

    return Scene(occupancy=occ, start=start, goal=goal, scenario=chosen)


def generate_scene_from_category(
    cfg: MapConfig,
    min_start_goal_dist_m: float,
    rng: np.random.Generator,
    category: str,
) -> Scene:
    if category == "A":
        scenario = "random"
    elif category == "B":
        scenario = "narrow"
    elif category == "C":
        scenario = "deadend" if rng.random() < 0.5 else "parking"
    else:
        raise ValueError(f"Unknown category {category}")
    return generate_scene(cfg, min_start_goal_dist_m, rng, scenario=scenario)


def scenario_histogram(scenes: Dict[str, int]) -> str:
    parts = [f"{k}: {v}" for k, v in sorted(scenes.items())]
    return ", ".join(parts)
