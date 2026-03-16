from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_cx8.common import (
    FitArtifact,
    build_state_cache,
    build_state_vector,
    fit_multiclass_model,
    load_fit_model,
    predict_logits,
    primitive_index_from_case,
)


@dataclass(frozen=True)
class CX8APPParams:
    patch_radius: int
    hidden_dim: int
    prior_scale: float
    learning_rate: float
    weight_decay: float
    epochs: int
    batch_size: int


def param_grid() -> list[CX8APPParams]:
    return [
        CX8APPParams(5, 96, 0.45, 1e-3, 1e-4, 60, 128),
        CX8APPParams(6, 128, 0.55, 1e-3, 1e-4, 70, 128),
        CX8APPParams(5, 128, 0.65, 7e-4, 3e-4, 80, 128),
    ]


def _dataset_from_assets(assets: list[dict[str, Any]], params: CX8APPParams) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    for item in assets:
        result = item['baseline_result']
        trace = item.get('trace', [])
        if not bool(result.success) or len(trace) <= 0:
            continue
        path = np.asarray(result.path, dtype=np.float32)
        pindex = primitive_index_from_case(item['case'])
        prev_steer = 0.0
        for t, primitive_idx in enumerate(trace):
            if t >= path.shape[0] - 1:
                break
            state = tuple(float(v) for v in path[t])
            xs.append(build_state_vector(item['case'], item['bundle'], item['field'], state, prev_steer=prev_steer, patch_radius=int(params.patch_radius)))
            ys.append(int(primitive_idx))
            prev_steer = pindex.actual_steer(int(primitive_idx), math.radians(float(item['case']['vehicle'].max_steer_deg)))
    if not xs:
        return np.zeros((0, 1), dtype=np.float32), np.zeros((0,), dtype=np.int64)
    return np.stack(xs, axis=0).astype(np.float32), np.asarray(ys, dtype=np.int64)


class APPPolicy:
    def __init__(self, model, meta: dict[str, Any], params: CX8APPParams, device: str) -> None:
        self.model = model
        self.meta = meta
        self.params = params
        self.device = str(device)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        case = getattr(self, 'case', None)
        bundle = getattr(self, 'bundle', None)
        field = getattr(self, 'field', None)
        if case is None or bundle is None or field is None:
            probs = np.ones(len(planner.motion_primitives), dtype=np.float32) / max(len(planner.motion_primitives), 1)
            return {'probs': probs, 'state_cache': None}
        state = (float(record.x), float(record.y), float(record.yaw))
        state_cache = build_state_cache(case, bundle, field, state, prev_steer=float(record.steer), patch_radius=int(self.params.patch_radius))
        feat = np.asarray(state_cache['state_vec'], dtype=np.float32)[None, :]
        logits = predict_logits(self.model, self.meta, feat, self.device)[0]
        logits = logits[:len(planner.motion_primitives)]
        logits = logits - float(np.max(logits))
        probs = np.exp(logits)
        probs = probs / max(float(np.sum(probs)), 1e-6)
        return {'probs': probs.astype(np.float32), 'state_cache': state_cache}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        probs = None if not isinstance(node_ctx, dict) else node_ctx.get('probs', None)
        if probs is None:
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        ranked = []
        for cand in candidates:
            prob = float(np.clip(np.asarray(probs, dtype=np.float32)[int(cand.primitive_index)], 1e-5, 1.0))
            delta = -float(self.params.prior_scale) * math.log(prob)
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX8APPParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    train_x, train_y = _dataset_from_assets(calib_train_assets, params)
    val_x, val_y = _dataset_from_assets(calib_val_assets, params)
    out_dir.mkdir(parents=True, exist_ok=True)
    if train_x.shape[0] == 0 or val_x.shape[0] == 0:
        return {'artifact': None, 'train_samples': int(train_x.shape[0]), 'val_samples': int(val_x.shape[0]), 'best_val_loss': float('inf')}
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
    return {
        'artifact': artifact,
        'model': model,
        'meta': meta,
        'params': params.__dict__,
        'train_samples': int(train_x.shape[0]),
        'val_samples': int(val_x.shape[0]),
        'best_val_loss': float(artifact.best_val_loss),
    }


def make_policy(memory: dict[str, Any], params: CX8APPParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    if memory.get('artifact', None) is None:
        return None
    model = memory['model']
    meta = memory['meta']
    policy = APPPolicy(model, meta, params, device)
    policy.case = case
    policy.bundle = bundle
    policy.field = field
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX8APPParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX8APPParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)


def ablation_policies(memory: dict[str, Any], params: CX8APPParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str) -> dict[str, Any]:
    out = {}
    learned = make_policy(memory, params, case, bundle, field, device)
    if learned is not None:
        out['learned'] = learned
    out['uniform'] = None
    return out
