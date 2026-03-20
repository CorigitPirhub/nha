from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import class_key
from rs_cx27.common import coarse_state_key, scene_kind
from rs_cx34 import cx34_a_msr as parent_mod


@dataclass(frozen=True)
class CX44ARMRCParams:
    review_cell_stride: int
    review_yaw_bins: int
    margin_thr: float
    anchor_eps: float


def param_grid() -> list[CX44ARMRCParams]:
    return [
        CX44ARMRCParams(review_cell_stride=3, review_yaw_bins=12, margin_thr=0.04, anchor_eps=0.02),
        CX44ARMRCParams(review_cell_stride=4, review_yaw_bins=12, margin_thr=0.05, anchor_eps=0.02),
        CX44ARMRCParams(review_cell_stride=4, review_yaw_bins=8, margin_thr=0.06, anchor_eps=0.03),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'Proxy-Only-Negative', 'force_negative_skip': True},
    ]


def _load_parent_params() -> parent_mod.CX34AMSRParams:
    data = json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))
    return parent_mod.CX34AMSRParams(**data['params'])


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX44ARMRCParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = _load_parent_params()
    parent_memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx44_a_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'parent_params': parent_params, 'parent_memory': parent_memory}


class RMRCPPolicy(parent_mod.MSRPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        parent_params: parent_mod.CX34AMSRParams,
        parent_memory: dict[str, Any],
        params: CX44ARMRCParams,
        *,
        disable_witness_transfer: bool = False,
        force_negative_skip: bool = False,
    ) -> None:
        super().__init__(case, bundle, field, parent_params, parent_memory, disable_macro_rescue=False)
        self.release_params = params
        self.disable_witness_transfer = bool(disable_witness_transfer)
        self.force_negative_skip = bool(force_negative_skip)
        self.enable_diagnostics = False
        if not isinstance(getattr(self, 'stats', None), dict):
            self.stats = {}
        self.stats['witness_hits'] = 0.0
        self.stats['witness_full_reviews'] = 0.0
        self.stats['witness_store_negative'] = 0.0
        self._diag_rows: list[dict[str, Any]] = []

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state.setdefault('cx44_neg_witness', {})
        search_state.setdefault('cx44_pending_sig', None)
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
                    cell_stride=int(max(self.release_params.review_cell_stride, 1)),
                    yaw_bins=int(max(self.release_params.review_yaw_bins, 1)),
                )
            ),
            int(bool(node_ctx.get('must_precede', False))),
            int(len(list(node_ctx.get('macros', []))) > 0),
        )

    def _lookup_neg_witness(self, record, node_ctx: dict[str, Any], search_state: dict[str, Any]) -> dict[str, Any] | None:
        sig = self._sig(record, node_ctx)
        witness = dict(search_state.get('cx44_neg_witness', {})).get(sig)
        if not isinstance(witness, dict):
            return None
        current_anchor = float(getattr(record, 'anchor', 0.0))
        if float(current_anchor) + float(self.release_params.anchor_eps) < float(witness.get('best_anchor', current_anchor)):
            return None
        return witness

    def _record_diag(self, record, node_ctx: dict[str, Any], action: str, **extra: Any) -> None:
        if not bool(self.enable_diagnostics):
            return
        self._diag_rows.append(
            {
                'sample_name': str(self.case.get('_cx44_sample_name', self.case.get('map_id', 'unknown'))),
                'scenario': str(self.case.get('scenario', 'unknown')),
                'x': float(getattr(record, 'x', 0.0)),
                'y': float(getattr(record, 'y', 0.0)),
                'yaw': float(getattr(record, 'yaw', 0.0)),
                'anchor': float(getattr(record, 'anchor', 0.0)),
                'class_key': str(class_key(node_ctx)) if isinstance(node_ctx, dict) else 'unknown',
                'action': str(action),
                **{str(k): v for k, v in extra.items()},
            }
        )

    def export_diagnostics(self) -> list[dict[str, Any]]:
        return list(self._diag_rows)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if self.disable_witness_transfer:
            search_state['cx44_pending_sig'] = self._sig(record, node_ctx)
            self.stats['witness_full_reviews'] = float(self.stats.get('witness_full_reviews', 0.0) + 1.0)
            self._record_diag(record, node_ctx, 'full_review_disabled')
            return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        witness = self._lookup_neg_witness(record, node_ctx, search_state)
        if self.force_negative_skip and len(list(node_ctx.get('macros', []))) > 0:
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            search_state['cx44_pending_sig'] = None
            self._record_diag(record, node_ctx, 'force_negative_skip')
            return []
        if isinstance(witness, dict):
            self.stats['witness_hits'] = float(self.stats.get('witness_hits', 0.0) + 1.0)
            search_state['cx44_pending_sig'] = None
            self._record_diag(record, node_ctx, 'witness_skip', witness_margin=float(witness.get('margin', 0.0)))
            return []
        search_state['cx44_pending_sig'] = self._sig(record, node_ctx)
        self.stats['witness_full_reviews'] = float(self.stats.get('witness_full_reviews', 0.0) + 1.0)
        self._record_diag(record, node_ctx, 'full_review')
        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        ranked = super().rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict):
            return ranked
        sig = search_state.get('cx44_pending_sig')
        if sig is None:
            return ranked
        items = ranked if isinstance(ranked, list) else []
        live_items = []
        for cand, decision in items:
            skip = bool(getattr(decision, 'skip', False)) if not isinstance(decision, dict) else bool(decision.get('skip', False))
            if not skip:
                live_items.append((cand, decision))
        if not live_items:
            search_state['cx44_pending_sig'] = None
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
            margin = float(macro_best - top_score)
            if margin >= float(self.release_params.margin_thr):
                witness_map = dict(search_state.get('cx44_neg_witness', {}))
                current_anchor = float(getattr(record, 'anchor', 0.0))
                witness_map[sig] = {'best_anchor': float(current_anchor), 'margin': float(margin)}
                search_state['cx44_neg_witness'] = witness_map
                self.stats['witness_store_negative'] = float(self.stats.get('witness_store_negative', 0.0) + 1.0)
                self._record_diag(record, node_ctx, 'store_negative', margin=float(margin))
        search_state['cx44_pending_sig'] = None
        return ranked


def make_policy(memory: dict[str, Any], params: CX44ARMRCParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = RMRCPPolicy(
        case,
        bundle,
        field,
        memory['parent_params'],
        memory['parent_memory'],
        params,
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX44ARMRCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, memory['parent_params'], memory['parent_memory'])


def build_standard_field(sample, predictor, params: CX44ARMRCParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.build_standard_field(sample, predictor, memory['parent_params'], memory['parent_memory']).astype(np.float32)
