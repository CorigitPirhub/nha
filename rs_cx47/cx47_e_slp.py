from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import class_key
from rs_cx46 import cx46_d_ewv as quality_mod
from rs_cx46 import cx46_f_rbcc as parent_mod
from rs_cx21.common import run_hybrid_with_policy


@dataclass(frozen=True)
class StoreLikelihoodModel:
    mean: np.ndarray
    std: np.ndarray
    direction: np.ndarray
    quality_edges: np.ndarray
    global_positive_rate: float
    class_counts: dict[tuple[Any, ...], tuple[int, int]]
    struct_counts: dict[tuple[Any, ...], tuple[int, int]]
    quality_counts: dict[int, tuple[int, int]]
    struct_quality_counts: dict[tuple[Any, ...], tuple[int, int]]
    positive_count: int
    negative_count: int


@dataclass(frozen=True)
class CX47ESLPParams:
    review_cell_stride: int
    review_yaw_bins: int
    margin_thr: float
    anchor_eps: float
    enable_parasol_misc: bool
    enable_deadend_labyrinth: bool
    enable_narrow_passage: bool
    band_slack: float
    similarity_scale: float
    certainty_floor: float
    reliable_ttl_boost: float
    reliable_anchor_boost: float
    local_ttl_scale: float
    local_anchor_scale: float
    max_ttl: int
    min_band_count: int
    class_prior_strength: float
    struct_prior_strength: float
    quality_prior_strength: float
    struct_quality_prior_strength: float
    quality_mix: float
    support_bonus: float
    miss_decay: float
    review_stride_scale: float
    force_review_prob: float
    max_review_period: int
    warmup_reviews: int
    diag_reg: float


def param_grid() -> list[CX47ESLPParams]:
    common = dict(
        review_cell_stride=3,
        review_yaw_bins=12,
        margin_thr=0.03,
        anchor_eps=0.02,
        enable_parasol_misc=True,
        enable_deadend_labyrinth=True,
        enable_narrow_passage=True,
        band_slack=0.15,
        similarity_scale=4.0,
        certainty_floor=0.20,
        reliable_ttl_boost=1.05,
        reliable_anchor_boost=1.00,
        local_ttl_scale=0.65,
        local_anchor_scale=0.60,
        max_ttl=112,
        min_band_count=8,
        class_prior_strength=56.0,
        struct_prior_strength=28.0,
        quality_prior_strength=18.0,
        struct_quality_prior_strength=10.0,
        support_bonus=0.22,
        max_review_period=8,
        diag_reg=0.25,
    )
    return [
        CX47ESLPParams(**common, quality_mix=0.55, miss_decay=0.18, review_stride_scale=3.0, force_review_prob=0.46, warmup_reviews=4),
        CX47ESLPParams(**common, quality_mix=0.60, miss_decay=0.22, review_stride_scale=3.5, force_review_prob=0.44, warmup_reviews=4),
        CX47ESLPParams(**common, quality_mix=0.50, miss_decay=0.16, review_stride_scale=2.6, force_review_prob=0.48, warmup_reviews=6),
        CX47ESLPParams(**common, quality_mix=0.65, miss_decay=0.25, review_stride_scale=4.0, force_review_prob=0.42, warmup_reviews=6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'No-Store-Proxy', 'disable_store_proxy': True},
    ]


def _to_parent_params(params: CX47ESLPParams) -> parent_mod.CX46FRBCCParams:
    return parent_mod.CX46FRBCCParams(
        review_cell_stride=int(params.review_cell_stride),
        review_yaw_bins=int(params.review_yaw_bins),
        margin_thr=float(params.margin_thr),
        anchor_eps=float(params.anchor_eps),
        enable_parasol_misc=bool(params.enable_parasol_misc),
        enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
        enable_narrow_passage=bool(params.enable_narrow_passage),
        band_slack=float(params.band_slack),
        similarity_scale=float(params.similarity_scale),
        certainty_floor=float(params.certainty_floor),
        reliable_ttl_boost=float(params.reliable_ttl_boost),
        reliable_anchor_boost=float(params.reliable_anchor_boost),
        local_ttl_scale=float(params.local_ttl_scale),
        local_anchor_scale=float(params.local_anchor_scale),
        max_ttl=int(params.max_ttl),
        min_band_count=int(params.min_band_count),
    )


