from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.dataset_builder import describe_split, generate_dataset_split
from utils.common import set_seed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate random training/validation/test dataset")
    p.add_argument("--output", type=Path, default=Path("data"))
    p.add_argument("--train", type=int, default=DEFAULT_CONFIG.dataset.train_size)
    p.add_argument("--val", type=int, default=DEFAULT_CONFIG.dataset.val_size)
    p.add_argument("--test", type=int, default=DEFAULT_CONFIG.dataset.test_size)
    p.add_argument("--teacher-yaw-bins", type=int, default=DEFAULT_CONFIG.dataset.teacher_yaw_bins)
    p.add_argument(
        "--teacher-mode",
        type=str,
        default=DEFAULT_CONFIG.dataset.teacher_mode,
        choices=[
            "dubins",
            "dubins_proxy",
            "reeds_shepp",
            "reeds_shepp_consistent",
            "hybrid_rs_esdf",
            "hybrid_rs_consistent_esdf",
        ],
    )
    p.add_argument("--teacher-rs-backend", type=str, default=DEFAULT_CONFIG.dataset.teacher_rs_backend, choices=["auto", "rsplan", "approx"])
    p.add_argument("--teacher-rs-step-size", type=float, default=DEFAULT_CONFIG.dataset.teacher_rs_step_size)
    p.add_argument("--hybrid-alpha", type=float, default=DEFAULT_CONFIG.dataset.hybrid_obstacle_alpha)
    p.add_argument("--hybrid-threshold", type=float, default=DEFAULT_CONFIG.dataset.hybrid_obstacle_threshold_m)
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    set_seed(args.seed)
    cfg.dataset.teacher_yaw_bins = int(args.teacher_yaw_bins)
    cfg.dataset.teacher_mode = str(args.teacher_mode)
    cfg.dataset.teacher_rs_backend = str(args.teacher_rs_backend)
    cfg.dataset.teacher_rs_step_size = float(args.teacher_rs_step_size)
    cfg.dataset.hybrid_obstacle_alpha = float(args.hybrid_alpha)
    cfg.dataset.hybrid_obstacle_threshold_m = float(args.hybrid_threshold)

    train_counts = generate_dataset_split(
        args.output / "train",
        args.train,
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=args.seed + 11,
    )
    val_counts = generate_dataset_split(
        args.output / "val",
        args.val,
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=args.seed + 22,
    )
    test_counts = generate_dataset_split(
        args.output / "test",
        args.test,
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=args.seed + 33,
    )

    print(describe_split("train", train_counts))
    print(describe_split("val", val_counts))
    print(describe_split("test", test_counts))
    print(
        f"teacher: mode={cfg.dataset.teacher_mode} yaw_bins={cfg.dataset.teacher_yaw_bins} "
        f"rs_backend={cfg.dataset.teacher_rs_backend} rs_step={cfg.dataset.teacher_rs_step_size:.2f} "
        f"hybrid_alpha={cfg.dataset.hybrid_obstacle_alpha:.3f} "
        f"hybrid_threshold={cfg.dataset.hybrid_obstacle_threshold_m:.2f}"
    )


if __name__ == "__main__":
    main()
