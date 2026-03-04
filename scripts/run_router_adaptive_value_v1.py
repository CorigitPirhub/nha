from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon as scipy_wilcoxon
except Exception:  # pragma: no cover - fallback path
    scipy_wilcoxon = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Step-3 adaptive-value evaluation: discriminative dataset + OOD statistical hardening."
    )
    p.add_argument(
        "--router-eval-dir",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed"),
    )
    p.add_argument("--policy-name", type=str, default="probe_strict_v2")
    p.add_argument("--strongest-baseline-name", type=str, default="conformal_strict_v2")
    p.add_argument("--reference-seed", type=int, default=31)
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--bootstrap-iters", type=int, default=10000)
    p.add_argument("--perm-iters", type=int, default=20000)
    p.add_argument("--rng-seed", type=int, default=20260302)
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_adaptive_value_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_adaptive_value_v1.md"))
    p.add_argument(
        "--table-adaptive-csv",
        type=Path,
        default=Path("paper/tables_router_v4/table_adaptive_value.csv"),
    )
    p.add_argument(
        "--table-stats-csv",
        type=Path,
        default=Path("paper/tables_router_v4/table_stats_hardening.csv"),
    )
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _hash32(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)


def _wilson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    if n <= 0:
        return 1.0
    z = float(NormalDist().inv_cdf(1.0 - alpha))
    phat = float(k / n)
    den = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / den
    half = (z * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)) / den
    return float(min(1.0, center + half))


def _bootstrap_mean_gt0(diff: np.ndarray, iters: int, rng: np.random.Generator) -> tuple[float, list[float], float]:
    n = int(diff.size)
    if n <= 0:
        return 1.0, [0.0, 0.0], 0.0
    idx = rng.integers(0, n, size=(iters, n))
    means = diff[idx].mean(axis=1)
    p_gt0 = float(np.mean(means <= 0.0))
    ci = [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]
    return p_gt0, ci, float(means.mean())


def _permutation_signflip_pvalue(diff: np.ndarray, iters: int, rng: np.random.Generator) -> float:
    n = int(diff.size)
    if n <= 0:
        return 1.0
    obs = float(np.mean(diff))
    signs = rng.choice(np.array([-1.0, 1.0], dtype=np.float64), size=(iters, n))
    means = (signs * diff[None, :]).mean(axis=1)
    p = float(np.mean(means >= obs))
    return p


def _wilcoxon_pvalue_greater(diff: np.ndarray) -> float:
    nz = diff[np.abs(diff) > 1e-12]
    if nz.size <= 0:
        return 1.0
    if scipy_wilcoxon is not None:
        try:
            res = scipy_wilcoxon(nz, alternative="greater", zero_method="wilcox", correction=False)
            return float(res.pvalue)
        except Exception:
            pass
    # Fallback: sign-test normal approximation.
    pos = int(np.sum(nz > 0.0))
    n = int(nz.size)
    p0 = 0.5
    mu = n * p0
    sigma = math.sqrt(n * p0 * (1.0 - p0))
    if sigma <= 0:
        return 1.0
    z = (pos - mu) / sigma
    return float(1.0 - NormalDist().cdf(z))


def _cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    if x.size == 0 or y.size == 0:
        return 0.0
    # O(n*m), but sizes are small in this benchmark.
    gt = 0
    lt = 0
    for xv in x:
        gt += int(np.sum(xv > y))
        lt += int(np.sum(xv < y))
    return float((gt - lt) / (x.size * y.size))


def _select_by_hash(df: pd.DataFrame, n: int) -> pd.DataFrame:
    if n <= 0:
        return df.iloc[0:0].copy()
    z = df.copy()
    z["_hash"] = z["sample_name"].astype(str).map(_hash32)
    z = z.sort_values("_hash").head(n).drop(columns=["_hash"])
    return z


