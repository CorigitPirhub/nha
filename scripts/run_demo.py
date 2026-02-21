from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shutil
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
from utils.visualization import (
    save_efficiency_scatter,
    save_nonholonomic_field_comparison,
    save_search_progress_animation,
    save_search_tree_comparison,
    save_training_curve,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="End-to-end demo with nonholonomic teacher")
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    p.add_argument("--train-counts", type=int, nargs=3, default=[24, 24, 24])
    p.add_argument("--val-counts", type=int, nargs=3, default=[6, 6, 6])
    p.add_argument("--test-counts", type=int, nargs=3, default=[8, 8, 8])
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--under-weight", type=float, default=1.0)
    p.add_argument("--prediction-mode", type=str, default="residual", choices=["absolute", "residual"])
    p.add_argument("--type-c-weight", type=float, default=1.0)
    p.add_argument("--residual-alpha", type=float, default=DEFAULT_CONFIG.planner.residual_alpha)
    p.add_argument("--use-rs-cache", dest="use_rs_cache", action="store_true", default=True)
    p.add_argument("--no-rs-cache", dest="use_rs_cache", action="store_false")
    p.add_argument("--rs-cache-dir", type=Path, default=Path("outputs/rs_cache"))
    p.add_argument(
        "--clear-rs-cache",
        dest="clear_rs_cache",
        action="store_true",
        default=True,
        help="Clear RS cache directory before benchmark cold run.",
    )
    p.add_argument(
        "--keep-rs-cache",
        dest="clear_rs_cache",
        action="store_false",
        help="Keep existing RS cache files; cold/hot separation may be invalid.",
    )
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--data-dir", type=Path, default=Path("data_benchmark"))
    p.add_argument("--output-dir", type=Path, default=Path("outputs"))
    p.add_argument(
        "--no-animation",
        action="store_true",
        help="Disable planning-process animation export.",
    )
    p.add_argument(
        "--animation-out",
        type=Path,
        default=None,
        help="Output path for planning animation (.mp4/.gif). Default: <output-dir>/figures/planning_process_demo.mp4",
    )
    p.add_argument("--animation-fps", type=int, default=20, help="Animation frame rate.")
    return p.parse_args()


def _print_method_table(summary: dict) -> None:
    m = summary["methods"]
    print("| method | success rate | avg expansions | avg runtime(ms) | avg total(ms) | avg path cost |")
    print("|---|---:|---:|---:|---:|---:|")
    for key in ["euclidean", "dubins", "rs_consistent", "ours"]:
        v = m[key]
        total = float(v.get("avg_time_total_ms", v["avg_time_ms"]))
        print(
            f"| {key} | {v['success_rate']:.3f} | {v['avg_expansions']:.1f} | {v['avg_time_ms']:.2f} | {total:.2f} | {v['avg_cost']:.2f} |"
        )


def _method_total_ms(summary: dict, method_key: str) -> float:
    v = summary["methods"][method_key]
    return float(v.get("avg_time_total_ms", v["avg_time_ms"]))


def _print_submission_table(cold_summary: dict, hot_summary: dict) -> None:
    labels = {
        "euclidean": "Euclidean",
        "dubins": "Dubins",
        "rs_consistent": "RS-Consistent",
        "ours": "Ours",
    }
    print("\n[Final Submission Table]")
    print("| Method | Avg Expansions | Avg Total Time (ms) - Cold | Avg Total Time (ms) - Hot |")
    print("|---|---:|---:|---:|")
    for key in ["euclidean", "dubins", "rs_consistent", "ours"]:
        exp = float(hot_summary["methods"][key]["avg_expansions"])
        cold_t = _method_total_ms(cold_summary, key)
        hot_t = _method_total_ms(hot_summary, key)
        print(f"| {labels[key]} | {exp:.1f} | {cold_t:.2f} | {hot_t:.2f} |")


