from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_macro_rescue.stack.support import SupportBand, fit_support_band, support_match, TreeNode, fit_tree, predict_tree, tree_to_dict
from rs_macro_rescue.stack import haa_policy as haa_mod
from rs_macro_rescue.stack.haa import (
    ADOPTION_FEATURE_NAMES,
    FrozenShadowTeacher,
    adoption_feature_vector,
    apply_class_edit,
    build_frozen_shadow_teacher,
    class_key,
    class_parts,
    class_key_from_parts,
    episode_feature_vector,
    make_shadow_policy,
    shadow_prepare,
    top_allowed_bucket,
)
from rs_macro_rescue.stack.legality import family_bucket_name


TRACE_EXTRA_FEATURES = (
    'support_count',
    'recover_left',
    'auto_state_idx',
    'macro_count',
    'active_flag',
)
TRACE_FEATURE_NAMES = ADOPTION_FEATURE_NAMES + TRACE_EXTRA_FEATURES
AUTO_STATE_INDEX = {
    'observe': 0,
    'candidate': 1,
    'commit': 2,
    'recover': 3,
}
FAMILY_BUCKETS = ('straight', 'forward_turn', 'reverse', 'reverse_setup')


@dataclass(frozen=True)
class FrozenHAATeacher:
    params: haa_mod.CX23CHAAParams
    memory: dict[str, Any]

    @property
    def shadow_teacher(self) -> FrozenShadowTeacher:
        return self.memory['shadow_teacher']


FROZEN_HAA_PARAMS = haa_mod.CX23CHAAParams(min_hits=4, min_gain=0.05, commit_steps=3, recover_steps=4, max_macros=3)


def load_frozen_haa_params() -> haa_mod.CX23CHAAParams:
    return FROZEN_HAA_PARAMS


def build_frozen_haa_teacher(train_assets, val_assets, predictor, cfg, device: str, out_dir: Path, dependencies: dict[str, Any] | None = None) -> FrozenHAATeacher:
    if isinstance(dependencies, dict) and isinstance(dependencies.get('haa_teacher'), FrozenHAATeacher):
        return dependencies['haa_teacher']
    params = load_frozen_haa_params()
    shadow_teacher = build_frozen_shadow_teacher(train_assets, val_assets, predictor, cfg, device, out_dir / 'shadow_cache', dependencies)
    memory = haa_mod.fit_variant(train_assets, val_assets, predictor, cfg, params, out_dir / 'haa_fit', device, {'shadow_teacher': shadow_teacher})
    return FrozenHAATeacher(params=params, memory=memory)


def make_haa_policy(teacher: FrozenHAATeacher, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray):
    case['_cx21_bundle'] = bundle
    return haa_mod.make_policy(teacher.memory, teacher.params, case, bundle, field, 'cuda', ablation=None)


def trace_feature_vector(ctx: dict[str, Any], search_state: dict[str, Any], case: dict[str, Any], bundle: dict[str, Any]) -> np.ndarray:
    return np.concatenate([
        adoption_feature_vector(case, bundle, ctx),
        np.asarray([
            float(search_state.get('haa_support_count', 0)),
            float(search_state.get('haa_recover_left', 0)),
            float(AUTO_STATE_INDEX.get(str(search_state.get('haa_state', 'observe')), 0)),
            float(len(list(ctx.get('macros', [])))),
            float(1.0 if bool(len(list(ctx.get('macros', []))) > 0) else 0.0),
        ], dtype=np.float32),
    ], axis=0).astype(np.float32)


def haa_prepare(policy, state: tuple[float, float, float], search_state: dict[str, Any]) -> dict[str, Any]:
    rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]))
    ctx = policy.prepare_expand(
        planner=None,
        record=rec,
        goal=None,
        records=None,
        open_heap=None,
        anchor_heap=None,
        search_state=search_state,
        h_pair=None,
    )
    return dict(ctx) if isinstance(ctx, dict) else {}


