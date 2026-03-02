from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from config import DEFAULT_CONFIG
from network.inference import NeuralHeuristicPredictor
from scripts.evaluate_baselines import _astar_grid, _euclidean_field, _path_length, _resolve_2d_heuristic


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate fast/slow counterfactual labels for router mixed benchmark.")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_mixed_v1"))
    p.add_argument("--split", type=str, default="test", choices=["train", "calib", "test"])
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--standard-base-mode", type=str, default="euclidean", choices=["euclidean", "rs"])
    p.add_argument("--repeat-samples", type=int, default=3)
    p.add_argument("--repeat-seed", type=int, default=20260302)
    p.add_argument("--enforce-gate", action="store_true", help="When enabled, strictly enforce phase-2 gate and fail on violation.")
    p.add_argument("--out-parquet", type=Path, default=Path("outputs/router_counterfactual_v1.parquet"))
    p.add_argument("--out-report", type=Path, default=Path("outputs/router_counterfactual_v1_report.json"))
    return p.parse_args()


def _read_index(index_csv: Path) -> list[dict]:
    if not index_csv.exists():
        raise FileNotFoundError(f"Missing split index: {index_csv}")
    rows: list[dict] = []
    with index_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(dict(r))
    if not rows:
        raise RuntimeError(f"Empty split index: {index_csv}")
    return rows


def _cv_percent(vals: list[float]) -> float:
    arr = np.asarray(vals, dtype=np.float64)
    mu = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    if abs(mu) < 1e-12:
        return float("inf")
    return float(abs(sd / mu) * 100.0)


