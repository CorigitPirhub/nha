from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage

from rs_cx.common import normalize01
from rs_cx5.common import (
    accepted_bundle_nonholonomic,
    accepted_bundle_standard,
    narrow_opportunity_map,
    flange_opportunity_map,
    separator_opportunity_map,
)
from rs_cx4.common import misc_penalty_map, top_budget_mask
from rs_cx3.common import path_tube


def action_score_bank(bundle: dict[str, Any]) -> dict[str, np.ndarray]:
    return {
        'narrow': narrow_opportunity_map(bundle),
        'flange': flange_opportunity_map(bundle),
        'separator': separator_opportunity_map(bundle),
    }


def certificate_map(bundle: dict[str, Any], score: np.ndarray, misc_weight: float, uncertainty_weight: float, margin: float) -> np.ndarray:
    misc = misc_penalty_map(bundle)
    uncertainty = normalize01(0.6 * bundle['risk'] + 0.4 * bundle['morph_width'])
    cert = np.asarray(score, dtype=np.float32) - float(misc_weight) * misc - float(uncertainty_weight) * uncertainty - float(margin)
    return cert.astype(np.float32)


def culprit_replay_map(bundle: dict[str, Any]) -> np.ndarray:
    score = (0.55 * bundle['barrier'] + 0.30 * bundle['risk'] + 0.15 * bundle['morph_width']) * path_tube(bundle['path_dist'], radius_m=1.4)
    return normalize01(ndimage.gaussian_filter(score.astype(np.float32), sigma=1.0))


def scene_bin_key(scene: dict[str, float]) -> tuple[int, int, int]:
    hard = int(np.clip(np.floor(float(scene.get('hard_likelihood', 0.0)) * 3.0), 0, 2))
    misc = int(np.clip(np.floor(float(scene.get('misc_likelihood', 0.0)) * 3.0), 0, 2))
    bridge = int(np.clip(np.floor(float(scene.get('bridge_diffuse', 0.0)) * 3.0), 0, 2))
    return hard, misc, bridge


def group_head_key(scene: dict[str, float]) -> str:
    hard = float(scene.get('hard_likelihood', 0.0))
    misc = float(scene.get('misc_likelihood', 0.0))
    bridge = float(scene.get('bridge_diffuse', 0.0))
    if misc > hard:
        return 'protected'
    if bridge < 0.03:
        return 'narrow'
    if bridge < 0.08:
        return 'flange'
    return 'separator'


def resize_like(arr: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.shape == target_shape:
        return arr
    zoom = (float(target_shape[0]) / max(arr.shape[0], 1), float(target_shape[1]) / max(arr.shape[1], 1))
    resized = ndimage.zoom(arr, zoom=zoom, order=1).astype(np.float32)
    out = np.zeros(target_shape, dtype=np.float32)
    h = min(target_shape[0], resized.shape[0])
    w = min(target_shape[1], resized.shape[1])
    out[:h, :w] = resized[:h, :w]
    return out


__all__ = [
    'accepted_bundle_nonholonomic',
    'accepted_bundle_standard',
    'action_score_bank',
    'certificate_map',
    'culprit_replay_map',
    'group_head_key',
    'resize_like',
    'scene_bin_key',
    'top_budget_mask',
]
