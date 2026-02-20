from __future__ import annotations

import argparse
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.dataset_builder import describe_split, generate_benchmark_split
from env.reeds_shepp import (
    RSConsistentCostConfig,
    compute_reeds_shepp_field,
    load_rs_field_cache,
    make_rs_field_cache_key,
    save_rs_field_cache,
)
from utils.common import set_seed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build fixed benchmark split with Type A/B/C")
    p.add_argument("--output", type=Path, default=Path("data_benchmark"))
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    p.add_argument("--train-counts", type=int, nargs=3, default=list(DEFAULT_CONFIG.dataset.benchmark_train_counts))
    p.add_argument("--val-counts", type=int, nargs=3, default=list(DEFAULT_CONFIG.dataset.benchmark_val_counts))
    p.add_argument("--test-counts", type=int, nargs=3, default=list(DEFAULT_CONFIG.dataset.benchmark_test_counts))
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
    p.add_argument(
        "--precompute-rs-cache",
        action="store_true",
        help="Precompute and save planner-consistent RS fields for train/val/test splits.",
    )
    p.add_argument(
        "--rs-cache-dir",
        type=Path,
        default=None,
        help="Directory for RS cache files; default is <output>/rs_cache.",
    )
    return p.parse_args()


def _precompute_rs_cache(split_dir: Path, cache_dir: Path, cfg) -> tuple[int, int]:
    files = sorted((split_dir).glob("*.npz"))
    if not files:
        return 0, 0
    cost_cfg = RSConsistentCostConfig.from_configs(cfg.vehicle, cfg.planner)
    hits = 0
    misses = 0
    for f in files:
        with np.load(f, allow_pickle=False) as data:
            occupancy = data["occupancy"].astype(bool)
            goal = tuple(float(v) for v in data["goal"].astype(np.float32))
        key = make_rs_field_cache_key(
            occupancy=occupancy,
            goal=goal,
            resolution=cfg.map.resolution,
            yaw_bins=cfg.dataset.teacher_yaw_bins,
            rho=cfg.vehicle.min_turn_radius,
            step_size=cfg.dataset.teacher_rs_step_size,
            backend=cfg.dataset.teacher_rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=cost_cfg,
        )
        cached = load_rs_field_cache(cache_dir, key)
        if cached is not None:
            hits += 1
            continue
        field = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal,
            resolution=cfg.map.resolution,
            yaw_bins=cfg.dataset.teacher_yaw_bins,
            rho=cfg.vehicle.min_turn_radius,
            fill_value=cfg.dataset.max_teacher_value,
            step_size=cfg.dataset.teacher_rs_step_size,
            backend=cfg.dataset.teacher_rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=cost_cfg,
        )
        save_rs_field_cache(cache_dir, key, field)
        misses += 1
    return hits, misses


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

    train = generate_benchmark_split(
        args.output / "train",
        tuple(int(v) for v in args.train_counts),
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=args.seed + 101,
    )
    val = generate_benchmark_split(
        args.output / "val",
        tuple(int(v) for v in args.val_counts),
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=args.seed + 202,
    )
    test = generate_benchmark_split(
        args.output / "test",
        tuple(int(v) for v in args.test_counts),
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=args.seed + 303,
    )

    print(describe_split("train", train))
    print(describe_split("val", val))
    print(describe_split("test", test))
    print(
        f"teacher: mode={cfg.dataset.teacher_mode} yaw_bins={cfg.dataset.teacher_yaw_bins} "
        f"rs_backend={cfg.dataset.teacher_rs_backend} rs_step={cfg.dataset.teacher_rs_step_size:.2f} "
        f"hybrid_alpha={cfg.dataset.hybrid_obstacle_alpha:.3f} "
        f"hybrid_threshold={cfg.dataset.hybrid_obstacle_threshold_m:.2f}"
    )

    if args.precompute_rs_cache:
        cache_dir = args.rs_cache_dir if args.rs_cache_dir is not None else (args.output / "rs_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        stats = {}
        for split in ["train", "val", "test"]:
            h, m = _precompute_rs_cache(args.output / split, cache_dir, cfg)
            stats[split] = {"hits": int(h), "misses": int(m)}
        print(f"rs cache precompute done: dir={cache_dir}")
        print(stats)


if __name__ == "__main__":
    main()
