from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx24 import cx24_d_ccc as ccc_mod
from rs_cx24 import cx24_e_ato as ato_mod
from rs_cx24.common import (
    AUTO_STATE_INDEX,
    FrozenHAATeacher,
    build_frozen_haa_teacher,
    compile_haa_trace_rows,
    make_haa_policy,
    observatory_summary,
    trace_feature_vector,
)
from rs_cx23.common import apply_class_edit, class_key, class_parts, macros_for_bucket
from rs_cx21.common import family_bucket_name


FROZEN_ATO_CHOSEN = Path('outputs/rs_p0cx24_e_pilot_v1/chosen.json')
FROZEN_CCC_CHOSEN = Path('outputs/rs_p0cx24_d_pilot_v1/chosen.json')


@dataclass(frozen=True)
class FrozenCX24Stack:
    haa_teacher: FrozenHAATeacher
    ato_params: ato_mod.CX24EATOParams
    ato_memory: dict[str, Any]
    ccc_params: ccc_mod.CX24DCCCParams
    ccc_memory: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_frozen_ato_params(chosen_json: Path = FROZEN_ATO_CHOSEN) -> ato_mod.CX24EATOParams:
    return ato_mod.CX24EATOParams(**_load_json(chosen_json)['params'])


def load_frozen_ccc_params(chosen_json: Path = FROZEN_CCC_CHOSEN) -> ccc_mod.CX24DCCCParams:
    return ccc_mod.CX24DCCCParams(**_load_json(chosen_json)['params'])


def build_frozen_cx24_stack(train_assets, val_assets, predictor, cfg, device: str, out_dir: Path, dependencies: dict[str, Any] | None = None) -> FrozenCX24Stack:
    if isinstance(dependencies, dict) and isinstance(dependencies.get('cx24_stack'), FrozenCX24Stack):
        return dependencies['cx24_stack']
    haa_teacher = build_frozen_haa_teacher(train_assets, val_assets, predictor, cfg, device, out_dir / 'haa_cache', dependencies)
    ato_params = load_frozen_ato_params()
    ato_memory = ato_mod.fit_variant(train_assets, val_assets, predictor, cfg, ato_params, out_dir / 'ato_fit', device, {'haa_teacher': haa_teacher})
    ccc_params = load_frozen_ccc_params()
    ccc_memory = ccc_mod.fit_variant(train_assets, val_assets, predictor, cfg, ccc_params, out_dir / 'ccc_fit', device, {'haa_teacher': haa_teacher})
    return FrozenCX24Stack(haa_teacher=haa_teacher, ato_params=ato_params, ato_memory=ato_memory, ccc_params=ccc_params, ccc_memory=ccc_memory)


def make_ato_policy(stack: FrozenCX24Stack, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray):
    case['_cx21_bundle'] = bundle
    return ato_mod.make_policy(stack.ato_memory, stack.ato_params, case, bundle, field, 'cuda', ablation=None)


def make_ccc_policy(stack: FrozenCX24Stack, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray):
    case['_cx21_bundle'] = bundle
    return ccc_mod.make_policy(stack.ccc_memory, stack.ccc_params, case, bundle, field, 'cuda', ablation=None)


def policy_prepare(policy, state: tuple[float, float, float], search_state: dict[str, Any]) -> dict[str, Any]:
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


def compile_dto_rows(train_assets: list[dict[str, Any]], stack: FrozenCX24Stack, *, horizon_steps: int, stride: int = 1) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = make_ato_policy(stack, case, bundle, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 3:
            continue
        search_state: dict[str, Any] = {}
        contexts = []
        prev_auto = 'observe'
        prev_key = 'uncertain|none'
        for state in path:
            ctx = policy_prepare(policy, tuple(map(float, state)), search_state)
            auto_state = str(search_state.get('haa_state', 'observe'))
            cur_key = str(class_key(ctx))
            contexts.append((ctx, auto_state, prev_auto, cur_key, prev_key, dict(search_state)))
            prev_auto = auto_state
            prev_key = cur_key
        costs = [float(ctx.get('foundation').cost_to_go) if ctx.get('foundation') is not None else 0.0 for ctx, _, _, _, _, _ in contexts]
        for idx in range(0, max(len(contexts) - 1, 0), max(int(stride), 1)):
            ctx, auto_state, prev_auto, cur_key, prev_key, ss = contexts[idx]
            future = costs[idx + 1 : min(len(costs), idx + 1 + int(max(horizon_steps, 1)))]
            gain = float(costs[idx] - min(future)) if future else 0.0
            rows.append({
                'scenario': str(case['scenario']),
                'sample_name': str(asset['path'].name),
                'class_key': str(cur_key),
                'prev_class_key': str(prev_key),
                'auto_state': str(auto_state),
                'prev_auto_state': str(prev_auto),
                'transition': f'{str(prev_auto)}->{str(auto_state)}',
                'class_transition': f'{str(prev_key)}->{str(cur_key)}',
                'trace_feature': trace_feature_vector(ctx, ss, case, bundle),
                'future_gain': float(gain),
                'support_count': int(ss.get('haa_support_count', 0)),
                'recover_left': int(ss.get('haa_recover_left', 0)),
                'macro_count': int(len(list(ctx.get('macros', [])))),
                'active': bool(auto_state == 'commit'),
            })
    return rows


def compile_risk_hotspots(rows: list[dict[str, Any]], *, min_hits: int) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        if str(row['auto_state']) != 'commit':
            continue
        grouped.setdefault(str(row['class_key']), []).append(float(row['future_gain']))
    out: dict[str, dict[str, float]] = {}
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=np.float32)
        if int(arr.size) < int(max(min_hits, 1)):
            continue
        neg_rate = float(np.mean(arr <= 0.0))
        out[str(key)] = {
            'hits': int(arr.size),
            'avg_gain': float(np.mean(arr)),
            'neg_rate': float(neg_rate),
        }
    return out


