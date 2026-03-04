from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-11 theory/experiment consistency validation for Conformal+Probe router.")
    p.add_argument("--phase8-dir", type=Path, default=Path("outputs/router_phase8_strict_v1"))
    p.add_argument(
        "--counterfactual-test-parquet",
        type=Path,
        default=Path("outputs/router_phase7_v1/common/router_counterfactual_test.parquet"),
    )
    p.add_argument(
        "--target-prior-index",
        type=Path,
        default=Path("data/router_phase9_public_v1/test_index.csv"),
        help="Target deployment prior source (difficulty distribution).",
    )
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05, help="Confidence level for Wilson upper bound.")
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase11_theory_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase11_theory_v1.md"))
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    phat = float(k / n)
    den = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / den
    half = (z * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)) / den
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return float(lo), float(hi)


def _load_seed_dirs(phase8_dir: Path) -> list[int]:
    seeds: list[int] = []
    for p in sorted((phase8_dir / "seeds").glob("seed_*")):
        try:
            seeds.append(int(str(p.name).replace("seed_", "")))
        except ValueError:
            continue
    if not seeds:
        raise RuntimeError(f"No seed dirs found in {phase8_dir / 'seeds'}")
    return seeds


def _write_report(path: Path, stats: dict, seed_df: pd.DataFrame, diff_df: pd.DataFrame) -> None:
    lines: list[str] = []
    lines.append("# Router Phase11 Theory V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Seeds: `{stats['seeds']}`")
    lines.append(f"- Epsilon: `{stats['config']['epsilon_rel']}`")
    lines.append(f"- Alpha: `{stats['config']['alpha']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Key Numbers")
    lines.append(f"- `probe_violation_rate_mean`: `{stats['summary']['probe_violation_rate_mean']:.6f}`")
    lines.append(f"- `probe_theory_upper_mean`: `{stats['summary']['probe_theory_upper_mean']:.6f}`")
    lines.append(f"- `max_probe_bound_gap_pct`: `{100.0 * stats['summary']['probe_bound_gap_max']:.3f}%`")
    lines.append(f"- `probe_monotone_safety_all`: `{stats['summary']['probe_monotone_safety_all']}`")
    lines.append("")
    lines.append("## Seed Metrics")
    lines.append(seed_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Difficulty-Shift Correction")
    lines.append(diff_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    if not args.phase8_dir.exists():
        raise FileNotFoundError(args.phase8_dir)
    if not args.counterfactual_test_parquet.exists():
        raise FileNotFoundError(args.counterfactual_test_parquet)
    if not args.target_prior_index.exists():
        raise FileNotFoundError(args.target_prior_index)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    seed_runs_csv = args.phase8_dir / "seed_runs.csv"
    if not seed_runs_csv.exists():
        raise FileNotFoundError(seed_runs_csv)
    seed_runs = pd.read_csv(seed_runs_csv)
    seed_lookup = {
        int(r["seed"]): float(r["probe_og_improve_vs_p5_pct"]) for _, r in seed_runs.iterrows()
    }

    cf = pd.read_parquet(args.counterfactual_test_parquet)[["sample_name", "q_rel", "difficulty"]].copy()
    target_df = pd.read_csv(args.target_prior_index)
    if "difficulty" not in target_df.columns:
        raise RuntimeError(f"target prior index missing difficulty column: {args.target_prior_index}")
    target_prior = target_df["difficulty"].astype(str).value_counts(normalize=True).to_dict()
    eval_prior = cf["difficulty"].astype(str).value_counts(normalize=True).to_dict()
    for d in ("easy", "medium", "hard"):
        target_prior.setdefault(d, 0.0)
        eval_prior.setdefault(d, 0.0)

    eps = float(args.epsilon_rel)
    z = float(1.959963984540054)  # fixed for 95% confidence (alpha=0.05)

    seeds = _load_seed_dirs(args.phase8_dir)
    seed_rows: list[dict] = []
    diff_rows: list[dict] = []

    for seed in seeds:
        root = args.phase8_dir / "seeds" / f"seed_{seed}" / "mixed"
        conf_dec_pq = root / "conformal_strict_v2" / "test_decisions.parquet"
        probe_dec_pq = root / "probe_strict_v2" / "test_decisions.parquet"
        if (not conf_dec_pq.exists()) or (not probe_dec_pq.exists()):
            raise FileNotFoundError(f"Missing decision file(s) for seed={seed}")

        conf = pd.read_parquet(conf_dec_pq)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_conf"})
        probe = pd.read_parquet(probe_dec_pq)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_probe"})
        df = cf.merge(conf, on="sample_name", how="inner").merge(probe, on="sample_name", how="inner")
        if len(df) != len(cf):
            raise RuntimeError(f"Decision merge mismatch seed={seed}: {len(df)} vs {len(cf)}")

        vio_conf = (df["use_fast_conf"].to_numpy(dtype=bool) & (df["q_rel"].to_numpy(dtype=np.float64) > eps))
        vio_probe = (df["use_fast_probe"].to_numpy(dtype=bool) & (df["q_rel"].to_numpy(dtype=np.float64) > eps))
        n = int(len(df))
        k_conf = int(np.sum(vio_conf))
        k_probe = int(np.sum(vio_probe))
        v_conf = float(k_conf / max(n, 1))
        v_probe = float(k_probe / max(n, 1))
        _, up_conf = _wilson_ci(k_conf, n, z=z)
        _, up_probe = _wilson_ci(k_probe, n, z=z)

        subset_violation = int(np.sum(df["use_fast_probe"].to_numpy(dtype=bool) & (~df["use_fast_conf"].to_numpy(dtype=bool))))
        monotone_safety = bool(v_probe <= v_conf + 1e-12)
        fast_subset = bool(subset_violation == 0)
        og_improve_pct = float(seed_lookup.get(int(seed), float("nan")))

        # Selection-bias correction: map mixed-eval risk to target deployment prior by difficulty.
        conf_target = 0.0
        probe_target = 0.0
        for d in ("easy", "medium", "hard"):
            dd = df[df["difficulty"].astype(str) == d]
            if len(dd) <= 0:
                continue
            vd_conf = float(np.mean(dd["use_fast_conf"].to_numpy(dtype=bool) & (dd["q_rel"].to_numpy(dtype=np.float64) > eps)))
            vd_probe = float(np.mean(dd["use_fast_probe"].to_numpy(dtype=bool) & (dd["q_rel"].to_numpy(dtype=np.float64) > eps)))
            conf_target += float(target_prior[d]) * vd_conf
            probe_target += float(target_prior[d]) * vd_probe

            diff_rows.append(
                {
                    "seed": int(seed),
                    "difficulty": d,
                    "target_prior": float(target_prior[d]),
                    "eval_prior": float(eval_prior[d]),
                    "conf_violation_rate_d": vd_conf,
                    "probe_violation_rate_d": vd_probe,
                }
            )

        # Error decomposition terms.
        finite_sample_slack = float(up_probe - v_probe)
        safety_gain = float(v_conf - v_probe)
        selection_shift = float(probe_target - v_probe)
        decomposition_rhs = float(v_conf - safety_gain + finite_sample_slack + abs(selection_shift))

        seed_rows.append(
            {
                "seed": int(seed),
                "num_cases": n,
                "conf_violation_rate": v_conf,
                "probe_violation_rate": v_probe,
                "conf_theory_upper": float(up_conf),
                "probe_theory_upper": float(up_probe),
                "probe_bound_gap": finite_sample_slack,
                "probe_monotone_safety": monotone_safety,
                "probe_fast_subset_of_conf": fast_subset,
                "probe_og_improve_vs_p5_pct": og_improve_pct,
                "probe_target_prior_violation_rate": probe_target,
                "selection_shift_target_minus_eval": selection_shift,
                "decomp_safety_gain_conf_minus_probe": safety_gain,
                "decomp_finite_sample_slack": finite_sample_slack,
                "decomp_rhs_upper": decomposition_rhs,
                "decomp_lhs_target_risk": probe_target,
            }
        )

    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    diff_df = pd.DataFrame(diff_rows).sort_values(["seed", "difficulty"]).reset_index(drop=True)

    summary = {
        "num_seeds": int(len(seed_df)),
        "probe_violation_rate_mean": float(seed_df["probe_violation_rate"].mean()),
        "probe_theory_upper_mean": float(seed_df["probe_theory_upper"].mean()),
        "probe_bound_gap_mean": float(seed_df["probe_bound_gap"].mean()),
        "probe_bound_gap_max": float(seed_df["probe_bound_gap"].max()),
        "probe_monotone_safety_all": bool(seed_df["probe_monotone_safety"].all()),
        "probe_fast_subset_all": bool(seed_df["probe_fast_subset_of_conf"].all()),
        "probe_og_improve_positive_all": bool((seed_df["probe_og_improve_vs_p5_pct"] > 0.0).all()),
        "decomposition_lhs_le_rhs_all": bool((seed_df["decomp_lhs_target_risk"] <= seed_df["decomp_rhs_upper"] + 1e-12).all()),
        "selection_shift_abs_mean": float(np.mean(np.abs(seed_df["selection_shift_target_minus_eval"].to_numpy(dtype=np.float64)))),
    }

    gate = {
        "five_seeds_completed": bool(int(summary["num_seeds"]) >= 5),
        "theory_bound_gap_le_2pct": bool(float(summary["probe_bound_gap_max"]) <= 0.02 + 1e-12),
        "empirical_le_theory_upper_all_seeds": bool(
            (seed_df["probe_violation_rate"] <= seed_df["probe_theory_upper"] + 1e-12).all()
        ),
        "probe_monotone_safety_all_seeds": bool(summary["probe_monotone_safety_all"]),
        "probe_fast_subset_of_conformal_all_seeds": bool(summary["probe_fast_subset_all"]),
        "probe_og_improve_positive_all_seeds": bool(summary["probe_og_improve_positive_all"]),
        "error_decomposition_lhs_le_rhs_all_seeds": bool(summary["decomposition_lhs_le_rhs_all"]),
    }

    seed_csv = out_dir / "seed_metrics.csv"
    diff_csv = out_dir / "difficulty_shift_metrics.csv"
    seed_df.to_csv(seed_csv, index=False)
    diff_df.to_csv(diff_csv, index=False)

    stats = {
        "version": "router_phase11_theory_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": [int(v) for v in seed_df["seed"].tolist()],
        "config": {
            "phase8_dir": str(args.phase8_dir),
            "counterfactual_test_parquet": str(args.counterfactual_test_parquet),
            "target_prior_index": str(args.target_prior_index),
            "epsilon_rel": float(args.epsilon_rel),
            "alpha": float(args.alpha),
            "target_prior_by_difficulty": {k: float(v) for k, v in target_prior.items()},
            "eval_prior_by_difficulty": {k: float(v) for k, v in eval_prior.items()},
        },
        "summary": summary,
        "gate_check": gate,
        "artifacts": {
            "seed_metrics_csv": str(seed_csv),
            "difficulty_shift_metrics_csv": str(diff_csv),
            "report_md": str(args.report_md),
        },
    }
    stats_path = out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(args.report_md, stats=stats, seed_df=seed_df, diff_df=diff_df)

    print(f"[phase11] stats={stats_path}")
    print(f"[phase11] report={args.report_md}")
    print(f"[phase11] gate={gate}")
    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("Phase-11 gate failed. Check outputs/router_phase11_theory_v1/stats.json")


if __name__ == "__main__":
    main()
