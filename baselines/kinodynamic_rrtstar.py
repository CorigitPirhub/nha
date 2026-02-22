from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

from config import PlannerConfig, VehicleConfig
from env.reeds_shepp import RSConsistentCostConfig, shortest_path_cost_consistent_with_path
from utils.common import wrap_to_pi


@dataclass
class _TreeNode:
    x: float
    y: float
    yaw: float
    parent: int
    cost: float
    edge_path: np.ndarray


def _state_valid(
    x: float,
    y: float,
    occupancy: np.ndarray,
    resolution: float,
    clearance_m: float,
    esdf: np.ndarray | None = None,
) -> bool:
    h, w = occupancy.shape
    if x < 0.0 or y < 0.0 or x >= w * resolution or y >= h * resolution:
        return False
    gx = int(np.clip(np.floor(x / resolution), 0, w - 1))
    gy = int(np.clip(np.floor(y / resolution), 0, h - 1))
    if occupancy[gy, gx]:
        return False
    if esdf is not None:
        d = float(esdf[gy, gx])
        if d <= clearance_m:
            return False
    return True


def _linear_fallback_path(
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    step_size: float,
) -> np.ndarray:
    d = math.hypot(goal[0] - start[0], goal[1] - start[1])
    n = max(2, int(math.ceil(d / max(step_size, 1e-3))) + 1)
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)
    xs = (1.0 - t) * float(start[0]) + t * float(goal[0])
    ys = (1.0 - t) * float(start[1]) + t * float(goal[1])
    y0 = float(start[2])
    y1 = float(goal[2])
    dy = wrap_to_pi(y1 - y0)
    yaws = y0 + t * dy
    return np.stack([xs, ys, yaws.astype(np.float32)], axis=1).astype(np.float32)


def _path_from_rs_obj(path_obj, start: tuple[float, float, float], goal: tuple[float, float, float], step_size: float) -> np.ndarray:
    if path_obj is None:
        return _linear_fallback_path(start, goal, step_size=step_size)
    try:
        xs, ys, yaws = path_obj.coordinates_tuple()
        if len(xs) >= 2:
            arr = np.stack([np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32), np.asarray(yaws, dtype=np.float32)], axis=1)
            return arr.astype(np.float32)
    except Exception:
        pass
    return _linear_fallback_path(start, goal, step_size=step_size)


def _edge_collision_free(
    path_xyz: np.ndarray,
    occupancy: np.ndarray,
    resolution: float,
    clearance_m: float,
    esdf: np.ndarray | None = None,
) -> bool:
    if path_xyz.size == 0:
        return False
    for i in range(path_xyz.shape[0]):
        x = float(path_xyz[i, 0])
        y = float(path_xyz[i, 1])
        if not _state_valid(x, y, occupancy, resolution, clearance_m, esdf=esdf):
            return False
    return True


def _connect_rs(
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    rho: float,
    cost_cfg: RSConsistentCostConfig,
    step_size: float,
) -> tuple[float, np.ndarray]:
    c, path_obj = shortest_path_cost_consistent_with_path(
        start=start,
        goal=goal,
        rho=float(rho),
        cost_cfg=cost_cfg,
        step_size=float(max(step_size, 1e-3)),
        backend="rsplan",
    )
    if not np.isfinite(c):
        return float("inf"), np.zeros((0, 3), dtype=np.float32)
    pxyz = _path_from_rs_obj(path_obj, start=start, goal=goal, step_size=step_size)
    return float(c), pxyz


def _sample_state(
    free_cells: np.ndarray,
    resolution: float,
    rng: np.random.Generator,
    goal: tuple[float, float, float],
    goal_sample_rate: float,
) -> tuple[float, float, float]:
    if float(rng.random()) < float(goal_sample_rate):
        return goal
    yx = free_cells[int(rng.integers(0, free_cells.shape[0]))]
    y = int(yx[0])
    x = int(yx[1])
    return float((x + 0.5) * resolution), float((y + 0.5) * resolution), float(rng.uniform(-math.pi, math.pi))


def _nearest_index(nodes: list[_TreeNode], q: tuple[float, float, float], yaw_weight: float) -> int:
    qx, qy, qyaw = q
    best = 0
    best_d = float("inf")
    for i, n in enumerate(nodes):
        dxy = math.hypot(n.x - qx, n.y - qy)
        dyaw = abs(wrap_to_pi(n.yaw - qyaw))
        d = dxy + float(yaw_weight) * dyaw
        if d < best_d:
            best_d = d
            best = i
    return best


