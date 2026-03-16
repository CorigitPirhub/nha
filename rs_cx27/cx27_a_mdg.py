from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import apply_class_edit
from rs_cx24.common import make_haa_policy
from rs_cx27.common import (
    CX27DiagnosticsMixin,
    CX27WatchdogConfig,
    build_frozen_haa_stack,
    complete_watchdog,
    downgrade_to_uncertain,
    init_watchdog,
    scene_kind,
    set_candidate,
    watchdog_evidence,
)


@dataclass(frozen=True)
class CX27AMDGParams:
    revisit_thr: int
    stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[CX27AMDGParams]:
    return [
        CX27AMDGParams(2, 24, 0.14, 0.58, 0.02, 0.06, 48, 16, 2, 24),
        CX27AMDGParams(2, 18, 0.10, 0.54, 0.02, 0.05, 40, 16, 2, 24),
        CX27AMDGParams(1, 18, 0.08, 0.50, 0.01, 0.04, 32, 12, 2, 20),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Maze-Guard', 'disable_mdg': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX27AMDGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    meta = {'params': params.__dict__}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'mdg_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'best_val_loss': float('nan')}


class MDGPolicy(CX27DiagnosticsMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX27AMDGParams, memory: dict[str, Any], disable_mdg: bool = False, enable_diagnostics: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_mdg = bool(disable_mdg)
        self.teacher = memory['haa_teacher']
        self.inner = make_haa_policy(self.teacher, case, bundle, self.field)
        self.active = bool(scene_kind(case, bundle) == 'maze' and str(case.get('scenario', '')) in {'maze', 'maze_single', 'maze_multi', 'deadend_labyrinth'})
        self.watchdog_cfg = CX27WatchdogConfig(
            cell_stride=int(params.cell_stride),
            yaw_bins=int(params.yaw_bins),
            progress_eps=float(params.progress_eps),
            commit_fail_margin=float(params.commit_fail_margin),
            failure_ttl=int(params.failure_ttl),
            history_window=int(params.history_window),
        )
        self._diag_init(enabled=enable_diagnostics)

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state['cx27_active'] = bool(self.active)
        if self.active:
            init_watchdog(search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        if not bool(search_state.get('cx27_active', False)):
            return ctx
        evidence = watchdog_evidence(search_state, record, self.case, self.bundle, ctx, self.watchdog_cfg)
        guard_reason = 'none'
        if (not self.disable_mdg) and str(evidence['scene_kind']) == 'maze' and str(search_state.get('haa_state', 'observe')) in {'candidate', 'commit'}:
            trigger = bool(
                int(evidence['revisit_count']) >= int(self.params.revisit_thr)
                or int(evidence['stall_steps']) >= int(self.params.stall_steps)
                or bool(evidence['blocklist_hit'])
            )
            if trigger:
                foundation = ctx.get('foundation')
                current_key = str(evidence['class_key'])
                if current_key == 'forward_safe|straight' and foundation is not None and (
                    float(getattr(foundation, 'reverse_required', 0.0)) >= float(self.params.reverse_required_thr)
                    or float(getattr(foundation, 'trap', 0.0)) >= float(self.params.trap_thr)
                ):
                    ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, 'reverse_setup|reverse', max_macros=int(self.teacher.params.max_macros))
                    set_candidate(search_state, 'reverse_setup|reverse')
                    guard_reason = 'maze_reverse_setup'
                else:
                    ctx = downgrade_to_uncertain(search_state, ctx, self.teacher.shadow_teacher.lag_teacher, max_macros=int(self.teacher.params.max_macros))
                    guard_reason = 'maze_abstain'
        self._diag_record(record, search_state, ctx, evidence, extra={'guard_reason': guard_reason})
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if bool(search_state.get('cx27_active', False)) and isinstance(node_ctx, dict):
            complete_watchdog(search_state, record, self.case, self.bundle, node_ctx, self.watchdog_cfg)


def make_policy(memory: dict[str, Any], params: CX27AMDGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MDGPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_mdg=bool(ablation.get('disable_mdg', False)),
        enable_diagnostics=bool(ablation.get('enable_diagnostics', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX27AMDGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return np.asarray(base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, memory['haa_teacher'].memory), dtype=np.float32)


def build_standard_field(sample, predictor, params: CX27AMDGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, memory['haa_teacher'].memory).astype(np.float32)