def compile_haa_trace_rows(train_assets: list[dict[str, Any]], teacher: FrozenHAATeacher, *, horizon_steps: int, stride: int = 1) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = make_haa_policy(teacher, case, bundle, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 3:
            continue
        search_state: dict[str, Any] = {}
        contexts = []
        prev_auto = 'observe'
        for idx_state, state in enumerate(path):
            ctx = haa_prepare(policy, tuple(map(float, state)), search_state)
            auto_state = str(search_state.get('haa_state', 'observe'))
            cur_key = str(search_state.get('haa_key', ''))
            contexts.append((ctx, auto_state, cur_key, prev_auto, dict(search_state)))
            prev_auto = auto_state
        costs = [float(ctx.get('foundation').cost_to_go) if ctx.get('foundation') is not None else 0.0 for ctx, _, _, _, _ in contexts]
        for idx in range(0, max(len(contexts) - 1, 0), max(int(stride), 1)):
            ctx, auto_state, cur_key, prev_auto, ss = contexts[idx]
            future = costs[idx + 1 : min(len(costs), idx + 1 + int(max(horizon_steps, 1)))]
            gain = float(costs[idx] - min(future)) if future else 0.0
            rows.append({
                'scenario': str(case['scenario']),
                'sample_name': str(asset['path'].name),
                'class_key': str(class_key(ctx)),
                'auto_state': str(auto_state),
                'prev_auto_state': str(prev_auto),
                'transition': f'{str(prev_auto)}->{str(auto_state)}',
                'active': bool(auto_state == 'commit'),
                'trace_feature': trace_feature_vector(ctx, ss, case, bundle),
                'future_gain': float(gain),
                'support_count': int(ss.get('haa_support_count', 0)),
                'recover_left': int(ss.get('haa_recover_left', 0)),
                'macro_count': int(len(list(ctx.get('macros', [])))),
            })
            prev_auto = auto_state
    return rows


def observatory_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    state_counts: dict[str, int] = {}
    by_scenario: dict[str, dict[str, int]] = {}
    transition_counts: dict[str, int] = {}
    false_commit_slices: list[dict[str, Any]] = []
    for row in rows:
        state = str(row['auto_state'])
        state_counts[state] = int(state_counts.get(state, 0)) + 1
        scen = str(row['scenario'])
        by_scenario.setdefault(scen, {})
        by_scenario[scen][state] = int(by_scenario[scen].get(state, 0)) + 1
        transition = str(row.get('transition', 'observe->observe'))
        transition_counts[transition] = int(transition_counts.get(transition, 0)) + 1
        if state == 'commit' and float(row['future_gain']) <= 0.0:
            false_commit_slices.append({
                'sample_name': str(row['sample_name']),
                'scenario': scen,
                'class_key': str(row['class_key']),
                'transition': transition,
                'future_gain': float(row['future_gain']),
                'support_count': int(row['support_count']),
                'recover_left': int(row['recover_left']),
                'macro_count': int(row['macro_count']),
            })
    false_commit_slices.sort(key=lambda item: float(item['future_gain']))
    return {
        'state_counts': state_counts,
        'state_counts_by_scenario': by_scenario,
        'transition_counts': transition_counts,
        'false_commit_slices': false_commit_slices[:50],
    }


def build_state_support(rows: list[dict[str, Any]], *, predicate, min_hits: int) -> dict[str, SupportBand]:
    grouped_feat: dict[str, list[np.ndarray]] = {}
    grouped_gain: dict[str, list[float]] = {}
    for row in rows:
        if not bool(predicate(row)):
            continue
        key = str(row['class_key'])
        grouped_feat.setdefault(key, []).append(np.asarray(row['trace_feature'], dtype=np.float32))
        grouped_gain.setdefault(key, []).append(float(row['future_gain']))
    out: dict[str, SupportBand] = {}
    for key, feats in grouped_feat.items():
        if len(feats) < int(max(min_hits, 1)):
            continue
        band = fit_support_band(feats, grouped_gain[key], low_q=0.05, high_q=0.95, sim_q=0.15)
        if band is not None:
            out[str(key)] = band
    return out


def best_band_match(bands: dict[str, SupportBand], feat: np.ndarray, *, gain_hint: float, slack: float) -> tuple[str, float]:
    best_key = 'uncertain|none'
    best_sim = -1.0
    for key, band in bands.items():
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched and float(sim) > best_sim:
            best_key = str(key)
            best_sim = float(sim)
    return best_key, float(best_sim if best_sim > -1.0 else 0.0)


class ObservatoryMixin:
    def _diag_init(self) -> None:
        self._diag_rows: list[dict[str, Any]] = []
        self._last_state = 'observe'

    def _diag_record(self, ctx: dict[str, Any], search_state: dict[str, Any], case: dict[str, Any], bundle: dict[str, Any], record) -> None:
        row = {
            'sample_name': str(case.get('map_id', 'unknown')),
            'scenario': str(case.get('scenario', 'unknown')),
            'x': float(record.x),
            'y': float(record.y),
            'yaw': float(record.yaw),
            'auto_state': str(search_state.get('haa_state', 'observe')),
            'class_key': str(class_key(ctx)),
            'support_count': int(search_state.get('haa_support_count', 0)),
            'recover_left': int(search_state.get('haa_recover_left', 0)),
            'macro_count': int(len(list(ctx.get('macros', [])))),
        }
        self._diag_rows.append(row)

    def export_diagnostics(self) -> list[dict[str, Any]]:
        return list(getattr(self, '_diag_rows', []))


__all__ = [
    'AUTO_STATE_INDEX',
    'FAMILY_BUCKETS',
    'FrozenHAATeacher',
    'ObservatoryMixin',
    'TRACE_FEATURE_NAMES',
    'best_band_match',
    'build_frozen_haa_teacher',
    'build_state_support',
    'class_key',
    'class_key_from_parts',
    'class_parts',
    'compile_haa_trace_rows',
    'haa_prepare',
    'load_frozen_haa_params',
    'make_haa_policy',
    'observatory_summary',
    'trace_feature_vector',
]
