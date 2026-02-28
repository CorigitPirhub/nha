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
        use_context_channels: bool = False,
        use_temporal_context: bool = True,
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
        self.use_context_channels = bool(use_context_channels)
        self.use_temporal_context = bool(use_temporal_context)
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
        self._wb_min = 1.5
        self._wb_max = 2.5
        self._steer_min = 30.0
        self._steer_max = 60.0

    @staticmethod
    def _norm_range(v: float, lo: float, hi: float) -> float:
        if hi <= lo:
            return 0.0
        return float(np.clip((v - lo) / (hi - lo), 0.0, 1.0))

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
            difficulty = str(sample["difficulty"]) if "difficulty" in sample else ("hard" if category == "C" else "unknown")
            source_dataset = str(sample["source_dataset"]) if "source_dataset" in sample else ""
            scenario_type = str(sample["scenario_type"]) if "scenario_type" in sample else ""
            dynamic_risk = sample["dynamic_risk"].astype(np.float32) if "dynamic_risk" in sample else np.zeros_like(occ)
            dynamic_risk_seq = sample["dynamic_risk_seq"].astype(np.float32) if "dynamic_risk_seq" in sample else None
            vehicle_wheel_base = float(sample["vehicle_wheel_base"]) if "vehicle_wheel_base" in sample else float(DEFAULT_CONFIG.vehicle.wheel_base)
            vehicle_width = float(sample["vehicle_width"]) if "vehicle_width" in sample else float(DEFAULT_CONFIG.vehicle.width)
            vehicle_max_steer_deg = float(sample["vehicle_max_steer_deg"]) if "vehicle_max_steer_deg" in sample else float(DEFAULT_CONFIG.vehicle.max_steer_deg)
            vehicle_battery = float(sample["vehicle_battery"]) if "vehicle_battery" in sample else 100.0
            vehicle_load_factor = float(sample["vehicle_load_factor"]) if "vehicle_load_factor" in sample else 1.0

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

            temporal_residual = None
            if self.prediction_mode == "residual" and "temporal_residual_3d" in sample:
                temporal_residual = sample["temporal_residual_3d"].astype(np.float32)

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
        if self.use_context_channels:
            dyn = np.clip(dynamic_risk.astype(np.float32), 0.0, 1.0)
            if self.use_temporal_context and dynamic_risk_seq is not None and dynamic_risk_seq.ndim == 3 and dynamic_risk_seq.shape[0] >= 3:
                dyn_t1 = np.clip(dynamic_risk_seq[1], 0.0, 1.0).astype(np.float32)
                dyn_t2 = np.clip(dynamic_risk_seq[2], 0.0, 1.0).astype(np.float32)
            else:
                dyn_t1 = dyn
                dyn_t2 = dyn
            wb_norm = self._norm_range(vehicle_wheel_base, self._wb_min, self._wb_max)
            steer_norm = self._norm_range(vehicle_max_steer_deg, self._steer_min, self._steer_max)
            batt_norm = self._norm_range(vehicle_battery, 20.0, 100.0)
            load_norm = self._norm_range(vehicle_load_factor, 1.0, 1.5)
            x = np.concatenate(
                [
                    x,
                    dyn[None, ...],
                    dyn_t1[None, ...],
                    dyn_t2[None, ...],
                    np.full((1, h, w), wb_norm, dtype=np.float32),
                    np.full((1, h, w), steer_norm, dtype=np.float32),
                    np.full((1, h, w), batt_norm, dtype=np.float32),
                    np.full((1, h, w), load_norm, dtype=np.float32),
                ],
                axis=0,
            ).astype(np.float32)

        scale = np.hypot(h * resolution, w * resolution)
        temporal_steps = 1
        yaw_bins = int(teacher.shape[0])
        if self.prediction_mode == "residual":
            if rs_base is None:
                raise RuntimeError("Residual mode requires RS base field.")

            # Static residual should always be part of supervision.
            # temporal_residual_3d is treated as dynamic increment on top of static residual.
            static_res = np.maximum((teacher - rs_base).astype(np.float32), 0.0).astype(np.float32)
            static_res = np.where(np.isfinite(static_res), static_res, 0.0).astype(np.float32)

            if self.use_temporal_context and temporal_residual is not None and temporal_residual.ndim == 4:
                temporal_steps = int(temporal_residual.shape[0])
                yaw_bins = int(temporal_residual.shape[1])

                temp = np.asarray(temporal_residual, dtype=np.float32)
                temp = np.where(np.isfinite(temp), temp, 0.0).astype(np.float32)
                temp = np.maximum(temp, 0.0).astype(np.float32)

                if static_res.shape[0] != yaw_bins:
                    if static_res.shape[0] == 1:
                        static_res_yaw = np.repeat(static_res, yaw_bins, axis=0).astype(np.float32)
                    else:
                        idx = (
                            np.floor(np.arange(yaw_bins, dtype=np.float32) * (static_res.shape[0] / float(max(yaw_bins, 1))))
                            .astype(np.int64)
                        ) % static_res.shape[0]
                        static_res_yaw = static_res[idx].astype(np.float32)
                else:
                    static_res_yaw = static_res

                static_t = np.broadcast_to(static_res_yaw[None, ...], (temporal_steps, yaw_bins, h, w)).astype(np.float32)
                target_t = (static_t + temp).astype(np.float32)
                target_t = np.maximum(target_t, 0.0).astype(np.float32)

                flat = target_t.reshape(temporal_steps * yaw_bins, h, w).astype(np.float32)
                pos = flat[flat > 0.0]
                if pos.size > 0:
                    clip_hi = float(np.percentile(pos, 99.0))
                else:
                    clip_hi = float(2.0 * np.hypot(h * resolution, w * resolution))
                clip_hi = float(np.clip(clip_hi, 1.0, 4.0 * np.hypot(h * resolution, w * resolution)))
                target_raw = np.clip(flat, 0.0, clip_hi).astype(np.float32)
            else:
                target_raw = static_res.astype(np.float32)
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
        narrow_thr = float(max(0.35, 0.95 * vehicle_width))
        narrow_mask_2d = ((occ < 0.5) & (esdf <= narrow_thr)).astype(np.float32)
        narrow_mask = np.broadcast_to(narrow_mask_2d[None, ...], target.shape).astype(np.float32)
        st = scenario_type.strip().lower()
        src = source_dataset.strip().lower()
        if not st:
            if src in {"mp", "csm"}:
                st = "standard"
            elif str(difficulty).strip().lower() == "hard":
                st = "hard"
            else:
                st = "general"

        is_standard = 1.0 if st == "standard" else 0.0
        if is_standard > 0.5:
            is_hard = 0.0
        else:
            is_hard = 1.0 if (st in {"hard", "nonholonomic", "hard_dynamic"} or str(difficulty).strip().lower() == "hard") else 0.0

        return {
            "input": torch.from_numpy(x),
            "target": torch.from_numpy(target),
            "mask": torch.from_numpy(mask),
            "loss_weight": torch.from_numpy(loss_weight),
            "sample_weight": torch.tensor(self.type_c_loss_weight if category == "C" else 1.0, dtype=torch.float32),
            "is_hard": torch.tensor(is_hard, dtype=torch.float32),
            "is_standard": torch.tensor(is_standard, dtype=torch.float32),
            "narrow_mask": torch.from_numpy(narrow_mask),
            "scale": torch.tensor(scale, dtype=torch.float32),
            "resolution": torch.tensor(resolution, dtype=torch.float32),
            "temporal_steps": torch.tensor(int(temporal_steps), dtype=torch.int64),
            "yaw_bins": torch.tensor(int(yaw_bins), dtype=torch.int64),
        }
