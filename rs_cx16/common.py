from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorCandidate
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_cx8.common import primitive_index_from_case, run_hybrid_with_policy, simulate_primitive_detailed
from rs_cx15.common import (
    RecoverabilityEncoder,
    RecoverabilitySpec,
    increment_slot_counter,
    margin_key,
    normalize_clip,
    primitive_family,
    primitive_family_from_index,
    primitive_group,
    read_slot_counter,
    recoverability_margin,
    reverse_need_score,
    save_meta,
    update_global_stall,
)
from rs_cx14.common import augmented_bundle, standard_identity_error


@dataclass(frozen=True)
class MacroPrimitive:
    name: str
    primitive_indices: tuple[int, ...]
    family: str
    avg_gain: float
    hits: int


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg) -> tuple[dict[str, Any], np.ndarray]:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return augmented_bundle(bundle), np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return np.asarray(field, dtype=np.float32)


def _family_from_sequence(case: dict[str, Any], seq: tuple[int, ...]) -> str:
    if not seq:
        return 'macro:none'
    fams = [primitive_family_from_index(case, idx) for idx in seq]
    if all(fam.startswith('B-') for fam in fams):
        return 'macro:reverse'
    if any(fam.startswith('B-') for fam in fams):
        return 'macro:reverse-setup'
    if all(fam.endswith('-S') for fam in fams):
        return 'macro:straight'
    return 'macro:turn'


def _margin_from_stats(stats, spec: RecoverabilitySpec) -> float:
    return recoverability_margin(
        stats,
        clearance_w=0.22,
        corridor_w=0.24,
        trap_w=0.30,
        reverse_w=0.20,
        lateral_w=0.10,
        forward_w=0.06,
        heading_w=0.08,
        spec=spec,
    )


def compile_viability_table(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    *,
    horizon_steps: int,
    min_samples: int,
) -> dict[tuple[int, ...], dict[str, Any]]:
    buckets: dict[tuple[int, ...], list[tuple[float, float, float]]] = {}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        stats_list = [encoder.features(tuple(float(v) for v in state)) for state in path]
        margins = [_margin_from_stats(stats, spec) for stats in stats_list]
        for idx, stats in enumerate(stats_list[:-1]):
            future = margins[idx + 1 : min(len(margins), idx + 1 + int(max(horizon_steps, 1)))]
            best_future = max(future) if future else margins[idx]
            gain = float(best_future - margins[idx])
            key = margin_key(stats)
            buckets.setdefault(key, []).append((float(gain), float(stats.trap), float(stats.corridor)))
    out = {}
    for key, rows in buckets.items():
        if len(rows) < int(max(min_samples, 1)):
            continue
        gains = np.asarray([r[0] for r in rows], dtype=np.float32)
        traps = np.asarray([r[1] for r in rows], dtype=np.float32)
        corridors = np.asarray([r[2] for r in rows], dtype=np.float32)
        out[tuple(key)] = {
            'num_samples': int(len(rows)),
            'avg_future_gain': float(np.mean(gains)),
            'trap_mean': float(np.mean(traps)),
            'corridor_mean': float(np.mean(corridors)),
        }
    return out


def query_viability_table(table: dict[tuple[int, ...], dict[str, Any]], key: tuple[int, ...]) -> dict[str, Any] | None:
    return table.get(tuple(key), None)


def compile_macro_library(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    *,
    horizon_steps: int,
    min_gain: float,
    max_macros: int,
) -> list[MacroPrimitive]:
    seq_stats: dict[tuple[int, ...], dict[str, Any]] = {}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 4 or len(trace) < 2:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        stats_list = [encoder.features(tuple(float(v) for v in state)) for state in path]
        margins = [_margin_from_stats(stats, spec) for stats in stats_list]
        for idx in range(min(len(trace) - 1, len(margins) - 2)):
            future = margins[idx + 1 : min(len(margins), idx + 1 + int(max(horizon_steps, 2)))]
            if not future:
                continue
            best_gain = float(max(future) - margins[idx])
            if best_gain < float(min_gain):
                continue
            seq = tuple(int(v) for v in trace[idx : idx + 2])
            if len(seq) < 2:
                continue
            entry = seq_stats.setdefault(seq, {'gain_sum': 0.0, 'hits': 0, 'case': asset['case']})
            entry['gain_sum'] = float(entry['gain_sum']) + float(best_gain)
            entry['hits'] = int(entry['hits']) + 1
    macros: list[MacroPrimitive] = []
    for seq, entry in seq_stats.items():
        case = entry['case']
        family = _family_from_sequence(case, seq)
        macros.append(
            MacroPrimitive(
                name='macro_' + '_'.join(str(i) for i in seq),
                primitive_indices=tuple(seq),
                family=str(family),
                avg_gain=float(entry['gain_sum']) / max(int(entry['hits']), 1),
                hits=int(entry['hits']),
            )
        )
    macros.sort(key=lambda m: (float(m.avg_gain), int(m.hits)), reverse=True)
    if not macros:
        macros = [
            MacroPrimitive('macro_rev_setup_l', (1, 6), 'macro:reverse-setup', 0.0, 0),
            MacroPrimitive('macro_rev_setup_r', (3, 8), 'macro:reverse-setup', 0.0, 0),
            MacroPrimitive('macro_escape_l', (1, 0), 'macro:reverse-setup', 0.0, 0),
            MacroPrimitive('macro_escape_r', (3, 2), 'macro:reverse-setup', 0.0, 0),
        ]
    return macros[: int(max(max_macros, 1))]


