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
    build_state_vector,
    bottleneck_regime_score,
    fit_multiclass_model,
    forward_escape_fraction,
    load_fit_model,
    predict_logits,
    primitive_index_from_case,
    reverse_escape_fraction,
)
from rs_cx8 import cx8_a_app, cx8_b_kfm, cx8_d_bca


@dataclass(frozen=True)
class CX8TDGParams:
    patch_radius: int
    hidden_dim: int
    mode_conf_thr: float
    learning_rate: float
    weight_decay: float
    epochs: int
    batch_size: int


def param_grid() -> list[CX8TDGParams]:
    return [
        CX8TDGParams(5, 96, 0.45, 1e-3, 1e-4, 60, 128),
        CX8TDGParams(5, 128, 0.50, 8e-4, 1e-4, 70, 128),
        CX8TDGParams(6, 128, 0.55, 8e-4, 3e-4, 80, 128),
    ]


def _online_feature_vector(case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, state: tuple[float, float, float], prev_steer: float, patch_radius: int, *, invalid_ratio: float, accepted_ratio: float, depth_norm: float, open_entropy: float) -> np.ndarray:
    base = build_state_vector(case, bundle, field, state, prev_steer=prev_steer, patch_radius=patch_radius)
    pindex = primitive_index_from_case(case)
    bottleneck = bottleneck_regime_score(case, bundle, field, state)
    rev_escape = reverse_escape_fraction(case, state, pindex)
    fwd_escape = forward_escape_fraction(case, state, pindex)
    extras = np.asarray([
        float(invalid_ratio),
        float(accepted_ratio),
        float(depth_norm),
        float(open_entropy),
        float(bottleneck),
        float(rev_escape),
        float(fwd_escape),
    ], dtype=np.float32)
    return np.concatenate([base, extras], axis=0).astype(np.float32)


def _pseudo_label(case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, state: tuple[float, float, float], invalid_ratio: float) -> int:
    pindex = primitive_index_from_case(case)
    bottleneck = bottleneck_regime_score(case, bundle, field, state)
    rev_escape = reverse_escape_fraction(case, state, pindex)
    if bottleneck < 0.25 and invalid_ratio < 0.30:
        return 0  # baseline
    if bottleneck < 0.48:
        return 1  # APP
    if invalid_ratio > 0.55 or rev_escape < 0.18:
        return 2  # KFM
    return 3  # BCA


def _dataset_from_assets(assets: list[dict[str, Any]], params: CX8TDGParams) -> tuple[np.ndarray, np.ndarray]:
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
        for t in range(min(len(trace), path.shape[0] - 1)):
            state = tuple(float(v) for v in path[t])
            valid_flags = []
            for idx in range(len(pindex)):
                feat, meta = cx8_b_kfm.build_state_action_vector(item['case'], item['bundle'], item['field'], state, prev_steer=prev_steer, primitive_index=int(idx), patch_radius=int(params.patch_radius)) if False else (None, None)
            max_steer = np.radians(float(item['case']['vehicle'].max_steer_deg))
            for idx in range(len(pindex)):
                steer = pindex.actual_steer(int(idx), max_steer)
                direction = pindex.actual_direction(int(idx))
                sim = cx8_b_kfm.build_state_action_vector(item['case'], item['bundle'], item['field'], state, prev_steer=prev_steer, primitive_index=int(idx), patch_radius=int(params.patch_radius))[1]['sim']
                valid_flags.append(1.0 if bool(sim['valid']) else 0.0)
            invalid_ratio = 1.0 - float(np.mean(valid_flags)) if valid_flags else 0.0
            accepted_ratio = float(np.mean(valid_flags)) if valid_flags else 0.0
            depth_norm = float(t) / max(len(trace), 1)
            open_entropy = float(np.std(valid_flags)) if valid_flags else 0.0
            xs.append(_online_feature_vector(item['case'], item['bundle'], item['field'], state, prev_steer=prev_steer, patch_radius=int(params.patch_radius), invalid_ratio=invalid_ratio, accepted_ratio=accepted_ratio, depth_norm=depth_norm, open_entropy=open_entropy))
            ys.append(int(_pseudo_label(item['case'], item['bundle'], item['field'], state, invalid_ratio)))
            chosen_idx = int(trace[t])
            prev_steer = pindex.actual_steer(int(chosen_idx), max_steer)
    if not xs:
        return np.zeros((0, 1), dtype=np.float32), np.zeros((0,), dtype=np.int64)
    return np.stack(xs, axis=0).astype(np.float32), np.asarray(ys, dtype=np.int64)


