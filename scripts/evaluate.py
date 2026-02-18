from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.teacher import compute_2d_dijkstra_field, fill_unreachable
from network.inference import NeuralHeuristicPredictor
from planner.evaluate import evaluate_on_dataset
from utils.common import ensure_dirs, set_seed
from utils.visualization import save_field_overview, save_path_comparison


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate baseline vs neural-guided planning")
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/heuristic_net.pt"))
    p.add_argument("--device", type=str, default=DEFAULT_CONFIG.train.device)
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    return p.parse_args()


def _print_table(summary: dict, baseline_name: str) -> None:
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
    cfg.train.device = args.device
    set_seed(args.seed)
    ensure_dirs([cfg.paths.output_dir, cfg.paths.figures_dir, cfg.paths.logs_dir])

    predictor = NeuralHeuristicPredictor(args.checkpoint, device=args.device, gaussian_sigma=cfg.dataset.gaussian_sigma)
    summary_geo, rows_geo, best_geo = evaluate_on_dataset(
        cfg,
        args.data / "test",
        predictor,
        cfg.paths.logs_dir,
        baseline_anchor_mode="euclidean",
        neural_anchor_mode="euclidean",
        tag="eval_geometric",
    )
    summary_blind, rows_blind, best_blind = evaluate_on_dataset(
        cfg,
        args.data / "test",
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

    with (cfg.paths.logs_dir / "eval_summary.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "geometric_vs_neural": summary_geo_dict,
                "blind_vs_neural": summary_blind_dict,
            },
            f,
            indent=2,
        )

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

    print(f"Saved logs under: {cfg.paths.logs_dir}")
    print(f"Saved figures under: {cfg.paths.figures_dir}")


if __name__ == "__main__":
    main()
