from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx4.common import accepted_cx3d_standard
from rs_cx8.common import (
    primitive_index_from_case,
    query_yaw_field,
    run_hybrid_with_policy,
    simulate_primitive_detailed,
)
from rs_cx10 import cx10_d_las
from rs_cx10.common import FEATURE_INDEX, build_compact_bundle_feature_vector, scene_feature_vector

PROPOSAL_FEATURE_NAMES = (
    'scene_hard',
    'scene_misc',
    'scene_bridge',
    'scene_open',
    'scene_score_mean',
    'scene_score_max',
    'scene_barrier_mean',
    'scene_focus_mean',
    'scene_corridor_gap_mean',
    'scene_score_std',
    'num_gates',
    'top_gate_score',
    'top_gate_inner_mode',
    'top_gate_outer_mode',
    'top_gate_bottleneck',
    'top_gate_clearance',
    'top_gate_corridor',
    'top_gate_width',
    'top_gate_goal_dist',
    'top_gate_heading_align',
    'top_gate_reverse_escape',
    'top_gate_forward_escape',
    'top_gate_curvature_slack',
    'mean_gate_score',
)

TOKEN_FEATURE_NAMES = (
    'gate_score',
    'inner_mode',
    'outer_mode',
    'goal_dist',
    'heading_align',
    'goal_yaw_cos',
    'clearance',
    'barrier',
    'corridor',
    'morph_width',
    'risk',
    'reverse_escape',
    'forward_escape',
    'bottleneck',
    'curvature_slack',
    'scene_hard',
    'scene_misc',
    'scene_bridge',
    'scene_open',
)


@dataclass(frozen=True)
class TreeNode:
    feature_index: int
    threshold: float
    prob: float
    left: 'TreeNode | None' = None
    right: 'TreeNode | None' = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None or self.right is None or int(self.feature_index) < 0


@dataclass(frozen=True)
class SupportBand:
    low: np.ndarray
    high: np.ndarray
    prototype: np.ndarray
    similarity_floor: float
    min_progress: float
    counts: int


@dataclass(frozen=True)
class BasePlanDelta:
    success_delta: float
    exp_delta: float
    time_delta_ms: float
    time_overhead_ratio: float
    path_delta: float


BASE_CHOSEN_JSON = Path('outputs/rs_p0cx10_d_pilot_v1/chosen.json')
TEACHER_CHOSEN_JSON = Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json')


def load_base_params(chosen_json: Path = BASE_CHOSEN_JSON) -> cx10_d_las.CX10DLASParams:
    data = json.loads(Path(chosen_json).read_text(encoding='utf-8'))
    return cx10_d_las.CX10DLASParams(**data['params'])


