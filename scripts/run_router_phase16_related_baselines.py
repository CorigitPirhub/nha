from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-16 related-work baseline runner (A/B/C families).")
    p.add_argument("--phase9-root", type=Path, default=Path("outputs/router_phase9_bench_v1"))
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument("--j-improve-target", type=float, default=0.03)
    p.add_argument("--max-risk-delta-pct", type=float, default=0.5)
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase16_related_baselines_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase16_related_baselines_v1.md"))
    p.add_argument("--tables-dir", type=Path, default=Path("paper/tables_router_v5"))
    p.add_argument("--appendix-md", type=Path, default=Path("paper/appendix_related_baselines.md"))
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


STATIC_COLS = [
    "line_block_ratio",
    "local_occ_ratio",
    "global_occ_ratio",
    "distance_ratio",
    "complexity_score",
    "los_clear",
]

PROBE_COLS = [
    "probe_success",
    "probe_expansions",
    "probe_runtime_ms",
    "probe_expansion_ratio",
    "probe_h_start",
    "probe_h_best",
    "probe_h_drop_ratio",
    "probe_progress_per_exp",
    "probe_open_growth",
    "probe_branching",
    "probe_improve_rate",
    "probe_bottleneck_rate",
    "probe_deadend_rate",
]


def _ensure_exists(path: Path, name: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {name}: {path}")


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-z))


