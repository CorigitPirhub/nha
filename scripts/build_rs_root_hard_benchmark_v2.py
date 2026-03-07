from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG, MapConfig
from env.esdf import compute_esdf
from env.teacher import compute_2d_dijkstra_field
from scripts.build_rs_root_hard_benchmark_v1 import (
    _clear_dir,
    _copy_public_anchor,
    _generate_occ_and_context,
    _sample_pair,
    _write_sample,
)
from utils.common import ensure_dirs, set_seed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build standardized RS-root hard benchmark v2 (dev/test split + relabeled difficulty).")
    p.add_argument("--output-root", type=Path, default=Path("data/benchmark/rs_root_hard_v2"))
    p.add_argument("--public-anchor-root", type=Path, default=Path("data/benchmark/parasol_narrow/test"))
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--resolution", type=float, default=0.5)
    p.add_argument("--map-size", type=int, default=96)
    p.add_argument("--synthetic-dev-per-family", type=int, default=6)
    p.add_argument("--synthetic-test-per-family", type=int, default=10)
    p.add_argument("--families", type=str, default="bug_trap,alpha_puzzle,flange,narrow_passage,maze,deadend_labyrinth")
    p.add_argument("--meta-path", type=Path, default=Path("data/benchmark/rs_root_hard_v2/meta.json"))
    p.add_argument("--dev-index", type=Path, default=Path("data/benchmark/rs_root_hard_v2/dev_index.csv"))
    p.add_argument("--test-index", type=Path, default=Path("data/benchmark/rs_root_hard_v2/test_index.csv"))
    p.add_argument("--report-md", type=Path, default=Path("reports/rs_root_hard_benchmark_v2.md"))
    p.add_argument("--manifest-json", type=Path, default=Path("outputs/rs_root_hard_benchmark_v2/manifest.json"))
    p.add_argument("--benchmark-card", type=Path, default=Path("docs/rs_root_hard_benchmark_card_v1.md"))
    return p.parse_args()


def _clear_dev_test(root: Path) -> None:
    ensure_dirs([root, root / "dev", root / "test"])
    for split in [root / "dev", root / "test"]:
        for p in split.glob("sample_*.npz"):
            p.unlink()


def _shortest_path_length(occ: np.ndarray, start_xy: tuple[float, float], goal_xy: tuple[float, float], resolution: float) -> float:
    d2 = compute_2d_dijkstra_field(occ, goal_xy, float(resolution))
    sx = int(np.clip(np.floor(start_xy[0] / resolution), 0, occ.shape[1] - 1))
    sy = int(np.clip(np.floor(start_xy[1] / resolution), 0, occ.shape[0] - 1))
    val = float(d2[sy, sx])
    return val


def _difficulty_relabel(*, occ: np.ndarray, start: tuple[float, float, float], goal: tuple[float, float, float], scenario: str, resolution: float) -> tuple[str, dict[str, float]]:
    occ_ratio = float(np.mean(occ.astype(np.float32)))
    euclid = float(np.hypot(float(goal[0]) - float(start[0]), float(goal[1]) - float(start[1])))
    sp = _shortest_path_length(occ, (float(start[0]), float(start[1])), (float(goal[0]), float(goal[1])), float(resolution))
    stretch = float(sp / max(euclid, 1e-6)) if np.isfinite(sp) else 1e6
    esdf = compute_esdf(occ, resolution=float(resolution)).astype(np.float32)
    free = esdf[~occ]
    p10_clear = float(np.quantile(free, 0.10)) if free.size > 0 else 0.0
    fam = str(scenario)
    score = 0
    if fam in {"maze", "deadend_labyrinth"}:
        score += 2
    elif fam in {"narrow_passage", "flange"}:
        score += 1
    if stretch >= 2.5:
        score += 2
    elif stretch >= 1.8:
        score += 1
    if p10_clear <= 0.65:
        score += 1
    if occ_ratio >= 0.33:
        score += 1
    label = "very_hard" if score >= 3 else "hard"
    return label, {
        "occ_ratio": occ_ratio,
        "euclid_m": euclid,
        "shortest_path_len_m": sp,
        "stretch": stretch,
        "p10_clearance_m": p10_clear,
        "difficulty_score": float(score),
    }


