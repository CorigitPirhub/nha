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
from env.dataset_builder import describe_split, generate_benchmark_split
from network.inference import NeuralHeuristicPredictor
from network.train import train_network
from planner.evaluate import evaluate_benchmark
from utils.common import ensure_dirs, set_seed
from utils.visualization import save_nonholonomic_field_comparison, save_search_tree_comparison, save_training_curve


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="End-to-end demo with nonholonomic teacher")
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    p.add_argument("--train-counts", type=int, nargs=3, default=[24, 24, 24])
    p.add_argument("--val-counts", type=int, nargs=3, default=[6, 6, 6])
    p.add_argument("--test-counts", type=int, nargs=3, default=[8, 8, 8])
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--data-dir", type=Path, default=Path("data_benchmark"))
    p.add_argument("--output-dir", type=Path, default=Path("outputs"))
    return p.parse_args()


def _print_method_table(summary: dict) -> None:
    m = summary["methods"]
    print("| method | success rate | avg expansions | avg runtime(ms) | avg path cost |")
    print("|---|---:|---:|---:|---:|")
    for key in ["euclidean", "dubins", "ours"]:
        v = m[key]
        print(
            f"| {key} | {v['success_rate']:.3f} | {v['avg_expansions']:.1f} | {v['avg_time_ms']:.2f} | {v['avg_cost']:.2f} |"
        )


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    cfg.seed = args.seed
    cfg.train.epochs = args.epochs
    cfg.train.batch_size = args.batch_size
    cfg.train.device = args.device

    if cfg.train.device.startswith("cuda") and not torch.cuda.is_available():
        cfg.train.device = "cpu"

    cfg.paths.data_dir = args.data_dir
    cfg.paths.output_dir = args.output_dir
    cfg.paths.checkpoints_dir = args.output_dir / "checkpoints"
    cfg.paths.figures_dir = args.output_dir / "figures"
    cfg.paths.logs_dir = args.output_dir / "logs"

    ensure_dirs([
        cfg.paths.data_dir,
        cfg.paths.output_dir,
        cfg.paths.checkpoints_dir,
        cfg.paths.figures_dir,
        cfg.paths.logs_dir,
    ])
    set_seed(cfg.seed)

    print("\n[1/4] Building fixed benchmark dataset (Type A/B/C)...")
    train_counts = generate_benchmark_split(
        cfg.paths.data_dir / "train",
        tuple(args.train_counts),
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=cfg.seed + 101,
    )
    val_counts = generate_benchmark_split(
        cfg.paths.data_dir / "val",
        tuple(args.val_counts),
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=cfg.seed + 202,
    )
    test_counts = generate_benchmark_split(
        cfg.paths.data_dir / "test",
        tuple(args.test_counts),
        cfg.map,
        cfg.dataset,
        cfg.vehicle,
        cfg.planner,
        seed=cfg.seed + 303,
    )
    print(describe_split("train", train_counts))
    print(describe_split("val", val_counts))
    print(describe_split("test", test_counts))

    print(f"\n[2/4] Training neural model on device={cfg.train.device} ...")
    ckpt_path, metrics = train_network(cfg, cfg.paths.data_dir / "train", cfg.paths.data_dir / "val")
    print(f"checkpoint: {ckpt_path}")
    print(f"best_val_loss: {metrics['best_val_loss']:.6f}")

    with (cfg.paths.logs_dir / "train_metrics.json").open("r", encoding="utf-8") as f:
        train_hist = json.load(f)
    save_training_curve(train_hist["train_loss"], train_hist["val_loss"], cfg.paths.figures_dir / "training_curve.png")

    print("\n[3/4] Running benchmark: Euclidean vs Dubins vs Ours...")
    predictor = NeuralHeuristicPredictor(ckpt_path, device=cfg.train.device, gaussian_sigma=cfg.dataset.gaussian_sigma)
    summary, rows, best = evaluate_benchmark(cfg, cfg.paths.data_dir / "test", predictor, cfg.paths.logs_dir, tag="benchmark")

    _print_method_table(summary)
    imp = summary["improvement_ours_vs_euclidean"]
    print(
        f"\nOurs vs Euclidean: expansion reduction={100.0 * imp['expansion_reduction_ratio']:.2f}% "
        f"time reduction={100.0 * imp['time_reduction_ratio']:.2f}%"
    )

    print("\nPer-category (avg expansions):")
    print("| category | euclidean | dubins | ours |")
    print("|---|---:|---:|---:|")
    for cat in ["A", "B", "C"]:
        if cat not in summary["by_category"]:
            continue
        s = summary["by_category"][cat]
        print(
            f"| {cat} | {s['euclidean']['avg_expansions']:.1f} | {s['dubins']['avg_expansions']:.1f} | {s['ours']['avg_expansions']:.1f} |"
        )

    print("\n[4/4] Saving qualitative search-tree visualization...")
    if best["payload"] is not None:
        p = best["payload"]
        save_search_tree_comparison(
            occupancy=p["occupancy"],
            euclidean_expanded=p["euclidean_expanded"],
            ours_expanded=p["ours_expanded"],
            euclidean_path=p["euclidean_path"],
            ours_path=p["ours_path"],
            resolution=cfg.map.resolution,
            start=tuple(float(v) for v in p["start"]),
            goal=tuple(float(v) for v in p["goal"]),
            out_path=cfg.paths.figures_dir / "search_tree_type_c_compare.png",
            title=f"Type-C Search Tree ({p['scenario']})",
        )
        save_nonholonomic_field_comparison(
            occupancy=p["occupancy"],
            teacher_3d=p.get("teacher_3d"),
            pred_3d=p.get("pred_field"),
            goal=tuple(float(v) for v in p["goal"]),
            yaw_ref=float(p["start"][2]),
            resolution=cfg.map.resolution,
            out_path=cfg.paths.figures_dir / "nonholonomic_field_compare.png",
            title=f"Type-C Heuristic Field ({p['scenario']})",
        )

    with (cfg.paths.logs_dir / "demo_summary.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "config": {
                    "seed": cfg.seed,
                    "train_counts": list(args.train_counts),
                    "val_counts": list(args.val_counts),
                    "test_counts": list(args.test_counts),
                    "epochs": cfg.train.epochs,
                    "batch_size": cfg.train.batch_size,
                    "device": cfg.train.device,
                    "teacher_yaw_bins": cfg.dataset.teacher_yaw_bins,
                },
                "train_metrics": metrics,
                "benchmark_summary": summary,
                "num_eval_cases": len(rows),
            },
            f,
            indent=2,
        )

    print("\nArtifacts:")
    print(f"- logs: {cfg.paths.logs_dir}")
    print(f"- figures: {cfg.paths.figures_dir}")
    print(f"- checkpoints: {cfg.paths.checkpoints_dir}")


if __name__ == "__main__":
    main()
