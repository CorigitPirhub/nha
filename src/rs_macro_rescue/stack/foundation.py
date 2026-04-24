from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from rs_macro_rescue.stack.support import SupportBand, fit_support_band, support_match
from rs_macro_rescue.stack.recoverability import (
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
from rs_macro_rescue.stack.nonholonomic import primitive_index_from_case, query_yaw_field


FOUNDATION_FEATURE_NAMES = (
    'cost_to_go',
    'viability',
    'recoverability',
    'reverse_required',
    'trap_escape_affinity',
    'trap',
    'corridor',
    'clearance',
    'reverse_clearance',
    'forward_clearance',
    'heading_cos',
)


@dataclass(frozen=True)
class FoundationState:
    cost_to_go: float
    viability: float
    recoverability: float
    reverse_required: float
    trap_escape_affinity: float
    trap: float
    corridor: float
    clearance: float
    reverse_clearance: float
    forward_clearance: float
    heading_cos: float


@dataclass(frozen=True)
class GrammarStateConfig:
    safe_cost: float
    boundary_viability: float
    reverse_required_thr: float
    trap_escape_thr: float
    trap_high_thr: float


GRAMMAR_STATES = (
    'direct_progress',
    'careful_boundary',
    'reverse_required',
    'escape_required',
)


def foundation_state(case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, encoder: RecoverabilityEncoder, state: tuple[float, float, float], spec: RecoverabilitySpec) -> FoundationState:
    stats = encoder.features(state)
    cost_to_go = float(query_yaw_field(np.asarray(field, dtype=np.float32), float(state[0]), float(state[1]), float(state[2]), float(case['resolution'])))
    viability = recoverability_margin(
        stats,
        clearance_w=0.22,
        corridor_w=0.26,
        trap_w=0.36,
        reverse_w=0.24,
        lateral_w=0.10,
        forward_w=0.04,
        heading_w=0.08,
        spec=spec,
    )
    reverse_required = float(reverse_need_score(stats, spec))
    trap_escape_affinity = float(stats.corridor - stats.trap + 0.25 * max(stats.left_clearance, stats.right_clearance) / max(float(spec.ray_horizon_steps * spec.ray_step_m), 1e-6))
    return FoundationState(
        cost_to_go=float(cost_to_go),
        viability=float(viability),
        recoverability=float(viability),
        reverse_required=float(reverse_required),
        trap_escape_affinity=float(trap_escape_affinity),
        trap=float(stats.trap),
        corridor=float(stats.corridor),
        clearance=float(stats.clearance),
        reverse_clearance=float(stats.reverse_clearance),
        forward_clearance=float(stats.forward_clearance),
        heading_cos=float(stats.heading_cos),
    )


def foundation_feature_vector(f: FoundationState) -> np.ndarray:
    return np.asarray([
        float(f.cost_to_go),
        float(f.viability),
        float(f.recoverability),
        float(f.reverse_required),
        float(f.trap_escape_affinity),
        float(f.trap),
        float(f.corridor),
        float(f.clearance),
        float(f.reverse_clearance),
        float(f.forward_clearance),
        float(f.heading_cos),
    ], dtype=np.float32)


def classify_grammar_state(f: FoundationState, cfg: GrammarStateConfig) -> str:
    if float(f.reverse_required) >= float(cfg.reverse_required_thr):
        return 'reverse_required'
    if float(f.trap) >= float(cfg.trap_high_thr) and float(f.trap_escape_affinity) <= float(cfg.trap_escape_thr):
        return 'escape_required'
    if float(f.viability) <= float(cfg.boundary_viability) or float(f.cost_to_go) >= float(cfg.safe_cost):
        return 'careful_boundary'
    return 'direct_progress'


def grammar_family_bonus(state: str, family: str, direction: int) -> float:
    fam = str(family)
    if state == 'reverse_required':
        if 'reverse' in fam or int(direction) < 0:
            return 0.12
        return -0.04
    if state == 'escape_required':
        if 'reverse' in fam or 'escape' in fam:
            return 0.10
        return -0.04
    if state == 'careful_boundary' and fam.startswith('macro:'):
        return 0.05
    return 0.0


def compile_head_support(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    state_cfg: GrammarStateConfig,
    macros: list[MacroPrimitive],
    viability_table: dict[tuple[int, ...], dict[str, Any]],
    *,
    horizon_steps: int,
    min_gain: float,
) -> tuple[dict[str, dict[str, SupportBand]], dict[str, dict[str, float]]]:
    macro_map = {tuple(m.primitive_indices): m for m in macros}
    rows_by_state: dict[str, dict[str, list[np.ndarray]]] = {state: {} for state in GRAMMAR_STATES}
    gains_by_state: dict[str, dict[str, list[float]]] = {state: {} for state in GRAMMAR_STATES}
    counts_by_state: dict[str, dict[str, int]] = {state: {} for state in GRAMMAR_STATES}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 4 or len(trace) < 2:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        heads = [foundation_state(asset['case'], asset['bundle'], asset['field'], encoder, tuple(float(v) for v in state), spec) for state in path]
        costs = [float(h.cost_to_go) for h in heads]
        for idx in range(min(len(trace) - 1, len(costs) - 2)):
            seq = tuple(int(v) for v in trace[idx : idx + 2])
            macro = macro_map.get(seq, None)
            if macro is None:
                continue
            future = costs[idx + 1 : min(len(costs), idx + 1 + int(max(horizon_steps, 2)))]
            if not future:
                continue
            gain = float(costs[idx] - min(future))
            if gain < float(min_gain):
                continue
            state = classify_grammar_state(heads[idx], state_cfg)
            feat = foundation_feature_vector(heads[idx])
            rows_by_state[state].setdefault(str(macro.name), []).append(feat)
            gains_by_state[state].setdefault(str(macro.name), []).append(gain)
            counts_by_state[state][str(macro.name)] = int(counts_by_state[state].get(str(macro.name), 0)) + 1
    support: dict[str, dict[str, SupportBand]] = {}
    counts: dict[str, dict[str, float]] = {}
    for state in GRAMMAR_STATES:
        support[state] = {}
        counts[state] = {}
        for macro in macros:
            rows = rows_by_state[state].get(str(macro.name), [])
            gains = gains_by_state[state].get(str(macro.name), [])
            band = fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)
            if band is not None:
                support[state][str(macro.name)] = band
                counts[state][str(macro.name)] = float(counts_by_state[state].get(str(macro.name), 0))
    return support, counts


