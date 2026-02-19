from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable

import numpy as np

from config import DatasetConfig, MapConfig, PlannerConfig, VehicleConfig
from env.esdf import compute_esdf
from env.map_generator import generate_scene, generate_scene_from_category, scenario_histogram, scenario_to_category
from env.reeds_shepp import RSConsistentCostConfig, compute_reeds_shepp_field
from env.teacher import compute_2d_dijkstra_field, compute_nonholonomic_teacher, fill_unreachable, world_to_grid


def _is_reachable(field: np.ndarray, start_xy: tuple[float, float], resolution: float, fill_value: float) -> bool:
    sx, sy = world_to_grid(start_xy[0], start_xy[1], resolution)
    sx = int(np.clip(sx, 0, field.shape[1] - 1))
    sy = int(np.clip(sy, 0, field.shape[0] - 1))
    v = float(field[sy, sx])
    return np.isfinite(v) and v < 0.95 * fill_value


def _save_sample(
    sample_path: Path,
    occupancy: np.ndarray,
    esdf: np.ndarray,
    teacher_2d: np.ndarray,
    teacher_3d: np.ndarray,
    rs_base_3d: np.ndarray,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    resolution: float,
    scenario: str,
    category: str,
    fill_value: float,
) -> None:
    np.savez_compressed(
        sample_path,
        occupancy=occupancy.astype(np.uint8),
        esdf=esdf.astype(np.float32),
        teacher=teacher_2d.astype(np.float32),
        teacher_2d=teacher_2d.astype(np.float32),
        teacher_3d=teacher_3d.astype(np.float32),
        rs_base_3d=rs_base_3d.astype(np.float32),
        start=np.asarray(start, dtype=np.float32),
        goal=np.asarray(goal, dtype=np.float32),
        resolution=np.float32(resolution),
        scenario=np.array(scenario),
        category=np.array(category),
        fill_value=np.float32(fill_value),
    )


