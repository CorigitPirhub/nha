from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
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
from env.scenario_generator import _generate_static_map, _sample_reachable_pair
from scripts.convert_parasol_benchmark import _gen_alpha_puzzle, _gen_bugtrap, _gen_flange
from utils.common import ensure_dirs, set_seed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build expanded RS-root hard benchmark v1.")
    p.add_argument("--output-root", type=Path, default=Path("data/benchmark/rs_root_hard_v1"))
    p.add_argument("--public-anchor-root", type=Path, default=Path("data/benchmark/parasol_narrow/test"))
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--resolution", type=float, default=0.5)
    p.add_argument("--map-size", type=int, default=96)
    p.add_argument("--synthetic-per-family", type=int, default=15)
    p.add_argument("--family-min-floor", type=int, default=10)
    p.add_argument("--families", type=str, default="bug_trap,alpha_puzzle,flange,narrow_passage,maze,deadend_labyrinth")
    p.add_argument("--difficulty-label", type=str, default="medium")
    p.add_argument("--meta-path", type=Path, default=Path("data/benchmark/rs_root_hard_v1/meta.json"))
    p.add_argument("--report-md", type=Path, default=Path("reports/rs_root_hard_benchmark_v1.md"))
    p.add_argument("--manifest-json", type=Path, default=Path("outputs/rs_root_hard_benchmark_v1/manifest.json"))
    return p.parse_args()


def _clear_dir(root: Path) -> None:
    ensure_dirs([root, root / "train", root / "test"])
    for split in [root / "train", root / "test"]:
        for p in split.glob("sample_*.npz"):
            p.unlink()


def _write_sample(
    *,
    out_path: Path,
    occ: np.ndarray,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    resolution: float,
    scenario: str,
    map_id: str,
    source_dataset: str,
    benchmark_group: str,
    difficulty: str,
) -> None:
    fill = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    goal_xy = (float(goal[0]), float(goal[1]))
    d2 = compute_2d_dijkstra_field(occ, goal_xy, float(resolution))
    teacher = np.where(np.isfinite(d2), d2, fill).astype(np.float32)
    teacher[occ] = fill
    esdf = compute_esdf(occ, resolution=resolution).astype(np.float32)
    np.savez_compressed(
        out_path,
        occupancy=occ.astype(bool),
        esdf=esdf,
        teacher=teacher,
        teacher_2d=teacher,
        teacher_3d=teacher[None, ...],
        start=np.asarray(start, dtype=np.float32),
        goal=np.asarray(goal, dtype=np.float32),
        resolution=np.float32(resolution),
        fill_value=np.float32(fill),
        scenario=np.asarray(str(scenario)),
        difficulty=np.asarray(str(difficulty)),
        task_type=np.asarray(str(scenario)),
        source_dataset=np.asarray(str(source_dataset)),
        benchmark_group=np.asarray(str(benchmark_group)),
        map_id=np.asarray(str(map_id)),
        category=np.asarray("C"),
        vehicle_wheel_base=np.float32(DEFAULT_CONFIG.vehicle.wheel_base),
        vehicle_length=np.float32(DEFAULT_CONFIG.vehicle.length),
        vehicle_width=np.float32(DEFAULT_CONFIG.vehicle.width),
        vehicle_max_steer_deg=np.float32(DEFAULT_CONFIG.vehicle.max_steer_deg),
        vehicle_min_turn_radius=np.float32(DEFAULT_CONFIG.vehicle.min_turn_radius),
        planner_step_size=np.float32(DEFAULT_CONFIG.planner.step_size),
        planner_reverse_penalty=np.float32(DEFAULT_CONFIG.planner.reverse_penalty),
        planner_steer_penalty=np.float32(DEFAULT_CONFIG.planner.steer_penalty),
        planner_steer_change_penalty=np.float32(DEFAULT_CONFIG.planner.steer_change_penalty),
    )


def _copy_public_anchor(src_root: Path, dst_root: Path) -> list[dict[str, Any]]:
    rows = []
    out_dir = dst_root / "test"
    next_idx = 0
    for src in sorted(src_root.glob("sample_*.npz")):
        dst = out_dir / f"sample_{next_idx:06d}.npz"
        next_idx += 1
        with np.load(src, allow_pickle=False) as z:
            payload = {k: z[k] for k in z.files}
        payload["source_dataset"] = np.asarray("parasol_public_anchor")
        payload["benchmark_group"] = np.asarray("public_anchor")
        np.savez_compressed(dst, **payload)
        rows.append({
            "split": "test",
            "path": str(dst),
            "source": "public_anchor",
            "scenario": str(payload.get("scenario", "unknown")),
            "map_id": str(payload.get("map_id", dst.stem)),
            "difficulty": str(payload.get("difficulty", "unknown")),
        })
    return rows


