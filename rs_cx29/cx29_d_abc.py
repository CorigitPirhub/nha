from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx21.common import run_hybrid_with_policy
from rs_cx24.common import make_haa_policy
from rs_cx28.common import BaseCX28Policy, CX27WatchdogConfig, build_frozen_haa_stack, class_key, misc_blocked, set_candidate, set_class_block, watchdog_evidence
from rs_cx23.common import apply_class_edit
from rs_cx8.common import load_nonholonomic_contexts
from scripts.evaluate_baselines import _load_nonholonomic_case


AUX_DEV_ROOT = Path('data/benchmark/rs_root_hard_v2/dev')
PARENT_CHOSEN = Path('outputs/rs_p0cx28_d_pilot_v1/chosen.json')


@dataclass(frozen=True)
class CX29DABCParams:
    maze_revisit_thr: int
    maze_stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    misc_revisit_thr: int
    misc_churn_thr: float
    misc_loop_thr: float
    block_ttl: int
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int


def param_grid() -> list[CX29DABCParams]:
    return [
        CX29DABCParams(2, 18, 0.10, 0.54, 1, 0.15, 0.06, 32, 0.02, 0.05, 32, 16, 2, 24),
        CX29DABCParams(2, 18, 0.10, 0.54, 1, 0.12, 0.05, 32, 0.02, 0.05, 32, 16, 2, 24),
        CX29DABCParams(2, 14, 0.08, 0.50, 1, 0.10, 0.05, 28, 0.02, 0.04, 28, 16, 2, 24),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Aux-Bridge-Calib', 'disable_aux_bridge_calib': True}]


def _aux_misc_paths() -> list[Path]:
    out = []
    for path in sorted(AUX_DEV_ROOT.glob('sample_*.npz')):
        try:
            if str(_load_nonholonomic_case(path).get('scenario', '')) == 'parasol_misc':
                out.append(path)
        except Exception:
            continue
    return out


def _parent_params():
    import rs_cx28.cx28_d_mft as parent_mod

    return parent_mod.CX28DMFTParams(**json.loads(PARENT_CHOSEN.read_text(encoding='utf-8'))['params'])


class ABCCalibPolicy(BaseCX28Policy):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX29DABCParams, memory: dict[str, Any], disable_aux_bridge_calib: bool = False, enable_diagnostics: bool = False) -> None:
        self.params = params
        self.disable_aux_bridge_calib = bool(disable_aux_bridge_calib)
        self.bridge_thr = float(memory.get('bridge_thr', 0.1))
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
        if (not self.disable_aux_bridge_calib) and str(self.scene_kind) == 'misc' and str(search_state.get('haa_state', 'observe')) in {'candidate', 'commit'}:
            current_key = str(class_key(ctx))
            scene = dict(self.bundle.get('scene', {}))
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
            if trigger and current_key == 'forward_safe|straight' and not misc_blocked(search_state, 'forward_safe|forward_turn'):
                if float(scene.get('bridge_diffuse', 0.0)) <= float(self.bridge_thr):
                    ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, 'forward_safe|forward_turn', max_macros=int(self.teacher.params.max_macros))
                    set_candidate(search_state, 'forward_safe|forward_turn')
                    guard_reason = f'misc_aux_bridge:{self.bridge_thr:.3f}'
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


def _score_bridge_threshold(aux_assets, memory: dict[str, Any], params: CX29DABCParams, bridge_thr: float, device: str) -> float:
    total = 0.0
    for asset in aux_assets:
        field = build_nonholonomic_field(asset['case'], None, None, params, memory)
        policy = ABCCalibPolicy(asset['case'], asset['bundle'], field, params, dict(memory, bridge_thr=float(bridge_thr)), enable_diagnostics=False)
        plan = run_hybrid_with_policy(asset['case'], field, 20000, successor_policy=policy, record_expanded=False)
        total += float(asset['baseline_result'].expansions) - float(plan.expansions)
    return float(total)


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX29DABCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    aux_paths = _aux_misc_paths()
    aux_assets = load_nonholonomic_contexts(aux_paths, predictor, cfg, tag='cx29:aux-misc')
    parent_params = _parent_params()
    import rs_cx28.cx28_d_mft as parent_mod
    enriched = []
    for asset in aux_assets:
        field = parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, {'haa_teacher': haa_teacher})
        asset = dict(asset)
        asset['field'] = np.asarray(field, dtype=np.float32)
        from rs_cx28.cx28_d_mft import make_policy as parent_make_policy
        parent_pol = parent_make_policy({'haa_teacher': haa_teacher}, parent_params, asset['case'], asset['bundle'], asset['field'], device, ablation=None)
        plan = run_hybrid_with_policy(asset['case'], asset['field'], 20000, successor_policy=parent_pol, record_expanded=False)
        asset['baseline_result'] = plan
        enriched.append(asset)
    memory = {'haa_teacher': haa_teacher}
    candidates = [0.09, 0.10, 0.11, 0.12, 0.13]
    scored = []
    for thr in candidates:
        scored.append((float(_score_bridge_threshold(enriched, memory, params, thr, device)), float(thr)))
    scored.sort(reverse=True)
    bridge_thr = float(scored[0][1]) if scored else 0.10
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'abc_meta.json').write_text(json.dumps({'params': params.__dict__, 'bridge_thr': bridge_thr, 'candidate_scores': scored, 'aux_misc_paths': [str(p) for p in aux_paths]}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'haa_teacher': haa_teacher, 'bridge_thr': bridge_thr, 'best_val_loss': float('nan')}


def make_policy(memory: dict[str, Any], params: CX29DABCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return ABCCalibPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_aux_bridge_calib=bool(ablation.get('disable_aux_bridge_calib', False)),
        enable_diagnostics=bool(ablation.get('enable_diagnostics', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX29DABCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return np.asarray(base_mod.build_nonholonomic_field(case, predictor, cfg, memory['haa_teacher'].params, memory['haa_teacher'].memory), dtype=np.float32)


def build_standard_field(sample, predictor, params: CX29DABCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    from rs_cx23 import cx23_c_haa as base_mod

    return base_mod.build_standard_field(sample, predictor, memory['haa_teacher'].params, memory['haa_teacher'].memory).astype(np.float32)
