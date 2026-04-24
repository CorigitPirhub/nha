from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from rs_macro_rescue.stack.support import SupportBand, fit_support_band, support_match
from rs_macro_rescue.stack.primitive import primitive_group
from rs_macro_rescue.stack.nonholonomic import primitive_index_from_case
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
    run_hybrid_with_policy,
    save_meta,
    standard_identity_error,
)
from rs_macro_rescue.stack.foundation import (
    CompilerNode,
    FoundationState,
    foundation_feature_vector,
    foundation_state,
    serializable_support_state,
)


CVF_MODES = (
    'forward_safe',
    'reverse_setup',
    'escape_border',
    'uncertain',
)

FAMILY_BUCKETS = (
    'straight',
    'forward_turn',
    'reverse',
    'reverse_setup',
)


@dataclass(frozen=True)
class CVFModeConfig:
    forward_viability_thr: float
    reverse_required_thr: float
    trap_high_thr: float
    escape_affinity_low_thr: float
    hopeless_viability_thr: float


@dataclass(frozen=True)
class FamilySupportStat:
    band: SupportBand
    avg_gain: float
    hits: int


@dataclass(frozen=True)
class StableGraphNode:
    sequence: tuple[int, ...]
    family: str
    recovered_mode: str
    avg_gain: float
    lower_bound: float
    hits: int


def family_bucket_name(family: str) -> str:
    fam = str(family)
    if fam.startswith('scg|'):
        parts = fam.split('|')
        if len(parts) >= 2:
            fam = parts[1]
    if 'reverse-setup' in fam:
        return 'reverse_setup'
    if 'reverse' in fam or fam.startswith('B-') or primitive_group(fam) == 'reverse':
        return 'reverse'
    if fam.endswith('-S') or 'straight' in fam:
        return 'straight'
    return 'forward_turn'


def consistency_error(f: FoundationState) -> float:
    target_reverse = float(
        np.clip(
            0.58
            - 0.72 * float(f.viability)
            + 0.28 * float(f.trap)
            - 0.16 * float(f.trap_escape_affinity),
            0.0,
            1.0,
        )
    )
    reverse_mismatch = abs(float(f.reverse_required) - target_reverse)
    trap_conflict = max(0.0, float(f.trap_escape_affinity) + 0.40 * float(f.trap) - 0.28 * float(f.corridor))
    hopeless_conflict = max(0.0, 0.08 - float(f.viability)) * max(0.0, 0.45 - float(f.reverse_required))
    return float(0.60 * reverse_mismatch + 0.25 * trap_conflict + 0.15 * hopeless_conflict)


def consistency_score(f: FoundationState) -> float:
    err = float(consistency_error(f))
    return float(np.exp(-2.25 * err))


def consistent_mode(f: FoundationState, cfg: CVFModeConfig) -> str:
    if float(f.viability) <= float(cfg.hopeless_viability_thr):
        return 'uncertain'
    if float(f.reverse_required) >= float(cfg.reverse_required_thr) and float(f.viability) > float(cfg.hopeless_viability_thr):
        return 'reverse_setup'
    if float(f.trap) >= float(cfg.trap_high_thr) and float(f.trap_escape_affinity) <= float(cfg.escape_affinity_low_thr):
        return 'escape_border'
    if float(f.viability) >= float(cfg.forward_viability_thr) and float(f.trap) < float(cfg.trap_high_thr):
        return 'forward_safe'
    return 'uncertain'


def _future_cost_gain(costs: list[float], idx: int, horizon_steps: int) -> float:
    future = costs[idx + 1 : min(len(costs), idx + 1 + int(max(horizon_steps, 1)))]
    if not future:
        return 0.0
    return float(costs[idx] - min(future))


def compile_mode_support(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    mode_cfg: CVFModeConfig,
    *,
    horizon_steps: int,
    min_gain: float,
) -> dict[str, SupportBand]:
    rows_by_mode = {mode: [] for mode in CVF_MODES if mode != 'uncertain'}
    gains_by_mode = {mode: [] for mode in CVF_MODES if mode != 'uncertain'}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 3:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        heads = [
            foundation_state(asset['case'], asset['bundle'], asset['field'], encoder, tuple(float(v) for v in state), spec)
            for state in path
        ]
        costs = [float(h.cost_to_go) for h in heads]
        for idx, head in enumerate(heads[:-1]):
            gain = _future_cost_gain(costs, idx, int(horizon_steps))
            if gain < float(min_gain):
                continue
            mode = consistent_mode(head, mode_cfg)
            if mode == 'uncertain':
                continue
            rows_by_mode[mode].append(foundation_feature_vector(head))
            gains_by_mode[mode].append(gain)
    out: dict[str, SupportBand] = {}
    for mode, rows in rows_by_mode.items():
        band = fit_support_band(rows, gains_by_mode[mode], low_q=0.05, high_q=0.95, sim_q=0.15)
        if band is not None:
            out[str(mode)] = band
    return out