def main() -> None:
    args = parse_args()
    out_parquet = args.out_parquet
    out_report = args.out_report
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    out_report.parent.mkdir(parents=True, exist_ok=True)

    index_rows = _read_index(args.dataset_root / f"{args.split}_index.csv")
    split_dir = args.dataset_root / args.split
    if not split_dir.exists():
        raise FileNotFoundError(f"Missing split directory: {split_dir}")

    predictor = NeuralHeuristicPredictor(
        args.checkpoint,
        device=args.device,
        gaussian_sigma=DEFAULT_CONFIG.dataset.gaussian_sigma,
    )

    rows: list[dict] = []
    n_total = len(index_rows)
    for i, meta in enumerate(index_rows, start=1):
        p = split_dir / meta["sample_name"]
        if not p.exists():
            raise FileNotFoundError(f"Missing sample link: {p}")
        s = load_grid_sample(p)

        start_xy = (s.start[0], s.start[1])
        goal_xy = (s.goal[0], s.goal[1])

        r_fast = _astar_grid(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=int(args.grid_max_expansions),
            heuristic_map=None,
            heuristic_weight=1.0,
        )

        t0 = time.perf_counter()
        base_override = None
        if predictor.prediction_mode == "residual" and str(args.standard_base_mode).lower() == "euclidean":
            base_override = _euclidean_field(
                occupancy=s.occupancy,
                goal_xy=goal_xy,
                resolution=s.resolution,
                fill_value=1e6,
            )
        pred = predictor.predict_field(
            occupancy=s.occupancy,
            esdf=np.zeros_like(s.occupancy, dtype=np.float32),
            start=s.start,
            goal=s.goal,
            resolution=s.resolution,
            base_field_override=base_override,
        )
        infer_slow_ms = float((time.perf_counter() - t0) * 1000.0)
        h_slow = _resolve_2d_heuristic(pred, s.occupancy)

        r_slow = _astar_grid(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=int(args.grid_max_expansions),
            heuristic_map=h_slow,
            heuristic_weight=1.0,
        )

        l_fast = float(r_fast["expansions"])
        l_slow = float(r_slow["expansions"])
        t_fast = float(r_fast["runtime_ms"])
        t_slow = float(r_slow["runtime_ms"] + infer_slow_ms)
        q = float(l_fast - l_slow)
        c = float(t_slow - t_fast)
        q_rel = float(q / max(l_slow, 1e-6))

        row = {
            "split": args.split,
            "case_id": str(meta["sample_name"]),
            "sample_name": str(meta["sample_name"]),
            "source_path": str(meta["source_path"]),
            "source_dataset": str(meta["source_dataset"]),
            "scenario": str(meta["scenario"]),
            "map_id": str(meta["map_id"]),
            "difficulty": str(meta["difficulty"]),
            "ood_family": int(meta["ood_family"]),
            "success_fast": bool(r_fast["success"]),
            "success_slow": bool(r_slow["success"]),
            "L_fast": l_fast,
            "L_slow": l_slow,
            "T_fast_ms": t_fast,
            "T_slow_ms": t_slow,
            "infer_slow_ms": infer_slow_ms,
            "search_fast_ms": float(r_fast["runtime_ms"]),
            "search_slow_ms": float(r_slow["runtime_ms"]),
            "path_len_fast": float(_path_length(r_fast["path"])),
            "path_len_slow": float(_path_length(r_slow["path"])),
            "q": q,
            "c": c,
            "q_rel": q_rel,
        }
        rows.append(row)

        if i % 100 == 0 or i == n_total:
            print(f"[counterfactual] processed {i}/{n_total}")

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No counterfactual rows generated.")

    # Phase-2 gate checks.
    expected = int(n_total)
    observed = int(len(df))
    coverage_ratio = float(observed / max(expected, 1))
    if bool(args.enforce_gate) and observed != expected:
        raise RuntimeError(f"Coverage gate failed: observed={observed}, expected={expected}")

    required_cols = [
        "split",
        "case_id",
        "source_dataset",
        "difficulty",
        "success_fast",
        "success_slow",
        "L_fast",
        "L_slow",
        "T_fast_ms",
        "T_slow_ms",
        "q",
        "c",
        "q_rel",
    ]
    missing_total = int(df[required_cols].isna().sum().sum())
    if bool(args.enforce_gate) and missing_total != 0:
        raise RuntimeError(f"Missing-value gate failed: {missing_total} missing values in required fields.")

    # Repeated sampling CV (3 repeats by default).
    rng = np.random.default_rng(int(args.repeat_seed))
    n = len(df)
    repeat_rows: list[dict] = []
    for k in range(int(args.repeat_samples)):
        idx = rng.integers(0, n, size=n)
        sub = df.iloc[idx]
        repeat_rows.append(
            {
                "repeat_id": k,
                "mean_L_fast": float(sub["L_fast"].mean()),
                "mean_L_slow": float(sub["L_slow"].mean()),
                "mean_T_fast_ms": float(sub["T_fast_ms"].mean()),
                "mean_T_slow_ms": float(sub["T_slow_ms"].mean()),
            }
        )
    rep_df = pd.DataFrame(repeat_rows)

    cv_stats = {
        "cv_mean_L_fast_pct": _cv_percent(rep_df["mean_L_fast"].tolist()),
        "cv_mean_L_slow_pct": _cv_percent(rep_df["mean_L_slow"].tolist()),
        "cv_mean_T_fast_ms_pct": _cv_percent(rep_df["mean_T_fast_ms"].tolist()),
        "cv_mean_T_slow_ms_pct": _cv_percent(rep_df["mean_T_slow_ms"].tolist()),
    }
    cv_pass = all(float(v) <= 5.0 for v in cv_stats.values())
    if bool(args.enforce_gate) and not cv_pass:
        raise RuntimeError(f"CV gate failed: {cv_stats}")

    df.to_parquet(out_parquet, index=False)
    rep_csv = out_report.with_suffix(".repeats.csv")
    rep_df.to_csv(rep_csv, index=False)

    report = {
        "version": "router_counterfactual_v1",
        "dataset_root": str(args.dataset_root.resolve()),
        "split": args.split,
        "checkpoint": str(args.checkpoint.resolve()),
        "device": args.device,
        "num_expected_cases": expected,
        "num_observed_cases": observed,
        "coverage_ratio": coverage_ratio,
        "missing_required_values": missing_total,
        "required_columns": required_cols,
        "repeat_samples": int(args.repeat_samples),
        "cv_stats_pct": cv_stats,
        "phase2_gate_check": {
            "coverage_100pct": bool(observed == expected),
            "missing_required_eq_0": bool(missing_total == 0),
            "cv_le_5pct": bool(cv_pass),
        },
        "aggregate_metrics": {
            "mean_L_fast": float(df["L_fast"].mean()),
            "mean_L_slow": float(df["L_slow"].mean()),
            "mean_T_fast_ms": float(df["T_fast_ms"].mean()),
            "mean_T_slow_ms": float(df["T_slow_ms"].mean()),
            "mean_q": float(df["q"].mean()),
            "mean_c_ms": float(df["c"].mean()),
            "mean_q_rel": float(df["q_rel"].mean()),
            "success_fast_rate": float(df["success_fast"].mean()),
            "success_slow_rate": float(df["success_slow"].mean()),
        },
        "outputs": {
            "parquet": str(out_parquet),
            "report_json": str(out_report),
            "repeat_csv": str(rep_csv),
        },
    }
    out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"[counterfactual] saved parquet: {out_parquet}")
    print(f"[counterfactual] saved report: {out_report}")
    print(f"[counterfactual] gate check: {report['phase2_gate_check']}")
    print(f"[counterfactual] cv_stats_pct: {cv_stats}")


if __name__ == "__main__":
    main()
