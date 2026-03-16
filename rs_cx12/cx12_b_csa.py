from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx10 import cx10_d_las
from rs_cx12.common import (
    BASE_CHOSEN_JSON,
    GEOM_FEATURE_NAMES,
    compare_plan_to_baseline,
    fit_geom_tree,
    geom_tree_dict,
    load_base_params,
    run_hybrid_with_policy,
    scene_context,
    signed_mode_delta,
    tree_prob,
)


@dataclass(frozen=True)
class CX12BCSAParams:
    positive_gain: float
    negative_loss: float
    pos_depth: int
    neg_depth: int
    pos_threshold: float
    neg_threshold: float
    positive_strength: float
    negative_strength: float


def param_grid() -> list[CX12BCSAParams]:
    return [
        CX12BCSAParams(50.0, 50.0, 2, 2, 0.45, 0.45, 0.25, 0.18),
        CX12BCSAParams(100.0, 50.0, 2, 2, 0.40, 0.40, 0.24, 0.20),
        CX12BCSAParams(150.0, 100.0, 3, 3, 0.35, 0.35, 0.26, 0.22),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'Positive-Only', 'disable_negative': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX12BCSAParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    deps = dependencies or {}
    guard_assets = list(deps.get('guard_assets', []))
    base_memory = deps['base_memory']
    base_params = deps.get('base_params', load_base_params(BASE_CHOSEN_JSON))
    pos_rows = []
    neg_rows = []
    for asset in guard_assets:
        ctx = scene_context(base_memory, base_params, asset['case'], asset['bundle'], asset['field'], device)
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(deps.get('dev_cap', 20000)), successor_policy=ctx['base_policy'], record_expanded=False) if ctx['base_policy'] is not None else asset['baseline_result']
        delta = compare_plan_to_baseline(asset['baseline_result'], plan, prep_ms=0.0)
        if str(asset['case']['scenario']) == 'narrow_passage' and float(delta['exp_delta']) >= float(params.positive_gain):
            pos_rows.append(np.asarray(ctx['geom_feature'], dtype=np.float32))
        if str(asset['case']['scenario']) == 'flange' and float(delta['exp_delta']) <= -float(params.negative_loss):
            neg_rows.append(np.asarray(ctx['geom_feature'], dtype=np.float32))
    x_pos = np.stack(pos_rows, axis=0) if pos_rows else np.zeros((2, len(GEOM_FEATURE_NAMES)), dtype=np.float32)
    y_pos = np.ones((x_pos.shape[0],), dtype=np.int64) if pos_rows else np.asarray([0, 0], dtype=np.int64)
    x_neg = np.stack(neg_rows, axis=0) if neg_rows else np.zeros((2, len(GEOM_FEATURE_NAMES)), dtype=np.float32)
    y_neg = np.ones((x_neg.shape[0],), dtype=np.int64) if neg_rows else np.asarray([0, 0], dtype=np.int64)
    pos_tree = fit_geom_tree(x_pos, y_pos, int(params.pos_depth))
    neg_tree = fit_geom_tree(x_neg, y_neg, int(params.neg_depth))
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'positive_rows': int(len(pos_rows)),
        'negative_rows': int(len(neg_rows)),
        'feature_names': list(GEOM_FEATURE_NAMES),
        'pos_tree': geom_tree_dict(pos_tree),
        'neg_tree': geom_tree_dict(neg_tree),
        'base_params': asdict(base_params),
    }
    (out_dir / 'csa_meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return {
        'pos_tree': pos_tree,
        'neg_tree': neg_tree,
        'train_rows': int(len(pos_rows) + len(neg_rows)),
        'base_memory': base_memory,
        'base_params': base_params,
        'best_val_loss': float('nan'),
    }


class CSAPolicy:
    def __init__(self, case: dict[str, Any], delegate, params: CX12BCSAParams, mode: int, sign: float) -> None:
        self.case = case
        self.delegate = delegate
        self.params = params
        self.mode = int(mode)
        self.sign = float(sign)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        if self.delegate is not None:
            ctx = self.delegate.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
            if isinstance(ctx, dict):
                ctx = dict(ctx)
                ctx['contrastive_mode'] = int(self.mode)
                ctx['contrastive_sign'] = float(self.sign)
                return ctx
        return {'contrastive_mode': int(self.mode), 'contrastive_sign': float(self.sign)}

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        contrast_mode = int(node_ctx.get('contrastive_mode', 0)) if isinstance(node_ctx, dict) else int(self.mode)
        sign = float(node_ctx.get('contrastive_sign', self.sign)) if isinstance(node_ctx, dict) else float(self.sign)
        ranked = []
        for cand in candidates:
            strength = float(self.params.positive_strength if sign < 0 else self.params.negative_strength)
            delta = signed_mode_delta(self.case, int(cand.primitive_index), int(contrast_mode), float(strength), float(sign))
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX12BCSAParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ctx = scene_context(memory['base_memory'], memory['base_params'], case, bundle, field, device)
    if ctx['top_gate'] is None:
        return None
    feat = np.asarray(ctx['geom_feature'], dtype=np.float32)
    pos_prob = float(tree_prob(memory['pos_tree'], feat))
    neg_prob = float(tree_prob(memory['neg_tree'], feat))
    if pos_prob >= float(params.pos_threshold):
        return ctx['base_policy']
    if isinstance(ablation, dict) and bool(ablation.get('disable_negative', False)):
        return None
    if neg_prob >= float(params.neg_threshold):
        return CSAPolicy(case, None, params, int(ctx['top_gate'].get('inner_mode', 0)), sign=1.0)
    return None


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX12BCSAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_nonholonomic_field(case, predictor, cfg, memory['base_params'] if memory else load_base_params(BASE_CHOSEN_JSON), memory['base_memory'] if memory else None)


def build_standard_field(sample, predictor, params: CX12BCSAParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx10_d_las.build_standard_field(sample, predictor, memory['base_params'] if memory else load_base_params(BASE_CHOSEN_JSON), memory['base_memory'] if memory else None)