def _event_key(case: dict[str, Any], node_ctx: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(case.get('scenario', '')),
        str(class_key(node_ctx)),
        int(bool(node_ctx.get('must_precede', False))),
        int(len(list(node_ctx.get('macros', []))) > 0),
    )


def _class_sig(event_key: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(event_key[1:])


def _support_count(event_key: tuple[Any, ...], support_counter: dict[tuple[Any, ...], int]) -> int:
    return int(support_counter.get(event_key, 0))


def _support_strength(event_key: tuple[Any, ...], support_counter: dict[tuple[Any, ...], int]) -> float:
    return float(np.tanh(float(_support_count(event_key, support_counter)) / 4.0))


def _feature(case: dict[str, Any], bundle: dict[str, Any], record, node_ctx: dict[str, Any], support_counter: dict[tuple[Any, ...], int]) -> np.ndarray:
    event_key = _event_key(case, node_ctx)
    support = float(_support_strength(event_key, support_counter))
    quality = quality_mod._quality_feature(case, bundle, record, node_ctx, 0.0, support_counter, defaultdict(dict), 0.03)
    extra = np.asarray(
        [
            float(bool(node_ctx.get('must_precede', False))),
            float(len(list(node_ctx.get('macros', []))) > 0),
            support,
        ],
        dtype=np.float32,
    )
    return np.concatenate([quality, extra], axis=0).astype(np.float32)


def _fit_support_counter(train_assets, predictor, cfg: CXGlobalConfig, parent_params: parent_mod.CX46FRBCCParams, memory: dict[str, Any], device: str) -> dict[tuple[Any, ...], int]:
    counter: defaultdict[tuple[Any, ...], int] = defaultdict(int)
    for asset in train_assets:
        field = parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = parent_mod.make_policy(memory, parent_params, asset['case'], bundle, field, device, ablation=None)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        search_state: dict[str, Any] = {}
        for state in path[:-1]:
            from types import SimpleNamespace
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=0.0)
            ctx = policy.prepare_expand(None, rec, None, None, None, None, search_state, None)
            if not isinstance(ctx, dict):
                continue
            counter[_event_key(asset['case'], ctx)] += 1
    return dict(counter)


def _quality_bin_edges(scores: np.ndarray) -> np.ndarray:
    if scores.size <= 0:
        return np.asarray([-0.5, 0.0, 0.5], dtype=np.float32)
    edges = np.asarray(np.quantile(scores, [0.2, 0.4, 0.6, 0.8]), dtype=np.float32)
    edges = np.unique(np.round(edges, 6))
    if edges.size <= 0:
        return np.asarray([-0.5, 0.0, 0.5], dtype=np.float32)
    return edges.astype(np.float32)


def _quality_bin(model: StoreLikelihoodModel, feat: np.ndarray) -> int:
    if model.direction.shape[0] != feat.shape[0]:
        return 0
    z = ((feat.astype(np.float32) - model.mean) / model.std).astype(np.float32)
    score = float(np.dot(z, model.direction))
    return int(np.searchsorted(model.quality_edges, score, side='right'))


def _count_update(counter: defaultdict[Any, list[int]], key: Any, label: float) -> None:
    item = counter[key]
    item[1] += 1
    if float(label) > 0.5:
        item[0] += 1


