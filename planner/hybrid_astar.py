from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from config import PlannerConfig, VehicleConfig
from planner.heuristics import HeuristicFn, compose_guidance, euclidean_heuristic
from utils.common import bilinear_interpolate, wrap_to_pi

State = Tuple[float, float, float]
StateKey = Tuple[int, int, int]
HeuristicPairFn = Callable[[float, float, float], Tuple[float, float]]
OpenQueueItem = Tuple[float, float, int, StateKey]
AnchorQueueItem = Tuple[float, int, StateKey]


@dataclass
class NodeRecord:
    x: float
    y: float
    yaw: float
    g: float
    anchor: float
    guided: float
    parent: Optional[StateKey]
    steer: float
    direction: int
    depth: int = 0
    priority_bias_primary: float = 0.0
    priority_bias_secondary: float = 0.0
    segment_states: Tuple[State, ...] = ()


@dataclass(frozen=True)
class SuccessorDecision:
    skip: bool = False
    extra_edge_cost: float = 0.0
    priority_primary_delta: float = 0.0
    priority_secondary_delta: float = 0.0


@dataclass(frozen=True)
class SuccessorCandidate:
    primitive_index: int
    steer: float
    direction: int
    next_state: State
    edge_cost: float
    anchor: float
    guided: float
    sim_info: Optional[dict[str, Any]] = None
    family: Optional[str] = None
    source: str = "primitive"
    segment_states: Optional[Tuple[State, ...]] = None


