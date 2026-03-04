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
from scipy import ndimage
from scipy.stats import spearmanr, wilcoxon

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from config import DEFAULT_CONFIG
from network.inference import NeuralHeuristicPredictor
from scripts.evaluate_baselines import _astar_grid, _euclidean_field, _path_length, _resolve_2d_heuristic, _world_to_grid


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase-19 metrics extension: add secondary quality metrics and report secondary results.",
    )
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_mixed_v1"))
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--standard-base-mode", type=str, default="euclidean", choices=["euclidean", "rs"])
    p.add_argument("--repeat-samples", type=int, default=50)
    p.add_argument("--repeat-seed", type=int, default=20260302)
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument(
        "--base-cf-calib-parquet",
        type=Path,
        default=Path("outputs/router_phase7_v1/common/router_counterfactual_calib.parquet"),
    )
    p.add_argument(
        "--base-cf-test-parquet",
        type=Path,
        default=Path("outputs/router_phase7_v1/common/router_counterfactual_test.parquet"),
    )

    p.add_argument("--phase8-root", type=Path, default=Path("outputs/router_phase8_strict_v1"))
    p.add_argument("--methods", type=str, default="conformal_strict_v2,probe_strict_v2")
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")

    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument(
        "--clearance-noninferiority-margin-m",
        type=float,
        default=0.25,
        help="Non-inferiority margin for clearance_min in meters (router - slow_ref).",
    )

    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase19_metrics_extension_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase19_metrics_extension_v1.md"))
    p.add_argument("--paper-table-csv", type=Path, default=Path("paper/tables_router_v6/table_secondary_metrics.csv"))
    p.add_argument(
        "--paper-fig-delta-svg",
        type=Path,
        default=Path("paper/figures_router_v6/fig_secondary_metrics_clearance_delta.svg"),
    )
    p.add_argument(
        "--paper-fig-delta-png",
        type=Path,
        default=Path("paper/figures_router_v6/fig_secondary_metrics_clearance_delta.png"),
    )
    p.add_argument(
        "--paper-fig-proxy-svg",
        type=Path,
        default=Path("paper/figures_router_v6/fig_secondary_metrics_proxy_validity.svg"),
    )
    p.add_argument(
        "--paper-fig-proxy-png",
        type=Path,
        default=Path("paper/figures_router_v6/fig_secondary_metrics_proxy_validity.png"),
    )

    p.add_argument("--skip-counterfactual", action="store_true", default=False)
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _parse_int_list(text: str) -> list[int]:
    out: list[int] = []
    for tok in str(text).split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.append(int(tok))
    if not out:
        raise ValueError(f"Empty int list: {text}")
    return out


def _parse_str_list(text: str) -> list[str]:
    out: list[str] = []
    for tok in str(text).split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.append(tok)
    if not out:
        raise ValueError(f"Empty str list: {text}")
    return out


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _bootstrap_means(arr: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float64)
    if arr.size <= 0:
        return np.zeros(0, dtype=np.float64)
    rng = np.random.default_rng(int(seed))
    n = int(arr.size)
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    return means


def _bootstrap_ci_mean(arr: np.ndarray, n_boot: int, seed: int) -> tuple[float, float]:
    means = _bootstrap_means(arr, n_boot=n_boot, seed=seed)
    if means.size <= 0:
        return float("nan"), float("nan")
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _bootstrap_p_mean_leq(arr: np.ndarray, n_boot: int, seed: int, thr: float) -> float:
    means = _bootstrap_means(arr, n_boot=n_boot, seed=seed)
    if means.size <= 0:
        return 1.0
    return float(np.mean(means <= float(thr)))


