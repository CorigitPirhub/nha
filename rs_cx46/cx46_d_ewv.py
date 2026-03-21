from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx22.common import episode_feature_vector, state_feature_vector
from rs_cx23.common import class_key
from rs_cx27.common import coarse_state_key
from rs_cx44 import cx44_b_fcwt as witness_mod
from rs_cx8.common import run_hybrid_with_policy


TARGET_SCENARIOS = ('parasol_misc', 'deadend_labyrinth', 'narrow_passage')
QUALITY_CLASSES = ('reliable', 'local', 'fragile')


@dataclass(frozen=True)
class CX46DEWVParams:
    review_cell_stride: int
    review_yaw_bins: int
    margin_thr: float
    anchor_eps: float
    enable_parasol_misc: bool
    enable_deadend_labyrinth: bool
    enable_narrow_passage: bool
    band_slack: float
    similarity_scale: float
    reliable_weight: float
    local_weight: float
    fragile_weight: float
    anchor_gain: float
    ttl_gain: float
    max_ttl: int
    min_band_count: int


@dataclass(frozen=True)
class QualityBand:
    low: np.ndarray
    high: np.ndarray
    mean: np.ndarray
    std: np.ndarray
    prototype: np.ndarray
    prior: float
    ttl_quantile: float
    anchor_quantile: float
    reuse_rate_mean: float
    count: int


def param_grid() -> list[CX46DEWVParams]:
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
        min_band_count=8,
    )
    return [
        CX46DEWVParams(**common, reliable_weight=1.20, local_weight=0.55, fragile_weight=0.85, anchor_gain=1.10, ttl_gain=0.80, max_ttl=96),
        CX46DEWVParams(**common, reliable_weight=1.30, local_weight=0.45, fragile_weight=0.90, anchor_gain=1.25, ttl_gain=0.90, max_ttl=112),
        CX46DEWVParams(**common, reliable_weight=1.15, local_weight=0.65, fragile_weight=0.80, anchor_gain=1.00, ttl_gain=0.75, max_ttl=88),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'Proxy-Only-Negative', 'force_negative_skip': True},
    ]


def _load_parent_params() -> witness_mod.parent_mod.parent_mod.CX34AMSRParams:
    data = json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))
    return witness_mod.parent_mod.parent_mod.CX34AMSRParams(**data['params'])


def _scenario_enabled(params: CX46DEWVParams, scenario: str) -> bool:
    return bool(
        (params.enable_parasol_misc and str(scenario) == 'parasol_misc')
        or (params.enable_deadend_labyrinth and str(scenario) == 'deadend_labyrinth')
        or (params.enable_narrow_passage and str(scenario) == 'narrow_passage')
    )


def _scenario_onehot(scenario: str) -> np.ndarray:
    return np.asarray([1.0 if str(scenario) == item else 0.0 for item in TARGET_SCENARIOS], dtype=np.float32)


def _type_sig(case: dict[str, Any], node_ctx: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(case.get('scenario', '')),
        str(class_key(node_ctx)),
        int(bool(node_ctx.get('must_precede', False))),
        int(len(list(node_ctx.get('macros', []))) > 0),
    )


def _fit_count_stats(type_counter: Counter[tuple[Any, ...]]) -> dict[str, dict[str, float]]:
    grouped: defaultdict[str, list[int]] = defaultdict(list)
    for sig, count in type_counter.items():
        grouped[str(sig[0])].append(int(count))
    out: dict[str, dict[str, float]] = {}
    for scenario, counts in grouped.items():
        arr = np.asarray(counts, dtype=np.float32)
        out[scenario] = {
            'q50': float(np.quantile(arr, 0.5)),
            'q90': float(np.quantile(arr, 0.9)),
            'max': float(np.max(arr)),
        }
    return out


