from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from pathlib import Path
import sys
from typing import Any

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG, DatasetConfig, MapConfig, PlannerConfig, VehicleConfig
from env.esdf import compute_esdf
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from env.teacher import compute_2d_dijkstra_field, compute_nonholonomic_teacher, fill_unreachable


DIFF_TO_CAT = {"simple": "A", "medium": "B", "hard": "C"}
MODE_TO_ID = {"linear": 0, "turning": 1, "random_walk": 2}
ID_TO_MODE = {v: k for k, v in MODE_TO_ID.items()}
VALID_DIFFICULTIES = ("simple", "medium", "hard")
VALID_DISTRIBUTIONS = ("random", "cluster", "along_path")


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


def _draw_rect(occ: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    h, w = occ.shape
    xa = int(np.clip(min(x0, x1), 1, w - 2))
    xb = int(np.clip(max(x0, x1), 1, w - 2))
    ya = int(np.clip(min(y0, y1), 1, h - 2))
    yb = int(np.clip(max(y0, y1), 1, h - 2))
    occ[ya : yb + 1, xa : xb + 1] = True


def _draw_disk(occ: np.ndarray, cx: int, cy: int, r: int, value: bool = True) -> None:
    h, w = occ.shape
    x0 = max(1, cx - r)
    x1 = min(w - 2, cx + r)
    y0 = max(1, cy - r)
    y1 = min(h - 2, cy + r)
    yy, xx = np.mgrid[y0 : y1 + 1, x0 : x1 + 1]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    occ[y0 : y1 + 1, x0 : x1 + 1][mask] = value


def _paint_disk_float(grid: np.ndarray, cx: int, cy: int, r: int, value: float) -> None:
    h, w = grid.shape
    x0 = max(1, cx - r)
    x1 = min(w - 2, cx + r)
    y0 = max(1, cy - r)
    y1 = min(h - 2, cy + r)
    yy, xx = np.mgrid[y0 : y1 + 1, x0 : x1 + 1]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    sl = grid[y0 : y1 + 1, x0 : x1 + 1]
    np.maximum(sl, value, out=sl, where=mask)


def _safe_mean_occ(occ: np.ndarray) -> float:
    return float(np.mean(occ.astype(np.float32)))


def _density_range_for_diff(diff: str) -> tuple[float, float]:
    if diff == "simple":
        return 0.30, 0.42
    if diff == "medium":
        return 0.42, 0.56
    return 0.56, 0.70


def _zoom_center(arr: np.ndarray, scale: float, order: int, cval: float) -> np.ndarray:
    h, w = arr.shape
    if abs(scale - 1.0) < 1e-3:
        return arr.copy()
    z = ndimage.zoom(arr.astype(np.float32), zoom=scale, order=order)
    zh, zw = z.shape
    out = np.full((h, w), cval, dtype=np.float32)

    if zh >= h:
        y0 = (zh - h) // 2
        ys = slice(y0, y0 + h)
        yd = slice(0, h)
    else:
        y0 = (h - zh) // 2
        ys = slice(0, zh)
        yd = slice(y0, y0 + zh)

    if zw >= w:
        x0 = (zw - w) // 2
        xs = slice(x0, x0 + w)
        xd = slice(0, w)
    else:
        x0 = (w - zw) // 2
        xs = slice(0, zw)
        xd = slice(x0, x0 + zw)

    out[yd, xd] = z[ys, xs]
    return out


def _apply_augmentation(
    occ_static: np.ndarray,
    dynamic_risk: np.ndarray,
    context_masks: dict[str, np.ndarray],
    rng: np.random.Generator,
    difficulty: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    angle = float(rng.uniform(0.0, 360.0))
    scale = float(rng.uniform(0.8, 1.2))
    flip_lr = bool(rng.random() < 0.5)
    flip_ud = bool(rng.random() < 0.25)

    occ = ndimage.rotate(occ_static.astype(np.float32), angle, reshape=False, order=0, mode="constant", cval=1.0)
    risk = ndimage.rotate(dynamic_risk.astype(np.float32), angle, reshape=False, order=1, mode="constant", cval=0.0)

    transformed_masks: dict[str, np.ndarray] = {}
    for k, m in context_masks.items():
        mm = ndimage.rotate(m.astype(np.float32), angle, reshape=False, order=0, mode="constant", cval=0.0)
        transformed_masks[k] = mm

    if flip_lr:
        occ = np.fliplr(occ)
        risk = np.fliplr(risk)
        transformed_masks = {k: np.fliplr(v) for k, v in transformed_masks.items()}
    if flip_ud:
        occ = np.flipud(occ)
        risk = np.flipud(risk)
        transformed_masks = {k: np.flipud(v) for k, v in transformed_masks.items()}

    occ = _zoom_center(occ, scale=scale, order=0, cval=1.0)
    risk = _zoom_center(risk, scale=scale, order=1, cval=0.0)
    transformed_masks = {k: _zoom_center(v, scale=scale, order=0, cval=0.0) for k, v in transformed_masks.items()}

    # Sensor-style occupancy noise.
    if difficulty == "simple":
        noise_p = 0.003
    elif difficulty == "medium":
        noise_p = 0.006
    else:
        noise_p = 0.010
    flip = rng.random(occ.shape) < noise_p
    occ = np.logical_xor(occ > 0.5, flip)
    _add_boundaries(occ)

    risk = np.clip(risk + rng.normal(0.0, 0.015, size=risk.shape).astype(np.float32), 0.0, 1.0)
    out_masks = {k: (v > 0.5) for k, v in transformed_masks.items()}
    return occ.astype(bool), risk.astype(np.float32), out_masks, {
        "augment_angle_deg": angle,
        "augment_scale": scale,
        "augment_flip_lr": float(flip_lr),
        "augment_flip_ud": float(flip_ud),
    }


def _sample_vehicle_params(rng: np.random.Generator) -> tuple[VehicleConfig, dict[str, float | str]]:
    wheel_base = float(rng.uniform(1.5, 2.5))
    track_width = float(rng.uniform(0.8, 1.2))
    max_steer_deg = float(rng.uniform(30.0, 60.0))
    length = float(wheel_base + rng.uniform(1.6, 2.5))
    width = float(track_width + rng.uniform(0.45, 0.75))
    min_turn_radius = float(max(1.2, wheel_base / max(math.tan(math.radians(max_steer_deg)), 1e-3)))

    load_class = "heavy" if rng.random() < 0.35 else "light"
    load_factor = 1.35 if load_class == "heavy" else 1.0
    battery = float(rng.uniform(20.0, 100.0))
    battery_norm = (battery - 20.0) / 80.0

    max_speed_scale = float(0.75 + 0.25 * battery_norm)
    if load_class == "heavy":
        max_speed_scale *= 0.78
    steer_rate_scale = float(0.80 + 0.20 * battery_norm)
    if load_class == "heavy":
        steer_rate_scale *= 0.82

    veh = replace(
        DEFAULT_CONFIG.vehicle,
        wheel_base=wheel_base,
        length=length,
        width=width,
        max_steer_deg=max_steer_deg,
        min_turn_radius=min_turn_radius,
    )
    meta = {
        "vehicle_wheel_base": wheel_base,
        "vehicle_track_width": track_width,
        "vehicle_length": length,
        "vehicle_width": width,
        "vehicle_max_steer_deg": max_steer_deg,
        "vehicle_min_turn_radius": min_turn_radius,
        "vehicle_load_factor": float(load_factor),
        "vehicle_load_class": load_class,
        "vehicle_battery": battery,
        "vehicle_max_speed_scale": float(max_speed_scale),
        "vehicle_steer_rate_scale": float(steer_rate_scale),
    }
    return veh, meta


def _sample_planner_params(base: PlannerConfig, veh_meta: dict[str, float | str]) -> PlannerConfig:
    planner = replace(base)
    load_factor = float(veh_meta.get("vehicle_load_factor", 1.0))
    battery = float(veh_meta.get("vehicle_battery", 100.0))
    battery_penalty = (100.0 - battery) / 100.0

    planner.step_size = float(np.clip(base.step_size * (1.0 - 0.12 * (load_factor - 1.0)), 0.45, 0.90))
    planner.reverse_penalty = float(base.reverse_penalty * (1.0 + 0.22 * (load_factor - 1.0) + 0.10 * battery_penalty))
    planner.steer_penalty = float(base.steer_penalty * (1.0 + 0.18 * (load_factor - 1.0)))
    planner.steer_change_penalty = float(base.steer_change_penalty * (1.0 + 0.20 * (load_factor - 1.0) + 0.12 * battery_penalty))
    return planner


def _random_polyline_points(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    n = int(rng.integers(4, 7))
    xs = np.linspace(2, w - 3, n)
    ys = rng.uniform(2, h - 3, size=n)
    pts = np.stack([xs, ys], axis=1)
    return pts.astype(np.float32)


def _generate_dense_random(
    map_cfg: MapConfig,
    difficulty: str,
    distribution_mode: str,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    h, w = map_cfg.height, map_cfg.width
    occ = np.zeros((h, w), dtype=bool)
    _add_boundaries(occ)

    d0, d1 = _density_range_for_diff(difficulty)
    target = float(rng.uniform(d0, d1))

    cluster_centers = np.stack(
        [rng.integers(5, w - 5, size=4), rng.integers(5, h - 5, size=4)], axis=1
    ).astype(np.int32)
    path_pts = _random_polyline_points(h, w, rng)

    iters = 0
    while _safe_mean_occ(occ) < target and iters < 1200:
        iters += 1
        shape = int(rng.integers(0, 3))

        if distribution_mode == "cluster":
            c = cluster_centers[int(rng.integers(0, len(cluster_centers)))]
            cx = int(np.clip(rng.normal(c[0], 4.0), 2, w - 3))
            cy = int(np.clip(rng.normal(c[1], 4.0), 2, h - 3))
        elif distribution_mode == "along_path":
            k = int(rng.integers(0, path_pts.shape[0] - 1))
            t = float(rng.uniform(0.0, 1.0))
            p = (1.0 - t) * path_pts[k] + t * path_pts[k + 1]
            nx = path_pts[k + 1, 0] - path_pts[k, 0]
            ny = path_pts[k + 1, 1] - path_pts[k, 1]
            norm = float(math.hypot(nx, ny) + 1e-6)
            nx, ny = -ny / norm, nx / norm
            off = float(rng.uniform(-5.0, 5.0))
            cx = int(np.clip(p[0] + off * nx, 2, w - 3))
            cy = int(np.clip(p[1] + off * ny, 2, h - 3))
        else:
            cx = int(rng.integers(2, w - 2))
            cy = int(rng.integers(2, h - 2))

        if shape == 0:
            rw = int(rng.integers(max(2, w // 22), max(4, w // 8)))
            rh = int(rng.integers(max(2, h // 22), max(4, h // 8)))
            _draw_rect(occ, cx - rw // 2, cy - rh // 2, cx + rw // 2, cy + rh // 2)
        elif shape == 1:
            rr = int(rng.integers(2, max(3, min(h, w) // 10)))
            _draw_disk(occ, cx, cy, rr, value=True)
        else:
            rr = int(rng.integers(2, max(4, min(h, w) // 12)))
            _draw_disk(occ, cx, cy, rr, value=True)
            _draw_disk(occ, int(np.clip(cx + rng.integers(-rr, rr + 1), 2, w - 3)), int(np.clip(cy + rng.integers(-rr, rr + 1), 2, h - 3)), rr, value=True)

    # Waiting zone and local free buffers.
    wz_w = int(max(6, w * 0.18))
    wz_h = int(max(6, h * 0.18))
    _carve_rect(occ, 2, 2, 2 + wz_w, 2 + wz_h)
    _carve_rect(occ, w - 3 - wz_w, h - 3 - wz_h, w - 3, h - 3)

    waiting_a = np.zeros_like(occ)
    waiting_b = np.zeros_like(occ)
    waiting_a[2 : 2 + wz_h + 1, 2 : 2 + wz_w + 1] = True
    waiting_b[h - 3 - wz_h : h - 2, w - 3 - wz_w : w - 2] = True

    context = {
        "start_zone": waiting_a,
        "goal_zone": waiting_b,
    }
    _add_boundaries(occ)
    return occ, context


def _generate_narrow_passage(
    map_cfg: MapConfig,
    vehicle_width: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    h, w = map_cfg.height, map_cfg.width
    occ = np.ones((h, w), dtype=bool)
    _add_boundaries(occ)

    # Chambers.
    _carve_rect(occ, 2, 2, w // 3, h - 3)
    _carve_rect(occ, int(2 * w / 3), 2, w - 3, h - 3)

    ratio = float(rng.uniform(1.2, 1.5))
    corridor_w_m = max(vehicle_width * ratio, vehicle_width + 0.2)
    corridor_w = int(max(2, round(corridor_w_m / map_cfg.resolution)))
    y_mid = int(rng.integers(h // 4, 3 * h // 4))

    # Zig-zag bottleneck.
    x0 = w // 3
    x1 = int(2 * w / 3)
    y1 = int(np.clip(y_mid + rng.integers(-h // 8, h // 8 + 1), 2, h - 3))
    _carve_rect(occ, x0, y_mid - corridor_w // 2, (x0 + x1) // 2, y_mid + corridor_w // 2)
    _carve_rect(occ, (x0 + x1) // 2 - corridor_w // 2, min(y_mid, y1), (x0 + x1) // 2 + corridor_w // 2, max(y_mid, y1))
    _carve_rect(occ, (x0 + x1) // 2, y1 - corridor_w // 2, x1, y1 + corridor_w // 2)

    # Dead-end branches.
    for _ in range(int(rng.integers(2, 5))):
        bx = int(rng.integers(w // 3, 2 * w // 3))
        by = int(rng.integers(2, h - 2))
        blen = int(rng.integers(4, 10))
        if rng.random() < 0.5:
            _carve_rect(occ, bx, by, bx + blen, by + corridor_w // 2)
        else:
            _carve_rect(occ, bx - blen, by, bx, by + corridor_w // 2)

    left_zone = np.zeros_like(occ)
    right_zone = np.zeros_like(occ)
    left_zone[2 : h - 2, 2 : w // 3] = True
    right_zone[2 : h - 2, int(2 * w / 3) : w - 2] = True
    bottleneck = np.zeros_like(occ)
    bottleneck[:, w // 3 : int(2 * w / 3)] = True

    _add_boundaries(occ)
    return occ, {
        "start_zone": left_zone,
        "goal_zone": right_zone,
        "bottleneck_zone": bottleneck,
        "corridor_width_cells": np.full_like(occ, corridor_w, dtype=np.int32),
    }


def _generate_warehouse(map_cfg: MapConfig, rng: np.random.Generator) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    h, w = map_cfg.height, map_cfg.width
    occ = np.zeros((h, w), dtype=bool)
    _add_boundaries(occ)

    rack_w = int(max(2, w // 18))
    aisle_w = int(max(3, w // 12))
    y0 = 3
    while y0 < h - 5:
        x = 3
        while x + rack_w < w - 3:
            if rng.random() < 0.86:
                _draw_rect(occ, x, y0, x + rack_w, min(h - 3, y0 + int(rng.integers(4, 9))))
            x += rack_w + aisle_w
        y0 += int(rng.integers(5, 10))

    # Keep at least one open waiting/turning zone.
    _carve_rect(occ, 2, 2, w // 4, h // 4)
    _carve_rect(occ, w - 3 - w // 4, h - 3 - h // 4, w - 3, h - 3)

    start_zone = np.zeros_like(occ)
    goal_zone = np.zeros_like(occ)
    start_zone[2 : 2 + h // 4, 2 : 2 + w // 4] = True
    goal_zone[h - 3 - h // 4 : h - 2, w - 3 - w // 4 : w - 2] = True
    _add_boundaries(occ)
    return occ, {"start_zone": start_zone, "goal_zone": goal_zone}


def _generate_city_street(map_cfg: MapConfig, rng: np.random.Generator) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    h, w = map_cfg.height, map_cfg.width
    occ = np.ones((h, w), dtype=bool)
    _add_boundaries(occ)

    road_w = int(max(3, w // 12))
    vx = [int(i) for i in np.linspace(road_w + 2, w - road_w - 3, int(rng.integers(3, 6)))]
    hy = [int(i) for i in np.linspace(road_w + 2, h - road_w - 3, int(rng.integers(3, 6)))]

    for x in vx:
        _carve_rect(occ, x - road_w // 2, 1, x + road_w // 2, h - 2)
    for y in hy:
        _carve_rect(occ, 1, y - road_w // 2, w - 2, y + road_w // 2)

    # Add urban clutter / parked objects near roads.
    for _ in range(int(rng.integers(18, 40))):
        rw = int(rng.integers(2, max(4, w // 16)))
        rh = int(rng.integers(2, max(4, h // 16)))
        cx = int(rng.integers(2, w - 2))
        cy = int(rng.integers(2, h - 2))
        if rng.random() < 0.65:
            _draw_rect(occ, cx - rw // 2, cy - rh // 2, cx + rw // 2, cy + rh // 2)

    _carve_rect(occ, 2, 2, w // 5, h // 5)
    _carve_rect(occ, w - 3 - w // 5, h - 3 - h // 5, w - 3, h - 3)

    start_zone = np.zeros_like(occ)
    goal_zone = np.zeros_like(occ)
    start_zone[2 : 2 + h // 5, 2 : 2 + w // 5] = True
    goal_zone[h - 3 - h // 5 : h - 2, w - 3 - w // 5 : w - 2] = True
    _add_boundaries(occ)
    return occ, {"start_zone": start_zone, "goal_zone": goal_zone}


def _generate_unstructured(map_cfg: MapConfig, difficulty: str, rng: np.random.Generator) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    h, w = map_cfg.height, map_cfg.width
    noise = ndimage.gaussian_filter(rng.normal(size=(h, w)).astype(np.float32), sigma=float(rng.uniform(1.0, 3.0)))
    d0, d1 = _density_range_for_diff(difficulty)
    target = float(rng.uniform(d0, d1))
    thr = float(np.quantile(noise, 1.0 - target))
    occ = noise >= thr

    # Add irregular blobs and remove isolated noise.
    occ = ndimage.binary_opening(occ, structure=np.ones((2, 2), dtype=bool))
    occ = ndimage.binary_closing(occ, structure=np.ones((2, 2), dtype=bool))
    for _ in range(int(rng.integers(12, 25))):
        cx = int(rng.integers(2, w - 2))
        cy = int(rng.integers(2, h - 2))
        rr = int(rng.integers(2, max(3, min(h, w) // 11)))
        _draw_disk(occ, cx, cy, rr, value=bool(rng.random() < 0.65))

    _add_boundaries(occ)
    _carve_rect(occ, 2, 2, w // 6, h // 6)
    _carve_rect(occ, w - 3 - w // 6, h - 3 - h // 6, w - 3, h - 3)

    start_zone = np.zeros_like(occ)
    goal_zone = np.zeros_like(occ)
    start_zone[2 : 2 + h // 6, 2 : 2 + w // 6] = True
    goal_zone[h - 3 - h // 6 : h - 2, w - 3 - w // 6 : w - 2] = True
    return occ.astype(bool), {"start_zone": start_zone, "goal_zone": goal_zone}


def _generate_maze(map_cfg: MapConfig, branching: str, rng: np.random.Generator) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    h, w = map_cfg.height, map_cfg.width
    occ = np.ones((h, w), dtype=bool)

    # Odd-grid DFS maze carving.
    for y in range(1, h - 1, 2):
        for x in range(1, w - 1, 2):
            occ[y, x] = False

    visited = np.zeros((h, w), dtype=bool)
    stack = [(1, 1)]
    visited[1, 1] = True

    while stack:
        y, x = stack[-1]
        cand: list[tuple[int, int, int, int]] = []
        for dy, dx in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            ny, nx = y + dy, x + dx
            if ny <= 0 or ny >= h - 1 or nx <= 0 or nx >= w - 1:
                continue
            if not visited[ny, nx]:
                cand.append((ny, nx, y + dy // 2, x + dx // 2))
        if not cand:
            stack.pop()
            continue
        ny, nx, wy, wx = cand[int(rng.integers(0, len(cand)))]
        visited[ny, nx] = True
        occ[wy, wx] = False
        stack.append((ny, nx))

    # Add extra branches for multi-branch variant.
    extra = int(0.03 * h * w) if branching == "multi" else int(0.01 * h * w)
    for _ in range(extra):
        y = int(rng.integers(1, h - 1))
        x = int(rng.integers(1, w - 1))
        if (y + x) % 2 == 1:
            occ[y, x] = False

    # Widen corridors to remain drivable.
    free = ~occ
    free = ndimage.binary_dilation(free, iterations=1)
    occ = ~free

    _add_boundaries(occ)
    _carve_rect(occ, 2, 2, w // 6, h // 6)
    _carve_rect(occ, w - 3 - w // 6, h - 3 - h // 6, w - 3, h - 3)

    start_zone = np.zeros_like(occ)
    goal_zone = np.zeros_like(occ)
    start_zone[2 : 2 + h // 6, 2 : 2 + w // 6] = True
    goal_zone[h - 3 - h // 6 : h - 2, w - 3 - w // 6 : w - 2] = True
    return occ.astype(bool), {"start_zone": start_zone, "goal_zone": goal_zone}


def _generate_deadend_labyrinth(map_cfg: MapConfig, rng: np.random.Generator) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    h, w = map_cfg.height, map_cfg.width
    occ = np.ones((h, w), dtype=bool)
    _add_boundaries(occ)

    # Main corridor and a cul-de-sac pocket.
    mid = int(h // 2 + rng.integers(-3, 4))
    half_w = int(rng.integers(2, 5))
    y0 = max(2, mid - half_w)
    y1 = min(h - 2, mid + half_w)
    _carve_rect(occ, 2, y0, w - 10, y1)

    bx0 = int(w - rng.integers(20, 26))
    bx1 = w - 4
    by0 = int(np.clip(mid - rng.integers(5, 9), 2, h - 10))
    by1 = int(np.clip(by0 + rng.integers(8, 14), by0 + 4, h - 2))
    _carve_rect(occ, bx0, by0, bx1, by1)

    for _ in range(int(rng.integers(8, 16))):
        x = int(rng.integers(4, w - 6))
        y = int(rng.integers(4, h - 6))
        if rng.random() < 0.6:
            _draw_rect(occ, x - 2, y - 1, x + 2, y + 1)

    _carve_rect(occ, 2, y0, w - 10, y1)
    _carve_rect(occ, bx0, by0, bx1, by1)

    pocket = np.zeros_like(occ)
    pocket[by0:by1, bx0:bx1] = True
    outside = np.zeros_like(occ)
    outside[y0:y1, 2 : max(3, bx0 - 2)] = True
    return occ, {"start_zone": pocket, "goal_zone": outside, "deadend_zone": pocket}


def _generate_static_map(
    map_cfg: MapConfig,
    difficulty: str,
    template: str,
    distribution_mode: str,
    vehicle_width: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    if template == "dense_random":
        return _generate_dense_random(map_cfg, difficulty=difficulty, distribution_mode=distribution_mode, rng=rng)
    if template == "narrow_passage":
        return _generate_narrow_passage(map_cfg, vehicle_width=vehicle_width, rng=rng)
    if template == "maze_single":
        return _generate_maze(map_cfg, branching="single", rng=rng)
    if template == "maze_multi":
        return _generate_maze(map_cfg, branching="multi", rng=rng)
    if template == "warehouse":
        return _generate_warehouse(map_cfg, rng=rng)
    if template == "city_street":
        return _generate_city_street(map_cfg, rng=rng)
    if template == "deadend_labyrinth":
        return _generate_deadend_labyrinth(map_cfg, rng=rng)
    if template == "unstructured":
        return _generate_unstructured(map_cfg, difficulty=difficulty, rng=rng)
    raise ValueError(f"Unknown template: {template}")


def _sample_dynamic_obstacles(
    occ_static: np.ndarray,
    resolution: float,
    difficulty: str,
    rng: np.random.Generator,
    horizon_steps: int,
    dt: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    h, w = occ_static.shape
    free = np.argwhere(~occ_static)
    if free.shape[0] < 10:
        return np.zeros((h, w), dtype=np.float32), {
            "dynamic_count": 0,
            "dynamic_modes": [],
            "dynamic_tracks": np.zeros((0, horizon_steps, 2), dtype=np.float32),
            "dynamic_radii_m": np.zeros((0,), dtype=np.float32),
            "dynamic_active": np.zeros((0, 2), dtype=np.int32),
            "dynamic_speed_mps": np.zeros((0,), dtype=np.float32),
        }

    if difficulty == "simple":
        n_dyn = int(rng.integers(0, 3))
    elif difficulty == "medium":
        n_dyn = int(rng.integers(2, 6))
    else:
        n_dyn = int(rng.integers(4, 9))

    risk = np.zeros((h, w), dtype=np.float32)
    tracks = np.zeros((n_dyn, horizon_steps, 2), dtype=np.float32)
    radii = np.zeros((n_dyn,), dtype=np.float32)
    active = np.zeros((n_dyn, 2), dtype=np.int32)
    speeds = np.zeros((n_dyn,), dtype=np.float32)
    mode_ids = np.zeros((n_dyn,), dtype=np.int32)

    for i in range(n_dyn):
        yx = free[int(rng.integers(0, free.shape[0]))]
        y = float(yx[0] + 0.5)
        x = float(yx[1] + 0.5)
        heading = float(rng.uniform(-math.pi, math.pi))
        speed = float(rng.uniform(0.2, 1.8))
        r_cells = int(rng.integers(1, 3 if difficulty != "hard" else 4))

        mode = str(rng.choice(["linear", "turning", "random_walk"]))
        mode_ids[i] = MODE_TO_ID[mode]
        start_t = int(rng.integers(0, max(1, horizon_steps // 3)))
        end_t = int(rng.integers(max(start_t + 3, horizon_steps // 2), horizon_steps + 1))
        active[i] = np.array([start_t, min(end_t, horizon_steps)], dtype=np.int32)
        speeds[i] = speed
        radii[i] = float(r_cells * resolution)

        vx = math.cos(heading) * speed / resolution
        vy = math.sin(heading) * speed / resolution

        px, py = x, y
        for t in range(horizon_steps):
            if t < start_t or t >= end_t:
                tracks[i, t] = np.array([np.nan, np.nan], dtype=np.float32)
                continue

            if mode == "turning":
                heading += float(rng.uniform(-0.22, 0.22))
                vx = math.cos(heading) * speed / resolution
                vy = math.sin(heading) * speed / resolution
            elif mode == "random_walk":
                vx += float(rng.normal(0.0, 0.18))
                vy += float(rng.normal(0.0, 0.18))
                mag = float(math.hypot(vx, vy))
                vmax = speed / resolution * 1.4
                if mag > vmax and mag > 1e-6:
                    s = vmax / mag
                    vx *= s
                    vy *= s

            nx = px + vx * dt
            ny = py + vy * dt

            bounced = False
            if nx < 1.5 or nx >= w - 1.5:
                vx *= -1.0
                nx = px + vx * dt
                bounced = True
            if ny < 1.5 or ny >= h - 1.5:
                vy *= -1.0
                ny = py + vy * dt
                bounced = True

            cx = int(np.clip(round(nx - 0.5), 1, w - 2))
            cy = int(np.clip(round(ny - 0.5), 1, h - 2))
            if occ_static[cy, cx]:
                vx *= -1.0
                vy *= -1.0
                nx = px + vx * dt
                ny = py + vy * dt
                bounced = True

            if bounced and mode == "turning":
                heading = float(math.atan2(vy, vx))

            px, py = nx, ny
            tracks[i, t] = np.array([(px + 0.5) * resolution, (py + 0.5) * resolution], dtype=np.float32)

            ccx = int(np.clip(round(px - 0.5), 1, w - 2))
            ccy = int(np.clip(round(py - 0.5), 1, h - 2))
            _paint_disk_float(risk, ccx, ccy, r_cells, value=1.0)

    # Temporal occupancy frequency proxy.
    risk = np.clip(ndimage.gaussian_filter(risk, sigma=0.8), 0.0, 1.0).astype(np.float32)
    meta = {
        "dynamic_count": int(n_dyn),
        "dynamic_modes": [ID_TO_MODE[int(v)] for v in mode_ids.tolist()],
        "dynamic_tracks": tracks,
        "dynamic_radii_m": radii.astype(np.float32),
        "dynamic_active": active.astype(np.int32),
        "dynamic_speed_mps": speeds.astype(np.float32),
        "dynamic_mode_ids": mode_ids.astype(np.int32),
    }
    return risk, meta


def _dynamic_risk_from_tracks_step(
    tracks: np.ndarray,
    radii_m: np.ndarray,
    resolution: float,
    h: int,
    w: int,
    step_idx: int,
) -> np.ndarray:
    risk = np.zeros((h, w), dtype=np.float32)
    if tracks.size == 0 or tracks.ndim != 3 or tracks.shape[-1] != 2:
        return risk
    if step_idx < 0 or step_idx >= tracks.shape[1]:
        return risk
    radii = np.asarray(radii_m, dtype=np.float32).reshape(-1)
    if radii.shape[0] < tracks.shape[0]:
        pad = np.full((tracks.shape[0] - radii.shape[0],), resolution, dtype=np.float32)
        radii = np.concatenate([radii, pad], axis=0)

    for i in range(tracks.shape[0]):
        x = float(tracks[i, step_idx, 0])
        y = float(tracks[i, step_idx, 1])
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        gx = int(np.clip(np.floor(x / resolution), 1, w - 2))
        gy = int(np.clip(np.floor(y / resolution), 1, h - 2))
        r_cells = int(max(1, np.ceil(float(radii[i]) / max(resolution, 1e-6))))
        _paint_disk_float(risk, gx, gy, r_cells, value=1.0)
    return np.clip(ndimage.gaussian_filter(risk, sigma=0.7), 0.0, 1.0).astype(np.float32)


def _sample_pose_from_cells(cells: np.ndarray, resolution: float, rng: np.random.Generator) -> tuple[float, float, float]:
    yx = cells[int(rng.integers(0, cells.shape[0]))]
    y, x = int(yx[0]), int(yx[1])
    return (float((x + 0.5) * resolution), float((y + 0.5) * resolution), float(rng.uniform(-math.pi, math.pi)))


def _line_risk_mean(risk: np.ndarray, a: tuple[float, float], b: tuple[float, float], resolution: float, n: int = 80) -> float:
    h, w = risk.shape
    xs = np.linspace(a[0], b[0], n)
    ys = np.linspace(a[1], b[1], n)
    gx = np.clip(np.floor(xs / resolution).astype(np.int32), 0, w - 1)
    gy = np.clip(np.floor(ys / resolution).astype(np.int32), 0, h - 1)
    vals = risk[gy, gx]
    return float(np.mean(vals))


def _sample_reachable_pair(
    occ: np.ndarray,
    resolution: float,
    fill_value: float,
    rng: np.random.Generator,
    min_dist: float,
    max_dist: float | None,
    start_mask: np.ndarray | None,
    goal_mask: np.ndarray | None,
    risk_map: np.ndarray | None,
    min_line_risk: float | None,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    free = ~occ
    if not np.any(free):
        return None

    if goal_mask is not None:
        g_cells = np.argwhere(free & goal_mask)
    else:
        g_cells = np.argwhere(free)
    if g_cells.shape[0] == 0:
        return None

    if start_mask is not None:
        s_pool = np.argwhere(free & start_mask)
    else:
        s_pool = np.argwhere(free)
    if s_pool.shape[0] == 0:
        return None

    for _ in range(60):
        gyx = g_cells[int(rng.integers(0, g_cells.shape[0]))]
        gy, gx = int(gyx[0]), int(gyx[1])
        goal_xy = ((gx + 0.5) * resolution, (gy + 0.5) * resolution)

        dfield = compute_2d_dijkstra_field(occ, goal_xy, resolution)
        dfield = fill_unreachable(dfield, occ, fill_value)

        if start_mask is not None:
            cand = np.argwhere((~occ) & start_mask & np.isfinite(dfield) & (dfield < 0.95 * fill_value))
        else:
            cand = np.argwhere((~occ) & np.isfinite(dfield) & (dfield < 0.95 * fill_value))
        if cand.shape[0] == 0:
            continue

        meters = dfield[cand[:, 0], cand[:, 1]]
        ok = meters >= min_dist
        if max_dist is not None:
            ok = ok & (meters <= max_dist)
        idx = np.where(ok)[0]
        if idx.size == 0:
            continue
        sy, sx = cand[int(idx[int(rng.integers(0, idx.size))])]

        start_xy = ((sx + 0.5) * resolution, (sy + 0.5) * resolution)
        if min_line_risk is not None and risk_map is not None:
            if _line_risk_mean(risk_map, start_xy, goal_xy, resolution=resolution) < min_line_risk:
                continue

        start = (float(start_xy[0]), float(start_xy[1]), float(rng.uniform(-math.pi, math.pi)))
        goal = (float(goal_xy[0]), float(goal_xy[1]), float(rng.uniform(-math.pi, math.pi)))
        return start, goal

    return None


def _sample_task(
    occ: np.ndarray,
    context: dict[str, np.ndarray],
    risk_map: np.ndarray,
    resolution: float,
    fill_value: float,
    task_type: str,
    rng: np.random.Generator,
) -> tuple[tuple[float, float, float], tuple[float, float, float], np.ndarray] | None:
    if task_type == "short_straight":
        pair = _sample_reachable_pair(occ, resolution, fill_value, rng, min_dist=6.0, max_dist=14.0, start_mask=context.get("start_zone"), goal_mask=context.get("goal_zone"), risk_map=None, min_line_risk=None)
    elif task_type == "long_detour":
        pair = _sample_reachable_pair(occ, resolution, fill_value, rng, min_dist=16.0, max_dist=None, start_mask=context.get("start_zone"), goal_mask=context.get("goal_zone"), risk_map=None, min_line_risk=None)
    elif task_type == "narrow_passage":
        pair = _sample_reachable_pair(occ, resolution, fill_value, rng, min_dist=10.0, max_dist=None, start_mask=context.get("start_zone"), goal_mask=context.get("goal_zone"), risk_map=None, min_line_risk=None)
    elif task_type == "dynamic_avoid":
        pair = _sample_reachable_pair(occ, resolution, fill_value, rng, min_dist=10.0, max_dist=None, start_mask=context.get("start_zone"), goal_mask=context.get("goal_zone"), risk_map=risk_map, min_line_risk=0.08)
    elif task_type == "deadend_reverse":
        pair = _sample_reachable_pair(occ, resolution, fill_value, rng, min_dist=8.0, max_dist=None, start_mask=context.get("deadend_zone", context.get("start_zone")), goal_mask=context.get("goal_zone"), risk_map=None, min_line_risk=None)
    else:
        pair = _sample_reachable_pair(occ, resolution, fill_value, rng, min_dist=10.0, max_dist=None, start_mask=context.get("start_zone"), goal_mask=context.get("goal_zone"), risk_map=None, min_line_risk=None)

    if pair is None:
        return None
    start, goal = pair

    if task_type != "multi_goal":
        seq = np.asarray([goal], dtype=np.float32)
        return start, goal, seq

    free = np.argwhere(~occ)
    if free.shape[0] < 8:
        return start, goal, np.asarray([goal], dtype=np.float32)

    goals = [goal]
    tries = 0
    while len(goals) < 3 and tries < 120:
        tries += 1
        g = _sample_pose_from_cells(free, resolution=resolution, rng=rng)
        if all(math.hypot(g[0] - gg[0], g[1] - gg[1]) > 4.0 for gg in goals):
            goals.append(g)
    seq = np.asarray(goals, dtype=np.float32)
    return start, goal, seq


def _derive_rs_base(
    occupancy: np.ndarray,
    esdf: np.ndarray,
    goal: tuple[float, float, float],
    teacher_3d: np.ndarray,
    map_cfg: MapConfig,
    ds_cfg: DatasetConfig,
    vehicle_cfg: VehicleConfig,
    planner_cfg: PlannerConfig,
    fill_value: float,
) -> np.ndarray:
    mode = str(ds_cfg.teacher_mode).lower()
    if mode in {"reeds_shepp_consistent", "rs_consistent", "reeds_shepp_costaware"}:
        base = teacher_3d.copy()
    elif mode in {"hybrid_rs_consistent_esdf", "hybrid_consistent", "rs_consistent_hybrid"}:
        obs = np.maximum(0.0, float(ds_cfg.hybrid_obstacle_threshold_m) - np.maximum(esdf, 0.0)).astype(np.float32)
        base = (teacher_3d - float(ds_cfg.hybrid_obstacle_alpha) * obs[None, ...]).astype(np.float32)
    else:
        cost_cfg = RSConsistentCostConfig.from_configs(vehicle_cfg=vehicle_cfg, planner_cfg=planner_cfg)
        base = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal,
            resolution=map_cfg.resolution,
            yaw_bins=int(teacher_3d.shape[0]),
            rho=vehicle_cfg.min_turn_radius,
            fill_value=fill_value,
            step_size=ds_cfg.teacher_rs_step_size,
            backend=ds_cfg.teacher_rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=cost_cfg,
        )
    base[:, occupancy] = fill_value
    base = np.where(np.isfinite(base), base, fill_value).astype(np.float32)
    return base


def _clear_split_dir(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in out_dir.glob("*.npz"):
        p.unlink()
    for p in out_dir.glob("*.vehicle.json"):
        p.unlink()
    for p in out_dir.glob("*.dynamic.json"):
        p.unlink()


def _save_sidecars(sample_path: Path, vehicle_meta: dict[str, Any], dyn_meta: dict[str, Any]) -> None:
    vehicle_path = sample_path.with_suffix(".vehicle.json")
    dyn_path = sample_path.with_suffix(".dynamic.json")

    with vehicle_path.open("w", encoding="utf-8") as f:
        json.dump(vehicle_meta, f, indent=2)

    compact_dyn = {
        "dynamic_count": int(dyn_meta.get("dynamic_count", 0)),
        "dynamic_modes": dyn_meta.get("dynamic_modes", []),
        "dynamic_radii_m": [float(v) for v in np.asarray(dyn_meta.get("dynamic_radii_m", []), dtype=np.float32).tolist()],
        "dynamic_speed_mps": [float(v) for v in np.asarray(dyn_meta.get("dynamic_speed_mps", []), dtype=np.float32).tolist()],
        "dynamic_active": np.asarray(dyn_meta.get("dynamic_active", []), dtype=np.int32).tolist(),
    }
    with dyn_path.open("w", encoding="utf-8") as f:
        json.dump(compact_dyn, f, indent=2)


def _difficulty_mix_for_split(split: str) -> dict[str, float]:
    if split == "train":
        return {"simple": 0.35, "medium": 0.40, "hard": 0.25}
    if split == "val":
        return {"simple": 0.25, "medium": 0.40, "hard": 0.35}
    return {"simple": 0.15, "medium": 0.35, "hard": 0.50}


def _template_pool_for_diff(diff: str) -> list[str]:
    if diff == "simple":
        return ["city_street", "warehouse", "dense_random"]
    if diff == "medium":
        return ["dense_random", "narrow_passage", "maze_multi", "unstructured", "city_street"]
    return ["narrow_passage", "maze_single", "deadend_labyrinth", "unstructured", "dense_random"]


def _task_pool_for_diff(diff: str) -> list[str]:
    if diff == "simple":
        return ["short_straight", "long_detour"]
    if diff == "medium":
        return ["long_detour", "narrow_passage", "dynamic_avoid", "multi_goal"]
    return ["narrow_passage", "dynamic_avoid", "deadend_reverse", "multi_goal", "long_detour"]


def _all_templates() -> list[str]:
    all_tpl = set(_template_pool_for_diff("simple"))
    all_tpl.update(_template_pool_for_diff("medium"))
    all_tpl.update(_template_pool_for_diff("hard"))
    return sorted(all_tpl)


def _all_tasks() -> list[str]:
    all_tasks = set(_task_pool_for_diff("simple"))
    all_tasks.update(_task_pool_for_diff("medium"))
    all_tasks.update(_task_pool_for_diff("hard"))
    return sorted(all_tasks)


def _parse_csv_values(raw: str | None) -> tuple[str, ...] | None:
    if raw is None:
        return None
    items = tuple(v.strip() for v in str(raw).split(",") if v.strip())
    return items if items else None


def _weighted_choice(
    weights: dict[str, float],
    rng: np.random.Generator,
    allowed: tuple[str, ...] | None = None,
) -> str:
    if allowed is not None:
        filtered = {k: float(v) for k, v in weights.items() if k in allowed}
        if not filtered:
            raise ValueError(f"No overlap between weights and allowed keys: {allowed}")
        weights = filtered
    keys = list(weights.keys())
    vals = np.asarray([float(weights[k]) for k in keys], dtype=np.float64)
    vals = vals / max(vals.sum(), 1e-6)
    return str(rng.choice(keys, p=vals))


def _generate_split(
    out_dir: Path,
    n_samples: int,
    split: str,
    map_cfg: MapConfig,
    ds_cfg: DatasetConfig,
    base_planner_cfg: PlannerConfig,
    seed: int,
    dynamic_horizon: int,
    dynamic_dt: float,
    use_augmentation: bool,
    include_rs_base: bool,
    difficulty_filter: tuple[str, ...] | None = None,
    template_filter: tuple[str, ...] | None = None,
    task_filter: tuple[str, ...] | None = None,
    distribution_filter: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    _clear_split_dir(out_dir)
    rng = np.random.default_rng(seed)
    fill_value = float(ds_cfg.max_teacher_value)

    if difficulty_filter is not None:
        bad = sorted(set(difficulty_filter) - set(VALID_DIFFICULTIES))
        if bad:
            raise ValueError(f"Unsupported difficulty values: {bad}. Valid: {list(VALID_DIFFICULTIES)}")
    if template_filter is not None:
        bad = sorted(set(template_filter) - set(_all_templates()))
        if bad:
            raise ValueError(f"Unsupported template values: {bad}.")
    if task_filter is not None:
        bad = sorted(set(task_filter) - set(_all_tasks()))
        if bad:
            raise ValueError(f"Unsupported task values: {bad}.")
    if distribution_filter is not None:
        bad = sorted(set(distribution_filter) - set(VALID_DISTRIBUTIONS))
        if bad:
            raise ValueError(f"Unsupported obstacle distribution values: {bad}. Valid: {list(VALID_DISTRIBUTIONS)}")

    distribution_pool = list(distribution_filter) if distribution_filter is not None else list(VALID_DISTRIBUTIONS)
    if not distribution_pool:
        raise ValueError("distribution_filter cannot be empty")

    stats_template: Counter[str] = Counter()
    stats_diff: Counter[str] = Counter()
    stats_task: Counter[str] = Counter()
    stats_dist: Counter[str] = Counter()

    created = 0
    tries = 0
    max_tries = max(6000, n_samples * 80)

    while created < n_samples and tries < max_tries:
        tries += 1
        difficulty = _weighted_choice(_difficulty_mix_for_split(split), rng, allowed=difficulty_filter)

        templates = _template_pool_for_diff(difficulty)
        if template_filter is not None:
            templates = [t for t in templates if t in template_filter]
            if not templates:
                templates = list(template_filter)
        template = str(rng.choice(templates))

        tasks = _task_pool_for_diff(difficulty)
        if task_filter is not None:
            tasks = [t for t in tasks if t in task_filter]
            if not tasks:
                tasks = list(task_filter)
        task_type = str(rng.choice(tasks))

        distribution_mode = str(rng.choice(distribution_pool))

        vehicle_cfg, vehicle_meta = _sample_vehicle_params(rng)
        planner_cfg = _sample_planner_params(base_planner_cfg, vehicle_meta)

        try:
            occ_static, context = _generate_static_map(
                map_cfg=map_cfg,
                difficulty=difficulty,
                template=template,
                distribution_mode=distribution_mode,
                vehicle_width=vehicle_cfg.width,
                rng=rng,
            )
        except Exception:
            continue

        dynamic_risk, dyn_meta = _sample_dynamic_obstacles(
            occ_static=occ_static,
            resolution=map_cfg.resolution,
            difficulty=difficulty,
            rng=rng,
            horizon_steps=dynamic_horizon,
            dt=dynamic_dt,
        )

        aug_meta: dict[str, float] = {}
        if use_augmentation:
            occ_static, dynamic_risk, context, aug_meta = _apply_augmentation(
                occ_static=occ_static,
                dynamic_risk=dynamic_risk,
                context_masks=context,
                rng=rng,
                difficulty=difficulty,
            )

        if difficulty == "simple":
            dyn_thr = float(rng.uniform(0.32, 0.45))
        elif difficulty == "medium":
            dyn_thr = float(rng.uniform(0.22, 0.35))
        else:
            dyn_thr = float(rng.uniform(0.15, 0.28))

        occupancy = np.logical_or(occ_static, dynamic_risk >= dyn_thr)
        _add_boundaries(occupancy)

        sampled = _sample_task(
            occ=occupancy,
            context=context,
            risk_map=dynamic_risk,
            resolution=map_cfg.resolution,
            fill_value=fill_value,
            task_type=task_type,
            rng=rng,
        )
        if sampled is None:
            continue

        start, goal, goal_seq = sampled

        sx = int(np.clip(np.floor(start[0] / map_cfg.resolution), 0, map_cfg.width - 1))
        sy = int(np.clip(np.floor(start[1] / map_cfg.resolution), 0, map_cfg.height - 1))
        gx = int(np.clip(np.floor(goal[0] / map_cfg.resolution), 0, map_cfg.width - 1))
        gy = int(np.clip(np.floor(goal[1] / map_cfg.resolution), 0, map_cfg.height - 1))
        if occupancy[sy, sx] or occupancy[gy, gx]:
            continue

        probe_2d = compute_2d_dijkstra_field(occupancy, (goal[0], goal[1]), map_cfg.resolution)
        probe_2d = fill_unreachable(probe_2d, occupancy, fill_value=fill_value)
        v0 = float(probe_2d[sy, sx])
        if not np.isfinite(v0) or v0 >= 0.95 * fill_value:
            continue

        esdf = compute_esdf(occupancy, map_cfg.resolution).astype(np.float32)
        if float(esdf[sy, sx]) <= 0.25 * vehicle_cfg.width or float(esdf[gy, gx]) <= 0.25 * vehicle_cfg.width:
            continue

        teacher_2d, teacher_3d, temporal_residual_3d = compute_nonholonomic_teacher(
            occupancy=occupancy,
            goal_pose=goal,
            resolution=map_cfg.resolution,
            yaw_bins=ds_cfg.teacher_yaw_bins,
            min_turn_radius=vehicle_cfg.min_turn_radius,
            fill_value=fill_value,
            teacher_mode=ds_cfg.teacher_mode,
            esdf=esdf,
            hybrid_obstacle_alpha=ds_cfg.hybrid_obstacle_alpha,
            hybrid_obstacle_threshold_m=ds_cfg.hybrid_obstacle_threshold_m,
            rs_backend=ds_cfg.teacher_rs_backend,
            rs_step_size=ds_cfg.teacher_rs_step_size,
            planner_cfg=planner_cfg,
            vehicle_cfg=vehicle_cfg,
            return_temporal_residual=True,
            temporal_indices=(0, 1, 2),
            dynamic_tracks=dyn_meta["dynamic_tracks"],
            dynamic_radii_m=dyn_meta["dynamic_radii_m"],
        )

        dynamic_risk_seq = np.stack(
            [
                _dynamic_risk_from_tracks_step(
                    tracks=dyn_meta["dynamic_tracks"],
                    radii_m=dyn_meta["dynamic_radii_m"],
                    resolution=map_cfg.resolution,
                    h=map_cfg.height,
                    w=map_cfg.width,
                    step_idx=0,
                ),
                _dynamic_risk_from_tracks_step(
                    tracks=dyn_meta["dynamic_tracks"],
                    radii_m=dyn_meta["dynamic_radii_m"],
                    resolution=map_cfg.resolution,
                    h=map_cfg.height,
                    w=map_cfg.width,
                    step_idx=1,
                ),
                _dynamic_risk_from_tracks_step(
                    tracks=dyn_meta["dynamic_tracks"],
                    radii_m=dyn_meta["dynamic_radii_m"],
                    resolution=map_cfg.resolution,
                    h=map_cfg.height,
                    w=map_cfg.width,
                    step_idx=2,
                ),
            ],
            axis=0,
        ).astype(np.float32)

        rs_base_3d = None
        if include_rs_base:
            rs_base_3d = _derive_rs_base(
                occupancy=occupancy,
                esdf=esdf,
                goal=goal,
                teacher_3d=teacher_3d,
                map_cfg=map_cfg,
                ds_cfg=ds_cfg,
                vehicle_cfg=vehicle_cfg,
                planner_cfg=planner_cfg,
                fill_value=fill_value,
            )

        category = DIFF_TO_CAT.get(difficulty, "C")
        sample_path = out_dir / f"sample_{created:05d}.npz"

        payload: dict[str, Any] = {
            "occupancy": occupancy.astype(np.uint8),
            "occupancy_static": occ_static.astype(np.uint8),
            "dynamic_risk": dynamic_risk.astype(np.float32),
            "dynamic_block_threshold": np.float32(dyn_thr),
            "esdf": esdf.astype(np.float32),
            "teacher": teacher_2d.astype(np.float32),
            "teacher_2d": teacher_2d.astype(np.float32),
            "teacher_3d": teacher_3d.astype(np.float32),
            "temporal_residual_3d": temporal_residual_3d.astype(np.float32),
            "start": np.asarray(start, dtype=np.float32),
            "goal": np.asarray(goal, dtype=np.float32),
            "goal_sequence": goal_seq.astype(np.float32),
            "resolution": np.float32(map_cfg.resolution),
            "fill_value": np.float32(fill_value),
            "scenario": np.array(template),
            "category": np.array(category),
            "difficulty": np.array(difficulty),
            "task_type": np.array(task_type),
            "obstacle_distribution": np.array(distribution_mode),
            "dynamic_tracks": dyn_meta["dynamic_tracks"].astype(np.float32),
            "dynamic_risk_seq": dynamic_risk_seq.astype(np.float32),
            "dynamic_radii_m": dyn_meta["dynamic_radii_m"].astype(np.float32),
            "dynamic_active": dyn_meta["dynamic_active"].astype(np.int32),
            "dynamic_speed_mps": dyn_meta["dynamic_speed_mps"].astype(np.float32),
            "dynamic_mode_ids": dyn_meta["dynamic_mode_ids"].astype(np.int32),
            "vehicle_wheel_base": np.float32(vehicle_meta["vehicle_wheel_base"]),
            "vehicle_track_width": np.float32(vehicle_meta["vehicle_track_width"]),
            "vehicle_length": np.float32(vehicle_meta["vehicle_length"]),
            "vehicle_width": np.float32(vehicle_meta["vehicle_width"]),
            "vehicle_max_steer_deg": np.float32(vehicle_meta["vehicle_max_steer_deg"]),
            "vehicle_min_turn_radius": np.float32(vehicle_meta["vehicle_min_turn_radius"]),
            "vehicle_load_factor": np.float32(vehicle_meta["vehicle_load_factor"]),
            "vehicle_battery": np.float32(vehicle_meta["vehicle_battery"]),
            "vehicle_max_speed_scale": np.float32(vehicle_meta["vehicle_max_speed_scale"]),
            "vehicle_steer_rate_scale": np.float32(vehicle_meta["vehicle_steer_rate_scale"]),
            "planner_step_size": np.float32(planner_cfg.step_size),
            "planner_reverse_penalty": np.float32(planner_cfg.reverse_penalty),
            "planner_steer_penalty": np.float32(planner_cfg.steer_penalty),
            "planner_steer_change_penalty": np.float32(planner_cfg.steer_change_penalty),
            **{k: np.float32(v) for k, v in aug_meta.items()},
        }
        if rs_base_3d is not None:
            payload["rs_base_3d"] = rs_base_3d.astype(np.float32)
        np.savez_compressed(sample_path, **payload)

        _save_sidecars(sample_path, vehicle_meta=vehicle_meta, dyn_meta=dyn_meta)

        created += 1
        stats_template[template] += 1
        stats_diff[difficulty] += 1
        stats_task[task_type] += 1
        stats_dist[distribution_mode] += 1

    if created < n_samples:
        raise RuntimeError(f"Could not generate split {split}: {created}/{n_samples}")

    summary = {
        "split": split,
        "num_samples": int(created),
        "template_histogram": dict(stats_template),
        "difficulty_histogram": dict(stats_diff),
        "task_histogram": dict(stats_task),
        "obstacle_distribution_histogram": dict(stats_dist),
        "teacher_mode": ds_cfg.teacher_mode,
        "teacher_yaw_bins": int(ds_cfg.teacher_yaw_bins),
        "teacher_rs_backend": ds_cfg.teacher_rs_backend,
        "teacher_rs_step_size": float(ds_cfg.teacher_rs_step_size),
        "hybrid_obstacle_alpha": float(ds_cfg.hybrid_obstacle_alpha),
        "hybrid_obstacle_threshold_m": float(ds_cfg.hybrid_obstacle_threshold_m),
        "dynamic_horizon": int(dynamic_horizon),
        "dynamic_dt": float(dynamic_dt),
        "include_rs_base": bool(include_rs_base),
        "difficulty_filter": list(difficulty_filter) if difficulty_filter is not None else None,
        "template_filter": list(template_filter) if template_filter is not None else None,
        "task_filter": list(task_filter) if task_filter is not None else None,
        "obstacle_distribution_filter": list(distribution_filter) if distribution_filter is not None else None,
        "map": {
            "height": int(map_cfg.height),
            "width": int(map_cfg.width),
            "resolution": float(map_cfg.resolution),
        },
    }

    with (out_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


def build_generalization_dataset(
    output_root: Path,
    train_count: int,
    val_count: int,
    test_count: int,
    seed: int,
    map_cfg: MapConfig,
    ds_cfg: DatasetConfig,
    planner_cfg: PlannerConfig,
    dynamic_horizon: int,
    dynamic_dt: float,
    use_augmentation: bool,
    include_rs_base: bool,
    difficulty_filter: tuple[str, ...] | None = None,
    template_filter: tuple[str, ...] | None = None,
    task_filter: tuple[str, ...] | None = None,
    distribution_filter: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    train_summary = _generate_split(
        out_dir=output_root / "train",
        n_samples=int(train_count),
        split="train",
        map_cfg=map_cfg,
        ds_cfg=ds_cfg,
        base_planner_cfg=planner_cfg,
        seed=seed + 101,
        dynamic_horizon=dynamic_horizon,
        dynamic_dt=dynamic_dt,
        use_augmentation=use_augmentation,
        include_rs_base=include_rs_base,
        difficulty_filter=difficulty_filter,
        template_filter=template_filter,
        task_filter=task_filter,
        distribution_filter=distribution_filter,
    )
    val_summary = _generate_split(
        out_dir=output_root / "val",
        n_samples=int(val_count),
        split="val",
        map_cfg=map_cfg,
        ds_cfg=ds_cfg,
        base_planner_cfg=planner_cfg,
        seed=seed + 202,
        dynamic_horizon=dynamic_horizon,
        dynamic_dt=dynamic_dt,
        use_augmentation=use_augmentation,
        include_rs_base=include_rs_base,
        difficulty_filter=difficulty_filter,
        template_filter=template_filter,
        task_filter=task_filter,
        distribution_filter=distribution_filter,
    )
    test_summary = _generate_split(
        out_dir=output_root / "test",
        n_samples=int(test_count),
        split="test",
        map_cfg=map_cfg,
        ds_cfg=ds_cfg,
        base_planner_cfg=planner_cfg,
        seed=seed + 303,
        dynamic_horizon=dynamic_horizon,
        dynamic_dt=dynamic_dt,
        use_augmentation=use_augmentation,
        include_rs_base=include_rs_base,
        difficulty_filter=difficulty_filter,
        template_filter=template_filter,
        task_filter=task_filter,
        distribution_filter=distribution_filter,
    )

    meta = {
        "seed": int(seed),
        "splits": {
            "train": train_summary,
            "val": val_summary,
            "test": test_summary,
        },
    }
    with (output_root / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generalization-oriented scenario generator")
    p.add_argument("--output", type=Path, default=Path("data"))
    p.add_argument("--train-count", type=int, default=1000)
    p.add_argument("--val-count", type=int, default=200)
    p.add_argument("--test-count", type=int, default=240)
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)

    p.add_argument("--map-width", type=int, default=DEFAULT_CONFIG.map.width)
    p.add_argument("--map-height", type=int, default=DEFAULT_CONFIG.map.height)
    p.add_argument("--resolution", type=float, default=DEFAULT_CONFIG.map.resolution)

    p.add_argument("--teacher-yaw-bins", type=int, default=8)
    p.add_argument(
        "--teacher-mode",
        type=str,
        default="dubins_proxy",
        choices=[
            "dubins",
            "dubins_proxy",
            "reeds_shepp",
            "reeds_shepp_consistent",
            "hybrid_rs_esdf",
            "hybrid_rs_consistent_esdf",
        ],
    )
    p.add_argument("--teacher-rs-backend", type=str, default="approx", choices=["auto", "rsplan", "approx"])
    p.add_argument("--teacher-rs-step-size", type=float, default=1.0)
    p.add_argument("--hybrid-alpha", type=float, default=0.15)
    p.add_argument("--hybrid-threshold", type=float, default=1.6)

    p.add_argument("--dynamic-horizon", type=int, default=24)
    p.add_argument("--dynamic-dt", type=float, default=0.45)
    p.add_argument(
        "--difficulty-filter",
        type=str,
        default="",
        help="Comma-separated subset of difficulties to sample from: simple,medium,hard",
    )
    p.add_argument(
        "--template-filter",
        type=str,
        default="",
        help="Comma-separated subset of templates to sample from",
    )
    p.add_argument(
        "--task-filter",
        type=str,
        default="",
        help="Comma-separated subset of task types to sample from",
    )
    p.add_argument(
        "--distribution-filter",
        type=str,
        default="",
        help="Comma-separated subset of obstacle distributions: random,cluster,along_path",
    )
    p.add_argument(
        "--include-rs-base",
        action="store_true",
        help="Compute and store rs_base_3d (required for residual training, slower).",
    )
    p.add_argument("--no-augmentation", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    cfg = DEFAULT_CONFIG
    map_cfg = replace(cfg.map)
    map_cfg.width = int(args.map_width)
    map_cfg.height = int(args.map_height)
    map_cfg.resolution = float(args.resolution)

    ds_cfg = replace(cfg.dataset)
    ds_cfg.teacher_yaw_bins = int(args.teacher_yaw_bins)
    ds_cfg.teacher_mode = str(args.teacher_mode)
    ds_cfg.teacher_rs_backend = str(args.teacher_rs_backend)
    ds_cfg.teacher_rs_step_size = float(args.teacher_rs_step_size)
    ds_cfg.hybrid_obstacle_alpha = float(args.hybrid_alpha)
    ds_cfg.hybrid_obstacle_threshold_m = float(args.hybrid_threshold)

    planner_cfg = replace(cfg.planner)

    difficulty_filter = _parse_csv_values(args.difficulty_filter)
    template_filter = _parse_csv_values(args.template_filter)
    task_filter = _parse_csv_values(args.task_filter)
    distribution_filter = _parse_csv_values(args.distribution_filter)

    meta = build_generalization_dataset(
        output_root=Path(args.output),
        train_count=int(args.train_count),
        val_count=int(args.val_count),
        test_count=int(args.test_count),
        seed=int(args.seed),
        map_cfg=map_cfg,
        ds_cfg=ds_cfg,
        planner_cfg=planner_cfg,
        dynamic_horizon=int(args.dynamic_horizon),
        dynamic_dt=float(args.dynamic_dt),
        use_augmentation=not bool(args.no_augmentation),
        include_rs_base=bool(args.include_rs_base),
        difficulty_filter=difficulty_filter,
        template_filter=template_filter,
        task_filter=task_filter,
        distribution_filter=distribution_filter,
    )

    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