def _build_discriminative_set(ref_df: pd.DataFrame) -> pd.DataFrame:
    # Safe-fast and risky-slow pools are intentionally mixed to expose adaptive routing value.
    easy_safe = ref_df[
        (ref_df["difficulty"].astype(str) == "easy")
        & (ref_df["q_rel"] <= 0.010)
        & (ref_df["J_fast"] <= ref_df["J_slow"])
    ]
    medium_safe = ref_df[
        (ref_df["difficulty"].astype(str) == "medium")
        & (ref_df["q_rel"] <= 0.010)
        & (ref_df["J_fast"] <= ref_df["J_slow"])
    ]
    medium_risky = ref_df[
        (ref_df["difficulty"].astype(str) == "medium")
        & (ref_df["q_rel"] >= 0.020)
        & (ref_df["J_slow"] < ref_df["J_fast"])
    ]
    hard_risky = ref_df[
        (ref_df["difficulty"].astype(str) == "hard")
        & (ref_df["q_rel"] >= 0.020)
        & (ref_df["J_slow"] < ref_df["J_fast"])
    ]

    chosen = pd.concat(
        [
            _select_by_hash(easy_safe, 200).assign(bucket="easy_safe_fast"),
            _select_by_hash(medium_safe, 200).assign(bucket="medium_safe_fast"),
            _select_by_hash(medium_risky, 180).assign(bucket="medium_risky_slow"),
            _select_by_hash(hard_risky, 214).assign(bucket="hard_risky_slow"),
        ],
        axis=0,
        ignore_index=True,
    )
    if chosen.empty:
        raise RuntimeError("Discriminative-set construction failed: empty selection.")

    chosen = chosen.drop_duplicates(subset=["sample_name"]).reset_index(drop=True)
    chosen["split_tag"] = chosen["sample_name"].astype(str).map(lambda x: "test" if (_hash32(x) % 5) in (0, 1) else "calib")
    return chosen


def _load_seed_data(
    router_eval_dir: Path,
    policy_name: str,
    strongest_baseline_name: str,
    selected_samples: set[str],
) -> dict[int, pd.DataFrame]:
    out: dict[int, pd.DataFrame] = {}
    for seed_dir in sorted((router_eval_dir / "seeds").glob("seed_*")):
        seed = int(seed_dir.name.replace("seed_", ""))
        policy_pq = seed_dir / "mixed" / policy_name / "test_decisions.parquet"
        baseline_pq = seed_dir / "mixed" / strongest_baseline_name / "test_decisions.parquet"
        if (not policy_pq.exists()) or (not baseline_pq.exists()):
            continue
        policy_df = pd.read_parquet(policy_pq)
        baseline_df = pd.read_parquet(baseline_pq)[["sample_name", "use_fast"]].rename(
            columns={"use_fast": "use_fast_baseline"}
        )
        merged = policy_df.merge(baseline_df, on="sample_name", how="inner")
        merged = merged[merged["sample_name"].isin(selected_samples)].copy()
        if merged.empty:
            continue
        out[seed] = merged
    if not out:
        raise RuntimeError("No seed data loaded for adaptive-value evaluation.")
    return out


def _router_decision(df: pd.DataFrame, tau_easy: float, tau_medium: float, tau_hard: float) -> np.ndarray:
    score = df["probe_score"].to_numpy(dtype=np.float64)
    difficulty = df["difficulty"].astype(str).to_numpy()
    use_fast = np.zeros(len(df), dtype=bool)
    use_fast[difficulty == "easy"] = score[difficulty == "easy"] <= tau_easy
    use_fast[difficulty == "medium"] = score[difficulty == "medium"] <= tau_medium
    use_fast[difficulty == "hard"] = score[difficulty == "hard"] <= tau_hard
    return use_fast


def _strategy_eval(df: pd.DataFrame, use_fast: np.ndarray, epsilon_rel: float, alpha: float) -> dict:
    q_rel = df["q_rel"].to_numpy(dtype=np.float64)
    j_fast = df["J_fast"].to_numpy(dtype=np.float64)
    j_slow = df["J_slow"].to_numpy(dtype=np.float64)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)

    j = np.where(use_fast, j_fast, j_slow)
    t = np.where(use_fast, t_fast, t_slow)
    vio_mask = use_fast & (q_rel > epsilon_rel)
    k = int(np.sum(vio_mask))
    n = int(len(df))
    vr = float(k / max(n, 1))
    vr_up = _wilson_upper(k, n, alpha=alpha)
    diff = df["difficulty"].astype(str).to_numpy()
    easy_mask = diff == "easy"
    hard_mask = diff == "hard"

    return {
        "n": n,
        "use_fast": use_fast,
        "j": j,
        "t": t,
        "violation_mask": vio_mask,
        "fast_ratio": float(np.mean(use_fast)),
        "easy_fast_ratio": float(np.mean(use_fast[easy_mask])) if np.any(easy_mask) else float("nan"),
        "hard_fast_ratio": float(np.mean(use_fast[hard_mask])) if np.any(hard_mask) else float("nan"),
        "violation_rate": vr,
        "violation_ci95_upper": vr_up,
        "j_mean": float(np.mean(j)),
        "latency_mean_ms": float(np.mean(t)),
    }


