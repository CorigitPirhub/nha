from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx8.common import (
    BUNDLE_LABELS,
    FitArtifact,
    bottleneck_regime_score,
    build_bundle_feature_vector,
    load_fit_model,
    predict_logits,
    primitive_index_from_case,
    query_yaw_field,
)


@dataclass(frozen=True)
class CX8DHeavyParams:
    patch_radius: int
    hidden_dim: int
    bottleneck_gate: float
    bundle_conf_thr: float
    bundle_scale: float
    learning_rate: float
    weight_decay: float
    epochs: int
    batch_size: int


def params_from_chosen(chosen_json: Path) -> CX8DHeavyParams:
    data = json.loads(chosen_json.read_text(encoding='utf-8'))
    return CX8DHeavyParams(**data['params'])


def load_locked_memory(chosen_json: Path, device: str) -> dict[str, Any]:
    data = json.loads(chosen_json.read_text(encoding='utf-8'))
    params = CX8DHeavyParams(**data['params'])
    fit_dir = Path(data['fit_dir'])
    artifact = FitArtifact(
        model_path=fit_dir / 'model.pt',
        meta_path=fit_dir / 'model_meta.json',
        best_val_loss=float(data.get('best_val_loss', float('nan'))),
        input_dim=0,
        output_dim=0,
    )
    model, meta = load_fit_model(artifact, device)
    return {
        'artifact': artifact,
        'model': model,
        'meta': meta,
        'params': params,
        'chosen': data,
    }


class HeavyPolicy:
    def __init__(self, model, meta: dict[str, Any], params: CX8DHeavyParams, device: str) -> None:
        self.model = model
        self.meta = meta
        self.params = params
        self.device = str(device)
        self.case = None
        self.bundle = None
        self.field = None
        self.primitive_index = None

    def _progress_certificate(self, record, records, planner) -> bool:
        if record.parent is None or record.parent not in records:
            return False
        parent = records[record.parent]
        cur_anchor = query_yaw_field(self.field, float(record.x), float(record.y), float(record.yaw), float(self.case['resolution']))
        par_anchor = query_yaw_field(self.field, float(parent.x), float(parent.y), float(parent.yaw), float(self.case['resolution']))
        cur_clear = float(planner.esdf[int(np.clip(np.floor(record.y / planner.resolution), 0, planner.h - 1)), int(np.clip(np.floor(record.x / planner.resolution), 0, planner.w - 1))])
        par_clear = float(planner.esdf[int(np.clip(np.floor(parent.y / planner.resolution), 0, planner.h - 1)), int(np.clip(np.floor(parent.x / planner.resolution), 0, planner.w - 1))])
        return bool((cur_anchor <= par_anchor + 0.05) and (cur_clear >= par_clear - 0.05))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        state = (float(record.x), float(record.y), float(record.yaw))
        regime = bottleneck_regime_score(self.case, self.bundle, self.field, state)
        if regime < float(self.params.bottleneck_gate):
            return {'bundle_id': None, 'bundle_conf': 0.0, 'regime': float(regime)}
        feat = build_bundle_feature_vector(self.case, self.bundle, self.field, state, prev_steer=float(record.steer), patch_radius=int(self.params.patch_radius))[None, :]
        logits = predict_logits(self.model, self.meta, feat, self.device)[0]
        logits = logits[:len(BUNDLE_LABELS)]
        logits = logits - float(np.max(logits))
        probs = np.exp(logits)
        probs = probs / max(float(np.sum(probs)), 1e-6)
        bundle_id = int(np.argmax(probs))
        bundle_conf = float(probs[bundle_id])
        if bundle_conf < float(self.params.bundle_conf_thr):
            bundle_id = None
        return {'bundle_id': bundle_id, 'bundle_conf': bundle_conf, 'regime': float(regime), 'probs': probs.astype(np.float32)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        bundle_id = node_ctx.get('bundle_id', None)
        conf = float(node_ctx.get('bundle_conf', 0.0))
        regime = float(node_ctx.get('regime', 0.0))
        if bundle_id is None:
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        progress_ok = self._progress_certificate(record, records, planner)
        ranked = []
        for cand in candidates:
            level, dirn = self.primitive_index.to_level_direction(int(cand.primitive_index))
            match = 0.0
            if int(bundle_id) == 0:  # forward_left_thread
                if dirn > 0 and level < -1e-6:
                    match = 1.0
                elif dirn > 0 and abs(level) <= 1e-6:
                    match = 0.35
                else:
                    match = -0.2
            elif int(bundle_id) == 1:  # forward_right_thread
                if dirn > 0 and level > 1e-6:
                    match = 1.0
                elif dirn > 0 and abs(level) <= 1e-6:
                    match = 0.35
                else:
                    match = -0.2
            elif int(bundle_id) == 2:  # reverse_setup_left
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
            elif int(bundle_id) == 3:  # reverse_setup_right
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
            delta = -float(self.params.bundle_scale) * float(conf) * float(regime) * float(match)
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy_from_locked(memory: dict[str, Any], case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str):
    policy = HeavyPolicy(memory['model'], memory['meta'], memory['params'], device)
    policy.case = case
    policy.bundle = bundle
    policy.field = field
    policy.primitive_index = primitive_index_from_case(case)
    return policy
