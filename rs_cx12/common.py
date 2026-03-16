from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx4.common import accepted_cx3d_standard
from rs_cx8.common import (
    query_yaw_field,
    run_hybrid_with_policy,
)
from rs_cx10 import cx10_d_las
from rs_cx10.common import FEATURE_INDEX, build_compact_bundle_feature_vector
from rs_cx11.common import fit_tree, predict_tree, tree_to_dict

BASE_CHOSEN_JSON = Path('outputs/rs_p0cx10_d_pilot_v1/chosen.json')

GEOM_FEATURE_NAMES = (
    'top_gate_score',
    'goal_dist',
    'heading_to_goal_cos',
    'clearance',
    'corridor_conf',
    'corridor_width',
    'bottleneck',
    'scene_hard',
    'scene_misc',
    'scene_bridge',
    'scene_open',
    'goal_ray_len',
    'goal_ray_clear_min',
    'goal_ray_clear_mean',
    'left_ray_len',
    'right_ray_len',
    'back_ray_len',
    'lateral_avg',
    'lateral_asym',
    'trap_score',
    'pocket_ratio',
    'exit_clearance_proxy',
)


@dataclass(frozen=True)
class GeomTreeNode:
    feature_index: int
    threshold: float
    prob: float
    left: Any = None
    right: Any = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None or self.right is None or int(self.feature_index) < 0


def load_base_params(chosen_json: Path = BASE_CHOSEN_JSON) -> cx10_d_las.CX10DLASParams:
    data = json.loads(Path(chosen_json).read_text(encoding='utf-8'))
    return cx10_d_las.CX10DLASParams(**data['params'])


def _ray_stats(
    case: dict[str, Any],
    state: tuple[float, float, float],
    angle: float,
    *,
    max_len: float = 6.0,
    step: float = 0.20,
) -> tuple[float, float, float]:
    x, y, _ = map(float, state)
    esdf = np.asarray(case['esdf'], dtype=np.float32)
    res = float(case['resolution'])
    cur = 0.0
    clearances: list[float] = []
    cutoff = 0.35 * float(case['vehicle'].width)
    while cur <= float(max_len):
        px = x + cur * math.cos(float(angle))
        py = y + cur * math.sin(float(angle))
        gx = int(np.floor(px / max(res, 1e-6)))
        gy = int(np.floor(py / max(res, 1e-6)))
        if gx < 0 or gy < 0 or gx >= esdf.shape[1] or gy >= esdf.shape[0]:
            break
        clearance = float(esdf[gy, gx])
        if clearance <= float(cutoff):
            break
        clearances.append(clearance)
        cur += float(step)
    if not clearances:
        return 0.0, 0.0, 0.0
    return float(cur), float(np.min(clearances)), float(np.mean(clearances))


def gate_geometry_features(case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, gate: dict[str, Any]) -> np.ndarray:
    feat_arr = gate.get('compact_feature', None)
    if feat_arr is None:
        feat_arr = build_compact_bundle_feature_vector(case, bundle, field, tuple(float(v) for v in gate['state']), prev_steer=0.0)
    feat = np.asarray(feat_arr, dtype=np.float32)
    state = tuple(float(v) for v in gate['state'])
    gx, gy, _ = map(float, case['goal'])
    heading = math.atan2(gy - float(state[1]), gx - float(state[0]))
    goal_ray_len, goal_ray_clear_min, goal_ray_clear_mean = _ray_stats(case, state, heading)
    left_ray_len, _, _ = _ray_stats(case, state, heading + 0.5 * math.pi)
    right_ray_len, _, _ = _ray_stats(case, state, heading - 0.5 * math.pi)
    back_ray_len, _, _ = _ray_stats(case, state, heading + math.pi)
    lateral_avg = 0.5 * (left_ray_len + right_ray_len)
    lateral_asym = abs(left_ray_len - right_ray_len)
    trap_score = float((lateral_avg + 0.5 * back_ray_len) / max(goal_ray_len, 0.25))
    pocket_ratio = float(back_ray_len / max(goal_ray_len, 0.25))
    exit_clearance_proxy = float(goal_ray_len * max(goal_ray_clear_min, 0.0))
    return np.asarray([
        float(gate.get('score', 0.0)),
        float(feat[FEATURE_INDEX['goal_dist']]),
        float(feat[FEATURE_INDEX['heading_align']]),
        float(feat[FEATURE_INDEX['clearance']]),
        float(feat[FEATURE_INDEX['corridor']]),
        float(feat[FEATURE_INDEX['morph_width']]),
        float(feat[FEATURE_INDEX['bottleneck']]),
        float(feat[FEATURE_INDEX['scene_hard']]),
        float(feat[FEATURE_INDEX['scene_misc']]),
        float(feat[FEATURE_INDEX['scene_bridge']]),
        float(feat[FEATURE_INDEX['scene_open']]),
        float(goal_ray_len),
        float(goal_ray_clear_min),
        float(goal_ray_clear_mean),
        float(left_ray_len),
        float(right_ray_len),
        float(back_ray_len),
        float(lateral_avg),
        float(lateral_asym),
        float(trap_score),
        float(pocket_ratio),
        float(exit_clearance_proxy),
    ], dtype=np.float32)


