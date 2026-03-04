from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.ensemble import GradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.router_method_core import RiskBudgetProtocol, split_conformal_upper_q, wilson_ci95


@dataclass(frozen=True)
class PortfolioConfig:
    protocol: RiskBudgetProtocol = RiskBudgetProtocol()
    group_col: str = "difficulty"
    group_values: tuple[str, ...] = ("easy", "medium", "hard")

    # Multi-arm definition (slow is reference).
    qpos_fast_col: str = "q_pos_fast"
    qpos_mid_col: str = "q_pos_mid"
    qpos_slow_col: str = "q_pos_slow"

    t_fast_col: str = "T_fast_ms"
    t_mid_col: str = "T_mid_ms"
    t_slow_col: str = "T_slow_ms"

    # Conformal miscoverage allocation (union bound across arms).
    delta_total: float = 0.05

    # Models.
    gbr_n_estimators: int = 600
    gbr_lr: float = 0.04
    gbr_max_depth: int = 3
    gbr_subsample: float = 0.9


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase23 portfolio router: extend dual-path routing to K>=3 arms under frozen protocol semantics."
    )
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")
    p.add_argument(
        "--calib-parquet",
        type=Path,
        default=Path("outputs/router_phase23_portfolio_v1/common/router_counterfactual_calib_k3_midnet.parquet"),
    )
    p.add_argument(
        "--test-parquet",
        type=Path,
        default=Path("outputs/router_phase23_portfolio_v1/common/router_counterfactual_test_k3_midnet.parquet"),
    )
    p.add_argument(
        "--static-features-calib",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/common/risk/features_calib.parquet"),
    )
    p.add_argument(
        "--static-features-test",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/common/risk/features_test.parquet"),
    )
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--delta-total", type=float, default=0.05, help="Total miscoverage budget for simultaneous conformal bounds.")
    p.add_argument(
        "--calib-train-frac",
        type=float,
        default=0.60,
        help="Fraction of calib split used to fit predictors; the remainder is used for split conformal calibration + tau search.",
    )
    p.add_argument(
        "--risk-safety-margin",
        type=float,
        default=0.005,
        help="Extra safety margin when selecting tau on calib: require Wilson CI upper <= (alpha - margin).",
    )
    p.add_argument("--tau-grid", type=int, default=31, help="Number of quantile grid points per tau (fast/mid).")
    p.add_argument("--tau-mid-include-eps", action="store_true", default=True)
    p.add_argument("--tau-mid-include-small", action="store_true", default=True, help="Include stricter tau_mid candidates < eps to force slow on some cases.")
    p.add_argument("--sweep-levels", type=int, default=15, help="Number of quantile levels per tau for the aligned sweep grid (used for Pareto check + figure).")
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase23_portfolio_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase23_portfolio_v1.md"))
    p.add_argument("--table-csv", type=Path, default=Path("paper/tables_router_v7/table_phase23_portfolio.csv"))
    p.add_argument("--fig-path", type=Path, default=Path("paper/figures_router_v7/fig_portfolio_tradeoff.svg"))
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument("--enforce-gate", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def _parse_seeds(raw: str) -> list[int]:
    out: list[int] = []
    for tok in str(raw).split(","):
        tok = tok.strip()
        if tok:
            out.append(int(tok))
    if not out:
        raise ValueError("Empty seed list.")
    return out


def _read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def _align_dummies(x_ref: pd.DataFrame, x_new: pd.DataFrame) -> pd.DataFrame:
    return x_new.reindex(columns=x_ref.columns, fill_value=0)


def _build_xy(calib_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Use only cheap map/query features + categorical dataset identifiers.
    feat_num = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "ood_family",
    ]
    feat_cat = ["difficulty", "source_dataset", "scenario", "map_id"]
    x_cal = pd.get_dummies(calib_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_test = pd.get_dummies(test_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_test = _align_dummies(x_cal, x_test)
    return x_cal, x_test


def _calibrate_beta(calib_df: pd.DataFrame, *, beta_cap: float = 200.0) -> tuple[float, float]:
    # Keep consistent with scripts/run_router_risk_v1.py.
    t_ref = float(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(calib_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    non_zero = q_pos[q_pos > 1e-9]
    if non_zero.size == 0:
        beta = 1.0
    else:
        q_pos_median = float(np.median(non_zero))
        t_norm_median = float(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)))
        beta = float(t_norm_median / max(q_pos_median, 1e-9))
    beta = float(np.clip(beta, 1e-3, max(beta_cap, 1e-3)))
    return t_ref, beta


def _policy_metrics_k3(
    df: pd.DataFrame,
    *,
    arm: np.ndarray,  # {"fast","mid","slow"}
    t_ref: float,
    beta: float,
    protocol: RiskBudgetProtocol,
) -> dict[str, float]:
    arm = np.asarray(arm).astype(str)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_mid = df["T_mid_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)

    l_slow = df["L_slow"].to_numpy(dtype=np.float64)
    l_fast = df["L_fast"].to_numpy(dtype=np.float64)
    l_mid = df["L_mid"].to_numpy(dtype=np.float64)

    t = np.where(arm == "fast", t_fast, np.where(arm == "mid", t_mid, t_slow))
    l = np.where(arm == "fast", l_fast, np.where(arm == "mid", l_mid, l_slow))
    drel = (l - l_slow) / np.maximum(l_slow, 1e-6)
    drel_pos = np.maximum(drel, 0.0)

    vio = (arm != "slow") & (drel > float(protocol.epsilon_rel))
    k = int(np.sum(vio))
    n = int(len(df))
    ci_lo, ci_hi = wilson_ci95(k, n, alpha=float(protocol.alpha))

    j = (t / max(float(t_ref), 1e-9)) + float(beta) * drel_pos
    j_oracle = np.minimum.reduce(
        [
            (t_fast / max(float(t_ref), 1e-9)) + float(beta) * np.maximum((l_fast - l_slow) / np.maximum(l_slow, 1e-6), 0.0),
            (t_mid / max(float(t_ref), 1e-9)) + float(beta) * np.maximum((l_mid - l_slow) / np.maximum(l_slow, 1e-6), 0.0),
            (t_slow / max(float(t_ref), 1e-9)),
        ]
    )
    og = (float(np.mean(j)) - float(np.mean(j_oracle))) / max(abs(float(np.mean(j_oracle))), 1e-9)

    return {
        "num_cases": float(n),
        "ratio_fast": float(np.mean(arm == "fast")),
        "ratio_mid": float(np.mean(arm == "mid")),
        "ratio_slow": float(np.mean(arm == "slow")),
        "avg_latency_ms": float(np.mean(t)),
        "avg_delta_l_rel": float(np.mean(drel)),
        "violation_rate": float(np.mean(vio)),
        "violation_rate_ci95_lo": float(ci_lo),
        "violation_rate_ci95_hi": float(ci_hi),
        "J_mean": float(np.mean(j)),
        "oracle_gap": float(og),
    }


@dataclass(frozen=True)
class _K3Cache:
    t_fast: np.ndarray
    t_mid: np.ndarray
    t_slow: np.ndarray
    j_fast: np.ndarray
    j_mid: np.ndarray
    j_slow: np.ndarray
    vio_fast: np.ndarray
    vio_mid: np.ndarray


def _prep_k3_cache(df: pd.DataFrame, *, t_ref: float, beta: float, protocol: RiskBudgetProtocol) -> _K3Cache:
    t_ref = float(max(float(t_ref), 1e-9))
    beta = float(beta)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_mid = df["T_mid_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)

    l_slow = df["L_slow"].to_numpy(dtype=np.float64)
    drel_fast = (df["L_fast"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)
    drel_mid = (df["L_mid"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)

    j_fast = (t_fast / t_ref) + beta * np.maximum(drel_fast, 0.0)
    j_mid = (t_mid / t_ref) + beta * np.maximum(drel_mid, 0.0)
    j_slow = t_slow / t_ref

    vio_fast = drel_fast > float(protocol.epsilon_rel)
    vio_mid = drel_mid > float(protocol.epsilon_rel)

    return _K3Cache(
        t_fast=t_fast.astype(np.float64),
        t_mid=t_mid.astype(np.float64),
        t_slow=t_slow.astype(np.float64),
        j_fast=j_fast.astype(np.float64),
        j_mid=j_mid.astype(np.float64),
        j_slow=j_slow.astype(np.float64),
        vio_fast=vio_fast.astype(bool),
        vio_mid=vio_mid.astype(bool),
    )


def _policy_basic_metrics_k3(cache: _K3Cache, *, arm: np.ndarray, protocol: RiskBudgetProtocol) -> dict[str, float]:
    arm = np.asarray(arm).astype(str)
    is_fast = arm == "fast"
    is_mid = arm == "mid"
    t = np.where(is_fast, cache.t_fast, np.where(is_mid, cache.t_mid, cache.t_slow))
    j = np.where(is_fast, cache.j_fast, np.where(is_mid, cache.j_mid, cache.j_slow))
    vio = (is_fast & cache.vio_fast) | (is_mid & cache.vio_mid)

    k = int(np.sum(vio))
    n = int(vio.size)
    _, ci_hi = wilson_ci95(k, n, alpha=float(protocol.alpha))
    return {
        "num_cases": float(n),
        "ratio_fast": float(np.mean(is_fast)),
        "ratio_mid": float(np.mean(is_mid)),
        "ratio_slow": float(1.0 - float(np.mean(is_fast)) - float(np.mean(is_mid))),
        "avg_latency_ms": float(np.mean(t)),
        "violation_rate": float(np.mean(vio)),
        "violation_rate_ci95_hi": float(ci_hi),
        "J_mean": float(np.mean(j)),
    }


def _bootstrap_ci(arr: np.ndarray, n_boot: int, seed: int = 20260302) -> tuple[float, float]:
    if arr.size <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(int(seed))
    n = int(arr.size)
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _bootstrap_p_le0(arr: np.ndarray, n_boot: int, seed: int = 20260302) -> float:
    # One-sided p-value for improvement: H1(mean(arr) < 0), where arr = (metric_policy - metric_baseline).
    if arr.size <= 0:
        return 1.0
    rng = np.random.default_rng(int(seed))
    n = int(arr.size)
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    return float(np.mean(means >= 0.0))


def _write_report(
    path: Path,
    *,
    summary: dict,
    seed_df: pd.DataFrame,
    sweep_df: pd.DataFrame,
    table_df: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# Phase23 Portfolio Router (v1)")
    lines.append("")
    lines.append("## Summary")
    for k, v in summary.items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Seed Metrics (test)")
    lines.append(seed_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Sweep (top feasible points, mean over seeds, test)")
    lines.append(sweep_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Paper Table (mean over seeds, test)")
    lines.append(table_df.to_markdown(index=False))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _ensure_dirs(paths: list[Path]) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    seeds = _parse_seeds(args.seeds)
    cfg = PortfolioConfig(
        protocol=RiskBudgetProtocol(epsilon_rel=float(args.epsilon_rel), alpha=float(args.alpha)),
        delta_total=float(args.delta_total),
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    _ensure_dirs([args.out_dir / "common", args.out_dir / "seeds"])

    calib_cf = _read_parquet(args.calib_parquet)
    test_cf = _read_parquet(args.test_parquet)
    feat_cal = _read_parquet(args.static_features_calib)
    feat_te = _read_parquet(args.static_features_test)

    calib = calib_cf.merge(feat_cal, on=["sample_name", "difficulty"], how="inner")
    test = test_cf.merge(feat_te, on=["sample_name", "difficulty"], how="inner")
    if len(calib) != len(calib_cf):
        raise RuntimeError(f"Static feature merge mismatch (calib): {len(calib)} vs {len(calib_cf)}")
    if len(test) != len(test_cf):
        raise RuntimeError(f"Static feature merge mismatch (test): {len(test)} vs {len(test_cf)}")

    # Derived labels for arms.
    calib["q_pos_fast"] = np.maximum(calib["q_rel"].to_numpy(dtype=np.float64), 0.0)
    calib["q_pos_mid"] = np.maximum(calib["q_rel_mid"].to_numpy(dtype=np.float64), 0.0)
    calib["q_pos_slow"] = 0.0
    test["q_pos_fast"] = np.maximum(test["q_rel"].to_numpy(dtype=np.float64), 0.0)
    test["q_pos_mid"] = np.maximum(test["q_rel_mid"].to_numpy(dtype=np.float64), 0.0)
    test["q_pos_slow"] = 0.0

    t_ref, beta = _calibrate_beta(calib)

    x_cal, x_test = _build_xy(calib, test)

    # Baselines (no learning).
    base_rows: list[dict] = []
    base_rows.append({"arm": "always_fast", **_policy_metrics_k3(test, arm=np.full(len(test), "fast"), t_ref=t_ref, beta=beta, protocol=cfg.protocol)})
    base_rows.append({"arm": "always_mid", **_policy_metrics_k3(test, arm=np.full(len(test), "mid"), t_ref=t_ref, beta=beta, protocol=cfg.protocol)})
    base_rows.append({"arm": "always_slow", **_policy_metrics_k3(test, arm=np.full(len(test), "slow"), t_ref=t_ref, beta=beta, protocol=cfg.protocol)})

    # Conformal allocation across arms.
    delta_fast = float(cfg.delta_total) / 2.0
    delta_mid = float(cfg.delta_total) / 2.0

    risk_target = float(cfg.protocol.alpha) - float(max(float(args.risk_safety_margin), 0.0))
    risk_target = float(max(risk_target, 0.0))

    seed_rows: list[dict] = []

    # For paper table, keep the final picked per-seed policy metrics.
    picked_metrics: list[dict] = []

    # Aligned sweep grid for tradeoff plotting and Pareto-region checks.
    test_cache = _prep_k3_cache(test, t_ref=t_ref, beta=beta, protocol=cfg.protocol)
    sweep_levels = int(max(args.sweep_levels, 3))
    sweep_q = np.linspace(0.0, 1.0, sweep_levels, dtype=np.float64)
    n_fast_levels = int(sweep_q.size + 2)  # [-inf] + quantiles + [+inf]
    n_mid_levels = int(sweep_q.size + 1)  # quantiles + [+inf]

    sweep_sum_latency = np.zeros((n_fast_levels, n_mid_levels), dtype=np.float64)
    sweep_sum_risk = np.zeros((n_fast_levels, n_mid_levels), dtype=np.float64)
    sweep_sum_j = np.zeros((n_fast_levels, n_mid_levels), dtype=np.float64)
    sweep_sum_ratio_fast = np.zeros((n_fast_levels, n_mid_levels), dtype=np.float64)
    sweep_sum_ratio_mid = np.zeros((n_fast_levels, n_mid_levels), dtype=np.float64)
    sweep_sum_ratio_slow = np.zeros((n_fast_levels, n_mid_levels), dtype=np.float64)
    sweep_hold_all_seeds = np.ones((n_fast_levels, n_mid_levels), dtype=bool)

    for seed in seeds:
        out_seed = args.out_dir / "seeds" / f"seed_{seed}"
        _ensure_dirs([out_seed])

        # Split calib into train/cal for valid split conformal (avoid training on calibration residuals).
        n_all = int(len(calib))
        train_frac = float(np.clip(float(args.calib_train_frac), 0.1, 0.9))
        n_train = int(round(train_frac * n_all))
        n_train = int(np.clip(n_train, 1, max(n_all - 1, 1)))
        rng = np.random.default_rng(int(seed))
        perm = rng.permutation(n_all)
        ids_tr = perm[:n_train]
        ids_cal = perm[n_train:]

        calib_tr = calib.iloc[ids_tr].reset_index(drop=True)
        calib_cal = calib.iloc[ids_cal].reset_index(drop=True)
        x_tr = x_cal.iloc[ids_tr].reset_index(drop=True)
        x_cal_split = x_cal.iloc[ids_cal].reset_index(drop=True)
        cal_cache = _prep_k3_cache(calib_cal, t_ref=t_ref, beta=beta, protocol=cfg.protocol)

        # Fit q_pos regressors.
        gbr_fast = GradientBoostingRegressor(
            n_estimators=int(cfg.gbr_n_estimators),
            learning_rate=float(cfg.gbr_lr),
            max_depth=int(cfg.gbr_max_depth),
            subsample=float(cfg.gbr_subsample),
            random_state=int(seed),
        )
        gbr_mid = GradientBoostingRegressor(
            n_estimators=int(cfg.gbr_n_estimators),
            learning_rate=float(cfg.gbr_lr),
            max_depth=int(cfg.gbr_max_depth),
            subsample=float(cfg.gbr_subsample),
            random_state=int(seed + 101),
        )
        y_fast_all = calib[cfg.qpos_fast_col].to_numpy(dtype=np.float64)
        y_mid_all = calib[cfg.qpos_mid_col].to_numpy(dtype=np.float64)
        y_fast_tr = y_fast_all[ids_tr]
        y_mid_tr = y_mid_all[ids_tr]
        y_fast_cal = y_fast_all[ids_cal]
        y_mid_cal = y_mid_all[ids_cal]

        gbr_fast.fit(x_tr, y_fast_tr)
        gbr_mid.fit(x_tr, y_mid_tr)

        yhat_fast_cal = np.clip(gbr_fast.predict(x_cal_split).astype(np.float64), 0.0, None)
        yhat_mid_cal = np.clip(gbr_mid.predict(x_cal_split).astype(np.float64), 0.0, None)

        # Split conformal offsets per group.
        groups = calib_cal[cfg.group_col].astype(str).to_numpy()
        q_fast: dict[str, float] = {}
        q_mid: dict[str, float] = {}
        for g in cfg.group_values:
            mask = groups == str(g)
            if int(np.sum(mask)) <= 0:
                q_fast[str(g)] = 0.0
                q_mid[str(g)] = 0.0
                continue
            q_fast[str(g)] = float(
                split_conformal_upper_q(y_cal=y_fast_cal[mask], yhat_cal=yhat_fast_cal[mask], alpha=float(delta_fast))
            )
            q_mid[str(g)] = float(
                split_conformal_upper_q(y_cal=y_mid_cal[mask], yhat_cal=yhat_mid_cal[mask], alpha=float(delta_mid))
            )

        u_fast_cal = yhat_fast_cal + np.array([q_fast.get(str(g), 0.0) for g in groups], dtype=np.float64)
        u_mid_cal = yhat_mid_cal + np.array([q_mid.get(str(g), 0.0) for g in groups], dtype=np.float64)

        # Candidate tau grids from quantiles (plus eps and +inf).
        n_grid = int(max(args.tau_grid, 5))
        q_grid = np.linspace(0.0, 1.0, n_grid)
        tau_fast_grid = sorted(set(float(np.quantile(u_fast_cal, q)) for q in q_grid))
        tau_mid_grid = sorted(set(float(np.quantile(u_mid_cal, q)) for q in q_grid))
        if bool(args.tau_mid_include_eps):
            tau_fast_grid = sorted(set(tau_fast_grid + [float(cfg.protocol.epsilon_rel)]))
            tau_mid_grid = sorted(set(tau_mid_grid + [float(cfg.protocol.epsilon_rel)]))
        if bool(args.tau_mid_include_small):
            tau_mid_grid = sorted(set(tau_mid_grid + [0.0, float(cfg.protocol.epsilon_rel) * 0.5]))
        # A permissive option to essentially disable slow fallback.
        tau_mid_grid = sorted(set(tau_mid_grid + [float("inf")]))

        # Baseline on the same calib split (for latency-aware tie-breaking).
        base_mid_cal = _policy_basic_metrics_k3(cal_cache, arm=np.full(len(calib_cal), "mid"), protocol=cfg.protocol)
        base_mid_cal_lat = float(base_mid_cal["avg_latency_ms"])

        best = None
        best_metrics = None
        best_lat_ok = None
        best_lat_ok_metrics = None

        # Grid search on calib for a risk-feasible operating point; optimize J then latency.
        for tau_fast in tau_fast_grid:
            is_fast = u_fast_cal <= float(tau_fast)
            for tau_mid in tau_mid_grid:
                is_mid = (~is_fast) & (u_mid_cal <= float(tau_mid))
                arm = np.where(is_fast, "fast", np.where(is_mid, "mid", "slow")).astype(object)
                m = _policy_basic_metrics_k3(cal_cache, arm=arm, protocol=cfg.protocol)
                risk_ok = bool(float(m["violation_rate_ci95_hi"]) <= float(risk_target) + 1e-12)
                if not risk_ok:
                    continue
                key = (float(m["J_mean"]), float(m["avg_latency_ms"]), float(m["violation_rate"]))
                if best is None or key < best:
                    best = key
                    best_metrics = {
                        "tau_fast": float(tau_fast),
                        "tau_mid": float(tau_mid),
                        "calib_metrics": m,
                    }
                # Prefer points that are no slower than always_mid on calib.
                if float(m["avg_latency_ms"]) <= base_mid_cal_lat + 1e-12:
                    if best_lat_ok is None or key < best_lat_ok:
                        best_lat_ok = key
                        best_lat_ok_metrics = {
                            "tau_fast": float(tau_fast),
                            "tau_mid": float(tau_mid),
                            "calib_metrics": m,
                            "latency_constraint": f"avg_latency_ms <= {base_mid_cal_lat:.6f} (always_mid on calib_split)",
                        }

        # Prefer a risk-feasible point that is not slower than always_mid on calib.
        if best_lat_ok_metrics is not None:
            best_metrics = best_lat_ok_metrics

        if best_metrics is None:
            # Fallback: pick the safest (lowest risk upper) point and record it.
            safest = None
            safest_rec = None
            for tau_fast in tau_fast_grid:
                is_fast = u_fast_cal <= float(tau_fast)
                for tau_mid in tau_mid_grid:
                    is_mid = (~is_fast) & (u_mid_cal <= float(tau_mid))
                    arm = np.where(is_fast, "fast", np.where(is_mid, "mid", "slow")).astype(object)
                    m = _policy_basic_metrics_k3(cal_cache, arm=arm, protocol=cfg.protocol)
                    key = (float(m["violation_rate_ci95_hi"]), float(m["J_mean"]), float(m["avg_latency_ms"]))
                    if safest is None or key < safest:
                        safest = key
                        safest_rec = (float(tau_fast), float(tau_mid), m)
            if safest_rec is None:
                raise RuntimeError("Empty tau grid search.")
            best_metrics = {
                "tau_fast": float(safest_rec[0]),
                "tau_mid": float(safest_rec[1]),
                "calib_metrics": safest_rec[2],
                "fallback_used": True,
            }

        # Apply to test.
        groups_te = test[cfg.group_col].astype(str).to_numpy()
        yhat_fast_te = np.clip(gbr_fast.predict(x_test).astype(np.float64), 0.0, None)
        yhat_mid_te = np.clip(gbr_mid.predict(x_test).astype(np.float64), 0.0, None)
        u_fast_te = yhat_fast_te + np.array([q_fast.get(str(g), 0.0) for g in groups_te], dtype=np.float64)
        u_mid_te = yhat_mid_te + np.array([q_mid.get(str(g), 0.0) for g in groups_te], dtype=np.float64)

        tau_fast = float(best_metrics["tau_fast"])
        tau_mid = float(best_metrics["tau_mid"])

        # Save calib-split decisions for theory validation (shift bounds / selection diagnostics).
        is_fast_cal = u_fast_cal <= tau_fast
        is_mid_cal = (~is_fast_cal) & (u_mid_cal <= tau_mid)
        arm_cal = np.where(is_fast_cal, "fast", np.where(is_mid_cal, "mid", "slow")).astype(object)
        cal_dec = pd.DataFrame(
            {
                "sample_name": calib_cal["sample_name"].astype(str),
                "difficulty": calib_cal["difficulty"].astype(str),
                "map_id": calib_cal["map_id"].astype(str),
                "ood_family": calib_cal["ood_family"].astype(int),
                "arm": arm_cal.astype(str),
                "u_fast": u_fast_cal,
                "u_mid": u_mid_cal,
                "q_rel_fast": calib_cal["q_rel"].to_numpy(dtype=np.float64),
                "q_rel_mid": calib_cal["q_rel_mid"].to_numpy(dtype=np.float64),
            }
        )
        cal_dec_path = out_seed / "calib_decisions.parquet"
        cal_dec.to_parquet(cal_dec_path, index=False)

        is_fast = u_fast_te <= tau_fast
        is_mid = (~is_fast) & (u_mid_te <= tau_mid)
        arm_te = np.where(is_fast, "fast", np.where(is_mid, "mid", "slow")).astype(object)

        test_metrics = _policy_metrics_k3(test, arm=arm_te, t_ref=t_ref, beta=beta, protocol=cfg.protocol)

        # Save per-sample decisions (for theory v3 checks).
        dec = pd.DataFrame(
            {
                "sample_name": test["sample_name"].astype(str),
                "difficulty": test["difficulty"].astype(str),
                "map_id": test["map_id"].astype(str),
                "ood_family": test["ood_family"].astype(int),
                "arm": arm_te.astype(str),
                "u_fast": u_fast_te,
                "u_mid": u_mid_te,
                "q_pos_fast": test[cfg.qpos_fast_col].to_numpy(dtype=np.float64),
                "q_pos_mid": test[cfg.qpos_mid_col].to_numpy(dtype=np.float64),
                "q_rel_fast": test["q_rel"].to_numpy(dtype=np.float64),
                "q_rel_mid": test["q_rel_mid"].to_numpy(dtype=np.float64),
            }
        )
        dec_path = out_seed / "test_decisions.parquet"
        dec.to_parquet(dec_path, index=False)

        seed_rows.append(
            {
                "seed": int(seed),
                "tau_fast": tau_fast,
                "tau_mid": tau_mid,
                "test_J_mean": float(test_metrics["J_mean"]),
                "test_latency_ms": float(test_metrics["avg_latency_ms"]),
                "test_violation_rate": float(test_metrics["violation_rate"]),
                "test_violation_ci95_hi": float(test_metrics["violation_rate_ci95_hi"]),
                "ratio_fast": float(test_metrics["ratio_fast"]),
                "ratio_mid": float(test_metrics["ratio_mid"]),
                "ratio_slow": float(test_metrics["ratio_slow"]),
                "calib_decisions_parquet": str(cal_dec_path),
                "decisions_parquet": str(dec_path),
            }
        )
        picked_metrics.append({"seed": int(seed)} | test_metrics)

        # Aligned sweep grid (quantile levels) for portfolio tradeoff + Pareto checks.
        tau_fast_sweep = np.quantile(u_fast_cal, sweep_q)
        tau_mid_sweep = np.quantile(u_mid_cal, sweep_q)
        tau_fast_vals = np.concatenate([np.array([-float("inf")], dtype=np.float64), tau_fast_sweep.astype(np.float64), np.array([float("inf")], dtype=np.float64)])
        tau_mid_vals = np.concatenate([tau_mid_sweep.astype(np.float64), np.array([float("inf")], dtype=np.float64)])

        for i, tau_fast_s in enumerate(tau_fast_vals):
            is_fast_s = u_fast_te <= float(tau_fast_s)
            for j, tau_mid_s in enumerate(tau_mid_vals):
                is_mid_s = (~is_fast_s) & (u_mid_te <= float(tau_mid_s))
                arm_s = np.where(is_fast_s, "fast", np.where(is_mid_s, "mid", "slow")).astype(object)
                m_s = _policy_basic_metrics_k3(test_cache, arm=arm_s, protocol=cfg.protocol)
                sweep_sum_latency[i, j] += float(m_s["avg_latency_ms"])
                sweep_sum_risk[i, j] += float(m_s["violation_rate"])
                sweep_sum_j[i, j] += float(m_s["J_mean"])
                sweep_sum_ratio_fast[i, j] += float(m_s["ratio_fast"])
                sweep_sum_ratio_mid[i, j] += float(m_s["ratio_mid"])
                sweep_sum_ratio_slow[i, j] += float(m_s["ratio_slow"])
                sweep_hold_all_seeds[i, j] = bool(sweep_hold_all_seeds[i, j] and (float(m_s["violation_rate_ci95_hi"]) <= float(cfg.protocol.alpha) + 1e-12))

    seed_df = pd.DataFrame(seed_rows)
    picked_df = pd.DataFrame(picked_metrics)

    # Sweep mean over seeds (aligned by quantile level indices, not raw tau values).
    sweep_mean_latency = sweep_sum_latency / float(len(seeds))
    sweep_mean_risk = sweep_sum_risk / float(len(seeds))
    sweep_mean_j = sweep_sum_j / float(len(seeds))
    sweep_mean_ratio_fast = sweep_sum_ratio_fast / float(len(seeds))
    sweep_mean_ratio_mid = sweep_sum_ratio_mid / float(len(seeds))
    sweep_mean_ratio_slow = sweep_sum_ratio_slow / float(len(seeds))

    fast_labels = ["-inf"] + [f"q={q:.3f}" for q in sweep_q.tolist()] + ["+inf"]
    mid_labels = [f"q={q:.3f}" for q in sweep_q.tolist()] + ["+inf"]
    sweep_rows = []
    for i, fl in enumerate(fast_labels):
        for j, ml in enumerate(mid_labels):
            sweep_rows.append(
                {
                    "fast_level": fl,
                    "mid_level": ml,
                    "J_mean": float(sweep_mean_j[i, j]),
                    "latency_ms": float(sweep_mean_latency[i, j]),
                    "violation_rate": float(sweep_mean_risk[i, j]),
                    "ratio_fast": float(sweep_mean_ratio_fast[i, j]),
                    "ratio_mid": float(sweep_mean_ratio_mid[i, j]),
                    "ratio_slow": float(sweep_mean_ratio_slow[i, j]),
                    "risk_hold_all_seeds": bool(sweep_hold_all_seeds[i, j]),
                }
            )
    sweep_df = pd.DataFrame(sweep_rows)

    # Compare vs best single arm under risk budget (typically always_mid).
    base_mid = next(r for r in base_rows if r["arm"] == "always_mid")
    dJ = picked_df["J_mean"].to_numpy(dtype=np.float64) - float(base_mid["J_mean"])
    dLat = picked_df["avg_latency_ms"].to_numpy(dtype=np.float64) - float(base_mid["avg_latency_ms"])
    dRisk = picked_df["violation_rate"].to_numpy(dtype=np.float64) - float(base_mid["violation_rate"])

    # Significance tests across seeds.
    boot_n = int(args.bootstrap_n)
    ci_dJ = _bootstrap_ci(dJ, boot_n)
    ci_dLat = _bootstrap_ci(dLat, boot_n)
    ci_dRisk = _bootstrap_ci(dRisk, boot_n)
    pJ = _bootstrap_p_le0(dJ, boot_n)  # want dJ < 0
    pLat = _bootstrap_p_le0(dLat, boot_n)  # want dLat < 0
    pRisk = _bootstrap_p_le0(dRisk, boot_n)  # want dRisk < 0

    try:
        wJ = float(wilcoxon(dJ).pvalue) if len(dJ) >= 3 else float("nan")
    except Exception:
        wJ = float("nan")

    # Gates.
    num_arms_ge_3 = bool(all(c in test.columns for c in ["L_fast", "L_mid", "L_slow"]))
    risk_constraint_hold_all_seeds = bool(np.all(seed_df["test_violation_ci95_hi"].to_numpy(dtype=np.float64) <= float(cfg.protocol.alpha) + 1e-12))
    # Pareto improvement region vs best arm (always_mid): look for any sweep point that dominates in (risk, latency, J)
    # and is risk-feasible on all seeds (Wilson CI upper <= alpha).
    sweep_dom_mask = (
        sweep_df["risk_hold_all_seeds"].astype(bool)
        & (sweep_df["violation_rate"].to_numpy(dtype=np.float64) <= float(base_mid["violation_rate"]) + 1e-12)
        & (sweep_df["latency_ms"].to_numpy(dtype=np.float64) <= float(base_mid["avg_latency_ms"]) - 1e-9)
        & (sweep_df["J_mean"].to_numpy(dtype=np.float64) <= float(base_mid["J_mean"]) - 1e-9)
    )
    pareto_improve_vs_best_arm = bool(bool(np.any(sweep_dom_mask)))

    gate = {
        "num_arms_ge_3": num_arms_ge_3,
        "risk_constraint_hold_all_seeds": risk_constraint_hold_all_seeds,
        "pareto_improve_vs_best_arm": pareto_improve_vs_best_arm,
    }

    pareto_candidate = None
    if pareto_improve_vs_best_arm:
        pareto_best = sweep_df[sweep_dom_mask].sort_values(["J_mean", "latency_ms", "violation_rate"]).head(1)
        if len(pareto_best) == 1:
            pareto_candidate = pareto_best.iloc[0].to_dict()

    # Table (mean over seeds).
    ours_mean = picked_df[["avg_latency_ms", "violation_rate", "J_mean", "oracle_gap", "ratio_fast", "ratio_mid", "ratio_slow"]].mean().to_dict()
    table_rows = []
    for r in base_rows:
        table_rows.append(
            {
                "method": r["arm"],
                "avg_latency_ms": float(r["avg_latency_ms"]),
                "violation_rate": float(r["violation_rate"]),
                "J_mean": float(r["J_mean"]),
                "oracle_gap": float(r["oracle_gap"]),
                "ratio_fast": float(r["ratio_fast"]),
                "ratio_mid": float(r["ratio_mid"]),
                "ratio_slow": float(r["ratio_slow"]),
            }
        )
    table_rows.append(
        {
            "method": "portfolio_router_v1",
            "avg_latency_ms": float(ours_mean["avg_latency_ms"]),
            "violation_rate": float(ours_mean["violation_rate"]),
            "J_mean": float(ours_mean["J_mean"]),
            "oracle_gap": float(ours_mean["oracle_gap"]),
            "ratio_fast": float(ours_mean["ratio_fast"]),
            "ratio_mid": float(ours_mean["ratio_mid"]),
            "ratio_slow": float(ours_mean["ratio_slow"]),
        }
    )
    table_df = pd.DataFrame(table_rows)

    # Save artifacts.
    args.table_csv.parent.mkdir(parents=True, exist_ok=True)
    table_df.to_csv(args.table_csv, index=False)

    sweep_csv = args.out_dir / "common" / "sweep_grid_mean_over_seeds.csv"
    sweep_csv.parent.mkdir(parents=True, exist_ok=True)
    sweep_df.to_csv(sweep_csv, index=False)

    # Plot sweep curve (mean over seeds).
    args.fig_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Missing dependency: matplotlib") from exc

    plt.figure(figsize=(6.6, 4.4))
    plot_df = sweep_df[sweep_df["risk_hold_all_seeds"].astype(bool)].copy()
    if len(plot_df) <= 0:
        plot_df = sweep_df.copy()
    sc = plt.scatter(plot_df["latency_ms"], plot_df["violation_rate"], c=plot_df["J_mean"], s=26, cmap="viridis", alpha=0.75, label="portfolio sweep (mean)")
    plt.colorbar(sc, label="J_mean")
    plt.scatter([base_mid["avg_latency_ms"]], [base_mid["violation_rate"]], s=40, label="always_mid")
    plt.scatter([table_rows[0]["avg_latency_ms"]], [table_rows[0]["violation_rate"]], s=40, label="always_fast")
    plt.scatter([table_rows[2]["avg_latency_ms"]], [table_rows[2]["violation_rate"]], s=40, label="always_slow")
    plt.scatter([float(ours_mean["avg_latency_ms"])], [float(ours_mean["violation_rate"])], s=55, marker="x", linewidths=2.0, label="selected_policy (mean)")
    if pareto_candidate is not None:
        plt.scatter([float(pareto_candidate["latency_ms"])], [float(pareto_candidate["violation_rate"])], s=70, marker="*", label="pareto_candidate")
    plt.axhline(float(cfg.protocol.alpha), color="red", linestyle="--", linewidth=1.0, label="alpha")
    plt.xlabel("Average Latency (ms)")
    plt.ylabel("Violation Rate")
    plt.title("Portfolio Tradeoff (Latency vs Risk)")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.fig_path, format="svg")
    plt.close()

    summary = {
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": seeds,
        "t_ref_ms": float(t_ref),
        "beta": float(beta),
        "baseline_best_arm": "always_mid",
        "selection": {
            "calib_train_frac": float(args.calib_train_frac),
            "risk_safety_margin": float(args.risk_safety_margin),
            "risk_ci95_hi_max_on_calib": float(risk_target),
        },
        "sweep": {
            "sweep_levels": int(args.sweep_levels),
            "sweep_csv": str(sweep_csv),
            "pareto_candidate": pareto_candidate,
        },
        "ours_vs_always_mid": {
            "dJ_mean": float(np.mean(dJ)),
            "dJ_ci95": [float(ci_dJ[0]), float(ci_dJ[1])],
            "dJ_boot_p_one_sided": float(pJ),
            "dJ_wilcoxon_p": float(wJ),
            "dLatency_mean_ms": float(np.mean(dLat)),
            "dLatency_ci95": [float(ci_dLat[0]), float(ci_dLat[1])],
            "dLatency_boot_p_one_sided": float(pLat),
            "dRisk_mean": float(np.mean(dRisk)),
            "dRisk_ci95": [float(ci_dRisk[0]), float(ci_dRisk[1])],
            "dRisk_boot_p_one_sided": float(pRisk),
        },
        "gate_check": gate,
        "artifacts": {
            "out_dir": str(args.out_dir),
            "report_md": str(args.report_md),
            "table_csv": str(args.table_csv),
            "fig_path": str(args.fig_path),
            "sweep_csv": str(sweep_csv),
        },
    }

    stats_path = args.out_dir / "stats.json"
    stats_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    sweep_feas = sweep_df[sweep_df["risk_hold_all_seeds"].astype(bool)].copy()
    sweep_show = sweep_feas if len(sweep_feas) > 0 else sweep_df
    sweep_show = sweep_show.sort_values(["J_mean", "latency_ms", "violation_rate"]).head(30)

    # Write report.
    _write_report(
        args.report_md,
        summary=summary,
        seed_df=seed_df,
        sweep_df=sweep_show,
        table_df=table_df,
    )

    if bool(args.enforce_gate):
        for k, v in gate.items():
            if not bool(v):
                raise RuntimeError(f"Phase23 gate failed: {k}={v}; see {stats_path}")

    print(f"[phase23] done in {(time.perf_counter() - t0):.3f}s")


if __name__ == "__main__":
    main()
