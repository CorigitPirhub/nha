from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import torch
from torch.utils.data import Dataset

from env.esdf import normalize_esdf
from utils.common import gaussian_2d


class HeuristicFieldDataset(Dataset):
    def __init__(self, root: Path, gaussian_sigma: float = 2.5, esdf_clip_m: float = 10.0) -> None:
        self.root = Path(root)
        self.files = sorted(self.root.glob("*.npz"))
        if not self.files:
            raise RuntimeError(f"No dataset files found under {self.root}")
        self.gaussian_sigma = float(gaussian_sigma)
        self.esdf_clip_m = float(esdf_clip_m)

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        with np.load(self.files[idx], allow_pickle=False) as sample:
            occ = sample["occupancy"].astype(np.float32)
            esdf = sample["esdf"].astype(np.float32)
            teacher = sample["teacher"].astype(np.float32)
            start = sample["start"].astype(np.float32)
            goal = sample["goal"].astype(np.float32)
            resolution = float(sample["resolution"])
            fill_value = float(sample["fill_value"])

        h, w = occ.shape
        start_cx = start[0] / resolution - 0.5
        start_cy = start[1] / resolution - 0.5
        goal_cx = goal[0] / resolution - 0.5
        goal_cy = goal[1] / resolution - 0.5

        start_map = gaussian_2d(h, w, start_cx, start_cy, self.gaussian_sigma)
        goal_map = gaussian_2d(h, w, goal_cx, goal_cy, self.gaussian_sigma)
        esdf_norm = normalize_esdf(esdf, clip_m=self.esdf_clip_m)

        x = np.stack([occ, esdf_norm, start_map, goal_map], axis=0).astype(np.float32)

        scale = np.hypot(h * resolution, w * resolution)
        target = (teacher / max(scale, 1e-3)).astype(np.float32)

        mask = ((occ < 0.5) & np.isfinite(teacher) & (teacher < 0.95 * fill_value)).astype(np.float32)

        return {
            "input": torch.from_numpy(x),
            "target": torch.from_numpy(target[None, ...]),
            "mask": torch.from_numpy(mask[None, ...]),
            "scale": torch.tensor(scale, dtype=torch.float32),
            "resolution": torch.tensor(resolution, dtype=torch.float32),
        }
