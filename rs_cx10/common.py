from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_cx8.common import (
    BUNDLE_LABELS,
    bottleneck_regime_score,
    build_bundle_feature_vector,
    build_compact_bundle_feature_vector,
    bundle_target_from_trace,
    predict_logits,
    primitive_index_from_case,
    run_hybrid_with_policy,
)
from rs_cx8 import cx8_d_heavy
from rs_cx9.common import primitive_priority_delta, select_bottleneck_windows

FEATURE_INDEX = {
    'goal_dist': 0,
    'goal_heading_cos': 1,
    'goal_heading_sin': 2,
    'goal_yaw_cos': 3,
    'goal_yaw_sin': 4,
    'prev_steer': 5,
    'clearance': 6,
    'focus': 7,
    'barrier': 8,
    'corridor': 9,
    'morph_width': 10,
    'risk': 11,
    'anchor': 12,
    'scene_hard': 13,
    'scene_misc': 14,
    'scene_bridge': 15,
    'scene_open': 16,
    'reverse_escape': 17,
    'forward_escape': 18,
    'bottleneck': 19,
    'prev_steer_dup': 20,
    'abs_prev_steer': 21,
    'heading_align': 22,
    'goal_yaw_cos_dup': 23,
    'curvature_slack': 24,
    'scene_hard_dup': 25,
    'scene_misc_dup': 26,
    'scene_bridge_dup': 27,
}

REVERSE_LABELS = {2, 3}
THREAD_LABELS = {0, 1}
MODE_NAMES = {
    0: 'neutral',
    1: 'thread_left',
    2: 'thread_right',
    3: 'reverse_left',
    4: 'reverse_right',
}


def bundle_to_mode(label: int | None) -> int:
    if label is None:
        return 0
    return int(label) + 1


def mode_to_bundle(mode: int | None) -> int | None:
    if mode is None:
        return None
    mode = int(mode)
    if mode <= 0:
        return None
    return int(mode) - 1


def scene_feature_vector(bundle: dict[str, Any]) -> np.ndarray:
    scene = bundle.get('scene', {})
    barrier = np.asarray(bundle['barrier'], dtype=np.float32)
    focus = np.asarray(bundle['focus'], dtype=np.float32)
    corridor = np.asarray(bundle['corridor'], dtype=np.float32)
    morph_width = np.asarray(bundle.get('morph_width', np.zeros_like(barrier)), dtype=np.float32)
    score = 0.45 * barrier + 0.30 * focus + 0.20 * (1.0 - corridor) + 0.05 * morph_width
    return np.asarray([
        float(scene.get('hard_likelihood', 0.0)),
        float(scene.get('misc_likelihood', 0.0)),
        float(scene.get('bridge_diffuse', 0.0)),
        float(scene.get('path_openness', 0.0)),
        float(np.mean(score)),
        float(np.max(score)),
        float(np.mean(barrier)),
        float(np.mean(focus)),
        float(np.mean(1.0 - corridor)),
        float(np.std(score)),
    ], dtype=np.float32)


def mode_name(mode: int) -> str:
    return MODE_NAMES.get(int(mode), f'mode_{int(mode)}')


def load_teacher_memory(chosen_json: Path, device: str) -> dict[str, Any]:
    return cx8_d_heavy.load_locked_memory(chosen_json, device)


def teacher_predict_bundle(
    teacher_memory: dict[str, Any],
    case: dict[str, Any],
    bundle: dict[str, Any],
    field: np.ndarray,
    state: tuple[float, float, float],
    *,
    prev_steer: float,
) -> dict[str, Any]:
    params = teacher_memory['params']
    regime = float(bottleneck_regime_score(case, bundle, field, state))
    if regime < float(params.bottleneck_gate):
        return {
            'bundle_id': None,
            'bundle_conf': 0.0,
            'regime': float(regime),
            'probs': np.zeros(len(BUNDLE_LABELS), dtype=np.float32),
        }
    feat = build_bundle_feature_vector(
        case,
        bundle,
        field,
        state,
        prev_steer=float(prev_steer),
        patch_radius=int(params.patch_radius),
    )[None, :]
    logits = predict_logits(teacher_memory['model'], teacher_memory['meta'], feat, device=str(teacher_memory.get('device', 'cpu')))[0]
    logits = np.asarray(logits[: len(BUNDLE_LABELS)], dtype=np.float32)
    logits = logits - float(np.max(logits))
    probs = np.exp(logits)
    probs = probs / max(float(np.sum(probs)), 1e-6)
    bundle_id = int(np.argmax(probs))
    conf = float(probs[bundle_id])
    if conf < float(params.bundle_conf_thr):
        bundle_id = None
    return {
        'bundle_id': bundle_id,
        'bundle_conf': float(conf),
        'regime': float(regime),
        'probs': probs.astype(np.float32),
    }


