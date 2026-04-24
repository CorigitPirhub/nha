from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_macro_rescue.stack.haa import apply_class_edit, class_key
from rs_macro_rescue.stack.haa_stack import FrozenHAATeacher, build_frozen_haa_teacher


@dataclass(frozen=True)
class CX27WatchdogConfig:
    cell_stride: int
    yaw_bins: int
    progress_eps: float
    commit_fail_margin: float
    failure_ttl: int
    history_window: int


def build_frozen_haa_stack(train_assets, val_assets, predictor, cfg, device: str, out_dir: Path, dependencies: dict[str, Any] | None = None) -> FrozenHAATeacher:
    if isinstance(dependencies, dict) and isinstance(dependencies.get('haa_teacher'), FrozenHAATeacher):
        return dependencies['haa_teacher']
    return build_frozen_haa_teacher(train_assets, val_assets, predictor, cfg, device, out_dir, dependencies)


def scene_kind(case: dict[str, Any], bundle: dict[str, Any]) -> str:
    scenario = str(case.get('scenario', ''))
    if scenario in {'maze', 'maze_single', 'maze_multi', 'deadend_labyrinth'}:
        return 'maze'
    if scenario == 'parasol_misc':
        return 'misc'
    scene = dict(bundle.get('scene', {}))
    barrier_peak = float(scene.get('barrier_peak', 0.0))
    hard_like = float(scene.get('hard_likelihood', 0.0))
    misc_like = float(scene.get('misc_likelihood', 0.0))
    if barrier_peak <= 0.05 and misc_like >= 0.95 and hard_like <= 0.60:
        return 'maze'
    if misc_like >= 0.80 and hard_like <= 0.55:
        return 'misc'
    return 'default'


def coarse_state_key(record, case: dict[str, Any], *, cell_stride: int, yaw_bins: int) -> tuple[int, int, int]:
    resolution = max(float(case.get('resolution', 1.0)), 1e-6)
    stride = max(int(cell_stride), 1)
    gx = int(np.floor(float(record.x) / resolution / float(stride)))
    gy = int(np.floor(float(record.y) / resolution / float(stride)))
    yaw = float(record.yaw)
    yaw_idx = int(np.floor((yaw + np.pi) / (2.0 * np.pi) * float(max(int(yaw_bins), 1)))) % max(int(yaw_bins), 1)
    return gx, gy, yaw_idx


def history_churn(history: list[str], current_key: str, *, window: int) -> float:
    if not history:
        return 0.0
    sub = history[-int(max(window, 1)) :]
    return float(np.mean([1.0 if str(item) != str(current_key) else 0.0 for item in sub]))


def loop_rate(state_history: list[str], *, window: int) -> float:
    if len(state_history) < 2:
        return 0.0
    sub = state_history[-int(max(window, 2)) :]
    pairs = list(zip(sub[:-1], sub[1:]))
    if not pairs:
        return 0.0
    return float(np.mean([1.0 if (a == 'commit' and b == 'recover') else 0.0 for a, b in pairs]))


def block_signature(kind: str, coarse_key: tuple[int, int, int], key: str) -> str:
    return f'{str(kind)}|{int(coarse_key[0])}|{int(coarse_key[1])}|{int(coarse_key[2])}|{str(key)}'


def init_watchdog(search_state: dict[str, Any]) -> None:
    search_state['cx27_visit_counts'] = {}
    search_state['cx27_best_anchor'] = float('inf')
    search_state['cx27_stall_steps'] = 0
    search_state['cx27_class_history'] = []
    search_state['cx27_state_history'] = []
    search_state['cx27_prev_auto'] = 'observe'
    search_state['cx27_prev_key'] = 'uncertain|none'
    search_state['cx27_recent_failures'] = 0
    search_state['cx27_commit_meta'] = None
    search_state['cx27_blocked'] = {}
    search_state['cx27_last_commit_failed'] = False
    search_state['cx27_last_failed_key'] = ''
    search_state['cx27_last_failed_kind'] = ''