def compile_transition_hotspots(rows: list[dict[str, Any]], *, min_hits: int) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row['transition']), []).append(float(row['future_gain']))
    out: dict[str, dict[str, float]] = {}
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=np.float32)
        if int(arr.size) < int(max(min_hits, 1)):
            continue
        out[str(key)] = {
            'hits': int(arr.size),
            'avg_gain': float(np.mean(arr)),
            'neg_rate': float(np.mean(arr <= 0.0)),
        }
    return out


def build_positive_negative_support(rows: list[dict[str, Any]], *, min_hits: int) -> tuple[dict[str, SupportBand], dict[str, SupportBand]]:
    pos_feats: dict[str, list[np.ndarray]] = {}
    pos_gains: dict[str, list[float]] = {}
    neg_feats: dict[str, list[np.ndarray]] = {}
    neg_gains: dict[str, list[float]] = {}
    for row in rows:
        if str(row['auto_state']) != 'commit':
            continue
        key = str(row['class_key'])
        feat = np.asarray(row['trace_feature'], dtype=np.float32)
        gain = float(row['future_gain'])
        if gain > 0.0:
            pos_feats.setdefault(key, []).append(feat)
            pos_gains.setdefault(key, []).append(gain)
        else:
            neg_feats.setdefault(key, []).append(feat)
            neg_gains.setdefault(key, []).append(gain)
    def _fit(mapping_f, mapping_g):
        out={}
        for key, feats in mapping_f.items():
            if len(feats) < int(max(min_hits,1)):
                continue
            band=fit_support_band(feats,mapping_g[key],low_q=0.05,high_q=0.95,sim_q=0.15)
            if band is not None:
                out[str(key)] = band
        return out
    return _fit(pos_feats, pos_gains), _fit(neg_feats, neg_gains)


def calibrate_margin(rows: list[dict[str, Any]], pos_support: dict[str, SupportBand], neg_support: dict[str, SupportBand], *, slack: float) -> dict[str, float]:
    pos_margins=[]
    neg_margins=[]
    for row in rows:
        if str(row['auto_state']) != 'commit':
            continue
        feat = np.asarray(row['trace_feature'], dtype=np.float32)
        gain = float(row['future_gain'])
        pos_key, pos_sim = best_support_class(pos_support, feat, gain_hint=gain, slack=float(slack))
        neg_key, neg_sim = best_support_class(neg_support, feat, gain_hint=gain, slack=float(slack))
        margin = float(pos_sim - neg_sim)
        if gain > 0:
            pos_margins.append(margin)
        else:
            neg_margins.append(margin)
    return {
        'pass_margin': float(np.quantile(np.asarray(pos_margins, dtype=np.float32), 0.2)) if pos_margins else 0.0,
        'reject_margin': float(np.quantile(np.asarray(neg_margins, dtype=np.float32), 0.8)) if neg_margins else 0.0,
    }


def best_support_class(support: dict[str, SupportBand], feat: np.ndarray, *, gain_hint: float, slack: float) -> tuple[str, float]:
    best_key='uncertain|none'
    best_sim=-1.0
    for key, band in support.items():
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched and float(sim)>best_sim:
            best_key=str(key); best_sim=float(sim)
    return best_key, float(best_sim if best_sim>-1.0 else 0.0)


def macros_for_current(ctx: dict[str, Any], lag_teacher, *, max_macros: int) -> list[Any]:
    mode, bucket = class_parts(class_key(ctx))
    return macros_for_bucket(lag_teacher, mode, bucket, max_macros=int(max_macros))


def soft_downgrade_ctx(ctx: dict[str, Any], lag_teacher, *, max_macros: int, mode: str = 'candidate') -> dict[str, Any]:
    out = dict(ctx)
    current_key = class_key(ctx)
    mode_name, bucket = class_parts(current_key)
    rules = dict(out.get('rules', {}))
    if str(bucket) in rules and str(rules[str(bucket)]) == 'allowed':
        rules[str(bucket)] = 'discouraged'
    out['rules'] = rules
    out['macros'] = macros_for_bucket(lag_teacher, mode_name, bucket, max_macros=max(int(max_macros), 1))[:1]
    out['soft_mode'] = str(mode)
    return out


__all__ = [
    'AUTO_STATE_INDEX',
    'FrozenCX24Stack',
    'build_frozen_cx24_stack',
    'build_positive_negative_support',
    'best_support_class',
    'calibrate_margin',
    'compile_dto_rows',
    'compile_risk_hotspots',
    'compile_transition_hotspots',
    'load_frozen_ato_params',
    'load_frozen_ccc_params',
    'make_ato_policy',
    'make_ccc_policy',
    'macros_for_current',
    'policy_prepare',
    'soft_downgrade_ctx',
]
