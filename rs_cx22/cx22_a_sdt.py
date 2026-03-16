from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx21.common import FAMILY_BUCKETS, consistency_score, family_bucket_name, foundation_state
from rs_cx22.common import (
    FEATURE_NAMES,
    MODE_INDEX,
    TreeNode,
    build_frozen_teacher,
    compile_teacher_state_rows,
    fit_tree,
    make_teacher_policy,
    predict_tree,
    state_feature_vector,
    teacher_prepare,
    tree_to_dict,
)
from rs_cx21 import cx21_b_lag as lag_mod


MODES = ('forward_safe', 'reverse_setup', 'escape_border')


@dataclass(frozen=True)
class CX22ASDTParams:
    max_depth: int
    mode_prob_thr: float
    allowed_bonus: float
    discouraged_penalty: float
    forbidden_penalty: float
    macro_bonus: float
    must_precede_bonus: float
    improve_gain: float
    max_macros: int
    step_stride: int


def param_grid() -> list[CX22ASDTParams]:
    return [
        CX22ASDTParams(2, 0.55, 0.08, 0.05, 0.08, 0.06, 0.08, 0.12, 2, 2),
        CX22ASDTParams(3, 0.50, 0.10, 0.06, 0.10, 0.08, 0.10, 0.14, 3, 2),
        CX22ASDTParams(3, 0.45, 0.12, 0.08, 0.12, 0.08, 0.12, 0.16, 3, 1),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [{'name': 'No-Tree', 'disable_tree': True}]


def _fixed_rules(mode: str) -> tuple[dict[str, str], bool]:
    rules = {bucket: 'discouraged' for bucket in FAMILY_BUCKETS}
    must_precede = False
    if mode == 'forward_safe':
        rules['straight'] = 'allowed'
        rules['forward_turn'] = 'allowed'
        rules['reverse'] = 'discouraged'
        rules['reverse_setup'] = 'discouraged'
    elif mode == 'reverse_setup':
        rules['reverse'] = 'allowed'
        rules['reverse_setup'] = 'allowed'
        rules['forward_turn'] = 'discouraged'
        rules['straight'] = 'forbidden'
        must_precede = True
    elif mode == 'escape_border':
        rules['reverse'] = 'allowed'
        rules['reverse_setup'] = 'allowed'
        rules['forward_turn'] = 'discouraged'
        rules['straight'] = 'forbidden'
    return rules, must_precede


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX22ASDTParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = build_frozen_teacher(calib_train_assets, calib_val_assets, predictor, cfg, device, out_dir, dependencies)
    rows = compile_teacher_state_rows(calib_train_assets, teacher, horizon_steps=int(teacher.params.horizon_steps), stride=int(params.step_stride))
    x = np.stack([np.asarray(r['feature'], dtype=np.float32) for r in rows], axis=0)
    trees: dict[str, TreeNode] = {}
    for mode in MODES:
        y = np.asarray([1 if str(r['mode']) == mode else 0 for r in rows], dtype=np.int64)
        trees[mode] = fit_tree(x, y, max_depth=int(params.max_depth))
    macros = list(teacher.memory.get('macros', []))
    mode_macros = {
        'forward_safe': [macro for macro in macros if family_bucket_name(str(macro.family)) in {'straight', 'forward_turn'}][: int(params.max_macros)],
        'reverse_setup': [macro for macro in macros if family_bucket_name(str(macro.family)) in {'reverse', 'reverse_setup'}][: int(params.max_macros)],
        'escape_border': [macro for macro in macros if family_bucket_name(str(macro.family)) in {'reverse', 'reverse_setup', 'forward_turn'}][: int(params.max_macros)],
    }
    lag_mod.save_meta(
        out_dir / 'sdt_meta.json',
        {
            'params': params.__dict__,
            'feature_names': FEATURE_NAMES,
            'trees': {mode: tree_to_dict(tree, FEATURE_NAMES) for mode, tree in trees.items()},
            'mode_macros': {mode: [m.name for m in items] for mode, items in mode_macros.items()},
        },
    )
    return {'teacher': teacher, 'trees': trees, 'mode_macros': mode_macros, 'best_val_loss': float('nan')}


class SDTPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX22ASDTParams, memory: dict[str, Any], disable_tree: bool = False) -> None:
        self.case = case
        self.bundle = bundle
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_tree = bool(disable_tree)
        self.teacher = memory['teacher']
        self.inner = make_teacher_policy(self.teacher, case, bundle, self.field)
        self.trees = dict(memory.get('trees', {}))
        self.mode_macros = dict(memory.get('mode_macros', {}))

    def _predict_mode(self, feat: np.ndarray) -> str:
        probs = {mode: float(predict_tree(tree, feat)) for mode, tree in self.trees.items()}
        mode, prob = max(probs.items(), key=lambda item: item[1])
        return str(mode) if float(prob) >= float(self.params.mode_prob_thr) else 'uncertain'

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        if self.disable_tree:
            return self.inner.prepare_expand(planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair)
        ctx = teacher_prepare(self.inner, (float(record.x), float(record.y), float(record.yaw)))
        feat = state_feature_vector(ctx)
        mode = self._predict_mode(feat)
        rules, must_precede = _fixed_rules(mode)
        macros = list(self.mode_macros.get(mode, [])) if mode in self.mode_macros else []
        conf = {bucket: (1.0 if str(rules.get(bucket, 'discouraged')) == 'allowed' else 0.0) for bucket in FAMILY_BUCKETS}
        ctx.update({
            'mode': str(mode),
            'rules': rules,
            'conf': conf,
            'must_precede': bool(must_precede),
            'macros': macros,
        })
        return ctx

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        return self.inner.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if self.disable_tree:
            return self.inner.rank_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict):
            return None
        current = node_ctx.get('foundation')
        if current is None:
            return None
        rules = dict(node_ctx.get('rules', {}))
        must_precede = bool(node_ctx.get('must_precede', False))
        current_cost = float(current.cost_to_go)
        current_viability = float(current.viability)
        ranked = []
        for cand in candidates:
            fam_bucket = family_bucket_name(lag_mod.macro_family(cand))
            label = str(rules.get(fam_bucket, 'discouraged'))
            nf = foundation_state(self.case, self.case.get('_cx21_bundle', {}), self.field, self.inner.encoder, cand.next_state, self.inner.spec)
            cons = float(consistency_score(nf))
            delta = 0.0
            delta += float(self.params.improve_gain) * float(nf.cost_to_go - current_cost)
            delta -= 0.04 * float(nf.viability - current_viability)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            if label == 'allowed':
                delta -= float(self.params.allowed_bonus) * float(cons)
            elif label == 'discouraged':
                delta += float(self.params.discouraged_penalty) * float(cons)
            elif label == 'forbidden':
                delta += float(self.params.forbidden_penalty) * float(cons)
            if must_precede:
                if fam_bucket in {'reverse', 'reverse_setup'} and int(cand.direction) < 0:
                    delta -= float(self.params.must_precede_bonus)
                elif fam_bucket in {'straight', 'forward_turn'} and int(cand.direction) > 0:
                    delta += float(self.params.must_precede_bonus)
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX22ASDTParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return SDTPolicy(case, bundle, field, params, memory, disable_tree=bool(ablation.get('disable_tree', False)))


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX22ASDTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    field = lag_mod.build_nonholonomic_field(case, predictor, cfg, memory['teacher'].params, memory['teacher'].memory)
    return np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor, params: CX22ASDTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return lag_mod.build_standard_field(sample, predictor, memory['teacher'].params, memory['teacher'].memory).astype(np.float32)
