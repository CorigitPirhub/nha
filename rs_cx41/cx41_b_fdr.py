from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import class_key
from rs_cx27.common import coarse_state_key
from rs_cx40 import cx40_a_cas as parent_mod


@dataclass(frozen=True)
class CX41BFDRParams:
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
    min_hits: int
    max_bridge_depth: int
    max_bridge_frontier: int
    max_review_targets: int
    max_screened_paths: int
    review_cell_stride: int
    review_yaw_bins: int


def param_grid() -> list[CX41BFDRParams]:
    return [
        CX41BFDRParams(**dict(params.__dict__, review_cell_stride=2, review_yaw_bins=12))
        for params in parent_mod.param_grid()
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Dominance-Gate', 'disable_dominance_gate': True},
        {'name': 'No-Depth2-Escalation', 'disable_depth2_escalation': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX41BFDRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = parent_mod.CX40ACASParams(**{k: v for k, v in params.__dict__.items() if k not in {'review_cell_stride', 'review_yaw_bins'}})
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx41_b_meta.json').write_text(
        json.dumps(
            {'params': params.__dict__},
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return memory


class FDRPolicy(parent_mod.CASPolicy):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX41BFDRParams, memory: dict[str, Any], *, disable_dominance_gate: bool = False, disable_depth2_escalation: bool = False) -> None:
        parent_params = parent_mod.CX40ACASParams(**{k: v for k, v in params.__dict__.items() if k not in {'review_cell_stride', 'review_yaw_bins'}})
        super().__init__(case, bundle, field, parent_params, memory, disable_prescreener=False, disable_depth2_escalation=disable_depth2_escalation)
        self.params = params
        self.disable_dominance_gate = bool(disable_dominance_gate)
        self.stats['dominance_skips'] = 0.0
        self.stats['dominance_runs'] = 0.0

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx41_review_best', {})
        return super().start_search(planner, start, goal, h_pair, search_state)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if isinstance(node_ctx, dict) and not self.disable_dominance_gate:
            key = (
                str(class_key(node_ctx)),
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
            best_map = search_state.setdefault('cx41_review_best', {})
            prev = best_map.get(key)
            if prev is not None and float(current_anchor) >= float(prev) - float(self.params.progress_eps):
                self.stats['dominance_skips'] = float(self.stats.get('dominance_skips', 0.0) + 1.0)
                return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
            best_map[key] = float(current_anchor)
            self.stats['dominance_runs'] = float(self.stats.get('dominance_runs', 0.0) + 1.0)
        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX41BFDRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return FDRPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_dominance_gate=bool(ablation.get('disable_dominance_gate', False)),
        disable_depth2_escalation=bool(ablation.get('disable_depth2_escalation', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX41BFDRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX40ACASParams(**{k: v for k, v in params.__dict__.items() if k not in {'review_cell_stride', 'review_yaw_bins'}})
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, parent_params, memory)


def build_standard_field(sample, predictor, params: CX41BFDRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX40ACASParams(**{k: v for k, v in params.__dict__.items() if k not in {'review_cell_stride', 'review_yaw_bins'}})
    return parent_mod.build_standard_field(sample, predictor, parent_params, memory).astype(np.float32)

