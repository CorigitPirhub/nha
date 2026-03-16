from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from rs_cx.common import (
    CXGlobalConfig,
    bottleneck_score,
    fuse_nonholonomic,
    nonholonomic_base_and_correction,
    standard_base_and_correction,
    uncertainty_score,
)


@dataclass(frozen=True)
class CXCDVPParams:
    residual_alpha: float
    effort_gain: float
    safe_dampen: float


def param_grid() -> list[CXCDVPParams]:
    return [
        CXCDVPParams(0.45, 0.25, 0.20),
        CXCDVPParams(0.45, 0.35, 0.30),
        CXCDVPParams(0.55, 0.25, 0.20),
        CXCDVPParams(0.55, 0.35, 0.30),
    ]


def _blend_map(corr3d: np.ndarray, esdf: np.ndarray, start_xy, goal_xy, resolution: float, effort_gain: float, safe_dampen: float) -> np.ndarray:
    u = uncertainty_score(corr3d, esdf, start_xy, goal_xy, resolution)
    prog = bottleneck_score(esdf, start_xy, goal_xy, resolution, corridor_thr=1.1, line_sigma_m=2.2)
    effort = np.clip(1.0 + float(effort_gain) * (1.0 - u), 0.8, 1.4)
    safe = np.clip(1.0 - float(safe_dampen) * u, 0.55, 1.0)
    gate = np.clip(prog, 0.0, 1.0)
    return (gate * safe + (1.0 - gate) * effort).astype(np.float32)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CXCDVPParams) -> np.ndarray:
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(params.residual_alpha))
    blend = _blend_map(corr3d, esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), params.effort_gain, params.safe_dampen)
    return fuse_nonholonomic(rs_base, corr3d * blend[None, ...], cfg.residual_floor_ratio)


def build_standard_field(sample, predictor, params: CXCDVPParams) -> np.ndarray:
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    blend = _blend_map(corr2d[None, ...], esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), params.effort_gain, params.safe_dampen)
    return (base + corr2d * blend).astype(np.float32)
