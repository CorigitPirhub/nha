from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import ndimage

from config import DEFAULT_CONFIG
from rs_cx.common import CXGlobalConfig, normalize01
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_cx8.common import (
    build_compact_bundle_feature_vector,
    build_compact_state_cache,
    bottleneck_regime_score,
    bundle_target_from_trace,
    load_nonholonomic_assets,
    primitive_index_from_case,
    query_yaw_field,
    run_hybrid_with_policy,
)
from utils.common import wrap_to_pi

MODE_LABELS = ('neutral', 'thread_left', 'thread_right', 'reverse_left', 'reverse_right')


@dataclass(frozen=True)
class CoarseGridSpec:
    stride_cells: int
    yaw_clusters: int = 1


def mode_from_bundle_target(target: int | None) -> int:
    if target is None:
        return 0
    return int(target) + 1


def mode_label(mode: int) -> str:
    return MODE_LABELS[int(np.clip(mode, 0, len(MODE_LABELS) - 1))]


def bundle_like_match(mode: int, level: float, direction: int) -> float:
    mode = int(mode)
    if mode == 0:
        return 0.0
    if mode == 1:  # thread_left
        if direction > 0 and level < -1e-6:
            return 1.0
        if direction > 0 and abs(level) <= 1e-6:
            return 0.45
        return -0.2
    if mode == 2:  # thread_right
        if direction > 0 and level > 1e-6:
            return 1.0
        if direction > 0 and abs(level) <= 1e-6:
            return 0.45
        return -0.2
    if mode == 3:  # reverse_left
        if direction < 0 and level < -1e-6:
            return 1.0
        if direction < 0 and abs(level) <= 1e-6:
            return 0.35
        if direction > 0 and level < -1e-6:
            return 0.20
        return -0.1
    if mode == 4:  # reverse_right
        if direction < 0 and level > 1e-6:
            return 1.0
        if direction < 0 and abs(level) <= 1e-6:
            return 0.35
        if direction > 0 and level > 1e-6:
            return 0.20
        return -0.1
    return 0.0


def primitive_priority_delta(case: dict[str, Any], primitive_index: int, mode: int, strength: float) -> float:
    pindex = primitive_index_from_case(case)
    level, direction = pindex.to_level_direction(int(primitive_index))
    match = bundle_like_match(int(mode), float(level), int(direction))
    return -float(strength) * float(match)