def _type_redundancy(sig: tuple[Any, ...], type_counter: dict[tuple[Any, ...], int], type_stats: dict[str, dict[str, float]]) -> float:
    count = float(type_counter.get(sig, 0))
    stat = dict(type_stats.get(str(sig[0]), {}))
    q50 = float(stat.get('q50', 0.0))
    q90 = float(stat.get('q90', q50 + 1.0))
    if q90 <= q50 + 1e-6:
        return 0.0
    z = (count - q50) / max(q90 - q50, 1e-6)
    return float(np.clip(1.0 / (1.0 + np.exp(-3.0 * z)), 0.0, 1.0))


def _quality_feature(
    case: dict[str, Any],
    bundle: dict[str, Any],
    record,
    node_ctx: dict[str, Any],
    margin: float,
    type_counter: dict[tuple[Any, ...], int],
    type_stats: dict[str, dict[str, float]],
    margin_thr: float,
) -> np.ndarray:
    structural_sig = _type_sig(case, node_ctx)
    state_feat = state_feature_vector(node_ctx)
    episode_feat = episode_feature_vector(case, bundle, node_ctx)
    macros = list(node_ctx.get('macros', []))
    extra = np.asarray(
        [
            float(bool(node_ctx.get('must_precede', False))),
            float(len(macros) > 0),
            float(min(len(macros), 3)) / 3.0,
            float(_type_redundancy(structural_sig, type_counter, type_stats)),
            float(np.tanh(float(margin) / max(float(margin_thr), 1e-6))),
            float(np.tanh(float(getattr(record, 'anchor', 0.0)) / 10.0)),
        ],
        dtype=np.float32,
    )
    return np.concatenate([_scenario_onehot(str(case.get('scenario', ''))), state_feat, episode_feat, extra], axis=0).astype(np.float32)


def _fit_quality_band(rows: list[dict[str, Any]], total: int) -> QualityBand | None:
    if not rows:
        return None
    feats = np.stack([np.asarray(row['feature'], dtype=np.float32) for row in rows], axis=0).astype(np.float32)
    low = np.quantile(feats, 0.05, axis=0).astype(np.float32)
    high = np.quantile(feats, 0.95, axis=0).astype(np.float32)
    mean = feats.mean(axis=0).astype(np.float32)
    std = feats.std(axis=0).astype(np.float32)
    std[std < 1e-6] = 1.0
    z = ((feats - mean) / std).astype(np.float32)
    norms = np.linalg.norm(z, axis=1, keepdims=True)
    norms[norms < 1e-6] = 1.0
    proto = (z / norms).mean(axis=0).astype(np.float32)
    pn = float(np.linalg.norm(proto))
    if pn > 1e-6:
        proto = (proto / pn).astype(np.float32)
    return QualityBand(
        low=low,
        high=high,
        mean=mean,
        std=std,
        prototype=proto,
        prior=float(len(rows)) / max(int(total), 1),
        ttl_quantile=float(np.quantile(np.asarray([float(row['max_popped_gap']) for row in rows], dtype=np.float32), 0.8)),
        anchor_quantile=float(np.quantile(np.asarray([float(row['max_anchor_gap']) for row in rows], dtype=np.float32), 0.8)),
        reuse_rate_mean=float(np.mean([float(row['reuse_rate']) for row in rows])),
        count=int(len(rows)),
    )


def _band_similarity(band: QualityBand | None, feat: np.ndarray, slack: float) -> float:
    if band is None:
        return -6.0
    feat = np.asarray(feat, dtype=np.float32)
    within = float(np.mean((feat >= (band.low - float(slack))) & (feat <= (band.high + float(slack)))))
    z = ((feat - band.mean) / band.std).astype(np.float32)
    zn = float(np.linalg.norm(z))
    if zn > 1e-6:
        z = (z / zn).astype(np.float32)
    sim = float(np.dot(z, band.prototype))
    return float(1.5 * sim + 0.75 * within + np.log(max(float(band.prior), 1e-6)))


