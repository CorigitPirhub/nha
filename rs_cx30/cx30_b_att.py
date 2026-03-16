from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import apply_class_edit, class_key
from rs_cx24.common import make_haa_policy
from rs_cx30.common import (
    AUX_FEATURE_NAMES,
    BaseCX28Policy,
    CX27WatchdogConfig,
    aux_misc_paths,
    build_frozen_haa_stack,
    compile_aux_trigger_tree,
    predict_tree,
    scene_feature_vector,
    simple_zero_h_pair,
    trigger_feature_vector,
    tree_to_dict,
)
from rs_cx28.common import set_candidate, watchdog_evidence
from rs_cx8.common import load_nonholonomic_contexts
from rs_cx29 import cx29_d_abc as parent_mod
from rs_cx21.common import run_hybrid_with_policy


@dataclass(frozen=True)
class CX30BATTParams:
    maze_revisit_thr: int
    maze_stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    tree_depth: int
    gain_margin: float
    prob_thr: float
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[CX30BATTParams]:
    return [
        CX30BATTParams(2, 18, 0.10, 0.54, 2, 0.02, 0.50, 0.02, 0.05, 32, 16, 2, 24),
        CX30BATTParams(2, 18, 0.10, 0.54, 2, 0.01, 0.45, 0.02, 0.05, 32, 16, 2, 24),
        CX30BATTParams(2, 18, 0.10, 0.54, 3, 0.01, 0.40, 0.02, 0.05, 32, 16, 2, 24),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Aux-Tree', 'disable_aux_tree': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX30BATTParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    aux_paths = aux_misc_paths()
    aux_ctx = load_nonholonomic_contexts(aux_paths, predictor, cfg, tag='cx30:aux-tree')
    parent_params = parent_mod.CX29DABCParams(**json.loads(Path('outputs/rs_p0cx29_d_pilot_v1/chosen.json').read_text())['params'])
    enriched = []
    for asset in aux_ctx:
        asset = dict(asset)
        field = parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, {'haa_teacher': haa_teacher, 'bridge_thr': 0.13})
        asset['field'] = np.asarray(field, dtype=np.float32)
        parent_policy = parent_mod.make_policy({'haa_teacher': haa_teacher, 'bridge_thr': 0.13}, parent_params, asset['case'], asset['bundle'], asset['field'], device, ablation=None)
        asset['baseline_result'] = run_hybrid_with_policy(asset['case'], asset['field'], 20000, successor_policy=parent_policy, record_expanded=False)
        enriched.append(asset)
    tree_model = compile_aux_trigger_tree(
        enriched,
        parent_mod.make_policy,
        haa_teacher,
        {'haa_teacher': haa_teacher, 'bridge_thr': 0.13},
        max_depth=int(params.tree_depth),
        gain_margin=float(params.gain_margin),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {'params': params.__dict__, 'tree': tree_to_dict(tree_model.tree, AUX_FEATURE_NAMES) if tree_model is not None else None, 'prob_thr': float(params.prob_thr), 'samples': int(tree_model.samples) if tree_model is not None else 0}
    (out_dir / 'att_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'tree_model': tree_model, 'best_val_loss': float('nan')}


class ATTPolicy(BaseCX28Policy):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX30BATTParams, memory: dict[str, Any], disable_aux_tree: bool = False, enable_diagnostics: bool = False) -> None:
        self.params = params
        self.disable_aux_tree = bool(disable_aux_tree)
        self.tree_model = memory.get('tree_model')
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
            ctx, search_state, evidence,
            revisit_thr=int(self.params.maze_revisit_thr),
            stall_steps=int(self.params.maze_stall_steps),
            reverse_required_thr=float(self.params.reverse_required_thr),
            trap_thr=float(self.params.trap_thr),
        )
        if (not self.disable_aux_tree) and str(self.scene_kind) == 'misc' and self.tree_model is not None and str(search_state.get('haa_state', 'observe')) in {'candidate', 'commit'}:
            if str(class_key(ctx)) == 'forward_safe|straight':
                feat = trigger_feature_vector(self.bundle, ctx, evidence)
                prob = float(predict_tree(self.tree_model.tree, feat))
                if prob >= float(self.params.prob_thr):
                    ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, 'forward_safe|forward_turn', max_macros=int(self.teacher.params.max_macros))
                    set_candidate(search_state, 'forward_safe|forward_turn')
                    guard_reason = f'misc_aux_tree:{prob:.3f}'
        self._diag_record(record, search_state, ctx, evidence, extra={'guard_reason': guard_reason})
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX30BATTParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return ATTPolicy(case, bundle, field, params, memory, disable_aux_tree=bool(ablation.get('disable_aux_tree', False)), enable_diagnostics=bool(ablation.get('enable_diagnostics', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX30BATTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return np.asarray(base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, memory['haa_teacher'].memory), dtype=np.float32)


def build_standard_field(sample, predictor, params: CX30BATTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, memory['haa_teacher'].memory).astype(np.float32)
