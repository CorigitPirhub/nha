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
    current_progress,
    increment_novelty,
    novelty_count,
    state_signature,
)


@dataclass(frozen=True)
class CX14CMHQParams:
    novelty_penalty: float
    trap_weight: float
    corridor_bonus: float
    stagnation_window: int
    switch_progress: float


def param_grid() -> list[CX14CMHQParams]:
    return [
        CX14CMHQParams(0.08, 0.05, 0.03, 4, 0.02),
        CX14CMHQParams(0.10, 0.06, 0.04, 5, 0.01),
        CX14CMHQParams(0.12, 0.07, 0.05, 6, 0.00),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'Static-Mix', 'disable_switch': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX14CMHQParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'mhq_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'best_val_loss': float('nan')}


class MHQPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX14CMHQParams, disable_switch: bool = False) -> None:
        self.case = case
        self.bundle = augmented_bundle(bundle)
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_switch = bool(disable_switch)
        self.spec = SignatureSpec()
        self.slot = '_cx14_mhq_counts'

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        sig = state_signature(self.case, self.bundle, (float(record.x), float(record.y), float(record.yaw)), self.spec)
        progress = current_progress(self.case, self.field, record, records, depth=int(max(self.params.stagnation_window, 1)))
        phase = 0 if self.disable_switch or float(progress) > float(self.params.switch_progress) else 1
        return {'sig': sig, 'phase': int(phase)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        ranked = []
        phase = int(node_ctx.get('phase', 0)) if isinstance(node_ctx, dict) else 0
        for cand in candidates:
            sig = state_signature(self.case, self.bundle, cand.next_state, self.spec)
            repeats = novelty_count(search_state, sig, self.slot)
            x, y, _ = cand.next_state
            trap = float(self.bundle['_cx14_trap'][int(np.clip(np.floor(y / self.case['resolution']), 0, self.bundle['_cx14_trap'].shape[0]-1)), int(np.clip(np.floor(x / self.case['resolution']), 0, self.bundle['_cx14_trap'].shape[1]-1))])
            corr = float(self.bundle['_cx14_corridor_score'][int(np.clip(np.floor(y / self.case['resolution']), 0, self.bundle['_cx14_corridor_score'].shape[0]-1)), int(np.clip(np.floor(x / self.case['resolution']), 0, self.bundle['_cx14_corridor_score'].shape[1]-1))])
            if phase == 0:
                delta = float(self.params.novelty_penalty) * float(repeats) + float(self.params.trap_weight) * trap - float(self.params.corridor_bonus) * corr
            else:
                delta = 0.5 * float(self.params.novelty_penalty) * float(repeats) + 1.5 * float(self.params.trap_weight) * trap - 0.5 * float(self.params.corridor_bonus) * corr
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        sig = node_ctx.get('sig', None) if isinstance(node_ctx, dict) else None
        if sig is not None:
            increment_novelty(search_state, tuple(sig), self.slot)


def make_policy(memory: dict[str, Any], params: CX14CMHQParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    return MHQPolicy(case, bundle, field, params, disable_switch=bool(isinstance(ablation, dict) and ablation.get('disable_switch', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX14CMHQParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx14_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX14CMHQParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)

