from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.parquet_guard import INPUTS_SHA256_FILENAME, write_record


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-22 direct baselines: CDT/CRC-style decisions under frozen protocol.")
    p.add_argument("--phase9-root", type=Path, default=Path("outputs/router_phase9_bench_v1"))
    p.add_argument(
        "--ours-policy-dirname",
        type=str,
        default="probe_strict_v2",
        help="Which per-seed policy directory to treat as 'ours' under phase9_root/router_eval/seeds/seed_*/mixed/ "
        "(default: probe_strict_v2; recovery: probe_selective_v1 / probe_boundary_v1 / probe_risktrade_v1).",
    )
    p.add_argument(
        "--ours-root",
        type=Path,
        default=None,
        help="Optional external per-seed root for ours: <root>/seeds/seed_*/{test_decisions.parquet,policy_metrics.json}.",
    )
    p.add_argument(
        "--ours-arm-table-test",
        type=Path,
        default=None,
        help="Optional weighted-arm counterfactual test parquet used when ours emits route_arm instead of use_fast.",
    )
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument("--cdt-alpha", type=float, default=0.10, help="Split conformal alpha for CDT-style upper bound on q_pos.")
    p.add_argument("--crc-alpha", type=float, default=0.10, help="Split conformal alpha for CRC-style upper bound on violation probability.")
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase22_direct_baselines_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase22_direct_baselines_v1.md"))
    p.add_argument("--tables-dir", type=Path, default=Path("paper/tables_router_v7"))
    p.add_argument("--enforce-gate", dest="enforce_gate", action="store_true", default=True)
    p.add_argument(
        "--no-enforce-gate",
        dest="enforce_gate",
        action="store_false",
        help="Write artifacts but do not raise on gate failures (useful for strict audit runs).",
    )
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


def _design_matrix(df: pd.DataFrame, cols: list[str], include_difficulty: bool = True) -> np.ndarray:
    x = df[cols].to_numpy(dtype=np.float64)
    if include_difficulty:
        diff = df["difficulty"].astype(str).to_numpy()
        is_medium = (diff == "medium").astype(np.float64)[:, None]
        is_hard = (diff == "hard").astype(np.float64)[:, None]
        x = np.concatenate([x, is_medium, is_hard], axis=1)
    return x.astype(np.float64)


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
    iters: int = 1800,
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


def _split_conformal_offsets_by_diff(
    *,
    diff: np.ndarray,
    s: np.ndarray,
    alpha: float,
) -> dict[str, float]:
    out: dict[str, float] = {}
    diff = np.asarray(diff, dtype=str)
    s = np.asarray(s, dtype=np.float64)
    for d in ("easy", "medium", "hard"):
        mask = diff == d
        vals = s[mask]
        n = int(vals.size)
        if n <= 0:
            out[d] = 0.0
            continue
        level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / n)
        level = float(np.clip(level, 0.0, 1.0))
        out[d] = float(np.quantile(vals, level, method="higher"))
    return out


def _resolve_policy_time_length(
    df: pd.DataFrame,
    *,
    use_fast: np.ndarray | None = None,
    route_arm: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, float]:
    if route_arm is not None:
        route_arm_arr = np.asarray(route_arm, dtype=str)
        if route_arm_arr.shape[0] != len(df):
            raise ValueError(f"route_arm shape mismatch: {route_arm_arr.shape} vs n={len(df)}")
        route_arm = route_arm_arr
        use_fast = None
    elif use_fast is None:
        raise ValueError("Exactly one of use_fast or route_arm must be provided.")

    if route_arm is None:
        uf = np.asarray(use_fast, dtype=bool)
        t = np.where(uf, df["T_fast_ms"].to_numpy(dtype=np.float64), df["T_slow_ms"].to_numpy(dtype=np.float64))
        l = np.where(uf, df["L_fast"].to_numpy(dtype=np.float64), df["L_slow"].to_numpy(dtype=np.float64))
        return t.astype(np.float64), l.astype(np.float64), float(np.mean(uf.astype(np.float64)))

    arms = np.asarray(route_arm, dtype=str)
    t = np.full(len(df), np.nan, dtype=np.float64)
    l = np.full(len(df), np.nan, dtype=np.float64)
    for arm in sorted({str(x) for x in arms.tolist()}):
        mask = arms == arm
        if arm == "fast":
            t_col = "T_fast_ms"
            l_col = "L_fast"
        elif arm == "slow":
            t_col = "T_slow_ms"
            l_col = "L_slow"
        else:
            tag = arm[3:] if arm.startswith("wa_") else arm
            t_col = f"T_{tag}_ms"
            l_col = f"L_{tag}"
        if t_col not in df.columns or l_col not in df.columns:
            raise KeyError(f"Missing weighted-arm columns for arm={arm}: {t_col}, {l_col}")
        t[mask] = df.loc[mask, t_col].to_numpy(dtype=np.float64)
        l[mask] = df.loc[mask, l_col].to_numpy(dtype=np.float64)
    if np.isnan(t).any() or np.isnan(l).any():
        raise RuntimeError("Unresolved route_arm values during policy evaluation.")
    return t.astype(np.float64), l.astype(np.float64), float(np.mean((arms == "fast").astype(np.float64)))



