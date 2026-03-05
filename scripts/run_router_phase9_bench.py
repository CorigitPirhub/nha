from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.parquet_guard import INPUTS_SHA256_FILENAME, compare_record, mismatch_summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-9 cross-benchmark generalization runner.")
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase9_bench_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase9_bench_v1.md"))
    p.add_argument("--tables-dir", type=Path, default=Path("paper/tables_router_v2"))
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument(
        "--direction-tol",
        type=float,
        default=0.01,
        help="Per-benchmark direction tolerance on mean_delta_j (allow tiny negative drift).",
    )

    # Phase-8 strict selection knobs (forwarded to scripts/run_router_phase8_strict.py).
    p.add_argument(
        "--calib-split-mode",
        type=str,
        default="train_val",
        choices=["none", "train_val"],
        help="Forwarded to Phase-8 strict: how to split the calibration split for selection.",
    )
    p.add_argument(
        "--calib-train-frac",
        type=float,
        default=0.60,
        help="Forwarded to Phase-8 strict: fraction of calib used as calib_train when --calib-split-mode=train_val.",
    )
    p.add_argument(
        "--calib-split-seed",
        type=int,
        default=20260302,
        help="Forwarded to Phase-8 strict: deterministic seed for calib_train/calib_val split.",
    )
    p.add_argument(
        "--conformal-select-on",
        type=str,
        default="calib",
        choices=["calib", "test"],
        help="Forwarded to Phase-8 strict: which split is used to select conformal hyperparameters.",
    )
    p.add_argument(
        "--probe-search-on",
        type=str,
        default="calib",
        choices=["calib", "test"],
        help="Forwarded to Phase-8 strict: which split is used to search probe flip counts.",
    )
    p.add_argument(
        "--phase8-strict-violation-target",
        type=float,
        default=0.20,
        help="Forwarded to Phase-8 strict: strict_violation_target (used for final evaluation).",
    )
    p.add_argument(
        "--phase8-strict-ci-upper-target",
        type=float,
        default=0.22,
        help="Forwarded to Phase-8 strict: strict_ci_upper_target (used for final evaluation).",
    )
    p.add_argument(
        "--phase8-strict-tune-violation-margin",
        type=float,
        default=0.14,
        help="Forwarded to Phase-8 strict: margin subtracted from strict_violation_target when tuning on the selection split.",
    )
    p.add_argument(
        "--phase8-strict-tune-ci-margin",
        type=float,
        default=0.13,
        help="Forwarded to Phase-8 strict: margin subtracted from strict_ci_upper_target when tuning on the selection split.",
    )
    p.add_argument(
        "--phase8-probe-include-cost-feature",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Forwarded to Phase-8 strict: include cost proxy `c` as a probe gain feature (cost-aware ranking).",
    )
    p.add_argument(
        "--phase8-probe-selection-mode",
        type=str,
        default="grid_search",
        choices=["grid_search", "conformal_lcb", "knapsack_lcb"],
        help="Forwarded to Phase-8 strict: probe selection mode.",
    )
    p.add_argument(
        "--phase8-probe-lcb-alpha",
        type=float,
        default=0.10,
        help="Forwarded to Phase-8 strict: miscoverage alpha for conformal_lcb mode.",
    )

    # Report path overrides for subroutines (avoid overwriting v1 reports when running audits).
    p.add_argument(
        "--risk-report-md",
        type=Path,
        default=None,
        help="Optional report path for Phase-4 risk. Default derives from --report-md.",
    )
    p.add_argument(
        "--router-eval-report-md",
        type=Path,
        default=None,
        help="Optional report path for Phase-8 router_eval. Default derives from --report-md.",
    )
    p.add_argument("--force", action="store_true")
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


def _run(cmd: list[str], log_path: Path, env_extra: dict[str, str] | None = None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(cmd)}\n")
        f.flush()
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        f.write(proc.stdout)
        f.flush()
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}; see {log_path}")


