from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from planner.hybrid_astar import SuccessorCandidate, SuccessorDecision
from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx21.common import family_bucket_name, macro_family


RANK_RELEASE_FEATURE_NAMES = (
    'scene_hard',
    'scene_misc',
    'scene_bridge',
    'scene_focus',
    'scene_open',
    'scene_barrier',
    'cur_cost',
    'cur_viability',
    'cur_reverse',
    'cur_trap_escape',
    'num_candidates',
    'num_macros',
    'num_allowed',
    'num_forbidden',
    'top_margin',
    'top_is_macro',
    'top_is_reverse',
    'top_label_allowed',
    'top_label_forbidden',
    'singleton',
)


@dataclass(frozen=True)
class RankReleaseContract:
    positive_support: SupportBand | None
    negative_support: SupportBand | None
    margin_floor: float
    positive_hits: int
    negative_hits: int


def _decision_to_dict(decision: SuccessorDecision | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(decision, SuccessorDecision):
        return {
            'skip': bool(decision.skip),
            'extra_edge_cost': float(decision.extra_edge_cost),
            'priority_primary_delta': float(decision.priority_primary_delta),
            'priority_secondary_delta': float(decision.priority_secondary_delta),
        }
    if isinstance(decision, dict):
        return {
            'skip': bool(decision.get('skip', False)),
            'extra_edge_cost': float(decision.get('extra_edge_cost', 0.0)),
            'priority_primary_delta': float(decision.get('priority_primary_delta', 0.0)),
            'priority_secondary_delta': float(decision.get('priority_secondary_delta', 0.0)),
        }
    return {
        'skip': False,
        'extra_edge_cost': 0.0,
        'priority_primary_delta': 0.0,
        'priority_secondary_delta': 0.0,
    }


def candidate_signature(cand: SuccessorCandidate) -> tuple[Any, ...]:
    sim = dict(getattr(cand, 'sim_info', {}) or {})
    return (
        str(getattr(cand, 'source', 'primitive')),
        str(getattr(cand, 'family', '')),
        int(getattr(cand, 'primitive_index', -1)),
        int(getattr(cand, 'direction', 1)),
        tuple(int(v) for v in sim.get('bridge_primitives', ())),
        tuple(round(float(v), 3) for v in tuple(getattr(cand, 'next_state', ()) or ())[:3]),
    )


def _topk_live_signatures(items: list[tuple[SuccessorCandidate, Any]], k: int = 2) -> tuple[tuple[Any, ...], ...]:
    out: list[tuple[Any, ...]] = []
    for cand, decision in items:
        dec = _decision_to_dict(decision)
        if bool(dec.get('skip', False)):
            continue
        out.append(candidate_signature(cand))
        if len(out) >= int(max(k, 1)):
            break
    return tuple(out)


def _bucket_label(node_ctx: dict[str, Any], cand: SuccessorCandidate) -> tuple[str, str, float]:
    rules = dict(node_ctx.get('rules', {}))
    conf = dict(node_ctx.get('conf', {}))
    fam_bucket = family_bucket_name(macro_family(cand))
    return str(fam_bucket), str(rules.get(fam_bucket, 'discouraged')), float(conf.get(fam_bucket, 0.0))


def _skip_forbidden_macro(node_ctx: dict[str, Any], candidates: list[SuccessorCandidate], cand: SuccessorCandidate, *, label: str) -> bool:
    if str(label) != 'forbidden':
        return False
    if str(getattr(cand, 'source', 'primitive')) != 'macro':
        return False
    labels = [str(_bucket_label(node_ctx, item)[1]) for item in candidates]
    num_non_forbidden = int(sum(lbl != 'forbidden' for lbl in labels))
    return bool(num_non_forbidden >= 2)


def cheap_rank_candidates(
    record,
    node_ctx: dict[str, Any],
    candidates: list[SuccessorCandidate],
    *,
    anchor_weight: float,
    guided_weight: float,
    allowed_bonus: float,
    discouraged_penalty: float,
    forbidden_penalty: float,
    macro_bonus: float,
    must_precede_bonus: float,
) -> tuple[list[tuple[SuccessorCandidate, dict[str, Any]]], dict[str, Any]]:
    foundation = node_ctx.get('foundation')
    current_cost = float(getattr(foundation, 'cost_to_go', getattr(record, 'anchor', 0.0)))
    current_anchor = float(getattr(record, 'anchor', current_cost))
    must_precede = bool(node_ctx.get('must_precede', False))
    ranked: list[tuple[SuccessorCandidate, dict[str, Any]]] = []
    live_scores: list[float] = []
    live_meta: list[tuple[str, bool, bool]] = []
    num_macros = 0
    num_allowed = 0
    num_forbidden = 0
    for cand in candidates:
        fam_bucket, label, conf = _bucket_label(node_ctx, cand)
        if str(getattr(cand, 'source', 'primitive')) == 'macro':
            num_macros += 1
        if label == 'allowed':
            num_allowed += 1
        if label == 'forbidden':
            num_forbidden += 1
        anchor_delta = float(getattr(cand, 'anchor', current_anchor)) - float(current_anchor)
        guided_delta = float(getattr(cand, 'guided', current_anchor)) - float(current_anchor)
        delta = float(anchor_weight) * float(anchor_delta) + float(guided_weight) * float(guided_delta)
        if str(getattr(cand, 'source', 'primitive')) == 'macro':
            delta -= float(macro_bonus)
        if label == 'allowed':
            delta -= float(allowed_bonus) * (0.5 + 0.5 * float(conf))
        elif label == 'discouraged':
            delta += float(discouraged_penalty) * (1.0 - float(conf))
        elif label == 'forbidden':
            delta += float(forbidden_penalty) * (1.0 + float(conf))
        if must_precede:
            if fam_bucket in {'reverse', 'reverse_setup'} and int(getattr(cand, 'direction', 1)) < 0:
                delta -= float(must_precede_bonus)
            elif fam_bucket in {'straight', 'forward_turn'} and int(getattr(cand, 'direction', 1)) > 0:
                delta += float(must_precede_bonus)
        skip = _skip_forbidden_macro(node_ctx, candidates, cand, label=label)
        decision = {
            'skip': bool(skip),
            'priority_primary_delta': 0.5 * float(delta),
            'priority_secondary_delta': float(delta),
        }
        ranked.append((cand, decision))
        if not skip:
            live_scores.append(float(delta))
            live_meta.append((
                str(label),
                bool(str(getattr(cand, 'source', 'primitive')) == 'macro'),
                bool(fam_bucket in {'reverse', 'reverse_setup'}),
            ))
    ranked.sort(key=lambda item: float(_decision_to_dict(item[1])['priority_secondary_delta']))
    live_sorted = [item for item in ranked if not bool(_decision_to_dict(item[1])['skip'])]
    margin = 1.0
    top_label = 'discouraged'
    top_is_macro = False
    top_is_reverse = False
    if live_sorted:
        top_cand, top_dec = live_sorted[0]
        top_bucket, top_label, _ = _bucket_label(node_ctx, top_cand)
        top_is_macro = bool(str(getattr(top_cand, 'source', 'primitive')) == 'macro')
        top_is_reverse = bool(top_bucket in {'reverse', 'reverse_setup'})
        best = float(_decision_to_dict(top_dec)['priority_secondary_delta'])
        if len(live_sorted) >= 2:
            second = float(_decision_to_dict(live_sorted[1][1])['priority_secondary_delta'])
            margin = float(second - best)
    meta = {
        'num_candidates': int(len(candidates)),
        'num_macros': int(num_macros),
        'num_allowed': int(num_allowed),
        'num_forbidden': int(num_forbidden),
        'top_margin': float(margin),
        'top_label': str(top_label),
        'top_is_macro': bool(top_is_macro),
        'top_is_reverse': bool(top_is_reverse),
        'singleton': bool(len([1 for _, dec in ranked if not bool(_decision_to_dict(dec)['skip'])]) <= 1),
        'topk': _topk_live_signatures(ranked, k=2),
    }
    return ranked, meta


def rank_release_feature(bundle: dict[str, Any], node_ctx: dict[str, Any], proxy_meta: dict[str, Any]) -> np.ndarray:
    scene = dict(bundle.get('scene', {}))
    foundation = node_ctx.get('foundation')
    return np.asarray(
        [
            float(scene.get('hard_likelihood', 0.0)),
            float(scene.get('misc_likelihood', 0.0)),
            float(scene.get('bridge_diffuse', 0.0)),
            float(scene.get('focus_gap', 0.0)),
            float(scene.get('path_openness', 0.0)),
            float(scene.get('barrier_peak', 0.0)),
            float(getattr(foundation, 'cost_to_go', 0.0)),
            float(getattr(foundation, 'viability', 0.0)),
            float(getattr(foundation, 'reverse_required', 0.0)),
            float(getattr(foundation, 'trap_escape_affinity', 0.0)),
            float(proxy_meta.get('num_candidates', 0)),
            float(proxy_meta.get('num_macros', 0)),
            float(proxy_meta.get('num_allowed', 0)),
            float(proxy_meta.get('num_forbidden', 0)),
            float(proxy_meta.get('top_margin', 0.0)),
            float(1.0 if bool(proxy_meta.get('top_is_macro', False)) else 0.0),
            float(1.0 if bool(proxy_meta.get('top_is_reverse', False)) else 0.0),
            float(1.0 if str(proxy_meta.get('top_label', 'discouraged')) == 'allowed' else 0.0),
            float(1.0 if str(proxy_meta.get('top_label', 'discouraged')) == 'forbidden' else 0.0),
            float(1.0 if bool(proxy_meta.get('singleton', False)) else 0.0),
        ],
        dtype=np.float32,
    )


def compile_rank_release_contract(rows: list[dict[str, Any]], *, min_hits: int) -> RankReleaseContract:
    positive_feats: list[np.ndarray] = []
    positive_margin: list[float] = []
    negative_feats: list[np.ndarray] = []
    negative_margin: list[float] = []
    for row in rows:
        feat = np.asarray(row['feature'], dtype=np.float32)
        margin = float(row['margin'])
        if bool(row['match']) and margin > 0.0:
            positive_feats.append(feat)
            positive_margin.append(float(margin))
        elif not bool(row['match']):
            negative_feats.append(feat)
            negative_margin.append(float(max(margin, 0.0)))
    positive_support = fit_support_band(positive_feats, positive_margin, low_q=0.05, high_q=0.95, sim_q=0.15) if len(positive_feats) >= int(max(min_hits, 1)) else None
    negative_support = fit_support_band(negative_feats, negative_margin, low_q=0.05, high_q=0.95, sim_q=0.15) if len(negative_feats) >= int(max(min_hits, 1)) else None
    margin_floor = float(np.quantile(np.asarray(positive_margin, dtype=np.float32), 0.20)) if positive_margin else 0.0
    return RankReleaseContract(
        positive_support=positive_support,
        negative_support=negative_support,
        margin_floor=float(margin_floor),
        positive_hits=int(len(positive_feats)),
        negative_hits=int(len(negative_feats)),
    )


def release_decision(contract: RankReleaseContract, feat: np.ndarray, *, margin: float, slack: float) -> tuple[bool, float, float]:
    if bool(contract.positive_hits <= 0):
        return False, 0.0, 0.0
    pos_match, pos_sim = support_match(contract.positive_support, np.asarray(feat, dtype=np.float32), float(margin), slack=float(slack))
    neg_match, neg_sim = support_match(contract.negative_support, np.asarray(feat, dtype=np.float32), float(max(margin, 0.0)), slack=float(slack))
    return bool(pos_match and not neg_match), float(pos_sim), float(neg_sim)


def rank_match(full_ranked: list[tuple[SuccessorCandidate, Any]] | None, proxy_ranked: list[tuple[SuccessorCandidate, Any]]) -> bool:
    full_items = full_ranked if isinstance(full_ranked, list) else []
    return bool(_topk_live_signatures(full_items, k=2) == _topk_live_signatures(proxy_ranked, k=2))


__all__ = [
    'RANK_RELEASE_FEATURE_NAMES',
    'RankReleaseContract',
    'candidate_signature',
    'cheap_rank_candidates',
    'compile_rank_release_contract',
    'rank_match',
    'rank_release_feature',
    'release_decision',
]
