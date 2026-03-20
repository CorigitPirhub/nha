from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorCandidate
from rs_cx8.common import primitive_index_from_case, simulate_primitive_detailed


@dataclass(frozen=True)
class BridgePathCandidate:
    primitive_indices: tuple[int, ...]
    first_steer: float
    last_steer: float
    direction: int
    next_state: tuple[float, float, float]
    edge_cost: float
    anchor: float
    guided: float
    segment_states: tuple[tuple[float, float, float], ...]


def _macro_segment_from_state(case: dict[str, Any], planner, state: tuple[float, float, float], seq: tuple[int, ...], prev_steer: float) -> tuple[tuple[float, float, float], tuple[tuple[float, float, float], ...], float, int] | None:
    pindex = primitive_index_from_case(case)
    cur = tuple(float(v) for v in state)
    segment_states = []
    total_cost = 0.0
    last_steer = float(prev_steer)
    last_direction = 1
    for primitive_index in seq:
        steer = float(pindex.actual_steer(int(primitive_index), float(planner.max_steer)))
        direction = int(pindex.actual_direction(int(primitive_index)))
        sim = simulate_primitive_detailed(case, cur, steer, direction)
        if not bool(sim.get('valid', False)) or sim.get('next_state', None) is None:
            return None
        nxt = tuple(float(v) for v in sim['next_state'])
        total_cost += float(planner._edge_cost(planner.cfg.step_size, steer, last_steer, direction))
        segment_states.append(nxt)
        cur = nxt
        last_steer = steer
        last_direction = int(direction)
    return cur, tuple(segment_states), float(total_cost), int(last_direction)


def enumerate_bridge_paths(
    case: dict[str, Any],
    planner,
    h_pair,
    primitive_cands: list[SuccessorCandidate],
    *,
    max_depth: int,
    max_frontier: int,
) -> list[BridgePathCandidate]:
    if not primitive_cands:
        return []
    frontier: list[BridgePathCandidate] = []
    out: list[BridgePathCandidate] = []
    for cand in primitive_cands:
        frontier.append(
            BridgePathCandidate(
                primitive_indices=(int(cand.primitive_index),),
                first_steer=float(cand.steer),
                last_steer=float(cand.steer),
                direction=int(cand.direction),
                next_state=tuple(map(float, cand.next_state)),
                edge_cost=float(cand.edge_cost),
                anchor=float(cand.anchor),
                guided=float(cand.guided),
                segment_states=tuple(tuple(map(float, s)) for s in (cand.segment_states or (tuple(map(float, cand.next_state)),))),
            )
        )
    frontier.sort(key=lambda item: float(item.anchor))
    frontier = frontier[: int(max(max_frontier, 1))]
    out.extend(frontier)
    if int(max_depth) <= 1:
        return out

    pindex = primitive_index_from_case(case)
    for _depth in range(2, int(max_depth) + 1):
        next_frontier: list[BridgePathCandidate] = []
        for path in frontier:
            for primitive_index in range(len(pindex)):
                steer = float(pindex.actual_steer(int(primitive_index), float(planner.max_steer)))
                direction = int(pindex.actual_direction(int(primitive_index)))
                sim = simulate_primitive_detailed(case, path.next_state, steer, direction)
                if not bool(sim.get('valid', False)) or sim.get('next_state', None) is None:
                    continue
                nxt = tuple(float(v) for v in sim['next_state'])
                edge_cost = float(path.edge_cost + float(planner._edge_cost(planner.cfg.step_size, steer, path.last_steer, direction)))
                na, nguided = h_pair(float(nxt[0]), float(nxt[1]), float(nxt[2]))
                next_frontier.append(
                    BridgePathCandidate(
                        primitive_indices=tuple(list(path.primitive_indices) + [int(primitive_index)]),
                        first_steer=float(path.first_steer),
                        last_steer=float(steer),
                        direction=int(direction),
                        next_state=tuple(nxt),
                        edge_cost=float(edge_cost),
                        anchor=float(na),
                        guided=float(nguided),
                        segment_states=tuple(list(path.segment_states) + [tuple(nxt)]),
                    )
                )
        if not next_frontier:
            break
        next_frontier.sort(key=lambda item: float(item.anchor))
        frontier = next_frontier[: int(max(max_frontier, 1))]
        out.extend(frontier)
    return out


