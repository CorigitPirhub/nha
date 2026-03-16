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
)


@dataclass(frozen=True)
class CXBBPFParams:
    residual_alpha: float
    progress_gain: float
    off_corridor_dampen: float


def param_grid() -> list[CXBBPFParams]:
    return [
        CXBBPFParams(0.45, 0.25, 0.10),
        CXBBPFParams(0.45, 0.40, 0.15),
        CXBBPFParams(0.55, 0.25, 0.10),
        CXBBPFParams(0.55, 0.40, 0.15),
    ]


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CXBBPFParams) -> np.ndarray:
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(params.residual_alpha))
    prog = bottleneck_score(esdf, (case['start'][0], case['start'][1]), (case['goal'][0], case['goal'][1]), float(case['resolution']), corridor_thr=1.2, line_sigma_m=2.4)
    scale = 1.0 + float(params.progress_gain) * prog - float(params.off_corridor_dampen) * (1.0 - prog)
    scale = np.clip(scale, 0.6, 1.5).astype(np.float32)
    corr_mod = corr3d * scale[None, ...]
    return fuse_nonholonomic(rs_base, corr_mod, cfg.residual_floor_ratio)


def build_standard_field(sample, predictor, params: CXBBPFParams) -> np.ndarray:
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    prog = bottleneck_score(esdf, (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), float(sample.resolution), corridor_thr=1.2, line_sigma_m=2.4)
    scale = 1.0 + float(params.progress_gain) * prog - float(params.off_corridor_dampen) * (1.0 - prog)
    scale = np.clip(scale, 0.6, 1.5).astype(np.float32)
    return (base + corr2d * scale).astype(np.float32)