def _fit_store_model(rows: list[dict[str, Any]], params: CX47ESLPParams) -> StoreLikelihoodModel:
    if not rows:
        return StoreLikelihoodModel(
            mean=np.zeros((1,), dtype=np.float32),
            std=np.ones((1,), dtype=np.float32),
            direction=np.zeros((1,), dtype=np.float32),
            quality_edges=np.asarray([-0.5, 0.0, 0.5], dtype=np.float32),
            global_positive_rate=0.0,
            class_counts={},
            struct_counts={},
            quality_counts={},
            struct_quality_counts={},
            positive_count=0,
            negative_count=0,
        )
    x = np.stack([np.asarray(row['feature'], dtype=np.float32) for row in rows], axis=0).astype(np.float32)
    y = np.asarray([float(row['label']) for row in rows], dtype=np.float32)
    mean = x.mean(axis=0).astype(np.float32)
    std = x.std(axis=0).astype(np.float32)
    std[std < 1e-6] = 1.0
    z = ((x - mean[None, :]) / std[None, :]).astype(np.float32)
    pos = z[y > 0.5]
    neg = z[y <= 0.5]
    if pos.shape[0] <= 0 or neg.shape[0] <= 0:
        direction = np.zeros((z.shape[1],), dtype=np.float32)
        scores = np.zeros((z.shape[0],), dtype=np.float32)
    else:
        pos_mu = pos.mean(axis=0).astype(np.float32)
        neg_mu = neg.mean(axis=0).astype(np.float32)
        pos_var = pos.var(axis=0).astype(np.float32)
        neg_var = neg.var(axis=0).astype(np.float32)
        direction = (pos_mu - neg_mu) / np.maximum(pos_var + neg_var + float(params.diag_reg), 1e-6)
        norm = float(np.linalg.norm(direction))
        if norm > 1e-6:
            direction = (direction / norm).astype(np.float32)
        scores = np.dot(z, direction.astype(np.float32)).astype(np.float32)
    edges = _quality_bin_edges(scores)

    class_counts: defaultdict[tuple[Any, ...], list[int]] = defaultdict(lambda: [0, 0])
    struct_counts: defaultdict[tuple[Any, ...], list[int]] = defaultdict(lambda: [0, 0])
    quality_counts: defaultdict[int, list[int]] = defaultdict(lambda: [0, 0])
    struct_quality_counts: defaultdict[tuple[Any, ...], list[int]] = defaultdict(lambda: [0, 0])
    for idx, row in enumerate(rows):
        event_key = tuple(row['event_key'])
        class_sig = _class_sig(event_key)
        qbin = int(np.searchsorted(edges, scores[idx], side='right'))
        label = float(row['label'])
        _count_update(class_counts, class_sig, label)
        _count_update(struct_counts, event_key, label)
        _count_update(quality_counts, qbin, label)
        _count_update(struct_quality_counts, (*event_key, qbin), label)

    return StoreLikelihoodModel(
        mean=mean,
        std=std,
        direction=direction.astype(np.float32),
        quality_edges=edges.astype(np.float32),
        global_positive_rate=float(np.mean(y)),
        class_counts={key: (int(val[0]), int(val[1])) for key, val in class_counts.items()},
        struct_counts={key: (int(val[0]), int(val[1])) for key, val in struct_counts.items()},
        quality_counts={int(key): (int(val[0]), int(val[1])) for key, val in quality_counts.items()},
        struct_quality_counts={key: (int(val[0]), int(val[1])) for key, val in struct_quality_counts.items()},
        positive_count=int(np.sum(y > 0.5)),
        negative_count=int(np.sum(y <= 0.5)),
    )


def _posterior_rate(counts: tuple[int, int] | None, prior: float, strength: float) -> float:
    positive, total = counts if isinstance(counts, tuple) else (0, 0)
    return float((float(positive) + float(strength) * float(prior)) / max(float(total) + float(strength), 1e-6))


class TracePolicy(parent_mod.RBCCPolicy):
    def __init__(self, case, bundle, field, params: CX47ESLPParams, memory: dict[str, Any], support_counter: dict[tuple[Any, ...], int]) -> None:
        super().__init__(case, bundle, field, _to_parent_params(params), memory, disable_witness_transfer=False, force_negative_skip=False, collect_quality_rows=False)
        self.params47e = params
        self.memory = memory
        self.support_counter = dict(support_counter)
        self.rows: list[dict[str, Any]] = []

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx47e_pending', None)
        return super().start_search(planner, start, goal, h_pair, search_state)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self._family_active() and isinstance(node_ctx, dict) and len(list(node_ctx.get('macros', []))) > 0:
            event_key = _event_key(self.case, node_ctx)
            search_state['cx47e_pending'] = {
                'feature': _feature(self.case, self.bundle, record, node_ctx, self.support_counter),
                'event_key': event_key,
                'support_count': int(_support_count(event_key, self.support_counter)),
                'store_before': float(self.stats.get('witness_store_negative', 0.0)),
            }
        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        ranked = super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        pending = search_state.get('cx47e_pending')
        if isinstance(pending, dict):
            store_before = float(pending.get('store_before', 0.0))
            store_after = float(self.stats.get('witness_store_negative', 0.0))
            self.rows.append(
                {
                    'feature': np.asarray(pending['feature'], dtype=np.float32),
                    'event_key': tuple(pending['event_key']),
                    'support_count': int(pending.get('support_count', 0)),
                    'label': 1.0 if store_after > store_before + 1e-6 else 0.0,
                }
            )
            search_state['cx47e_pending'] = None
        return ranked


