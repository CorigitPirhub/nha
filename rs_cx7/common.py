from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage

from rs_cx.common import normalize01
from rs_cx6.common import accepted_bundle_nonholonomic, accepted_bundle_standard, action_score_bank, certificate_map, culprit_replay_map, group_head_key, resize_like, scene_bin_key
from rs_cx4.common import misc_penalty_map, top_budget_mask
from rs_cx3.common import activation_mask


def evidence_bank(bundle: dict[str, Any], occupancy: np.ndarray) -> dict[str, np.ndarray]:
    actions = action_score_bank(bundle)
    misc = misc_penalty_map(bundle)
    uncertainty = normalize01(0.6 * bundle['risk'] + 0.4 * bundle['morph_width'])
    support = activation_mask(actions['narrow'] + actions['separator'], occupancy, quantile=0.94, min_ratio=0.003, max_ratio=0.04)
    return {
        'narrow': actions['narrow'],
        'flange': actions['flange'],
        'separator': actions['separator'],
        'misc': misc,
        'uncertainty': uncertainty,
        'support': support.astype(np.float32),
    }


def evidence_accumulation_map(bundle: dict[str, Any], occupancy: np.ndarray, misc_w: float, uncert_w: float, support_w: float, margin: float) -> np.ndarray:
    bank = evidence_bank(bundle, occupancy)
    raw = 0.55 * bank['narrow'] + 0.25 * bank['separator'] + 0.20 * bank['flange']
    raw = raw - float(misc_w) * bank['misc'] - float(uncert_w) * bank['uncertainty'] + float(support_w) * bank['support'] - float(margin)
    return raw.astype(np.float32)


def duel_choice(bundle: dict[str, Any], occupancy: np.ndarray, misc_w: float, margin: float, budget_ratio: float) -> tuple[np.ndarray, np.ndarray]:
    actions = action_score_bank(bundle)
    misc = misc_penalty_map(bundle)
    scores = []
    for _, score in actions.items():
        duel = score - float(misc_w) * misc - float(margin)
        scores.append(duel.astype(np.float32))
    stack = np.stack(scores, axis=0)
    best_idx = np.argmax(stack, axis=0)
    best_score = np.max(stack, axis=0)
    best_pos = np.maximum(best_score, 0.0).astype(np.float32)
    mask = top_budget_mask(best_pos, occupancy, budget_ratio, min_ratio=0.002, max_ratio=0.03)
    return best_idx.astype(np.int32), (best_pos * mask).astype(np.float32)


def omnipredictive_representation(bundle: dict[str, Any], occupancy: np.ndarray) -> dict[str, np.ndarray]:
    bank = evidence_bank(bundle, occupancy)
    shared = normalize01(0.35 * bank['narrow'] + 0.25 * bank['separator'] + 0.15 * bank['flange'] + 0.15 * bank['support'] - 0.10 * bank['misc'])
    return {
        'shared': shared.astype(np.float32),
        'gain': normalize01(shared * (1.0 - 0.35 * bank['misc'])).astype(np.float32),
        'cost': normalize01(bank['misc'] + 0.5 * bank['uncertainty']).astype(np.float32),
        'support': bank['support'].astype(np.float32),
    }


def decoupled_specialist_memory(dev_cases: list[dict[str, Any]], predictor, cfg) -> dict[str, Any]:
    proto = {'protected': [], 'narrow': [], 'flange': [], 'separator': []}
    for item in dev_cases:
        bundle, _ = accepted_bundle_nonholonomic(item['case'], predictor, cfg)
        key = group_head_key(bundle['scene'])
        acts = action_score_bank(bundle)
        if key == 'narrow':
            head = acts['narrow']
        elif key == 'flange':
            head = acts['flange']
        elif key == 'separator':
            head = acts['separator']
        else:
            head = np.zeros_like(bundle['focus'], dtype=np.float32)
        proto[key].append(head.astype(np.float32))
    out = {}
    for key, vals in proto.items():
        out[key] = np.mean(np.stack(vals, axis=0), axis=0).astype(np.float32) if vals else None
    return {'proto': out}


def arbitration_score(bundle: dict[str, Any], margin: float) -> float:
    hard = float(bundle['scene'].get('hard_likelihood', 0.0))
    misc = float(bundle['scene'].get('misc_likelihood', 0.0))
    z = 10.0 * (hard - misc - float(margin))
    return float(1.0 / (1.0 + np.exp(-z)))


__all__ = [
    'accepted_bundle_nonholonomic',
    'accepted_bundle_standard',
    'arbitration_score',
    'decoupled_specialist_memory',
    'duel_choice',
    'evidence_accumulation_map',
    'evidence_bank',
    'omnipredictive_representation',
    'resize_like',
    'scene_bin_key',
    'top_budget_mask',
]
