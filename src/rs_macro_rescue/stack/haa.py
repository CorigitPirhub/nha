from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_macro_rescue.stack.support import SupportBand, TreeNode, fit_support_band, fit_tree, predict_tree, support_match, tree_to_dict
from rs_macro_rescue.stack import shadow_policy as sha_mod
from rs_macro_rescue.stack.shadow import (
    EPISODE_FEATURE_NAMES,
    FEATURE_NAMES,
    FrozenTeacher,
    build_frozen_teacher,
    class_key,
    episode_feature_vector,
    make_teacher_policy,
    state_feature_vector,
    teacher_prepare,
    top_allowed_bucket,
)
from rs_macro_rescue.stack.legality import family_bucket_name


FAMILY_BUCKETS = ('straight', 'forward_turn', 'reverse', 'reverse_setup')
ADOPTION_FEATURE_NAMES = FEATURE_NAMES + EPISODE_FEATURE_NAMES


@dataclass(frozen=True)
class FrozenShadowTeacher:
    params: sha_mod.CX22DSHAParams
    memory: dict[str, Any]

    @property
    def lag_teacher(self) -> FrozenTeacher:
        return self.memory['teacher']


FROZEN_SHADOW_PARAMS = sha_mod.CX22DSHAParams(min_hits=4, lcb_q=0.20, min_score=0.0)


def load_frozen_shadow_params() -> sha_mod.CX22DSHAParams:
    return FROZEN_SHADOW_PARAMS


def build_frozen_shadow_teacher(train_assets, val_assets, predictor, cfg, device: str, out_dir: Path, dependencies: dict[str, Any] | None = None) -> FrozenShadowTeacher:
    if isinstance(dependencies, dict) and isinstance(dependencies.get('shadow_teacher'), FrozenShadowTeacher):
        return dependencies['shadow_teacher']
    params = load_frozen_shadow_params()
    memory = sha_mod.fit_variant(train_assets, val_assets, predictor, cfg, params, out_dir / 'shadow_teacher_fit', device, dependencies)
    return FrozenShadowTeacher(params=params, memory=memory)


def make_shadow_policy(shadow_teacher: FrozenShadowTeacher, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray):
    case['_cx21_bundle'] = bundle
    return sha_mod.make_policy(shadow_teacher.memory, shadow_teacher.params, case, bundle, field, 'cuda', ablation=None)


def shadow_prepare(policy, state: tuple[float, float, float]) -> dict[str, Any]:
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


def adoption_feature_vector(case: dict[str, Any], bundle: dict[str, Any], ctx: dict[str, Any]) -> np.ndarray:
    return np.concatenate([state_feature_vector(ctx), episode_feature_vector(case, bundle, ctx)], axis=0).astype(np.float32)


def class_parts(key: str) -> tuple[str, str]:
    raw = str(key)
    if '|' not in raw:
        return 'uncertain', 'none'
    mode, bucket = raw.split('|', 1)
    return str(mode), str(bucket)


def class_key_from_parts(mode: str, bucket: str) -> str:
    return f'{str(mode)}|{str(bucket)}'


def macros_for_bucket(lag_teacher: FrozenTeacher, mode: str, bucket: str, *, max_macros: int) -> list[Any]:
    macros = list(lag_teacher.memory.get('macros', []))
    out = []
    for macro in macros:
        fam_bucket = family_bucket_name(str(macro.family))
        if str(bucket) == 'none':
            continue
        if str(mode) == 'reverse_setup':
            if fam_bucket in {'reverse', 'reverse_setup'}:
                out.append(macro)
        elif str(mode) == 'escape_border':
            if fam_bucket == str(bucket) or (str(bucket) in {'reverse', 'reverse_setup'} and fam_bucket in {'reverse', 'reverse_setup'}):
                out.append(macro)
        else:
            if fam_bucket == str(bucket):
                out.append(macro)
        if len(out) >= int(max(max_macros, 0)):
            break
    return out


def rules_for_bucket(mode: str, bucket: str) -> tuple[dict[str, str], bool]:
    rules = {fam: 'discouraged' for fam in FAMILY_BUCKETS}
    must_precede = False
    mode = str(mode)
    bucket = str(bucket)
    if bucket == 'none':
        return rules, False
    if mode == 'forward_safe':
        rules[bucket] = 'allowed'
        if bucket in {'straight', 'forward_turn'}:
            other = 'forward_turn' if bucket == 'straight' else 'straight'
            rules[other] = 'discouraged'
    elif mode == 'reverse_setup':
        rules['reverse'] = 'allowed'
        rules['reverse_setup'] = 'allowed'
        rules['straight'] = 'forbidden'
        rules['forward_turn'] = 'discouraged'
        must_precede = True
    elif mode == 'escape_border':
        if bucket in {'reverse', 'reverse_setup'}:
            rules['reverse'] = 'allowed'
            rules['reverse_setup'] = 'allowed'
            rules['forward_turn'] = 'discouraged'
            rules['straight'] = 'forbidden'
        else:
            rules[bucket] = 'allowed'
            rules['straight'] = 'discouraged'
            rules['forward_turn'] = 'discouraged'
    else:
        rules[bucket] = 'allowed'
    return rules, must_precede