def _neighbor_indices(nodes: list[_TreeNode], q: tuple[float, float, float], radius_m: float) -> list[int]:
    qx, qy, _ = q
    out: list[int] = []
    r2 = float(radius_m * radius_m)
    for i, n in enumerate(nodes):
        dx = n.x - qx
        dy = n.y - qy
        if dx * dx + dy * dy <= r2:
            out.append(i)
    return out


def _reconstruct_path(
    nodes: list[_TreeNode],
    goal_parent_idx: int,
    goal_edge: np.ndarray,
) -> np.ndarray:
    chain = []
    idx = goal_parent_idx
    while idx >= 0:
        chain.append(idx)
        idx = int(nodes[idx].parent)
    chain.reverse()

    segs: list[np.ndarray] = []
    for i, node_idx in enumerate(chain):
        n = nodes[node_idx]
        if i == 0:
            segs.append(np.asarray([[n.x, n.y, n.yaw]], dtype=np.float32))
        else:
            ep = n.edge_path
            if ep.size == 0:
                continue
            segs.append(ep[1:] if ep.shape[0] > 1 else ep)
    if goal_edge.size > 0:
        segs.append(goal_edge[1:] if goal_edge.shape[0] > 1 else goal_edge)
    if not segs:
        return np.zeros((0, 3), dtype=np.float32)
    return np.concatenate(segs, axis=0).astype(np.float32)


