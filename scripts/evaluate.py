from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from network.inference import NeuralHeuristicPredictor
from planner.evaluate import evaluate_benchmark
from utils.common import ensure_dirs, set_seed
from utils.visualization import save_nonholonomic_field_comparison, save_search_tree_comparison


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark: Euclidean vs Dubins vs RS-Consistent vs Neural Guided")
    p.add_argument("--data", type=Path, default=Path("data_benchmark"))
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/heuristic_net.pt"))
    p.add_argument("--teacher-yaw-bins", type=int, default=DEFAULT_CONFIG.dataset.teacher_yaw_bins)
    p.add_argument("--teacher-rs-backend", type=str, default=DEFAULT_CONFIG.dataset.teacher_rs_backend, choices=["auto", "rsplan", "approx"])
    p.add_argument("--teacher-rs-step-size", type=float, default=DEFAULT_CONFIG.dataset.teacher_rs_step_size)
    p.add_argument(
        "--neural-clip",
        type=float,
        default=-1.0,
        help="Override neural clip factor to Euclidean anchor upper bound; <=0 means adaptive.",
    )
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    p.add_argument(
        "--skip-figures",
        action="store_true",
        help="Skip qualitative figure generation for faster, non-blocking benchmark runs.",
    )
    return p.parse_args()


def _print_method_table(summary: dict) -> None:
    m = summary["methods"]
    print("| method | success rate | avg expansions | avg runtime(ms) | avg path cost |")
    print("|---|---:|---:|---:|---:|")
    for key in ["euclidean", "dubins", "rs_consistent", "ours"]:
        v = m[key]
        print(
            f"| {key} | {v['success_rate']:.3f} | {v['avg_expansions']:.1f} | {v['avg_time_ms']:.2f} | {v['avg_cost']:.2f} |"
        )


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    cfg.train.device = args.device
    cfg.dataset.teacher_yaw_bins = int(args.teacher_yaw_bins)
    cfg.dataset.teacher_rs_backend = str(args.teacher_rs_backend)
    cfg.dataset.teacher_rs_step_size = float(args.teacher_rs_step_size)
    set_seed(args.seed)
    ensure_dirs([cfg.paths.output_dir, cfg.paths.figures_dir, cfg.paths.logs_dir])

    predictor = NeuralHeuristicPredictor(args.checkpoint, device=args.device, gaussian_sigma=cfg.dataset.gaussian_sigma)
    clip_override = None if args.neural_clip <= 0.0 else float(args.neural_clip)
    summary, rows, best = evaluate_benchmark(
        cfg,
        args.data / "test",
        predictor,
        cfg.paths.logs_dir,
        tag="benchmark",
        neural_clip_override=clip_override,
    )

    print("\n[Overall Benchmark]")
    _print_method_table(summary)
    imp = summary["improvement_ours_vs_euclidean"]
    print(
        f"\nOurs vs Euclidean: expansion reduction={100.0 * imp['expansion_reduction_ratio']:.2f}% "
        f"time reduction={100.0 * imp['time_reduction_ratio']:.2f}%"
    )
    imp_db = summary.get("improvement_ours_vs_dubins", {})
    imp_rs = summary.get("improvement_ours_vs_rs_consistent", {})
    if "expansion_reduction_ratio" in imp_db:
        print(f"Ours vs Dubins: expansion reduction={100.0 * imp_db['expansion_reduction_ratio']:.2f}%")
    if "expansion_reduction_ratio" in imp_rs:
        print(f"Ours vs RS-Consistent: expansion reduction={100.0 * imp_rs['expansion_reduction_ratio']:.2f}%")

    print("\n[Per-category average expansions]")
    print("| category | euclidean | dubins | rs_consistent | ours |")
    print("|---|---:|---:|---:|---:|")
    for cat in ["A", "B", "C"]:
        if cat not in summary["by_category"]:
            continue
        s = summary["by_category"][cat]
        print(
            f"| {cat} | {s['euclidean']['avg_expansions']:.1f} | {s['dubins']['avg_expansions']:.1f} | {s['rs_consistent']['avg_expansions']:.1f} | {s['ours']['avg_expansions']:.1f} |"
        )

    with (cfg.paths.logs_dir / "benchmark_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    if (not args.skip_figures) and best["payload"] is not None:
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
        save_nonholonomic_field_comparison(
            occupancy=p["occupancy"],
            teacher_3d=p.get("dubins_field"),
            pred_3d=p.get("rs_cons_field"),
            goal=tuple(float(v) for v in p["goal"]),
            yaw_ref=float(p["start"][2]),
            resolution=cfg.map.resolution,
            out_path=cfg.paths.figures_dir / "teacher_dubins_vs_rs_consistent.png",
            title=f"Type-C Teacher Compare ({p['scenario']})",
        )

    print(f"Saved logs under: {cfg.paths.logs_dir}")
    print(f"Saved figures under: {cfg.paths.figures_dir}")


if __name__ == "__main__":
    main()
