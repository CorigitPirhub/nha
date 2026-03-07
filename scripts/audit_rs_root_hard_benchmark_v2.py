from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit rs_root_hard_v2 sample quality by split/family.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark/rs_root_hard_v2"))
    p.add_argument("--out-csv", type=Path, default=Path("outputs/rs_root_hard_benchmark_v2/quality_summary.csv"))
    p.add_argument("--out-json", type=Path, default=Path("outputs/rs_root_hard_benchmark_v2/quality_summary.json"))
    p.add_argument("--report-md", type=Path, default=Path("reports/rs_root_hard_benchmark_v2_quality.md"))
    return p.parse_args()


def _world_to_grid(x: float, y: float, resolution: float, width: int, height: int) -> tuple[int, int]:
    gx = int(np.clip(np.round(x / resolution - 0.5), 0, width - 1))
    gy = int(np.clip(np.round(y / resolution - 0.5), 0, height - 1))
    return gx, gy


def _scan_split(split_dir: Path, split_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in sorted(split_dir.glob("sample_*.npz")):
        with np.load(p, allow_pickle=False) as z:
            occ = z["occupancy"].astype(bool)
            esdf = z["esdf"].astype(np.float32)
            teacher = z["teacher_2d"].astype(np.float32)
            start = tuple(float(v) for v in z["start"].astype(np.float32))
            goal = tuple(float(v) for v in z["goal"].astype(np.float32))
            resolution = float(z["resolution"])
            scenario = str(z["scenario"])
            source = str(z["source_dataset"]) if "source_dataset" in z else "unknown"
            difficulty = str(z["difficulty"])
            difficulty_score = float(z["difficulty_score"]) if "difficulty_score" in z else float("nan")
            width = int(occ.shape[1])
            height = int(occ.shape[0])
            sx, sy = _world_to_grid(start[0], start[1], resolution, width, height)
            gx, gy = _world_to_grid(goal[0], goal[1], resolution, width, height)
            start_free = bool(not occ[sy, sx])
            goal_free = bool(not occ[gy, gx])
            teacher_val = float(teacher[sy, sx])
            reachable = bool(np.isfinite(teacher_val) and teacher_val < 0.95 * 1e6)
            euclid = float(np.hypot(goal[0] - start[0], goal[1] - start[1]))
            stretch = float(teacher_val / max(euclid, 1e-6)) if reachable else float("nan")
            free = esdf[~occ]
            p10_clear = float(np.quantile(free, 0.10)) if free.size > 0 else float("nan")
            rows.append(
                {
                    "split": split_name,
                    "sample_name": p.name,
                    "source": source,
                    "scenario": scenario,
                    "difficulty": difficulty,
                    "difficulty_score": difficulty_score,
                    "start_goal_free": float(start_free and goal_free),
                    "teacher_reachable": float(reachable),
                    "occ_ratio": float(np.mean(occ.astype(np.float32))),
                    "euclid_m": euclid,
                    "teacher_path_len_m": teacher_val if reachable else float("nan"),
                    "stretch": stretch,
                    "p10_clearance_m": p10_clear,
                }
            )
    return rows


def _agg(records: list[dict[str, Any]], split: str, family: str) -> dict[str, Any]:
    vals = records
    arr = lambda k: np.asarray([float(r[k]) for r in vals if np.isfinite(float(r[k]))], dtype=np.float64)
    out = {
        "split": split,
        "family": family,
        "num_samples": len(vals),
        "start_goal_free_rate": float(np.mean(arr("start_goal_free"))) if len(vals) else float("nan"),
        "teacher_reachable_rate": float(np.mean(arr("teacher_reachable"))) if len(vals) else float("nan"),
        "avg_occ_ratio": float(np.mean(arr("occ_ratio"))) if arr("occ_ratio").size else float("nan"),
        "avg_difficulty_score": float(np.mean(arr("difficulty_score"))) if arr("difficulty_score").size else float("nan"),
        "avg_euclid_m": float(np.mean(arr("euclid_m"))) if arr("euclid_m").size else float("nan"),
        "avg_teacher_path_len_m": float(np.mean(arr("teacher_path_len_m"))) if arr("teacher_path_len_m").size else float("nan"),
        "avg_stretch": float(np.mean(arr("stretch"))) if arr("stretch").size else float("nan"),
        "p90_stretch": float(np.quantile(arr("stretch"), 0.90)) if arr("stretch").size else float("nan"),
        "avg_p10_clearance_m": float(np.mean(arr("p10_clearance_m"))) if arr("p10_clearance_m").size else float("nan"),
    }
    return out


def main() -> None:
    args = parse_args()
    all_rows: list[dict[str, Any]] = []
    for split in ["dev", "test"]:
        all_rows.extend(_scan_split(Path(args.benchmark_root) / split, split))

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        groups[(row["split"], "ALL")].append(row)
        groups[(row["split"], str(row["scenario"]))].append(row)

    summary_rows = [_agg(v, split=k[0], family=k[1]) for k, v in sorted(groups.items())]
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    payload = {"version": "rs_root_hard_v2_quality_v1", "benchmark_root": str(args.benchmark_root), "rows": summary_rows}
    args.out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# RS Root Hard Benchmark V2 — Sample Quality Audit",
        "",
        "This audit reports sample-quality statistics by `split / family`, focusing on solvability, geometric difficulty, and path-related statistics.",
        "",
        "## Summary Table",
        "",
    ]
    header = "| split | family | n | free-rate | reachable-rate | occ | diff-score | euclid | path-len | stretch | p90-stretch | p10-clear |"
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines.extend([header, sep])
    for row in summary_rows:
        lines.append(
            f"| {row['split']} | {row['family']} | {row['num_samples']} | {row['start_goal_free_rate']:.3f} | {row['teacher_reachable_rate']:.3f} | {row['avg_occ_ratio']:.3f} | {row['avg_difficulty_score']:.3f} | {row['avg_euclid_m']:.3f} | {row['avg_teacher_path_len_m']:.3f} | {row['avg_stretch']:.3f} | {row['p90_stretch']:.3f} | {row['avg_p10_clearance_m']:.3f} |"
        )
    args.report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[rs-root-hard-v2-audit] csv={args.out_csv}")
    print(f"[rs-root-hard-v2-audit] json={args.out_json}")
    print(f"[rs-root-hard-v2-audit] report={args.report_md}")


if __name__ == "__main__":
    main()