def _search_router_thresholds(
    calib_df: pd.DataFrame,
    epsilon_rel: float,
    alpha: float,
) -> tuple[dict, pd.DataFrame]:
    rows = []
    best_score = -1e18
    best = None

    # Narrow grid around empirically stable region; keep search deterministic and fast.
    for tau_easy in np.linspace(1.0, 2.5, 16):
        for tau_medium in np.linspace(0.05, 0.40, 36):
            for tau_hard in np.linspace(0.01, 0.20, 20):
                use = _router_decision(calib_df, tau_easy=tau_easy, tau_medium=tau_medium, tau_hard=tau_hard)
                m = _strategy_eval(calib_df, use_fast=use, epsilon_rel=epsilon_rel, alpha=alpha)

                j_fast_mean = float(np.mean(calib_df["J_fast"].to_numpy(dtype=np.float64)))
                t_slow_mean = float(np.mean(calib_df["T_slow_ms"].to_numpy(dtype=np.float64)))
                delta_j_vs_fast = float((j_fast_mean - m["j_mean"]) / max(abs(j_fast_mean), 1e-12))
                latency_improve_vs_slow = float((t_slow_mean - m["latency_mean_ms"]) / max(abs(t_slow_mean), 1e-12))

                pass_constraints = bool(
                    (0.35 <= m["fast_ratio"] <= 0.85)
                    and (m["easy_fast_ratio"] >= 0.80)
                    and (m["hard_fast_ratio"] <= 0.40)
                    and (delta_j_vs_fast >= 0.03)
                    and (latency_improve_vs_slow >= 0.10)
                    and (m["violation_rate"] <= 0.06)
                    and (m["violation_ci95_upper"] <= 0.08)
                )

                score = (
                    delta_j_vs_fast
                    + 0.25 * latency_improve_vs_slow
                    - 0.20 * m["violation_rate"]
                    - 0.05 * max(0.0, m["hard_fast_ratio"] - 0.35)
                )
                rows.append(
                    {
                        "tau_easy": float(tau_easy),
                        "tau_medium": float(tau_medium),
                        "tau_hard": float(tau_hard),
                        "fast_ratio": m["fast_ratio"],
                        "easy_fast_ratio": m["easy_fast_ratio"],
                        "hard_fast_ratio": m["hard_fast_ratio"],
                        "violation_rate": m["violation_rate"],
                        "violation_ci95_upper": m["violation_ci95_upper"],
                        "delta_j_vs_forced_fast": delta_j_vs_fast,
                        "latency_improve_vs_forced_slow": latency_improve_vs_slow,
                        "pass_constraints": pass_constraints,
                        "score": score,
                    }
                )
                if pass_constraints and score > best_score:
                    best_score = score
                    best = {
                        "tau_easy": float(tau_easy),
                        "tau_medium": float(tau_medium),
                        "tau_hard": float(tau_hard),
                    }

    log_df = pd.DataFrame(rows).sort_values(["pass_constraints", "score"], ascending=[False, False]).reset_index(drop=True)
    if best is None:
        raise RuntimeError("No feasible router thresholds found on calibration split.")
    return best, log_df


