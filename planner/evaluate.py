from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from config import ExperimentConfig
from env.dubins import compute_dubins_field
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from network.inference import NeuralHeuristicPredictor
from planner.heuristics import FieldHeuristic, ResidualYawFieldHeuristic, YawFieldHeuristic, euclidean_heuristic
from planner.hybrid_astar import HybridAStarPlanner, PlanResult


@dataclass
class MethodMetrics:
    success: bool
    expansions: int
    time_ms: float
    cost: float


@dataclass
class CaseMetrics:
    case_id: int
    scenario: str
    category: str
    euclidean_success: bool
    euclidean_expansions: int
    euclidean_time_ms: float
    euclidean_cost: float
    dubins_success: bool
    dubins_expansions: int
    dubins_time_ms: float
    dubins_cost: float
    rs_consistent_success: bool
    rs_consistent_expansions: int
    rs_consistent_time_ms: float
    rs_consistent_cost: float
    ours_success: bool
    ours_expansions: int
    ours_time_ms: float
    ours_cost: float


def _safe_mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else float("nan")


def _to_method_metrics(r: PlanResult) -> MethodMetrics:
    return MethodMetrics(
        success=r.success,
        expansions=int(r.expansions),
        time_ms=float(r.runtime_ms),
        cost=float(r.cost) if np.isfinite(r.cost) else float("nan"),
    )


def _run_method(
    planner: HybridAStarPlanner,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    anchor_fn,
    guidance_fn=None,
    main_mode: str = "anchor",
    record_expanded: bool = False,
) -> PlanResult:
    return planner.plan(
        start=start,
        goal=goal,
        anchor_fn=anchor_fn,
        guidance_fn=guidance_fn,
        main_mode=main_mode,
        record_expanded=record_expanded,
    )


def _build_guidance_fn(pred_field: np.ndarray, cfg: ExperimentConfig, occupancy: np.ndarray):
    if pred_field.ndim == 2:
        free_vals = pred_field[~occupancy]
        clip_max = float(np.percentile(free_vals, 98)) if free_vals.size > 0 else cfg.dataset.max_teacher_value
        clip_max = float(np.clip(clip_max, 1.0, cfg.dataset.max_teacher_value))
        return FieldHeuristic(pred_field, cfg.map.resolution, max_value=clip_max, scale=1.0)

    free_vals = pred_field[:, ~occupancy]
    clip_max = float(np.percentile(free_vals, 98)) if free_vals.size > 0 else cfg.dataset.max_teacher_value
    clip_max = float(np.clip(clip_max, 1.0, cfg.dataset.max_teacher_value))
    return YawFieldHeuristic(pred_field, cfg.map.resolution, max_value=clip_max, scale=1.0)


def _make_clipped_anchor(raw_fn, eu_fn, clip_factor: float):
    clip_factor = float(max(1.0, clip_factor))

    def _fn(x: float, y: float, yaw: float) -> float:
        return min(float(raw_fn(x, y, yaw)), clip_factor * float(eu_fn(x, y, yaw)))

    return _fn


def _adaptive_neural_clip_factor(occupancy: np.ndarray) -> float:
    # Conservative in open scenes, more trust in constrained scenes.
    occ_ratio = float(np.mean(occupancy))
    if occ_ratio < 0.12:
        return 1.0
    if occ_ratio < 0.20:
        return 1.2
    return 1.8


