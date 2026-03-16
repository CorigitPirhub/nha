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
class CX27FMMRParams:
    maze_revisit_thr: int
    maze_stall_steps: int
    misc_revisit_thr: int
    misc_churn_thr: float
    reverse_required_thr: float
    trap_thr: float
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[CX27FMMRParams]:
    return [
        CX27FMMRParams(2, 18, 1, 0.25, 0.08, 0.50, 0.02, 0.04, 32, 16, 2, 24),
        CX27FMMRParams(2, 14, 1, 0.20, 0.06, 0.48, 0.02, 0.04, 28, 16, 2, 24),
        CX27FMMRParams(1, 14, 1, 0.15, 0.05, 0.46, 0.01, 0.03, 24, 12, 2, 20),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-MazeMisc-Repair', 'disable_mmr': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX27FMMRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'mmr_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'best_val_loss': float('nan')}


class MMRPolicy(CX27DiagnosticsMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX27FMMRParams, memory: dict[str, Any], disable_mmr: bool = False, enable_diagnostics: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_mmr = bool(disable_mmr)
        self.teacher = memory['haa_teacher']
        self.inner = make_haa_policy(self.teacher, case, bundle, self.field)
        self.target_scene = str(scene_kind(case, bundle))
        self.active = bool(str(case.get('scenario', '')) in {'maze', 'parasol_misc'} and self.target_scene in {'maze', 'misc'})
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
            search_state['cx27_misc_blocked_classes'] = {}

    def _blocked_misc(self, search_state: dict[str, Any], key: str) -> bool:
        blocked = dict(search_state.get('cx27_misc_blocked_classes', {}))
        return int(blocked.get(str(key), -1)) >= int(search_state.get('popped', 0))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        if not bool(search_state.get('cx27_active', False)) or self.disable_mmr:
            return ctx
        evidence = watchdog_evidence(search_state, record, self.case, self.bundle, ctx, self.watchdog_cfg)
        current_key = str(evidence['class_key'])
        foundation = ctx.get('foundation')
        guard_reason = 'none'
        if str(search_state.get('haa_state', 'observe')) in {'candidate', 'commit'} and current_key == 'forward_safe|straight':
            if self.target_scene == 'maze':
                trigger = bool(
                    bool(evidence['blocklist_hit'])
                    or int(evidence['revisit_count']) >= int(self.params.maze_revisit_thr)
                    or int(evidence['stall_steps']) >= int(self.params.maze_stall_steps)
                )
                if trigger:
                    if foundation is not None and (
                        float(getattr(foundation, 'reverse_required', 0.0)) >= float(self.params.reverse_required_thr)
                        or float(getattr(foundation, 'trap', 0.0)) >= float(self.params.trap_thr)
                    ):
                        ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, 'reverse_setup|reverse', max_macros=int(self.teacher.params.max_macros))
                        set_candidate(search_state, 'reverse_setup|reverse')
                        guard_reason = 'maze_reverse_setup'
                    else:
                        ctx = downgrade_to_uncertain(search_state, ctx, self.teacher.shadow_teacher.lag_teacher, max_macros=int(self.teacher.params.max_macros))
                        guard_reason = 'maze_abstain'
            elif self.target_scene == 'misc':
                trigger = bool(
                    self._blocked_misc(search_state, current_key)
                    or bool(evidence['blocklist_hit'])
                    or int(evidence['recent_failures']) >= 1
                    or (
                        int(evidence['revisit_count']) >= int(self.params.misc_revisit_thr)
                        and float(evidence['class_churn']) >= float(self.params.misc_churn_thr)
                    )
                )
                if trigger:
                    if not self._blocked_misc(search_state, 'reverse_setup|reverse'):
                        ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, 'reverse_setup|reverse', max_macros=int(self.teacher.params.max_macros))
                        set_candidate(search_state, 'reverse_setup|reverse')
                        guard_reason = 'misc_force_reverse'
                    else:
                        ctx = downgrade_to_uncertain(search_state, ctx, self.teacher.shadow_teacher.lag_teacher, max_macros=int(self.teacher.params.max_macros))
                        guard_reason = 'misc_abstain'
        elif self.target_scene == 'misc' and str(search_state.get('haa_state', 'observe')) in {'candidate', 'commit'} and current_key == 'reverse_setup|reverse':
            if self._blocked_misc(search_state, current_key):
                ctx = downgrade_to_uncertain(search_state, ctx, self.teacher.shadow_teacher.lag_teacher, max_macros=int(self.teacher.params.max_macros))
                guard_reason = 'misc_reverse_blocked'
        self._diag_record(record, search_state, ctx, evidence, extra={'guard_reason': guard_reason, 'misc_forward_blocked': int(self._blocked_misc(search_state, 'forward_safe|straight')), 'misc_reverse_blocked': int(self._blocked_misc(search_state, 'reverse_setup|reverse'))})
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if not bool(search_state.get('cx27_active', False)) or not isinstance(node_ctx, dict):
            return
        complete_watchdog(search_state, record, self.case, self.bundle, node_ctx, self.watchdog_cfg)
        if self.target_scene == 'misc' and bool(search_state.get('cx27_last_commit_failed', False)):
            blocked = dict(search_state.get('cx27_misc_blocked_classes', {}))
            failed_key = str(search_state.get('cx27_last_failed_key', ''))
            blocked[failed_key] = int(search_state.get('popped', 0)) + int(self.params.failure_ttl)
            search_state['cx27_misc_blocked_classes'] = blocked


def make_policy(memory: dict[str, Any], params: CX27FMMRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MMRPolicy(case, bundle, field, params, memory, disable_mmr=bool(ablation.get('disable_mmr', False)), enable_diagnostics=bool(ablation.get('enable_diagnostics', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX27FMMRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return np.asarray(base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, memory['haa_teacher'].memory), dtype=np.float32)


def build_standard_field(sample, predictor, params: CX27FMMRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, memory['haa_teacher'].memory).astype(np.float32)
