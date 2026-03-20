from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import class_key
from rs_cx24.common import build_frozen_haa_teacher
from rs_cx34 import cx34_a_msr as parent_mod
from rs_cx43.common import cheap_rank_candidates


@dataclass(frozen=True)
class CX43CISRRParams:
    margin_thr: float
    anchor_weight: float
    guided_weight: float
    allowed_bonus: float
    discouraged_penalty: float
    forbidden_penalty: float
    macro_bonus: float
    must_precede_bonus: float


def param_grid() -> list[CX43CISRRParams]:
    base = dict(anchor_weight=0.75, guided_weight=0.25, allowed_bonus=0.04, discouraged_penalty=0.03, forbidden_penalty=0.08, macro_bonus=0.04, must_precede_bonus=0.05)
    return [
        CX43CISRRParams(margin_thr=0.04, **base),
        CX43CISRRParams(margin_thr=0.05, **base),
        CX43CISRRParams(margin_thr=0.06, **base),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Rank-Release', 'disable_rank_release': True},
        {'name': 'Proxy-Only', 'force_proxy_only': True},
    ]


def _load_parent_params() -> parent_mod.CX34AMSRParams:
    data = json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))
    return parent_mod.CX34AMSRParams(**data['params'])


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX43CISRRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = build_frozen_haa_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    parent_params = _load_parent_params()
    parent_memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, {'haa_teacher': teacher})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx43_c_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'parent_params': parent_params, 'parent_memory': parent_memory}


class ISRRPolicy(parent_mod.MSRPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        parent_params: parent_mod.CX34AMSRParams,
        parent_memory: dict[str, Any],
        params: CX43CISRRParams,
        *,
        disable_rank_release: bool = False,
        force_proxy_only: bool = False,
    ) -> None:
        super().__init__(case, bundle, field, parent_params, parent_memory, disable_macro_rescue=False)
        self.release_params = params
        self.disable_rank_release = bool(disable_rank_release)
        self.force_proxy_only = bool(force_proxy_only)
        if not isinstance(getattr(self, 'stats', None), dict):
            self.stats = {}
        self.stats['rank_release_hits'] = 0.0
        self.stats['rank_release_full'] = 0.0
        self.stats['rank_release_singletons'] = 0.0

    def _structural_release_ok(self, node_ctx: dict[str, Any], proxy_meta: dict[str, Any]) -> bool:
        return bool(
            str(class_key(node_ctx)) != 'uncertain|none'
            and not bool(node_ctx.get('must_precede', False))
            and int(proxy_meta.get('num_macros', 0)) == 0
            and int(proxy_meta.get('num_forbidden', 0)) == 0
            and str(proxy_meta.get('top_label', 'discouraged')) == 'allowed'
            and float(proxy_meta.get('top_margin', 0.0)) >= float(self.release_params.margin_thr)
        )

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not candidates:
            return super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        proxy_ranked, proxy_meta = cheap_rank_candidates(
            record,
            node_ctx,
            list(candidates),
            anchor_weight=float(self.release_params.anchor_weight),
            guided_weight=float(self.release_params.guided_weight),
            allowed_bonus=float(self.release_params.allowed_bonus),
            discouraged_penalty=float(self.release_params.discouraged_penalty),
            forbidden_penalty=float(self.release_params.forbidden_penalty),
            macro_bonus=float(self.release_params.macro_bonus),
            must_precede_bonus=float(self.release_params.must_precede_bonus),
        )
        if bool(proxy_meta.get('singleton', False)):
            self.stats['rank_release_singletons'] = float(self.stats.get('rank_release_singletons', 0.0) + 1.0)
            return proxy_ranked
        if self.disable_rank_release:
            self.stats['rank_release_full'] = float(self.stats.get('rank_release_full', 0.0) + 1.0)
            return super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.force_proxy_only or self._structural_release_ok(node_ctx, proxy_meta):
            self.stats['rank_release_hits'] = float(self.stats.get('rank_release_hits', 0.0) + 1.0)
            return proxy_ranked
        self.stats['rank_release_full'] = float(self.stats.get('rank_release_full', 0.0) + 1.0)
        return super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX43CISRRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return ISRRPolicy(
        case,
        bundle,
        field,
        memory['parent_params'],
        memory['parent_memory'],
        params,
        disable_rank_release=bool(ablation.get('disable_rank_release', False)),
        force_proxy_only=bool(ablation.get('force_proxy_only', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX43CISRRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, memory['parent_params'], memory['parent_memory'])


def build_standard_field(sample, predictor, params: CX43CISRRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(sample, predictor, memory['parent_params'], memory['parent_memory']).astype(np.float32)