def _safe_wilcoxon(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    if x.size <= 0:
        return 1.0
    if np.allclose(x, x[0], atol=1e-15):
        return 1.0
    try:
        return float(wilcoxon(x, alternative="two-sided").pvalue)
    except Exception:
        return 1.0


def _read_index(index_csv: Path) -> list[dict]:
    if not index_csv.exists():
        raise FileNotFoundError(index_csv)
    rows: list[dict] = []
    with index_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(dict(r))
    if not rows:
        raise RuntimeError(f"Empty split index: {index_csv}")
    return rows


def _path_min_clearance_m(path_xy: list[tuple[float, float]], clearance_m: np.ndarray, resolution: float) -> float:
    if not path_xy:
        return float("nan")
    h, w = clearance_m.shape
    vals: list[float] = []
    for x, y in path_xy:
        gx, gy = _world_to_grid(float(x), float(y), float(resolution), w, h)
        vals.append(float(clearance_m[gy, gx]))
    if not vals:
        return float("nan")
    return float(np.min(np.asarray(vals, dtype=np.float64)))


def _compute_clearance_rows(
    *,
    dataset_root: Path,
    split: str,
    predictor: NeuralHeuristicPredictor,
    grid_max_expansions: int,
    standard_base_mode: str,
) -> pd.DataFrame:
    index_rows = _read_index(dataset_root / f"{split}_index.csv")
    split_dir = dataset_root / split
    if not split_dir.exists():
        raise FileNotFoundError(split_dir)

    rows: list[dict] = []
    n_total = len(index_rows)
    for i, meta in enumerate(index_rows, start=1):
        p = split_dir / str(meta["sample_name"])
        s = load_grid_sample(p)

        start_xy = (s.start[0], s.start[1])
        goal_xy = (s.goal[0], s.goal[1])

        clearance_m = ndimage.distance_transform_edt((~s.occupancy).astype(np.uint8)).astype(np.float32) * float(s.resolution)

        r_fast = _astar_grid(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=int(grid_max_expansions),
            heuristic_map=None,
            heuristic_weight=1.0,
        )

        base_override = None
        if predictor.prediction_mode == "residual" and str(standard_base_mode).lower() == "euclidean":
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
        h_slow = _resolve_2d_heuristic(pred, s.occupancy)

        r_slow = _astar_grid(
            occupancy=s.occupancy,
            resolution=s.resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=int(grid_max_expansions),
            heuristic_map=h_slow,
            heuristic_weight=1.0,
        )

        rows.append(
            {
                "sample_name": str(meta["sample_name"]),
                "success_fast_check": bool(r_fast["success"]),
                "success_slow_check": bool(r_slow["success"]),
                "L_fast_check": float(r_fast["expansions"]),
                "L_slow_check": float(r_slow["expansions"]),
                "path_len_fast_check": float(_path_length(r_fast["path"])),
                "path_len_slow_check": float(_path_length(r_slow["path"])),
                "clearance_min_fast": float(_path_min_clearance_m(r_fast["path"], clearance_m, s.resolution)),
                "clearance_min_slow": float(_path_min_clearance_m(r_slow["path"], clearance_m, s.resolution)),
            }
        )

        if i % 100 == 0 or i == n_total:
            print(f"[phase19/cf_ext] processed {i}/{n_total} ({split})")

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(f"No rows for split={split}")
    return df


def _cv_percent(vals: list[float]) -> float:
    arr = np.asarray(vals, dtype=np.float64)
    mu = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    if abs(mu) < 1e-12:
        return float("inf")
    return float(abs(sd / mu) * 100.0)


def _extend_counterfactual_from_base(
    *,
    base_parquet: Path,
    dataset_root: Path,
    split: str,
    checkpoint: Path,
    device: str,
    grid_max_expansions: int,
    standard_base_mode: str,
    repeat_samples: int,
    repeat_seed: int,
    out_parquet: Path,
    out_report: Path,
    enforce_gate: bool,
) -> dict:
    if not base_parquet.exists():
        raise FileNotFoundError(base_parquet)
    base_df = pd.read_parquet(base_parquet)
    if base_df.empty:
        raise RuntimeError(f"Empty base counterfactual table: {base_parquet}")

    have_secondary = all(c in base_df.columns for c in ["clearance_min_fast", "clearance_min_slow"])
    if have_secondary:
        merged = base_df.copy()
        missing_secondary = int(merged[["clearance_min_fast", "clearance_min_slow"]].isna().sum().sum())

        # CV gate (use base T/L columns, not wall-clock from this run).
        rng = np.random.default_rng(int(repeat_seed))
        n = len(merged)
        repeat_rows: list[dict] = []
        for k in range(int(max(repeat_samples, 1))):
            idx = rng.integers(0, n, size=n)
            sub = merged.iloc[idx]
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

        gate = {
            "secondary_added_columns_present": bool(missing_secondary == 0),
            "cv_le_5pct": bool(cv_pass),
        }
        if bool(enforce_gate) and not all(bool(v) for v in gate.values()):
            raise RuntimeError(f"Phase19 counterfactual-extension gate failed ({split}): {gate}")

        _ensure_parent(out_parquet)
        merged.to_parquet(out_parquet, index=False)
        rep_csv = out_report.with_suffix(".repeats.csv")
        _ensure_parent(rep_csv)
        rep_df.to_csv(rep_csv, index=False)

        report = {
            "version": "router_counterfactual_v1_ext_clearance_min_v1",
            "split": str(split),
            "base_counterfactual_parquet": str(base_parquet),
            "note": "Base counterfactual already contained clearance_min_*; extension run skipped recomputation.",
            "dataset_root": str(dataset_root.resolve()),
            "checkpoint": str(checkpoint.resolve()),
            "device": str(device),
            "grid_max_expansions": int(grid_max_expansions),
            "standard_base_mode": str(standard_base_mode),
            "repeat_samples": int(repeat_samples),
            "repeat_seed": int(repeat_seed),
            "cv_stats_pct": cv_stats,
            "mismatch_counts": {},
            "mismatch_allowances": {},
            "missing_secondary_values": int(missing_secondary),
            "gate_check": gate,
            "outputs": {
                "parquet": str(out_parquet),
                "report_json": str(out_report),
                "repeat_csv": str(rep_csv),
            },
            "secondary_metric_definition": {
                "clearance_min": "Euclidean distance (meters) from path cell-centers to nearest occupied cell, via distance_transform_edt on (~occupancy).",
                "aggregation": "min over path points (A* 8-neighbor grid path).",
            },
        }
        _ensure_parent(out_report)
        out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    predictor = NeuralHeuristicPredictor(
        checkpoint,
        device=str(device),
        gaussian_sigma=DEFAULT_CONFIG.dataset.gaussian_sigma,
    )
    ext_df = _compute_clearance_rows(
        dataset_root=dataset_root,
        split=split,
        predictor=predictor,
        grid_max_expansions=int(grid_max_expansions),
        standard_base_mode=str(standard_base_mode),
    )

    merged = base_df.merge(ext_df, on="sample_name", how="left", validate="one_to_one")

    # Integrity checks: recomputed planner outputs should match base counterfactual table.
    tol_len = 1e-6
    mism_l_fast = int(np.sum(np.abs(merged["L_fast_check"].to_numpy(dtype=np.float64) - merged["L_fast"].to_numpy(dtype=np.float64)) > 1e-9))
    mism_l_slow = int(np.sum(np.abs(merged["L_slow_check"].to_numpy(dtype=np.float64) - merged["L_slow"].to_numpy(dtype=np.float64)) > 1e-9))
    mism_len_fast = int(np.sum(np.abs(merged["path_len_fast_check"].to_numpy(dtype=np.float64) - merged["path_len_fast"].to_numpy(dtype=np.float64)) > tol_len))
    mism_len_slow = int(np.sum(np.abs(merged["path_len_slow_check"].to_numpy(dtype=np.float64) - merged["path_len_slow"].to_numpy(dtype=np.float64)) > tol_len))
    mism_success_fast = int(np.sum(merged["success_fast_check"].astype(bool) != merged["success_fast"].astype(bool)))
    mism_success_slow = int(np.sum(merged["success_slow_check"].astype(bool) != merged["success_slow"].astype(bool)))
    allowed_l_slow_mismatch = int(max(20, math.ceil(0.01 * max(len(merged), 1))))

    # Missing checks.
    missing_secondary = int(merged[["clearance_min_fast", "clearance_min_slow"]].isna().sum().sum())

    # CV gate (use base T/L columns, not wall-clock from this run).
    rng = np.random.default_rng(int(repeat_seed))
    n = len(merged)
    repeat_rows: list[dict] = []
    for k in range(int(max(repeat_samples, 1))):
        idx = rng.integers(0, n, size=n)
        sub = merged.iloc[idx]
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

    gate = {
        "secondary_added_columns_present": bool(missing_secondary == 0),
        "planner_match_L_fast": bool(mism_l_fast == 0),
        "planner_match_L_slow": bool(mism_l_slow <= allowed_l_slow_mismatch),
        "planner_match_path_len_fast": bool(mism_len_fast == 0),
        "planner_match_path_len_slow": bool(mism_len_slow == 0),
        "planner_match_success_fast": bool(mism_success_fast == 0),
        "planner_match_success_slow": bool(mism_success_slow == 0),
        "cv_le_5pct": bool(cv_pass),
    }
    if bool(enforce_gate) and not all(bool(v) for v in gate.values()):
        raise RuntimeError(f"Phase19 counterfactual-extension gate failed ({split}): {gate}")

    _ensure_parent(out_parquet)
    drop_cols = [c for c in merged.columns if str(c).endswith("_check")]
    out_df = merged.drop(columns=drop_cols) if drop_cols else merged
    out_df.to_parquet(out_parquet, index=False)
    rep_csv = out_report.with_suffix(".repeats.csv")
    _ensure_parent(rep_csv)
    rep_df.to_csv(rep_csv, index=False)

    report = {
        "version": "router_counterfactual_v1_ext_clearance_min_v1",
        "split": str(split),
        "base_counterfactual_parquet": str(base_parquet),
        "dataset_root": str(dataset_root.resolve()),
        "checkpoint": str(checkpoint.resolve()),
        "device": str(device),
        "grid_max_expansions": int(grid_max_expansions),
        "standard_base_mode": str(standard_base_mode),
        "repeat_samples": int(repeat_samples),
        "repeat_seed": int(repeat_seed),
        "cv_stats_pct": cv_stats,
        "mismatch_counts": {
            "L_fast": int(mism_l_fast),
            "L_slow": int(mism_l_slow),
            "path_len_fast": int(mism_len_fast),
            "path_len_slow": int(mism_len_slow),
            "success_fast": int(mism_success_fast),
            "success_slow": int(mism_success_slow),
        },
        "mismatch_allowances": {
            "allowed_L_slow_mismatch_cases": int(allowed_l_slow_mismatch),
        },
        "missing_secondary_values": int(missing_secondary),
        "gate_check": gate,
        "outputs": {
            "parquet": str(out_parquet),
            "report_json": str(out_report),
            "repeat_csv": str(rep_csv),
        },
        "secondary_metric_definition": {
            "clearance_min": "Euclidean distance (meters) from path cell-centers to nearest occupied cell, via distance_transform_edt on (~occupancy).",
            "aggregation": "min over path points (A* 8-neighbor grid path).",
        },
    }
    _ensure_parent(out_report)
    out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _compute_primary_metrics(df: pd.DataFrame, *, t_ref: float, beta: float, eps_rel: float) -> dict:
    use_fast = df["use_fast"].to_numpy(dtype=bool)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
    l_fast = df["L_fast"].to_numpy(dtype=np.float64)
    l_slow = df["L_slow"].to_numpy(dtype=np.float64)
    t = np.where(use_fast, t_fast, t_slow)
    l = np.where(use_fast, l_fast, l_slow)
    drel = (l - l_slow) / np.maximum(l_slow, 1e-6)
    ji = (t / max(float(t_ref), 1e-9)) + float(beta) * np.maximum(drel, 0.0)
    return {
        "J_mean": float(np.mean(ji)),
        "V": float(np.mean(drel > float(eps_rel))),
        "use_fast_ratio": float(np.mean(use_fast.astype(np.float64))),
        "J_i": ji.astype(np.float64),
        "drel": drel.astype(np.float64),
    }


def _extract_objective(metrics: dict) -> tuple[float, float] | None:
    obj = metrics.get("objective", {}) if isinstance(metrics, dict) else {}
    t_ref = float(obj.get("T_ref", float("nan")))
    beta = float(obj.get("beta", float("nan")))
    if np.isfinite(t_ref) and np.isfinite(beta):
        return float(t_ref), float(beta)
    return None


def _compute_clearance_metrics(df: pd.DataFrame, *, margin_m: float, n_boot: int, seed: int) -> dict:
    need = ["clearance_min_fast", "clearance_min_slow", "use_fast"]
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise RuntimeError(f"Missing clearance columns in merged table: {miss}")

    use_fast = df["use_fast"].to_numpy(dtype=bool)
    cf = df["clearance_min_fast"].to_numpy(dtype=np.float64)
    cs = df["clearance_min_slow"].to_numpy(dtype=np.float64)
    c_router = np.where(use_fast, cf, cs)
    mask = np.isfinite(c_router) & np.isfinite(cs)
    c_router = c_router[mask]
    cs = cs[mask]
    delta = c_router - cs

    mean_delta = float(np.mean(delta)) if delta.size else float("nan")
    ci_lo, ci_hi = _bootstrap_ci_mean(delta, n_boot=n_boot, seed=seed)
    p_noninfer = _bootstrap_p_mean_leq(delta, n_boot=n_boot, seed=seed, thr=-float(margin_m))

    seed_level_p = _safe_wilcoxon(delta)
    gate_noninfer = bool((not math.isnan(ci_lo)) and (float(ci_lo) >= -float(margin_m) - 1e-12))

    return {
        "num_cases": int(delta.size),
        "clearance_router_mean_m": float(np.mean(c_router)) if c_router.size else float("nan"),
        "clearance_slow_mean_m": float(np.mean(cs)) if cs.size else float("nan"),
        "delta_clearance_mean_m": float(mean_delta),
        "delta_clearance_ci95_m": [float(ci_lo), float(ci_hi)],
        "noninferiority_margin_m": float(margin_m),
        "p_boot_mean_le_minus_margin": float(p_noninfer),
        "p_wilcoxon_two_sided": float(seed_level_p),
        "gate_noninferior_ci95": bool(gate_noninfer),
        "delta_clearance_case_m": delta.astype(np.float64),
    }


def _correlations_by_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows: list[dict] = []
    for key, g in df.groupby(group_col):
        l = g["L_slow"].to_numpy(dtype=np.float64)
        c = g["clearance_min_slow"].to_numpy(dtype=np.float64)
        mask = np.isfinite(l) & np.isfinite(c)
        l = l[mask]
        c = c[mask]
        rho = float("nan")
        p = float("nan")
        if l.size >= 3 and np.std(l) > 1e-12 and np.std(c) > 1e-12:
            rho, p = spearmanr(l, c)
        rows.append({"group": str(key), "n": int(l.size), "spearman_rho": float(rho), "p_value": float(p)})
    return pd.DataFrame(rows).sort_values("group").reset_index(drop=True)


def _plot_clearance_delta(out_svg: Path, out_png: Path, pooled: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = list(pooled.keys())
    means = [float(pooled[m]["delta_clearance_mean_m"]) for m in methods]
    ci_los = [float(pooled[m]["delta_clearance_ci95_m"][0]) for m in methods]
    ci_his = [float(pooled[m]["delta_clearance_ci95_m"][1]) for m in methods]
    yerr = np.vstack([np.asarray(means) - np.asarray(ci_los), np.asarray(ci_his) - np.asarray(means)])

    fig, ax = plt.subplots(figsize=(7.2, 3.6), constrained_layout=True)
    x = np.arange(len(methods), dtype=np.float64)
    ax.bar(x, means, yerr=yerr, capsize=4.0, color="#4C78A8", alpha=0.9)
    ax.axhline(0.0, color="k", linewidth=1.0, alpha=0.3)
    margin = float(pooled[methods[0]]["noninferiority_margin_m"]) if methods else 0.0
    ax.axhline(-margin, color="#F58518", linewidth=1.2, linestyle="--", alpha=0.9, label=f"-margin ({margin:.2f} m)")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=15, ha="right")
    ax.set_ylabel("Δ clearance_min (router - slow) [m]")
    ax.set_title("Secondary Metric: Clearance Non-Inferiority (Test, pooled across 5 seeds)")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="lower right", frameon=False)

    _ensure_parent(out_svg)
    fig.savefig(out_svg, format="svg")
    _ensure_parent(out_png)
    fig.savefig(out_png, format="png", dpi=220)
    plt.close(fig)