def match_mode_support(
    support: dict[str, SupportBand],
    feat: np.ndarray,
    *,
    gain_hint: float,
    slack: float,
) -> tuple[str, bool, float]:
    best_mode = 'uncertain'
    best_match = False
    best_sim = -1.0
    for mode in ('forward_safe', 'reverse_setup', 'escape_border'):
        band = support.get(mode, None)
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched and float(sim) > best_sim:
            best_mode = str(mode)
            best_match = True
            best_sim = float(sim)
    return best_mode, bool(best_match), float(best_sim if best_sim > -1.0 else 0.0)


def compile_family_support(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    mode_cfg: CVFModeConfig,
    *,
    horizon_steps: int,
    min_gain: float,
) -> dict[str, dict[str, FamilySupportStat]]:
    rows_by_mode: dict[str, dict[str, list[np.ndarray]]] = {
        mode: {bucket: [] for bucket in FAMILY_BUCKETS}
        for mode in CVF_MODES
        if mode != 'uncertain'
    }
    gains_by_mode: dict[str, dict[str, list[float]]] = {
        mode: {bucket: [] for bucket in FAMILY_BUCKETS}
        for mode in CVF_MODES
        if mode != 'uncertain'
    }
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 4 or len(trace) < 2:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        heads = [
            foundation_state(asset['case'], asset['bundle'], asset['field'], encoder, tuple(float(v) for v in state), spec)
            for state in path
        ]
        costs = [float(h.cost_to_go) for h in heads]
        for idx in range(min(len(trace) - 1, len(heads) - 2)):
            gain = _future_cost_gain(costs, idx, int(horizon_steps))
            if gain < float(min_gain):
                continue
            mode = consistent_mode(heads[idx], mode_cfg)
            if mode == 'uncertain':
                continue
            primitive_indices = tuple(int(v) for v in trace[idx : idx + 2])
            if len(primitive_indices) < 2:
                continue
            pindex = primitive_index_from_case(asset['case'])
            p0 = int(primitive_indices[0])
            p1 = int(primitive_indices[1])
            fam0 = family_bucket_name(pindex.label(p0))
            fam1 = family_bucket_name(pindex.label(p1))
            bucket = fam0
            if fam0.startswith('reverse') and fam1 in {'straight', 'forward_turn'}:
                bucket = 'reverse_setup'
            rows_by_mode[mode][bucket].append(foundation_feature_vector(heads[idx]))
            gains_by_mode[mode][bucket].append(gain)
    out: dict[str, dict[str, FamilySupportStat]] = {}
    for mode in ('forward_safe', 'reverse_setup', 'escape_border'):
        out[mode] = {}
        for bucket in FAMILY_BUCKETS:
            rows = rows_by_mode[mode][bucket]
            gains = gains_by_mode[mode][bucket]
            band = fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)
            if band is not None:
                out[mode][bucket] = FamilySupportStat(
                    band=band,
                    avg_gain=float(np.mean(gains)) if gains else 0.0,
                    hits=int(len(rows)),
                )
    return out


def compile_stable_graph(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    mode_cfg: CVFModeConfig,
    *,
    horizon_steps: int,
    min_gain: float,
    min_hits: int,
    max_nodes_per_mode: int,
) -> tuple[dict[str, list[StableGraphNode]], dict[str, dict[str, SupportBand]]]:
    rows_by_mode: dict[str, dict[tuple[int, ...], list[np.ndarray]]] = {mode: {} for mode in CVF_MODES if mode != 'uncertain'}
    gains_by_mode: dict[str, dict[tuple[int, ...], list[float]]] = {mode: {} for mode in CVF_MODES if mode != 'uncertain'}
    recovered_by_mode: dict[str, dict[tuple[int, ...], str]] = {mode: {} for mode in CVF_MODES if mode != 'uncertain'}
    family_by_mode: dict[str, dict[tuple[int, ...], str]] = {mode: {} for mode in CVF_MODES if mode != 'uncertain'}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 5 or len(trace) < 3:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        heads = [
            foundation_state(asset['case'], asset['bundle'], asset['field'], encoder, tuple(float(v) for v in state), spec)
            for state in path
        ]
        costs = [float(h.cost_to_go) for h in heads]
        for idx in range(min(len(trace) - 2, len(heads) - 3)):
            future = costs[idx + 1 : min(len(costs), idx + 1 + int(max(horizon_steps, 2)))]
            if not future:
                continue
            best_offset = int(np.argmin(np.asarray(future, dtype=np.float32))) + 1
            gain = float(costs[idx] - future[best_offset - 1])
            if gain < float(min_gain):
                continue
            mode = consistent_mode(heads[idx], mode_cfg)
            if mode == 'uncertain':
                continue
            seq = tuple(int(v) for v in trace[idx : idx + 3])
            if len(seq) < 3:
                continue
            recovered_mode = consistent_mode(heads[min(idx + best_offset, len(heads) - 1)], mode_cfg)
            pindex = primitive_index_from_case(asset['case'])
            labels = [str(pindex.label(int(v))) for v in seq]
            if any(label.startswith('B-') for label in labels) and any(not label.startswith('B-') for label in labels):
                bucket = 'reverse_setup'
            elif all(label.startswith('B-') for label in labels):
                bucket = 'reverse'
            elif all(label.endswith('-S') for label in labels):
                bucket = 'straight'
            else:
                bucket = 'forward_turn'
            rows_by_mode[mode].setdefault(seq, []).append(foundation_feature_vector(heads[idx]))
            gains_by_mode[mode].setdefault(seq, []).append(gain)
            recovered_by_mode[mode][seq] = str(recovered_mode)
            family_by_mode[mode][seq] = str(bucket)
    graph: dict[str, list[StableGraphNode]] = {mode: [] for mode in CVF_MODES if mode != 'uncertain'}
    support: dict[str, dict[str, SupportBand]] = {mode: {} for mode in CVF_MODES if mode != 'uncertain'}
    for mode in ('forward_safe', 'reverse_setup', 'escape_border'):
        for seq, rows in rows_by_mode[mode].items():
            gains = gains_by_mode[mode][seq]
            if len(rows) < int(max(min_hits, 1)):
                continue
            band = fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)
            if band is None:
                continue
            support[mode][str(tuple(seq))] = band
            graph[mode].append(
                StableGraphNode(
                    sequence=tuple(seq),
                    family=str(family_by_mode[mode][seq]),
                    recovered_mode=str(recovered_by_mode[mode][seq]),
                    avg_gain=float(np.mean(gains)),
                    lower_bound=float(np.quantile(np.asarray(gains, dtype=np.float32), 0.2)),
                    hits=int(len(rows)),
                )
            )
        graph[mode].sort(key=lambda node: (float(node.lower_bound), float(node.avg_gain), int(node.hits)), reverse=True)
        graph[mode] = graph[mode][: int(max(max_nodes_per_mode, 1))]
    return graph, support


