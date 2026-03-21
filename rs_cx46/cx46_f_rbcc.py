from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx46 import cx46_d_ewv as parent_mod


@dataclass(frozen=True)
class CX46FRBCCParams:
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


def param_grid() -> list[CX46FRBCCParams]:
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
        max_ttl=112,
        min_band_count=8,
    )
    return [
        CX46FRBCCParams(**common, certainty_floor=0.25, reliable_ttl_boost=1.10, reliable_anchor_boost=1.05, local_ttl_scale=0.60, local_anchor_scale=0.55),
        CX46FRBCCParams(**common, certainty_floor=0.30, reliable_ttl_boost=1.15, reliable_anchor_boost=1.10, local_ttl_scale=0.55, local_anchor_scale=0.50),
        CX46FRBCCParams(**common, certainty_floor=0.20, reliable_ttl_boost=1.05, reliable_anchor_boost=1.00, local_ttl_scale=0.65, local_anchor_scale=0.60),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return parent_mod.ablation_specs()


def _to_parent_params(params: CX46FRBCCParams) -> parent_mod.CX46DEWVParams:
    return parent_mod.CX46DEWVParams(
        review_cell_stride=int(params.review_cell_stride),
        review_yaw_bins=int(params.review_yaw_bins),
        margin_thr=float(params.margin_thr),
        anchor_eps=float(params.anchor_eps),
        enable_parasol_misc=bool(params.enable_parasol_misc),
        enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
        enable_narrow_passage=bool(params.enable_narrow_passage),
        band_slack=float(params.band_slack),
        similarity_scale=float(params.similarity_scale),
        reliable_weight=1.0,
        local_weight=1.0,
        fragile_weight=1.0,
        anchor_gain=1.0,
        ttl_gain=1.0,
        max_ttl=int(params.max_ttl),
        min_band_count=int(params.min_band_count),
    )


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX46FRBCCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = _to_parent_params(params)
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir, device, dependencies)
    meta = {
        'params': params.__dict__,
        'quality_model': {
            'class_counts': dict(memory.get('quality_model', {}).get('class_counts', {})),
            'num_rows': int(memory.get('quality_model', {}).get('num_rows', 0)),
            'num_active_rows': int(memory.get('quality_model', {}).get('num_active_rows', 0)),
            'num_hit_rows': int(memory.get('quality_model', {}).get('num_hit_rows', 0)),
        },
    }
    (out_dir / 'cx46_f_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return memory


class RBCCPolicy(parent_mod.QualityTracePolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        params: CX46FRBCCParams,
        memory: dict[str, Any],
        *,
        disable_witness_transfer: bool = False,
        force_negative_skip: bool = False,
        collect_quality_rows: bool = False,
    ) -> None:
        super().__init__(
            case,
            bundle,
            field,
            memory['parent_params'],
            memory['parent_memory'],
            _to_parent_params(params),
            type_counter=memory['type_counter'],
            type_stats=memory['type_stats'],
            quality_bands=dict(memory.get('quality_model', {}).get('bands', {})),
            disable_witness_transfer=disable_witness_transfer,
            force_negative_skip=force_negative_skip,
            collect_quality_rows=collect_quality_rows,
        )
        self.params46f = params
        self.stats['rbcc_certainty_sum'] = 0.0
        self.stats['rbcc_certainty_count'] = 0.0

    def _quality_for_store(self, record, node_ctx: dict[str, Any], margin: float) -> dict[str, float]:
        feat = parent_mod._quality_feature(
            self.case,
            self.bundle,
            record,
            node_ctx,
            float(margin),
            self.type_counter,
            self.type_stats,
            float(self.params46f.margin_thr),
        )
        bands = dict(self.quality_bands)
        logits = {key: parent_mod._band_similarity(bands.get(key), feat, float(self.params46f.band_slack)) for key in parent_mod.QUALITY_CLASSES}
        weights = parent_mod._softmax(logits, float(self.params46f.similarity_scale))
        positive_mass = float(weights.get('reliable', 0.0) + weights.get('local', 0.0))
        certainty = float(abs(float(weights.get('reliable', 0.0)) - float(weights.get('local', 0.0))) / max(positive_mass, 1e-6))
        reliable = float(weights.get('reliable', 0.0))
        local = float(weights.get('local', 0.0))
        fragile = float(weights.get('fragile', 0.0))
        strength = float(positive_mass * (float(self.params46f.certainty_floor) + (1.0 - float(self.params46f.certainty_floor)) * certainty))
        store_strength = float(np.clip(reliable + 0.45 * local * certainty, 0.0, 1.0))
        self.stats['rbcc_certainty_sum'] = float(self.stats.get('rbcc_certainty_sum', 0.0) + certainty)
        self.stats['rbcc_certainty_count'] = float(self.stats.get('rbcc_certainty_count', 0.0) + 1.0)
        return {
            'feature': feat,
            'reliable': reliable,
            'local': local,
            'fragile': fragile,
            'strength': strength,
            'store_strength': store_strength,
            'certainty': certainty,
        }

    def _ttl_and_radius(self, quality: dict[str, float]) -> tuple[int, float]:
        reliable = float(quality.get('reliable', 0.0))
        local = float(quality.get('local', 0.0))
        certainty = float(quality.get('certainty', 0.0))
        bands = dict(self.quality_bands)
        rel_band = bands.get('reliable')
        loc_band = bands.get('local')
        rel_ttl = float(getattr(rel_band, 'ttl_quantile', 8.0))
        loc_ttl = float(getattr(loc_band, 'ttl_quantile', 4.0))
        rel_anchor = float(getattr(rel_band, 'anchor_quantile', self.params46f.anchor_eps))
        loc_anchor = float(getattr(loc_band, 'anchor_quantile', self.params46f.anchor_eps))
        if reliable >= local:
            ttl = rel_ttl * float(self.params46f.reliable_ttl_boost) * (0.75 + 0.75 * certainty)
            anchor = rel_anchor * float(self.params46f.reliable_anchor_boost) * (0.75 + 0.65 * certainty)
        else:
            ttl = loc_ttl * float(self.params46f.local_ttl_scale) * (0.60 + 0.40 * certainty)
            anchor = loc_anchor * float(self.params46f.local_anchor_scale) * (0.65 + 0.35 * certainty)
        return int(round(max(4.0, min(float(self.params46f.max_ttl), ttl)))), float(max(float(self.params46f.anchor_eps), anchor))

    def _register_store(self, sig: tuple[Any, ...], record, node_ctx: dict[str, Any], margin: float, quality: dict[str, float], search_state: dict[str, Any]) -> dict[str, Any]:
        witness = super()._register_store(sig, record, node_ctx, margin, quality, search_state)
        witness_map = dict(search_state.get('cx46d_witness', {}))
        stored = dict(witness_map.get(sig, witness))
        stored['stored_popped'] = int(search_state.get('popped', 0))
        stored['stored_anchor'] = float(getattr(record, 'anchor', 0.0))
        witness_map[sig] = stored
        search_state['cx46d_witness'] = witness_map
        return stored

    def _probe_witness(self, sig: tuple[Any, ...], record, search_state: dict[str, Any]) -> dict[str, Any] | None:
        witness = dict(search_state.get('cx46d_witness', {})).get(sig)
        if not isinstance(witness, dict):
            return None
        quality = dict(witness.get('quality', {}))
        reliable = float(quality.get('reliable', 0.0))
        local = float(quality.get('local', 0.0))
        if local > reliable:
            current_popped = int(search_state.get('popped', 0))
            stored_popped = int(witness.get('stored_popped', current_popped))
            effective_expiry = int(stored_popped + 0.60 * max(int(witness.get('expiry', stored_popped)) - stored_popped, 0))
            if current_popped > effective_expiry:
                return None
            current_anchor = float(getattr(record, 'anchor', 0.0))
            stored_anchor = float(witness.get('best_anchor', current_anchor))
            effective_radius = 0.60 * float(witness.get('anchor_radius', self.params46f.anchor_eps))
            if max(current_anchor - stored_anchor, 0.0) > effective_radius:
                return None
        return super()._probe_witness(sig, record, search_state)


def make_policy(memory: dict[str, Any], params: CX46FRBCCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = RBCCPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
        collect_quality_rows=False,
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX46FRBCCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, _to_parent_params(params), memory)


def build_standard_field(sample, predictor, params: CX46FRBCCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(sample, predictor, _to_parent_params(params), memory).astype(np.float32)
