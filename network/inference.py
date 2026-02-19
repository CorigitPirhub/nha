from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import torch

from config import DEFAULT_CONFIG
from env.esdf import normalize_esdf
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from network.model import TinyUNet
from utils.common import gaussian_2d


class NeuralHeuristicPredictor:
    def __init__(self, checkpoint: Path, device: str = "cpu", gaussian_sigma: float = 2.5) -> None:
        if device.startswith("cuda") and not torch.cuda.is_available():
            print("[warning] CUDA requested but unavailable for inference, fallback to CPU.")
            device = "cpu"

        payload = torch.load(checkpoint, map_location=device, weights_only=False)
        in_channels = int(payload.get("in_channels", 4))
        out_channels = int(payload.get("out_channels", 1))
        if "base_channels" in payload:
            base_channels = int(payload["base_channels"])
        else:
            base_channels = int(payload["model_state"]["inc.block.0.weight"].shape[0])
        cfg_dict = payload.get("config", {}) if isinstance(payload, dict) else {}
        train_cfg = cfg_dict.get("train", {}) if isinstance(cfg_dict, dict) else {}
        ds_cfg = cfg_dict.get("dataset", {}) if isinstance(cfg_dict, dict) else {}
        veh_cfg = cfg_dict.get("vehicle", {}) if isinstance(cfg_dict, dict) else {}
        pl_cfg = cfg_dict.get("planner", {}) if isinstance(cfg_dict, dict) else {}

        prediction_mode = str(payload.get("prediction_mode", train_cfg.get("prediction_mode", "absolute"))).lower()
        if prediction_mode not in {"absolute", "residual"}:
            prediction_mode = "absolute"
        output_activation = str(
            payload.get("output_activation", "identity" if prediction_mode == "residual" else "softplus")
        ).lower()
        residual_nonnegative = bool(payload.get("residual_nonnegative", prediction_mode == "residual"))

        model = TinyUNet(
            in_channels=in_channels,
            out_channels=out_channels,
            base=base_channels,
            output_activation=output_activation,
        )
        model.load_state_dict(payload["model_state"])
        model.eval()

        self.model = model.to(device)
        self.device = torch.device(device)
        self.gaussian_sigma = float(gaussian_sigma)
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.prediction_mode = prediction_mode
        self.residual_nonnegative = residual_nonnegative
        self.fill_value = float(ds_cfg.get("max_teacher_value", DEFAULT_CONFIG.dataset.max_teacher_value))
        self.rs_backend = str(ds_cfg.get("teacher_rs_backend", DEFAULT_CONFIG.dataset.teacher_rs_backend))
        self.rs_step_size = float(ds_cfg.get("teacher_rs_step_size", DEFAULT_CONFIG.dataset.teacher_rs_step_size))
        self.min_turn_radius = float(veh_cfg.get("min_turn_radius", DEFAULT_CONFIG.vehicle.min_turn_radius))
        self.rs_cost_cfg = RSConsistentCostConfig(
            reverse_penalty=float(pl_cfg.get("reverse_penalty", DEFAULT_CONFIG.planner.reverse_penalty)),
            steer_penalty=float(pl_cfg.get("steer_penalty", DEFAULT_CONFIG.planner.steer_penalty)),
            steer_change_penalty=float(pl_cfg.get("steer_change_penalty", DEFAULT_CONFIG.planner.steer_change_penalty)),
            step_size=float(pl_cfg.get("step_size", DEFAULT_CONFIG.planner.step_size)),
            wheel_base=float(veh_cfg.get("wheel_base", DEFAULT_CONFIG.vehicle.wheel_base)),
            max_steer_rad=float(np.deg2rad(float(veh_cfg.get("max_steer_deg", DEFAULT_CONFIG.vehicle.max_steer_deg)))),
        )

    def _build_input(
        self,
        occupancy: np.ndarray,
        esdf: np.ndarray,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        resolution: float,
    ) -> np.ndarray:
        occ = occupancy.astype(np.float32)
        h, w = occ.shape
        esdf_norm = normalize_esdf(esdf)

        if self.in_channels == 5:
            goal_map = gaussian_2d(
                h,
                w,
                goal[0] / resolution - 0.5,
                goal[1] / resolution - 0.5,
                self.gaussian_sigma,
            )
            goal_sin = np.full((h, w), np.sin(goal[2]), dtype=np.float32)
            goal_cos = np.full((h, w), np.cos(goal[2]), dtype=np.float32)
            inp = np.stack([occ, esdf_norm, goal_map, goal_sin, goal_cos], axis=0)
            return inp.astype(np.float32)

        start_map = gaussian_2d(
            h,
            w,
            start[0] / resolution - 0.5,
            start[1] / resolution - 0.5,
            self.gaussian_sigma,
        )
        goal_map = gaussian_2d(
            h,
            w,
            goal[0] / resolution - 0.5,
            goal[1] / resolution - 0.5,
            self.gaussian_sigma,
        )
        inp = np.stack([occ, esdf_norm, start_map, goal_map], axis=0)
        return inp.astype(np.float32)

    @torch.no_grad()
    def predict_field(
        self,
        occupancy: np.ndarray,
        esdf: np.ndarray,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        resolution: float,
        base_field_override: np.ndarray | None = None,
    ) -> np.ndarray:
        h, w = occupancy.shape
        inp = self._build_input(occupancy, esdf, start, goal, resolution)

        x = torch.from_numpy(inp[None, ...]).to(self.device)
        pred_norm = self.model(x).cpu().numpy()[0]

        scale = np.hypot(h * resolution, w * resolution)
        pred = (pred_norm * scale).astype(np.float32)

        if self.prediction_mode == "residual":
            if self.residual_nonnegative:
                pred = np.maximum(pred, 0.0).astype(np.float32)
            if base_field_override is None:
                base = self.compute_rs_analytical_base_field(occupancy, goal, resolution)
            else:
                base = base_field_override.astype(np.float32)
            pred = (base + pred).astype(np.float32)

        if pred.ndim == 2:
            fill = float(self.fill_value if np.isfinite(self.fill_value) else np.max(pred) + 5.0)
            pred[occupancy] = fill
            return pred

        # [C, H, W]
        fill = float(self.fill_value if np.isfinite(self.fill_value) else np.max(pred) + 5.0)
        pred[:, occupancy] = fill
        return pred

    @torch.no_grad()
    def predict_residual_field(
        self,
        occupancy: np.ndarray,
        esdf: np.ndarray,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        resolution: float,
    ) -> np.ndarray:
        h, w = occupancy.shape
        inp = self._build_input(occupancy, esdf, start, goal, resolution)
        x = torch.from_numpy(inp[None, ...]).to(self.device)
        pred_norm = self.model(x).cpu().numpy()[0]
        scale = np.hypot(h * resolution, w * resolution)
        pred = (pred_norm * scale).astype(np.float32)
        if self.prediction_mode != "residual":
            pred = pred.copy()
            fill = float(self.fill_value if np.isfinite(self.fill_value) else np.max(pred) + 5.0)
            if pred.ndim == 2:
                pred[occupancy] = fill
            else:
                pred[:, occupancy] = fill
            return pred
        if self.residual_nonnegative:
            pred = np.maximum(pred, 0.0).astype(np.float32)
        return pred

    def compute_rs_analytical_base_field(
        self,
        occupancy: np.ndarray,
        goal: Tuple[float, float, float],
        resolution: float,
    ) -> np.ndarray:
        if self.out_channels <= 1:
            h, w = occupancy.shape
            yy, xx = np.mgrid[0:h, 0:w]
            wx = (xx + 0.5) * resolution
            wy = (yy + 0.5) * resolution
            base2d = np.hypot(wx - goal[0], wy - goal[1]).astype(np.float32)
            base2d[occupancy] = self.fill_value
            return base2d

        return compute_reeds_shepp_field(
            occupancy=occupancy.astype(bool),
            goal=goal,
            resolution=resolution,
            yaw_bins=int(self.out_channels),
            rho=float(self.min_turn_radius),
            fill_value=float(self.fill_value),
            step_size=float(self.rs_step_size),
            backend=self.rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=self.rs_cost_cfg,
        ).astype(np.float32)
