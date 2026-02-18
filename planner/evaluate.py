from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from config import ExperimentConfig
from network.inference import NeuralHeuristicPredictor
from planner.heuristics import FieldHeuristic, euclidean_heuristic
from planner.hybrid_astar import HybridAStarPlanner, PlanResult


@dataclass
class CaseMetrics:
    case_id: int
    scenario: str
    baseline_success: bool
    neural_success: bool
    baseline_expansions: int
    neural_expansions: int
    baseline_time_ms: float
    neural_time_ms: float
    baseline_cost: float
    neural_cost: float


@dataclass
class EvalSummary:
    num_cases: int
    baseline_success_rate: float
    neural_success_rate: float
    baseline_avg_expansions: float
    neural_avg_expansions: float
    baseline_avg_time_ms: float
    neural_avg_time_ms: float
    baseline_avg_cost: float
    neural_avg_cost: float
    expansion_reduction_ratio: float


def _run_planner(
    cfg: ExperimentConfig,
    occupancy: np.ndarray,
    esdf: np.ndarray,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    guidance_field: Optional[np.ndarray],
    anchor_mode: str = "euclidean",
) -> PlanResult:
    planner = HybridAStarPlanner(
        occupancy=occupancy,
        resolution=cfg.map.resolution,
        vehicle_cfg=cfg.vehicle,
        planner_cfg=cfg.planner,
        esdf=esdf,
    )

    guidance_fn = None
    if guidance_field is not None:
        free_vals = guidance_field[~occupancy]
        clip_max = float(np.percentile(free_vals, 95) * 1.5) if free_vals.size > 0 else cfg.dataset.max_teacher_value
        clip_max = float(np.clip(clip_max, 1.0, cfg.dataset.max_teacher_value))
        guidance_fn = FieldHeuristic(
            guidance_field,
            cfg.map.resolution,
            max_value=clip_max,
            scale=0.8,
        )

    if anchor_mode == "euclidean":
        anchor_fn = euclidean_heuristic((goal[0], goal[1]))
    elif anchor_mode == "zero":
        anchor_fn = lambda x, y, yaw: 0.0
    else:
        raise ValueError(f"Unknown anchor mode: {anchor_mode}")

    return planner.plan(start=start, goal=goal, guidance_fn=guidance_fn, anchor_fn=anchor_fn)


def _safe_mean(values: List[float]) -> float:
    if not values:
        return float("nan")
    return float(np.mean(values))


def evaluate_on_dataset(
    cfg: ExperimentConfig,
    test_dir: Path,
    predictor: NeuralHeuristicPredictor,
    out_dir: Path,
    baseline_anchor_mode: str = "euclidean",
    neural_anchor_mode: str = "euclidean",
    tag: str = "eval",
) -> tuple[EvalSummary, List[CaseMetrics], Dict[str, np.ndarray]]:
    files = sorted(test_dir.glob("*.npz"))
    if not files:
        raise RuntimeError(f"No test files found in {test_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    rows: List[CaseMetrics] = []

    best_example = {
        "reduction": -np.inf,
        "payload": None,
    }

    for case_id, p in enumerate(files):
        with np.load(p, allow_pickle=False) as data:
            occupancy = data["occupancy"].astype(bool)
            esdf = data["esdf"].astype(np.float32)
            start = tuple(float(v) for v in data["start"].astype(np.float32))
            goal = tuple(float(v) for v in data["goal"].astype(np.float32))
            scenario = str(data["scenario"]) if "scenario" in data else "unknown"

        baseline = _run_planner(
            cfg,
            occupancy,
            esdf,
            start,
            goal,
            guidance_field=None,
            anchor_mode=baseline_anchor_mode,
        )

        pred_field = predictor.predict_field(occupancy, esdf, start, goal, resolution=cfg.map.resolution)
        neural = _run_planner(
            cfg,
            occupancy,
            esdf,
            start,
            goal,
            guidance_field=pred_field,
            anchor_mode=neural_anchor_mode,
        )

        row = CaseMetrics(
            case_id=case_id,
            scenario=scenario,
            baseline_success=baseline.success,
            neural_success=neural.success,
            baseline_expansions=baseline.expansions,
            neural_expansions=neural.expansions,
            baseline_time_ms=baseline.runtime_ms,
            neural_time_ms=neural.runtime_ms,
            baseline_cost=float(baseline.cost) if np.isfinite(baseline.cost) else float("nan"),
            neural_cost=float(neural.cost) if np.isfinite(neural.cost) else float("nan"),
        )
        rows.append(row)

        if baseline.success and neural.success:
            reduction = baseline.expansions - neural.expansions
            if reduction > best_example["reduction"]:
                best_example = {
                    "reduction": reduction,
                    "payload": {
                        "occupancy": occupancy,
                        "esdf": esdf,
                        "start": np.asarray(start, dtype=np.float32),
                        "goal": np.asarray(goal, dtype=np.float32),
                        "pred": pred_field,
                        "baseline_path": baseline.path,
                        "neural_path": neural.path,
                        "scenario": scenario,
                    },
                }

    baseline_succ = [r for r in rows if r.baseline_success]
    neural_succ = [r for r in rows if r.neural_success]
    both_succ = [r for r in rows if r.baseline_success and r.neural_success]

    b_exp = [float(r.baseline_expansions) for r in baseline_succ]
    n_exp = [float(r.neural_expansions) for r in neural_succ]
    b_t = [r.baseline_time_ms for r in baseline_succ]
    n_t = [r.neural_time_ms for r in neural_succ]
    b_c = [r.baseline_cost for r in baseline_succ if np.isfinite(r.baseline_cost)]
    n_c = [r.neural_cost for r in neural_succ if np.isfinite(r.neural_cost)]

    exp_red = float("nan")
    if both_succ:
        b_both = np.array([r.baseline_expansions for r in both_succ], dtype=np.float32)
        n_both = np.array([r.neural_expansions for r in both_succ], dtype=np.float32)
        exp_red = float(np.mean((b_both - n_both) / np.maximum(b_both, 1.0)))

    summary = EvalSummary(
        num_cases=len(rows),
        baseline_success_rate=len(baseline_succ) / max(len(rows), 1),
        neural_success_rate=len(neural_succ) / max(len(rows), 1),
        baseline_avg_expansions=_safe_mean(b_exp),
        neural_avg_expansions=_safe_mean(n_exp),
        baseline_avg_time_ms=_safe_mean(b_t),
        neural_avg_time_ms=_safe_mean(n_t),
        baseline_avg_cost=_safe_mean(b_c),
        neural_avg_cost=_safe_mean(n_c),
        expansion_reduction_ratio=exp_red,
    )

    csv_path = out_dir / f"{tag}_cases.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))

    with (out_dir / f"{tag}_summary.json").open("w", encoding="utf-8") as f:
        json.dump(asdict(summary), f, indent=2)

    return summary, rows, best_example
