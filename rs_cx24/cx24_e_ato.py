from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import ObservatoryMixin, build_frozen_haa_teacher, compile_haa_trace_rows, make_haa_policy, observatory_summary
from rs_cx23 import cx23_c_haa as base_mod


@dataclass(frozen=True)
class CX24EATOParams:
    trace_stride: int


def param_grid() -> list[CX24EATOParams]:
    return [CX24EATOParams(1)]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Observatory', 'disable_observatory': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX24EATOParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_haa_trace_rows(calib_train_assets, haa_teacher, horizon_steps=int(haa_teacher.params.commit_steps + haa_teacher.params.recover_steps), stride=int(params.trace_stride))
    summary = observatory_summary(rows)
    base_mod.base_mod.lag_mod.save_meta(out_dir / 'ato_meta.json', {'params': params.__dict__, 'observatory': summary})
    return {'haa_teacher': haa_teacher, 'observatory': summary, 'best_val_loss': float('nan')}


class ATOPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX24EATOParams, memory: dict[str, Any], disable_observatory: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_observatory = bool(disable_observatory)
        self.haa_teacher = memory['haa_teacher']
        self.inner = make_haa_policy(self.haa_teacher, case, bundle, self.field)
        self._diag_init()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if (not self.disable_observatory) and isinstance(ctx, dict):
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX24EATOParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return ATOPolicy(case, bundle, field, params, memory, disable_observatory=bool(ablation.get('disable_observatory', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX24EATOParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, {'shadow_teacher': shadow})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX24EATOParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, {'shadow_teacher': shadow}).astype(np.float32)
