from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_baselines import (
    NeuralHeuristicPredictor,
    _compute_case_rs_field,
    _load_nonholonomic_case,
    _make_no_rs_anchor,
    _make_ours_anchor,
    _make_rs_anchor,
    _path_length,
    _run_hybrid_method,
    _scenario_bucket,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RS-root hard benchmark evaluation v1 (Full/No-RS/No-Residual only).")
    p.add_argument("--hard-root", type=Path, default=Path("data/benchmark/rs_root_hard_v1/test"))
    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--max-cases", type=int, default=-1)
    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--hybrid-max-expansions", type=int, default=12000)
    p.add_argument("--hybrid-hard-max-expansions", type=int, default=13000)
    p.add_argument("--hybrid-maze-max-expansions", type=int, default=18000)
    p.add_argument("--hybrid-budget-cap", type=int, default=7000)
    p.add_argument("--rs-field-yaw-bins", type=int, default=24)
    p.add_argument("--residual-alpha", type=float, default=0.675)
    p.add_argument("--residual-clip", type=float, default=28.0)
    p.add_argument("--residual-bias-quantile", type=float, default=0.25)
    p.add_argument("--residual-corridor-threshold", type=float, default=0.9)
    p.add_argument("--residual-corridor-suppress", type=float, default=0.3)
    p.add_argument("--residual-topq-quantile", type=float, default=0.1)
    p.add_argument("--residual-contrastive-bg-quantile", type=float, default=0.62)
    p.add_argument("--residual-contrastive-neg-scale", type=float, default=0.16)
    p.add_argument("--residual-contrastive-pos-scale", type=float, default=1.25)
    p.add_argument("--residual-floor-ratio", type=float, default=0.62)
    p.add_argument("--residual-open-boost", type=float, default=0.45)
    p.add_argument("--residual-open-boost-topq", type=float, default=0.9)
    p.add_argument("--residual-open-boost-min-line-clearance", type=float, default=1.8)
    p.add_argument("--esdf-anchor-alpha", type=float, default=0.15)
    p.add_argument("--esdf-anchor-threshold", type=float, default=1.3)
    p.add_argument("--summary-csv", type=Path, default=Path("outputs/paper/rs_root_hard_v1_exp3/exp_results_summary.csv"))
    p.add_argument("--report-md", type=Path, default=Path("reports/rs_root_hard_v1_exp3.md"))
    p.add_argument("--manifest-json", type=Path, default=Path("outputs/paper/rs_root_hard_v1_exp3/manifest.json"))
    return p.parse_args()


def _planner_budget(planner_cfg, case: dict, args: argparse.Namespace) -> int:
    cap = int(max(planner_cfg.max_expansions, args.hybrid_max_expansions))
    if case["difficulty"] == "hard":
        cap = max(cap, int(args.hybrid_hard_max_expansions))
    if case["scenario"] in {"maze_single", "maze", "deadend_labyrinth"}:
        cap = max(cap, int(args.hybrid_maze_max_expansions))
    if int(args.hybrid_budget_cap) > 0:
        cap = min(cap, int(args.hybrid_budget_cap))
    return cap


def _collect_rows(args: argparse.Namespace) -> list[dict[str, object]]:
    files = sorted(Path(args.hard_root).glob("sample_*.npz"))
    if int(args.max_cases) > 0:
        files = files[: int(args.max_cases)]
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    rows: list[dict[str, object]] = []
    for i, path in enumerate(files, start=1):
        case = _load_nonholonomic_case(path)
        budget = _planner_budget(case["planner_cfg"], case, args)
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=int(args.rs_field_yaw_bins))
        rs_anchor = _make_rs_anchor(case, rs_field=rs_field)
        full_anchor = _make_ours_anchor(
            case,
            predictor,
            args.residual_alpha,
            args.residual_clip,
            args.residual_bias_quantile,
            args.residual_corridor_threshold,
            args.residual_corridor_suppress,
            args.residual_topq_quantile,
            args.residual_contrastive_bg_quantile,
            args.residual_contrastive_neg_scale,
            args.residual_contrastive_pos_scale,
            args.residual_floor_ratio,
            0,
            0.0,
            1.0,
            0.0,
            0.0,
            1.0,
            args.residual_open_boost,
            args.residual_open_boost_topq,
            args.residual_open_boost_min_line_clearance,
            0.0,
            0.0,
            0.95,
            False,
            rs_base_override=rs_field,
        )
        no_rs_anchor = _make_no_rs_anchor(case, predictor, residual_clip=args.residual_clip)
        r_rs = _run_hybrid_method(case, rs_anchor, max_expansions=budget)
        r_full = _run_hybrid_method(case, full_anchor, max_expansions=budget)
        r_no_rs = _run_hybrid_method(case, no_rs_anchor, max_expansions=budget)
        bucket = _scenario_bucket(case["scenario"])
        for method, rr in [("Full", r_full), ("No-RS", r_no_rs), ("No-Residual", r_rs)]:
            rows.append({
                "experiment": "exp3_ablation",
                "dataset": "rs_root_hard_v1",
                "scenario_bucket": bucket,
                "scenario": str(case["scenario"]),
                "method": method,
                "case_id": path.name,
                "success": float(rr["success"]),
                "expansions": float(rr["expansions"]) if rr["expansions"] is not None else float("nan"),
                "path_length": float(_path_length(rr["path"])) if rr["path"] else float("nan"),
                "time_ms": float(rr["runtime_ms"]) if rr["runtime_ms"] is not None else float("nan"),
            })
        if i % 5 == 0 or i == len(files):
            print(f"[rs-root-exp3] processed {i}/{len(files)} cases")
    return rows