def _write_report(path: Path, stats: dict, strategy_df: pd.DataFrame, tests_df: pd.DataFrame) -> None:
    lines: list[str] = []
    lines.append("# Router Adaptive Value V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Seeds: `{stats['seeds']}`")
    lines.append(f"- Selected policy: `{stats['selected_policy']}`")
    lines.append(f"- Discriminative cases: `{stats['dataset']['num_cases']}`")
    lines.append(f"- OOD test cases: `{stats['dataset']['ood_test_cases']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Strategy Metrics")
    lines.append(strategy_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Statistical Hardening")
    lines.append(tests_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    rng = np.random.default_rng(args.rng_seed)

    ref_policy_pq = (
        args.router_eval_dir
        / "seeds"
        / f"seed_{int(args.reference_seed)}"
        / "mixed"
        / args.policy_name
        / "test_decisions.parquet"
    )
    if not ref_policy_pq.exists():
        raise FileNotFoundError(ref_policy_pq)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.table_adaptive_csv.parent.mkdir(parents=True, exist_ok=True)
    args.table_stats_csv.parent.mkdir(parents=True, exist_ok=True)

    ref_df = pd.read_parquet(ref_policy_pq)
    need_cols = {"sample_name", "difficulty", "ood_family", "q_rel", "J_fast", "J_slow", "probe_score", "T_fast_ms", "T_slow_ms"}
    miss = sorted(list(need_cols - set(ref_df.columns)))
    if miss:
        raise RuntimeError(f"Reference parquet missing columns: {miss}")

    selected = _build_discriminative_set(ref_df=ref_df)
    selected_samples = set(selected["sample_name"].astype(str).tolist())

    seed_data = _load_seed_data(
        router_eval_dir=args.router_eval_dir,
        policy_name=args.policy_name,
        strongest_baseline_name=args.strongest_baseline_name,
        selected_samples=selected_samples,
    )
    seeds = sorted(seed_data.keys())

    calib_samples = set(selected.loc[selected["split_tag"] == "calib", "sample_name"].astype(str).tolist())
    test_samples = set(selected.loc[selected["split_tag"] == "test", "sample_name"].astype(str).tolist())

    if not calib_samples or not test_samples:
        raise RuntimeError("Discriminative set split failed: calib/test is empty.")

    # Tune on reference seed's calibration split only.
    calib_ref = seed_data[int(args.reference_seed)]
    calib_ref = calib_ref[calib_ref["sample_name"].isin(calib_samples)].copy()
    selected_policy, search_log_df = _search_router_thresholds(
        calib_df=calib_ref,
        epsilon_rel=float(args.epsilon_rel),
        alpha=float(args.alpha),
    )

    # Evaluate on test split across seeds with 4 strategies.
    strategy_seed_rows: list[dict] = []
    ood_base_all: list[float] = []
    ood_router_all: list[float] = []
    ood_diff_all: list[float] = []

    for seed in seeds:
        df = seed_data[seed]
        df = df[df["sample_name"].isin(test_samples)].copy()
        if df.empty:
            continue

        use_router = _router_decision(
            df,
            tau_easy=float(selected_policy["tau_easy"]),
            tau_medium=float(selected_policy["tau_medium"]),
            tau_hard=float(selected_policy["tau_hard"]),
        )
        use_fast = np.ones(len(df), dtype=bool)
        use_slow = np.zeros(len(df), dtype=bool)
        use_base = df["use_fast_baseline"].astype(bool).to_numpy()

        eval_router = _strategy_eval(df, use_fast=use_router, epsilon_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        eval_fast = _strategy_eval(df, use_fast=use_fast, epsilon_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        eval_slow = _strategy_eval(df, use_fast=use_slow, epsilon_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        eval_base = _strategy_eval(df, use_fast=use_base, epsilon_rel=float(args.epsilon_rel), alpha=float(args.alpha))

        named = {
            "router": eval_router,
            "forced_fast": eval_fast,
            "forced_slow": eval_slow,
            "strongest_baseline": eval_base,
        }
        for name, mm in named.items():
            strategy_seed_rows.append(
                {
                    "seed": int(seed),
                    "strategy": name,
                    "n_cases": int(mm["n"]),
                    "fast_ratio": mm["fast_ratio"],
                    "easy_fast_ratio": mm["easy_fast_ratio"],
                    "hard_fast_ratio": mm["hard_fast_ratio"],
                    "violation_rate": mm["violation_rate"],
                    "violation_ci95_upper": mm["violation_ci95_upper"],
                    "j_mean": mm["j_mean"],
                    "latency_mean_ms": mm["latency_mean_ms"],
                }
            )

        ood_mask = df["ood_family"].to_numpy(dtype=np.int32) == 1
        if np.any(ood_mask):
            ood_base = eval_base["j"][ood_mask]
            ood_router = eval_router["j"][ood_mask]
            ood_base_all.extend(ood_base.tolist())
            ood_router_all.extend(ood_router.tolist())
            ood_diff_all.extend((ood_base - ood_router).tolist())

    seed_df = pd.DataFrame(strategy_seed_rows)
    if seed_df.empty:
        raise RuntimeError("No strategy metrics computed on test split.")

    # Pooled-by-strategy metrics.
    pooled_rows = []
    for strategy, g in seed_df.groupby("strategy", as_index=False):
        pooled_rows.append(
            {
                "strategy": strategy,
                "n_cases_total": int(g["n_cases"].sum()),
                "fast_ratio_mean": float(g["fast_ratio"].mean()),
                "easy_fast_ratio_mean": float(g["easy_fast_ratio"].mean()),
                "hard_fast_ratio_mean": float(g["hard_fast_ratio"].mean()),
                "violation_rate_mean": float(g["violation_rate"].mean()),
                "violation_ci95_upper_mean": float(g["violation_ci95_upper"].mean()),
                "j_mean": float(g["j_mean"].mean()),
                "latency_mean_ms": float(g["latency_mean_ms"].mean()),
            }
        )
    pooled_df = pd.DataFrame(pooled_rows).sort_values("strategy").reset_index(drop=True)

    get_row = lambda s: pooled_df[pooled_df["strategy"] == s].iloc[0]
    row_router = get_row("router")
    row_fast = get_row("forced_fast")
    row_slow = get_row("forced_slow")
    row_base = get_row("strongest_baseline")

    delta_j_vs_fast = float((row_fast["j_mean"] - row_router["j_mean"]) / max(abs(row_fast["j_mean"]), 1e-12))
    latency_improve_vs_slow = float(
        (row_slow["latency_mean_ms"] - row_router["latency_mean_ms"]) / max(abs(row_slow["latency_mean_ms"]), 1e-12)
    )

    ood_base_arr = np.array(ood_base_all, dtype=np.float64)
    ood_router_arr = np.array(ood_router_all, dtype=np.float64)
    ood_diff = np.array(ood_diff_all, dtype=np.float64)
    if ood_diff.size <= 0:
        raise RuntimeError("OOD subset is empty; cannot run Step-3 statistical tests.")

    ood_delta_j = float((np.mean(ood_base_arr) - np.mean(ood_router_arr)) / max(abs(np.mean(ood_base_arr)), 1e-12))
    p_boot, ci_boot, mean_boot = _bootstrap_mean_gt0(ood_diff, iters=int(args.bootstrap_iters), rng=rng)
    p_wil = _wilcoxon_pvalue_greater(ood_diff)
    p_perm = _permutation_signflip_pvalue(ood_diff, iters=int(args.perm_iters), rng=rng)
    cliffs = _cliffs_delta(ood_base_arr, ood_router_arr)

    tests_df = pd.DataFrame(
        [
            {
                "test": "bootstrap_mean_diff_gt0",
                "stat": mean_boot,
                "p_value": p_boot,
                "ci95_low": ci_boot[0],
                "ci95_high": ci_boot[1],
            },
            {
                "test": "wilcoxon_paired_greater",
                "stat": float(np.mean(ood_diff)),
                "p_value": p_wil,
                "ci95_low": float("nan"),
                "ci95_high": float("nan"),
            },
            {
                "test": "permutation_signflip_greater",
                "stat": float(np.mean(ood_diff)),
                "p_value": p_perm,
                "ci95_low": float("nan"),
                "ci95_high": float("nan"),
            },
            {
                "test": "cliffs_delta_base_vs_router",
                "stat": cliffs,
                "p_value": float("nan"),
                "ci95_low": float("nan"),
                "ci95_high": float("nan"),
            },
        ]
    )

    # Gate checks from TASK Step-3.
    gate = {
        "fast_ratio_not_degenerate": bool(0.35 <= float(row_router["fast_ratio_mean"]) <= 0.85),
        "stratified_split_valid": bool(
            (float(row_router["easy_fast_ratio_mean"]) >= 0.80) and (float(row_router["hard_fast_ratio_mean"]) <= 0.40)
        ),
        "deltaJ_vs_forced_fast_ge_3pct": bool(delta_j_vs_fast >= 0.03),
        "latency_vs_forced_slow_improve_ge_10pct": bool(latency_improve_vs_slow >= 0.10),
        "risk_violation_rate_le_6pct": bool(float(row_router["violation_rate_mean"]) <= 0.06),
        "risk_ci95_upper_le_8pct": bool(float(row_router["violation_ci95_upper_mean"]) <= 0.08),
        "ood_pooled_deltaJ_gt_0": bool(ood_delta_j > 0.0),
        "ood_p_value_lt_0_01": bool(p_boot < 0.01),
        "effect_size_cliffs_delta_ge_0_147": bool(cliffs >= 0.147),
    }

    # Save artifacts.
    selected_csv = args.out_dir / "discriminative_set.csv"
    ood_csv = args.out_dir / "ood_set.csv"
    search_log_csv = args.out_dir / "policy_selection_log.csv"
    seed_metrics_csv = args.out_dir / "seed_strategy_metrics.csv"
    stats_tests_csv = args.out_dir / "stats_tests.csv"
    stats_json = args.out_dir / "stats.json"

    selected.sort_values(["split_tag", "difficulty", "sample_name"]).to_csv(selected_csv, index=False)
    selected[(selected["split_tag"] == "test") & (selected["ood_family"].astype(np.int32) == 1)].to_csv(ood_csv, index=False)
    search_log_df.to_csv(search_log_csv, index=False)
    seed_df.to_csv(seed_metrics_csv, index=False)
    tests_df.to_csv(stats_tests_csv, index=False)

    # table_adaptive_value.csv
    table_adaptive_df = pooled_df.copy()
    table_adaptive_df["delta_j_vs_forced_fast"] = np.nan
    table_adaptive_df["latency_improve_vs_forced_slow"] = np.nan
    table_adaptive_df["ood_delta_j_vs_strongest"] = np.nan
    mask_router = table_adaptive_df["strategy"] == "router"
    table_adaptive_df.loc[mask_router, "delta_j_vs_forced_fast"] = delta_j_vs_fast
    table_adaptive_df.loc[mask_router, "latency_improve_vs_forced_slow"] = latency_improve_vs_slow
    table_adaptive_df.loc[mask_router, "ood_delta_j_vs_strongest"] = ood_delta_j
    table_adaptive_df.to_csv(args.table_adaptive_csv, index=False)
    tests_df.to_csv(args.table_stats_csv, index=False)

    stats = {
        "version": "router_adaptive_value_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": [int(s) for s in seeds],
        "selected_policy": {
            "feature": "probe_score",
            "tau_easy": float(selected_policy["tau_easy"]),
            "tau_medium": float(selected_policy["tau_medium"]),
            "tau_hard": float(selected_policy["tau_hard"]),
        },
        "dataset": {
            "num_cases": int(len(selected)),
            "calib_cases": int(np.sum(selected["split_tag"] == "calib")),
            "test_cases": int(np.sum(selected["split_tag"] == "test")),
            "ood_test_cases": int(np.sum((selected["split_tag"] == "test") & (selected["ood_family"].astype(np.int32) == 1))),
            "difficulty_counts": {k: int(v) for k, v in selected["difficulty"].astype(str).value_counts().to_dict().items()},
            "bucket_counts": {k: int(v) for k, v in selected["bucket"].astype(str).value_counts().to_dict().items()},
        },
        "summary": {
            "router_fast_ratio_mean": float(row_router["fast_ratio_mean"]),
            "router_easy_fast_ratio_mean": float(row_router["easy_fast_ratio_mean"]),
            "router_hard_fast_ratio_mean": float(row_router["hard_fast_ratio_mean"]),
            "router_violation_rate_mean": float(row_router["violation_rate_mean"]),
            "router_violation_ci95_upper_mean": float(row_router["violation_ci95_upper_mean"]),
            "delta_j_vs_forced_fast": delta_j_vs_fast,
            "latency_improve_vs_forced_slow": latency_improve_vs_slow,
            "ood_pooled_delta_j_vs_strongest": ood_delta_j,
            "ood_bootstrap_p_value": p_boot,
            "ood_wilcoxon_p_value": p_wil,
            "ood_permutation_p_value": p_perm,
            "ood_cliffs_delta": cliffs,
        },
        "gate_check": gate,
        "artifacts": {
            "discriminative_set_csv": str(selected_csv),
            "ood_set_csv": str(ood_csv),
            "policy_selection_log_csv": str(search_log_csv),
            "seed_strategy_metrics_csv": str(seed_metrics_csv),
            "stats_tests_csv": str(stats_tests_csv),
            "table_adaptive_value_csv": str(args.table_adaptive_csv),
            "table_stats_hardening_csv": str(args.table_stats_csv),
            "report_md": str(args.report_md),
        },
    }
    stats_json.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    _write_report(path=args.report_md, stats=stats, strategy_df=table_adaptive_df, tests_df=tests_df)

    print(f"[adaptive_v1] stats={stats_json}")
    print(f"[adaptive_v1] report={args.report_md}")
    print(f"[adaptive_v1] gate={gate}")
    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("adaptive_value_v1 gate failed")


if __name__ == "__main__":
    main()
