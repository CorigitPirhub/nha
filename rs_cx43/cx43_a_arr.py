from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx21.common import run_hybrid_with_policy
from rs_cx24.common import build_frozen_haa_teacher
from rs_cx34 import cx34_a_msr as parent_mod
from rs_cx43.common import (
    RankReleaseContract,
    cheap_rank_candidates,
    compile_rank_release_contract,
    rank_match,
    rank_release_feature,
    release_decision,
)


@dataclass(frozen=True)
class CX43AARRParams:
    min_hits: int
    support_slack: float
    anchor_weight: float
    guided_weight: float
    allowed_bonus: float
    discouraged_penalty: float
    forbidden_penalty: float
    macro_bonus: float
    must_precede_bonus: float


def param_grid() -> list[CX43AARRParams]:
    return [CX43AARRParams(8, 0.00, 0.75, 0.25, 0.040, 0.030, 0.080, 0.040, 0.050)]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Rank-Release', 'disable_rank_release': True},
        {'name': 'Proxy-Only', 'force_proxy_only': True},
    ]


def _load_parent_params() -> parent_mod.CX34AMSRParams:
    data = json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))
    return parent_mod.CX34AMSRParams(**data['params'])


class _CollectorPolicy:
    def __init__(self, base_policy, params: CX43AARRParams) -> None:
        self.base_policy = base_policy
        self.params = params
        self.rows: list[dict[str, Any]] = []

    def start_search(self, *args, **kwargs):
        if hasattr(self.base_policy, 'start_search'):
            return self.base_policy.start_search(*args, **kwargs)

    def prepare_expand(self, *args, **kwargs):
        return self.base_policy.prepare_expand(*args, **kwargs)

    def extra_successors(self, *args, **kwargs):
        return self.base_policy.extra_successors(*args, **kwargs)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        full_ranked = self.base_policy.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict) or not candidates:
            return full_ranked
        proxy_ranked, proxy_meta = cheap_rank_candidates(
            record,
            node_ctx,
            list(candidates),
            anchor_weight=float(self.params.anchor_weight),
            guided_weight=float(self.params.guided_weight),
            allowed_bonus=float(self.params.allowed_bonus),
            discouraged_penalty=float(self.params.discouraged_penalty),
            forbidden_penalty=float(self.params.forbidden_penalty),
            macro_bonus=float(self.params.macro_bonus),
            must_precede_bonus=float(self.params.must_precede_bonus),
        )
        feat = rank_release_feature(getattr(self.base_policy, 'bundle', {}), node_ctx, proxy_meta)
        self.rows.append(
            {
                'feature': feat,
                'margin': float(proxy_meta.get('top_margin', 0.0)),
                'match': bool(rank_match(full_ranked, proxy_ranked)),
            }
        )
        return full_ranked

    def complete_expand(self, *args, **kwargs):
        if hasattr(self.base_policy, 'complete_expand'):
            return self.base_policy.complete_expand(*args, **kwargs)


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX43AARRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = build_frozen_haa_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    parent_params = _load_parent_params()
    parent_memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, {'haa_teacher': teacher})
    trace_rows: list[dict[str, Any]] = []
    for asset in calib_train_assets:
        field = parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, parent_memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        collector = _CollectorPolicy(parent_mod.make_policy(parent_memory, parent_params, asset['case'], bundle, field, device, ablation=None), params)
        run_hybrid_with_policy(asset['case'], field, 20000, successor_policy=collector, record_expanded=False)
        trace_rows.extend(list(collector.rows))
    contract = compile_rank_release_contract(trace_rows, min_hits=int(params.min_hits))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx43_a_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'contract': {
                    'positive_hits': int(contract.positive_hits),
                    'negative_hits': int(contract.negative_hits),
                    'margin_floor': float(contract.margin_floor),
                },
                'trace_rows': int(len(trace_rows)),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    return {
        'parent_params': parent_params,
        'parent_memory': parent_memory,
        'rank_release_contract': contract,
    }


class ARRPolicy:
    def __init__(self, policy, bundle: dict[str, Any], params: CX43AARRParams, contract: RankReleaseContract, *, disable_rank_release: bool = False, force_proxy_only: bool = False) -> None:
        self.policy = policy
        self.bundle = bundle
        self.params = params
        self.contract = contract
        self.disable_rank_release = bool(disable_rank_release)
        self.force_proxy_only = bool(force_proxy_only)
        self.stats: dict[str, float] = {
            'rank_release_hits': 0.0,
            'rank_release_full': 0.0,
            'rank_release_singletons': 0.0,
        }

    def start_search(self, *args, **kwargs):
        if hasattr(self.policy, 'start_search'):
            return self.policy.start_search(*args, **kwargs)

    def prepare_expand(self, *args, **kwargs):
        return self.policy.prepare_expand(*args, **kwargs)

    def extra_successors(self, *args, **kwargs):
        return self.policy.extra_successors(*args, **kwargs)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not candidates:
            return self.policy.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        proxy_ranked, proxy_meta = cheap_rank_candidates(
            record,
            node_ctx,
            list(candidates),
            anchor_weight=float(self.params.anchor_weight),
            guided_weight=float(self.params.guided_weight),
            allowed_bonus=float(self.params.allowed_bonus),
            discouraged_penalty=float(self.params.discouraged_penalty),
            forbidden_penalty=float(self.params.forbidden_penalty),
            macro_bonus=float(self.params.macro_bonus),
            must_precede_bonus=float(self.params.must_precede_bonus),
        )
        if bool(proxy_meta.get('singleton', False)):
            self.stats['rank_release_singletons'] = float(self.stats.get('rank_release_singletons', 0.0) + 1.0)
            return proxy_ranked
        if self.disable_rank_release:
            self.stats['rank_release_full'] = float(self.stats.get('rank_release_full', 0.0) + 1.0)
            return self.policy.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.force_proxy_only:
            self.stats['rank_release_hits'] = float(self.stats.get('rank_release_hits', 0.0) + 1.0)
            return proxy_ranked
        feat = rank_release_feature(self.bundle, node_ctx, proxy_meta)
        allow, _, _ = release_decision(
            self.contract,
            feat,
            margin=float(proxy_meta.get('top_margin', 0.0)),
            slack=float(self.params.support_slack),
        )
        if allow:
            self.stats['rank_release_hits'] = float(self.stats.get('rank_release_hits', 0.0) + 1.0)
            return proxy_ranked
        self.stats['rank_release_full'] = float(self.stats.get('rank_release_full', 0.0) + 1.0)
        return self.policy.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def complete_expand(self, *args, **kwargs):
        if hasattr(self.policy, 'complete_expand'):
            return self.policy.complete_expand(*args, **kwargs)


def make_policy(memory: dict[str, Any], params: CX43AARRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    base_policy = parent_mod.make_policy(memory['parent_memory'], memory['parent_params'], case, bundle, field, device, ablation=None)
    return ARRPolicy(
        base_policy,
        bundle,
        params,
        memory['rank_release_contract'],
        disable_rank_release=bool(ablation.get('disable_rank_release', False)),
        force_proxy_only=bool(ablation.get('force_proxy_only', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX43AARRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, memory['parent_params'], memory['parent_memory'])


def build_standard_field(sample, predictor, params: CX43AARRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(sample, predictor, memory['parent_params'], memory['parent_memory']).astype(np.float32)
