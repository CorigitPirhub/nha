from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import class_key
from rs_cx27.common import coarse_state_key
from rs_cx34 import cx34_a_msr as parent_mod


@dataclass(frozen=True)
class CX42ADCLParams:
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
    review_cell_stride: int
    review_yaw_bins: int


def param_grid() -> list[CX42ADCLParams]:
    return [
        CX42ADCLParams(**dict(params.__dict__, review_cell_stride=2, review_yaw_bins=12))
        for params in parent_mod.param_grid()
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Dominance-Compatibility', 'disable_dominance_compatibility': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX42ADCLParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = parent_mod.CX34AMSRParams(**{k: v for k, v in params.__dict__.items() if k not in {'review_cell_stride', 'review_yaw_bins'}})
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir, device, dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx42_a_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return memory


class DCLPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX42ADCLParams, memory: dict[str, Any], disable_dominance_compatibility: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_dominance_compatibility = bool(disable_dominance_compatibility)
        parent_params = parent_mod.CX34AMSRParams(**{k: v for k, v in params.__dict__.items() if k not in {'review_cell_stride', 'review_yaw_bins'}})
        self.base = parent_mod.make_policy(memory, parent_params, case, bundle, field, 'cpu', ablation=None)
        self.stats: dict[str, float] = {
            'dominance_runs': 0.0,
            'dominance_skips': 0.0,
        }

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx42_best_frontier', {})
        if hasattr(self.base, 'start_search'):
            self.base.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if not isinstance(ctx, dict) or self.disable_dominance_compatibility:
            return ctx
        key = (
            str(class_key(ctx)),
            tuple(
                coarse_state_key(
                    record,
                    self.case,
                    cell_stride=int(max(self.params.review_cell_stride, 1)),
                    yaw_bins=int(max(self.params.review_yaw_bins, 1)),
                )
            ),
        )
        current_anchor = float(getattr(record, 'anchor', h_pair(float(record.x), float(record.y), float(record.yaw))[0]))
        best_map = search_state.setdefault('cx42_best_frontier', {})
        prev = best_map.get(key)
        allow = bool(prev is None or float(current_anchor) < float(prev) - float(self.params.progress_eps))
        if allow:
            best_map[key] = float(current_anchor)
            self.stats['dominance_runs'] = float(self.stats.get('dominance_runs', 0.0) + 1.0)
            ctx['_cx42_allow_review'] = True
        else:
            self.stats['dominance_skips'] = float(self.stats.get('dominance_skips', 0.0) + 1.0)
            ctx['_cx42_allow_review'] = False
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if isinstance(node_ctx, dict) and not self.disable_dominance_compatibility and not bool(node_ctx.get('_cx42_allow_review', False)):
            return []
        return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if isinstance(node_ctx, dict) and not self.disable_dominance_compatibility and not bool(node_ctx.get('_cx42_allow_review', False)):
            return None
        return self.base.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if hasattr(self.base, 'complete_expand'):
            return self.base.complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX42ADCLParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return DCLPolicy(case, bundle, field, params, memory, disable_dominance_compatibility=bool(ablation.get('disable_dominance_compatibility', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX42ADCLParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX34AMSRParams(**{k: v for k, v in params.__dict__.items() if k not in {'review_cell_stride', 'review_yaw_bins'}})
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, parent_params, memory)


def build_standard_field(sample, predictor, params: CX42ADCLParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX34AMSRParams(**{k: v for k, v in params.__dict__.items() if k not in {'review_cell_stride', 'review_yaw_bins'}})
    return parent_mod.build_standard_field(sample, predictor, parent_params, memory).astype(np.float32)