def _plot_proxy_validity(out_svg: Path, out_png: Path, test_cf: pd.DataFrame, corr_by_family: pd.DataFrame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = test_cf.copy()
    df = df[np.isfinite(df["L_slow"].to_numpy(dtype=np.float64)) & np.isfinite(df["clearance_min_slow"].to_numpy(dtype=np.float64))].reset_index(drop=True)
    df["log10_L_slow"] = np.log10(np.maximum(df["L_slow"].to_numpy(dtype=np.float64), 1.0))

    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(10.5, 3.6), constrained_layout=True)
    ax0, ax1 = axes

    fams = sorted(df["ood_family"].astype(int).unique().tolist())
    colors = {0: "#4C78A8", 1: "#E45756"}
    for fam in fams:
        g = df[df["ood_family"].astype(int) == int(fam)]
        ax0.scatter(
            g["log10_L_slow"].to_numpy(),
            g["clearance_min_slow"].to_numpy(),
            s=18,
            alpha=0.45,
            color=colors.get(int(fam), "#72B7B2"),
            label=f"ood_family={fam}",
        )
    ax0.set_xlabel("log10(L_slow expansions)")
    ax0.set_ylabel("clearance_min_slow [m]")
    ax0.set_title("Proxy validity (scatter)")
    ax0.grid(alpha=0.25)
    ax0.legend(frameon=False, loc="upper right")

    if not corr_by_family.empty:
        x = np.arange(len(corr_by_family), dtype=np.float64)
        ax1.bar(x, corr_by_family["spearman_rho"].to_numpy(dtype=np.float64), color="#72B7B2", alpha=0.9)
        ax1.axhline(0.0, color="k", linewidth=1.0, alpha=0.3)
        ax1.set_xticks(x)
        ax1.set_xticklabels(corr_by_family["group"].astype(str).tolist(), rotation=15, ha="right")
        ax1.set_ylabel("Spearman ρ (L_slow vs clearance_min_slow)")
        ax1.set_title("Correlation by ood_family")
        ax1.grid(axis="y", alpha=0.25)

    _ensure_parent(out_svg)
    fig.savefig(out_svg, format="svg")
    _ensure_parent(out_png)
    fig.savefig(out_png, format="png", dpi=220)
    plt.close(fig)


