from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10.common import (
    FEATURE_INDEX,
    build_compact_bundle_feature_vector,
    collect_compilation_rows,
    default_nonholonomic_field,
    default_standard_field,
    fit_rulebook,
    predict_rulebook,
    primitive_index_from_case,
    primitive_priority_delta,
)


@dataclass(frozen=True)
class CX10ACECParams:
    regime_floor: float
    teacher_conf_floor: float
    sample_stride: int
    similarity_thr: float
    bottleneck_thr: float
    misc_margin: float
    mode_strength: float
    support_slack: float
    allow_reverse_low_escape: bool


DEFAULT_TEACHER = Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json')


def param_grid() -> list[CX10ACECParams]:
    return [
        CX10ACECParams(0.40, 0.50, 1, 0.24, 0.40, 0.04, 0.26, 0.00, False),
        CX10ACECParams(0.38, 0.48, 1, 0.22, 0.38, 0.06, 0.24, 0.02, False),
        CX10ACECParams(0.42, 0.52, 2, 0.26, 0.42, 0.04, 0.28, 0.00, False),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {
            'name': 'No-Abstain',
            'overrides': {
                'similarity_thr': 0.12,
                'bottleneck_thr': 0.30,
                'misc_margin': 0.50,
                'allow_reverse_low_escape': True,
            },
        },
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX10ACECParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher_memory = (dependencies or {}).get('teacher_memory', None)
    if teacher_memory is None:
        raise ValueError('CX10-A requires frozen CX8-D teacher memory')
    rows = collect_compilation_rows(
        calib_train_assets,
        teacher_memory,
        regime_floor=float(params.regime_floor),
        teacher_conf_floor=float(params.teacher_conf_floor),
        sample_stride=int(params.sample_stride),
    )
    bank = fit_rulebook(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'num_rows': int(len(rows)),
        'counts': {str(k): int(v) for k, v in bank.get('counts', {}).items()},
        'teacher_chosen_json': str((dependencies or {}).get('teacher_chosen_json', DEFAULT_TEACHER)),
        'regime_floor': float(params.regime_floor),
        'teacher_conf_floor': float(params.teacher_conf_floor),
    }
    (out_dir / 'rulebook_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'bank': bank,
        'train_rows': int(len(rows)),
        'best_val_loss': float('nan'),
    }


class CECPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, bank: dict[str, Any], params: CX10ACECParams) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.bank = bank
        self.params = params
        self.primitive_index = primitive_index_from_case(case)
        self.scene_misc = float(bundle.get('scene', {}).get('misc_likelihood', 0.0))
        self.scene_hard = float(bundle.get('scene', {}).get('hard_likelihood', 0.0))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        feat = build_compact_bundle_feature_vector(
            self.case,
            self.bundle,
            self.field,
            (float(record.x), float(record.y), float(record.yaw)),
            prev_steer=float(record.steer),
            primitive_index=self.primitive_index,
        )
        pred = predict_rulebook(
            feat,
            self.bank,
            similarity_thr=float(max(self.params.similarity_thr - self.params.support_slack, 0.0)),
            bottleneck_thr=float(self.params.bottleneck_thr),
            misc_margin=float(self.params.misc_margin),
            allow_reverse_with_low_escape=bool(self.params.allow_reverse_low_escape),
        )
        return {
            'mode': int(pred.get('mode', 0)),
            'confidence': float(pred.get('confidence', 0.0)),
            'similarity': float(pred.get('similarity', 0.0)),
            'bottleneck': float(feat[FEATURE_INDEX['bottleneck']]),
        }

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        mode = int(node_ctx.get('mode', 0)) if isinstance(node_ctx, dict) else 0
        conf = float(node_ctx.get('confidence', 0.0)) if isinstance(node_ctx, dict) else 0.0
        bottleneck = float(node_ctx.get('bottleneck', 0.0)) if isinstance(node_ctx, dict) else 0.0
        strength = float(self.params.mode_strength) * (0.35 + 0.65 * conf) * max(0.25, bottleneck)
        ranked = []
        for cand in candidates:
            delta = primitive_priority_delta(self.case, int(cand.primitive_index), int(mode), float(strength))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def _apply_overrides(params: CX10ACECParams, overrides: dict[str, Any] | None) -> CX10ACECParams:
    if not overrides:
        return params
    return replace(params, **overrides)


def make_policy(memory: dict[str, Any], params: CX10ACECParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    cur = _apply_overrides(params, ablation.get('overrides') if isinstance(ablation, dict) else None)
    return CECPolicy(case, bundle, field, memory['bank'], cur)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX10ACECParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_nonholonomic_field(case, predictor, cfg)


def build_standard_field(sample, predictor, params: CX10ACECParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_standard_field(sample, predictor)
