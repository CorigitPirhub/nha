from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from rs_cx23.common import class_key


FeatureFn = Callable[[Any, Any, dict[str, Any], dict[str, Any]], dict[str, Any]]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _stats_snapshot(policy: Any) -> dict[str, float]:
    stats = getattr(policy, 'stats', {})
    if not isinstance(stats, dict):
        return {}
    return {str(k): _safe_float(v) for k, v in stats.items() if isinstance(v, (int, float))}


def _base_event_key(case: dict[str, Any], node_ctx: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(case.get('scenario', '')),
        str(class_key(node_ctx)),
        int(bool(node_ctx.get('must_precede', False))),
        int(len(list(node_ctx.get('macros', []))) > 0),
    )


@dataclass
class EventLogRecord:
    event_id: int
    sample_name: str
    scenario: str
    popped: int
    x: float
    y: float
    yaw: float
    anchor: float
    class_key: str
    must_precede: int
    macro_count: int
    candidate_count: int
    event_key: tuple[Any, ...]
    full_review: int
    witness_hit: int
    store_negative: int
    family_gate_hits_delta: float
    witness_hits_delta: float
    witness_full_reviews_delta: float
    witness_store_negative_delta: float
    extra: dict[str, Any]

    def to_row(self) -> dict[str, Any]:
        return {
            'event_id': int(self.event_id),
            'sample_name': str(self.sample_name),
            'scenario': str(self.scenario),
            'popped': int(self.popped),
            'x': float(self.x),
            'y': float(self.y),
            'yaw': float(self.yaw),
            'anchor': float(self.anchor),
            'class_key': str(self.class_key),
            'must_precede': int(self.must_precede),
            'macro_count': int(self.macro_count),
            'candidate_count': int(self.candidate_count),
            'event_key': json.dumps(list(self.event_key), ensure_ascii=False),
            'full_review': int(self.full_review),
            'witness_hit': int(self.witness_hit),
            'store_negative': int(self.store_negative),
            'family_gate_hits_delta': float(self.family_gate_hits_delta),
            'witness_hits_delta': float(self.witness_hits_delta),
            'witness_full_reviews_delta': float(self.witness_full_reviews_delta),
            'witness_store_negative_delta': float(self.witness_store_negative_delta),
            **{str(k): v for k, v in self.extra.items()},
        }