def proposal_context(
    base_memory: dict[str, Any],
    base_params: cx10_d_las.CX10DLASParams,
    case: dict[str, Any],
    bundle: dict[str, Any],
    field: np.ndarray,
    device: str,
) -> dict[str, Any]:
    base_policy = cx10_d_las.make_policy(base_memory, base_params, case, bundle, field, device, ablation=None)
    gates = list(getattr(base_policy, 'gates', [])) if base_policy is not None else []
    scene_feat = scene_feature_vector(bundle)
    token_rows = []
    for gate in gates:
        feat = build_compact_bundle_feature_vector(case, bundle, field, gate['state'], prev_steer=0.0)
        token_feat = np.asarray([
            float(gate.get('score', 0.0)),
            float(gate.get('inner_mode', 0)),
            float(gate.get('outer_mode', 0)),
            float(feat[FEATURE_INDEX['goal_dist']]),
            float(feat[FEATURE_INDEX['heading_align']]),
            float(feat[FEATURE_INDEX['goal_yaw_cos_dup']]),
            float(feat[FEATURE_INDEX['clearance']]),
            float(feat[FEATURE_INDEX['barrier']]),
            float(feat[FEATURE_INDEX['corridor']]),
            float(feat[FEATURE_INDEX['morph_width']]),
            float(feat[FEATURE_INDEX['risk']]),
            float(feat[FEATURE_INDEX['reverse_escape']]),
            float(feat[FEATURE_INDEX['forward_escape']]),
            float(feat[FEATURE_INDEX['bottleneck']]),
            float(feat[FEATURE_INDEX['curvature_slack']]),
            float(feat[FEATURE_INDEX['scene_hard']]),
            float(feat[FEATURE_INDEX['scene_misc']]),
            float(feat[FEATURE_INDEX['scene_bridge']]),
            float(feat[FEATURE_INDEX['scene_open']]),
        ], dtype=np.float32)
        token_rows.append({
            **gate,
            'compact_feature': np.asarray(feat, dtype=np.float32),
            'token_feature': token_feat,
            'token_key': token_key(int(gate.get('outer_mode', 0)), int(gate.get('inner_mode', 0))),
        })
    top_gate = max(token_rows, key=lambda item: float(item.get('score', 0.0))) if token_rows else None
    proposal_feature = np.asarray([
        float(scene_feat[0]),
        float(scene_feat[1]),
        float(scene_feat[2]),
        float(scene_feat[3]),
        float(scene_feat[4]),
        float(scene_feat[5]),
        float(scene_feat[6]),
        float(scene_feat[7]),
        float(scene_feat[8]),
        float(scene_feat[9]),
        float(len(token_rows)),
        float(top_gate.get('score', 0.0) if top_gate else 0.0),
        float(top_gate.get('inner_mode', 0) if top_gate else 0.0),
        float(top_gate.get('outer_mode', 0) if top_gate else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['bottleneck']] if top_gate is not None else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['clearance']] if top_gate is not None else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['corridor']] if top_gate is not None else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['morph_width']] if top_gate is not None else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['goal_dist']] if top_gate is not None else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['heading_align']] if top_gate is not None else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['reverse_escape']] if top_gate is not None else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['forward_escape']] if top_gate is not None else 0.0),
        float(top_gate['compact_feature'][FEATURE_INDEX['curvature_slack']] if top_gate is not None else 0.0),
        float(np.mean([float(g['score']) for g in token_rows])) if token_rows else 0.0,
    ], dtype=np.float32)
    return {
        'base_policy': base_policy,
        'scene_feature': np.asarray(scene_feat, dtype=np.float32),
        'proposal_feature': proposal_feature,
        'gates': token_rows,
        'top_gate': top_gate,
    }


def token_key(outer_mode: int, inner_mode: int) -> str:
    outer = int(outer_mode)
    inner = int(inner_mode)
    return f'o{outer}_i{inner}'


def mode_side(mode: int) -> int:
    mode = int(mode)
    if mode in (1, 3):
        return -1
    if mode in (2, 4):
        return 1
    return 0


def _path_len(plan) -> float:
    arr = np.asarray(plan.path[:, :2], dtype=np.float32) if hasattr(plan, 'path') else np.asarray(plan, dtype=np.float32)
    if arr.shape[0] < 2:
        return float('nan')
    return float(np.sum(np.linalg.norm(arr[1:] - arr[:-1], axis=1)))


def compare_plan_to_baseline(baseline, plan, prep_ms: float = 0.0) -> BasePlanDelta:
    total_ms = float(getattr(plan, 'runtime_ms', 0.0)) + float(prep_ms)
    base_path = _path_len(baseline)
    alt_path = _path_len(plan)
    return BasePlanDelta(
        success_delta=float(getattr(plan, 'success', 0.0)) - float(getattr(baseline, 'success', 0.0)),
        exp_delta=float(getattr(baseline, 'expansions', 0.0)) - float(getattr(plan, 'expansions', 0.0)),
        time_delta_ms=float(getattr(baseline, 'runtime_ms', 0.0)) - float(total_ms),
        time_overhead_ratio=(float(total_ms) - float(getattr(baseline, 'runtime_ms', 0.0))) / max(float(getattr(baseline, 'runtime_ms', 0.0)), 1e-6),
        path_delta=(float(base_path) - float(alt_path)) if np.isfinite(float(base_path)) and np.isfinite(float(alt_path)) else float('nan'),
    )


