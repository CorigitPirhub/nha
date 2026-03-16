from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import (
    adoption_feature_vector,
    apply_class_edit,
    best_support_class,
    build_class_support,
    build_frozen_shadow_teacher,
    compile_shadow_rows,
    make_shadow_policy,
    shadow_prepare,
)
from rs_cx22 import cx22_d_sha as base_mod


@dataclass(frozen=True)
class CX23BCADParams:
    min_hits: int
    suppress_margin: float
    promote_margin: float
    support_slack: float
    max_macros: int


def param_grid() -> list[CX23BCADParams]:
    return [
        CX23BCADParams(3, 0.02, 0.02, 0.20, 3),
        CX23BCADParams(4, 0.01, 0.03, 0.18, 3),
        CX23BCADParams(5, 0.00, 0.04, 0.16, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Contrastive', 'disable_contrastive': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX23BCADParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    shadow_teacher = build_frozen_shadow_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_shadow_rows(calib_train_assets, shadow_teacher, horizon_steps=int(shadow_teacher.lag_teacher.params.horizon_steps), stride=1)
    pos_support = build_class_support(rows, positive=True, min_hits=int(params.min_hits))
    neg_support = build_class_support(rows, positive=False, min_hits=int(params.min_hits))
    base_mod.lag_mod.save_meta(
        out_dir / 'cad_meta.json',
        {
            'params': params.__dict__,
            'positive_classes': sorted(pos_support.keys()),
            'negative_classes': sorted(neg_support.keys()),
        },
    )
    return {'shadow_teacher': shadow_teacher, 'pos_support': pos_support, 'neg_support': neg_support, 'best_val_loss': float('nan')}


class CADPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX23BCADParams, memory: dict[str, Any], disable_contrastive: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_contrastive = bool(disable_contrastive)
        self.shadow_teacher = memory['shadow_teacher']
        self.inner = make_shadow_policy(self.shadow_teacher, case, bundle, self.field)
        self.pos_support = dict(memory.get('pos_support', {}))
        self.neg_support = dict(memory.get('neg_support', {}))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = shadow_prepare(self.inner, (float(record.x), float(record.y), float(record.yaw)))
        if self.disable_contrastive:
            return ctx
        feat = adoption_feature_vector(self.case, self.bundle, ctx)
        gain_hint = float(ctx.get('oracle_gain', 0.0))
        pos_key, pos_sim = best_support_class(self.pos_support, feat, gain_hint=gain_hint, slack=float(self.params.support_slack))
        neg_key, neg_sim = best_support_class(self.neg_support, feat, gain_hint=gain_hint, slack=float(self.params.support_slack))
        if float(neg_sim) > float(pos_sim) + float(self.params.suppress_margin):
            return apply_class_edit(ctx, self.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
        if pos_key != 'uncertain|none' and float(pos_sim) >= float(neg_sim) + float(self.params.promote_margin):
            return apply_class_edit(ctx, self.shadow_teacher.lag_teacher, pos_key, max_macros=int(self.params.max_macros))
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX23BCADParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CADPolicy(case, bundle, field, params, memory, disable_contrastive=bool(ablation.get('disable_contrastive', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX23BCADParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, memory['shadow_teacher'].params, memory['shadow_teacher'].memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX23BCADParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return base_mod.build_standard_field(sample, predictor, memory['shadow_teacher'].params, memory['shadow_teacher'].memory).astype(np.float32)