def _rewrite_with_label(src: Path, dst: Path, *, split: str, source: str, benchmark_group: str) -> dict[str, Any]:
    with np.load(src, allow_pickle=False) as z:
        payload = {k: z[k] for k in z.files}
    occ = payload["occupancy"].astype(bool)
    start = tuple(float(v) for v in payload["start"].astype(np.float32))
    goal = tuple(float(v) for v in payload["goal"].astype(np.float32))
    resolution = float(payload["resolution"])
    scenario = str(payload.get("scenario", "unknown"))
    map_id = str(payload.get("map_id", dst.stem))
    label, info = _difficulty_relabel(occ=occ, start=start, goal=goal, scenario=scenario, resolution=resolution)
    payload["difficulty"] = np.asarray(label)
    payload["difficulty_source"] = np.asarray("rs_root_structural_rule_v1")
    payload["difficulty_score"] = np.asarray(info["difficulty_score"], dtype=np.float32)
    payload["difficulty_occ_ratio"] = np.asarray(info["occ_ratio"], dtype=np.float32)
    payload["difficulty_stretch"] = np.asarray(info["stretch"], dtype=np.float32)
    payload["difficulty_p10_clearance_m"] = np.asarray(info["p10_clearance_m"], dtype=np.float32)
    payload["source_dataset"] = np.asarray(source)
    payload["benchmark_group"] = np.asarray(benchmark_group)
    np.savez_compressed(dst, **payload)
    return {
        "split": split,
        "sample_name": dst.name,
        "path": str(dst),
        "source": source,
        "scenario": scenario,
        "map_id": map_id,
        "difficulty": label,
        "difficulty_score": info["difficulty_score"],
        "occ_ratio": info["occ_ratio"],
        "stretch": info["stretch"],
        "p10_clearance_m": info["p10_clearance_m"],
    }


