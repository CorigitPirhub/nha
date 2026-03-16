from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx9.common import (
    accepted_cx3d_nonholonomic,
    accepted_cx3d_standard,
    collect_mode_training_rows,
    fit_mode_prototypes,
    nearest_mode,
    primitive_priority_delta,
    query_dense_mode,
    rasterize_sparse_mode_map,
    select_bottleneck_windows,
)
from rs_cx9.common import build_compact_bundle_feature_vector


@dataclass(frozen=True)
class CX9DBWRParams:
    top_k: int
    gate_threshold: float
    window_radius_m: float
    mode_strength: float
    neutral_similarity: float


def param_grid() -> list[CX9DBWRParams]:
    return [
        CX9DBWRParams(2, 0.42, 2.0, 0.30, 0.10),
        CX9DBWRParams(3, 0.40, 2.4, 0.36, 0.12),
        CX9DBWRParams(3, 0.48, 1.8, 0.42, 0.14),
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX9DBWRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = collect_mode_training_rows(calib_train_assets)
    proto_bank = fit_mode_prototypes(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'window_meta.json').write_text(
        __import__('json').dumps({'counts': proto_bank.get('counts', {}), 'num_rows': len(rows)}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return {'prototype_bank': proto_bank, 'train_rows': int(len(rows)), 'best_val_loss': float('nan')}


class BWRPolicy:
    def __init__(self, case: dict[str, Any], mode_map: np.ndarray, params: CX9DBWRParams) -> None:
        self.case = case
        self.mode_map = np.asarray(mode_map, dtype=np.int16)
        self.params = params

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        mode = query_dense_mode(self.case, self.mode_map, (float(record.x), float(record.y), float(record.yaw)))
        return {'mode': int(mode)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        mode = int(node_ctx.get('mode', 0)) if isinstance(node_ctx, dict) else 0
        ranked = []
        for cand in candidates:
            delta = primitive_priority_delta(self.case, int(cand.primitive_index), mode, float(self.params.mode_strength))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX9DBWRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    windows = select_bottleneck_windows(case, bundle, field, top_k=int(params.top_k), min_sep_m=2.5, gate_threshold=float(params.gate_threshold))
    proto_bank = memory.get('prototype_bank', {})
    labeled = []
    for win in windows:
        feat = build_compact_bundle_feature_vector(case, bundle, field, win['state'], prev_steer=0.0)
        mode, sim = nearest_mode(feat, proto_bank, neutral_if_small=float(params.neutral_similarity))
        if int(mode) == 0:
            continue
        labeled.append({**win, 'mode': int(mode), 'similarity': float(sim)})
    mode_map = rasterize_sparse_mode_map(case, labeled, radius_m=float(params.window_radius_m))
    return BWRPolicy(case, mode_map, params)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX9DBWRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX9DBWRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)
