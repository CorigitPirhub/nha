from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10.common import build_compact_bundle_feature_vector, default_nonholonomic_field, default_standard_field, scene_feature_vector
from rs_cx10 import cx10_d_las
from rs_cx9.common import select_bottleneck_windows


FEATURE_NAMES = (
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
    'top_gate_bottleneck',
    'top_gate_clearance',
    'top_gate_corridor',
    'top_gate_width',
    'top_gate_inner_mode',
    'top_gate_outer_mode',
    'mean_gate_score',
)


@dataclass(frozen=True)
class CX10DSelectiveParams:
    prob_threshold: float
    sketch_conf_threshold: float
    tree_max_depth: int = 2


@dataclass(frozen=True)
class TreeNode:
    feature_index: int
    threshold: float
    prob: float
    left: 'TreeNode | None' = None
    right: 'TreeNode | None' = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None or self.right is None or self.feature_index < 0


@dataclass(frozen=True)
class GuardDecision:
    safe: bool
    probability: float
    sketch_confidence: float
    reason: str


def param_grid() -> list[CX10DSelectiveParams]:
    return [
        CX10DSelectiveParams(0.55, 0.22),
        CX10DSelectiveParams(0.60, 0.24),
        CX10DSelectiveParams(0.65, 0.26),
        CX10DSelectiveParams(0.70, 0.28),
    ]


def _gini(y: np.ndarray) -> float:
    if y.size <= 0:
        return 0.0
    p = float(np.mean(y))
    return 1.0 - p * p - (1.0 - p) * (1.0 - p)


def _best_split(x: np.ndarray, y: np.ndarray, min_leaf: int = 1) -> tuple[int, float, float] | None:
    parent = _gini(y)
    best = None
    n, d = x.shape
    if n < 2 * int(min_leaf):
        return None
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
            if best is None or gain > best[2] + 1e-12:
                best = (int(feat), float(thr), float(gain))
    return best


def _fit_tree(x: np.ndarray, y: np.ndarray, depth: int, max_depth: int) -> TreeNode:
    prob = float(np.mean(y)) if y.size else 0.0
    if depth >= int(max_depth) or y.size <= 1 or np.all(y == y[0]):
        return TreeNode(feature_index=-1, threshold=0.0, prob=prob)
    split = _best_split(x, y)
    if split is None or split[2] <= 1e-9:
        return TreeNode(feature_index=-1, threshold=0.0, prob=prob)
    feat, thr, _ = split
    left_mask = x[:, feat] <= float(thr)
    right_mask = ~left_mask
    left = _fit_tree(x[left_mask], y[left_mask], depth + 1, max_depth)
    right = _fit_tree(x[right_mask], y[right_mask], depth + 1, max_depth)
    return TreeNode(feature_index=int(feat), threshold=float(thr), prob=prob, left=left, right=right)


def _predict_tree(node: TreeNode, x: np.ndarray) -> float:
    cur = node
    feat = np.asarray(x, dtype=np.float32)
    while cur is not None and not cur.is_leaf:
        cur = cur.left if float(feat[cur.feature_index]) <= float(cur.threshold) else cur.right
    return float(cur.prob if cur is not None else 0.0)


def _tree_to_dict(node: TreeNode) -> dict[str, Any]:
    out = {
        'feature_index': int(node.feature_index),
        'feature_name': FEATURE_NAMES[node.feature_index] if int(node.feature_index) >= 0 else 'leaf',
        'threshold': float(node.threshold),
        'prob': float(node.prob),
    }
    if node.left is not None:
        out['left'] = _tree_to_dict(node.left)
    if node.right is not None:
        out['right'] = _tree_to_dict(node.right)
    return out


def _base_policy_and_feature(
    memory: dict[str, Any],
    base_params: cx10_d_las.CX10DLASParams,
    case: dict[str, Any],
    bundle: dict[str, Any],
    field: np.ndarray,
    device: str,
):
    policy = cx10_d_las.make_policy(memory, base_params, case, bundle, field, device, ablation=None)
    gates = list(getattr(policy, 'gates', [])) if policy is not None else []
    if gates:
        top_gate = max(gates, key=lambda item: float(item.get('score', 0.0)))
        feat = build_compact_bundle_feature_vector(case, bundle, field, top_gate['state'], prev_steer=0.0)
        top_score = float(top_gate.get('score', 0.0))
        top_inner = int(top_gate.get('inner_mode', 0))
        top_outer = int(top_gate.get('outer_mode', 0))
        top_bottleneck = float(feat[19])
        top_clearance = float(feat[6])
        top_corridor = float(feat[9])
        top_width = float(feat[10])
    else:
        top_score = 0.0
        top_inner = 0
        top_outer = 0
        top_bottleneck = 0.0
        top_clearance = 0.0
        top_corridor = 0.0
        top_width = 0.0
    scene_feat = scene_feature_vector(bundle)
    feature = np.asarray([
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
        float(len(gates)),
        float(top_score),
        float(top_bottleneck),
        float(top_clearance),
        float(top_corridor),
        float(top_width),
        float(top_inner),
        float(top_outer),
        float(np.mean([float(g.get('score', 0.0)) for g in gates])) if gates else 0.0,
    ], dtype=np.float32)
    meta = {
        'num_gates': int(len(gates)),
        'top_gate_score': float(top_score),
        'top_gate_inner_mode': int(top_inner),
        'top_gate_outer_mode': int(top_outer),
        'top_gate_bottleneck': float(top_bottleneck),
        'top_gate_clearance': float(top_clearance),
        'top_gate_corridor': float(top_corridor),
        'top_gate_width': float(top_width),
    }
    return policy, feature, meta


