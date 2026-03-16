from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
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
    extract_escape_motif_memory,
    macro_successor_candidates,
    margin_key,
    query_viability_table,
    recoverability_margin,
    reverse_need_score,
    run_hybrid_with_policy,
    save_meta,
    standard_identity_error,
    macro_family,
)
from rs_cx8.common import primitive_index_from_case


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


@dataclass(frozen=True)
class MotifEdge:
    sequence: tuple[int, ...]
    family: str
    recovered_key: tuple[int, ...]
    avg_gain: float
    hits: int


def feature_vector(stats, margin: float, oracle_gain: float, spec: RecoverabilitySpec) -> np.ndarray:
    horizon = float(spec.ray_step_m * spec.ray_horizon_steps)
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


def _margin_from_stats(stats, spec: RecoverabilitySpec) -> float:
    return recoverability_margin(
        stats,
        clearance_w=0.22,
        corridor_w=0.24,
        trap_w=0.32,
        reverse_w=0.22,
        lateral_w=0.10,
        forward_w=0.06,
        heading_w=0.08,
        spec=spec,
    )


def compile_macro_support(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    macros: list[MacroPrimitive],
    viability_table: dict[tuple[int, ...], dict[str, Any]],
    *,
    horizon_steps: int,
    min_gain: float,
) -> dict[str, SupportBand]:
    by_name: dict[str, list[np.ndarray]] = {}
    by_gain: dict[str, list[float]] = {}
    macro_map = {tuple(m.primitive_indices): m for m in macros}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 4 or len(trace) < 2:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        stats_list = [encoder.features(tuple(float(v) for v in state)) for state in path]
        margins = [_margin_from_stats(stats, spec) for stats in stats_list]
        for idx in range(min(len(trace) - 1, len(margins) - 2)):
            seq = tuple(int(v) for v in trace[idx : idx + 2])
            macro = macro_map.get(seq, None)
            if macro is None:
                continue
            future = margins[idx + 1 : min(len(margins), idx + 1 + int(max(horizon_steps, 2)))]
            if not future:
                continue
            best_gain = float(max(future) - margins[idx])
            if best_gain < float(min_gain):
                continue
            stats = stats_list[idx]
            oracle = query_viability_table(viability_table, margin_key(stats))
            oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
            feat = feature_vector(stats, margins[idx], oracle_gain, spec)
            by_name.setdefault(str(macro.name), []).append(feat)
            by_gain.setdefault(str(macro.name), []).append(float(best_gain))
    out = {}
    for macro in macros:
        rows = by_name.get(str(macro.name), [])
        gains = by_gain.get(str(macro.name), [])
        band = fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)
        if band is not None:
            out[str(macro.name)] = band
    return out


def choose_macro_subset(
    macros: list[MacroPrimitive],
    support: dict[str, SupportBand],
    feat: np.ndarray,
    *,
    gain_hint: float,
    slack: float,
    max_macros: int,
) -> list[MacroPrimitive]:
    scored: list[tuple[float, MacroPrimitive]] = []
    for macro in macros:
        band = support.get(str(macro.name), None)
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched:
            score = float(sim) + 0.05 * float(macro.avg_gain)
            scored.append((score, macro))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [macro for _, macro in scored[: int(max(max_macros, 0))]]


