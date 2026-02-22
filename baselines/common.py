from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from scipy import ndimage
from torch.utils.data import Dataset

from env.teacher import compute_2d_dijkstra_field
from utils.common import gaussian_2d


@dataclass
class GridSample:
    occupancy: np.ndarray
    teacher_2d: np.ndarray
    start: tuple[float, float, float]
    goal: tuple[float, float, float]
    resolution: float
    scenario: str
    difficulty: str
    source_dataset: str
    map_id: str


def load_grid_sample(path: Path) -> GridSample:
    with np.load(path, allow_pickle=False) as z:
        occupancy = z["occupancy"].astype(bool)
        resolution = float(z["resolution"]) if "resolution" in z else 0.5
        start = tuple(float(v) for v in z["start"].astype(np.float32))
        goal = tuple(float(v) for v in z["goal"].astype(np.float32))
        scenario = str(z["scenario"]) if "scenario" in z else "unknown"
        difficulty = str(z["difficulty"]) if "difficulty" in z else "unknown"
        source_dataset = str(z["source_dataset"]) if "source_dataset" in z else "unknown"
        map_id = str(z["map_id"]) if "map_id" in z else "unknown"

        if "teacher_2d" in z:
            teacher = z["teacher_2d"].astype(np.float32)
        elif "teacher" in z:
            t = z["teacher"].astype(np.float32)
            teacher = t[0] if t.ndim == 3 else t
        else:
            teacher = compute_2d_dijkstra_field(occupancy=occupancy, goal_xy=(goal[0], goal[1]), resolution=resolution)

    fill = 1e6
    teacher = np.where(np.isfinite(teacher), teacher, fill).astype(np.float32)
    teacher[occupancy] = fill
    return GridSample(
        occupancy=occupancy,
        teacher_2d=teacher,
        start=start,
        goal=goal,
        resolution=resolution,
        scenario=scenario,
        difficulty=difficulty,
        source_dataset=source_dataset,
        map_id=map_id,
    )


def select_files(paths: Iterable[Path], max_samples: int, seed: int) -> list[Path]:
    files = sorted(list(paths))
    if max_samples <= 0 or len(files) <= max_samples:
        return files
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(files), size=max_samples, replace=False)
    idx.sort()
    return [files[int(i)] for i in idx]


class GridHeuristicDataset(Dataset):
    def __init__(
        self,
        files: list[Path],
        sigma: float = 2.5,
        mode: str = "start_goal",
        target_size: int | None = 64,
    ) -> None:
        self.files = list(files)
        if not self.files:
            raise RuntimeError("Empty dataset file list")
        self.sigma = float(sigma)
        self.mode = str(mode)
        self.target_size = int(target_size) if target_size is not None else None

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        s = load_grid_sample(self.files[idx])
        occupancy = s.occupancy.copy()
        teacher = s.teacher_2d.copy()
        resolution = float(s.resolution)

        if self.target_size is not None and occupancy.shape != (self.target_size, self.target_size):
            h0, w0 = occupancy.shape
            z_h = self.target_size / float(max(h0, 1))
            z_w = self.target_size / float(max(w0, 1))
            occupancy = ndimage.zoom(occupancy.astype(np.float32), zoom=(z_h, z_w), order=0) > 0.5
            teacher = ndimage.zoom(teacher.astype(np.float32), zoom=(z_h, z_w), order=1)
            teacher[occupancy] = 1e6
            # Preserve physical map extent by scaling resolution with original grid width.
            resolution = float(resolution * (w0 / float(self.target_size)))

        h, w = occupancy.shape
        occ = occupancy.astype(np.float32)

        sx = s.start[0] / resolution - 0.5
        sy = s.start[1] / resolution - 0.5
        gx = s.goal[0] / resolution - 0.5
        gy = s.goal[1] / resolution - 0.5

        start_map = gaussian_2d(h, w, sx, sy, self.sigma)
        goal_map = gaussian_2d(h, w, gx, gy, self.sigma)

        if self.mode == "goal_only":
            x = np.stack([occ, goal_map], axis=0).astype(np.float32)
        else:
            x = np.stack([occ, start_map, goal_map], axis=0).astype(np.float32)

        scale = np.hypot(h * resolution, w * resolution)
        y = (teacher / max(scale, 1e-3)).astype(np.float32)
        y = np.clip(y, 0.0, 1e4)
        mask = ((~occupancy) & np.isfinite(teacher) & (teacher < 0.95 * 1e6)).astype(np.float32)

        return {
            "input": torch.from_numpy(x),
            "target": torch.from_numpy(y[None, ...]),
            "mask": torch.from_numpy(mask[None, ...]),
            "scale": torch.tensor(scale, dtype=torch.float32),
            "resolution": torch.tensor(resolution, dtype=torch.float32),
        }
