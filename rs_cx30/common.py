from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from planner.hybrid_astar import HybridAStarPlanner
from rs_cx11.common import fit_tree, predict_tree, tree_to_dict
from rs_cx28.common import BaseCX28Policy, CX27WatchdogConfig, build_frozen_haa_stack, misc_blocked, set_class_block
from rs_cx29.common import rollout_score
from rs_cx8.common import load_nonholonomic_contexts
from scripts.evaluate_baselines import _load_nonholonomic_case


AUX_DEV_ROOT = Path('data/benchmark/rs_root_hard_v2/dev')
PARENT_CHOSEN = Path('outputs/rs_p0cx29_d_pilot_v1/chosen.json')
AUX_FEATURE_NAMES = (
    'bridge_diffuse',
    'path_openness',
    'focus_gap',
    'hard_likelihood',
    'misc_likelihood',
    'openness',
    'barrier_peak',
    'reverse_required',
    'trap',
    'corridor',
    'class_churn',
    'loop_rate',
)


def load_parent_params():
    import rs_cx29.cx29_d_abc as parent_mod

    return parent_mod.CX29DABCParams(**json.loads(PARENT_CHOSEN.read_text(encoding='utf-8'))['params'])


def aux_misc_paths() -> list[Path]:
    out = []
    for path in sorted(AUX_DEV_ROOT.glob('sample_*.npz')):
        try:
            if str(_load_nonholonomic_case(path).get('scenario', '')) == 'parasol_misc':
                out.append(path)
        except Exception:
            continue
    return out


def scene_feature_vector(bundle: dict[str, Any]) -> np.ndarray:
    scene = dict(bundle.get('scene', {}))
    return np.asarray([
        float(scene.get('bridge_diffuse', 0.0)),
        float(scene.get('path_openness', 0.0)),
        float(scene.get('focus_gap', 0.0)),
        float(scene.get('hard_likelihood', 0.0)),
        float(scene.get('misc_likelihood', 0.0)),
        float(scene.get('openness', 0.0)),
        float(scene.get('barrier_peak', 0.0)),
    ], dtype=np.float32)


def trigger_feature_vector(bundle: dict[str, Any], ctx: dict[str, Any], evidence: dict[str, Any]) -> np.ndarray:
    foundation = ctx.get('foundation')
    scene = scene_feature_vector(bundle)
    return np.concatenate([
        scene,
        np.asarray([
            float(getattr(foundation, 'reverse_required', 0.0) if foundation is not None else 0.0),
            float(getattr(foundation, 'trap', 0.0) if foundation is not None else 0.0),
            float(getattr(foundation, 'corridor', 0.0) if foundation is not None else 0.0),
            float(evidence.get('class_churn', 0.0)),
            float(evidence.get('loop_rate', 0.0)),
        ], dtype=np.float32),
    ], axis=0).astype(np.float32)


def simple_zero_h_pair():
    return lambda x, y, yaw: (0.0, 0.0)


def planner_for_case(case: dict[str, Any]) -> HybridAStarPlanner:
    return HybridAStarPlanner(case['occupancy'], float(case['resolution']), case['vehicle'], case['planner_cfg'], case['esdf'])


@dataclass(frozen=True)
class AuxTreeModel:
    tree: Any
    threshold: float
    samples: int


def compile_aux_trigger_tree(aux_assets: list[dict[str, Any]], parent_policy_factory, teacher, parent_memory: dict[str, Any], *, max_depth: int, gain_margin: float) -> AuxTreeModel | None:
    rows_x = []
    rows_y = []
    parent_params = load_parent_params()
    for asset in aux_assets:
        case = asset['case']
        bundle = asset['bundle']
        field = np.asarray(asset['field'], dtype=np.float32)
        parent_policy = parent_policy_factory(parent_memory, parent_params, case, bundle, field, 'cuda', ablation=None)
        parent_plan = asset.get('baseline_result')
        if parent_plan is None:
            continue
        search_state: dict[str, Any] = {}
        if hasattr(parent_policy, 'start_search'):
            parent_policy.start_search(None, tuple(case['start']), tuple(case['goal']), simple_zero_h_pair(), search_state)
        planner = planner_for_case(case)
        h_pair = simple_zero_h_pair()
        for state in np.asarray(parent_plan.path, dtype=np.float32):
            rec = SimpleNamespace(
                x=float(state[0]),
                y=float(state[1]),
                yaw=float(state[2]),
                g=0.0,
                guided=0.0,
                anchor=0.0,
                steer=0.0,
                direction=1,
            )
            ctx = parent_policy.prepare_expand(planner, rec, tuple(case['goal']), {}, [], [], search_state, h_pair)
            if not isinstance(ctx, dict):
                continue
            if str(ctx.get('mode', '')) != 'forward_safe':
                continue
            allowed = [bucket for bucket, label in dict(ctx.get('rules', {})).items() if str(label) == 'allowed']
            if 'straight' not in allowed:
                continue
            evidence = {'class_churn': float(search_state.get('cx27_recent_failures', 0) > 0), 'loop_rate': float(search_state.get('cx27_last_commit_failed', False))}
            feat = trigger_feature_vector(bundle, ctx, evidence)
            current_score = rollout_score(case, field, planner, rec, h_pair, teacher.shadow_teacher.lag_teacher, 'forward_safe|straight', max_macros=int(teacher.params.max_macros), depth=2, discount=0.85)
            turn_score = rollout_score(case, field, planner, rec, h_pair, teacher.shadow_teacher.lag_teacher, 'forward_safe|forward_turn', max_macros=int(teacher.params.max_macros), depth=2, discount=0.85)
            rows_x.append(feat)
            rows_y.append(1.0 if float(turn_score) > float(current_score) + float(gain_margin) else 0.0)
    if len(rows_x) < 8:
        return None
    x = np.asarray(rows_x, dtype=np.float32)
    y = np.asarray(rows_y, dtype=np.float32)
    tree = fit_tree(x, y, max_depth=int(max_depth))
    threshold = 0.5
    return AuxTreeModel(tree=tree, threshold=float(threshold), samples=int(len(rows_x)))


__all__ = [
    'AUX_DEV_ROOT',
    'AUX_FEATURE_NAMES',
    'AuxTreeModel',
    'BaseCX28Policy',
    'CX27WatchdogConfig',
    'aux_misc_paths',
    'build_frozen_haa_stack',
    'compile_aux_trigger_tree',
    'load_parent_params',
    'misc_blocked',
    'planner_for_case',
    'predict_tree',
    'scene_feature_vector',
    'set_class_block',
    'simple_zero_h_pair',
    'trigger_feature_vector',
    'tree_to_dict',
]
