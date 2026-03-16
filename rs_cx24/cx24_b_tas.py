from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import ObservatoryMixin, apply_class_edit, best_band_match, build_frozen_haa_teacher, build_state_support, compile_haa_trace_rows, make_haa_policy, trace_feature_vector
from rs_cx22 import cx22_d_sha as base_mod


@dataclass(frozen=True)
class CX24BTASParams:
    min_hits: int
    tail_thr: float
    support_slack: float
    max_macros: int


def param_grid() -> list[CX24BTASParams]:
    return [
        CX24BTASParams(3, 0.15, 0.22, 3),
        CX24BTASParams(4, 0.20, 0.18, 3),
        CX24BTASParams(5, 0.25, 0.16, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Tail-Shield', 'disable_tail_shield': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX24BTASParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_haa_trace_rows(calib_train_assets, haa_teacher, horizon_steps=int(haa_teacher.params.commit_steps + haa_teacher.params.recover_steps), stride=1)
    tail_support = build_state_support(
        rows,
        predicate=lambda r: float(r['future_gain']) <= 0.0 and (float(r['trace_feature'][7]) < float(params.tail_thr) or float(r['trace_feature'][10]) > 0.5),
        min_hits=int(params.min_hits),
    )
    base_mod.lag_mod.save_meta(out_dir / 'tas_meta.json', {'params': params.__dict__, 'tail_keys': sorted(tail_support.keys())})
    return {'haa_teacher': haa_teacher, 'tail_support': tail_support, 'best_val_loss': float('nan')}


class TASPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX24BTASParams, memory: dict[str, Any], disable_tail_shield: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_tail_shield = bool(disable_tail_shield)
        self.haa_teacher = memory['haa_teacher']
        self.inner = make_haa_policy(self.haa_teacher, case, bundle, self.field)
        self.tail_support = dict(memory.get('tail_support', {}))
        self._diag_init()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict) and not self.disable_tail_shield:
            feat = trace_feature_vector(ctx, search_state, self.case, self.bundle)
            tail_key, tail_sim = best_band_match(self.tail_support, feat, gain_hint=float(ctx.get('oracle_gain', 0.0)), slack=float(self.params.support_slack))
            if tail_key != 'uncertain|none':
                ctx = apply_class_edit(ctx, self.haa_teacher.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
                search_state['haa_state'] = 'recover'
        if isinstance(ctx, dict):
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX24BTASParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return TASPolicy(case, bundle, field, params, memory, disable_tail_shield=bool(ablation.get('disable_tail_shield', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX24BTASParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, shadow.params, shadow.memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX24BTASParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    return base_mod.build_standard_field(sample, predictor, shadow.params, shadow.memory).astype(np.float32)
