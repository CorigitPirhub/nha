from __future__ import annotations

import heapq
from typing import Any

import numpy as np
from scipy import ndimage

from rs_cx.common import normalize01
from rs_cx4.common import ACCEPTED_CX3D_PARAMS, accepted_cx3d_nonholonomic, accepted_cx3d_standard, hard_opportunity_map, misc_penalty_map, top_budget_mask
from rs_cx3.common import activation_mask, path_tube, scene_bundle_nonholonomic, scene_bundle_standard, scene_gate
from scripts.evaluate_baselines import _make_rs_anchor, _run_hybrid_method


def accepted_bundle_nonholonomic(case: dict[str, Any], predictor, cfg):
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return bundle, np.asarray(field, dtype=np.float32)


def accepted_bundle_standard(sample, predictor):
    bundle, field = accepted_cx3d_standard(sample, predictor)
    return bundle, np.asarray(field, dtype=np.float32)


def scene_reward_scale(scene: dict[str, float], margin: float = 0.0, sharpness: float = 10.0) -> float:
    hard = float(scene.get('hard_likelihood', 0.0))
    misc = float(scene.get('misc_likelihood', 0.0))
    z = float(sharpness) * (hard - misc - float(margin))
    return float(1.0 / (1.0 + np.exp(-z)))


def scene_cost_scale(scene: dict[str, float], margin: float = 0.0, sharpness: float = 10.0) -> float:
    hard = float(scene.get('hard_likelihood', 0.0))
    misc = float(scene.get('misc_likelihood', 0.0))
    z = float(sharpness) * (misc - hard - float(margin))
    return float(1.0 / (1.0 + np.exp(-z)))


def narrow_opportunity_map(bundle: dict[str, Any]) -> np.ndarray:
    bridge_low = np.clip(float(bundle['scene'].get('bridge_diffuse', 0.0)) - bundle['bridge'], 0.0, 1.0)
    path_open = float(bundle['scene'].get('path_openness', 1.0))
    penalty = max(0.0, min(1.0, 0.95 - path_open))
    score = (0.45 * bundle['barrier'] + 0.35 * bundle['morph_width'] + 0.20 * bundle['risk']) * (1.0 - 0.20 * bundle['corridor'])
    score = score * path_tube(bundle['path_dist'], radius_m=1.5) * (1.0 + penalty) * (1.0 + bridge_low)
    return normalize01(score)


def flange_opportunity_map(bundle: dict[str, Any]) -> np.ndarray:
    corridor = bundle['corridor']
    score = (0.35 * bundle['risk'] + 0.35 * corridor + 0.30 * bundle['focus']) * (1.0 - 0.5 * bundle['barrier'])
    score = score * path_tube(bundle['path_dist'], radius_m=2.0)
    return normalize01(score)


def separator_opportunity_map(bundle: dict[str, Any]) -> np.ndarray:
    score = (0.55 * bundle['barrier'] + 0.25 * bundle['risk'] + 0.20 * bundle['morph_width']) * (1.0 - 0.15 * bundle['corridor'])
    return normalize01(score)


def culprit_funnel_map(bundle: dict[str, Any], occupancy: np.ndarray) -> np.ndarray:
    score = narrow_opportunity_map(bundle)
    mask = activation_mask(score, occupancy, quantile=0.95, min_ratio=0.003, max_ratio=0.03)
    funnel = ndimage.gaussian_filter(mask.astype(np.float32), sigma=1.2)
    funnel *= path_tube(bundle['path_dist'], radius_m=1.8)
    return normalize01(funnel)


