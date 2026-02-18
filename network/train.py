from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Tuple

import torch
from torch.utils.data import DataLoader

from config import ExperimentConfig
from network.dataset import HeuristicFieldDataset
from network.model import TinyUNet


def _masked_loss(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    err = pred - target
    over = torch.relu(err)
    base = err**2
    asym = base + 3.0 * (over**2)
    denom = mask.sum().clamp_min(1.0)
    return (asym * mask).sum() / denom


def _eval(model: torch.nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    total = 0.0
    count = 0
    with torch.no_grad():
        for batch in loader:
            x = batch["input"].to(device)
            y = batch["target"].to(device)
            m = batch["mask"].to(device)
            pred = model(x)
            loss = _masked_loss(pred, y, m)
            total += float(loss.item())
            count += 1
    return total / max(count, 1)


def train_network(cfg: ExperimentConfig, train_dir: Path, val_dir: Path) -> Tuple[Path, Dict[str, float]]:
    device = torch.device(cfg.train.device)
    train_ds = HeuristicFieldDataset(train_dir, gaussian_sigma=cfg.dataset.gaussian_sigma)
    val_ds = HeuristicFieldDataset(val_dir, gaussian_sigma=cfg.dataset.gaussian_sigma)

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.train.batch_size,
        shuffle=True,
        num_workers=cfg.train.num_workers,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.train.batch_size,
        shuffle=False,
        num_workers=cfg.train.num_workers,
    )

    model = TinyUNet(in_channels=4, base=32).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=cfg.train.learning_rate,
        weight_decay=cfg.train.weight_decay,
    )

    best_val = float("inf")
    history = {"train_loss": [], "val_loss": []}
    best_state = None

    for epoch in range(cfg.train.epochs):
        model.train()
        epoch_loss = 0.0
        n = 0

        for batch in train_loader:
            x = batch["input"].to(device)
            y = batch["target"].to(device)
            m = batch["mask"].to(device)

            pred = model(x)
            loss = _masked_loss(pred, y, m)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()

            epoch_loss += float(loss.item())
            n += 1

        train_loss = epoch_loss / max(n, 1)
        val_loss = _eval(model, val_loader, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}

    ckpt_dir = cfg.paths.checkpoints_dir
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / "heuristic_net.pt"

    payload = {
        "model_state": best_state,
        "history": history,
        "config": asdict(cfg),
    }
    torch.save(payload, ckpt_path)

    metrics = {
        "best_val_loss": float(best_val),
        "final_train_loss": float(history["train_loss"][-1]),
        "final_val_loss": float(history["val_loss"][-1]),
    }

    log_path = cfg.paths.logs_dir / "train_metrics.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(metrics | history, f, indent=2)

    return ckpt_path, metrics
