from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx21.common import FAMILY_BUCKETS
from rs_cx22.common import build_frozen_teacher, compile_teacher_state_rows, make_teacher_policy, state_feature_vector, teacher_prepare, top_allowed_bucket
from rs_cx21 import cx21_b_lag as lag_mod


@dataclass(frozen=True)
class CX22BDCGParams:
    activation_thr: float
    hard_conf_thr: float
    risk_score_thr: float
    min_future_gain: float


def param_grid() -> list[CX22BDCGParams]:
    return [
        CX22BDCGParams(0.18, 0.50, 0.00, 0.10),
        CX22BDCGParams(0.24, 0.60, 0.05, 0.12),
        CX22BDCGParams(0.30, 0.70, 0.08, 0.15),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Decision-Gate', 'disable_decision_gate': True},
        {'name': 'No-Conformal', 'disable_conformal': True},
    ]


def _decision_score(ctx: dict[str, Any]) -> float:
    foundation = ctx.get('foundation')
    if foundation is None:
        return 0.0
    max_conf = max(dict(ctx.get('conf', {})).values()) if dict(ctx.get('conf', {})) else 0.0
    return float(
        0.55 * float(max_conf)
        + 0.35 * float(ctx.get('oracle_gain', 0.0))
        + 0.10 * max(float(foundation.reverse_required), 0.0)
        + 0.05 * max(-float(foundation.trap_escape_affinity), 0.0)
    )


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX22BDCGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = build_frozen_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_teacher_state_rows(calib_train_assets, teacher, horizon_steps=int(teacher.params.horizon_steps), stride=1)
    class_stats = {}
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row['class_key']), []).append(float(row['future_gain']))
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=np.float32)
        class_stats[key] = {
            'avg_gain': float(np.mean(arr)),
            'risk_score': float(np.quantile(arr, 0.2)),
            'hits': int(arr.size),
        }
    lag_mod.save_meta(out_dir / 'dcg_meta.json', {'params': params.__dict__, 'class_stats': class_stats})
    return {'teacher': teacher, 'class_stats': class_stats, 'best_val_loss': float('nan')}


class DCGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX22BDCGParams, memory: dict[str, Any], disable_decision_gate: bool = False, disable_conformal: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_decision_gate = bool(disable_decision_gate)
        self.disable_conformal = bool(disable_conformal)
        self.teacher = memory['teacher']
        self.inner = make_teacher_policy(self.teacher, case, bundle, self.field)
        self.class_stats = dict(memory.get('class_stats', {}))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = teacher_prepare(self.inner, (float(record.x), float(record.y), float(record.yaw)))
        score = _decision_score(ctx)
        gate_active = bool(self.disable_decision_gate or (state_feature_vector(ctx)[6] >= float(self.params.min_future_gain) and score >= float(self.params.activation_thr) and str(ctx.get('mode', 'uncertain')) != 'forward_safe'))
        rules = dict(ctx.get('rules', {}))
        if gate_active and not self.disable_conformal:
            conf = dict(ctx.get('conf', {}))
            class_key = f"{ctx.get('mode', 'uncertain')}|{top_allowed_bucket(ctx)}"
            risk_score = float(self.class_stats.get(class_key, {}).get('risk_score', 0.0))
            for bucket, label in list(rules.items()):
                if str(label) == 'forbidden' and (float(conf.get(bucket, 0.0)) < float(self.params.hard_conf_thr) or float(risk_score) < float(self.params.risk_score_thr)):
                    rules[bucket] = 'discouraged'
        if not gate_active:
            rules = {bucket: 'discouraged' for bucket in FAMILY_BUCKETS}
            ctx['macros'] = []
            ctx['must_precede'] = False
        ctx['rules'] = rules
        ctx['gate_active'] = bool(gate_active)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not bool(node_ctx.get('gate_active', False)):
            return []
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not bool(node_ctx.get('gate_active', False)):
            return None
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX22BDCGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return DCGPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_decision_gate=bool(ablation.get('disable_decision_gate', False)),
        disable_conformal=bool(ablation.get('disable_conformal', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX22BDCGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = lag_mod.build_nonholonomic_field(case, predictor, cfg, memory['teacher'].params, memory['teacher'].memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX22BDCGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return lag_mod.build_standard_field(sample, predictor, memory['teacher'].params, memory['teacher'].memory).astype(np.float32)