def collect_mode_training_rows(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in assets:
        result = item['baseline_result']
        trace = item.get('trace', [])
        if not bool(result.success) or len(trace) <= 0:
            continue
        path = np.asarray(result.path, dtype=np.float32)
        pindex = primitive_index_from_case(item['case'])
        prev_steer = 0.0
        for t in range(min(len(trace), path.shape[0] - 1)):
            state = tuple(float(v) for v in path[t])
            target = bundle_target_from_trace(trace, t, pindex)
            score = bottleneck_regime_score(item['case'], item['bundle'], item['field'], state)
            if target is None and float(score) < 0.35:
                chosen_idx = int(trace[t])
                prev_steer = pindex.actual_steer(chosen_idx, math.radians(float(item['case']['vehicle'].max_steer_deg)))
                continue
            feat = build_compact_bundle_feature_vector(item['case'], item['bundle'], item['field'], state, prev_steer=prev_steer)
            rows.append({
                'feature': feat.astype(np.float32),
                'mode': int(mode_from_bundle_target(target)),
                'score': float(score),
                'scenario': str(item['case']['scenario']),
                'sample_name': str(item['path'].name),
            })
            chosen_idx = int(trace[t])
            prev_steer = pindex.actual_steer(chosen_idx, math.radians(float(item['case']['vehicle'].max_steer_deg)))
    return rows


def fit_mode_prototypes(rows: list[dict[str, Any]], num_modes: int = len(MODE_LABELS)) -> dict[str, Any]:
    if not rows:
        return {'prototypes': {}, 'counts': {}}
    by_mode: dict[int, list[np.ndarray]] = {}
    for row in rows:
        by_mode.setdefault(int(row['mode']), []).append(np.asarray(row['feature'], dtype=np.float32))
    prototypes = {}
    counts = {}
    for mode, feats in by_mode.items():
        stack = np.stack(feats, axis=0).astype(np.float32)
        proto = np.mean(stack, axis=0).astype(np.float32)
        norm = float(np.linalg.norm(proto))
        if norm > 1e-6:
            proto = proto / norm
        prototypes[int(mode)] = proto
        counts[int(mode)] = int(len(feats))
    return {'prototypes': prototypes, 'counts': counts}


def nearest_mode(feature: np.ndarray, prototype_bank: dict[str, Any], *, neutral_if_small: float = 0.10) -> tuple[int, float]:
    if not prototype_bank.get('prototypes'):
        return 0, 0.0
    feat = np.asarray(feature, dtype=np.float32)
    n = float(np.linalg.norm(feat))
    if n > 1e-6:
        feat = feat / n
    best_mode = 0
    best_sim = -1.0
    for mode, proto in prototype_bank['prototypes'].items():
        sim = float(np.dot(feat, np.asarray(proto, dtype=np.float32)))
        if sim > best_sim:
            best_sim = sim
            best_mode = int(mode)
    if best_sim < float(neutral_if_small):
        return 0, float(best_sim)
    return int(best_mode), float(best_sim)


def coarse_grid_shape(case: dict[str, Any], spec: CoarseGridSpec) -> tuple[int, int]:
    h, w = np.asarray(case['occupancy']).shape
    stride = int(max(spec.stride_cells, 1))
    return int(math.ceil(h / stride)), int(math.ceil(w / stride))


def coarse_cell_center(case: dict[str, Any], gy: int, gx: int, spec: CoarseGridSpec) -> tuple[float, float]:
    stride = int(max(spec.stride_cells, 1))
    y = (float(gy * stride) + 0.5 * float(stride)) * float(case['resolution'])
    x = (float(gx * stride) + 0.5 * float(stride)) * float(case['resolution'])
    max_x = (case['occupancy'].shape[1] - 0.5) * float(case['resolution'])
    max_y = (case['occupancy'].shape[0] - 0.5) * float(case['resolution'])
    return float(min(x, max_x)), float(min(y, max_y))


def state_for_cell(case: dict[str, Any], gy: int, gx: int, spec: CoarseGridSpec, *, yaw: float | None = None) -> tuple[float, float, float]:
    x, y = coarse_cell_center(case, gy, gx, spec)
    if yaw is None:
        gxw, gyw, gyaw = map(float, case['goal'])
        yaw = math.atan2(gyw - y, gxw - x)
    return (float(x), float(y), float(yaw))


def build_coarse_mode_map(case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, spec: CoarseGridSpec, prototype_bank: dict[str, Any], *, gate_threshold: float, neutral_similarity: float = 0.10) -> tuple[np.ndarray, np.ndarray]:
    gh, gw = coarse_grid_shape(case, spec)
    mode_map = np.zeros((gh, gw), dtype=np.int16)
    conf_map = np.zeros((gh, gw), dtype=np.float32)
    pindex = primitive_index_from_case(case)
    for gy in range(gh):
        for gx in range(gw):
            x, y, yaw = state_for_cell(case, gy, gx, spec)
            score = bottleneck_regime_score(case, bundle, field, (x, y, yaw))
            if score < float(gate_threshold):
                continue
            feat = build_compact_bundle_feature_vector(case, bundle, field, (x, y, yaw), prev_steer=0.0, primitive_index=pindex, escape_features=(0.0, 0.0))
            mode, sim = nearest_mode(feat, prototype_bank, neutral_if_small=float(neutral_similarity))
            mode_map[gy, gx] = int(mode)
            conf_map[gy, gx] = float(max(sim, 0.0))
    return mode_map, conf_map


def query_coarse_mode(case: dict[str, Any], mode_map: np.ndarray, spec: CoarseGridSpec, state: tuple[float, float, float]) -> int:
    x, y, _ = state
    stride = int(max(spec.stride_cells, 1))
    gx = int(np.clip(np.floor(float(x) / float(case['resolution']) / stride), 0, mode_map.shape[1] - 1))
    gy = int(np.clip(np.floor(float(y) / float(case['resolution']) / stride), 0, mode_map.shape[0] - 1))
    return int(mode_map[gy, gx])


def geometric_bottleneck_map(bundle: dict[str, Any]) -> np.ndarray:
    score = 0.45 * bundle['barrier'] + 0.30 * bundle['focus'] + 0.20 * (1.0 - bundle['corridor']) + 0.05 * bundle['morph_width']
    return normalize01(np.asarray(score, dtype=np.float32))


def select_bottleneck_windows(case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, *, top_k: int, min_sep_m: float, gate_threshold: float) -> list[dict[str, Any]]:
    score_map = geometric_bottleneck_map(bundle)
    occ = np.asarray(case['occupancy'], dtype=bool)
    free_scores = np.asarray(score_map, dtype=np.float32).copy()
    free_scores[occ] = -1.0
    windows: list[dict[str, Any]] = []
    work = free_scores.copy()
    radius_px = max(int(round(float(min_sep_m) / max(float(case['resolution']), 1e-6))), 1)
    for _ in range(int(top_k)):
        idx = np.unravel_index(int(np.argmax(work)), work.shape)
        if float(work[idx]) < float(gate_threshold):
            break
        gy, gx = int(idx[0]), int(idx[1])
        state = state_for_cell(case, gy, gx, CoarseGridSpec(stride_cells=1))
        windows.append({'grid_y': gy, 'grid_x': gx, 'state': state, 'score': float(work[idx])})
        y0 = max(0, gy - radius_px)
        y1 = min(work.shape[0], gy + radius_px + 1)
        x0 = max(0, gx - radius_px)
        x1 = min(work.shape[1], gx + radius_px + 1)
        work[y0:y1, x0:x1] = -1.0
    return windows


def rasterize_sparse_mode_map(case: dict[str, Any], windows: list[dict[str, Any]], *, radius_m: float) -> np.ndarray:
    occ = np.asarray(case['occupancy'], dtype=bool)
    out = np.zeros_like(occ, dtype=np.int16)
    radius_px = max(int(round(float(radius_m) / max(float(case['resolution']), 1e-6))), 1)
    for win in windows:
        gy = int(win['grid_y'])
        gx = int(win['grid_x'])
        mode = int(win['mode'])
        y0 = max(0, gy - radius_px)
        y1 = min(out.shape[0], gy + radius_px + 1)
        x0 = max(0, gx - radius_px)
        x1 = min(out.shape[1], gx + radius_px + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        mask = (yy - gy) ** 2 + (xx - gx) ** 2 <= radius_px ** 2
        view = out[y0:y1, x0:x1]
        view[mask] = int(mode)
    return out


def query_dense_mode(case: dict[str, Any], mode_map: np.ndarray, state: tuple[float, float, float]) -> int:
    x, y, _ = state
    gx = int(np.clip(np.floor(float(x) / float(case['resolution'])), 0, mode_map.shape[1] - 1))
    gy = int(np.clip(np.floor(float(y) / float(case['resolution'])), 0, mode_map.shape[0] - 1))
    return int(mode_map[gy, gx])


def select_program_gates(case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, prototype_bank: dict[str, Any], *, top_k: int, gate_threshold: float) -> list[dict[str, Any]]:
    windows = select_bottleneck_windows(case, bundle, field, top_k=int(top_k), min_sep_m=3.0, gate_threshold=float(gate_threshold))
    gates: list[dict[str, Any]] = []
    for win in windows:
        feat = build_compact_bundle_feature_vector(case, bundle, field, win['state'], prev_steer=0.0)
        mode, sim = nearest_mode(feat, prototype_bank, neutral_if_small=0.10)
        if mode == 0:
            continue
        gates.append({'state': win['state'], 'mode': int(mode), 'score': float(win['score']), 'similarity': float(sim)})
    gates.sort(key=lambda g: (-float(g['score']), -float(g['similarity'])))
    return gates[: int(top_k)]


def gate_progress(gate_state: tuple[float, float, float], current_state: tuple[float, float, float]) -> float:
    gx, gy, _ = gate_state
    x, y, _ = current_state
    return float(np.hypot(gx - x, gy - y))


def active_gate_mode(gates: list[dict[str, Any]], current_state: tuple[float, float, float], *, reached_thr_m: float = 1.5) -> int:
    if not gates:
        return 0
    for gate in gates:
        if gate_progress(gate['state'], current_state) > float(reached_thr_m):
            return int(gate['mode'])
    return 0


__all__ = [
    'CoarseGridSpec',
    'MODE_LABELS',
    'accepted_cx3d_nonholonomic',
    'accepted_cx3d_standard',
    'active_gate_mode',
    'build_coarse_mode_map',
    'build_compact_bundle_feature_vector',
    'build_compact_state_cache',
    'bundle_target_from_trace',
    'collect_mode_training_rows',
    'fit_mode_prototypes',
    'geometric_bottleneck_map',
    'load_nonholonomic_assets',
    'mode_from_bundle_target',
    'mode_label',
    'nearest_mode',
    'primitive_bias_for_mode',
    'primitive_index_from_case',
    'query_coarse_mode',
    'query_dense_mode',
    'run_hybrid_with_policy',
    'rasterize_sparse_mode_map',
    'select_bottleneck_windows',
    'select_program_gates',
]
