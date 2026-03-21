from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx45 import cx45_b_eaw as parent_mod


@dataclass(frozen=True)
class CX45CMBEAWParams:
    review_cell_stride: int
    review_yaw_bins: int
    margin_thr: float
    anchor_eps: float
    enable_parasol_misc: bool
    enable_deadend_labyrinth: bool
    enable_narrow_passage: bool
    support_thr: float
    support_decay: float
    base_ttl: int
    ttl_bonus: int
    anchor_scale: float
    margin_scale: float


def param_grid() -> list[CX45CMBEAWParams]:
    return [
        CX45CMBEAWParams(3, 12, 0.03, 0.02, True, True, True, 0.55, 0.85, 24, 48, 1.0, 1.0),
        CX45CMBEAWParams(3, 12, 0.03, 0.02, True, True, True, 0.60, 0.90, 24, 64, 1.2, 1.0),
        CX45CMBEAWParams(3, 12, 0.03, 0.02, True, True, True, 0.60, 0.90, 32, 64, 1.0, 1.0),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'Proxy-Only-Negative', 'force_negative_skip': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX45CMBEAWParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = parent_mod.CX45BEAWParams(
        review_cell_stride=int(params.review_cell_stride),
        review_yaw_bins=int(params.review_yaw_bins),
        margin_thr=float(params.margin_thr),
        anchor_eps=float(params.anchor_eps),
        enable_parasol_misc=bool(params.enable_parasol_misc),
        enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
        enable_narrow_passage=bool(params.enable_narrow_passage),
        support_thr=float(params.support_thr),
        support_decay=float(params.support_decay),
        base_ttl=int(params.base_ttl),
        ttl_bonus=int(params.ttl_bonus),
        anchor_scale=float(params.anchor_scale),
        margin_scale=float(params.margin_scale),
    )
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir, device, dependencies)
    (out_dir / 'cx45_c_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return memory


class MBEAWPolicy(parent_mod.EAWPolicy):
    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self._family_active():
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return parent_mod.parent_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict):
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return parent_mod.parent_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if len(list(node_ctx.get('macros', []))) <= 0:
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return parent_mod.parent_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX45CMBEAWParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = MBEAWPolicy(
        case,
        bundle,
        field,
        memory['parent_params'],
        memory['parent_memory'],
        parent_mod.CX45BEAWParams(
            review_cell_stride=int(params.review_cell_stride),
            review_yaw_bins=int(params.review_yaw_bins),
            margin_thr=float(params.margin_thr),
            anchor_eps=float(params.anchor_eps),
            enable_parasol_misc=bool(params.enable_parasol_misc),
            enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
            enable_narrow_passage=bool(params.enable_narrow_passage),
            support_thr=float(params.support_thr),
            support_decay=float(params.support_decay),
            base_ttl=int(params.base_ttl),
            ttl_bonus=int(params.ttl_bonus),
            anchor_scale=float(params.anchor_scale),
            margin_scale=float(params.margin_scale),
        ),
        memory['signature_counter'],
        memory['family_stats'],
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX45CMBEAWParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, parent_mod.CX45BEAWParams(
        review_cell_stride=int(params.review_cell_stride),
        review_yaw_bins=int(params.review_yaw_bins),
        margin_thr=float(params.margin_thr),
        anchor_eps=float(params.anchor_eps),
        enable_parasol_misc=bool(params.enable_parasol_misc),
        enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
        enable_narrow_passage=bool(params.enable_narrow_passage),
        support_thr=float(params.support_thr),
        support_decay=float(params.support_decay),
        base_ttl=int(params.base_ttl),
        ttl_bonus=int(params.ttl_bonus),
        anchor_scale=float(params.anchor_scale),
        margin_scale=float(params.margin_scale),
    ), memory)


def build_standard_field(sample, predictor, params: CX45CMBEAWParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(sample, predictor, parent_mod.CX45BEAWParams(
        review_cell_stride=int(params.review_cell_stride),
        review_yaw_bins=int(params.review_yaw_bins),
        margin_thr=float(params.margin_thr),
        anchor_eps=float(params.anchor_eps),
        enable_parasol_misc=bool(params.enable_parasol_misc),
        enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
        enable_narrow_passage=bool(params.enable_narrow_passage),
        support_thr=float(params.support_thr),
        support_decay=float(params.support_decay),
        base_ttl=int(params.base_ttl),
        ttl_bonus=int(params.ttl_bonus),
        anchor_scale=float(params.anchor_scale),
        margin_scale=float(params.margin_scale),
    ), memory).astype(np.float32)