class EventLogBuffer:
    def __init__(self, policy_name: str, feature_fn: FeatureFn | None = None) -> None:
        self.policy_name = str(policy_name)
        self.feature_fn = feature_fn
        self._rows: list[dict[str, Any]] = []
        self._next_event_id = 0

    def reset(self) -> None:
        self._rows = []
        self._next_event_id = 0

    def export_rows(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as f:
            for row in self._rows:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')

    def _make_record(self, policy: Any, record: Any, node_ctx: dict[str, Any], search_state: dict[str, Any], candidate_count: int, before: dict[str, float], after: dict[str, float], store_negative: int) -> dict[str, Any]:
        self._next_event_id += 1
        extra = self.feature_fn(policy, record, node_ctx, search_state) if self.feature_fn is not None else {}
        row = EventLogRecord(
            event_id=int(self._next_event_id),
            sample_name=str(policy.case.get('_cx44_sample_name', policy.case.get('map_id', 'unknown'))),
            scenario=str(policy.case.get('scenario', '')),
            popped=int(search_state.get('popped', 0)),
            x=_safe_float(getattr(record, 'x', 0.0)),
            y=_safe_float(getattr(record, 'y', 0.0)),
            yaw=_safe_float(getattr(record, 'yaw', 0.0)),
            anchor=_safe_float(getattr(record, 'anchor', 0.0)),
            class_key=str(class_key(node_ctx)),
            must_precede=int(bool(node_ctx.get('must_precede', False))),
            macro_count=int(len(list(node_ctx.get('macros', [])))),
            candidate_count=int(candidate_count),
            event_key=_base_event_key(policy.case, node_ctx),
            full_review=int(after.get('witness_full_reviews', 0.0) > before.get('witness_full_reviews', 0.0) + 1e-6),
            witness_hit=int(after.get('witness_hits', 0.0) > before.get('witness_hits', 0.0) + 1e-6),
            store_negative=int(store_negative),
            family_gate_hits_delta=float(after.get('family_gate_hits', 0.0) - before.get('family_gate_hits', 0.0)),
            witness_hits_delta=float(after.get('witness_hits', 0.0) - before.get('witness_hits', 0.0)),
            witness_full_reviews_delta=float(after.get('witness_full_reviews', 0.0) - before.get('witness_full_reviews', 0.0)),
            witness_store_negative_delta=float(after.get('witness_store_negative', 0.0) - before.get('witness_store_negative', 0.0)),
            extra=dict(extra) if isinstance(extra, dict) else {},
        ).to_row()
        return row

    def start_search(self, search_state: dict[str, Any]) -> None:
        search_state.setdefault('_cx47log_pending', None)
        search_state.setdefault('_cx47log_seen', {})
        search_state.setdefault('_cx47log_event_seen', 0)

    def before_extra(self, policy: Any, record: Any, node_ctx: Any, candidates: list[Any], search_state: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(node_ctx, dict):
            return None
        if len(list(node_ctx.get('macros', []))) <= 0:
            return None
        event_key = _base_event_key(policy.case, node_ctx)
        seen_map = dict(search_state.get('_cx47log_seen', {}))
        seen_before = int(seen_map.get(event_key, 0))
        seen_map[event_key] = seen_before + 1
        search_state['_cx47log_seen'] = seen_map
        search_state['_cx47log_event_seen'] = seen_before
        return {
            'before': _stats_snapshot(policy),
            'record': record,
            'node_ctx': node_ctx,
            'candidate_count': int(len(candidates)),
            'event_seen': int(seen_before),
        }

    def after_extra(self, policy: Any, probe: dict[str, Any] | None, search_state: dict[str, Any]) -> None:
        if not isinstance(probe, dict):
            return
        after = _stats_snapshot(policy)
        row = self._make_record(policy, probe['record'], probe['node_ctx'], search_state, int(probe['candidate_count']), probe['before'], after, 0)
        if int(row['full_review']) == 1 and int(row['witness_hit']) == 0:
            search_state['_cx47log_pending'] = {
                'row': row,
                'after_extra': after,
            }
        else:
            self._rows.append(row)

    def after_rank(self, policy: Any, search_state: dict[str, Any]) -> None:
        pending = search_state.get('_cx47log_pending')
        if not isinstance(pending, dict) or not isinstance(pending.get('row'), dict):
            search_state['_cx47log_event_seen'] = 0
            return
        after_rank = _stats_snapshot(policy)
        row = dict(pending['row'])
        after_extra = dict(pending.get('after_extra', {}))
        row['witness_store_negative_delta'] = float(after_rank.get('witness_store_negative', 0.0) - after_extra.get('witness_store_negative', 0.0))
        row['store_negative'] = int(float(row['witness_store_negative_delta']) > 1e-6)
        self._rows.append(row)
        search_state['_cx47log_pending'] = None
        search_state['_cx47log_event_seen'] = 0


class PolicyEventAdapter:
    def __init__(self, policy: Any, logger: EventLogBuffer) -> None:
        self.policy = policy
        self.logger = logger

    def __getattr__(self, name: str) -> Any:
        return getattr(self.policy, name)

    def start_search(self, planner, start, goal, h_pair, search_state):
        self.logger.start_search(search_state)
        if hasattr(self.policy, 'start_search'):
            return self.policy.start_search(planner, start, goal, h_pair, search_state)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        return self.policy.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        probe = self.logger.before_extra(self.policy, record, node_ctx, candidates, search_state)
        out = self.policy.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        self.logger.after_extra(self.policy, probe, search_state)
        return out

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        out = self.policy.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        self.logger.after_rank(self.policy, search_state)
        return out

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if hasattr(self.policy, 'complete_expand'):
            return self.policy.complete_expand(planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair)


def cx46_feature_fn(policy: Any, record: Any, node_ctx: dict[str, Any], search_state: dict[str, Any]) -> dict[str, Any]:
    event_key = _base_event_key(policy.case, node_ctx)
    support_count = 0
    if hasattr(policy, 'type_counter'):
        support_count = int(getattr(policy, 'type_counter', {}).get(event_key, 0))
    return {
        'support_count': int(support_count),
        'store_strength_proxy': float(np.tanh(float(support_count) / 4.0)),
        'event_seen': int(search_state.get('_cx47log_event_seen', 0)) if isinstance(search_state, dict) else 0,
    }
