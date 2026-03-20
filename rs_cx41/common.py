from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from planner.hybrid_astar import SuccessorCandidate
from rs_cx27.common import coarse_state_key
from rs_cx39.common import BridgePathCandidate
from rs_cx40.common import bridge_efficiency
from rs_cx8.common import primitive_index_from_case, simulate_primitive_detailed


@dataclass(frozen=True)
class SubstrateBridgeNode:
    coarse_key: tuple[int, int, int]
    depth: int
    path: BridgePathCandidate
    bridge_eff: float


def _path_key(case: dict[str, Any], path: BridgePathCandidate, *, cell_stride: int, yaw_bins: int) -> tuple[int, int, int]:
    end = SimpleNamespace(x=float(path.next_state[0]), y=float(path.next_state[1]), yaw=float(path.next_state[2]))
    return coarse_state_key(end, case, cell_stride=int(cell_stride), yaw_bins=int(yaw_bins))


def _better_path(a: SubstrateBridgeNode, b: SubstrateBridgeNode) -> bool:
    if float(a.bridge_eff) != float(b.bridge_eff):
        return float(a.bridge_eff) > float(b.bridge_eff)
    if float(a.path.edge_cost) != float(b.path.edge_cost):
        return float(a.path.edge_cost) < float(b.path.edge_cost)
    return float(a.path.anchor) < float(b.path.anchor)


def _candidate_to_path(cand: SuccessorCandidate) -> BridgePathCandidate:
    return BridgePathCandidate(
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


def _expand_path(case: dict[str, Any], planner, h_pair, path: BridgePathCandidate) -> list[BridgePathCandidate]:
    pindex = primitive_index_from_case(case)
    out: list[BridgePathCandidate] = []
    for primitive_index in range(len(pindex)):
        steer = float(pindex.actual_steer(int(primitive_index), float(planner.max_steer)))
        direction = int(pindex.actual_direction(int(primitive_index)))
        sim = simulate_primitive_detailed(case, path.next_state, steer, direction)
        if not bool(sim.get('valid', False)) or sim.get('next_state', None) is None:
            continue
        nxt = tuple(float(v) for v in sim['next_state'])
        edge_cost = float(path.edge_cost + float(planner._edge_cost(planner.cfg.step_size, steer, path.last_steer, direction)))
        na, nguided = h_pair(float(nxt[0]), float(nxt[1]), float(nxt[2]))
        out.append(
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
    return out


def build_substrate_frontier(
    case: dict[str, Any],
    planner,
    h_pair,
    primitive_cands: list[SuccessorCandidate],
    *,
    current_anchor: float,
    cell_stride: int,
    yaw_bins: int,
    max_depth: int,
    max_frontier: int,
) -> list[SubstrateBridgeNode]:
    if not primitive_cands:
        return []
    out: list[SubstrateBridgeNode] = []

    current_paths = [_candidate_to_path(cand) for cand in primitive_cands]
    for depth in range(1, int(max_depth) + 1):
        collapsed: dict[tuple[tuple[int, int, int], int], SubstrateBridgeNode] = {}
        for path in current_paths:
            node = SubstrateBridgeNode(
                coarse_key=_path_key(case, path, cell_stride=int(cell_stride), yaw_bins=int(yaw_bins)),
                depth=int(depth),
                path=path,
                bridge_eff=float(bridge_efficiency(case, h_pair, float(current_anchor), path)),
            )
            key = (node.coarse_key, int(depth))
            prev = collapsed.get(key)
            if prev is None or _better_path(node, prev):
                collapsed[key] = node
        if not collapsed:
            break
        frontier_nodes = sorted(collapsed.values(), key=lambda item: (float(item.path.anchor), -float(item.bridge_eff), float(item.path.edge_cost)))[: int(max(max_frontier, 1))]
        out.extend(frontier_nodes)
        if depth >= int(max_depth):
            break
        next_paths: list[BridgePathCandidate] = []
        for node in frontier_nodes:
            next_paths.extend(_expand_path(case, planner, h_pair, node.path))
        current_paths = next_paths
        if not current_paths:
            break
    return out


__all__ = [
    'SubstrateBridgeNode',
    'build_substrate_frontier',
]

