from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_baselines import (
    NeuralHeuristicPredictor,
    _compute_case_rs_field,
    _load_nonholonomic_case,
    _make_ours_anchor,
    _make_rs_anchor,
    _path_length,
    _run_hybrid_method,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="P0-C RS root nearest-baseline axis search on rs_root_hard_v2.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark/rs_root_hard_v2"))
    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--budget-caps", type=str, default="2500,3500,5000,7000")
    p.add_argument("--dev-per-family", type=int, default=2)
    p.add_argument("--path-delta-max-percent", type=float, default=1.0)
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
    p.add_argument("--out-root", type=Path, default=Path("outputs/rs_root_p0c_axis_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/rs_root_p0c_axis_v1.md"))
    return p.parse_args()


def _parse_caps(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
    if not vals:
        raise ValueError("empty budget caps")
    return vals


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _select_dev_subset(files: list[Path], per_family: int) -> list[Path]:
    if int(per_family) <= 0:
        return list(files)
    by_scenario: dict[str, list[Path]] = defaultdict(list)
    for p in files:
        with np.load(p, allow_pickle=False) as z:
            by_scenario[str(z["scenario"])] .append(p)
    chosen: list[Path] = []
    for scenario, group in sorted(by_scenario.items()):
        chosen.extend(group[: int(per_family)])
    return sorted(chosen)


def _case_rows(split: str, files: list[Path], caps: list[int], predictor: NeuralHeuristicPredictor, args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(files)
    for i, path in enumerate(files, start=1):
        case = _load_nonholonomic_case(path)
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=int(args.rs_field_yaw_bins))
        rs_anchor = _make_rs_anchor(case, rs_field=rs_field)
        ours_anchor = _make_ours_anchor(
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
        for cap in caps:
            r_h = _run_hybrid_method(case, rs_anchor, max_expansions=int(cap))
            r_o = _run_hybrid_method(case, ours_anchor, max_expansions=int(cap))
            rows.append({
                "split": split,
                "cap": int(cap),
                "sample_name": path.name,
                "scenario": str(case["scenario"]),
                "difficulty": str(case["difficulty"]),
                "method": "Hybrid A* (RS)",
                "success": float(r_h["success"]),
                "expansions": float(r_h["expansions"]),
                "path_length": float(_path_length(r_h["path"])) if r_h["path"] else float("nan"),
                "time_ms": float(r_h["runtime_ms"]),
            })
            rows.append({
                "split": split,
                "cap": int(cap),
                "sample_name": path.name,
                "scenario": str(case["scenario"]),
                "difficulty": str(case["difficulty"]),
                "method": "Ours",
                "success": float(r_o["success"]),
                "expansions": float(r_o["expansions"]),
                "path_length": float(_path_length(r_o["path"])) if r_o["path"] else float("nan"),
                "time_ms": float(r_o["runtime_ms"]),
            })
        if i % 5 == 0 or i == total:
            print(f"[rs-root-p0c] split={split} processed {i}/{total}")
    return rows


def _summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["split"]), int(row["cap"]), str(row["method"]))].append(row)
    out = []
    for (split, cap, method), grp in sorted(groups.items()):
        succ = np.asarray([float(r["success"]) for r in grp], dtype=np.float64)
        exp = np.asarray([float(r["expansions"]) for r in grp], dtype=np.float64)
        path = np.asarray([float(r["path_length"]) for r in grp if np.isfinite(float(r["path_length"]))], dtype=np.float64)
        time_arr = np.asarray([float(r["time_ms"]) for r in grp], dtype=np.float64)
        out.append({
            "split": split,
            "cap": int(cap),
            "method": method,
            "num_cases": int(len(grp)),
            "success_rate": float(np.mean(succ)),
            "avg_expansions": float(np.mean(exp)),
            "avg_path_length": float(np.mean(path)) if path.size else float("nan"),
            "avg_time_ms": float(np.mean(time_arr)),
        })
    return out


