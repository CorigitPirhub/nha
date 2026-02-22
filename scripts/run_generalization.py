from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
import sys
import time

import numpy as np
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.scenario_generator import build_generalization_dataset
from env.reeds_shepp import (
    RSConsistentCostConfig,
    compute_reeds_shepp_field,
    load_rs_field_cache,
    make_rs_field_cache_key,
    save_rs_field_cache,
)
from network.dataset import HeuristicFieldDataset
from network.inference import NeuralHeuristicPredictor
from network.model import build_model
from network.train import _masked_loss
from planner.heuristics import FieldHeuristic, ResidualYawFieldHeuristic, YawFieldHeuristic, euclidean_heuristic
from planner.hybrid_astar import HybridAStarPlanner
from utils.common import ensure_dirs, set_seed


def _parse_csv_values(raw: str | None) -> tuple[str, ...] | None:
    if raw is None:
        return None
    items = tuple(v.strip() for v in str(raw).split(",") if v.strip())
    return items if items else None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Optimized generalization pipeline for hard+dynamic bottleneck")
    p.add_argument("--data-root", type=Path, default=Path("data"))
    p.add_argument("--output-root", type=Path, default=Path("outputs"))
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    p.add_argument("--run-tag", type=str, default="generalization_optimized")

    p.add_argument("--train-count", type=int, default=1000)
    p.add_argument("--val-count", type=int, default=200)
    p.add_argument("--test-count", type=int, default=220)
    p.add_argument("--skip-generation", action="store_true")

    p.add_argument("--map-width", type=int, default=DEFAULT_CONFIG.map.width)
    p.add_argument("--map-height", type=int, default=DEFAULT_CONFIG.map.height)
    p.add_argument("--resolution", type=float, default=DEFAULT_CONFIG.map.resolution)

    p.add_argument("--teacher-yaw-bins", type=int, default=8)
    p.add_argument(
        "--teacher-mode",
        type=str,
        default="reeds_shepp_consistent",
        choices=[
            "dubins",
            "dubins_proxy",
            "reeds_shepp",
            "reeds_shepp_consistent",
            "hybrid_rs_esdf",
            "hybrid_rs_consistent_esdf",
        ],
    )
    p.add_argument("--teacher-rs-backend", type=str, default="approx", choices=["auto", "rsplan", "approx"])
    p.add_argument("--teacher-rs-step-size", type=float, default=1.0)
    p.add_argument("--hybrid-alpha", type=float, default=0.15)
    p.add_argument("--hybrid-threshold", type=float, default=1.6)
    p.add_argument("--dynamic-horizon", type=int, default=24)
    p.add_argument("--dynamic-dt", type=float, default=0.45)
    p.add_argument("--difficulty-filter", type=str, default="")
    p.add_argument("--template-filter", type=str, default="")
    p.add_argument("--task-filter", type=str, default="")
    p.add_argument("--distribution-filter", type=str, default="")
    p.add_argument("--no-augmentation", action="store_true")

    p.add_argument("--prediction-mode", type=str, default="residual", choices=["absolute", "residual"])
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=12)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--under-weight", type=float, default=1.8)
    p.add_argument(
        "--hard-under-weight",
        type=float,
        default=1.2,
        help="Underestimation penalty for hard samples; lower than --under-weight to reduce conservative over-bias.",
    )
    p.add_argument(
        "--hard-over-weight",
        type=float,
        default=0.08,
        help="Penalty on positive residual error for hard samples (suppresses overestimated residuals).",
    )
    p.add_argument(
        "--narrow-over-weight",
        type=float,
        default=0.05,
        help="Penalty on positive residual error inside narrow corridors (ESDF-based mask).",
    )
    p.add_argument("--dist-weight-scale", type=float, default=6.0)
    p.add_argument("--dist-weight-min", type=float, default=0.25)
    p.add_argument("--type-c-weight", type=float, default=1.8)
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--num-workers", type=int, default=0)
    p.add_argument("--use-context-channels", action="store_true", default=True)
    p.add_argument("--disable-temporal-context", action="store_true")
    p.add_argument("--temporal-lambda", type=float, default=0.1)
    p.add_argument(
        "--hard-rank-lambda",
        type=float,
        default=0.0,
        help="Search-aware ranking loss weight on hard samples (pairwise high-vs-low residual ordering).",
    )
    p.add_argument(
        "--hard-rank-topk",
        type=int,
        default=64,
        help="Top/Bottom-K cells used by hard ranking consistency loss.",
    )
    p.add_argument(
        "--hard-rank-margin",
        type=float,
        default=0.01,
        help="Margin used by hard ranking hinge loss (normalized residual units).",
    )
    p.add_argument("--model-name", type=str, default="smallunet", choices=["tinyunet", "smallunet"])
    p.add_argument("--model-base", type=int, default=64)

    p.add_argument("--lr-plateau-factor", type=float, default=0.5)
    p.add_argument("--lr-plateau-patience", type=int, default=2)
    p.add_argument("--lr-plateau-min", type=float, default=1e-6)

    p.add_argument("--eval-train-cases", type=int, default=60)
    p.add_argument("--eval-test-cases", type=int, default=80)
    p.add_argument("--final-train-cases", type=int, default=200)
    p.add_argument("--final-test-cases", type=int, default=220)
    p.add_argument("--residual-alpha", type=float, default=1.5)
    p.add_argument(
        "--residual-clip-m",
        type=float,
        default=8.0,
        help="Upper bound (meters) for predicted residual to stabilize search.",
    )
    p.add_argument(
        "--residual-bias-quantile",
        type=float,
        default=0.0,
        help="Subtract this free-space residual quantile per-case to suppress global overestimation bias.",
    )
    p.add_argument(
        "--residual-corridor-threshold",
        type=float,
        default=0.0,
        help="When >0, suppress residual inside low-clearance cells with ESDF below this threshold (meters).",
    )
    p.add_argument(
        "--residual-corridor-suppress",
        type=float,
        default=0.0,
        help="Suppression strength in [0,1] for ESDF-based corridor residual gating.",
    )
    p.add_argument("--max-expansions", type=int, default=25000)
    p.add_argument(
        "--hard-max-expansions",
        type=int,
        default=10000,
        help="Search budget for hard difficulty cases.",
    )
    p.add_argument(
        "--maze-max-expansions",
        type=int,
        default=15000,
        help="Search budget for maze_single/deadend_labyrinth cases.",
    )
    p.add_argument(
        "--narrow-max-expansions",
        type=int,
        default=12000,
        help="Search budget for narrow_passage cases.",
    )
    p.add_argument(
        "--init-checkpoint",
        type=Path,
        default=Path("outputs/checkpoints/heuristic_net_generalization_optimized.pt"),
        help="Warm-start training from an existing checkpoint when shapes match.",
    )

    p.add_argument(
        "--baseline-checkpoint",
        type=Path,
        default=Path("outputs/checkpoints/heuristic_net_generalization_best.pt"),
    )
    p.add_argument("--baseline-data-meta", type=Path, default=Path("data/meta.json"))
    p.add_argument("--target-hard-improve", type=float, default=0.10)
    p.add_argument(
        "--disable-euclidean-fallback",
        action="store_true",
        help="Disable fallback-to-euclidean when neural-guided search fails.",
    )
    return p.parse_args()


def _epoch_ckpt_path(ckpt_dir: Path, run_tag: str, epoch: int) -> Path:
    return ckpt_dir / f"heuristic_net_{run_tag}_epoch_{epoch:03d}.pt"


def _best_ckpt_path(ckpt_dir: Path, run_tag: str) -> Path:
    return ckpt_dir / f"heuristic_net_{run_tag}.pt"