def _softmax(logits: dict[str, float], scale: float) -> dict[str, float]:
    if not logits:
        return {key: 0.0 for key in QUALITY_CLASSES}
    arr = np.asarray([float(scale) * float(logits[key]) for key in QUALITY_CLASSES], dtype=np.float32)
    arr = arr - float(np.max(arr))
    exp = np.exp(arr)
    denom = float(np.sum(exp))
    if denom <= 1e-6:
        return {key: 0.0 for key in QUALITY_CLASSES}
    return {key: float(exp[idx] / denom) for idx, key in enumerate(QUALITY_CLASSES)}


def _predict_quality(bands: dict[str, QualityBand | None], feat: np.ndarray, params: CX46DEWVParams) -> dict[str, float]:
    logits = {key: _band_similarity(bands.get(key), feat, float(params.band_slack)) for key in QUALITY_CLASSES}
    weights = _softmax(logits, float(params.similarity_scale))
    reliable = float(weights.get('reliable', 0.0))
    local = float(weights.get('local', 0.0))
    fragile = float(weights.get('fragile', 0.0))
    strength = float(np.clip(float(params.reliable_weight) * reliable + float(params.local_weight) * local - float(params.fragile_weight) * fragile, 0.0, 1.0))
    return {
        **weights,
        'strength': strength,
        'store_strength': float(np.clip(reliable + 0.6 * local, 0.0, 1.0)),
    }


def _build_type_memory(calib_train_assets, predictor, cfg: CXGlobalConfig, parent_params, parent_memory, params: CX46DEWVParams, device: str) -> tuple[dict[tuple[Any, ...], int], dict[str, dict[str, float]]]:
    type_counter: Counter[tuple[Any, ...]] = Counter()
    for asset in calib_train_assets:
        scenario = str(asset['case'].get('scenario', ''))
        if not _scenario_enabled(params, scenario):
            continue
        field = witness_mod.parent_mod.parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, parent_memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = witness_mod.parent_mod.parent_mod.make_policy(parent_memory, parent_params, asset['case'], bundle, field, device, ablation=None)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        search_state: dict[str, Any] = {}
        for state in path[:-1]:
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=0.0)
            ctx = policy.prepare_expand(None, rec, None, None, None, None, search_state, None)
            if not isinstance(ctx, dict):
                continue
            type_counter[_type_sig(asset['case'], ctx)] += 1
    return dict(type_counter), _fit_count_stats(type_counter)


