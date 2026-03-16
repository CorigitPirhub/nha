from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_cx8.common import bottleneck_regime_score
from rs_cx8.common import (
    FitArtifact,
    build_compact_state_cache,
    build_kfm_compact_action_vector_from_cache,
    build_state_action_vector,
    fit_multilabel_model,
    load_fit_model,
    predict_logits,
    primitive_index_from_case,
)


@dataclass(frozen=True)
class CX8KFMParams:
    patch_radius: int
    hidden_dim: int
    gate_threshold: float
    hard_threshold: float
    useful_threshold: float
    hard_margin_m: float
    soft_margin_m: float
    soft_penalty: float
    learning_rate: float
    weight_decay: float
    epochs: int
    batch_size: int


def param_grid() -> list[CX8KFMParams]:
    return [
        CX8KFMParams(5, 64, 0.35, 0.72, 0.42, 0.10, 0.35, 0.30, 1e-3, 1e-4, 60, 128),
        CX8KFMParams(5, 96, 0.42, 0.78, 0.38, 0.15, 0.40, 0.45, 8e-4, 1e-4, 70, 128),
        CX8KFMParams(6, 96, 0.50, 0.82, 0.35, 0.20, 0.45, 0.55, 8e-4, 3e-4, 80, 128),
    ]


def _dataset_from_assets(assets: list[dict[str, Any]], params: CX8KFMParams) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
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
            chosen_idx = int(trace[t])
            for primitive_idx in range(len(pindex)):
                state_cache = build_compact_state_cache(item['case'], item['bundle'], item['field'], state, prev_steer=prev_steer, primitive_index=pindex, escape_features=(0.0, 0.0))
                feat, meta = build_kfm_compact_action_vector_from_cache(item['case'], item['bundle'], item['field'], state_cache, int(primitive_idx))
                sim = meta['sim']
                valid = bool(sim['valid'])
                min_clearance = float(sim['min_clearance']) if valid else -1.0
                progress = float(meta['progress'])
                useful = 1.0 if int(primitive_idx) == chosen_idx else 0.0
                risky = 0.0
                if not valid:
                    risky = 1.0
                elif int(primitive_idx) != chosen_idx:
                    if min_clearance < float(params.soft_margin_m) or progress < 0.05:
                        risky = 1.0
                ys.append(np.asarray([useful, risky], dtype=np.float32))
                xs.append(feat.astype(np.float32))
            prev_steer = pindex.actual_steer(int(chosen_idx), np.radians(float(item['case']['vehicle'].max_steer_deg)))
    if not xs:
        return np.zeros((0, 1), dtype=np.float32), np.zeros((0, 2), dtype=np.float32)
    return np.stack(xs, axis=0).astype(np.float32), np.stack(ys, axis=0).astype(np.float32)