def _corner_context(occ: np.ndarray) -> dict[str, np.ndarray]:
    h, w = occ.shape
    start_zone = np.zeros_like(occ, dtype=bool)
    goal_zone = np.zeros_like(occ, dtype=bool)
    start_zone[2 : 2 + h // 4, 2 : 2 + w // 4] = True
    goal_zone[h - 2 - h // 4 : h - 2, w - 2 - w // 4 : w - 2] = True
    return {"start_zone": start_zone, "goal_zone": goal_zone}


def _generate_occ_and_context(family: str, map_cfg: MapConfig, rng: np.random.Generator) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    fam = str(family)
    if fam == "bug_trap":
        occ = _gen_bugtrap(map_cfg.width, rng, tightness=float(rng.uniform(1.05, 1.30)))
        return occ.astype(bool), _corner_context(occ)
    if fam == "alpha_puzzle":
        occ = _gen_alpha_puzzle(map_cfg.width, rng, tightness=float(rng.uniform(1.05, 1.25)))
        return occ.astype(bool), _corner_context(occ)
    if fam == "flange":
        occ = _gen_flange(map_cfg.width, rng, tightness=float(rng.uniform(0.90, 1.20)))
        return occ.astype(bool), _corner_context(occ)
    if fam == "narrow_passage":
        return _generate_static_map(map_cfg, difficulty="hard", template="narrow_passage", distribution_mode="random", vehicle_width=DEFAULT_CONFIG.vehicle.width, rng=rng)
    if fam == "maze":
        occ, ctx = _generate_static_map(map_cfg, difficulty="hard", template="maze_single", distribution_mode="random", vehicle_width=DEFAULT_CONFIG.vehicle.width, rng=rng)
        return occ.astype(bool), ctx
    if fam == "deadend_labyrinth":
        return _generate_static_map(map_cfg, difficulty="hard", template="deadend_labyrinth", distribution_mode="random", vehicle_width=DEFAULT_CONFIG.vehicle.width, rng=rng)
    raise ValueError(fam)


def _sample_pair(occ: np.ndarray, ctx: dict[str, np.ndarray], resolution: float, family: str, rng: np.random.Generator) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    fill = float(DEFAULT_CONFIG.dataset.max_teacher_value)
    if family == "deadend_labyrinth":
        min_dists = [8.0, 6.0]
        start_mask = ctx.get("deadend_zone", ctx.get("start_zone"))
        goal_mask = ctx.get("goal_zone")
    elif family == "maze":
        min_dists = [16.0, 12.0, 8.0]
        start_mask = ctx.get("start_zone")
        goal_mask = ctx.get("goal_zone")
    elif family == "narrow_passage":
        min_dists = [10.0, 8.0]
        start_mask = ctx.get("start_zone")
        goal_mask = ctx.get("goal_zone")
    else:
        min_dists = [10.0, 8.0]
        start_mask = ctx.get("start_zone")
        goal_mask = ctx.get("goal_zone")
    for min_dist in min_dists:
        for sm, gm in [(start_mask, goal_mask), (None, None)]:
            pair = _sample_reachable_pair(
                occ=occ,
                resolution=float(resolution),
                fill_value=float(fill),
                rng=rng,
                min_dist=float(min_dist),
                max_dist=None,
                start_mask=sm,
                goal_mask=gm,
                risk_map=None,
                min_line_risk=None,
            )
            if pair is not None:
                return pair
    return None


def _build_synthetic_rows(output_root: Path, families: list[str], per_family: int, resolution: float, map_size: int, difficulty_label: str, seed: int) -> list[dict[str, Any]]:
    out_rows: list[dict[str, Any]] = []
    out_dir = output_root / "test"
    existing = sorted(out_dir.glob("sample_*.npz"))
    next_idx = len(existing)
    map_cfg = MapConfig(width=int(map_size), height=int(map_size), resolution=float(resolution))
    for fam_idx, family in enumerate(families):
        made = 0
        trial = 0
        print(f"[rs-root-hard] family={family} target={per_family}")
        while made < int(per_family):
            if trial > int(per_family) * 40:
                if made >= int(args.family_min_floor):
                    print(f"[rs-root-hard] family={family} stop-early at {made}/{per_family} after {trial} trials")
                    break
                raise RuntimeError(f"Failed to generate enough samples for family={family}: {made}/{per_family}")
            trial += 1
            rng = np.random.default_rng(int(seed) + fam_idx * 10000 + trial)
            occ, ctx = _generate_occ_and_context(family, map_cfg, rng)
            pair = _sample_pair(occ, ctx, resolution=float(resolution), family=str(family), rng=rng)
            if pair is None:
                continue
            start, goal = pair
            dst = out_dir / f"sample_{next_idx:06d}.npz"
            next_idx += 1
            map_id = f"{family}_s{int(seed)}_q{made:03d}_t{trial:04d}"
            _write_sample(
                out_path=dst,
                occ=occ,
                start=start,
                goal=goal,
                resolution=float(resolution),
                scenario=str(family),
                map_id=map_id,
                source_dataset="rs_root_hard_v1_synth",
                benchmark_group="synthetic_hard",
                difficulty=str(difficulty_label),
            )
            out_rows.append({
                "split": "test",
                "path": str(dst),
                "source": "synthetic_hard",
                "scenario": str(family),
                "map_id": map_id,
                "difficulty": str(difficulty_label),
            })
            made += 1
            if made % 5 == 0 or made == int(per_family):
                print(f"[rs-root-hard] family={family} progress={made}/{per_family} trials={trial}")
    return out_rows


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


def main() -> None:
    args = parse_args()
    set_seed(int(args.seed))
    _clear_dir(args.output_root)
    families = [x.strip() for x in str(args.families).split(",") if x.strip()]
    rows = []
    rows.extend(_copy_public_anchor(args.public_anchor_root, args.output_root))
    rows.extend(
        _build_synthetic_rows(
            output_root=args.output_root,
            families=families,
            per_family=int(args.synthetic_per_family),
            resolution=float(args.resolution),
            map_size=int(args.map_size),
            difficulty_label=str(args.difficulty_label),
            seed=int(args.seed),
        )
    )
    summary = _scan(rows)
    meta = {
        "name": "rs_root_hard_v1",
        "seed": int(args.seed),
        "resolution": float(args.resolution),
        "map_size": int(args.map_size),
        "protocol_role": "expanded_hard_narrow_benchmark_for_rs_root_claim",
        "public_anchor_root": str(args.public_anchor_root),
        "synthetic_per_family": int(args.synthetic_per_family),
        "synthetic_families": list(families),
        "splits": {
            "train": {"num_samples": 0, "scenario_histogram": {}, "difficulty_histogram": {}, "source_histogram": {}, "num_maps": 0},
            "test": summary,
        },
    }
    args.meta_path.parent.mkdir(parents=True, exist_ok=True)
    args.meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest = {
        "version": "rs_root_hard_benchmark_v1",
        "output_root": str(args.output_root),
        "meta_path": str(args.meta_path),
        "seed": int(args.seed),
        "public_anchor_root": str(args.public_anchor_root),
        "synthetic_per_family": int(args.synthetic_per_family),
        "synthetic_families": list(families),
        "test_summary": summary,
    }
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# RS Root Hard Benchmark V1",
        "",
        "Status: `built`",
        "",
        "This benchmark expands the previous tiny `parasol_narrow/test` hard bundle into a larger **test-only** benchmark for the RS-root claim.",
        "",
        "## Composition",
        f"- public anchor root: `{args.public_anchor_root}`",
        f"- synthetic families: `{families}`",
        f"- synthetic samples per family: `{int(args.synthetic_per_family)}`",
        f"- total test samples: `{summary['num_samples']}`",
        f"- total maps: `{summary['num_maps']}`",
        f"- source histogram: `{summary['source_histogram']}`",
        f"- scenario histogram: `{summary['scenario_histogram']}`",
        f"- difficulty histogram: `{summary['difficulty_histogram']}`",
        "",
        "## Intended use",
        "- Use this benchmark as the expanded high-difficulty benchmark for the RS-root claim.",
        "- Keep it test-only; do not merge it into training or calibration splits of later method experiments.",
        "- Report narrow/maze/deadend/other or the finer family histogram explicitly when writing root-claim evidence.",
        "",
        "## Artifact chain",
        f"- output root: `{args.output_root}`",
        f"- meta: `{args.meta_path}`",
        f"- manifest: `{args.manifest_json}`",
    ]
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[rs-root-hard] meta={args.meta_path}")
    print(f"[rs-root-hard] report={args.report_md}")
    print(f"[rs-root-hard] manifest={args.manifest_json}")


if __name__ == "__main__":
    main()
