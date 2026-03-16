from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10.common import (
    build_compact_bundle_feature_vector,
    collect_compilation_rows,
    default_nonholonomic_field,
    default_standard_field,
    fit_rulebook,
    nearest_window,
    order_windows_by_anchor,
    predict_rulebook,
    primitive_priority_delta,
    select_bottleneck_windows,
)


@dataclass(frozen=True)
class CX10BHBCParams:
    regime_floor: float
    teacher_conf_floor: float
    sample_stride: int
    top_k_windows: int
    gate_threshold: float
    pre_radius_m: float
    commit_radius_m: float
    similarity_thr: float
    bottleneck_thr: float
    misc_margin: float
    mode_strength: float
    enable_setup: bool


DEFAULT_TEACHER = Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json')


def param_grid() -> list[CX10BHBCParams]:
    return [
        CX10BHBCParams(0.40, 0.50, 1, 2, 0.40, 3.0, 1.4, 0.22, 0.38, 0.05, 0.28, True),
        CX10BHBCParams(0.38, 0.48, 1, 3, 0.38, 3.2, 1.5, 0.20, 0.36, 0.06, 0.26, True),
        CX10BHBCParams(0.42, 0.52, 2, 2, 0.42, 2.8, 1.2, 0.24, 0.40, 0.04, 0.30, True),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {
            'name': 'No-Setup',
            'overrides': {
                'enable_setup': False,
                'pre_radius_m': 1.6,
            },
        },
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX10BHBCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher_memory = (dependencies or {}).get('teacher_memory', None)
    if teacher_memory is None:
        raise ValueError('CX10-B requires frozen CX8-D teacher memory')
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
        'top_k_windows': int(params.top_k_windows),
        'gate_threshold': float(params.gate_threshold),
    }
    (out_dir / 'script_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'bank': bank, 'train_rows': int(len(rows)), 'best_val_loss': float('nan')}


def _window_modes(bundle_id: int, enable_setup: bool) -> tuple[int, int]:
    if int(bundle_id) == 2:
        return (3 if enable_setup else 0, 1)
    if int(bundle_id) == 3:
        return (4 if enable_setup else 0, 2)
    if int(bundle_id) == 0:
        return (0, 1)
    if int(bundle_id) == 1:
        return (0, 2)
    return 0, 0


class HBCPolicy:
    def __init__(self, case: dict[str, Any], windows: list[dict[str, Any]], params: CX10BHBCParams) -> None:
        self.case = case
        self.windows = windows
        self.params = params

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        state = (float(record.x), float(record.y), float(record.yaw))
        window, dist = nearest_window(self.windows, state)
        if window is None or float(dist) > float(self.params.pre_radius_m):
            return {'mode': 0, 'window_score': 0.0, 'dist_to_gate': float(dist)}
        if float(dist) <= float(self.params.commit_radius_m):
            mode = int(window['thread_mode'])
        else:
            mode = int(window['prepare_mode'])
        return {'mode': int(mode), 'window_score': float(window['score']), 'dist_to_gate': float(dist)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        mode = int(node_ctx.get('mode', 0)) if isinstance(node_ctx, dict) else 0
        score = float(node_ctx.get('window_score', 0.0)) if isinstance(node_ctx, dict) else 0.0
        strength = float(self.params.mode_strength) * max(0.35, min(1.0, score))
        ranked = []
        for cand in candidates:
            delta = primitive_priority_delta(self.case, int(cand.primitive_index), int(mode), float(strength))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def _apply_overrides(params: CX10BHBCParams, overrides: dict[str, Any] | None) -> CX10BHBCParams:
    if not overrides:
        return params
    return replace(params, **overrides)


def make_policy(memory: dict[str, Any], params: CX10BHBCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    cur = _apply_overrides(params, ablation.get('overrides') if isinstance(ablation, dict) else None)
    windows = select_bottleneck_windows(
        case,
        bundle,
        field,
        top_k=int(cur.top_k_windows),
        min_sep_m=2.5,
        gate_threshold=float(cur.gate_threshold),
    )
    labeled = []
    for win in order_windows_by_anchor(case, field, windows):
        feat = build_compact_bundle_feature_vector(case, bundle, field, win['state'], prev_steer=0.0)
        pred = predict_rulebook(
            feat,
            memory['bank'],
            similarity_thr=float(cur.similarity_thr),
            bottleneck_thr=float(cur.bottleneck_thr),
            misc_margin=float(cur.misc_margin),
            allow_reverse_with_low_escape=False,
        )
        bundle_id = pred.get('bundle_id', None)
        if bundle_id is None:
            continue
        prepare_mode, thread_mode = _window_modes(int(bundle_id), bool(cur.enable_setup))
        labeled.append({
            **win,
            'prepare_mode': int(prepare_mode),
            'thread_mode': int(thread_mode),
            'bundle_id': int(bundle_id),
            'score': float(max(win['score'], pred.get('confidence', 0.0))),
        })
    return HBCPolicy(case, labeled, cur)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX10BHBCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_nonholonomic_field(case, predictor, cfg)


def build_standard_field(sample, predictor, params: CX10BHBCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_standard_field(sample, predictor)
