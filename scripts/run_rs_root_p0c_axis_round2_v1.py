from __future__ import annotations

import argparse
import csv
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
    p = argparse.ArgumentParser(description="P0-C round2 fixed-axis verification on rs_root_hard_v2.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark/rs_root_hard_v2"))
    p.add_argument("--prior-manifest", type=Path, default=Path("outputs/rs_root_p0c_axis_v1/manifest.json"))
    p.add_argument("--fixed-cap", type=int, default=-1)
    p.add_argument("--families", type=str, default="narrow_passage,maze,deadend_labyrinth")
    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--bootstrap-n", type=int, default=5000)
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
    p.add_argument("--out-root", type=Path, default=Path("outputs/rs_root_p0c_axis_round2_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/rs_root_p0c_axis_round2_v1.md"))
    return p.parse_args()


def _families(raw: str) -> set[str]:
    return {x.strip() for x in str(raw).split(",") if x.strip()}


def _bootstrap_mean_ci(delta: np.ndarray, n_boot: int) -> tuple[float, float, float]:
    arr = np.asarray(delta, dtype=np.float64)
    n = int(arr.size)
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(20260307)
    boots = np.empty(int(n_boot), dtype=np.float64)
    for i in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        boots[i] = float(np.mean(arr[idx]))
    lo = float(np.quantile(boots, 0.025))
    hi = float(np.quantile(boots, 0.975))
    p_gt0 = float(np.mean(boots <= 0.0))
    return float(np.mean(arr)), lo, hi, p_gt0


def _fixed_cap(args: argparse.Namespace) -> int:
    if int(args.fixed_cap) > 0:
        return int(args.fixed_cap)
    d = json.loads(args.prior_manifest.read_text(encoding="utf-8"))
    return int(d["dev_selection"]["cap"])


def _filter_files(split_dir: Path, families: set[str], *, anchor_only: bool | None) -> list[Path]:
    out = []
    for p in sorted(split_dir.glob("sample_*.npz")):
        with np.load(p, allow_pickle=False) as z:
            scenario = str(z["scenario"])
            source = str(z.get("source_dataset", "unknown"))
        if scenario not in families:
            continue
        if anchor_only is True and source != "parasol_public_anchor":
            continue
        if anchor_only is False and source == "parasol_public_anchor":
            continue
        out.append(p)
    return out


def _run(files: list[Path], cap: int, predictor: NeuralHeuristicPredictor, args: argparse.Namespace, split: str, group: str) -> list[dict[str, Any]]:
    rows = []
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
        rh = _run_hybrid_method(case, rs_anchor, max_expansions=int(cap))
        ro = _run_hybrid_method(case, ours_anchor, max_expansions=int(cap))
        rows.append({
            "split": split,
            "group": group,
            "scenario": str(case["scenario"]),
            "sample_name": path.name,
            "method": "Hybrid A* (RS)",
            "success": float(rh["success"]),
            "expansions": float(rh["expansions"]),
            "path_length": float(_path_length(rh["path"])) if rh["path"] else float("nan"),
            "time_ms": float(rh["runtime_ms"]),
        })
        rows.append({
            "split": split,
            "group": group,
            "scenario": str(case["scenario"]),
            "sample_name": path.name,
            "method": "Ours",
            "success": float(ro["success"]),
            "expansions": float(ro["expansions"]),
            "path_length": float(_path_length(ro["path"])) if ro["path"] else float("nan"),
            "time_ms": float(ro["runtime_ms"]),
        })
        if i % 5 == 0 or i == total:
            print(f"[rs-root-p0c-r2] split={split} group={group} processed {i}/{total}")
    return rows