def compile_motif_automaton(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    viability_table: dict[tuple[int, ...], dict[str, Any]],
    *,
    horizon_steps: int,
    min_gain: float,
) -> tuple[dict[tuple[int, ...], list[MotifEdge]], dict[tuple[int, ...], dict[str, SupportBand]]]:
    edge_rows: dict[tuple[int, ...], dict[tuple[int, ...], list[np.ndarray]]] = {}
    edge_gains: dict[tuple[int, ...], dict[tuple[int, ...], list[float]]] = {}
    edge_meta: dict[tuple[int, ...], dict[tuple[int, ...], dict[str, Any]]] = {}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 5 or len(trace) < 3:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        stats_list = [encoder.features(tuple(float(v) for v in state)) for state in path]
        margins = [_margin_from_stats(stats, spec) for stats in stats_list]
        for idx in range(min(len(trace) - 2, len(margins) - 3)):
            future_slice = margins[idx + 1 : min(len(margins), idx + 1 + int(max(horizon_steps, 2)))]
            if not future_slice:
                continue
            best_offset = int(np.argmax(np.asarray(future_slice, dtype=np.float32))) + 1
            best_gain = float(future_slice[best_offset - 1] - margins[idx])
            if best_gain < float(min_gain):
                continue
            entry_stats = stats_list[idx]
            recovered_stats = stats_list[min(idx + best_offset, len(stats_list) - 1)]
            entry_key = margin_key(entry_stats)
            recovered_key = margin_key(recovered_stats)
            seq = tuple(int(v) for v in trace[idx : idx + 3])
            oracle = query_viability_table(viability_table, entry_key)
            oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
            feat = feature_vector(entry_stats, margins[idx], oracle_gain, spec)
            edge_rows.setdefault(entry_key, {}).setdefault(seq, []).append(feat)
            edge_gains.setdefault(entry_key, {}).setdefault(seq, []).append(float(best_gain))
            meta = edge_meta.setdefault(entry_key, {}).setdefault(seq, {'gain_sum': 0.0, 'hits': 0, 'recovered_key': recovered_key, 'family': _seq_family(asset['case'], seq)})
            meta['gain_sum'] = float(meta['gain_sum']) + float(best_gain)
            meta['hits'] = int(meta['hits']) + 1
            meta['recovered_key'] = recovered_key
    automaton: dict[tuple[int, ...], list[MotifEdge]] = {}
    support_map: dict[tuple[int, ...], dict[str, SupportBand]] = {}
    for entry_key, seq_dict in edge_rows.items():
        edges = []
        support_row = {}
        for seq, rows in seq_dict.items():
            meta = edge_meta[entry_key][seq]
            gains = edge_gains[entry_key][seq]
            band = fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)
            if band is not None:
                support_row[str(seq)] = band
            edges.append(
                MotifEdge(
                    sequence=tuple(seq),
                    family=str(meta['family']),
                    recovered_key=tuple(meta['recovered_key']),
                    avg_gain=float(meta['gain_sum']) / max(int(meta['hits']), 1),
                    hits=int(meta['hits']),
                )
            )
        edges.sort(key=lambda edge: (float(edge.avg_gain), int(edge.hits)), reverse=True)
        automaton[tuple(entry_key)] = edges
        support_map[tuple(entry_key)] = support_row
    return automaton, support_map


def _seq_family(case: dict[str, Any], seq: tuple[int, ...]) -> str:
    if not seq:
        return 'motif:none'
    pindex = primitive_index_from_case(case)
    fams = [pindex.label(int(v)) for v in seq]
    if any(str(fam).startswith('B-') for fam in fams):
        return 'motif:reverse'
    return 'motif:forward'


def choose_motif_edges(
    edges: list[MotifEdge],
    support: dict[str, SupportBand],
    feat: np.ndarray,
    *,
    gain_hint: float,
    slack: float,
    max_edges: int,
) -> list[MotifEdge]:
    scored: list[tuple[float, MotifEdge]] = []
    for edge in edges:
        band = support.get(str(tuple(edge.sequence)), None)
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched:
            score = float(sim) + 0.05 * float(edge.avg_gain)
            scored.append((score, edge))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [edge for _, edge in scored[: int(max(max_edges, 0))]]


def serializable_support(bands: dict[str, SupportBand]) -> dict[str, Any]:
    out = {}
    for key, band in bands.items():
        out[str(key)] = {
            'similarity_floor': float(band.similarity_floor),
            'min_progress': float(band.min_progress),
            'counts': int(band.counts),
        }
    return out


__all__ = [
    'FEATURE_NAMES',
    'MotifEdge',
    'RecoverabilityEncoder',
    'RecoverabilitySpec',
    'SupportBand',
    'build_nonholonomic_field',
    'build_standard_field',
    'choose_macro_subset',
    'choose_motif_edges',
    'compile_macro_library',
    'compile_macro_support',
    'compile_motif_automaton',
    'compile_viability_table',
    'extract_escape_motif_memory',
    'feature_vector',
    'macro_family',
    'macro_successor_candidates',
    'margin_key',
    'query_viability_table',
    'recoverability_margin',
    'reverse_need_score',
    'run_hybrid_with_policy',
    'save_meta',
    'serializable_support',
    'standard_identity_error',
]
