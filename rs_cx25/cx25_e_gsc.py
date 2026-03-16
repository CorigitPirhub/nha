from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import ObservatoryMixin, compile_haa_trace_rows
from rs_cx25.common import build_frozen_cx24_stack, class_key, make_ccc_policy
from rs_cx23 import cx23_c_haa as haa_mod
from rs_cx23.common import apply_class_edit


@dataclass(frozen=True)
class CX25EGSCParams:
    min_hits: int
    worst_group_floor: float
    tail_floor: float


def param_grid() -> list[CX25EGSCParams]:
    return [
        CX25EGSCParams(3, 0.0, 0.0),
        CX25EGSCParams(4, 0.02, 0.0),
        CX25EGSCParams(4, 0.05, 0.02),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Group-Stable', 'disable_group_stable': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX25EGSCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    stack = build_frozen_cx24_stack(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_haa_trace_rows(calib_train_assets, stack.haa_teacher, horizon_steps=int(stack.haa_teacher.params.commit_steps + stack.haa_teacher.params.recover_steps), stride=1)
    grouped = {}
    for row in rows:
        grouped.setdefault(str(row['class_key']), {}).setdefault(str(row['scenario']), []).append(float(row['future_gain']))
    robust = {}
    for key, scen_map in grouped.items():
        total = sum(len(v) for v in scen_map.values())
        if total < int(params.min_hits):
            continue
        means = {scen: float(np.mean(np.asarray(vals, dtype=np.float32))) for scen, vals in scen_map.items()}
        robust[key] = {'worst': min(means.values()), 'tail': float(means.get('parasol_misc', min(means.values()))), 'avg': float(np.mean(list(means.values())))}
    haa_mod.base_mod.lag_mod.save_meta(out_dir / 'gsc_meta.json', {'params': params.__dict__, 'robust': robust})
    return {'stack': stack, 'robust': robust, 'best_val_loss': float('nan')}


class GSCPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX25EGSCParams, memory: dict[str, Any], disable_group_stable: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_group_stable = bool(disable_group_stable)
        self.stack = memory['stack']
        self.inner = make_ccc_policy(self.stack, case, bundle, self.field)
        self.robust = dict(memory.get('robust', {}))
        self._diag_init()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict) and not self.disable_group_stable:
            key = str(class_key(ctx))
            stats = self.robust.get(key, {'worst': float('-inf'), 'tail': float('-inf')})
            if float(stats['worst']) < float(self.params.worst_group_floor) or float(stats['tail']) < float(self.params.tail_floor):
                ctx = apply_class_edit(ctx, self.stack.haa_teacher.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.stack.haa_teacher.params.max_macros))
                search_state['haa_state'] = 'recover'
        if isinstance(ctx, dict):
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX25EGSCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return GSCPolicy(case, bundle, field, params, memory, disable_group_stable=bool(ablation.get('disable_group_stable', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX25EGSCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = haa_mod.build_nonholonomic_field(case, predictor, cfg, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher})
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX25EGSCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return haa_mod.build_standard_field(sample, predictor, memory['stack'].haa_teacher.params, {'shadow_teacher': memory['stack'].haa_teacher.shadow_teacher}).astype(np.float32)
