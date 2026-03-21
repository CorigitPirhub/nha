from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import class_key
from rs_cx27.common import coarse_state_key, scene_kind
from rs_cx44 import cx44_b_fcwt as parent_mod


@dataclass(frozen=True)
class CX46AFCWPParams:
    review_cell_stride: int
    review_yaw_bins: int
    margin_thr: float
    anchor_eps: float
    enable_parasol_misc: bool
    enable_deadend_labyrinth: bool
    enable_narrow_passage: bool
    misc_prior_floor: float
    deadend_prior_floor: float
    narrow_prior_floor: float
    misc_support_thr: float
    deadend_support_thr: float
    narrow_support_thr: float
    support_decay: float
    base_ttl: int
    ttl_bonus: int
    anchor_scale: float


def param_grid() -> list[CX46AFCWPParams]:
    common = dict(
        review_cell_stride=3,
        review_yaw_bins=12,
        margin_thr=0.03,
        anchor_eps=0.02,
        enable_parasol_misc=True,
        enable_deadend_labyrinth=True,
        enable_narrow_passage=True,
        support_decay=0.9,
        base_ttl=24,
        ttl_bonus=64,
        anchor_scale=1.0,
    )
    return [
        CX46AFCWPParams(**common, misc_prior_floor=0.80, deadend_prior_floor=0.55, narrow_prior_floor=0.45, misc_support_thr=0.80, deadend_support_thr=0.60, narrow_support_thr=0.55),
        CX46AFCWPParams(**common, misc_prior_floor=0.85, deadend_prior_floor=0.60, narrow_prior_floor=0.50, misc_support_thr=0.85, deadend_support_thr=0.65, narrow_support_thr=0.55),
        CX46AFCWPParams(**common, misc_prior_floor=0.90, deadend_prior_floor=0.65, narrow_prior_floor=0.50, misc_support_thr=0.90, deadend_support_thr=0.70, narrow_support_thr=0.60),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'Proxy-Only-Negative', 'force_negative_skip': True},
    ]


def _family_enabled(params: CX46AFCWPParams, scenario: str) -> bool:
    return bool(
        (params.enable_parasol_misc and str(scenario) == 'parasol_misc')
        or (params.enable_deadend_labyrinth and str(scenario) == 'deadend_labyrinth')
        or (params.enable_narrow_passage and str(scenario) == 'narrow_passage')
    )


