from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx8.common import FitArtifact, fit_multiclass_model, load_fit_model, predict_logits
from rs_cx9.common import (
    CoarseGridSpec,
    accepted_cx3d_nonholonomic,
    accepted_cx3d_standard,
    build_compact_bundle_feature_vector,
    collect_mode_training_rows,
    mode_from_bundle_target,
    primitive_priority_delta,
    query_coarse_mode,
)


@dataclass(frozen=True)
class CX9CCPFParams:
    stride_cells: int
    yaw_clusters: int
    gate_threshold: float
    mode_strength: float
    hidden_dim: int
    learning_rate: float
    weight_decay: float
    epochs: int
    batch_size: int


def param_grid() -> list[CX9CCPFParams]:
    return [
        CX9CCPFParams(4, 4, 0.38, 0.28, 64, 1e-3, 1e-4, 55, 128),
        CX9CCPFParams(4, 6, 0.42, 0.34, 96, 8e-4, 1e-4, 65, 128),
        CX9CCPFParams(5, 6, 0.48, 0.40, 96, 8e-4, 3e-4, 75, 128),
    ]


def _dataset_from_assets(assets: list[dict[str, Any]], params: CX9CCPFParams) -> tuple[np.ndarray, np.ndarray]:
    rows = collect_mode_training_rows(assets)
    xs = [np.asarray(r['feature'], dtype=np.float32) for r in rows]
    ys = [int(r['mode']) for r in rows]
    for item in assets:
        result = item['baseline_result']
        if not bool(result.success):
            continue
        path = np.asarray(result.path, dtype=np.float32)
        for t in range(0, max(path.shape[0] - 1, 0), 4):
            state = tuple(float(v) for v in path[t])
            feat = build_compact_bundle_feature_vector(item['case'], item['bundle'], item['field'], state, prev_steer=0.0)
            xs.append(np.asarray(feat, dtype=np.float32))
            ys.append(0)
    if not xs:
        return np.zeros((0, 1), dtype=np.float32), np.zeros((0,), dtype=np.int64)
    return np.stack(xs, axis=0).astype(np.float32), np.asarray(ys, dtype=np.int64)


class CPFPolicy:
    def __init__(self, case: dict[str, Any], mode_map: np.ndarray, params: CX9CCPFParams) -> None:
        self.case = case
        self.mode_map = np.asarray(mode_map, dtype=np.int16)
        self.params = params
        self.spec = CoarseGridSpec(stride_cells=int(params.stride_cells), yaw_clusters=int(params.yaw_clusters))

    def _query_mode(self, state: tuple[float, float, float]) -> int:
        x, y, yaw = state
        stride = int(max(self.params.stride_cells, 1))
        gx = int(np.clip(np.floor(float(x) / float(self.case['resolution']) / stride), 0, self.mode_map.shape[2] - 1))
        gy = int(np.clip(np.floor(float(y) / float(self.case['resolution']) / stride), 0, self.mode_map.shape[1] - 1))
        yaw_clusters = int(max(self.params.yaw_clusters, 1))
        yaw_bin = int(np.floor((yaw + np.pi) / (2.0 * np.pi) * yaw_clusters)) % yaw_clusters
        return int(self.mode_map[yaw_bin, gy, gx])

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        mode = self._query_mode((float(record.x), float(record.y), float(record.yaw)))
        return {'mode': int(mode)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        mode = int(node_ctx.get('mode', 0)) if isinstance(node_ctx, dict) else 0
        ranked = []
        for cand in candidates:
            delta = primitive_priority_delta(self.case, int(cand.primitive_index), mode, float(self.params.mode_strength))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX9CCPFParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    train_x, train_y = _dataset_from_assets(calib_train_assets, params)
    val_x, val_y = _dataset_from_assets(calib_val_assets, params)
    out_dir.mkdir(parents=True, exist_ok=True)
    if train_x.shape[0] == 0 or val_x.shape[0] == 0:
        return {'artifact': None, 'train_rows': int(train_x.shape[0]), 'best_val_loss': float('inf')}
    artifact: FitArtifact = fit_multiclass_model(
        train_x,
        train_y,
        val_x,
        val_y,
        model_path=out_dir / 'model.pt',
        meta_path=out_dir / 'model_meta.json',
        hidden_dim=int(params.hidden_dim),
        learning_rate=float(params.learning_rate),
        weight_decay=float(params.weight_decay),
        epochs=int(params.epochs),
        batch_size=int(params.batch_size),
        device=str(device),
        seed=7,
    )
    model, meta = load_fit_model(artifact, str(device))
    return {'artifact': artifact, 'model': model, 'meta': meta, 'train_rows': int(train_x.shape[0]), 'best_val_loss': float(artifact.best_val_loss)}


def make_policy(memory: dict[str, Any], params: CX9CCPFParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    if memory.get('artifact', None) is None:
        return None
    model = memory['model']; meta = memory['meta']
    stride = int(max(params.stride_cells, 1))
    gh = int(math.ceil(case['occupancy'].shape[0] / stride))
    gw = int(math.ceil(case['occupancy'].shape[1] / stride))
    yaw_clusters = int(max(params.yaw_clusters, 1))
    feats = []
    coords = []
    for yaw_bin in range(yaw_clusters):
        yaw = -np.pi + (yaw_bin + 0.5) * (2.0 * np.pi / yaw_clusters)
        for gy in range(gh):
            for gx in range(gw):
                x = (gx * stride + 0.5 * stride) * float(case['resolution'])
                y = (gy * stride + 0.5 * stride) * float(case['resolution'])
                x = float(min(x, (case['occupancy'].shape[1] - 0.5) * float(case['resolution'])))
                y = float(min(y, (case['occupancy'].shape[0] - 0.5) * float(case['resolution'])))
                feat = build_compact_bundle_feature_vector(case, bundle, field, (x, y, yaw), prev_steer=0.0)
                feats.append(feat)
                coords.append((yaw_bin, gy, gx))
    logits = predict_logits(model, meta, np.stack(feats, axis=0), device)
    modes = np.argmax(logits, axis=1).astype(np.int16)
    mode_map = np.zeros((yaw_clusters, gh, gw), dtype=np.int16)
    for mode, (yaw_bin, gy, gx) in zip(modes, coords):
        mode_map[yaw_bin, gy, gx] = int(mode)
    return CPFPolicy(case, mode_map, params)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX9CCPFParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX9CCPFParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)
