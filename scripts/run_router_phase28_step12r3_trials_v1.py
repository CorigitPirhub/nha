from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_router_phase8_strict import _split_calib_train_val, _trace_switch_design_matrix, _wilson_ci
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
DCDR_EXTRA_COLS = [
    "dcdr_clutter_gap",
    "dcdr_detour_gap",
    "dcdr_clearance_span",
    "dcdr_fill_gap",
    "dcdr_search_density",
    "dcdr_safe_progress",
    "use_fast_default",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step12-R3 trial runner (K -> I -> J -> L) under strict semantics.")
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument(
        "--strict-phase9-root",
        type=Path,
        default=Path("outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak"),
        help="Frozen strict Phase9 root used as source of truth for base counterfactual/static/probe/P5 decisions.",
    )
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--calib-train-frac", type=float, default=0.60)
    p.add_argument("--calib-split-seed", type=int, default=20260302)
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument("--fastgeom-max-expansions", type=int, default=50000)
    p.add_argument("--fastgeom-corridor-radius-cells", type=int, default=2)
    p.add_argument("--csrr-max-cases", type=int, default=400)
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase28_step12r3_trials_v1.md"))
    p.add_argument("--summary-json", type=Path, default=Path("outputs/router_phase28_step12r3_trials_v1/summary.json"))
    return p.parse_args()


def _parse_seeds(s: str) -> list[int]:
    return [int(x.strip()) for x in str(s).split(",") if x.strip()]


def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_p5_decisions(strict_phase9_root: Path, seed: int, split: str) -> pd.DataFrame:
    path = strict_phase9_root / "router_eval" / "seeds" / f"seed_{seed}" / "mixed" / "conformal_strict_v2" / f"{split}_decisions.parquet"
    df = pd.read_parquet(path)[["sample_name", "use_fast"]].copy()
    return df.rename(columns={"use_fast": "use_fast_p5"})


def _objective_from_calib_train(calib_train_df: pd.DataFrame) -> tuple[float, float]:
    t_ref = float(np.median(calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(calib_train_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    nz = q_pos[q_pos > 1e-9]
    q_med = float(np.median(nz)) if nz.size > 0 else 1.0
    beta = float(np.clip(np.median(calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)) / max(q_med, 1e-9), 1e-3, 200.0))
    return t_ref, beta


def _route_only_j(df: pd.DataFrame, use_fast: np.ndarray, *, t_ref: float, beta: float, alt_t_col: str = "T_slow_ms", alt_q_col: str | None = None) -> np.ndarray:
    uf = np.asarray(use_fast, dtype=bool)
    q_fast = np.maximum(df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    j_fast = df["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + float(beta) * q_fast
    if alt_q_col is None:
        q_alt = np.zeros(len(df), dtype=np.float64)
    else:
        q_alt = np.maximum(df[alt_q_col].to_numpy(dtype=np.float64), 0.0)
    j_alt = df[alt_t_col].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + float(beta) * q_alt
    return np.where(uf, j_fast, j_alt).astype(np.float64)


def _probe_cost_norm(df: pd.DataFrame, *, t_ref: float) -> np.ndarray:
    return np.clip(df["probe_runtime_ms"].to_numpy(dtype=np.float64), 0.0, None) / max(t_ref, 1e-9)


def _compute_policy_metrics(df: pd.DataFrame, use_fast: np.ndarray, *, eps_rel: float, alt_q_col: str | None = None, alt_t_col: str = "T_slow_ms") -> dict:
    uf = np.asarray(use_fast, dtype=bool)
    q_fast = df["q_rel"].to_numpy(dtype=np.float64)
    if alt_q_col is None:
        q_alt = np.zeros(len(df), dtype=np.float64)
    else:
        q_alt = df[alt_q_col].to_numpy(dtype=np.float64)
    drel = np.where(uf, q_fast, q_alt)
    vio = drel > float(eps_rel)
    k = int(np.sum(vio))
    n = int(len(df))
    ci_lo, ci_hi = _wilson_ci(k, n)
    return {
        "num_cases": n,
        "fast_ratio": float(np.mean(uf.astype(np.float64))),
        "violation_rate": float(np.mean(vio.astype(np.float64))),
        "violation_count": int(k),
        "violation_rate_ci95": [float(ci_lo), float(ci_hi)],
        "avg_delta_l_rel": float(np.mean(drel)),
        "avg_latency_ms": float(np.mean(np.where(uf, df["T_fast_ms"].to_numpy(dtype=np.float64), df[alt_t_col].to_numpy(dtype=np.float64)))),
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


def _build_dcdr_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["dcdr_clutter_gap"] = out["fg_corridor_occ_mean"].to_numpy(dtype=np.float64) - out["local_occ_ratio"].to_numpy(dtype=np.float64)
    out["dcdr_detour_gap"] = out["fg_path_stretch"].to_numpy(dtype=np.float64) - out["distance_ratio"].to_numpy(dtype=np.float64)
    out["dcdr_clearance_span"] = out["fg_path_clear_mean"].to_numpy(dtype=np.float64) - out["fg_path_clear_min"].to_numpy(dtype=np.float64)
    out["dcdr_fill_gap"] = out["fg_exp_fill_ratio"].to_numpy(dtype=np.float64) - out["fg_exp_bbox_ratio"].to_numpy(dtype=np.float64)
    out["dcdr_search_density"] = out["fg_exp_per_path_m"].to_numpy(dtype=np.float64) * np.maximum(out["fg_corridor_occ_mean"].to_numpy(dtype=np.float64), 1e-6)
    out["dcdr_safe_progress"] = (1.0 - np.clip(out["fg_exp_goal_dist_ratio"].to_numpy(dtype=np.float64), 0.0, 1.0)) * np.maximum(out["fg_path_clear_min"].to_numpy(dtype=np.float64), 0.0)
    return out


def _matrix(df: pd.DataFrame, feature_cols: list[str], *, ref_cols: pd.Index | None = None) -> pd.DataFrame:
    cols = list(feature_cols) + ["difficulty"]
    miss = [c for c in cols if c not in df.columns]
    if miss:
        raise RuntimeError(f"Missing feature columns: {miss}")
    x = pd.get_dummies(df[cols], columns=["difficulty"], drop_first=False)
    if ref_cols is not None:
        x = x.reindex(columns=ref_cols, fill_value=0)
    return x


def _eval_delta(
    *,
    df: pd.DataFrame,
    use_fast_p5: np.ndarray,
    use_fast_route: np.ndarray,
    t_ref: float,
    beta: float,
    overhead: np.ndarray | None = None,
    alt_t_col: str = "T_slow_ms",
    alt_q_col: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    j_p5 = _route_only_j(df, use_fast_p5, t_ref=t_ref, beta=beta, alt_t_col="T_slow_ms", alt_q_col=None)
    j_route_only = _route_only_j(df, use_fast_route, t_ref=t_ref, beta=beta, alt_t_col=alt_t_col, alt_q_col=alt_q_col)
    over = np.zeros(len(df), dtype=np.float64) if overhead is None else np.asarray(overhead, dtype=np.float64)
    j_total = j_route_only + over
    return (j_p5 - j_total).astype(np.float64), (j_p5 - j_route_only).astype(np.float64), over.astype(np.float64)


def _save_policy_dir(out_dir: Path, *, split_name: str, df: pd.DataFrame, use_fast: np.ndarray, trigger: np.ndarray, extra_cols: dict[str, np.ndarray] | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    res = pd.DataFrame({
        "sample_name": df["sample_name"].astype(str),
        "difficulty": df["difficulty"].astype(str),
        "use_fast": np.asarray(use_fast, dtype=bool),
        "probe_used": np.asarray(trigger, dtype=bool),
    })
    res["route"] = np.where(res["use_fast"].to_numpy(dtype=bool), "fast", "slow")
    if extra_cols:
        for k, v in extra_cols.items():
            res[str(k)] = np.asarray(v)
    path = out_dir / f"{split_name}_decisions.parquet"
    res.to_parquet(path, index=False)
    return path


def _summarize_seed(
    *,
    seed: int,
    df_test: pd.DataFrame,
    use_fast_p5_test: np.ndarray,
    use_fast_test: np.ndarray,
    trigger_test: np.ndarray,
    t_ref: float,
    beta: float,
    overhead_test: np.ndarray | None,
    alt_t_col: str = "T_slow_ms",
    alt_q_col: str | None = None,
    eps_rel: float,
) -> dict:
    d_total, d_route, over = _eval_delta(
        df=df_test,
        use_fast_p5=use_fast_p5_test,
        use_fast_route=use_fast_test,
        t_ref=t_ref,
        beta=beta,
        overhead=overhead_test,
        alt_t_col=alt_t_col,
        alt_q_col=alt_q_col,
    )
    metrics = _compute_policy_metrics(df_test, use_fast_test, eps_rel=eps_rel, alt_q_col=alt_q_col, alt_t_col=alt_t_col)
    return {
        "seed": int(seed),
        "mean_delta_j": float(np.mean(d_total)),
        "median_delta_j": float(np.median(d_total)),
        "mean_delta_j_route_only": float(np.mean(d_route)),
        "mean_probe_overhead_norm": float(np.mean(over)),
        "trigger_rate": float(np.mean(np.asarray(trigger_test, dtype=np.float64))),
        "violation_rate": float(metrics["violation_rate"]),
        "violation_ci95_upper": float(metrics["violation_rate_ci95"][1]),
        "fast_ratio": float(metrics["fast_ratio"]),
        "num_cases": int(metrics["num_cases"]),
    }


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


def _run_k_dcdr(args: argparse.Namespace, calib_df: pd.DataFrame, test_df: pd.DataFrame, fastgeom_cal: pd.DataFrame, fastgeom_test: pd.DataFrame) -> dict:
    out_dir = ROOT / "outputs/router_phase28_k_dcdr_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    calib = _build_dcdr_features(calib_df.merge(fastgeom_cal, on=["sample_name", "difficulty"], how="inner"))
    test = _build_dcdr_features(test_df.merge(fastgeom_test, on=["sample_name", "difficulty"], how="inner"))
    feature_cols = STATIC_BASE_COLS + FASTGEOM_COLS + DCDR_EXTRA_COLS

    all_delta: list[np.ndarray] = []
    all_route: list[np.ndarray] = []
    all_over: list[np.ndarray] = []
    seed_rows: list[dict] = []
    per_seed: dict[str, dict] = {}

    seeds = _parse_seeds(args.seeds)
    for seed in seeds:
        p5_cal = _load_p5_decisions(args.strict_phase9_root, seed, "calib")
        p5_test = _load_p5_decisions(args.strict_phase9_root, seed, "test")
        cal = calib.merge(p5_cal, on="sample_name", how="inner")
        te = test.merge(p5_test, on="sample_name", how="inner")
        if len(cal) != len(calib) or len(te) != len(test):
            raise RuntimeError(f"P5 decision merge mismatch for seed={seed}")
        cal_train, cal_val, split_map = _split_calib_train_val(cal, train_frac=float(args.calib_train_frac), seed=int(args.calib_split_seed))
        train = cal_train.loc[cal_train["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        val = cal_val.loc[cal_val["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        test_elig = te.loc[te["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        t_ref, beta = _objective_from_calib_train(cal_train)
        y_train = (
            cal_train.loc[cal_train["use_fast_p5"].to_numpy(dtype=bool), "T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
            + beta * np.maximum(train["q_rel"].to_numpy(dtype=np.float64), 0.0)
            - train["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
        )
        x_train = _matrix(train, feature_cols)
        x_val = _matrix(val, feature_cols, ref_cols=x_train.columns)
        x_test = _matrix(test_elig, feature_cols, ref_cols=x_train.columns)
        reg = GradientBoostingRegressor(random_state=int(seed), n_estimators=500, learning_rate=0.04, max_depth=3, subsample=0.9)
        reg.fit(x_train, y_train)
        pred_val = reg.predict(x_val).astype(np.float64)
        pred_test = reg.predict(x_test).astype(np.float64)
        resid_val = (pred_val - (
            val["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
            + beta * np.maximum(val["q_rel"].to_numpy(dtype=np.float64), 0.0)
            - val["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
        )).astype(np.float64)
        q_by_diff: dict[str, float] = {}
        val_diff = val["difficulty"].to_numpy(dtype=str)
        for d in ("easy", "medium", "hard"):
            mask = val_diff == d
            arr = resid_val[mask]
            if arr.size <= 0:
                q_by_diff[d] = 0.0
                continue
            level = float(np.ceil((arr.size + 1) * (1.0 - float(args.alpha))) / arr.size)
            q_by_diff[d] = float(np.quantile(arr, np.clip(level, 0.0, 1.0), method="higher"))
        lcb_val = pred_val - np.array([q_by_diff[d] for d in val_diff], dtype=np.float64)
        cand = sorted(set(float(x) for x in np.quantile(lcb_val, np.linspace(0.0, 1.0, 81), method="higher").tolist() + [0.0, float("inf")]))
        best = None
        val_use_fast_p5 = cal_val["use_fast_p5"].to_numpy(dtype=bool)
        for thr in cand:
            sw_sub = lcb_val > float(thr)
            use_fast_val = val_use_fast_p5.copy()
            use_fast_val[val_use_fast_p5] = ~sw_sub
            d_total, d_route, over = _eval_delta(df=cal_val, use_fast_p5=val_use_fast_p5, use_fast_route=use_fast_val, t_ref=t_ref, beta=beta)
            metrics = _compute_policy_metrics(cal_val, use_fast_val, eps_rel=float(args.epsilon_rel))
            key = (float(np.mean(d_total)), -float(np.mean(use_fast_val.astype(np.float64))))
            if best is None or key > best["key"]:
                best = {"key": key, "thr": float(thr), "lcb_val": lcb_val, "switch_val": sw_sub, "metrics": metrics}
        assert best is not None
        test_diff = test_elig["difficulty"].to_numpy(dtype=str)
        lcb_test = pred_test - np.array([q_by_diff[d] for d in test_diff], dtype=np.float64)
        switch_test_sub = lcb_test > float(best["thr"])
        use_fast_test = te["use_fast_p5"].to_numpy(dtype=bool).copy()
        elig_test_mask = te["use_fast_p5"].to_numpy(dtype=bool)
        use_fast_test[elig_test_mask] = ~switch_test_sub
        trigger_test = switch_test_sub.astype(bool)
        d_total, d_route, over = _eval_delta(df=te, use_fast_p5=te["use_fast_p5"].to_numpy(dtype=bool), use_fast_route=use_fast_test, t_ref=t_ref, beta=beta)
        all_delta.append(d_total)
        all_route.append(d_route)
        all_over.append(over)
        seed_rows.append(
            _summarize_seed(
                seed=int(seed),
                df_test=te,
                use_fast_p5_test=te["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_test=use_fast_test,
                trigger_test=trigger_test,
                t_ref=t_ref,
                beta=beta,
                overhead_test=np.zeros(len(te), dtype=np.float64),
                eps_rel=float(args.epsilon_rel),
            )
        )
        seed_dir = out_dir / "seeds" / f"seed_{seed}" / "mixed" / "disagreement_cert_v1"
        cal_labels = calib["sample_name"].astype(str).map(split_map)
        use_fast_cal = cal["use_fast_p5"].to_numpy(dtype=bool).copy()
        elig_cal = cal["use_fast_p5"].to_numpy(dtype=bool)
        pred_cal_all = reg.predict(_matrix(cal.loc[elig_cal].reset_index(drop=True), feature_cols, ref_cols=x_train.columns)).astype(np.float64)
        diff_cal = cal.loc[elig_cal, "difficulty"].to_numpy(dtype=str)
        lcb_cal = pred_cal_all - np.array([q_by_diff[d] for d in diff_cal], dtype=np.float64)
        sw_cal = lcb_cal > float(best["thr"])
        use_fast_cal[elig_cal] = ~sw_cal
        switch_cal_full = np.zeros(len(cal), dtype=bool)
        switch_cal_full[elig_cal] = sw_cal.astype(bool)
        switch_test_full = np.zeros(len(te), dtype=bool)
        switch_test_full[elig_test_mask] = switch_test_sub.astype(bool)
        lcb_test_full = np.full(len(te), np.nan, dtype=np.float64)
        lcb_test_full[elig_test_mask] = lcb_test.astype(np.float64)
        _save_policy_dir(seed_dir, split_name="calib", df=cal, use_fast=use_fast_cal, trigger=np.zeros(len(cal), dtype=bool), extra_cols={"switch_to_slow": switch_cal_full})
        _save_policy_dir(seed_dir, split_name="test", df=te, use_fast=use_fast_test, trigger=np.zeros(len(te), dtype=bool), extra_cols={"switch_to_slow": switch_test_full, "lcb_gain": lcb_test_full})
        metrics = {
            "version": "disagreement_cert_v1",
            "seed": int(seed),
            "objective": {"T_ref": float(t_ref), "beta": float(beta)},
            "selected_policy": {"threshold": float(best["thr"]), "q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()}, "feature_family": "static_plus_fastgeom_disagreement"},
            "val_metrics": best["metrics"],
            "test_metrics": _compute_policy_metrics(te, use_fast_test, eps_rel=float(args.epsilon_rel)),
            "delta_j_mean_vs_p5_test": float(np.mean(d_total)),
            "delta_j_route_only_vs_p5_test": float(np.mean(d_route)),
            "artifacts": {
                "calib_decisions_parquet": str(seed_dir / "calib_decisions.parquet"),
                "test_decisions_parquet": str(seed_dir / "test_decisions.parquet"),
            },
        }
        (seed_dir / "policy_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        per_seed[str(seed)] = metrics

    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    all_delta_arr = np.concatenate(all_delta) if all_delta else np.zeros(0, dtype=np.float64)
    all_route_arr = np.concatenate(all_route) if all_route else np.zeros(0, dtype=np.float64)
    stats = {
        "scheme": "K",
        "name": "DCDR",
        "runtime_hours": 0.0,
        "pooled": _pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n)),
        "decomposition": {
            "mean_delta_j_route_only": float(np.mean(all_route_arr)) if all_route_arr.size > 0 else float("nan"),
            "mean_probe_overhead_norm": 0.0,
            "trigger_rate": float(seed_df["trigger_rate"].mean()) if not seed_df.empty else float("nan"),
        },
        "gate_check": {
            "pooled_p_lt_0_01": bool(_pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n))["p_value_bootstrap_gt0"] < 0.01),
            "pooled_ci95_not_cross_0": bool(_pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n))["ci95"][0] > 0.0),
            "risk_ci95_upper_le_alpha_all_seeds": bool((seed_df["violation_ci95_upper"] <= float(args.alpha) + 1e-12).all()),
        },
        "seed_rows": seed_rows,
    }
    stats["runtime_hours"] = float(0.0)
    (out_dir / "seed_runs.csv").parent.mkdir(parents=True, exist_ok=True)
    seed_df.to_csv(out_dir / "seed_runs.csv", index=False)
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def _run_i_cgas(args: argparse.Namespace, calib_df: pd.DataFrame, test_df: pd.DataFrame, probe_cal: pd.DataFrame, probe_test: pd.DataFrame) -> dict:
    out_dir = ROOT / "outputs/router_phase28_i_cgas_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    calib = calib_df.merge(probe_cal, on=["sample_name", "difficulty"], how="inner")
    test = test_df.merge(probe_test, on=["sample_name", "difficulty"], how="inner")

    all_delta: list[np.ndarray] = []
    all_route: list[np.ndarray] = []
    all_over: list[np.ndarray] = []
    seed_rows: list[dict] = []
    seeds = _parse_seeds(args.seeds)

    for seed in seeds:
        p5_cal = _load_p5_decisions(args.strict_phase9_root, seed, "calib")
        p5_test = _load_p5_decisions(args.strict_phase9_root, seed, "test")
        cal = calib.merge(p5_cal, on="sample_name", how="inner")
        te = test.merge(p5_test, on="sample_name", how="inner")
        cal_train, cal_val, _ = _split_calib_train_val(cal, train_frac=float(args.calib_train_frac), seed=int(args.calib_split_seed))
        train = cal_train.loc[cal_train["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        val = cal_val.loc[cal_val["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        test_elig = te.loc[te["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        t_ref, beta = _objective_from_calib_train(cal_train)
        y_train = train["q_rel"].to_numpy(dtype=np.float64) - float(args.epsilon_rel)
        x_train = _trace_switch_design_matrix(train)
        x_val = _trace_switch_design_matrix(val, ref_cols=x_train.columns)
        x_test = _trace_switch_design_matrix(test_elig, ref_cols=x_train.columns)
        reg = GradientBoostingRegressor(random_state=int(seed), n_estimators=400, learning_rate=0.05, max_depth=3, subsample=0.9)
        reg.fit(x_train, y_train)
        pred_val = reg.predict(x_val).astype(np.float64)
        pred_test = reg.predict(x_test).astype(np.float64)
        resid_val = (val["q_rel"].to_numpy(dtype=np.float64) - float(args.epsilon_rel) - pred_val).astype(np.float64)
        q_by_diff: dict[str, float] = {}
        val_diff = val["difficulty"].to_numpy(dtype=str)
        for d in ("easy", "medium", "hard"):
            mask = val_diff == d
            arr = resid_val[mask]
            if arr.size <= 0:
                q_by_diff[d] = 0.0
                continue
            level = float(np.ceil((arr.size + 1) * (1.0 - float(args.alpha))) / arr.size)
            q_by_diff[d] = float(np.quantile(arr, np.clip(level, 0.0, 1.0), method="higher"))
        ucb_val = pred_val + np.array([q_by_diff[d] for d in val_diff], dtype=np.float64)
        val_use_fast_p5 = cal_val["use_fast_p5"].to_numpy(dtype=bool)
        probe_cost_val = _probe_cost_norm(cal_val, t_ref=t_ref)[val_use_fast_p5]
        cand = sorted(set(float(x) for x in np.quantile(ucb_val, np.linspace(0.0, 1.0, 81), method="higher").tolist() + [0.0, float("inf")]))
        best = None
        for thr in cand:
            sw_sub = ucb_val > float(thr)
            use_fast_val = val_use_fast_p5.copy()
            use_fast_val[val_use_fast_p5] = ~sw_sub
            overhead_full = np.zeros(len(cal_val), dtype=np.float64)
            overhead_full[val_use_fast_p5] = probe_cost_val * sw_sub.astype(np.float64)
            d_total, d_route, over = _eval_delta(df=cal_val, use_fast_p5=val_use_fast_p5, use_fast_route=use_fast_val, t_ref=t_ref, beta=beta, overhead=overhead_full)
            key = (float(np.mean(d_total)), -float(np.mean(sw_sub.astype(np.float64))))
            if best is None or key > best["key"]:
                best = {"key": key, "thr": float(thr)}
        assert best is not None
        test_diff = test_elig["difficulty"].to_numpy(dtype=str)
        ucb_test = pred_test + np.array([q_by_diff[d] for d in test_diff], dtype=np.float64)
        sw_test_sub = ucb_test > float(best["thr"])
        elig_test_mask = te["use_fast_p5"].to_numpy(dtype=bool)
        use_fast_test = te["use_fast_p5"].to_numpy(dtype=bool).copy()
        use_fast_test[elig_test_mask] = ~sw_test_sub
        overhead_test = np.zeros(len(te), dtype=np.float64)
        overhead_test[elig_test_mask] = _probe_cost_norm(te.loc[elig_test_mask].reset_index(drop=True), t_ref=t_ref) * sw_test_sub.astype(np.float64)
        d_total, d_route, over = _eval_delta(df=te, use_fast_p5=te["use_fast_p5"].to_numpy(dtype=bool), use_fast_route=use_fast_test, t_ref=t_ref, beta=beta, overhead=overhead_test)
        all_delta.append(d_total)
        all_route.append(d_route)
        all_over.append(over)
        seed_rows.append(
            _summarize_seed(
                seed=int(seed),
                df_test=te,
                use_fast_p5_test=te["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_test=use_fast_test,
                trigger_test=sw_test_sub,
                t_ref=t_ref,
                beta=beta,
                overhead_test=overhead_test,
                eps_rel=float(args.epsilon_rel),
            )
        )
        seed_dir = out_dir / "seeds" / f"seed_{seed}" / "mixed" / "gap_stop_cert_v1"
        switch_test_full = np.zeros(len(te), dtype=bool)
        switch_test_full[elig_test_mask] = sw_test_sub.astype(bool)
        ucb_test_full = np.full(len(te), np.nan, dtype=np.float64)
        ucb_test_full[elig_test_mask] = ucb_test.astype(np.float64)
        _save_policy_dir(seed_dir, split_name="test", df=te, use_fast=use_fast_test, trigger=switch_test_full, extra_cols={"ucb_excess": ucb_test_full, "trace_overhead_norm": overhead_test})
        metrics = {
            "version": "gap_stop_cert_v1",
            "seed": int(seed),
            "probe_overhead_mode": "trace_slow_only",
            "objective": {"T_ref": float(t_ref), "beta": float(beta)},
            "selected_policy": {"threshold": float(best["thr"]), "q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()}, "score": "UCB(q_rel - eps_rel)"},
            "test_metrics": _compute_policy_metrics(te, use_fast_test, eps_rel=float(args.epsilon_rel)),
            "delta_j_mean_vs_p5_test": float(np.mean(d_total)),
            "delta_j_route_only_vs_p5_test": float(np.mean(d_route)),
            "mean_trace_overhead_norm_test": float(np.mean(over)),
        }
        (seed_dir / "policy_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    all_delta_arr = np.concatenate(all_delta) if all_delta else np.zeros(0, dtype=np.float64)
    all_route_arr = np.concatenate(all_route) if all_route else np.zeros(0, dtype=np.float64)
    all_over_arr = np.concatenate(all_over) if all_over else np.zeros(0, dtype=np.float64)
    pooled = _pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n))
    stats = {
        "scheme": "I",
        "name": "CGAS",
        "pooled": pooled,
        "decomposition": {
            "mean_delta_j_route_only": float(np.mean(all_route_arr)) if all_route_arr.size > 0 else float("nan"),
            "mean_probe_overhead_norm": float(np.mean(all_over_arr)) if all_over_arr.size > 0 else float("nan"),
            "trigger_rate": float(seed_df["trigger_rate"].mean()) if not seed_df.empty else float("nan"),
        },
        "gate_check": {
            "pooled_p_lt_0_01": bool(pooled["p_value_bootstrap_gt0"] < 0.01),
            "pooled_ci95_not_cross_0": bool(pooled["ci95"][0] > 0.0),
            "risk_ci95_upper_le_alpha_all_seeds": bool((seed_df["violation_ci95_upper"] <= float(args.alpha) + 1e-12).all()),
        },
        "seed_rows": seed_rows,
    }
    seed_df.to_csv(out_dir / "seed_runs.csv", index=False)
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def _run_j_csrr(args: argparse.Namespace, calib_cf: Path, test_cf: Path) -> dict:
    out_dir = ROOT / "outputs/router_phase28_j_csrr_v1"
    common = out_dir / "common"
    common.mkdir(parents=True, exist_ok=True)
    cal_mid = common / "router_counterfactual_calib_crop_padded.parquet"
    te_mid = common / "router_counterfactual_test_crop_padded.parquet"
    slow_ckpt = ROOT / "outputs/checkpoints/exp3_final_manual_v11b.pt"
    for split, base, outp in [("calib", calib_cf, cal_mid), ("test", test_cf, te_mid)]:
        report = outp.with_name(outp.stem + "_report.json")
        if not outp.exists():
            cmd = [
                sys.executable,
                str(ROOT / "scripts/run_router_phase23_build_k3_counterfactual_v1.py"),
                "--dataset-root", str(args.dataset_root),
                "--split", split,
                "--base-parquet", str(base),
                "--mid-method", "crop_padded",
                "--slow-checkpoint", str(slow_ckpt),
                "--device", "cpu",
                "--crop-margin-cells", "8",
                "--crop-pad-multiple", "32",
                "--max-cases", str(int(args.csrr_max_cases)),
                "--out-parquet", str(outp),
                "--out-report", str(report),
            ]
            subprocess.run(cmd, check=True)
    calib = pd.read_parquet(cal_mid)
    test = pd.read_parquet(te_mid)
    t_ref, beta = _objective_from_calib_train(calib)
    def _arm_point(df: pd.DataFrame, l_col: str, t_col: str) -> dict:
        q = np.maximum((df[l_col].to_numpy(dtype=np.float64) - df["L_slow"].to_numpy(dtype=np.float64)) / np.maximum(df["L_slow"].to_numpy(dtype=np.float64), 1e-6), 0.0)
        j = df[t_col].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + beta * q
        vio = q > float(args.epsilon_rel)
        return {"J_mean": float(np.mean(j)), "violation_rate": float(np.mean(vio)), "latency_ms": float(np.mean(df[t_col].to_numpy(dtype=np.float64)))}
    pts = {
        "always_fast": _arm_point(test, "L_fast", "T_fast_ms"),
        "always_crop_padded": _arm_point(test, "L_mid", "T_mid_ms"),
        "always_slow": _arm_point(test, "L_slow", "T_slow_ms"),
    }
    j_fast = test["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + beta * np.maximum(test["q_rel"].to_numpy(dtype=np.float64), 0.0)
    q_mid = np.maximum(test["q_rel_mid"].to_numpy(dtype=np.float64), 0.0)
    j_mid = test["T_mid_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + beta * q_mid
    j_slow = test["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
    best_idx = np.argmin(np.stack([j_fast, j_mid, j_slow], axis=0), axis=0)
    stats = {
        "scheme": "J",
        "name": "CSRR",
        "arm_points": pts,
        "mid_best_fraction": float(np.mean(best_idx == 1)),
        "mid_beats_slow_fraction": float(np.mean(j_mid < j_slow)),
        "mid_beats_fast_fraction": float(np.mean(j_mid < j_fast)),
        "dominated_by_best_single_arm": bool(pts["always_crop_padded"]["J_mean"] >= min(pts["always_fast"]["J_mean"], pts["always_slow"]["J_mean"])),
        "status": "arm_pilot_only",
        "pilot_max_cases": int(args.csrr_max_cases),
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def _run_l_cssd(args: argparse.Namespace, calib_df: pd.DataFrame, test_df: pd.DataFrame, probe_cal: pd.DataFrame, probe_test: pd.DataFrame, fastgeom_cal: pd.DataFrame, fastgeom_test: pd.DataFrame) -> dict:
    out_dir = ROOT / "outputs/router_phase28_l_cssd_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    calib = _build_dcdr_features(calib_df.merge(probe_cal, on=["sample_name", "difficulty"], how="inner").merge(fastgeom_cal, on=["sample_name", "difficulty"], how="inner"))
    test = _build_dcdr_features(test_df.merge(probe_test, on=["sample_name", "difficulty"], how="inner").merge(fastgeom_test, on=["sample_name", "difficulty"], how="inner"))
    teacher_feat_cols = list(_trace_switch_design_matrix(calib.head(1)).columns)
    student_feat_cols = STATIC_BASE_COLS + FASTGEOM_COLS + DCDR_EXTRA_COLS

    all_delta: list[np.ndarray] = []
    all_route: list[np.ndarray] = []
    seed_rows: list[dict] = []
    seeds = _parse_seeds(args.seeds)

    for seed in seeds:
        p5_cal = _load_p5_decisions(args.strict_phase9_root, seed, "calib")
        p5_test = _load_p5_decisions(args.strict_phase9_root, seed, "test")
        cal = calib.merge(p5_cal, on="sample_name", how="inner")
        te = test.merge(p5_test, on="sample_name", how="inner")
        cal_train, cal_val, _ = _split_calib_train_val(cal, train_frac=float(args.calib_train_frac), seed=int(args.calib_split_seed))
        train = cal_train.loc[cal_train["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        val = cal_val.loc[cal_val["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        test_elig = te.loc[te["use_fast_p5"].to_numpy(dtype=bool)].reset_index(drop=True)
        t_ref, beta = _objective_from_calib_train(cal_train)
        g_train = (
            train["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
            + beta * np.maximum(train["q_rel"].to_numpy(dtype=np.float64), 0.0)
            - train["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
        )
        x_teacher_train = _trace_switch_design_matrix(train)
        teacher = GradientBoostingRegressor(random_state=int(seed), n_estimators=500, learning_rate=0.04, max_depth=3, subsample=0.9)
        teacher.fit(x_teacher_train, g_train)
        x_student_train = _matrix(train, student_feat_cols)
        x_student_val = _matrix(val, student_feat_cols, ref_cols=x_student_train.columns)
        x_student_test = _matrix(test_elig, student_feat_cols, ref_cols=x_student_train.columns)
        teacher_soft_train = teacher.predict(x_teacher_train).astype(np.float64)
        student_target = (0.7 * teacher_soft_train + 0.3 * g_train).astype(np.float64)
        student = make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(16, 4), random_state=int(seed), max_iter=800, learning_rate_init=1e-3))
        student.fit(x_student_train, student_target)
        pred_val = student.predict(x_student_val).astype(np.float64)
        pred_test = student.predict(x_student_test).astype(np.float64)
        g_val_true = (
            val["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
            + beta * np.maximum(val["q_rel"].to_numpy(dtype=np.float64), 0.0)
            - val["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
        )
        resid_val = (pred_val - g_val_true).astype(np.float64)
        q_by_diff: dict[str, float] = {}
        val_diff = val["difficulty"].to_numpy(dtype=str)
        for d in ("easy", "medium", "hard"):
            mask = val_diff == d
            arr = resid_val[mask]
            if arr.size <= 0:
                q_by_diff[d] = 0.0
                continue
            level = float(np.ceil((arr.size + 1) * (1.0 - float(args.alpha))) / arr.size)
            q_by_diff[d] = float(np.quantile(arr, np.clip(level, 0.0, 1.0), method="higher"))
        lcb_val = pred_val - np.array([q_by_diff[d] for d in val_diff], dtype=np.float64)
        cand = sorted(set(float(x) for x in np.quantile(lcb_val, np.linspace(0.0, 1.0, 81), method="higher").tolist() + [0.0, float("inf")]))
        best = None
        val_use_fast_p5 = cal_val["use_fast_p5"].to_numpy(dtype=bool)
        for thr in cand:
            sw_sub = lcb_val > float(thr)
            use_fast_val = val_use_fast_p5.copy()
            use_fast_val[val_use_fast_p5] = ~sw_sub
            d_total, _, _ = _eval_delta(df=cal_val, use_fast_p5=val_use_fast_p5, use_fast_route=use_fast_val, t_ref=t_ref, beta=beta)
            key = (float(np.mean(d_total)), -float(np.mean(sw_sub.astype(np.float64))))
            if best is None or key > best["key"]:
                best = {"key": key, "thr": float(thr)}
        assert best is not None
        test_diff = test_elig["difficulty"].to_numpy(dtype=str)
        lcb_test = pred_test - np.array([q_by_diff[d] for d in test_diff], dtype=np.float64)
        sw_test_sub = lcb_test > float(best["thr"])
        elig_test_mask = te["use_fast_p5"].to_numpy(dtype=bool)
        use_fast_test = te["use_fast_p5"].to_numpy(dtype=bool).copy()
        use_fast_test[elig_test_mask] = ~sw_test_sub
        d_total, d_route, over = _eval_delta(df=te, use_fast_p5=te["use_fast_p5"].to_numpy(dtype=bool), use_fast_route=use_fast_test, t_ref=t_ref, beta=beta)
        all_delta.append(d_total)
        all_route.append(d_route)
        seed_rows.append(
            _summarize_seed(
                seed=int(seed),
                df_test=te,
                use_fast_p5_test=te["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_test=use_fast_test,
                trigger_test=sw_test_sub,
                t_ref=t_ref,
                beta=beta,
                overhead_test=np.zeros(len(te), dtype=np.float64),
                eps_rel=float(args.epsilon_rel),
            )
        )
        seed_dir = out_dir / "seeds" / f"seed_{seed}" / "mixed" / "distilled_stat_router_v1"
        switch_test_full = np.zeros(len(te), dtype=bool)
        switch_test_full[elig_test_mask] = sw_test_sub.astype(bool)
        lcb_test_full = np.full(len(te), np.nan, dtype=np.float64)
        lcb_test_full[elig_test_mask] = lcb_test.astype(np.float64)
        _save_policy_dir(seed_dir, split_name="test", df=te, use_fast=use_fast_test, trigger=np.zeros(len(te), dtype=bool), extra_cols={"switch_to_slow": switch_test_full, "lcb_gain": lcb_test_full})
        metrics = {
            "version": "distilled_stat_router_v1",
            "seed": int(seed),
            "objective": {"T_ref": float(t_ref), "beta": float(beta)},
            "selected_policy": {"threshold": float(best["thr"]), "q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()}},
            "distillation": {"teacher": "probe+static+fastgeom GBDT", "student": "StandardScaler+MLPRegressor(16,4)", "target": "0.7*teacher_soft + 0.3*oracle_signed_gain"},
            "delta_j_mean_vs_p5_test": float(np.mean(d_total)),
            "delta_j_route_only_vs_p5_test": float(np.mean(d_route)),
            "test_metrics": _compute_policy_metrics(te, use_fast_test, eps_rel=float(args.epsilon_rel)),
        }
        (seed_dir / "policy_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    all_delta_arr = np.concatenate(all_delta) if all_delta else np.zeros(0, dtype=np.float64)
    all_route_arr = np.concatenate(all_route) if all_route else np.zeros(0, dtype=np.float64)
    pooled = _pooled_stats(all_delta_arr, bootstrap_n=int(args.bootstrap_n))
    stats = {
        "scheme": "L",
        "name": "CSSD",
        "pooled": pooled,
        "decomposition": {
            "mean_delta_j_route_only": float(np.mean(all_route_arr)) if all_route_arr.size > 0 else float("nan"),
            "mean_probe_overhead_norm": 0.0,
            "trigger_rate": float(seed_df["trigger_rate"].mean()) if not seed_df.empty else float("nan"),
        },
        "gate_check": {
            "pooled_p_lt_0_01": bool(pooled["p_value_bootstrap_gt0"] < 0.01),
            "pooled_ci95_not_cross_0": bool(pooled["ci95"][0] > 0.0),
            "risk_ci95_upper_le_alpha_all_seeds": bool((seed_df["violation_ci95_upper"] <= float(args.alpha) + 1e-12).all()),
        },
        "seed_rows": seed_rows,
    }
    seed_df.to_csv(out_dir / "seed_runs.csv", index=False)
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def _write_report(path: Path, summary: dict) -> None:
    lines: list[str] = []
    lines.append("# Step12-R3 Trial Report (v1)")
    lines.append("")
    lines.append("Strict source root: `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/`")
    lines.append("")
    for key in ["K", "I", "J", "L"]:
        stats = summary[key]
        lines.append(f"## Scheme {key} — {stats.get('name', key)}")
        if "pooled" in stats:
            pooled = stats["pooled"]
            lines.append(f"- pooled mean ΔJ: `{pooled['mean_delta_j']:.6f}`")
            lines.append(f"- pooled 95% CI: `[{pooled['ci95'][0]:.6f}, {pooled['ci95'][1]:.6f}]`")
            lines.append(f"- bootstrap p(gt0): `{pooled['p_value_bootstrap_gt0']:.6f}`")
            dec = stats.get("decomposition", {})
            lines.append(f"- route-only mean ΔJ: `{dec.get('mean_delta_j_route_only', float('nan')):.6f}`")
            lines.append(f"- overhead mean: `{dec.get('mean_probe_overhead_norm', float('nan')):.6f}`")
            lines.append(f"- gate: `{stats.get('gate_check', {})}`")
        else:
            lines.append(f"- stats: `{json.dumps(stats, ensure_ascii=False)}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    strict_root = args.strict_phase9_root
    calib_cf = strict_root / "common" / "router_counterfactual_calib.parquet"
    test_cf = strict_root / "common" / "router_counterfactual_test.parquet"
    static_cal = strict_root / "common" / "risk" / "features_calib.parquet"
    static_test = strict_root / "common" / "risk" / "features_test.parquet"
    probe_cal = strict_root / "router_eval" / "common" / "probe_features_calib.parquet"
    probe_test = strict_root / "router_eval" / "common" / "probe_features_test.parquet"

    calib_df = pd.read_parquet(calib_cf).merge(pd.read_parquet(static_cal), on=["sample_name", "difficulty"], how="inner")
    test_df = pd.read_parquet(test_cf).merge(pd.read_parquet(static_test), on=["sample_name", "difficulty"], how="inner")
    fastgeom_cal_pq, fastgeom_test_pq = _make_fastgeom_tables(args, ROOT / "outputs/router_phase28_step12r3_trials_v1")
    fastgeom_cal = pd.read_parquet(fastgeom_cal_pq)
    fastgeom_test = pd.read_parquet(fastgeom_test_pq)
    probe_cal_df = pd.read_parquet(probe_cal)
    probe_test_df = pd.read_parquet(probe_test)

    summary = {}
    summary["K"] = _run_k_dcdr(args, calib_df, test_df, fastgeom_cal, fastgeom_test)
    summary["I"] = _run_i_cgas(args, calib_df, test_df, probe_cal_df, probe_test_df)
    summary["J"] = _run_j_csrr(args, calib_cf, test_cf)
    summary["L"] = _run_l_cssd(args, calib_df, test_df, probe_cal_df, probe_test_df, fastgeom_cal, fastgeom_test)
    summary["runtime_hours"] = float((time.perf_counter() - t0) / 3600.0)

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_report(args.report_md, summary)
    print(f"[step12-r3] summary={args.summary_json}")
    print(f"[step12-r3] report={args.report_md}")


if __name__ == "__main__":
    main()
