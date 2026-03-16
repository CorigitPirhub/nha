from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_cx11.common import TreeNode, fit_tree, predict_tree, tree_to_dict
from rs_cx15.common import primitive_group
from rs_cx21 import cx21_b_lag as lag_mod
from rs_cx21.common import family_bucket_name
from rs_cx21.common import run_hybrid_with_policy
from rs_cx8.common import query_yaw_field


FROZEN_CHOSEN_JSON = Path('outputs/rs_p0cx21_b_pilot_v1/chosen.json')


@dataclass(frozen=True)
class FrozenTeacher:
    params: lag_mod.CX21BLAGParams
    memory: dict[str, Any]


FEATURE_NAMES = (
    'cost_to_go',
    'viability',
    'reverse_required',
    'trap_escape_affinity',
    'trap',
    'corridor',
    'oracle_gain',
    'max_conf',
    'allowed_count',
)


EPISODE_FEATURE_NAMES = (
    'scene_hard',
    'scene_misc',
    'scene_bridge',
    'scene_open',
    'cost_to_go',
    'viability',
    'reverse_required',
    'trap_escape_affinity',
    'oracle_gain',
    'max_conf',
    'allowed_count',
)


MODE_INDEX = {
    'uncertain': 0,
    'forward_safe': 1,
    'reverse_setup': 2,
    'escape_border': 3,
}


def load_frozen_teacher_params(chosen_json: Path = FROZEN_CHOSEN_JSON) -> lag_mod.CX21BLAGParams:
    data = json.loads(Path(chosen_json).read_text(encoding='utf-8'))
    return lag_mod.CX21BLAGParams(**data['params'])


def build_frozen_teacher(train_assets, val_assets, predictor, cfg, device: str, out_dir: Path, dependencies: dict[str, Any] | None = None) -> FrozenTeacher:
    if isinstance(dependencies, dict) and isinstance(dependencies.get('teacher'), FrozenTeacher):
        return dependencies['teacher']
    params = load_frozen_teacher_params()
    memory = lag_mod.fit_variant(train_assets, val_assets, predictor, cfg, params, out_dir / 'teacher_fit', device)
    return FrozenTeacher(params=params, memory=memory)


def make_teacher_policy(teacher: FrozenTeacher, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray):
    case['_cx21_bundle'] = bundle
    return lag_mod.make_policy(teacher.memory, teacher.params, case, bundle, field, 'cuda', ablation=None)


def teacher_prepare(policy, state: tuple[float, float, float]) -> dict[str, Any]:
    rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]))
    ctx = policy.prepare_expand(
        planner=None,
        record=rec,
        goal=None,
        records=None,
        open_heap=None,
        anchor_heap=None,
        search_state=None,
        h_pair=None,
    )
    return dict(ctx) if isinstance(ctx, dict) else {}


def _max_conf(ctx: dict[str, Any]) -> float:
    conf = dict(ctx.get('conf', {}))
    return float(max(conf.values())) if conf else 0.0


def _allowed_count(ctx: dict[str, Any]) -> int:
    rules = dict(ctx.get('rules', {}))
    return int(sum(1 for value in rules.values() if str(value) == 'allowed'))


def state_feature_vector(ctx: dict[str, Any]) -> np.ndarray:
    foundation = ctx.get('foundation')
    if foundation is None:
        return np.zeros(len(FEATURE_NAMES), dtype=np.float32)
    oracle_gain = float(ctx.get('oracle_gain', 0.0))
    return np.asarray([
        float(foundation.cost_to_go),
        float(foundation.viability),
        float(foundation.reverse_required),
        float(foundation.trap_escape_affinity),
        float(foundation.trap),
        float(foundation.corridor),
        float(oracle_gain),
        float(_max_conf(ctx)),
        float(_allowed_count(ctx)),
    ], dtype=np.float32)


def episode_feature_vector(case: dict[str, Any], bundle: dict[str, Any], ctx: dict[str, Any]) -> np.ndarray:
    foundation = ctx.get('foundation')
    scene = dict(bundle.get('scene', {}))
    return np.asarray([
        float(scene.get('hard_likelihood', 0.0)),
        float(scene.get('misc_likelihood', 0.0)),
        float(scene.get('bridge_diffuse', 0.0)),
        float(scene.get('path_openness', 0.0)),
        float(getattr(foundation, 'cost_to_go', 0.0)),
        float(getattr(foundation, 'viability', 0.0)),
        float(getattr(foundation, 'reverse_required', 0.0)),
        float(getattr(foundation, 'trap_escape_affinity', 0.0)),
        float(ctx.get('oracle_gain', 0.0)),
        float(_max_conf(ctx)),
        float(_allowed_count(ctx)),
    ], dtype=np.float32)


def state_mode(ctx: dict[str, Any]) -> str:
    return str(ctx.get('mode', 'uncertain'))


def top_allowed_bucket(ctx: dict[str, Any]) -> str:
    rules = dict(ctx.get('rules', {}))
    conf = dict(ctx.get('conf', {}))
    allowed = [bucket for bucket, label in rules.items() if str(label) == 'allowed']
    if not allowed:
        return 'none'
    allowed.sort(key=lambda bucket: float(conf.get(bucket, 0.0)), reverse=True)
    return str(allowed[0])


