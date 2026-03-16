from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import (
    apply_class_edit,
    build_frozen_shadow_teacher,
    class_key,
    class_parts,
    class_key_from_parts,
    compile_shadow_rows,
    make_shadow_policy,
    shadow_prepare,
)
from rs_cx22 import cx22_d_sha as base_mod


@dataclass(frozen=True)
class CX23DCCEParams:
    min_hits: int
    min_gain_delta: float
    max_macros: int


def param_grid() -> list[CX23DCCEParams]:
    return [
        CX23DCCEParams(3, 0.05, 3),
        CX23DCCEParams(4, 0.02, 3),
        CX23DCCEParams(4, 0.00, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Editor', 'disable_editor': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX23DCCEParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    shadow_teacher = build_frozen_shadow_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_shadow_rows(calib_train_assets, shadow_teacher, horizon_steps=int(shadow_teacher.lag_teacher.params.horizon_steps), stride=1)
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row['class_key']), []).append(float(row['future_gain']))
    stats = {}
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=np.float32)
        if int(arr.size) >= int(params.min_hits):
            stats[str(key)] = {'avg_gain': float(np.mean(arr)), 'hits': int(arr.size)}
    editor = {}
    for key, st in stats.items():
        mode, bucket = class_parts(key)
        best_key = key
        best_gain = float(st['avg_gain'])
        for sib_bucket in ('straight', 'forward_turn', 'reverse', 'reverse_setup', 'none'):
            sib_key = class_key_from_parts(mode, sib_bucket)
            sib_stat = stats.get(sib_key)
            if sib_stat is None:
                continue
            if float(sib_stat['avg_gain']) > best_gain + float(params.min_gain_delta):
                best_key = sib_key
                best_gain = float(sib_stat['avg_gain'])
        if best_key != key:
            editor[str(key)] = {'replacement': str(best_key), 'gain_delta': float(best_gain - float(st['avg_gain']))}
    base_mod.lag_mod.save_meta(out_dir / 'cce_meta.json', {'params': params.__dict__, 'editor': editor, 'class_stats': stats})
    return {'shadow_teacher': shadow_teacher, 'editor': editor, 'best_val_loss': float('nan')}


class CCEPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX23DCCEParams, memory: dict[str, Any], disable_editor: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_editor = bool(disable_editor)
        self.shadow_teacher = memory['shadow_teacher']
        self.inner = make_shadow_policy(self.shadow_teacher, case, bundle, self.field)
        self.editor = dict(memory.get('editor', {}))

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = shadow_prepare(self.inner, (float(record.x), float(record.y), float(record.yaw)))
        if self.disable_editor:
            return ctx
        current_key = str(class_key(ctx))
        edit = self.editor.get(current_key)
        if edit is None:
            return ctx
        return apply_class_edit(ctx, self.shadow_teacher.lag_teacher, str(edit['replacement']), max_macros=int(self.params.max_macros))

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX23DCCEParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CCEPolicy(case, bundle, field, params, memory, disable_editor=bool(ablation.get('disable_editor', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX23DCCEParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, memory['shadow_teacher'].params, memory['shadow_teacher'].memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX23DCCEParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return base_mod.build_standard_field(sample, predictor, memory['shadow_teacher'].params, memory['shadow_teacher'].memory).astype(np.float32)