def collect_compilation_rows(
    assets: Iterable[dict[str, Any]],
    teacher_memory: dict[str, Any],
    *,
    regime_floor: float,
    teacher_conf_floor: float,
    sample_stride: int,
    max_rows_per_case: int = 128,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in assets:
        result = asset['baseline_result']
        trace = list(asset.get('trace', []))
        if not bool(result.success) or len(trace) <= 0 or np.asarray(result.path).shape[0] < 2:
            continue
        case = asset['case']
        bundle = asset['bundle']
        field = asset['field']
        pindex = primitive_index_from_case(case)
        path = np.asarray(result.path, dtype=np.float32)
        seen_keys: set[tuple[int, int, int, int]] = set()
        prev_steer = 0.0
        kept = 0
        max_steer = math.radians(float(case['vehicle'].max_steer_deg))
        horizon = min(len(trace), int(path.shape[0]) - 1)
        for t in range(horizon):
            chosen_idx = int(trace[t])
            if int(sample_stride) > 1 and (t % int(sample_stride)) != 0:
                prev_steer = pindex.actual_steer(chosen_idx, max_steer)
                continue
            state = tuple(float(v) for v in path[t])
            teacher = teacher_predict_bundle(
                teacher_memory,
                case,
                bundle,
                field,
                state,
                prev_steer=float(prev_steer),
            )
            trace_target = bundle_target_from_trace(trace, t, pindex)
            label = None
            source = 'none'
            if teacher['bundle_id'] is not None and float(teacher['bundle_conf']) >= float(teacher_conf_floor):
                label = int(teacher['bundle_id'])
                source = 'teacher'
            elif trace_target is not None and float(teacher['regime']) >= float(regime_floor):
                label = int(trace_target)
                source = 'trace'
            if label is None:
                prev_steer = pindex.actual_steer(chosen_idx, max_steer)
                continue
            if float(teacher['regime']) < float(regime_floor) and trace_target is None:
                prev_steer = pindex.actual_steer(chosen_idx, max_steer)
                continue
            feat = build_compact_bundle_feature_vector(case, bundle, field, state, prev_steer=float(prev_steer), primitive_index=pindex)
            x, y, yaw = state
            key = (int(round(x / max(float(case['resolution']), 1e-6))), int(round(y / max(float(case['resolution']), 1e-6))), int(round(yaw * 10.0)), int(label))
            if key in seen_keys:
                prev_steer = pindex.actual_steer(chosen_idx, max_steer)
                continue
            seen_keys.add(key)
            rows.append({
                'feature': np.asarray(feat, dtype=np.float32),
                'scene_feature': scene_feature_vector(bundle),
                'label': int(label),
                'mode': int(label) + 1,
                'regime': float(teacher['regime']),
                'teacher_conf': float(teacher['bundle_conf']),
                'scenario': str(case['scenario']),
                'sample_name': str(asset['path'].name),
                'state': (float(x), float(y), float(yaw)),
                'prev_steer': float(prev_steer),
                'source': source,
            })
            kept += 1
            prev_steer = pindex.actual_steer(chosen_idx, max_steer)
            if int(max_rows_per_case) > 0 and kept >= int(max_rows_per_case):
                break
    return rows


def _standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0, keepdims=True).astype(np.float32)
    std = x.std(axis=0, keepdims=True).astype(np.float32)
    std[std < 1e-6] = 1.0
    z = ((x - mean) / std).astype(np.float32)
    return z, mean.astype(np.float32), std.astype(np.float32)