def _write_index(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["split", "sample_name", "path", "source", "scenario", "map_id", "difficulty", "difficulty_score", "occ_ratio", "stretch", "p10_clearance_m"])
        return
    fieldnames = ["split", "sample_name", "path", "source", "scenario", "map_id", "difficulty", "difficulty_score", "occ_ratio", "stretch", "p10_clearance_m"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def _scan(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scen = Counter(str(r["scenario"]) for r in rows)
    diff = Counter(str(r["difficulty"]) for r in rows)
    src = Counter(str(r["source"]) for r in rows)
    maps = Counter(str(r["map_id"]) for r in rows)
    return {
        "num_samples": len(rows),
        "scenario_histogram": dict(sorted(scen.items())),
        "difficulty_histogram": dict(sorted(diff.items())),
        "source_histogram": dict(sorted(src.items())),
        "num_maps": len(maps),
    }


def _split_public_anchor(public_root: Path, out_root: Path, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files = sorted(public_root.glob("sample_*.npz"))
    by_scenario: dict[str, list[Path]] = defaultdict(list)
    for p in files:
        with np.load(p, allow_pickle=False) as z:
            by_scenario[str(z.get("scenario", "unknown"))].append(p)
    dev_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    dev_dir = out_root / "dev"
    test_dir = out_root / "test"
    dev_idx = 0
    test_idx = 0
    rng = np.random.default_rng(int(seed) + 901)
    for scenario, group in sorted(by_scenario.items()):
        group = list(group)
        rng.shuffle(group)
        if len(group) <= 1:
            dev_count = 0
        else:
            dev_count = max(1, int(round(0.33 * len(group))))
            dev_count = min(dev_count, len(group) - 1)
        dev_group = group[:dev_count]
        test_group = group[dev_count:]
        for src in dev_group:
            dst = dev_dir / f"sample_{dev_idx:06d}.npz"
            dev_idx += 1
            dev_rows.append(_rewrite_with_label(src, dst, split="dev", source="parasol_public_anchor", benchmark_group="public_anchor_dev"))
        for src in test_group:
            dst = test_dir / f"sample_{test_idx:06d}.npz"
            test_idx += 1
            test_rows.append(_rewrite_with_label(src, dst, split="test", source="parasol_public_anchor", benchmark_group="public_anchor_test"))
    return dev_rows, test_rows


def _next_index(split_dir: Path) -> int:
    return len(list(split_dir.glob("sample_*.npz")))


def _build_synthetic_split_rows(out_root: Path, *, split: str, families: list[str], per_family: int, seed: int, resolution: float, map_size: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    split_dir = out_root / split
    next_idx = _next_index(split_dir)
    map_cfg = MapConfig(width=int(map_size), height=int(map_size), resolution=float(resolution))
    for fam_idx, family in enumerate(families):
        made = 0
        trial = 0
        while made < int(per_family):
            if trial > int(per_family) * 60:
                raise RuntimeError(f"Failed to generate enough samples for split={split}, family={family}: {made}/{per_family}")
            trial += 1
            rng = np.random.default_rng(int(seed) + (0 if split == 'dev' else 100000) + fam_idx * 10000 + trial)
            occ, ctx = _generate_occ_and_context(family, map_cfg, rng)
            pair = _sample_pair(occ, ctx, resolution=float(resolution), family=str(family), rng=rng)
            if pair is None:
                continue
            start, goal = pair
            dst = split_dir / f"sample_{next_idx:06d}.npz"
            next_idx += 1
            map_id = f"{family}_{split}_s{int(seed)}_q{made:03d}_t{trial:04d}"
            _write_sample(
                out_path=dst,
                occ=occ,
                start=start,
                goal=goal,
                resolution=float(resolution),
                scenario=str(family),
                map_id=map_id,
                source_dataset="rs_root_hard_v2_synth",
                benchmark_group=f"synthetic_{split}",
                difficulty="hard",
            )
            rows.append(_rewrite_with_label(dst, dst, split=split, source="rs_root_hard_v2_synth", benchmark_group=f"synthetic_{split}"))
            made += 1
    return rows


def main() -> None:
    args = parse_args()
    set_seed(int(args.seed))
    _clear_dev_test(args.output_root)
    families = [x.strip() for x in str(args.families).split(",") if x.strip()]
    dev_rows, test_rows = _split_public_anchor(args.public_anchor_root, args.output_root, int(args.seed))
    dev_rows.extend(_build_synthetic_split_rows(args.output_root, split="dev", families=families, per_family=int(args.synthetic_dev_per_family), seed=int(args.seed), resolution=float(args.resolution), map_size=int(args.map_size)))
    test_rows.extend(_build_synthetic_split_rows(args.output_root, split="test", families=families, per_family=int(args.synthetic_test_per_family), seed=int(args.seed), resolution=float(args.resolution), map_size=int(args.map_size)))
    _write_index(args.dev_index, dev_rows)
    _write_index(args.test_index, test_rows)

    meta = {
        "name": "rs_root_hard_v2",
        "status": "standardized_internal_benchmark",
        "seed": int(args.seed),
        "resolution": float(args.resolution),
        "map_size": int(args.map_size),
        "protocol_role": "standardized_internal_hard_benchmark_for_rs_root_claim",
        "public_anchor_root": str(args.public_anchor_root),
        "synthetic_dev_per_family": int(args.synthetic_dev_per_family),
        "synthetic_test_per_family": int(args.synthetic_test_per_family),
        "synthetic_families": list(families),
        "difficulty_source": "rs_root_structural_rule_v1",
        "splits": {
            "dev": _scan(dev_rows),
            "test": _scan(test_rows),
        },
    }
    args.meta_path.parent.mkdir(parents=True, exist_ok=True)
    args.meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest = {
        "version": "rs_root_hard_benchmark_v2",
        "output_root": str(args.output_root),
        "meta_path": str(args.meta_path),
        "dev_index": str(args.dev_index),
        "test_index": str(args.test_index),
        "seed": int(args.seed),
        "public_anchor_root": str(args.public_anchor_root),
        "synthetic_dev_per_family": int(args.synthetic_dev_per_family),
        "synthetic_test_per_family": int(args.synthetic_test_per_family),
        "synthetic_families": list(families),
        "split_summary": meta["splits"],
    }
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# RS Root Hard Benchmark V2",
        "",
        "Status: `built`",
        "",
        "This benchmark upgrades `rs_root_hard_v1` toward a more standardized internal benchmark with `dev/test` separation, relabeled difficulty, split indices, and a benchmark card.",
        "",
        "## Dev Split",
        f"- samples: `{meta['splits']['dev']['num_samples']}`",
        f"- source histogram: `{meta['splits']['dev']['source_histogram']}`",
        f"- scenario histogram: `{meta['splits']['dev']['scenario_histogram']}`",
        f"- difficulty histogram: `{meta['splits']['dev']['difficulty_histogram']}`",
        "",
        "## Test Split",
        f"- samples: `{meta['splits']['test']['num_samples']}`",
        f"- source histogram: `{meta['splits']['test']['source_histogram']}`",
        f"- scenario histogram: `{meta['splits']['test']['scenario_histogram']}`",
        f"- difficulty histogram: `{meta['splits']['test']['difficulty_histogram']}`",
        "",
        "## Standardization Notes",
        "- public anchors are stratified into dev/test where possible; singleton public scenarios remain in test only.",
        "- synthetic samples are generated separately for dev and test, with disjoint seeds and map ids.",
        "- difficulty is relabeled by a structural rule using occupancy ratio, shortest-path stretch, clearance, and family prior.",
        "- this benchmark is still internal/versioned, not an official community benchmark.",
    ]
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.write_text("\n".join(lines), encoding="utf-8")

    card_lines = [
        "# RS Root Hard Benchmark Card (V1)",
        "",
        "## Status",
        "- type: internal standardized benchmark",
        "- official/community benchmark: no",
        "- intended role: RS-root hard-scene audit and development benchmark",
        "",
        "## Motivation",
        "- extend the tiny public `parasol_narrow` hard bundle into a larger, versioned hard benchmark",
        "- support dev/test separation for root-claim development",
        "- keep public anchors while adding synthetic hard families for broader geometry coverage",
        "",
        "## Composition",
        f"- public anchor root: `{args.public_anchor_root}`",
        f"- dev synthetic per family: `{int(args.synthetic_dev_per_family)}`",
        f"- test synthetic per family: `{int(args.synthetic_test_per_family)}`",
        f"- families: `{families}`",
        f"- dev summary: `{meta['splits']['dev']}`",
        f"- test summary: `{meta['splits']['test']}`",
        "",
        "## Difficulty Relabeling",
        "- source: `rs_root_structural_rule_v1`",
        "- inputs: occupancy ratio, shortest-path stretch, clearance quantile, scenario-family prior",
        "- labels: `hard`, `very_hard`",
        "- note: this relabeling is internal and not inherited from any official source label",
        "",
        "## Allowed Uses",
        "- root-claim stress test and standardized internal benchmarking",
        "- dev split for method shaping within the RS-root line",
        "- test split for final internal reporting under the same benchmark version",
        "",
        "## Forbidden Uses",
        "- do not describe this benchmark as an official or community-standard benchmark",
        "- do not mix this benchmark with training/calibration splits of unrelated later tasks",
        "- do not hide the distinction between public-anchor samples and synthetic-extension samples",
        "",
        "## Artifact Chain",
        f"- root: `{args.output_root}`",
        f"- meta: `{args.meta_path}`",
        f"- dev index: `{args.dev_index}`",
        f"- test index: `{args.test_index}`",
        f"- manifest: `{args.manifest_json}`",
        f"- audit report: `{args.report_md}`",
    ]
    args.benchmark_card.parent.mkdir(parents=True, exist_ok=True)
    args.benchmark_card.write_text("\n".join(card_lines), encoding="utf-8")

    print(f"[rs-root-hard-v2] meta={args.meta_path}")
    print(f"[rs-root-hard-v2] report={args.report_md}")
    print(f"[rs-root-hard-v2] manifest={args.manifest_json}")
    print(f"[rs-root-hard-v2] benchmark_card={args.benchmark_card}")


if __name__ == "__main__":
    main()