class QualityTracePolicy(witness_mod.FCWTPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        parent_params,
        parent_memory: dict[str, Any],
        params: CX46DEWVParams,
        *,
        type_counter: dict[tuple[Any, ...], int],
        type_stats: dict[str, dict[str, float]],
        quality_bands: dict[str, QualityBand | None] | None,
        disable_witness_transfer: bool = False,
        force_negative_skip: bool = False,
        collect_quality_rows: bool = False,
    ) -> None:
        super().__init__(
            case,
            bundle,
            field,
            parent_params,
            parent_memory,
            witness_mod.CX44BFCWTParams(
                review_cell_stride=int(params.review_cell_stride),
                review_yaw_bins=int(params.review_yaw_bins),
                margin_thr=float(params.margin_thr),
                anchor_eps=float(params.anchor_eps),
                enable_parasol_misc=bool(params.enable_parasol_misc),
                enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
                enable_narrow_passage=bool(params.enable_narrow_passage),
            ),
            disable_witness_transfer=disable_witness_transfer,
            force_negative_skip=force_negative_skip,
        )
        self.params46 = params
        self.type_counter = dict(type_counter)
        self.type_stats = dict(type_stats)
        self.quality_bands = dict(quality_bands or {})
        self.collect_quality_rows = bool(collect_quality_rows)
        self.branch = 'witness_quality'
        self.stats['wqr_reliable_store'] = 0.0
        self.stats['wqr_local_store'] = 0.0
        self.stats['wqr_fragile_store'] = 0.0
        self.stats['wqr_strength_sum'] = 0.0
        self.stats['wqr_strength_count'] = 0.0

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx46d_witness', {})
        search_state.setdefault('cx46d_pending', None)
        search_state.setdefault('cx46d_trace_rows', {})
        search_state.setdefault('cx46d_trace_seq', 0)
        self._last_trace_rows = search_state['cx46d_trace_rows']
        if hasattr(super(), 'start_search'):
            return super().start_search(planner, start, goal, h_pair, search_state)

    def export_quality_rows(self) -> list[dict[str, Any]]:
        out = []
        for row in dict(getattr(self, '_last_trace_rows', {})).values():
            item = dict(row)
            feat = item.get('feature')
            if isinstance(feat, np.ndarray):
                item['feature'] = feat.astype(np.float32)
            out.append(item)
        return out

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        self._last_trace_rows = dict(search_state.get('cx46d_trace_rows', {}))
        return super().complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)

    def _sig(self, record, node_ctx: dict[str, Any]) -> tuple[Any, ...]:
        return (
            str(self.case.get('scenario', '')),
            str(class_key(node_ctx)),
            tuple(
                coarse_state_key(
                    record,
                    self.case,
                    cell_stride=int(self.params46.review_cell_stride),
                    yaw_bins=int(self.params46.review_yaw_bins),
                )
            ),
            int(bool(node_ctx.get('must_precede', False))),
            int(len(list(node_ctx.get('macros', []))) > 0),
        )

    def _quality_for_store(self, record, node_ctx: dict[str, Any], margin: float) -> dict[str, float]:
        feat = _quality_feature(
            self.case,
            self.bundle,
            record,
            node_ctx,
            float(margin),
            self.type_counter,
            self.type_stats,
            float(self.params46.margin_thr),
        )
        if self.quality_bands:
            pred = _predict_quality(self.quality_bands, feat, self.params46)
        else:
            pred = {'reliable': 0.0, 'local': 1.0, 'fragile': 0.0, 'strength': 1.0, 'store_strength': 1.0}
        return {'feature': feat, **pred}

    def _ttl_and_radius(self, quality: dict[str, float]) -> tuple[int, float]:
        if not self.quality_bands:
            return int(1_000_000), float(self.params46.anchor_eps)
        bands = self.quality_bands
        ttl = 0.0
        radius = 0.0
        for key in QUALITY_CLASSES:
            band = bands.get(key)
            weight = float(quality.get(key, 0.0))
            if band is None or weight <= 0.0:
                continue
            ttl += weight * float(band.ttl_quantile)
            radius += weight * float(band.anchor_quantile)
        ttl = min(float(self.params46.max_ttl), max(4.0, float(self.params46.ttl_gain) * ttl))
        radius = max(float(self.params46.anchor_eps), float(self.params46.anchor_gain) * radius)
        return int(round(ttl)), float(radius)

    def _register_store(self, sig: tuple[Any, ...], record, node_ctx: dict[str, Any], margin: float, quality: dict[str, float], search_state: dict[str, Any]) -> dict[str, Any]:
        witness_map = dict(search_state.get('cx46d_witness', {}))
        current_popped = int(search_state.get('popped', 0))
        current_anchor = float(getattr(record, 'anchor', 0.0))
        ttl, anchor_radius = self._ttl_and_radius(quality)
        seq = int(search_state.get('cx46d_trace_seq', 0)) + 1
        search_state['cx46d_trace_seq'] = seq
        witness = {
            'id': int(seq),
            'best_anchor': float(current_anchor),
            'margin': float(margin),
            'expiry': int(current_popped + ttl),
            'anchor_radius': float(anchor_radius),
            'quality': {key: float(quality.get(key, 0.0)) for key in ('reliable', 'local', 'fragile', 'strength', 'store_strength')},
        }
        witness_map[sig] = witness
        search_state['cx46d_witness'] = witness_map
        if self.collect_quality_rows:
            trace_map = dict(search_state.get('cx46d_trace_rows', {}))
            trace_map[int(seq)] = {
                'scenario': str(self.case.get('scenario', '')),
                'class_key': str(class_key(node_ctx)),
                'feature': np.asarray(quality['feature'], dtype=np.float32),
                'margin': float(margin),
                'revisit_count': 0,
                'hit_count': 0,
                'reuse_rate': 0.0,
                'max_popped_gap': 0.0,
                'max_anchor_gap': 0.0,
                'store_strength': float(quality.get('store_strength', 0.0)),
                'quality_strength': float(quality.get('strength', 0.0)),
                'reliable_weight': float(quality.get('reliable', 0.0)),
                'local_weight': float(quality.get('local', 0.0)),
                'fragile_weight': float(quality.get('fragile', 0.0)),
                'stored_popped': int(current_popped),
                'stored_anchor': float(current_anchor),
            }
            search_state['cx46d_trace_rows'] = trace_map
            self._last_trace_rows = trace_map
        return witness

    def _probe_witness(self, sig: tuple[Any, ...], record, search_state: dict[str, Any]) -> dict[str, Any] | None:
        witness = dict(search_state.get('cx46d_witness', {})).get(sig)
        if not isinstance(witness, dict):
            return None
        wid = int(witness.get('id', -1))
        trace_map = dict(search_state.get('cx46d_trace_rows', {}))
        if wid in trace_map:
            row = dict(trace_map[wid])
            current_popped = int(search_state.get('popped', 0))
            current_anchor = float(getattr(record, 'anchor', 0.0))
            row['revisit_count'] = int(row.get('revisit_count', 0)) + 1
            row['max_popped_gap'] = float(max(float(row.get('max_popped_gap', 0.0)), float(current_popped - int(row.get('stored_popped', current_popped)))))
            row['max_anchor_gap'] = float(max(float(row.get('max_anchor_gap', 0.0)), max(current_anchor - float(row.get('stored_anchor', current_anchor)), 0.0)))
            trace_map[wid] = row
            search_state['cx46d_trace_rows'] = trace_map
            self._last_trace_rows = trace_map
        current_popped = int(search_state.get('popped', 0))
        if int(witness.get('expiry', -1)) < current_popped:
            return None
        current_anchor = float(getattr(record, 'anchor', 0.0))
        anchor_gap = max(float(current_anchor) - float(witness.get('best_anchor', current_anchor)), 0.0)
        if anchor_gap > float(witness.get('anchor_radius', self.params46.anchor_eps)):
            return None
        if wid in trace_map:
            row = dict(trace_map[wid])
            row['hit_count'] = int(row.get('hit_count', 0)) + 1
            revisit_count = int(max(row.get('revisit_count', 1), 1))
            row['reuse_rate'] = float(row['hit_count']) / float(revisit_count)
            trace_map[wid] = row
            search_state['cx46d_trace_rows'] = trace_map
            self._last_trace_rows = trace_map
        return witness

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self._family_active():
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict):
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return witness_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if len(list(node_ctx.get('macros', []))) <= 0:
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return witness_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        self.stats['family_gate_hits'] = float(self.stats.get('family_gate_hits', 0.0) + 1.0)
        sig = self._sig(record, node_ctx)
        if self.disable_witness_transfer:
            search_state['cx46d_pending'] = {'sig': sig, 'record': record, 'node_ctx': node_ctx}
            self.stats['witness_full_reviews'] = float(self.stats.get('witness_full_reviews', 0.0) + 1.0)
            return witness_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        witness = self._probe_witness(sig, record, search_state)
        if self.force_negative_skip:
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            search_state['cx46d_pending'] = None
            return []
        if isinstance(witness, dict):
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            search_state['cx46d_pending'] = None
            return []
        search_state['cx46d_pending'] = {'sig': sig, 'record': record, 'node_ctx': node_ctx}
        self.stats['witness_full_reviews'] = float(self.stats.get('witness_full_reviews', 0.0) + 1.0)
        return witness_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        ranked = witness_mod.parent_mod.parent_mod.MSRPolicy.rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        pending = search_state.get('cx46d_pending')
        if not isinstance(pending, dict) or not isinstance(node_ctx, dict):
            return ranked
        items = ranked if isinstance(ranked, list) else []
        live_items = []
        for cand, decision in items:
            skip = bool(getattr(decision, 'skip', False)) if not isinstance(decision, dict) else bool(decision.get('skip', False))
            if not skip:
                live_items.append((cand, decision))
        if not live_items:
            search_state['cx46d_pending'] = None
            return ranked
        top_cand, top_dec = live_items[0]
        top_is_macro = str(getattr(top_cand, 'source', 'primitive')) == 'macro'
        top_score = float(getattr(top_dec, 'priority_secondary_delta', 0.0)) if not isinstance(top_dec, dict) else float(top_dec.get('priority_secondary_delta', 0.0))
        macro_scores = []
        for cand, dec in live_items:
            if str(getattr(cand, 'source', 'primitive')) != 'macro':
                continue
            macro_scores.append(float(getattr(dec, 'priority_secondary_delta', 0.0)) if not isinstance(dec, dict) else float(dec.get('priority_secondary_delta', 0.0)))
        if (not top_is_macro) and macro_scores:
            macro_best = float(min(macro_scores))
            margin = float(max(macro_best - top_score, 0.0))
            if margin >= float(self.params46.margin_thr):
                quality = self._quality_for_store(record, node_ctx, margin)
                strength = float(quality.get('strength', 0.0))
                self.stats['wqr_strength_sum'] = float(self.stats.get('wqr_strength_sum', 0.0) + strength)
                self.stats['wqr_strength_count'] = float(self.stats.get('wqr_strength_count', 0.0) + 1.0)
                if float(quality.get('reliable', 0.0)) >= max(float(quality.get('local', 0.0)), float(quality.get('fragile', 0.0))):
                    self.stats['wqr_reliable_store'] = float(self.stats.get('wqr_reliable_store', 0.0) + 1.0)
                elif float(quality.get('local', 0.0)) >= float(quality.get('fragile', 0.0)):
                    self.stats['wqr_local_store'] = float(self.stats.get('wqr_local_store', 0.0) + 1.0)
                else:
                    self.stats['wqr_fragile_store'] = float(self.stats.get('wqr_fragile_store', 0.0) + 1.0)
                if float(quality.get('store_strength', 0.0)) > 0.05:
                    self._register_store(pending['sig'], record, node_ctx, margin, quality, search_state)
                    self.stats['witness_store_negative'] = float(self.stats.get('witness_store_negative', 0.0) + 1.0)
        search_state['cx46d_pending'] = None
        return ranked


