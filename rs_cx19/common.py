from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx16.common import (
    MacroPrimitive,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field,
    build_standard_field,
    compile_macro_library,
    compile_viability_table,
    macro_family,
    macro_successor_candidates,
    margin_key,
    query_viability_table,
    recoverability_margin,
    reverse_need_score,
    run_hybrid_with_policy,
    save_meta,
    standard_identity_error,
)
from rs_cx8.common import primitive_index_from_case


VIABILITY_STATES = (
    'safe_progress',
    'recoverable_boundary',
    'reverse_required',
    'near_trap',
)


@dataclass(frozen=True)
class ViabilityStateConfig:
    safe_margin: float
    boundary_margin: float
    reverse_need_thr: float
    oracle_gain_thr: float
    trap_high_thr: float
    corridor_low_thr: float


@dataclass(frozen=True)
class CompilerEdge:
    sequence: tuple[int, ...]
    family: str
    recovered_state: str
    avg_gain: float
    hits: int


FEATURE_NAMES = (
    'margin',
    'oracle_gain',
    'clearance',
    'trap',
    'corridor',
    'reverse_clearance',
    'forward_clearance',
    'lateral_clearance',
    'heading_cos',
    'goal_distance_norm',
    'reverse_need',
)


def classify_viability_state(stats, margin: float, oracle_gain: float, cfg: ViabilityStateConfig, spec: RecoverabilitySpec) -> str:
    reverse_need = float(reverse_need_score(stats, spec))
    if reverse_need >= float(cfg.reverse_need_thr) and float(margin) <= max(float(cfg.safe_margin), float(cfg.boundary_margin)):
        return 'reverse_required'
    if float(margin) <= float(cfg.boundary_margin) and float(stats.trap) >= float(cfg.trap_high_thr) and float(stats.corridor) <= float(cfg.corridor_low_thr):
        return 'near_trap'
    if float(margin) <= float(cfg.safe_margin) or float(oracle_gain) >= float(cfg.oracle_gain_thr):
        return 'recoverable_boundary'
    return 'safe_progress'


def state_family_bonus(state: str, family: str, direction: int) -> float:
    fam = str(family)
    if state == 'reverse_required':
        if 'reverse' in fam or int(direction) < 0:
            return 0.12
        return -0.04
    if state == 'near_trap':
        if 'reverse' in fam or 'escape' in fam:
            return 0.10
        if fam.startswith('F-'):
            return -0.04
    if state == 'recoverable_boundary':
        if fam.startswith('macro:'):
            return 0.05
    return 0.0


def feature_vector(stats, margin: float, oracle_gain: float, spec: RecoverabilitySpec) -> np.ndarray:
    return np.asarray([
        float(margin),
        float(oracle_gain),
        float(stats.clearance),
        float(stats.trap),
        float(stats.corridor),
        float(stats.reverse_clearance),
        float(stats.forward_clearance),
        float(max(stats.left_clearance, stats.right_clearance)),
        float(stats.heading_cos),
        float(min(float(stats.goal_distance), float(spec.goal_dist_clip_m))) / max(float(spec.goal_dist_clip_m), 1e-6),
        float(reverse_need_score(stats, spec)),
    ], dtype=np.float32)


def _base_margin(stats, spec: RecoverabilitySpec) -> float:
    return recoverability_margin(
        stats,
        clearance_w=0.20,
        corridor_w=0.26,
        trap_w=0.36,
        reverse_w=0.24,
        lateral_w=0.10,
        forward_w=0.04,
        heading_w=0.08,
        spec=spec,
    )


def state_family_bonus(state: str, family: str, direction: int) -> float:
    fam = str(family)
    if state == 'reverse_required':
        if 'reverse' in fam or int(direction) < 0:
            return 0.12
        return -0.04
    if state == 'near_trap':
        if 'reverse' in fam or 'escape' in fam:
            return 0.10
        if fam.startswith('F-'):
            return -0.04
    if state == 'recoverable_boundary':
        if fam.startswith('macro:'):
            return 0.05
    return 0.0