def apply_class_edit(ctx: dict[str, Any], lag_teacher: FrozenTeacher, target_key: str, *, max_macros: int) -> dict[str, Any]:
    mode, bucket = class_parts(target_key)
    new_ctx = dict(ctx)
    rules, must_precede = rules_for_bucket(mode, bucket)
    new_ctx['mode'] = str(mode)
    new_ctx['rules'] = rules
    new_ctx['must_precede'] = bool(must_precede)
    new_ctx['macros'] = macros_for_bucket(lag_teacher, mode, bucket, max_macros=int(max_macros))
    conf = {fam: (1.0 if str(rules.get(fam, 'discouraged')) == 'allowed' else 0.0) for fam in FAMILY_BUCKETS}
    new_ctx['conf'] = conf
    return new_ctx


def compile_shadow_rows(train_assets: list[dict[str, Any]], shadow_teacher: FrozenShadowTeacher, *, horizon_steps: int, stride: int = 1) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = make_shadow_policy(shadow_teacher, case, bundle, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 3:
            continue
        contexts = [shadow_prepare(policy, tuple(map(float, state))) for state in path]
        costs = [float(ctx.get('foundation').cost_to_go) if ctx.get('foundation') is not None else 0.0 for ctx in contexts]
        for idx in range(0, max(len(contexts) - 1, 0), max(int(stride), 1)):
            ctx = contexts[idx]
            future = costs[idx + 1 : min(len(costs), idx + 1 + int(max(horizon_steps, 1)))]
            gain = float(costs[idx] - min(future)) if future else 0.0
            rows.append({
                'scenario': str(case['scenario']),
                'class_key': str(class_key(ctx)),
                'mode': str(ctx.get('mode', 'uncertain')),
                'bucket': str(top_allowed_bucket(ctx)),
                'active': bool(len(list(ctx.get('macros', []))) > 0),
                'feature': adoption_feature_vector(case, bundle, ctx),
                'future_gain': float(gain),
            })
    return rows


def frequent_positive_classes(rows: list[dict[str, Any]], *, min_hits: int, min_gain: float) -> list[str]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row['class_key']), []).append(float(row['future_gain']))
    out = []
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=np.float32)
        if int(arr.size) >= int(max(min_hits, 1)) and float(np.mean(arr)) >= float(min_gain):
            out.append(str(key))
    out.sort()
    return out


def build_class_support(rows: list[dict[str, Any]], *, positive: bool, min_hits: int) -> dict[str, SupportBand]:
    grouped_feats: dict[str, list[np.ndarray]] = {}
    grouped_gains: dict[str, list[float]] = {}
    for row in rows:
        label = float(row['future_gain'])
        if positive and label <= 0.0:
            continue
        if (not positive) and label >= 0.0:
            continue
        key = str(row['class_key'])
        grouped_feats.setdefault(key, []).append(np.asarray(row['feature'], dtype=np.float32))
        grouped_gains.setdefault(key, []).append(label)
    out: dict[str, SupportBand] = {}
    for key, feats in grouped_feats.items():
        if len(feats) < int(max(min_hits, 1)):
            continue
        band = fit_support_band(feats, grouped_gains[key], low_q=0.05, high_q=0.95, sim_q=0.15)
        if band is not None:
            out[str(key)] = band
    return out


def best_support_class(support: dict[str, SupportBand], feat: np.ndarray, *, gain_hint: float, slack: float, allowed_keys: set[str] | None = None) -> tuple[str, float]:
    best_key = 'uncertain|none'
    best_sim = -1.0
    for key, band in support.items():
        if allowed_keys is not None and str(key) not in allowed_keys:
            continue
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched and float(sim) > best_sim:
            best_key = str(key)
            best_sim = float(sim)
    return str(best_key), float(best_sim if best_sim > -1.0 else 0.0)


__all__ = [
    'ADOPTION_FEATURE_NAMES',
    'EPISODE_FEATURE_NAMES',
    'FAMILY_BUCKETS',
    'FEATURE_NAMES',
    'FrozenShadowTeacher',
    'SupportBand',
    'TreeNode',
    'adoption_feature_vector',
    'apply_class_edit',
    'best_support_class',
    'build_class_support',
    'build_frozen_shadow_teacher',
    'class_key',
    'class_key_from_parts',
    'class_parts',
    'compile_shadow_rows',
    'fit_tree',
    'frequent_positive_classes',
    'load_frozen_shadow_params',
    'make_shadow_policy',
    'predict_tree',
    'rules_for_bucket',
    'shadow_prepare',
    'tree_to_dict',
]
