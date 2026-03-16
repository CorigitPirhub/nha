from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10.common import (
    FEATURE_INDEX,
    REVERSE_LABELS,
    build_compact_bundle_feature_vector,
    bundle_side,
    collect_compilation_rows,
    default_nonholonomic_field,
    default_standard_field,
    fit_rulebook,
    predict_rulebook,
    primitive_priority_delta,
    recent_records,
)


@dataclass(frozen=True)
class CX10CNFAParams:
    regime_floor: float
    teacher_conf_floor: float
    sample_stride: int
    similarity_thr: float
    bottleneck_thr: float
    misc_margin: float
    mode_strength: float
    history_steps: int
    persist_steps: int
    reverse_steer_frac: float
    commit_bottleneck_thr: float


DEFAULT_TEACHER = Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json')


def param_grid() -> list[CX10CNFAParams]:
    return [
        CX10CNFAParams(0.40, 0.50, 1, 0.22, 0.38, 0.05, 0.28, 4, 2, 0.10, 0.36),
        CX10CNFAParams(0.38, 0.48, 1, 0.20, 0.36, 0.06, 0.26, 5, 3, 0.08, 0.34),
        CX10CNFAParams(0.42, 0.52, 2, 0.24, 0.40, 0.04, 0.30, 4, 2, 0.12, 0.38),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {
            'name': 'No-Phase',
            'overrides': {
                'history_steps': 0,
                'persist_steps': 0,
            },
        },
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX10CNFAParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher_memory = (dependencies or {}).get('teacher_memory', None)
    if teacher_memory is None:
        raise ValueError('CX10-C requires frozen CX8-D teacher memory')
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
        'history_steps': int(params.history_steps),
        'persist_steps': int(params.persist_steps),
    }
    (out_dir / 'nfa_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'bank': bank, 'train_rows': int(len(rows)), 'best_val_loss': float('nan')}


class NFAPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, bank: dict[str, Any], params: CX10CNFAParams) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.bank = bank
        self.params = params

    def _predict_here(self, record) -> tuple[np.ndarray, dict[str, Any]]:
        feat = build_compact_bundle_feature_vector(
            self.case,
            self.bundle,
            self.field,
            (float(record.x), float(record.y), float(record.yaw)),
            prev_steer=float(record.steer),
        )
        pred = predict_rulebook(
            feat,
            self.bank,
            similarity_thr=float(self.params.similarity_thr),
            bottleneck_thr=float(self.params.bottleneck_thr),
            misc_margin=float(self.params.misc_margin),
            allow_reverse_with_low_escape=False,
        )
        return feat, pred

    def _history_side(self, planner, record, records) -> int:
        hist = recent_records(record, records, int(self.params.history_steps))
        max_steer = float(planner.max_steer)
        for rec in hist:
            if int(rec.direction) < 0 and float(rec.steer) <= -float(self.params.reverse_steer_frac) * max_steer:
                return -1
            if int(rec.direction) < 0 and float(rec.steer) >= float(self.params.reverse_steer_frac) * max_steer:
                return 1
        for rec in hist:
            if int(rec.direction) > 0 and float(rec.steer) < -1e-6:
                return -1
            if int(rec.direction) > 0 and float(rec.steer) > 1e-6:
                return 1
        return 0

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        feat, pred = self._predict_here(record)
        bottleneck = float(feat[FEATURE_INDEX['bottleneck']])
        bundle_id = pred.get('bundle_id', None)
        side = bundle_side(bundle_id)
        hist = recent_records(record, records, int(self.params.history_steps))
        hist_side = self._history_side(planner, record, records)
        reverse_recent = False
        if int(self.params.persist_steps) > 0:
            limit = min(len(hist), int(self.params.persist_steps) + 1)
            max_steer = float(planner.max_steer)
            for rec in hist[:limit]:
                if int(rec.direction) < 0 and abs(float(rec.steer)) >= float(self.params.reverse_steer_frac) * max_steer:
                    reverse_recent = True
                    break
        mode = 0
        phase = 'neutral'
        if reverse_recent and hist_side != 0 and bottleneck >= float(self.params.commit_bottleneck_thr):
            mode = 1 if hist_side < 0 else 2
            phase = 'commit_thread'
        elif bundle_id is not None and int(bundle_id) in REVERSE_LABELS and bottleneck >= float(self.params.bottleneck_thr):
            mode = 3 if side < 0 else 4
            phase = 'prepare_reverse'
        elif bundle_id is not None and side != 0 and bottleneck >= float(self.params.commit_bottleneck_thr):
            mode = 1 if side < 0 else 2
            phase = 'direct_thread'
        elif hist_side != 0 and bottleneck >= float(self.params.commit_bottleneck_thr) and int(self.params.persist_steps) > 0:
            mode = 1 if hist_side < 0 else 2
            phase = 'recover'
        return {
            'mode': int(mode),
            'phase': phase,
            'confidence': float(pred.get('confidence', 0.0)),
            'bottleneck': float(bottleneck),
        }

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        mode = int(node_ctx.get('mode', 0)) if isinstance(node_ctx, dict) else 0
        conf = float(node_ctx.get('confidence', 0.0)) if isinstance(node_ctx, dict) else 0.0
        bottleneck = float(node_ctx.get('bottleneck', 0.0)) if isinstance(node_ctx, dict) else 0.0
        strength = float(self.params.mode_strength) * max(0.3, bottleneck) * (0.4 + 0.6 * conf)
        ranked = []
        for cand in candidates:
            delta = primitive_priority_delta(self.case, int(cand.primitive_index), int(mode), float(strength))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def _apply_overrides(params: CX10CNFAParams, overrides: dict[str, Any] | None) -> CX10CNFAParams:
    if not overrides:
        return params
    return replace(params, **overrides)


def make_policy(memory: dict[str, Any], params: CX10CNFAParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    cur = _apply_overrides(params, ablation.get('overrides') if isinstance(ablation, dict) else None)
    return NFAPolicy(case, bundle, field, memory['bank'], cur)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX10CNFAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_nonholonomic_field(case, predictor, cfg)


def build_standard_field(sample, predictor, params: CX10CNFAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_standard_field(sample, predictor)
