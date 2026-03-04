from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.router_policy_v1 import sha256_file


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-17 policy alignment: offline policy artifact == system policy.")
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase17_policy_alignment_v1"))
    p.add_argument("--policy-artifact", type=Path, default=Path("artifacts/router_policy_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase17_policy_alignment_v1.md"))
    p.add_argument(
        "--paper-table-csv",
        type=Path,
        default=Path("paper/tables_router_v5/table_phase17_policy_alignment.csv"),
    )
    p.add_argument(
        "--paper-fig-svg",
        type=Path,
        default=Path("paper/figures_router_v5/fig_policy_alignment_p99_latency.svg"),
    )
    p.add_argument(
        "--paper-fig-png",
        type=Path,
        default=Path("paper/figures_router_v5/fig_policy_alignment_p99_latency.png"),
    )
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _read_selected_cases(stats: dict) -> pd.DataFrame:
    art = stats.get("artifacts", {})
    csv_path = Path(str(art.get("selected_cases_csv", "")))
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path)


def _same_cases(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    if a.empty or b.empty:
        return False
    if "sample_name" not in a.columns or "sample_name" not in b.columns:
        return False
    return a["sample_name"].astype(str).tolist() == b["sample_name"].astype(str).tolist()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _plot_p99_latency(
    out_svg: Path,
    out_png: Path,
    p10_rule: dict,
    p10_policy: dict,
    p12_rule: dict,
    p12_policy: dict,
) -> None:
    import matplotlib.pyplot as plt

    phases = [
        ("Phase10 System", p10_rule, p10_policy),
        ("Phase12 Realworld/HIL", p12_rule, p12_policy),
    ]
    platforms = sorted(list(p10_rule["platform_metrics"].keys()))

    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(10.5, 3.6), constrained_layout=True)
    if not isinstance(axes, np.ndarray):
        axes = np.asarray([axes])

    for ax, (title, rule, pol) in zip(axes, phases):
        x = np.arange(len(platforms), dtype=np.float64)
        w = 0.36
        rule_vals = [float(rule["platform_metrics"][pf]["latency_p99_ms"]) for pf in platforms]
        pol_vals = [float(pol["platform_metrics"][pf]["latency_p99_ms"]) for pf in platforms]
        ax.bar(x - w / 2, rule_vals, width=w, label="rule_router", color="#4C78A8")
        ax.bar(x + w / 2, pol_vals, width=w, label="policy_router", color="#F58518")
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(platforms, rotation=20, ha="right")
        ax.set_ylabel("p99 latency (ms)")
        ax.grid(axis="y", alpha=0.25)
        # Annotate delta.
        for i, (rv, pv) in enumerate(zip(rule_vals, pol_vals)):
            ax.text(
                float(i),
                float(max(rv, pv)) * 1.01,
                f"Δ={pv - rv:+.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.12))

    _ensure_parent(out_svg)
    fig.savefig(out_svg, format="svg")
    _ensure_parent(out_png)
    fig.savefig(out_png, format="png", dpi=200)
    plt.close(fig)


def _write_report(path: Path, stats: dict) -> None:
    lines: list[str] = []
    lines.append("# Router Phase17 Policy Alignment V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Router policy artifact: `{stats['policy']['artifact_dir']}`")
    lines.append(f"- `policy.json` sha256: `{stats['policy']['policy_json_sha256']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## No-Regression Thresholds (Frozen)")
    thr = stats["thresholds"]
    lines.append(f"- `min_success_delta_each` (policy - rule): `{thr['min_success_delta_each']:+.4f}`")
    lines.append(f"- `max_p99_latency_delta_ms_each` (policy - rule): `{thr['max_p99_latency_delta_ms_each']:+.3f}`")
    lines.append(f"- `min_worst10_success_delta` (policy - rule): `{thr['min_worst10_success_delta']:+.4f}`")
    lines.append(f"- `min_recovery_success_delta` (policy - rule): `{thr['min_recovery_success_delta']:+.4f}`")
    lines.append("")
    lines.append("## Key Deltas (policy - rule)")
    for row in stats["comparisons"]["rows"]:
        lines.append(
            f"- `{row['phase']}/{row['platform']}`: "
            f"Δsuccess=`{row['delta_success']:+.4f}`, "
            f"Δp99_ms=`{row['delta_p99_ms']:+.3f}`, "
            f"Δp95_ms=`{row['delta_p95_ms']:+.3f}`"
        )
    lines.append("")
    lines.append("## Offline vs Deployment Note")
    lines.append(
        "This phase seals the paper-to-system gap by ensuring the closed-loop runner loads and logs a single "
        "policy artifact (`artifacts/router_policy_v1/`) with hash-tracked parameters and models. The offline "
        "risk certificates (Phase11/Theory v2) still apply only under the frozen counterfactual protocol; this "
        "phase explicitly reports any deployment-induced shifts via closed-loop metrics rather than assuming "
        "offline guarantees transfer unchanged."
    )
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")
    _ensure_parent(path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    policy_dir = Path(args.policy_artifact)
    policy_json = policy_dir / "policy.json"
    if not policy_json.exists():
        raise FileNotFoundError(policy_json)
    policy_sha = sha256_file(policy_json)

    # Expected run outputs.
    paths = {
        "p10_rule": out_dir / "rule" / "phase10" / "stats.json",
        "p10_policy": out_dir / "policy" / "phase10" / "stats.json",
        "p12_rule": out_dir / "rule" / "phase12" / "stats.json",
        "p12_policy": out_dir / "policy" / "phase12" / "stats.json",
        "p14_rule": out_dir / "rule" / "phase14" / "stats.json",
        "p14_policy": out_dir / "policy" / "phase14" / "stats.json",
    }
    p10_rule = _load_json(paths["p10_rule"])
    p10_policy = _load_json(paths["p10_policy"])
    p12_rule = _load_json(paths["p12_rule"])
    p12_policy = _load_json(paths["p12_policy"])
    p14_rule = _load_json(paths["p14_rule"])
    p14_policy = _load_json(paths["p14_policy"])

    # Single-source-of-truth check: policy hash must match all policy runs.
    policy_hash_ok = True
    for phase_name, pol in [
        ("phase10", p10_policy),
        ("phase12", p12_policy),
        ("phase14", p14_policy),
    ]:
        got = str(pol.get("config", {}).get("policy_json_sha256", ""))
        if got != policy_sha:
            print(f"[phase17] policy sha mismatch on {phase_name}: want={policy_sha}, got={got}")
            policy_hash_ok = False

    # Ensure identical case selection for fair rule vs policy comparison.
    same_cases_p10 = _same_cases(_read_selected_cases(p10_rule), _read_selected_cases(p10_policy))
    same_cases_p12 = _same_cases(_read_selected_cases(p12_rule), _read_selected_cases(p12_policy))
    same_cases_p14 = _same_cases(_read_selected_cases(p14_rule), _read_selected_cases(p14_policy))

    # Gate checks from each phase.
    policy_phase_gates_ok = bool(
        all(bool(v) for v in p10_policy.get("gate_check", {}).values())
        and all(bool(v) for v in p12_policy.get("gate_check", {}).values())
        and all(bool(v) for v in p14_policy.get("gate_check", {}).values())
    )

    # No-regression thresholds (frozen in report).
    thr = {
        "min_success_delta_each": -0.005,
        "max_p99_latency_delta_ms_each": 5.0,
        "min_worst10_success_delta": -0.01,
        "min_recovery_success_delta": -0.01,
    }

    rows: list[dict] = []
    no_reg_ok = True

    for phase, rule, pol in [
        ("phase10", p10_rule, p10_policy),
        ("phase12", p12_rule, p12_policy),
    ]:
        for pf, rmet in rule["platform_metrics"].items():
            pmet = pol["platform_metrics"][pf]
            d_succ = float(pmet["success_rate"]) - float(rmet["success_rate"])
            d_p95 = float(pmet["latency_p95_ms"]) - float(rmet["latency_p95_ms"])
            d_p99 = float(pmet["latency_p99_ms"]) - float(rmet["latency_p99_ms"])
            rows.append(
                {
                    "phase": phase,
                    "platform": pf,
                    "rule_success": float(rmet["success_rate"]),
                    "policy_success": float(pmet["success_rate"]),
                    "delta_success": d_succ,
                    "rule_p95_ms": float(rmet["latency_p95_ms"]),
                    "policy_p95_ms": float(pmet["latency_p95_ms"]),
                    "delta_p95_ms": d_p95,
                    "rule_p99_ms": float(rmet["latency_p99_ms"]),
                    "policy_p99_ms": float(pmet["latency_p99_ms"]),
                    "delta_p99_ms": d_p99,
                }
            )
            if d_succ < float(thr["min_success_delta_each"]) - 1e-12:
                no_reg_ok = False
            if d_p99 > float(thr["max_p99_latency_delta_ms_each"]) + 1e-12:
                no_reg_ok = False
            if int(pmet.get("catastrophic_collision_count", 0)) != 0:
                no_reg_ok = False

    # Stress summary deltas.
    d_worst10 = float(p14_policy["summary"]["worst10_success_rate"]) - float(p14_rule["summary"]["worst10_success_rate"])
    d_recover = float(p14_policy["summary"]["recovery_success_rate"]) - float(p14_rule["summary"]["recovery_success_rate"])
    if d_worst10 < float(thr["min_worst10_success_delta"]) - 1e-12:
        no_reg_ok = False
    if d_recover < float(thr["min_recovery_success_delta"]) - 1e-12:
        no_reg_ok = False
    if int(p14_policy["summary"].get("catastrophic_collision_count", 0)) != 0:
        no_reg_ok = False

    # Export paper table.
    table_rows: list[dict] = []
    for phase, rule, pol in [
        ("phase10", p10_rule, p10_policy),
        ("phase12", p12_rule, p12_policy),
    ]:
        for pf in sorted(rule["platform_metrics"].keys()):
            rmet = rule["platform_metrics"][pf]
            pmet = pol["platform_metrics"][pf]
            table_rows.append(
                {
                    "phase": phase,
                    "platform": pf,
                    "rule_success_rate": float(rmet["success_rate"]),
                    "policy_success_rate": float(pmet["success_rate"]),
                    "delta_success_rate": float(pmet["success_rate"]) - float(rmet["success_rate"]),
                    "rule_latency_p95_ms": float(rmet["latency_p95_ms"]),
                    "policy_latency_p95_ms": float(pmet["latency_p95_ms"]),
                    "delta_latency_p95_ms": float(pmet["latency_p95_ms"]) - float(rmet["latency_p95_ms"]),
                    "rule_latency_p99_ms": float(rmet["latency_p99_ms"]),
                    "policy_latency_p99_ms": float(pmet["latency_p99_ms"]),
                    "delta_latency_p99_ms": float(pmet["latency_p99_ms"]) - float(rmet["latency_p99_ms"]),
                    "rule_fast_call_ratio": float(rmet["fast_call_ratio"]),
                    "policy_fast_call_ratio": float(pmet["fast_call_ratio"]),
                    "delta_fast_call_ratio": float(pmet["fast_call_ratio"]) - float(rmet["fast_call_ratio"]),
                    "rule_slow_call_ratio": float(rmet["slow_call_ratio"]),
                    "policy_slow_call_ratio": float(pmet["slow_call_ratio"]),
                    "delta_slow_call_ratio": float(pmet["slow_call_ratio"]) - float(rmet["slow_call_ratio"]),
                }
            )
    table_rows.append(
        {
            "phase": "phase14_stress",
            "platform": "all",
            "rule_success_rate": float(p14_rule["summary"]["overall_success_rate"]),
            "policy_success_rate": float(p14_policy["summary"]["overall_success_rate"]),
            "delta_success_rate": float(p14_policy["summary"]["overall_success_rate"])
            - float(p14_rule["summary"]["overall_success_rate"]),
            "rule_latency_p95_ms": float("nan"),
            "policy_latency_p95_ms": float("nan"),
            "delta_latency_p95_ms": float("nan"),
            "rule_latency_p99_ms": float("nan"),
            "policy_latency_p99_ms": float("nan"),
            "delta_latency_p99_ms": float("nan"),
            "rule_fast_call_ratio": float("nan"),
            "policy_fast_call_ratio": float("nan"),
            "delta_fast_call_ratio": float("nan"),
            "rule_slow_call_ratio": float("nan"),
            "policy_slow_call_ratio": float("nan"),
            "delta_slow_call_ratio": float("nan"),
            "rule_worst10_success_rate": float(p14_rule["summary"]["worst10_success_rate"]),
            "policy_worst10_success_rate": float(p14_policy["summary"]["worst10_success_rate"]),
            "delta_worst10_success_rate": float(d_worst10),
            "rule_recovery_success_rate": float(p14_rule["summary"]["recovery_success_rate"]),
            "policy_recovery_success_rate": float(p14_policy["summary"]["recovery_success_rate"]),
            "delta_recovery_success_rate": float(d_recover),
        }
    )
    df_table = pd.DataFrame(table_rows)
    _ensure_parent(args.paper_table_csv)
    df_table.to_csv(args.paper_table_csv, index=False)

    # Export paper figure.
    _plot_p99_latency(
        out_svg=args.paper_fig_svg,
        out_png=args.paper_fig_png,
        p10_rule=p10_rule,
        p10_policy=p10_policy,
        p12_rule=p12_rule,
        p12_policy=p12_policy,
    )

    gate = {
        "policy_single_source_of_truth": bool(policy_hash_ok),
        "same_selected_cases_phase10": bool(same_cases_p10),
        "same_selected_cases_phase12": bool(same_cases_p12),
        "same_selected_cases_phase14": bool(same_cases_p14),
        "phase10_12_14_gates_all_true_under_policy": bool(policy_phase_gates_ok),
        "policy_vs_rule_no_regression_large": bool(no_reg_ok),
    }

    stats = {
        "version": "router_phase17_policy_alignment_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "policy": {
            "artifact_dir": str(policy_dir),
            "policy_json": str(policy_json),
            "policy_json_sha256": str(policy_sha),
        },
        "thresholds": thr,
        "comparisons": {"rows": rows, "stress": {"delta_worst10_success": d_worst10, "delta_recovery_success": d_recover}},
        "gate_check": gate,
        "artifacts": {
            "out_dir": str(out_dir),
            "report_md": str(args.report_md),
            "paper_table_csv": str(args.paper_table_csv),
            "paper_fig_svg": str(args.paper_fig_svg),
            "paper_fig_png": str(args.paper_fig_png),
            "phase10_rule_stats": str(paths["p10_rule"]),
            "phase10_policy_stats": str(paths["p10_policy"]),
            "phase12_rule_stats": str(paths["p12_rule"]),
            "phase12_policy_stats": str(paths["p12_policy"]),
            "phase14_rule_stats": str(paths["p14_rule"]),
            "phase14_policy_stats": str(paths["p14_policy"]),
        },
    }
    stats_path = out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(args.report_md, stats=stats)

    print(f"[phase17] stats={stats_path}")
    print(f"[phase17] report={args.report_md}")
    print(f"[phase17] gate={gate}")
    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("Phase-17 gate failed. Check outputs/router_phase17_policy_alignment_v1/stats.json")


if __name__ == "__main__":
    main()