def _standardize_fit(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu = np.mean(x, axis=0)
    sig = np.std(x, axis=0)
    sig = np.where(sig > 1e-12, sig, 1.0)
    return mu.astype(np.float64), sig.astype(np.float64)


def _standardize_apply(x: np.ndarray, mu: np.ndarray, sig: np.ndarray) -> np.ndarray:
    return ((x - mu) / sig).astype(np.float64)


def _design_matrix(df: pd.DataFrame, cols: list[str], include_difficulty: bool = True) -> tuple[np.ndarray, list[str]]:
    x = df[cols].to_numpy(dtype=np.float64)
    names = list(cols)
    if include_difficulty:
        diff = df["difficulty"].astype(str).to_numpy()
        is_medium = (diff == "medium").astype(np.float64)[:, None]
        is_hard = (diff == "hard").astype(np.float64)[:, None]
        x = np.concatenate([x, is_medium, is_hard], axis=1)
        names.extend(["is_medium", "is_hard"])
    return x, names


def _ridge_fit(x: np.ndarray, y: np.ndarray, l2: float) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xb = np.concatenate([np.ones((x.shape[0], 1), dtype=np.float64), x], axis=1)
    d = xb.shape[1]
    a = xb.T @ xb
    reg = np.eye(d, dtype=np.float64) * float(l2)
    reg[0, 0] = 0.0
    a = a + reg
    b = xb.T @ y
    try:
        w = np.linalg.solve(a, b)
    except np.linalg.LinAlgError:
        w = np.linalg.lstsq(a, b, rcond=None)[0]
    return w.astype(np.float64)


def _ridge_pred(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    xb = np.concatenate([np.ones((x.shape[0], 1), dtype=np.float64), x], axis=1)
    return (xb @ w).astype(np.float64)


def _logistic_fit(
    x: np.ndarray,
    y: np.ndarray,
    l2: float,
    lr: float = 0.2,
    iters: int = 2000,
) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xb = np.concatenate([np.ones((x.shape[0], 1), dtype=np.float64), x], axis=1)
    w = np.zeros(xb.shape[1], dtype=np.float64)

    n = float(max(xb.shape[0], 1))
    for _ in range(int(max(iters, 1))):
        p = _sigmoid(xb @ w)
        grad = (xb.T @ (p - y)) / n
        grad[1:] += float(l2) * w[1:]
        w -= float(lr) * grad
    return w.astype(np.float64)


def _logistic_pred_prob(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    xb = np.concatenate([np.ones((x.shape[0], 1), dtype=np.float64), x], axis=1)
    return _sigmoid(xb @ w).astype(np.float64)


def _eval_policy(
    df: pd.DataFrame,
    use_fast: np.ndarray,
    t_ref: float,
    beta: float,
    epsilon_rel: float,
) -> dict:
    uf = np.asarray(use_fast, dtype=bool)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
    l_fast = df["L_fast"].to_numpy(dtype=np.float64)
    l_slow = df["L_slow"].to_numpy(dtype=np.float64)

    t = np.where(uf, t_fast, t_slow)
    l = np.where(uf, l_fast, l_slow)
    drel = (l - l_slow) / np.maximum(l_slow, 1e-6)
    ji = t / max(float(t_ref), 1e-6) + float(beta) * np.maximum(drel, 0.0)

    return {
        "J_mean": float(np.mean(ji)),
        "V": float(np.mean(drel > float(epsilon_rel))),
        "J_i": ji.astype(np.float64),
        "drel": drel.astype(np.float64),
        "use_fast_ratio": float(np.mean(uf.astype(np.float64))),
    }


def _bootstrap_ci(arr: np.ndarray, n_boot: int, seed: int = 20260303) -> tuple[float, float]:
    if arr.size <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(int(seed))
    n = arr.size
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _bootstrap_p_gt0(arr: np.ndarray, n_boot: int, seed: int = 20260303) -> float:
    if arr.size <= 0:
        return 1.0
    rng = np.random.default_rng(int(seed))
    n = arr.size
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    return float(np.mean(means <= 0.0))


def _safe_wilcoxon_gt0(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    if x.size <= 0:
        return 1.0
    if np.allclose(x, x[0], atol=1e-15):
        return 0.0 if x[0] > 0.0 else 1.0
    return float(wilcoxon(x, alternative="greater", zero_method="pratt").pvalue)

def _select_tau_under_latency_cap(
    score: np.ndarray,
    j_fast: np.ndarray,
    j_slow: np.ndarray,
    t_fast: np.ndarray,
    t_slow: np.ndarray,
    probe_ms: np.ndarray,
    cap_total_ms: float,
) -> dict:
    score = np.asarray(score, dtype=np.float64)
    j_fast = np.asarray(j_fast, dtype=np.float64)
    j_slow = np.asarray(j_slow, dtype=np.float64)
    t_fast = np.asarray(t_fast, dtype=np.float64)
    t_slow = np.asarray(t_slow, dtype=np.float64)
    probe_ms = np.asarray(probe_ms, dtype=np.float64)

    if score.size <= 0:
        raise ValueError("Empty score array.")

    probe_mean = float(np.mean(probe_ms))
    order = np.argsort(score, kind="mergesort")
    s = score[order]
    jf = j_fast[order]
    js = j_slow[order]
    tf = t_fast[order]
    ts = t_slow[order]
    n = float(s.size)

    tot_js = float(np.sum(js))
    tot_ts = float(np.sum(ts))
    pref_jf = np.concatenate([[0.0], np.cumsum(jf)])
    pref_js = np.concatenate([[0.0], np.cumsum(js)])
    pref_tf = np.concatenate([[0.0], np.cumsum(tf)])
    pref_ts = np.concatenate([[0.0], np.cumsum(ts)])

    # Policy with k fast cases (lowest scores) and (n-k) slow cases.
    j_sum = pref_jf + (tot_js - pref_js)
    t_sum = pref_tf + (tot_ts - pref_ts)
    j_mean = j_sum / n
    total_lat_mean = (t_sum / n) + probe_mean

    feasible = total_lat_mean <= float(cap_total_ms) + 1e-12
    if not bool(np.any(feasible)):
        raise RuntimeError(
            f"No feasible threshold under latency cap: cap_total_ms={cap_total_ms:.6f}, "
            f"min_total_ms={float(np.min(total_lat_mean)):.6f}"
        )

    # Choose the feasible k with minimal true J mean.
    feas_idx = np.where(feasible)[0]
    k = int(feas_idx[int(np.argmin(j_mean[feasible]))])

    if k <= 0:
        tau = -1e18
    elif k >= int(s.size):
        tau = 1e18
    else:
        tau = float(0.5 * (s[k - 1] + s[k]))

    return {
        "tau": float(tau),
        "k_fast": int(k),
        "fast_ratio": float(k / n),
        "calib_J_mean": float(j_mean[k]),
        "calib_route_latency_mean_ms": float((t_sum[k] / n)),
        "calib_probe_latency_mean_ms": float(probe_mean),
        "calib_total_latency_mean_ms": float(total_lat_mean[k]),
    }


def _tau_min_for_route_latency_mean_cap(
    score: np.ndarray,
    t_fast: np.ndarray,
    t_slow: np.ndarray,
    cap_route_mean_ms: float,
) -> dict:
    score = np.asarray(score, dtype=np.float64)
    t_fast = np.asarray(t_fast, dtype=np.float64)
    t_slow = np.asarray(t_slow, dtype=np.float64)
    if score.size <= 0:
        raise ValueError("Empty score array.")

    order = np.argsort(score, kind="mergesort")
    s = score[order]
    tf = t_fast[order]
    ts = t_slow[order]
    n = float(s.size)

    tot_ts = float(np.sum(ts))
    pref_tf = np.concatenate([[0.0], np.cumsum(tf)])
    pref_ts = np.concatenate([[0.0], np.cumsum(ts)])
    t_sum = pref_tf + (tot_ts - pref_ts)
    route_mean = t_sum / n

    feasible = route_mean <= float(cap_route_mean_ms) + 1e-12
    if not bool(np.any(feasible)):
        raise RuntimeError(
            f"No feasible threshold under route-latency cap: cap_route_mean_ms={cap_route_mean_ms:.6f}, "
            f"min_route_mean_ms={float(np.min(route_mean)):.6f}"
        )
    # Minimal k that satisfies the cap (maximize slow usage under budget).
    k = int(np.where(feasible)[0][0])
    if k <= 0:
        tau = -1e18
    elif k >= int(s.size):
        tau = 1e18
    else:
        tau = float(0.5 * (s[k - 1] + s[k]))

    return {
        "tau": float(tau),
        "k_fast": int(k),
        "fast_ratio": float(k / n),
        "route_latency_mean_ms": float(route_mean[k]),
    }


def _apply_flips_from_p5(
    p5_use_fast: np.ndarray,
    difficulty: np.ndarray,
    flip_score: np.ndarray,
    k_slow_by_diff: dict[str, int],
) -> np.ndarray:
    p5_use_fast = np.asarray(p5_use_fast, dtype=bool)
    diff = np.asarray(difficulty, dtype=str)
    score = np.asarray(flip_score, dtype=np.float64)
    use_fast = p5_use_fast.copy()
    for d in ["easy", "medium", "hard"]:
        k = int(k_slow_by_diff.get(d, 0))
        if k <= 0:
            continue
        idx = np.where((diff == d) & p5_use_fast)[0]
        if idx.size <= 0:
            continue
        k = int(min(k, idx.size))
        order = np.argsort(score[idx], kind="mergesort")
        sel = idx[order[-k:]]
        use_fast[sel] = False
    return use_fast.astype(bool)


def _flip_budget_check(
    p5_use_fast: np.ndarray,
    use_fast: np.ndarray,
    difficulty: np.ndarray,
    k_slow_by_diff: dict[str, int],
) -> dict:
    p5_use_fast = np.asarray(p5_use_fast, dtype=bool)
    use_fast = np.asarray(use_fast, dtype=bool)
    diff = np.asarray(difficulty, dtype=str)

    extra_slow = p5_use_fast & (~use_fast)
    illegal_fast = (~p5_use_fast) & use_fast

    out = {
        "illegal_p5_slow_to_fast": int(np.sum(illegal_fast)),
        "flip_total": int(np.sum(extra_slow)),
        "ok": True,
    }
    for d in ["easy", "medium", "hard"]:
        k = int(k_slow_by_diff.get(d, 0))
        cnt = int(np.sum(extra_slow & (diff == d)))
        out[f"flip_{d}"] = cnt
        out[f"k_{d}"] = k
        if cnt != k:
            out["ok"] = False
    if out["illegal_p5_slow_to_fast"] != 0:
        out["ok"] = False
    return out


def _train_rational_static_v1(
    calib_df: pd.DataFrame,
    test_df: pd.DataFrame,
    p5_use_fast_cal: np.ndarray,
    p5_use_fast_test: np.ndarray,
    k_slow_by_diff: dict[str, int],
    t_ref: float,
    beta: float,
    epsilon_rel: float,
    seed: int,
) -> tuple[np.ndarray, dict]:
    # Family-A baseline: start from P5 (conformal strict) and flip the top-k P5-fast cases to slow using
    # a rational score learned from static heuristics.
    p5_use_fast_cal = np.asarray(p5_use_fast_cal, dtype=bool)
    p5_use_fast_test = np.asarray(p5_use_fast_test, dtype=bool)

    q_rel = calib_df["q_rel"].to_numpy(dtype=np.float64)
    mask = p5_use_fast_cal
    if int(np.sum(mask)) <= 10:
        raise RuntimeError("Too few P5-fast calibration cases for rational_static_v1.")

    # Multi-heuristic static score (z-normalized on calib P5-fast subset).
    cols = ["complexity_score", "global_occ_ratio", "local_occ_ratio", "line_block_ratio", "distance_ratio"]
    x_sub = calib_df[cols].to_numpy(dtype=np.float64)[mask]
    los_risk_sub = (1.0 - calib_df["los_clear"].to_numpy(dtype=np.float64))[mask][:, None]
    x_sub = np.concatenate([x_sub, los_risk_sub], axis=1)
    mu, sig = _standardize_fit(x_sub)

    def score(df: pd.DataFrame) -> np.ndarray:
        x = df[cols].to_numpy(dtype=np.float64)
        los_risk = (1.0 - df["los_clear"].to_numpy(dtype=np.float64))[:, None]
        x = np.concatenate([x, los_risk], axis=1)
        z = _standardize_apply(x, mu, sig)
        return np.sum(z, axis=1).astype(np.float64)

    score_cal = score(calib_df)
    score_test = score(test_df)

    use_fast = _apply_flips_from_p5(
        p5_use_fast=p5_use_fast_test,
        difficulty=test_df["difficulty"].to_numpy(dtype=str),
        flip_score=score_test,
        k_slow_by_diff=k_slow_by_diff,
    )
    use_fast_cal = _apply_flips_from_p5(
        p5_use_fast=p5_use_fast_cal,
        difficulty=calib_df["difficulty"].to_numpy(dtype=str),
        flip_score=score_cal,
        k_slow_by_diff=k_slow_by_diff,
    )
    calib_v = float(np.mean(np.where(use_fast_cal, q_rel, 0.0) > float(epsilon_rel)))
    budget_check_test = _flip_budget_check(
        p5_use_fast=p5_use_fast_test,
        use_fast=use_fast,
        difficulty=test_df["difficulty"].to_numpy(dtype=str),
        k_slow_by_diff=k_slow_by_diff,
    )
    meta = {
        "family": "A",
        "method": "rational_static_v1",
        "info_used": "static_features_only",
        "model": "start from P5; flip top-k P5-fast to slow by z-scored static heuristic sum",
        "feature_names": cols + ["los_risk"],
        "z_norm_mu": [float(x) for x in mu.tolist()],
        "z_norm_sig": [float(x) for x in sig.tolist()],
        "calib_objective": {
            "epsilon_rel": float(epsilon_rel),
            "t_ref": float(t_ref),
            "beta": float(beta),
        },
        "calib_budget": {
            "k_slow_by_difficulty": {k: int(v) for k, v in dict(k_slow_by_diff).items()},
            "calib_V": float(calib_v),
        },
        "budget_check_test": budget_check_test,
    }
    return use_fast.astype(bool), meta


def _conformal_pvals(
    alpha0: np.ndarray,
    alpha1: np.ndarray,
    diff: np.ndarray,
    sorted_scores_by_diff: dict[str, np.ndarray],
    sorted_scores_global: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    alpha0 = np.asarray(alpha0, dtype=np.float64)
    alpha1 = np.asarray(alpha1, dtype=np.float64)
    diff = np.asarray(diff, dtype=str)

    def pval(sorted_scores: np.ndarray, a: np.ndarray) -> np.ndarray:
        n = int(sorted_scores.size)
        # count(scores >= a) = n - lower_bound(a)
        idx = np.searchsorted(sorted_scores, a, side="left")
        ge = float(n) - idx.astype(np.float64)
        return (ge + 1.0) / (float(n) + 1.0)

    p0 = np.empty_like(alpha0)
    p1 = np.empty_like(alpha1)
    for d in ["easy", "medium", "hard"]:
        idx = np.where(diff == d)[0]
        if idx.size == 0:
            continue
        scores = sorted_scores_by_diff.get(d, None)
        if scores is None or int(scores.size) < 50:
            scores = sorted_scores_global
        p0[idx] = pval(scores, alpha0[idx])
        p1[idx] = pval(scores, alpha1[idx])

    unk = ~(np.isin(diff, ["easy", "medium", "hard"]))
    if np.any(unk):
        p0[unk] = pval(sorted_scores_global, alpha0[unk])
        p1[unk] = pval(sorted_scores_global, alpha1[unk])
    return p0.astype(np.float64), p1.astype(np.float64)


def _train_conformal_switch_static_v1(
    calib_df: pd.DataFrame,
    test_df: pd.DataFrame,
    p5_use_fast_cal: np.ndarray,
    p5_use_fast_test: np.ndarray,
    k_slow_by_diff: dict[str, int],
    epsilon_rel: float,
    alpha: float,
    seed: int,
) -> tuple[np.ndarray, dict]:
    # Family-B baseline: start from P5 and flip top-k P5-fast cases by a conformalized risk score.
    p5_use_fast_cal = np.asarray(p5_use_fast_cal, dtype=bool)
    p5_use_fast_test = np.asarray(p5_use_fast_test, dtype=bool)

    x_all, feat_names = _design_matrix(calib_df, STATIC_COLS, include_difficulty=True)
    y_all = calib_df["q_rel"].to_numpy(dtype=np.float64)
    diff_all = calib_df["difficulty"].to_numpy(dtype=str)

    mask = p5_use_fast_cal
    if int(np.sum(mask)) <= 10:
        raise RuntimeError("Too few P5-fast calibration cases for conformal_switch_static_v1.")

    x_sub = x_all[mask]
    y_sub = y_all[mask]
    diff_sub = diff_all[mask]

    rng = np.random.default_rng(int(seed) + 160016)
    idx_tr: list[int] = []
    idx_cal: list[int] = []
    for d in ["easy", "medium", "hard"]:
        idx = np.where(diff_sub == d)[0]
        rng.shuffle(idx)
        n = int(idx.size)
        n_tr = int(0.7 * n)
        idx_tr.extend(idx[:n_tr].tolist())
        idx_cal.extend(idx[n_tr:].tolist())
    idx_tr = np.array(sorted(idx_tr), dtype=np.int64)
    idx_cal = np.array(sorted(idx_cal), dtype=np.int64)

    mu, sig = _standardize_fit(x_sub[idx_tr])
    x_tr = _standardize_apply(x_sub[idx_tr], mu, sig)
    x_cal = _standardize_apply(x_sub[idx_cal], mu, sig)
    y_tr = y_sub[idx_tr]
    y_cal = y_sub[idx_cal]

    best = {"l2": None, "mse_cal": float("inf"), "q": None, "w": None}
    for l2 in [1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 1.0]:
        w = _ridge_fit(x_tr, y_tr, l2=float(l2))
        pred_cal = _ridge_pred(x_cal, w)
        resid = (y_cal - pred_cal).astype(np.float64)
        q = float(np.quantile(resid, 1.0 - float(alpha)))
        mse = float(np.mean((pred_cal - y_cal) ** 2))
        if mse < float(best["mse_cal"]):
            best = {"l2": float(l2), "mse_cal": float(mse), "q": float(q), "w": w}

    x_test, _ = _design_matrix(test_df, STATIC_COLS, include_difficulty=True)
    x_test = _standardize_apply(x_test, mu, sig)
    pred_test = _ridge_pred(x_test, np.asarray(best["w"], dtype=np.float64))
    score_test = pred_test + float(best["q"])
    use_fast = _apply_flips_from_p5(
        p5_use_fast=p5_use_fast_test,
        difficulty=test_df["difficulty"].to_numpy(dtype=str),
        flip_score=score_test,
        k_slow_by_diff=k_slow_by_diff,
    )

    score_cal = _ridge_pred(_standardize_apply(x_all, mu, sig), np.asarray(best["w"], dtype=np.float64)) + float(best["q"])
    use_fast_cal = _apply_flips_from_p5(
        p5_use_fast=p5_use_fast_cal,
        difficulty=calib_df["difficulty"].to_numpy(dtype=str),
        flip_score=score_cal,
        k_slow_by_diff=k_slow_by_diff,
    )
    calib_v = float(np.mean(np.where(use_fast_cal, y_all, 0.0) > float(epsilon_rel)))
    budget_check_test = _flip_budget_check(
        p5_use_fast=p5_use_fast_test,
        use_fast=use_fast,
        difficulty=test_df["difficulty"].to_numpy(dtype=str),
        k_slow_by_diff=k_slow_by_diff,
    )
    meta = {
        "family": "B",
        "method": "conformal_switch_static_v1",
        "info_used": "static_features_only",
        "model": "start from P5; flip top-k P5-fast to slow by conformal upper(q_rel|static+difficulty)",
        "feature_names": feat_names,
        "alpha_protocol": float(alpha),
        "l2": float(best["l2"]),
        "q_residual_quantile": float(best["q"]),
        "split_counts": {"train": int(idx_tr.size), "calibration": int(idx_cal.size)},
        "calib_objective": {"epsilon_rel": float(epsilon_rel)},
        "calib_budget": {
            "k_slow_by_difficulty": {k: int(v) for k, v in dict(k_slow_by_diff).items()},
            "calib_V": float(calib_v),
        },
        "budget_check_test": budget_check_test,
    }
    return use_fast.astype(bool), meta


def _train_meta_quit_probe_v1(
    calib_df: pd.DataFrame,
    test_df: pd.DataFrame,
    p5_use_fast_cal: np.ndarray,
    p5_use_fast_test: np.ndarray,
    k_slow_by_diff: dict[str, int],
    t_ref: float,
    beta: float,
    epsilon_rel: float,
    seed: int,
) -> tuple[np.ndarray, dict]:
    # Family-C baseline: start from P5 and flip top-k P5-fast cases to slow using a probe-based meta-reasoning score.
    p5_use_fast_cal = np.asarray(p5_use_fast_cal, dtype=bool)
    p5_use_fast_test = np.asarray(p5_use_fast_test, dtype=bool)
    q_rel = calib_df["q_rel"].to_numpy(dtype=np.float64)
    mask = p5_use_fast_cal
    if int(np.sum(mask)) <= 10:
        raise RuntimeError("Too few P5-fast calibration cases for meta_quit_probe_v1.")

    # Meta-reasoning "when-to-quit" probe score (z-normalized on calib P5-fast subset).
    # Larger -> more likely to benefit from escalation to slow.
    f = calib_df
    x_sub = np.stack(
        [
            (1.0 - f["probe_success"].to_numpy(dtype=np.float64)),
            f["probe_deadend_rate"].to_numpy(dtype=np.float64),
            f["probe_bottleneck_rate"].to_numpy(dtype=np.float64),
            f["probe_open_growth"].to_numpy(dtype=np.float64),
            f["probe_branching"].to_numpy(dtype=np.float64),
            -f["probe_progress_per_exp"].to_numpy(dtype=np.float64),
            -f["probe_improve_rate"].to_numpy(dtype=np.float64),
            -f["probe_h_drop_ratio"].to_numpy(dtype=np.float64),
        ],
        axis=1,
    )[mask]
    mu, sig = _standardize_fit(x_sub)

    def score(df: pd.DataFrame) -> np.ndarray:
        x = np.stack(
            [
                (1.0 - df["probe_success"].to_numpy(dtype=np.float64)),
                df["probe_deadend_rate"].to_numpy(dtype=np.float64),
                df["probe_bottleneck_rate"].to_numpy(dtype=np.float64),
                df["probe_open_growth"].to_numpy(dtype=np.float64),
                df["probe_branching"].to_numpy(dtype=np.float64),
                -df["probe_progress_per_exp"].to_numpy(dtype=np.float64),
                -df["probe_improve_rate"].to_numpy(dtype=np.float64),
                -df["probe_h_drop_ratio"].to_numpy(dtype=np.float64),
            ],
            axis=1,
        )
        z = _standardize_apply(x, mu, sig)
        return np.sum(z, axis=1).astype(np.float64)

    score_cal = score(calib_df)
    score_test = score(test_df)

    use_fast = _apply_flips_from_p5(
        p5_use_fast=p5_use_fast_test,
        difficulty=test_df["difficulty"].to_numpy(dtype=str),
        flip_score=score_test,
        k_slow_by_diff=k_slow_by_diff,
    )
    use_fast_cal = _apply_flips_from_p5(
        p5_use_fast=p5_use_fast_cal,
        difficulty=calib_df["difficulty"].to_numpy(dtype=str),
        flip_score=score_cal,
        k_slow_by_diff=k_slow_by_diff,
    )
    calib_v = float(np.mean(np.where(use_fast_cal, q_rel, 0.0) > float(epsilon_rel)))
    budget_check_test = _flip_budget_check(
        p5_use_fast=p5_use_fast_test,
        use_fast=use_fast,
        difficulty=test_df["difficulty"].to_numpy(dtype=str),
        k_slow_by_diff=k_slow_by_diff,
    )
    meta = {
        "family": "C",
        "method": "meta_quit_probe_v1",
        "info_used": "probe_features_only",
        "model": "start from P5; flip top-k P5-fast to slow by z-scored probe heuristic sum",
        "feature_names": [
            "1-probe_success",
            "probe_deadend_rate",
            "probe_bottleneck_rate",
            "probe_open_growth",
            "probe_branching",
            "-probe_progress_per_exp",
            "-probe_improve_rate",
            "-probe_h_drop_ratio",
        ],
        "z_norm_mu": [float(x) for x in mu.tolist()],
        "z_norm_sig": [float(x) for x in sig.tolist()],
        "calib_objective": {
            "epsilon_rel": float(epsilon_rel),
            "t_ref": float(t_ref),
            "beta": float(beta),
        },
        "calib_budget": {
            "k_slow_by_difficulty": {k: int(v) for k, v in dict(k_slow_by_diff).items()},
            "calib_V": float(calib_v),
        },
        "budget_check_test": budget_check_test,
    }
    return use_fast.astype(bool), meta


def _write_report(
    report_md: Path,
    stats: dict,
    seed_df: pd.DataFrame,
    method_df: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# Router Phase16 Related Baselines V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Seeds: `{stats['seeds']}`")
    lines.append(f"- Best related baseline: `{stats['best_related_baseline']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Main Metrics (vs best related baseline)")
    lines.append(
        f"- `J_improve_mean`: `{stats['summary']['j_improve_vs_best_related_mean'] * 100.0:.3f}%`"
    )
    lines.append(
        f"- `risk_delta_mean_pct`: `{stats['summary']['risk_delta_vs_best_related_mean_pct']:.3f}`"
    )
    lines.append(
        "- `pooled_delta_j_ci95`: "
        f"`[{stats['summary']['pooled_delta_j_ci95'][0]:.6f}, {stats['summary']['pooled_delta_j_ci95'][1]:.6f}]`"
    )
    lines.append(
        f"- `pooled_p_value_bootstrap_gt0`: `{stats['summary']['pooled_p_value_bootstrap_gt0']:.6e}`"
    )
    lines.append(f"- `seed_level_p_value_wilcoxon`: `{stats['summary']['pooled_p_value_wilcoxon']:.6e}`")
    lines.append("")
    lines.append("## Methods (mean over seeds)")
    lines.append("| method | family | info | J_mean | V | use_fast | total_lat_ms |")
    lines.append("|---|---:|---|---:|---:|---:|---:|")
    for _, r in method_df.iterrows():
        lines.append(
            f"| {r['method']} | {r['family']} | {r['info_used']} | {float(r['J_mean_mean']):.6f} | "
            f"{float(r['V_mean']):.6f} | {float(r['use_fast_ratio_mean']):.6f} | {float(r['total_latency_mean_ms_mean']):.6f} |"
        )
    lines.append("")
    lines.append("## Seed Metrics (ours vs best related)")
    lines.append("| seed | best related | J improve | risk delta (pct) |")
    lines.append("|---:|---|---:|---:|")
    for _, r in seed_df.iterrows():
        lines.append(
            f"| {int(r['seed'])} | {r['best_related']} | {float(r['j_improve_vs_best_related']) * 100.0:.3f}% | "
            f"{float(r['risk_delta_vs_best_related_pct']):.3f} |"
        )
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")

    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines), encoding="utf-8")


def _write_appendix(appendix_md: Path) -> None:
    txt = """# Appendix: Related-Work Baselines (Phase16)

This appendix documents the *implementation details* and *fairness/budget* assumptions for the Phase16 baselines.

## Protocol and fairness
- All methods are evaluated on the same Phase9 counterfactual tables: `router_counterfactual_{calib,test}.parquet`.
- Objective and risk use the frozen protocol (`docs/router_protocol_v1.md`): `J` and `V=P(delta_l_rel>epsilon_rel)`.
- Baseline models (feature→score) are fit using `calib` only.
- Compute/budget accounting follows the in-repo strict-router convention: all related baselines start from the Phase-5 conformal route and are only allowed to **flip a fixed number of P5-fast cases to slow** (per difficulty).

## Baseline families

### Family A — Rational multi-heuristic deployment (`rational_static_v1`)
**Idea:** a rational escalation rule: “spend extra compute only where it helps most”, using static heuristics.

**Implementation:**
- Start from Phase-5 conformal route (`conformal_strict_v2`).
- Compute a z-scored static heuristic sum on `calib` P5-fast cases (complexity/occupancy/LOS proxies).
- On `test`, among P5-fast cases, flip the top-`k_slow_by_difficulty[d]` cases (largest score) to slow for each difficulty `d`.

### Family B — Conformalized switching / decision (`conformal_switch_static_v1`)
**Idea:** conformalized risk-aware escalation: flip cases that are most likely to incur large quality loss under fast.

**Implementation:**
- Start from Phase-5 conformal route (`conformal_strict_v2`).
- Fit ridge regression on `calib` P5-fast cases to predict `q_rel` from static features.
- Use split conformal residual quantiles to form an upper bound `q_rel_upper`.
- On `test`, among P5-fast cases, flip the top-`k_slow_by_difficulty[d]` cases (largest `q_rel_upper`) to slow for each difficulty `d`.

### Family C — Meta-reasoning / when-to-quit (`meta_quit_probe_v1`)
**Idea:** after a small probe computation, decide whether to “quit early” (stay fast) or “continue computing” (escalate to slow).

**Implementation:**
- Start from Phase-5 conformal route (`conformal_strict_v2`).
- Compute a z-scored probe heuristic sum on `calib` P5-fast cases (success/stagnation/dead-end proxies).
- On `test`, among P5-fast cases, flip the top-`k_slow_by_difficulty[d]` cases (largest score) to slow for each difficulty `d`.

"""
    appendix_md.parent.mkdir(parents=True, exist_ok=True)
    appendix_md.write_text(txt, encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_out = out_dir / "tables"
    tables_out.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)

    phase9_stats_path = args.phase9_root / "stats.json"
    _ensure_exists(phase9_stats_path, "phase9 stats")
    phase9 = _load_json(phase9_stats_path)
    seeds = [int(s) for s in phase9.get("seeds", [7, 11, 19, 23, 31])]

    cf_calib_pq = args.phase9_root / "common" / "router_counterfactual_calib.parquet"
    cf_test_pq = args.phase9_root / "common" / "router_counterfactual_test.parquet"
    static_cal_pq = args.phase9_root / "common" / "risk" / "features_calib.parquet"
    static_test_pq = args.phase9_root / "common" / "risk" / "features_test.parquet"
    probe_cal_pq = args.phase9_root / "router_eval" / "common" / "probe_features_calib.parquet"
    probe_test_pq = args.phase9_root / "router_eval" / "common" / "probe_features_test.parquet"
    for p, n in [
        (cf_calib_pq, "counterfactual calib parquet"),
        (cf_test_pq, "counterfactual test parquet"),
        (static_cal_pq, "static features calib parquet"),
        (static_test_pq, "static features test parquet"),
        (probe_cal_pq, "probe features calib parquet"),
        (probe_test_pq, "probe features test parquet"),
    ]:
        _ensure_exists(p, n)

    cf_calib = pd.read_parquet(cf_calib_pq)
    cf_test = pd.read_parquet(cf_test_pq)
    static_cal = pd.read_parquet(static_cal_pq)
    static_test = pd.read_parquet(static_test_pq)
    probe_cal = pd.read_parquet(probe_cal_pq)
    probe_test = pd.read_parquet(probe_test_pq)

    calib_df = (
        cf_calib.merge(static_cal, on=["sample_name", "difficulty"], how="left")
        .merge(probe_cal, on=["sample_name", "difficulty"], how="left")
        .reset_index(drop=True)
    )
    test_df = (
        cf_test.merge(static_test, on=["sample_name", "difficulty"], how="left")
        .merge(probe_test, on=["sample_name", "difficulty"], how="left")
        .reset_index(drop=True)
    )
    if calib_df[STATIC_COLS + PROBE_COLS].isna().any().any():
        raise RuntimeError("Missing required features after merge (calib).")
    if test_df[STATIC_COLS + PROBE_COLS].isna().any().any():
        raise RuntimeError("Missing required features after merge (test).")

    per_seed_methods: list[dict] = []
    seed_evals: dict[int, dict[str, dict]] = {}
    seed_meta: dict[int, dict[str, dict]] = {}
    budget_rows: list[dict] = []
    budget_check_rows: list[dict] = []

    for seed in seeds:
        seed_root = args.phase9_root / "router_eval" / "seeds" / f"seed_{seed}" / "mixed"
        ours_dec_pq = seed_root / "probe_strict_v2" / "test_decisions.parquet"
        ours_metrics_js = seed_root / "probe_strict_v2" / "policy_metrics.json"
        p5_test_pq = seed_root / "conformal_strict_v2" / "test_decisions.parquet"
        p5_calib_pq = seed_root / "conformal_strict_v2" / "calib_decisions.parquet"
        _ensure_exists(ours_dec_pq, f"ours decisions (seed={seed})")
        _ensure_exists(ours_metrics_js, f"ours policy metrics (seed={seed})")
        _ensure_exists(p5_test_pq, f"p5 decisions test (seed={seed})")
        _ensure_exists(p5_calib_pq, f"p5 decisions calib (seed={seed})")

        ours_dec = pd.read_parquet(ours_dec_pq)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_ours"})
        p5_test = pd.read_parquet(p5_test_pq)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_p5"})
        p5_cal = pd.read_parquet(p5_calib_pq)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_p5"})
        m = _load_json(ours_metrics_js)
        t_ref = float(m["objective"]["T_ref"])
        beta = float(m["objective"]["beta"])

        df_test = test_df.merge(ours_dec, on="sample_name", how="left").merge(p5_test, on="sample_name", how="left")
        if df_test[["use_fast_ours", "use_fast_p5"]].isna().any().any():
            raise RuntimeError(f"Missing ours decisions after merge (seed={seed}).")
        df_cal = calib_df.merge(p5_cal, on="sample_name", how="left")
        if df_cal["use_fast_p5"].isna().any():
            raise RuntimeError(f"Missing p5 calib decisions after merge (seed={seed}).")

        k_slow_by_diff = m.get("selected_policy", {}).get("k_slow_by_difficulty", None)
        if not isinstance(k_slow_by_diff, dict):
            extra = df_test["use_fast_p5"].to_numpy(dtype=bool) & (~df_test["use_fast_ours"].to_numpy(dtype=bool))
            diff = df_test["difficulty"].to_numpy(dtype=str)
            k_slow_by_diff = {d: int(np.sum(extra & (diff == d))) for d in ["easy", "medium", "hard"]}
        k_slow_by_diff = {k: int(v) for k, v in dict(k_slow_by_diff).items()}

        ours_budget_check = _flip_budget_check(
            p5_use_fast=df_test["use_fast_p5"].to_numpy(dtype=bool),
            use_fast=df_test["use_fast_ours"].to_numpy(dtype=bool),
            difficulty=df_test["difficulty"].to_numpy(dtype=str),
            k_slow_by_diff=k_slow_by_diff,
        )
        budget_rows.append(
            {
                "seed": int(seed),
                "k_slow_easy": int(k_slow_by_diff.get("easy", 0)),
                "k_slow_medium": int(k_slow_by_diff.get("medium", 0)),
                "k_slow_hard": int(k_slow_by_diff.get("hard", 0)),
                "ours_flip_ok": bool(ours_budget_check.get("ok", False)),
                "ours_flip_total": int(ours_budget_check.get("flip_total", 0)),
            }
        )

        use_fast_a, meta_a = _train_rational_static_v1(
            calib_df=df_cal,
            test_df=df_test,
            p5_use_fast_cal=df_cal["use_fast_p5"].to_numpy(dtype=bool),
            p5_use_fast_test=df_test["use_fast_p5"].to_numpy(dtype=bool),
            k_slow_by_diff=k_slow_by_diff,
            t_ref=t_ref,
            beta=beta,
            epsilon_rel=float(args.epsilon_rel),
            seed=int(seed),
        )
        use_fast_b, meta_b = _train_conformal_switch_static_v1(
            calib_df=df_cal,
            test_df=df_test,
            p5_use_fast_cal=df_cal["use_fast_p5"].to_numpy(dtype=bool),
            p5_use_fast_test=df_test["use_fast_p5"].to_numpy(dtype=bool),
            k_slow_by_diff=k_slow_by_diff,
            epsilon_rel=float(args.epsilon_rel),
            alpha=float(args.alpha),
            seed=int(seed),
        )
        use_fast_c, meta_c = _train_meta_quit_probe_v1(
            calib_df=df_cal,
            test_df=df_test,
            p5_use_fast_cal=df_cal["use_fast_p5"].to_numpy(dtype=bool),
            p5_use_fast_test=df_test["use_fast_p5"].to_numpy(dtype=bool),
            k_slow_by_diff=k_slow_by_diff,
            t_ref=t_ref,
            beta=beta,
            epsilon_rel=float(args.epsilon_rel),
            seed=int(seed),
        )

        policies = {
            "ours_probe_strict_v2": df_test["use_fast_ours"].to_numpy(dtype=bool),
            "p5_conformal_strict_v2": df_test["use_fast_p5"].to_numpy(dtype=bool),
            "rational_static_v1": use_fast_a,
            "conformal_switch_static_v1": use_fast_b,
            "meta_quit_probe_v1": use_fast_c,
        }
        meta_by_method = {
            "rational_static_v1": meta_a,
            "conformal_switch_static_v1": meta_b,
            "meta_quit_probe_v1": meta_c,
        }
        for method in ["rational_static_v1", "conformal_switch_static_v1", "meta_quit_probe_v1"]:
            r = dict(meta_by_method[method].get("budget_check_test", {}))
            r.update({"seed": int(seed), "method": str(method)})
            budget_check_rows.append(r)

        evals: dict[str, dict] = {}
        for name, uf in policies.items():
            evals[name] = _eval_policy(
                df=df_test,
                use_fast=uf,
                t_ref=t_ref,
                beta=beta,
                epsilon_rel=float(args.epsilon_rel),
            )
            uses_probe = bool(name in ["ours_probe_strict_v2", "meta_quit_probe_v1"])
            route_lat = np.where(
                np.asarray(uf, dtype=bool),
                df_test["T_fast_ms"].to_numpy(dtype=np.float64),
                df_test["T_slow_ms"].to_numpy(dtype=np.float64),
            )
            probe_lat = df_test["probe_runtime_ms"].to_numpy(dtype=np.float64) if uses_probe else np.zeros(len(df_test), dtype=np.float64)
            total_lat = route_lat + probe_lat
            if name == "ours_probe_strict_v2":
                fam = "ours"
                info = "probe+conformal"
            elif name == "p5_conformal_strict_v2":
                fam = "p5"
                info = "conformal_only"
            else:
                fam = str(meta_by_method[name]["family"])
                info = str(meta_by_method[name]["info_used"])
            per_seed_methods.append(
                {
                    "seed": int(seed),
                    "method": str(name),
                    "family": fam,
                    "info_used": info,
                    "J_mean": float(evals[name]["J_mean"]),
                    "V": float(evals[name]["V"]),
                    "use_fast_ratio": float(evals[name]["use_fast_ratio"]),
                    "route_latency_mean_ms": float(np.mean(route_lat)),
                    "probe_latency_mean_ms": float(np.mean(probe_lat)),
                    "total_latency_mean_ms": float(np.mean(total_lat)),
                    "t_ref": float(t_ref),
                    "beta": float(beta),
                }
            )

        seed_evals[int(seed)] = evals
        seed_meta[int(seed)] = meta_by_method

        # Write per-seed decision artifacts for reproducibility.
        seed_out = out_dir / "seeds" / f"seed_{seed}"
        for method, uf in [
            ("rational_static_v1", use_fast_a),
            ("conformal_switch_static_v1", use_fast_b),
            ("meta_quit_probe_v1", use_fast_c),
        ]:
            d = seed_out / method
            d.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                {
                    "sample_name": df_test["sample_name"].astype(str),
                    "difficulty": df_test["difficulty"].astype(str),
                    "use_fast": np.asarray(uf, dtype=bool),
                }
            ).to_parquet(d / "test_decisions.parquet", index=False)
            (d / "policy_meta.json").write_text(json.dumps(seed_meta[int(seed)][method], indent=2), encoding="utf-8")

    method_seed_df = pd.DataFrame(per_seed_methods)
    related_methods = ["rational_static_v1", "conformal_switch_static_v1", "meta_quit_probe_v1"]
    method_summary = (
        method_seed_df.groupby(["method", "family", "info_used"], as_index=False)
        .agg(
            J_mean_mean=("J_mean", "mean"),
            J_mean_std=("J_mean", "std"),
            V_mean=("V", "mean"),
            V_std=("V", "std"),
            use_fast_ratio_mean=("use_fast_ratio", "mean"),
            use_fast_ratio_std=("use_fast_ratio", "std"),
            total_latency_mean_ms_mean=("total_latency_mean_ms", "mean"),
            total_latency_mean_ms_std=("total_latency_mean_ms", "std"),
        )
        .sort_values("J_mean_mean", ascending=True)
        .reset_index(drop=True)
    )

    best_related = (
        method_summary[method_summary["method"].isin(related_methods)]
        .sort_values("J_mean_mean", ascending=True)
        .reset_index(drop=True)
    )
    if len(best_related) <= 0:
        raise RuntimeError("No related baselines found for Phase16.")
    best_related_method = str(best_related.iloc[0]["method"])

    seed_rows: list[dict] = []
    pooled_delta_j: list[np.ndarray] = []
    bench_rows: list[dict] = []
    for seed in seeds:
        ours = seed_evals[int(seed)]["ours_probe_strict_v2"]
        base = seed_evals[int(seed)][best_related_method]
        j_improve = float((base["J_mean"] - ours["J_mean"]) / max(abs(base["J_mean"]), 1e-12))
        risk_delta_pct = float((ours["V"] - base["V"]) * 100.0)
        delta_case = (base["J_i"] - ours["J_i"]) / max(abs(base["J_mean"]), 1e-9)
        pooled_delta_j.append(delta_case.astype(np.float64))
        seed_rows.append(
            {
                "seed": int(seed),
                "best_related": best_related_method,
                "j_ours": float(ours["J_mean"]),
                "j_best_related": float(base["J_mean"]),
                "j_improve_vs_best_related": float(j_improve),
                "risk_ours": float(ours["V"]),
                "risk_best_related": float(base["V"]),
                "risk_delta_vs_best_related_pct": float(risk_delta_pct),
            }
        )

        # Per-benchmark direction detail (test split).
        df_test = test_df
        for ds, g in df_test.groupby("source_dataset"):
            idx = g.index.to_numpy(dtype=np.int64)
            j_ours_ds = float(np.mean(ours["J_i"][idx]))
            j_base_ds = float(np.mean(base["J_i"][idx]))
            imp_ds = float((j_base_ds - j_ours_ds) / max(abs(j_base_ds), 1e-12))
            bench_rows.append({"seed": int(seed), "source_dataset": str(ds), "delta_j": float(imp_ds)})

    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    bench_seed_df = pd.DataFrame(bench_rows)
    bench_summary = (
        bench_seed_df.groupby("source_dataset", as_index=False)
        .agg(delta_j_mean=("delta_j", "mean"), delta_j_std=("delta_j", "std"), delta_j_min=("delta_j", "min"), delta_j_max=("delta_j", "max"))
        .sort_values("source_dataset")
        .reset_index(drop=True)
    )
    bench_summary["delta_j_std"] = bench_summary["delta_j_std"].fillna(0.0)

    pooled = np.concatenate(pooled_delta_j) if pooled_delta_j else np.zeros(0, dtype=np.float64)
    pooled_mean = float(np.mean(pooled)) if pooled.size > 0 else float("nan")
    pooled_std = float(np.std(pooled)) if pooled.size > 0 else float("nan")
    ci_lo, ci_hi = _bootstrap_ci(pooled, n_boot=int(args.bootstrap_n))
    p_boot = _bootstrap_p_gt0(pooled, n_boot=int(args.bootstrap_n))
    p_wil = _safe_wilcoxon_gt0(seed_df["j_improve_vs_best_related"].to_numpy(dtype=np.float64))

    budget_df = pd.DataFrame(budget_rows).sort_values("seed").reset_index(drop=True)
    budget_csv = tables_out / "budget_caps.csv"
    budget_df.to_csv(budget_csv, index=False)

    budget_check_df = pd.DataFrame(budget_check_rows).sort_values(["method", "seed"]).reset_index(drop=True)
    budget_check_csv = tables_out / "budget_checks.csv"
    budget_check_df.to_csv(budget_check_csv, index=False)

    budget_ok = bool(budget_df["ours_flip_ok"].all()) and (bool(budget_check_df["ok"].all()) if len(budget_check_df) else False)

    gate = {
        "baseline_family_count_ge_3": True,
        "same_protocol_and_budget": bool(budget_ok),
        "J_improve_vs_best_related_ge_3pct": bool(float(seed_df["j_improve_vs_best_related"].mean()) >= float(args.j_improve_target)),
        "risk_not_worse_deltaV_le_0_5pct": bool(float(seed_df["risk_delta_vs_best_related_pct"].mean()) <= float(args.max_risk_delta_pct)),
        "pooled_p_lt_0_01": bool(float(p_boot) < 0.01),
        "pooled_ci95_not_cross_0": bool(float(ci_lo) > 0.0),
    }
    gate["pooled_p_lt_0_01_and_ci_no_cross_0"] = bool(gate["pooled_p_lt_0_01"] and gate["pooled_ci95_not_cross_0"])

    seed_metrics_csv = tables_out / "seed_metrics.csv"
    method_summary_csv = tables_out / "method_summary.csv"
    bench_csv = tables_out / "seed_benchmark_direction.csv"
    sig_csv = tables_out / "significance.csv"

    seed_df.to_csv(seed_metrics_csv, index=False)
    method_summary.to_csv(method_summary_csv, index=False)
    bench_summary.to_csv(bench_csv, index=False)
    pd.DataFrame(
        [
            {
                "best_related_baseline": best_related_method,
                "n_pooled": int(pooled.size),
                "pooled_mean_delta_j": float(pooled_mean),
                "pooled_std_delta_j": float(pooled_std),
                "pooled_ci95_low": float(ci_lo),
                "pooled_ci95_high": float(ci_hi),
                "pooled_p_value_bootstrap_gt0": float(p_boot),
                "seed_level_p_value_wilcoxon": float(p_wil),
            }
        ]
    ).to_csv(sig_csv, index=False)

    # Paper table (single CSV as requested by TASK.md Step1).
    paper_table = args.tables_dir / "table_phase16_related_baselines.csv"
    method_summary.sort_values(["family", "method"]).to_csv(paper_table, index=False)

    _write_appendix(args.appendix_md)

    stats = {
        "version": "router_phase16_related_baselines_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": seeds,
        "best_related_baseline": best_related_method,
        "counts": {
            "baseline_family_count": 3,
            "related_methods": related_methods,
            "pooled_cases": int(pooled.size),
            "public_benchmarks": int(bench_summary["source_dataset"].nunique()),
        },
        "summary": {
            "j_improve_vs_best_related_mean": float(seed_df["j_improve_vs_best_related"].mean()),
            "j_improve_vs_best_related_std": float(seed_df["j_improve_vs_best_related"].std(ddof=0)),
            "risk_delta_vs_best_related_mean_pct": float(seed_df["risk_delta_vs_best_related_pct"].mean()),
            "risk_delta_vs_best_related_std_pct": float(seed_df["risk_delta_vs_best_related_pct"].std(ddof=0)),
            "pooled_delta_j_mean": float(pooled_mean),
            "pooled_delta_j_std": float(pooled_std),
            "pooled_delta_j_ci95": [float(ci_lo), float(ci_hi)],
            "pooled_p_value_bootstrap_gt0": float(p_boot),
            "pooled_p_value_wilcoxon": float(p_wil),
        },
        "benchmark_direction": bench_summary.to_dict(orient="records"),
        "baseline_meta_by_seed": {str(k): v for k, v in seed_meta.items()},
        "gate_check": {
            "baseline_family_count_ge_3": gate["baseline_family_count_ge_3"],
            "same_protocol_and_budget": gate["same_protocol_and_budget"],
            "J_improve_vs_best_related_ge_3pct": gate["J_improve_vs_best_related_ge_3pct"],
            "risk_not_worse_deltaV_le_0_5pct": gate["risk_not_worse_deltaV_le_0_5pct"],
            "pooled_p_lt_0_01_and_ci_no_cross_0": gate["pooled_p_lt_0_01_and_ci_no_cross_0"],
        },
        "artifacts": {
            "out_dir": str(out_dir),
            "seed_metrics_csv": str(seed_metrics_csv),
            "method_summary_csv": str(method_summary_csv),
            "seed_benchmark_direction_csv": str(bench_csv),
            "significance_csv": str(sig_csv),
            "budget_caps_csv": str(budget_csv),
            "budget_checks_csv": str(budget_check_csv),
            "paper_table_csv": str(paper_table),
            "appendix_md": str(args.appendix_md),
            "report_md": str(args.report_md),
        },
    }

    stats_path = out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(args.report_md, stats=stats, seed_df=seed_df, method_df=method_summary)

    print(f"[phase16] stats={stats_path}")
    print(f"[phase16] report={args.report_md}")
    print(f"[phase16] best_related={best_related_method}")
    print(f"[phase16] gate={stats['gate_check']}")

    if bool(args.enforce_gate) and not all(stats["gate_check"].values()):
        raise RuntimeError("Phase-16 gate failed. Check outputs/router_phase16_related_baselines_v1/stats.json")


if __name__ == "__main__":
    main()
