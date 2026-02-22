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
from network.model import build_model


def _masked_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    loss_weight: torch.Tensor,
    sample_weight: torch.Tensor | None,
    underestimation_weight: float,
    hard_mask: torch.Tensor | None = None,
    hard_underestimation_weight: float | None = None,
    hard_overestimation_weight: float = 0.0,
    narrow_mask: torch.Tensor | None = None,
    narrow_overestimation_weight: float = 0.0,
    temporal_steps: int = 1,
    yaw_bins: int | None = None,
    temporal_lambda: float = 0.1,
    hard_rank_lambda: float = 0.0,
    hard_rank_topk: int = 64,
    hard_rank_margin: float = 0.01,
) -> torch.Tensor:
    err = pred - target
    sq = err**2
    under = (err < 0.0).to(pred.dtype)
    under_weight = torch.full_like(err, float(max(underestimation_weight, 1e-3)))
    if hard_mask is not None and hard_underestimation_weight is not None:
        hm = hard_mask.to(pred.dtype).view(-1, 1, 1, 1)
        hw = float(max(hard_underestimation_weight, 1e-3))
        under_weight = under_weight * (1.0 - hm) + hw * hm
    asym = sq * (1.0 + (under_weight - 1.0) * under)
    w = mask * loss_weight
    if sample_weight is not None:
        w = w * sample_weight.to(pred.dtype).view(-1, 1, 1, 1)
    denom = w.sum().clamp_min(1.0)
    base_loss = (asym * w).sum() / denom

    if float(hard_overestimation_weight) > 0.0:
        over = torch.relu(err)
        ow = w
        if hard_mask is not None:
            ow = ow * hard_mask.to(pred.dtype).view(-1, 1, 1, 1)
        oden = ow.sum().clamp_min(1.0)
        base_loss = base_loss + float(hard_overestimation_weight) * ((over * ow).sum() / oden)

    if float(narrow_overestimation_weight) > 0.0 and narrow_mask is not None:
        nm = narrow_mask.to(pred.dtype)
        if nm.ndim == 3:
            nm = nm.unsqueeze(1)
        if nm.shape[1] == 1 and pred.shape[1] != 1:
            nm = nm.expand(-1, pred.shape[1], -1, -1)
        ow_n = w * nm
        oden_n = ow_n.sum().clamp_min(1.0)
        base_loss = base_loss + float(narrow_overestimation_weight) * ((torch.relu(err) * ow_n).sum() / oden_n)

    total_loss = base_loss

    yb = int(yaw_bins) if yaw_bins is not None else int(pred.shape[1])
    t_steps = int(max(temporal_steps, 1))
    if float(temporal_lambda) > 0.0 and t_steps > 1 and yb > 0 and pred.shape[1] == t_steps * yb:
        bsz, _, h, w2 = pred.shape
        pred_t = pred.view(bsz, t_steps, yb, h, w2)
        mask_t = mask.view(bsz, t_steps, yb, h, w2)
        temporal_mask = (mask_t[:, 1:] * mask_t[:, :-1]).to(pred.dtype)
        if sample_weight is not None:
            temporal_mask = temporal_mask * sample_weight.to(pred.dtype).view(-1, 1, 1, 1, 1)
        temporal_diff = torch.abs(pred_t[:, 1:] - pred_t[:, :-1])
        temporal_denom = temporal_mask.sum().clamp_min(1.0)
        temporal_loss = (temporal_diff * temporal_mask).sum() / temporal_denom
        total_loss = total_loss + float(temporal_lambda) * temporal_loss

    # Search-aware ranking consistency for hard scenes:
    # enforce that states with larger teacher residual keep larger predicted residual.
    if float(hard_rank_lambda) > 0.0 and hard_mask is not None:
        margin = float(max(hard_rank_margin, 0.0))
        rank_terms: list[torch.Tensor] = []
        hard_ids = (hard_mask.to(pred.dtype).view(-1) > 0.5).nonzero(as_tuple=False).view(-1)
        for b in hard_ids:
            valid = (mask[b] > 0.5)
            n_valid = int(valid.sum().item())
            if n_valid < 8:
                continue
            t = target[b][valid]
            p = pred[b][valid]
            if t.numel() < 8:
                continue
            k = int(min(max(int(hard_rank_topk), 2), int(t.numel() // 2)))
            if k < 2:
                continue
            hi = torch.topk(t, k=k, largest=True).indices
            lo = torch.topk(t, k=k, largest=False).indices
            p_hi = p[hi].unsqueeze(1)
            p_lo = p[lo].unsqueeze(0)
            rank_terms.append(torch.relu(margin - (p_hi - p_lo)).mean())
        if rank_terms:
            rank_loss = torch.stack(rank_terms).mean()
            total_loss = total_loss + float(hard_rank_lambda) * rank_loss

    return total_loss


def _eval(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    underestimation_weight: float,
    hard_underestimation_weight: float | None = None,
    hard_overestimation_weight: float = 0.0,
    narrow_overestimation_weight: float = 0.0,
    hard_rank_lambda: float = 0.0,
    hard_rank_topk: int = 64,
    hard_rank_margin: float = 0.01,
) -> float:
    model.eval()
    total = 0.0
    count = 0
    with torch.no_grad():
        for batch in loader:
            x = batch["input"].to(device, non_blocking=True)
            y = batch["target"].to(device, non_blocking=True)
            m = batch["mask"].to(device, non_blocking=True)
            lw = batch["loss_weight"].to(device, non_blocking=True)
            sw = batch.get("sample_weight")
            if sw is not None:
                sw = sw.to(device, non_blocking=True)
            hm = batch.get("is_hard")
            if hm is not None:
                hm = hm.to(device, non_blocking=True)
            nm = batch.get("narrow_mask")
            if nm is not None:
                nm = nm.to(device, non_blocking=True)
            t_steps = int(batch.get("temporal_steps", torch.tensor([1]))[0].item())
            yaw_bins = int(batch.get("yaw_bins", torch.tensor([y.shape[1]]))[0].item())
            pred = model(x)
            loss = _masked_loss(
                pred,
                y,
                m,
                lw,
                sw,
                underestimation_weight=underestimation_weight,
                hard_mask=hm,
                hard_underestimation_weight=hard_underestimation_weight,
                hard_overestimation_weight=hard_overestimation_weight,
                narrow_mask=nm,
                narrow_overestimation_weight=narrow_overestimation_weight,
                temporal_steps=t_steps,
                yaw_bins=yaw_bins,
                temporal_lambda=0.1,
                hard_rank_lambda=hard_rank_lambda,
                hard_rank_topk=hard_rank_topk,
                hard_rank_margin=hard_rank_margin,
            )
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
        type_c_loss_weight=cfg.train.type_c_loss_weight,
    )
    val_ds = HeuristicFieldDataset(
        val_dir,
        gaussian_sigma=cfg.dataset.gaussian_sigma,
        distance_weight_scale_m=cfg.train.distance_weight_scale_m,
        distance_weight_min=cfg.train.distance_weight_min,
        hybrid_obstacle_alpha=cfg.dataset.hybrid_obstacle_alpha,
        hybrid_obstacle_threshold_m=cfg.dataset.hybrid_obstacle_threshold_m,
        prediction_mode=cfg.train.prediction_mode,
        type_c_loss_weight=cfg.train.type_c_loss_weight,
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

    model_base = 64
    model_name = "smallunet"
    model = build_model(
        model_name=model_name,
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
    hard_under_w = float(getattr(cfg.train, "hard_underestimation_weight", cfg.train.underestimation_weight))
    hard_over_w = float(getattr(cfg.train, "hard_overestimation_weight", 0.0))
    narrow_over_w = float(getattr(cfg.train, "narrow_overestimation_weight", 0.0))
    hard_rank_lambda = float(getattr(cfg.train, "hard_rank_lambda", 0.0))
    hard_rank_topk = int(getattr(cfg.train, "hard_rank_topk", 64))
    hard_rank_margin = float(getattr(cfg.train, "hard_rank_margin", 0.01))

    for epoch in range(cfg.train.epochs):
        model.train()
        epoch_loss = 0.0
        n = 0

        for batch in train_loader:
            x = batch["input"].to(device, non_blocking=True)
            y = batch["target"].to(device, non_blocking=True)
            m = batch["mask"].to(device, non_blocking=True)
            lw = batch["loss_weight"].to(device, non_blocking=True)
            sw = batch.get("sample_weight")
            if sw is not None:
                sw = sw.to(device, non_blocking=True)
            hm = batch.get("is_hard")
            if hm is not None:
                hm = hm.to(device, non_blocking=True)
            nm = batch.get("narrow_mask")
            if nm is not None:
                nm = nm.to(device, non_blocking=True)
            t_steps = int(batch.get("temporal_steps", torch.tensor([1]))[0].item())
            yaw_bins = int(batch.get("yaw_bins", torch.tensor([y.shape[1]]))[0].item())

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                pred = model(x)
                loss = _masked_loss(
                    pred,
                    y,
                    m,
                    lw,
                    sw,
                    underestimation_weight=cfg.train.underestimation_weight,
                    hard_mask=hm,
                    hard_underestimation_weight=hard_under_w,
                    hard_overestimation_weight=hard_over_w,
                    narrow_mask=nm,
                    narrow_overestimation_weight=narrow_over_w,
                    temporal_steps=t_steps,
                    yaw_bins=yaw_bins,
                    temporal_lambda=0.1,
                    hard_rank_lambda=hard_rank_lambda,
                    hard_rank_topk=hard_rank_topk,
                    hard_rank_margin=hard_rank_margin,
                )

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()

            epoch_loss += float(loss.item())
            n += 1

        train_loss = epoch_loss / max(n, 1)
        val_loss = _eval(
            model,
            val_loader,
            device,
            underestimation_weight=cfg.train.underestimation_weight,
            hard_underestimation_weight=hard_under_w,
            hard_overestimation_weight=hard_over_w,
            narrow_overestimation_weight=narrow_over_w,
            hard_rank_lambda=hard_rank_lambda,
            hard_rank_topk=hard_rank_topk,
            hard_rank_margin=hard_rank_margin,
        )
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
        "model_name": model_name,
        "temporal_steps": int(train_ds[0].get("temporal_steps", torch.tensor(1)).item()),
        "heuristic_yaw_bins": int(train_ds[0].get("yaw_bins", torch.tensor(out_channels)).item()),
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
        "type_c_loss_weight": float(cfg.train.type_c_loss_weight),
    }

    log_path = cfg.paths.logs_dir / "train_metrics.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(metrics | history, f, indent=2)

    return ckpt_path, metrics