def _paired_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = defaultdict(dict)
    for row in rows:
        by_name[row["sample_name"]][row["method"]] = row
    succ_delta = []
    exp_delta = []
    time_delta = []
    path_delta = []
    family = defaultdict(list)
    for sample, pack in sorted(by_name.items()):
        if "Ours" not in pack or "Hybrid A* (RS)" not in pack:
            continue
        ours = pack["Ours"]
        base = pack["Hybrid A* (RS)"]
        succ_delta.append(float(ours["success"]) - float(base["success"]))
        exp_delta.append(float(base["expansions"]) - float(ours["expansions"]))
        time_delta.append(float(base["time_ms"]) - float(ours["time_ms"]))
        if np.isfinite(float(ours["path_length"])) and np.isfinite(float(base["path_length"])):
            path_delta.append(float(base["path_length"]) - float(ours["path_length"]))
        family[str(ours["scenario"])] .append((float(ours["success"]), float(base["success"]), float(ours["expansions"]), float(base["expansions"]), float(ours["time_ms"]), float(base["time_ms"])))
    succ_m, succ_lo, succ_hi, succ_p = _bootstrap_mean_ci(np.asarray(succ_delta), 5000)
    exp_m, exp_lo, exp_hi, exp_p = _bootstrap_mean_ci(np.asarray(exp_delta), 5000)
    time_m, time_lo, time_hi, time_p = _bootstrap_mean_ci(np.asarray(time_delta), 5000)
    if path_delta:
        path_m, path_lo, path_hi, path_p = _bootstrap_mean_ci(np.asarray(path_delta), 5000)
    else:
        path_m = path_lo = path_hi = path_p = float("nan")
    fam_rows = []
    for scen, vals in sorted(family.items()):
        arr = np.asarray(vals, dtype=np.float64)
        fam_rows.append({
            "scenario": scen,
            "num_cases": int(arr.shape[0]),
            "success_delta_pp": float(100.0 * np.mean(arr[:,0] - arr[:,1])),
            "exp_delta_pct": float(100.0 * (np.mean(arr[:,3]) - np.mean(arr[:,2])) / max(abs(np.mean(arr[:,3])),1e-12)),
            "time_delta_pct": float(100.0 * (np.mean(arr[:,5]) - np.mean(arr[:,4])) / max(abs(np.mean(arr[:,5])),1e-12)),
        })
    return {
        "num_pairs": len(succ_delta),
        "success_delta": {"mean": succ_m, "ci95": [succ_lo, succ_hi], "p_boot_le0": succ_p},
        "exp_delta": {"mean": exp_m, "ci95": [exp_lo, exp_hi], "p_boot_le0": exp_p},
        "time_delta": {"mean": time_m, "ci95": [time_lo, time_hi], "p_boot_le0": time_p},
        "path_delta": {"mean": path_m, "ci95": [path_lo, path_hi], "p_boot_le0": path_p},
        "family_rows": fam_rows,
    }


def main() -> None:
    args = parse_args()
    families = _families(args.families)
    cap = _fixed_cap(args)
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    t0 = time.perf_counter()

    runs = []
    for split in ["dev", "test"]:
        split_dir = args.benchmark_root / split
        for group, anchor_only in [("high_constraint_all", None), ("public_anchor_only", True)]:
            files = _filter_files(split_dir, families, anchor_only=anchor_only)
            if not files:
                continue
            runs.extend(_run(files, cap, predictor, args, split, group))

    args.out_root.mkdir(parents=True, exist_ok=True)
    with (args.out_root / "case_rows.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(runs[0].keys()))
        writer.writeheader(); writer.writerows(runs)

    grouped = defaultdict(list)
    for row in runs:
        grouped[(row["split"], row["group"])].append(row)
    summary = {f"{k[0]}::{k[1]}": _paired_metrics(v) for k, v in sorted(grouped.items())}
    manifest = {
        "version": "rs_root_p0c_axis_round2_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "fixed_cap": int(cap),
        "families": sorted(list(families)),
        "summary": summary,
    }
    (args.out_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# P0-C Round2 Fixed-Axis Report (V1)",
        "",
        f"- fixed cap (frozen from round1 dev selection): `{cap}`",
        f"- families: `{sorted(list(families))}`",
        "- no budget-cap search in this round; this is a fixed-protocol verification.",
        "",
    ]
    for key, val in summary.items():
        lines.append(f"## {key}")
        lines.append(f"- num pairs: `{val['num_pairs']}`")
        lines.append(f"- success delta mean: `{val['success_delta']['mean']:.6f}`; CI=`{val['success_delta']['ci95']}`; p<=0=`{val['success_delta']['p_boot_le0']:.6f}`")
        lines.append(f"- expansion delta mean: `{val['exp_delta']['mean']:.6f}`; CI=`{val['exp_delta']['ci95']}`; p<=0=`{val['exp_delta']['p_boot_le0']:.6f}`")
        lines.append(f"- time delta mean: `{val['time_delta']['mean']:.6f}`; CI=`{val['time_delta']['ci95']}`; p<=0=`{val['time_delta']['p_boot_le0']:.6f}`")
        lines.append(f"- path delta mean: `{val['path_delta']['mean']:.6f}`; CI=`{val['path_delta']['ci95']}`; p<=0=`{val['path_delta']['p_boot_le0']:.6f}`")
        lines.append("")
        lines.append("| scenario | n | success delta (pp) | exp delta (%) | time delta (%) |")
        lines.append("|---|---:|---:|---:|---:|")
        for row in val['family_rows']:
            lines.append(f"| {row['scenario']} | {row['num_cases']} | {row['success_delta_pp']:.3f} | {row['exp_delta_pct']:.3f} | {row['time_delta_pct']:.3f} |")
        lines.append("")
    args.report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[rs-root-p0c-r2] report={args.report_md}")
    print(f"[rs-root-p0c-r2] out_root={args.out_root}")


if __name__ == "__main__":
    main()