def _select_cap(dev_summary: list[dict[str, Any]], path_delta_max_percent: float) -> tuple[int, dict[str, Any]]:
    by = {(r["cap"], r["method"]): r for r in dev_summary}
    candidates = []
    caps = sorted(set(int(r["cap"]) for r in dev_summary))
    for cap in caps:
        ours = by[(cap, "Ours")]
        base = by[(cap, "Hybrid A* (RS)")]
        success_delta_pp = 100.0 * (float(ours["success_rate"]) - float(base["success_rate"]))
        exp_delta_pct = 100.0 * (float(ours["avg_expansions"]) - float(base["avg_expansions"])) / max(abs(float(base["avg_expansions"])), 1e-12)
        time_delta_pct = 100.0 * (float(ours["avg_time_ms"]) - float(base["avg_time_ms"])) / max(abs(float(base["avg_time_ms"])), 1e-12)
        path_delta_pct = 100.0 * (float(ours["avg_path_length"]) - float(base["avg_path_length"])) / max(abs(float(base["avg_path_length"])), 1e-12)
        acceptable_path = bool(path_delta_pct <= float(path_delta_max_percent))
        candidates.append({
            "cap": int(cap),
            "success_delta_pp": float(success_delta_pp),
            "exp_delta_pct": float(exp_delta_pct),
            "time_delta_pct": float(time_delta_pct),
            "path_delta_pct": float(path_delta_pct),
            "acceptable_path": acceptable_path,
        })
    feasible = [c for c in candidates if c["acceptable_path"]]
    if not feasible:
        feasible = candidates
    feasible.sort(key=lambda x: (x["success_delta_pp"], -x["time_delta_pct"], -x["exp_delta_pct"]), reverse=True)
    chosen = feasible[0]
    return int(chosen["cap"]), chosen