def choose_stable_nodes(
    mode: str,
    graph: dict[str, list[StableGraphNode]],
    support: dict[str, dict[str, SupportBand]],
    feat: np.ndarray,
    *,
    gain_hint: float,
    slack: float,
    max_nodes: int,
    use_support_filter: bool,
) -> list[StableGraphNode]:
    scored: list[tuple[float, StableGraphNode]] = []
    for node in graph.get(str(mode), []):
        band = support.get(str(mode), {}).get(str(tuple(node.sequence)), None)
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if bool(use_support_filter) and not bool(matched):
            continue
        score = float(sim) + 0.10 * float(node.lower_bound) + 0.02 * float(node.hits)
        scored.append((score, node))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [node for _, node in scored[: int(max(max_nodes, 0))]]


def stable_graph_family_tag(node: StableGraphNode) -> str:
    return f"scg|{node.family}|{node.recovered_mode}|{float(node.lower_bound):.6f}|{int(node.hits)}"


def parse_stable_graph_family(tag: str) -> tuple[str, str, float, int]:
    raw = str(tag)
    if not raw.startswith('scg|'):
        return family_bucket_name(raw), 'uncertain', 0.0, 0
    parts = raw.split('|')
    if len(parts) < 5:
        return family_bucket_name(raw), 'uncertain', 0.0, 0
    return family_bucket_name(parts[1]), str(parts[2]), float(parts[3]), int(parts[4])


def serializable_family_support(stats: dict[str, dict[str, FamilySupportStat]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mode, mapping in stats.items():
        out[str(mode)] = {}
        for bucket, stat in mapping.items():
            out[str(mode)][str(bucket)] = {
                'avg_gain': float(stat.avg_gain),
                'hits': int(stat.hits),
                'band': {
                    'similarity_floor': float(stat.band.similarity_floor),
                    'min_progress': float(stat.band.min_progress),
                    'counts': int(stat.band.counts),
                },
            }
    return out


def serializable_graph(graph: dict[str, list[StableGraphNode]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mode, nodes in graph.items():
        out[str(mode)] = [
            {
                'sequence': list(node.sequence),
                'family': str(node.family),
                'recovered_mode': str(node.recovered_mode),
                'avg_gain': float(node.avg_gain),
                'lower_bound': float(node.lower_bound),
                'hits': int(node.hits),
            }
            for node in nodes
        ]
    return out


__all__ = [
    'CVFModeConfig',
    'CVF_MODES',
    'CompilerNode',
    'FAMILY_BUCKETS',
    'FamilySupportStat',
    'FoundationState',
    'MacroPrimitive',
    'RecoverabilityEncoder',
    'RecoverabilitySpec',
    'StableGraphNode',
    'build_nonholonomic_field',
    'build_standard_field',
    'compile_family_support',
    'compile_macro_library',
    'compile_mode_support',
    'compile_stable_graph',
    'compile_viability_table',
    'consistency_error',
    'consistency_score',
    'consistent_mode',
    'family_bucket_name',
    'foundation_feature_vector',
    'foundation_state',
    'macro_family',
    'macro_successor_candidates',
    'margin_key',
    'match_mode_support',
    'parse_stable_graph_family',
    'query_viability_table',
    'run_hybrid_with_policy',
    'save_meta',
    'serializable_family_support',
    'serializable_graph',
    'serializable_support_state',
    'stable_graph_family_tag',
    'standard_identity_error',
]
