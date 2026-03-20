from __future__ import annotations

from typing import Any

import numpy as np

from rs_cx16.common import macro_family
from rs_cx37.common import replay_priority_prior


def candidate_immediate_progress(current_anchor: float, cand) -> float:
    return float(current_anchor - float(getattr(cand, 'guided', 0.0)))


def bounded_local_review_score(case: dict[str, Any], h_pair, current_anchor: float, cand) -> float:
    from rs_cx36.common import best_primitive_score

    immediate = candidate_immediate_progress(float(current_anchor), cand)
    next_progress = best_primitive_score(case, tuple(map(float, cand.next_state)), h_pair)
    source_bonus = 0.04 if str(getattr(cand, 'source', 'primitive')) == 'macro' else 0.0
    reverse_bonus = 0.02 if int(getattr(cand, 'direction', 1)) < 0 else 0.0
    return float(immediate + 0.55 * next_progress + source_bonus + reverse_bonus)


def review_priority_delta(review_score: float, prior_score: float) -> float:
    return float(-(0.55 * float(review_score) + 0.45 * float(prior_score)))


__all__ = [
    'bounded_local_review_score',
    'candidate_immediate_progress',
    'replay_priority_prior',
    'review_priority_delta',
]