def _bootstrap_ci(arr: np.ndarray, n_boot: int, seed: int = 20260302) -> tuple[float, float]:
    if arr.size <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(int(seed))
    n = arr.size
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    lo = float(np.quantile(means, 0.025))
    hi = float(np.quantile(means, 0.975))
    return lo, hi


def _bootstrap_p_gt0(arr: np.ndarray, n_boot: int, seed: int = 20260302) -> float:
    if arr.size <= 0:
        return 1.0
    rng = np.random.default_rng(int(seed))
    n = arr.size
    means = np.empty(int(max(n_boot, 1)), dtype=np.float64)
    for i in range(means.size):
        idx = rng.integers(0, n, size=n)
        means[i] = float(np.mean(arr[idx]))
    # One-sided: p-value for H1(mean_delta_j > 0).
    return float(np.mean(means <= 0.0))


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _build_dataset(args: argparse.Namespace, log: Path) -> Path:
    manifest = args.dataset_root / "manifest.json"
    if args.force or not manifest.exists():
        _run(
            [
                sys.executable,
                "scripts/build_router_phase9_dataset.py",
                "--benchmark-root",
                str(args.benchmark_root),
                "--out-root",
                str(args.dataset_root),
            ],
            log_path=log,
        )
    return manifest


def _run_counterfactual(args: argparse.Namespace, split: str, out_root: Path, log: Path) -> tuple[Path, Path]:
    out_pq = out_root / f"router_counterfactual_{split}.parquet"
    out_js = out_root / f"router_counterfactual_{split}_report.json"
    if args.force or (not out_pq.exists()) or (not out_js.exists()):
        _run(
            [
                sys.executable,
                "scripts/run_router_counterfactual.py",
                "--dataset-root",
                str(args.dataset_root),
                "--split",
                split,
                "--checkpoint",
                str(args.checkpoint),
                "--device",
                str(args.device),
                "--out-parquet",
                str(out_pq),
                "--out-report",
                str(out_js),
            ],
            log_path=log,
        )
    return out_pq, out_js


def _run_risk_features(
    args: argparse.Namespace,
    calib_pq: Path,
    test_pq: Path,
    risk_out: Path,
    log: Path,
) -> None:
    metrics = risk_out / "policy_metrics.json"
    if args.force or not metrics.exists():
        _run(
            [
                sys.executable,
                "scripts/run_router_risk_v1.py",
                "--dataset-root",
                str(args.dataset_root),
                "--calib-parquet",
                str(calib_pq),
                "--test-parquet",
                str(test_pq),
                "--easy-fast-min",
                "0.0",
                "--easy-fast-max",
                "1.0",
                "--medium-fast-min",
                "0.0",
                "--medium-fast-max",
                "1.0",
                "--hard-fast-min",
                "0.0",
                "--hard-fast-max",
                "1.0",
                "--min-j-improve",
                "-1.0",
                "--out-dir",
                str(risk_out),
                "--report-md",
                str(args.risk_report_md),
            ],
            log_path=log,
        )


