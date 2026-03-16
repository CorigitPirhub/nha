from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx22.common import build_frozen_teacher, class_stats_from_rows, compile_teacher_state_rows, make_teacher_policy, teacher_prepare
from rs_cx21 import cx21_b_lag as lag_mod


@dataclass(frozen=True)
class CX22DSHAParams:
    min_hits: int
    lcb_q: float
    min_score: float


def param_grid() -> list[CX22DSHAParams]:
    return [
        CX22DSHAParams(4, 0.20, 0.00),
        CX22DSHAParams(5, 0.25, 0.02),
        CX22DSHAParams(6, 0.30, 0.05),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Class-Gate', 'disable_class_gate': True},
        {'name': 'No-LCB', 'disable_lcb': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX22DSHAParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = build_frozen_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_teacher_state_rows(calib_train_assets, teacher, horizon_steps=int(teacher.params.horizon_steps), stride=1)
    stats = class_stats_from_rows(rows, use_lcb=True, min_hits=int(params.min_hits), lcb_q=float(params.lcb_q))
    allowed = {key: val for key, val in stats.items() if float(val['score']) >= float(params.min_score)}
    avg_allowed = class_stats_from_rows(rows, use_lcb=False, min_hits=int(params.min_hits), lcb_q=float(params.lcb_q))
    lag_mod.save_meta(out_dir / 'sha_meta.json', {'params': params.__dict__, 'allowed_classes': allowed, 'avg_classes': avg_allowed})
    return {'teacher': teacher, 'allowed_classes': allowed, 'avg_allowed_classes': avg_allowed, 'best_val_loss': float('nan')}


class SHAPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX22DSHAParams, memory: dict[str, Any], disable_class_gate: bool = False, disable_lcb: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_class_gate = bool(disable_class_gate)
        self.disable_lcb = bool(disable_lcb)
        self.teacher = memory['teacher']
        self.inner = make_teacher_policy(self.teacher, case, bundle, self.field)
        self.allowed_classes = dict(memory.get('allowed_classes', {}))
        self.avg_allowed_classes = dict(memory.get('avg_allowed_classes', {}))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = teacher_prepare(self.inner, (float(record.x), float(record.y), float(record.yaw)))
        if self.disable_class_gate:
            return ctx
        allowed_map = self.avg_allowed_classes if self.disable_lcb else self.allowed_classes
        mode = str(ctx.get('mode', 'uncertain'))
        rules = dict(ctx.get('rules', {}))
        filtered_macros = []
        for macro in list(ctx.get('macros', [])):
            bucket = lag_mod.family_bucket_name(str(macro.family))
            if f'{mode}|{bucket}' in allowed_map:
                filtered_macros.append(macro)
        for bucket, label in list(rules.items()):
            if f'{mode}|{bucket}' not in allowed_map and str(label) in {'allowed', 'forbidden'}:
                rules[bucket] = 'discouraged'
        ctx['rules'] = rules
        ctx['macros'] = filtered_macros
        ctx['must_precede'] = bool(ctx.get('must_precede', False) and f'{mode}|reverse_setup' in allowed_map)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX22DSHAParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return SHAPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_class_gate=bool(ablation.get('disable_class_gate', False)),
        disable_lcb=bool(ablation.get('disable_lcb', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX22DSHAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = lag_mod.build_nonholonomic_field(case, predictor, cfg, memory['teacher'].params, memory['teacher'].memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX22DSHAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return lag_mod.build_standard_field(sample, predictor, memory['teacher'].params, memory['teacher'].memory).astype(np.float32)
