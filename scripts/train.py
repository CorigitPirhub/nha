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
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output root. If provided, checkpoints/figures/logs are written under this directory.",
    )
    p.add_argument("--epochs", type=int, default=DEFAULT_CONFIG.train.epochs)
    p.add_argument("--batch-size", type=int, default=DEFAULT_CONFIG.train.batch_size)
    p.add_argument("--lr", type=float, default=DEFAULT_CONFIG.train.learning_rate)
    p.add_argument("--model-name", type=str, default=DEFAULT_CONFIG.train.model_name, choices=["tinyunet", "smallunet"])
    p.add_argument("--model-base", type=int, default=DEFAULT_CONFIG.train.model_base)
    p.add_argument("--use-context-channels", action="store_true", help="Enable extra context channels (12ch input).")
    p.add_argument("--no-temporal-context", action="store_true", help="Disable temporal context supervision (if available in dataset).")
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
        "--type-c-weight",
        type=float,
        default=DEFAULT_CONFIG.train.type_c_loss_weight,
        help="Extra sample-level loss weight for category C cases.",
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
    if args.output_dir is not None:
        cfg.paths.output_dir = args.output_dir
        cfg.paths.checkpoints_dir = args.output_dir / "checkpoints"
        cfg.paths.figures_dir = args.output_dir / "figures"
        cfg.paths.logs_dir = args.output_dir / "logs"
    cfg.train.epochs = args.epochs
    cfg.train.batch_size = args.batch_size
    cfg.train.learning_rate = args.lr
    cfg.train.model_name = str(args.model_name).lower()
    cfg.train.model_base = int(args.model_base)
    cfg.train.use_context_channels = bool(args.use_context_channels)
    cfg.train.use_temporal_context = bool(not args.no_temporal_context)
    cfg.train.underestimation_weight = args.under_weight
    cfg.train.distance_weight_scale_m = args.dist_weight_scale
    cfg.train.distance_weight_min = args.dist_weight_min
    cfg.train.type_c_loss_weight = args.type_c_weight
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
    print(f"model: {cfg.train.model_name} base={cfg.train.model_base} context={cfg.train.use_context_channels} temporal={cfg.train.use_temporal_context}")
    ckpt, metrics = train_network(cfg, args.data / "train", args.data / "val", init_checkpoint=args.init_checkpoint)

    with (cfg.paths.logs_dir / "train_metrics.json").open("r", encoding="utf-8") as f:
        all_metrics = json.load(f)
    save_training_curve(all_metrics["train_loss"], all_metrics["val_loss"], cfg.paths.figures_dir / "training_curve.png")

    print(f"checkpoint: {ckpt}")
    print(f"best_val_loss: {metrics['best_val_loss']:.6f}")


if __name__ == "__main__":
    main()