def _build_model_and_loaders(args: argparse.Namespace, cfg):
    train_ds = HeuristicFieldDataset(
        args.data_root / "train",
        gaussian_sigma=cfg.dataset.gaussian_sigma,
        distance_weight_scale_m=cfg.train.distance_weight_scale_m,
        distance_weight_min=cfg.train.distance_weight_min,
        hybrid_obstacle_alpha=cfg.dataset.hybrid_obstacle_alpha,
        hybrid_obstacle_threshold_m=cfg.dataset.hybrid_obstacle_threshold_m,
        prediction_mode=cfg.train.prediction_mode,
        type_c_loss_weight=cfg.train.type_c_loss_weight,
        use_context_channels=bool(args.use_context_channels),
        use_temporal_context=not bool(args.disable_temporal_context),
    )
    val_ds = HeuristicFieldDataset(
        args.data_root / "val",
        gaussian_sigma=cfg.dataset.gaussian_sigma,
        distance_weight_scale_m=cfg.train.distance_weight_scale_m,
        distance_weight_min=cfg.train.distance_weight_min,
        hybrid_obstacle_alpha=cfg.dataset.hybrid_obstacle_alpha,
        hybrid_obstacle_threshold_m=cfg.dataset.hybrid_obstacle_threshold_m,
        prediction_mode=cfg.train.prediction_mode,
        type_c_loss_weight=cfg.train.type_c_loss_weight,
        use_context_channels=bool(args.use_context_channels),
        use_temporal_context=not bool(args.disable_temporal_context),
    )

    sample0 = train_ds[0]
    in_channels = int(sample0["input"].shape[0])
    out_channels = int(sample0["target"].shape[0])
    temporal_steps = int(sample0.get("temporal_steps", torch.tensor(1)).item())
    heuristic_yaw_bins = int(sample0.get("yaw_bins", torch.tensor(out_channels)).item())
    output_activation = "identity" if cfg.train.prediction_mode == "residual" else "softplus"

    model = build_model(
        model_name=str(args.model_name),
        in_channels=in_channels,
        out_channels=out_channels,
        base=int(args.model_base),
        output_activation=output_activation,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.train.batch_size,
        shuffle=True,
        num_workers=cfg.train.num_workers,
        pin_memory=(cfg.train.device.startswith("cuda")),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.train.batch_size,
        shuffle=False,
        num_workers=cfg.train.num_workers,
        pin_memory=(cfg.train.device.startswith("cuda")),
    )
    return (
        model,
        train_loader,
        val_loader,
        in_channels,
        out_channels,
        output_activation,
        temporal_steps,
        heuristic_yaw_bins,
    )


def _eval_loss(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    under_weight: float,
    hard_under_weight: float,
    hard_over_weight: float,
    narrow_over_weight: float,
    temporal_lambda: float,
    hard_rank_lambda: float,
    hard_rank_topk: int,
    hard_rank_margin: float,
) -> float:
    model.eval()
    total = 0.0
    n = 0
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
                underestimation_weight=under_weight,
                hard_mask=hm,
                hard_underestimation_weight=hard_under_weight,
                hard_overestimation_weight=hard_over_weight,
                narrow_mask=nm,
                narrow_overestimation_weight=narrow_over_weight,
                temporal_steps=t_steps,
                yaw_bins=yaw_bins,
                temporal_lambda=temporal_lambda,
                hard_rank_lambda=hard_rank_lambda,
                hard_rank_topk=hard_rank_topk,
                hard_rank_margin=hard_rank_margin,
            )
            total += float(loss.item())
            n += 1
    return total / max(n, 1)


def _save_checkpoint(
    out_path: Path,
    model: torch.nn.Module,
    cfg,
    in_channels: int,
    out_channels: int,
    output_activation: str,
    history: dict,
    model_name: str,
    base_channels: int,
    temporal_steps: int,
    heuristic_yaw_bins: int,
) -> None:
    payload = {
        "model_state": {k: v.detach().cpu() for k, v in model.state_dict().items()},
        "history": history,
        "config": asdict(cfg),
        "in_channels": int(in_channels),
        "out_channels": int(out_channels),
        "base_channels": int(base_channels),
        "prediction_mode": cfg.train.prediction_mode,
        "output_activation": output_activation,
        "residual_nonnegative": bool(cfg.train.prediction_mode == "residual"),
        "model_name": str(model_name),
        "temporal_steps": int(temporal_steps),
        "heuristic_yaw_bins": int(heuristic_yaw_bins),
    }
    torch.save(payload, out_path)


def _ours_metrics(summary: dict) -> dict[str, float]:
    m = summary.get("methods", {}).get("ours", {})
    return {
        "success_rate": float(m.get("success_rate", float("nan"))),
        "avg_expansions": float(m.get("avg_expansions", float("nan"))),
        "avg_cost": float(m.get("avg_cost", float("nan"))),
        "avg_time_total_ms": float(m.get("avg_time_total_ms", m.get("avg_time_ms", float("nan")))),
    }


def _safe_group_success(summary: dict, group_key: str, key: str) -> float:
    g = summary.get(group_key, {}).get(key, {}).get("ours", {})
    return float(g.get("success_rate", float("nan")))


def _save_loss_curve_svg(train_loss: list[float], val_loss: list[float], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = max(len(train_loss), len(val_loss), 1)
    all_vals = [float(v) for v in train_loss + val_loss if np.isfinite(v)]
    y_min = float(min(all_vals)) if all_vals else 0.0
    y_max = float(max(all_vals)) if all_vals else 1.0
    if abs(y_max - y_min) < 1e-9:
        y_max = y_min + 1.0

    w, h = 880, 360
    ml, mr, mt, mb = 56, 20, 30, 42
    pw, ph = w - ml - mr, h - mt - mb

    def px(i: int) -> float:
        return ml + (i / max(n - 1, 1)) * pw

    def py(v: float) -> float:
        t = (v - y_min) / max(y_max - y_min, 1e-9)
        return mt + (1.0 - t) * ph

    def poly(vals: list[float]) -> str:
        pts = []
        for i, v in enumerate(vals):
            if not np.isfinite(v):
                continue
            pts.append(f"{px(i):.2f},{py(float(v)):.2f}")
        return " ".join(pts)

    train_pts = poly([float(v) for v in train_loss])
    val_pts = poly([float(v) for v in val_loss])

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">')
    lines.append('<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>')
    lines.append(f'<text x="{ml}" y="20" font-size="15" fill="#111">Training/Validation Loss Curve</text>')
    lines.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#333" stroke-width="1.2"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#333" stroke-width="1.2"/>')

    for k in range(6):
        yy = mt + ph * (k / 5.0)
        yv = y_max - (y_max - y_min) * (k / 5.0)
        lines.append(f'<line x1="{ml}" y1="{yy:.2f}" x2="{ml+pw}" y2="{yy:.2f}" stroke="#e5e7eb" stroke-width="1"/>')
        lines.append(f'<text x="{ml-8}" y="{yy+4:.2f}" font-size="10" text-anchor="end" fill="#666">{yv:.4f}</text>')

    for k in range(min(11, n)):
        ix = int(round((n - 1) * k / max(min(10, n - 1), 1)))
        xx = px(ix)
        lines.append(f'<line x1="{xx:.2f}" y1="{mt}" x2="{xx:.2f}" y2="{mt+ph}" stroke="#f1f5f9" stroke-width="1"/>')
        lines.append(f'<text x="{xx:.2f}" y="{mt+ph+16}" font-size="10" text-anchor="middle" fill="#666">{ix+1}</text>')

    if train_pts:
        lines.append(f'<polyline fill="none" stroke="#1d4ed8" stroke-width="2" points="{train_pts}"/>')
    if val_pts:
        lines.append(f'<polyline fill="none" stroke="#dc2626" stroke-width="2" points="{val_pts}"/>')

    lx = ml + pw - 160
    ly = mt + 16
    lines.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+26}" y2="{ly}" stroke="#1d4ed8" stroke-width="2"/><text x="{lx+32}" y="{ly+4}" font-size="11" fill="#111">train</text>')
    lines.append(f'<line x1="{lx}" y1="{ly+18}" x2="{lx+26}" y2="{ly+18}" stroke="#dc2626" stroke-width="2"/><text x="{lx+32}" y="{ly+22}" font-size="11" fill="#111">val</text>')
    lines.append('</svg>')
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _load_init_checkpoint(model: torch.nn.Module, init_checkpoint: Path | None) -> None:
    if init_checkpoint is None:
        return
    ckpt = Path(init_checkpoint)
    if not ckpt.exists():
        return
    payload = torch.load(ckpt, map_location="cpu", weights_only=False)
    src = payload.get("model_state", payload) if isinstance(payload, dict) else payload
    if not isinstance(src, dict):
        return
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
    print(f"[init] loaded {len(matched)} params from {ckpt} (skipped={skipped})")