def sparse_action_atoms(bundle: dict[str, Any], occupancy: np.ndarray) -> list[dict[str, Any]]:
    atoms = []
    for name, score in [
        ('narrow', narrow_opportunity_map(bundle)),
        ('flange', flange_opportunity_map(bundle)),
        ('separator', separator_opportunity_map(bundle)),
    ]:
        mask = top_budget_mask(score, occupancy, budget_ratio=0.02, min_ratio=0.002, max_ratio=0.03)
        gain = float(np.mean(score[mask > 0])) if np.any(mask > 0) else 0.0
        cost = float(np.mean(misc_penalty_map(bundle)[mask > 0])) if np.any(mask > 0) else 0.0
        mass = float(np.mean(mask[~occupancy])) if np.any(~occupancy) else 0.0
        atoms.append({'name': name, 'mask': mask.astype(np.float32), 'score': score.astype(np.float32), 'gain': gain, 'cost': cost, 'mass': mass})
    return atoms


def knapsack_select(atoms: list[dict[str, Any]], misc_budget: float, max_atoms: int = 2) -> list[dict[str, Any]]:
    if not atoms:
        return []
    atoms = sorted(atoms, key=lambda a: (a['gain'] - a['cost'], a['gain']), reverse=True)
    chosen = []
    used = 0.0
    for atom in atoms:
        if len(chosen) >= int(max_atoms):
            break
        c = float(atom['cost']) + 0.5 * float(atom['mass'])
        if used + c > float(misc_budget):
            continue
        chosen.append(atom)
        used += c
    return chosen


def uplift_actions(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {'name': 'narrow', 'score': narrow_opportunity_map(bundle)},
        {'name': 'flange', 'score': flange_opportunity_map(bundle)},
        {'name': 'separator', 'score': separator_opportunity_map(bundle)},
    ]


def local_action_choice(bundle: dict[str, Any], occupancy: np.ndarray, beta: float, margin: float, budget_ratio: float) -> tuple[np.ndarray, np.ndarray]:
    actions = uplift_actions(bundle)
    scores = []
    misc = misc_penalty_map(bundle)
    for action in actions:
        uplift = action['score'] - float(beta) * misc - float(margin)
        scores.append(uplift.astype(np.float32))
    stack = np.stack(scores, axis=0)
    best_idx = np.argmax(stack, axis=0)
    best_score = np.max(stack, axis=0)
    best_pos = np.maximum(best_score, 0.0).astype(np.float32)
    mask = top_budget_mask(best_pos, occupancy, budget_ratio=budget_ratio, min_ratio=0.002, max_ratio=0.03)
    return best_idx.astype(np.int32), (best_pos * mask).astype(np.float32)


def dev_trace_memory(dev_cases: list[dict[str, Any]], predictor, cfg) -> dict[str, Any]:
    proto=[]
    for item in dev_cases:
        case=item['case']
        bundle,_ = accepted_bundle_nonholonomic(case, predictor, cfg)
        score = culprit_funnel_map(bundle, case['occupancy'])
        mass = float(np.mean(score[~case['occupancy']])) if np.any(~case['occupancy']) else 0.0
        proto.append({'scene': dict(bundle['scene']), 'funnel': score.astype(np.float32), 'mass': mass})
    return {'proto': proto}


def trace_similarity(bundle: dict[str, Any], proto_scene: dict[str, float]) -> float:
    s = bundle['scene']
    diff = abs(float(s.get('hard_likelihood', 0.0)) - float(proto_scene.get('hard_likelihood', 0.0)))
    diff += abs(float(s.get('misc_likelihood', 0.0)) - float(proto_scene.get('misc_likelihood', 0.0)))
    diff += abs(float(s.get('path_openness', 0.0)) - float(proto_scene.get('path_openness', 0.0)))
    return float(np.exp(-3.0 * diff))


__all__ = [
    'ACCEPTED_CX3D_PARAMS',
    'accepted_bundle_nonholonomic',
    'accepted_bundle_standard',
    'culprit_funnel_map',
    'dev_trace_memory',
    'flange_opportunity_map',
    'hard_opportunity_map',
    'knapsack_select',
    'local_action_choice',
    'misc_penalty_map',
    'narrow_opportunity_map',
    'scene_cost_scale',
    'scene_reward_scale',
    'separator_opportunity_map',
    'sparse_action_atoms',
    'trace_similarity',
    'uplift_actions',
]