def _run_router_eval(
    args: argparse.Namespace,
    seeds: list[int],
    calib_pq: Path,
    test_pq: Path,
    risk_out: Path,
    out_dir: Path,
    log: Path,
) -> Path:
    stats = out_dir / "stats.json"
    if args.force or not stats.exists():
        _run(
            [
                sys.executable,
                "scripts/run_router_phase8_strict.py",
                "--seeds",
                ",".join(str(s) for s in seeds),
                "--dataset-root",
                str(args.dataset_root),
                "--calib-parquet",
                str(calib_pq),
                "--test-parquet",
                str(test_pq),
                "--static-features-calib",
                str(risk_out / "features_calib.parquet"),
                "--static-features-test",
                str(risk_out / "features_test.parquet"),
                "--probe-features-calib",
                str(out_dir / "common" / "probe_features_calib.parquet"),
                "--probe-features-test",
                str(out_dir / "common" / "probe_features_test.parquet"),
                "--strict-violation-target",
                str(float(args.phase8_strict_violation_target)),
                "--strict-ci-upper-target",
                str(float(args.phase8_strict_ci_upper_target)),
                "--strict-tune-violation-margin",
                str(float(args.phase8_strict_tune_violation_margin)),
                "--strict-tune-ci-margin",
                str(float(args.phase8_strict_tune_ci_margin)),
                "--calib-split-mode",
                str(args.calib_split_mode),
                "--calib-train-frac",
                str(float(args.calib_train_frac)),
                "--calib-split-seed",
                str(int(args.calib_split_seed)),
                "--conformal-select-on",
                str(args.conformal_select_on),
                "--probe-search-on",
                str(args.probe_search_on),
                "--probe-include-cost-feature" if bool(args.phase8_probe_include_cost_feature) else "--no-probe-include-cost-feature",
                "--probe-selection-mode",
                str(args.phase8_probe_selection_mode),
                "--probe-lcb-alpha",
                str(float(args.phase8_probe_lcb_alpha)),
                "--no-enforce-gate",
                "--out-dir",
                str(out_dir),
                "--report-md",
                str(args.router_eval_report_md),
            ],
            log_path=log,
        )
    return stats


