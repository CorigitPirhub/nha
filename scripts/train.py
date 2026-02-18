from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from network.train import train_network
from utils.common import ensure_dirs, set_seed
from utils.visualization import save_training_curve


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train neural heuristic predictor")
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--epochs", type=int, default=DEFAULT_CONFIG.train.epochs)
    p.add_argument("--batch-size", type=int, default=DEFAULT_CONFIG.train.batch_size)
    p.add_argument("--lr", type=float, default=DEFAULT_CONFIG.train.learning_rate)
    p.add_argument("--device", type=str, default=DEFAULT_CONFIG.train.device)
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    cfg.train.epochs = args.epochs
    cfg.train.batch_size = args.batch_size
    cfg.train.learning_rate = args.lr
    cfg.train.device = args.device

    ensure_dirs([cfg.paths.output_dir, cfg.paths.checkpoints_dir, cfg.paths.logs_dir, cfg.paths.figures_dir])
    set_seed(args.seed)

    ckpt, metrics = train_network(cfg, args.data / "train", args.data / "val")

    with (cfg.paths.logs_dir / "train_metrics.json").open("r", encoding="utf-8") as f:
        all_metrics = json.load(f)
    save_training_curve(all_metrics["train_loss"], all_metrics["val_loss"], cfg.paths.figures_dir / "training_curve.png")

    print(f"checkpoint: {ckpt}")
    print(f"best_val_loss: {metrics['best_val_loss']:.6f}")


if __name__ == "__main__":
    main()