class TDGPolicy:
    def __init__(self, model, meta: dict[str, Any], params: CX8TDGParams, device: str, delegates: dict[str, Any]) -> None:
        self.model = model
        self.meta = meta
        self.params = params
        self.device = str(device)
        self.delegates = delegates

    def _open_entropy(self, open_heap, records) -> float:
        vals = []
        for primary, _, _, key in open_heap[: min(len(open_heap), 32)]:
            rec = records.get(key)
            if rec is None:
                continue
            vals.append(float(primary))
        if len(vals) <= 1:
            return 0.0
        arr = np.asarray(vals, dtype=np.float32)
        arr = arr - np.min(arr)
        arr = np.exp(-arr / max(float(np.std(arr) + 1e-6), 1e-6))
        arr = arr / max(float(np.sum(arr)), 1e-6)
        return float(-np.sum(arr * np.log(np.clip(arr, 1e-6, 1.0))))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        case = getattr(self, 'case', None)
        bundle = getattr(self, 'bundle', None)
        field = getattr(self, 'field', None)
        if case is None or bundle is None or field is None:
            return {'mode_id': 0, 'delegate': None, 'delegate_ctx': None}
        denom = max(float(search_state.get('valid_successors', 0) + search_state.get('invalid_successors', 0)), 1.0)
        invalid_ratio = float(search_state.get('invalid_successors', 0)) / denom
        accepted_ratio = float(search_state.get('accepted_successors', 0)) / max(float(search_state.get('valid_successors', 0)), 1.0)
        depth_norm = float(record.depth) / 25.0
        open_entropy = self._open_entropy(open_heap, records)
        feat = _online_feature_vector(
            case,
            bundle,
            field,
            (float(record.x), float(record.y), float(record.yaw)),
            prev_steer=float(record.steer),
            patch_radius=int(self.params.patch_radius),
            invalid_ratio=invalid_ratio,
            accepted_ratio=accepted_ratio,
            depth_norm=depth_norm,
            open_entropy=open_entropy,
        )[None, :]
        logits = predict_logits(self.model, self.meta, feat, self.device)[0]
        logits = logits[:4]
        logits = logits - float(np.max(logits))
        probs = np.exp(logits)
        probs = probs / max(float(np.sum(probs)), 1e-6)
        mode_id = int(np.argmax(probs))
        if float(probs[mode_id]) < float(self.params.mode_conf_thr):
            mode_id = 0
        delegate_key = {1: 'APP', 2: 'KFM', 3: 'BCA'}.get(mode_id, None)
        delegate = self.delegates.get(delegate_key, None)
        delegate_ctx = None
        if delegate is not None and hasattr(delegate, 'prepare_expand'):
            delegate_ctx = delegate.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        return {'mode_id': mode_id, 'probs': probs.astype(np.float32), 'delegate': delegate, 'delegate_ctx': delegate_ctx}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        delegate = node_ctx.get('delegate', None)
        delegate_ctx = node_ctx.get('delegate_ctx', None)
        if delegate is None or not hasattr(delegate, 'rank_successors'):
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        return delegate.rank_successors(planner, record, goal, records, candidates, delegate_ctx, search_state, h_pair)


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX8TDGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    train_x, train_y = _dataset_from_assets(calib_train_assets, params)
    val_x, val_y = _dataset_from_assets(calib_val_assets, params)
    out_dir.mkdir(parents=True, exist_ok=True)
    if train_x.shape[0] == 0 or val_x.shape[0] == 0:
        return {'artifact': None, 'train_samples': int(train_x.shape[0]), 'val_samples': int(val_x.shape[0]), 'best_val_loss': float('inf'), 'dependencies': dependencies or {}}
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
        'dependencies': dependencies or {},
    }


def make_policy(memory: dict[str, Any], params: CX8TDGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    if memory.get('artifact', None) is None:
        return None
    deps = memory.get('dependencies', {})
    delegates = {}
    if 'APP' in deps and deps['APP'].get('memory') is not None:
        delegates['APP'] = cx8_a_app.make_policy(deps['APP']['memory'], deps['APP']['params'], case, bundle, field, device)
    if 'KFM' in deps and deps['KFM'].get('memory') is not None:
        delegates['KFM'] = cx8_b_kfm.make_policy(deps['KFM']['memory'], deps['KFM']['params'], case, bundle, field, device)
    if 'BCA' in deps and deps['BCA'].get('memory') is not None:
        delegates['BCA'] = cx8_d_bca.make_policy(deps['BCA']['memory'], deps['BCA']['params'], case, bundle, field, device)
    policy = TDGPolicy(memory['model'], memory['meta'], params, device, delegates)
    policy.case = case
    policy.bundle = bundle
    policy.field = field
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX8TDGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX8TDGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)


def ablation_policies(memory: dict[str, Any], params: CX8TDGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str) -> dict[str, Any]:
    out = {}
    learned = make_policy(memory, params, case, bundle, field, device)
    if learned is not None:
        out['learned'] = learned
    deps = memory.get('dependencies', {})
    if 'APP' in deps and deps['APP'].get('memory') is not None:
        out['fixed_app'] = cx8_a_app.make_policy(deps['APP']['memory'], deps['APP']['params'], case, bundle, field, device)
    if 'KFM' in deps and deps['KFM'].get('memory') is not None:
        out['fixed_kfm'] = cx8_b_kfm.make_policy(deps['KFM']['memory'], deps['KFM']['params'], case, bundle, field, device)
    if 'BCA' in deps and deps['BCA'].get('memory') is not None:
        out['fixed_bca'] = cx8_d_bca.make_policy(deps['BCA']['memory'], deps['BCA']['params'], case, bundle, field, device)
    out['baseline'] = None
    return out