def scene_context(
    base_memory: dict[str, Any],
    base_params: cx10_d_las.CX10DLASParams,
    case: dict[str, Any],
    bundle: dict[str, Any],
    field: np.ndarray,
    device: str,
) -> dict[str, Any]:
    base_policy = cx10_d_las.make_policy(base_memory, base_params, case, bundle, field, device, ablation=None)
    gates = list(getattr(base_policy, 'gates', [])) if base_policy is not None else []
    top_gate = max(gates, key=lambda item: float(item.get('score', 0.0))) if gates else None
    if top_gate is not None and top_gate.get('compact_feature', None) is None:
        top_gate = {
            **top_gate,
            'compact_feature': build_compact_bundle_feature_vector(case, bundle, field, tuple(float(v) for v in top_gate['state']), prev_steer=0.0),
        }
    geom = gate_geometry_features(case, bundle, field, top_gate) if top_gate is not None else np.zeros(len(GEOM_FEATURE_NAMES), dtype=np.float32)
    return {
        'base_policy': base_policy,
        'gates': gates,
        'top_gate': top_gate,
        'geom_feature': geom,
    }


def fit_geom_tree(features: np.ndarray, labels: np.ndarray, max_depth: int) -> GeomTreeNode:
    tree = fit_tree(np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int64), max_depth=int(max_depth))
    return GeomTreeNode(
        feature_index=int(tree.feature_index),
        threshold=float(tree.threshold),
        prob=float(tree.prob),
        left=None if tree.left is None else fit_geom_tree(np.zeros((2, features.shape[1]), dtype=np.float32), np.asarray([0, 0], dtype=np.int64), 0) if False else tree.left,  # type: ignore[arg-type]
        right=None if tree.right is None else fit_geom_tree(np.zeros((2, features.shape[1]), dtype=np.float32), np.asarray([0, 0], dtype=np.int64), 0) if False else tree.right,  # type: ignore[arg-type]
    )


def tree_prob(tree: Any, feat: np.ndarray) -> float:
    return float(predict_tree(tree, np.asarray(feat, dtype=np.float32)))


def geom_tree_dict(tree: Any) -> dict[str, Any]:
    return tree_to_dict(tree, GEOM_FEATURE_NAMES)


def standard_identity_error(sample, predictor, field_builder) -> float:
    _, accepted = accepted_cx3d_standard(sample, predictor)
    field = field_builder(sample, predictor)
    return float(np.max(np.abs(np.asarray(field, dtype=np.float32) - np.asarray(accepted, dtype=np.float32))))


def recent_anchor_progress(
    case: dict[str, Any],
    field: np.ndarray,
    record,
    records: dict[Any, Any],
    *,
    depth: int,
) -> float:
    cur = record
    vals = []
    for _ in range(int(max(depth, 0))):
        parent_key = getattr(cur, 'parent', None)
        if parent_key is None or parent_key not in records:
            break
        parent = records[parent_key]
        cur_anchor = float(query_yaw_field(field, float(cur.x), float(cur.y), float(cur.yaw), float(case['resolution'])))
        parent_anchor = float(query_yaw_field(field, float(parent.x), float(parent.y), float(parent.yaw), float(case['resolution'])))
        vals.append(parent_anchor - cur_anchor)
        cur = parent
    if not vals:
        return 0.0
    return float(np.mean(vals))


def compare_plan_to_baseline(baseline, plan, prep_ms: float = 0.0) -> dict[str, float]:
    total_ms = float(getattr(plan, 'runtime_ms', 0.0)) + float(prep_ms)
    return {
        'success_delta': float(getattr(plan, 'success', 0.0)) - float(getattr(baseline, 'success', 0.0)),
        'exp_delta': float(getattr(baseline, 'expansions', 0.0)) - float(getattr(plan, 'expansions', 0.0)),
        'time_delta_ms': float(getattr(baseline, 'runtime_ms', 0.0)) - float(total_ms),
        'time_overhead_ratio': (float(total_ms) - float(getattr(baseline, 'runtime_ms', 0.0))) / max(float(getattr(baseline, 'runtime_ms', 0.0)), 1e-6),
    }


def signed_mode_delta(case: dict[str, Any], primitive_index: int, mode: int, strength: float, sign: float) -> float:
    from rs_cx9.common import primitive_priority_delta
    base = float(primitive_priority_delta(case, int(primitive_index), int(mode), float(strength)))
    return float(sign) * base


__all__ = [
    'BASE_CHOSEN_JSON',
    'GEOM_FEATURE_NAMES',
    'compare_plan_to_baseline',
    'fit_geom_tree',
    'gate_geometry_features',
    'geom_tree_dict',
    'load_base_params',
    'recent_anchor_progress',
    'run_hybrid_with_policy',
    'scene_context',
    'signed_mode_delta',
    'standard_identity_error',
    'tree_prob',
]
