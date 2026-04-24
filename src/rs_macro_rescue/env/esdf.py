from __future__ import annotations

import numpy as np
from scipy import ndimage


def compute_esdf(occupancy: np.ndarray, resolution: float) -> np.ndarray:
    """Signed distance field in meters: obstacle interior < 0, free space > 0."""
    if occupancy.dtype != bool:
        occupancy = occupancy.astype(bool)

    free = ~occupancy
    dist_out = ndimage.distance_transform_edt(free) * resolution
    dist_in = ndimage.distance_transform_edt(occupancy) * resolution
    esdf = dist_out - dist_in
    return esdf.astype(np.float32)


def normalize_esdf(esdf: np.ndarray, clip_m: float = 10.0) -> np.ndarray:
    clipped = np.clip(esdf, -clip_m, clip_m)
    return (clipped / clip_m).astype(np.float32)
