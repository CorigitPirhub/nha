from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import apply_class_edit, class_key
from rs_cx24.common import make_haa_policy
from rs_cx28.common import set_candidate, watchdog_evidence
from rs_cx33.common import BaseCX28Policy, CX27WatchdogConfig, build_frozen_haa_stack


@dataclass(frozen=True)
class CX33BBSRParams:
    maze_revisit_thr: int
    maze_stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    turn_bridge_max: float
    turn_focus_max: float
    rescue_bridge_max: float
    rescue_focus_min: float
    rescue_path_min: float
    rescue_target: str
    rescue_budget: int
    suppress_bridge_min: float
    suppress_bridge_max: float
    suppress_focus_max: float
    suppress_path_min: float
    suppress_target: str
    stubborn_bridge_min: float
    stubborn_focus_max: float
    stubborn_path_max: float
    stubborn_target: str
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[CX33BBSRParams]:
    return [
        CX33BBSRParams(2, 18, 0.10, 0.54, 0.10, 0.36, 0.08, 0.39, 0.99, 'escape_border|reverse', 1, 0.11, 0.13, 0.31, 0.97, 'uncertain|none', 0.13, 0.33, 0.97, 'forward_safe|forward_turn', 0.02, 0.05, 32, 16, 2, 24),
        CX33BBSRParams(2, 18, 0.10, 0.54, 0.10, 0.36, 0.08, 0.39, 0.99, 'escape_border|reverse', 1, 0.11, 0.13, 0.31, 0.97, 'uncertain|none', 0.13, 0.33, 0.96, 'forward_safe|forward_turn', 0.02, 0.05, 32, 16, 2, 24),
        CX33BBSRParams(2, 18, 0.10, 0.54, 0.10, 0.36, 0.08, 0.39, 0.99, 'escape_border|reverse', 1, 0.11, 0.13, 0.31, 0.97, 'uncertain|none', 0.125, 0.34, 0.97, 'forward_safe|forward_turn', 0.02, 0.05, 32, 16, 2, 24),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Stubborn-Uncertain-Turn', 'disable_stubborn_uncertain_turn': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX33BBSRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx33_b_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'best_val_loss': float('nan')}


class BSRPolicy(BaseCX28Policy):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX33BBSRParams, memory: dict[str, Any], disable_stubborn_uncertain_turn: bool = False, enable_diagnostics: bool = False) -> None:
        self.params = params
        self.disable_stubborn_uncertain_turn = bool(disable_stubborn_uncertain_turn)
        teacher = memory['haa_teacher']
        self.inner = make_haa_policy(teacher, case, bundle, np.asarray(field, dtype=np.float32))
        watchdog_cfg = CX27WatchdogConfig(
            cell_stride=int(params.cell_stride),
            yaw_bins=int(params.yaw_bins),
            progress_eps=float(params.progress_eps),
            commit_fail_margin=float(params.commit_fail_margin),
            failure_ttl=int(params.failure_ttl),
            history_window=int(params.history_window),
        )
        self._init_core(case, bundle, field, teacher, watchdog_cfg, enable_diagnostics)
        self.scene = dict(bundle.get('scene', {}))

    def start_search(self, planner, start, goal, h_pair, search_state):
        super().start_search(planner, start, goal, h_pair, search_state)
        if bool(search_state.get('cx28_active', False)):
            search_state['cx33_rescue_count'] = 0

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        if not bool(search_state.get('cx28_active', False)):
            return ctx
        evidence = watchdog_evidence(search_state, record, self.case, self.bundle, ctx, self.watchdog_cfg)
        guard_reason = 'none'
        ctx, guard_reason = self._maze_guard(
            ctx, search_state, evidence,
            revisit_thr=int(self.params.maze_revisit_thr),
            stall_steps=int(self.params.maze_stall_steps),
            reverse_required_thr=float(self.params.reverse_required_thr),
            trap_thr=float(self.params.trap_thr),
        )
        bridge = float(self.scene.get('bridge_diffuse', 0.0))
        focus = float(self.scene.get('focus_gap', 0.0))
        path_open = float(self.scene.get('path_openness', 0.0))
        key = str(class_key(ctx))
        if str(self.case.get('scenario', '')) == 'parasol_misc':
            if key == 'forward_safe|straight' and bridge <= float(self.params.turn_bridge_max) and focus <= float(self.params.turn_focus_max):
                ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, 'forward_safe|forward_turn', max_macros=int(self.teacher.params.max_macros))
                set_candidate(search_state, 'forward_safe|forward_turn')
                guard_reason = 'misc_turn_slice'
            elif key == 'escape_border|reverse' and float(self.params.suppress_bridge_min) <= bridge <= float(self.params.suppress_bridge_max) and focus <= float(self.params.suppress_focus_max) and path_open >= float(self.params.suppress_path_min):
                ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, str(self.params.suppress_target), max_macros=int(self.teacher.params.max_macros))
                if str(self.params.suppress_target) != 'uncertain|none':
                    set_candidate(search_state, str(self.params.suppress_target))
                guard_reason = f'misc_suppress:{self.params.suppress_target}'
            elif key == 'uncertain|none' and bridge <= float(self.params.rescue_bridge_max) and focus >= float(self.params.rescue_focus_min) and path_open >= float(self.params.rescue_path_min) and int(search_state.get('cx33_rescue_count', 0)) < int(self.params.rescue_budget):
                ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, str(self.params.rescue_target), max_macros=int(self.teacher.params.max_macros))
                set_candidate(search_state, str(self.params.rescue_target))
                search_state['cx33_rescue_count'] = int(search_state.get('cx33_rescue_count', 0)) + 1
                guard_reason = f'misc_rescue:{self.params.rescue_target}'
            elif (not self.disable_stubborn_uncertain_turn) and key == 'uncertain|none' and bridge >= float(self.params.stubborn_bridge_min) and focus <= float(self.params.stubborn_focus_max) and path_open <= float(self.params.stubborn_path_max):
                ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, str(self.params.stubborn_target), max_macros=int(self.teacher.params.max_macros))
                set_candidate(search_state, str(self.params.stubborn_target))
                guard_reason = f'misc_stubborn:{self.params.stubborn_target}'
        self._diag_record(record, search_state, ctx, evidence, extra={'guard_reason': guard_reason})
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX33BBSRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return BSRPolicy(case, bundle, field, params, memory, disable_stubborn_uncertain_turn=bool(ablation.get('disable_stubborn_uncertain_turn', False)), enable_diagnostics=bool(ablation.get('enable_diagnostics', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX33BBSRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod
    return np.asarray(base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, memory['haa_teacher'].memory), dtype=np.float32)


def build_standard_field(sample, predictor, params: CX33BBSRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod
    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, memory['haa_teacher'].memory).astype(np.float32)
