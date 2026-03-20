from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx23.common import class_key
from rs_cx27.common import scene_kind, watchdog_evidence, coarse_state_key
from rs_cx36.common import build_local_proxy
from rs_cx40.common import event_scheduler_score, primitive_candidates_from_record
from rs_cx41 import cx41_b_fdr as parent_mod


@dataclass(frozen=True)
class FrontierDisagreementContract:
    positive_support: SupportBand | None
    negative_support: SupportBand | None
    score_floor: float
    positive_hits: int
    negative_hits: int


@dataclass(frozen=True)
class CX41CFDGParams:
    turn_bridge_max: float
    turn_focus_max: float
    rescue_bridge_max: float
    rescue_focus_min: float
    rescue_path_min: float
    rescue_budget: int
    suppress_bridge_min: float
    suppress_bridge_max: float
    suppress_focus_max: float
    suppress_path_min: float
    stubborn_bridge_min: float
    stubborn_focus_max: float
    stubborn_path_max: float
    macro_bridge_min: float
    macro_bridge_max: float
    macro_focus_min: float
    macro_focus_max: float
    macro_path_min: float
    macro_path_max: float
    maze_revisit_thr: int
    maze_stall_steps: int
    reverse_required_thr: float
    trap_thr: float
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int
    cell_stride: int
    yaw_bins: int
    min_hits: int
    max_bridge_depth: int
    max_bridge_frontier: int
    max_review_targets: int
    max_screened_paths: int
    review_cell_stride: int
    review_yaw_bins: int


def param_grid() -> list[CX41CFDGParams]:
    return [CX41CFDGParams(**params.__dict__) for params in parent_mod.param_grid()]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Disagreement-Gate', 'disable_disagreement_gate': True},
        {'name': 'No-Dominance-Gate', 'disable_dominance_gate': True},
    ]


def _dominance_key(case: dict[str, Any], params: CX41CFDGParams, record, node_ctx: dict[str, Any]) -> tuple[str, tuple[int, int, int]]:
    return (
        str(class_key(node_ctx)),
        tuple(
            coarse_state_key(
                record,
                case,
                cell_stride=int(max(params.review_cell_stride, 1)),
                yaw_bins=int(max(params.review_yaw_bins, 1)),
            )
        ),
    )


def _frontier_feature(case: dict[str, Any], bundle: dict[str, Any], params: CX41CFDGParams, primitive_cands, node_ctx: dict[str, Any], evidence: dict[str, Any]) -> np.ndarray:
    deltas = np.asarray([float(getattr(cand, 'anchor', 0.0) - getattr(cand, 'guided', 0.0)) for cand in primitive_cands], dtype=np.float32)
    if deltas.size <= 0:
        deltas = np.zeros(1, dtype=np.float32)
    sorted_delta = np.sort(deltas)[::-1]
    top1 = float(sorted_delta[0])
    top2 = float(sorted_delta[1]) if sorted_delta.size > 1 else 0.0
    gap = float(top1 - top2)
    coarse_keys = {
        coarse_state_key(
            SimpleNamespace(x=float(cand.next_state[0]), y=float(cand.next_state[1]), yaw=float(cand.next_state[2])),
            case,
            cell_stride=int(max(params.review_cell_stride, 1)),
            yaw_bins=int(max(params.review_yaw_bins, 1)),
        )
        for cand in primitive_cands
    }
    dirs = [int(getattr(cand, 'direction', 1)) for cand in primitive_cands]
    reverse_frac = float(np.mean([1.0 if d < 0 else 0.0 for d in dirs])) if dirs else 0.0
    kind = str(scene_kind(case, bundle))
    return np.asarray(
        [
            float(1.0 if kind == 'default' else 0.0),
            float(1.0 if kind == 'maze' else 0.0),
            float(1.0 if kind == 'misc' else 0.0),
            float(event_scheduler_score(node_ctx, evidence)),
            float(evidence.get('stall_steps', 0)),
            float(evidence.get('class_churn', 0.0)),
            float(evidence.get('loop_rate', 0.0)),
            float(evidence.get('recent_failures', 0)),
            float(1.0 if bool(evidence.get('blocklist_hit', False)) else 0.0),
            float(len(primitive_cands)),
            float(len(coarse_keys)),
            float(top1),
            float(top2),
            float(gap),
            float(np.std(deltas)) if deltas.size > 1 else 0.0,
            float(reverse_frac),
        ],
        dtype=np.float32,
    )


