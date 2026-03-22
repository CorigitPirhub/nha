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
class FutureSavingsModel:
    mean: np.ndarray
    std: np.ndarray
    direction: np.ndarray
    quality_edges: np.ndarray
    global_mean: float
    class_stats: dict[tuple[Any, ...], tuple[float, int]]
    struct_stats: dict[tuple[Any, ...], tuple[float, int]]
    quality_stats: dict[int, tuple[float, int]]
    struct_quality_stats: dict[tuple[Any, ...], tuple[float, int]]
    positive_count: int
    zero_count: int


@dataclass(frozen=True)
class CX47HFCSParams:
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
    force_review_value: float
    max_review_period: int
    warmup_reviews: int
    provisional_store_relief: float
    realized_savings_bonus: float
    realized_savings_cap: int
    future_hit_scale: float
    diag_reg: float


def param_grid() -> list[CX47HFCSParams]:
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
        class_prior_strength=24.0,
        struct_prior_strength=12.0,
        quality_prior_strength=12.0,
        struct_quality_prior_strength=8.0,
        support_bonus=0.18,
        max_review_period=8,
        provisional_store_relief=0.4,
        realized_savings_cap=4,
        diag_reg=0.25,
    )
    return [
        CX47HFCSParams(**common, quality_mix=0.55, miss_decay=0.14, review_stride_scale=2.6, force_review_value=0.16, warmup_reviews=4, realized_savings_bonus=0.28, future_hit_scale=1.5),
        CX47HFCSParams(**common, quality_mix=0.60, miss_decay=0.18, review_stride_scale=3.0, force_review_value=0.18, warmup_reviews=4, realized_savings_bonus=0.35, future_hit_scale=2.0),
        CX47HFCSParams(**common, quality_mix=0.50, miss_decay=0.12, review_stride_scale=2.3, force_review_value=0.14, warmup_reviews=6, realized_savings_bonus=0.32, future_hit_scale=1.5),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'No-Future-Savings-Proxy', 'disable_future_proxy': True},
        {'name': 'No-Realized-Savings-Credit', 'disable_realized_credit': True},
    ]


def _to_parent_params(params: CX47HFCSParams) -> parent_mod.CX46FRBCCParams:
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


def _quality_bin(model: FutureSavingsModel, feat: np.ndarray) -> int:
    if model.direction.shape[0] != feat.shape[0]:
        return 0
    z = ((feat.astype(np.float32) - model.mean) / model.std).astype(np.float32)
    score = float(np.dot(z, model.direction))
    return int(np.searchsorted(model.quality_edges, score, side='right'))


def _scaled_savings(future_hits: float, params: CX47HFCSParams) -> float:
    return float(np.tanh(float(max(future_hits, 0.0)) / max(float(params.future_hit_scale), 1e-6)))


def _accumulate(counter: defaultdict[Any, list[float]], key: Any, value: float) -> None:
    item = counter[key]
    item[0] += float(value)
    item[1] += 1.0


