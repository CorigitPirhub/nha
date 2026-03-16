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
    set_candidate,
    watchdog_evidence,
)


@dataclass(frozen=True)
class CX27BTADParams:
    misc_revisit_thr: int
    churn_thr: float
    loop_thr: float
    failure_thr: int
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[CX27BTADParams]:
    return [
        CX27BTADParams(2, 0.55, 0.15, 1, 0.02, 0.05, 40, 16, 2, 24),
        CX27BTADParams(2, 0.45, 0.12, 1, 0.02, 0.04, 32, 16, 2, 24),
        CX27BTADParams(1, 0.40, 0.10, 1, 0.01, 0.04, 28, 12, 2, 20),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Misc-Dampener', 'disable_tad': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX27BTADParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'tad_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'best_val_loss': float('nan')}


class TADPolicy(CX27DiagnosticsMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX27BTADParams, memory: dict[str, Any], disable_tad: bool = False, enable_diagnostics: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_tad = bool(disable_tad)
        self.teacher = memory['haa_teacher']
        self.inner = make_haa_policy(self.teacher, case, bundle, self.field)
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
        init_watchdog(search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        evidence = watchdog_evidence(search_state, record, self.case, self.bundle, ctx, self.watchdog_cfg)
        guard_reason = 'none'
        current_key = str(evidence['class_key'])
        if (not self.disable_tad) and str(evidence['scene_kind']) == 'misc' and str(search_state.get('haa_state', 'observe')) in {'candidate', 'commit'}:
            trigger = bool(
                bool(evidence['blocklist_hit'])
                or int(evidence['recent_failures']) >= int(self.params.failure_thr)
                or (
                    int(evidence['revisit_count']) >= int(self.params.misc_revisit_thr)
                    and (float(evidence['class_churn']) >= float(self.params.churn_thr) or float(evidence['loop_rate']) >= float(self.params.loop_thr))
                )
            )
            if trigger and current_key == 'forward_safe|straight':
                if str(search_state.get('haa_state', 'observe')) == 'commit' and not bool(evidence['blocklist_hit']):
                    ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, current_key, max_macros=max(int(self.teacher.params.max_macros) - 1, 1))
                    set_candidate(search_state, current_key)
                    guard_reason = 'misc_soft_commit'
                else:
                    ctx = downgrade_to_uncertain(search_state, ctx, self.teacher.shadow_teacher.lag_teacher, max_macros=int(self.teacher.params.max_macros))
                    guard_reason = 'misc_abstain'
        self._diag_record(record, search_state, ctx, evidence, extra={'guard_reason': guard_reason})
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if isinstance(node_ctx, dict):
            complete_watchdog(search_state, record, self.case, self.bundle, node_ctx, self.watchdog_cfg)


def make_policy(memory: dict[str, Any], params: CX27BTADParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return TADPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_tad=bool(ablation.get('disable_tad', False)),
        enable_diagnostics=bool(ablation.get('enable_diagnostics', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX27BTADParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return np.asarray(base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, memory['haa_teacher'].memory), dtype=np.float32)


def build_standard_field(sample, predictor, params: CX27BTADParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, memory['haa_teacher'].memory).astype(np.float32)
