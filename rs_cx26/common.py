from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx24 import cx24_d_ccc as ccc_mod
from rs_cx24 import cx24_e_ato as ato_mod
from rs_cx25 import cx25_b_dto as dto_mod
from rs_cx25.common import FrozenCX24Stack, build_frozen_cx24_stack, soft_downgrade_ctx
from rs_cx24.common import trace_feature_vector
from rs_cx23.common import FAMILY_BUCKETS, apply_class_edit, class_key, class_parts, macros_for_bucket


FROZEN_DTO_CHOSEN = Path('outputs/rs_p0cx25_b_pilot_v1/chosen.json')

DTO_SCHEMA = (
    'occupancy_hotspot_score',
    'transition_hotspot_score',
    'false_commit_ledger_hit',
    'churn_score',
    'commit_recover_loop_score',
    'local_proxy_disagreement',
    'sibling_inconsistency',
    'tail_uncertainty',
)

WINDOWS = {
    'W_short': 8,
    'W_mid': 24,
    'W_long': 64,
}


@dataclass(frozen=True)
class FrozenCX25Stack:
    cx24_stack: FrozenCX24Stack
    dto_params: dto_mod.CX25BDTOParams
    dto_memory: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_frozen_dto_params(chosen_json: Path = FROZEN_DTO_CHOSEN) -> dto_mod.CX25BDTOParams:
    return dto_mod.CX25BDTOParams(**_load_json(chosen_json)['params'])


def build_frozen_cx25_stack(train_assets, val_assets, predictor, cfg, device: str, out_dir: Path, dependencies: dict[str, Any] | None = None) -> FrozenCX25Stack:
    if isinstance(dependencies, dict) and isinstance(dependencies.get('cx25_stack'), FrozenCX25Stack):
        return dependencies['cx25_stack']
    cx24_stack = build_frozen_cx24_stack(train_assets, val_assets, predictor, cfg, device, out_dir / 'cx24_cache', dependencies)
    dto_params = load_frozen_dto_params()
    dto_memory = dto_mod.fit_variant(train_assets, val_assets, predictor, cfg, dto_params, out_dir / 'dto_fit', device, {'cx24_stack': cx24_stack})
    return FrozenCX25Stack(cx24_stack=cx24_stack, dto_params=dto_params, dto_memory=dto_memory)


def make_dto_policy(stack: FrozenCX25Stack, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray):
    case['_cx21_bundle'] = bundle
    return dto_mod.make_policy(stack.dto_memory, stack.dto_params, case, bundle, field, 'cuda', ablation=None)


def make_ccc_policy(stack: FrozenCX25Stack, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray):
    case['_cx21_bundle'] = bundle
    return ccc_mod.make_policy(stack.cx24_stack.ccc_memory, stack.cx24_stack.ccc_params, case, bundle, field, 'cuda', ablation=None)


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


def dto_contract_meta() -> dict[str, Any]:
    return {
        'schema': list(DTO_SCHEMA),
        'windows': dict(WINDOWS),
        'normalization': {name: '[0,1]' for name in DTO_SCHEMA},
    }


def compile_dto_contract_rows(train_assets: list[dict[str, Any]], stack: FrozenCX25Stack, *, horizon_steps: int, stride: int = 1) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in train_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        policy = make_dto_policy(stack, case, bundle, field)
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        if path.shape[0] < 3:
            continue
        search_state: dict[str, Any] = {}
        prev_auto = 'observe'
        prev_key = 'uncertain|none'
        contexts = []
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
            feat = trace_feature_vector(ctx, ss, case, bundle)
            rows.append({
                'scenario': str(case['scenario']),
                'sample_name': str(asset['path'].name),
                'class_key': str(cur_key),
                'prev_class_key': str(prev_key),
                'auto_state': str(auto_state),
                'prev_auto_state': str(prev_auto),
                'transition': f'{prev_auto}->{auto_state}',
                'trace_feature': feat,
                'future_gain': float(gain),
                'support_count': int(ss.get('haa_support_count', 0)),
                'recover_left': int(ss.get('haa_recover_left', 0)),
                'macro_count': int(len(list(ctx.get('macros', [])))),
            })
    return rows


def _fit_support(rows: list[np.ndarray], gains: list[float], *, min_hits: int) -> SupportBand | None:
    if len(rows) < int(max(min_hits, 1)):
        return None
    return fit_support_band(rows, gains, low_q=0.05, high_q=0.95, sim_q=0.15)