def _save_submission_csv(cold_summary: dict, hot_summary: dict, out_path: Path) -> None:
    labels = {
        "euclidean": "Euclidean",
        "dubins": "Dubins",
        "rs_consistent": "RS-Consistent",
        "ours": "Ours",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Method",
                "Avg Expansions",
                "Avg Total Time (ms) - Cold",
                "Avg Total Time (ms) - Hot",
            ]
        )
        for key in ["euclidean", "dubins", "rs_consistent", "ours"]:
            writer.writerow(
                [
                    labels[key],
                    f"{float(hot_summary['methods'][key]['avg_expansions']):.6f}",
                    f"{_method_total_ms(cold_summary, key):.6f}",
                    f"{_method_total_ms(hot_summary, key):.6f}",
                ]
            )


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    cfg.seed = args.seed
    cfg.train.epochs = args.epochs
    cfg.train.batch_size = args.batch_size
    cfg.train.learning_rate = args.lr
    cfg.train.underestimation_weight = args.under_weight
    cfg.train.prediction_mode = args.prediction_mode
    cfg.train.type_c_loss_weight = args.type_c_weight
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

    print("\n[1/5] Building fixed benchmark dataset (Type A/B/C)...")
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

    print(f"\n[2/5] Training neural model on device={cfg.train.device} ...")
    ckpt_path, metrics = train_network(cfg, cfg.paths.data_dir / "train", cfg.paths.data_dir / "val")
    print(f"checkpoint: {ckpt_path}")
    print(f"best_val_loss: {metrics['best_val_loss']:.6f}")

    with (cfg.paths.logs_dir / "train_metrics.json").open("r", encoding="utf-8") as f:
        train_hist = json.load(f)
    save_training_curve(train_hist["train_loss"], train_hist["val_loss"], cfg.paths.figures_dir / "training_curve.png")

    bench_mode = "cold + hot cache" if args.use_rs_cache else "single pass"
    print(
        f"\n[3/5] Running benchmark ({bench_mode}): "
        "Euclidean vs Dubins vs RS-Consistent vs Ours..."
    )
    predictor = NeuralHeuristicPredictor(ckpt_path, device=cfg.train.device, gaussian_sigma=cfg.dataset.gaussian_sigma)

    cold_summary: dict
    hot_summary: dict
    rows = []
    best = {"payload": None}
    if args.use_rs_cache:
        if args.clear_rs_cache and args.rs_cache_dir.exists():
            shutil.rmtree(args.rs_cache_dir)
        args.rs_cache_dir.mkdir(parents=True, exist_ok=True)

        cold_summary, _, cold_best = evaluate_benchmark(
            cfg,
            cfg.paths.data_dir / "test",
            predictor,
            cfg.paths.logs_dir,
            tag="benchmark_cache_cold",
            residual_alpha=float(args.residual_alpha),
            use_rs_cache=True,
            rs_cache_dir=args.rs_cache_dir,
        )
        hot_summary, hot_rows, hot_best = evaluate_benchmark(
            cfg,
            cfg.paths.data_dir / "test",
            predictor,
            cfg.paths.logs_dir,
            tag="benchmark_cache_hot",
            residual_alpha=float(args.residual_alpha),
            use_rs_cache=True,
            rs_cache_dir=args.rs_cache_dir,
        )
        rows = hot_rows
        best = hot_best if hot_best.get("payload") is not None else cold_best
        cstat = cold_summary.get("rs_cache_stats", {})
        hstat = hot_summary.get("rs_cache_stats", {})
        print(
            f"Cold cache stats: hits={cstat.get('hits', 0)} misses={cstat.get('misses', 0)} "
            f"hit_rate={100.0 * float(cstat.get('hit_rate', 0.0)):.2f}%"
        )
        print(
            f"Hot cache stats: hits={hstat.get('hits', 0)} misses={hstat.get('misses', 0)} "
            f"hit_rate={100.0 * float(hstat.get('hit_rate', 0.0)):.2f}%"
        )
    else:
        hot_summary, rows, best = evaluate_benchmark(
            cfg,
            cfg.paths.data_dir / "test",
            predictor,
            cfg.paths.logs_dir,
            tag="benchmark",
            residual_alpha=float(args.residual_alpha),
            use_rs_cache=False,
            rs_cache_dir=args.rs_cache_dir,
        )
        cold_summary = hot_summary

    _print_method_table(hot_summary)
    imp = hot_summary["improvement_ours_vs_euclidean"]
    print(
        f"\nOurs vs Euclidean: expansion reduction={100.0 * imp['expansion_reduction_ratio']:.2f}% "
        f"time reduction={100.0 * imp['time_reduction_ratio']:.2f}%"
    )
    if "improvement_ours_vs_dubins" in hot_summary:
        print(
            "Ours vs Dubins: expansion reduction="
            f"{100.0 * hot_summary['improvement_ours_vs_dubins']['expansion_reduction_ratio']:.2f}%"
        )
    if "improvement_ours_vs_rs_consistent" in hot_summary:
        print(
            "Ours vs RS-Consistent: expansion reduction="
            f"{100.0 * hot_summary['improvement_ours_vs_rs_consistent']['expansion_reduction_ratio']:.2f}%"
        )

    print("\nPer-category (avg expansions):")
    print("| category | euclidean | dubins | rs_consistent | ours |")
    print("|---|---:|---:|---:|---:|")
    for cat in ["A", "B", "C"]:
        if cat not in hot_summary["by_category"]:
            continue
        s = hot_summary["by_category"][cat]
        print(
            f"| {cat} | {s['euclidean']['avg_expansions']:.1f} | {s['dubins']['avg_expansions']:.1f} "
            f"| {s['rs_consistent']['avg_expansions']:.1f} | {s['ours']['avg_expansions']:.1f} |"
        )

    _print_submission_table(cold_summary, hot_summary)
    submission_csv = cfg.paths.logs_dir / "final_submission_table.csv"
    _save_submission_csv(cold_summary, hot_summary, submission_csv)
    save_efficiency_scatter(
        hot_summary,
        cfg.paths.figures_dir / "efficiency_scatter_cache_hot.png",
        title="Efficiency-Quality Tradeoff (Cache Hot)",
    )
    anim_path = None

    print("\n[4/5] Saving qualitative search-tree visualization...")
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
        if not args.no_animation:
            anim_out = args.animation_out if args.animation_out is not None else (cfg.paths.figures_dir / "planning_process_demo.mp4")
            anim_path = save_search_progress_animation(
                occupancy=p["occupancy"],
                euclidean_expanded=p["euclidean_expanded"],
                ours_expanded=p["ours_expanded"],
                euclidean_path=p["euclidean_path"],
                ours_path=p["ours_path"],
                resolution=cfg.map.resolution,
                start=tuple(float(v) for v in p["start"]),
                goal=tuple(float(v) for v in p["goal"]),
                out_path=anim_out,
                title=f"Type-C Planning Process ({p['scenario']})",
                fps=max(int(args.animation_fps), 1),
            )
            print(f"Saved planning animation: {anim_path}")

    print("\n[5/5] Writing final summary logs...")
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
                    "learning_rate": cfg.train.learning_rate,
                    "prediction_mode": cfg.train.prediction_mode,
                    "underestimation_weight": cfg.train.underestimation_weight,
                    "type_c_loss_weight": cfg.train.type_c_loss_weight,
                    "residual_alpha": float(args.residual_alpha),
                    "use_rs_cache": bool(args.use_rs_cache),
                    "clear_rs_cache": bool(args.clear_rs_cache),
                    "rs_cache_dir": str(args.rs_cache_dir),
                    "device": cfg.train.device,
                    "teacher_yaw_bins": cfg.dataset.teacher_yaw_bins,
                    "teacher_mode": cfg.dataset.teacher_mode,
                },
                "train_metrics": metrics,
                "benchmark_summary_hot": hot_summary,
                "benchmark_summary_cold": cold_summary,
                "num_eval_cases": len(rows),
            },
            f,
            indent=2,
        )

    print("\nArtifacts:")
    print(f"- logs: {cfg.paths.logs_dir}")
    print(f"- submission table: {submission_csv}")
    print(f"- figures: {cfg.paths.figures_dir}")
    if anim_path is not None:
        print(f"- planning animation: {anim_path}")
    print(f"- checkpoints: {cfg.paths.checkpoints_dir}")


if __name__ == "__main__":
    main()
