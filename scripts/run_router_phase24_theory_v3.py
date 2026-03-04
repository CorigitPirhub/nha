from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.router_method_core import wilson_ci95


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase24 theory_v3 validation: multi-arm portfolio + prior-shift risk certificate + two-stage probe monotonicity."
    )
    p.add_argument("--phase23-out-dir", type=Path, default=Path("outputs/router_phase23_portfolio_v1"))
    p.add_argument(
        "--phase23-test-parquet",
        type=Path,
        default=Path("outputs/router_phase23_portfolio_v1/common/router_counterfactual_test_k3_midnet.parquet"),
    )
    p.add_argument(
        "--phase23-calib-parquet",
        type=Path,
        default=Path("outputs/router_phase23_portfolio_v1/common/router_counterfactual_calib_k3_midnet.parquet"),
    )
    p.add_argument(
        "--phase9-eval-dir",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed"),
    )
    p.add_argument("--phase9-base-policy", type=str, default="conformal_strict_v2")
    p.add_argument("--phase9-probe-policy", type=str, default="probe_strict_v2")
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05, help="Confidence level for Wilson/empirical Bernstein bounds.")
    p.add_argument("--max-shift-slack", type=float, default=0.04, help="Upper bound on (bound - empirical) slack for shift certificates.")
    p.add_argument("--max-regret-slack", type=float, default=0.25, help="Upper bound on (ucb - mean) slack for regret certificates.")
    p.add_argument("--theory-doc", type=Path, default=Path("docs/router_theory_v3.md"))
    p.add_argument("--appendix-doc", type=Path, default=Path("docs/router_theory_v3_appendix.md"))
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase24_theory_v3"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase24_theory_v3.md"))
    p.add_argument("--enforce-gate", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def _load_seed_dirs(out_dir: Path) -> list[int]:
    seeds: list[int] = []
    for p in sorted((out_dir / "seeds").glob("seed_*")):
        try:
            seeds.append(int(p.name.replace("seed_", "")))
        except ValueError:
            continue
    return seeds


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


def _empirical_bernstein_upper(vals: np.ndarray, delta: float) -> float:
    vals = np.asarray(vals, dtype=np.float64)
    if vals.size <= 1:
        return float(vals.mean()) if vals.size else 0.0
    n = float(vals.size)
    mean = float(np.mean(vals))
    var = float(np.var(vals, ddof=1))
    vmax = float(np.max(vals))
    if vmax <= 0.0:
        return 0.0
    delta = float(max(delta, 1e-12))
    logt = float(math.log(3.0 / delta))
    rad = math.sqrt((2.0 * var * logt) / n) + (3.0 * vmax * logt) / (n - 1.0)
    return float(mean + rad)


def _vio_portfolio(df: pd.DataFrame, *, eps: float) -> np.ndarray:
    arm = df["arm"].astype(str).to_numpy()
    qf = df["q_rel_fast"].to_numpy(dtype=np.float64)
    qm = df["q_rel_mid"].to_numpy(dtype=np.float64)
    vio = ((arm == "fast") & (qf > float(eps))) | ((arm == "mid") & (qm > float(eps)))
    return vio.astype(bool)


def _write_report(
    path: Path,
    *,
    stats: dict,
    seed_df: pd.DataFrame,
    shift_df: pd.DataFrame,
    probe_df: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# Router Theory V3 Report (Phase24)")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Seeds: `{stats['seeds']}`")
    lines.append(f"- Theorems: `{stats['theorem_coverage']['new_theorem_count']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Seed Checks (Phase23)")
    lines.append(seed_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Shift Certificates (Phase23, by OOD family)")
    lines.append(shift_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Probe Monotonicity (Phase9)")
    lines.append(probe_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    theory_cov = _parse_theorem_coverage(args.theory_doc, args.appendix_doc)

    stats23_path = args.phase23_out_dir / "stats.json"
    if not stats23_path.exists():
        raise FileNotFoundError(stats23_path)
    stats23 = json.loads(stats23_path.read_text(encoding="utf-8"))
    t_ref = float(stats23["t_ref_ms"])
    beta = float(stats23["beta"])

    seeds = _load_seed_dirs(args.phase23_out_dir)
    if not seeds:
        raise RuntimeError(f"No seed dirs found under {args.phase23_out_dir}")

    cf_test = pd.read_parquet(args.phase23_test_parquet)

    # Phase23 checks.
    seed_rows: list[dict] = []
    shift_rows: list[dict] = []

    for seed in seeds:
        sd = args.phase23_out_dir / "seeds" / f"seed_{seed}"
        dec_te_path = sd / "test_decisions.parquet"
        dec_ca_path = sd / "calib_decisions.parquet"
        if not dec_te_path.exists():
            raise FileNotFoundError(dec_te_path)
        if not dec_ca_path.exists():
            raise FileNotFoundError(dec_ca_path)

        dec_te = pd.read_parquet(dec_te_path)
        dec_ca = pd.read_parquet(dec_ca_path)
        req_te = {"sample_name", "difficulty", "ood_family", "arm"}
        if not req_te.issubset(dec_te.columns):
            raise RuntimeError(f"Missing columns in {dec_te_path}: {sorted(list(req_te - set(dec_te.columns)))}")
        req_ca = {"sample_name", "difficulty", "ood_family", "arm", "q_rel_fast", "q_rel_mid"}
        if not req_ca.issubset(dec_ca.columns):
            raise RuntimeError(f"Missing columns in {dec_ca_path}: {sorted(list(req_ca - set(dec_ca.columns)))}")

        # Merge with counterfactuals for regret computation.
        join_cols = ["sample_name", "difficulty"]
        te = dec_te.merge(
            cf_test[
                [
                    "sample_name",
                    "difficulty",
                    "L_fast",
                    "L_mid",
                    "L_slow",
                    "T_fast_ms",
                    "T_mid_ms",
                    "T_slow_ms",
                ]
            ],
            on=join_cols,
            how="inner",
        )
        if len(te) != len(dec_te):
            raise RuntimeError(f"Phase23 merge mismatch on test: {len(te)} vs {len(dec_te)} (seed={seed})")

        l_slow = te["L_slow"].to_numpy(dtype=np.float64)
        drel_fast = (te["L_fast"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)
        drel_mid = (te["L_mid"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)
        j_fast = te["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + beta * np.maximum(drel_fast, 0.0)
        j_mid = te["T_mid_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + beta * np.maximum(drel_mid, 0.0)
        j_slow = te["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
        j_star = np.minimum.reduce([j_fast, j_mid, j_slow])

        arm = te["arm"].astype(str).to_numpy()
        j_pi = np.where(arm == "fast", j_fast, np.where(arm == "mid", j_mid, j_slow))
        regret = np.maximum(j_pi - j_star, 0.0)
        regret_mean = float(np.mean(regret))
        regret_ucb = float(_empirical_bernstein_upper(regret, delta=float(args.alpha)))
        regret_slack = float(regret_ucb - regret_mean)

        # Empirical risk on test.
        vio_te = _vio_portfolio(te, eps=float(args.epsilon_rel))
        risk_te = float(np.mean(vio_te))

        seed_rows.append(
            {
                "seed": int(seed),
                "test_violation_rate": risk_te,
                "regret_mean": regret_mean,
                "regret_ucb": regret_ucb,
                "regret_slack": regret_slack,
                "decisions_test": str(dec_te_path),
                "decisions_calib": str(dec_ca_path),
            }
        )

        # Shift certificate: bound test risk under difficulty prior shift using calib (difficulty-wise) upper bounds.
        # We validate the bound separately on each OOD family subset in test.
        u_by_d: dict[str, float] = {}
        for d in ["easy", "medium", "hard"]:
            dd = dec_ca[dec_ca["difficulty"].astype(str) == d]
            n = int(len(dd))
            if n <= 0:
                u_by_d[d] = 1.0
                continue
            vio = _vio_portfolio(dd, eps=float(args.epsilon_rel))
            k = int(np.sum(vio))
            _, hi = wilson_ci95(k, n, alpha=float(args.alpha))
            u_by_d[d] = float(hi)

        for fam in sorted(list(set(dec_te["ood_family"].astype(int).unique().tolist()) | set(dec_ca["ood_family"].astype(int).unique().tolist()))):
            te_f = te[te["ood_family"].astype(int) == int(fam)].copy()
            if len(te_f) <= 0:
                continue

            # Test difficulty prior within this family.
            counts = te_f["difficulty"].astype(str).value_counts()
            n_te = float(len(te_f))
            p_by_d = {d: float(counts.get(d, 0) / max(n_te, 1.0)) for d in ["easy", "medium", "hard"]}

            bound = float(sum(p_by_d[d] * u_by_d[d] for d in ["easy", "medium", "hard"]))
            vio_te_f = _vio_portfolio(te_f, eps=float(args.epsilon_rel))
            emp = float(np.mean(vio_te_f))
            slack = float(bound - emp)
            hold = bool(emp <= bound + 1e-12)

            shift_rows.append(
                {
                    "seed": int(seed),
                    "ood_family": int(fam),
                    "n_calib": int(len(dec_ca)),
                    "n_test": int(len(te_f)),
                    "emp_risk_test": emp,
                    "bound_from_calib": bound,
                    "slack": slack,
                    "hold": hold,
                    "p_test_easy": p_by_d["easy"],
                    "p_test_medium": p_by_d["medium"],
                    "p_test_hard": p_by_d["hard"],
                    "u_calib_easy": u_by_d["easy"],
                    "u_calib_medium": u_by_d["medium"],
                    "u_calib_hard": u_by_d["hard"],
                }
            )

    seed_df = pd.DataFrame(seed_rows).sort_values("seed")
    shift_df = pd.DataFrame(shift_rows).sort_values(["seed", "ood_family"])

    # Phase9 probe monotonicity checks.
    probe_rows: list[dict] = []
    for seed in seeds:
        base_path = (
            args.phase9_eval_dir
            / "seeds"
            / f"seed_{seed}"
            / "mixed"
            / str(args.phase9_base_policy)
            / "test_decisions.parquet"
        )
        probe_path = (
            args.phase9_eval_dir
            / "seeds"
            / f"seed_{seed}"
            / "mixed"
            / str(args.phase9_probe_policy)
            / "test_decisions.parquet"
        )
        if not base_path.exists() or not probe_path.exists():
            continue
        base = pd.read_parquet(base_path)
        probe = pd.read_parquet(probe_path)
        req = {"sample_name", "use_fast", "q_rel"}
        if not req.issubset(base.columns) or not req.issubset(probe.columns):
            raise RuntimeError(f"Missing required columns for probe check on seed={seed}")

        m = base[["sample_name", "use_fast", "q_rel"]].merge(
            probe[["sample_name", "use_fast", "q_rel"]],
            on="sample_name",
            how="inner",
            suffixes=("_base", "_probe"),
        )
        if len(m) != len(base):
            raise RuntimeError(f"Probe merge mismatch on seed={seed}: {len(m)} vs {len(base)}")

        use_fast_base = m["use_fast_base"].astype(bool).to_numpy()
        use_fast_probe = m["use_fast_probe"].astype(bool).to_numpy()
        monotone_violate = int(np.sum(use_fast_probe & (~use_fast_base)))
        monotone_hold = bool(monotone_violate == 0)

        q_rel = m["q_rel_base"].to_numpy(dtype=np.float64)
        vio_base = use_fast_base & (q_rel > float(args.epsilon_rel))
        vio_probe = use_fast_probe & (q_rel > float(args.epsilon_rel))
        risk_base = float(np.mean(vio_base))
        risk_probe = float(np.mean(vio_probe))
        risk_noninc = bool(risk_probe <= risk_base + 1e-12)

        probe_rows.append(
            {
                "seed": int(seed),
                "monotone_hold": monotone_hold,
                "monotone_violate_cases": monotone_violate,
                "risk_base": risk_base,
                "risk_probe": risk_probe,
                "risk_nonincrease_hold": risk_noninc,
                "base_path": str(base_path),
                "probe_path": str(probe_path),
            }
        )

    probe_df = pd.DataFrame(probe_rows).sort_values("seed")

    # Aggregate gates.
    theory_v3_nontrivial = bool(theory_cov["new_theorem_count_ge_2"] and theory_cov["proof_complete"])
    shift_hold_all = bool(len(shift_df) > 0 and bool(np.all(shift_df["hold"].astype(bool).to_numpy())))
    probe_hold_all = bool(len(probe_df) > 0 and bool(np.all(probe_df["monotone_hold"].astype(bool).to_numpy())) and bool(np.all(probe_df["risk_nonincrease_hold"].astype(bool).to_numpy())))
    empirical_checks_all_hold = bool(shift_hold_all and probe_hold_all)

    shift_slack_ok = bool(len(shift_df) > 0 and float(np.max(shift_df["slack"].to_numpy(dtype=np.float64))) <= float(args.max_shift_slack) + 1e-12)
    regret_slack_ok = bool(float(np.max(seed_df["regret_slack"].to_numpy(dtype=np.float64))) <= float(args.max_regret_slack) + 1e-12)
    bound_gap_reasonable = bool(shift_slack_ok and regret_slack_ok)

    gate = {
        "theory_v3_nontrivial": theory_v3_nontrivial,
        "empirical_checks_all_hold": empirical_checks_all_hold,
        "bound_gap_reasonable": bound_gap_reasonable,
    }

    # Save artifacts.
    seed_csv = args.out_dir / "seed_checks.csv"
    shift_csv = args.out_dir / "shift_bounds.csv"
    probe_csv = args.out_dir / "probe_monotone.csv"
    seed_df.to_csv(seed_csv, index=False)
    shift_df.to_csv(shift_csv, index=False)
    probe_df.to_csv(probe_csv, index=False)

    stats = {
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "seeds": seeds,
        "phase23": {
            "t_ref_ms": t_ref,
            "beta": beta,
            "out_dir": str(args.phase23_out_dir),
        },
        "theorem_coverage": theory_cov,
        "thresholds": {
            "max_shift_slack": float(args.max_shift_slack),
            "max_regret_slack": float(args.max_regret_slack),
        },
        "summary": {
            "shift_slack_max": float(np.max(shift_df["slack"].to_numpy(dtype=np.float64))) if len(shift_df) else float("nan"),
            "regret_slack_max": float(np.max(seed_df["regret_slack"].to_numpy(dtype=np.float64))) if len(seed_df) else float("nan"),
        },
        "gate_check": gate,
        "artifacts": {
            "out_dir": str(args.out_dir),
            "report_md": str(args.report_md),
            "seed_csv": str(seed_csv),
            "shift_csv": str(shift_csv),
            "probe_csv": str(probe_csv),
        },
    }
    stats_path = args.out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")

    _write_report(args.report_md, stats=stats, seed_df=seed_df, shift_df=shift_df, probe_df=probe_df)

    if bool(args.enforce_gate):
        for k, v in gate.items():
            if not bool(v):
                raise RuntimeError(f"Phase24 gate failed: {k}={v}; see {stats_path}")

    print(f"[phase24] done in {(time.perf_counter() - t0):.3f}s")


if __name__ == "__main__":
    main()