def best_mode_progress(case: dict[str, Any], field: np.ndarray, gate_state: tuple[float, float, float], mode: int) -> float:
    pindex = primitive_index_from_case(case)
    max_steer = math.radians(float(case['vehicle'].max_steer_deg))
    best = -1e6
    for idx in range(len(pindex)):
        level, direction = pindex.to_level_direction(idx)
        match = False
        if int(mode) == 1 and direction > 0 and level < -1e-6:
            match = True
        elif int(mode) == 2 and direction > 0 and level > 1e-6:
            match = True
        elif int(mode) == 3 and direction < 0 and level < -1e-6:
            match = True
        elif int(mode) == 4 and direction < 0 and level > 1e-6:
            match = True
        if not match:
            continue
        steer = pindex.actual_steer(idx, max_steer)
        sim = simulate_primitive_detailed(case, gate_state, steer, direction)
        if not bool(sim.get('valid', False)) or sim.get('next_state', None) is None:
            continue
        anchor_here = float(query_yaw_field(field, float(gate_state[0]), float(gate_state[1]), float(gate_state[2]), float(case['resolution'])))
        nx, ny, nyaw = sim['next_state']
        anchor_next = float(query_yaw_field(field, float(nx), float(ny), float(nyaw), float(case['resolution'])))
        progress = float(anchor_here - anchor_next)
        best = max(best, progress)
    return float(best if np.isfinite(best) else -1e6)


def _gini(y: np.ndarray) -> float:
    if y.size <= 0:
        return 0.0
    p = float(np.mean(y))
    return 1.0 - p * p - (1.0 - p) * (1.0 - p)


def _best_split(x: np.ndarray, y: np.ndarray, min_leaf: int = 2) -> tuple[int, float, float] | None:
    n, d = x.shape
    if n < 2 * int(min_leaf):
        return None
    parent = _gini(y)
    best = None
    for feat in range(d):
        values = np.unique(np.asarray(x[:, feat], dtype=np.float32))
        if values.size < 2:
            continue
        thresholds = (values[:-1] + values[1:]) * 0.5
        for thr in thresholds:
            left = x[:, feat] <= float(thr)
            right = ~left
            if int(np.sum(left)) < int(min_leaf) or int(np.sum(right)) < int(min_leaf):
                continue
            gain = parent - (
                float(np.sum(left)) / float(n) * _gini(y[left])
                + float(np.sum(right)) / float(n) * _gini(y[right])
            )
            if best is None or gain > best[2] + 1e-9:
                best = (int(feat), float(thr), float(gain))
    return best


def fit_tree(x: np.ndarray, y: np.ndarray, max_depth: int, depth: int = 0) -> TreeNode:
    prob = float(np.mean(y)) if y.size else 0.0
    if depth >= int(max_depth) or y.size <= 2 or np.all(y == y[0]):
        return TreeNode(feature_index=-1, threshold=0.0, prob=prob)
    split = _best_split(x, y)
    if split is None or split[2] <= 1e-9:
        return TreeNode(feature_index=-1, threshold=0.0, prob=prob)
    feat, thr, _ = split
    left_mask = x[:, feat] <= float(thr)
    right_mask = ~left_mask
    left = fit_tree(x[left_mask], y[left_mask], max_depth=max_depth, depth=depth + 1)
    right = fit_tree(x[right_mask], y[right_mask], max_depth=max_depth, depth=depth + 1)
    return TreeNode(feature_index=int(feat), threshold=float(thr), prob=prob, left=left, right=right)


def predict_tree(tree: TreeNode, x: np.ndarray) -> float:
    cur = tree
    feat = np.asarray(x, dtype=np.float32)
    while cur is not None and not cur.is_leaf:
        cur = cur.left if float(feat[cur.feature_index]) <= float(cur.threshold) else cur.right
    return float(cur.prob if cur is not None else 0.0)