def kinodynamic_rrt_star(
    occupancy: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    vehicle_cfg: VehicleConfig,
    planner_cfg: PlannerConfig,
    max_iters: int,
    rng: np.random.Generator,
    esdf: np.ndarray | None = None,
    goal_sample_rate: float = 0.15,
    neighbor_radius_m: float | None = None,
    yaw_weight: float = 0.35,
) -> dict:
    t0 = time.perf_counter()
    occ = occupancy.astype(bool)
    free = np.argwhere(~occ)
    if free.size == 0:
        return {"success": False, "expansions": 0, "runtime_ms": 0.0, "path": [], "cost": float("inf")}

    clearance = 0.35 * float(vehicle_cfg.width)
    if not _state_valid(start[0], start[1], occ, resolution, clearance, esdf=esdf):
        return {"success": False, "expansions": 0, "runtime_ms": 0.0, "path": [], "cost": float("inf")}
    if not _state_valid(goal[0], goal[1], occ, resolution, clearance, esdf=esdf):
        return {"success": False, "expansions": 0, "runtime_ms": 0.0, "path": [], "cost": float("inf")}

    cost_cfg = RSConsistentCostConfig.from_configs(vehicle_cfg=vehicle_cfg, planner_cfg=planner_cfg)
    step_size = float(max(planner_cfg.step_size, 0.1))
    rho = float(vehicle_cfg.min_turn_radius)
    if neighbor_radius_m is None:
        neighbor_radius_m = float(max(3.5 * rho, 8.0 * resolution))

    nodes: list[_TreeNode] = [
        _TreeNode(
            x=float(start[0]),
            y=float(start[1]),
            yaw=float(start[2]),
            parent=-1,
            cost=0.0,
            edge_path=np.asarray([[float(start[0]), float(start[1]), float(start[2])]], dtype=np.float32),
        )
    ]

    best_goal_cost = float("inf")
    best_goal_parent = -1
    best_goal_edge = np.zeros((0, 3), dtype=np.float32)
    expansions = 0

    for _ in range(max(int(max_iters), 1)):
        expansions += 1
        q_rand = _sample_state(free, resolution, rng, goal=goal, goal_sample_rate=goal_sample_rate)

        i_near = _nearest_index(nodes, q_rand, yaw_weight=float(yaw_weight))
        near = nodes[i_near]
        c_near, p_near = _connect_rs(
            start=(near.x, near.y, near.yaw),
            goal=q_rand,
            rho=rho,
            cost_cfg=cost_cfg,
            step_size=step_size,
        )
        if not np.isfinite(c_near) or p_near.size == 0:
            continue
        if not _edge_collision_free(p_near, occ, resolution, clearance_m=clearance, esdf=esdf):
            continue

        q_new = (float(p_near[-1, 0]), float(p_near[-1, 1]), float(p_near[-1, 2]))
        if not _state_valid(q_new[0], q_new[1], occ, resolution, clearance, esdf=esdf):
            continue

        best_parent = i_near
        best_parent_edge = p_near
        best_new_cost = float(near.cost + c_near)

        nbrs = _neighbor_indices(nodes, q_new, radius_m=float(neighbor_radius_m))
        for j in nbrs:
            cand = nodes[j]
            c_edge, p_edge = _connect_rs(
                start=(cand.x, cand.y, cand.yaw),
                goal=q_new,
                rho=rho,
                cost_cfg=cost_cfg,
                step_size=step_size,
            )
            if not np.isfinite(c_edge) or p_edge.size == 0:
                continue
            if not _edge_collision_free(p_edge, occ, resolution, clearance_m=clearance, esdf=esdf):
                continue
            cand_cost = float(cand.cost + c_edge)
            if cand_cost + 1e-6 < best_new_cost:
                best_new_cost = cand_cost
                best_parent = j
                best_parent_edge = p_edge

        new_idx = len(nodes)
        nodes.append(
            _TreeNode(
                x=q_new[0],
                y=q_new[1],
                yaw=q_new[2],
                parent=int(best_parent),
                cost=float(best_new_cost),
                edge_path=best_parent_edge.astype(np.float32),
            )
        )

        # Rewire neighbors through q_new.
        for j in nbrs:
            if j == best_parent:
                continue
            old = nodes[j]
            c_edge, p_edge = _connect_rs(
                start=q_new,
                goal=(old.x, old.y, old.yaw),
                rho=rho,
                cost_cfg=cost_cfg,
                step_size=step_size,
            )
            if not np.isfinite(c_edge) or p_edge.size == 0:
                continue
            if not _edge_collision_free(p_edge, occ, resolution, clearance_m=clearance, esdf=esdf):
                continue
            cand_cost = float(nodes[new_idx].cost + c_edge)
            if cand_cost + 1e-6 < old.cost:
                old.parent = int(new_idx)
                old.cost = cand_cost
                old.edge_path = p_edge.astype(np.float32)
                nodes[j] = old

        # Goal connection attempt.
        c_goal, p_goal = _connect_rs(
            start=q_new,
            goal=goal,
            rho=rho,
            cost_cfg=cost_cfg,
            step_size=step_size,
        )
        if np.isfinite(c_goal) and p_goal.size > 0 and _edge_collision_free(p_goal, occ, resolution, clearance_m=clearance, esdf=esdf):
            total_goal = float(nodes[new_idx].cost + c_goal)
            if total_goal + 1e-6 < best_goal_cost:
                best_goal_cost = total_goal
                best_goal_parent = int(new_idx)
                best_goal_edge = p_goal.astype(np.float32)

    if best_goal_parent < 0:
        return {
            "success": False,
            "expansions": float(expansions),
            "runtime_ms": (time.perf_counter() - t0) * 1000.0,
            "path": [],
            "cost": float("inf"),
        }

    path_xyz = _reconstruct_path(nodes, goal_parent_idx=best_goal_parent, goal_edge=best_goal_edge)
    path_xy = [(float(path_xyz[i, 0]), float(path_xyz[i, 1])) for i in range(path_xyz.shape[0])]
    return {
        "success": True,
        "expansions": float(expansions),
        "runtime_ms": (time.perf_counter() - t0) * 1000.0,
        "path": path_xy,
        "cost": float(best_goal_cost),
    }


def kinodynamic_bit_star(
    occupancy: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    vehicle_cfg: VehicleConfig,
    planner_cfg: PlannerConfig,
    max_iters: int,
    rng: np.random.Generator,
    esdf: np.ndarray | None = None,
) -> dict:
    # Lightweight informed variant: stronger goal bias + tighter rewiring radius.
    radius = float(max(2.8 * float(vehicle_cfg.min_turn_radius), 6.0 * float(resolution)))
    return kinodynamic_rrt_star(
        occupancy=occupancy,
        resolution=resolution,
        start=start,
        goal=goal,
        vehicle_cfg=vehicle_cfg,
        planner_cfg=planner_cfg,
        max_iters=max_iters,
        rng=rng,
        esdf=esdf,
        goal_sample_rate=0.22,
        neighbor_radius_m=radius,
        yaw_weight=0.40,
    )