def build_dto_compiler(rows: list[dict[str, Any]], *, min_hits: int) -> dict[str, Any]:
    class_group: dict[str, list[float]] = defaultdict(list)
    transition_group: dict[str, list[float]] = defaultdict(list)
    false_rows: dict[str, list[np.ndarray]] = defaultdict(list)
    false_gains: dict[str, list[float]] = defaultdict(list)
    pos_rows: dict[str, list[np.ndarray]] = defaultdict(list)
    pos_gains: dict[str, list[float]] = defaultdict(list)
    tail_rows: list[np.ndarray] = []
    tail_gains: list[float] = []
    for row in rows:
        key = str(row['class_key'])
        trans = str(row['transition'])
        gain = float(row['future_gain'])
        class_group[key].append(gain)
        transition_group[trans].append(gain)
        feat = np.asarray(row['trace_feature'], dtype=np.float32)
        if str(row['auto_state']) == 'commit':
            if gain <= 0.0:
                false_rows[key].append(feat)
                false_gains[key].append(gain)
            else:
                pos_rows[key].append(feat)
                pos_gains[key].append(gain)
        if str(row['scenario']) == 'parasol_misc' and gain <= 0.0:
            tail_rows.append(feat)
            tail_gains.append(gain)
    class_stats = {}
    for key, vals in class_group.items():
        arr = np.asarray(vals, dtype=np.float32)
        if int(arr.size) >= int(max(min_hits, 1)):
            class_stats[key] = {'hits': int(arr.size), 'avg_gain': float(np.mean(arr)), 'neg_rate': float(np.mean(arr <= 0.0))}
    transition_stats = {}
    for key, vals in transition_group.items():
        arr = np.asarray(vals, dtype=np.float32)
        if int(arr.size) >= int(max(min_hits, 1)):
            transition_stats[key] = {'hits': int(arr.size), 'avg_gain': float(np.mean(arr)), 'neg_rate': float(np.mean(arr <= 0.0))}
    false_ledger_classes = {k for k, v in class_stats.items() if float(v['neg_rate']) >= 0.5 and float(v['avg_gain']) <= 0.0}
    false_ledger_transitions = {k for k, v in transition_stats.items() if float(v['neg_rate']) >= 0.5 and float(v['avg_gain']) <= 0.0}
    pos_support = {k: _fit_support(v, pos_gains[k], min_hits=min_hits) for k, v in pos_rows.items()}
    pos_support = {k: v for k, v in pos_support.items() if v is not None}
    neg_support = {k: _fit_support(v, false_gains[k], min_hits=min_hits) for k, v in false_rows.items()}
    neg_support = {k: v for k, v in neg_support.items() if v is not None}
    tail_support = _fit_support(tail_rows, tail_gains, min_hits=min_hits)
    return {
        'contract': dto_contract_meta(),
        'class_stats': class_stats,
        'transition_stats': transition_stats,
        'false_ledger_classes': sorted(false_ledger_classes),
        'false_ledger_transitions': sorted(false_ledger_transitions),
        'pos_support': pos_support,
        'neg_support': neg_support,
        'tail_support': tail_support,
    }


def init_dto_episode(search_state: dict[str, Any]) -> None:
    search_state['dto_history_auto'] = []
    search_state['dto_history_class'] = []
    search_state['dto_review_count'] = 0
    search_state['dto_intervene_count'] = 0
    search_state['dto_prev_auto'] = 'observe'
    search_state['dto_prev_class'] = 'uncertain|none'


def complete_dto_episode(search_state: dict[str, Any], node_ctx: dict[str, Any] | None) -> None:
    auto = str(search_state.get('haa_state', 'observe'))
    key = str(class_key(node_ctx)) if isinstance(node_ctx, dict) else 'uncertain|none'
    for hist_key, value in [('dto_history_auto', auto), ('dto_history_class', key)]:
        hist = list(search_state.get(hist_key, []))
        hist.append(value)
        if len(hist) > int(WINDOWS['W_long']):
            hist = hist[-int(WINDOWS['W_long']):]
        search_state[hist_key] = hist
    search_state['dto_prev_auto'] = auto
    search_state['dto_prev_class'] = key


def _recent_ratio(history: list[str], target, window: int) -> float:
    if not history:
        return 0.0
    sub = history[-int(max(window, 1)):]
    if callable(target):
        return float(np.mean([1.0 if target(v) else 0.0 for v in sub]))
    return float(np.mean([1.0 if v == target else 0.0 for v in sub]))


def _best_support_sim(support: dict[str, SupportBand], feat: np.ndarray, *, gain_hint: float, slack: float) -> tuple[str, float]:
    best_key = 'uncertain|none'
    best_sim = -1.0
    for key, band in support.items():
        matched, sim = support_match(band, feat, float(gain_hint), slack=float(slack))
        if matched and float(sim) > best_sim:
            best_key = str(key)
            best_sim = float(sim)
    return best_key, float(best_sim if best_sim > -1.0 else 0.0)


