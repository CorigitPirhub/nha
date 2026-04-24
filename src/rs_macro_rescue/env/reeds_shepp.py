from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

import numpy as np

from rs_macro_rescue.config import PlannerConfig, VehicleConfig
from rs_macro_rescue.env.dubins import compute_dubins_field, shortest_path_length as dubins_shortest_path_length, yaw_bin_centers


try:
    from rsplan import path as rsplan_path
    from rsplan import planner as rsplan_planner

    _HAS_RSPLAN = True
except Exception:
    rsplan_path = None
    rsplan_planner = None
    _HAS_RSPLAN = False


@dataclass
class RSConsistentCostConfig:
    reverse_penalty: float
    steer_penalty: float
    steer_change_penalty: float
    step_size: float
    wheel_base: float
    max_steer_rad: float

    @classmethod
    def from_configs(cls, vehicle_cfg: VehicleConfig, planner_cfg: PlannerConfig) -> "RSConsistentCostConfig":
        return cls(
            reverse_penalty=float(planner_cfg.reverse_penalty),
            steer_penalty=float(planner_cfg.steer_penalty),
            steer_change_penalty=float(planner_cfg.steer_change_penalty),
            step_size=float(planner_cfg.step_size),
            wheel_base=float(vehicle_cfg.wheel_base),
            max_steer_rad=float(np.deg2rad(vehicle_cfg.max_steer_deg)),
        )


