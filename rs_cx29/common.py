from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_cx8.common import query_yaw_field
from rs_cx21.common import macro_successor_candidates
from rs_cx23.common import FAMILY_BUCKETS, class_parts, macros_for_bucket


@dataclass(frozen=True)
class RolloutStep:
    score_gain: float
    next_record: Any


def _field_cost(field: np.ndarray, case: dict[str, Any], state: tuple[float, float, float]) -> float:
    return float(query_yaw_field(np.asarray(field, dtype=np.float32), float(state[0]), float(state[1]), float(state[2]), float(case['resolution'])))


def _primitive_successors(case: dict[str, Any], planner, record, h_pair) -> list[tuple[float, Any]]:
    out = []
    for steer, direction in list(getattr(planner, 'motion_primitives', [])):
        nxt = planner._simulate(float(record.x), float(record.y), float(record.yaw), float(steer), int(direction))
        if nxt is None:
            continue
        edge = float(planner._edge_cost(planner.cfg.step_size, float(steer), float(getattr(record, 'steer', 0.0)), int(direction)))
        na, nguided = h_pair(*nxt)
        out.append((
            float(nguided),
            SimpleNamespace(
                x=float(nxt[0]),
                y=float(nxt[1]),
                yaw=float(nxt[2]),
                g=float(record.g) + edge,
                guided=float(nguided),
                anchor=float(na),
                steer=float(steer),
                direction=int(direction),
            ),
        ))
    return out


def _macro_successors(case: dict[str, Any], planner, record, h_pair, lag_teacher, target_key: str, *, max_macros: int) -> list[Any]:
    mode, bucket = class_parts(str(target_key))
    macros = macros_for_bucket(lag_teacher, mode, bucket, max_macros=int(max_macros))
    if not macros:
        return []
    return list(macro_successor_candidates(case, planner, record, h_pair, macros, max_macros=len(macros)))


def best_step_for_key(case: dict[str, Any], field: np.ndarray, planner, record, h_pair, lag_teacher, target_key: str, *, max_macros: int) -> RolloutStep | None:
    start_cost = _field_cost(field, case, (float(record.x), float(record.y), float(record.yaw)))
    if str(target_key) == 'uncertain|none':
        candidates = _primitive_successors(case, planner, record, h_pair)
        if not candidates:
            return None
        best = None
        best_gain = float('-inf')
        for _, nrec in candidates:
            gain = start_cost - _field_cost(field, case, (float(nrec.x), float(nrec.y), float(nrec.yaw)))
            if gain > best_gain:
                best_gain = float(gain)
                best = nrec
        return RolloutStep(score_gain=float(best_gain), next_record=best)
    candidates = _macro_successors(case, planner, record, h_pair, lag_teacher, target_key, max_macros=int(max_macros))
    if not candidates:
        return None
    best = None
    best_gain = float('-inf')
    for cand in candidates:
        state = tuple(float(v) for v in cand.next_state)
        gain = start_cost - _field_cost(field, case, state)
        if gain > best_gain:
            best_gain = float(gain)
            best = SimpleNamespace(
                x=float(state[0]),
                y=float(state[1]),
                yaw=float(state[2]),
                g=float(record.g) + float(cand.edge_cost),
                guided=float(cand.guided),
                anchor=float(cand.anchor),
                steer=float(getattr(record, 'steer', 0.0)),
                direction=int(getattr(cand, 'direction', 1)),
            )
    return RolloutStep(score_gain=float(best_gain), next_record=best)


def rollout_score(case: dict[str, Any], field: np.ndarray, planner, record, h_pair, lag_teacher, target_key: str, *, max_macros: int, depth: int, discount: float) -> float:
    cur = SimpleNamespace(
        x=float(record.x),
        y=float(record.y),
        yaw=float(record.yaw),
        g=float(record.g),
        guided=float(record.guided),
        anchor=float(getattr(record, 'anchor', 0.0)),
        steer=float(getattr(record, 'steer', 0.0)),
        direction=int(getattr(record, 'direction', 1)),
    )
    total = 0.0
    gamma = 1.0
    for _ in range(int(max(depth, 1))):
        step = best_step_for_key(case, field, planner, cur, h_pair, lag_teacher, target_key, max_macros=int(max_macros))
        if step is None:
            break
        total += float(gamma) * float(step.score_gain)
        cur = step.next_record
        gamma *= float(discount)
    return float(total)


__all__ = [
    'FAMILY_BUCKETS',
    'RolloutStep',
    'best_step_for_key',
    'rollout_score',
]
