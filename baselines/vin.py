from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from baselines.common import GridHeuristicDataset, select_files
from utils.common import gaussian_2d, set_seed


class VINCore(nn.Module):
    def __init__(self, in_channels: int = 2, k: int = 20, hidden: int = 32) -> None:
        super().__init__()
        self.k = int(k)
        self.reward = nn.Sequential(
            nn.Conv2d(in_channels, hidden, kernel_size=3, padding=1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, 1, kernel_size=1, padding=0, bias=True),
        )
        self.q = nn.Conv2d(2, 8, kernel_size=3, padding=1, bias=False)
        self.head = nn.Sequential(
            nn.Conv2d(2, hidden, kernel_size=3, padding=1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, 1, kernel_size=1, padding=0, bias=True),
            nn.Softplus(beta=1.0),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        r = self.reward(x)
        v = torch.zeros_like(r)
        for _ in range(self.k):
            q = self.q(torch.cat([r, v], dim=1))
            v, _ = torch.max(q, dim=1, keepdim=True)
        out = self.head(torch.cat([r, v], dim=1))
        return out


@dataclass
class VINLite:
    model: VINCore
    device: torch.device
    sigma: float = 2.5

    @classmethod
    def load(cls, checkpoint: Path, device: str = "cpu") -> "VINLite":
        if device.startswith("cuda") and not torch.cuda.is_available():
            device = "cpu"
        payload = torch.load(checkpoint, map_location=device, weights_only=False)
        model = VINCore(
            in_channels=int(payload.get("in_channels", 2)),
            k=int(payload.get("k", 20)),
            hidden=int(payload.get("hidden", 32)),
        )
        model.load_state_dict(payload["model_state"])
        model.eval()
        return cls(model=model.to(device), device=torch.device(device), sigma=float(payload.get("sigma", 2.5)))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state": self.model.state_dict(),
                "in_channels": 2,
                "k": self.model.k,
                "hidden": 32,
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
        del start
        occ = occupancy.astype(np.float32)
        h, w = occ.shape

        gx = goal[0] / resolution - 0.5
        gy = goal[1] / resolution - 0.5
        goal_map = gaussian_2d(h, w, gx, gy, self.sigma)

        x = np.stack([occ, goal_map], axis=0).astype(np.float32)
        xt = torch.from_numpy(x[None, ...]).to(self.device)
        pred = self.model(xt).cpu().numpy()[0, 0]
        scale = np.hypot(h * resolution, w * resolution)
        out = (pred * scale).astype(np.float32)
        out[occupancy.astype(bool)] = 1e6
        return out


def _masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    diff = (pred - target) ** 2 * mask
    denom = torch.clamp(mask.sum(), min=1.0)
    return diff.sum() / denom


def train_vin(
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

    train_files = select_files(sorted(Path(train_dir).glob("sample_*.npz")), max_train_samples, seed=seed + 211)
    val_files = []
    if val_dir is not None and Path(val_dir).exists():
        val_files = select_files(sorted(Path(val_dir).glob("sample_*.npz")), max_val_samples, seed=seed + 223)

    train_ds = GridHeuristicDataset(train_files, sigma=2.5, mode="goal_only")
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = None
    if val_files:
        val_ds = GridHeuristicDataset(val_files, sigma=2.5, mode="goal_only")
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    model = VINCore(in_channels=2, k=20, hidden=32).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="min", factor=0.5, patience=1)

    history = {"train_loss": [], "val_loss": [], "lr": []}

    for _epoch in range(1, max(int(epochs), 1) + 1):
        model.train()
        total = 0.0
        n = 0
        for batch in train_loader:
            x = batch["input"].to(device)
            y = batch["target"].to(device)
            m = batch["mask"].to(device)

            opt.zero_grad(set_to_none=True)
            pred = model(x)
            loss = _masked_mse(pred, y, m)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()

            total += float(loss.item())
            n += 1
        train_loss = total / max(n, 1)

        val_loss = train_loss
        if val_loader is not None:
            model.eval()
            total_val = 0.0
            k = 0
            with torch.no_grad():
                for batch in val_loader:
                    x = batch["input"].to(device)
                    y = batch["target"].to(device)
                    m = batch["mask"].to(device)
                    pred = model(x)
                    loss = _masked_mse(pred, y, m)
                    total_val += float(loss.item())
                    k += 1
            val_loss = total_val / max(k, 1)

        scheduler.step(val_loss)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["lr"].append(float(opt.param_groups[0]["lr"]))

    model.eval()
    solver = VINLite(model=model, device=torch.device(device), sigma=2.5)
    solver.save(checkpoint_out)

    return {
        "checkpoint": str(checkpoint_out),
        "num_train": len(train_files),
        "num_val": len(val_files),
        "history": history,
    }