def watchdog_evidence(search_state: dict[str, Any], record, case: dict[str, Any], bundle: dict[str, Any], ctx: dict[str, Any], cfg: CX27WatchdogConfig) -> dict[str, Any]:
    key = str(class_key(ctx))
    kind = scene_kind(case, bundle)
    coarse = coarse_state_key(record, case, cell_stride=int(cfg.cell_stride), yaw_bins=int(cfg.yaw_bins))
    blocked = dict(search_state.get('cx27_blocked', {}))
    current_popped = int(search_state.get('popped', 0))
    signature = block_signature(kind, coarse, key)
    return {
        'scene_kind': str(kind),
        'class_key': key,
        'coarse_key': coarse,
        'revisit_count': int(dict(search_state.get('cx27_visit_counts', {})).get(coarse, 0)),
        'stall_steps': int(search_state.get('cx27_stall_steps', 0)),
        'class_churn': float(history_churn(list(search_state.get('cx27_class_history', [])), key, window=int(cfg.history_window))),
        'loop_rate': float(loop_rate(list(search_state.get('cx27_state_history', [])), window=int(cfg.history_window))),
        'recent_failures': int(search_state.get('cx27_recent_failures', 0)),
        'blocklist_hit': bool(int(blocked.get(signature, -1)) >= int(current_popped)),
        'signature': signature,
    }


def downgrade_to_uncertain(search_state: dict[str, Any], ctx: dict[str, Any], lag_teacher, *, max_macros: int) -> dict[str, Any]:
    search_state['haa_state'] = 'observe'
    search_state['haa_key'] = ''
    search_state['haa_support_count'] = 0
    search_state['haa_recover_left'] = 0
    return apply_class_edit(ctx, lag_teacher, 'uncertain|none', max_macros=int(max_macros))


def set_candidate(search_state: dict[str, Any], target_key: str) -> None:
    search_state['haa_state'] = 'candidate'
    search_state['haa_key'] = str(target_key)
    search_state['haa_support_count'] = 1
    search_state['haa_recover_left'] = 0