def dto_evidence(compiler: dict[str, Any], ctx: dict[str, Any], search_state: dict[str, Any], case: dict[str, Any], bundle: dict[str, Any], *, support_slack: float = 0.2) -> dict[str, float]:
    key = str(class_key(ctx))
    prev_auto = str(search_state.get('dto_prev_auto', 'observe'))
    auto = str(search_state.get('haa_state', 'observe'))
    transition = f'{prev_auto}->{auto}'
    class_stats = dict(compiler.get('class_stats', {})).get(key, {})
    transition_stats = dict(compiler.get('transition_stats', {})).get(transition, {})
    feat = trace_feature_vector(ctx, search_state, case, bundle)
    gain_hint = float(ctx.get('oracle_gain', 0.0))
    _, pos_sim = _best_support_sim(dict(compiler.get('pos_support', {})), feat, gain_hint=gain_hint, slack=float(support_slack))
    _, neg_sim = _best_support_sim(dict(compiler.get('neg_support', {})), feat, gain_hint=gain_hint, slack=float(support_slack))
    tail_band = compiler.get('tail_support')
    tail_sim = 0.0
    if tail_band is not None:
        matched, sim = support_match(tail_band, feat, float(gain_hint), slack=float(support_slack))
        tail_sim = float(sim if matched else 0.0)
    auto_hist = list(search_state.get('dto_history_auto', []))
    class_hist = list(search_state.get('dto_history_class', []))
    churn_score = _recent_ratio(class_hist, lambda a: a != key, WINDOWS['W_short'])
    loop_score = 0.0
    if auto_hist:
        recent_pairs = list(zip(auto_hist[-int(WINDOWS['W_mid'])-1:-1], auto_hist[-int(WINDOWS['W_mid']):]))
        if recent_pairs:
            loop_score = float(np.mean([1.0 if (a == 'commit' and b == 'recover') else 0.0 for a, b in recent_pairs]))
    local_proxy_disagreement = float(np.clip(0.5 + 0.5 * (neg_sim - pos_sim), 0.0, 1.0))
    sibling_inconsistency = float(np.clip(max(0.0, neg_sim - pos_sim), 0.0, 1.0))
    tail_uncertainty = float(np.clip(max(tail_sim, 1.0 - max(pos_sim, neg_sim, 0.0)), 0.0, 1.0))
    return {
        'occupancy_hotspot_score': float(np.clip(class_stats.get('neg_rate', 0.0), 0.0, 1.0)),
        'transition_hotspot_score': float(np.clip(transition_stats.get('neg_rate', 0.0), 0.0, 1.0)),
        'false_commit_ledger_hit': 1.0 if key in set(compiler.get('false_ledger_classes', [])) or transition in set(compiler.get('false_ledger_transitions', [])) else 0.0,
        'churn_score': float(np.clip(churn_score, 0.0, 1.0)),
        'commit_recover_loop_score': float(np.clip(loop_score, 0.0, 1.0)),
        'local_proxy_disagreement': float(np.clip(local_proxy_disagreement, 0.0, 1.0)),
        'sibling_inconsistency': float(np.clip(sibling_inconsistency, 0.0, 1.0)),
        'tail_uncertainty': float(np.clip(tail_uncertainty, 0.0, 1.0)),
        'current_class_key': key,
        'current_transition': transition,
    }


def macro_proxy_score(case, planner, record, h_pair, lag_teacher, current_key: str, *, max_macros: int) -> tuple[float, str, float]:
    mode, bucket = class_parts(current_key)
    current_macros = macros_for_bucket(lag_teacher, mode, bucket, max_macros=int(max_macros))
    def _score(macros):
        if not macros:
            return float('-inf')
        cands = ccc_mod.base_mod.lag_mod.macro_successor_candidates(case, planner, record, h_pair, macros, max_macros=len(macros))
        if not cands:
            return float('-inf')
        here = float(record.g + record.guided)
        return max(float(here - (record.g + float(c.guided))) for c in cands)
    commit_score = float(_score(current_macros))
    siblings = [b for b in FAMILY_BUCKETS if b != str(bucket)]
    best_sib = 'none'
    best_sib_score = float('-inf')
    for sib in siblings:
        score = float(_score(macros_for_bucket(lag_teacher, mode, sib, max_macros=int(max_macros))))
        if score > best_sib_score:
            best_sib = str(sib)
            best_sib_score = score
    return commit_score, best_sib, best_sib_score


class DTOObservabilityMixin:
    def _dto_diag_init(self) -> None:
        self._diag_rows: list[dict[str, Any]] = []

    def _dto_diag_record(self, record, search_state: dict[str, Any], ctx: dict[str, Any], evidence: dict[str, Any]) -> None:
        row = {
            'x': float(record.x),
            'y': float(record.y),
            'yaw': float(record.yaw),
            'auto_state': str(search_state.get('haa_state', 'observe')),
            'class_key': str(class_key(ctx)),
        }
        row.update({k: float(v) if isinstance(v, (int, float, np.floating)) else v for k, v in evidence.items()})
        self._diag_rows.append(row)

    def export_diagnostics(self) -> list[dict[str, Any]]:
        return list(getattr(self, '_diag_rows', []))


__all__ = [
    'DTOObservabilityMixin',
    'DTO_SCHEMA',
    'FrozenCX25Stack',
    'WINDOWS',
    'build_dto_compiler',
    'build_frozen_cx25_stack',
    'complete_dto_episode',
    'dto_contract_meta',
    'dto_evidence',
    'init_dto_episode',
    'load_frozen_dto_params',
    'macro_proxy_score',
    'make_ccc_policy',
    'make_dto_policy',
    'policy_prepare',
    'soft_downgrade_ctx',
]