def compile_state_macro_support(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    state_cfg: ViabilityStateConfig,
    macros: list[MacroPrimitive],
    viability_table: dict[tuple[int, ...], dict[str, Any]],
    *,
    horizon_steps: int,
    min_gain: float,
) -> tuple[dict[str, dict[str, SupportBand]], dict[str, dict[str, float]]]:
    macro_map = {tuple(m.primitive_indices): m for m in macros}
    rows_by_state: dict[str, dict[str, list[np.ndarray]]] = {state: {} for state in VIABILITY_STATES}
    gains_by_state: dict[str, dict[str, list[float]]] = {state: {} for state in VIABILITY_STATES}
    counts_by_state: dict[str, dict[str, int]] = {state: {} for state in VIABILITY_STATES}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 4 or len(trace) < 2:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        stats_list = [encoder.features(tuple(float(v) for v in state)) for state in path]
        margins = [_base_margin(stats, spec) for stats in stats_list]
        for idx in range(min(len(trace) - 1, len(margins) - 2)):
            seq = tuple(int(v) for v in trace[idx : idx + 2])
            macro = macro_map.get(seq, None)
            if macro is None:
                continue
            future = margins[idx + 1 : min(len(margins), idx + 1 + int(max(horizon_steps, 2)))]
            if not future:
                continue
            gain = float(max(future) - margins[idx])
            if gain < float(min_gain):
                continue
            stats = stats_list[idx]
            oracle = query_viability_table(viability_table, margin_key(stats))
            oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
            state = classify_viability_state(stats, margins[idx], oracle_gain, state_cfg, spec)
            feat = feature_vector(stats, margins[idx], oracle_gain, spec)
            rows_by_state[state].setdefault(str(macro.name), []).append(feat)
            gains_by_state[state].setdefault(str(macro.name), []).append(gain)
            counts_by_state[state][str(macro.name)] = int(counts_by_state[state].get(str(macro.name), 0)) + 1
    support: dict[str, dict[str, SupportBand]] = {}
    counts: dict[str, dict[str, float]] = {}
    for state in VIABILITY_STATES:
        support[state] = {}
        counts[state] = {}
        for macro in macros:
            rows = rows_by_state.get(state, {}).get(str(macro.name), [])
            gains = gains_by_state.get(state, {}).get(str(macro.name), [])
            band = fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)
            if band is not None:
                support[state][str(macro.name)] = band
                counts[state][str(macro.name)] = float(counts_by_state[state].get(str(macro.name), 0))
    return support, counts


def choose_state_macros(
    state: str,
    macros: list[MacroPrimitive],
    support: dict[str, dict[str, SupportBand]],
    counts: dict[str, dict[str, float]],
    feat: np.ndarray,
    *,
    gain_hint: float,
    slack: float,
    max_macros: int,
) -> list[MacroPrimitive]:
    support_state = support.get(str(state), {})
    count_state = counts.get(str(state), {})
    scored: list[tuple[float, MacroPrimitive]] = []
    for macro in macros:
        band = support_state.get(str(macro.name), None)
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched:
            score = float(sim) + 0.04 * float(macro.avg_gain) + 0.01 * float(count_state.get(str(macro.name), 0.0))
            scored.append((score, macro))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [macro for _, macro in scored[: int(max(max_macros, 0))]]


def _seq_family(case: dict[str, Any], seq: tuple[int, ...]) -> str:
    if not seq:
        return 'motif:none'
    pindex = primitive_index_from_case(case)
    fams = [pindex.label(int(v)) for v in seq]
    if any(str(fam).startswith('B-') for fam in fams):
        return 'motif:reverse'
    return 'motif:forward'


