from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import torch
from scipy import ndimage

from rs_macro_rescue.config import DEFAULT_CONFIG
from rs_macro_rescue.planner.hybrid_astar import HybridAStarPlanner, PlanResult
from rs_macro_rescue.stack.base import CXGlobalConfig, normalize01
from rs_macro_rescue.stack.accepted import ACCEPTED_CX3D_PARAMS, accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_macro_rescue.utils.common import bilinear_interpolate, wrap_to_pi


@dataclass(frozen=True)
class PrimitiveIndex:
    steer_levels: tuple[float, ...]
    directions: tuple[int, ...]
    labels: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.labels)

    def to_level_direction(self, index: int) -> tuple[float, int]:
        idx = int(index)
        return float(self.steer_levels[idx]), int(self.directions[idx])

    def label(self, index: int) -> str:
        return self.labels[int(index)]

    def actual_steer(self, index: int, max_steer_rad: float) -> float:
        level, _ = self.to_level_direction(index)
        return float(level) * float(max_steer_rad)

    def actual_direction(self, index: int) -> int:
        _, direction = self.to_level_direction(index)
        return int(direction)


@dataclass(frozen=True)
class FitArtifact:
    model_path: Path
    meta_path: Path
    best_val_loss: float
    input_dim: int
    output_dim: int


