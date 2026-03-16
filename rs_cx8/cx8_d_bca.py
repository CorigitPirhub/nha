from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_cx8.common import (
    BUNDLE_LABELS,
    FitArtifact,
    bottleneck_regime_score,
    build_compact_bundle_feature_vector,
    bundle_target_from_trace,
    fit_multiclass_model,
    load_fit_model,
    primitive_index_from_case,
    query_yaw_field,
)


@dataclass(frozen=True)
class CX8BCAParams:
    patch_radius: int
    hidden_dim: int
    bottleneck_gate: float
    activation_gate: float
    bundle_conf_thr: float
    bundle_scale: float
    learning_rate: float
    weight_decay: float
    epochs: int
    batch_size: int


def param_grid() -> list[CX8BCAParams]:
    return [
        CX8BCAParams(0, 32, 0.42, 0.62, 0.58, 0.22, 1e-3, 1e-4, 45, 128),
        CX8BCAParams(0, 40, 0.50, 0.70, 0.58, 0.34, 8e-4, 1e-4, 50, 128),
        CX8BCAParams(0, 48, 0.55, 0.75, 0.62, 0.42, 8e-4, 3e-4, 55, 128),
    ]


def _dataset_from_assets(assets: list[dict[str, Any]], params: CX8BCAParams) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    for item in assets:
        result = item['baseline_result']
        trace = item.get('trace', [])
        if not bool(result.success) or len(trace) <= 1:
            continue
        path = np.asarray(result.path, dtype=np.float32)
        pindex = primitive_index_from_case(item['case'])
        prev_steer = 0.0
        for t in range(min(len(trace), path.shape[0] - 2)):
            state = tuple(float(v) for v in path[t])
            target = bundle_target_from_trace(trace, t, pindex)
            score = bottleneck_regime_score(item['case'], item['bundle'], item['field'], state)
            if target is None and score < float(params.bottleneck_gate):
                chosen_idx = int(trace[t])
                prev_steer = pindex.actual_steer(int(chosen_idx), np.radians(float(item['case']['vehicle'].max_steer_deg)))
                continue
            if target is None:
                continue
            xs.append(build_compact_bundle_feature_vector(item['case'], item['bundle'], item['field'], state, prev_steer=prev_steer))
            ys.append(int(target))
            chosen_idx = int(trace[t])
            prev_steer = pindex.actual_steer(int(chosen_idx), np.radians(float(item['case']['vehicle'].max_steer_deg)))
    if not xs:
        return np.zeros((0, 1), dtype=np.float32), np.zeros((0,), dtype=np.int64)
    return np.stack(xs, axis=0).astype(np.float32), np.asarray(ys, dtype=np.int64)


