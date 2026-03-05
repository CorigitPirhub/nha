from __future__ import annotations

import argparse
import json
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

    # Latency columns.
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


@dataclass(frozen=True)
class Setting:
    name: str
    description: str
    source_dataset: str | None = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase25 generalization: validate portfolio routing under frozen protocol across multiple settings."
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
    p.add_argument("--delta-total", type=float, default=0.05)
    p.add_argument("--calib-train-frac", type=float, default=0.60)
    p.add_argument("--risk-safety-margin", type=float, default=0.005)
    p.add_argument("--tau-grid", type=int, default=31)
    p.add_argument("--tau-mid-include-eps", action="store_true", default=True)
    p.add_argument("--tau-mid-include-small", action="store_true", default=True)
    p.add_argument("--sweep-levels", type=int, default=15)

    p.add_argument(
        "--settings",
        type=str,
        default="mp,csm",
        help="Comma-separated setting names. Supported: mp,csm.",
    )

    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase25_generalization_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase25_generalization_v1.md"))
    p.add_argument("--fig-dir", type=Path, default=Path("paper/figures_router_v7"))
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


def _bootstrap_ci(arr: np.ndarray, n_boot: int, seed: int = 20260303) -> tuple[float, float]:
    if arr.size <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(int(seed))
    n = int(arr.size)
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _bootstrap_p_le0(arr: np.ndarray, n_boot: int, seed: int = 20260303) -> float:
    if arr.size <= 0:
        return 1.0
    rng = np.random.default_rng(int(seed))
    n = int(arr.size)
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    return float(np.mean(means >= 0.0))


