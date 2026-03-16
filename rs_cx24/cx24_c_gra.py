from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import ObservatoryMixin, apply_class_edit, build_frozen_haa_teacher, class_key, compile_haa_trace_rows, make_haa_policy
from rs_cx22 import cx22_d_sha as base_mod


@dataclass(frozen=True)
class CX24CGRAParams:
    min_hits: int
    worst_group_floor: float
    max_macros: int


def param_grid() -> list[CX24CGRAParams]:
    return [
        CX24CGRAParams(3, 0.00, 3),
        CX24CGRAParams(4, 0.02, 3),
        CX24CGRAParams(4, 0.05, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Group-Robust', 'disable_group_robust': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX24CGRAParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_haa_trace_rows(calib_train_assets, haa_teacher, horizon_steps=int(haa_teacher.params.commit_steps + haa_teacher.params.recover_steps), stride=1)
    grouped: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        grouped.setdefault(str(row['class_key']), {}).setdefault(str(row['scenario']), []).append(float(row['future_gain']))
    robust_scores = {}
    for key, scen_map in grouped.items():
        total = sum(len(v) for v in scen_map.values())
        if total < int(params.min_hits):
            continue
        scen_means = [float(np.mean(np.asarray(v, dtype=np.float32))) for v in scen_map.values()]
        robust_scores[str(key)] = {
            'worst': float(min(scen_means)),
            'avg': float(np.mean(scen_means)),
            'num_groups': int(len(scen_map)),
        }
    base_mod.lag_mod.save_meta(out_dir / 'gra_meta.json', {'params': params.__dict__, 'robust_scores': robust_scores})
    return {'haa_teacher': haa_teacher, 'robust_scores': robust_scores, 'best_val_loss': float('nan')}


class GRAPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX24CGRAParams, memory: dict[str, Any], disable_group_robust: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_group_robust = bool(disable_group_robust)
        self.haa_teacher = memory['haa_teacher']
        self.inner = make_haa_policy(self.haa_teacher, case, bundle, self.field)
        self.robust_scores = dict(memory.get('robust_scores', {}))
        self._diag_init()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict) and (not self.disable_group_robust):
            key = str(class_key(ctx))
            score = self.robust_scores.get(key, {'worst': float('-inf')})
            if float(score.get('worst', float('-inf'))) < float(self.params.worst_group_floor):
                ctx = apply_class_edit(ctx, self.haa_teacher.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
                search_state['haa_state'] = 'recover'
        if isinstance(ctx, dict):
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX24CGRAParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return GRAPolicy(case, bundle, field, params, memory, disable_group_robust=bool(ablation.get('disable_group_robust', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX24CGRAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, shadow.params, shadow.memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX24CGRAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    return base_mod.build_standard_field(sample, predictor, shadow.params, shadow.memory).astype(np.float32)