class PrimitiveMLP(torch.nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden_dim: int = 96, dropout: float = 0.0) -> None:
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(int(input_dim), int(hidden_dim)),
            torch.nn.ReLU(inplace=True),
            torch.nn.Dropout(float(dropout)),
            torch.nn.Linear(int(hidden_dim), int(hidden_dim)),
            torch.nn.ReLU(inplace=True),
            torch.nn.Dropout(float(dropout)),
            torch.nn.Linear(int(hidden_dim), int(output_dim)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def primitive_index_from_planner(planner: HybridAStarPlanner) -> PrimitiveIndex:
    steer_levels = []
    directions = []
    labels = []
    max_steer = float(max(abs(float(s)) for s, _ in planner.motion_primitives)) if planner.motion_primitives else 1.0
    for steer, direction in planner.motion_primitives:
        level = 0.0 if max_steer <= 1e-6 else float(steer) / max_steer
        steer_levels.append(level)
        directions.append(int(direction))
        turn = 'L' if level < -1e-6 else ('R' if level > 1e-6 else 'S')
        travel = 'F' if int(direction) > 0 else 'B'
        labels.append(f'{travel}-{turn}')
    return PrimitiveIndex(tuple(steer_levels), tuple(directions), tuple(labels))


def primitive_index_from_case(case: dict[str, Any]) -> PrimitiveIndex:
    planner = HybridAStarPlanner(
        occupancy=case['occupancy'],
        resolution=float(case['resolution']),
        vehicle_cfg=case['vehicle'],
        planner_cfg=case['planner_cfg'],
        esdf=case['esdf'],
    )
    return primitive_index_from_planner(planner)


def _load_nonholonomic_case(path: Path) -> dict[str, Any]:
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

        vehicle_context = {
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
        "vehicle_context": vehicle_context,
    }


def _state_key_approx(state: tuple[float, float, float], resolution: float) -> tuple[int, int, int]:
    x, y, yaw = state
    gx = int(np.floor(float(x) / max(float(resolution), 1e-6)))
    gy = int(np.floor(float(y) / max(float(resolution), 1e-6)))
    yaw_bin = int(np.floor((wrap_to_pi(float(yaw)) + np.pi) / (2.0 * np.pi) * 72.0)) % 72
    return gx, gy, yaw_bin


def _sample2d(arr: np.ndarray, x: float, y: float, resolution: float, *, order: int = 1, cval: float = 0.0) -> float:
    grid_x = float(x) / max(float(resolution), 1e-6)
    grid_y = float(y) / max(float(resolution), 1e-6)
    if order == 1:
        return float(bilinear_interpolate(np.asarray(arr, dtype=np.float32), float(x), float(y), float(resolution)))
    return float(ndimage.map_coordinates(np.asarray(arr, dtype=np.float32), [[grid_y], [grid_x]], order=int(order), mode='constant', cval=float(cval))[0])


def _yaw_bin_from_state(field3d: np.ndarray, yaw: float) -> int:
    bins = int(field3d.shape[0]) if field3d.ndim == 3 else 1
    if bins <= 1:
        return 0
    return int(np.floor((wrap_to_pi(float(yaw)) + np.pi) / (2.0 * np.pi) * bins)) % bins


def query_yaw_field(field3d: np.ndarray, x: float, y: float, yaw: float, resolution: float) -> float:
    arr = np.asarray(field3d, dtype=np.float32)
    if arr.ndim == 2:
        return _sample2d(arr, x, y, resolution, order=1, cval=float(DEFAULT_CONFIG.dataset.max_teacher_value))
    idx = _yaw_bin_from_state(arr, yaw)
    return _sample2d(arr[idx], x, y, resolution, order=1, cval=float(DEFAULT_CONFIG.dataset.max_teacher_value))


def _field_value_channel(field2d: np.ndarray) -> np.ndarray:
    arr = np.asarray(field2d, dtype=np.float32)
    finite = np.isfinite(arr)
    if not np.any(finite):
        return np.zeros_like(arr, dtype=np.float32)
    clipped = np.clip(arr[finite], 0.0, np.quantile(arr[finite], 0.98))
    scale = float(max(np.mean(clipped) + 1e-6, 1.0))
    out = np.exp(-np.clip(arr, 0.0, 5.0 * scale) / scale).astype(np.float32)
    out[~finite] = 0.0
    return out


def build_ego_patch(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state: tuple[float, float, float],
    patch_radius: int = 5,
) -> np.ndarray:
    radius = int(max(patch_radius, 1))
    side = 2 * radius + 1
    x, y, yaw = map(float, state)
    resolution = float(case['resolution'])
    grid = np.arange(-radius, radius + 1, dtype=np.float32)
    local_x, local_y = np.meshgrid(grid, grid)
    dx = local_x * resolution
    dy = local_y * resolution
    c = math.cos(yaw)
    s = math.sin(yaw)
    world_x = x + dx * c - dy * s
    world_y = y + dx * s + dy * c
    coords = np.stack([world_y / resolution, world_x / resolution], axis=0)

    occ = ndimage.map_coordinates(case['occupancy'].astype(np.float32), coords, order=0, mode='constant', cval=1.0)
    esdf = ndimage.map_coordinates(np.maximum(case['esdf'], 0.0).astype(np.float32), coords, order=1, mode='constant', cval=0.0)
    focus = ndimage.map_coordinates(bundle['focus'].astype(np.float32), coords, order=1, mode='constant', cval=0.0)
    barrier = ndimage.map_coordinates(bundle['barrier'].astype(np.float32), coords, order=1, mode='constant', cval=0.0)
    corridor = ndimage.map_coordinates(bundle['corridor'].astype(np.float32), coords, order=1, mode='constant', cval=0.0)
    field_slice = field3d if field3d.ndim == 2 else field3d[_yaw_bin_from_state(np.asarray(field3d), yaw)]
    field_val = ndimage.map_coordinates(_field_value_channel(field_slice).astype(np.float32), coords, order=1, mode='constant', cval=0.0)

    patch = np.stack([
        occ.astype(np.float32),
        normalize01(esdf).astype(np.float32),
        focus.astype(np.float32),
        barrier.astype(np.float32),
        corridor.astype(np.float32),
        field_val.astype(np.float32),
    ], axis=0)
    assert patch.shape == (6, side, side)
    return patch.astype(np.float32)


def _patch_summary_features(patch: np.ndarray) -> np.ndarray:
    arr = np.asarray(patch, dtype=np.float32)
    feats: list[float] = []
    ch, h, w = arr.shape
    mid_h = h // 2
    mid_w = w // 2
    quadrants = [
        arr[:, :mid_h + 1, :mid_w + 1],
        arr[:, :mid_h + 1, mid_w:],
        arr[:, mid_h:, :mid_w + 1],
        arr[:, mid_h:, mid_w:],
    ]
    for c in range(ch):
        feats.extend([
            float(np.mean(arr[c])),
            float(np.std(arr[c])),
            float(np.mean(arr[c, :mid_h + 1, :])),
            float(np.mean(arr[c, mid_h:, :])),
            float(np.mean(arr[c, :, :mid_w + 1])),
            float(np.mean(arr[c, :, mid_w:])),
        ])
        for q in quadrants:
            feats.append(float(np.mean(q[c])))
    return np.asarray(feats, dtype=np.float32)


def _local_goal_features(case: dict[str, Any], state: tuple[float, float, float]) -> np.ndarray:
    x, y, yaw = map(float, state)
    gx, gy, gyaw = map(float, case['goal'])
    dx = gx - x
    dy = gy - y
    dist = math.hypot(dx, dy)
    goal_dir = math.atan2(dy, dx)
    heading_err = wrap_to_pi(goal_dir - yaw)
    goal_yaw_err = wrap_to_pi(gyaw - yaw)
    return np.asarray([
        float(dist),
        float(math.cos(heading_err)),
        float(math.sin(heading_err)),
        float(math.cos(goal_yaw_err)),
        float(math.sin(goal_yaw_err)),
    ], dtype=np.float32)


def simulate_primitive_detailed(
    case: dict[str, Any],
    state: tuple[float, float, float],
    steer: float,
    direction: int,
) -> dict[str, Any]:
    x, y, yaw = map(float, state)
    vehicle = case['vehicle']
    planner_cfg = case['planner_cfg']
    esdf = case['esdf']
    resolution = float(case['resolution'])
    clearance_floor = 0.35 * float(vehicle.width)
    n = max(1, int(np.ceil(float(planner_cfg.step_size) / max(float(planner_cfg.collision_check_step), 1e-6))))
    ds = float(planner_cfg.step_size) / float(n)
    cx, cy, cyaw = x, y, yaw
    clearances = []
    samples: list[tuple[float, float, float]] = []
    for _ in range(n):
        signed_ds = ds * int(direction)
        cx += signed_ds * math.cos(cyaw)
        cy += signed_ds * math.sin(cyaw)
        cyaw = wrap_to_pi(cyaw + signed_ds * math.tan(float(steer)) / max(float(vehicle.wheel_base), 1e-6))
        if cx < 0.0 or cy < 0.0 or cx >= esdf.shape[1] * resolution or cy >= esdf.shape[0] * resolution:
            return {'valid': False, 'next_state': None, 'min_clearance': -1.0, 'end_clearance': -1.0, 'samples': samples}
        clearance = _sample2d(esdf, cx, cy, resolution, order=1, cval=0.0)
        samples.append((float(cx), float(cy), float(cyaw)))
        clearances.append(float(clearance))
        if clearance <= clearance_floor:
            return {'valid': False, 'next_state': None, 'min_clearance': float(min(clearances) if clearances else -1.0), 'end_clearance': float(clearances[-1]), 'samples': samples}
    return {
        'valid': True,
        'next_state': (float(cx), float(cy), float(cyaw)),
        'min_clearance': float(min(clearances) if clearances else 0.0),
        'end_clearance': float(clearances[-1] if clearances else 0.0),
        'samples': samples,
    }


def reverse_escape_fraction(case: dict[str, Any], state: tuple[float, float, float], primitive_index: PrimitiveIndex) -> float:
    max_steer = math.radians(float(case['vehicle'].max_steer_deg))
    vals = []
    for idx in range(len(primitive_index)):
        if primitive_index.actual_direction(idx) >= 0:
            continue
        steer = primitive_index.actual_steer(idx, max_steer)
        sim = simulate_primitive_detailed(case, state, steer, -1)
        vals.append(1.0 if sim['valid'] else 0.0)
    return float(np.mean(vals)) if vals else 0.0


def forward_escape_fraction(case: dict[str, Any], state: tuple[float, float, float], primitive_index: PrimitiveIndex) -> float:
    max_steer = math.radians(float(case['vehicle'].max_steer_deg))
    vals = []
    for idx in range(len(primitive_index)):
        if primitive_index.actual_direction(idx) <= 0:
            continue
        steer = primitive_index.actual_steer(idx, max_steer)
        sim = simulate_primitive_detailed(case, state, steer, 1)
        vals.append(1.0 if sim['valid'] else 0.0)
    return float(np.mean(vals)) if vals else 0.0


def build_state_cache(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state: tuple[float, float, float],
    prev_steer: float,
    patch_radius: int,
    primitive_index: PrimitiveIndex | None = None,
    escape_features: tuple[float, float] | None = None,
) -> dict[str, Any]:
    x, y, yaw = map(float, state)
    primitive_index = primitive_index if primitive_index is not None else primitive_index_from_case(case)
    patch = build_ego_patch(case, bundle, field3d, state, patch_radius=patch_radius)
    patch_feat = _patch_summary_features(patch)
    current_clearance = _sample2d(case['esdf'], x, y, float(case['resolution']), order=1, cval=0.0)
    focus = _sample2d(bundle['focus'], x, y, float(case['resolution']), order=1, cval=0.0)
    barrier = _sample2d(bundle['barrier'], x, y, float(case['resolution']), order=1, cval=0.0)
    corridor = _sample2d(bundle['corridor'], x, y, float(case['resolution']), order=1, cval=0.0)
    morph = _sample2d(bundle['morph_width'], x, y, float(case['resolution']), order=1, cval=0.0)
    risk = _sample2d(bundle['risk'], x, y, float(case['resolution']), order=1, cval=0.0)
    anchor_here = query_yaw_field(field3d, x, y, yaw, float(case['resolution']))
    if escape_features is None:
        reverse_escape = float(reverse_escape_fraction(case, state, primitive_index))
        forward_escape = float(forward_escape_fraction(case, state, primitive_index))
    else:
        reverse_escape = float(escape_features[0])
        forward_escape = float(escape_features[1])
    extras = np.asarray([
        float(prev_steer),
        float(current_clearance),
        float(focus),
        float(barrier),
        float(corridor),
        float(morph),
        float(risk),
        float(anchor_here),
        float(reverse_escape),
        float(forward_escape),
    ], dtype=np.float32)
    state_vec = np.concatenate([patch.reshape(-1), patch_feat, _local_goal_features(case, state), extras], axis=0).astype(np.float32)
    return {
        'state': (float(x), float(y), float(yaw)),
        'prev_steer': float(prev_steer),
        'patch_radius': int(patch_radius),
        'primitive_index': primitive_index,
        'state_vec': state_vec,
        'anchor_here': float(anchor_here),
        'reverse_escape': float(reverse_escape),
        'forward_escape': float(forward_escape),
    }


def build_state_vector(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state: tuple[float, float, float],
    prev_steer: float,
    patch_radius: int,
) -> np.ndarray:
    return np.asarray(build_state_cache(case, bundle, field3d, state, prev_steer=prev_steer, patch_radius=patch_radius)['state_vec'], dtype=np.float32)


def build_state_action_vector_from_cache(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state_cache: dict[str, Any],
    primitive_index: int,
    *,
    sim: dict[str, Any] | None = None,
    next_state: tuple[float, float, float] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    state_vec = np.asarray(state_cache['state_vec'], dtype=np.float32)
    pindex = state_cache['primitive_index']
    prev_steer = float(state_cache['prev_steer'])
    max_steer = math.radians(float(case['vehicle'].max_steer_deg))
    steer = pindex.actual_steer(int(primitive_index), max_steer)
    direction = pindex.actual_direction(int(primitive_index))
    state = state_cache['state']
    if sim is None:
        sim = simulate_primitive_detailed(case, state, steer, direction)
    anchor_here = float(state_cache['anchor_here'])
    if next_state is None:
        next_state = sim.get('next_state', None)
    if sim.get('valid', False) and next_state is not None:
        nx, ny, nyaw = next_state
        anchor_next = query_yaw_field(field3d, nx, ny, nyaw, float(case['resolution']))
        focus_next = _sample2d(bundle['focus'], nx, ny, float(case['resolution']), order=1, cval=0.0)
        barrier_next = _sample2d(bundle['barrier'], nx, ny, float(case['resolution']), order=1, cval=0.0)
        corridor_next = _sample2d(bundle['corridor'], nx, ny, float(case['resolution']), order=1, cval=0.0)
        progress = float(anchor_here - anchor_next)
        next_goal = _local_goal_features(case, (nx, ny, nyaw))
    else:
        anchor_next = float(DEFAULT_CONFIG.dataset.max_teacher_value)
        focus_next = barrier_next = corridor_next = 0.0
        progress = -1e3
        next_goal = np.zeros(5, dtype=np.float32)
        next_state = None
    action_feat = np.asarray([
        float(primitive_index),
        float(steer / max(max_steer, 1e-6)),
        float(abs(steer) / max(max_steer, 1e-6)),
        float(direction),
        float(1.0 if direction < 0 else 0.0),
        float(prev_steer / max(max_steer, 1e-6)),
        float((steer - prev_steer) / max(max_steer, 1e-6)),
        float(1.0 if sim.get('valid', False) else 0.0),
        float(sim.get('min_clearance', -1.0)),
        float(sim.get('end_clearance', -1.0)),
        float(anchor_here),
        float(anchor_next),
        float(progress),
        float(focus_next),
        float(barrier_next),
        float(corridor_next),
    ], dtype=np.float32)
    feat = np.concatenate([state_vec, action_feat, next_goal], axis=0).astype(np.float32)
    meta = {
        'sim': sim,
        'steer': float(steer),
        'direction': int(direction),
        'anchor_here': float(anchor_here),
        'anchor_next': float(anchor_next),
        'progress': float(progress),
        'next_state': next_state,
    }
    return feat, meta


def build_state_action_vector(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state: tuple[float, float, float],
    prev_steer: float,
    primitive_index: int,
    patch_radius: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    state_cache = build_state_cache(case, bundle, field3d, state, prev_steer=prev_steer, patch_radius=patch_radius)
    return build_state_action_vector_from_cache(case, bundle, field3d, state_cache, primitive_index)


def build_compact_state_cache(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state: tuple[float, float, float],
    prev_steer: float,
    primitive_index: PrimitiveIndex | None = None,
    escape_features: tuple[float, float] | None = None,
) -> dict[str, Any]:
    x, y, yaw = map(float, state)
    primitive_index = primitive_index if primitive_index is not None else primitive_index_from_case(case)
    if escape_features is None:
        reverse_escape = float(reverse_escape_fraction(case, state, primitive_index))
        forward_escape = float(forward_escape_fraction(case, state, primitive_index))
    else:
        reverse_escape = float(escape_features[0])
        forward_escape = float(escape_features[1])
    state_vec = np.concatenate([
        _local_goal_features(case, state),
        np.asarray([
            float(prev_steer),
            float(_sample2d(case['esdf'], x, y, float(case['resolution']), order=1, cval=0.0)),
            float(_sample2d(bundle['focus'], x, y, float(case['resolution']), order=1, cval=0.0)),
            float(_sample2d(bundle['barrier'], x, y, float(case['resolution']), order=1, cval=0.0)),
            float(_sample2d(bundle['corridor'], x, y, float(case['resolution']), order=1, cval=0.0)),
            float(_sample2d(bundle['morph_width'], x, y, float(case['resolution']), order=1, cval=0.0)),
            float(_sample2d(bundle['risk'], x, y, float(case['resolution']), order=1, cval=0.0)),
            float(query_yaw_field(field3d, x, y, yaw, float(case['resolution']))),
            float(bundle['scene'].get('hard_likelihood', 0.0)),
            float(bundle['scene'].get('misc_likelihood', 0.0)),
            float(bundle['scene'].get('bridge_diffuse', 0.0)),
            float(bundle['scene'].get('path_openness', 0.0)),
            float(reverse_escape),
            float(forward_escape),
        ], dtype=np.float32),
    ], axis=0).astype(np.float32)
    return {
        'state': (float(x), float(y), float(yaw)),
        'prev_steer': float(prev_steer),
        'primitive_index': primitive_index,
        'state_vec': state_vec,
        'anchor_here': float(query_yaw_field(field3d, x, y, yaw, float(case['resolution']))),
        'reverse_escape': float(reverse_escape),
        'forward_escape': float(forward_escape),
    }


def build_kfm_compact_action_vector_from_cache(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state_cache: dict[str, Any],
    primitive_index: int,
    *,
    sim: dict[str, Any] | None = None,
    next_state: tuple[float, float, float] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    state_vec = np.asarray(state_cache['state_vec'], dtype=np.float32)
    pindex = state_cache['primitive_index']
    prev_steer = float(state_cache['prev_steer'])
    max_steer = math.radians(float(case['vehicle'].max_steer_deg))
    steer = pindex.actual_steer(int(primitive_index), max_steer)
    direction = pindex.actual_direction(int(primitive_index))
    state = state_cache['state']
    if sim is None:
        sim = simulate_primitive_detailed(case, state, steer, direction)
    if next_state is None:
        next_state = sim.get('next_state', None)
    anchor_here = float(state_cache['anchor_here'])
    if sim.get('valid', False) and next_state is not None:
        nx, ny, nyaw = next_state
        anchor_next = query_yaw_field(field3d, nx, ny, nyaw, float(case['resolution']))
        focus_next = _sample2d(bundle['focus'], nx, ny, float(case['resolution']), order=1, cval=0.0)
        barrier_next = _sample2d(bundle['barrier'], nx, ny, float(case['resolution']), order=1, cval=0.0)
        corridor_next = _sample2d(bundle['corridor'], nx, ny, float(case['resolution']), order=1, cval=0.0)
        clearance_next = _sample2d(case['esdf'], nx, ny, float(case['resolution']), order=1, cval=0.0)
        progress = float(anchor_here - anchor_next)
        next_goal = _local_goal_features(case, (nx, ny, nyaw))
    else:
        anchor_next = float(DEFAULT_CONFIG.dataset.max_teacher_value)
        focus_next = barrier_next = corridor_next = clearance_next = 0.0
        progress = -1e3
        next_goal = np.zeros(5, dtype=np.float32)
    feat = np.concatenate([
        state_vec,
        np.asarray([
            float(primitive_index),
            float(steer / max(max_steer, 1e-6)),
            float(abs(steer) / max(max_steer, 1e-6)),
            float(direction),
            float(1.0 if direction < 0 else 0.0),
            float(prev_steer / max(max_steer, 1e-6)),
            float((steer - prev_steer) / max(max_steer, 1e-6)),
            float(1.0 if sim.get('valid', False) else 0.0),
            float(sim.get('min_clearance', -1.0)),
            float(sim.get('end_clearance', -1.0)),
            float(clearance_next),
            float(anchor_next),
            float(progress),
            float(focus_next),
            float(barrier_next),
            float(corridor_next),
        ], dtype=np.float32),
        next_goal.astype(np.float32),
    ], axis=0).astype(np.float32)
    meta = {
        'sim': sim,
        'steer': float(steer),
        'direction': int(direction),
        'anchor_here': float(anchor_here),
        'anchor_next': float(anchor_next),
        'progress': float(progress),
        'next_state': next_state,
    }
    return feat, meta


def bottleneck_regime_score(case: dict[str, Any], bundle: dict[str, Any], field3d: np.ndarray, state: tuple[float, float, float]) -> float:
    x, y, yaw = map(float, state)
    clearance = _sample2d(case['esdf'], x, y, float(case['resolution']), order=1, cval=0.0)
    barrier = _sample2d(bundle['barrier'], x, y, float(case['resolution']), order=1, cval=0.0)
    focus = _sample2d(bundle['focus'], x, y, float(case['resolution']), order=1, cval=0.0)
    corridor = _sample2d(bundle['corridor'], x, y, float(case['resolution']), order=1, cval=0.0)
    _, goal_cos, goal_sin, _, _ = _local_goal_features(case, state)
    heading_misalignment = 1.0 - float(goal_cos)
    raw = 1.2 * barrier + 0.8 * focus + 0.6 * (1.0 - corridor) + 0.8 * heading_misalignment - 0.35 * clearance
    return float(1.0 / (1.0 + math.exp(-4.0 * raw)))


BUNDLE_LABELS = ('forward_left_thread', 'forward_right_thread', 'reverse_setup_left', 'reverse_setup_right')


def bundle_target_from_trace(trace: list[int], t: int, primitive_index: PrimitiveIndex) -> int | None:
    if t >= len(trace):
        return None
    first = int(trace[t])
    direction = primitive_index.actual_direction(first)
    level, _ = primitive_index.to_level_direction(first)
    if direction > 0 and level < -1e-6:
        return 0
    if direction > 0 and level > 1e-6:
        return 1
    if direction < 0 and t + 1 < len(trace):
        second = int(trace[t + 1])
        second_dir = primitive_index.actual_direction(second)
        second_level, _ = primitive_index.to_level_direction(second)
        if second_dir > 0 and second_level < -1e-6:
            return 2
        if second_dir > 0 and second_level > 1e-6:
            return 3
    return None


def build_bundle_feature_vector(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state: tuple[float, float, float],
    prev_steer: float,
    patch_radius: int,
) -> np.ndarray:
    base = build_state_vector(case, bundle, field3d, state, prev_steer=prev_steer, patch_radius=patch_radius)
    score = bottleneck_regime_score(case, bundle, field3d, state)
    return np.concatenate([base, np.asarray([float(score)], dtype=np.float32)], axis=0).astype(np.float32)


def build_compact_bundle_feature_vector(
    case: dict[str, Any],
    bundle: dict[str, Any],
    field3d: np.ndarray,
    state: tuple[float, float, float],
    prev_steer: float,
    primitive_index: PrimitiveIndex | None = None,
    escape_features: tuple[float, float] | None = None,
) -> np.ndarray:
    state_cache = build_compact_state_cache(
        case,
        bundle,
        field3d,
        state,
        prev_steer=prev_steer,
        primitive_index=primitive_index,
        escape_features=escape_features,
    )
    x, y, yaw = map(float, state)
    goal_feat = _local_goal_features(case, state)
    heading_align = float(goal_feat[1])
    goal_yaw_cos = float(goal_feat[3])
    curvature_slack = float(max(_sample2d(case['esdf'], x, y, float(case['resolution']), order=1, cval=0.0) - float(case['vehicle'].min_turn_radius) * 0.1, 0.0))
    bottleneck = float(bottleneck_regime_score(case, bundle, field3d, state))
    extra = np.asarray([
        float(bottleneck),
        float(prev_steer),
        float(abs(prev_steer)),
        float(heading_align),
        float(goal_yaw_cos),
        float(curvature_slack),
        float(bundle['scene'].get('hard_likelihood', 0.0)),
        float(bundle['scene'].get('misc_likelihood', 0.0)),
        float(bundle['scene'].get('bridge_diffuse', 0.0)),
    ], dtype=np.float32)
    return np.concatenate([np.asarray(state_cache['state_vec'], dtype=np.float32), extra], axis=0).astype(np.float32)


def run_hybrid_with_policy(
    case: dict[str, Any],
    anchor_field: np.ndarray,
    max_expansions: int,
    successor_policy: Any | None = None,
    record_expanded: bool = False,
) -> PlanResult:
    planner_cfg = case['planner_cfg']
    planner_cfg = type(planner_cfg)(**planner_cfg.__dict__)
    planner_cfg.max_expansions = int(max_expansions)
    planner = HybridAStarPlanner(
        occupancy=case['occupancy'],
        resolution=float(case['resolution']),
        vehicle_cfg=case['vehicle'],
        planner_cfg=planner_cfg,
        esdf=case['esdf'],
    )
    from rs_macro_rescue.planner.heuristics import YawFieldHeuristic

    anchor_fn = YawFieldHeuristic(
        field_3d=np.asarray(anchor_field, dtype=np.float32),
        resolution=float(case['resolution']),
        max_value=float(DEFAULT_CONFIG.dataset.max_teacher_value),
        scale=1.0,
    )
    return planner.plan(
        start=tuple(map(float, case['start'])),
        goal=tuple(map(float, case['goal'])),
        anchor_fn=anchor_fn,
        guidance_fn=None,
        main_mode='anchor',
        record_expanded=record_expanded,
        successor_policy=successor_policy,
    )


def infer_path_primitive_trace(case: dict[str, Any], path: np.ndarray) -> list[int]:
    if path.shape[0] < 2:
        return []
    pindex = primitive_index_from_case(case)
    max_steer = math.radians(float(case['vehicle'].max_steer_deg))
    trace: list[int] = []
    for i in range(path.shape[0] - 1):
        state = tuple(float(v) for v in path[i])
        target = tuple(float(v) for v in path[i + 1])
        best = None
        for idx in range(len(pindex)):
            steer = pindex.actual_steer(idx, max_steer)
            direction = pindex.actual_direction(idx)
            sim = simulate_primitive_detailed(case, state, steer, direction)
            if not sim['valid'] or sim['next_state'] is None:
                continue
            nx, ny, nyaw = sim['next_state']
            err = math.hypot(target[0] - nx, target[1] - ny) + 0.25 * abs(wrap_to_pi(target[2] - nyaw))
            if best is None or err < best[0]:
                best = (err, idx)
        if best is not None:
            trace.append(int(best[1]))
    return trace


def prepare_case_context(case: dict[str, Any], predictor, cfg: CXGlobalConfig) -> dict[str, Any]:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return {
        'case': case,
        'bundle': bundle,
        'field': np.asarray(field, dtype=np.float32),
    }


def prepare_case_assets(case: dict[str, Any], predictor, cfg: CXGlobalConfig, max_expansions: int) -> dict[str, Any]:
    asset = prepare_case_context(case, predictor, cfg)
    result = run_hybrid_with_policy(case, asset['field'], max_expansions=int(max_expansions), successor_policy=None, record_expanded=False)
    trace = infer_path_primitive_trace(case, result.path)
    asset.update({
        'baseline_result': result,
        'trace': trace,
    })
    return asset


def load_nonholonomic_contexts(files: Sequence[Path], predictor, cfg: CXGlobalConfig, *, tag: str = 'cx8-contexts') -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    total = len(files)
    for i, path in enumerate(files, start=1):
        case = _load_nonholonomic_case(path)
        ctx = prepare_case_context(case, predictor, cfg)
        ctx['path'] = path
        out.append(ctx)
        if i % 5 == 0 or i == total:
            print(f'[{tag}] prepared {i}/{total}')
    return out


def load_nonholonomic_assets(files: Sequence[Path], predictor, cfg: CXGlobalConfig, max_expansions: int, *, tag: str = 'cx8-assets') -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    total = len(files)
    for i, path in enumerate(files, start=1):
        case = _load_nonholonomic_case(path)
        asset = prepare_case_assets(case, predictor, cfg, max_expansions=max_expansions)
        asset['path'] = path
        out.append(asset)
        if i % 5 == 0 or i == total:
            print(f'[{tag}] prepared {i}/{total}')
    return out


def set_torch_seed(seed: int) -> None:
    torch.manual_seed(int(seed))
    np.random.seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def _standardize(train_x: np.ndarray, val_x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0, keepdims=True).astype(np.float32)
    std = train_x.std(axis=0, keepdims=True).astype(np.float32)
    std[std < 1e-6] = 1.0
    return ((train_x - mean) / std).astype(np.float32), ((val_x - mean) / std).astype(np.float32), mean.astype(np.float32), std.astype(np.float32)


def fit_multiclass_model(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    *,
    model_path: Path,
    meta_path: Path,
    hidden_dim: int,
    learning_rate: float,
    weight_decay: float,
    epochs: int,
    batch_size: int,
    device: str,
    seed: int,
) -> FitArtifact:
    set_torch_seed(int(seed))
    xtr, xva, mean, std = _standardize(np.asarray(train_x, dtype=np.float32), np.asarray(val_x, dtype=np.float32))
    ytr = np.asarray(train_y, dtype=np.int64)
    yva = np.asarray(val_y, dtype=np.int64)
    input_dim = int(xtr.shape[1])
    output_dim = int(np.max(ytr)) + 1
    model = PrimitiveMLP(input_dim, output_dim, hidden_dim=int(hidden_dim)).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=float(learning_rate), weight_decay=float(weight_decay))
    loss_fn = torch.nn.CrossEntropyLoss()

    tr_x = torch.from_numpy(xtr)
    tr_y = torch.from_numpy(ytr)
    va_x = torch.from_numpy(xva).to(device)
    va_y = torch.from_numpy(yva).to(device)
    best_loss = float('inf')
    best_state = None
    n = tr_x.shape[0]
    bs = int(max(batch_size, 1))
    for _ in range(int(epochs)):
        perm = torch.randperm(n)
        model.train()
        for start in range(0, n, bs):
            idx = perm[start:start + bs]
            xb = tr_x[idx].to(device)
            yb = tr_y[idx].to(device)
            optim.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            optim.step()
        model.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(model(va_x), va_y).item())
        if val_loss < best_loss:
            best_loss = val_loss
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    if best_state is None:
        best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, model_path)
    meta = {
        'type': 'multiclass',
        'input_dim': int(input_dim),
        'output_dim': int(output_dim),
        'hidden_dim': int(hidden_dim),
        'mean': mean.squeeze(0).tolist(),
        'std': std.squeeze(0).tolist(),
        'best_val_loss': float(best_loss),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return FitArtifact(model_path=model_path, meta_path=meta_path, best_val_loss=float(best_loss), input_dim=input_dim, output_dim=output_dim)


def fit_multilabel_model(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    *,
    model_path: Path,
    meta_path: Path,
    hidden_dim: int,
    learning_rate: float,
    weight_decay: float,
    epochs: int,
    batch_size: int,
    device: str,
    seed: int,
) -> FitArtifact:
    set_torch_seed(int(seed))
    xtr, xva, mean, std = _standardize(np.asarray(train_x, dtype=np.float32), np.asarray(val_x, dtype=np.float32))
    ytr = np.asarray(train_y, dtype=np.float32)
    yva = np.asarray(val_y, dtype=np.float32)
    input_dim = int(xtr.shape[1])
    output_dim = int(ytr.shape[1])
    model = PrimitiveMLP(input_dim, output_dim, hidden_dim=int(hidden_dim)).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=float(learning_rate), weight_decay=float(weight_decay))
    loss_fn = torch.nn.BCEWithLogitsLoss()
    tr_x = torch.from_numpy(xtr)
    tr_y = torch.from_numpy(ytr)
    va_x = torch.from_numpy(xva).to(device)
    va_y = torch.from_numpy(yva).to(device)
    best_loss = float('inf')
    best_state = None
    n = tr_x.shape[0]
    bs = int(max(batch_size, 1))
    for _ in range(int(epochs)):
        perm = torch.randperm(n)
        model.train()
        for start in range(0, n, bs):
            idx = perm[start:start + bs]
            xb = tr_x[idx].to(device)
            yb = tr_y[idx].to(device)
            optim.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            optim.step()
        model.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(model(va_x), va_y).item())
        if val_loss < best_loss:
            best_loss = val_loss
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    if best_state is None:
        best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, model_path)
    meta = {
        'type': 'multilabel',
        'input_dim': int(input_dim),
        'output_dim': int(output_dim),
        'hidden_dim': int(hidden_dim),
        'mean': mean.squeeze(0).tolist(),
        'std': std.squeeze(0).tolist(),
        'best_val_loss': float(best_loss),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return FitArtifact(model_path=model_path, meta_path=meta_path, best_val_loss=float(best_loss), input_dim=input_dim, output_dim=output_dim)


def load_fit_model(artifact: FitArtifact, device: str) -> tuple[PrimitiveMLP, dict[str, Any]]:
    meta = json.loads(Path(artifact.meta_path).read_text(encoding='utf-8'))
    model = PrimitiveMLP(int(meta['input_dim']), int(meta['output_dim']), hidden_dim=int(meta['hidden_dim']))
    state = torch.load(artifact.model_path, map_location='cpu', weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model, meta


def predict_logits(model: PrimitiveMLP, meta: dict[str, Any], x: np.ndarray, device: str) -> np.ndarray:
    mean = np.asarray(meta['mean'], dtype=np.float32)[None, :]
    std = np.asarray(meta['std'], dtype=np.float32)[None, :]
    std[std < 1e-6] = 1.0
    arr = ((np.asarray(x, dtype=np.float32) - mean) / std).astype(np.float32)
    with torch.no_grad():
        logits = model(torch.from_numpy(arr).to(device)).detach().cpu().numpy()
    return logits.astype(np.float32)


def choose_calib_split(dev_files: Sequence[Path], seed: int) -> dict[str, list[Path]]:
    by_scenario: dict[str, list[Path]] = {}
    for p in sorted(dev_files):
        with np.load(p, allow_pickle=False) as z:
            by_scenario.setdefault(str(z['scenario']), []).append(p)
    rng = np.random.default_rng(int(seed))
    train_files: list[Path] = []
    val_files: list[Path] = []
    for scenario, files in sorted(by_scenario.items()):
        files = list(files)
        rng.shuffle(files)
        if len(files) <= 1:
            train_files.extend(files)
            continue
        val_count = 1 if len(files) <= 4 else 2
        val_files.extend(sorted(files[:val_count]))
        train_files.extend(sorted(files[val_count:]))
    return {'calib_train': sorted(train_files), 'calib_val': sorted(val_files)}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_inputs_sha256(paths: Iterable[Path], out_path: Path) -> None:
    payload = {str(Path(p)): sha256_file(Path(p)) for p in sorted({Path(p) for p in paths}) if Path(p).exists()}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


__all__ = [
    'ACCEPTED_CX3D_PARAMS',
    'BUNDLE_LABELS',
    'CXGlobalConfig',
    'FitArtifact',
    'PrimitiveIndex',
    'PrimitiveMLP',
    'accepted_cx3d_nonholonomic',
    'accepted_cx3d_standard',
    'build_bundle_feature_vector',
    'build_ego_patch',
    'build_state_action_vector',
    'build_state_action_vector_from_cache',
    'build_state_cache',
    'build_compact_bundle_feature_vector',
    'build_compact_state_cache',
    'build_state_vector',
    'build_kfm_compact_action_vector_from_cache',
    'bottleneck_regime_score',
    'bundle_target_from_trace',
    'choose_calib_split',
    'fit_multiclass_model',
    'fit_multilabel_model',
    'infer_path_primitive_trace',
    'load_fit_model',
    'load_nonholonomic_assets',
    'load_nonholonomic_contexts',
    'predict_logits',
    'prepare_case_assets',
    'primitive_index_from_case',
    'primitive_index_from_planner',
    'query_yaw_field',
    'reverse_escape_fraction',
    'run_hybrid_with_policy',
    'set_torch_seed',
    'sha256_file',
    'simulate_primitive_detailed',
    'write_inputs_sha256',
]