def _write_master_report(
    path: Path,
    *,
    summary: dict,
    setting_rows: list[dict],
) -> None:
    lines: list[str] = []
    lines.append("# Phase25 Generalization (v1)")
    lines.append("")
    lines.append("## Summary")
    for k, v in summary.items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Per-setting Gates and Deltas (test, mean over seeds)")
    lines.append(
        "- `best_feasible_*` is the best (min `J_mean`) point in the aligned sweep grid among rows with `risk_hold_all_seeds=True`."
    )
    lines.append("- `selected_*` is the mean of the policy selected by the calibration-time grid search (same logic as Phase23).")
    df = pd.DataFrame(setting_rows)
    lines.append(df.to_markdown(index=False))
    lines.append("")
    lines.append("## Artifacts")
    art = summary.get("artifacts", {})
    for k in sorted(art.keys()):
        lines.append(f"- `{k}`: `{art[k]}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _resolve_settings(raw: str) -> list[Setting]:
    items = [s.strip().lower() for s in str(raw).split(",") if s.strip()]
    out: list[Setting] = []
    for it in items:
        if it == "mp":
            out.append(Setting(name="mp", description="In-distribution MP maps (source_dataset=mp).", source_dataset="mp"))
        elif it == "csm":
            out.append(Setting(name="csm", description="OOD CSM maps (source_dataset=csm).", source_dataset="csm"))
        else:
            raise ValueError(f"Unknown setting: {it} (supported: mp,csm)")
    if not out:
        raise ValueError("Empty settings list.")
    # De-duplicate by name while preserving order.
    seen: set[str] = set()
    dedup: list[Setting] = []
    for s in out:
        if s.name not in seen:
            dedup.append(s)
            seen.add(s.name)
    return dedup


def _run_setting(
    setting: Setting,
    *,
    seeds: list[int],
    calib_all: pd.DataFrame,
    test_all: pd.DataFrame,
    cfg: PortfolioConfig,
    args: argparse.Namespace,
) -> dict:
    calib = calib_all.copy()
    test = test_all.copy()
    if setting.source_dataset is not None:
        calib = calib[calib["source_dataset"].astype(str) == str(setting.source_dataset)].reset_index(drop=True)
        test = test[test["source_dataset"].astype(str) == str(setting.source_dataset)].reset_index(drop=True)
    if len(calib) <= 10 or len(test) <= 10:
        raise RuntimeError(f"Setting {setting.name}: too few samples (calib={len(calib)}, test={len(test)})")

    t_ref, beta = _calibrate_beta(calib)
    x_cal, x_test = _build_xy(calib, test)

    # Baselines (no learning).
    base_rows: list[dict] = []
    base_rows.append({"arm": "always_fast", **_policy_metrics_k3(test, arm=np.full(len(test), "fast"), t_ref=t_ref, beta=beta, protocol=cfg.protocol)})
    base_rows.append({"arm": "always_mid", **_policy_metrics_k3(test, arm=np.full(len(test), "mid"), t_ref=t_ref, beta=beta, protocol=cfg.protocol)})
    base_rows.append({"arm": "always_slow", **_policy_metrics_k3(test, arm=np.full(len(test), "slow"), t_ref=t_ref, beta=beta, protocol=cfg.protocol)})

    # Baseline best single arm under risk budget (use Wilson CI upper).
    feasible = [r for r in base_rows if float(r["violation_rate_ci95_hi"]) <= float(cfg.protocol.alpha) + 1e-12]
    if not feasible:
        feasible = [base_rows[-1]]  # always_slow should always be feasible; keep safe fallback.
    base_best = sorted(feasible, key=lambda r: (float(r["J_mean"]), float(r["avg_latency_ms"]), float(r["violation_rate"])))[0]

    test_cache = _prep_k3_cache(test, t_ref=t_ref, beta=beta, protocol=cfg.protocol)

    # Aligned sweep grid (quantile levels).
    sweep_levels = int(max(args.sweep_levels, 5))
    sweep_q = np.linspace(0.0, 1.0, int(sweep_levels), dtype=np.float64)
    n_fast = int(sweep_q.size + 2)  # -inf + q-levels + +inf
    n_mid = int(sweep_q.size + 1)  # q-levels + +inf
    sweep_sum_latency = np.zeros((n_fast, n_mid), dtype=np.float64)
    sweep_sum_risk = np.zeros((n_fast, n_mid), dtype=np.float64)
    sweep_sum_j = np.zeros((n_fast, n_mid), dtype=np.float64)
    sweep_hold_all_seeds = np.ones((n_fast, n_mid), dtype=bool)

    delta_fast = float(cfg.delta_total) / 2.0
    delta_mid = float(cfg.delta_total) / 2.0
    risk_target = float(cfg.protocol.alpha) - float(args.risk_safety_margin)

    seed_rows: list[dict] = []
    picked_metrics: list[dict] = []
    for seed in seeds:
        # Split calib into train/cal for valid split conformal.
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
        # Include sentinel extremes so the selector can represent "disable fast" / "disable mid" exactly.
        tau_fast_grid = sorted(set(tau_fast_grid + [-float("inf")]))
        tau_mid_grid = sorted(set(tau_mid_grid + [-float("inf")]))
        if bool(args.tau_mid_include_eps):
            tau_fast_grid = sorted(set(tau_fast_grid + [float(cfg.protocol.epsilon_rel)]))
            tau_mid_grid = sorted(set(tau_mid_grid + [float(cfg.protocol.epsilon_rel)]))
        if bool(args.tau_mid_include_small):
            tau_mid_grid = sorted(set(tau_mid_grid + [0.0, float(cfg.protocol.epsilon_rel) * 0.5]))
        tau_mid_grid = sorted(set(tau_mid_grid + [float("inf")]))

        # Baseline on same calib split (for latency-aware tie-breaking).
        base_mid_cal = _policy_basic_metrics_k3(cal_cache, arm=np.full(len(calib_cal), "mid"), protocol=cfg.protocol)
        base_mid_cal_lat = float(base_mid_cal["avg_latency_ms"])

        best = None
        best_metrics = None
        best_lat_ok = None
        best_lat_ok_metrics = None

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
                    best_metrics = {"tau_fast": float(tau_fast), "tau_mid": float(tau_mid), "calib_metrics": m}
                if float(m["avg_latency_ms"]) <= base_mid_cal_lat + 1e-12:
                    if best_lat_ok is None or key < best_lat_ok:
                        best_lat_ok = key
                        best_lat_ok_metrics = {
                            "tau_fast": float(tau_fast),
                            "tau_mid": float(tau_mid),
                            "calib_metrics": m,
                            "latency_constraint": f"avg_latency_ms <= {base_mid_cal_lat:.6f} (always_mid on calib_split)",
                        }

        if best_lat_ok_metrics is not None:
            best_metrics = best_lat_ok_metrics

        if best_metrics is None:
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

        groups_te = test[cfg.group_col].astype(str).to_numpy()
        yhat_fast_te = np.clip(gbr_fast.predict(x_test).astype(np.float64), 0.0, None)
        yhat_mid_te = np.clip(gbr_mid.predict(x_test).astype(np.float64), 0.0, None)
        u_fast_te = yhat_fast_te + np.array([q_fast.get(str(g), 0.0) for g in groups_te], dtype=np.float64)
        u_mid_te = yhat_mid_te + np.array([q_mid.get(str(g), 0.0) for g in groups_te], dtype=np.float64)

        tau_fast = float(best_metrics["tau_fast"])
        tau_mid = float(best_metrics["tau_mid"])

        is_fast = u_fast_te <= tau_fast
        is_mid = (~is_fast) & (u_mid_te <= tau_mid)
        arm_te = np.where(is_fast, "fast", np.where(is_mid, "mid", "slow")).astype(object)
        test_metrics = _policy_metrics_k3(test, arm=arm_te, t_ref=t_ref, beta=beta, protocol=cfg.protocol)
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
            }
        )
        picked_metrics.append({"seed": int(seed)} | test_metrics)

        # Sweep grid on test using tau quantile levels from calib split.
        tau_fast_sweep = np.quantile(u_fast_cal, sweep_q)
        tau_mid_sweep = np.quantile(u_mid_cal, sweep_q)
        tau_fast_vals = np.concatenate(
            [np.array([-float("inf")], dtype=np.float64), tau_fast_sweep.astype(np.float64), np.array([float("inf")], dtype=np.float64)]
        )
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
                sweep_hold_all_seeds[i, j] = bool(
                    sweep_hold_all_seeds[i, j]
                    and (float(m_s["violation_rate_ci95_hi"]) <= float(cfg.protocol.alpha) + 1e-12)
                )

    seed_df = pd.DataFrame(seed_rows)
    picked_df = pd.DataFrame(picked_metrics)

    # Sweep mean over seeds (aligned by quantile level indices).
    sweep_mean_latency = sweep_sum_latency / float(len(seeds))
    sweep_mean_risk = sweep_sum_risk / float(len(seeds))
    sweep_mean_j = sweep_sum_j / float(len(seeds))

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
                    "risk_hold_all_seeds": bool(sweep_hold_all_seeds[i, j]),
                }
            )
    sweep_df = pd.DataFrame(sweep_rows)

    # Deltas vs baseline best feasible single arm.
    dJ = picked_df["J_mean"].to_numpy(dtype=np.float64) - float(base_best["J_mean"])
    dLat = picked_df["avg_latency_ms"].to_numpy(dtype=np.float64) - float(base_best["avg_latency_ms"])
    dRisk = picked_df["violation_rate"].to_numpy(dtype=np.float64) - float(base_best["violation_rate"])
    boot_n = int(args.bootstrap_n)
    ci_dJ = _bootstrap_ci(dJ, boot_n)
    ci_dLat = _bootstrap_ci(dLat, boot_n)
    ci_dRisk = _bootstrap_ci(dRisk, boot_n)
    pJ = _bootstrap_p_le0(dJ, boot_n)
    pLat = _bootstrap_p_le0(dLat, boot_n)
    pRisk = _bootstrap_p_le0(dRisk, boot_n)
    try:
        wJ = float(wilcoxon(dJ).pvalue) if len(dJ) >= 3 else float("nan")
    except Exception:
        wJ = float("nan")

    risk_constraint_hold_all_seeds = bool(
        np.all(seed_df["test_violation_ci95_hi"].to_numpy(dtype=np.float64) <= float(cfg.protocol.alpha) + 1e-12)
    )

    # Trend check 1 (strict): exists a risk-feasible sweep point that strictly dominates baseline best in (J, latency)
    # while not worse in empirical violation rate.
    sweep_feas = sweep_df[sweep_df["risk_hold_all_seeds"].astype(bool)].copy()
    strict_dom_mask = (
        (sweep_feas["violation_rate"].to_numpy(dtype=np.float64) <= float(base_best["violation_rate"]) + 1e-12)
        & (sweep_feas["latency_ms"].to_numpy(dtype=np.float64) <= float(base_best["avg_latency_ms"]) - 1e-9)
        & (sweep_feas["J_mean"].to_numpy(dtype=np.float64) <= float(base_best["J_mean"]) - 1e-9)
    )
    pareto_strict_improve_vs_best = bool(np.any(strict_dom_mask))

    # Trend check 2 (robust): best feasible J is not worse than baseline best J (up to tiny epsilon).
    j_best_feas = float(sweep_feas["J_mean"].min()) if len(sweep_feas) > 0 else float("inf")
    best_j_not_worse = bool(j_best_feas <= float(base_best["J_mean"]) + 1e-12)

    best_feasible_point = None
    if len(sweep_feas) > 0:
        best_row = sweep_feas.sort_values(["J_mean", "latency_ms", "violation_rate"]).head(1)
        if len(best_row) == 1:
            best_feasible_point = best_row.iloc[0].to_dict()

    setting_gate = {
        "risk_constraint_hold_all_seeds": risk_constraint_hold_all_seeds,
        "pareto_strict_improve_vs_best_single_arm": pareto_strict_improve_vs_best,
        "best_feasible_J_not_worse_than_best_single_arm": best_j_not_worse,
    }

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
            }
        )
    table_rows.append(
        {
            "method": "portfolio_router_v1",
            "avg_latency_ms": float(ours_mean["avg_latency_ms"]),
            "violation_rate": float(ours_mean["violation_rate"]),
            "J_mean": float(ours_mean["J_mean"]),
            "oracle_gap": float(ours_mean["oracle_gap"]),
        }
    )
    table_df = pd.DataFrame(table_rows)

    return {
        "setting": {
            "name": setting.name,
            "description": setting.description,
            "num_calib": int(len(calib)),
            "num_test": int(len(test)),
        },
        "t_ref_ms": float(t_ref),
        "beta": float(beta),
        "sweep_best_feasible": best_feasible_point,
        "baseline_best_single_arm": {
            "name": str(base_best["arm"]),
            "avg_latency_ms": float(base_best["avg_latency_ms"]),
            "violation_rate": float(base_best["violation_rate"]),
            "J_mean": float(base_best["J_mean"]),
        },
        "ours_vs_best_single_arm": {
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
        "gate_check": setting_gate,
        "seed_metrics_test": seed_df,
        "sweep_df": sweep_df,
        "paper_table": table_df,
    }


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    seeds = _parse_seeds(args.seeds)
    settings = _resolve_settings(args.settings)
    cfg = PortfolioConfig(protocol=RiskBudgetProtocol(epsilon_rel=float(args.epsilon_rel), alpha=float(args.alpha)), delta_total=float(args.delta_total))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "settings").mkdir(parents=True, exist_ok=True)
    args.fig_dir.mkdir(parents=True, exist_ok=True)

    calib_cf = _read_parquet(args.calib_parquet)
    test_cf = _read_parquet(args.test_parquet)
    feat_cal = _read_parquet(args.static_features_calib)
    feat_te = _read_parquet(args.static_features_test)

    calib_all = calib_cf.merge(feat_cal, on=["sample_name", "difficulty"], how="inner")
    test_all = test_cf.merge(feat_te, on=["sample_name", "difficulty"], how="inner")
    if len(calib_all) != len(calib_cf):
        raise RuntimeError(f"Static feature merge mismatch (calib): {len(calib_all)} vs {len(calib_cf)}")
    if len(test_all) != len(test_cf):
        raise RuntimeError(f"Static feature merge mismatch (test): {len(test_all)} vs {len(test_cf)}")

    # Derived labels for arms.
    calib_all["q_pos_fast"] = np.maximum(calib_all["q_rel"].to_numpy(dtype=np.float64), 0.0)
    calib_all["q_pos_mid"] = np.maximum(calib_all["q_rel_mid"].to_numpy(dtype=np.float64), 0.0)
    test_all["q_pos_fast"] = np.maximum(test_all["q_rel"].to_numpy(dtype=np.float64), 0.0)
    test_all["q_pos_mid"] = np.maximum(test_all["q_rel_mid"].to_numpy(dtype=np.float64), 0.0)

    setting_rows: list[dict] = []
    setting_summaries: dict[str, dict] = {}

    for s in settings:
        rec = _run_setting(s, seeds=seeds, calib_all=calib_all, test_all=test_all, cfg=cfg, args=args)

        out_setting = args.out_dir / "settings" / s.name
        (out_setting / "common").mkdir(parents=True, exist_ok=True)

        seed_df: pd.DataFrame = rec.pop("seed_metrics_test")
        sweep_df: pd.DataFrame = rec.pop("sweep_df")
        table_df: pd.DataFrame = rec.pop("paper_table")

        seed_csv = out_setting / "common" / "seed_metrics_test.csv"
        sweep_csv = out_setting / "common" / "sweep_grid_mean_over_seeds.csv"
        table_csv = out_setting / "common" / "table_summary.csv"
        seed_df.to_csv(seed_csv, index=False)
        sweep_df.to_csv(sweep_csv, index=False)
        table_df.to_csv(table_csv, index=False)

        # Figure.
        fig_path = args.fig_dir / f"fig_generalization_{s.name}.svg"
        try:
            import matplotlib.pyplot as plt
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Missing dependency: matplotlib") from exc

        base = rec["baseline_best_single_arm"]
        plt.figure(figsize=(6.6, 4.4))
        plot_df = sweep_df[sweep_df["risk_hold_all_seeds"].astype(bool)].copy()
        if len(plot_df) <= 0:
            plot_df = sweep_df.copy()
        sc = plt.scatter(
            plot_df["latency_ms"],
            plot_df["violation_rate"],
            c=plot_df["J_mean"],
            s=26,
            cmap="viridis",
            alpha=0.75,
            label=f"sweep (mean, {s.name})",
        )
        plt.colorbar(sc, label="J_mean")
        plt.scatter([float(base["avg_latency_ms"])], [float(base["violation_rate"])], s=45, label=f"best_single_arm={base['name']}")
        ours_row = table_df[table_df["method"] == "portfolio_router_v1"].iloc[0]
        plt.scatter([float(ours_row["avg_latency_ms"])], [float(ours_row["violation_rate"])], s=65, marker="x", linewidths=2.0, label="selected_policy (mean)")
        plt.axhline(float(cfg.protocol.alpha), color="red", linestyle="--", linewidth=1.0, label="alpha")
        plt.xlabel("Average Latency (ms)")
        plt.ylabel("Violation Rate")
        plt.title(f"Generalization Tradeoff — {s.name}")
        plt.grid(alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_path, format="svg")
        plt.close()

        rec["artifacts"] = {
            "out_setting_dir": str(out_setting),
            "seed_csv": str(seed_csv),
            "sweep_csv": str(sweep_csv),
            "table_csv": str(table_csv),
            "fig_path": str(fig_path),
        }
        (out_setting / "stats.json").write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")

        gate = rec["gate_check"]
        deltas = rec["ours_vs_best_single_arm"]
        base = rec["baseline_best_single_arm"]
        ours_row = table_df[table_df["method"] == "portfolio_router_v1"].iloc[0].to_dict()
        best_feas = rec.get("sweep_best_feasible") or {}
        setting_rows.append(
            {
                "setting": s.name,
                "num_test": rec["setting"]["num_test"],
                "baseline_best_arm": base["name"],
                "baseline_J_mean": float(base["J_mean"]),
                "baseline_latency_ms": float(base["avg_latency_ms"]),
                "baseline_violation_rate": float(base["violation_rate"]),
                "selected_J_mean": float(ours_row["J_mean"]),
                "selected_latency_ms": float(ours_row["avg_latency_ms"]),
                "selected_violation_rate": float(ours_row["violation_rate"]),
                "best_feasible_J_mean": float(best_feas.get("J_mean", float("nan"))),
                "best_feasible_latency_ms": float(best_feas.get("latency_ms", float("nan"))),
                "best_feasible_violation_rate": float(best_feas.get("violation_rate", float("nan"))),
                "risk_hold_all_seeds": bool(gate["risk_constraint_hold_all_seeds"]),
                "pareto_strict": bool(gate["pareto_strict_improve_vs_best_single_arm"]),
                "bestJ_not_worse": bool(gate["best_feasible_J_not_worse_than_best_single_arm"]),
                "dJ_mean": float(deltas["dJ_mean"]),
                "dLatency_mean_ms": float(deltas["dLatency_mean_ms"]),
                "dRisk_mean": float(deltas["dRisk_mean"]),
            }
        )
        setting_summaries[s.name] = rec

    # Master gates.
    new_settings_ge_2 = bool(len(settings) >= 2)
    risk_control_holds_in_new_settings = bool(
        all(bool(setting_summaries[s.name]["gate_check"]["risk_constraint_hold_all_seeds"]) for s in settings)
    )
    trend_consistent = bool(
        all(
            bool(setting_summaries[s.name]["gate_check"]["best_feasible_J_not_worse_than_best_single_arm"])
            for s in settings
        )
    )

    gate = {
        "new_settings_ge_2": new_settings_ge_2,
        "risk_control_holds_in_new_settings": risk_control_holds_in_new_settings,
        "trend_consistent": trend_consistent,
    }

    summary = {
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": seeds,
        "settings": [s.name for s in settings],
        "gate_check": gate,
        "artifacts": {
            "out_dir": str(args.out_dir),
            "report_md": str(args.report_md),
            "fig_dir": str(args.fig_dir),
            "per_setting_stats": {k: v["artifacts"]["out_setting_dir"] for k, v in setting_summaries.items()},
        },
    }

    stats_path = args.out_dir / "stats.json"
    stats_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    # Report.
    _write_master_report(args.report_md, summary=summary, setting_rows=setting_rows)

    if bool(args.enforce_gate):
        for k, v in gate.items():
            if not bool(v):
                raise RuntimeError(f"Phase25 gate failed: {k}={v}; see {stats_path}")

    print(f"[phase25] done in {(time.perf_counter() - t0):.3f}s")


if __name__ == "__main__":
    main()
