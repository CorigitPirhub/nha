from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader

from config import ExperimentConfig
from network.dataset import HeuristicFieldDataset
from network.model import TinyUNet


def _masked_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    loss_weight: torch.Tensor,
    underestimation_weight: float,
) -> torch.Tensor:
    err = pred - target
    sq = err**2
    under = (err < 0.0).to(pred.dtype)
    asym = sq * (1.0 + (float(underestimation_weight) - 1.0) * under)
    w = mask * loss_weight
    denom = w.sum().clamp_min(1.0)
    return (asym * w).sum() / denom


def _eval(model: torch.nn.Module, loader: DataLoader, device: torch.device, underestimation_weight: float) -> float:
    model.eval()
    total = 0.0
    count = 0
    with torch.no_grad():
        for batch in loader:
            x = batch["input"].to(device, non_blocking=True)
            y = batch["target"].to(device, non_blocking=True)
            m = batch["mask"].to(device, non_blocking=True)
            lw = batch["loss_weight"].to(device, non_blocking=True)
            pred = model(x)
            loss = _masked_loss(pred, y, m, lw, underestimation_weight=underestimation_weight)
            total += float(loss.item())
            count += 1
    return total / max(count, 1)


def _load_init_checkpoint(model: torch.nn.Module, init_checkpoint: Path | None) -> None:
    if init_checkpoint is None:
        return
    payload = torch.load(init_checkpoint, map_location="cpu", weights_only=False)
    src = payload.get("model_state", payload) if isinstance(payload, dict) else payload
    if not isinstance(src, dict):
        raise RuntimeError(f"Unsupported checkpoint format: {init_checkpoint}")

    dst = model.state_dict()
    matched = {}
    skipped = 0
    for k, v in src.items():
        if k in dst and tuple(dst[k].shape) == tuple(v.shape):
            matched[k] = v
        else:
            skipped += 1
    dst.update(matched)
    model.load_state_dict(dst, strict=False)
    print(f"[init] loaded {len(matched)} params from {init_checkpoint} (skipped={skipped})")


def train_network(
    cfg: ExperimentConfig,
    train_dir: Path,
    val_dir: Path,
    init_checkpoint: Path | None = None,
) -> Tuple[Path, Dict[str, float]]:
    requested_device = cfg.train.device
    if requested_device.startswith("cuda") and not torch.cuda.is_available():
        print("[warning] CUDA requested but unavailable, fallback to CPU.")
        requested_device = "cpu"
    device = torch.device(requested_device)

    train_ds = HeuristicFieldDataset(
        train_dir,
        gaussian_sigma=cfg.dataset.gaussian_sigma,
        distance_weight_scale_m=cfg.train.distance_weight_scale_m,
        distance_weight_min=cfg.train.distance_weight_min,
        hybrid_obstacle_alpha=cfg.dataset.hybrid_obstacle_alpha,
        hybrid_obstacle_threshold_m=cfg.dataset.hybrid_obstacle_threshold_m,
        prediction_mode=cfg.train.prediction_mode,
    )
    val_ds = HeuristicFieldDataset(
        val_dir,
        gaussian_sigma=cfg.dataset.gaussian_sigma,
        distance_weight_scale_m=cfg.train.distance_weight_scale_m,
        distance_weight_min=cfg.train.distance_weight_min,
        hybrid_obstacle_alpha=cfg.dataset.hybrid_obstacle_alpha,
        hybrid_obstacle_threshold_m=cfg.dataset.hybrid_obstacle_threshold_m,
        prediction_mode=cfg.train.prediction_mode,
    )

    out_channels = int(train_ds[0]["target"].shape[0])
    in_channels = int(train_ds[0]["input"].shape[0])
    output_activation = "identity" if cfg.train.prediction_mode == "residual" else "softplus"

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.train.batch_size,
        shuffle=True,
        num_workers=cfg.train.num_workers,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.train.batch_size,
        shuffle=False,
        num_workers=cfg.train.num_workers,
        pin_memory=(device.type == "cuda"),
    )

    model_base = 48
    model = TinyUNet(
        in_channels=in_channels,
        out_channels=out_channels,
        base=model_base,
        output_activation=output_activation,
    ).to(device)
    _load_init_checkpoint(model, init_checkpoint)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=cfg.train.learning_rate,
        weight_decay=cfg.train.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(cfg.train.epochs, 1),
        eta_min=cfg.train.learning_rate * float(np.clip(cfg.train.cosine_eta_min_ratio, 0.0, 1.0)),
    )

    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    best_val = float("inf")
    history = {"train_loss": [], "val_loss": [], "lr": []}
    best_state = None

    for epoch in range(cfg.train.epochs):
        model.train()
        epoch_loss = 0.0
        n = 0

        for batch in train_loader:
            x = batch["input"].to(device, non_blocking=True)
            y = batch["target"].to(device, non_blocking=True)
            m = batch["mask"].to(device, non_blocking=True)
            lw = batch["loss_weight"].to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                pred = model(x)
                loss = _masked_loss(
                    pred,
                    y,
                    m,
                    lw,
                    underestimation_weight=cfg.train.underestimation_weight,
                )

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()

            epoch_loss += float(loss.item())
            n += 1

        train_loss = epoch_loss / max(n, 1)
        val_loss = _eval(model, val_loader, device, underestimation_weight=cfg.train.underestimation_weight)
        history["lr"].append(float(optimizer.param_groups[0]["lr"]))
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        print(
            f"epoch {epoch + 1:02d}/{cfg.train.epochs} "
            f"lr={optimizer.param_groups[0]['lr']:.3e} train={train_loss:.5f} val={val_loss:.5f}"
        )

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}

        scheduler.step()

    ckpt_dir = cfg.paths.checkpoints_dir
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / "heuristic_net.pt"

    payload = {
        "model_state": best_state,
        "history": history,
        "config": asdict(cfg),
        "in_channels": in_channels,
        "out_channels": out_channels,
        "base_channels": model_base,
        "prediction_mode": cfg.train.prediction_mode,
        "output_activation": output_activation,
        "residual_nonnegative": bool(cfg.train.prediction_mode == "residual"),
    }
    torch.save(payload, ckpt_path)

    metrics = {
        "best_val_loss": float(best_val),
        "final_train_loss": float(history["train_loss"][-1]),
        "final_val_loss": float(history["val_loss"][-1]),
        "final_lr": float(history["lr"][-1]) if history["lr"] else float(cfg.train.learning_rate),
        "device": str(device),
        "in_channels": in_channels,
        "out_channels": out_channels,
        "prediction_mode": cfg.train.prediction_mode,
    }

    log_path = cfg.paths.logs_dir / "train_metrics.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(metrics | history, f, indent=2)

    return ckpt_path, metrics