def build_case_rows(
    assets: list[dict[str, Any]],
    base_memory: dict[str, Any],
    base_params: cx10_d_las.CX10DLASParams,
    device: str,
) -> list[dict[str, Any]]:
    rows = []
    for asset in assets:
        field = np.asarray(asset['field'], dtype=np.float32)
        _, feature, meta = _base_policy_and_feature(base_memory, base_params, asset['case'], asset['bundle'], field, device)
        rows.append({
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'label': 1 if str(asset['case']['scenario']) == 'narrow_passage' else 0,
            'feature': feature,
            **meta,
        })
    return rows


def fit_variant(
    calib_train_assets,
    calib_val_assets,
    predictor,
    cfg: CXGlobalConfig,
    params: CX10DSelectiveParams,
    out_dir: Path,
    device: str,
    dependencies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    deps = dependencies or {}
    base_params = deps['base_params']
    base_memory = deps['base_memory']
    train_rows = build_case_rows(list(calib_train_assets), base_memory, base_params, device)
    x = np.stack([np.asarray(r['feature'], dtype=np.float32) for r in train_rows], axis=0)
    y = np.asarray([int(r['label']) for r in train_rows], dtype=np.int64)
    tree = _fit_tree(x, y, depth=0, max_depth=int(params.tree_max_depth))
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'train_cases': int(len(train_rows)),
        'positive_cases': int(np.sum(y)),
        'feature_names': list(FEATURE_NAMES),
        'tree': _tree_to_dict(tree),
        'base_params': asdict(base_params),
    }
    (out_dir / 'guard_tree.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'tree': tree, 'train_rows': train_rows, 'best_val_loss': float('nan'), 'base_memory': base_memory, 'base_params': base_params}


def guard_decision(
    memory: dict[str, Any],
    params: CX10DSelectiveParams,
    base_memory: dict[str, Any],
    base_params: cx10_d_las.CX10DLASParams,
    case: dict[str, Any],
    bundle: dict[str, Any],
    field: np.ndarray,
    device: str,
) -> tuple[GuardDecision, np.ndarray, dict[str, Any], Any | None]:
    base_policy, feature, meta = _base_policy_and_feature(base_memory, base_params, case, bundle, field, device)
    prob = _predict_tree(memory['tree'], feature)
    sketch_conf = float(meta.get('top_gate_score', 0.0))
    safe = bool(prob >= float(params.prob_threshold) and sketch_conf >= float(params.sketch_conf_threshold))
    reason = 'safe' if safe else ('low_prob' if prob < float(params.prob_threshold) else 'low_conf')
    return GuardDecision(safe=safe, probability=float(prob), sketch_confidence=float(sketch_conf), reason=reason), feature, meta, base_policy


def make_policy(
    memory: dict[str, Any],
    params: CX10DSelectiveParams,
    case: dict[str, Any],
    bundle: dict[str, Any],
    field: np.ndarray,
    device: str,
    ablation: dict[str, Any] | None = None,
):
    deps = ablation or {}
    base_memory = deps.get('base_memory') or memory.get('base_memory')
    base_params = deps.get('base_params') or memory.get('base_params')
    if base_memory is None or base_params is None:
        raise ValueError('CX10-D-Selective requires base CX10-D memory and params')
    if isinstance(ablation, dict) and ablation.get('disable_guard', False):
        return cx10_d_las.make_policy(base_memory, base_params, case, bundle, field, device, ablation=None)
    decision, _, _, base_policy = guard_decision(memory, params, base_memory, base_params, case, bundle, field, device)
    if not decision.safe:
        return None
    return base_policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX10DSelectiveParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_nonholonomic_field(case, predictor, cfg)


def build_standard_field(sample, predictor, params: CX10DSelectiveParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_standard_field(sample, predictor)