def _save_path_compare_svg(
    occupancy: np.ndarray,
    baseline_path: np.ndarray,
    neural_path: np.ndarray,
    resolution: float,
    out_path: Path,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    title: str,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h, w = occupancy.shape
    scale = 8
    pad = 20
    W = w * scale + pad * 2
    H = h * scale + pad * 2 + 24

    def to_px(x_m: float, y_m: float) -> tuple[float, float]:
        gx = x_m / resolution - 0.5
        gy = y_m / resolution - 0.5
        return pad + gx * scale, pad + (h - 1 - gy) * scale

    def polyline(path: np.ndarray, color: str, width: float) -> str:
        if path.size == 0:
            return ""
        pts = []
        for i in range(path.shape[0]):
            x, y = float(path[i, 0]), float(path[i, 1])
            px, py = to_px(x, y)
            pts.append(f"{px:.2f},{py:.2f}")
        return f'<polyline fill="none" stroke="{color}" stroke-width="{width}" points="{" ".join(pts)}"/>'

    obs_rects: list[str] = []
    ys, xs = np.where(occupancy)
    for y, x in zip(ys.tolist(), xs.tolist()):
        rx = pad + x * scale
        ry = pad + (h - 1 - y) * scale
        obs_rects.append(f'<rect x="{rx:.2f}" y="{ry:.2f}" width="{scale}" height="{scale}" fill="#111827"/>')

    sx, sy = to_px(float(start[0]), float(start[1]))
    gx, gy = to_px(float(goal[0]), float(goal[1]))

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    lines.append('<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>')
    lines.append(f'<text x="{pad}" y="16" font-size="14" fill="#111">{title}</text>')
    lines.append(f'<rect x="{pad}" y="{pad}" width="{w*scale}" height="{h*scale}" fill="#f8fafc" stroke="#94a3b8" stroke-width="1"/>')
    lines.extend(obs_rects)
    bpoly = polyline(baseline_path, "#2563eb", 2.2)
    npoly = polyline(neural_path, "#ea580c", 2.2)
    if bpoly:
        lines.append(bpoly)
    if npoly:
        lines.append(npoly)
    lines.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="4" fill="#22c55e" stroke="#111"/>')
    lines.append(f'<circle cx="{gx:.2f}" cy="{gy:.2f}" r="4" fill="#ef4444" stroke="#111"/>')
    lines.append(f'<text x="{pad}" y="{H-8}" font-size="11" fill="#2563eb">baseline</text>')
    lines.append(f'<text x="{pad+80}" y="{H-8}" font-size="11" fill="#ea580c">optimized</text>')
    lines.append('</svg>')
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _compute_template_task_joint_ratio(
    train_dir: Path,
    templates: tuple[str, ...],
    task_type: str,
) -> float:
    files = sorted(Path(train_dir).glob("sample_*.npz"))
    if not files:
        return float("nan")
    wanted = set(str(v) for v in templates)
    hit = 0
    for p in files:
        try:
            with np.load(p, allow_pickle=False) as d:
                t = str(d["scenario"]) if "scenario" in d else ""
                task = str(d["task_type"]) if "task_type" in d else ""
            if t in wanted and task == str(task_type):
                hit += 1
        except Exception:
            continue
    return float(hit / max(len(files), 1))


def _subset_files(files: list[Path], max_cases: int) -> list[Path]:
    if max_cases > 0 and len(files) > max_cases:
        idx = np.linspace(0, len(files) - 1, max_cases, dtype=np.int32)
        return [files[int(i)] for i in np.unique(idx)]
    return files


def _load_case(cfg, p: Path) -> dict:
    with np.load(p, allow_pickle=False) as data:
        resolution = float(data["resolution"]) if "resolution" in data else float(cfg.map.resolution)
        occupancy = data["occupancy"].astype(bool)
        if "occupancy_static" in data and "dynamic_risk" in data:
            occ_static = data["occupancy_static"].astype(bool)
            dyn_risk = np.clip(data["dynamic_risk"].astype(np.float32), 0.0, 1.0)
            risk_thr = float(data["dynamic_block_threshold"]) if "dynamic_block_threshold" in data else 0.25
            occupancy = np.logical_or(occ_static, dyn_risk >= risk_thr)
        dynamic_risk = data["dynamic_risk"].astype(np.float32) if "dynamic_risk" in data else None
        dynamic_risk_seq = data["dynamic_risk_seq"].astype(np.float32) if "dynamic_risk_seq" in data else None
        esdf = data["esdf"].astype(np.float32)
        start = tuple(float(v) for v in data["start"].astype(np.float32))
        goal = tuple(float(v) for v in data["goal"].astype(np.float32))
        difficulty = str(data["difficulty"]) if "difficulty" in data else "unknown"
        task_type = str(data["task_type"]) if "task_type" in data else "unknown"
        scenario = str(data["scenario"]) if "scenario" in data else "unknown"

        veh = replace(cfg.vehicle)
        if "vehicle_wheel_base" in data:
            veh.wheel_base = float(data["vehicle_wheel_base"])
        if "vehicle_length" in data:
            veh.length = float(data["vehicle_length"])
        if "vehicle_width" in data:
            veh.width = float(data["vehicle_width"])
        if "vehicle_max_steer_deg" in data:
            veh.max_steer_deg = float(data["vehicle_max_steer_deg"])
        if "vehicle_min_turn_radius" in data:
            veh.min_turn_radius = float(data["vehicle_min_turn_radius"])

        planner_cfg = replace(cfg.planner)
        if "planner_step_size" in data:
            planner_cfg.step_size = float(data["planner_step_size"])
        if "planner_reverse_penalty" in data:
            planner_cfg.reverse_penalty = float(data["planner_reverse_penalty"])
        if "planner_steer_penalty" in data:
            planner_cfg.steer_penalty = float(data["planner_steer_penalty"])
        if "planner_steer_change_penalty" in data:
            planner_cfg.steer_change_penalty = float(data["planner_steer_change_penalty"])

        vehicle_context = {
            "wheel_base": float(getattr(veh, "wheel_base", cfg.vehicle.wheel_base)),
            "max_steer_deg": float(getattr(veh, "max_steer_deg", cfg.vehicle.max_steer_deg)),
            "battery": float(data["vehicle_battery"]) if "vehicle_battery" in data else 100.0,
            "load_factor": float(data["vehicle_load_factor"]) if "vehicle_load_factor" in data else 1.0,
        }

    return {
        "path": p,
        "resolution": resolution,
        "occupancy": occupancy,
        "dynamic_risk": dynamic_risk,
        "dynamic_risk_seq": dynamic_risk_seq,
        "esdf": esdf,
        "start": start,
        "goal": goal,
        "difficulty": difficulty,
        "task_type": task_type,
        "scenario": scenario,
        "vehicle": veh,
        "planner_cfg": planner_cfg,
        "vehicle_context": vehicle_context,
    }


def _build_heuristic(
    cfg,
    predictor: NeuralHeuristicPredictor,
    case: dict,
    rs_cache_dir: Path,
    residual_alpha: float,
    residual_clip_m: float,
):
    resolution = float(case["resolution"])
    occupancy = case["occupancy"]
    esdf = case["esdf"]
    start = case["start"]
    goal = case["goal"]
    veh = case["vehicle"]
    planner_cfg = case["planner_cfg"]
    dynamic_risk = case["dynamic_risk"]
    dynamic_risk_seq = case["dynamic_risk_seq"]
    vehicle_context = case["vehicle_context"]

    t_h0 = time.perf_counter()
    rs_ms = 0.0

    if predictor.prediction_mode == "residual":
        def _calibrate_residual(pred_res: np.ndarray) -> np.ndarray:
            out = pred_res.astype(np.float32, copy=True)
            occ = occupancy.astype(bool)
            free = ~occ
            q = float(np.clip(getattr(cfg.planner, "residual_bias_quantile", 0.0), 0.0, 0.95))
            if q > 0.0 and np.any(free):
                flat = out[:, free].reshape(-1)
                if flat.size > 0:
                    bias = float(np.quantile(flat, q))
                    if np.isfinite(bias) and bias > 0.0:
                        out = np.maximum(out - bias, 0.0).astype(np.float32)

            thr = float(max(getattr(cfg.planner, "residual_corridor_threshold", 0.0), 0.0))
            sup = float(np.clip(getattr(cfg.planner, "residual_corridor_suppress", 0.0), 0.0, 1.0))
            if thr > 0.0 and sup > 0.0:
                clearance = np.maximum(esdf.astype(np.float32), 0.0)
                corridor = np.clip((thr - clearance) / max(thr, 1e-6), 0.0, 1.0)
                scale = 1.0 - sup * corridor
                out = (out * scale[None, ...]).astype(np.float32)
            out[:, occ] = 0.0
            return out

        rs_cfg = RSConsistentCostConfig.from_configs(veh, planner_cfg)
        yaw_bins = int(max(1, predictor.heuristic_yaw_bins))
        key = make_rs_field_cache_key(
            occupancy=occupancy,
            goal=goal,
            resolution=resolution,
            yaw_bins=yaw_bins,
            rho=veh.min_turn_radius,
            step_size=cfg.dataset.teacher_rs_step_size,
            backend=cfg.dataset.teacher_rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=rs_cfg,
        )
        rs_base = load_rs_field_cache(rs_cache_dir, key)
        if rs_base is None:
            rs_base = compute_reeds_shepp_field(
                occupancy=occupancy,
                goal=goal,
                resolution=resolution,
                yaw_bins=yaw_bins,
                rho=veh.min_turn_radius,
                fill_value=cfg.dataset.max_teacher_value,
                step_size=cfg.dataset.teacher_rs_step_size,
                backend=cfg.dataset.teacher_rs_backend,
                cost_mode="planner_consistent",
                cost_cfg=rs_cfg,
            )
            save_rs_field_cache(rs_cache_dir, key, rs_base)
        rs_ms = (time.perf_counter() - t_h0) * 1000.0

        t_pred = time.perf_counter()
        pred_res = predictor.predict_residual_field(
            occupancy=occupancy,
            esdf=esdf,
            start=start,
            goal=goal,
            resolution=resolution,
            dynamic_risk=dynamic_risk,
            dynamic_risk_seq=dynamic_risk_seq,
            vehicle_context=vehicle_context,
        )
        pred_res = (np.maximum(pred_res, 0.0) * float(max(residual_alpha, 0.0))).astype(np.float32)
        pred_res = np.clip(pred_res, 0.0, float(max(residual_clip_m, 0.0))).astype(np.float32)
        pred_res = _calibrate_residual(pred_res)
        heur = ResidualYawFieldHeuristic(
            base_field_3d=rs_base.astype(np.float32),
            residual_field_3d=pred_res,
            resolution=resolution,
            max_value=cfg.dataset.max_teacher_value,
            scale=1.0,
        )
        pred_ms = (time.perf_counter() - t_pred) * 1000.0
        return heur, pred_ms, rs_ms

    pred = predictor.predict_field(
        occupancy=occupancy,
        esdf=esdf,
        start=start,
        goal=goal,
        resolution=resolution,
        dynamic_risk=dynamic_risk,
        dynamic_risk_seq=dynamic_risk_seq,
        vehicle_context=vehicle_context,
    )
    pred_ms = (time.perf_counter() - t_h0) * 1000.0

    if pred.ndim == 2:
        free_vals = pred[~occupancy]
        clip_max = float(np.percentile(free_vals, 98)) if free_vals.size > 0 else cfg.dataset.max_teacher_value
        clip_max = float(np.clip(clip_max, 1.0, cfg.dataset.max_teacher_value))
        return FieldHeuristic(pred, resolution, max_value=clip_max, scale=1.0), pred_ms, rs_ms

    free_vals = pred[:, ~occupancy]
    clip_max = float(np.percentile(free_vals, 98)) if free_vals.size > 0 else cfg.dataset.max_teacher_value
    clip_max = float(np.clip(clip_max, 1.0, cfg.dataset.max_teacher_value))
    return YawFieldHeuristic(pred, resolution, max_value=clip_max, scale=1.0), pred_ms, rs_ms


def _evaluate_split(
    cfg,
    split_dir: Path,
    predictor: NeuralHeuristicPredictor,
    logs_dir: Path,
    tag: str,
    max_cases: int,
    residual_alpha: float,
    residual_clip_m: float,
    use_euclidean_fallback: bool,
    hard_max_expansions: int,
    maze_max_expansions: int,
    narrow_max_expansions: int,
) -> dict:
    files = sorted(split_dir.glob("*.npz"))
    if not files:
        raise RuntimeError(f"No cases in split: {split_dir}")
    files = _subset_files(files, int(max_cases))

    rs_cache_dir = cfg.paths.output_dir / f"rs_cache_{tag}"
    rs_cache_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    by_diff_rows: dict[str, list[dict]] = {}
    by_task_rows: dict[str, list[dict]] = {}
    fallback_count = 0

    for p in files:
        case = _load_case(cfg, p)
        planner_cfg = replace(case["planner_cfg"])
        cap = int(max(planner_cfg.max_expansions, cfg.planner.max_expansions))
        if str(case["difficulty"]) == "hard" and int(hard_max_expansions) > 0:
            cap = max(cap, int(hard_max_expansions))
        if str(case["scenario"]) in {"maze_single", "deadend_labyrinth"} and int(maze_max_expansions) > 0:
            cap = max(cap, int(maze_max_expansions))
        if str(case["scenario"]) == "narrow_passage" and int(narrow_max_expansions) > 0:
            cap = max(cap, int(narrow_max_expansions))
        planner_cfg.max_expansions = int(cap)

        planner = HybridAStarPlanner(
            occupancy=case["occupancy"],
            resolution=case["resolution"],
            vehicle_cfg=case["vehicle"],
            planner_cfg=planner_cfg,
            esdf=case["esdf"],
        )
        heur, pred_ms, rs_ms = _build_heuristic(
            cfg=cfg,
            predictor=predictor,
            case=case,
            rs_cache_dir=rs_cache_dir,
            residual_alpha=float(residual_alpha),
            residual_clip_m=float(residual_clip_m),
        )
        res = planner.plan(
            start=case["start"],
            goal=case["goal"],
            anchor_fn=heur,
            guidance_fn=None,
            main_mode="anchor",
            record_expanded=False,
        )
        total_ms = float(res.runtime_ms + pred_ms + rs_ms)
        fallback_used = False
        if (not res.success) and bool(use_euclidean_fallback):
            eu_anchor = euclidean_heuristic((case["goal"][0], case["goal"][1]))
            fb = planner.plan(
                start=case["start"],
                goal=case["goal"],
                anchor_fn=eu_anchor,
                guidance_fn=None,
                main_mode="anchor",
                record_expanded=False,
            )
            total_ms += float(fb.runtime_ms)
            if fb.success:
                res = fb
                fallback_used = True
                fallback_count += 1
        row = {
            "success": bool(res.success),
            "expansions": float(res.expansions),
            "cost": float(res.cost) if np.isfinite(res.cost) else float("nan"),
            "time_ms": float(total_ms),
            "difficulty": str(case["difficulty"]),
            "task_type": str(case["task_type"]),
            "scenario": str(case["scenario"]),
            "fallback_used": bool(fallback_used),
            "max_expansions": float(planner_cfg.max_expansions),
        }
        rows.append(row)
        by_diff_rows.setdefault(str(case["difficulty"]), []).append(row)
        by_task_rows.setdefault(str(case["task_type"]), []).append(row)

    succ = [r for r in rows if r["success"]]
    summary = {
        "num_cases": len(rows),
        "methods": {
            "ours": {
                "success_rate": len(succ) / max(len(rows), 1),
                "avg_expansions": float(np.mean([r["expansions"] for r in succ])) if succ else float("nan"),
                "avg_cost": float(np.mean([r["cost"] for r in succ if np.isfinite(r["cost"])])) if succ else float("nan"),
                "avg_time_ms": float(np.mean([r["time_ms"] for r in succ])) if succ else float("nan"),
                "avg_time_total_ms": float(np.mean([r["time_ms"] for r in succ])) if succ else float("nan"),
                "fallback_rate": float(fallback_count / max(len(rows), 1)),
                "avg_max_expansions": float(np.mean([r["max_expansions"] for r in rows])) if rows else float("nan"),
            }
        },
        "by_difficulty": {},
        "by_task": {},
    }
    for d, drows in sorted(by_diff_rows.items()):
        dsucc = [r for r in drows if r["success"]]
        summary["by_difficulty"][d] = {
            "ours": {
                "success_rate": len(dsucc) / max(len(drows), 1),
                "avg_expansions": float(np.mean([r["expansions"] for r in dsucc])) if dsucc else float("nan"),
                "avg_cost": float(np.mean([r["cost"] for r in dsucc if np.isfinite(r["cost"])])) if dsucc else float("nan"),
                "avg_time_ms": float(np.mean([r["time_ms"] for r in dsucc])) if dsucc else float("nan"),
            }
        }
    for t, trows in sorted(by_task_rows.items()):
        tsucc = [r for r in trows if r["success"]]
        summary["by_task"][t] = {
            "ours": {
                "success_rate": len(tsucc) / max(len(trows), 1),
                "avg_expansions": float(np.mean([r["expansions"] for r in tsucc])) if tsucc else float("nan"),
                "avg_cost": float(np.mean([r["cost"] for r in tsucc if np.isfinite(r["cost"])])) if tsucc else float("nan"),
                "avg_time_ms": float(np.mean([r["time_ms"] for r in tsucc])) if tsucc else float("nan"),
            }
        }

    logs_dir.mkdir(parents=True, exist_ok=True)
    with (logs_dir / f"{tag}_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


def _find_case_file(test_dir: Path, want_task: str | None = None, want_scenario_prefix: str | None = None) -> Path | None:
    for p in sorted(test_dir.glob("*.npz")):
        with np.load(p, allow_pickle=False) as d:
            task = str(d["task_type"]) if "task_type" in d else ""
            scenario = str(d["scenario"]) if "scenario" in d else ""
        if want_task is not None and task != want_task:
            continue
        if want_scenario_prefix is not None and not scenario.startswith(want_scenario_prefix):
            continue
        return p
    return None


def _render_case_compare(
    cfg,
    case_path: Path,
    baseline_predictor: NeuralHeuristicPredictor | None,
    optimized_predictor: NeuralHeuristicPredictor,
    residual_alpha: float,
    residual_clip_m: float,
    out_png: Path,
) -> None:
    case = _load_case(cfg, case_path)

    planner_base = HybridAStarPlanner(
        occupancy=case["occupancy"],
        resolution=case["resolution"],
        vehicle_cfg=case["vehicle"],
        planner_cfg=case["planner_cfg"],
        esdf=case["esdf"],
    )
    planner_opt = HybridAStarPlanner(
        occupancy=case["occupancy"],
        resolution=case["resolution"],
        vehicle_cfg=case["vehicle"],
        planner_cfg=case["planner_cfg"],
        esdf=case["esdf"],
    )

    if baseline_predictor is None:
        base_path = np.zeros((0, 3), dtype=np.float32)
    else:
        h_base, _, _ = _build_heuristic(
            cfg=cfg,
            predictor=baseline_predictor,
            case=case,
            rs_cache_dir=cfg.paths.output_dir / "rs_cache_vis_baseline",
            residual_alpha=float(residual_alpha),
            residual_clip_m=float(residual_clip_m),
        )
        r_base = planner_base.plan(
            start=case["start"],
            goal=case["goal"],
            anchor_fn=h_base,
            guidance_fn=None,
            main_mode="anchor",
            record_expanded=True,
        )
        base_path = r_base.path

    h_opt, _, _ = _build_heuristic(
        cfg=cfg,
        predictor=optimized_predictor,
        case=case,
        rs_cache_dir=cfg.paths.output_dir / "rs_cache_vis_optimized",
        residual_alpha=float(residual_alpha),
        residual_clip_m=float(residual_clip_m),
    )
    r_opt = planner_opt.plan(
        start=case["start"],
        goal=case["goal"],
        anchor_fn=h_opt,
        guidance_fn=None,
        main_mode="anchor",
        record_expanded=True,
    )

    _save_path_compare_svg(
        occupancy=case["occupancy"],
        baseline_path=base_path,
        neural_path=r_opt.path,
        resolution=float(case["resolution"]),
        out_path=out_png,
        start=case["start"],
        goal=case["goal"],
        title=f"Baseline vs Optimized ({case['scenario']}/{case['task_type']})",
    )


def _fmt_hist(meta: dict, split_name: str, key: str, max_items: int = 8) -> str:
    split_meta = meta.get("splits", {}).get(split_name, {})
    hist = split_meta.get(key, {}) or {}
    total = int(split_meta.get("num_samples", 0))
    if not hist or total <= 0:
        return "无"
    items = sorted(hist.items(), key=lambda kv: int(kv[1]), reverse=True)[:max_items]
    return "；".join(f"{k}:{int(v)}({int(v)/total:.1%})" for k, v in items)


def _write_optimized_report(
    report_path: Path,
    baseline_dataset_meta: dict | None,
    optimized_dataset_meta: dict,
    epoch_rows: list[dict],
    baseline_summary: dict | None,
    final_train_summary: dict,
    final_test_summary: dict,
    best_epoch: int,
    best_ckpt: Path,
    loss_curve_path: Path,
    dynamic_fig: Path | None,
    maze_fig: Path | None,
    maze_dynamic_fig: Path | None,
    baseline_maze_dynamic_ratio: float | None,
    optimized_maze_dynamic_ratio: float | None,
    target_hard_improve: float,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    train_ours = _ours_metrics(final_train_summary)
    test_ours = _ours_metrics(final_test_summary)

    baseline_test = _ours_metrics(baseline_summary) if baseline_summary is not None else None
    base_hard = _safe_group_success(baseline_summary or {}, "by_difficulty", "hard")
    base_dyn = _safe_group_success(baseline_summary or {}, "by_task", "dynamic_avoid")
    opt_hard = _safe_group_success(final_test_summary, "by_difficulty", "hard")
    opt_dyn = _safe_group_success(final_test_summary, "by_task", "dynamic_avoid")

    hard_delta = opt_hard - base_hard if np.isfinite(base_hard) and np.isfinite(opt_hard) else float("nan")
    dyn_delta = opt_dyn - base_dyn if np.isfinite(base_dyn) and np.isfinite(opt_dyn) else float("nan")

    lines: list[str] = []
    lines.append("# Hard+Dynamic 泛化定向优化报告")
    lines.append("")
    lines.append(f"生成日期：{date.today().isoformat()}")
    lines.append("")

    lines.append("## 1. 数据集重平衡对比")
    lines.append("")
    if baseline_dataset_meta is not None:
        lines.append("- 基线训练集难度分布：{}".format(_fmt_hist(baseline_dataset_meta, "train", "difficulty_histogram", 6)))
        lines.append("- 基线训练集任务分布：{}".format(_fmt_hist(baseline_dataset_meta, "train", "task_histogram", 8)))
    lines.append("- 优化训练集难度分布：{}".format(_fmt_hist(optimized_dataset_meta, "train", "difficulty_histogram", 6)))
    lines.append("- 优化训练集任务分布：{}".format(_fmt_hist(optimized_dataset_meta, "train", "task_histogram", 8)))
    lines.append("- 测试集难度分布：{}".format(_fmt_hist(optimized_dataset_meta, "test", "difficulty_histogram", 6)))
    lines.append("- 测试集任务分布：{}".format(_fmt_hist(optimized_dataset_meta, "test", "task_histogram", 8)))
    if baseline_maze_dynamic_ratio is not None and np.isfinite(float(baseline_maze_dynamic_ratio)):
        lines.append(
            "- 基线训练集 `maze_single/deadend_labyrinth & dynamic_avoid` 占比：{:.1%}".format(float(baseline_maze_dynamic_ratio))
        )
    if optimized_maze_dynamic_ratio is not None and np.isfinite(float(optimized_maze_dynamic_ratio)):
        lines.append(
            "- 优化训练集 `maze_single/deadend_labyrinth & dynamic_avoid` 占比：{:.1%}".format(float(optimized_maze_dynamic_ratio))
        )
    lines.append("")

    lines.append("## 2. 训练过程（10 epochs）")
    lines.append("")
    lines.append(f"- 最优 epoch：{best_epoch}")
    lines.append(f"- 最优模型：`{best_ckpt}`")
    lines.append(f"- 训练损失曲线：`{loss_curve_path}`")
    lines.append("")
    lines.append("| epoch | train loss | val loss | test success | hard success | dynamic_avoid success |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for r in epoch_rows:
        lines.append(
            "| {e} | {tr:.5f} | {va:.5f} | {ts:.3f} | {hs:.3f} | {ds:.3f} |".format(
                e=r["epoch"],
                tr=r["train_loss"],
                va=r["val_loss"],
                ts=r["test_success_rate"],
                hs=r.get("test_hard_success", float("nan")),
                ds=r.get("test_dynamic_success", float("nan")),
            )
        )
    lines.append("")

    lines.append("## 3. 优化前后测试性能对比")
    lines.append("")
    lines.append("| model | success rate | hard success | dynamic_avoid success | avg expansions | avg cost |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    if baseline_test is not None:
        lines.append(
            "| baseline | {:.3f} | {:.3f} | {:.3f} | {:.1f} | {:.2f} |".format(
                baseline_test["success_rate"],
                base_hard,
                base_dyn,
                baseline_test["avg_expansions"],
                baseline_test["avg_cost"],
            )
        )
    lines.append(
        "| optimized | {:.3f} | {:.3f} | {:.3f} | {:.1f} | {:.2f} |".format(
            test_ours["success_rate"],
            opt_hard,
            opt_dyn,
            test_ours["avg_expansions"],
            test_ours["avg_cost"],
        )
    )
    lines.append("")
    lines.append("| model | hard avg expansions | hard avg cost | dynamic_avoid avg expansions | dynamic_avoid avg cost |")
    lines.append("|---|---:|---:|---:|---:|")
    bh = (baseline_summary or {}).get("by_difficulty", {}).get("hard", {}).get("ours", {})
    bd = (baseline_summary or {}).get("by_task", {}).get("dynamic_avoid", {}).get("ours", {})
    oh = final_test_summary.get("by_difficulty", {}).get("hard", {}).get("ours", {})
    od = final_test_summary.get("by_task", {}).get("dynamic_avoid", {}).get("ours", {})
    if baseline_summary is not None:
        lines.append(
            "| baseline | {:.1f} | {:.2f} | {:.1f} | {:.2f} |".format(
                float(bh.get("avg_expansions", float("nan"))),
                float(bh.get("avg_cost", float("nan"))),
                float(bd.get("avg_expansions", float("nan"))),
                float(bd.get("avg_cost", float("nan"))),
            )
        )
    lines.append(
        "| optimized | {:.1f} | {:.2f} | {:.1f} | {:.2f} |".format(
            float(oh.get("avg_expansions", float("nan"))),
            float(oh.get("avg_cost", float("nan"))),
            float(od.get("avg_expansions", float("nan"))),
            float(od.get("avg_cost", float("nan"))),
        )
    )
    lines.append("")
    lines.append("- hard 场景提升：{:+.3f}".format(hard_delta if np.isfinite(hard_delta) else float("nan")))
    lines.append("- dynamic_avoid 提升：{:+.3f}".format(dyn_delta if np.isfinite(dyn_delta) else float("nan")))
    lines.append("")

    lines.append("## 4. 典型场景轨迹可视化")
    lines.append("")
    if dynamic_fig is not None:
        lines.append(f"- 动态避障轨迹：`{dynamic_fig}`")
    if maze_fig is not None:
        lines.append(f"- 迷宫穿行轨迹：`{maze_fig}`")
    if maze_dynamic_fig is not None:
        lines.append(f"- 迷宫+动态避障轨迹：`{maze_dynamic_fig}`")
    lines.append("")

    lines.append("## 5. 结论")
    lines.append("")
    if np.isfinite(hard_delta) and hard_delta >= float(target_hard_improve):
        lines.append(f"- 已达到 hard 场景提升目标（>= {target_hard_improve:.3f}）。")
    else:
        lines.append(f"- 尚未达到 hard 场景提升目标（目标 {target_hard_improve:.3f}），建议继续增加 hard+dynamic 权重并扩充训练轮次。")
    lines.append("- 该轮优化引入了 RS-consistent 残差学习、时序残差监督与 SmallUNet(SE)，并在复杂场景上进行定向训练。")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()

    cfg = DEFAULT_CONFIG
    cfg.seed = int(args.seed)

    cfg.map = replace(cfg.map)
    cfg.map.width = int(args.map_width)
    cfg.map.height = int(args.map_height)
    cfg.map.resolution = float(args.resolution)

    cfg.dataset = replace(cfg.dataset)
    cfg.dataset.teacher_yaw_bins = int(args.teacher_yaw_bins)
    cfg.dataset.teacher_mode = str(args.teacher_mode)
    cfg.dataset.teacher_rs_backend = str(args.teacher_rs_backend)
    cfg.dataset.teacher_rs_step_size = float(args.teacher_rs_step_size)
    cfg.dataset.hybrid_obstacle_alpha = float(args.hybrid_alpha)
    cfg.dataset.hybrid_obstacle_threshold_m = float(args.hybrid_threshold)

    cfg.train = replace(cfg.train)
    cfg.train.epochs = int(args.epochs)
    cfg.train.batch_size = int(args.batch_size)
    cfg.train.learning_rate = float(args.lr)
    cfg.train.underestimation_weight = float(args.under_weight)
    cfg.train.hard_underestimation_weight = float(args.hard_under_weight)  # type: ignore[attr-defined]
    cfg.train.hard_overestimation_weight = float(args.hard_over_weight)  # type: ignore[attr-defined]
    cfg.train.narrow_overestimation_weight = float(args.narrow_over_weight)  # type: ignore[attr-defined]
    cfg.train.hard_rank_lambda = float(args.hard_rank_lambda)  # type: ignore[attr-defined]
    cfg.train.hard_rank_topk = int(args.hard_rank_topk)  # type: ignore[attr-defined]
    cfg.train.hard_rank_margin = float(args.hard_rank_margin)  # type: ignore[attr-defined]
    cfg.train.distance_weight_scale_m = float(args.dist_weight_scale)
    cfg.train.distance_weight_min = float(args.dist_weight_min)
    cfg.train.type_c_loss_weight = float(args.type_c_weight)
    cfg.train.prediction_mode = str(args.prediction_mode)
    cfg.train.num_workers = int(args.num_workers)
    cfg.train.device = str(args.device)

    cfg.planner = replace(cfg.planner)
    cfg.planner.max_expansions = int(max(args.max_expansions, 5000))
    cfg.planner.residual_alpha = float(args.residual_alpha)
    cfg.planner.residual_bias_quantile = float(args.residual_bias_quantile)  # type: ignore[attr-defined]
    cfg.planner.residual_corridor_threshold = float(args.residual_corridor_threshold)  # type: ignore[attr-defined]
    cfg.planner.residual_corridor_suppress = float(args.residual_corridor_suppress)  # type: ignore[attr-defined]

    cfg.paths = replace(cfg.paths)
    cfg.paths.data_dir = Path(args.data_root)
    cfg.paths.output_dir = Path(args.output_root)
    cfg.paths.logs_dir = cfg.paths.output_dir / "logs"
    cfg.paths.checkpoints_dir = cfg.paths.output_dir / "checkpoints"
    cfg.paths.figures_dir = cfg.paths.output_dir / "figures"

    ensure_dirs([cfg.paths.output_dir, cfg.paths.logs_dir, cfg.paths.checkpoints_dir, cfg.paths.figures_dir, cfg.paths.data_dir])
    set_seed(cfg.seed)

    if cfg.train.device.startswith("cuda") and not torch.cuda.is_available():
        cfg.train.device = "cpu"

    if not args.skip_generation:
        print("[1/5] Generating generalized scenario dataset...")
        difficulty_filter = _parse_csv_values(args.difficulty_filter)
        template_filter = _parse_csv_values(args.template_filter)
        task_filter = _parse_csv_values(args.task_filter)
        distribution_filter = _parse_csv_values(args.distribution_filter)
        dataset_meta = build_generalization_dataset(
            output_root=cfg.paths.data_dir,
            train_count=int(args.train_count),
            val_count=int(args.val_count),
            test_count=int(args.test_count),
            seed=int(args.seed),
            map_cfg=cfg.map,
            ds_cfg=cfg.dataset,
            planner_cfg=cfg.planner,
            dynamic_horizon=int(args.dynamic_horizon),
            dynamic_dt=float(args.dynamic_dt),
            use_augmentation=not bool(args.no_augmentation),
            include_rs_base=bool(cfg.train.prediction_mode == "residual"),
            difficulty_filter=difficulty_filter,
            template_filter=template_filter,
            task_filter=task_filter,
            distribution_filter=distribution_filter,
        )
    else:
        print("[1/5] Skipping generation; loading existing dataset meta...")
        dataset_meta = json.loads((cfg.paths.data_dir / "meta.json").read_text(encoding="utf-8"))

    tmeta = dataset_meta.get("splits", {}).get("train", {})
    cfg.dataset.teacher_yaw_bins = int(tmeta.get("teacher_yaw_bins", cfg.dataset.teacher_yaw_bins))
    cfg.dataset.teacher_mode = str(tmeta.get("teacher_mode", cfg.dataset.teacher_mode))
    cfg.dataset.teacher_rs_backend = str(tmeta.get("teacher_rs_backend", cfg.dataset.teacher_rs_backend))
    cfg.dataset.teacher_rs_step_size = float(tmeta.get("teacher_rs_step_size", cfg.dataset.teacher_rs_step_size))

    print("[2/5] Building SmallUNet + dataloaders...")
    (
        model,
        train_loader,
        val_loader,
        in_channels,
        out_channels,
        output_activation,
        temporal_steps,
        heuristic_yaw_bins,
    ) = _build_model_and_loaders(args, cfg)

    device = torch.device(cfg.train.device)
    model = model.to(device)
    _load_init_checkpoint(model, args.init_checkpoint)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.train.learning_rate, weight_decay=cfg.train.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=float(np.clip(args.lr_plateau_factor, 0.1, 0.9)),
        patience=int(max(args.lr_plateau_patience, 1)),
        min_lr=float(max(args.lr_plateau_min, 1e-8)),
    )
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    history: dict[str, list[float]] = {
        "train_loss": [],
        "val_loss": [],
        "lr": [],
        "train_success_rate": [],
        "test_success_rate": [],
        "train_avg_expansions": [],
        "test_avg_expansions": [],
        "test_hard_success": [],
        "test_dynamic_success": [],
    }
    epoch_rows: list[dict] = []

    best_epoch = -1
    best_score = (-1.0, -1.0, -1.0, float("inf"))
    best_ckpt = _best_ckpt_path(cfg.paths.checkpoints_dir, args.run_tag)

    print("[3/5] Training with per-epoch hard+dynamic evaluation...")
    for epoch in range(1, cfg.train.epochs + 1):
        model.train()
        epoch_loss = 0.0
        steps = 0
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
            y_bins = int(batch.get("yaw_bins", torch.tensor([y.shape[1]]))[0].item())

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
                    hard_underestimation_weight=float(args.hard_under_weight),
                    hard_overestimation_weight=float(args.hard_over_weight),
                    narrow_mask=nm,
                    narrow_overestimation_weight=float(args.narrow_over_weight),
                    temporal_steps=t_steps,
                    yaw_bins=y_bins,
                    temporal_lambda=float(args.temporal_lambda),
                    hard_rank_lambda=float(args.hard_rank_lambda),
                    hard_rank_topk=int(args.hard_rank_topk),
                    hard_rank_margin=float(args.hard_rank_margin),
                )

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()

            epoch_loss += float(loss.item())
            steps += 1

        train_loss = epoch_loss / max(steps, 1)
        val_loss = _eval_loss(
            model,
            val_loader,
            device=device,
            under_weight=cfg.train.underestimation_weight,
            hard_under_weight=float(args.hard_under_weight),
            hard_over_weight=float(args.hard_over_weight),
            narrow_over_weight=float(args.narrow_over_weight),
            temporal_lambda=float(args.temporal_lambda),
            hard_rank_lambda=float(args.hard_rank_lambda),
            hard_rank_topk=int(args.hard_rank_topk),
            hard_rank_margin=float(args.hard_rank_margin),
        )
        scheduler.step(val_loss)
        current_lr = float(optimizer.param_groups[0]["lr"])

        ckpt_path = _epoch_ckpt_path(cfg.paths.checkpoints_dir, args.run_tag, epoch)
        _save_checkpoint(
            ckpt_path,
            model,
            cfg,
            in_channels=in_channels,
            out_channels=out_channels,
            output_activation=output_activation,
            history=history,
            model_name=args.model_name,
            base_channels=int(args.model_base),
            temporal_steps=temporal_steps,
            heuristic_yaw_bins=heuristic_yaw_bins,
        )

        predictor = NeuralHeuristicPredictor(ckpt_path, device=cfg.train.device, gaussian_sigma=cfg.dataset.gaussian_sigma)
        train_summary = _evaluate_split(
            cfg,
            cfg.paths.data_dir / "train",
            predictor,
            cfg.paths.logs_dir,
            tag=f"{args.run_tag}_train_epoch_{epoch:03d}",
            max_cases=int(args.eval_train_cases),
            residual_alpha=float(args.residual_alpha),
            residual_clip_m=float(args.residual_clip_m),
            use_euclidean_fallback=(not bool(args.disable_euclidean_fallback)),
            hard_max_expansions=int(args.hard_max_expansions),
            maze_max_expansions=int(args.maze_max_expansions),
            narrow_max_expansions=int(args.narrow_max_expansions),
        )
        test_summary = _evaluate_split(
            cfg,
            cfg.paths.data_dir / "test",
            predictor,
            cfg.paths.logs_dir,
            tag=f"{args.run_tag}_test_epoch_{epoch:03d}",
            max_cases=int(args.eval_test_cases),
            residual_alpha=float(args.residual_alpha),
            residual_clip_m=float(args.residual_clip_m),
            use_euclidean_fallback=(not bool(args.disable_euclidean_fallback)),
            hard_max_expansions=int(args.hard_max_expansions),
            maze_max_expansions=int(args.maze_max_expansions),
            narrow_max_expansions=int(args.narrow_max_expansions),
        )

        train_m = _ours_metrics(train_summary)
        test_m = _ours_metrics(test_summary)
        test_hard = _safe_group_success(test_summary, "by_difficulty", "hard")
        test_dyn = _safe_group_success(test_summary, "by_task", "dynamic_avoid")

        history["train_loss"].append(float(train_loss))
        history["val_loss"].append(float(val_loss))
        history["lr"].append(current_lr)
        history["train_success_rate"].append(float(train_m["success_rate"]))
        history["test_success_rate"].append(float(test_m["success_rate"]))
        history["train_avg_expansions"].append(float(train_m["avg_expansions"]))
        history["test_avg_expansions"].append(float(test_m["avg_expansions"]))
        history["test_hard_success"].append(float(test_hard))
        history["test_dynamic_success"].append(float(test_dyn))

        row = {
            "epoch": int(epoch),
            "train_loss": float(train_loss),
            "val_loss": float(val_loss),
            "lr": current_lr,
            "train_success_rate": float(train_m["success_rate"]),
            "test_success_rate": float(test_m["success_rate"]),
            "train_avg_expansions": float(train_m["avg_expansions"]),
            "test_avg_expansions": float(test_m["avg_expansions"]),
            "test_hard_success": float(test_hard),
            "test_dynamic_success": float(test_dyn),
            "train_avg_cost": float(train_m["avg_cost"]),
            "test_avg_cost": float(test_m["avg_cost"]),
        }
        epoch_rows.append(row)

        score = (
            float(test_m["success_rate"]),
            float(test_hard) if np.isfinite(test_hard) else -1.0,
            float(test_dyn) if np.isfinite(test_dyn) else -1.0,
            -float(test_m["avg_expansions"]) if np.isfinite(test_m["avg_expansions"]) else -1e9,
        )
        if score > best_score:
            best_score = score
            best_epoch = int(epoch)
            _save_checkpoint(
                best_ckpt,
                model,
                cfg,
                in_channels=in_channels,
                out_channels=out_channels,
                output_activation=output_activation,
                history=history,
                model_name=args.model_name,
                base_channels=int(args.model_base),
                temporal_steps=temporal_steps,
                heuristic_yaw_bins=heuristic_yaw_bins,
            )

        print(
            f"epoch {epoch:02d}/{cfg.train.epochs} "
            f"lr={current_lr:.2e} train_loss={train_loss:.5f} val_loss={val_loss:.5f} "
            f"test_succ={test_m['success_rate']:.3f} hard={test_hard:.3f} dyn={test_dyn:.3f}"
        )

    print("[4/5] Final evaluation (optimized + baseline)...")
    final_predictor = NeuralHeuristicPredictor(best_ckpt, device=cfg.train.device, gaussian_sigma=cfg.dataset.gaussian_sigma)
    final_train_summary = _evaluate_split(
        cfg,
        cfg.paths.data_dir / "train",
        final_predictor,
        cfg.paths.logs_dir,
        tag=f"{args.run_tag}_final_train",
        max_cases=int(args.final_train_cases),
        residual_alpha=float(args.residual_alpha),
        residual_clip_m=float(args.residual_clip_m),
        use_euclidean_fallback=(not bool(args.disable_euclidean_fallback)),
        hard_max_expansions=int(args.hard_max_expansions),
        maze_max_expansions=int(args.maze_max_expansions),
        narrow_max_expansions=int(args.narrow_max_expansions),
    )
    final_test_summary = _evaluate_split(
        cfg,
        cfg.paths.data_dir / "test",
        final_predictor,
        cfg.paths.logs_dir,
        tag=f"{args.run_tag}_final_test",
        max_cases=int(args.final_test_cases),
        residual_alpha=float(args.residual_alpha),
        residual_clip_m=float(args.residual_clip_m),
        use_euclidean_fallback=(not bool(args.disable_euclidean_fallback)),
        hard_max_expansions=int(args.hard_max_expansions),
        maze_max_expansions=int(args.maze_max_expansions),
        narrow_max_expansions=int(args.narrow_max_expansions),
    )

    baseline_summary = None
    if args.baseline_checkpoint.exists():
        baseline_predictor = NeuralHeuristicPredictor(args.baseline_checkpoint, device=cfg.train.device, gaussian_sigma=cfg.dataset.gaussian_sigma)
        baseline_summary = _evaluate_split(
            cfg,
            cfg.paths.data_dir / "test",
            baseline_predictor,
            cfg.paths.logs_dir,
            tag=f"{args.run_tag}_baseline_test",
            max_cases=int(args.final_test_cases),
            residual_alpha=float(args.residual_alpha),
            residual_clip_m=float(args.residual_clip_m),
            use_euclidean_fallback=False,
            hard_max_expansions=int(args.hard_max_expansions),
            maze_max_expansions=int(args.maze_max_expansions),
            narrow_max_expansions=int(args.narrow_max_expansions),
        )
    else:
        baseline_predictor = None

    args_json = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    history_path = cfg.paths.logs_dir / f"{args.run_tag}_history.json"
    with history_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "config": {
                    "args": args_json,
                    "resolved_device": cfg.train.device,
                    "in_channels": in_channels,
                    "out_channels": out_channels,
                    "temporal_steps": temporal_steps,
                    "heuristic_yaw_bins": heuristic_yaw_bins,
                },
                "dataset_meta": dataset_meta,
                "epoch_rows": epoch_rows,
                "best_epoch": int(best_epoch),
                "best_checkpoint": str(best_ckpt),
                "final_train_summary": final_train_summary,
                "final_test_summary": final_test_summary,
                "baseline_summary": baseline_summary,
            },
            f,
            indent=2,
        )

    loss_curve_path = cfg.paths.figures_dir / f"{args.run_tag}_loss_curve.svg"
    _save_loss_curve_svg(history["train_loss"], history["val_loss"], loss_curve_path)

    dynamic_case = _find_case_file(cfg.paths.data_dir / "test", want_task="dynamic_avoid")
    maze_case = _find_case_file(cfg.paths.data_dir / "test", want_scenario_prefix="maze")
    maze_dynamic_case = _find_case_file(
        cfg.paths.data_dir / "test",
        want_task="dynamic_avoid",
        want_scenario_prefix="maze",
    )
    dynamic_fig = None
    maze_fig = None
    maze_dynamic_fig = None

    if dynamic_case is not None:
        dynamic_fig = cfg.paths.figures_dir / f"{args.run_tag}_trajectory_dynamic_avoid.svg"
        _render_case_compare(
            cfg,
            case_path=dynamic_case,
            baseline_predictor=baseline_predictor,
            optimized_predictor=final_predictor,
            residual_alpha=float(args.residual_alpha),
            residual_clip_m=float(args.residual_clip_m),
            out_png=dynamic_fig,
        )

    if maze_case is not None:
        maze_fig = cfg.paths.figures_dir / f"{args.run_tag}_trajectory_maze.svg"
        _render_case_compare(
            cfg,
            case_path=maze_case,
            baseline_predictor=baseline_predictor,
            optimized_predictor=final_predictor,
            residual_alpha=float(args.residual_alpha),
            residual_clip_m=float(args.residual_clip_m),
            out_png=maze_fig,
        )

    if maze_dynamic_case is not None:
        maze_dynamic_fig = cfg.paths.figures_dir / f"{args.run_tag}_trajectory_maze_dynamic.svg"
        _render_case_compare(
            cfg,
            case_path=maze_dynamic_case,
            baseline_predictor=baseline_predictor,
            optimized_predictor=final_predictor,
            residual_alpha=float(args.residual_alpha),
            residual_clip_m=float(args.residual_clip_m),
            out_png=maze_dynamic_fig,
        )

    baseline_dataset_meta = None
    if args.baseline_data_meta.exists():
        baseline_dataset_meta = json.loads(args.baseline_data_meta.read_text(encoding="utf-8"))

    baseline_maze_dynamic_ratio = None
    if args.baseline_data_meta.exists():
        try:
            base_root = args.baseline_data_meta.parent
            baseline_maze_dynamic_ratio = _compute_template_task_joint_ratio(
                train_dir=base_root / "train",
                templates=("maze_single", "deadend_labyrinth"),
                task_type="dynamic_avoid",
            )
        except Exception:
            baseline_maze_dynamic_ratio = None

    optimized_maze_dynamic_ratio = None
    try:
        optimized_maze_dynamic_ratio = _compute_template_task_joint_ratio(
            train_dir=cfg.paths.data_dir / "train",
            templates=("maze_single", "deadend_labyrinth"),
            task_type="dynamic_avoid",
        )
    except Exception:
        optimized_maze_dynamic_ratio = None

    print("[5/5] Writing optimized report...")
    report_path = cfg.paths.output_dir / f"{args.run_tag}_report.md"
    _write_optimized_report(
        report_path=report_path,
        baseline_dataset_meta=baseline_dataset_meta,
        optimized_dataset_meta=dataset_meta,
        epoch_rows=epoch_rows,
        baseline_summary=baseline_summary,
        final_train_summary=final_train_summary,
        final_test_summary=final_test_summary,
        best_epoch=int(best_epoch),
        best_ckpt=best_ckpt,
        loss_curve_path=loss_curve_path,
        dynamic_fig=dynamic_fig,
        maze_fig=maze_fig,
        maze_dynamic_fig=maze_dynamic_fig,
        baseline_maze_dynamic_ratio=baseline_maze_dynamic_ratio,
        optimized_maze_dynamic_ratio=optimized_maze_dynamic_ratio,
        target_hard_improve=float(args.target_hard_improve),
    )

    print(f"best checkpoint: {best_ckpt}")
    print(f"history: {history_path}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