def _summarize_rows(rows: list[CaseMetrics]) -> dict:
    out: dict = {"num_cases": len(rows), "methods": {}, "by_category": {}}
    methods = ["euclidean", "dubins", "rs_consistent", "ours"]

    for m in methods:
        succ_rows = [r for r in rows if getattr(r, f"{m}_success")]
        out["methods"][m] = {
            "success_rate": len(succ_rows) / max(len(rows), 1),
            "avg_expansions": _safe_mean([float(getattr(r, f"{m}_expansions")) for r in succ_rows]),
            "avg_time_ms": _safe_mean([float(getattr(r, f"{m}_time_ms")) for r in succ_rows]),
            "avg_cost": _safe_mean([float(getattr(r, f"{m}_cost")) for r in succ_rows if np.isfinite(getattr(r, f"{m}_cost"))]),
        }

    for cat in ["A", "B", "C"]:
        cat_rows = [r for r in rows if r.category == cat]
        if not cat_rows:
            continue
        out["by_category"][cat] = {}
        for m in methods:
            succ_rows = [r for r in cat_rows if getattr(r, f"{m}_success")]
            out["by_category"][cat][m] = {
                "success_rate": len(succ_rows) / max(len(cat_rows), 1),
                "avg_expansions": _safe_mean([float(getattr(r, f"{m}_expansions")) for r in succ_rows]),
                "avg_time_ms": _safe_mean([float(getattr(r, f"{m}_time_ms")) for r in succ_rows]),
                "avg_cost": _safe_mean([float(getattr(r, f"{m}_cost")) for r in succ_rows if np.isfinite(getattr(r, f"{m}_cost"))]),
            }

    # Improvement of ours over Euclidean on cases both successful.
    both = [r for r in rows if r.euclidean_success and r.ours_success]
    if both:
        b = np.array([r.euclidean_expansions for r in both], dtype=np.float32)
        o = np.array([r.ours_expansions for r in both], dtype=np.float32)
        t_b = np.array([r.euclidean_time_ms for r in both], dtype=np.float32)
        t_o = np.array([r.ours_time_ms for r in both], dtype=np.float32)
        b_mean = float(np.mean(b))
        o_mean = float(np.mean(o))
        tb_mean = float(np.mean(t_b))
        to_mean = float(np.mean(t_o))
        out["improvement_ours_vs_euclidean"] = {
            "expansion_reduction_ratio": float((b_mean - o_mean) / max(b_mean, 1.0)),
            "time_reduction_ratio": float((tb_mean - to_mean) / max(tb_mean, 1e-6)),
        }
    else:
        out["improvement_ours_vs_euclidean"] = {
            "expansion_reduction_ratio": float("nan"),
            "time_reduction_ratio": float("nan"),
        }

    both_db = [r for r in rows if r.dubins_success and r.ours_success]
    if both_db:
        b = np.array([r.dubins_expansions for r in both_db], dtype=np.float32)
        o = np.array([r.ours_expansions for r in both_db], dtype=np.float32)
        b_mean = float(np.mean(b))
        o_mean = float(np.mean(o))
        out["improvement_ours_vs_dubins"] = {
            "expansion_reduction_ratio": float((b_mean - o_mean) / max(b_mean, 1.0)),
        }
    else:
        out["improvement_ours_vs_dubins"] = {"expansion_reduction_ratio": float("nan")}

    both_rs = [r for r in rows if r.rs_consistent_success and r.ours_success]
    if both_rs:
        b = np.array([r.rs_consistent_expansions for r in both_rs], dtype=np.float32)
        o = np.array([r.ours_expansions for r in both_rs], dtype=np.float32)
        b_mean = float(np.mean(b))
        o_mean = float(np.mean(o))
        out["improvement_ours_vs_rs_consistent"] = {
            "expansion_reduction_ratio": float((b_mean - o_mean) / max(b_mean, 1.0)),
        }
    else:
        out["improvement_ours_vs_rs_consistent"] = {"expansion_reduction_ratio": float("nan")}

    return out


