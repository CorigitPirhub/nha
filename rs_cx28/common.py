from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx21.common import macro_successor_candidates
from rs_cx23.common import apply_class_edit, class_key, class_parts, macros_for_bucket
from rs_cx27.common import (
    CX27DiagnosticsMixin,
    CX27WatchdogConfig,
    block_signature,
    build_frozen_haa_stack,
    complete_watchdog,
    coarse_state_key,
    downgrade_to_uncertain,
    init_watchdog,
    scene_kind,
    set_candidate,
    watchdog_evidence,
)


FROZEN_CX27A_CHOSEN = Path('outputs/rs_p0cx27_a_pilot_v1/chosen.json')


def load_cx27a_parent_params() -> dict[str, Any]:
    return json.loads(FROZEN_CX27A_CHOSEN.read_text(encoding='utf-8'))


def primitive_proxy_score(planner, record, h_pair) -> float:
    if planner is None or h_pair is None:
        return float('-inf')
    here = float(record.g + record.guided)
    best = float('-inf')
    for steer, direction in list(getattr(planner, 'motion_primitives', [])):
        nxt = planner._simulate(float(record.x), float(record.y), float(record.yaw), float(steer), int(direction))
        if nxt is None:
            continue
        _, nguided = h_pair(*nxt)
        best = max(best, float(here - (record.g + float(nguided))))
    return float(best)


def class_proxy_score(case: dict[str, Any], planner, record, h_pair, lag_teacher, target_key: str, *, max_macros: int) -> float:
    if str(target_key) == 'uncertain|none':
        return primitive_proxy_score(planner, record, h_pair)
    mode, bucket = class_parts(str(target_key))
    macros = macros_for_bucket(lag_teacher, mode, bucket, max_macros=int(max_macros))
    if not macros:
        return float('-inf')
    cands = macro_successor_candidates(case, planner, record, h_pair, macros, max_macros=len(macros))
    if not cands:
        return float('-inf')
    here = float(record.g + record.guided)
    return float(max(float(here - (record.g + float(c.guided))) for c in cands))


def misc_scene_bonus(bundle: dict[str, Any], target_key: str) -> float:
    scene = dict(bundle.get('scene', {}))
    barrier_peak = float(scene.get('barrier_peak', 0.0))
    hard_like = float(scene.get('hard_likelihood', 0.0))
    misc_like = float(scene.get('misc_likelihood', 0.0))
    bridge_diffuse = float(scene.get('bridge_diffuse', 0.0))
    bonus = 0.0
    if str(target_key) == 'forward_safe|forward_turn' and barrier_peak >= 0.9:
        bonus += 0.06
    if str(target_key) == 'reverse_setup|reverse' and misc_like >= 0.75 and hard_like <= 0.70:
        bonus += 0.05
    if str(target_key) == 'escape_border|reverse' and bridge_diffuse >= 0.08:
        bonus += 0.04
    return float(bonus)


def misc_shortlist(bundle: dict[str, Any], current_key: str) -> list[str]:
    out = [str(current_key), 'forward_safe|forward_turn', 'reverse_setup|reverse', 'escape_border|reverse', 'uncertain|none']
    seen = set()
    unique = []
    for item in out:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def set_class_block(search_state: dict[str, Any], key: str, ttl: int) -> None:
    blocked = dict(search_state.get('cx28_misc_blocked', {}))
    blocked[str(key)] = int(search_state.get('popped', 0)) + int(ttl)
    search_state['cx28_misc_blocked'] = blocked


def misc_blocked(search_state: dict[str, Any], key: str) -> bool:
    blocked = dict(search_state.get('cx28_misc_blocked', {}))
    return int(blocked.get(str(key), -1)) >= int(search_state.get('popped', 0))


def prune_misc_blocks(search_state: dict[str, Any]) -> None:
    blocked = dict(search_state.get('cx28_misc_blocked', {}))
    current = int(search_state.get('popped', 0))
    search_state['cx28_misc_blocked'] = {str(k): int(v) for k, v in blocked.items() if int(v) >= current}


def init_misc_watchdog(search_state: dict[str, Any]) -> None:
    init_watchdog(search_state)
    search_state['cx28_misc_blocked'] = {}


class BaseCX28Policy(CX27DiagnosticsMixin):
    def _init_core(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, teacher, watchdog_cfg: CX27WatchdogConfig, enable_diagnostics: bool) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.teacher = teacher
        self.scene_kind = str(scene_kind(case, bundle))
        self.active = bool(str(case.get('scenario', '')) in {'maze', 'parasol_misc'})
        self.watchdog_cfg = watchdog_cfg
        self._diag_init(enabled=enable_diagnostics)

    def start_search(self, planner, start, goal, h_pair, search_state):
        search_state['cx28_active'] = bool(self.active)
        if self.active:
            init_misc_watchdog(search_state)

    def _maze_guard(self, ctx: dict[str, Any], search_state: dict[str, Any], evidence: dict[str, Any], *, revisit_thr: int, stall_steps: int, reverse_required_thr: float, trap_thr: float) -> tuple[dict[str, Any], str]:
        guard_reason = 'none'
        if str(self.scene_kind) != 'maze' or str(search_state.get('haa_state', 'observe')) not in {'candidate', 'commit'}:
            return ctx, guard_reason
        trigger = bool(
            bool(evidence.get('blocklist_hit', False))
            or int(evidence.get('revisit_count', 0)) >= int(revisit_thr)
            or int(evidence.get('stall_steps', 0)) >= int(stall_steps)
        )
        if not trigger:
            return ctx, guard_reason
        foundation = ctx.get('foundation')
        current_key = str(evidence.get('class_key', class_key(ctx)))
        if current_key == 'forward_safe|straight' and foundation is not None and (
            float(getattr(foundation, 'reverse_required', 0.0)) >= float(reverse_required_thr)
            or float(getattr(foundation, 'trap', 0.0)) >= float(trap_thr)
        ):
            ctx = apply_class_edit(ctx, self.teacher.shadow_teacher.lag_teacher, 'reverse_setup|reverse', max_macros=int(self.teacher.params.max_macros))
            set_candidate(search_state, 'reverse_setup|reverse')
            guard_reason = 'maze_reverse_setup'
        else:
            ctx = downgrade_to_uncertain(search_state, ctx, self.teacher.shadow_teacher.lag_teacher, max_macros=int(self.teacher.params.max_macros))
            guard_reason = 'maze_abstain'
        return ctx, guard_reason

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if not bool(search_state.get('cx28_active', False)) or not isinstance(node_ctx, dict):
            return
        complete_watchdog(search_state, record, self.case, self.bundle, node_ctx, self.watchdog_cfg)
        prune_misc_blocks(search_state)


__all__ = [
    'BaseCX28Policy',
    'CX27DiagnosticsMixin',
    'CX27WatchdogConfig',
    'apply_class_edit',
    'block_signature',
    'build_frozen_haa_stack',
    'class_key',
    'class_proxy_score',
    'coarse_state_key',
    'complete_watchdog',
    'downgrade_to_uncertain',
    'init_misc_watchdog',
    'load_cx27a_parent_params',
    'misc_blocked',
    'misc_scene_bonus',
    'misc_shortlist',
    'primitive_proxy_score',
    'scene_kind',
    'set_candidate',
    'set_class_block',
    'watchdog_evidence',
]
