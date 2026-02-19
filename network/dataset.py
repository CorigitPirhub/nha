from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import numpy as np
import torch
from torch.utils.data import Dataset

from config import DEFAULT_CONFIG
from env.esdf import normalize_esdf
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from utils.common import gaussian_2d


class HeuristicFieldDataset(Dataset):
    def __init__(
        self,
        root: Path,
        gaussian_sigma: float = 2.5,
        esdf_clip_m: float = 10.0,
        distance_weight_scale_m: float = 6.0,
        distance_weight_min: float = 0.25,
        hybrid_obstacle_alpha: float = 0.0,
        hybrid_obstacle_threshold_m: float = 1.5,
        prediction_mode: str = "absolute",
        type_c_loss_weight: float = 1.0,
    ) -> None:
        self.root = Path(root)
        self.files = sorted(self.root.glob("*.npz"))
        if not self.files:
            raise RuntimeError(f"No dataset files found under {self.root}")
        self.gaussian_sigma = float(gaussian_sigma)
        self.esdf_clip_m = float(esdf_clip_m)
        self.distance_weight_scale_m = float(max(distance_weight_scale_m, 1e-3))
        self.distance_weight_min = float(np.clip(distance_weight_min, 1e-3, 1.0))
        self.hybrid_obstacle_alpha = float(max(hybrid_obstacle_alpha, 0.0))
        self.hybrid_obstacle_threshold_m = float(max(hybrid_obstacle_threshold_m, 1e-3))
        self.type_c_loss_weight = float(max(type_c_loss_weight, 1.0))
        self.prediction_mode = str(prediction_mode).lower()
        if self.prediction_mode not in {"absolute", "residual"}:
            raise ValueError(f"Unsupported prediction_mode: {prediction_mode}")

        meta_path = self.root / "meta.json"
        if meta_path.exists():
            try:
                self.meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                self.meta = {}
        else:
            self.meta = {}

        self.meta_teacher_mode = str(self.meta.get("teacher_mode", "")).lower()
        self.meta_hybrid_alpha = float(self.meta.get("hybrid_obstacle_alpha", 0.0))
        self.meta_hybrid_threshold = float(self.meta.get("hybrid_obstacle_threshold_m", 1.5))
        self.meta_rs_backend = str(self.meta.get("teacher_rs_backend", "auto"))
        self.meta_rs_step_size = float(self.meta.get("teacher_rs_step_size", 1.0))
        self._fallback_rs_cost_cfg = RSConsistentCostConfig.from_configs(DEFAULT_CONFIG.vehicle, DEFAULT_CONFIG.planner)

    def __len__(self) -> int:
        return len(self.files)

    def _derive_rs_base(
        self,
        sample: np.lib.npyio.NpzFile,
        teacher: np.ndarray,
        occ: np.ndarray,
        esdf: np.ndarray,
        goal: np.ndarray,
        resolution: float,
        fill_value: float,
    ) -> np.ndarray:
        if "rs_base_3d" in sample:
            base = sample["rs_base_3d"].astype(np.float32)
            return base

        if teacher.ndim != 3:
            raise RuntimeError("Residual mode requires 3D teacher / rs_base_3d.")

        mode = self.meta_teacher_mode
        if mode in {"reeds_shepp_consistent", "rs_consistent", "reeds_shepp_costaware"}:
            base = teacher.copy()
        elif mode in {"hybrid_rs_consistent_esdf", "hybrid_consistent", "rs_consistent_hybrid"}:
            obs = np.maximum(0.0, self.meta_hybrid_threshold - np.maximum(esdf, 0.0)).astype(np.float32)
            base = (teacher - self.meta_hybrid_alpha * obs[None, ...]).astype(np.float32)
        else:
            base = compute_reeds_shepp_field(
                occupancy=occ.astype(bool),
                goal=(float(goal[0]), float(goal[1]), float(goal[2])),
                resolution=resolution,
                yaw_bins=int(teacher.shape[0]),
                rho=float(DEFAULT_CONFIG.vehicle.min_turn_radius),
                fill_value=fill_value,
                step_size=self.meta_rs_step_size,
                backend=self.meta_rs_backend,
                cost_mode="planner_consistent",
                cost_cfg=self._fallback_rs_cost_cfg,
            )

        base[:, occ > 0.5] = fill_value
        base = np.where(np.isfinite(base), base, fill_value).astype(np.float32)
        return base

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        with np.load(self.files[idx], allow_pickle=False) as sample:
            occ = sample["occupancy"].astype(np.float32)
            esdf = sample["esdf"].astype(np.float32)
            goal = sample["goal"].astype(np.float32)
            resolution = float(sample["resolution"])
            fill_value = float(sample["fill_value"])
            category = str(sample["category"]) if "category" in sample else "U"

            if "teacher_3d" in sample:
                teacher = sample["teacher_3d"].astype(np.float32)
                teacher_2d = sample["teacher_2d"].astype(np.float32)
            else:
                # Backward compatibility with old 2D dataset.
                t2d = sample["teacher"].astype(np.float32)
                teacher = t2d[None, ...]
                teacher_2d = t2d

            rs_base = None
            if self.prediction_mode == "residual":
                rs_base = self._derive_rs_base(sample, teacher, occ, esdf, goal, resolution, fill_value)

        if self.hybrid_obstacle_alpha > 0.0:
            obs_cost = np.maximum(0.0, self.hybrid_obstacle_threshold_m - np.maximum(esdf, 0.0)).astype(np.float32)
            teacher = (teacher + self.hybrid_obstacle_alpha * obs_cost[None, ...]).astype(np.float32)

        h, w = occ.shape
        goal_cx = goal[0] / resolution - 0.5
        goal_cy = goal[1] / resolution - 0.5

        goal_map = gaussian_2d(h, w, goal_cx, goal_cy, self.gaussian_sigma)
        esdf_norm = normalize_esdf(esdf, clip_m=self.esdf_clip_m)

        goal_sin = np.full((h, w), np.sin(goal[2]), dtype=np.float32)
        goal_cos = np.full((h, w), np.cos(goal[2]), dtype=np.float32)

        x = np.stack([occ, esdf_norm, goal_map, goal_sin, goal_cos], axis=0).astype(np.float32)

        scale = np.hypot(h * resolution, w * resolution)
        if self.prediction_mode == "residual":
            if rs_base is None:
                raise RuntimeError("Residual mode requires RS base field.")
            target_raw = (teacher - rs_base).astype(np.float32)
        else:
            target_raw = teacher.astype(np.float32)
        target = (target_raw / max(scale, 1e-3)).astype(np.float32)

        base_mask = ((occ < 0.5) & np.isfinite(teacher_2d) & (teacher_2d < 0.95 * fill_value)).astype(np.float32)
        if self.prediction_mode == "residual" and rs_base is not None:
            rs_ok = np.isfinite(rs_base[0]) & (rs_base[0] < 0.95 * fill_value)
            base_mask = (base_mask > 0.5) & rs_ok
            base_mask = base_mask.astype(np.float32)
        mask = np.broadcast_to(base_mask[None, ...], target.shape).astype(np.float32)
        dist_w = 1.0 / (1.0 + np.maximum(teacher_2d, 0.0) / self.distance_weight_scale_m)
        dist_w = np.clip(dist_w, self.distance_weight_min, 1.0).astype(np.float32)
        loss_weight = np.broadcast_to(dist_w[None, ...], target.shape).astype(np.float32)

        return {
            "input": torch.from_numpy(x),
            "target": torch.from_numpy(target),
            "mask": torch.from_numpy(mask),
            "loss_weight": torch.from_numpy(loss_weight),
            "sample_weight": torch.tensor(self.type_c_loss_weight if category == "C" else 1.0, dtype=torch.float32),
            "scale": torch.tensor(scale, dtype=torch.float32),
            "resolution": torch.tensor(resolution, dtype=torch.float32),
        }