def _collect_quality_rows(calib_train_assets, predictor, cfg: CXGlobalConfig, parent_params, parent_memory, params: CX46DEWVParams, type_counter: dict[tuple[Any, ...], int], type_stats: dict[str, dict[str, float]], device: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in calib_train_assets:
        scenario = str(asset['case'].get('scenario', ''))
        if not _scenario_enabled(params, scenario):
            continue
        field = witness_mod.parent_mod.parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, parent_memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = QualityTracePolicy(
            asset['case'],
            bundle,
            field,
            parent_params,
            parent_memory,
            params,
            type_counter=type_counter,
            type_stats=type_stats,
            quality_bands=None,
            disable_witness_transfer=False,
            force_negative_skip=False,
            collect_quality_rows=True,
        )
        run_hybrid_with_policy(asset['case'], field, 20000, successor_policy=policy, record_expanded=False)
        rows.extend(policy.export_quality_rows())
    return rows


def _fit_quality_model(rows: list[dict[str, Any]], params: CX46DEWVParams) -> dict[str, Any]:
    active_rows = []
    hit_rows = []
    fragile_rows = []
    for row in rows:
        revisit_count = int(row.get('revisit_count', 0))
        hit_count = int(row.get('hit_count', 0))
        reuse_rate = float(hit_count) / float(max(revisit_count, 1)) if revisit_count > 0 else 0.0
        item = dict(row)
        item['reuse_rate'] = float(reuse_rate)
        if revisit_count > 0:
            active_rows.append(item)
        if hit_count > 0:
            hit_rows.append(item)
        elif revisit_count > 0:
            fragile_rows.append(item)
    reliable_rows: list[dict[str, Any]] = []
    local_rows: list[dict[str, Any]] = []
    if hit_rows:
        reuse_arr = np.asarray([float(row['reuse_rate']) for row in hit_rows], dtype=np.float32)
        gap_arr = np.asarray([float(row['max_popped_gap']) for row in hit_rows], dtype=np.float32)
        reliable_reuse_thr = float(np.quantile(reuse_arr, 0.6))
        reliable_gap_thr = float(np.quantile(gap_arr, 0.6))
        for row in hit_rows:
            if float(row['reuse_rate']) >= reliable_reuse_thr and float(row['max_popped_gap']) >= reliable_gap_thr:
                reliable_rows.append(row)
            else:
                local_rows.append(row)
    labeled_total = int(len(reliable_rows) + len(local_rows) + len(fragile_rows))
    if labeled_total <= 0:
        return {'bands': {key: None for key in QUALITY_CLASSES}, 'class_counts': {key: 0 for key in QUALITY_CLASSES}}
    min_band = int(max(params.min_band_count, 1))
    bands = {
        'reliable': _fit_quality_band(reliable_rows if len(reliable_rows) >= min_band else hit_rows, labeled_total),
        'local': _fit_quality_band(local_rows if len(local_rows) >= min_band else hit_rows, labeled_total),
        'fragile': _fit_quality_band(fragile_rows if len(fragile_rows) >= min_band else active_rows, labeled_total),
    }
    return {
        'bands': bands,
        'class_counts': {
            'reliable': int(len(reliable_rows)),
            'local': int(len(local_rows)),
            'fragile': int(len(fragile_rows)),
        },
        'num_rows': int(len(rows)),
        'num_active_rows': int(len(active_rows)),
        'num_hit_rows': int(len(hit_rows)),
    }


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX46DEWVParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = _load_parent_params()
    parent_memory = witness_mod.parent_mod.parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    type_counter, type_stats = _build_type_memory(calib_train_assets, predictor, cfg, parent_params, parent_memory, params, device)
    quality_rows = _collect_quality_rows(calib_train_assets, predictor, cfg, parent_params, parent_memory, params, type_counter, type_stats, device)
    quality_model = _fit_quality_model(quality_rows, params)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'params': params.__dict__,
        'type_signature_count': int(len(type_counter)),
        'quality_model': {
            'class_counts': dict(quality_model.get('class_counts', {})),
            'num_rows': int(quality_model.get('num_rows', 0)),
            'num_active_rows': int(quality_model.get('num_active_rows', 0)),
            'num_hit_rows': int(quality_model.get('num_hit_rows', 0)),
        },
    }
    (out_dir / 'cx46_d_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'parent_params': parent_params,
        'parent_memory': parent_memory,
        'type_counter': type_counter,
        'type_stats': type_stats,
        'quality_model': quality_model,
    }


def make_policy(memory: dict[str, Any], params: CX46DEWVParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = QualityTracePolicy(
        case,
        bundle,
        field,
        memory['parent_params'],
        memory['parent_memory'],
        params,
        type_counter=memory['type_counter'],
        type_stats=memory['type_stats'],
        quality_bands=dict(memory.get('quality_model', {}).get('bands', {})),
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
        collect_quality_rows=False,
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX46DEWVParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return witness_mod.parent_mod.parent_mod.build_nonholonomic_field(case, predictor, cfg, memory['parent_params'], memory['parent_memory'])


def build_standard_field(sample, predictor, params: CX46DEWVParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return witness_mod.parent_mod.parent_mod.build_standard_field(sample, predictor, memory['parent_params'], memory['parent_memory']).astype(np.float32)
