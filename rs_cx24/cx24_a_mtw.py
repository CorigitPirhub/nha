from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import (
    AUTO_STATE_INDEX,
    ObservatoryMixin,
    TRACE_FEATURE_NAMES,
    apply_class_edit,
    best_band_match,
    build_frozen_haa_teacher,
    build_state_support,
    compile_haa_trace_rows,
    make_haa_policy,
    observatory_summary,
    trace_feature_vector,
)
from rs_cx23 import cx23_c_haa as base_mod


@dataclass(frozen=True)
class CX24AMTWParams:
    min_hits: int
    support_slack: float
    trap_sim_margin: float
    max_macros: int


def param_grid() -> list[CX24AMTWParams]:
    return [
        CX24AMTWParams(3, 0.18, 0.00, 3),
        CX24AMTWParams(4, 0.16, 0.02, 3),
        CX24AMTWParams(4, 0.14, 0.05, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Trap-Witness', 'disable_trap_witness': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX24AMTWParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_haa_trace_rows(calib_train_assets, haa_teacher, horizon_steps=int(haa_teacher.params.commit_steps + haa_teacher.params.recover_steps), stride=1)
    trap_support = build_state_support(rows, predicate=lambda r: str(r['scenario']) == 'maze' and str(r['auto_state']) == 'commit' and float(r['future_gain']) <= 0.0, min_hits=int(params.min_hits))
    escape_support = build_state_support(rows, predicate=lambda r: float(r['future_gain']) > 0.0 and str(r['auto_state']) == 'commit', min_hits=int(params.min_hits))
    base_mod.base_mod.lag_mod.save_meta(
        out_dir / 'mtw_meta.json',
        {
            'params': params.__dict__,
            'trace_feature_names': TRACE_FEATURE_NAMES,
            'observatory': observatory_summary(rows),
            'trap_keys': sorted(trap_support.keys()),
            'escape_keys': sorted(escape_support.keys()),
        },
    )
    return {'haa_teacher': haa_teacher, 'trap_support': trap_support, 'escape_support': escape_support, 'best_val_loss': float('nan')}


class MTWPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX24AMTWParams, memory: dict[str, Any], disable_trap_witness: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_trap_witness = bool(disable_trap_witness)
        self.haa_teacher = memory['haa_teacher']
        self.inner = make_haa_policy(self.haa_teacher, case, bundle, self.field)
        self.trap_support = dict(memory.get('trap_support', {}))
        self.escape_support = dict(memory.get('escape_support', {}))
        self._diag_init()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        if not self.disable_trap_witness:
            feat = trace_feature_vector(ctx, search_state, self.case, self.bundle)
            trap_key, trap_sim = best_band_match(self.trap_support, feat, gain_hint=float(ctx.get('oracle_gain', 0.0)), slack=float(self.params.support_slack))
            escape_key, escape_sim = best_band_match(self.escape_support, feat, gain_hint=float(ctx.get('oracle_gain', 0.0)), slack=float(self.params.support_slack))
            if trap_key != 'uncertain|none' and float(trap_sim) >= float(escape_sim) + float(self.params.trap_sim_margin):
                ctx = apply_class_edit(ctx, self.haa_teacher.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
                search_state['haa_state'] = 'recover'
        self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX24AMTWParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MTWPolicy(case, bundle, field, params, memory, disable_trap_witness=bool(ablation.get('disable_trap_witness', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX24AMTWParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, {'shadow_teacher': shadow})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX24AMTWParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, {'shadow_teacher': shadow}).astype(np.float32)