def _compute_benchmark_metrics(
    seeds: list[int],
    cf_test: pd.DataFrame,
    router_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    seed_rows: list[dict] = []
    pooled_delta: list[np.ndarray] = []
    by_seed_ds: list[dict] = []

    for seed in seeds:
        seed_root = router_dir / "seeds" / f"seed_{seed}" / "mixed"
        p5_dec = pd.read_parquet(seed_root / "conformal_strict_v2" / "test_decisions.parquet")[["sample_name", "use_fast"]]
        p5_dec = p5_dec.rename(columns={"use_fast": "use_fast_p5"})
        p6_dec = pd.read_parquet(seed_root / "probe_strict_v2" / "test_decisions.parquet")[["sample_name", "use_fast"]]
        p6_dec = p6_dec.rename(columns={"use_fast": "use_fast_router"})
        m_probe = _load_json(seed_root / "probe_strict_v2" / "policy_metrics.json")

        t_ref = float(m_probe["objective"]["T_ref"])
        beta = float(m_probe["objective"]["beta"])

        df = cf_test.merge(p5_dec, on="sample_name", how="inner").merge(p6_dec, on="sample_name", how="inner")
        if len(df) != len(cf_test):
            raise RuntimeError(f"Decision merge mismatch on seed {seed}: {len(df)} vs {len(cf_test)}")

        j_fast = df["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + beta * np.maximum(
            df["q_rel"].to_numpy(dtype=np.float64), 0.0
        )
        j_slow = df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
        j_p5 = np.where(df["use_fast_p5"].to_numpy(dtype=bool), j_fast, j_slow)
        j_router = np.where(df["use_fast_router"].to_numpy(dtype=bool), j_fast, j_slow)
        d_j = (j_p5 - j_router).astype(np.float64)
        pooled_delta.append(d_j)

        seed_rows.append(
            {
                "seed": int(seed),
                "mean_delta_j": float(np.mean(d_j)),
                "median_delta_j": float(np.median(d_j)),
                "num_cases": int(len(d_j)),
            }
        )

        for ds in sorted(df["source_dataset"].unique().tolist()):
            mask = df["source_dataset"].to_numpy() == ds
            by_seed_ds.append(
                {
                    "seed": int(seed),
                    "source_dataset": str(ds),
                    "num_cases": int(np.sum(mask)),
                    "mean_delta_j": float(np.mean(d_j[mask])),
                    "median_delta_j": float(np.median(d_j[mask])),
                }
            )

    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    ds_df = pd.DataFrame(by_seed_ds).sort_values(["source_dataset", "seed"]).reset_index(drop=True)
    all_delta = np.concatenate(pooled_delta) if pooled_delta else np.zeros(0, dtype=np.float64)
    return seed_df, ds_df, all_delta


def _write_report(path: Path, stats: dict) -> None:
    lines: list[str] = []
    lines.append("# Router Phase9 Bench V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Public benchmarks: `{stats['counts']['num_public_benchmarks']}`")
    lines.append(f"- Public test cases: `{stats['counts']['num_public_test_cases']}`")
    lines.append(f"- OOD map families (test): `{stats['counts']['num_ood_map_families']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Main Statistics")
    lines.append(f"- `pooled_mean_delta_j`: `{stats['pooled']['mean_delta_j']:.6f}`")
    lines.append(
        f"- `pooled_mean_delta_j_95ci`: `[{stats['pooled']['ci95'][0]:.6f}, {stats['pooled']['ci95'][1]:.6f}]`"
    )
    lines.append(f"- `pooled_p_value_bootstrap_gt0`: `{stats['pooled']['p_value_bootstrap_gt0']:.6e}`")
    lines.append(f"- `pooled_p_value_wilcoxon`: `{stats['pooled']['p_value_wilcoxon']:.6e}`")
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    seeds = _parse_seeds(args.seeds)

    if args.risk_report_md is None:
        args.risk_report_md = args.report_md.with_name(f"{args.report_md.stem}_risk.md")
    if args.router_eval_report_md is None:
        args.router_eval_report_md = args.report_md.with_name(f"{args.report_md.stem}_router_eval.md")

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = args.tables_dir
    tables_dir.mkdir(parents=True, exist_ok=True)
    run_log = out_dir / "run.log"

    # Cache guard: bind downstream outputs to the counterfactual input parquets.
    # If the input parquets are overwritten, force a full rerun to avoid stale skip logic.
    if not bool(args.force):
        common_dir = out_dir / "common"
        calib_pq = common_dir / "router_counterfactual_calib.parquet"
        test_pq = common_dir / "router_counterfactual_test.parquet"
        force_reason = None

        risk_out = common_dir / "risk"
        risk_metrics = risk_out / "policy_metrics.json"
        if risk_metrics.exists():
            try:
                ok, cur, prev = compare_record(
                    risk_out / INPUTS_SHA256_FILENAME,
                    {"calib_parquet": calib_pq, "test_parquet": test_pq},
                )
                if not ok:
                    force_reason = f"risk inputs changed ({mismatch_summary(cur, prev)})"
            except Exception as exc:
                force_reason = f"risk cache check failed ({exc})"

        router_eval_out = out_dir / "router_eval"
        router_stats = router_eval_out / "stats.json"
        if (force_reason is None) and router_stats.exists():
            probe_cal = router_eval_out / "common" / "probe_features_calib.parquet"
            probe_te = router_eval_out / "common" / "probe_features_test.parquet"
            try:
                ok, cur, prev = compare_record(
                    router_eval_out / INPUTS_SHA256_FILENAME,
                    {
                        "calib_parquet": calib_pq,
                        "test_parquet": test_pq,
                        "static_features_calib": common_dir / "risk" / "features_calib.parquet",
                        "static_features_test": common_dir / "risk" / "features_test.parquet",
                        "probe_features_calib": probe_cal,
                        "probe_features_test": probe_te,
                    },
                )
                if not ok:
                    force_reason = f"router_eval inputs changed ({mismatch_summary(cur, prev)})"
            except Exception as exc:
                force_reason = f"router_eval cache check failed ({exc})"

        if force_reason is not None:
            print(f"[phase9] parquet overwrite detected: {force_reason}; forcing full rerun.")
            args.force = True

    manifest = _build_dataset(args, log=run_log)
    manifest_data = _load_json(manifest)

    common = out_dir / "common"
    common.mkdir(parents=True, exist_ok=True)
    calib_pq, _calib_rep = _run_counterfactual(args, split="calib", out_root=common, log=run_log)
    test_pq, _test_rep = _run_counterfactual(args, split="test", out_root=common, log=run_log)

    risk_out = common / "risk"
    _run_risk_features(args=args, calib_pq=calib_pq, test_pq=test_pq, risk_out=risk_out, log=run_log)

    router_eval_out = out_dir / "router_eval"
    _run_router_eval(
        args=args,
        seeds=seeds,
        calib_pq=calib_pq,
        test_pq=test_pq,
        risk_out=risk_out,
        out_dir=router_eval_out,
        log=run_log,
    )

    cf_test = pd.read_parquet(test_pq)
    seed_df, ds_df, all_delta = _compute_benchmark_metrics(seeds=seeds, cf_test=cf_test, router_dir=router_eval_out)

    # Per-benchmark direction consistency.
    ds_summary = (
        ds_df.groupby("source_dataset", as_index=False)["mean_delta_j"]
        .agg(["mean", "std", "min", "max"])
        .reset_index()
        .rename(columns={"mean": "mean_delta_j_mean", "std": "mean_delta_j_std", "min": "mean_delta_j_min", "max": "mean_delta_j_max"})
    )
    # "Direction-consistent" on public cross-benchmark tests:
    # allow tiny negative drift within tolerance to avoid over-penalizing
    # near-zero regimes (e.g., tiny benchmark slices with effectively tied policies).
    ds_summary["direction_positive"] = ds_summary["mean_delta_j_mean"] >= -float(args.direction_tol)
    direction_consistent = bool(ds_summary["direction_positive"].all())

    # Pooled significance.
    if all_delta.size <= 0:
        raise RuntimeError("Empty pooled delta array.")
    ci_lo, ci_hi = _bootstrap_ci(all_delta, n_boot=int(args.bootstrap_n))
    p_boot = _bootstrap_p_gt0(all_delta, n_boot=int(args.bootstrap_n))
    try:
        p_val = float(wilcoxon(all_delta, alternative="greater", zero_method="wilcox").pvalue)
    except ValueError:
        # Fallback for edge cases where all differences are identical.
        p_val = 1.0 if float(np.mean(all_delta)) <= 0.0 else 0.0

    # Drift from phase-7 frozen reference.
    p7_stats = _load_json(ROOT / "outputs/router_phase7_v1/stats.json")
    drift_ok = bool(p7_stats["gate_check"]["exp3_exp4_drift_abs_le_0_5pct"])

    # Dataset counts / gates.
    test_stat = manifest_data["splits"]["test"]
    n_public_cases = int(test_stat["num_cases"])
    n_public_bench = int(len(test_stat["source_counts"]))
    n_ood_families = int(test_stat["ood_family_unique"])

    gate = {
        "public_benchmarks_ge_3": bool(n_public_bench >= 3),
        "public_cases_ge_3000": bool(n_public_cases >= 3000),
        "ood_map_families_ge_2": bool(n_ood_families >= 2),
        "direction_consistent_per_benchmark": bool(direction_consistent),
        "pooled_p_lt_0_01": bool(p_boot < 0.01),
        "exp3_exp4_drift_abs_le_0_5pct": bool(drift_ok),
    }

    # Export tables.
    table_split = tables_dir / "table_phase9_split_counts.csv"
    pd.DataFrame(
        [
            {
                "split": "test",
                "num_cases": n_public_cases,
                "source_counts": json.dumps(test_stat["source_counts"], ensure_ascii=False),
                "ood_family_unique": n_ood_families,
                "ood_family_ratio": float(test_stat["ood_family_ratio"]),
            }
        ]
    ).to_csv(table_split, index=False)

    table_seed = tables_dir / "table_phase9_seed_mean_delta_j.csv"
    seed_df.to_csv(table_seed, index=False)

    table_ds_seed = tables_dir / "table_phase9_seed_dataset_delta_j.csv"
    ds_df.to_csv(table_ds_seed, index=False)

    table_ds_summary = tables_dir / "table_phase9_dataset_summary.csv"
    ds_summary.to_csv(table_ds_summary, index=False)

    table_sig = tables_dir / "table_phase9_significance.csv"
    pd.DataFrame(
        [
            {
                "claim": "pooled_delta_j_router_vs_p5",
                "n": int(all_delta.size),
                "mean": float(np.mean(all_delta)),
                "std": float(np.std(all_delta)),
                "ci95_low": float(ci_lo),
                "ci95_high": float(ci_hi),
                "p_value_bootstrap_gt0": float(p_boot),
                "p_value_wilcoxon": float(p_val),
                "pass_p_lt_0_01": bool(p_boot < 0.01),
                "direction": ">0",
            }
        ]
    ).to_csv(table_sig, index=False)

    # Reuse external baseline table from P7 as cross-paper baseline appendix input.
    ext_src = ROOT / "paper/tables_router_v1/table_phase7_external_baselines.csv"
    ext_dst = tables_dir / "table_phase9_external_baselines.csv"
    if ext_src.exists():
        pd.read_csv(ext_src).to_csv(ext_dst, index=False)
    else:
        pd.DataFrame().to_csv(ext_dst, index=False)

    stats = {
        "version": "router_phase9_bench_v1",
        "seeds": [int(s) for s in seeds],
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "router_eval_config": {
            "calib_split_mode": str(args.calib_split_mode),
            "calib_train_frac": float(args.calib_train_frac),
            "calib_split_seed": int(args.calib_split_seed),
            "conformal_select_on": str(args.conformal_select_on),
            "probe_search_on": str(args.probe_search_on),
            "phase8_strict_violation_target": float(args.phase8_strict_violation_target),
            "phase8_strict_ci_upper_target": float(args.phase8_strict_ci_upper_target),
            "phase8_strict_tune_violation_margin": float(args.phase8_strict_tune_violation_margin),
            "phase8_strict_tune_ci_margin": float(args.phase8_strict_tune_ci_margin),
            "phase8_probe_include_cost_feature": bool(args.phase8_probe_include_cost_feature),
            "phase8_probe_selection_mode": str(args.phase8_probe_selection_mode),
            "phase8_probe_lcb_alpha": float(args.phase8_probe_lcb_alpha),
        },
        "counts": {
            "num_public_benchmarks": int(n_public_bench),
            "num_public_test_cases": int(n_public_cases),
            "num_ood_map_families": int(n_ood_families),
        },
        "pooled": {
            "mean_delta_j": float(np.mean(all_delta)),
            "std_delta_j": float(np.std(all_delta)),
            "ci95": [float(ci_lo), float(ci_hi)],
            "p_value_bootstrap_gt0": float(p_boot),
            "p_value_wilcoxon": float(p_val),
        },
        "direction_by_benchmark": ds_summary.to_dict(orient="records"),
        "gate_check": gate,
        "artifacts": {
            "manifest_json": str(manifest),
            "counterfactual_calib_parquet": str(calib_pq),
            "counterfactual_test_parquet": str(test_pq),
            "router_eval_out": str(router_eval_out),
            "seed_runs_csv": str(table_seed),
            "seed_dataset_csv": str(table_ds_seed),
            "dataset_summary_csv": str(table_ds_summary),
            "significance_csv": str(table_sig),
            "split_table_csv": str(table_split),
            "external_baselines_csv": str(ext_dst),
            "report_md": str(args.report_md),
        },
    }
    stats_path = out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(args.report_md, stats=stats)

    print(f"[phase9] stats={stats_path}")
    print(f"[phase9] report={args.report_md}")
    print(f"[phase9] gate={gate}")
    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("Phase-9 gate failed. Check outputs/router_phase9_bench_v1/stats.json")


if __name__ == "__main__":
    main()
