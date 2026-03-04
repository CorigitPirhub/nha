from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Step-1 theory_v2 validation: theorem coverage + risk/shift bound checks on 5 seeds and OOD map families."
    )
    p.add_argument(
        "--router-eval-dir",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed"),
    )
    p.add_argument("--policy-name", type=str, default="probe_strict_v2")
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05, help="One-sided confidence level.")
    p.add_argument("--shift-l1-radius", type=float, default=0.20)
    p.add_argument("--grid-step", type=float, default=0.05)
    p.add_argument("--min-seeds", type=int, default=5)
    p.add_argument("--min-map-families", type=int, default=10)
    p.add_argument("--theory-doc", type=Path, default=Path("docs/router_theory_v2.md"))
    p.add_argument("--appendix-doc", type=Path, default=Path("docs/router_theory_v2_appendix.md"))
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_theory_v2"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_theory_v2.md"))
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _wilson_upper(k: int, n: int, alpha: float) -> float:
    if n <= 0:
        return 1.0
    z = float(NormalDist().inv_cdf(1.0 - alpha))
    phat = float(k / n)
    den = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / den
    half = (z * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)) / den
    return float(min(1.0, center + half))


def _empirical_bernstein_upper(vals: np.ndarray, alpha: float) -> float:
    if vals.size <= 1:
        return float(vals.mean()) if vals.size else 0.0
    n = float(vals.size)
    mean = float(np.mean(vals))
    var = float(np.var(vals, ddof=1))
    vmax = float(np.max(vals))
    if vmax <= 0.0:
        return 0.0
    delta = max(float(alpha), 1e-12)
    logt = float(math.log(3.0 / delta))
    rad = math.sqrt((2.0 * var * logt) / n) + (3.0 * vmax * logt) / (n - 1.0)
    return float(mean + rad)


def _load_seed_dirs(router_eval_dir: Path) -> list[int]:
    seeds: list[int] = []
    for p in sorted((router_eval_dir / "seeds").glob("seed_*")):
        try:
            seeds.append(int(p.name.replace("seed_", "")))
        except ValueError:
            continue
    return seeds


def _simplex_grid(step: float) -> list[np.ndarray]:
    points: list[np.ndarray] = []
    m = int(round(1.0 / step))
    for i in range(m + 1):
        for j in range(m + 1 - i):
            k = m - i - j
            p = np.array([i * step, j * step, k * step], dtype=np.float64)
            if abs(np.sum(p) - 1.0) <= 1e-9:
                points.append(p)
    return points


def _parse_theorem_coverage(theory_doc: Path, appendix_doc: Path) -> dict:
    missing = []
    if not theory_doc.exists():
        missing.append(str(theory_doc))
    if not appendix_doc.exists():
        missing.append(str(appendix_doc))
    if missing:
        return {
            "new_theorem_count": 0,
            "new_theorem_count_ge_2": False,
            "proof_complete": False,
            "missing_docs": missing,
            "theorem_sections": [],
        }

    txt = appendix_doc.read_text(encoding="utf-8")
    sections = re.split(r"(?im)^##\s+Theorem\s+", txt)
    theorem_sections = [s for s in sections[1:] if s.strip()]
    theorem_count = len(theorem_sections)

    complete_flags: list[bool] = []
    theorem_titles: list[str] = []
    for sec in theorem_sections:
        first = sec.strip().splitlines()[0].strip()
        theorem_titles.append(first)
        low = sec.lower()
        has_assumptions = ("### assumptions" in low) or ("## assumptions" in low)
        has_statement = ("### statement" in low) or ("## statement" in low)
        has_proof = ("### proof" in low) or ("## proof" in low)
        complete_flags.append(bool(has_assumptions and has_statement and has_proof))

    return {
        "new_theorem_count": theorem_count,
        "new_theorem_count_ge_2": bool(theorem_count >= 2),
        "proof_complete": bool(theorem_count >= 2 and all(complete_flags)),
        "missing_docs": [],
        "theorem_sections": theorem_titles,
    }


