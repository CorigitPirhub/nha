from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx46 import cx46_f_rbcc as parent_mod


@dataclass(frozen=True)
class CX46JRRCParams:
    review_cell_stride: int
    review_yaw_bins: int
    margin_thr: float
    anchor_eps: float
    enable_parasol_misc: bool
    enable_deadend_labyrinth: bool
    enable_narrow_passage: bool
    band_slack: float
    similarity_scale: float
    certainty_floor: float
    reliable_ttl_boost: float
    reliable_anchor_boost: float
    local_ttl_scale: float
    local_anchor_scale: float
    max_ttl: int
    min_band_count: int
    initial_credit: float
    miss_cost: float
    hit_reward: float
    store_reward: float
    low_credit_stride: int
    min_credit_floor: float


def param_grid() -> list[CX46JRRCParams]:
    common = dict(
        review_cell_stride=3,
        review_yaw_bins=12,
        margin_thr=0.03,
        anchor_eps=0.02,
        enable_parasol_misc=True,
        enable_deadend_labyrinth=True,
        enable_narrow_passage=True,
        band_slack=0.15,
        similarity_scale=4.0,
        certainty_floor=0.20,
        reliable_ttl_boost=1.05,
        reliable_anchor_boost=1.00,
        local_ttl_scale=0.65,
        local_anchor_scale=0.60,
        max_ttl=112,
        min_band_count=8,
        min_credit_floor=-3.0,
    )
    return [
        CX46JRRCParams(**common, initial_credit=2.0, miss_cost=1.0, hit_reward=0.75, store_reward=1.5, low_credit_stride=2),
        CX46JRRCParams(**common, initial_credit=3.0, miss_cost=1.0, hit_reward=0.50, store_reward=1.5, low_credit_stride=2),
        CX46JRRCParams(**common, initial_credit=2.0, miss_cost=1.0, hit_reward=0.75, store_reward=2.0, low_credit_stride=3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'No-Credit-Gate', 'disable_credit_gate': True},
    ]


def _to_parent_params(params: CX46JRRCParams) -> parent_mod.CX46FRBCCParams:
    return parent_mod.CX46FRBCCParams(
        review_cell_stride=int(params.review_cell_stride),
        review_yaw_bins=int(params.review_yaw_bins),
        margin_thr=float(params.margin_thr),
        anchor_eps=float(params.anchor_eps),
        enable_parasol_misc=bool(params.enable_parasol_misc),
        enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
        enable_narrow_passage=bool(params.enable_narrow_passage),
        band_slack=float(params.band_slack),
        similarity_scale=float(params.similarity_scale),
        certainty_floor=float(params.certainty_floor),
        reliable_ttl_boost=float(params.reliable_ttl_boost),
        reliable_anchor_boost=float(params.reliable_anchor_boost),
        local_ttl_scale=float(params.local_ttl_scale),
        local_anchor_scale=float(params.local_anchor_scale),
        max_ttl=int(params.max_ttl),
        min_band_count=int(params.min_band_count),
    )


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX46JRRCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, _to_parent_params(params), out_dir, device, dependencies)
    (out_dir / 'cx46_j_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return memory


class RRCPolicy(parent_mod.RBCCPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        params: CX46JRRCParams,
        memory: dict[str, Any],
        *,
        disable_witness_transfer: bool = False,
        disable_credit_gate: bool = False,
        force_negative_skip: bool = False,
        collect_quality_rows: bool = False,
    ) -> None:
        super().__init__(
            case,
            bundle,
            field,
            _to_parent_params(params),
            memory,
            disable_witness_transfer=disable_witness_transfer,
            force_negative_skip=force_negative_skip,
            collect_quality_rows=collect_quality_rows,
        )
        self.params46j = params
        self.disable_credit_gate = bool(disable_credit_gate)
        self.stats['credit_gate_skips'] = 0.0

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx46j_credit', float(self.params46j.initial_credit))
        search_state.setdefault('cx46j_review_index', 0)
        search_state.setdefault('cx46j_pending_credit', None)
        return super().start_search(planner, start, goal, h_pair, search_state)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self._family_active() or not isinstance(node_ctx, dict) or len(list(node_ctx.get('macros', []))) <= 0:
            return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_witness_transfer:
            return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        sig = self._sig(record, node_ctx)
        witness = self._probe_witness(sig, record, search_state)
        if isinstance(witness, dict):
            search_state['cx46j_credit'] = min(float(self.params46j.initial_credit) + float(self.params46j.store_reward), float(search_state.get('cx46j_credit', 0.0)) + float(self.params46j.hit_reward))
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            search_state['cx46d_pending'] = None
            return []
        if not self.disable_credit_gate:
            review_index = int(search_state.get('cx46j_review_index', 0)) + 1
            search_state['cx46j_review_index'] = review_index
            credit = float(search_state.get('cx46j_credit', 0.0))
            if credit < 0.0 and (review_index % int(max(self.params46j.low_credit_stride, 1))) != 0:
                self.stats['credit_gate_skips'] = float(self.stats.get('credit_gate_skips', 0.0) + 1.0)
                search_state['cx46d_pending'] = None
                return parent_mod.parent_mod.witness_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
            search_state['cx46j_pending_credit'] = {
                'credit_before': credit,
                'store_before': float(self.stats.get('witness_store_negative', 0.0)),
            }
        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        ranked = super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        pending = search_state.get('cx46j_pending_credit')
        if isinstance(pending, dict):
            credit_before = float(pending.get('credit_before', 0.0))
            store_before = float(pending.get('store_before', 0.0))
            store_after = float(self.stats.get('witness_store_negative', 0.0))
            if store_after > store_before + 1e-6:
                credit = credit_before + float(self.params46j.store_reward)
            else:
                credit = credit_before - float(self.params46j.miss_cost)
            search_state['cx46j_credit'] = max(float(self.params46j.min_credit_floor), credit)
            search_state['cx46j_pending_credit'] = None
        return ranked


def make_policy(memory: dict[str, Any], params: CX46JRRCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = RRCPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        disable_credit_gate=bool(ablation.get('disable_credit_gate', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
        collect_quality_rows=False,
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX46JRRCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, _to_parent_params(params), memory)


def build_standard_field(sample, predictor, params: CX46JRRCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(sample, predictor, _to_parent_params(params), memory).astype(np.float32)
