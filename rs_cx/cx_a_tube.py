from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from rs_cx.common import (
    CXGlobalConfig,
    bottleneck_score,
    fuse_nonholonomic,
    local_std_map,
    nonholonomic_base_and_correction,
    normalize01,
    standard_base_and_correction,
    uncertainty_score,
)
from scripts.evaluate_baselines import _resolve_2d_heuristic


@dataclass(frozen=True)
class CXATubeParams:
    residual_alpha: float
    tube_open_gain: float
    tube_conservative_gain: float


def param_grid() -> list[CXATubeParams]:
    return [
        CXATubeParams(0.45, 0.25, 0.20),
        CXATubeParams(0.55, 0.25, 0.20),
        CXATubeParams(0.45, 0.35, 0.30),
        CXATubeParams(0.55, 0.35, 0.30),
    ]


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CXATubeParams) -> np.ndarray:
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(
        case,
        predictor,
        cfg,
        residual_alpha=float(params.residual_alpha),
        open_boost=0.0,
        corridor_suppress=cfg.residual_corridor_suppress,
    )
    u = uncertainty_score(corr3d, esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']))
    scale = 1.0 + float(params.tube_open_gain) * (1.0 - u) - float(params.tube_conservative_gain) * u
    scale = np.clip(scale, 0.55, 1.35).astype(np.float32)
    corr_mod = corr3d * scale[None, ...]
    return fuse_nonholonomic(rs_base, corr_mod, cfg.residual_floor_ratio)


def build_standard_field(sample, predictor, params: CXATubeParams) -> np.ndarray:
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    yaw_like = corr2d[None, ...]
    u = uncertainty_score(yaw_like, esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution))
    scale = 1.0 + float(params.tube_open_gain) * (1.0 - u) - float(params.tube_conservative_gain) * u
    scale = np.clip(scale, 0.55, 1.35).astype(np.float32)
    return (base + corr2d * scale).astype(np.float32)