class KFMPolicy:
    requires_sim_stats = True

    def __init__(self, model, meta: dict[str, Any], params: CX8KFMParams, device: str) -> None:
        self.model = model
        self.meta = meta
        self.params = params
        self.device = str(device)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        case = getattr(self, 'case', None)
        bundle = getattr(self, 'bundle', None)
        field = getattr(self, 'field', None)
        if case is None or bundle is None or field is None:
            return {'state_cache': None}
        state = (float(record.x), float(record.y), float(record.yaw))
        regime = bottleneck_regime_score(case, bundle, field, state)
        if float(regime) < float(self.params.gate_threshold):
            return {'state_cache': None, 'regime': float(regime), 'gated_off': True}
        state_cache = build_compact_state_cache(case, bundle, field, state, prev_steer=float(record.steer), escape_features=(0.0, 0.0))
        return {'state_cache': state_cache, 'regime': float(regime), 'gated_off': False}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        case = getattr(self, 'case', None)
        bundle = getattr(self, 'bundle', None)
        field = getattr(self, 'field', None)
        state_cache = None if not isinstance(node_ctx, dict) else node_ctx.get('state_cache', None)
        if case is None or bundle is None or field is None or state_cache is None or not candidates:
            return [(cand, {'skip': False}) for cand in candidates]
        total_reverse = max(sum(1 for _, d in planner.motion_primitives if int(d) < 0), 1)
        total_forward = max(sum(1 for _, d in planner.motion_primitives if int(d) > 0), 1)
        reverse_valid = float(sum(1 for cand in candidates if int(cand.direction) < 0)) / float(total_reverse)
        forward_valid = float(sum(1 for cand in candidates if int(cand.direction) > 0)) / float(total_forward)
        state_cache = dict(state_cache)
        state_cache['state_vec'] = np.asarray(state_cache['state_vec'], dtype=np.float32).copy()
        state_cache['state_vec'][-2] = float(reverse_valid)
        state_cache['state_vec'][-1] = float(forward_valid)
        state_cache['reverse_escape'] = float(reverse_valid)
        state_cache['forward_escape'] = float(forward_valid)
        feat_rows = []
        metas = []
        for cand in candidates:
            feat, meta = build_kfm_compact_action_vector_from_cache(
                case, bundle, field, state_cache, int(cand.primitive_index), sim=cand.sim_info or {}, next_state=cand.next_state
            )
            feat_rows.append(feat)
            metas.append(meta)
        logits = predict_logits(self.model, self.meta, np.stack(feat_rows, axis=0), self.device)
        ranked = []
        for cand, meta, logit in zip(candidates, metas, logits):
            useful_logit = float(np.clip(logit[0], -20.0, 20.0))
            risk_logit = float(np.clip(logit[1], -20.0, 20.0))
            useful_prob = float(1.0 / (1.0 + np.exp(-useful_logit)))
            risk_prob = float(1.0 / (1.0 + np.exp(-risk_logit)))
            sim = meta['sim']
            margin = float(sim.get('min_clearance', -1.0)) - float(planner.vehicle_clearance) - float(self.params.hard_margin_m)
            decision = {'skip': False, 'extra_edge_cost': 0.0}
            if margin < 0.0 and risk_prob >= float(self.params.hard_threshold) and useful_prob <= float(self.params.useful_threshold):
                decision['skip'] = True
            else:
                soft_gap = max(float(self.params.soft_margin_m) - max(float(sim.get('min_clearance', -1.0)) - float(planner.vehicle_clearance), 0.0), 0.0)
                decision['extra_edge_cost'] = float(self.params.soft_penalty) * max(risk_prob - useful_prob, 0.0) * soft_gap
            ranked.append((cand, decision))
        return ranked


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX8KFMParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    train_x, train_y = _dataset_from_assets(calib_train_assets, params)
    val_x, val_y = _dataset_from_assets(calib_val_assets, params)
    out_dir.mkdir(parents=True, exist_ok=True)
    if train_x.shape[0] == 0 or val_x.shape[0] == 0:
        return {'artifact': None, 'train_samples': int(train_x.shape[0]), 'val_samples': int(val_x.shape[0]), 'best_val_loss': float('inf')}
    artifact: FitArtifact = fit_multilabel_model(
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


def make_policy(memory: dict[str, Any], params: CX8KFMParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    if memory.get('artifact', None) is None:
        return None
    policy = KFMPolicy(memory['model'], memory['meta'], params, device)
    policy.case = case
    policy.bundle = bundle
    policy.field = field
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX8KFMParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX8KFMParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return field.astype(np.float32)


def ablation_policies(memory: dict[str, Any], params: CX8KFMParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str) -> dict[str, Any]:
    out = {}
    learned = make_policy(memory, params, case, bundle, field, device)
    if learned is not None:
        out['learned'] = learned
        soft_only = make_policy(memory, params, case, bundle, field, device)
        soft_only.params = CX8KFMParams(**{**params.__dict__, 'hard_threshold': 1.1})
        out['soft_only'] = soft_only
    out['analytic_only'] = None
    return out