def _compose_review_candidate(case: dict[str, Any], planner, h_pair, bridge: BridgePathCandidate, macro: Any, prior_score: float, review_score: float, *, source: str) -> SuccessorCandidate | None:
    built = _macro_segment_from_state(case, planner, bridge.next_state, tuple(int(v) for v in macro.primitive_indices), float(bridge.last_steer))
    if built is None:
        return None
    nxt, seg, macro_cost, last_direction = built
    na, nguided = h_pair(float(nxt[0]), float(nxt[1]), float(nxt[2]))
    seg_states = tuple(list(bridge.segment_states) + list(seg))
    return SuccessorCandidate(
        primitive_index=-1,
        steer=float(bridge.first_steer),
        direction=int(last_direction),
        next_state=tuple(nxt),
        edge_cost=float(bridge.edge_cost + macro_cost),
        anchor=float(na),
        guided=float(nguided),
        sim_info={
            'prior_score': float(prior_score),
            'review_score': float(review_score),
            'bridge_depth': int(len(bridge.primitive_indices)),
            'bridge_primitives': tuple(int(v) for v in bridge.primitive_indices),
        },
        family=str(getattr(macro, 'family', 'macro:review')),
        source=str(source),
        segment_states=seg_states,
    )


def detour_review_candidates(
    case: dict[str, Any],
    planner,
    h_pair,
    primitive_cands: list[SuccessorCandidate],
    macro_choices: list[tuple[SuccessorCandidate, Any, float, float]],
) -> list[SuccessorCandidate]:
    out: list[SuccessorCandidate] = []
    for prim_cand, macro, prior_score, review_score in macro_choices:
        bridge = BridgePathCandidate(
            primitive_indices=(int(prim_cand.primitive_index),),
            first_steer=float(prim_cand.steer),
            last_steer=float(prim_cand.steer),
            direction=int(prim_cand.direction),
            next_state=tuple(map(float, prim_cand.next_state)),
            edge_cost=float(prim_cand.edge_cost),
            anchor=float(prim_cand.anchor),
            guided=float(prim_cand.guided),
            segment_states=tuple(tuple(map(float, s)) for s in (prim_cand.segment_states or (tuple(map(float, prim_cand.next_state)),))),
        )
        built = _compose_review_candidate(case, planner, h_pair, bridge, macro, float(prior_score), float(review_score), source='review')
        if built is None:
            continue
        sim_info = dict(built.sim_info or {})
        sim_info['base_primitive_index'] = int(prim_cand.primitive_index)
        out.append(
            SuccessorCandidate(
                primitive_index=int(built.primitive_index),
                steer=float(built.steer),
                direction=int(built.direction),
                next_state=tuple(built.next_state),
                edge_cost=float(built.edge_cost),
                anchor=float(built.anchor),
                guided=float(built.guided),
                sim_info=sim_info,
                family=str(built.family),
                source=str(built.source),
                segment_states=tuple(built.segment_states or ()),
            )
        )
    return out


def bridge_review_candidates(
    case: dict[str, Any],
    planner,
    h_pair,
    bridge_choices: list[tuple[BridgePathCandidate, Any, float, float]],
    *,
    source: str = 'bridge_review',
) -> list[SuccessorCandidate]:
    out: list[SuccessorCandidate] = []
    for bridge, macro, prior_score, review_score in bridge_choices:
        row = _compose_review_candidate(case, planner, h_pair, bridge, macro, float(prior_score), float(review_score), source=str(source))
        if row is not None:
            out.append(row)
    return out


__all__ = [
    'BridgePathCandidate',
    'bridge_review_candidates',
    'detour_review_candidates',
    'enumerate_bridge_paths',
]
