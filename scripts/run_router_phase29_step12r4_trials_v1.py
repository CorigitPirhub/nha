from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from scripts.evaluate_baselines import _astar_grid, _path_length
from scripts.run_router_phase8_strict import _split_calib_train_val, _wilson_ci
from scripts.run_router_phase9_bench import _bootstrap_ci, _bootstrap_p_gt0
from utils.router_fastgeom import build_fastgeom_features

STATIC_BASE_COLS = [
    "line_block_ratio",
    "local_occ_ratio",
    "global_occ_ratio",
    "distance_ratio",
    "complexity_score",
    "los_clear",
    "L_fast",
    "T_fast_ms",
    "search_fast_ms",
    "path_len_fast",
]
FASTGEOM_COLS = [
    "fg_path_stretch",
    "fg_path_clear_mean",
    "fg_path_clear_std",
    "fg_path_clear_min",
    "fg_path_turn_mean_rad",
    "fg_path_turn_sum_rad",
    "fg_line_dev_mean_m",
    "fg_line_dev_p90_m",
    "fg_corridor_occ_mean",
    "fg_exp_bbox_ratio",
    "fg_exp_fill_ratio",
    "fg_exp_map_ratio",
    "fg_exp_goal_dist_ratio",
    "fg_exp_per_path_m",
    "fg_ms_per_exp",
]
DIFFICULTIES = ("easy", "medium", "hard")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step12-R4 strict trial runner: weighted-search portfolio family.")
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument(
        "--strict-phase9-root",
        type=Path,
        default=Path("outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak"),
        help="Frozen strict Phase9 root used as source of truth for base counterfactual/static/P5 decisions.",
    )
    p.add_argument("--weights", type=str, default="1.00,1.05,1.10,1.15,1.20,1.25,1.35")
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--calib-train-frac", type=float, default=0.60)
    p.add_argument("--calib-split-seed", type=int, default=20260306)
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--max-cases", type=int, default=-1, help="If >0, subsample each split for smoke debugging.")
    p.add_argument("--path-rel-mean-max", type=float, default=0.01)
    p.add_argument("--path-rel-p95-max", type=float, default=0.05)
    p.add_argument("--tree-depths", type=str, default="1,2")
    p.add_argument("--tree-min-leafs", type=str, default="120,240,360")
    p.add_argument("--fastgeom-max-expansions", type=int, default=50000)
    p.add_argument("--fastgeom-corridor-radius-cells", type=int, default=2)
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase29_step12r4_trials_v1.md"))
    p.add_argument("--summary-json", type=Path, default=Path("outputs/router_phase29_step12r4_trials_v1/summary.json"))
    return p.parse_args()


def _parse_seeds(raw: str) -> list[int]:
    return [int(x.strip()) for x in str(raw).split(",") if x.strip()]


def _parse_weights(raw: str) -> list[float]:
    vals = [float(x.strip()) for x in str(raw).split(",") if x.strip()]
    if not vals:
        raise ValueError("Empty weight list.")
    vals = sorted({round(v, 4) for v in vals})
    if 1.0 not in vals:
        vals = [1.0] + vals
    return vals