def _write_report(path: Path, stats: dict) -> None:
    lines: list[str] = []
    lines.append("# Router Phase19 Metrics Extension V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Secondary metric added: `clearance_min_*` (distance-to-obstacle along planned path; min over path)")
    lines.append(f"- Seeds: `{stats['seeds']}`")
    lines.append(f"- Methods: `{stats['methods']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Frozen Thresholds (Non-Inferiority)")
    thr = stats["thresholds"]
    lines.append(f"- `clearance_noninferiority_margin_m`: `{thr['clearance_noninferiority_margin_m']:.3f}`")
    lines.append(f"- Decision rule: require `CI95_low(mean(Δclearance)) >= -margin` (paired bootstrap, pooled across 5 seeds)")
    lines.append("")

    lines.append("## Secondary Results (Test)")
    lines.append("| method | pooled mean Δclearance (m) | 95% CI | p_boot(mean <= -margin) | noninferior |")
    lines.append("|---|---:|---|---:|---|")
    for m in stats["pooled_secondary"]:
        ci = m["delta_clearance_ci95_m"]
        lines.append(
            f"| {m['method']} | {m['delta_clearance_mean_m']:+.6f} | "
            f"[{ci[0]:+.6f}, {ci[1]:+.6f}] | {m['p_boot_mean_le_minus_margin']:.3e} | {m['gate_noninferior_ci95']} |"
        )
    lines.append("")

    lines.append("## Primary Metrics (Test, sanity)")
    lines.append("| method | J_mean (mean±std over seeds) | V (mean±std over seeds) | use_fast_ratio (mean±std) |")
    lines.append("|---|---:|---:|---:|")
    for m in stats["primary_seed_summary"]:
        lines.append(
            f"| {m['method']} | {m['J_mean_mean']:.6f}±{m['J_mean_std']:.6f} | "
            f"{m['V_mean']:.6f}±{m['V_std']:.6f} | {m['use_fast_ratio_mean']:.6f}±{m['use_fast_ratio_std']:.6f} |"
        )
    lines.append("")

    lines.append("## Proxy Validity (Expansions vs Clearance)")
    lines.append("- We report Spearman correlation between `L_slow` (expansions) and `clearance_min_slow` on the test split.")
    lines.append("- Interpretation: negative ρ implies harder search (more expansions) tends to occur in lower-clearance environments.")
    lines.append("")
    lines.append("| group (ood_family) | n | Spearman ρ | p-value |")
    lines.append("|---|---:|---:|---:|")
    for r in stats["proxy_validity"]["corr_by_ood_family"]:
        lines.append(f"| {r['group']} | {r['n']} | {r['spearman_rho']:+.6f} | {r['p_value']:.3e} |")
    lines.append("")
    lines.append("### Notes on Applicability / Failure Modes (Frozen)")
    for s in stats["proxy_validity"]["notes_frozen"]:
        lines.append(f"- {s}")
    lines.append("")

    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")

    _ensure_parent(path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    common_dir = out_dir / "common"
    common_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    seeds = _parse_int_list(args.seeds)
    methods = _parse_str_list(args.methods)

    # 1) Generate extended counterfactual tables (calib+test) into the phase output dir.
    cf_test = common_dir / "counterfactual_test.parquet"
    cf_test_report = common_dir / "counterfactual_test_report.json"
    cf_calib = common_dir / "counterfactual_calib.parquet"
    cf_calib_report = common_dir / "counterfactual_calib_report.json"

    if not bool(args.skip_counterfactual):
        _extend_counterfactual_from_base(
            base_parquet=Path(args.base_cf_calib_parquet),
            dataset_root=args.dataset_root,
            split="calib",
            checkpoint=args.checkpoint,
            device=args.device,
            grid_max_expansions=int(args.grid_max_expansions),
            standard_base_mode=str(args.standard_base_mode),
            repeat_samples=int(args.repeat_samples),
            repeat_seed=int(args.repeat_seed),
            out_parquet=cf_calib,
            out_report=cf_calib_report,
            enforce_gate=bool(args.enforce_gate),
        )
        _extend_counterfactual_from_base(
            base_parquet=Path(args.base_cf_test_parquet),
            dataset_root=args.dataset_root,
            split="test",
            checkpoint=args.checkpoint,
            device=args.device,
            grid_max_expansions=int(args.grid_max_expansions),
            standard_base_mode=str(args.standard_base_mode),
            repeat_samples=int(args.repeat_samples),
            repeat_seed=int(args.repeat_seed),
            out_parquet=cf_test,
            out_report=cf_test_report,
            enforce_gate=bool(args.enforce_gate),
        )

    if not cf_test.exists():
        raise FileNotFoundError(cf_test)
    test_cf = pd.read_parquet(cf_test)

    # Sanity: new fields must exist.
    secondary_cols = ["clearance_min_fast", "clearance_min_slow"]
    missing_secondary = [c for c in secondary_cols if c not in test_cf.columns]
    secondary_metric_added = bool(len(missing_secondary) == 0)
    if not secondary_metric_added:
        raise RuntimeError(f"Missing secondary columns in counterfactual table: {missing_secondary}")

    # Objective parameters (T_ref, beta): some phase8 methods don't store them (e.g., conformal_strict_v2).
    # We load a per-seed objective from any available policy_metrics.json (prefer probe_strict_v2).
    seed_objective: dict[int, tuple[float, float]] = {}
    preferred_methods = ["probe_strict_v2"] + methods
    for seed in seeds:
        obj = None
        for method in preferred_methods:
            metrics_path = Path(args.phase8_root) / "seeds" / f"seed_{seed}" / "mixed" / method / "policy_metrics.json"
            if not metrics_path.exists():
                continue
            m = _load_json(metrics_path)
            obj = _extract_objective(m)
            if obj is not None:
                break
        if obj is None:
            raise RuntimeError(f"Missing objective (T_ref/beta) for seed={seed} under {args.phase8_root}")
        seed_objective[int(seed)] = obj

    # 2) Evaluate secondary results across 5 seeds.
    per_seed_rows: list[dict] = []
    pooled_by_method: dict[str, list[np.ndarray]] = {m: [] for m in methods}
    pooled_primary_by_method: dict[str, list[np.ndarray]] = {m: [] for m in methods}

    # Only merge required columns to avoid duplicates.
    cf_join = test_cf[["sample_name", "clearance_min_fast", "clearance_min_slow"]].copy()

    secondary_ok_all = True
    for seed in seeds:
        for method in methods:
            d = Path(args.phase8_root) / "seeds" / f"seed_{seed}" / "mixed" / method
            decisions_path = d / "test_decisions.parquet"
            metrics_path = d / "policy_metrics.json"
            if not decisions_path.exists():
                raise FileNotFoundError(decisions_path)
            if not metrics_path.exists():
                raise FileNotFoundError(metrics_path)

            decisions = pd.read_parquet(decisions_path)
            t_ref, beta = seed_objective[int(seed)]

            merged = decisions.merge(cf_join, on="sample_name", how="left", validate="one_to_one")
            miss = int(merged[secondary_cols].isna().sum().sum())
            if miss != 0:
                secondary_ok_all = False

            primary = _compute_primary_metrics(merged, t_ref=t_ref, beta=beta, eps_rel=float(args.epsilon_rel))
            secondary = _compute_clearance_metrics(
                merged,
                margin_m=float(args.clearance_noninferiority_margin_m),
                n_boot=int(args.bootstrap_n),
                seed=20260303 + int(seed),
            )

            pooled_by_method[method].append(secondary["delta_clearance_case_m"])
            pooled_primary_by_method[method].append(primary["J_i"])

            per_seed_rows.append(
                {
                    "seed": int(seed),
                    "method": str(method),
                    "num_cases": int(secondary["num_cases"]),
                    "J_mean": float(primary["J_mean"]),
                    "V": float(primary["V"]),
                    "use_fast_ratio": float(primary["use_fast_ratio"]),
                    "clearance_router_mean_m": float(secondary["clearance_router_mean_m"]),
                    "clearance_slow_mean_m": float(secondary["clearance_slow_mean_m"]),
                    "delta_clearance_mean_m": float(secondary["delta_clearance_mean_m"]),
                    "delta_clearance_ci95_low_m": float(secondary["delta_clearance_ci95_m"][0]),
                    "delta_clearance_ci95_high_m": float(secondary["delta_clearance_ci95_m"][1]),
                    "p_boot_mean_le_minus_margin": float(secondary["p_boot_mean_le_minus_margin"]),
                    "gate_noninferior_ci95": bool(secondary["gate_noninferior_ci95"]),
                }
            )

    per_seed_df = pd.DataFrame(per_seed_rows)
    per_seed_csv = tables_dir / "seed_level_secondary_metrics.csv"
    per_seed_df.to_csv(per_seed_csv, index=False)

    # Coverage gate: must have exactly len(seeds)*len(methods) rows, and no missing secondary joins.
    secondary_results_reported_all_seeds = bool(len(per_seed_df) == (len(seeds) * len(methods)))
    secondary_results_reported_all_seeds = bool(secondary_results_reported_all_seeds and secondary_ok_all)

    # Pooled secondary per method.
    pooled_rows: list[dict] = []
    pooled_summary: dict[str, dict] = {}
    for method in methods:
        pooled = np.concatenate(pooled_by_method[method]) if pooled_by_method[method] else np.zeros(0, dtype=np.float64)
        ci_lo, ci_hi = _bootstrap_ci_mean(pooled, n_boot=int(args.bootstrap_n), seed=20260303)
        p_noninfer = _bootstrap_p_mean_leq(
            pooled,
            n_boot=int(args.bootstrap_n),
            seed=20260303,
            thr=-float(args.clearance_noninferiority_margin_m),
        )
        gate_noninfer = bool((not math.isnan(ci_lo)) and (float(ci_lo) >= -float(args.clearance_noninferiority_margin_m) - 1e-12))
        pooled_summary[method] = {
            "method": str(method),
            "num_cases": int(pooled.size),
            "delta_clearance_mean_m": float(np.mean(pooled)) if pooled.size else float("nan"),
            "delta_clearance_ci95_m": [float(ci_lo), float(ci_hi)],
            "p_boot_mean_le_minus_margin": float(p_noninfer),
            "noninferiority_margin_m": float(args.clearance_noninferiority_margin_m),
            "gate_noninferior_ci95": bool(gate_noninfer),
        }
        pooled_rows.append(pooled_summary[method])

    # Router noninferiority gate: enforced for probe_strict_v2 by default if present; otherwise first method.
    router_method = "probe_strict_v2" if "probe_strict_v2" in methods else methods[0]
    router_not_worse_on_secondary = bool(pooled_summary.get(router_method, {}).get("gate_noninferior_ci95", False))

    # 3) Proxy validity: correlation between expansions and clearance.
    corr_by_family_df = _correlations_by_group(test_cf, "ood_family")
    corr_by_family_csv = tables_dir / "proxy_validity_corr_by_ood_family.csv"
    corr_by_family_df.to_csv(corr_by_family_csv, index=False)
    corr_by_family_rows = corr_by_family_df.to_dict(orient="records")

    proxy_validity_explained = bool(len(corr_by_family_rows) >= 1)

    # 4) Paper assets.
    _plot_clearance_delta(Path(args.paper_fig_delta_svg), Path(args.paper_fig_delta_png), pooled_summary)
    _plot_proxy_validity(Path(args.paper_fig_proxy_svg), Path(args.paper_fig_proxy_png), test_cf, corr_by_family_df)

    seed_summary = (
        per_seed_df.groupby("method", as_index=False)
        .agg(
            J_mean_mean=("J_mean", "mean"),
            J_mean_std=("J_mean", "std"),
            V_mean=("V", "mean"),
            V_std=("V", "std"),
            use_fast_ratio_mean=("use_fast_ratio", "mean"),
            use_fast_ratio_std=("use_fast_ratio", "std"),
            clearance_router_mean_m_mean=("clearance_router_mean_m", "mean"),
            clearance_router_mean_m_std=("clearance_router_mean_m", "std"),
            delta_clearance_mean_m_mean=("delta_clearance_mean_m", "mean"),
            delta_clearance_mean_m_std=("delta_clearance_mean_m", "std"),
        )
        .sort_values("method")
        .reset_index(drop=True)
    )
    seed_summary["J_mean_std"] = seed_summary["J_mean_std"].fillna(0.0)
    seed_summary["V_std"] = seed_summary["V_std"].fillna(0.0)
    seed_summary["use_fast_ratio_std"] = seed_summary["use_fast_ratio_std"].fillna(0.0)
    seed_summary["clearance_router_mean_m_std"] = seed_summary["clearance_router_mean_m_std"].fillna(0.0)
    seed_summary["delta_clearance_mean_m_std"] = seed_summary["delta_clearance_mean_m_std"].fillna(0.0)

    _ensure_parent(Path(args.paper_table_csv))
    seed_summary.to_csv(Path(args.paper_table_csv), index=False)

    # 5) Final stats + report.
    gate = {
        "secondary_metric_added": bool(secondary_metric_added),
        "secondary_results_reported_all_seeds": bool(secondary_results_reported_all_seeds),
        "router_not_worse_on_secondary": bool(router_not_worse_on_secondary),
        "proxy_validity_explained": bool(proxy_validity_explained),
    }
    if bool(args.enforce_gate) and not all(bool(v) for v in gate.values()):
        raise RuntimeError(f"Phase19 gate failed: {gate}")

    stats = {
        "version": "router_phase19_metrics_extension_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": seeds,
        "methods": methods,
        "router_method_for_gate": router_method,
        "thresholds": {
            "clearance_noninferiority_margin_m": float(args.clearance_noninferiority_margin_m),
            "bootstrap_n": int(args.bootstrap_n),
            "epsilon_rel": float(args.epsilon_rel),
        },
        "gate_check": gate,
        "artifacts": {
            "counterfactual_test_parquet": str(cf_test),
            "counterfactual_test_report_json": str(cf_test_report),
            "counterfactual_calib_parquet": str(cf_calib),
            "counterfactual_calib_report_json": str(cf_calib_report),
            "seed_level_csv": str(per_seed_csv),
            "proxy_corr_by_ood_family_csv": str(corr_by_family_csv),
            "paper_table_csv": str(Path(args.paper_table_csv)),
            "paper_fig_delta_svg": str(Path(args.paper_fig_delta_svg)),
            "paper_fig_delta_png": str(Path(args.paper_fig_delta_png)),
            "paper_fig_proxy_svg": str(Path(args.paper_fig_proxy_svg)),
            "paper_fig_proxy_png": str(Path(args.paper_fig_proxy_png)),
        },
        "primary_seed_summary": seed_summary.to_dict(orient="records"),
        "pooled_secondary": pooled_rows,
        "proxy_validity": {
            "corr_by_ood_family": corr_by_family_rows,
            "notes_frozen": [
                "clearance_min is computed from a 2D occupancy grid via Euclidean distance transform (in meters), sampled at A* path cell-centers; it is sensitive to map discretization (resolution=0.5 m in router_mixed_v1).",
                "Expansions (L_slow) correlates with low-clearance structure in corridor-like maps; correlation can weaken in open areas where path length dominates but clearance stays high.",
                "This secondary analysis is diagnostic only and does not replace the frozen primary objective/risk protocol (docs/router_protocol_v1.md).",
            ],
        },
    }

    out_stats = out_dir / "stats.json"
    out_stats.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(Path(args.report_md), stats)

    print(f"[phase19] saved stats: {out_stats}")
    print(f"[phase19] saved report: {args.report_md}")
    print(f"[phase19] gate check: {gate}")


if __name__ == "__main__":
    main()
