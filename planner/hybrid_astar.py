from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from config import PlannerConfig, VehicleConfig
from planner.heuristics import HeuristicFn, compose_guidance, euclidean_heuristic
from utils.common import bilinear_interpolate, wrap_to_pi


@dataclass
class NodeRecord:
    x: float
    y: float
    yaw: float
    g: float
    anchor: float
    guided: float
    parent: Optional[Tuple[int, int, int]]
    steer: float
    direction: int


@dataclass
class PlanResult:
    success: bool
    path: np.ndarray
    cost: float
    expansions: int
    runtime_ms: float
    message: str


class HybridAStarPlanner:
    def __init__(
        self,
        occupancy: np.ndarray,
        resolution: float,
        vehicle_cfg: VehicleConfig,
        planner_cfg: PlannerConfig,
        esdf: Optional[np.ndarray] = None,
    ) -> None:
        self.occupancy = occupancy.astype(bool)
        self.resolution = float(resolution)
        self.vehicle_cfg = vehicle_cfg
        self.cfg = planner_cfg
        self.esdf = esdf

        self.h, self.w = self.occupancy.shape
        self.max_steer = math.radians(vehicle_cfg.max_steer_deg)
        self.vehicle_clearance = 0.35 * vehicle_cfg.width

        steer_levels = np.array([-1.0, -0.5, 0.0, 0.5, 1.0], dtype=np.float32)
        self.motion_primitives: List[Tuple[float, int]] = []
        for s in steer_levels:
            steer = float(s * self.max_steer)
            self.motion_primitives.append((steer, 1))
            self.motion_primitives.append((steer, -1))

    def plan(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        guidance_fn: Optional[HeuristicFn] = None,
        anchor_fn: Optional[HeuristicFn] = None,
    ) -> PlanResult:
        t0 = time.perf_counter()
        if anchor_fn is None:
            anchor_fn = euclidean_heuristic((goal[0], goal[1]))
        h_pair = compose_guidance(anchor_fn, guidance_fn, self.cfg.guidance_blend)

        if not self._state_is_valid(start[0], start[1]) or not self._state_is_valid(goal[0], goal[1]):
            return PlanResult(False, np.zeros((0, 3), dtype=np.float32), np.inf, 0, 0.0, "Start or goal in collision")

        upper_bound = np.inf
        pre_expansions = 0
        pre_success = False

        if guidance_fn is not None and self.cfg.warm_start_budget > 0:
            warm_budget = int(self.cfg.warm_start_budget)
            warm = self._search(
                start=start,
                goal=goal,
                h_pair=h_pair,
                mode="guided",
                max_expansions=warm_budget,
                upper_bound=np.inf,
                stop_on_first_goal=True,
            )
            pre_expansions = warm.expansions
            if warm.success:
                upper_bound = warm.cost
                pre_success = True

        main = self._search(
            start=start,
            goal=goal,
            h_pair=h_pair,
            mode="anchor",
            max_expansions=self.cfg.max_expansions,
            upper_bound=upper_bound,
            stop_on_first_goal=False,
        )
        total_ms = (time.perf_counter() - t0) * 1000.0
        main.runtime_ms = total_ms
        main.expansions += pre_expansions

        if main.success:
            if pre_success:
                main.message = "ok (warm-started by neural guidance)"
            return main

        if pre_success:
            warm.runtime_ms = total_ms
            warm.expansions = pre_expansions + main.expansions
            warm.message = "fallback warm solution (optimality not certified due expansion limit)"
            return warm

        return main

    def _search(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        h_pair,
        mode: str,
        max_expansions: int,
        upper_bound: float,
        stop_on_first_goal: bool,
    ) -> PlanResult:
        start_key = self._state_key(*start)
        a0, g0 = h_pair(*start)

        records: Dict[Tuple[int, int, int], NodeRecord] = {
            start_key: NodeRecord(
                x=float(start[0]),
                y=float(start[1]),
                yaw=wrap_to_pi(float(start[2])),
                g=0.0,
                anchor=float(a0),
                guided=float(g0),
                parent=None,
                steer=0.0,
                direction=1,
            )
        }

        open_heap: List[Tuple[float, float, int, Tuple[int, int, int]]] = []
        anchor_heap: List[Tuple[float, int, Tuple[int, int, int]]] = []
        counter = 0
        p0, s0 = self._priority(records[start_key], mode)
        heapq.heappush(open_heap, (p0, s0, counter, start_key))
        heapq.heappush(anchor_heap, (records[start_key].g + records[start_key].anchor, counter, start_key))

        expanded_best_g: Dict[Tuple[int, int, int], float] = {}
        best_goal_key: Optional[Tuple[int, int, int]] = None
        best_goal_cost = float(upper_bound)
        expansions = 0

        while open_heap and expansions < max_expansions:
            primary, _, _, key = heapq.heappop(open_heap)
            rec = records.get(key)
            if rec is None:
                continue

            expected_primary, _ = self._priority(rec, mode)
            if abs(primary - expected_primary) > 1e-6:
                continue

            if rec.g + rec.anchor >= best_goal_cost:
                continue

            prev = expanded_best_g.get(key)
            if prev is not None and rec.g >= prev - 1e-9:
                continue
            expanded_best_g[key] = rec.g
            expansions += 1

            if self._is_goal(rec.x, rec.y, rec.yaw, goal):
                if rec.g < best_goal_cost:
                    best_goal_cost = rec.g
                    best_goal_key = key
                if stop_on_first_goal:
                    path = self._reconstruct_path(key, records)
                    return PlanResult(True, path, float(rec.g), expansions, 0.0, "goal found")

            if mode == "anchor" and best_goal_key is not None:
                min_anchor = self._peek_min_anchor(anchor_heap, records)
                if min_anchor >= best_goal_cost - 1e-6:
                    path = self._reconstruct_path(best_goal_key, records)
                    return PlanResult(True, path, float(best_goal_cost), expansions, 0.0, "optimal")

            for steer, direction in self.motion_primitives:
                nxt = self._simulate(rec.x, rec.y, rec.yaw, steer, direction)
                if nxt is None:
                    continue
                nx, ny, nyaw = nxt

                edge = self._edge_cost(self.cfg.step_size, steer, rec.steer, direction)
                ng = rec.g + edge
                if ng >= best_goal_cost:
                    continue

                na, nguided = h_pair(nx, ny, nyaw)
                if ng + na >= best_goal_cost:
                    continue

                nkey = self._state_key(nx, ny, nyaw)
                old = records.get(nkey)
                if old is not None and ng >= old.g - 1e-9:
                    continue

                nrec = NodeRecord(
                    x=nx,
                    y=ny,
                    yaw=nyaw,
                    g=ng,
                    anchor=float(na),
                    guided=float(nguided),
                    parent=key,
                    steer=steer,
                    direction=direction,
                )
                records[nkey] = nrec
                counter += 1
                p, s = self._priority(nrec, mode)
                heapq.heappush(open_heap, (p, s, counter, nkey))
                heapq.heappush(anchor_heap, (ng + na, counter, nkey))

        if best_goal_key is not None:
            path = self._reconstruct_path(best_goal_key, records)
            return PlanResult(True, path, float(best_goal_cost), expansions, 0.0, "bounded by expansion limit")

        return PlanResult(False, np.zeros((0, 3), dtype=np.float32), np.inf, expansions, 0.0, "search failed")

    def _priority(self, rec: NodeRecord, mode: str) -> Tuple[float, float]:
        f_anchor = rec.g + rec.anchor
        f_guided = rec.g + rec.guided
        if mode == "guided":
            return f_guided, f_anchor
        return f_anchor, f_guided

    def _peek_min_anchor(
        self,
        anchor_heap: List[Tuple[float, int, Tuple[int, int, int]]],
        records: Dict[Tuple[int, int, int], NodeRecord],
    ) -> float:
        while anchor_heap:
            f_anchor, _, key = anchor_heap[0]
            rec = records.get(key)
            if rec is None:
                heapq.heappop(anchor_heap)
                continue
            expected = rec.g + rec.anchor
            if abs(f_anchor - expected) > 1e-6:
                heapq.heappop(anchor_heap)
                continue
            return float(expected)
        return np.inf

    def _is_goal(self, x: float, y: float, yaw: float, goal: Tuple[float, float, float]) -> bool:
        d = math.hypot(goal[0] - x, goal[1] - y)
        if d > self.cfg.goal_tolerance_xy:
            return False
        dyaw = abs(wrap_to_pi(goal[2] - yaw))
        return dyaw <= math.radians(self.cfg.goal_tolerance_yaw_deg)

    def _edge_cost(self, step: float, steer: float, prev_steer: float, direction: int) -> float:
        c = float(step)
        if direction < 0:
            c *= self.cfg.reverse_penalty
        c += self.cfg.steer_penalty * abs(steer) / max(self.max_steer, 1e-3) * step
        c += self.cfg.steer_change_penalty * abs(steer - prev_steer) / max(self.max_steer, 1e-3) * step
        return c

    def _simulate(self, x: float, y: float, yaw: float, steer: float, direction: int) -> Optional[Tuple[float, float, float]]:
        n = max(1, int(np.ceil(self.cfg.step_size / self.cfg.collision_check_step)))
        ds = self.cfg.step_size / n

        cx, cy, cyaw = x, y, yaw
        for _ in range(n):
            signed_ds = ds * direction
            cx += signed_ds * math.cos(cyaw)
            cy += signed_ds * math.sin(cyaw)
            cyaw = wrap_to_pi(cyaw + signed_ds * math.tan(steer) / self.vehicle_cfg.wheel_base)
            if not self._state_is_valid(cx, cy):
                return None

        return cx, cy, cyaw

    def _state_is_valid(self, x: float, y: float) -> bool:
        if x < 0.0 or y < 0.0:
            return False
        if x >= self.w * self.resolution or y >= self.h * self.resolution:
            return False

        if self.esdf is not None:
            d = bilinear_interpolate(self.esdf, x, y, self.resolution)
            if d <= self.vehicle_clearance:
                return False
            return True

        gx = int(np.clip(np.floor(x / self.resolution), 0, self.w - 1))
        gy = int(np.clip(np.floor(y / self.resolution), 0, self.h - 1))
        return not bool(self.occupancy[gy, gx])

    def _state_key(self, x: float, y: float, yaw: float) -> Tuple[int, int, int]:
        gx = int(np.clip(np.floor(x / self.resolution), 0, self.w - 1))
        gy = int(np.clip(np.floor(y / self.resolution), 0, self.h - 1))
        theta = wrap_to_pi(yaw)
        yaw_bin = int(np.floor((theta + np.pi) / (2.0 * np.pi) * self.cfg.yaw_bins)) % self.cfg.yaw_bins
        return gx, gy, yaw_bin

    def _reconstruct_path(
        self,
        goal_key: Tuple[int, int, int],
        records: Dict[Tuple[int, int, int], NodeRecord],
    ) -> np.ndarray:
        rev: List[Tuple[float, float, float]] = []
        key: Optional[Tuple[int, int, int]] = goal_key
        while key is not None:
            rec = records[key]
            rev.append((rec.x, rec.y, rec.yaw))
            key = rec.parent
        rev.reverse()
        return np.asarray(rev, dtype=np.float32)