def _route_fast_mask(*, use_fast: np.ndarray | None = None, route_arm: np.ndarray | None = None) -> np.ndarray:
    if route_arm is not None:
        return (np.asarray(route_arm, dtype=str) == "fast").astype(np.float64)
    if use_fast is None:
        raise ValueError("Either use_fast or route_arm must be provided.")
    return np.asarray(use_fast, dtype=np.float64)



def _compute_probe_overhead_ms(
    df: pd.DataFrame,
    *,
    use_fast: np.ndarray | None = None,
    route_arm: np.ndarray | None = None,
    probe_used: np.ndarray | None = None,
    overhead_mode: str = "additive",
) -> np.ndarray:
    if probe_used is None:
        return np.zeros(len(df), dtype=np.float64)
    used = np.asarray(probe_used, dtype=np.float64)
    if used.shape[0] != len(df):
        raise ValueError(f"probe_used shape mismatch: {used.shape} vs n={len(df)}")
    fast_mask = _route_fast_mask(use_fast=use_fast, route_arm=route_arm)
    probe_runtime = df["probe_runtime_ms"].to_numpy(dtype=np.float64)
    infer_slow = df["infer_slow_ms"].to_numpy(dtype=np.float64)
    mode = str(overhead_mode).lower().strip()
    if mode in {"trace_slow_overlap_infer", "trace_overlap_infer_slow_only", "overlap_infer_slow_only"}:
        return np.maximum(probe_runtime - infer_slow, 0.0) * used * (1.0 - fast_mask)
    if mode in {"prefix_reuse", "prefix_reuse_fast_only", "prefixreuse"}:
        return probe_runtime * used * fast_mask
    if mode in {"trace_slow_only", "trace_prefix_slow_only", "slow_only"}:
        return probe_runtime * used * (1.0 - fast_mask)
    return probe_runtime * used