def tree_to_dict(tree: TreeNode, names: tuple[str, ...]) -> dict[str, Any]:
    out = {
        'feature_index': int(tree.feature_index),
        'feature_name': names[tree.feature_index] if int(tree.feature_index) >= 0 else 'leaf',
        'threshold': float(tree.threshold),
        'prob': float(tree.prob),
    }
    if tree.left is not None:
        out['left'] = tree_to_dict(tree.left, names)
    if tree.right is not None:
        out['right'] = tree_to_dict(tree.right, names)
    return out


def fit_support_band(rows: list[np.ndarray], progresses: list[float], *, low_q: float, high_q: float, sim_q: float) -> SupportBand | None:
    if not rows:
        return None
    x = np.stack([np.asarray(r, dtype=np.float32) for r in rows], axis=0)
    mean = x.mean(axis=0, keepdims=True).astype(np.float32)
    std = x.std(axis=0, keepdims=True).astype(np.float32)
    std[std < 1e-6] = 1.0
    z = ((x - mean) / std).astype(np.float32)
    proto = np.mean(z, axis=0).astype(np.float32)
    n = float(np.linalg.norm(proto))
    if n > 1e-6:
        proto = proto / n
    sims = []
    for row in z:
        r = row.astype(np.float32)
        rn = float(np.linalg.norm(r))
        if rn > 1e-6:
            r = r / rn
        sims.append(float(np.dot(r, proto)))
    low = np.quantile(x, float(low_q), axis=0).astype(np.float32)
    high = np.quantile(x, float(high_q), axis=0).astype(np.float32)
    return SupportBand(
        low=low,
        high=high,
        prototype=np.concatenate([mean[0], std[0], proto], axis=0).astype(np.float32),
        similarity_floor=float(np.quantile(np.asarray(sims, dtype=np.float32), float(sim_q))),
        min_progress=float(np.quantile(np.asarray(progresses, dtype=np.float32), 0.2)) if len(progresses) else 0.0,
        counts=int(len(rows)),
    )


def support_match(band: SupportBand | None, feat: np.ndarray, progress: float, *, slack: float) -> tuple[bool, float]:
    if band is None:
        return False, 0.0
    feat = np.asarray(feat, dtype=np.float32)
    dim = feat.shape[0]
    low = np.asarray(band.low, dtype=np.float32) - float(slack)
    high = np.asarray(band.high, dtype=np.float32) + float(slack)
    within = np.all((feat >= low) & (feat <= high))
    mean = np.asarray(band.prototype[:dim], dtype=np.float32)
    std = np.asarray(band.prototype[dim:2 * dim], dtype=np.float32)
    proto = np.asarray(band.prototype[2 * dim:], dtype=np.float32)
    z = (feat - mean) / std
    zn = float(np.linalg.norm(z))
    if zn > 1e-6:
        z = z / zn
    sim = float(np.dot(z.astype(np.float32), proto.astype(np.float32)))
    good = bool(within and sim >= float(band.similarity_floor) and float(progress) >= float(band.min_progress))
    return good, float(sim)


def ensure_standard_field_identity(sample, predictor, field_builder) -> float:
    _, accepted = accepted_cx3d_standard(sample, predictor)
    field = field_builder(sample, predictor)
    return float(np.max(np.abs(np.asarray(field, dtype=np.float32) - np.asarray(accepted, dtype=np.float32))))


__all__ = [
    'BASE_CHOSEN_JSON',
    'PROPOSAL_FEATURE_NAMES',
    'TOKEN_FEATURE_NAMES',
    'SupportBand',
    'TEACHER_CHOSEN_JSON',
    'TreeNode',
    'best_mode_progress',
    'compare_plan_to_baseline',
    'ensure_standard_field_identity',
    'fit_support_band',
    'fit_tree',
    'load_base_params',
    'mode_side',
    'predict_tree',
    'proposal_context',
    'run_hybrid_with_policy',
    'support_match',
    'token_key',
    'tree_to_dict',
]
