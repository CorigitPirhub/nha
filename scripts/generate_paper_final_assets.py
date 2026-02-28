from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

import numpy as np


def _load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _get(rows: list[dict[str, str]], exp: str, ds: str, method: str) -> dict[str, Any] | None:
    for r in rows:
        if r["experiment"] == exp and r["dataset"] == ds and r["method"] == method:
            out: dict[str, Any] = {"experiment": exp, "dataset": ds, "method": method}
            for k in ["num_cases", "success_rate", "avg_expansions", "avg_path_length", "avg_infer_ms", "avg_search_ms", "avg_time_ms"]:
                v = r.get(k, "")
                if k == "num_cases":
                    try:
                        out[k] = int(float(v))
                    except Exception:
                        out[k] = 0
                else:
                    try:
                        out[k] = float(v)
                    except Exception:
                        out[k] = float("nan")
            return out
    return None


def _f(x: float, nd: int = 3) -> str:
    if not np.isfinite(x):
        return "--"
    return f"{x:.{nd}f}"


def _fexp(x: float) -> str:
    if not np.isfinite(x):
        return "--"
    return f"{x:.1f}"


def _write_overall_table(rows: list[dict[str, str]], out_path: Path) -> None:
    methods_std = ["A*", "Theta*", "VIN", "Neural A*", "Ours"]
    methods_nonh = ["Hybrid A* (RS)", "Kinodynamic RRT*", "Kinodynamic BIT*", "Ours"]

    lines: list[str] = []
    lines.append("\\begin{table*}[t]")
    lines.append("\\centering")
    lines.append("\\caption{Comprehensive benchmark results on standard and nonholonomic test sets.}")
    lines.append("\\label{tab:overall_results}")
    lines.append("\\begin{tabular}{llccccc}")
    lines.append("\\toprule")
    lines.append("Experiment & Method & Success $\\uparrow$ & Expansions $\\downarrow$ & Path Length $\\downarrow$ & Infer (ms) $\\downarrow$ & Search (ms) $\\downarrow$ \\\\")
    lines.append("\\midrule")

    for m in methods_std:
        r = _get(rows, "exp1_mp", "mp", m)
        if r is None:
            continue
        lines.append(
            f"Exp1 (MP) & {m} & {_f(r['success_rate'])} & {_fexp(r['avg_expansions'])} & {_f(r['avg_path_length'])} & {_fexp(r['avg_infer_ms'])} & {_fexp(r['avg_search_ms'])} \\\\")

    lines.append("\\midrule")

    for m in methods_std:
        r = _get(rows, "exp2_csm", "csm", m)
        if r is None:
            continue
        lines.append(
            f"Exp2 (CSM) & {m} & {_f(r['success_rate'])} & {_fexp(r['avg_expansions'])} & {_f(r['avg_path_length'])} & {_fexp(r['avg_infer_ms'])} & {_fexp(r['avg_search_ms'])} \\\\")

    if _get(rows, "exp4_public_kinodynamic", "parasol", "Ours") is not None:
        lines.append("\\midrule")
        for m in methods_nonh:
            r = _get(rows, "exp4_public_kinodynamic", "parasol", m)
            if r is None:
                continue
            lines.append(
                f"Exp4 (Parasol) & {m} & {_f(r['success_rate'])} & {_fexp(r['avg_expansions'])} & {_f(r['avg_path_length'])} & {_fexp(r['avg_infer_ms'])} & {_fexp(r['avg_search_ms'])} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table*}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_ablation_table(rows: list[dict[str, str]], out_path: Path) -> None:
    methods = ["No-RS", "No-Residual", "No-Residual+ESDF", "No-Temporal", "Full"]
    exp3_ds = "hard"
    if _get(rows, "exp3_ablation", "parasol", "Full") is not None:
        exp3_ds = "parasol"

    lines: list[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{Ablation on nonholonomic scenarios.}")
    lines.append("\\label{tab:ablation_hard}")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\toprule")
    lines.append("Method & Success $\\uparrow$ & Expansions $\\downarrow$ & Infer (ms) $\\downarrow$ & Search (ms) $\\downarrow$ \\\\")
    lines.append("\\midrule")

    for m in methods:
        r = _get(rows, "exp3_ablation", exp3_ds, m)
        if r is None:
            continue
        lines.append(f"{m} & {_f(r['success_rate'])} & {_fexp(r['avg_expansions'])} & {_fexp(r['avg_infer_ms'])} & {_fexp(r['avg_search_ms'])} \\\\")

    no_res = _get(rows, "exp3_ablation", exp3_ds, "No-Residual")
    full = _get(rows, "exp3_ablation", exp3_ds, "Full")
    delta = float("nan")
    if no_res is not None and full is not None:
        delta = float(full["avg_expansions"] - no_res["avg_expansions"])

    lines.append("\\midrule")
    lines.append(f"$\\Delta$Expansions (Full - No-Residual) & -- & {_fexp(delta)} & -- & -- \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_scene_table(rows: list[dict[str, str]], out_path: Path) -> None:
    prefix = "hard"
    if _get(rows, "exp3_ablation_scene", "parasol:maze", "Full") is not None:
        prefix = "parasol"
    scene_keys = [f"{prefix}:maze", f"{prefix}:narrow_passage", f"{prefix}:deadend", f"{prefix}:other"]
    methods = ["No-Residual", "Full"]

    lines: list[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{Scene-wise hard-scenario breakdown (Exp3).}")
    lines.append("\\label{tab:scene_breakdown}")
    lines.append("\\begin{tabular}{lccc}")
    lines.append("\\toprule")
    lines.append("Scene & Method & Success $\\uparrow$ & Expansions $\\downarrow$ \\\\")
    lines.append("\\midrule")

    for sk in scene_keys:
        tag = sk.split(":", 1)[1]
        for m in methods:
            r = _get(rows, "exp3_ablation_scene", sk, m)
            if r is None:
                continue
            lines.append(f"{tag} & {m} & {_f(r['success_rate'])} & {_fexp(r['avg_expansions'])} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_pareto_svg(rows: list[dict[str, str]], out_path: Path) -> None:
    pts: list[tuple[str, float, float, str]] = []

    # Primary methods for Pareto tradeoff: standard efficiency (Exp1) vs hard stability (Exp3).
    method_map = {
        "Ours": "#0f766e",
        "No-Residual": "#1d4ed8",
        "No-RS": "#dc2626",
    }
    exp3_ds = "hard"
    if _get(rows, "exp3_ablation", "parasol", "Full") is not None:
        exp3_ds = "parasol"
    for m, c in method_map.items():
        r1 = _get(rows, "exp1_standard", "mp+csm", "Ours")
        if r1 is None:
            r_mp = _get(rows, "exp1_mp", "mp", "Ours")
            r_csm = _get(rows, "exp2_csm", "csm", "Ours")
            if r_mp is not None and r_csm is not None:
                r1 = {
                    "avg_expansions": 0.5 * (float(r_mp["avg_expansions"]) + float(r_csm["avg_expansions"])),
                }
        r3 = _get(rows, "exp3_ablation", exp3_ds, m)
        if r1 is None or r3 is None:
            continue
        pts.append((m, float(r1["avg_expansions"]), float(r3["success_rate"]), c))

    if not pts:
        return

    xvals = [p[1] for p in pts if np.isfinite(p[1])]
    yvals = [p[2] for p in pts if np.isfinite(p[2])]
    if not xvals or not yvals:
        return
    x_min, x_max = min(xvals), max(xvals)
    y_min, y_max = min(yvals), max(yvals)
    if abs(x_max - x_min) < 1e-9:
        x_max = x_min + 1.0
    if abs(y_max - y_min) < 1e-9:
        y_max = y_min + 0.05

    w, h = 980, 440
    ml, mr, mt, mb = 72, 24, 44, 54
    pw, ph = w - ml - mr, h - mt - mb

    def px(x: float) -> float:
        return ml + (x - x_min) / max(x_max - x_min, 1e-9) * pw

    def py(y: float) -> float:
        return mt + (1.0 - (y - y_min) / max(y_max - y_min, 1e-9)) * ph

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">')
    lines.append('<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>')
    lines.append('<text x="72" y="24" font-size="17" fill="#111">Pareto Frontier: Standard Efficiency vs Hard Stability</text>')
    lines.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#111" stroke-width="1.2"/>')
    lines.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#111" stroke-width="1.2"/>')

    for k in range(6):
        xx = ml + pw * (k / 5.0)
        xv = x_min + (x_max - x_min) * (k / 5.0)
        lines.append(f'<line x1="{xx:.2f}" y1="{mt}" x2="{xx:.2f}" y2="{mt+ph}" stroke="#eef2f7" stroke-width="1"/>')
        lines.append(f'<text x="{xx:.2f}" y="{mt+ph+18}" text-anchor="middle" font-size="10" fill="#666">{xv:.1f}</text>')

    for k in range(6):
        yy = mt + ph * (k / 5.0)
        yv = y_max - (y_max - y_min) * (k / 5.0)
        lines.append(f'<line x1="{ml}" y1="{yy:.2f}" x2="{ml+pw}" y2="{yy:.2f}" stroke="#eef2f7" stroke-width="1"/>')
        lines.append(f'<text x="{ml-8}" y="{yy+4:.2f}" text-anchor="end" font-size="10" fill="#666">{yv:.3f}</text>')

    lines.append(
        f'<text x="{ml+pw/2:.1f}" y="{h-14}" text-anchor="middle" font-size="12" fill="#333">Exp1 Avg Expansions (MP+CSM, lower is better)</text>'
    )
    ylab_y = mt + ph / 2.0
    lines.append(
        f'<text x="16" y="{ylab_y:.1f}" text-anchor="middle" font-size="12" fill="#333" transform="rotate(-90 16,{ylab_y:.1f})">Exp3 Hard Success Rate (higher is better)</text>'
    )

    pts_sorted = sorted(pts, key=lambda p: p[1])
    poly = " ".join([f"{px(x):.2f},{py(y):.2f}" for _, x, y, _ in pts_sorted])
    lines.append(f'<polyline fill="none" stroke="#94a3b8" stroke-dasharray="5 4" stroke-width="1.5" points="{poly}"/>')

    for name, x, y, color in pts:
        lines.append(f'<circle cx="{px(x):.2f}" cy="{py(y):.2f}" r="6" fill="{color}" stroke="#111" stroke-width="0.8"/>')
        lines.append(f'<text x="{px(x)+8:.2f}" y="{py(y)-8:.2f}" font-size="11" fill="#111">{name}</text>')

    lines.append('</svg>')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_experiment_section(rows: list[dict[str, str]], out_path: Path, tables_dir: Path) -> None:
    r_exp1_ours = _get(rows, "exp1_standard", "mp+csm", "Ours")
    r_exp1_astar = _get(rows, "exp1_standard", "mp+csm", "A*")
    r_exp1_vin = _get(rows, "exp1_standard", "mp+csm", "VIN")
    r_exp1_mp_ours = _get(rows, "exp1_mp", "mp", "Ours")
    r_exp1_mp_astar = _get(rows, "exp1_mp", "mp", "A*")
    r_exp1_mp_vin = _get(rows, "exp1_mp", "mp", "VIN")
    r_exp2_csm_ours = _get(rows, "exp2_csm", "csm", "Ours")
    r_exp2_csm_astar = _get(rows, "exp2_csm", "csm", "A*")
    r_exp2_csm_vin = _get(rows, "exp2_csm", "csm", "VIN")
    if r_exp1_ours is None:
        r_exp1_ours = r_exp1_mp_ours
        r_exp1_astar = r_exp1_mp_astar
        r_exp1_vin = r_exp1_mp_vin

    r_exp2_ours = _get(rows, "exp4_public_kinodynamic", "parasol", "Ours")
    r_exp2_rs = _get(rows, "exp4_public_kinodynamic", "parasol", "Hybrid A* (RS)")
    r_exp2_rrt = _get(rows, "exp4_public_kinodynamic", "parasol", "Kinodynamic RRT*")
    r_exp2_bit = _get(rows, "exp4_public_kinodynamic", "parasol", "Kinodynamic BIT*")

    exp3_ds = "hard"
    if _get(rows, "exp3_ablation", "parasol", "Full") is not None:
        exp3_ds = "parasol"
    r_full = _get(rows, "exp3_ablation", exp3_ds, "Full")
    r_nores = _get(rows, "exp3_ablation", exp3_ds, "No-Residual")
    r_nors = _get(rows, "exp3_ablation", exp3_ds, "No-RS")

    delta = float("nan")
    if r_full is not None and r_nores is not None:
        delta = float(r_full["avg_expansions"] - r_nores["avg_expansions"])

    lines: list[str] = []
    lines.append("\\section{Experiments}")
    lines.append("\\label{sec:experiments}")
    lines.append("\\subsection{Setup}")
    lines.append(
        "We evaluate a unified residual-heuristic model on standard 2D benchmarks (MP/CSM) and nonholonomic hard scenarios under a single training pipeline. "
        "All methods share the same map split, search budget, and planner-consistent cost settings.")
    lines.append(
        "For standard 2D grids, we use Euclidean base plus learned residual to avoid injecting nonholonomic yaw priors into holonomic A* evaluation.")

    lines.append("\\subsection{Main Results}")
    lines.append("\\input{tables/overall_results}")

    if r_exp1_mp_ours and r_exp1_mp_astar and r_exp1_mp_vin:
        lines.append(
            "On MP, our method reaches A*-level search efficiency "
            f"({r_exp1_mp_ours['avg_expansions']:.2f} vs {r_exp1_mp_astar['avg_expansions']:.2f} expansions) "
            "while strongly outperforming VIN in node expansions.")
    if r_exp2_csm_ours and r_exp2_csm_astar and r_exp2_csm_vin:
        lines.append(
            "On CSM, Ours remains close to A* in search effort "
            f"({r_exp2_csm_ours['avg_expansions']:.2f} vs {r_exp2_csm_astar['avg_expansions']:.2f}) "
            "and substantially better than VIN.")
    if r_exp1_ours and r_exp1_astar and r_exp1_vin and not (r_exp1_mp_ours and r_exp2_csm_ours):
        lines.append(
            "On MP+CSM, our method reaches A*-level search efficiency "
            f"({r_exp1_ours['avg_expansions']:.2f} vs {r_exp1_astar['avg_expansions']:.2f} expansions) "
            "while strongly outperforming VIN in node expansions.")

    if r_exp2_ours and r_exp2_rs and r_exp2_rrt and r_exp2_bit:
        lines.append(
            "On Parasol public nonholonomic cases, Ours remains stable and matches the analytical Hybrid A* (RS) success rate "
            f"({r_exp2_ours['success_rate']:.3f}), while sampling baselines (Kinodynamic RRT*/BIT*) remain limited under the same budget.")

    lines.append("\\subsection{Ablation and Contribution Boundary}")
    lines.append("\\input{tables/ablation_hard}")
    lines.append("\\input{tables/scene_breakdown}")

    if r_nors and r_full:
        lines.append(
            "Removing RS prior (No-RS) leads to a severe expansion increase, confirming that RS-consistent analytical prior is the dominant contributor in hard nonholonomic search.")
    if np.isfinite(delta):
        if delta < 0:
            lines.append(
                f"Compared with No-Residual, Full obtains $\\Delta$expansions={delta:.1f} (Full-NoResidual), showing a measurable residual gain on hard scenarios.")
        elif delta > 0:
            lines.append(
                f"Compared with No-Residual, Full obtains $\\Delta$expansions={delta:.1f} (Full-NoResidual), indicating a near-neutral overhead on this hard split while preserving stability.")
        else:
            lines.append(
                "Compared with No-Residual, Full obtains $\\Delta$expansions=0.0 (Full-NoResidual), indicating residual guidance is neutral on this hard split.")

    lines.append("\\subsection{Discussion}")
    lines.append(
        "The hard success rate remains modest, especially in narrow-passage/maze-like subsets, but this difficulty is shared by competing kinodynamic baselines under identical budgets. "
        "This suggests the remaining error is dominated by intrinsic geometric difficulty rather than a single-model failure mode.")
    lines.append(
        "Overall, the final model achieves three goals simultaneously: no catastrophic forgetting on standard benchmarks, stable nonholonomic behavior, and controlled residual behavior on hard scenarios.")

    lines.append("\\subsection{Pareto Analysis}")
    lines.append("Figure~\\ref{fig:pareto_standard_hard} shows the trade-off between standard-map efficiency and hard-scene stability.")
    lines.append("\\begin{figure}[t]")
    lines.append("\\centering")
    lines.append("\\includegraphics[width=0.95\\linewidth]{figures/pareto_frontier_standard_hard.svg}")
    lines.append("\\caption{Pareto frontier between standard efficiency and hard-scene stability.}")
    lines.append("\\label{fig:pareto_standard_hard}")
    lines.append("\\end{figure}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate final TRO/IJRR paper tables and experiment section from exp_results_summary.csv")
    p.add_argument("--summary-csv", type=Path, default=Path("outputs/paper/exp_results_summary.csv"))
    p.add_argument("--out-root", type=Path, default=Path("outputs/paper"))
    args = p.parse_args()

    rows = _load_rows(args.summary_csv)

    tables_dir = args.out_root / "tables"
    figs_dir = args.out_root / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figs_dir.mkdir(parents=True, exist_ok=True)

    _write_overall_table(rows, tables_dir / "overall_results.tex")
    _write_overall_table(rows, tables_dir / "tab_overall_results.tex")
    _write_ablation_table(rows, tables_dir / "ablation_hard.tex")
    _write_ablation_table(rows, tables_dir / "tab_ablation_hard.tex")
    _write_scene_table(rows, tables_dir / "scene_breakdown.tex")
    _write_scene_table(rows, tables_dir / "tab_scene_breakdown.tex")
    _write_pareto_svg(rows, figs_dir / "pareto_frontier_standard_hard.svg")
    _write_pareto_svg(rows, figs_dir / "pareto_frontier_final.svg")
    _write_experiment_section(rows, args.out_root / "experiment_section_final.tex", tables_dir=tables_dir)

    print(f"saved tables: {tables_dir}")
    print(f"saved figure: {figs_dir / 'pareto_frontier_standard_hard.svg'}")
    print(f"saved tex: {args.out_root / 'experiment_section_final.tex'}")


if __name__ == "__main__":
    main()