def compile_motif_compiler_graph(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    state_cfg: ViabilityStateConfig,
    viability_table: dict[tuple[int, ...], dict[str, Any]],
    *,
    horizon_steps: int,
    min_gain: float,
) -> tuple[dict[str, list[CompilerEdge]], dict[str, dict[str, SupportBand]]]:
    rows_by_state: dict[str, dict[tuple[int, ...], list[np.ndarray]]] = {state: {} for state in VIABILITY_STATES}
    gains_by_state: dict[str, dict[tuple[int, ...], list[float]]] = {state: {} for state in VIABILITY_STATES}
    meta_by_state: dict[str, dict[tuple[int, ...], dict[str, Any]]] = {state: {} for state in VIABILITY_STATES}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 5 or len(trace) < 3:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        stats_list = [encoder.features(tuple(float(v) for v in state)) for state in path]
        margins = [_base_margin(stats, spec) for stats in stats_list]
        for idx in range(min(len(trace) - 2, len(margins) - 3)):
            future = margins[idx + 1 : min(len(margins), idx + 1 + int(max(horizon_steps, 2)))]
            if not future:
                continue
            best_offset = int(np.argmax(np.asarray(future, dtype=np.float32))) + 1
            best_gain = float(future[best_offset - 1] - margins[idx])
            if best_gain < float(min_gain):
                continue
            entry_stats = stats_list[idx]
            recovered_stats = stats_list[min(idx + best_offset, len(stats_list) - 1)]
            entry_oracle = query_viability_table(viability_table, margin_key(entry_stats))
            entry_oracle_gain = float(entry_oracle.get('avg_future_gain', 0.0)) if isinstance(entry_oracle, dict) else 0.0
            entry_state = classify_viability_state(entry_stats, margins[idx], entry_oracle_gain, state_cfg, spec)
            recovered_state = classify_viability_state(recovered_stats, margins[min(idx + best_offset, len(margins) - 1)], 0.0, state_cfg, spec)
            seq = tuple(int(v) for v in trace[idx : idx + 3])
            feat = feature_vector(entry_stats, margins[idx], entry_oracle_gain, spec)
            rows_by_state[entry_state].setdefault(seq, []).append(feat)
            gains_by_state[entry_state].setdefault(seq, []).append(best_gain)
            meta = meta_by_state[entry_state].setdefault(
                seq,
                {'gain_sum': 0.0, 'hits': 0, 'family': _seq_family(asset['case'], seq), 'recovered_state': recovered_state},
            )
            meta['gain_sum'] = float(meta['gain_sum']) + float(best_gain)
            meta['hits'] = int(meta['hits']) + 1
            meta['recovered_state'] = str(recovered_state)
    graph: dict[str, list[CompilerEdge]] = {}
    support: dict[str, dict[str, SupportBand]] = {}
    for state in VIABILITY_STATES:
        graph[state] = []
        support[state] = {}
        for seq, rows in rows_by_state.get(state, {}).items():
            gains = gains_by_state[state][seq]
            meta = meta_by_state[state][seq]
            band = fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)
            if band is not None:
                support[state][str(seq)] = band
            graph[state].append(
                CompilerEdge(
                    sequence=tuple(seq),
                    family=str(meta['family']),
                    recovered_state=str(meta['recovered_state']),
                    avg_gain=float(meta['gain_sum']) / max(int(meta['hits']), 1),
                    hits=int(meta['hits']),
                )
            )
        graph[state].sort(key=lambda edge: (float(edge.avg_gain), int(edge.hits)), reverse=True)
    return graph, support


def choose_state_motif_edges(
    state: str,
    edges: dict[str, list[CompilerEdge]],
    support: dict[str, dict[str, SupportBand]],
    feat: np.ndarray,
    *,
    gain_hint: float,
    slack: float,
    max_edges: int,
) -> list[CompilerEdge]:
    scored: list[tuple[float, CompilerEdge]] = []
    for edge in edges.get(str(state), []):
        band = support.get(str(state), {}).get(str(tuple(edge.sequence)), None)
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched:
            score = float(sim) + 0.05 * float(edge.avg_gain)
            scored.append((score, edge))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [edge for _, edge in scored[: int(max(max_edges, 0))]]


def serializable_support_state(bands: dict[str, dict[str, SupportBand]]) -> dict[str, Any]:
    out = {}
    for state, mapping in bands.items():
        out[str(state)] = {}
        for key, band in mapping.items():
            out[str(state)][str(key)] = {
                'similarity_floor': float(band.similarity_floor),
                'min_progress': float(band.min_progress),
                'counts': int(band.counts),
            }
    return out


__all__ = [
    'CompilerEdge',
    'FEATURE_NAMES',
    'MacroPrimitive',
    'RecoverabilityEncoder',
    'RecoverabilitySpec',
    'VIABILITY_STATES',
    'ViabilityStateConfig',
    'build_nonholonomic_field',
    'build_standard_field',
    'choose_state_macros',
    'choose_state_motif_edges',
    'classify_viability_state',
    'compile_macro_library',
    'compile_motif_compiler_graph',
    'compile_state_macro_support',
    'compile_viability_table',
    'feature_vector',
    'macro_family',
    'macro_successor_candidates',
    'margin_key',
    'query_viability_table',
    'recoverability_margin',
    'reverse_need_score',
    'run_hybrid_with_policy',
    'save_meta',
    'serializable_support_state',
    'standard_identity_error',
    'state_family_bonus',
]
