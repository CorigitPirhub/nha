from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import apply_class_edit, class_key
from rs_cx24.common import make_haa_policy
from rs_cx30.common import BaseCX28Policy, CX27WatchdogConfig, build_frozen_haa_stack
from rs_cx28.common import set_candidate, watchdog_evidence


@dataclass(frozen=True)
class CX30APORParams:
    maze_revisit_thr: int
    maze_stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    bridge_low: float
    bridge_high: float
    path_openness_thr: float
    focus_gap_thr: float
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[CX30APORParams]:
    return [
        CX30APORParams(2, 18, 0.10, 0.54, 0.09, 0.14, 0.96, 0.35, 0.02, 0.05, 32, 16, 2, 24),
        CX30APORParams(2, 18, 0.10, 0.54, 0.09, 0.145, 0.97, 0.36, 0.02, 0.05, 32, 16, 2, 24),
        CX30APORParams(2, 18, 0.10, 0.54, 0.08, 0.14, 0.96, 0.34, 0.02, 0.05, 32, 16, 2, 24),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Path-Open-Refine', 'disable_por': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX30APORParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'por_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'best_val_loss': float('nan')}


class PORPolicy(BaseCX28Policy):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX30APORParams, memory: dict[str, Any], disable_por: bool = False, enable_diagnostics: bool = False) -> None:
        self.params = params
        self.disable_por = bool(disable_por)
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

    def _should_turn(self) -> bool:
        scene = dict(self.bundle.get('scene', {}))
        bridge = float(scene.get('bridge_diffuse', 0.0))
        path_open = float(scene.get('path_openness', 0.0))
        focus_gap = float(scene.get('focus_gap', 0.0))
        if bridge <= float(self.params.bridge_low) and focus_gap <= float(self.params.focus_gap_thr):
            return True
        if bridge <= float(self.params.bridge_high) and path_open <= float(self.params.path_openness_thr) and focus_gap <= float(self.params.focus_gap_thr):
            return True
        return False

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
        if (not self.disable_por) and str(self.scene_kind) == 'misc' and str(search_state.get('haa_state', 'observe')) in {'candidate', 'commit'}:
            if str(class_key(ctx)) == 'forward_safe|straight' and self._should_turn():
                ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, 'forward_safe|forward_turn', max_macros=int(self.teacher.params.max_macros))
                set_candidate(search_state, 'forward_safe|forward_turn')
                guard_reason = 'misc_por:forward_turn'
        self._diag_record(record, search_state, ctx, evidence, extra={'guard_reason': guard_reason})
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX30APORParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return PORPolicy(case, bundle, field, params, memory, disable_por=bool(ablation.get('disable_por', False)), enable_diagnostics=bool(ablation.get('enable_diagnostics', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX30APORParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return np.asarray(base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, memory['haa_teacher'].memory), dtype=np.float32)


def build_standard_field(sample, predictor, params: CX30APORParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, memory['haa_teacher'].memory).astype(np.float32)