@dataclass
class PlanResult:
    success: bool
    path: np.ndarray
    cost: float
    expansions: int
    runtime_ms: float
    message: str
    expanded_xy: np.ndarray


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
        start: State,
        goal: State,
        guidance_fn: Optional[HeuristicFn] = None,
        anchor_fn: Optional[HeuristicFn] = None,
        main_mode: str = "anchor",
        record_expanded: bool = False,
        successor_policy: Optional[Any] = None,
    ) -> PlanResult:
        t0 = time.perf_counter()
        if anchor_fn is None:
            anchor_fn = euclidean_heuristic((goal[0], goal[1]))
        h_pair = compose_guidance(anchor_fn, guidance_fn, self.cfg.guidance_blend)

        if not self._state_is_valid(start[0], start[1]) or not self._state_is_valid(goal[0], goal[1]):
            return PlanResult(
                False,
                np.zeros((0, 3), dtype=np.float32),
                np.inf,
                0,
                0.0,
                "Start or goal in collision",
                np.zeros((0, 2), dtype=np.float32),
            )

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
                record_expanded=record_expanded,
                successor_policy=successor_policy,
            )
            pre_expansions = warm.expansions
            if warm.success:
                upper_bound = warm.cost
                pre_success = True

        main = self._search(
            start=start,
            goal=goal,
            h_pair=h_pair,
            mode=main_mode,
            max_expansions=self.cfg.max_expansions,
            upper_bound=upper_bound,
            stop_on_first_goal=False,
            record_expanded=record_expanded,
            successor_policy=successor_policy,
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
        start: State,
        goal: State,
        h_pair: HeuristicPairFn,
        mode: str,
        max_expansions: int,
        upper_bound: float,
        stop_on_first_goal: bool,
        record_expanded: bool,
        successor_policy: Optional[Any],
    ) -> PlanResult:
        start_key = self._state_key(*start)
        a0, g0 = h_pair(*start)

        records: Dict[StateKey, NodeRecord] = {
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
                depth=0,
                priority_bias_primary=0.0,
                priority_bias_secondary=0.0,
                segment_states=((float(start[0]), float(start[1]), float(start[2])),),
            )
        }

        open_heap: List[OpenQueueItem] = []
        anchor_heap: List[AnchorQueueItem] = []
        counter = 0
        p0, s0 = self._priority(records[start_key], mode)
        heapq.heappush(open_heap, (p0, s0, counter, start_key))
        heapq.heappush(anchor_heap, (records[start_key].g + records[start_key].anchor, counter, start_key))

        expanded_best_g: Dict[StateKey, float] = {}
        best_goal_key: Optional[StateKey] = None
        best_goal_cost = float(upper_bound)
        expansions = 0
        expanded_xy: List[Tuple[float, float]] = []
        search_state: dict[str, Any] = {
            'mode': str(mode),
            'popped': 0,
            'expansions': 0,
            'invalid_successors': 0,
            'valid_successors': 0,
            'accepted_successors': 0,
            'best_goal_cost': float(best_goal_cost),
            'last_expanded_anchor': float(a0),
        }

        if successor_policy is not None and hasattr(successor_policy, 'start_search'):
            successor_policy.start_search(
                planner=self,
                start=start,
                goal=goal,
                h_pair=h_pair,
                search_state=search_state,
            )

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
            search_state['popped'] = int(search_state.get('popped', 0)) + 1
            search_state['expansions'] = int(expansions)
            search_state['best_goal_cost'] = float(best_goal_cost)
            search_state['last_expanded_anchor'] = float(rec.anchor)
            if record_expanded:
                expanded_xy.append((rec.x, rec.y))

            if self._is_goal(rec.x, rec.y, rec.yaw, goal):
                if rec.g < best_goal_cost:
                    best_goal_cost = rec.g
                    best_goal_key = key
                    search_state['best_goal_cost'] = float(best_goal_cost)
                if stop_on_first_goal:
                    path = self._reconstruct_path(key, records)
                    return PlanResult(
                        True,
                        path,
                        float(rec.g),
                        expansions,
                        0.0,
                        "goal found",
                        np.asarray(expanded_xy, dtype=np.float32),
                    )

            if best_goal_key is not None:
                min_anchor = self._peek_min_anchor(anchor_heap, records)
                search_state['current_min_anchor'] = float(min_anchor)
                if min_anchor >= best_goal_cost - 1e-6:
                    path = self._reconstruct_path(best_goal_key, records)
                    return PlanResult(
                        True,
                        path,
                        float(best_goal_cost),
                        expansions,
                        0.0,
                        "optimal",
                        np.asarray(expanded_xy, dtype=np.float32),
                    )

            node_ctx: Any = None
            primitive_order = list(range(len(self.motion_primitives)))
            if successor_policy is not None and hasattr(successor_policy, 'prepare_expand'):
                prepared = successor_policy.prepare_expand(
                    planner=self,
                    record=rec,
                    goal=goal,
                    records=records,
                    open_heap=open_heap,
                    anchor_heap=anchor_heap,
                    search_state=search_state,
                    h_pair=h_pair,
                )
                if isinstance(prepared, dict):
                    node_ctx = prepared
                    if 'primitive_order' in prepared:
                        raw_order = [int(i) for i in prepared['primitive_order']]
                        seen = set()
                        primitive_order = []
                        for idx in raw_order:
                            if 0 <= idx < len(self.motion_primitives) and idx not in seen:
                                primitive_order.append(idx)
                                seen.add(idx)
                        for idx in range(len(self.motion_primitives)):
                            if idx not in seen:
                                primitive_order.append(idx)
                else:
                    node_ctx = prepared

            invalid_local = 0
            valid_local = 0
            accepted_local = 0
            need_sim_stats = bool(successor_policy is not None and getattr(successor_policy, 'requires_sim_stats', False))
            raw_candidates: List[SuccessorCandidate] = []
            for primitive_index in primitive_order:
                steer, direction = self.motion_primitives[int(primitive_index)]
                sim_info = self._simulate_detailed(rec.x, rec.y, rec.yaw, steer, direction) if need_sim_stats else None
                if need_sim_stats:
                    if not sim_info or not bool(sim_info.get('valid', False)) or sim_info.get('next_state', None) is None:
                        invalid_local += 1
                        continue
                    nx, ny, nyaw = sim_info['next_state']
                else:
                    nxt = self._simulate(rec.x, rec.y, rec.yaw, steer, direction)
                    if nxt is None:
                        invalid_local += 1
                        continue
                    nx, ny, nyaw = nxt
                valid_local += 1

                edge = self._edge_cost(self.cfg.step_size, steer, rec.steer, direction)
                na, nguided = h_pair(nx, ny, nyaw)
                raw_candidates.append(SuccessorCandidate(
                    primitive_index=int(primitive_index),
                    steer=float(steer),
                    direction=int(direction),
                    next_state=(float(nx), float(ny), float(nyaw)),
                    edge_cost=float(edge),
                    anchor=float(na),
                    guided=float(nguided),
                    sim_info=sim_info,
                    family=None,
                    source="primitive",
                    segment_states=((float(nx), float(ny), float(nyaw)),),
                ))

            if successor_policy is not None and hasattr(successor_policy, 'extra_successors'):
                extra = successor_policy.extra_successors(
                    planner=self,
                    record=rec,
                    goal=goal,
                    records=records,
                    candidates=raw_candidates,
                    node_ctx=node_ctx,
                    search_state=search_state,
                    h_pair=h_pair,
                )
                if extra is not None:
                    for cand in extra:
                        if isinstance(cand, SuccessorCandidate):
                            raw_candidates.append(cand)

            ranked_candidates: List[Tuple[SuccessorCandidate, SuccessorDecision]] = [(cand, SuccessorDecision()) for cand in raw_candidates]
            if successor_policy is not None and hasattr(successor_policy, 'rank_successors'):
                ranked = successor_policy.rank_successors(
                    planner=self,
                    record=rec,
                    goal=goal,
                    records=records,
                    candidates=raw_candidates,
                    node_ctx=node_ctx,
                    search_state=search_state,
                    h_pair=h_pair,
                )
                if ranked is not None:
                    ranked_candidates = []
                    for item in ranked:
                        if isinstance(item, tuple) and len(item) == 2:
                            cand, maybe_decision = item
                        else:
                            cand, maybe_decision = item, SuccessorDecision()
                        if isinstance(maybe_decision, SuccessorDecision):
                            decision = maybe_decision
                        else:
                            decision = SuccessorDecision(
                                skip=bool(maybe_decision.get('skip', False)),
                                extra_edge_cost=float(maybe_decision.get('extra_edge_cost', 0.0)),
                                priority_primary_delta=float(maybe_decision.get('priority_primary_delta', 0.0)),
                                priority_secondary_delta=float(maybe_decision.get('priority_secondary_delta', 0.0)),
                            )
                        ranked_candidates.append((cand, decision))

            for cand, decision in ranked_candidates:
                if successor_policy is not None and not hasattr(successor_policy, 'rank_successors') and hasattr(successor_policy, 'adjust_successor'):
                    maybe = successor_policy.adjust_successor(
                        planner=self,
                        record=rec,
                        goal=goal,
                        records=records,
                        primitive_index=int(cand.primitive_index),
                        steer=float(cand.steer),
                        direction=int(cand.direction),
                        next_state=cand.next_state,
                        base_edge_cost=float(cand.edge_cost),
                        base_anchor=float(cand.anchor),
                        base_guided=float(cand.guided),
                        sim_info=cand.sim_info,
                        node_ctx=node_ctx,
                        search_state=search_state,
                        h_pair=h_pair,
                    )
                    if isinstance(maybe, SuccessorDecision):
                        decision = maybe
                    elif isinstance(maybe, dict):
                        decision = SuccessorDecision(
                            skip=bool(maybe.get('skip', False)),
                            extra_edge_cost=float(maybe.get('extra_edge_cost', 0.0)),
                            priority_primary_delta=float(maybe.get('priority_primary_delta', 0.0)),
                            priority_secondary_delta=float(maybe.get('priority_secondary_delta', 0.0)),
                        )
                if decision.skip:
                    continue

                ng = rec.g + float(cand.edge_cost) + float(decision.extra_edge_cost)
                if ng >= best_goal_cost:
                    continue
                if ng + float(cand.anchor) >= best_goal_cost:
                    continue

                nx, ny, nyaw = cand.next_state
                nkey = self._state_key(nx, ny, nyaw)
                old = records.get(nkey)
                if old is not None and ng >= old.g - 1e-9:
                    continue

                nrec = NodeRecord(
                    x=nx,
                    y=ny,
                    yaw=nyaw,
                    g=ng,
                    anchor=float(cand.anchor),
                    guided=float(cand.guided),
                    parent=key,
                    steer=float(cand.steer),
                    direction=int(cand.direction),
                    depth=int(rec.depth) + 1,
                    priority_bias_primary=float(decision.priority_primary_delta),
                    priority_bias_secondary=float(decision.priority_secondary_delta),
                    segment_states=tuple(cand.segment_states) if cand.segment_states is not None else ((float(nx), float(ny), float(nyaw)),),
                )
                records[nkey] = nrec
                counter += 1
                p, s = self._priority(nrec, mode)
                heapq.heappush(open_heap, (p, s, counter, nkey))
                heapq.heappush(anchor_heap, (ng + float(cand.anchor), counter, nkey))
                accepted_local += 1

            search_state['invalid_successors'] = int(search_state.get('invalid_successors', 0)) + int(invalid_local)
            search_state['valid_successors'] = int(search_state.get('valid_successors', 0)) + int(valid_local)
            search_state['accepted_successors'] = int(search_state.get('accepted_successors', 0)) + int(accepted_local)

            if successor_policy is not None and hasattr(successor_policy, 'complete_expand'):
                successor_policy.complete_expand(
                    planner=self,
                    record=rec,
                    goal=goal,
                    records=records,
                    node_ctx=node_ctx,
                    invalid_local=int(invalid_local),
                    valid_local=int(valid_local),
                    accepted_local=int(accepted_local),
                    search_state=search_state,
                    h_pair=h_pair,
                )

        if best_goal_key is not None:
            path = self._reconstruct_path(best_goal_key, records)
            return PlanResult(
                True,
                path,
                float(best_goal_cost),
                expansions,
                0.0,
                "bounded by expansion limit",
                np.asarray(expanded_xy, dtype=np.float32),
            )

        return PlanResult(
            False,
            np.zeros((0, 3), dtype=np.float32),
            np.inf,
            expansions,
            0.0,
            "search failed",
            np.asarray(expanded_xy, dtype=np.float32),
        )

    def _priority(self, rec: NodeRecord, mode: str) -> Tuple[float, float]:
        f_anchor = rec.g + rec.anchor
        f_guided = rec.g + rec.guided
        if mode == "guided":
            return (
                f_guided + float(rec.priority_bias_primary),
                f_anchor + float(rec.priority_bias_secondary),
            )
        return (
            f_anchor + float(rec.priority_bias_primary),
            f_guided + float(rec.priority_bias_secondary),
        )

    def _peek_min_anchor(
        self,
        anchor_heap: List[AnchorQueueItem],
        records: Dict[StateKey, NodeRecord],
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

    def _is_goal(self, x: float, y: float, yaw: float, goal: State) -> bool:
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

    def _simulate(self, x: float, y: float, yaw: float, steer: float, direction: int) -> Optional[State]:
        info = self._simulate_detailed(x, y, yaw, steer, direction)
        nxt = info.get('next_state', None)
        if not bool(info.get('valid', False)) or nxt is None:
            return None
        return nxt

    def _simulate_detailed(self, x: float, y: float, yaw: float, steer: float, direction: int) -> dict[str, Any]:
        n = max(1, int(np.ceil(self.cfg.step_size / self.cfg.collision_check_step)))
        ds = self.cfg.step_size / n

        cx, cy, cyaw = x, y, yaw
        min_clearance = float('inf')
        end_clearance = float('inf')
        for _ in range(n):
            signed_ds = ds * direction
            cx += signed_ds * math.cos(cyaw)
            cy += signed_ds * math.sin(cyaw)
            cyaw = wrap_to_pi(cyaw + signed_ds * math.tan(steer) / self.vehicle_cfg.wheel_base)
            if cx < 0.0 or cy < 0.0 or cx >= self.w * self.resolution or cy >= self.h * self.resolution:
                return {'valid': False, 'next_state': None, 'min_clearance': -1.0, 'end_clearance': -1.0}
            if self.esdf is not None:
                clearance = float(bilinear_interpolate(self.esdf, cx, cy, self.resolution))
                min_clearance = min(min_clearance, clearance)
                end_clearance = clearance
                if clearance <= self.vehicle_clearance:
                    return {'valid': False, 'next_state': None, 'min_clearance': float(min_clearance), 'end_clearance': float(end_clearance)}
            elif not self._state_is_valid(cx, cy):
                return {'valid': False, 'next_state': None, 'min_clearance': -1.0, 'end_clearance': -1.0}

        if self.esdf is None:
            min_clearance = float('nan')
            end_clearance = float('nan')
        return {'valid': True, 'next_state': (cx, cy, cyaw), 'min_clearance': float(min_clearance), 'end_clearance': float(end_clearance)}

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

    def _state_key(self, x: float, y: float, yaw: float) -> StateKey:
        gx = int(np.clip(np.floor(x / self.resolution), 0, self.w - 1))
        gy = int(np.clip(np.floor(y / self.resolution), 0, self.h - 1))
        theta = wrap_to_pi(yaw)
        yaw_bin = int(np.floor((theta + np.pi) / (2.0 * np.pi) * self.cfg.yaw_bins)) % self.cfg.yaw_bins
        return gx, gy, yaw_bin

    def _reconstruct_path(
        self,
        goal_key: StateKey,
        records: Dict[StateKey, NodeRecord],
    ) -> np.ndarray:
        rev_segments: List[List[Tuple[float, float, float]]] = []
        key: Optional[StateKey] = goal_key
        while key is not None:
            rec = records[key]
            seg = list(rec.segment_states) if rec.segment_states else [(rec.x, rec.y, rec.yaw)]
            rev_segments.append([(float(x), float(y), float(yaw)) for x, y, yaw in seg])
            key = rec.parent
        rev_segments.reverse()
        path: List[Tuple[float, float, float]] = []
        for idx, seg in enumerate(rev_segments):
            if idx == 0:
                path.extend(seg)
            else:
                path.extend(seg)
        return np.asarray(path, dtype=np.float32)