def evaluate_benchmark(
    cfg: ExperimentConfig,
    test_dir: Path,
    predictor: NeuralHeuristicPredictor,
    out_dir: Path,
    tag: str = "benchmark",
    neural_clip_override: float | None = None,
) -> tuple[dict, list[CaseMetrics], dict]:
    files = sorted(test_dir.glob("*.npz"))
    if not files:
        raise RuntimeError(f"No test files found in {test_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[CaseMetrics] = []
    eval_yaw_bins = int(cfg.dataset.teacher_yaw_bins)
    if predictor.prediction_mode == "residual":
        eval_yaw_bins = int(predictor.out_channels)

    best_type_c = {"gain": -np.inf, "payload": None}

    for case_id, p in enumerate(files):
        with np.load(p, allow_pickle=False) as data:
            occupancy = data["occupancy"].astype(bool)
            esdf = data["esdf"].astype(np.float32)
            teacher_3d = data["teacher_3d"].astype(np.float32) if "teacher_3d" in data else None
            start = tuple(float(v) for v in data["start"].astype(np.float32))
            goal = tuple(float(v) for v in data["goal"].astype(np.float32))
            scenario = str(data["scenario"]) if "scenario" in data else "unknown"
            category = str(data["category"]) if "category" in data else "U"

        planner = HybridAStarPlanner(
            occupancy=occupancy,
            resolution=cfg.map.resolution,
            vehicle_cfg=cfg.vehicle,
            planner_cfg=cfg.planner,
            esdf=esdf,
        )

        clip_factor_dubins = 2.0
        rs_cost_cfg = RSConsistentCostConfig.from_configs(cfg.vehicle, cfg.planner)

        # Baseline 1: Euclidean anchor
        eu_anchor = euclidean_heuristic((goal[0], goal[1]))
        eu_result = _run_method(planner, start, goal, anchor_fn=eu_anchor, guidance_fn=None, main_mode="anchor", record_expanded=(category == "C"))

        # Baseline 2: clipped Dubins anchor (nonholonomic analytic prior with Euclidean safety cap)
        dubins_field = compute_dubins_field(
            occupancy=occupancy,
            goal=goal,
            resolution=cfg.map.resolution,
            yaw_bins=eval_yaw_bins,
            rho=cfg.vehicle.min_turn_radius,
            fill_value=cfg.dataset.max_teacher_value,
        )
        dubins_raw = YawFieldHeuristic(
            dubins_field,
            cfg.map.resolution,
            max_value=cfg.dataset.max_teacher_value,
            scale=1.0,
        )
        dubins_anchor = _make_clipped_anchor(dubins_raw, eu_anchor, clip_factor=clip_factor_dubins)
        db_result = _run_method(planner, start, goal, anchor_fn=dubins_anchor, guidance_fn=None, main_mode="anchor")

        # Baseline 3: planner-consistent Reeds-Shepp analytic anchor.
        rs_cons_field = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal,
            resolution=cfg.map.resolution,
            yaw_bins=eval_yaw_bins,
            rho=cfg.vehicle.min_turn_radius,
            fill_value=cfg.dataset.max_teacher_value,
            step_size=cfg.dataset.teacher_rs_step_size,
            backend=cfg.dataset.teacher_rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=rs_cost_cfg,
        )
        rs_cons_anchor = YawFieldHeuristic(
            rs_cons_field,
            cfg.map.resolution,
            max_value=cfg.dataset.max_teacher_value,
            scale=1.0,
        )
        rs_result = _run_method(planner, start, goal, anchor_fn=rs_cons_anchor, guidance_fn=None, main_mode="anchor")

        # Ours: residual-corrected anchor or absolute neural anchor.
        if predictor.prediction_mode == "residual":
            pred_residual = predictor.predict_residual_field(occupancy, esdf, start, goal, resolution=cfg.map.resolution)
            # Residual branch should only add environment-aware penalty, never weaken RS analytical prior.
            pred_residual = np.maximum(pred_residual, 0.0).astype(np.float32)
            neural_raw = ResidualYawFieldHeuristic(
                base_field_3d=rs_cons_field,
                residual_field_3d=pred_residual,
                resolution=cfg.map.resolution,
                max_value=cfg.dataset.max_teacher_value,
                scale=1.0,
            )
            pred_field = (rs_cons_field + pred_residual).astype(np.float32)
            pred_field[:, occupancy] = cfg.dataset.max_teacher_value
            neural_anchor = neural_raw
        else:
            pred_field = predictor.predict_field(occupancy, esdf, start, goal, resolution=cfg.map.resolution)
            neural_raw = _build_guidance_fn(pred_field, cfg, occupancy)
            neural_anchor = _make_clipped_anchor(
                neural_raw,
                eu_anchor,
                clip_factor=float(neural_clip_override)
                if neural_clip_override is not None
                else _adaptive_neural_clip_factor(occupancy),
            )
        ours_result = _run_method(
            planner,
            start,
            goal,
            anchor_fn=neural_anchor,
            guidance_fn=None,
            main_mode="anchor",
            record_expanded=(category == "C"),
        )

        eu = _to_method_metrics(eu_result)
        db = _to_method_metrics(db_result)
        rs = _to_method_metrics(rs_result)
        ou = _to_method_metrics(ours_result)

        rows.append(
            CaseMetrics(
                case_id=case_id,
                scenario=scenario,
                category=category,
                euclidean_success=eu.success,
                euclidean_expansions=eu.expansions,
                euclidean_time_ms=eu.time_ms,
                euclidean_cost=eu.cost,
                dubins_success=db.success,
                dubins_expansions=db.expansions,
                dubins_time_ms=db.time_ms,
                dubins_cost=db.cost,
                rs_consistent_success=rs.success,
                rs_consistent_expansions=rs.expansions,
                rs_consistent_time_ms=rs.time_ms,
                rs_consistent_cost=rs.cost,
                ours_success=ou.success,
                ours_expansions=ou.expansions,
                ours_time_ms=ou.time_ms,
                ours_cost=ou.cost,
            )
        )

        if category == "C" and eu.success and ou.success:
            gain = eu.expansions - ou.expansions
            if gain > best_type_c["gain"]:
                best_type_c = {
                    "gain": gain,
                    "payload": {
                        "occupancy": occupancy,
                        "start": np.asarray(start, dtype=np.float32),
                        "goal": np.asarray(goal, dtype=np.float32),
                        "scenario": scenario,
                        "category": category,
                        "esdf": esdf,
                        "teacher_3d": teacher_3d,
                        "dubins_field": dubins_field,
                        "rs_cons_field": rs_cons_field,
                        "pred_field": pred_field,
                        "euclidean_path": eu_result.path,
                        "ours_path": ours_result.path,
                        "euclidean_expanded": eu_result.expanded_xy,
                        "ours_expanded": ours_result.expanded_xy,
                    },
                }

    summary = _summarize_rows(rows)

    csv_path = out_dir / f"{tag}_cases.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))

    summary_path = out_dir / f"{tag}_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary, rows, best_type_c
