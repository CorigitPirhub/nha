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
    collect_scene_template_rows,
    default_nonholonomic_field,
    default_standard_field,
    fit_rulebook,
    fit_scene_template_bank,
    nearest_window,
    order_windows_by_anchor,
    predict_rulebook,
    predict_scene_template,
    primitive_priority_delta,
    scene_feature_vector,
    select_bottleneck_windows,
)


@dataclass(frozen=True)
class CX10DLASParams:
    regime_floor: float
    teacher_conf_floor: float
    sample_stride: int
    top_k_windows: int
    gate_threshold: float
    macro_radius_m: float
    commit_radius_m: float
    similarity_thr: float
    bottleneck_thr: float
    scene_similarity_thr: float
    misc_margin: float
    mode_strength: float
    use_scene_template: bool


DEFAULT_TEACHER = Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json')


def param_grid() -> list[CX10DLASParams]:
    return [
        CX10DLASParams(0.40, 0.50, 1, 2, 0.40, 3.2, 1.5, 0.22, 0.38, 0.18, 0.05, 0.27, True),
        CX10DLASParams(0.38, 0.48, 1, 3, 0.38, 3.4, 1.6, 0.20, 0.36, 0.16, 0.06, 0.25, True),
        CX10DLASParams(0.42, 0.52, 2, 2, 0.42, 3.0, 1.4, 0.24, 0.40, 0.20, 0.04, 0.29, True),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {
            'name': 'No-Template',
            'overrides': {
                'use_scene_template': False,
                'scene_similarity_thr': 1.1,
            },
        },
    ]


def _template_tokens(template: str) -> list[int]:
    if template == 'reverse_left_then_thread_left':
        return [3, 1]
    if template == 'reverse_right_then_thread_right':
        return [4, 2]
    if template == 'thread_left_only':
        return [1]
    if template == 'thread_right_only':
        return [2]
    return []


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX10DLASParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher_memory = (dependencies or {}).get('teacher_memory', None)
    if teacher_memory is None:
        raise ValueError('CX10-D requires frozen CX8-D teacher memory')
    rows = collect_compilation_rows(
        calib_train_assets,
        teacher_memory,
        regime_floor=float(params.regime_floor),
        teacher_conf_floor=float(params.teacher_conf_floor),
        sample_stride=int(params.sample_stride),
    )
    bank = fit_rulebook(rows)
    scene_rows = collect_scene_template_rows(
        calib_train_assets,
        teacher_memory,
        top_k_windows=int(params.top_k_windows),
        gate_threshold=float(params.gate_threshold),
        regime_floor=float(params.regime_floor),
        teacher_conf_floor=float(params.teacher_conf_floor),
    )
    scene_bank = fit_scene_template_bank(scene_rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'num_rows': int(len(rows)),
        'scene_rows': int(len(scene_rows)),
        'counts': {str(k): int(v) for k, v in bank.get('counts', {}).items()},
        'templates': {str(k): int(v) for k, v in scene_bank.get('counts', {}).items()},
        'teacher_chosen_json': str((dependencies or {}).get('teacher_chosen_json', DEFAULT_TEACHER)),
    }
    (out_dir / 'las_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'bank': bank, 'scene_bank': scene_bank, 'train_rows': int(len(rows)), 'best_val_loss': float('nan')}


class LASPolicy:
    def __init__(self, case: dict[str, Any], gates: list[dict[str, Any]], params: CX10DLASParams) -> None:
        self.case = case
        self.gates = gates
        self.params = params

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        state = (float(record.x), float(record.y), float(record.yaw))
        gate, dist = nearest_window(self.gates, state)
        if gate is None or float(dist) > float(self.params.macro_radius_m):
            return {'mode': 0, 'gate_score': 0.0, 'dist_to_gate': float(dist)}
        if float(dist) <= float(self.params.commit_radius_m):
            mode = int(gate['inner_mode'])
        else:
            mode = int(gate['outer_mode']) if int(gate['outer_mode']) > 0 else int(gate['inner_mode'])
        return {'mode': int(mode), 'gate_score': float(gate['score']), 'dist_to_gate': float(dist)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        mode = int(node_ctx.get('mode', 0)) if isinstance(node_ctx, dict) else 0
        gate_score = float(node_ctx.get('gate_score', 0.0)) if isinstance(node_ctx, dict) else 0.0
        strength = float(self.params.mode_strength) * max(0.35, min(1.0, gate_score))
        ranked = []
        for cand in candidates:
            delta = primitive_priority_delta(self.case, int(cand.primitive_index), int(mode), float(strength))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def _apply_overrides(params: CX10DLASParams, overrides: dict[str, Any] | None) -> CX10DLASParams:
    if not overrides:
        return params
    return replace(params, **overrides)


def make_policy(memory: dict[str, Any], params: CX10DLASParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    cur = _apply_overrides(params, ablation.get('overrides') if isinstance(ablation, dict) else None)
    windows = order_windows_by_anchor(
        case,
        field,
        select_bottleneck_windows(case, bundle, field, top_k=int(cur.top_k_windows), min_sep_m=2.5, gate_threshold=float(cur.gate_threshold)),
    )
    scene_pred = predict_scene_template(scene_feature_vector(bundle), memory['scene_bank'], similarity_thr=float(cur.scene_similarity_thr))
    template = str(scene_pred['template']) if bool(cur.use_scene_template) else 'neutral'
    tokens = _template_tokens(template)
    gates = []
    for idx, win in enumerate(windows):
        feat = build_compact_bundle_feature_vector(case, bundle, field, win['state'], prev_steer=0.0)
        local = predict_rulebook(
            feat,
            memory['bank'],
            similarity_thr=float(cur.similarity_thr),
            bottleneck_thr=float(cur.bottleneck_thr),
            misc_margin=float(cur.misc_margin),
            allow_reverse_with_low_escape=False,
        )
        if bool(cur.use_scene_template) and tokens:
            if len(tokens) == 1:
                outer_mode = 0
                inner_mode = int(tokens[0])
            else:
                if idx == 0:
                    outer_mode = int(tokens[0])
                    inner_mode = int(tokens[1])
                else:
                    outer_mode = 0
                    inner_mode = int(tokens[min(idx, len(tokens) - 1)])
        else:
            outer_mode = 0
            inner_mode = int(local.get('mode', 0))
        if int(inner_mode) <= 0 and int(outer_mode) <= 0:
            continue
        gates.append({
            **win,
            'outer_mode': int(outer_mode),
            'inner_mode': int(inner_mode),
            'score': float(max(win['score'], local.get('confidence', 0.0), scene_pred.get('similarity', 0.0))),
            'template': template,
        })
    return LASPolicy(case, gates, cur)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX10DLASParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_nonholonomic_field(case, predictor, cfg)


def build_standard_field(sample, predictor, params: CX10DLASParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return default_standard_field(sample, predictor)
