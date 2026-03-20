from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx16.common import macro_successor_candidates
from rs_cx23.common import class_key
from rs_cx33 import cx33_b_bsr as base_mod
from rs_cx35.common import (
    build_frozen_haa_stack,
    build_local_proxy,
    choose_typed_family,
    compile_typed_macro_support,
    reverse_pair_families,
)


@dataclass(frozen=True)
class CX35ATMFIParams:
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


def param_grid() -> list[CX35ATMFIParams]:
    return [
        CX35ATMFIParams(
            0.10,
            0.36,
            0.08,
            0.39,
            0.99,
            1,
            0.11,
            0.13,
            0.31,
            0.97,
            0.125,
            0.34,
            0.97,
            2,
            18,
            0.10,
            0.54,
            0.02,
            0.05,
            32,
            16,
            2,
            24,
            2,
        ),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Typed-Macro-Family', 'disable_typed_macro_family': True},
        {'name': 'No-Witness', 'disable_witness': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX35ATMFIParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = build_frozen_haa_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    support = compile_typed_macro_support(
        calib_train_assets,
        teacher,
        families=reverse_pair_families(),
        min_hits=int(params.min_hits),
        out_dir=out_dir,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx35_a_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'families': {
                    name: {
                        'avg_score': float(stat.avg_score),
                        'hits': int(stat.hits),
                    }
                    for name, stat in support['support'].items()
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return {
        'haa_teacher': teacher,
        'typed_macro_families': support['families'],
        'typed_macro_support': support['support'],
        'best_val_loss': float('nan'),
    }


class TMFIPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX35ATMFIParams, memory: dict[str, Any], disable_typed_macro_family: bool = False, disable_witness: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_typed_macro_family = bool(disable_typed_macro_family)
        self.disable_witness = bool(disable_witness)
        self.teacher = memory['haa_teacher']
        self.typed_macro_families = tuple(memory.get('typed_macro_families', reverse_pair_families()))
        self.typed_macro_support = dict(memory.get('typed_macro_support', {}))
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
        self._local_proxy = None

    def start_search(self, planner, start, goal, h_pair, search_state):
        if hasattr(self.base, 'start_search'):
            self.base.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        search_state['last_record_x'] = float(record.x)
        search_state['last_record_y'] = float(record.y)
        search_state['last_record_yaw'] = float(record.yaw)
        return self.base.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        extra = self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_typed_macro_family or not isinstance(node_ctx, dict):
            return extra
        if str(class_key(node_ctx)) != 'uncertain|none':
            return extra
        families = self.typed_macro_families
        support = self.typed_macro_support
        if self.disable_witness:
            local_state = (float(record.x), float(record.y), float(record.yaw))
            scored: list[tuple[float, Any]] = []
            for family in families:
                score, macro = choose_single_best(self.case, local_state, h_pair, family)
                if macro is not None and float(score) > 0.0:
                    scored.append((float(score), macro))
            if not scored:
                return extra
            scored.sort(key=lambda item: item[0], reverse=True)
            chosen_macros = [scored[0][1]]
        else:
            family_name, chosen_macros, _ = choose_typed_family(self.case, self.bundle, node_ctx, search_state, h_pair, families, support)
            if family_name is None or not chosen_macros:
                return extra
            search_state['cx35_last_family'] = str(family_name)
        extra_rows = list(extra or [])
        extra_rows.extend(macro_successor_candidates(self.case, planner, record, h_pair, chosen_macros, max_macros=len(chosen_macros)))
        return extra_rows

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.base.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if hasattr(self.base, 'complete_expand'):
            return self.base.complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)


def choose_single_best(case: dict[str, Any], state: tuple[float, float, float], h_pair, family) -> tuple[float, Any | None]:
    from rs_cx35.common import best_macro_score_for_family

    return best_macro_score_for_family(case, state, h_pair, family)


def make_policy(memory: dict[str, Any], params: CX35ATMFIParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return TMFIPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_typed_macro_family=bool(ablation.get('disable_typed_macro_family', False)),
        disable_witness=bool(ablation.get('disable_witness', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX35ATMFIParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return base_mod.build_nonholonomic_field(
        case,
        predictor,
        cfg,
        base_mod.CX33BBSRParams(
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
        ),
        memory,
    )


def build_standard_field(sample, predictor, params: CX35ATMFIParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return base_mod.build_standard_field(
        sample,
        predictor,
        base_mod.CX33BBSRParams(
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
        ),
        memory,
    ).astype(np.float32)
