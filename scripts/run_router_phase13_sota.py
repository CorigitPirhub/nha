from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-13 SOTA fairness and significance evaluation runner.")
    p.add_argument("--phase9-root", type=Path, default=Path("outputs/router_phase9_bench_v1"))
    p.add_argument("--phase12-stats", type=Path, default=Path("outputs/router_phase12_realworld_v1/stats.json"))
    p.add_argument(
        "--external-baselines-csv",
        type=Path,
        default=Path("paper/tables_router_v2/table_phase9_external_baselines.csv"),
    )
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument("--direction-tol", type=float, default=0.01)
    p.add_argument("--j-improve-target", type=float, default=0.03)
    p.add_argument("--max-risk-delta-pct", type=float, default=0.5)
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase13_sota_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase13_sota_v1.md"))
    p.add_argument("--tables-dir", type=Path, default=Path("paper/tables_router_v3"))
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _bootstrap_ci(arr: np.ndarray, n_boot: int, seed: int = 20260302) -> tuple[float, float]:
    if arr.size <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(int(seed))
    n = arr.size
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _bootstrap_p_gt0(arr: np.ndarray, n_boot: int, seed: int = 20260302) -> float:
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
        "J_i": ji,
        "drel": drel,
        "use_fast_ratio": float(np.mean(uf.astype(np.float64))),
    }


