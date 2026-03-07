from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build public-anchor-only comparison table for RS-root claim.")
    p.add_argument("--exp3-summary", type=Path, default=Path("outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv"))
    p.add_argument("--exp4-summary", type=Path, default=Path("outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv"))
    p.add_argument("--out-csv", type=Path, default=Path("paper/tables_rs_root_v1/table_rs_root_anchor_only_comparison.csv"))
    p.add_argument("--report-md", type=Path, default=Path("reports/rs_root_anchor_only_table_v1.md"))
    return p.parse_args()


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _find(rows: list[dict[str, str]], experiment: str, dataset: str, method: str) -> dict[str, str]:
    for row in rows:
        if row.get("experiment") == experiment and row.get("dataset") == dataset and row.get("method") == method:
            return row
    raise KeyError((experiment, dataset, method))


def _fd(x: str) -> float:
    return float(x)


def main() -> None:
    exp3 = _read(args.exp3_summary)
    exp4 = _read(args.exp4_summary)
    rows = []

    exp3_full = _find(exp3, "exp3_ablation", "parasol", "Full")
    exp3_no_rs = _find(exp3, "exp3_ablation", "parasol", "No-RS")
    exp3_no_res = _find(exp3, "exp3_ablation", "parasol", "No-Residual")
    exp3_narrow_full = _find(exp3, "exp3_ablation_scene", "parasol:narrow_passage", "Full")
    exp3_narrow_no_rs = _find(exp3, "exp3_ablation_scene", "parasol:narrow_passage", "No-RS")

    rows.append({
        "block": "hard_bundle_overall",
        "dataset": "parasol (public anchor)",
        "comparison": "Full vs No-RS",
        "metric": "success_rate",
        "ours": exp3_full["success_rate"],
        "baseline": exp3_no_rs["success_rate"],
        "delta": f"{100.0 * (_fd(exp3_full['success_rate']) - _fd(exp3_no_rs['success_rate'])):.3f} pp",
        "comment": "necessity / solvability collapse",
    })
    rows.append({
        "block": "hard_bundle_overall",
        "dataset": "parasol (public anchor)",
        "comparison": "Full vs No-Residual",
        "metric": "avg_expansions",
        "ours": exp3_full["avg_expansions"],
        "baseline": exp3_no_res["avg_expansions"],
        "delta": f"{100.0 * (_fd(exp3_full['avg_expansions']) - _fd(exp3_no_res['avg_expansions'])) / max(abs(_fd(exp3_no_res['avg_expansions'])),1e-12):.3f}%",
        "comment": "residual gain on public anchor bundle",
    })
    rows.append({
        "block": "hard_bundle_overall",
        "dataset": "parasol (public anchor)",
        "comparison": "Full vs No-Residual",
        "metric": "avg_time_ms",
        "ours": exp3_full["avg_time_ms"],
        "baseline": exp3_no_res["avg_time_ms"],
        "delta": f"{100.0 * (_fd(exp3_full['avg_time_ms']) - _fd(exp3_no_res['avg_time_ms'])) / max(abs(_fd(exp3_no_res['avg_time_ms'])),1e-12):.3f}%",
        "comment": "residual gain on public anchor bundle",
    })
    rows.append({
        "block": "narrow_subset",
        "dataset": "parasol:narrow_passage (public anchor subset)",
        "comparison": "Full vs No-RS",
        "metric": "success_rate",
        "ours": exp3_narrow_full["success_rate"],
        "baseline": exp3_narrow_no_rs["success_rate"],
        "delta": f"{100.0 * (_fd(exp3_narrow_full['success_rate']) - _fd(exp3_narrow_no_rs['success_rate'])):.3f} pp",
        "comment": "tiny subset; keep as anchor-only diagnostic, not standalone SOTA claim",
    })

    exp4_ours = _find(exp4, "exp4_public_kinodynamic", "parasol", "Ours")
    exp4_hybrid = _find(exp4, "exp4_public_kinodynamic", "parasol", "Hybrid A* (RS)")
    exp4_bit = _find(exp4, "exp4_public_kinodynamic", "parasol", "Kinodynamic BIT*")
    exp4_rrt = _find(exp4, "exp4_public_kinodynamic", "parasol", "Kinodynamic RRT*")
    rows.append({
        "block": "fair_nearest_baseline",
        "dataset": "parasol (public anchor)",
        "comparison": "Ours vs Hybrid A* (RS)",
        "metric": "avg_expansions",
        "ours": exp4_ours["avg_expansions"],
        "baseline": exp4_hybrid["avg_expansions"],
        "delta": f"{100.0 * (_fd(exp4_ours['avg_expansions']) - _fd(exp4_hybrid['avg_expansions'])) / max(abs(_fd(exp4_hybrid['avg_expansions'])),1e-12):.3f}%",
        "comment": "primary nearest-baseline axis",
    })
    rows.append({
        "block": "fair_nearest_baseline",
        "dataset": "parasol (public anchor)",
        "comparison": "Ours vs Hybrid A* (RS)",
        "metric": "avg_time_ms",
        "ours": exp4_ours["avg_time_ms"],
        "baseline": exp4_hybrid["avg_time_ms"],
        "delta": f"{100.0 * (_fd(exp4_ours['avg_time_ms']) - _fd(exp4_hybrid['avg_time_ms'])) / max(abs(_fd(exp4_hybrid['avg_time_ms'])),1e-12):.3f}%",
        "comment": "primary nearest-baseline axis",
    })
    rows.append({
        "block": "fair_auxiliary_only",
        "dataset": "parasol (public anchor)",
        "comparison": "Ours vs Kinodynamic BIT*",
        "metric": "avg_time_ms",
        "ours": exp4_ours["avg_time_ms"],
        "baseline": exp4_bit["avg_time_ms"],
        "delta": f"{100.0 * (_fd(exp4_ours['avg_time_ms']) - _fd(exp4_bit['avg_time_ms'])) / max(abs(_fd(exp4_bit['avg_time_ms'])),1e-12):.3f}%",
        "comment": "auxiliary only; not allowed as the primary root claim target",
    })
    rows.append({
        "block": "fair_auxiliary_only",
        "dataset": "parasol (public anchor)",
        "comparison": "Ours vs Kinodynamic RRT*",
        "metric": "avg_time_ms",
        "ours": exp4_ours["avg_time_ms"],
        "baseline": exp4_rrt["avg_time_ms"],
        "delta": f"{100.0 * (_fd(exp4_ours['avg_time_ms']) - _fd(exp4_rrt['avg_time_ms'])) / max(abs(_fd(exp4_rrt['avg_time_ms'])),1e-12):.3f}%",
        "comment": "auxiliary only; not allowed as the primary root claim target",
    })

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# RS Root — Public Anchor-Only Comparison Table",
        "",
        "This table preserves a root-claim comparison sheet using only the original public-anchor artifacts.",
        "",
        f"- source exp3 summary: `{args.exp3_summary}`",
        f"- source exp4 fair summary: `{args.exp4_summary}`",
        f"- table csv: `{args.out_csv}`",
        "",
        "| block | dataset | comparison | metric | ours | baseline | delta | comment |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(f"| {r['block']} | {r['dataset']} | {r['comparison']} | {r['metric']} | {r['ours']} | {r['baseline']} | {r['delta']} | {r['comment']} |")
    args.report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[rs-root-anchor-only] csv={args.out_csv}")
    print(f"[rs-root-anchor-only] report={args.report_md}")


if __name__ == "__main__":
    args = parse_args()
    main()
