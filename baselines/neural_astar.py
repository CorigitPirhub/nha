from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from baselines.common import GridHeuristicDataset, load_grid_sample, select_files
from utils.common import gaussian_2d, set_seed


class _ConvBlock(nn.Module):
    def __init__(self, c_in: int, c_out: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(c_in, c_out, 3, padding=1, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
            nn.Conv2d(c_out, c_out, 3, padding=1, bias=False),
            nn.BatchNorm2d(c_out),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class NeuralAStarNet(nn.Module):
    def __init__(self, in_channels: int = 3, base: int = 32) -> None:
        super().__init__()
        self.enc1 = _ConvBlock(in_channels, base)
        self.enc2 = nn.Sequential(nn.MaxPool2d(2), _ConvBlock(base, base * 2))
        self.enc3 = nn.Sequential(nn.MaxPool2d(2), _ConvBlock(base * 2, base * 4))
        self.dec2 = _ConvBlock(base * 4 + base * 2, base * 2)
        self.dec1 = _ConvBlock(base * 2 + base, base)
        self.out = nn.Conv2d(base, 1, kernel_size=1)
        self.softplus = nn.Softplus(beta=1.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.enc1(x)
        x2 = self.enc2(x1)
        x3 = self.enc3(x2)

        y = F.interpolate(x3, size=x2.shape[-2:], mode="bilinear", align_corners=False)
        y = self.dec2(torch.cat([y, x2], dim=1))
        y = F.interpolate(y, size=x1.shape[-2:], mode="bilinear", align_corners=False)
        y = self.dec1(torch.cat([y, x1], dim=1))
        y = self.out(y)
        return self.softplus(y)


@dataclass
class NeuralAStarLite:
    model: NeuralAStarNet
    device: torch.device
    sigma: float = 2.5

    @classmethod
    def load(cls, checkpoint: Path, device: str = "cpu") -> "NeuralAStarLite":
        if device.startswith("cuda") and not torch.cuda.is_available():
            device = "cpu"
        payload = torch.load(checkpoint, map_location=device, weights_only=False)
        model = NeuralAStarNet(in_channels=int(payload.get("in_channels", 3)), base=int(payload.get("base", 32)))
        model.load_state_dict(payload["model_state"])
        model.eval()
        return cls(
            model=model.to(device),
            device=torch.device(device),
            sigma=float(payload.get("sigma", 2.5)),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state": self.model.state_dict(),
                "in_channels": 3,
                "base": 32,
                "sigma": float(self.sigma),
            },
            path,
        )

    @torch.no_grad()
    def predict_field(
        self,
        occupancy: np.ndarray,
        start: tuple[float, float, float],
        goal: tuple[float, float, float],
        resolution: float,
    ) -> np.ndarray:
        occ = occupancy.astype(np.float32)
        h, w = occ.shape

        sx = start[0] / resolution - 0.5
        sy = start[1] / resolution - 0.5
        gx = goal[0] / resolution - 0.5
        gy = goal[1] / resolution - 0.5
        start_map = gaussian_2d(h, w, sx, sy, self.sigma)
        goal_map = gaussian_2d(h, w, gx, gy, self.sigma)

        x = np.stack([occ, start_map, goal_map], axis=0).astype(np.float32)
        xt = torch.from_numpy(x[None, ...]).to(self.device)
        pred = self.model(xt).cpu().numpy()[0, 0]
        scale = np.hypot(h * resolution, w * resolution)
        out = (pred * scale).astype(np.float32)
        out[occupancy.astype(bool)] = 1e6
        return out


def _masked_l1(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    diff = torch.abs(pred - target) * mask
    denom = torch.clamp(mask.sum(), min=1.0)
    return diff.sum() / denom


def train_neural_astar(
    train_dir: Path,
    val_dir: Path | None,
    checkpoint_out: Path,
    seed: int = 7,
    device: str = "cpu",
    epochs: int = 5,
    batch_size: int = 16,
    lr: float = 1e-3,
    max_train_samples: int = 0,
    max_val_samples: int = 0,
) -> dict:
    set_seed(seed)
    if device.startswith("cuda") and not torch.cuda.is_available():
        device = "cpu"

    train_files = select_files(sorted(Path(train_dir).glob("sample_*.npz")), max_train_samples, seed=seed + 101)
    val_files = []
    if val_dir is not None and Path(val_dir).exists():
        val_files = select_files(sorted(Path(val_dir).glob("sample_*.npz")), max_val_samples, seed=seed + 103)

    train_ds = GridHeuristicDataset(train_files, sigma=2.5, mode="start_goal")
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = None
    if val_files:
        val_ds = GridHeuristicDataset(val_files, sigma=2.5, mode="start_goal")
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    model = NeuralAStarNet(in_channels=3, base=32).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="min", factor=0.5, patience=1)

    history = {"train_loss": [], "val_loss": [], "lr": []}

    for _epoch in range(1, max(int(epochs), 1) + 1):
        model.train()
        train_loss = 0.0
        n = 0
        for batch in train_loader:
            x = batch["input"].to(device)
            y = batch["target"].to(device)
            m = batch["mask"].to(device)

            opt.zero_grad(set_to_none=True)
            pred = model(x)
            loss = _masked_l1(pred, y, m)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()

            train_loss += float(loss.item())
            n += 1
        train_loss = train_loss / max(n, 1)

        val_loss = train_loss
        if val_loader is not None:
            model.eval()
            total = 0.0
            k = 0
            with torch.no_grad():
                for batch in val_loader:
                    x = batch["input"].to(device)
                    y = batch["target"].to(device)
                    m = batch["mask"].to(device)
                    pred = model(x)
                    loss = _masked_l1(pred, y, m)
                    total += float(loss.item())
                    k += 1
            val_loss = total / max(k, 1)

        scheduler.step(val_loss)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["lr"].append(float(opt.param_groups[0]["lr"]))

    model.eval()
    solver = NeuralAStarLite(model=model, device=torch.device(device), sigma=2.5)
    solver.save(checkpoint_out)

    return {
        "checkpoint": str(checkpoint_out),
        "num_train": len(train_files),
        "num_val": len(val_files),
        "history": history,
    }