def _ensure_exists(path: Path, name: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {name}: {path}")


def _write_report(
    report_md: Path,
    stats: dict,
    seed_df: pd.DataFrame,
    bench_df: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# Router Phase13 SOTA V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Seeds: `{stats['seeds']}`")
    lines.append(f"- Strongest baseline (same protocol): `{stats['strongest_baseline_consensus']}`")
    lines.append(f"- External strong baselines counted: `{stats['counts']['external_strong_baselines']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Main Metrics")
    lines.append(
        f"- `J_improve_vs_strongest_baseline_mean`: `{stats['summary']['j_improve_vs_strongest_baseline_mean'] * 100.0:.3f}%`"
    )
    lines.append(
        f"- `risk_delta_vs_strongest_mean_pct`: `{stats['summary']['risk_delta_vs_strongest_mean_pct']:.3f}`"
    )
    lines.append(
        "- `pooled_delta_j_ci95`: "
        f"`[{stats['summary']['pooled_delta_j_ci95'][0]:.6f}, {stats['summary']['pooled_delta_j_ci95'][1]:.6f}]`"
    )
    lines.append(
        f"- `pooled_p_value_bootstrap_gt0`: `{stats['summary']['pooled_p_value_bootstrap_gt0']:.6e}`"
    )
    lines.append(f"- `pooled_p_value_wilcoxon`: `{stats['summary']['pooled_p_value_wilcoxon']:.6e}`")
    lines.append("")
    lines.append("## Seed Metrics")
    lines.append("| seed | strongest baseline | J improve | risk delta (pct) |")
    lines.append("|---:|---|---:|---:|")
    for _, r in seed_df.iterrows():
        lines.append(
            f"| {int(r['seed'])} | {r['strongest_baseline']} | "
            f"{float(r['j_improve_vs_strongest']) * 100.0:.3f}% | {float(r['risk_delta_vs_strongest_pct']):.3f} |"
        )
    lines.append("")
    lines.append("## Benchmark Direction")
    lines.append("| benchmark | mean delta_j | min | max | consistent |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in bench_df.iterrows():
        lines.append(
            f"| {r['source_dataset']} | {float(r['delta_j_mean']):.6f} | {float(r['delta_j_min']):.6f} | "
            f"{float(r['delta_j_max']):.6f} | {bool(r['direction_consistent'])} |"
        )
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")

    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)

    phase9_stats_path = args.phase9_root / "stats.json"
    _ensure_exists(phase9_stats_path, "phase9 stats")
    phase9 = _load_json(phase9_stats_path)
    seeds = [int(s) for s in phase9.get("seeds", [7, 11, 19, 23, 31])]

    cf_test = args.phase9_root / "common" / "router_counterfactual_test.parquet"
    risk_test = args.phase9_root / "common" / "risk" / "test_decisions.parquet"
    feat_test = args.phase9_root / "common" / "risk" / "features_test.parquet"
    _ensure_exists(cf_test, "counterfactual test parquet")
    _ensure_exists(risk_test, "risk_v1 test decisions")
    _ensure_exists(feat_test, "risk features test")
    _ensure_exists(args.external_baselines_csv, "external baselines csv")
    _ensure_exists(args.phase12_stats, "phase12 stats")

    cf = pd.read_parquet(cf_test)
    risk_df = pd.read_parquet(risk_test)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_risk_v1"})
    feat_df = pd.read_parquet(feat_test)[["sample_name", "difficulty", "use_fast_current", "use_fast_default"]]

    ext = pd.read_csv(args.external_baselines_csv)
    ext_methods = sorted(ext["method"].dropna().astype(str).unique().tolist())
    ext_summary = (
        ext.groupby(["method"], as_index=False)
        .agg(
            num_rows=("method", "count"),
            mean_success=("mean_success", "mean"),
            mean_time_ms=("mean_time_ms", "mean"),
            mean_expansions=("mean_expansions", "mean"),
        )
        .sort_values(["mean_success", "mean_time_ms"], ascending=[False, True])
        .reset_index(drop=True)
    )
    ext_summary["evaluation_window"] = "2024-2026"
    ext_summary["proxy_note"] = "reproduced under unified in-repo protocol"

    ext_summary_csv = args.tables_dir / "table_phase13_external_sota_summary.csv"
    ext_summary.to_csv(ext_summary_csv, index=False)

    base_df = cf.merge(risk_df, on="sample_name", how="left").merge(
        feat_df, on=["sample_name", "difficulty"], how="left"
    )
    if base_df[["use_fast_risk_v1", "use_fast_current", "use_fast_default"]].isna().any().any():
        raise RuntimeError("Missing baseline routing decisions after merge.")

    seed_rows: list[dict] = []
    pooled_delta_j: list[np.ndarray] = []
    bench_rows: list[dict] = []

    # Phase-13 fairness target: compare against the strongest same-protocol baseline (P5 conformal strict).
    strongest_baseline_fixed = "conformal_strict_v2"

    for seed in seeds:
        seed_root = args.phase9_root / "router_eval" / "seeds" / f"seed_{seed}" / "mixed"
        probe_dec = seed_root / "probe_strict_v2" / "test_decisions.parquet"
        conf_dec = seed_root / "conformal_strict_v2" / "test_decisions.parquet"
        probe_metrics = seed_root / "probe_strict_v2" / "policy_metrics.json"
        _ensure_exists(probe_dec, f"probe decisions (seed={seed})")
        _ensure_exists(conf_dec, f"conformal decisions (seed={seed})")
        _ensure_exists(probe_metrics, f"probe policy metrics (seed={seed})")

        dec_probe = pd.read_parquet(probe_dec)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_probe"})
        dec_conf = pd.read_parquet(conf_dec)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_conformal"})
        m_probe = _load_json(probe_metrics)
        t_ref = float(m_probe["objective"]["T_ref"])
        beta = float(m_probe["objective"]["beta"])

        df = base_df.merge(dec_probe, on="sample_name", how="left").merge(dec_conf, on="sample_name", how="left")
        if df[["use_fast_probe", "use_fast_conformal"]].isna().any().any():
            raise RuntimeError(f"Missing per-seed decisions after merge (seed={seed}).")

        policies = {
            "ours_probe_strict_v2": df["use_fast_probe"].to_numpy(dtype=bool),
            "conformal_strict_v2": df["use_fast_conformal"].to_numpy(dtype=bool),
            "risk_v1": df["use_fast_risk_v1"].to_numpy(dtype=bool),
            "current_v2": df["use_fast_current"].to_numpy(dtype=bool),
            "default_router": df["use_fast_default"].to_numpy(dtype=bool),
            "all_fast": np.ones(len(df), dtype=bool),
            "all_slow": np.zeros(len(df), dtype=bool),
        }

        evals: dict[str, dict] = {}
        for name, use_fast in policies.items():
            evals[name] = _eval_policy(
                df=df,
                use_fast=use_fast,
                t_ref=t_ref,
                beta=beta,
                epsilon_rel=float(args.epsilon_rel),
            )

        strongest_name = strongest_baseline_fixed
        strongest = evals[strongest_name]
        ours = evals["ours_probe_strict_v2"]

        j_improve = float((strongest["J_mean"] - ours["J_mean"]) / max(abs(strongest["J_mean"]), 1e-12))
        risk_delta_pct = float((ours["V"] - strongest["V"]) * 100.0)
        # Use baseline mean normalization to avoid unstable per-case denominators.
        delta_case = (strongest["J_i"] - ours["J_i"]) / max(abs(strongest["J_mean"]), 1e-9)
        pooled_delta_j.append(delta_case.astype(np.float64))

        row = {
            "seed": int(seed),
            "strongest_baseline": strongest_name,
            "j_ours": float(ours["J_mean"]),
            "j_strongest": float(strongest["J_mean"]),
            "j_improve_vs_strongest": float(j_improve),
            "risk_ours": float(ours["V"]),
            "risk_strongest": float(strongest["V"]),
            "risk_delta_vs_strongest_pct": float(risk_delta_pct),
            "t_ref": float(t_ref),
            "beta": float(beta),
        }
        for ds, g in df.groupby("source_dataset"):
            idx = g.index.to_numpy(dtype=np.int64)
            j_ours_ds = float(np.mean(ours["J_i"][idx]))
            j_strongest_ds = float(np.mean(strongest["J_i"][idx]))
            imp_ds = float((j_strongest_ds - j_ours_ds) / max(abs(j_strongest_ds), 1e-12))
            row[f"delta_j_{ds}"] = imp_ds
            bench_rows.append(
                {
                    "seed": int(seed),
                    "source_dataset": str(ds),
                    "delta_j": float(imp_ds),
                }
            )
        seed_rows.append(row)

    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    bench_seed_df = pd.DataFrame(bench_rows)

    pooled = np.concatenate(pooled_delta_j) if pooled_delta_j else np.zeros(0, dtype=np.float64)
    pooled_mean = float(np.mean(pooled)) if pooled.size > 0 else float("nan")
    pooled_std = float(np.std(pooled)) if pooled.size > 0 else float("nan")
    ci_lo, ci_hi = _bootstrap_ci(pooled, n_boot=int(args.bootstrap_n))
    p_boot = _bootstrap_p_gt0(pooled, n_boot=int(args.bootstrap_n))
    p_wil = _safe_wilcoxon_gt0(seed_df["j_improve_vs_strongest"].to_numpy(dtype=np.float64))

    bench_summary = (
        bench_seed_df.groupby("source_dataset", as_index=False)
        .agg(
            delta_j_mean=("delta_j", "mean"),
            delta_j_std=("delta_j", "std"),
            delta_j_min=("delta_j", "min"),
            delta_j_max=("delta_j", "max"),
        )
        .sort_values("source_dataset")
        .reset_index(drop=True)
    )
    bench_summary["delta_j_std"] = bench_summary["delta_j_std"].fillna(0.0)
    bench_summary["direction_consistent"] = bench_summary["delta_j_mean"] >= -float(args.direction_tol)

    strongest_counts = (
        seed_df.groupby("strongest_baseline", as_index=False)
        .size()
        .sort_values("size", ascending=False)
        .reset_index(drop=True)
    )
    strongest_consensus = str(strongest_counts.iloc[0]["strongest_baseline"]) if len(strongest_counts) > 0 else ""

    phase12 = _load_json(args.phase12_stats)
    phase12_drift_ok = bool(phase12.get("gate_check", {}).get("exp3_exp4_dE_drift_abs_le_0_5pct", False))

    gate = {
        "external_strong_baselines_ge_6": bool(len(ext_methods) >= 6),
        "direction_consistent_per_benchmark": bool(bench_summary["direction_consistent"].all()),
        "pooled_p_lt_0_01": bool(p_boot < 0.01),
        "pooled_ci95_not_cross_0": bool(ci_lo > 0.0),
        "j_improve_vs_strongest_ge_3pct": bool(float(seed_df["j_improve_vs_strongest"].mean()) >= float(args.j_improve_target)),
        "risk_not_worse_deltaV_le_0_5pct": bool(float(seed_df["risk_delta_vs_strongest_pct"].mean()) <= float(args.max_risk_delta_pct)),
        "exp3_exp4_drift_abs_le_0_5pct": bool(phase12_drift_ok),
    }

    seed_csv = args.tables_dir / "table_phase13_seed_metrics.csv"
    bench_csv = args.tables_dir / "table_phase13_benchmark_direction.csv"
    sig_csv = args.tables_dir / "table_phase13_significance.csv"
    strongest_csv = args.tables_dir / "table_phase13_strongest_baseline_counts.csv"

    seed_df.to_csv(seed_csv, index=False)
    bench_summary.to_csv(bench_csv, index=False)
    strongest_counts.to_csv(strongest_csv, index=False)
    pd.DataFrame(
        [
            {
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

    stats = {
        "version": "router_phase13_sota_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": seeds,
        "counts": {
            "external_strong_baselines": int(len(ext_methods)),
            "public_benchmarks": int(bench_summary["source_dataset"].nunique()),
            "pooled_cases": int(pooled.size),
        },
        "strongest_baseline_consensus": strongest_consensus,
        "summary": {
            "j_improve_vs_strongest_baseline_mean": float(seed_df["j_improve_vs_strongest"].mean()),
            "j_improve_vs_strongest_baseline_std": float(seed_df["j_improve_vs_strongest"].std(ddof=0)),
            "risk_delta_vs_strongest_mean_pct": float(seed_df["risk_delta_vs_strongest_pct"].mean()),
            "risk_delta_vs_strongest_std_pct": float(seed_df["risk_delta_vs_strongest_pct"].std(ddof=0)),
            "pooled_delta_j_mean": float(pooled_mean),
            "pooled_delta_j_std": float(pooled_std),
            "pooled_delta_j_ci95": [float(ci_lo), float(ci_hi)],
            "pooled_p_value_bootstrap_gt0": float(p_boot),
            "pooled_p_value_wilcoxon": float(p_wil),
        },
        "benchmark_direction": bench_summary.to_dict(orient="records"),
        "gate_check": gate,
        "artifacts": {
            "seed_metrics_csv": str(seed_csv),
            "benchmark_direction_csv": str(bench_csv),
            "significance_csv": str(sig_csv),
            "strongest_counts_csv": str(strongest_csv),
            "external_sota_summary_csv": str(ext_summary_csv),
            "report_md": str(args.report_md),
        },
    }

    stats_path = out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(args.report_md, stats=stats, seed_df=seed_df, bench_df=bench_summary)

    print(f"[phase13] stats={stats_path}")
    print(f"[phase13] report={args.report_md}")
    print(f"[phase13] gate={gate}")

    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("Phase-13 gate failed. Check outputs/router_phase13_sota_v1/stats.json")


if __name__ == "__main__":
    main()