def _cleanup_npz(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.npz"):
        old.unlink()


def _derive_rs_base_3d(
    occupancy: np.ndarray,
    esdf: np.ndarray,
    goal: tuple[float, float, float],
    teacher_3d: np.ndarray,
    map_cfg: MapConfig,
    ds_cfg: DatasetConfig,
    vehicle_cfg: VehicleConfig,
    planner_cfg: PlannerConfig | None,
    fill_value: float,
) -> np.ndarray:
    mode = str(ds_cfg.teacher_mode).lower()
    if mode in {"reeds_shepp_consistent", "rs_consistent", "reeds_shepp_costaware"}:
        base = teacher_3d.copy()
    elif mode in {"hybrid_rs_consistent_esdf", "hybrid_consistent", "rs_consistent_hybrid"}:
        obs = np.maximum(0.0, float(ds_cfg.hybrid_obstacle_threshold_m) - np.maximum(esdf, 0.0)).astype(np.float32)
        base = (teacher_3d - float(ds_cfg.hybrid_obstacle_alpha) * obs[None, ...]).astype(np.float32)
    else:
        if planner_cfg is None:
            raise ValueError("planner_cfg is required to derive rs_base_3d")
        cost_cfg = RSConsistentCostConfig.from_configs(vehicle_cfg=vehicle_cfg, planner_cfg=planner_cfg)
        base = compute_reeds_shepp_field(
            occupancy=occupancy,
            goal=goal,
            resolution=map_cfg.resolution,
            yaw_bins=int(teacher_3d.shape[0]),
            rho=vehicle_cfg.min_turn_radius,
            fill_value=fill_value,
            step_size=ds_cfg.teacher_rs_step_size,
            backend=ds_cfg.teacher_rs_backend,
            cost_mode="planner_consistent",
            cost_cfg=cost_cfg,
        )
    base[:, occupancy] = fill_value
    base = np.where(np.isfinite(base), base, fill_value).astype(np.float32)
    return base


def generate_dataset_split(
    out_dir: Path,
    num_samples: int,
    map_cfg: MapConfig,
    ds_cfg: DatasetConfig,
    vehicle_cfg: VehicleConfig,
    planner_cfg: PlannerConfig | None,
    seed: int,
    scenario_cycle: Iterable[str] | None = None,
) -> Dict[str, int]:
    _cleanup_npz(out_dir)

    rng = np.random.default_rng(seed)
    counts: Dict[str, int] = {"random": 0, "narrow": 0, "parking": 0, "deadend": 0}

    created = 0
    tries = 0
    max_tries = max(3000, num_samples * 40)
    fill_value = ds_cfg.max_teacher_value

    cycle = list(scenario_cycle) if scenario_cycle is not None else None

    while created < num_samples and tries < max_tries:
        tries += 1

        if cycle:
            scenario = cycle[created % len(cycle)]
            scene = generate_scene(map_cfg, ds_cfg.min_start_goal_dist_m, rng, scenario=scenario)
        else:
            scene = generate_scene(map_cfg, ds_cfg.min_start_goal_dist_m, rng)

        esdf = compute_esdf(scene.occupancy, map_cfg.resolution)
        probe_2d = compute_2d_dijkstra_field(scene.occupancy, (scene.goal[0], scene.goal[1]), map_cfg.resolution)
        probe_2d = fill_unreachable(probe_2d, scene.occupancy, fill_value=fill_value)
        if not _is_reachable(probe_2d, (scene.start[0], scene.start[1]), map_cfg.resolution, fill_value):
            continue

        teacher_2d, teacher_3d = compute_nonholonomic_teacher(
            occupancy=scene.occupancy,
            goal_pose=scene.goal,
            resolution=map_cfg.resolution,
            yaw_bins=ds_cfg.teacher_yaw_bins,
            min_turn_radius=vehicle_cfg.min_turn_radius,
            fill_value=fill_value,
            teacher_mode=ds_cfg.teacher_mode,
            esdf=esdf,
            hybrid_obstacle_alpha=ds_cfg.hybrid_obstacle_alpha,
            hybrid_obstacle_threshold_m=ds_cfg.hybrid_obstacle_threshold_m,
            rs_backend=ds_cfg.teacher_rs_backend,
            rs_step_size=ds_cfg.teacher_rs_step_size,
            planner_cfg=planner_cfg,
            vehicle_cfg=vehicle_cfg,
        )
        rs_base_3d = _derive_rs_base_3d(
            occupancy=scene.occupancy,
            esdf=esdf,
            goal=scene.goal,
            teacher_3d=teacher_3d,
            map_cfg=map_cfg,
            ds_cfg=ds_cfg,
            vehicle_cfg=vehicle_cfg,
            planner_cfg=planner_cfg,
            fill_value=fill_value,
        )

        category = scenario_to_category(scene.scenario)
        sample_path = out_dir / f"sample_{created:05d}.npz"
        _save_sample(
            sample_path,
            scene.occupancy,
            esdf,
            teacher_2d,
            teacher_3d,
            rs_base_3d,
            scene.start,
            scene.goal,
            map_cfg.resolution,
            scene.scenario,
            category,
            fill_value,
        )

        counts[scene.scenario] += 1
        created += 1

    if created < num_samples:
        raise RuntimeError(f"Could not generate requested samples: {created}/{num_samples}")

    meta = {
        "num_samples": created,
        "scenario_histogram": counts,
        "resolution": map_cfg.resolution,
        "map_size": [map_cfg.height, map_cfg.width],
        "fill_value": fill_value,
        "teacher_yaw_bins": ds_cfg.teacher_yaw_bins,
        "teacher_mode": ds_cfg.teacher_mode,
        "teacher_rs_backend": ds_cfg.teacher_rs_backend,
        "teacher_rs_step_size": ds_cfg.teacher_rs_step_size,
        "hybrid_obstacle_alpha": ds_cfg.hybrid_obstacle_alpha,
        "hybrid_obstacle_threshold_m": ds_cfg.hybrid_obstacle_threshold_m,
    }
    with (out_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return counts


def generate_benchmark_split(
    out_dir: Path,
    counts_by_category: tuple[int, int, int],
    map_cfg: MapConfig,
    ds_cfg: DatasetConfig,
    vehicle_cfg: VehicleConfig,
    planner_cfg: PlannerConfig | None,
    seed: int,
) -> Dict[str, int]:
    _cleanup_npz(out_dir)
    rng = np.random.default_rng(seed)
    fill_value = ds_cfg.max_teacher_value

    scenarios: Dict[str, int] = {"random": 0, "narrow": 0, "parking": 0, "deadend": 0}
    categories = ["A", "B", "C"]

    idx = 0
    for cat, n_cat in zip(categories, counts_by_category):
        created = 0
        tries = 0
        max_tries = max(1200, n_cat * 30)
        while created < n_cat and tries < max_tries:
            tries += 1
            scene = generate_scene_from_category(map_cfg, ds_cfg.min_start_goal_dist_m, rng, category=cat)

            esdf = compute_esdf(scene.occupancy, map_cfg.resolution)
            probe_2d = compute_2d_dijkstra_field(scene.occupancy, (scene.goal[0], scene.goal[1]), map_cfg.resolution)
            probe_2d = fill_unreachable(probe_2d, scene.occupancy, fill_value=fill_value)
            if not _is_reachable(probe_2d, (scene.start[0], scene.start[1]), map_cfg.resolution, fill_value):
                continue

            teacher_2d, teacher_3d = compute_nonholonomic_teacher(
                occupancy=scene.occupancy,
                goal_pose=scene.goal,
                resolution=map_cfg.resolution,
                yaw_bins=ds_cfg.teacher_yaw_bins,
                min_turn_radius=vehicle_cfg.min_turn_radius,
                fill_value=fill_value,
                teacher_mode=ds_cfg.teacher_mode,
                esdf=esdf,
                hybrid_obstacle_alpha=ds_cfg.hybrid_obstacle_alpha,
                hybrid_obstacle_threshold_m=ds_cfg.hybrid_obstacle_threshold_m,
                rs_backend=ds_cfg.teacher_rs_backend,
                rs_step_size=ds_cfg.teacher_rs_step_size,
                planner_cfg=planner_cfg,
                vehicle_cfg=vehicle_cfg,
            )
            rs_base_3d = _derive_rs_base_3d(
                occupancy=scene.occupancy,
                esdf=esdf,
                goal=scene.goal,
                teacher_3d=teacher_3d,
                map_cfg=map_cfg,
                ds_cfg=ds_cfg,
                vehicle_cfg=vehicle_cfg,
                planner_cfg=planner_cfg,
                fill_value=fill_value,
            )
            sample_path = out_dir / f"sample_{idx:05d}.npz"
            _save_sample(
                sample_path,
                scene.occupancy,
                esdf,
                teacher_2d,
                teacher_3d,
                rs_base_3d,
                scene.start,
                scene.goal,
                map_cfg.resolution,
                scene.scenario,
                cat,
                fill_value,
            )
            scenarios[scene.scenario] += 1
            created += 1
            idx += 1

        if created < n_cat:
            raise RuntimeError(f"Could not build category {cat}: {created}/{n_cat}")

    meta = {
        "num_samples": int(sum(counts_by_category)),
        "counts_by_category": {
            "A": int(counts_by_category[0]),
            "B": int(counts_by_category[1]),
            "C": int(counts_by_category[2]),
        },
        "scenario_histogram": scenarios,
        "resolution": map_cfg.resolution,
        "map_size": [map_cfg.height, map_cfg.width],
        "fill_value": fill_value,
        "teacher_yaw_bins": ds_cfg.teacher_yaw_bins,
        "teacher_mode": ds_cfg.teacher_mode,
        "teacher_rs_backend": ds_cfg.teacher_rs_backend,
        "teacher_rs_step_size": ds_cfg.teacher_rs_step_size,
        "hybrid_obstacle_alpha": ds_cfg.hybrid_obstacle_alpha,
        "hybrid_obstacle_threshold_m": ds_cfg.hybrid_obstacle_threshold_m,
    }
    with (out_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return scenarios


def describe_split(name: str, counts: Dict[str, int]) -> str:
    return f"{name}: {scenario_histogram(counts)}"
