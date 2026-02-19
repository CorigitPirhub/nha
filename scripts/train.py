from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from network.train import train_network
from utils.common import ensure_dirs, set_seed
from utils.visualization import save_training_curve


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train neural heuristic predictor")
    p.add_argument("--data", type=Path, default=Path("data_benchmark"))
    p.add_argument("--epochs", type=int, default=DEFAULT_CONFIG.train.epochs)
    p.add_argument("--batch-size", type=int, default=DEFAULT_CONFIG.train.batch_size)
    p.add_argument("--lr", type=float, default=DEFAULT_CONFIG.train.learning_rate)
    p.add_argument(
        "--under-weight",
        type=float,
        default=DEFAULT_CONFIG.train.underestimation_weight,
        help="Penalty multiplier when prediction underestimates teacher (pred < gt).",
    )
    p.add_argument(
        "--dist-weight-scale",
        type=float,
        default=DEFAULT_CONFIG.train.distance_weight_scale_m,
        help="Distance scale (m) for inverse-distance loss weighting.",
    )
    p.add_argument(
        "--dist-weight-min",
        type=float,
        default=DEFAULT_CONFIG.train.distance_weight_min,
        help="Minimum distance loss weight.",
    )
    p.add_argument(
        "--eta-min-ratio",
        type=float,
        default=DEFAULT_CONFIG.train.cosine_eta_min_ratio,
        help="Cosine LR scheduler min-lr ratio.",
    )
    p.add_argument(
        "--hybrid-alpha",
        type=float,
        default=DEFAULT_CONFIG.dataset.hybrid_obstacle_alpha,
        help="Training target enhancement: teacher += alpha * obstacle_cost(esdf).",
    )
    p.add_argument(
        "--hybrid-threshold",
        type=float,
        default=DEFAULT_CONFIG.dataset.hybrid_obstacle_threshold_m,
        help="ESDF threshold (m) for obstacle_cost in hybrid target.",
    )
    p.add_argument(
        "--init-checkpoint",
        type=Path,
        default=None,
        help="Optional checkpoint for finetuning warm start.",
    )
    p.add_argument(
        "--prediction-mode",
        type=str,
        default=DEFAULT_CONFIG.train.prediction_mode,
        choices=["absolute", "residual"],
        help="Train to predict absolute heuristic or residual correction.",
    )
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    cfg.train.epochs = args.epochs
    cfg.train.batch_size = args.batch_size
    cfg.train.learning_rate = args.lr
    cfg.train.underestimation_weight = args.under_weight
    cfg.train.distance_weight_scale_m = args.dist_weight_scale
    cfg.train.distance_weight_min = args.dist_weight_min
    cfg.train.cosine_eta_min_ratio = args.eta_min_ratio
    cfg.dataset.hybrid_obstacle_alpha = args.hybrid_alpha
    cfg.dataset.hybrid_obstacle_threshold_m = args.hybrid_threshold
    cfg.train.prediction_mode = args.prediction_mode
    cfg.train.device = args.device

    if cfg.train.device.startswith("cuda") and not torch.cuda.is_available():
        cfg.train.device = "cpu"

    ensure_dirs([cfg.paths.output_dir, cfg.paths.checkpoints_dir, cfg.paths.logs_dir, cfg.paths.figures_dir])
    set_seed(args.seed)

    print(f"training device: {cfg.train.device}")
    ckpt, metrics = train_network(cfg, args.data / "train", args.data / "val", init_checkpoint=args.init_checkpoint)

    with (cfg.paths.logs_dir / "train_metrics.json").open("r", encoding="utf-8") as f:
        all_metrics = json.load(f)
    save_training_curve(all_metrics["train_loss"], all_metrics["val_loss"], cfg.paths.figures_dir / "training_curve.png")

    print(f"checkpoint: {ckpt}")
    print(f"best_val_loss: {metrics['best_val_loss']:.6f}")


if __name__ == "__main__":
    main()
