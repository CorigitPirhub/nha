from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx24.common import ObservatoryMixin, apply_class_edit, build_frozen_haa_teacher, class_key, class_parts, make_haa_policy, trace_feature_vector
from rs_cx23.common import macros_for_bucket
from rs_cx21.common import family_bucket_name
from rs_cx22 import cx22_d_sha as base_mod


@dataclass(frozen=True)
class CX24DCCCParams:
    commit_margin: float
    sibling_margin: float
    max_macros: int


def param_grid() -> list[CX24DCCCParams]:
    return [
        CX24DCCCParams(0.02, 0.01, 3),
        CX24DCCCParams(0.04, 0.02, 3),
        CX24DCCCParams(0.06, 0.03, 3),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Certificate', 'disable_certificate': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX24DCCCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    haa_teacher = build_frozen_haa_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    base_mod.lag_mod.save_meta(out_dir / 'ccc_meta.json', {'params': params.__dict__})
    return {'haa_teacher': haa_teacher, 'best_val_loss': float('nan')}


class CCCPolicy(ObservatoryMixin):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX24DCCCParams, memory: dict[str, Any], disable_certificate: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_certificate = bool(disable_certificate)
        self.haa_teacher = memory['haa_teacher']
        self.inner = make_haa_policy(self.haa_teacher, case, bundle, self.field)
        self._diag_init()

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ctx = self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        if isinstance(ctx, dict):
            self._diag_record(ctx, search_state, self.case, self.bundle, record)
        return ctx

    def _macro_proxy_score(self, planner, record, h_pair, mode: str, bucket: str) -> float:
        macros = macros_for_bucket(self.haa_teacher.shadow_teacher.lag_teacher, mode, bucket, max_macros=int(self.params.max_macros))
        if not macros:
            return float('-inf')
        cands = base_mod.lag_mod.macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros))
        if not cands:
            return float('-inf')
        here = float(record.g + record.guided)
        best = max(float(here - (record.g + float(c.guided))) for c in cands)
        return float(best)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_certificate or not isinstance(node_ctx, dict):
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        current_key = str(class_key(node_ctx))
        mode, bucket = class_parts(current_key)
        if str(search_state.get('haa_state', 'observe')) != 'commit' or str(bucket) == 'none':
            return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        commit_score = self._macro_proxy_score(planner, record, h_pair, mode, bucket)
        baseline_score = max((float(record.g + record.guided) - (record.g + float(c.guided)) for c in candidates if getattr(c, 'source', 'primitive') == 'primitive'), default=float('-inf'))
        siblings = [b for b in ('straight', 'forward_turn', 'reverse', 'reverse_setup') if b != str(bucket)]
        sibling_score = max((self._macro_proxy_score(planner, record, h_pair, mode, sib) for sib in siblings), default=float('-inf'))
        if commit_score < max(baseline_score + float(self.params.commit_margin), sibling_score + float(self.params.sibling_margin)):
            edited = apply_class_edit(node_ctx, self.haa_teacher.shadow_teacher.lag_teacher, 'uncertain|none', max_macros=int(self.params.max_macros))
            node_ctx.clear()
            node_ctx.update(edited)
            search_state['haa_state'] = 'recover'
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX24DCCCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return CCCPolicy(case, bundle, field, params, memory, disable_certificate=bool(ablation.get('disable_certificate', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX24DCCCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    field = base_mod.build_nonholonomic_field(case, predictor, cfg, shadow.params, shadow.memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX24DCCCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    shadow = memory['haa_teacher'].shadow_teacher
    return base_mod.build_standard_field(sample, predictor, shadow.params, shadow.memory).astype(np.float32)
