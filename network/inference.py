from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import torch

from config import DEFAULT_CONFIG
from env.esdf import normalize_esdf
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from network.model import build_model
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
        model_name = str(payload.get("model_name", train_cfg.get("model_name", "tinyunet"))).lower()
        model_state = payload["model_state"]
        if model_name in {"smallunet", "small_unet", "small"}:
            has_context = any(k.startswith("context_dilated.") or k.startswith("context_ppm.") for k in model_state.keys())
            if not has_context:
                model_name = "smallunet_legacy"
        temporal_steps = int(payload.get("temporal_steps", 1))
        heuristic_yaw_bins = int(payload.get("heuristic_yaw_bins", out_channels))
        if heuristic_yaw_bins <= 0:
            heuristic_yaw_bins = out_channels
        if temporal_steps <= 0:
            temporal_steps = 1
        if temporal_steps * heuristic_yaw_bins != out_channels and heuristic_yaw_bins == out_channels:
            temporal_steps = 1

        model = build_model(
            model_name=model_name,
            in_channels=in_channels,
            out_channels=out_channels,
            base=base_channels,
            output_activation=output_activation,
        )
        incompatible = model.load_state_dict(model_state, strict=False)
        if incompatible.missing_keys or incompatible.unexpected_keys:
            print(
                "[warning] checkpoint/model mismatch: "
                f"missing={len(incompatible.missing_keys)} unexpected={len(incompatible.unexpected_keys)}"
            )
        model.eval()

        self.model = model.to(device)
        self.device = torch.device(device)
        self.gaussian_sigma = float(gaussian_sigma)
        self.in_channels = in_channels
        self.raw_out_channels = out_channels
        self.temporal_steps = temporal_steps
        self.heuristic_yaw_bins = heuristic_yaw_bins
        self.out_channels = heuristic_yaw_bins
        self.prediction_mode = prediction_mode
        self.residual_nonnegative = residual_nonnegative
        self.model_name = model_name
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
        self._wb_min = 1.5
        self._wb_max = 2.5
        self._steer_min = 30.0
        self._steer_max = 60.0

    @staticmethod
    def _norm_range(v: float, lo: float, hi: float) -> float:
        if hi <= lo:
            return 0.0
        return float(np.clip((v - lo) / (hi - lo), 0.0, 1.0))

    def _build_input(
        self,
        occupancy: np.ndarray,
        esdf: np.ndarray,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        resolution: float,
        dynamic_risk: np.ndarray | None = None,
        dynamic_risk_seq: np.ndarray | None = None,
        vehicle_context: dict | None = None,
    ) -> np.ndarray:
        occ = occupancy.astype(np.float32)
        h, w = occ.shape
        esdf_norm = normalize_esdf(esdf)

        if self.in_channels >= 5:
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
            dyn = np.clip(dynamic_risk.astype(np.float32), 0.0, 1.0) if dynamic_risk is not None else np.zeros((h, w), dtype=np.float32)
            if dynamic_risk_seq is not None and dynamic_risk_seq.ndim == 3 and dynamic_risk_seq.shape[0] >= 3:
                dyn_t1 = np.clip(dynamic_risk_seq[1].astype(np.float32), 0.0, 1.0)
                dyn_t2 = np.clip(dynamic_risk_seq[2].astype(np.float32), 0.0, 1.0)
            else:
                dyn_t1 = dyn
                dyn_t2 = dyn
            ctx = vehicle_context or {}
            wb = self._norm_range(float(ctx.get("wheel_base", DEFAULT_CONFIG.vehicle.wheel_base)), self._wb_min, self._wb_max)
            steer = self._norm_range(float(ctx.get("max_steer_deg", DEFAULT_CONFIG.vehicle.max_steer_deg)), self._steer_min, self._steer_max)
            batt = self._norm_range(float(ctx.get("battery", 100.0)), 20.0, 100.0)
            load = self._norm_range(float(ctx.get("load_factor", 1.0)), 1.0, 1.5)
            extras = np.stack(
                [
                    dyn,
                    dyn_t1,
                    dyn_t2,
                    np.full((h, w), wb, dtype=np.float32),
                    np.full((h, w), steer, dtype=np.float32),
                    np.full((h, w), batt, dtype=np.float32),
                    np.full((h, w), load, dtype=np.float32),
                ],
                axis=0,
            )
            inp = np.concatenate([inp, extras], axis=0)
            if inp.shape[0] > self.in_channels:
                inp = inp[: self.in_channels]
            elif inp.shape[0] < self.in_channels:
                pad = np.zeros((self.in_channels - inp.shape[0], h, w), dtype=np.float32)
                inp = np.concatenate([inp, pad], axis=0)
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

    def _extract_current_step_field(self, pred: np.ndarray) -> np.ndarray:
        if pred.ndim != 3:
            return pred
        if self.temporal_steps <= 1:
            return pred
        c, h, w = pred.shape
        if c != self.temporal_steps * self.heuristic_yaw_bins:
            return pred
        reshaped = pred.reshape(self.temporal_steps, self.heuristic_yaw_bins, h, w)
        return reshaped[0].astype(np.float32)

    @torch.no_grad()
    def predict_field(
        self,
        occupancy: np.ndarray,
        esdf: np.ndarray,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        resolution: float,
        base_field_override: np.ndarray | None = None,
        dynamic_risk: np.ndarray | None = None,
        dynamic_risk_seq: np.ndarray | None = None,
        vehicle_context: dict | None = None,
    ) -> np.ndarray:
        h, w = occupancy.shape
        inp = self._build_input(
            occupancy,
            esdf,
            start,
            goal,
            resolution,
            dynamic_risk=dynamic_risk,
            dynamic_risk_seq=dynamic_risk_seq,
            vehicle_context=vehicle_context,
        )

        x = torch.from_numpy(inp[None, ...]).to(self.device)
        pred_norm = self.model(x).cpu().numpy()[0]

        scale = np.hypot(h * resolution, w * resolution)
        pred = (pred_norm * scale).astype(np.float32)
        pred = self._extract_current_step_field(pred)

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
        dynamic_risk: np.ndarray | None = None,
        dynamic_risk_seq: np.ndarray | None = None,
        vehicle_context: dict | None = None,
    ) -> np.ndarray:
        h, w = occupancy.shape
        inp = self._build_input(
            occupancy,
            esdf,
            start,
            goal,
            resolution,
            dynamic_risk=dynamic_risk,
            dynamic_risk_seq=dynamic_risk_seq,
            vehicle_context=vehicle_context,
        )
        x = torch.from_numpy(inp[None, ...]).to(self.device)
        pred_norm = self.model(x).cpu().numpy()[0]
        scale = np.hypot(h * resolution, w * resolution)
        pred = (pred_norm * scale).astype(np.float32)
        pred = self._extract_current_step_field(pred)
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
        if self.heuristic_yaw_bins <= 1:
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
            yaw_bins=int(self.heuristic_yaw_bins),
            rho=float(self.min_turn_radius),
            fill_value=float(self.fill_value),
            step_size=float(self.rs_step_size),
            backend=self.rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=self.rs_cost_cfg,
        ).astype(np.float32)
