from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import (
    ADOPTION_FEATURE_NAMES,
    TreeNode,
    adoption_feature_vector,
    apply_class_edit,
    build_frozen_shadow_teacher,
    compile_shadow_rows,
    fit_tree,
    frequent_positive_classes,
    make_shadow_policy,
    predict_tree,
    shadow_prepare,
    tree_to_dict,
)
from rs_cx22 import cx22_d_sha as base_mod


@dataclass(frozen=True)
class CX23ASADParams:
    max_depth: int
    min_hits: int
    min_gain: float
    prob_thr: float
    max_macros: int


def param_grid() -> list[CX23ASADParams]:
    return [
        CX23ASADParams(2, 4, 0.02, 0.55, 2),
        CX23ASADParams(3, 4, 0.01, 0.50, 3),
        CX23ASADParams(3, 3, 0.00, 0.45, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Distill', 'disable_distill': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX23ASADParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    shadow_teacher = build_frozen_shadow_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_shadow_rows(calib_train_assets, shadow_teacher, horizon_steps=int(shadow_teacher.lag_teacher.params.horizon_steps), stride=1)
    classes = frequent_positive_classes(rows, min_hits=int(params.min_hits), min_gain=float(params.min_gain))
    x = np.stack([np.asarray(r['feature'], dtype=np.float32) for r in rows], axis=0)
    active_y = np.asarray([1 if str(r['class_key']) in classes else 0 for r in rows], dtype=np.int64)
    active_tree = fit_tree(x, active_y, max_depth=int(params.max_depth))
    class_trees: dict[str, TreeNode] = {}
    for key in classes:
        y = np.asarray([1 if str(r['class_key']) == str(key) else 0 for r in rows], dtype=np.int64)
        class_trees[str(key)] = fit_tree(x, y, max_depth=int(params.max_depth))
    base_mod.lag_mod.save_meta(
        out_dir / 'sad_meta.json',
        {
            'params': params.__dict__,
            'classes': classes,
            'active_tree': tree_to_dict(active_tree, ADOPTION_FEATURE_NAMES),
            'class_trees': {k: tree_to_dict(v, ADOPTION_FEATURE_NAMES) for k, v in class_trees.items()},
        },
    )
    return {'shadow_teacher': shadow_teacher, 'classes': classes, 'active_tree': active_tree, 'class_trees': class_trees, 'best_val_loss': float('nan')}


class SADPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX23ASADParams, memory: dict[str, Any], disable_distill: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_distill = bool(disable_distill)
        self.shadow_teacher = memory['shadow_teacher']
        self.inner = make_shadow_policy(self.shadow_teacher, case, bundle, self.field)
        self.classes = list(memory.get('classes', []))
        self.active_tree = memory.get('active_tree')
        self.class_trees = dict(memory.get('class_trees', {}))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = shadow_prepare(self.inner, (float(record.x), float(record.y), float(record.yaw)))
        if self.disable_distill:
            return ctx
        feat = adoption_feature_vector(self.case, self.bundle, ctx)
        active_prob = float(predict_tree(self.active_tree, feat)) if self.active_tree is not None else 0.0
        if active_prob < float(self.params.prob_thr):
            return apply_class_edit(ctx, self.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
        best_key = 'uncertain|none'
        best_prob = -1.0
        for key in self.classes:
            tree = self.class_trees.get(str(key))
            if tree is None:
                continue
            prob = float(predict_tree(tree, feat))
            if prob > best_prob:
                best_prob = prob
                best_key = str(key)
        if best_key == 'uncertain|none':
            return apply_class_edit(ctx, self.shadow_teacher.lag_teacher, best_key, max_macros=int(self.params.max_macros))
        return apply_class_edit(ctx, self.shadow_teacher.lag_teacher, best_key, max_macros=int(self.params.max_macros))

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX23ASADParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return SADPolicy(case, bundle, field, params, memory, disable_distill=bool(ablation.get('disable_distill', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX23ASADParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, memory['shadow_teacher'].params, memory['shadow_teacher'].memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX23ASADParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return base_mod.build_standard_field(sample, predictor, memory['shadow_teacher'].params, memory['shadow_teacher'].memory).astype(np.float32)