def class_key(ctx: dict[str, Any]) -> str:
    return f"{state_mode(ctx)}|{top_allowed_bucket(ctx)}"


def _future_gain_from_costs(costs: list[float], idx: int, horizon_steps: int) -> float:
    future = costs[idx + 1 : min(len(costs), idx + 1 + int(max(horizon_steps, 1)))]
    if not future:
        return 0.0
    return float(costs[idx] - min(future))


def compile_teacher_state_rows(train_assets: list[dict[str, Any]], teacher: FrozenTeacher, *, horizon_steps: int, stride: int = 1) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = make_teacher_policy(teacher, case, bundle, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 3:
            continue
        contexts = [teacher_prepare(policy, tuple(map(float, state))) for state in path]
        costs = [float(ctx.get('foundation').cost_to_go) if ctx.get('foundation') is not None else float(query_yaw_field(field, float(state[0]), float(state[1]), float(state[2]), float(case['resolution']))) for state, ctx in zip(path, contexts)]
        for idx in range(0, max(len(contexts) - 1, 0), max(int(stride), 1)):
            ctx = contexts[idx]
            gain = _future_gain_from_costs(costs, idx, int(horizon_steps))
            rows.append({
                'scenario': str(case['scenario']),
                'feature': state_feature_vector(ctx),
                'episode_feature': episode_feature_vector(case, bundle, ctx),
                'mode': state_mode(ctx),
                'mode_index': int(MODE_INDEX.get(state_mode(ctx), 0)),
                'top_bucket': top_allowed_bucket(ctx),
                'class_key': class_key(ctx),
                'future_gain': float(gain),
                'max_conf': float(_max_conf(ctx)),
                'oracle_gain': float(ctx.get('oracle_gain', 0.0)),
                'allowed_count': int(_allowed_count(ctx)),
            })
    return rows


def teacher_case_deltas(train_assets: list[dict[str, Any]], teacher: FrozenTeacher, *, cap: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = make_teacher_policy(teacher, case, bundle, field)
        plan = run_hybrid_with_policy(case, field, int(cap), successor_policy=policy, record_expanded=False)
        baseline = asset['baseline_result']
        start_ctx = teacher_prepare(policy, tuple(map(float, case['start'])))
        rows.append({
            'scenario': str(case['scenario']),
            'sample_name': str(asset['path'].name),
            'episode_feature': episode_feature_vector(case, bundle, start_ctx),
            'success_delta': float(plan.success) - float(baseline.success),
            'exp_delta': float(baseline.expansions) - float(plan.expansions),
            'time_overhead_ratio': (float(plan.runtime_ms) - float(baseline.runtime_ms)) / max(float(baseline.runtime_ms), 1e-6),
        })
    return rows


def class_stats_from_rows(rows: list[dict[str, Any]], *, use_lcb: bool, min_hits: int, lcb_q: float) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row['class_key']), []).append(float(row['future_gain']))
    out: dict[str, dict[str, float]] = {}
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=np.float32)
        if int(arr.size) < int(max(min_hits, 1)):
            continue
        score = float(np.quantile(arr, float(lcb_q))) if bool(use_lcb) else float(np.mean(arr))
        out[str(key)] = {
            'hits': int(arr.size),
            'avg_gain': float(np.mean(arr)),
            'score': float(score),
        }
    return out


def promotion_score_from_public(public_delta: list[dict[str, Any]], public_family: list[dict[str, Any]], method_name: str) -> tuple[float, dict[str, float]]:
    full = next((r for r in public_delta if r['dataset'] == 'exp4' and r['method'] == method_name), None)
    family_map = {}
    for row in public_family:
        if row['dataset'] == 'exp4' and row['method'] == method_name:
            family_map[str(row['scenario'])] = float(row['exp_delta'])
    full_exp = float(full['exp_delta']) if full is not None else float('-inf')
    penalties = (
        0.75 * min(0.0, float(family_map.get('narrow_passage', 0.0)))
        + 0.75 * min(0.0, float(family_map.get('maze', 0.0)))
        + 0.50 * min(0.0, float(family_map.get('parasol_misc', 0.0)))
    )
    score = float(full_exp + penalties)
    family_map['promotion_score'] = float(score)
    return float(score), family_map


__all__ = [
    'EPISODE_FEATURE_NAMES',
    'FEATURE_NAMES',
    'FROZEN_CHOSEN_JSON',
    'FrozenTeacher',
    'MODE_INDEX',
    'TreeNode',
    'build_frozen_teacher',
    'class_key',
    'class_stats_from_rows',
    'compile_teacher_state_rows',
    'episode_feature_vector',
    'fit_tree',
    'load_frozen_teacher_params',
    'make_teacher_policy',
    'predict_tree',
    'promotion_score_from_public',
    'state_feature_vector',
    'teacher_case_deltas',
    'teacher_prepare',
    'top_allowed_bucket',
    'tree_to_dict',
]