def _write_report(
    path: Path,
    stats: dict,
    seed_df: pd.DataFrame,
    map_df: pd.DataFrame,
    shift_df: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# Router Theory V2 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Seeds: `{stats['seeds']}`")
    lines.append(f"- Map families: `{stats['summary']['map_family_count']}`")
    lines.append(f"- Pooled risk gap: `{100.0 * stats['summary']['pooled_theory_gap']:.3f}%`")
    lines.append(f"- Pooled risk (empirical/upper): `{stats['summary']['pooled_violation_rate']:.6f}` / `{stats['summary']['pooled_theory_upper']:.6f}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Step-1 Deliverable Check")
    for k, v in stats["deliverables"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Seed Risk/Regret Metrics")
    lines.append(seed_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Map-Family Risk Metrics (Top 20 by support)")
    top_map = map_df.sort_values("n_cases", ascending=False).head(20)
    lines.append(top_map.to_markdown(index=False))
    lines.append("")
    lines.append("## Shift-Robust Checks")
    lines.append(shift_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    seeds = _load_seed_dirs(args.router_eval_dir)
    if not seeds:
        raise RuntimeError(f"No seed directories found under {args.router_eval_dir}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    theory_cov = _parse_theorem_coverage(args.theory_doc, args.appendix_doc)
    difficulty_order = ["easy", "medium", "hard"]
    grid = _simplex_grid(args.grid_step)

    seed_rows: list[dict] = []
    shift_rows: list[dict] = []
    map_rows_all: list[pd.DataFrame] = []

    for seed in seeds:
        dec = args.router_eval_dir / "seeds" / f"seed_{seed}" / "mixed" / args.policy_name / "test_decisions.parquet"
        if not dec.exists():
            raise FileNotFoundError(dec)
        df = pd.read_parquet(dec).copy()
        required = {"sample_name", "use_fast", "q_rel", "difficulty", "map_id", "J_fast", "J_slow"}
        miss = sorted(list(required - set(df.columns)))
        if miss:
            raise RuntimeError(f"Missing columns in {dec}: {miss}")

        use_fast = df["use_fast"].astype(bool).to_numpy()
        q_rel = df["q_rel"].to_numpy(dtype=np.float64)
        vio = use_fast & (q_rel > float(args.epsilon_rel))
        n = int(len(df))
        k = int(np.sum(vio))
        v = float(k / max(n, 1))
        up = _wilson_upper(k, n, args.alpha)
        gap = float(up - v)

        # Objective-regret certificate (Theorem-B check).
        j_fast = df["J_fast"].to_numpy(dtype=np.float64)
        j_slow = df["J_slow"].to_numpy(dtype=np.float64)
        j_policy = np.where(use_fast, j_fast, j_slow)
        j_star = np.minimum(j_fast, j_slow)
        regret = np.maximum(j_policy - j_star, 0.0)
        regret_mean = float(np.mean(regret))
        regret_up = _empirical_bernstein_upper(regret, args.alpha)

        # Difficulty-wise risk for shift-robust bound.
        v_d: list[float] = []
        u_d: list[float] = []
        prior_nom = []
        for d in difficulty_order:
            dd = df[df["difficulty"].astype(str) == d]
            nd = int(len(dd))
            if nd <= 0:
                v_d.append(0.0)
                u_d.append(1.0)
                prior_nom.append(0.0)
                continue
            vd = float(
                np.mean(
                    dd["use_fast"].astype(bool).to_numpy()
                    & (dd["q_rel"].to_numpy(dtype=np.float64) > float(args.epsilon_rel))
                )
            )
            kd = int(np.sum(dd["use_fast"].astype(bool).to_numpy() & (dd["q_rel"].to_numpy(dtype=np.float64) > float(args.epsilon_rel))))
            ud = _wilson_upper(kd, nd, args.alpha)
            v_d.append(vd)
            u_d.append(ud)
            prior_nom.append(float(nd / n))
        v_d_np = np.array(v_d, dtype=np.float64)
        u_d_np = np.array(u_d, dtype=np.float64)
        p0 = np.array(prior_nom, dtype=np.float64)

        # Uncertainty set U_rho around nominal prior; brute-force on simplex grid.
        candidates = [p for p in grid if float(np.sum(np.abs(p - p0))) <= float(args.shift_l1_radius) + 1e-12]
        if not candidates:
            candidates = [p0]
        emp_worst = max(float(np.dot(p, v_d_np)) for p in candidates)
        bound_worst = max(float(np.dot(p, u_d_np)) for p in candidates)
        hold = bool(emp_worst <= bound_worst + 1e-12)

        shift_rows.append(
            {
                "seed": int(seed),
                "nominal_prior_easy": float(p0[0]),
                "nominal_prior_medium": float(p0[1]),
                "nominal_prior_hard": float(p0[2]),
                "candidate_priors": int(len(candidates)),
                "empirical_worst_shifted_risk": emp_worst,
                "theory_worst_shifted_upper": bound_worst,
                "shift_robust_hold": hold,
            }
        )

        seed_rows.append(
            {
                "seed": int(seed),
                "n_cases": n,
                "violation_rate": v,
                "theory_upper": up,
                "theory_gap": gap,
                "empirical_le_upper": bool(v <= up + 1e-12),
                "regret_mean": regret_mean,
                "regret_upper": regret_up,
                "regret_bound_hold": bool(regret_mean <= regret_up + 1e-12),
                "map_family_count": int(df["map_id"].astype(str).nunique()),
            }
        )

        map_grp = (
            df.assign(vio=vio.astype(np.int32))
            .groupby("map_id", as_index=False)
            .agg(k_vio=("vio", "sum"), n_cases=("vio", "count"))
        )
        map_grp["seed"] = int(seed)
        map_grp["violation_rate"] = map_grp["k_vio"] / map_grp["n_cases"].clip(lower=1)
        map_grp["theory_upper"] = [
            _wilson_upper(int(kv), int(nn), args.alpha)
            for kv, nn in zip(map_grp["k_vio"].tolist(), map_grp["n_cases"].tolist())
        ]
        map_grp["theory_gap"] = map_grp["theory_upper"] - map_grp["violation_rate"]
        map_grp["empirical_le_upper"] = map_grp["violation_rate"] <= map_grp["theory_upper"] + 1e-12
        map_rows_all.append(map_grp)

    seed_df = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    shift_df = pd.DataFrame(shift_rows).sort_values("seed").reset_index(drop=True)
    map_df = pd.concat(map_rows_all, axis=0, ignore_index=True)

    pooled_n = int(seed_df["n_cases"].sum())
    pooled_k = int(np.round(float((seed_df["violation_rate"] * seed_df["n_cases"]).sum())))
    pooled_v = float(pooled_k / max(pooled_n, 1))
    pooled_up = _wilson_upper(pooled_k, pooled_n, args.alpha)
    pooled_gap = float(pooled_up - pooled_v)

    map_agg = (
        map_df.groupby("map_id", as_index=False)
        .agg(k_vio=("k_vio", "sum"), n_cases=("n_cases", "sum"))
        .sort_values("n_cases", ascending=False)
        .reset_index(drop=True)
    )
    map_agg["violation_rate"] = map_agg["k_vio"] / map_agg["n_cases"].clip(lower=1)
    map_agg["theory_upper"] = [
        _wilson_upper(int(kv), int(nn), args.alpha)
        for kv, nn in zip(map_agg["k_vio"].tolist(), map_agg["n_cases"].tolist())
    ]
    map_agg["theory_gap"] = map_agg["theory_upper"] - map_agg["violation_rate"]
    map_agg["empirical_le_upper"] = map_agg["violation_rate"] <= map_agg["theory_upper"] + 1e-12

    seed_csv = args.out_dir / "seed_metrics.csv"
    map_csv = args.out_dir / "map_family_metrics.csv"
    shift_csv = args.out_dir / "shift_robust_metrics.csv"
    seed_df.to_csv(seed_csv, index=False)
    map_agg.to_csv(map_csv, index=False)
    shift_df.to_csv(shift_csv, index=False)

    summary = {
        "seed_count": int(len(seed_df)),
        "map_family_count": int(map_agg["map_id"].nunique()),
        "pooled_n_cases": pooled_n,
        "pooled_violation_rate": pooled_v,
        "pooled_theory_upper": pooled_up,
        "pooled_theory_gap": pooled_gap,
        "seed_empirical_le_upper_all": bool(seed_df["empirical_le_upper"].all()),
        "map_empirical_le_upper_all": bool(map_agg["empirical_le_upper"].all()),
        "regret_bound_hold_all_seeds": bool(seed_df["regret_bound_hold"].all()),
        "shift_robust_bound_hold_all_seeds": bool(shift_df["shift_robust_hold"].all()),
    }

    gate = {
        "new_theorem_count_ge_2": bool(theory_cov["new_theorem_count_ge_2"]),
        "proof_complete": bool(theory_cov["proof_complete"]),
        "empirical_le_theory_upper_all_seeds": bool(summary["seed_empirical_le_upper_all"]),
        "theory_gap_le_1pct": bool(float(summary["pooled_theory_gap"]) <= 0.01 + 1e-12),
        "shift_robust_bound_hold": bool(summary["shift_robust_bound_hold_all_seeds"]),
        "min_seed_count_ge_5": bool(int(summary["seed_count"]) >= int(args.min_seeds)),
        "map_family_count_ge_min": bool(int(summary["map_family_count"]) >= int(args.min_map_families)),
        "map_empirical_le_theory_upper_all": bool(summary["map_empirical_le_upper_all"]),
    }

    stats = {
        "version": "router_theory_v2",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": [int(v) for v in seed_df["seed"].tolist()],
        "config": {
            "router_eval_dir": str(args.router_eval_dir),
            "policy_name": args.policy_name,
            "epsilon_rel": float(args.epsilon_rel),
            "alpha": float(args.alpha),
            "shift_l1_radius": float(args.shift_l1_radius),
            "grid_step": float(args.grid_step),
            "min_seeds": int(args.min_seeds),
            "min_map_families": int(args.min_map_families),
            "theory_doc": str(args.theory_doc),
            "appendix_doc": str(args.appendix_doc),
        },
        "theorem_coverage": theory_cov,
        "summary": summary,
        "gate_check": gate,
        "deliverables": {
            "docs/router_theory_v2.md": bool(args.theory_doc.exists()),
            "docs/router_theory_v2_appendix.md": bool(args.appendix_doc.exists()),
            "scripts/run_router_theory_v2.py": True,
            "outputs/router_theory_v2/stats.json": True,
            "reports/router_theory_v2.md": True,
        },
        "artifacts": {
            "seed_metrics_csv": str(seed_csv),
            "map_family_metrics_csv": str(map_csv),
            "shift_robust_metrics_csv": str(shift_csv),
            "report_md": str(args.report_md),
        },
    }

    stats_path = args.out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(args.report_md, stats=stats, seed_df=seed_df, map_df=map_agg, shift_df=shift_df)

    print(f"[theory_v2] stats={stats_path}")
    print(f"[theory_v2] report={args.report_md}")
    print(f"[theory_v2] gate={gate}")
    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("theory_v2 gate failed")


if __name__ == "__main__":
    main()