def fit_rulebook(rows: list[dict[str, Any]], *, sim_quantile: float = 0.25) -> dict[str, Any]:
    if not rows:
        return {
            'prototypes': {},
            'scene_prototypes': {},
            'support': {},
            'counts': {},
            'mean': np.zeros((1, len(FEATURE_INDEX)), dtype=np.float32),
            'std': np.ones((1, len(FEATURE_INDEX)), dtype=np.float32),
        }
    x = np.stack([np.asarray(r['feature'], dtype=np.float32) for r in rows], axis=0)
    z, mean, std = _standardize(x)
    scene_x = np.stack([np.asarray(r['scene_feature'], dtype=np.float32) for r in rows], axis=0)
    scene_z, scene_mean, scene_std = _standardize(scene_x)
    by_label: dict[int, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        by_label[int(row['label'])].append(idx)
    prototypes: dict[int, np.ndarray] = {}
    scene_prototypes: dict[int, np.ndarray] = {}
    support: dict[int, dict[str, float]] = {}
    counts: dict[int, int] = {}
    for label, idxs in sorted(by_label.items()):
        lab = z[idxs]
        proto = np.mean(lab, axis=0).astype(np.float32)
        norm = float(np.linalg.norm(proto))
        if norm > 1e-6:
            proto = proto / norm
        scene_proto = np.mean(scene_z[idxs], axis=0).astype(np.float32)
        scene_norm = float(np.linalg.norm(scene_proto))
        if scene_norm > 1e-6:
            scene_proto = scene_proto / scene_norm
        sims = lab @ proto
        support[int(label)] = {
            'sim_floor': float(np.quantile(sims, float(np.clip(sim_quantile, 0.0, 0.9)))) if sims.size else 0.0,
            'bottleneck_floor': float(np.quantile(x[idxs, FEATURE_INDEX['bottleneck']], 0.25)),
            'reverse_floor': float(np.quantile(x[idxs, FEATURE_INDEX['reverse_escape']], 0.25)),
            'forward_floor': float(np.quantile(x[idxs, FEATURE_INDEX['forward_escape']], 0.25)),
            'hard_margin_floor': float(np.quantile(x[idxs, FEATURE_INDEX['scene_hard']] - x[idxs, FEATURE_INDEX['scene_misc']], 0.2)),
        }
        prototypes[int(label)] = proto
        scene_prototypes[int(label)] = scene_proto
        counts[int(label)] = int(len(idxs))
    return {
        'prototypes': prototypes,
        'scene_prototypes': scene_prototypes,
        'support': support,
        'counts': counts,
        'mean': mean,
        'std': std,
        'scene_mean': scene_mean,
        'scene_std': scene_std,
    }


def _normalize_with_bank(feature: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    arr = np.asarray(feature, dtype=np.float32)[None, :]
    z = ((arr - np.asarray(mean, dtype=np.float32)) / np.asarray(std, dtype=np.float32)).astype(np.float32)[0]
    norm = float(np.linalg.norm(z))
    if norm > 1e-6:
        z = z / norm
    return z.astype(np.float32)


def predict_rulebook(
    feature: np.ndarray,
    bank: dict[str, Any],
    *,
    similarity_thr: float,
    bottleneck_thr: float,
    misc_margin: float,
    allow_reverse_with_low_escape: bool = False,
) -> dict[str, Any]:
    if not bank.get('prototypes'):
        return {'bundle_id': None, 'mode': 0, 'similarity': 0.0, 'confidence': 0.0}
    x = np.asarray(feature, dtype=np.float32)
    z = _normalize_with_bank(x, bank['mean'], bank['std'])
    best_label = None
    best_sim = -1e9
    for label, proto in bank['prototypes'].items():
        sim = float(np.dot(z, np.asarray(proto, dtype=np.float32)))
        if sim > best_sim:
            best_sim = sim
            best_label = int(label)
    if best_label is None:
        return {'bundle_id': None, 'mode': 0, 'similarity': 0.0, 'confidence': 0.0}
    support = bank['support'].get(int(best_label), {})
    required_sim = max(float(similarity_thr), float(support.get('sim_floor', -1.0)) - 0.04)
    if best_sim < required_sim:
        return {'bundle_id': None, 'mode': 0, 'similarity': float(best_sim), 'confidence': 0.0}
    if float(x[FEATURE_INDEX['bottleneck']]) < max(float(bottleneck_thr), float(support.get('bottleneck_floor', 0.0))):
        return {'bundle_id': None, 'mode': 0, 'similarity': float(best_sim), 'confidence': 0.0}
    if float(x[FEATURE_INDEX['scene_misc']]) > float(x[FEATURE_INDEX['scene_hard']]) + float(misc_margin):
        return {'bundle_id': None, 'mode': 0, 'similarity': float(best_sim), 'confidence': 0.0}
    if int(best_label) in REVERSE_LABELS and not bool(allow_reverse_with_low_escape):
        if float(x[FEATURE_INDEX['reverse_escape']]) + 0.02 < max(0.02, float(support.get('reverse_floor', 0.0))):
            return {'bundle_id': None, 'mode': 0, 'similarity': float(best_sim), 'confidence': 0.0}
    conf = float(np.clip((best_sim - required_sim) / max(1.0 - required_sim, 1e-6), 0.0, 1.0))
    return {
        'bundle_id': int(best_label),
        'mode': bundle_to_mode(int(best_label)),
        'similarity': float(best_sim),
        'confidence': float(conf),
    }


def fit_scene_template_bank(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            'templates': {},
            'counts': {},
            'mean': np.zeros((1, 10), dtype=np.float32),
            'std': np.ones((1, 10), dtype=np.float32),
        }
    x = np.stack([np.asarray(r['scene_feature'], dtype=np.float32) for r in rows], axis=0)
    z, mean, std = _standardize(x)
    by_template: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        by_template[str(row['template'])].append(idx)
    templates = {}
    counts = {}
    for key, idxs in sorted(by_template.items()):
        proto = np.mean(z[idxs], axis=0).astype(np.float32)
        norm = float(np.linalg.norm(proto))
        if norm > 1e-6:
            proto = proto / norm
        templates[key] = proto
        counts[key] = int(len(idxs))
    return {
        'templates': templates,
        'counts': counts,
        'mean': mean,
        'std': std,
    }


def predict_scene_template(scene_feature: np.ndarray, bank: dict[str, Any], *, similarity_thr: float) -> dict[str, Any]:
    if not bank.get('templates'):
        return {'template': 'neutral', 'similarity': 0.0}
    z = _normalize_with_bank(np.asarray(scene_feature, dtype=np.float32), bank['mean'], bank['std'])
    best_key = 'neutral'
    best_sim = -1e9
    for key, proto in bank['templates'].items():
        sim = float(np.dot(z, np.asarray(proto, dtype=np.float32)))
        if sim > best_sim:
            best_sim = sim
            best_key = str(key)
    if best_sim < float(similarity_thr):
        return {'template': 'neutral', 'similarity': float(best_sim)}
    return {'template': best_key, 'similarity': float(best_sim)}


def order_windows_by_anchor(case: dict[str, Any], field: np.ndarray, windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not windows:
        return []
    ranked = []
    for win in windows:
        x, y, yaw = win['state']
        anchor = float(field[0, 0, 0]) if np.asarray(field).ndim == 0 else float(np.nan)
        if np.asarray(field).ndim >= 2:
            from rs_cx8.common import query_yaw_field
            anchor = float(query_yaw_field(field, float(x), float(y), float(yaw), float(case['resolution'])))
        ranked.append({**win, 'anchor': float(anchor)})
    ranked.sort(key=lambda item: float(item['anchor']), reverse=True)
    return ranked


def nearest_window(windows: list[dict[str, Any]], state: tuple[float, float, float]) -> tuple[dict[str, Any] | None, float]:
    if not windows:
        return None, float('inf')
    x, y, _ = state
    best = None
    best_dist = float('inf')
    for win in windows:
        wx, wy, _ = win['state']
        dist = float(np.hypot(float(wx) - float(x), float(wy) - float(y)))
        if dist < best_dist:
            best = win
            best_dist = dist
    return best, float(best_dist)


def recent_records(record, records: dict[Any, Any], depth: int) -> list[Any]:
    out = []
    cur = record
    for _ in range(int(max(depth, 0))):
        if cur is None:
            break
        out.append(cur)
        parent_key = getattr(cur, 'parent', None)
        if parent_key is None or parent_key not in records:
            break
        cur = records[parent_key]
    return out


def bundle_side(label: int | None) -> int:
    if label is None:
        return 0
    return -1 if int(label) in (0, 2) else (1 if int(label) in (1, 3) else 0)


def template_tokens_from_labels(labels: list[int]) -> str:
    if not labels:
        return 'neutral'
    primary = int(labels[0])
    if primary == 2:
        return 'reverse_left_then_thread_left'
    if primary == 3:
        return 'reverse_right_then_thread_right'
    if primary == 0:
        return 'thread_left_only'
    if primary == 1:
        return 'thread_right_only'
    return 'neutral'


def collect_scene_template_rows(
    assets: Iterable[dict[str, Any]],
    teacher_memory: dict[str, Any],
    *,
    top_k_windows: int,
    gate_threshold: float,
    regime_floor: float,
    teacher_conf_floor: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in assets:
        case = asset['case']
        bundle = asset['bundle']
        field = asset['field']
        windows = select_bottleneck_windows(case, bundle, field, top_k=int(top_k_windows), min_sep_m=2.5, gate_threshold=float(gate_threshold))
        labels: list[int] = []
        for win in order_windows_by_anchor(case, field, windows):
            feat = build_compact_bundle_feature_vector(case, bundle, field, win['state'], prev_steer=0.0)
            pred = teacher_predict_bundle(teacher_memory, case, bundle, field, win['state'], prev_steer=0.0)
            label = pred['bundle_id'] if pred['bundle_id'] is not None and float(pred['bundle_conf']) >= float(teacher_conf_floor) else None
            if label is None and float(pred['regime']) >= float(regime_floor):
                bankless = int(np.argmax([feat[FEATURE_INDEX['reverse_escape']], feat[FEATURE_INDEX['forward_escape']], feat[FEATURE_INDEX['barrier']], feat[FEATURE_INDEX['corridor']]]))
                if bankless == 0:
                    label = 2
                elif bankless == 1:
                    label = 3
                elif feat[FEATURE_INDEX['goal_heading_cos']] >= 0.0:
                    label = 0 if feat[FEATURE_INDEX['goal_heading_sin']] <= 0.0 else 1
            if label is not None:
                labels.append(int(label))
        rows.append({
            'sample_name': str(asset['path'].name),
            'scenario': str(case['scenario']),
            'scene_feature': scene_feature_vector(bundle),
            'template': template_tokens_from_labels(labels[:2]),
            'labels': labels[:2],
        })
    return rows


def default_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def default_standard_field(sample, predictor) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)


__all__ = [
    'BUNDLE_LABELS',
    'FEATURE_INDEX',
    'MODE_NAMES',
    'REVERSE_LABELS',
    'THREAD_LABELS',
    'accepted_cx3d_nonholonomic',
    'accepted_cx3d_standard',
    'bottleneck_regime_score',
    'build_compact_bundle_feature_vector',
    'bundle_side',
    'bundle_to_mode',
    'collect_compilation_rows',
    'collect_scene_template_rows',
    'cx8_d_heavy',
    'default_nonholonomic_field',
    'default_standard_field',
    'fit_rulebook',
    'fit_scene_template_bank',
    'load_teacher_memory',
    'mode_name',
    'mode_to_bundle',
    'nearest_window',
    'order_windows_by_anchor',
    'predict_rulebook',
    'predict_scene_template',
    'primitive_index_from_case',
    'primitive_priority_delta',
    'recent_records',
    'run_hybrid_with_policy',
    'scene_feature_vector',
    'select_bottleneck_windows',
    'teacher_predict_bundle',
]
