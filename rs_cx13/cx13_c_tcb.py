from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx13.common import (
    BASELINE_CHOSEN_JSON,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    extract_tickets,
    query_ticket,
)


@dataclass(frozen=True)
class CX13CTCBParams:
    top_k: int
    radius_m: float
    reserve_budget: int
    overrun_penalty: float
    reverse_quota: int
    corridor_bonus: float


def param_grid() -> list[CX13CTCBParams]:
    return [
        CX13CTCBParams(2, 2.2, 8, 0.18, 2, 0.04),
        CX13CTCBParams(3, 2.0, 7, 0.20, 2, 0.04),
        CX13CTCBParams(3, 1.8, 6, 0.24, 1, 0.05),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Contract', 'disable_contract': True}]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX13CTCBParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    guard_assets = list((dependencies or {}).get('guard_assets', []))
    stats = []
    for asset in guard_assets:
        tickets = extract_tickets(
            asset['case'],
            asset['bundle'],
            asset['field'],
            top_k=int(params.top_k),
            radius_m=float(params.radius_m),
            reserve_budget=int(params.reserve_budget),
            overrun_penalty=float(params.overrun_penalty),
            reverse_quota=int(params.reverse_quota),
        )
        stats.append({'sample_name': str(asset['path'].name), 'num_tickets': len(tickets)})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'tcb_meta.json').write_text(json.dumps({'guard_stats': stats[:20], 'num_guard_assets': len(stats)}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'best_val_loss': float('nan')}


class TCBPolicy:
    def __init__(self, case: dict[str, Any], tickets: list[Any], params: CX13CTCBParams, disable_contract: bool = False) -> None:
        self.case = case
        self.tickets = tickets
        self.params = params
        self.disable_contract = bool(disable_contract)
        self.count_key = '_cx13_tcb_counts'
        self.rev_key = '_cx13_tcb_rev'

    def _counts(self, search_state: dict[str, Any]) -> dict[int, int]:
        return search_state.setdefault(self.count_key, {})

    def _reverse_counts(self, search_state: dict[str, Any]) -> dict[int, int]:
        return search_state.setdefault(self.rev_key, {})

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        ticket_id = query_ticket(self.tickets, (float(record.x), float(record.y), float(record.yaw)))
        return {'ticket_id': int(ticket_id)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_contract:
            return [(cand, {'priority_secondary_delta': 0.0}) for cand in candidates]
        counts = self._counts(search_state)
        reverse_counts = self._reverse_counts(search_state)
        ticket_meta = {int(t.ticket_id): t for t in self.tickets}
        ranked = []
        for cand in candidates:
            ticket_id = query_ticket(self.tickets, cand.next_state)
            ticket = ticket_meta.get(int(ticket_id), None)
            delta = 0.0
            if ticket is not None:
                used = int(counts.get(int(ticket_id), 0))
                rev_used = int(reverse_counts.get(int(ticket_id), 0))
                if used >= int(ticket.reserve_budget):
                    delta += float(ticket.overrun_penalty)
                if int(cand.direction) < 0 and rev_used >= int(ticket.reverse_quota):
                    delta += float(ticket.overrun_penalty)
                if used < int(ticket.reserve_budget):
                    delta -= float(self.params.corridor_bonus) * (0.5 + float(ticket.score))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if self.disable_contract:
            return
        ticket_id = int(node_ctx.get('ticket_id', 0)) if isinstance(node_ctx, dict) else 0
        if ticket_id == 0:
            return
        counts = self._counts(search_state)
        counts[ticket_id] = int(counts.get(ticket_id, 0)) + 1
        if int(record.direction) < 0:
            reverse_counts = self._reverse_counts(search_state)
            reverse_counts[ticket_id] = int(reverse_counts.get(ticket_id, 0)) + 1


def make_policy(memory: dict[str, Any], params: CX13CTCBParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    tickets = extract_tickets(
        case,
        bundle,
        field,
        top_k=int(params.top_k),
        radius_m=float(params.radius_m),
        reserve_budget=int(params.reserve_budget),
        overrun_penalty=float(params.overrun_penalty),
        reverse_quota=int(params.reverse_quota),
    )
    return TCBPolicy(case, tickets, params, disable_contract=bool(isinstance(ablation, dict) and ablation.get('disable_contract', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX13CTCBParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    _, field = build_base_field(case, predictor, cfg)
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX13CTCBParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