def _load_parent_params() -> parent_mod.parent_mod.parent_mod.CX34AMSRParams:
    data = json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))
    return parent_mod.parent_mod.parent_mod.CX34AMSRParams(**data['params'])


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX46AFCWPParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = _load_parent_params()
    parent_memory = parent_mod.parent_mod.parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    sig_counter: Counter[tuple[Any, ...]] = Counter()
    family_counts: defaultdict[str, list[int]] = defaultdict(list)
    for asset in calib_train_assets:
        scenario = str(asset['case'].get('scenario', ''))
        if not _family_enabled(params, scenario):
            continue
        field = parent_mod.parent_mod.parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, parent_memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = parent_mod.parent_mod.parent_mod.make_policy(parent_memory, parent_params, asset['case'], bundle, field, device, ablation=None)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        from types import SimpleNamespace
        search_state: dict[str, Any] = {}
        for state in path[:-1]:
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=0.0)
            ctx = policy.prepare_expand(None, rec, None, None, None, None, search_state, None)
            if not isinstance(ctx, dict):
                continue
            sig = (
                str(scene_kind(asset['case'], bundle)),
                str(class_key(ctx)),
                tuple(
                    coarse_state_key(
                        rec,
                        asset['case'],
                        cell_stride=int(params.review_cell_stride),
                        yaw_bins=int(params.review_yaw_bins),
                    )
                ),
                int(bool(ctx.get('must_precede', False))),
                int(len(list(ctx.get('macros', []))) > 0),
            )
            sig_counter[sig] += 1
    for sig, count in sig_counter.items():
        family_counts[str(sig[0])].append(int(count))
    family_stats = {}
    for family, counts in family_counts.items():
        arr = np.asarray(counts, dtype=np.float32)
        family_stats[family] = {
            'q50': float(np.quantile(arr, 0.5)),
            'q80': float(np.quantile(arr, 0.8)),
            'q90': float(np.quantile(arr, 0.9)),
            'max': float(np.max(arr)),
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx46_a_meta.json').write_text(json.dumps({'params': params.__dict__, 'family_stats': family_stats, 'eligible_signature_count': int(len(sig_counter))}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'parent_params': parent_params, 'parent_memory': parent_memory, 'signature_counter': dict(sig_counter), 'family_stats': family_stats}


class FCWPPolicy(parent_mod.FCWTPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        parent_params,
        parent_memory: dict[str, Any],
        params: CX46AFCWPParams,
        signature_counter: dict[tuple[Any, ...], int],
        family_stats: dict[str, dict[str, float]],
        *,
        disable_witness_transfer: bool = False,
        force_negative_skip: bool = False,
    ) -> None:
        super().__init__(
            case,
            bundle,
            field,
            parent_params,
            parent_memory,
            parent_mod.CX44BFCWTParams(
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
        self.fcwp_params = params
        self.signature_counter = dict(signature_counter)
        self.family_stats = dict(family_stats)
        self.stats['fcwp_prior_sum'] = 0.0
        self.stats['fcwp_prior_count'] = 0.0
        self.stats['fcwp_skip_hits'] = 0.0

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx46_pending', None)
        search_state.setdefault('cx46_witness', {})
        if hasattr(super(), 'start_search'):
            return super().start_search(planner, start, goal, h_pair, search_state)

    def _sig(self, record, node_ctx: dict[str, Any]) -> tuple[Any, ...]:
        return (
            str(scene_kind(self.case, self.bundle)),
            str(class_key(node_ctx)),
            tuple(
                coarse_state_key(
                    record,
                    self.case,
                    cell_stride=int(self.fcwp_params.review_cell_stride),
                    yaw_bins=int(self.fcwp_params.review_yaw_bins),
                )
            ),
            int(bool(node_ctx.get('must_precede', False))),
            int(len(list(node_ctx.get('macros', []))) > 0),
        )

    def _family_prior_floor(self, family: str) -> float:
        if family == 'parasol_misc':
            return float(self.fcwp_params.misc_prior_floor)
        if family == 'deadend_labyrinth':
            return float(self.fcwp_params.deadend_prior_floor)
        if family == 'narrow_passage':
            return float(self.fcwp_params.narrow_prior_floor)
        return 1.0

    def _family_support_thr(self, family: str) -> float:
        if family == 'parasol_misc':
            return float(self.fcwp_params.misc_support_thr)
        if family == 'deadend_labyrinth':
            return float(self.fcwp_params.deadend_support_thr)
        if family == 'narrow_passage':
            return float(self.fcwp_params.narrow_support_thr)
        return 1.0

    def _prior(self, sig: tuple[Any, ...]) -> float:
        count = float(self.signature_counter.get(sig, 0))
        family = str(sig[0])
        stat = dict(self.family_stats.get(family, {}))
        q50 = float(stat.get('q50', 0.0))
        q90 = float(stat.get('q90', q50 + 1.0))
        if q90 <= q50 + 1e-6:
            return 0.0
        z = (count - q50) / max(q90 - q50, 1e-6)
        return float(np.clip(1.0 / (1.0 + np.exp(-3.0 * z)), 0.0, 1.0))

    def _lookup_witness(self, sig: tuple[Any, ...], record, search_state: dict[str, Any]) -> dict[str, Any] | None:
        witness = dict(search_state.get('cx46_witness', {})).get(sig)
        if not isinstance(witness, dict):
            return None
        current_popped = int(search_state.get('popped', 0))
        if int(witness.get('expiry', -1)) < current_popped:
            return None
        family = str(sig[0])
        support_thr = self._family_support_thr(family)
        support = float(witness.get('support', 0.0))
        current_anchor = float(getattr(record, 'anchor', 0.0))
        anchor_allow = float(current_anchor) + float(self.fcwp_params.anchor_eps) * (1.0 + float(self.fcwp_params.anchor_scale) * support) >= float(witness.get('best_anchor', current_anchor))
        if bool(support >= support_thr and anchor_allow):
            return witness
        return None

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self._family_active():
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return parent_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict):
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return parent_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        family = str(self.case.get('scenario', ''))
        self.stats['family_gate_hits'] = float(self.stats.get('family_gate_hits', 0.0) + 1.0)
        sig = self._sig(record, node_ctx)
        prior = self._prior(sig)
        self.stats['fcwp_prior_sum'] = float(self.stats.get('fcwp_prior_sum', 0.0) + prior)
        self.stats['fcwp_prior_count'] = float(self.stats.get('fcwp_prior_count', 0.0) + 1.0)
        if prior < self._family_prior_floor(family):
            return parent_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_witness_transfer:
            search_state['cx46_pending'] = (sig, prior)
            self.stats['witness_full_reviews'] = float(self.stats.get('witness_full_reviews', 0.0) + 1.0)
            return parent_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        witness = self._lookup_witness(sig, record, search_state)
        if self.force_negative_skip and len(list(node_ctx.get('macros', []))) > 0:
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            self.stats['fcwp_skip_hits'] = float(self.stats.get('fcwp_skip_hits', 0.0) + 1.0)
            search_state['cx46_pending'] = None
            return []
        if isinstance(witness, dict):
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            self.stats['fcwp_skip_hits'] = float(self.stats.get('fcwp_skip_hits', 0.0) + 1.0)
            search_state['cx46_pending'] = None
            return []
        search_state['cx46_pending'] = (sig, prior)
        self.stats['witness_full_reviews'] = float(self.stats.get('witness_full_reviews', 0.0) + 1.0)
        return parent_mod.parent_mod.parent_mod.MSRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        ranked = parent_mod.parent_mod.parent_mod.MSRPolicy.rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        pending = search_state.get('cx46_pending')
        if pending is None or not isinstance(node_ctx, dict):
            return ranked
        sig, prior = pending
        items = ranked if isinstance(ranked, list) else []
        live_items = []
        for cand, decision in items:
            skip = bool(getattr(decision, 'skip', False)) if not isinstance(decision, dict) else bool(decision.get('skip', False))
            if not skip:
                live_items.append((cand, decision))
        if not live_items:
            search_state['cx46_pending'] = None
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
            family = str(sig[0])
            support_thr = self._family_support_thr(family)
            evidence = float(prior * np.tanh(margin / max(float(self.fcwp_params.margin_thr), 1e-6)))
            witness_map = dict(search_state.get('cx46_witness', {}))
            current_anchor = float(getattr(record, 'anchor', 0.0))
            current_popped = int(search_state.get('popped', 0))
            prev = witness_map.get(sig, {})
            prev_support = float(prev.get('support', 0.0)) if isinstance(prev, dict) else 0.0
            support = float(prev_support * float(self.fcwp_params.support_decay) + evidence)
            if support >= 0.35 * support_thr:
                witness_map[sig] = {
                    'best_anchor': min(float(prev.get('best_anchor', current_anchor)) if isinstance(prev, dict) else current_anchor, current_anchor),
                    'support': float(support),
                    'expiry': int(max(int(prev.get('expiry', current_popped)) if isinstance(prev, dict) else current_popped, current_popped + int(self.fcwp_params.base_ttl + round(self.fcwp_params.ttl_bonus * min(support, 1.0))))),
                }
                search_state['cx46_witness'] = witness_map
                self.stats['witness_store_negative'] = float(self.stats.get('witness_store_negative', 0.0) + 1.0)
        search_state['cx46_pending'] = None
        return ranked


def make_policy(memory: dict[str, Any], params: CX46AFCWPParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = FCWPPolicy(
        case,
        bundle,
        field,
        memory['parent_params'],
        memory['parent_memory'],
        params,
        memory['signature_counter'],
        memory['family_stats'],
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX46AFCWPParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.parent_mod.parent_mod.build_nonholonomic_field(case, predictor, cfg, memory['parent_params'], memory['parent_memory'])


def build_standard_field(sample, predictor, params: CX46AFCWPParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.parent_mod.parent_mod.build_standard_field(sample, predictor, memory['parent_params'], memory['parent_memory']).astype(np.float32)