def _wrap_to_pi(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def _reverse_only_dubins_length(
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    rho: float,
) -> float:
    s = (start[0], start[1], _wrap_to_pi(start[2] + math.pi))
    g = (goal[0], goal[1], _wrap_to_pi(goal[2] + math.pi))
    return dubins_shortest_path_length(s, g, rho=rho)


def _segment_direction(segment) -> int:
    d = float(getattr(segment, "direction", 0.0))
    l = float(getattr(segment, "length", 0.0))
    if abs(d) > 1e-6:
        return -1 if d < 0.0 else 1
    if abs(l) > 1e-6:
        return -1 if l < 0.0 else 1
    return 1


def _segment_length(segment) -> float:
    return float(abs(float(getattr(segment, "length", 0.0))))


def _segment_steer_rad(segment, rho: float, cfg: RSConsistentCostConfig) -> float:
    seg_type = str(getattr(segment, "type", "straight")).lower()
    if seg_type == "left":
        sign = 1.0
    elif seg_type == "right":
        sign = -1.0
    else:
        return 0.0
    steer = math.atan2(cfg.wheel_base, max(float(rho), 1e-6))
    steer = float(min(steer, cfg.max_steer_rad))
    return sign * steer


def path_cost_consistent(segments: Iterable, rho: float, cfg: RSConsistentCostConfig) -> float:
    """
    Planner-consistent cost integration along RS segments.
    Matches Hybrid-A* edge terms:
      - reverse penalty on traveled distance
      - steer penalty on traveled distance
      - steer-change penalty at steering switches
    """
    max_steer = max(float(cfg.max_steer_rad), 1e-6)
    step = max(float(cfg.step_size), 1e-6)
    total = 0.0
    prev_steer = 0.0
    first = True

    for seg in segments:
        seg_len = _segment_length(seg)
        if seg_len <= 1e-9:
            continue
        direction = _segment_direction(seg)
        steer = _segment_steer_rad(seg, rho=rho, cfg=cfg)
        n_steps = max(1, int(np.ceil(seg_len / step)))
        ds = seg_len / n_steps

        for i in range(n_steps):
            edge = ds
            if direction < 0:
                edge *= float(cfg.reverse_penalty)
            edge += float(cfg.steer_penalty) * abs(steer) / max_steer * ds
            if i == 0:
                # Penalize steering switch once at the segment boundary.
                # This mirrors planner edge-cost dependence on previous steering command.
                edge += float(cfg.steer_change_penalty) * abs(steer - prev_steer) / max_steer * ds
            total += edge

        prev_steer = steer
        first = False

    if first:
        return 0.0
    return float(total)


def _solve_rs_candidates(
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    rho: float,
    step_size: float,
) -> list:
    if not _HAS_RSPLAN:
        return []
    try:
        return list(
            rsplan_planner._solve_path(  # type: ignore[attr-defined]
                start=start,
                end=goal,
                turn_rad=float(rho),
                step_size=float(max(step_size, 1e-3)),
            )
        )
    except Exception:
        try:
            p = rsplan_path(
                start,
                goal,
                turn_radius=float(rho),
                runway_length=0.0,
                step_size=float(max(step_size, 1e-3)),
            )
            return [p]
        except Exception:
            return []


def shortest_path_length(
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    rho: float,
    step_size: float = 1.0,
    backend: str = "auto",
) -> float:
    use_rsplan = backend in {"auto", "rsplan"} and _HAS_RSPLAN
    if use_rsplan:
        try:
            p = rsplan_path(
                start,
                goal,
                turn_radius=float(rho),
                runway_length=0.0,
                step_size=float(max(step_size, 1e-3)),
            )
            return float(p.total_length)
        except Exception:
            pass

    forward = dubins_shortest_path_length(start, goal, rho=rho)
    reverse = _reverse_only_dubins_length(start, goal, rho=rho)
    return float(min(forward, reverse))


def shortest_path_cost_consistent(
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    rho: float,
    cost_cfg: RSConsistentCostConfig,
    step_size: float = 1.0,
    backend: str = "auto",
) -> float:
    cost, _ = shortest_path_cost_consistent_with_path(
        start=start,
        goal=goal,
        rho=rho,
        cost_cfg=cost_cfg,
        step_size=step_size,
        backend=backend,
    )
    return cost


def shortest_path_cost_consistent_with_path(
    start: Tuple[float, float, float],
    goal: Tuple[float, float, float],
    rho: float,
    cost_cfg: RSConsistentCostConfig,
    step_size: float = 1.0,
    backend: str = "auto",
) -> tuple[float, object | None]:
    backend = str(backend).lower()
    if backend in {"auto", "rsplan"} and _HAS_RSPLAN:
        best = float("inf")
        best_path = None
        for p in _solve_rs_candidates(start, goal, rho=rho, step_size=step_size):
            c = path_cost_consistent(p.segments, rho=rho, cfg=cost_cfg)
            if c < best:
                best = c
                best_path = p
        if np.isfinite(best):
            return float(best), best_path
    # Fallback: geometric RS lower bound when RS solver unavailable.
    return shortest_path_length(start, goal, rho=rho, step_size=step_size, backend="approx"), None


def _compute_field_via_rsplan(
    occupancy: np.ndarray,
    goal: Tuple[float, float, float],
    resolution: float,
    yaw_bins: int,
    rho: float,
    fill_value: float,
    step_size: float,
    cost_mode: str,
    cost_cfg: RSConsistentCostConfig | None,
) -> np.ndarray:
    h, w = occupancy.shape
    out = np.full((yaw_bins, h, w), fill_value, dtype=np.float32)

    free_y, free_x = np.where(~occupancy)
    if free_x.size == 0:
        return out

    world_x = (free_x.astype(np.float32) + 0.5) * float(resolution)
    world_y = (free_y.astype(np.float32) + 0.5) * float(resolution)
    yaw_centers = yaw_bin_centers(yaw_bins).astype(np.float32)

    use_consistent = cost_mode == "planner_consistent"
    if use_consistent and cost_cfg is None:
        raise ValueError("cost_cfg is required when cost_mode='planner_consistent'")

    for k, yaw0 in enumerate(yaw_centers):
        vals = np.empty_like(world_x, dtype=np.float32)
        for i in range(world_x.size):
            st = (float(world_x[i]), float(world_y[i]), float(yaw0))
            if use_consistent:
                v = shortest_path_cost_consistent(
                    start=st,
                    goal=goal,
                    rho=rho,
                    cost_cfg=cost_cfg,  # type: ignore[arg-type]
                    step_size=step_size,
                    backend="rsplan",
                )
            else:
                v = shortest_path_length(
                    start=st,
                    goal=goal,
                    rho=rho,
                    step_size=step_size,
                    backend="rsplan",
                )
            vals[i] = float(v)
        out[k, free_y, free_x] = vals

    out[:, occupancy] = fill_value
    out = np.where(np.isfinite(out), out, fill_value).astype(np.float32)
    return out


def _compute_field_approx(
    occupancy: np.ndarray,
    goal: Tuple[float, float, float],
    resolution: float,
    yaw_bins: int,
    rho: float,
    fill_value: float,
) -> np.ndarray:
    dubins_fwd = compute_dubins_field(
        occupancy=occupancy,
        goal=goal,
        resolution=resolution,
        yaw_bins=yaw_bins,
        rho=rho,
        fill_value=fill_value,
    )

    goal_rev = (float(goal[0]), float(goal[1]), _wrap_to_pi(float(goal[2]) + math.pi))
    dubins_rev_ref = compute_dubins_field(
        occupancy=occupancy,
        goal=goal_rev,
        resolution=resolution,
        yaw_bins=yaw_bins,
        rho=rho,
        fill_value=fill_value,
    )

    half_shift = yaw_bins / 2.0
    idx = np.arange(yaw_bins, dtype=np.float32) + half_shift
    i0 = np.floor(idx).astype(np.int32) % yaw_bins
    i1 = (i0 + 1) % yaw_bins
    w = idx - np.floor(idx)
    dubins_rev = (1.0 - w)[:, None, None] * dubins_rev_ref[i0] + w[:, None, None] * dubins_rev_ref[i1]

    out = np.minimum(dubins_fwd, dubins_rev.astype(np.float32))
    out[:, occupancy] = fill_value
    out = np.where(np.isfinite(out), out, fill_value).astype(np.float32)
    return out


def compute_reeds_shepp_field(
    occupancy: np.ndarray,
    goal: Tuple[float, float, float],
    resolution: float,
    yaw_bins: int,
    rho: float,
    fill_value: float,
    step_size: float = 1.0,
    backend: str = "auto",
    cost_mode: str = "length",
    cost_cfg: RSConsistentCostConfig | None = None,
) -> np.ndarray:
    """
    Compute a [yaw_bin, y, x] Reeds-Shepp field.

    backend:
      - "auto": use rsplan if available, otherwise fast approximation.
      - "rsplan": force rsplan path solver.
      - "approx": bidirectional-Dubins approximation.

    cost_mode:
      - "length": geometric RS length.
      - "planner_consistent": planner-aligned RS cost.
    """
    backend = str(backend).lower()
    cost_mode = str(cost_mode).lower()
    if backend not in {"auto", "rsplan", "approx"}:
        raise ValueError(f"Unknown backend: {backend}")
    if cost_mode not in {"length", "planner_consistent"}:
        raise ValueError(f"Unknown cost_mode: {cost_mode}")

    if backend in {"auto", "rsplan"} and _HAS_RSPLAN:
        return _compute_field_via_rsplan(
            occupancy=occupancy,
            goal=goal,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=rho,
            fill_value=fill_value,
            step_size=step_size,
            cost_mode=cost_mode,
            cost_cfg=cost_cfg,
        )

    return _compute_field_approx(
        occupancy=occupancy,
        goal=goal,
        resolution=resolution,
        yaw_bins=yaw_bins,
        rho=rho,
        fill_value=fill_value,
    )


def make_rs_field_cache_key(
    occupancy: np.ndarray,
    goal: Tuple[float, float, float],
    resolution: float,
    yaw_bins: int,
    rho: float,
    step_size: float,
    backend: str,
    cost_mode: str,
    cost_cfg: RSConsistentCostConfig | None = None,
) -> str:
    h = hashlib.sha1()
    occ_u8 = np.ascontiguousarray(occupancy.astype(np.uint8))
    h.update(occ_u8.tobytes())
    meta = np.asarray(
        [
            float(goal[0]),
            float(goal[1]),
            float(goal[2]),
            float(resolution),
            float(yaw_bins),
            float(rho),
            float(step_size),
        ],
        dtype=np.float32,
    )
    h.update(meta.tobytes())
    h.update(str(backend).lower().encode("utf-8"))
    h.update(str(cost_mode).lower().encode("utf-8"))
    if cost_cfg is not None:
        cost_meta = np.asarray(
            [
                float(cost_cfg.reverse_penalty),
                float(cost_cfg.steer_penalty),
                float(cost_cfg.steer_change_penalty),
                float(cost_cfg.step_size),
                float(cost_cfg.wheel_base),
                float(cost_cfg.max_steer_rad),
            ],
            dtype=np.float32,
        )
        h.update(cost_meta.tobytes())
    return h.hexdigest()


def rs_field_cache_path(cache_dir: Path, key: str) -> Path:
    return Path(cache_dir) / f"rs_field_{key}.npy"


def load_rs_field_cache(cache_dir: Path, key: str) -> np.ndarray | None:
    path = rs_field_cache_path(cache_dir, key)
    if not path.exists():
        return None
    try:
        arr = np.load(path, allow_pickle=False)
    except Exception:
        return None
    if not isinstance(arr, np.ndarray):
        return None
    return arr.astype(np.float32, copy=False)


def save_rs_field_cache(cache_dir: Path, key: str, field: np.ndarray) -> Path:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = rs_field_cache_path(cache_dir, key)
    np.save(path, field.astype(np.float32))
    return path
