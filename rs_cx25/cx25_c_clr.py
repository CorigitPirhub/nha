from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import ObservatoryMixin, trace_feature_vector
from rs_cx25.common import (
    best_support_class,
    build_frozen_cx24_stack,
    build_positive_negative_support,
    calibrate_margin,
    compile_dto_rows,
    make_ccc_policy,
    soft_downgrade_ctx,
)
from rs_cx23 import cx23_c_haa as haa_mod
from rs_cx23.common import apply_class_edit


@dataclass(frozen=True)
class CX25CCLRParams:
    min_hits: int
    support_slack: float
    max_macros: int


def param_grid() -> list[CX25CCLRParams]:
    return [
        CX25CCLRParams(3, 0.22, 3),
        CX25CCLRParams(4, 0.20, 3),
        CX25CCLRParams(5, 0.18, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Calibrated-Review', 'disable_calibrated_review': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX25CCLRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    stack = build_frozen_cx24_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_dto_rows(calib_train_assets, stack, horizon_steps=int(stack.haa_teacher.params.commit_steps + stack.haa_teacher.params.recover_steps), stride=1)
    pos_support, neg_support = build_positive_negative_support(rows, min_hits=int(params.min_hits))
    margin_cfg = calibrate_margin(rows, pos_support, neg_support, slack=float(params.support_slack))
    haa_mod.base_mod.lag_mod.save_meta(out_dir / 'clr_meta.json', {'params': params.__dict__, 'margin_cfg': margin_cfg, 'positive_classes': sorted(pos_support.keys()), 'negative_classes': sorted(neg_support.keys())})
    return {'stack': stack, 'pos_support': pos_support, 'neg_support': neg_support, 'margin_cfg': margin_cfg, 'best_val_loss': float('nan')}


class CLRPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX25CCLRParams, memory: dict[str, Any], disable_calibrated_review: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_calibrated_review = bool(disable_calibrated_review)
        self.stack = memory['stack']
        self.inner = make_ccc_policy(self.stack, case, bundle, self.field)
        self.pos_support = dict(memory.get('pos_support', {}))
        self.neg_support = dict(memory.get('neg_support', {}))
        self.margin_cfg = dict(memory.get('margin_cfg', {}))
        self._diag_init()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict):
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_calibrated_review or not isinstance(node_ctx, dict) or str(search_state.get('haa_state', 'observe')) != 'commit':
            return extra
        feat = trace_feature_vector(node_ctx, search_state, self.case, self.bundle)
        pos_key, pos_sim = best_support_class(self.pos_support, feat, gain_hint=float(node_ctx.get('oracle_gain', 0.0)), slack=float(self.params.support_slack))
        neg_key, neg_sim = best_support_class(self.neg_support, feat, gain_hint=float(node_ctx.get('oracle_gain', 0.0)), slack=float(self.params.support_slack))
        margin = float(pos_sim - neg_sim)
        pass_margin = float(self.margin_cfg.get('pass_margin', 0.0))
        reject_margin = float(self.margin_cfg.get('reject_margin', 0.0))
        if margin < reject_margin:
            edited = apply_class_edit(node_ctx, self.stack.haa_teacher.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
            node_ctx.clear(); node_ctx.update(edited)
            search_state['haa_state'] = 'recover'
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if margin < pass_margin:
            edited = soft_downgrade_ctx(node_ctx, self.stack.haa_teacher.shadow_teacher.lag_teacher, max_macros=int(self.params.max_macros))
            node_ctx.clear(); node_ctx.update(edited)
            search_state['haa_state'] = 'candidate'
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        return extra

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX25CCLRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CLRPolicy(case, bundle, field, params, memory, disable_calibrated_review=bool(ablation.get('disable_calibrated_review', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX25CCLRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = haa_mod.build_nonholonomic_field(case, predictor, cfg, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX25CCLRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return haa_mod.build_standard_field(sample, predictor, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher}).astype(np.float32)