def choose_head_macros(state: str, macros: list[MacroPrimitive], support: dict[str, dict[str, SupportBand]], counts: dict[str, dict[str, float]], feat: np.ndarray, *, gain_hint: float, slack: float, max_macros: int) -> list[MacroPrimitive]:
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


@dataclass(frozen=True)
class CompilerNode:
    sequence: tuple[int, ...]
    family: str
    recovered_state: str
    avg_gain: float
    hits: int


def compile_foundation_graph(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    state_cfg: GrammarStateConfig,
    *,
    horizon_steps: int,
    min_gain: float,
) -> tuple[dict[str, list[CompilerNode]], dict[str, dict[str, SupportBand]]]:
    rows_by_state: dict[str, dict[tuple[int, ...], list[np.ndarray]]] = {state: {} for state in GRAMMAR_STATES}
    gains_by_state: dict[str, dict[tuple[int, ...], list[float]]] = {state: {} for state in GRAMMAR_STATES}
    meta_by_state: dict[str, dict[tuple[int, ...], dict[str, Any]]] = {state: {} for state in GRAMMAR_STATES}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 5 or len(trace) < 3:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        heads = [foundation_state(asset['case'], asset['bundle'], asset['field'], encoder, tuple(float(v) for v in state), spec) for state in path]
        costs = [float(h.cost_to_go) for h in heads]
        for idx in range(min(len(trace) - 2, len(costs) - 3)):
            future = costs[idx + 1 : min(len(costs), idx + 1 + int(max(horizon_steps, 2)))]
            if not future:
                continue
            best_offset = int(np.argmin(np.asarray(future, dtype=np.float32))) + 1
            gain = float(costs[idx] - future[best_offset - 1])
            if gain < float(min_gain):
                continue
            seq = tuple(int(v) for v in trace[idx : idx + 3])
            state = classify_grammar_state(heads[idx], state_cfg)
            recovered_state = classify_grammar_state(heads[min(idx + best_offset, len(heads) - 1)], state_cfg)
            feat = foundation_feature_vector(heads[idx])
            rows_by_state[state].setdefault(seq, []).append(feat)
            gains_by_state[state].setdefault(seq, []).append(gain)
            meta = meta_by_state[state].setdefault(seq, {'gain_sum': 0.0, 'hits': 0, 'family': _seq_family(asset['case'], seq), 'recovered_state': recovered_state})
            meta['gain_sum'] = float(meta['gain_sum']) + float(gain)
            meta['hits'] = int(meta['hits']) + 1
            meta['recovered_state'] = str(recovered_state)
    graph: dict[str, list[CompilerNode]] = {}
    support: dict[str, dict[str, SupportBand]] = {}
    for state in GRAMMAR_STATES:
        graph[state] = []
        support[state] = {}
        for seq, rows in rows_by_state[state].items():
            gains = gains_by_state[state][seq]
            meta = meta_by_state[state][seq]
            band = fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)
            if band is not None:
                support[state][str(seq)] = band
            graph[state].append(
                CompilerNode(
                    sequence=tuple(seq),
                    family=str(meta['family']),
                    recovered_state=str(meta['recovered_state']),
                    avg_gain=float(meta['gain_sum']) / max(int(meta['hits']), 1),
                    hits=int(meta['hits']),
                )
            )
        graph[state].sort(key=lambda node: (float(node.avg_gain), int(node.hits)), reverse=True)
    return graph, support


def choose_graph_nodes(state: str, graph: dict[str, list[CompilerNode]], support: dict[str, dict[str, SupportBand]], feat: np.ndarray, *, gain_hint: float, slack: float, max_edges: int) -> list[CompilerNode]:
    scored: list[tuple[float, CompilerNode]] = []
    for node in graph.get(str(state), []):
        band = support.get(str(state), {}).get(str(tuple(node.sequence)), None)
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched:
            score = float(sim) + 0.05 * float(node.avg_gain)
            scored.append((score, node))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [node for _, node in scored[: int(max(max_edges, 0))]]


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
    'CompilerNode',
    'FOUNDATION_FEATURE_NAMES',
    'GRAMMAR_STATES',
    'GrammarStateConfig',
    'MacroPrimitive',
    'RecoverabilityEncoder',
    'RecoverabilitySpec',
    'ViabilityStateConfig',
    'build_nonholonomic_field',
    'build_standard_field',
    'choose_graph_nodes',
    'choose_head_macros',
    'classify_grammar_state',
    'compile_foundation_graph',
    'compile_head_support',
    'compile_macro_library',
    'compile_viability_table',
    'feature_vector',
    'foundation_feature_vector',
    'foundation_state',
    'grammar_family_bonus',
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
]