def _fit_future_model(rows: list[dict[str, Any]], params: CX47HFCSParams) -> FutureSavingsModel:
    if not rows:
        return FutureSavingsModel(
            mean=np.zeros((1,), dtype=np.float32),
            std=np.ones((1,), dtype=np.float32),
            direction=np.zeros((1,), dtype=np.float32),
            quality_edges=np.asarray([-0.5, 0.0, 0.5], dtype=np.float32),
            global_mean=0.0,
            class_stats={},
            struct_stats={},
            quality_stats={},
            struct_quality_stats={},
            positive_count=0,
            zero_count=0,
        )
    x = np.stack([np.asarray(row['feature'], dtype=np.float32) for row in rows], axis=0).astype(np.float32)
    y = np.asarray([float(row['label']) for row in rows], dtype=np.float32)
    mean = x.mean(axis=0).astype(np.float32)
    std = x.std(axis=0).astype(np.float32)
    std[std < 1e-6] = 1.0
    z = ((x - mean[None, :]) / std[None, :]).astype(np.float32)
    pos = z[y > 1e-6]
    neg = z[y <= 1e-6]
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

    class_stats: defaultdict[tuple[Any, ...], list[float]] = defaultdict(lambda: [0.0, 0.0])
    struct_stats: defaultdict[tuple[Any, ...], list[float]] = defaultdict(lambda: [0.0, 0.0])
    quality_stats: defaultdict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    struct_quality_stats: defaultdict[tuple[Any, ...], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for idx, row in enumerate(rows):
        event_key = tuple(row['event_key'])
        class_sig = _class_sig(event_key)
        qbin = int(np.searchsorted(edges, scores[idx], side='right'))
        value = float(row['label'])
        _accumulate(class_stats, class_sig, value)
        _accumulate(struct_stats, event_key, value)
        _accumulate(quality_stats, qbin, value)
        _accumulate(struct_quality_stats, (*event_key, qbin), value)

    return FutureSavingsModel(
        mean=mean,
        std=std,
        direction=direction.astype(np.float32),
        quality_edges=edges.astype(np.float32),
        global_mean=float(np.mean(y)),
        class_stats={key: (float(val[0]), int(val[1])) for key, val in class_stats.items()},
        struct_stats={key: (float(val[0]), int(val[1])) for key, val in struct_stats.items()},
        quality_stats={int(key): (float(val[0]), int(val[1])) for key, val in quality_stats.items()},
        struct_quality_stats={key: (float(val[0]), int(val[1])) for key, val in struct_quality_stats.items()},
        positive_count=int(np.sum(y > 1e-6)),
        zero_count=int(np.sum(y <= 1e-6)),
    )


def _posterior_mean(stats: tuple[float, int] | None, prior_mean: float, strength: float) -> float:
    total_value, count = stats if isinstance(stats, tuple) else (0.0, 0)
    return float((float(total_value) + float(strength) * float(prior_mean)) / max(float(count) + float(strength), 1e-6))


class FutureTracePolicy(parent_mod.RBCCPolicy):
    def __init__(self, case, bundle, field, params: CX47HFCSParams, memory: dict[str, Any], support_counter: dict[tuple[Any, ...], int]) -> None:
        super().__init__(
            case,
            bundle,
            field,
            _to_parent_params(params),
            memory,
            disable_witness_transfer=False,
            force_negative_skip=False,
            collect_quality_rows=True,
        )
        self.params47h = params
        self.support_counter = dict(support_counter)
        self.rows: list[dict[str, Any]] = []

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx47h_pending', None)
        return super().start_search(planner, start, goal, h_pair, search_state)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self._family_active() and isinstance(node_ctx, dict) and len(list(node_ctx.get('macros', []))) > 0:
            event_key = _event_key(self.case, node_ctx)
            search_state['cx47h_pending'] = {
                'feature': _feature(self.case, self.bundle, record, node_ctx, self.support_counter),
                'event_key': event_key,
                'support_count': int(_support_count(event_key, self.support_counter)),
                'store_before': float(self.stats.get('witness_store_negative', 0.0)),
                'trace_before': int(search_state.get('cx46d_trace_seq', 0)),
            }
        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        ranked = super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        pending = search_state.get('cx47h_pending')
        if isinstance(pending, dict):
            store_before = float(pending.get('store_before', 0.0))
            store_after = float(self.stats.get('witness_store_negative', 0.0))
            trace_after = int(search_state.get('cx46d_trace_seq', 0))
            witness_id = int(trace_after) if store_after > store_before + 1e-6 and trace_after > int(pending.get('trace_before', 0)) else -1
            self.rows.append(
                {
                    'feature': np.asarray(pending['feature'], dtype=np.float32),
                    'event_key': tuple(pending['event_key']),
                    'support_count': int(pending.get('support_count', 0)),
                    'witness_id': int(witness_id),
                }
            )
            search_state['cx47h_pending'] = None
        return ranked

    def export_future_rows(self) -> list[dict[str, Any]]:
        trace_map = dict(getattr(self, '_last_trace_rows', {}))
        out: list[dict[str, Any]] = []
        for row in self.rows:
            item = dict(row)
            witness_id = int(item.pop('witness_id', -1))
            future_hits = 0.0
            revisit_count = 0.0
            if witness_id > 0 and witness_id in trace_map:
                trace = dict(trace_map[witness_id])
                future_hits = float(trace.get('hit_count', 0.0))
                revisit_count = float(trace.get('revisit_count', 0.0))
            item['future_hits'] = future_hits
            item['revisit_count'] = revisit_count
            item['label'] = float(_scaled_savings(future_hits, self.params47h))
            out.append(item)
        return out


def _collect_rows(train_assets, predictor, cfg: CXGlobalConfig, parent_params: parent_mod.CX46FRBCCParams, memory: dict[str, Any], params: CX47HFCSParams, device: str) -> tuple[list[dict[str, Any]], dict[tuple[Any, ...], int]]:
    support_counter = _fit_support_counter(train_assets, predictor, cfg, parent_params, memory, device)
    rows: list[dict[str, Any]] = []
    for asset in train_assets:
        field = parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = FutureTracePolicy(asset['case'], bundle, field, params, memory, support_counter)
        run_hybrid_with_policy(asset['case'], field, 20000, successor_policy=policy, record_expanded=False)
        rows.extend(policy.export_future_rows())
    return rows, support_counter


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX47HFCSParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = _to_parent_params(params)
    dependencies = dependencies if isinstance(dependencies, dict) else {}
    memory = dependencies.get('parent_memory')
    if not isinstance(memory, dict):
        memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    rows = dependencies.get('future_rows')
    support_counter = dependencies.get('support_counter')
    if not isinstance(rows, list) or not isinstance(support_counter, dict):
        rows, support_counter = _collect_rows(calib_train_assets, predictor, cfg, parent_params, memory, params, device)
    model = _fit_future_model(rows, params)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx47_h_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'future_model': {
                    'positive_count': int(model.positive_count),
                    'zero_count': int(model.zero_count),
                    'class_key_count': int(len(model.class_stats)),
                    'event_key_count': int(len(model.struct_stats)),
                    'quality_bin_count': int(len(model.quality_stats)),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    memory = dict(memory)
    memory['future_model'] = model
    memory['support_counter'] = dict(support_counter)
    return memory


class FCSPolicy(parent_mod.RBCCPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        params: CX47HFCSParams,
        memory: dict[str, Any],
        *,
        disable_witness_transfer: bool = False,
        disable_future_proxy: bool = False,
        disable_realized_credit: bool = False,
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
        self.params47h = params
        self.disable_future_proxy = bool(disable_future_proxy)
        self.disable_realized_credit = bool(disable_realized_credit)
        self.future_model: FutureSavingsModel = memory['future_model']
        self.support_counter = dict(memory.get('support_counter', {}))
        self.stats['future_proxy_skips'] = 0.0
        self.stats['future_proxy_value_sum'] = 0.0
        self.stats['future_proxy_value_count'] = 0.0
        self.stats['future_proxy_period_sum'] = 0.0
        self.stats['future_proxy_period_count'] = 0.0
        self.stats['future_saved_reviews_credit'] = 0.0

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx47h_seen', {})
        search_state.setdefault('cx47h_miss_streak', {})
        search_state.setdefault('cx47h_realized_savings', {})
        search_state.setdefault('cx47h_review_key', None)
        return super().start_search(planner, start, goal, h_pair, search_state)

    def _register_store(self, sig: tuple[Any, ...], record, node_ctx: dict[str, Any], margin: float, quality: dict[str, float], search_state: dict[str, Any]) -> dict[str, Any]:
        witness = super()._register_store(sig, record, node_ctx, margin, quality, search_state)
        review_key = search_state.get('cx47h_review_key')
        if isinstance(review_key, tuple):
            witness_map = dict(search_state.get('cx46d_witness', {}))
            stored = dict(witness_map.get(sig, witness))
            stored['review_event_key'] = tuple(review_key)
            witness_map[sig] = stored
            search_state['cx46d_witness'] = witness_map
            return stored
        return witness

    def _probe_witness(self, sig: tuple[Any, ...], record, search_state: dict[str, Any]) -> dict[str, Any] | None:
        witness = super()._probe_witness(sig, record, search_state)
        if isinstance(witness, dict) and not self.disable_realized_credit:
            review_key = witness.get('review_event_key')
            if isinstance(review_key, tuple):
                realized = dict(search_state.get('cx47h_realized_savings', {}))
                realized[review_key] = int(realized.get(review_key, 0)) + 1
                search_state['cx47h_realized_savings'] = realized
                miss_map = dict(search_state.get('cx47h_miss_streak', {}))
                miss_map[review_key] = 0
                search_state['cx47h_miss_streak'] = miss_map
                self.stats['future_saved_reviews_credit'] = float(self.stats.get('future_saved_reviews_credit', 0.0) + 1.0)
        return witness

    def _expected_savings(self, record, node_ctx: dict[str, Any]) -> float:
        event_key = _event_key(self.case, node_ctx)
        feat = _feature(self.case, self.bundle, record, node_ctx, self.support_counter)
        qbin = _quality_bin(self.future_model, feat)
        p_global = float(self.future_model.global_mean)
        p_class = _posterior_mean(
            self.future_model.class_stats.get(_class_sig(event_key)),
            p_global,
            float(self.params47h.class_prior_strength),
        )
        p_struct = _posterior_mean(
            self.future_model.struct_stats.get(event_key),
            p_class,
            float(self.params47h.struct_prior_strength),
        )
        p_quality = _posterior_mean(
            self.future_model.quality_stats.get(int(qbin)),
            p_global,
            float(self.params47h.quality_prior_strength),
        )
        prior_mix = (1.0 - float(self.params47h.quality_mix)) * p_struct + float(self.params47h.quality_mix) * p_quality
        p_sq = _posterior_mean(
            self.future_model.struct_quality_stats.get((*event_key, int(qbin))),
            prior_mix,
            float(self.params47h.struct_quality_prior_strength),
        )
        value = 0.30 * p_struct + 0.50 * p_sq + 0.20 * p_quality
        return float(np.clip(value, 0.0, 1.0))

    def _review_period(self, base_value: float, event_key: tuple[Any, ...], miss_streak: int, realized_savings: int) -> int:
        effective_value = float(base_value) * float(np.exp(-float(self.params47h.miss_decay) * float(max(miss_streak, 0))))
        support = float(_support_strength(event_key, self.support_counter))
        if not self.disable_realized_credit:
            realized_credit = float(np.tanh(float(min(realized_savings, int(self.params47h.realized_savings_cap))) / 2.0))
            effective_value = float(np.clip(effective_value + float(self.params47h.realized_savings_bonus) * realized_credit, 0.0, 1.0))
        period = 1.0 + float(self.params47h.review_stride_scale) * float(np.clip(1.0 - effective_value, 0.0, 1.0))
        period = period / max(1.0 + float(self.params47h.support_bonus) * support, 1e-6)
        if effective_value >= float(self.params47h.force_review_value):
            period = 1.0
        period = float(np.clip(period, 1.0, float(max(int(self.params47h.max_review_period), 1))))
        self.stats['future_proxy_period_sum'] = float(self.stats.get('future_proxy_period_sum', 0.0) + period)
        self.stats['future_proxy_period_count'] = float(self.stats.get('future_proxy_period_count', 0.0) + 1.0)
        return int(max(1, min(int(self.params47h.max_review_period), int(round(period)))))

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self._family_active() or not isinstance(node_ctx, dict) or len(list(node_ctx.get('macros', []))) <= 0:
            return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_witness_transfer:
            search_state['cx47h_review_key'] = None
            return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

        sig = self._sig(record, node_ctx)
        witness = self._probe_witness(sig, record, search_state)
        if isinstance(witness, dict):
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            search_state['cx46d_pending'] = None
            search_state['cx47h_review_key'] = None
            return []

        if not self.disable_future_proxy:
            event_key = _event_key(self.case, node_ctx)
            seen_map = dict(search_state.get('cx47h_seen', {}))
            seen = int(seen_map.get(event_key, 0)) + 1
            seen_map[event_key] = seen
            search_state['cx47h_seen'] = seen_map
            miss_map = dict(search_state.get('cx47h_miss_streak', {}))
            miss_streak = int(miss_map.get(event_key, 0))
            realized_savings = int(dict(search_state.get('cx47h_realized_savings', {})).get(event_key, 0))
            value = float(self._expected_savings(record, node_ctx))
            self.stats['future_proxy_value_sum'] = float(self.stats.get('future_proxy_value_sum', 0.0) + value)
            self.stats['future_proxy_value_count'] = float(self.stats.get('future_proxy_value_count', 0.0) + 1.0)
            period = int(self._review_period(value, event_key, miss_streak, realized_savings))
            if seen > int(max(self.params47h.warmup_reviews, 0)):
                probe_idx = int(seen - int(self.params47h.warmup_reviews) - 1)
                if (probe_idx % max(period, 1)) != 0:
                    self.stats['future_proxy_skips'] = float(self.stats.get('future_proxy_skips', 0.0) + 1.0)
                    search_state['cx46d_pending'] = None
                    search_state['cx47h_review_key'] = None
                    return quality_mod.witness_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
            search_state['cx47h_review_key'] = event_key
        else:
            search_state['cx47h_review_key'] = None

        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        review_key = search_state.get('cx47h_review_key')
        store_before = float(self.stats.get('witness_store_negative', 0.0))
        ranked = super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if isinstance(review_key, tuple):
            store_after = float(self.stats.get('witness_store_negative', 0.0))
            miss_map = dict(search_state.get('cx47h_miss_streak', {}))
            if store_after > store_before + 1e-6:
                current = float(miss_map.get(review_key, 0))
                miss_map[review_key] = int(max(current - float(self.params47h.provisional_store_relief), 0.0))
            else:
                miss_map[review_key] = int(miss_map.get(review_key, 0)) + 1
            search_state['cx47h_miss_streak'] = miss_map
        search_state['cx47h_review_key'] = None
        return ranked


def make_policy(memory: dict[str, Any], params: CX47HFCSParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = FCSPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        disable_future_proxy=bool(ablation.get('disable_future_proxy', False)),
        disable_realized_credit=bool(ablation.get('disable_realized_credit', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
        collect_quality_rows=False,
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX47HFCSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, _to_parent_params(params), memory)


def build_standard_field(sample, predictor, params: CX47HFCSParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(sample, predictor, _to_parent_params(params), memory).astype(np.float32)