def compile_frontier_disagreement_contract(calib_train_assets: list[dict[str, Any]], *, memory: dict[str, Any], params_obj: CX41CFDGParams) -> FrontierDisagreementContract:
    parent_params = parent_mod.CX41BFDRParams(**params_obj.__dict__)
    pos_feats: list[np.ndarray] = []
    pos_scores: list[float] = []
    neg_feats: list[np.ndarray] = []
    neg_scores: list[float] = []

    for asset in calib_train_assets:
        case = asset['case']
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = parent_mod.make_policy(memory, parent_params, case, bundle, field, 'cpu', ablation=None)
        planner, h_pair = build_local_proxy(case, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        search_state: dict[str, Any] = {}
        if hasattr(policy, 'start_search'):
            policy.start_search(planner, tuple(map(float, case['start'])), tuple(map(float, case['goal'])), h_pair, search_state)
        for state in path[:-1]:
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=float(h_pair(float(state[0]), float(state[1]), float(state[2]))[0]), steer=0.0)
            node_ctx = policy.prepare_expand(planner, rec, tuple(map(float, case['goal'])), None, None, None, search_state, h_pair)
            if not isinstance(node_ctx, dict):
                continue
            key = _dominance_key(case, params_obj, rec, node_ctx)
            current_anchor = float(rec.anchor)
            best_map = search_state.setdefault('cx41_review_best_fdg_compile', {})
            prev = best_map.get(key)
            dominant = bool(prev is None or current_anchor < float(prev) - float(params_obj.progress_eps))
            if not dominant:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, node_ctx, 0, 0, 0, search_state, h_pair)
                continue
            best_map[key] = float(current_anchor)
            primitive_cands = [cand for cand in primitive_candidates_from_record(case, planner, rec, h_pair) if str(getattr(cand, 'source', 'primitive')) == 'primitive']
            if not primitive_cands:
                if hasattr(policy, 'complete_expand'):
                    policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, node_ctx, 0, 0, 0, search_state, h_pair)
                continue
            evidence = watchdog_evidence(search_state, rec, case, bundle, node_ctx, policy.watchdog_cfg)
            feat = _frontier_feature(case, bundle, params_obj, primitive_cands, node_ctx, evidence)
            extra = policy.extra_successors(planner, rec, tuple(map(float, case['goal'])), None, primitive_cands, node_ctx, search_state, h_pair) or []
            score = float(event_scheduler_score(node_ctx, evidence))
            if any(str(getattr(cand, 'source', 'primitive')) == 'bridge_review' for cand in extra):
                pos_feats.append(feat)
                pos_scores.append(score)
            else:
                neg_feats.append(feat)
                neg_scores.append(score)
            if hasattr(policy, 'complete_expand'):
                policy.complete_expand(planner, rec, tuple(map(float, case['goal'])), None, node_ctx, 0, 0, 0, search_state, h_pair)

    pos_band = fit_support_band(pos_feats, pos_scores, low_q=0.05, high_q=0.95, sim_q=0.15) if pos_feats else None
    neg_band = fit_support_band(neg_feats, neg_scores, low_q=0.05, high_q=0.95, sim_q=0.15) if neg_feats else None
    score_floor = float(np.quantile(np.asarray(pos_scores, dtype=np.float32), 0.05)) if pos_scores else 0.0
    return FrontierDisagreementContract(
        positive_support=pos_band,
        negative_support=neg_band,
        score_floor=float(score_floor),
        positive_hits=int(len(pos_feats)),
        negative_hits=int(len(neg_feats)),
    )


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX41CFDGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = parent_mod.CX41BFDRParams(**params.__dict__)
    memory = parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    contract = compile_frontier_disagreement_contract(calib_train_assets, memory=memory, params_obj=params)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx41_c_meta.json').write_text(
        json.dumps(
            {
                'params': params.__dict__,
                'contract': {
                    'positive_hits': int(contract.positive_hits),
                    'negative_hits': int(contract.negative_hits),
                    'score_floor': float(contract.score_floor),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    memory = dict(memory)
    memory['frontier_disagreement_contract'] = contract
    return memory


class FDGPolicy(parent_mod.FDRPolicy):
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX41CFDGParams, memory: dict[str, Any], *, disable_disagreement_gate: bool = False, disable_dominance_gate: bool = False) -> None:
        parent_params = parent_mod.CX41BFDRParams(**params.__dict__)
        super().__init__(case, bundle, field, parent_params, memory, disable_dominance_gate=disable_dominance_gate, disable_depth2_escalation=False)
        self.params = params
        self.disable_disagreement_gate = bool(disable_disagreement_gate)
        self.contract: FrontierDisagreementContract = memory['frontier_disagreement_contract']
        self.stats['fdg_runs'] = 0.0
        self.stats['fdg_skips'] = 0.0

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not self.disable_dominance_gate:
            key = _dominance_key(self.case, self.params, record, node_ctx)
            current_anchor = float(getattr(record, 'anchor', h_pair(float(record.x), float(record.y), float(record.yaw))[0]))
            best_map = search_state.setdefault('cx41_review_best', {})
            prev = best_map.get(key)
            if prev is not None and float(current_anchor) >= float(prev) - float(self.params.progress_eps):
                self.stats['dominance_skips'] = float(self.stats.get('dominance_skips', 0.0) + 1.0)
                return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
            best_map[key] = float(current_anchor)
            self.stats['dominance_runs'] = float(self.stats.get('dominance_runs', 0.0) + 1.0)
        if self.disable_disagreement_gate:
            return parent_mod.FDRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        primitive_cands = [cand for cand in candidates if str(getattr(cand, 'source', 'primitive')) == 'primitive']
        if not primitive_cands:
            return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        evidence = watchdog_evidence(search_state, record, self.case, self.bundle, node_ctx, self.watchdog_cfg)
        feat = _frontier_feature(self.case, self.bundle, self.params, primitive_cands, node_ctx, evidence)
        score = float(event_scheduler_score(node_ctx, evidence))
        pos_match, pos_sim = support_match(self.contract.positive_support, feat, score, slack=0.0)
        neg_match, neg_sim = support_match(self.contract.negative_support, feat, score, slack=0.0)
        allow = bool((pos_match or float(score) >= float(self.contract.score_floor)) and not neg_match)
        if not allow:
            self.stats['fdg_skips'] = float(self.stats.get('fdg_skips', 0.0) + 1.0)
            return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        self.stats['fdg_runs'] = float(self.stats.get('fdg_runs', 0.0) + 1.0)
        return parent_mod.FDRPolicy.extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX41CFDGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return FDGPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_disagreement_gate=bool(ablation.get('disable_disagreement_gate', False)),
        disable_dominance_gate=bool(ablation.get('disable_dominance_gate', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX41CFDGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX41BFDRParams(**params.__dict__)
    return parent_mod.build_nonholonomic_field(case, predictor, cfg, parent_params, memory)


def build_standard_field(sample, predictor, params: CX41CFDGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    parent_params = parent_mod.CX41BFDRParams(**params.__dict__)
    return parent_mod.build_standard_field(sample, predictor, parent_params, memory).astype(np.float32)

