from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import DEFAULT_CONFIG
from rs_cx5.common import accepted_bundle_nonholonomic, accepted_bundle_standard, knapsack_select, scene_reward_scale, sparse_action_atoms


@dataclass(frozen=True)
class CX5CPAAParams:
    misc_budget: float
    max_atoms: int
    gain: float


def param_grid() -> list[CX5CPAAParams]:
    return [
        CX5CPAAParams(0.06, 1, 0.90),
        CX5CPAAParams(0.08, 2, 1.00),
        CX5CPAAParams(0.10, 2, 1.10),
        CX5CPAAParams(0.12, 3, 1.15),
    ]


def _delta(bundle: dict, occupancy: np.ndarray, params: CX5CPAAParams) -> np.ndarray:
    atoms = sparse_action_atoms(bundle, occupancy)
    chosen = knapsack_select(atoms, misc_budget=float(params.misc_budget), max_atoms=int(params.max_atoms))
    if not chosen:
        return np.zeros_like(bundle['focus'], dtype=np.float32)
    reward = scene_reward_scale(bundle['scene'], margin=0.02, sharpness=10.0)
    out = np.zeros_like(bundle['focus'], dtype=np.float32)
    for atom in chosen:
        out += atom['mask'] * atom['score']
    return float(params.gain) * reward * out


def build_nonholonomic_field(case: dict, predictor, cfg, params: CX5CPAAParams) -> np.ndarray:
    bundle, field = accepted_bundle_nonholonomic(case, predictor, cfg)
    delta = _delta(bundle, case['occupancy'], params)
    out = np.clip(field + delta[None, ...], 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    return out


def build_standard_field(sample, predictor, params: CX5CPAAParams) -> np.ndarray:
    bundle, field = accepted_bundle_standard(sample, predictor)
    delta = _delta(bundle, sample.occupancy, params)
    out = np.clip(field + delta, 0.0, float(DEFAULT_CONFIG.dataset.max_teacher_value)).astype(np.float32)
    out[sample.occupancy] = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    return out
