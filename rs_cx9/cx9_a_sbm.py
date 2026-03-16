from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx9.common import (
    CoarseGridSpec,
    accepted_cx3d_nonholonomic,
    accepted_cx3d_standard,
    build_coarse_mode_map,
    collect_mode_training_rows,
    fit_mode_prototypes,
    primitive_priority_delta,
    primitive_index_from_case,
    query_coarse_mode,
)


@dataclass(frozen=True)
class CX9ASBMParams:
    stride_cells: int
    gate_threshold: float
    neutral_similarity: float
    apply_conf_threshold: float
    local_score_threshold: float
    mode_strength: float
    misc_margin: float
    misc_misc_thr: float
    misc_open_thr: float
    misc_bridge_thr: float


def param_grid() -> list[CX9ASBMParams]:
    return [
        CX9ASBMParams(5, 0.45, 0.10, 0.08, 0.20, 0.24, 0.02, 0.78, 0.94, 0.10),
        CX9ASBMParams(5, 0.45, 0.10, 0.10, 0.22, 0.22, 0.04, 0.80, 0.94, 0.12),
        CX9ASBMParams(6, 0.48, 0.12, 0.10, 0.25, 0.22, 0.04, 0.82, 0.95, 0.12),
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX9ASBMParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = collect_mode_training_rows(calib_train_assets)
    proto_bank = fit_mode_prototypes(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'prototype_meta.json').write_text(
        __import__('json').dumps({'counts': proto_bank.get('counts', {}), 'num_rows': len(rows)}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return {
        'prototype_bank': proto_bank,
        'train_rows': int(len(rows)),
        'best_val_loss': float('nan'),
    }


class SBMPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], mode_map: np.ndarray, conf_map: np.ndarray, score_map: np.ndarray, params: CX9ASBMParams) -> None:
        self.case = case
        self.bundle = bundle
        self.mode_map = np.asarray(mode_map, dtype=np.int16)
        self.conf_map = np.asarray(conf_map, dtype=np.float32)
        self.score_map = np.asarray(score_map, dtype=np.float32)
        self.params = params
        self.spec = CoarseGridSpec(stride_cells=int(params.stride_cells))
        self.primitive_index = primitive_index_from_case(case)
        self.orders_by_mode = self._build_orders()

    def _build_orders(self) -> dict[int, list[int]]:
        orders: dict[int, list[int]] = {}
        for mode in range(5):
            scored = []
            for idx in range(len(self.primitive_index)):
                delta = primitive_priority_delta(self.case, int(idx), int(mode), float(self.params.mode_strength))
                scored.append((float(delta), int(idx)))
            scored.sort(key=lambda x: float(x[0]))
            orders[mode] = [idx for _, idx in scored]
        return orders

    def _scene_misc_abstain(self) -> bool:
        scene = self.bundle.get('scene', {})
        misc = float(scene.get('misc_likelihood', 0.0))
        hard = float(scene.get('hard_likelihood', 0.0))
        path_open = float(scene.get('path_openness', 0.0))
        bridge = float(scene.get('bridge_diffuse', 0.0))
        if misc > hard + float(self.params.misc_margin):
            return True
        if misc >= float(self.params.misc_misc_thr) and path_open >= float(self.params.misc_open_thr) and bridge >= float(self.params.misc_bridge_thr):
            return True
        return False

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        if self._scene_misc_abstain():
            return {'mode': 0, 'primitive_order': self.orders_by_mode[0]}
        state = (float(record.x), float(record.y), float(record.yaw))
        gx = int(np.clip(np.floor(float(record.x) / float(self.case['resolution'])), 0, self.conf_map.shape[1] - 1))
        gy = int(np.clip(np.floor(float(record.y) / float(self.case['resolution'])), 0, self.conf_map.shape[0] - 1))
        local_conf = float(self.conf_map[gy, gx])
        local_score = float(self.score_map[gy, gx])
        if local_conf < float(self.params.apply_conf_threshold) or local_score < float(self.params.local_score_threshold):
            return {'mode': 0, 'primitive_order': self.orders_by_mode[0]}
        mode = query_coarse_mode(self.case, self.mode_map, self.spec, state)
        return {'mode': int(mode), 'primitive_order': self.orders_by_mode.get(int(mode), self.orders_by_mode[0])}


def make_policy(memory: dict[str, Any], params: CX9ASBMParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    proto_bank = memory.get('prototype_bank', {})
    mode_map, conf_map = build_coarse_mode_map(
        case,
        bundle,
        field,
        CoarseGridSpec(stride_cells=int(params.stride_cells)),
        proto_bank,
        gate_threshold=float(params.gate_threshold),
        neutral_similarity=float(params.neutral_similarity),
    )
    score_map = 0.45 * np.asarray(bundle['barrier'], dtype=np.float32) + 0.35 * np.asarray(bundle['focus'], dtype=np.float32) + 0.20 * (1.0 - np.asarray(bundle['corridor'], dtype=np.float32))
    score_map = np.asarray(score_map, dtype=np.float32)
    return SBMPolicy(case, bundle, mode_map, conf_map, score_map, params)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX9ASBMParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX9ASBMParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)