def extract_escape_motif_memory(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    *,
    horizon_steps: int,
    min_gain: float,
) -> dict[tuple[int, ...], dict[str, Any]]:
    memory: dict[tuple[int, ...], dict[str, Any]] = {}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 4 or len(trace) < 2:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        stats_list = [encoder.features(tuple(float(v) for v in state)) for state in path]
        margins = [_margin_from_stats(stats, spec) for stats in stats_list]
        for idx in range(min(len(trace) - 1, len(margins) - 2)):
            future = margins[idx + 1 : min(len(margins), idx + 1 + int(max(horizon_steps, 2)))]
            if not future:
                continue
            best_gain = float(max(future) - margins[idx])
            if best_gain < float(min_gain):
                continue
            key = margin_key(stats_list[idx])
            seq = tuple(int(v) for v in trace[idx : idx + 2])
            entry = memory.setdefault(key, {'hits': 0, 'gain_sum': 0.0, 'seq_counts': {}})
            entry['hits'] = int(entry['hits']) + 1
            entry['gain_sum'] = float(entry['gain_sum']) + float(best_gain)
            seq_counts = entry['seq_counts']
            seq_counts[str(seq)] = int(seq_counts.get(str(seq), 0)) + 1
    out = {}
    for key, entry in memory.items():
        seq_counts = entry['seq_counts']
        best_seq = max(seq_counts.items(), key=lambda item: (int(item[1]), item[0]))[0] if seq_counts else None
        if best_seq is None:
            continue
        seq = tuple(int(v.strip()) for v in best_seq.strip('()').split(',') if v.strip())
        out[tuple(key)] = {
            'sequence': tuple(seq),
            'avg_gain': float(entry['gain_sum']) / max(int(entry['hits']), 1),
            'hits': int(entry['hits']),
        }
    return out


def _macro_segment(case: dict[str, Any], planner, state: tuple[float, float, float], seq: tuple[int, ...], prev_steer: float) -> tuple[tuple[float, float, float], tuple[tuple[float, float, float], ...], float] | None:
    pindex = primitive_index_from_case(case)
    cur = tuple(float(v) for v in state)
    segment_states = []
    total_cost = 0.0
    last_steer = float(prev_steer)
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
    return cur, tuple(segment_states), float(total_cost)


def macro_successor_candidates(
    case: dict[str, Any],
    planner,
    record,
    h_pair,
    macros: list[MacroPrimitive],
    *,
    max_macros: int,
) -> list[SuccessorCandidate]:
    out: list[SuccessorCandidate] = []
    state = (float(record.x), float(record.y), float(record.yaw))
    for macro in macros[: int(max(max_macros, 0))]:
        built = _macro_segment(case, planner, state, tuple(macro.primitive_indices), float(record.steer))
        if built is None:
            continue
        nxt, seg, edge_cost = built
        na, nguided = h_pair(*nxt)
        out.append(
            SuccessorCandidate(
                primitive_index=-1,
                steer=0.0,
                direction=int(-1 if 'reverse' in str(macro.family) else 1),
                next_state=tuple(nxt),
                edge_cost=float(edge_cost),
                anchor=float(na),
                guided=float(nguided),
                sim_info=None,
                family=str(macro.family),
                source='macro',
                segment_states=tuple(seg),
            )
        )
    return out


def macro_family(candidate: SuccessorCandidate) -> str:
    if getattr(candidate, 'family', None):
        return str(candidate.family)
    return primitive_family(candidate)


def macro_group(family: str) -> str:
    fam = str(family)
    if fam.startswith('macro:'):
        return fam
    return primitive_group(fam)


def local_review_score(
    stats,
    current_margin: float,
    *,
    candidate_margin: float,
    reverse_need: float,
    family: str,
) -> float:
    score = float(candidate_margin - float(current_margin))
    if float(reverse_need) > 0.08 and ('reverse' in str(family) or str(family).startswith('B-')):
        score += 0.06
    score += 0.02 * float(stats.corridor) - 0.03 * float(stats.trap)
    return float(score)


__all__ = [
    'MacroPrimitive',
    'RecoverabilityEncoder',
    'RecoverabilitySpec',
    'build_nonholonomic_field',
    'build_standard_field',
    'compile_macro_library',
    'compile_viability_table',
    'extract_escape_motif_memory',
    'increment_slot_counter',
    'local_review_score',
    'macro_family',
    'macro_group',
    'macro_successor_candidates',
    'margin_key',
    'normalize_clip',
    'primitive_family',
    'primitive_group',
    'query_viability_table',
    'read_slot_counter',
    'recoverability_margin',
    'reverse_need_score',
    'run_hybrid_with_policy',
    'save_meta',
    'standard_identity_error',
    'update_global_stall',
]