class BCAPolicy:
    def __init__(self, model, meta: dict[str, Any], params: CX8BCAParams, device: str) -> None:
        import torch
        self.model = model
        self.meta = meta
        self.params = params
        self.device = str(device)
        self.mean = np.asarray(meta['mean'], dtype=np.float32)[None, :]
        self.std = np.asarray(meta['std'], dtype=np.float32)[None, :]
        self.std[self.std < 1e-6] = 1.0
        self._torch = torch

    def _predict_logits(self, feat: np.ndarray) -> np.ndarray:
        arr = ((np.asarray(feat, dtype=np.float32) - self.mean) / self.std).astype(np.float32)
        with self._torch.no_grad():
            out = self.model(self._torch.from_numpy(arr).to(self.device)).detach().cpu().numpy()
        return out.astype(np.float32)

    def _progress_certificate(self, record, records, planner) -> bool:
        if record.parent is None or record.parent not in records:
            return False
        parent = records[record.parent]
        case = getattr(self, 'case')
        field = getattr(self, 'field')
        cur_anchor = query_yaw_field(field, float(record.x), float(record.y), float(record.yaw), float(case['resolution']))
        par_anchor = query_yaw_field(field, float(parent.x), float(parent.y), float(parent.yaw), float(case['resolution']))
        cur_clear = float(planner.esdf[int(np.clip(np.floor(record.y / planner.resolution), 0, planner.h - 1)), int(np.clip(np.floor(record.x / planner.resolution), 0, planner.w - 1))])
        par_clear = float(planner.esdf[int(np.clip(np.floor(parent.y / planner.resolution), 0, planner.h - 1)), int(np.clip(np.floor(parent.x / planner.resolution), 0, planner.w - 1))])
        return bool((cur_anchor <= par_anchor + 0.05) and (cur_clear >= par_clear - 0.05))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        case = getattr(self, 'case', None)
        bundle = getattr(self, 'bundle', None)
        field = getattr(self, 'field', None)
        if case is None or bundle is None or field is None:
            return None
        state = (float(record.x), float(record.y), float(record.yaw))
        regime = bottleneck_regime_score(case, bundle, field, state)
        invalid_ratio = float(search_state.get('invalid_successors', 0)) / max(float(search_state.get('valid_successors', 0) + search_state.get('invalid_successors', 0)), 1.0)
        activation = 0.65 * float(regime) + 0.35 * float(invalid_ratio)
        if activation < float(self.params.activation_gate) or regime < float(self.params.bottleneck_gate):
            return {'bundle_id': None, 'bundle_conf': 0.0, 'regime': float(regime), 'activation': float(activation)}
        feat = build_compact_bundle_feature_vector(case, bundle, field, state, prev_steer=float(record.steer))[None, :]
        logits = self._predict_logits(feat)[0]
        logits = logits[:len(BUNDLE_LABELS)]
        logits = logits - float(np.max(logits))
        probs = np.exp(logits)
        probs = probs / max(float(np.sum(probs)), 1e-6)
        bundle_id = int(np.argmax(probs))
        bundle_conf = float(probs[bundle_id])
        if bundle_conf < float(self.params.bundle_conf_thr):
            bundle_id = None
        return {'bundle_id': bundle_id, 'bundle_conf': bundle_conf, 'regime': float(regime), 'activation': float(activation), 'probs': probs.astype(np.float32)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        bundle_id = node_ctx.get('bundle_id', None)
        conf = float(node_ctx.get('bundle_conf', 0.0))
        regime = float(node_ctx.get('regime', 0.0))
        activation = float(node_ctx.get('activation', regime))
        if bundle_id is None:
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        pindex = self.primitive_index
        progress_ok = self._progress_certificate(record, records, planner)
        ranked = []
        for cand in candidates:
            level, dirn = pindex.to_level_direction(int(cand.primitive_index))
            match = 0.0
            if int(bundle_id) == 0:
                if dirn > 0 and level < -1e-6:
                    match = 1.0
                elif dirn > 0 and abs(level) <= 1e-6:
                    match = 0.35
                else:
                    match = -0.2
            elif int(bundle_id) == 1:
                if dirn > 0 and level > 1e-6:
                    match = 1.0
                elif dirn > 0 and abs(level) <= 1e-6:
                    match = 0.35
                else:
                    match = -0.2
            elif int(bundle_id) == 2:
                if record.direction < 0 and record.steer < -0.10 * planner.max_steer and progress_ok:
                    if dirn > 0 and level < -1e-6:
                        match = 1.0
                    elif dirn > 0 and abs(level) <= 1e-6:
                        match = 0.25
                    else:
                        match = -0.1
                else:
                    if dirn < 0 and level < -1e-6:
                        match = 1.0
                    elif dirn < 0 and abs(level) <= 1e-6:
                        match = 0.25
                    else:
                        match = -0.1
            elif int(bundle_id) == 3:
                if record.direction < 0 and record.steer > 0.10 * planner.max_steer and progress_ok:
                    if dirn > 0 and level > 1e-6:
                        match = 1.0
                    elif dirn > 0 and abs(level) <= 1e-6:
                        match = 0.25
                    else:
                        match = -0.1
                else:
                    if dirn < 0 and level > 1e-6:
                        match = 1.0
                    elif dirn < 0 and abs(level) <= 1e-6:
                        match = 0.25
                    else:
                        match = -0.1
            delta = -float(self.params.bundle_scale) * float(conf) * float(activation) * float(match)
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX8BCAParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
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


def make_policy(memory: dict[str, Any], params: CX8BCAParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    if memory.get('artifact', None) is None:
        return None
    policy = BCAPolicy(memory['model'], memory['meta'], params, device)
    policy.case = case
    policy.bundle = bundle
    policy.field = field
    policy.primitive_index = primitive_index_from_case(case)
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX8BCAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX8BCAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)


def ablation_policies(memory: dict[str, Any], params: CX8BCAParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str) -> dict[str, Any]:
    out = {}
    learned = make_policy(memory, params, case, bundle, field, device)
    if learned is not None:
        out['learned'] = learned
    out['detector_only'] = None
    return out
