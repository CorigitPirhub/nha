from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_macro_rescue.stack.base import CXGlobalConfig
from rs_macro_rescue.stack.recoverability import macro_successor_candidates
from rs_macro_rescue.stack.haa import class_key
from rs_macro_rescue.stack import bsr as base_mod
from rs_macro_rescue.mainline.common import CUSTOM_MACRO_REV2, MacroRescueSliceSpec, build_frozen_haa_stack, scene_match


@dataclass(frozen=True)
class MacroRescueParams:
    turn_bridge_max: float
    turn_focus_max: float
    rescue_bridge_max: float
    rescue_focus_min: float
    rescue_path_min: float
    rescue_budget: int
    suppress_bridge_min: float
    suppress_bridge_max: float
    suppress_focus_max: float
    suppress_path_min: float
    stubborn_bridge_min: float
    stubborn_focus_max: float
    stubborn_path_max: float
    macro_bridge_min: float
    macro_bridge_max: float
    macro_focus_min: float
    macro_focus_max: float
    macro_path_min: float
    macro_path_max: float
    maze_revisit_thr: int
    maze_stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[MacroRescueParams]:
    return [
        MacroRescueParams(0.10, 0.36, 0.08, 0.39, 0.99, 1, 0.11, 0.13, 0.31, 0.97, 0.125, 0.34, 0.97, 0.075, 0.095, 0.34, 0.37, 0.97, 1.01, 2, 18, 0.10, 0.54, 0.02, 0.05, 32, 16, 2, 24),
        MacroRescueParams(0.10, 0.36, 0.08, 0.39, 0.99, 1, 0.11, 0.13, 0.31, 0.97, 0.125, 0.34, 0.97, 0.078, 0.095, 0.34, 0.37, 0.97, 1.01, 2, 18, 0.10, 0.54, 0.02, 0.05, 32, 16, 2, 24),
        MacroRescueParams(0.10, 0.36, 0.08, 0.39, 0.99, 1, 0.11, 0.13, 0.31, 0.97, 0.125, 0.34, 0.97, 0.075, 0.098, 0.34, 0.38, 0.97, 1.01, 2, 18, 0.10, 0.54, 0.02, 0.05, 32, 16, 2, 24),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Custom-Macro-Rescue', 'disable_macro_rescue': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: MacroRescueParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'msr_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'best_val_loss': float('nan')}


class MSRPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: MacroRescueParams, memory: dict[str, Any], disable_macro_rescue: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_macro_rescue = bool(disable_macro_rescue)
        self.teacher = memory['haa_teacher']
        base_params = base_mod.CX33BBSRParams(
            maze_revisit_thr=int(params.maze_revisit_thr),
            maze_stall_steps=int(params.maze_stall_steps),
            reverse_required_thr=float(params.reverse_required_thr),
            trap_thr=float(params.trap_thr),
            turn_bridge_max=float(params.turn_bridge_max),
            turn_focus_max=float(params.turn_focus_max),
            rescue_bridge_max=float(params.rescue_bridge_max),
            rescue_focus_min=float(params.rescue_focus_min),
            rescue_path_min=float(params.rescue_path_min),
            rescue_target='escape_border|reverse',
            rescue_budget=int(params.rescue_budget),
            suppress_bridge_min=float(params.suppress_bridge_min),
            suppress_bridge_max=float(params.suppress_bridge_max),
            suppress_focus_max=float(params.suppress_focus_max),
            suppress_path_min=float(params.suppress_path_min),
            suppress_target='uncertain|none',
            stubborn_bridge_min=float(params.stubborn_bridge_min),
            stubborn_focus_max=float(params.stubborn_focus_max),
            stubborn_path_max=float(params.stubborn_path_max),
            stubborn_target='forward_safe|forward_turn',
            progress_eps=float(params.progress_eps),
            commit_fail_margin=float(params.commit_fail_margin),
            failure_ttl=int(params.failure_ttl),
            history_window=int(params.history_window),
            cell_stride=int(params.cell_stride),
            yaw_bins=int(params.yaw_bins),
        )
        base_memory = {'haa_teacher': self.teacher}
        self.base = base_mod.make_policy(base_memory, base_params, case, bundle, self.field, 'cpu', ablation=None)
        self.macro_spec = MacroRescueSliceSpec(
            bridge_min=float(params.macro_bridge_min),
            bridge_max=float(params.macro_bridge_max),
            focus_min=float(params.macro_focus_min),
            focus_max=float(params.macro_focus_max),
            path_min=float(params.macro_path_min),
            path_max=float(params.macro_path_max),
        )

    def start_search(self, planner, start, goal, h_pair, search_state):
        if hasattr(self.base, 'start_search'):
            self.base.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        return self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_macro_rescue or not isinstance(node_ctx, dict):
            return extra
        if str(self.case.get('scenario', '')) != 'parasol_misc':
            return extra
        if str(class_key(node_ctx)) != 'uncertain|none':
            return extra
        if not scene_match(self.bundle, self.macro_spec):
            return extra
        extra_rows = list(extra or [])
        extra_rows.extend(macro_successor_candidates(self.case, planner, record, h_pair, [CUSTOM_MACRO_REV2], max_macros=1))
        return extra_rows

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.base.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if hasattr(self.base, 'complete_expand'):
            return self.base.complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: MacroRescueParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MSRPolicy(case, bundle, field, params, memory, disable_macro_rescue=bool(ablation.get('disable_macro_rescue', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: MacroRescueParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return base_mod.build_nonholonomic_field(case, predictor, cfg, base_mod.CX33BBSRParams(
        maze_revisit_thr=int(params.maze_revisit_thr),
        maze_stall_steps=int(params.maze_stall_steps),
        reverse_required_thr=float(params.reverse_required_thr),
        trap_thr=float(params.trap_thr),
        turn_bridge_max=float(params.turn_bridge_max),
        turn_focus_max=float(params.turn_focus_max),
        rescue_bridge_max=float(params.rescue_bridge_max),
        rescue_focus_min=float(params.rescue_focus_min),
        rescue_path_min=float(params.rescue_path_min),
        rescue_target='escape_border|reverse',
        rescue_budget=int(params.rescue_budget),
        suppress_bridge_min=float(params.suppress_bridge_min),
        suppress_bridge_max=float(params.suppress_bridge_max),
        suppress_focus_max=float(params.suppress_focus_max),
        suppress_path_min=float(params.suppress_path_min),
        suppress_target='uncertain|none',
        stubborn_bridge_min=float(params.stubborn_bridge_min),
        stubborn_focus_max=float(params.stubborn_focus_max),
        stubborn_path_max=float(params.stubborn_path_max),
        stubborn_target='forward_safe|forward_turn',
        progress_eps=float(params.progress_eps),
        commit_fail_margin=float(params.commit_fail_margin),
        failure_ttl=int(params.failure_ttl),
        history_window=int(params.history_window),
        cell_stride=int(params.cell_stride),
        yaw_bins=int(params.yaw_bins),
    ), memory)


def build_standard_field(sample, predictor, params: MacroRescueParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return base_mod.build_standard_field(sample, predictor, base_mod.CX33BBSRParams(
        maze_revisit_thr=int(params.maze_revisit_thr),
        maze_stall_steps=int(params.maze_stall_steps),
        reverse_required_thr=float(params.reverse_required_thr),
        trap_thr=float(params.trap_thr),
        turn_bridge_max=float(params.turn_bridge_max),
        turn_focus_max=float(params.turn_focus_max),
        rescue_bridge_max=float(params.rescue_bridge_max),
        rescue_focus_min=float(params.rescue_focus_min),
        rescue_path_min=float(params.rescue_path_min),
        rescue_target='escape_border|reverse',
        rescue_budget=int(params.rescue_budget),
        suppress_bridge_min=float(params.suppress_bridge_min),
        suppress_bridge_max=float(params.suppress_bridge_max),
        suppress_focus_max=float(params.suppress_focus_max),
        suppress_path_min=float(params.suppress_path_min),
        suppress_target='uncertain|none',
        stubborn_bridge_min=float(params.stubborn_bridge_min),
        stubborn_focus_max=float(params.stubborn_focus_max),
        stubborn_path_max=float(params.stubborn_path_max),
        stubborn_target='forward_safe|forward_turn',
        progress_eps=float(params.progress_eps),
        commit_fail_margin=float(params.commit_fail_margin),
        failure_ttl=int(params.failure_ttl),
        history_window=int(params.history_window),
        cell_stride=int(params.cell_stride),
        yaw_bins=int(params.yaw_bins),
    ), memory)
