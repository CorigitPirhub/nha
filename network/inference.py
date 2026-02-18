from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import torch

from env.esdf import normalize_esdf
from network.model import TinyUNet
from utils.common import gaussian_2d


class NeuralHeuristicPredictor:
    def __init__(self, checkpoint: Path, device: str = "cpu", gaussian_sigma: float = 2.5) -> None:
        payload = torch.load(checkpoint, map_location=device, weights_only=False)
        model = TinyUNet(in_channels=4, base=32)
        model.load_state_dict(payload["model_state"])
        model.eval()

        self.model = model.to(device)
        self.device = torch.device(device)
        self.gaussian_sigma = float(gaussian_sigma)

    @torch.no_grad()
    def predict_field(
        self,
        occupancy: np.ndarray,
        esdf: np.ndarray,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        resolution: float,
    ) -> np.ndarray:
        occ = occupancy.astype(np.float32)
        h, w = occ.shape

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
        esdf_norm = normalize_esdf(esdf)

        inp = np.stack([occ, esdf_norm, start_map, goal_map], axis=0)[None, ...]
        x = torch.from_numpy(inp).to(self.device)
        pred_norm = self.model(x).cpu().numpy()[0, 0]

        scale = np.hypot(h * resolution, w * resolution)
        pred = pred_norm * scale
        pred[occupancy] = np.max(pred) + 5.0
        return pred.astype(np.float32)