def _eval_policy(
    df: pd.DataFrame,
    use_fast: np.ndarray | None,
    t_ref: float,
    beta: float,
    epsilon_rel: float,
    *,
    route_arm: np.ndarray | None = None,
    extra_time_ms: np.ndarray | None = None,
) -> dict:
    t, l, use_fast_ratio = _resolve_policy_time_length(df, use_fast=use_fast, route_arm=route_arm)
    l_slow = df["L_slow"].to_numpy(dtype=np.float64)

    extra = np.zeros(len(df), dtype=np.float64) if extra_time_ms is None else np.asarray(extra_time_ms, dtype=np.float64)
    if extra.shape[0] != len(df):
        raise ValueError(f"extra_time_ms shape mismatch: {extra.shape} vs n={len(df)}")
    t = t + extra
    drel = (l - l_slow) / np.maximum(l_slow, 1e-6)
    ji = t / max(float(t_ref), 1e-6) + float(beta) * np.maximum(drel, 0.0)

    return {
        "J_mean": float(np.mean(ji)),
        "V": float(np.mean(drel > float(epsilon_rel))),
        "J_i": ji.astype(np.float64),
        "drel": drel.astype(np.float64),
        "use_fast_ratio": float(use_fast_ratio),
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
    try:
        return float(wilcoxon(x, alternative="greater", zero_method="pratt").pvalue)
    except Exception:
        return 1.0


def _apply_flip_budget(
    *,
    base_use_fast: np.ndarray,
    score: np.ndarray,
    difficulty: np.ndarray,
    k_slow_by_diff: dict[str, int],
) -> tuple[np.ndarray, dict[str, float]]:
    """
    Start from `base_use_fast` and flip the top-k (highest score) fast cases to slow per difficulty.
    Returns (use_fast, tau_by_diff).
    """

    base_use_fast = np.asarray(base_use_fast, dtype=bool)
    score = np.asarray(score, dtype=np.float64)
    diff = np.asarray(difficulty, dtype=str)
    use = base_use_fast.copy()
    tau: dict[str, float] = {}

    # Tie-break to keep deterministic.
    score = score + np.arange(score.size, dtype=np.float64) * 1e-12

    for d in ("easy", "medium", "hard"):
        ids = np.where((diff == d) & base_use_fast)[0]
        if ids.size <= 0:
            tau[d] = float("inf")
            continue
        ord_desc = ids[np.argsort(score[ids])[::-1]]
        k = int(np.clip(int(k_slow_by_diff.get(d, 0)), 0, int(ord_desc.size)))
        use[ord_desc[:k]] = False
        if k <= 0:
            tau[d] = float(np.max(score[ids]) + 1e-12)
        elif k >= int(ord_desc.size):
            tau[d] = float(np.min(score[ids]) - 1e-12)
        else:
            tau[d] = float((score[ord_desc[k - 1]] + score[ord_desc[k]]) * 0.5)
    return use.astype(bool), tau


def _flip_budget_check(
    *,
    p5_use_fast: np.ndarray,
    use_fast: np.ndarray,
    difficulty: np.ndarray,
    k_slow_by_diff: dict[str, int],
) -> dict[str, object]:
    p5_use_fast = np.asarray(p5_use_fast, dtype=bool)
    use_fast = np.asarray(use_fast, dtype=bool)
    diff = np.asarray(difficulty, dtype=str)

    bad = (~p5_use_fast) & use_fast
    if bool(np.any(bad)):
        return {"ok": False, "reason": "invalid_flip_slow_to_fast", "count": int(np.sum(bad))}

    flips = p5_use_fast & (~use_fast)
    rows: list[dict] = []
    ok = True
    for d in ("easy", "medium", "hard"):
        cap = int(k_slow_by_diff.get(d, 0))
        c = int(np.sum(flips & (diff == d)))
        if c > cap:
            ok = False
        rows.append({"difficulty": d, "flip_count": c, "cap": cap})
    return {"ok": bool(ok), "flip_total": int(np.sum(flips)), "per_diff": rows}



def _weighted_slow_budget_check(
    *,
    route_arm: np.ndarray,
    difficulty: np.ndarray,
    k_slow_by_diff: dict[str, int],
) -> dict[str, object]:
    arms = np.asarray(route_arm, dtype=str)
    diff = np.asarray(difficulty, dtype=str)
    slow = arms == "slow"
    rows: list[dict] = []
    ok = True
    for d in ("easy", "medium", "hard"):
        cap = int(k_slow_by_diff.get(d, 0))
        c = int(np.sum(slow & (diff == d)))
        if c > cap:
            ok = False
        rows.append({"difficulty": d, "slow_count": c, "cap": cap})
    return {"ok": bool(ok), "slow_total": int(np.sum(slow)), "per_diff": rows}


def _train_crc_static_pupper_v1(
    *,
    calib_df: pd.DataFrame,
    test_df: pd.DataFrame,
    p5_use_fast_cal: np.ndarray,
    p5_use_fast_test: np.ndarray,
    k_slow_by_diff: dict[str, int],
    epsilon_rel: float,
    alpha_conformal: float,
    seed: int,
) -> tuple[np.ndarray, dict]:
    """
    CRC-style baseline:
    1) fit a violation classifier p_hat(x)=P(q_rel>eps),
    2) split-conformalize to p_upper(x)=clip(p_hat+q_d,0,1),
    3) under the fixed budget (top-k flips per difficulty), flip highest p_upper fast cases to slow.
    """

    mask = np.asarray(p5_use_fast_cal, dtype=bool)
    if int(np.sum(mask)) <= 10:
        raise RuntimeError("Not enough P5-fast calibration samples for CRC baseline.")

    x_cal = _design_matrix(calib_df.loc[mask], STATIC_COLS, include_difficulty=True)
    mu, sig = _standardize_fit(x_cal)
    x_cal = _standardize_apply(x_cal, mu, sig)

    y_cal = (calib_df.loc[mask, "q_rel"].to_numpy(dtype=np.float64) > float(epsilon_rel)).astype(np.float64)

    w = _logistic_fit(x_cal, y_cal, l2=0.8, lr=0.25, iters=2200)
    p_hat_cal = _logistic_pred_prob(x_cal, w)

    diff_cal = calib_df.loc[mask, "difficulty"].astype(str).to_numpy()
    s = np.maximum(y_cal - p_hat_cal, 0.0)
    q_by_diff = _split_conformal_offsets_by_diff(diff=diff_cal, s=s, alpha=float(alpha_conformal))

    x_test = _design_matrix(test_df, STATIC_COLS, include_difficulty=True)
    x_test = _standardize_apply(x_test, mu, sig)
    p_hat_test = _logistic_pred_prob(x_test, w)
    diff_test = test_df["difficulty"].astype(str).to_numpy()
    q = np.array([float(q_by_diff.get(d, 0.0)) for d in diff_test], dtype=np.float64)
    p_upper_test = np.clip(p_hat_test + q, 0.0, 1.0)

    use_fast, tau = _apply_flip_budget(
        base_use_fast=np.asarray(p5_use_fast_test, dtype=bool),
        score=p_upper_test,
        difficulty=diff_test,
        k_slow_by_diff=k_slow_by_diff,
    )
    meta = {
        "family": "CRC",
        "info_used": "static_p_upper_rank",
        "alpha_conformal": float(alpha_conformal),
        "q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()},
        "tau_by_difficulty": {k: float(v) for k, v in tau.items()},
        "model": {"type": "logistic_gd", "l2": 0.8, "lr": 0.25, "iters": 2200, "seed": int(seed)},
    }
    return use_fast.astype(bool), meta


def _train_cdt_worstcase_j_v1(
    *,
    calib_df: pd.DataFrame,
    test_df: pd.DataFrame,
    p5_use_fast_cal: np.ndarray,
    p5_use_fast_test: np.ndarray,
    k_slow_by_diff: dict[str, int],
    t_ref: float,
    beta: float,
    alpha_conformal: float,
    seed: int,
) -> tuple[np.ndarray, dict]:
    """
    CDT-style baseline (cost-aware):
    1) fit a regressor for q_pos=max(q_rel,0),
    2) split-conformalize to an upper bound q_pos <= q_hat + q_d (groupwise),
    3) compute worst-case fast cost: J_fast_upper = T_fast/T_ref + beta*q_pos_upper,
       slow cost: J_slow = T_slow/T_ref,
    4) under fixed budget, flip largest (J_fast_upper - J_slow) fast cases to slow.
    """

    mask = np.asarray(p5_use_fast_cal, dtype=bool)
    if int(np.sum(mask)) <= 10:
        raise RuntimeError("Not enough P5-fast calibration samples for CDT baseline.")

    q_pos_cal = np.maximum(calib_df.loc[mask, "q_rel"].to_numpy(dtype=np.float64), 0.0)
    x_cal = _design_matrix(calib_df.loc[mask], STATIC_COLS, include_difficulty=True)
    mu, sig = _standardize_fit(x_cal)
    x_cal = _standardize_apply(x_cal, mu, sig)
    w = _ridge_fit(x_cal, q_pos_cal, l2=1.0)
    q_hat_cal = np.clip(_ridge_pred(x_cal, w), 0.0, None)

    diff_cal = calib_df.loc[mask, "difficulty"].astype(str).to_numpy()
    s = np.maximum(q_pos_cal - q_hat_cal, 0.0)
    q_by_diff = _split_conformal_offsets_by_diff(diff=diff_cal, s=s, alpha=float(alpha_conformal))

    x_test = _design_matrix(test_df, STATIC_COLS, include_difficulty=True)
    x_test = _standardize_apply(x_test, mu, sig)
    q_hat_test = np.clip(_ridge_pred(x_test, w), 0.0, None)

    diff_test = test_df["difficulty"].astype(str).to_numpy()
    q_off = np.array([float(q_by_diff.get(d, 0.0)) for d in diff_test], dtype=np.float64)
    q_upper = np.clip(q_hat_test + q_off, 0.0, None)

    t_fast = test_df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = test_df["T_slow_ms"].to_numpy(dtype=np.float64)
    j_fast_upper = t_fast / max(float(t_ref), 1e-9) + float(beta) * q_upper
    j_slow = t_slow / max(float(t_ref), 1e-9)
    margin = j_fast_upper - j_slow

    use_fast, tau = _apply_flip_budget(
        base_use_fast=np.asarray(p5_use_fast_test, dtype=bool),
        score=margin,
        difficulty=diff_test,
        k_slow_by_diff=k_slow_by_diff,
    )
    meta = {
        "family": "CDT",
        "info_used": "static_conformal_worstcase_J",
        "alpha_conformal": float(alpha_conformal),
        "q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()},
        "tau_by_difficulty": {k: float(v) for k, v in tau.items()},
        "model": {"type": "ridge_closed_form", "l2": 1.0, "seed": int(seed)},
    }
    return use_fast.astype(bool), meta


def _write_report(
    report_path: Path,
    *,
    stats: dict,
) -> None:
    s = stats
    lines: list[str] = []
    lines.append("# Router Phase22 Direct Baselines V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{s['runtime_hours']:.3f} h`")
    lines.append(f"- Seeds: `{s['seeds']}`")
    lines.append(f"- Best direct baseline: `{s['best_direct_baseline']}`")
    if 'budget_parity_mode_consensus' in s:
        lines.append(f"- Budget parity mode: `{s['budget_parity_mode_consensus']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in s["gate_check"].items():
        lines.append(f"- `{k}`: `{bool(v)}`")
    lines.append("")
    lines.append("## Main Metrics (vs best direct baseline)")
    summ = s["summary"]
    lines.append(f"- `J_improve_mean`: `{summ['j_improve_vs_best_direct_mean']:.3f}%`")
    lines.append(f"- `risk_delta_mean_pct`: `{summ['risk_delta_vs_best_direct_mean_pct']:.3f}`")
    lines.append(f"- `pooled_delta_j_ci95`: `{summ['pooled_delta_j_ci95']}`")
    lines.append(f"- `pooled_p_value_bootstrap_gt0`: `{summ['pooled_p_value_bootstrap_gt0']:.6e}`")
    lines.append(f"- `seed_level_p_value_wilcoxon`: `{summ['seed_level_p_value_wilcoxon']:.6e}`")
    lines.append(f"- `ours_vs_best_direct_significant_p_lt_0_01`: `{bool(summ['ours_vs_best_direct_significant_p_lt_0_01'])}`")
    lines.append("")
    lines.append("## Direct Baseline Strength (vs P5)")
    lines.append(f"- `best_direct_vs_p5_J_improve_mean`: `{summ['j_improve_best_direct_vs_p5_mean']:.3f}%`")
    lines.append(f"- `best_direct_vs_p5_pooled_ci95`: `{summ['pooled_delta_j_best_direct_vs_p5_ci95']}`")
    lines.append(f"- `best_direct_vs_p5_p_value_bootstrap_gt0`: `{summ['pooled_p_value_bootstrap_gt0_best_direct_vs_p5']:.6e}`")
    lines.append(f"- `best_direct_vs_p5_significant_p_lt_0_01`: `{bool(summ['best_direct_vs_p5_significant_p_lt_0_01'])}`")
    lines.append("")
    if not bool(summ["ours_vs_best_direct_significant_p_lt_0_01"]):
        lines.append("## Note")
        if float(summ["j_improve_vs_best_direct_mean"]) > 0.0:
            lines.append(
                "- Ours improves over the best direct baseline in mean `J`, but this difference is **not** significant at `p<0.01` under the frozen bootstrap protocol."
            )
        else:
            lines.append(
                "- Ours does **not** improve over the best direct baseline in mean `J` under this protocol; claims should be reframed accordingly."
            )
        lines.append("- Claims should be reframed accordingly (see `paper/related_work_neurips_alignment.md`).")
    lines.append("")
    lines.append("## Artifacts")
    for k, v in s["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_out = out_dir / "tables"
    tables_out.mkdir(parents=True, exist_ok=True)

    seeds = [7, 11, 19, 23, 31]

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
    if args.ours_arm_table_test is not None:
        _ensure_exists(args.ours_arm_table_test, "ours weighted-arm test parquet")

    ours_arm_test_df = None
    if args.ours_arm_table_test is not None:
        ours_arm_test_df = pd.read_parquet(args.ours_arm_table_test)

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

    direct_methods = ["crc_static_pupper_v1", "cdt_worstcase_j_v1"]

    for seed in seeds:
        seed_root = args.phase9_root / "router_eval" / "seeds" / f"seed_{seed}" / "mixed"
        ours_dir = (args.ours_root / "seeds" / f"seed_{seed}") if args.ours_root is not None else (seed_root / str(args.ours_policy_dirname))
        ours_dec_pq = ours_dir / "test_decisions.parquet"
        ours_metrics_js = ours_dir / "policy_metrics.json"
        p5_test_pq = seed_root / "conformal_strict_v2" / "test_decisions.parquet"
        p5_calib_pq = seed_root / "conformal_strict_v2" / "calib_decisions.parquet"
        for p, n in [
            (ours_dec_pq, f"ours decisions (seed={seed})"),
            (ours_metrics_js, f"ours policy metrics (seed={seed})"),
            (p5_test_pq, f"p5 decisions test (seed={seed})"),
            (p5_calib_pq, f"p5 decisions calib (seed={seed})"),
        ]:
            _ensure_exists(p, n)

        ours_dec_df = pd.read_parquet(ours_dec_pq)
        if "use_fast" not in ours_dec_df.columns and "route_arm" not in ours_dec_df.columns:
            raise RuntimeError(f"Ours decisions must contain use_fast or route_arm (seed={seed}).")
        cols = ["sample_name"]
        merge_keys = ["sample_name"]
        if "difficulty" in ours_dec_df.columns:
            cols.append("difficulty")
            merge_keys = ["sample_name", "difficulty"]
        if "use_fast" in ours_dec_df.columns:
            cols.append("use_fast")
        if "route_arm" in ours_dec_df.columns:
            cols.append("route_arm")
        if "probe_used" in ours_dec_df.columns:
            cols.append("probe_used")
        ours_dec = ours_dec_df[cols].rename(
            columns={"use_fast": "use_fast_ours", "route_arm": "route_arm_ours", "probe_used": "probe_used_ours"}
        )
        if "probe_used_ours" not in ours_dec.columns:
            ours_dec["probe_used_ours"] = False if "route_arm_ours" in ours_dec.columns else True
        p5_test = pd.read_parquet(p5_test_pq)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_p5"})
        p5_cal = pd.read_parquet(p5_calib_pq)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_p5"})
        m = _load_json(ours_metrics_js)
        t_ref = float(m["objective"]["T_ref"])
        beta = float(m["objective"]["beta"])
        overhead_mode = str(m.get("probe_overhead_mode", "additive")).lower().strip()

        df_test = test_df.merge(ours_dec, on=merge_keys, how="left").merge(p5_test, on="sample_name", how="left")
        if "route_arm_ours" in df_test.columns:
            if ours_arm_test_df is None:
                raise RuntimeError("route_arm decisions require --ours-arm-table-test.")
            df_test = df_test.merge(ours_arm_test_df, on=["sample_name", "difficulty"], how="left")
        required = ["use_fast_p5", "probe_used_ours"]
        if "use_fast_ours" in df_test.columns:
            required.append("use_fast_ours")
        if "route_arm_ours" in df_test.columns:
            required.append("route_arm_ours")
        if df_test[required].isna().any().any():
            raise RuntimeError(f"Missing ours/p5 decisions after merge (seed={seed}).")
        df_cal = calib_df.merge(p5_cal, on="sample_name", how="left")
        if df_cal["use_fast_p5"].isna().any():
            raise RuntimeError(f"Missing p5 calib decisions after merge (seed={seed}).")

        ours_route_arm = df_test["route_arm_ours"].to_numpy(dtype=str) if "route_arm_ours" in df_test.columns else None
        ours_use_fast = df_test["use_fast_ours"].to_numpy(dtype=bool) if "use_fast_ours" in df_test.columns else None
        budget_mode = "flip_budget_fast_to_slow"
        k_slow_by_diff = m.get("selected_policy", {}).get("k_slow_by_difficulty", None)
        if ours_route_arm is not None:
            budget_mode = "weighted_search_slow_fallback_cap"
            if not isinstance(k_slow_by_diff, dict):
                diff = df_test["difficulty"].to_numpy(dtype=str)
                slow = ours_route_arm == "slow"
                k_slow_by_diff = {d: int(np.sum(slow & (diff == d))) for d in ["easy", "medium", "hard"]}
            k_slow_by_diff = {k: int(v) for k, v in dict(k_slow_by_diff).items()}
            ours_budget_check = _weighted_slow_budget_check(
                route_arm=ours_route_arm,
                difficulty=df_test["difficulty"].to_numpy(dtype=str),
                k_slow_by_diff=k_slow_by_diff,
            )
            ours_budget_total = int(ours_budget_check.get("slow_total", 0))
        else:
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
            ours_budget_total = int(ours_budget_check.get("flip_total", 0))
        budget_rows.append(
            {
                "seed": int(seed),
                "budget_parity_mode": str(budget_mode),
                "k_slow_easy": int(k_slow_by_diff.get("easy", 0)),
                "k_slow_medium": int(k_slow_by_diff.get("medium", 0)),
                "k_slow_hard": int(k_slow_by_diff.get("hard", 0)),
                "ours_budget_ok": bool(ours_budget_check.get("ok", False)),
                "ours_budget_total": int(ours_budget_total),
            }
        )

        use_fast_crc, meta_crc = _train_crc_static_pupper_v1(
            calib_df=df_cal,
            test_df=df_test,
            p5_use_fast_cal=df_cal["use_fast_p5"].to_numpy(dtype=bool),
            p5_use_fast_test=df_test["use_fast_p5"].to_numpy(dtype=bool),
            k_slow_by_diff=k_slow_by_diff,
            epsilon_rel=float(args.epsilon_rel),
            alpha_conformal=float(args.crc_alpha),
            seed=int(seed),
        )
        use_fast_cdt, meta_cdt = _train_cdt_worstcase_j_v1(
            calib_df=df_cal,
            test_df=df_test,
            p5_use_fast_cal=df_cal["use_fast_p5"].to_numpy(dtype=bool),
            p5_use_fast_test=df_test["use_fast_p5"].to_numpy(dtype=bool),
            k_slow_by_diff=k_slow_by_diff,
            t_ref=t_ref,
            beta=beta,
            alpha_conformal=float(args.cdt_alpha),
            seed=int(seed),
        )

        seed_meta[int(seed)] = {
            "crc_static_pupper_v1": meta_crc,
            "cdt_worstcase_j_v1": meta_cdt,
        }
        for method, uf in [
            ("crc_static_pupper_v1", use_fast_crc),
            ("cdt_worstcase_j_v1", use_fast_cdt),
        ]:
            r = dict(
                _flip_budget_check(
                    p5_use_fast=df_test["use_fast_p5"].to_numpy(dtype=bool),
                    use_fast=uf,
                    difficulty=df_test["difficulty"].to_numpy(dtype=str),
                    k_slow_by_diff=k_slow_by_diff,
                )
            )
            r.update({"seed": int(seed), "method": str(method)})
            budget_check_rows.append(r)

        policies = {
            "ours": {
                "use_fast": ours_use_fast,
                "route_arm": ours_route_arm,
                "uses_probe": bool(np.any(df_test["probe_used_ours"].to_numpy(dtype=bool))),
            },
            "p5_conformal_strict_v2": {
                "use_fast": df_test["use_fast_p5"].to_numpy(dtype=bool),
                "route_arm": None,
                "uses_probe": False,
            },
            "crc_static_pupper_v1": {"use_fast": use_fast_crc, "route_arm": None, "uses_probe": False},
            "cdt_worstcase_j_v1": {"use_fast": use_fast_cdt, "route_arm": None, "uses_probe": False},
        }

        evals: dict[str, dict] = {}
        for name, spec in policies.items():
            uf = spec["use_fast"]
            route_arm = spec["route_arm"]
            uses_probe = bool(spec["uses_probe"])
            probe_lat = (
                _compute_probe_overhead_ms(
                    df_test,
                    use_fast=uf,
                    route_arm=route_arm,
                    probe_used=df_test["probe_used_ours"].to_numpy(dtype=bool),
                    overhead_mode=overhead_mode,
                )
                if uses_probe
                else np.zeros(len(df_test), dtype=np.float64)
            )
            evals[name] = _eval_policy(
                df=df_test,
                use_fast=uf,
                route_arm=route_arm,
                t_ref=t_ref,
                beta=beta,
                epsilon_rel=float(args.epsilon_rel),
                extra_time_ms=(probe_lat if uses_probe else None),
            )
            route_lat, _, _ = _resolve_policy_time_length(df_test, use_fast=uf, route_arm=route_arm)
            total_lat = route_lat + probe_lat

            if name == "ours":
                fam = "ours"
                info = "weighted_search_tree_zero_probe" if route_arm is not None else "probe+conformal"
            elif name == "p5_conformal_strict_v2":
                fam = "p5"
                info = "conformal_only"
            else:
                fam = str(seed_meta[int(seed)][name]["family"])
                info = str(seed_meta[int(seed)][name]["info_used"])

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
                    "probe_trigger_rate": float(np.mean(df_test["probe_used_ours"].to_numpy(dtype=np.float64))) if uses_probe else 0.0,
                    "total_latency_mean_ms": float(np.mean(total_lat)),
                    "t_ref": float(t_ref),
                    "beta": float(beta),
                }
            )

        seed_evals[int(seed)] = evals

        # Write per-seed decision artifacts.
        seed_out = out_dir / "seeds" / f"seed_{seed}"
        for method, uf in [
            ("crc_static_pupper_v1", use_fast_crc),
            ("cdt_worstcase_j_v1", use_fast_cdt),
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

    best_direct = (
        method_summary[method_summary["method"].isin(direct_methods)]
        .sort_values("J_mean_mean", ascending=True)
        .reset_index(drop=True)
    )
    if len(best_direct) <= 0:
        raise RuntimeError("No direct baselines found for Phase22.")
    best_direct_method = str(best_direct.iloc[0]["method"])

    seed_rows: list[dict] = []
    pooled_delta_j: list[np.ndarray] = []
    bench_rows: list[dict] = []
    for seed in seeds:
        ours = seed_evals[int(seed)]["ours"]
        base = seed_evals[int(seed)][best_direct_method]
        j_improve = float((base["J_mean"] - ours["J_mean"]) / max(abs(base["J_mean"]), 1e-12))
        risk_delta_pct = float((ours["V"] - base["V"]) * 100.0)
        delta_case = (base["J_i"] - ours["J_i"]) / max(abs(base["J_mean"]), 1e-9)
        pooled_delta_j.append(delta_case.astype(np.float64))
        seed_rows.append(
            {
                "seed": int(seed),
                "best_direct": best_direct_method,
                "j_ours": float(ours["J_mean"]),
                "j_best_direct": float(base["J_mean"]),
                "j_improve_vs_best_direct": float(j_improve),
                "risk_ours": float(ours["V"]),
                "risk_best_direct": float(base["V"]),
                "risk_delta_vs_best_direct_pct": float(risk_delta_pct),
            }
        )

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
    bench_summary["direction_consistent"] = bench_summary["delta_j_mean"] >= -1e-9

    pooled = np.concatenate(pooled_delta_j) if pooled_delta_j else np.zeros(0, dtype=np.float64)
    pooled_mean = float(np.mean(pooled)) if pooled.size > 0 else float("nan")
    pooled_std = float(np.std(pooled)) if pooled.size > 0 else float("nan")
    ci_lo, ci_hi = _bootstrap_ci(pooled, n_boot=int(args.bootstrap_n))
    p_boot = _bootstrap_p_gt0(pooled, n_boot=int(args.bootstrap_n))
    p_wil = _safe_wilcoxon_gt0(seed_df["j_improve_vs_best_direct"].to_numpy(dtype=np.float64))

    # Also quantify best direct baseline strength vs P5 baseline (same protocol/budget accounting).
    seed_rows_bd_vs_p5: list[dict] = []
    pooled_delta_j_bd_vs_p5: list[np.ndarray] = []
    for seed in seeds:
        p5 = seed_evals[int(seed)]["p5_conformal_strict_v2"]
        bd = seed_evals[int(seed)][best_direct_method]
        imp = float((p5["J_mean"] - bd["J_mean"]) / max(abs(p5["J_mean"]), 1e-12))
        delta_case = (p5["J_i"] - bd["J_i"]) / max(abs(p5["J_mean"]), 1e-9)
        pooled_delta_j_bd_vs_p5.append(delta_case.astype(np.float64))
        seed_rows_bd_vs_p5.append({"seed": int(seed), "j_improve_best_direct_vs_p5": float(imp)})
    pooled_bd_vs_p5 = np.concatenate(pooled_delta_j_bd_vs_p5) if pooled_delta_j_bd_vs_p5 else np.zeros(0, dtype=np.float64)
    ci_lo_bd, ci_hi_bd = _bootstrap_ci(pooled_bd_vs_p5, n_boot=int(args.bootstrap_n), seed=20260303 + 22)
    p_boot_bd = _bootstrap_p_gt0(pooled_bd_vs_p5, n_boot=int(args.bootstrap_n), seed=20260303 + 22)

    budget_df = pd.DataFrame(budget_rows).sort_values("seed").reset_index(drop=True)
    budget_check_df = pd.DataFrame(budget_check_rows).sort_values(["method", "seed"]).reset_index(drop=True)
    budget_ok = bool(budget_df["ours_budget_ok"].all()) and (bool(budget_check_df["ok"].all()) if len(budget_check_df) else False)
    budget_mode_consensus = (
        str(budget_df["budget_parity_mode"].mode().iloc[0]) if len(budget_df) and "budget_parity_mode" in budget_df.columns else "unknown"
    )

    ours_sig = bool(float(p_boot) < 0.01 and float(ci_lo) > 0.0 and bool(bench_summary["direction_consistent"].all()))
    bd_sig = bool(float(p_boot_bd) < 0.01 and float(ci_lo_bd) > 0.0)

    gate = {
        "direct_baselines_ge_2": bool(len(direct_methods) >= 2),
        "same_protocol_and_budget": bool(budget_ok),
        "either_win_or_reframe": bool(ours_sig or (float(seed_df["j_improve_vs_best_direct"].mean()) > 0.0)),
        # We require at least one statistically-hardened result at the p<0.01 level:
        # either ours beats the best direct baseline significantly, or the best direct baseline beats P5 significantly.
        "main_result_significant": bool(ours_sig or bd_sig),
    }

    # Write tables (out_dir).
    seed_metrics_csv = tables_out / "seed_metrics.csv"
    method_summary_csv = tables_out / "method_summary.csv"
    bench_csv = tables_out / "seed_benchmark_direction.csv"
    sig_csv = tables_out / "significance.csv"
    budget_csv = tables_out / "budget_caps.csv"
    budget_check_csv = tables_out / "budget_checks.csv"
    stats_path = out_dir / "stats.json"

    seed_df.to_csv(seed_metrics_csv, index=False)
    method_summary.to_csv(method_summary_csv, index=False)
    bench_summary.to_csv(bench_csv, index=False)
    budget_df.to_csv(budget_csv, index=False)
    budget_check_df.to_csv(budget_check_csv, index=False)
    pd.DataFrame(
        [
            {
                "best_direct_baseline": best_direct_method,
                "n_pooled": int(pooled.size),
                "pooled_mean_delta_j": float(pooled_mean),
                "pooled_std_delta_j": float(pooled_std),
                "pooled_ci95_low": float(ci_lo),
                "pooled_ci95_high": float(ci_hi),
                "pooled_p_value_bootstrap_gt0": float(p_boot),
                "seed_level_p_value_wilcoxon": float(p_wil),
                "best_direct_vs_p5_ci95_low": float(ci_lo_bd),
                "best_direct_vs_p5_ci95_high": float(ci_hi_bd),
                "best_direct_vs_p5_p_value_bootstrap_gt0": float(p_boot_bd),
            }
        ]
    ).to_csv(sig_csv, index=False)

    # Paper table.
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    paper_table = args.tables_dir / "table_phase22_direct_baselines.csv"
    method_summary.sort_values(["family", "method"]).to_csv(paper_table, index=False)

    stats = {
        "version": "router_phase22_direct_baselines_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": seeds,
        "ours_policy_dirname": str(args.ours_policy_dirname),
        "ours_root": (str(args.ours_root) if args.ours_root is not None else None),
        "ours_arm_table_test": (str(args.ours_arm_table_test) if args.ours_arm_table_test is not None else None),
        "budget_parity_mode_consensus": str(budget_mode_consensus),
        "best_direct_baseline": best_direct_method,
        "counts": {
            "direct_baselines": direct_methods,
            "pooled_cases": int(pooled.size),
            "public_benchmarks": int(bench_summary["source_dataset"].nunique()),
        },
        "summary": {
            "j_improve_vs_best_direct_mean": float(seed_df["j_improve_vs_best_direct"].mean() * 100.0),
            "j_improve_vs_best_direct_std": float(seed_df["j_improve_vs_best_direct"].std(ddof=0) * 100.0),
            "risk_delta_vs_best_direct_mean_pct": float(seed_df["risk_delta_vs_best_direct_pct"].mean()),
            "risk_delta_vs_best_direct_std_pct": float(seed_df["risk_delta_vs_best_direct_pct"].std(ddof=0)),
            "pooled_delta_j_mean": float(pooled_mean),
            "pooled_delta_j_std": float(pooled_std),
            "pooled_delta_j_ci95": [float(ci_lo), float(ci_hi)],
            "pooled_p_value_bootstrap_gt0": float(p_boot),
            "seed_level_p_value_wilcoxon": float(p_wil),
            "ours_vs_best_direct_significant_p_lt_0_01": bool(ours_sig),
            "j_improve_best_direct_vs_p5_mean": float(np.mean([r["j_improve_best_direct_vs_p5"] for r in seed_rows_bd_vs_p5]) * 100.0),
            "pooled_delta_j_best_direct_vs_p5_ci95": [float(ci_lo_bd), float(ci_hi_bd)],
            "pooled_p_value_bootstrap_gt0_best_direct_vs_p5": float(p_boot_bd),
            "best_direct_vs_p5_significant_p_lt_0_01": bool(bd_sig),
        },
        "benchmark_direction": bench_summary.to_dict(orient="records"),
        "baseline_meta_by_seed": {str(k): v for k, v in seed_meta.items()},
        "gate_check": gate,
        "artifacts": {
            "out_dir": str(out_dir),
            "seed_metrics_csv": str(seed_metrics_csv),
            "method_summary_csv": str(method_summary_csv),
            "significance_csv": str(sig_csv),
            "paper_table_csv": str(paper_table),
            "report_md": str(args.report_md),
        },
    }
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    _write_report(args.report_md, stats=stats)
    input_parquets: dict[str, Path] = {
        "phase9_counterfactual_calib_parquet": cf_calib_pq,
        "phase9_counterfactual_test_parquet": cf_test_pq,
        "phase9_static_features_calib_parquet": static_cal_pq,
        "phase9_static_features_test_parquet": static_test_pq,
        "phase9_probe_features_calib_parquet": probe_cal_pq,
        "phase9_probe_features_test_parquet": probe_test_pq,
    }
    for seed in seeds:
        seed_root = args.phase9_root / "router_eval" / "seeds" / f"seed_{seed}" / "mixed"
        ours_dir = (args.ours_root / "seeds" / f"seed_{seed}") if args.ours_root is not None else (seed_root / str(args.ours_policy_dirname))
        input_parquets[f"seed_{seed}_ours_test_decisions_parquet"] = ours_dir / "test_decisions.parquet"
        input_parquets[f"seed_{seed}_ours_policy_metrics_json"] = ours_dir / "policy_metrics.json"
        input_parquets[f"seed_{seed}_p5_conformal_test_decisions_parquet"] = (
            seed_root / "conformal_strict_v2" / "test_decisions.parquet"
        )
        input_parquets[f"seed_{seed}_p5_conformal_calib_decisions_parquet"] = (
            seed_root / "conformal_strict_v2" / "calib_decisions.parquet"
        )
    if args.ours_arm_table_test is not None:
        input_parquets["ours_arm_table_test_parquet"] = args.ours_arm_table_test
    write_record(out_dir / INPUTS_SHA256_FILENAME, input_parquets)

    if bool(args.enforce_gate):
        bad = [k for k, v in gate.items() if not bool(v)]
        if bad:
            raise RuntimeError(f"[phase22] gate failed: {bad}")

    print(f"[phase22] wrote: {stats_path}")
    print(f"[phase22] report: {args.report_md}")


if __name__ == "__main__":
    main()