def _test_family_summary(rows: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if int(row["cap"]) != int(cap) or str(row["split"]) != "test":
            continue
        groups[(str(row["scenario"]), str(row["method"]))].append(row)
    out = []
    for (scenario, method), grp in sorted(groups.items()):
        succ = np.asarray([float(r["success"]) for r in grp], dtype=np.float64)
        exp = np.asarray([float(r["expansions"]) for r in grp], dtype=np.float64)
        path = np.asarray([float(r["path_length"]) for r in grp if np.isfinite(float(r["path_length"]))], dtype=np.float64)
        time_arr = np.asarray([float(r["time_ms"]) for r in grp], dtype=np.float64)
        out.append({
            "scenario": scenario,
            "method": method,
            "num_cases": len(grp),
            "success_rate": float(np.mean(succ)),
            "avg_expansions": float(np.mean(exp)),
            "avg_path_length": float(np.mean(path)) if path.size else float("nan"),
            "avg_time_ms": float(np.mean(time_arr)),
        })
    return out


def main() -> None:
    args = parse_args()
    caps = _parse_caps(args.budget_caps)
    dev_files_all = sorted((args.benchmark_root / "dev").glob("sample_*.npz"))
    dev_files = _select_dev_subset(dev_files_all, int(args.dev_per_family))
    test_files = sorted((args.benchmark_root / "test").glob("sample_*.npz"))
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)

    t0 = time.perf_counter()
    dev_rows = _case_rows("dev", dev_files, caps, predictor, args)
    dev_summary = _summary(dev_rows)
    selected_cap, selected_info = _select_cap(dev_summary, path_delta_max_percent=float(args.path_delta_max_percent))
    print(f"[rs-root-p0c] selected dev cap={selected_cap} info={selected_info}")
    test_rows = _case_rows("test", test_files, [selected_cap], predictor, args)
    test_summary = _summary(test_rows)
    family_summary = _test_family_summary(test_rows, selected_cap)

    args.out_root.mkdir(parents=True, exist_ok=True)
    with (args.out_root / "dev_case_rows.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(dev_rows[0].keys()))
        writer.writeheader(); writer.writerows(dev_rows)
    with (args.out_root / "dev_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(dev_summary[0].keys()))
        writer.writeheader(); writer.writerows(dev_summary)
    with (args.out_root / "test_case_rows.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(test_rows[0].keys()))
        writer.writeheader(); writer.writerows(test_rows)
    with (args.out_root / "test_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(test_summary[0].keys()))
        writer.writeheader(); writer.writerows(test_summary)
    with (args.out_root / "test_family_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(family_summary[0].keys()))
        writer.writeheader(); writer.writerows(family_summary)

    inputs = {
        str(args.benchmark_root / "meta.json"): _sha256(args.benchmark_root / "meta.json"),
        str(args.benchmark_root / "dev_index.csv"): _sha256(args.benchmark_root / "dev_index.csv"),
        str(args.benchmark_root / "test_index.csv"): _sha256(args.benchmark_root / "test_index.csv"),
        str(args.ours_checkpoint): _sha256(args.ours_checkpoint),
    }
    manifest = {
        "version": "rs_root_p0c_axis_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "benchmark_root": str(args.benchmark_root),
        "inputs_sha256": inputs,
        "budget_caps_dev": caps,
        "dev_per_family": int(args.dev_per_family),
        "dev_cases_total": int(len(dev_files_all)),
        "dev_cases_used_for_selection": int(len(dev_files)),
        "selected_cap_from_dev": int(selected_cap),
        "selected_cap_dev_stats": selected_info,
        "path_delta_max_percent": float(args.path_delta_max_percent),
    }
    (args.out_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    dev_by = {(r["cap"], r["method"]): r for r in dev_summary}
    test_by = {(r["cap"], r["method"]): r for r in test_summary}
    dev_o = dev_by[(selected_cap, "Ours")]
    dev_h = dev_by[(selected_cap, "Hybrid A* (RS)")]
    test_o = test_by[(selected_cap, "Ours")]
    test_h = test_by[(selected_cap, "Hybrid A* (RS)")]
    lines = [
        "# P0-C RS Root Axis Report (V1)",
        "",
        "Selection rule:",
        f"- Search fixed budget caps on a stratified `dev` subset only (`per_family={int(args.dev_per_family)}`, used `{len(dev_files)}` / `{len(dev_files_all)}` cases).",
        "- Require acceptable path delta (or fall back to best available if none passes).",
        "- Choose by success delta first, then time reduction, then expansion reduction.",
        "- Evaluate the chosen cap on `test` exactly once.",
        "",
        f"Selected cap from dev: `{selected_cap}`",
        f"- dev success delta (pp): `{selected_info['success_delta_pp']:.3f}`",
        f"- dev expansion delta (%): `{selected_info['exp_delta_pct']:.3f}`",
        f"- dev time delta (%): `{selected_info['time_delta_pct']:.3f}`",
        f"- dev path delta (%): `{selected_info['path_delta_pct']:.3f}`",
        "",
        "## Test Summary at Selected Cap",
        f"- Ours success: `{float(test_o['success_rate']):.6f}`",
        f"- Hybrid success: `{float(test_h['success_rate']):.6f}`",
        f"- success delta (pp): `{100.0 * (float(test_o['success_rate']) - float(test_h['success_rate'])):.3f}`",
        f"- expansions delta (%): `{100.0 * (float(test_o['avg_expansions']) - float(test_h['avg_expansions'])) / max(abs(float(test_h['avg_expansions'])),1e-12):.3f}`",
        f"- time delta (%): `{100.0 * (float(test_o['avg_time_ms']) - float(test_h['avg_time_ms'])) / max(abs(float(test_h['avg_time_ms'])),1e-12):.3f}`",
        f"- path delta (%): `{100.0 * (float(test_o['avg_path_length']) - float(test_h['avg_path_length'])) / max(abs(float(test_h['avg_path_length'])),1e-12):.3f}`",
        "",
        "## Test Family Summary",
    ]
    header = "| scenario | method | n | success | expansions | path_len | time_ms |"
    sep = "|---|---:|---:|---:|---:|---:|---:|"
    lines.extend([header, sep])
    for row in family_summary:
        lines.append(f"| {row['scenario']} | {row['method']} | {row['num_cases']} | {row['success_rate']:.3f} | {row['avg_expansions']:.3f} | {row['avg_path_length']:.3f} | {row['avg_time_ms']:.3f} |")
    args.report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[rs-root-p0c] report={args.report_md}")
    print(f"[rs-root-p0c] out_root={args.out_root}")


if __name__ == "__main__":
    main()