def _aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    groups = defaultdict(list)
    for r in rows:
        groups[(str(r["experiment"]), str(r["dataset"]), str(r["method"]))].append(r)
        groups[("exp3_ablation_scene", f"rs_root_hard_v1:{r['scenario_bucket']}", str(r["method"]))].append(r)
    for (exp, ds, method), grp in sorted(groups.items()):
        succ = np.asarray([float(r["success"]) for r in grp], dtype=np.float64)
        exps = np.asarray([float(r["expansions"]) for r in grp if np.isfinite(float(r["expansions"]))], dtype=np.float64)
        lens = np.asarray([float(r["path_length"]) for r in grp if np.isfinite(float(r["path_length"]))], dtype=np.float64)
        times = np.asarray([float(r["time_ms"]) for r in grp if np.isfinite(float(r["time_ms"]))], dtype=np.float64)
        out.append({
            "experiment": exp,
            "dataset": ds,
            "method": method,
            "num_cases": len(grp),
            "success_rate": float(np.mean(succ)) if succ.size else float("nan"),
            "avg_expansions": float(np.mean(exps)) if exps.size else float("nan"),
            "avg_path_length": float(np.mean(lens)) if lens.size else float("nan"),
            "avg_time_ms": float(np.mean(times)) if times.size else float("nan"),
        })
    return out


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    rows = _collect_rows(args)
    summary = _aggregate(rows)
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["experiment", "dataset", "method", "num_cases", "success_rate", "avg_expansions", "avg_path_length", "avg_time_ms"])
        writer.writeheader()
        writer.writerows(summary)

    by_key = {(r["experiment"], r["dataset"], r["method"]): r for r in summary}
    full = by_key[("exp3_ablation", "rs_root_hard_v1", "Full")]
    no_rs = by_key[("exp3_ablation", "rs_root_hard_v1", "No-RS")]
    no_res = by_key[("exp3_ablation", "rs_root_hard_v1", "No-Residual")]
    manifest = {
        "version": "rs_root_hard_v1_exp3",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "hard_root": str(args.hard_root),
        "summary_csv": str(args.summary_csv),
        "rows": {
            "full": full,
            "no_rs": no_rs,
            "no_residual": no_res,
        },
        "derived": {
            "success_drop_pp_full_to_no_rs": 100.0 * (float(full["success_rate"]) - float(no_rs["success_rate"])),
            "delta_expansions_full_vs_no_residual_percent": 100.0 * (float(full["avg_expansions"]) - float(no_res["avg_expansions"])) / max(abs(float(no_res["avg_expansions"])), 1e-12),
            "delta_time_full_vs_no_residual_percent": 100.0 * (float(full["avg_time_ms"]) - float(no_res["avg_time_ms"])) / max(abs(float(no_res["avg_time_ms"])), 1e-12),
        },
    }
    args.manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# RS Root Hard Benchmark Exp3 Audit (V1)",
        "",
        f"- hard root: `{args.hard_root}`",
        f"- summary csv: `{args.summary_csv}`",
        f"- success Full vs No-RS: `{float(full['success_rate']):.6f}` vs `{float(no_rs['success_rate']):.6f}`",
        f"- expansions Full vs No-Residual: `{float(full['avg_expansions']):.3f}` vs `{float(no_res['avg_expansions']):.3f}`",
        f"- time Full vs No-Residual: `{float(full['avg_time_ms']):.3f}` vs `{float(no_res['avg_time_ms']):.3f}`",
        f"- success drop (pp): `{manifest['derived']['success_drop_pp_full_to_no_rs']:.3f}`",
        f"- dE Full vs No-Residual: `{manifest['derived']['delta_expansions_full_vs_no_residual_percent']:.3f}%`",
        f"- dT Full vs No-Residual: `{manifest['derived']['delta_time_full_vs_no_residual_percent']:.3f}%`",
        "",
        "Scene-bucket rows:",
    ]
    for r in summary:
        if str(r['experiment']) == 'exp3_ablation_scene':
            lines.append(f"- `{r['dataset']}` / `{r['method']}`: success=`{float(r['success_rate']):.6f}`, expansions=`{r['avg_expansions']}`, time_ms=`{r['avg_time_ms']}`")
    args.report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[rs-root-exp3] summary={args.summary_csv}")
    print(f"[rs-root-exp3] report={args.report_md}")
    print(f"[rs-root-exp3] manifest={args.manifest_json}")


if __name__ == "__main__":
    main()
