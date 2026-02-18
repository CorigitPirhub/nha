from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.dataset_builder import describe_split, generate_dataset_split
from network.inference import NeuralHeuristicPredictor
from network.train import train_network
from planner.evaluate import evaluate_on_dataset
from utils.common import ensure_dirs, set_seed
from utils.visualization import save_field_overview, save_path_comparison, save_training_curve
from env.teacher import compute_2d_dijkstra_field, fill_unreachable


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="End-to-end demo for neural-guided Hybrid A*")
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    p.add_argument("--train-size", type=int, default=80)
    p.add_argument("--val-size", type=int, default=16)
    p.add_argument("--test-size", type=int, default=12)
    p.add_argument("--epochs", type=int, default=6)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--device", type=str, default=DEFAULT_CONFIG.train.device)
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--output-dir", type=Path, default=Path("outputs"))
    return p.parse_args()


def _print_table(summary: dict, baseline_name: str) -> None:
    print("\n=== Baseline vs Neural-Guided Hybrid A* ===")
    print(f"| metric | {baseline_name} | neural-guided |")
    print("|---|---:|---:|")
    print(f"| success rate | {summary['baseline_success_rate']:.3f} | {summary['neural_success_rate']:.3f} |")
    print(f"| avg expansions | {summary['baseline_avg_expansions']:.1f} | {summary['neural_avg_expansions']:.1f} |")
    print(f"| avg runtime (ms) | {summary['baseline_avg_time_ms']:.2f} | {summary['neural_avg_time_ms']:.2f} |")
    print(f"| avg path cost | {summary['baseline_avg_cost']:.2f} | {summary['neural_avg_cost']:.2f} |")
    print(f"| expansion reduction | - | {summary['expansion_reduction_ratio'] * 100.0:.2f}% |")


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    cfg.seed = args.seed
    cfg.dataset.train_size = args.train_size
    cfg.dataset.val_size = args.val_size
    cfg.dataset.test_size = args.test_size
    cfg.train.epochs = args.epochs
    cfg.train.batch_size = args.batch_size
    cfg.train.device = args.device

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

    print("\n[1/4] Generating datasets...")
    train_counts = generate_dataset_split(
        cfg.paths.data_dir / "train",
        cfg.dataset.train_size,
        cfg.map,
        cfg.dataset,
        seed=cfg.seed + 11,
    )
    val_counts = generate_dataset_split(
        cfg.paths.data_dir / "val",
        cfg.dataset.val_size,
        cfg.map,
        cfg.dataset,
        seed=cfg.seed + 22,
    )
    test_counts = generate_dataset_split(
        cfg.paths.data_dir / "test",
        cfg.dataset.test_size,
        cfg.map,
        cfg.dataset,
        seed=cfg.seed + 33,
    )
    print(describe_split("train", train_counts))
    print(describe_split("val", val_counts))
    print(describe_split("test", test_counts))

    print("\n[2/4] Training neural heuristic model...")
    ckpt_path, metrics = train_network(cfg, cfg.paths.data_dir / "train", cfg.paths.data_dir / "val")
    print(f"checkpoint: {ckpt_path}")
    print(f"best_val_loss: {metrics['best_val_loss']:.6f}")

    with (cfg.paths.logs_dir / "train_metrics.json").open("r", encoding="utf-8") as f:
        train_hist = json.load(f)
    save_training_curve(train_hist["train_loss"], train_hist["val_loss"], cfg.paths.figures_dir / "training_curve.png")

    print("\n[3/4] Evaluating baseline vs neural-guided planner...")
    predictor = NeuralHeuristicPredictor(ckpt_path, device=cfg.train.device, gaussian_sigma=cfg.dataset.gaussian_sigma)
    summary_geo, rows_geo, best_geo = evaluate_on_dataset(
        cfg,
        cfg.paths.data_dir / "test",
        predictor,
        cfg.paths.logs_dir,
        baseline_anchor_mode="euclidean",
        neural_anchor_mode="euclidean",
        tag="eval_geometric",
    )
    summary_blind, rows_blind, best_blind = evaluate_on_dataset(
        cfg,
        cfg.paths.data_dir / "test",
        predictor,
        cfg.paths.logs_dir,
        baseline_anchor_mode="zero",
        neural_anchor_mode="euclidean",
        tag="eval_blind",
    )
    summary_geo_dict = summary_geo.__dict__
    summary_blind_dict = summary_blind.__dict__

    print("\n[Geometric heuristic vs neural-guided]")
    _print_table(summary_geo_dict, baseline_name="geometric")
    print("\n[Blind search vs neural-guided]")
    _print_table(summary_blind_dict, baseline_name="blind(h=0)")

    print("\n[4/4] Saving qualitative visualizations...")
    best = best_blind if best_blind["payload"] is not None else best_geo
    if best["payload"] is not None:
        payload = best["payload"]
        teacher = compute_2d_dijkstra_field(
            payload["occupancy"],
            (float(payload["goal"][0]), float(payload["goal"][1])),
            cfg.map.resolution,
        )
        teacher = fill_unreachable(teacher, payload["occupancy"], cfg.dataset.max_teacher_value)

        save_field_overview(
            payload["occupancy"],
            payload["esdf"],
            teacher,
            payload["pred"],
            cfg.paths.figures_dir / "example_fields.png",
            title=f"best_case_{payload['scenario']}",
        )
        save_path_comparison(
            payload["occupancy"],
            payload["baseline_path"],
            payload["neural_path"],
            cfg.map.resolution,
            cfg.paths.figures_dir / "example_paths.png",
            start=tuple(float(v) for v in payload["start"]),
            goal=tuple(float(v) for v in payload["goal"]),
            title=f"path_compare_{payload['scenario']}",
        )

    with (cfg.paths.logs_dir / "demo_summary.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "config": {
                    "seed": cfg.seed,
                    "train_size": cfg.dataset.train_size,
                    "val_size": cfg.dataset.val_size,
                    "test_size": cfg.dataset.test_size,
                    "epochs": cfg.train.epochs,
                    "batch_size": cfg.train.batch_size,
                    "device": cfg.train.device,
                },
                "train_metrics": metrics,
                "eval_summary": {
                    "geometric_vs_neural": summary_geo_dict,
                    "blind_vs_neural": summary_blind_dict,
                },
                "num_eval_cases": len(rows_geo),
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