def complete_watchdog(search_state: dict[str, Any], record, case: dict[str, Any], bundle: dict[str, Any], ctx: dict[str, Any], cfg: CX27WatchdogConfig) -> None:
    auto = str(search_state.get('haa_state', 'observe'))
    key = str(search_state.get('haa_key') or class_key(ctx))
    kind = scene_kind(case, bundle)
    coarse = coarse_state_key(record, case, cell_stride=int(cfg.cell_stride), yaw_bins=int(cfg.yaw_bins))
    current_popped = int(search_state.get('popped', 0))

    best_anchor = float(search_state.get('cx27_best_anchor', float('inf')))
    if float(record.anchor) < best_anchor - float(cfg.progress_eps):
        search_state['cx27_best_anchor'] = float(record.anchor)
        search_state['cx27_stall_steps'] = 0
    else:
        search_state['cx27_stall_steps'] = int(search_state.get('cx27_stall_steps', 0)) + 1

    visits = dict(search_state.get('cx27_visit_counts', {}))
    visits[coarse] = int(visits.get(coarse, 0)) + 1
    search_state['cx27_visit_counts'] = visits

    class_hist = list(search_state.get('cx27_class_history', []))
    class_hist.append(str(key))
    search_state['cx27_class_history'] = class_hist[-int(max(cfg.history_window, 1)) :]

    state_hist = list(search_state.get('cx27_state_history', []))
    state_hist.append(str(auto))
    search_state['cx27_state_history'] = state_hist[-int(max(cfg.history_window, 2)) :]

    prev_auto = str(search_state.get('cx27_prev_auto', 'observe'))
    blocked = dict(search_state.get('cx27_blocked', {}))
    search_state['cx27_last_commit_failed'] = False
    search_state['cx27_last_failed_key'] = ''
    search_state['cx27_last_failed_kind'] = ''

    active_blocked = {}
    for signature, expiry in blocked.items():
        if int(expiry) >= int(current_popped):
            active_blocked[str(signature)] = int(expiry)
    blocked = active_blocked

    commit_meta = search_state.get('cx27_commit_meta')
    if auto == 'commit':
        if not isinstance(commit_meta, dict) or prev_auto != 'commit':
            commit_meta = {
                'scene_kind': str(kind),
                'coarse_key': coarse,
                'class_key': str(key),
                'start_anchor': float(record.anchor),
                'best_anchor': float(record.anchor),
            }
        else:
            commit_meta['best_anchor'] = min(float(commit_meta.get('best_anchor', float(record.anchor))), float(record.anchor))
    elif prev_auto == 'commit' and isinstance(commit_meta, dict):
        improvement = float(commit_meta.get('start_anchor', float(record.anchor))) - float(commit_meta.get('best_anchor', float(record.anchor)))
        if improvement < float(cfg.commit_fail_margin):
            signature = block_signature(
                str(commit_meta.get('scene_kind', kind)),
                tuple(commit_meta.get('coarse_key', coarse)),
                str(commit_meta.get('class_key', key)),
            )
            blocked[signature] = int(current_popped) + int(cfg.failure_ttl)
            search_state['cx27_recent_failures'] = min(int(search_state.get('cx27_recent_failures', 0)) + 1, 32)
            search_state['cx27_last_commit_failed'] = True
            search_state['cx27_last_failed_key'] = str(commit_meta.get('class_key', key))
            search_state['cx27_last_failed_kind'] = str(commit_meta.get('scene_kind', kind))
        else:
            search_state['cx27_recent_failures'] = max(int(search_state.get('cx27_recent_failures', 0)) - 1, 0)
        commit_meta = None
    search_state['cx27_commit_meta'] = commit_meta
    search_state['cx27_blocked'] = blocked
    search_state['cx27_prev_auto'] = str(auto)
    search_state['cx27_prev_key'] = str(key)


class CX27DiagnosticsMixin:
    def _diag_init(self, enabled: bool = False) -> None:
        self._diag_enabled = bool(enabled)
        self._diag_rows: list[dict[str, Any]] = []

    def _diag_record(self, record, search_state: dict[str, Any], ctx: dict[str, Any], evidence: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
        if not bool(getattr(self, '_diag_enabled', False)):
            return
        row = {
            'x': float(record.x),
            'y': float(record.y),
            'yaw': float(record.yaw),
            'auto_state': str(search_state.get('haa_state', 'observe')),
            'class_key': str(class_key(ctx)),
            'stall_steps': int(evidence.get('stall_steps', 0)),
            'revisit_count': int(evidence.get('revisit_count', 0)),
            'class_churn': float(evidence.get('class_churn', 0.0)),
            'loop_rate': float(evidence.get('loop_rate', 0.0)),
            'recent_failures': int(evidence.get('recent_failures', 0)),
            'blocklist_hit': int(bool(evidence.get('blocklist_hit', False))),
            'scene_kind': str(evidence.get('scene_kind', 'default')),
        }
        if isinstance(extra, dict):
            for key, value in extra.items():
                row[str(key)] = value
        self._diag_rows.append(row)

    def export_diagnostics(self) -> list[dict[str, Any]]:
        if not bool(getattr(self, '_diag_enabled', False)):
            return []
        return list(getattr(self, '_diag_rows', []))


__all__ = [
    'CX27DiagnosticsMixin',
    'CX27WatchdogConfig',
    'block_signature',
    'build_frozen_haa_stack',
    'coarse_state_key',
    'complete_watchdog',
    'downgrade_to_uncertain',
    'init_watchdog',
    'scene_kind',
    'set_candidate',
    'watchdog_evidence',
]
