from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import ndimage
from sklearn.cluster import KMeans

from rs_cx.common import (
    CXGlobalConfig,
    fuse_nonholonomic,
    local_std_map,
    nonholonomic_base_and_correction,
    standard_base_and_correction,
)


@dataclass(frozen=True)
class CXDPMFParams:
    residual_alpha: float
    n_proto: int
    mix_ratio: float


def param_grid() -> list[CXDPMFParams]:
    return [
        CXDPMFParams(0.45, 3, 0.20),
        CXDPMFParams(0.45, 3, 0.35),
        CXDPMFParams(0.55, 3, 0.20),
        CXDPMFParams(0.55, 3, 0.35),
    ]


def build_dev_memory(dev_cases: list[dict[str, Any]], predictor, cfg: CXGlobalConfig, params: CXDPMFParams) -> dict[str, Any]:
    feats = []
    kernels = []
    for item in dev_cases:
        case = item['case']
        _, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(params.residual_alpha))
        mean2d = np.mean(corr3d, axis=0)
        free = esdf[~case['occupancy']]
        p10_clear = float(np.quantile(free, 0.10)) if free.size else 0.0
        feat = [
            float(np.mean(case['occupancy'].astype(np.float32))),
            float(np.mean(mean2d)),
            float(np.mean(local_std_map(mean2d))),
            p10_clear,
        ]
        feats.append(feat)
        kernels.append(mean2d.astype(np.float32))
    x = np.asarray(feats, dtype=np.float32)
    n_proto = int(min(max(1, params.n_proto), len(x)))
    kmeans = KMeans(n_clusters=n_proto, n_init=10, random_state=20260307)
    labels = kmeans.fit_predict(x)
    proto = []
    for i in range(n_proto):
        mask = labels == i
        proto.append(np.mean(np.stack([kernels[j] for j in np.where(mask)[0]], axis=0), axis=0).astype(np.float32))
    return {'kmeans': kmeans, 'proto': proto}


def _embed_nonh(case: dict[str, Any], corr3d: np.ndarray, esdf: np.ndarray) -> np.ndarray:
    mean2d = np.mean(corr3d, axis=0)
    free = esdf[~case['occupancy']]
    p10_clear = float(np.quantile(free, 0.10)) if free.size else 0.0
    return np.asarray([
        float(np.mean(case['occupancy'].astype(np.float32))),
        float(np.mean(mean2d)),
        float(np.mean(local_std_map(mean2d))),
        p10_clear,
    ], dtype=np.float32)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CXDPMFParams, memory: dict[str, Any]) -> np.ndarray:
    rs_base, corr3d, esdf = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(params.residual_alpha))
    emb = _embed_nonh(case, corr3d, esdf)[None, :]
    idx = int(memory['kmeans'].predict(emb)[0])
    kernel2d = np.asarray(memory['proto'][idx], dtype=np.float32)
    kernel3d = np.repeat(kernel2d[None, ...], corr3d.shape[0], axis=0)
    corr_mod = (1.0 - float(params.mix_ratio)) * corr3d + float(params.mix_ratio) * kernel3d
    corr_mod = np.maximum(corr_mod, 0.0).astype(np.float32)
    return fuse_nonholonomic(rs_base, corr_mod, cfg.residual_floor_ratio)


def _resize_kernel(kernel2d: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    kernel = np.asarray(kernel2d, dtype=np.float32)
    if kernel.shape == target_shape:
        return kernel
    zoom = (float(target_shape[0]) / max(kernel.shape[0], 1), float(target_shape[1]) / max(kernel.shape[1], 1))
    resized = ndimage.zoom(kernel, zoom=zoom, order=1).astype(np.float32)
    out = np.zeros(target_shape, dtype=np.float32)
    h = min(target_shape[0], resized.shape[0])
    w = min(target_shape[1], resized.shape[1])
    out[:h, :w] = resized[:h, :w]
    return out


def build_standard_field(sample, predictor, params: CXDPMFParams, memory: dict[str, Any]) -> np.ndarray:
    base, corr2d, esdf = standard_base_and_correction(sample, predictor)
    free = esdf[~sample.occupancy]
    p10_clear = float(np.quantile(free, 0.10)) if free.size else 0.0
    emb = np.asarray([[float(np.mean(sample.occupancy.astype(np.float32))), float(np.mean(corr2d)), float(np.mean(local_std_map(corr2d))), p10_clear]], dtype=np.float32)
    idx = int(memory['kmeans'].predict(emb)[0])
    kernel2d = _resize_kernel(np.asarray(memory['proto'][idx], dtype=np.float32), corr2d.shape)
    corr_mod = (1.0 - float(params.mix_ratio)) * corr2d + float(params.mix_ratio) * kernel2d
    corr_mod = np.maximum(corr_mod, 0.0).astype(np.float32)
    return (base + corr_mod).astype(np.float32)