def _parse_int_list(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
    if not vals:
        raise ValueError("Empty integer list.")
    return vals


def _read_index(index_csv: Path) -> list[dict[str, str]]:
    if not index_csv.exists():
        raise FileNotFoundError(index_csv)
    rows: list[dict[str, str]] = []
    with index_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({str(k): str(v) for k, v in row.items()})
    if not rows:
        raise RuntimeError(f"Empty split index: {index_csv}")
    return rows


def _weight_tag(weight: float) -> str:
    return f"w{int(round(float(weight) * 100.0)):03d}"


def _load_p5_decisions(strict_phase9_root: Path, seed: int, split: str) -> pd.DataFrame:
    path = strict_phase9_root / "router_eval" / "seeds" / f"seed_{seed}" / "mixed" / "conformal_strict_v2" / f"{split}_decisions.parquet"
    return pd.read_parquet(path)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_p5"})


def _objective_from_calib_train(calib_train_df: pd.DataFrame) -> tuple[float, float]:
    t_ref = float(np.median(calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(calib_train_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    nz = q_pos[q_pos > 1e-9]
    q_med = float(np.median(nz)) if nz.size > 0 else 1.0
    beta = float(
        np.clip(
            np.median(calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)) / max(q_med, 1e-9),
            1e-3,
            200.0,
        )
    )
    return t_ref, beta


def _pooled_stats(all_delta: np.ndarray, *, bootstrap_n: int) -> dict:
    if all_delta.size <= 0:
        raise RuntimeError("Empty pooled delta array.")
    ci_lo, ci_hi = _bootstrap_ci(all_delta, n_boot=int(bootstrap_n))
    p_boot = _bootstrap_p_gt0(all_delta, n_boot=int(bootstrap_n))
    try:
        p_w = float(wilcoxon(all_delta, alternative="greater", zero_method="wilcox").pvalue)
    except ValueError:
        p_w = 1.0 if float(np.mean(all_delta)) <= 0.0 else 0.0
    return {
        "mean_delta_j": float(np.mean(all_delta)),
        "std_delta_j": float(np.std(all_delta)),
        "ci95": [float(ci_lo), float(ci_hi)],
        "p_value_bootstrap_gt0": float(p_boot),
        "p_value_wilcoxon": float(p_w),
    }


def _make_fastgeom_tables(args: argparse.Namespace, out_root: Path) -> tuple[Path, Path]:
    common = out_root / "common"
    common.mkdir(parents=True, exist_ok=True)
    cal = common / "fastgeom_features_calib.parquet"
    te = common / "fastgeom_features_test.parquet"
    if not cal.exists():
        build_fastgeom_features(
            dataset_root=args.dataset_root,
            split="calib",
            out_cache=cal,
            max_expansions=int(args.fastgeom_max_expansions),
            corridor_radius_cells=int(args.fastgeom_corridor_radius_cells),
        )
    if not te.exists():
        build_fastgeom_features(
            dataset_root=args.dataset_root,
            split="test",
            out_cache=te,
            max_expansions=int(args.fastgeom_max_expansions),
            corridor_radius_cells=int(args.fastgeom_corridor_radius_cells),
        )
    return cal, te


def _build_weight_tables(args: argparse.Namespace, out_root: Path, weights: list[float]) -> tuple[Path, Path]:
    common = out_root / "common"
    common.mkdir(parents=True, exist_ok=True)
    cal_path = common / "router_counterfactual_calib_wastar.parquet"
    test_path = common / "router_counterfactual_test_wastar.parquet"
    wanted = [_weight_tag(w) for w in weights if abs(w - 1.0) > 1e-9]

    def _ensure(split: str, out_path: Path) -> None:
        index_rows = _read_index(args.dataset_root / f"{split}_index.csv")
        if int(args.max_cases) > 0 and int(args.max_cases) < len(index_rows):
            rng = np.random.default_rng(20260306 if split == "calib" else 20260307)
            pick = rng.choice(np.arange(len(index_rows)), size=int(args.max_cases), replace=False)
            index_rows = [index_rows[int(i)] for i in sorted(pick.tolist())]
        expected_rows = len(index_rows)
        if out_path.exists():
            try:
                df_existing = pd.read_parquet(out_path)
                full_cols = set(df_existing.columns.tolist())
                need = {f"L_{tag}" for tag in wanted} | {f"T_{tag}_ms" for tag in wanted} | {f"path_len_{tag}" for tag in wanted}
                if need.issubset(full_cols) and len(df_existing) == expected_rows:
                    return
            except Exception:
                pass
        split_dir = args.dataset_root / split
        rows: list[dict[str, float | str | bool]] = []
        total = len(index_rows)
        for i, meta in enumerate(index_rows, start=1):
            sample_name = str(meta["sample_name"])
            sample = load_grid_sample(split_dir / sample_name)
            start_xy = (float(sample.start[0]), float(sample.start[1]))
            goal_xy = (float(sample.goal[0]), float(sample.goal[1]))
            row: dict[str, float | str | bool] = {
                "sample_name": sample_name,
                "difficulty": str(meta["difficulty"]),
            }
            for weight in weights:
                if abs(weight - 1.0) <= 1e-9:
                    continue
                tag = _weight_tag(weight)
                res = _astar_grid(
                    occupancy=sample.occupancy,
                    resolution=float(sample.resolution),
                    start_xy=start_xy,
                    goal_xy=goal_xy,
                    max_expansions=int(args.grid_max_expansions),
                    heuristic_map=None,
                    heuristic_weight=float(weight),
                    record_expanded=False,
                )
                row[f"success_{tag}"] = bool(res["success"])
                row[f"L_{tag}"] = float(res["expansions"])
                row[f"T_{tag}_ms"] = float(res["runtime_ms"])
                row[f"path_len_{tag}"] = float(_path_length(res.get("path", [])))
            rows.append(row)
            if i % 200 == 0 or i == total:
                print(f"[step12-r4:wastar] {split} processed {i}/{total}")
        pd.DataFrame(rows).to_parquet(out_path, index=False)

    _ensure("calib", cal_path)
    _ensure("test", test_path)
    return cal_path, test_path


class ArmCache:
    def __init__(self, df: pd.DataFrame, weights: list[float], *, t_ref: float, beta: float):
        self.df = df
        self.t_ref = float(max(float(t_ref), 1e-9))
        self.beta = float(beta)
        self.arms: dict[str, dict[str, np.ndarray]] = {}
        l_slow = df["L_slow"].to_numpy(dtype=np.float64)
        path_slow = df["path_len_slow"].to_numpy(dtype=np.float64)

        fast_drel = (df["L_fast"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)
        self.arms["fast"] = {
            "L": df["L_fast"].to_numpy(dtype=np.float64),
            "T": df["T_fast_ms"].to_numpy(dtype=np.float64),
            "path": df["path_len_fast"].to_numpy(dtype=np.float64),
            "drel": fast_drel,
            "qpos": np.maximum(fast_drel, 0.0),
        }
        self.arms["slow"] = {
            "L": l_slow,
            "T": df["T_slow_ms"].to_numpy(dtype=np.float64),
            "path": path_slow,
            "drel": np.zeros(len(df), dtype=np.float64),
            "qpos": np.zeros(len(df), dtype=np.float64),
        }
        for weight in weights:
            if abs(weight - 1.0) <= 1e-9:
                continue
            tag = _weight_tag(weight)
            key = f"wa_{tag}"
            drel = (df[f"L_{tag}"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)
            self.arms[key] = {
                "L": df[f"L_{tag}"].to_numpy(dtype=np.float64),
                "T": df[f"T_{tag}_ms"].to_numpy(dtype=np.float64),
                "path": df[f"path_len_{tag}"].to_numpy(dtype=np.float64),
                "drel": drel,
                "qpos": np.maximum(drel, 0.0),
            }
        for key, pack in self.arms.items():
            pack["J"] = pack["T"] / self.t_ref + self.beta * pack["qpos"]
            pack["path_rel"] = (pack["path"] - path_slow) / np.maximum(path_slow, 1e-6)

    def names(self, *, include_slow: bool) -> list[str]:
        names = ["fast"] + [k for k in self.arms.keys() if k.startswith("wa_")]
        names = sorted(names, key=lambda x: (0 if x == "fast" else float(x.split("_")[-1][1:]) if x.startswith("wa_") else 9999))
        if include_slow:
            names = names + ["slow"]
        return names


def _selection_metrics(cache: ArmCache, selected: np.ndarray, *, eps_rel: float, alpha: float) -> dict:
    selected = np.asarray(selected).astype(str)
    n = len(selected)
    j = np.zeros(n, dtype=np.float64)
    drel = np.zeros(n, dtype=np.float64)
    path_rel = np.zeros(n, dtype=np.float64)
    counts: dict[str, int] = {}
    for arm_name, pack in cache.arms.items():
        mask = selected == arm_name
        if not np.any(mask):
            counts[arm_name] = 0
            continue
        j[mask] = pack["J"][mask]
        drel[mask] = pack["drel"][mask]
        path_rel[mask] = pack["path_rel"][mask]
        counts[arm_name] = int(np.sum(mask))
    vio = drel > float(eps_rel)
    ci_lo, ci_hi = _wilson_ci(int(np.sum(vio)), int(n))
    return {
        "J_mean": float(np.mean(j)),
        "J_array": j,
        "drel_array": drel,
        "path_rel_array": path_rel,
        "violation_rate": float(np.mean(vio.astype(np.float64))),
        "violation_ci95_upper": float(ci_hi),
        "path_rel_mean": float(np.mean(path_rel)),
        "path_rel_p95": float(np.quantile(path_rel, 0.95)),
        "avg_latency_ms": float(np.mean([cache.arms[a]["T"][i] for i, a in enumerate(selected)])),
        "arm_counts": counts,
        "arm_distribution": {k: float(v / max(n, 1)) for k, v in counts.items()},
    }


def _p5_j_array(df: pd.DataFrame, use_fast_p5: np.ndarray, *, t_ref: float, beta: float) -> np.ndarray:
    q_fast = np.maximum(df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    j_fast = df["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + float(beta) * q_fast
    j_slow = df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
    return np.where(np.asarray(use_fast_p5, dtype=bool), j_fast, j_slow).astype(np.float64)


def _is_feasible(metrics: dict, *, alpha: float, path_rel_mean_max: float, path_rel_p95_max: float) -> bool:
    return bool(
        float(metrics["violation_ci95_upper"]) <= float(alpha) + 1e-12
        and float(metrics["path_rel_mean"]) <= float(path_rel_mean_max) + 1e-12
        and float(metrics["path_rel_p95"]) <= float(path_rel_p95_max) + 1e-12
    )


def _oracle_best_arm_indices(cache: ArmCache, arm_space: list[str]) -> np.ndarray:
    mats = np.stack([cache.arms[a]["J"] for a in arm_space], axis=1)
    return np.argmin(mats, axis=1).astype(np.int64)


def _build_feature_matrices(df_train: pd.DataFrame, df_val: pd.DataFrame, df_test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cols = STATIC_BASE_COLS + FASTGEOM_COLS + ["difficulty"]
    miss = [c for c in cols if c not in df_train.columns]
    if miss:
        raise RuntimeError(f"Missing feature columns for tree selector: {miss}")
    x_train = pd.get_dummies(df_train[cols], columns=["difficulty"], drop_first=False)
    x_val = pd.get_dummies(df_val[cols], columns=["difficulty"], drop_first=False).reindex(columns=x_train.columns, fill_value=0)
    x_test = pd.get_dummies(df_test[cols], columns=["difficulty"], drop_first=False).reindex(columns=x_train.columns, fill_value=0)
    return x_train, x_val, x_test


def _summarize_seed(
    *,
    seed: int,
    test_metrics: dict,
    j_p5_test: np.ndarray,
    selected_test: np.ndarray,
    method_name: str,
    policy_desc: dict,
) -> tuple[dict, np.ndarray]:
    j_sel = np.asarray(test_metrics["J_array"], dtype=np.float64)
    delta = (j_p5_test - j_sel).astype(np.float64)
    arm_dist = test_metrics["arm_distribution"]
    row = {
        "seed": int(seed),
        "mean_delta_j": float(np.mean(delta)),
        "median_delta_j": float(np.median(delta)),
        "mean_delta_j_route_only": float(np.mean(delta)),
        "mean_probe_overhead_norm": 0.0,
        "trigger_rate": float(1.0 - arm_dist.get("fast", 0.0)),
        "violation_rate": float(test_metrics["violation_rate"]),
        "violation_ci95_upper": float(test_metrics["violation_ci95_upper"]),
        "path_rel_mean": float(test_metrics["path_rel_mean"]),
        "path_rel_p95": float(test_metrics["path_rel_p95"]),
        "avg_latency_ms": float(test_metrics["avg_latency_ms"]),
        "arm_distribution": arm_dist,
        "selected_policy": policy_desc,
        "method": str(method_name),
        "num_cases": int(len(selected_test)),
    }
    return row, delta


def _save_weighted_policy_seed(
    out_dir: Path,
    *,
    seed: int,
    df_test: pd.DataFrame,
    selected_test: np.ndarray,
    t_ref: float,
    beta: float,
    policy_desc: dict,
    method_name: str,
    test_metrics: dict,
) -> None:
    seed_dir = out_dir / "seeds" / f"seed_{int(seed)}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    route_arm = np.asarray(selected_test, dtype=str)
    decisions = pd.DataFrame(
        {
            "sample_name": df_test["sample_name"].astype(str),
            "difficulty": df_test["difficulty"].astype(str),
            "route_arm": route_arm,
            "use_fast": route_arm == "fast",
            "probe_used": np.zeros(len(route_arm), dtype=bool),
        }
    )
    decisions.to_parquet(seed_dir / "test_decisions.parquet", index=False)
    metrics = {
        "version": "weighted_search_portfolio_policy_v1",
        "routing_family": "weighted_search_portfolio",
        "decision_space": "weighted_search_portfolio",
        "probe_overhead_mode": "none",
        "objective": {"T_ref": float(t_ref), "beta": float(beta)},
        "selected_policy": policy_desc,
        "route_arm_space": sorted({str(x) for x in route_arm.tolist()}),
        "test_metrics": {
            "J_mean": float(test_metrics["J_mean"]),
            "violation_rate": float(test_metrics["violation_rate"]),
            "violation_ci95_upper": float(test_metrics["violation_ci95_upper"]),
            "avg_latency_ms": float(test_metrics["avg_latency_ms"]),
            "arm_distribution": {str(k): float(v) for k, v in dict(test_metrics["arm_distribution"]).items()},
        },
        "method": str(method_name),
    }
    (seed_dir / "policy_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")


def _run_m_const_weight(args: argparse.Namespace, calib: pd.DataFrame, test: pd.DataFrame, weights: list[float]) -> dict:
    out_dir = ROOT / "outputs/router_phase29_m_const_weight_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    arm_space = ["fast"] + [f"wa_{_weight_tag(w)}" for w in weights if abs(w - 1.0) > 1e-9]

    all_delta: list[np.ndarray] = []
    seed_rows: list[dict] = []
    seeds = _parse_seeds(args.seeds)
    for seed in seeds:
        p5_cal = _load_p5_decisions(args.strict_phase9_root, seed, "calib")
        p5_test = _load_p5_decisions(args.strict_phase9_root, seed, "test")
        cal = calib.merge(p5_cal, on="sample_name", how="inner")
        te = test.merge(p5_test, on="sample_name", how="inner")
        cal_train, cal_val, _ = _split_calib_train_val(cal, train_frac=float(args.calib_train_frac), seed=int(args.calib_split_seed) + int(seed))
        t_ref, beta = _objective_from_calib_train(cal_train)
        cache_val = ArmCache(cal_val, weights, t_ref=t_ref, beta=beta)
        cache_test = ArmCache(te, weights, t_ref=t_ref, beta=beta)

        best_arm = None
        best_metrics = None
        for arm_name in arm_space:
            selected_val = np.asarray([arm_name] * len(cal_val))
            metrics_val = _selection_metrics(cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
            if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                continue
            if best_metrics is None or float(metrics_val["J_mean"]) < float(best_metrics["J_mean"]):
                best_arm = arm_name
                best_metrics = metrics_val
        if best_arm is None:
            best_arm = "fast"
            best_metrics = _selection_metrics(cache_val, np.asarray([best_arm] * len(cal_val)), eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))

        selected_test = np.asarray([best_arm] * len(te))
        metrics_test = _selection_metrics(cache_test, selected_test, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        j_p5_test = _p5_j_array(te, te["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta)
        policy_desc = {"selected_arm": best_arm}
        _save_weighted_policy_seed(
            out_dir,
            seed=seed,
            df_test=te,
            selected_test=selected_test,
            t_ref=t_ref,
            beta=beta,
            policy_desc=policy_desc,
            method_name="WAStarConst",
            test_metrics=metrics_test,
        )
        row, delta = _summarize_seed(
            seed=seed,
            test_metrics=metrics_test,
            j_p5_test=j_p5_test,
            selected_test=selected_test,
            method_name="WAStarConst",
            policy_desc=policy_desc,
        )
        seed_rows.append(row)
        all_delta.append(delta)

    all_delta_arr = np.concatenate(all_delta)
    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    stats = {
        "scheme": "M",
        "name": "WAStarConst",
        "pooled": _pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n)),
        "decomposition": {
            "mean_delta_j_route_only": float(np.mean(all_delta_arr)),
            "mean_probe_overhead_norm": 0.0,
            "trigger_rate": float(seed_df["trigger_rate"].mean()),
        },
        "gate_check": {
            "pooled_p_lt_0_01": bool(_pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n))["p_value_bootstrap_gt0"] < 0.01),
            "pooled_ci95_not_cross_0": bool(_pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n))["ci95"][0] > 0.0),
            "risk_ci95_upper_le_alpha_all_seeds": bool((seed_df["violation_ci95_upper"] <= float(args.alpha) + 1e-12).all()),
            "path_audit_hold_all_seeds": bool(
                (seed_df["path_rel_mean"] <= float(args.path_rel_mean_max) + 1e-12).all()
                and (seed_df["path_rel_p95"] <= float(args.path_rel_p95_max) + 1e-12).all()
            ),
        },
        "seed_rows": seed_rows,
    }
    seed_df.to_csv(out_dir / "seed_runs.csv", index=False)
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def _run_n_difficulty_weight(args: argparse.Namespace, calib: pd.DataFrame, test: pd.DataFrame, weights: list[float]) -> dict:
    out_dir = ROOT / "outputs/router_phase29_n_difficulty_weight_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    arm_space = ["fast"] + [f"wa_{_weight_tag(w)}" for w in weights if abs(w - 1.0) > 1e-9]

    all_delta: list[np.ndarray] = []
    seed_rows: list[dict] = []
    seeds = _parse_seeds(args.seeds)
    combos = list(product(arm_space, repeat=len(DIFFICULTIES)))

    for seed in seeds:
        p5_cal = _load_p5_decisions(args.strict_phase9_root, seed, "calib")
        p5_test = _load_p5_decisions(args.strict_phase9_root, seed, "test")
        cal = calib.merge(p5_cal, on="sample_name", how="inner")
        te = test.merge(p5_test, on="sample_name", how="inner")
        cal_train, cal_val, _ = _split_calib_train_val(cal, train_frac=float(args.calib_train_frac), seed=int(args.calib_split_seed) + int(seed))
        t_ref, beta = _objective_from_calib_train(cal_train)
        cache_val = ArmCache(cal_val, weights, t_ref=t_ref, beta=beta)
        cache_test = ArmCache(te, weights, t_ref=t_ref, beta=beta)

        best_combo = None
        best_metrics = None
        for combo in combos:
            mapping = {d: combo[i] for i, d in enumerate(DIFFICULTIES)}
            selected_val = cal_val["difficulty"].astype(str).map(mapping).fillna("fast").to_numpy(dtype=str)
            metrics_val = _selection_metrics(cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
            if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                continue
            if best_metrics is None or float(metrics_val["J_mean"]) < float(best_metrics["J_mean"]):
                best_combo = mapping
                best_metrics = metrics_val
        if best_combo is None:
            best_combo = {d: "fast" for d in DIFFICULTIES}

        selected_test = te["difficulty"].astype(str).map(best_combo).fillna("fast").to_numpy(dtype=str)
        metrics_test = _selection_metrics(cache_test, selected_test, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        j_p5_test = _p5_j_array(te, te["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta)
        policy_desc = {"weights_by_difficulty": best_combo}
        _save_weighted_policy_seed(
            out_dir,
            seed=seed,
            df_test=te,
            selected_test=selected_test,
            t_ref=t_ref,
            beta=beta,
            policy_desc=policy_desc,
            method_name="DifficultyWeightPortfolio",
            test_metrics=metrics_test,
        )
        row, delta = _summarize_seed(
            seed=seed,
            test_metrics=metrics_test,
            j_p5_test=j_p5_test,
            selected_test=selected_test,
            method_name="DifficultyWeightPortfolio",
            policy_desc=policy_desc,
        )
        seed_rows.append(row)
        all_delta.append(delta)

    all_delta_arr = np.concatenate(all_delta)
    pooled = _pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n))
    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    stats = {
        "scheme": "N",
        "name": "DifficultyWeightPortfolio",
        "pooled": pooled,
        "decomposition": {
            "mean_delta_j_route_only": float(np.mean(all_delta_arr)),
            "mean_probe_overhead_norm": 0.0,
            "trigger_rate": float(seed_df["trigger_rate"].mean()),
        },
        "gate_check": {
            "pooled_p_lt_0_01": bool(pooled["p_value_bootstrap_gt0"] < 0.01),
            "pooled_ci95_not_cross_0": bool(pooled["ci95"][0] > 0.0),
            "risk_ci95_upper_le_alpha_all_seeds": bool((seed_df["violation_ci95_upper"] <= float(args.alpha) + 1e-12).all()),
            "path_audit_hold_all_seeds": bool(
                (seed_df["path_rel_mean"] <= float(args.path_rel_mean_max) + 1e-12).all()
                and (seed_df["path_rel_p95"] <= float(args.path_rel_p95_max) + 1e-12).all()
            ),
        },
        "seed_rows": seed_rows,
    }
    seed_df.to_csv(out_dir / "seed_runs.csv", index=False)
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def _run_tree_portfolio(
    *,
    args: argparse.Namespace,
    calib: pd.DataFrame,
    test: pd.DataFrame,
    weights: list[float],
    include_slow: bool,
    scheme_key: str,
    scheme_name: str,
    out_dir: Path,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    depths = _parse_int_list(args.tree_depths)
    min_leafs = _parse_int_list(args.tree_min_leafs)

    all_delta: list[np.ndarray] = []
    seed_rows: list[dict] = []
    seeds = _parse_seeds(args.seeds)

    for seed in seeds:
        p5_cal = _load_p5_decisions(args.strict_phase9_root, seed, "calib")
        p5_test = _load_p5_decisions(args.strict_phase9_root, seed, "test")
        cal = calib.merge(p5_cal, on="sample_name", how="inner")
        te = test.merge(p5_test, on="sample_name", how="inner")
        cal_train, cal_val, _ = _split_calib_train_val(cal, train_frac=float(args.calib_train_frac), seed=int(args.calib_split_seed) + int(seed))
        t_ref, beta = _objective_from_calib_train(cal_train)
        cache_train = ArmCache(cal_train, weights, t_ref=t_ref, beta=beta)
        cache_val = ArmCache(cal_val, weights, t_ref=t_ref, beta=beta)
        cache_test = ArmCache(te, weights, t_ref=t_ref, beta=beta)
        arm_space = cache_train.names(include_slow=include_slow)

        x_train, x_val, x_test = _build_feature_matrices(cal_train, cal_val, te)
        y_train = _oracle_best_arm_indices(cache_train, arm_space)

        best = None
        for depth in depths:
            for min_leaf in min_leafs:
                clf = DecisionTreeClassifier(max_depth=int(depth), min_samples_leaf=int(min_leaf), random_state=int(seed))
                clf.fit(x_train, y_train)
                leaf_train = clf.apply(x_train)
                leaf_val = clf.apply(x_val)
                leaf_test = clf.apply(x_test)

                leaf_to_arm: dict[int, str] = {}
                for leaf_id in np.unique(leaf_train):
                    mask = leaf_train == leaf_id
                    best_arm = None
                    best_j = None
                    for arm_name in arm_space:
                        m = float(np.mean(cache_train.arms[arm_name]["J"][mask]))
                        if best_j is None or m < best_j:
                            best_j = m
                            best_arm = arm_name
                    leaf_to_arm[int(leaf_id)] = str(best_arm)

                selected_val = np.asarray([leaf_to_arm[int(x)] for x in leaf_val], dtype=str)
                metrics_val = _selection_metrics(cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
                if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                    continue
                if best is None or float(metrics_val["J_mean"]) < float(best["metrics_val"]["J_mean"]):
                    best = {
                        "depth": int(depth),
                        "min_leaf": int(min_leaf),
                        "leaf_to_arm": leaf_to_arm,
                        "leaf_test": leaf_test,
                        "metrics_val": metrics_val,
                    }

        if best is None:
            selected_test = np.asarray(["fast"] * len(te), dtype=str)
            policy_desc = {"fallback": "all_fast"}
        else:
            selected_test = np.asarray([best["leaf_to_arm"][int(x)] for x in best["leaf_test"]], dtype=str)
            policy_desc = {
                "depth": int(best["depth"]),
                "min_samples_leaf": int(best["min_leaf"]),
                "leaf_to_arm": {str(k): str(v) for k, v in best["leaf_to_arm"].items()},
            }

        metrics_test = _selection_metrics(cache_test, selected_test, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        j_p5_test = _p5_j_array(te, te["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta)
        _save_weighted_policy_seed(
            out_dir,
            seed=seed,
            df_test=te,
            selected_test=selected_test,
            t_ref=t_ref,
            beta=beta,
            policy_desc=policy_desc,
            method_name=scheme_name,
            test_metrics=metrics_test,
        )
        row, delta = _summarize_seed(
            seed=seed,
            test_metrics=metrics_test,
            j_p5_test=j_p5_test,
            selected_test=selected_test,
            method_name=scheme_name,
            policy_desc=policy_desc,
        )
        seed_rows.append(row)
        all_delta.append(delta)

    all_delta_arr = np.concatenate(all_delta)
    pooled = _pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n))
    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    stats = {
        "scheme": scheme_key,
        "name": scheme_name,
        "pooled": pooled,
        "decomposition": {
            "mean_delta_j_route_only": float(np.mean(all_delta_arr)),
            "mean_probe_overhead_norm": 0.0,
            "trigger_rate": float(seed_df["trigger_rate"].mean()),
        },
        "gate_check": {
            "pooled_p_lt_0_01": bool(pooled["p_value_bootstrap_gt0"] < 0.01),
            "pooled_ci95_not_cross_0": bool(pooled["ci95"][0] > 0.0),
            "risk_ci95_upper_le_alpha_all_seeds": bool((seed_df["violation_ci95_upper"] <= float(args.alpha) + 1e-12).all()),
            "path_audit_hold_all_seeds": bool(
                (seed_df["path_rel_mean"] <= float(args.path_rel_mean_max) + 1e-12).all()
                and (seed_df["path_rel_p95"] <= float(args.path_rel_p95_max) + 1e-12).all()
            ),
        },
        "seed_rows": seed_rows,
    }
    seed_df.to_csv(out_dir / "seed_runs.csv", index=False)
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def _write_report(path: Path, summary: dict, weights: list[float]) -> None:
    lines: list[str] = []
    lines.append("# Step12-R4 Trial Report (v1)")
    lines.append("")
    lines.append("Strict source root: `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/`")
    lines.append(f"Candidate weight set: `{[round(w, 3) for w in weights]}`")
    lines.append("Execution order: `M -> N -> O -> P`")
    lines.append("")
    lines.append("Design family: weighted-search portfolio under strict semantics (zero probe overhead; auxiliary path-length audit to avoid pure metric gaming).")
    lines.append("")
    for key in ["M", "N", "O", "P"]:
        stats = summary[key]
        pooled = stats["pooled"]
        dec = stats.get("decomposition", {})
        gate = stats.get("gate_check", {})
        lines.append(f"## Scheme {key} — {stats.get('name', key)}")
        lines.append(f"- pooled mean ΔJ: `{pooled['mean_delta_j']:.6f}`")
        lines.append(f"- pooled 95% CI: `[{pooled['ci95'][0]:.6f}, {pooled['ci95'][1]:.6f}]`")
        lines.append(f"- bootstrap p(gt0): `{pooled['p_value_bootstrap_gt0']:.6f}`")
        lines.append(f"- route-only mean ΔJ: `{dec.get('mean_delta_j_route_only', float('nan')):.6f}`")
        lines.append(f"- trigger / non-fast rate: `{dec.get('trigger_rate', float('nan')):.6f}`")
        lines.append(f"- gate: `{gate}`")
        best_seed = max(stats.get("seed_rows", []), key=lambda r: float(r.get("mean_delta_j", -1e18))) if stats.get("seed_rows") else None
        if best_seed is not None:
            lines.append(f"- example selected policy: `{best_seed.get('selected_policy', {})}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    weights = _parse_weights(args.weights)
    out_root = ROOT / "outputs/router_phase29_step12r4_trials_v1"
    out_root.mkdir(parents=True, exist_ok=True)

    strict_root = args.strict_phase9_root
    calib_cf = strict_root / "common" / "router_counterfactual_calib.parquet"
    test_cf = strict_root / "common" / "router_counterfactual_test.parquet"
    static_cal = strict_root / "common" / "risk" / "features_calib.parquet"
    static_test = strict_root / "common" / "risk" / "features_test.parquet"

    weight_cal_pq, weight_test_pq = _build_weight_tables(args, out_root, weights)
    fastgeom_cal_pq, fastgeom_test_pq = _make_fastgeom_tables(args, out_root)

    calib = pd.read_parquet(calib_cf).merge(pd.read_parquet(static_cal), on=["sample_name", "difficulty"], how="inner")
    calib = calib.merge(pd.read_parquet(weight_cal_pq), on=["sample_name", "difficulty"], how="inner")
    calib = calib.merge(pd.read_parquet(fastgeom_cal_pq), on=["sample_name", "difficulty"], how="inner")

    test = pd.read_parquet(test_cf).merge(pd.read_parquet(static_test), on=["sample_name", "difficulty"], how="inner")
    test = test.merge(pd.read_parquet(weight_test_pq), on=["sample_name", "difficulty"], how="inner")
    test = test.merge(pd.read_parquet(fastgeom_test_pq), on=["sample_name", "difficulty"], how="inner")

    summary: dict[str, object] = {}
    summary["M"] = _run_m_const_weight(args, calib, test, weights)
    summary["N"] = _run_n_difficulty_weight(args, calib, test, weights)
    summary["O"] = _run_tree_portfolio(
        args=args,
        calib=calib,
        test=test,
        weights=weights,
        include_slow=False,
        scheme_key="O",
        scheme_name="TreeWeightPortfolio",
        out_dir=ROOT / "outputs/router_phase29_o_tree_weight_v1",
    )
    summary["P"] = _run_tree_portfolio(
        args=args,
        calib=calib,
        test=test,
        weights=weights,
        include_slow=True,
        scheme_key="P",
        scheme_name="TreeWeightSlowFallback",
        out_dir=ROOT / "outputs/router_phase29_p_tree_weight_slow_v1",
    )
    summary["runtime_hours"] = float((time.perf_counter() - t0) / 3600.0)

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_report(args.report_md, summary, weights)
    print(f"[step12-r4] summary={args.summary_json}")
    print(f"[step12-r4] report={args.report_md}")


if __name__ == "__main__":
    main()