def _collect_rows(train_assets, predictor, cfg: CXGlobalConfig, parent_params: parent_mod.CX46FRBCCParams, memory: dict[str, Any], params: CX47ESLPParams, device: str) -> tuple[list[dict[str, Any]], dict[tuple[Any, ...], int]]:
    support_counter = _fit_support_counter(train_assets, predictor, cfg, parent_params, memory, device)
    rows: list[dict[str, Any]] = []
    for asset in train_assets:
        field = parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = TracePolicy(asset['case'], bundle, field, params, memory, support_counter)
        run_hybrid_with_policy(asset['case'], field, 20000, successor_policy=policy, record_expanded=False)
        rows.extend(policy.rows)
    return rows, support_counter


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX47ESLPParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = _to_parent_params(params)
    dependencies = dependencies if isinstance(dependencies, dict) else {}
    memory = dependencies.get('parent_memory')
    if not isinstance(memory, dict):
        memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    rows = dependencies.get('store_rows')
    support_counter = dependencies.get('support_counter')
    if not isinstance(rows, list) or not isinstance(support_counter, dict):
        rows, support_counter = _collect_rows(calib_train_assets, predictor, cfg, parent_params, memory, params, device)
    model = _fit_store_model(rows, params)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx47_e_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'store_model': {
                    'positive_count': int(model.positive_count),
                    'negative_count': int(model.negative_count),
                    'class_key_count': int(len(model.class_counts)),
                    'event_key_count': int(len(model.struct_counts)),
                    'quality_bin_count': int(len(model.quality_counts)),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    memory = dict(memory)
    memory['store_model'] = model
    memory['support_counter'] = dict(support_counter)
    return memory


class SLPPolicy(parent_mod.RBCCPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        params: CX47ESLPParams,
        memory: dict[str, Any],
        *,
        disable_witness_transfer: bool = False,
        disable_store_proxy: bool = False,
        force_negative_skip: bool = False,
        collect_quality_rows: bool = False,
    ) -> None:
        super().__init__(
            case,
            bundle,
            field,
            _to_parent_params(params),
            memory,
            disable_witness_transfer=disable_witness_transfer,
            force_negative_skip=force_negative_skip,
            collect_quality_rows=collect_quality_rows,
        )
        self.params47e = params
        self.memory = memory
        self.disable_store_proxy = bool(disable_store_proxy)
        self.store_model: StoreLikelihoodModel = memory['store_model']
        self.support_counter = dict(memory.get('support_counter', {}))
        self.stats['store_proxy_skips'] = 0.0
        self.stats['store_proxy_prob_sum'] = 0.0
        self.stats['store_proxy_prob_count'] = 0.0
        self.stats['store_proxy_period_sum'] = 0.0
        self.stats['store_proxy_period_count'] = 0.0

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx47e_seen', {})
        search_state.setdefault('cx47e_miss_streak', {})
        search_state.setdefault('cx47e_review_key', None)
        return super().start_search(planner, start, goal, h_pair, search_state)

    def _store_prob(self, record, node_ctx: dict[str, Any]) -> float:
        event_key = _event_key(self.case, node_ctx)
        feat = _feature(self.case, self.bundle, record, node_ctx, self.support_counter)
        qbin = _quality_bin(self.store_model, feat)
        p_global = float(self.store_model.global_positive_rate)
        p_class = _posterior_rate(
            self.store_model.class_counts.get(_class_sig(event_key)),
            p_global,
            float(self.params47e.class_prior_strength),
        )
        p_struct = _posterior_rate(
            self.store_model.struct_counts.get(event_key),
            p_class,
            float(self.params47e.struct_prior_strength),
        )
        p_quality = _posterior_rate(
            self.store_model.quality_counts.get(int(qbin)),
            p_global,
            float(self.params47e.quality_prior_strength),
        )
        prior_mix = (1.0 - float(self.params47e.quality_mix)) * p_struct + float(self.params47e.quality_mix) * p_quality
        p_sq = _posterior_rate(
            self.store_model.struct_quality_counts.get((*event_key, int(qbin))),
            prior_mix,
            float(self.params47e.struct_quality_prior_strength),
        )
        prob = 0.35 * p_struct + 0.50 * p_sq + 0.15 * p_quality
        return float(np.clip(prob, 0.0, 1.0))

    def _review_period(self, base_prob: float, event_key: tuple[Any, ...], miss_streak: int) -> int:
        effective_prob = float(base_prob) * float(np.exp(-float(self.params47e.miss_decay) * float(max(miss_streak, 0))))
        period = 1.0 + float(self.params47e.review_stride_scale) * float(np.clip(1.0 - effective_prob, 0.0, 1.0))
        support = float(_support_strength(event_key, self.support_counter))
        period = period / max(1.0 + float(self.params47e.support_bonus) * support, 1e-6)
        if effective_prob >= float(self.params47e.force_review_prob):
            period = 1.0
        period = float(np.clip(period, 1.0, float(max(int(self.params47e.max_review_period), 1))))
        self.stats['store_proxy_period_sum'] = float(self.stats.get('store_proxy_period_sum', 0.0) + period)
        self.stats['store_proxy_period_count'] = float(self.stats.get('store_proxy_period_count', 0.0) + 1.0)
        return int(max(1, min(int(self.params47e.max_review_period), int(round(period)))))

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self._family_active() or not isinstance(node_ctx, dict) or len(list(node_ctx.get('macros', []))) <= 0:
            return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_witness_transfer:
            search_state['cx47e_review_key'] = None
            return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

        sig = self._sig(record, node_ctx)
        witness = self._probe_witness(sig, record, search_state)
        if isinstance(witness, dict):
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            search_state['cx46d_pending'] = None
            search_state['cx47e_review_key'] = None
            return []

        if not self.disable_store_proxy:
            event_key = _event_key(self.case, node_ctx)
            seen_map = dict(search_state.get('cx47e_seen', {}))
            seen = int(seen_map.get(event_key, 0)) + 1
            seen_map[event_key] = seen
            search_state['cx47e_seen'] = seen_map
            miss_map = dict(search_state.get('cx47e_miss_streak', {}))
            miss_streak = int(miss_map.get(event_key, 0))
            prob = float(self._store_prob(record, node_ctx))
            self.stats['store_proxy_prob_sum'] = float(self.stats.get('store_proxy_prob_sum', 0.0) + prob)
            self.stats['store_proxy_prob_count'] = float(self.stats.get('store_proxy_prob_count', 0.0) + 1.0)
            period = int(self._review_period(prob, event_key, miss_streak))
            if seen > int(max(self.params47e.warmup_reviews, 0)):
                probe_idx = int(seen - int(self.params47e.warmup_reviews) - 1)
                if (probe_idx % max(period, 1)) != 0:
                    self.stats['store_proxy_skips'] = float(self.stats.get('store_proxy_skips', 0.0) + 1.0)
                    search_state['cx46d_pending'] = None
                    search_state['cx47e_review_key'] = None
                    return quality_mod.witness_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
            search_state['cx47e_review_key'] = event_key
        else:
            search_state['cx47e_review_key'] = None

        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        review_key = search_state.get('cx47e_review_key')
        store_before = float(self.stats.get('witness_store_negative', 0.0))
        ranked = super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if isinstance(review_key, tuple):
            store_after = float(self.stats.get('witness_store_negative', 0.0))
            miss_map = dict(search_state.get('cx47e_miss_streak', {}))
            if store_after > store_before + 1e-6:
                miss_map[review_key] = 0
            else:
                miss_map[review_key] = int(miss_map.get(review_key, 0)) + 1
            search_state['cx47e_miss_streak'] = miss_map
        search_state['cx47e_review_key'] = None
        return ranked


def make_policy(memory: dict[str, Any], params: CX47ESLPParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = SLPPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        disable_store_proxy=bool(ablation.get('disable_store_proxy', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
        collect_quality_rows=False,
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX47ESLPParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, _to_parent_params(params), memory)


def build_standard_field(sample, predictor, params: CX47ESLPParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(sample, predictor, _to_parent_params(params), memory).astype(np.float32)
