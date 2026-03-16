from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx14.common import (
    SignatureSpec,
    augmented_bundle,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    increment_novelty,
    novelty_count,
    state_signature,
)


@dataclass(frozen=True)
class CX14ANSGParams:
    repeat_penalty: float
    novelty_bonus: float
    trap_weight: float
    corridor_weight: float


def param_grid() -> list[CX14ANSGParams]:
    return [
        CX14ANSGParams(0.08, 0.04, 0.05, 0.03),
        CX14ANSGParams(0.10, 0.05, 0.06, 0.04),
        CX14ANSGParams(0.12, 0.06, 0.08, 0.05),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Novelty', 'disable_novelty': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX14ANSGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'nsg_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'best_val_loss': float('nan')}


class NSGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], params: CX14ANSGParams, disable_novelty: bool = False) -> None:
        self.case = case
        self.bundle = augmented_bundle(bundle)
        self.params = params
        self.disable_novelty = bool(disable_novelty)
        self.slot = '_cx14_nsg_counts'
        self.spec = SignatureSpec()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        sig = state_signature(self.case, self.bundle, (float(record.x), float(record.y), float(record.yaw)), self.spec)
        return {'sig': sig}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        ranked = []
        for cand in candidates:
            sig = state_signature(self.case, self.bundle, cand.next_state, self.spec)
            repeats = novelty_count(search_state, sig, self.slot)
            delta = 0.0
            if not self.disable_novelty:
                delta += float(self.params.repeat_penalty) * float(repeats)
                if repeats == 0:
                    delta -= float(self.params.novelty_bonus)
            x, y, _ = cand.next_state
            trap = float(self.bundle['_cx14_trap'][int(np.clip(np.floor(y / self.case['resolution']), 0, self.bundle['_cx14_trap'].shape[0]-1)), int(np.clip(np.floor(x / self.case['resolution']), 0, self.bundle['_cx14_trap'].shape[1]-1))])
            corr = float(self.bundle['_cx14_corridor_score'][int(np.clip(np.floor(y / self.case['resolution']), 0, self.bundle['_cx14_corridor_score'].shape[0]-1)), int(np.clip(np.floor(x / self.case['resolution']), 0, self.bundle['_cx14_corridor_score'].shape[1]-1))])
            delta += float(self.params.trap_weight) * trap
            delta -= float(self.params.corridor_weight) * corr
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        sig = node_ctx.get('sig', None) if isinstance(node_ctx, dict) else None
        if sig is not None:
            increment_novelty(search_state, tuple(sig), self.slot)


def make_policy(memory: dict[str, Any], params: CX14ANSGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    return NSGPolicy(case, bundle, params, disable_novelty=bool(isinstance(ablation, dict) and ablation.get('disable_novelty', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX14ANSGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx14_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX14ANSGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)

