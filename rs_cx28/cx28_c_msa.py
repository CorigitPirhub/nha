from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import make_haa_policy
from rs_cx28.common import (
    BaseCX28Policy,
    CX27WatchdogConfig,
    build_frozen_haa_stack,
    class_key,
    class_proxy_score,
    downgrade_to_uncertain,
    misc_blocked,
    misc_scene_bonus,
    misc_shortlist,
    set_candidate,
    set_class_block,
    watchdog_evidence,
)


@dataclass(frozen=True)
class CX28CMSAParams:
    maze_revisit_thr: int
    maze_stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    misc_revisit_thr: int
    misc_churn_thr: float
    misc_loop_thr: float
    scene_bonus_scale: float
    switch_margin: float
    block_ttl: int
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[CX28CMSAParams]:
    return [
        CX28CMSAParams(2, 18, 0.10, 0.54, 1, 0.20, 0.08, 1.0, 0.02, 48, 0.02, 0.05, 32, 16, 2, 24),
        CX28CMSAParams(2, 18, 0.10, 0.54, 1, 0.15, 0.06, 1.2, 0.01, 40, 0.02, 0.05, 32, 16, 2, 24),
        CX28CMSAParams(2, 14, 0.08, 0.50, 1, 0.10, 0.05, 1.4, 0.00, 32, 0.02, 0.04, 28, 16, 2, 24),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Scene-Arbitration', 'disable_scene_arbitration': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX28CMSAParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'msa_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'best_val_loss': float('nan')}


class MSAPolicy(BaseCX28Policy):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX28CMSAParams, memory: dict[str, Any], disable_scene_arbitration: bool = False, enable_diagnostics: bool = False) -> None:
        self.params = params
        self.disable_scene_arbitration = bool(disable_scene_arbitration)
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

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict):
            return ctx
        if not bool(search_state.get('cx28_active', False)):
            return ctx
        evidence = watchdog_evidence(search_state, record, self.case, self.bundle, ctx, self.watchdog_cfg)
        guard_reason = 'none'
        ctx, guard_reason = self._maze_guard(
            ctx,
            search_state,
            evidence,
            revisit_thr=int(self.params.maze_revisit_thr),
            stall_steps=int(self.params.maze_stall_steps),
            reverse_required_thr=float(self.params.reverse_required_thr),
            trap_thr=float(self.params.trap_thr),
        )
        evidence['class_key'] = str(class_key(ctx))
        if (not self.disable_scene_arbitration) and str(self.scene_kind) == 'misc' and str(search_state.get('haa_state', 'observe')) in {'candidate', 'commit'}:
            current_key = str(class_key(ctx))
            trigger = bool(
                bool(evidence.get('blocklist_hit', False))
                or int(evidence.get('recent_failures', 0)) >= 1
                or (
                    int(evidence.get('revisit_count', 0)) >= int(self.params.misc_revisit_thr)
                    and (
                        float(evidence.get('class_churn', 0.0)) >= float(self.params.misc_churn_thr)
                        or float(evidence.get('loop_rate', 0.0)) >= float(self.params.misc_loop_thr)
                    )
                )
            )
            if trigger and planner is not None and h_pair is not None:
                current_score = class_proxy_score(self.case, planner, record, h_pair, self.teacher.shadow_teacher.lag_teacher, current_key, max_macros=int(self.teacher.params.max_macros))
                scored = []
                for target_key in misc_shortlist(self.bundle, current_key):
                    if target_key != current_key and misc_blocked(search_state, target_key):
                        continue
                    score = class_proxy_score(self.case, planner, record, h_pair, self.teacher.shadow_teacher.lag_teacher, target_key, max_macros=int(self.teacher.params.max_macros))
                    score += float(self.params.scene_bonus_scale) * misc_scene_bonus(self.bundle, target_key)
                    scored.append((float(score), str(target_key)))
                scored.sort(reverse=True)
                if scored:
                    best_score, best_key = scored[0]
                    if best_key != current_key and best_score >= current_score + float(self.params.switch_margin):
                        if best_key == 'uncertain|none':
                            ctx = downgrade_to_uncertain(search_state, ctx, self.teacher.shadow_teacher.lag_teacher, max_macros=int(self.teacher.params.max_macros))
                            guard_reason = 'misc_scene_abstain'
                        else:
                            from rs_cx23.common import apply_class_edit
                            ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, best_key, max_macros=int(self.teacher.params.max_macros))
                            set_candidate(search_state, best_key)
                            guard_reason = f'misc_scene:{best_key}'
        self._diag_record(record, search_state, ctx, evidence, extra={'guard_reason': guard_reason})
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if not bool(search_state.get('cx28_active', False)) or not isinstance(node_ctx, dict):
            return
        super().complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)
        if str(self.scene_kind) == 'misc' and bool(search_state.get('cx27_last_commit_failed', False)):
            failed_key = str(search_state.get('cx27_last_failed_key', ''))
            if failed_key:
                set_class_block(search_state, failed_key, int(self.params.block_ttl))


def make_policy(memory: dict[str, Any], params: CX28CMSAParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return MSAPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_scene_arbitration=bool(ablation.get('disable_scene_arbitration', False)),
        enable_diagnostics=bool(ablation.get('enable_diagnostics', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX28CMSAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return np.asarray(base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, memory['haa_teacher'].memory), dtype=np.float32)


def build_standard_field(sample, predictor, params: CX28CMSAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, memory['haa_teacher'].memory).astype(np.float32)
