from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx21.common import (
    CVFModeConfig,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    compile_mode_support,
    compile_viability_table,
    consistency_score,
    consistent_mode,
    foundation_feature_vector,
    foundation_state,
    margin_key,
    match_mode_support,
    query_viability_table,
    save_meta,
)


@dataclass(frozen=True)
class CX21ACVFParams:
    cost_gain: float
    viability_gain: float
    oracle_gain: float
    reverse_align_gain: float
    escape_gain: float
    support_gain: float
    uncertainty_penalty: float
    support_slack: float
    forward_viability_thr: float
    reverse_required_thr: float
    trap_high_thr: float
    escape_affinity_low_thr: float
    hopeless_viability_thr: float
    stride_cells: int
    yaw_stride: int
    horizon_steps: int


def param_grid() -> list[CX21ACVFParams]:
    return [
        CX21ACVFParams(0.10, 0.12, 0.08, 0.10, 0.08, 0.06, 0.05, 0.18, 0.34, 0.08, 0.56, -0.02, 0.10, 2, 2, 5),
        CX21ACVFParams(0.12, 0.14, 0.10, 0.12, 0.10, 0.08, 0.06, 0.20, 0.32, 0.07, 0.54, 0.00, 0.08, 2, 2, 5),
        CX21ACVFParams(0.14, 0.16, 0.12, 0.14, 0.12, 0.10, 0.08, 0.22, 0.30, 0.06, 0.50, 0.02, 0.06, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Consistency', 'disable_consistency': True}]


def _mode_cfg(params: CX21ACVFParams) -> CVFModeConfig:
    return CVFModeConfig(
        forward_viability_thr=float(params.forward_viability_thr),
        reverse_required_thr=float(params.reverse_required_thr),
        trap_high_thr=float(params.trap_high_thr),
        escape_affinity_low_thr=float(params.escape_affinity_low_thr),
        hopeless_viability_thr=float(params.hopeless_viability_thr),
    )


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX21ACVFParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    mode_cfg = _mode_cfg(params)
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    support = compile_mode_support(calib_train_assets, spec, mode_cfg, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    save_meta(
        out_dir / 'cvf_meta.json',
        {
            'params': params.__dict__,
            'mode_cfg': mode_cfg.__dict__,
            'mode_support': {
                mode: {
                    'similarity_floor': float(band.similarity_floor),
                    'min_progress': float(band.min_progress),
                    'counts': int(band.counts),
                }
                for mode, band in support.items()
            },
            'viability_table_size': int(len(table)),
        },
    )
    return {'viability_table': table, 'mode_support': support, 'best_val_loss': float('nan')}


class CVFPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX21ACVFParams, memory: dict[str, Any], disable_consistency: bool = False) -> None:
        self.case = case
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_consistency = bool(disable_consistency)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.mode_cfg = _mode_cfg(params)
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.mode_support = dict(memory.get('mode_support', {})) if isinstance(memory, dict) else {}

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        state = (float(record.x), float(record.y), float(record.yaw))
        cur = foundation_state(self.case, self.case.get('_cx21_bundle', {}), self.field, self.encoder, state, self.spec)
        stats = self.encoder.features(state)
        oracle = query_viability_table(self.table, margin_key(stats))
        oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
        feat = foundation_feature_vector(cur)
        support_mode, matched, sim = match_mode_support(
            self.mode_support,
            feat,
            gain_hint=max(float(oracle_gain), 0.0),
            slack=float(self.params.support_slack),
        )
        base_mode = consistent_mode(cur, self.mode_cfg)
        active_mode = support_mode if bool(matched) else str(base_mode)
        return {
            'foundation': cur,
            'mode': str(active_mode),
            'oracle_gain': float(oracle_gain),
            'support_sim': float(sim),
            'support_matched': bool(matched),
        }

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return None
        current = node_ctx.get('foundation')
        if current is None:
            return None
        current_cost = float(current.cost_to_go)
        current_viability = float(current.viability)
        current_mode = str(node_ctx.get('mode', 'uncertain'))
        ranked = []
        for cand in candidates:
            nf = foundation_state(self.case, self.case.get('_cx21_bundle', {}), self.field, self.encoder, cand.next_state, self.spec)
            stats = self.encoder.features(cand.next_state)
            oracle = query_viability_table(self.table, margin_key(stats))
            oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
            feat = foundation_feature_vector(nf)
            support_mode, matched, sim = match_mode_support(
                self.mode_support,
                feat,
                gain_hint=max(float(oracle_gain), 0.0),
                slack=float(self.params.support_slack),
            )
            cons = 1.0 if self.disable_consistency else float(consistency_score(nf))
            delta = 0.0
            delta += float(self.params.cost_gain) * float(nf.cost_to_go - current_cost)
            delta -= float(self.params.viability_gain) * float(nf.viability - current_viability)
            delta -= float(self.params.oracle_gain) * float(oracle_gain)
            if not self.disable_consistency:
                delta += float(self.params.uncertainty_penalty) * float(1.0 - cons)
                if matched:
                    delta -= float(self.params.support_gain) * float(max(sim, 0.0))
                else:
                    delta += float(self.params.uncertainty_penalty)
            if current_mode == 'reverse_setup':
                if int(cand.direction) < 0:
                    delta -= float(self.params.reverse_align_gain) * float(cons)
                else:
                    delta += 0.75 * float(self.params.reverse_align_gain) * float(cons)
            elif current_mode == 'escape_border':
                if int(cand.direction) < 0:
                    delta -= float(self.params.escape_gain) * float(cons)
                else:
                    delta += 0.50 * float(self.params.escape_gain) * float(cons)
            elif current_mode == 'forward_safe' and int(cand.direction) < 0:
                delta += 0.50 * float(self.params.reverse_align_gain) * float(cons)
            if not self.disable_consistency and matched and support_mode != current_mode and current_mode != 'uncertain':
                delta += 0.04
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX21ACVFParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CVFPolicy(case, bundle, field, params, memory, disable_consistency=bool(ablation.get('disable_consistency', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX21ACVFParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx21_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX21ACVFParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
