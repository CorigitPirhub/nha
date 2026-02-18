from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import numpy as np

from config import DatasetConfig, MapConfig
from env.esdf import compute_esdf
from env.map_generator import generate_scene, scenario_histogram
from env.teacher import compute_2d_dijkstra_field, fill_unreachable, world_to_grid


def _is_reachable(field: np.ndarray, start_xy: tuple[float, float], resolution: float) -> bool:
    sx, sy = world_to_grid(start_xy[0], start_xy[1], resolution)
    sx = int(np.clip(sx, 0, field.shape[1] - 1))
    sy = int(np.clip(sy, 0, field.shape[0] - 1))
    return np.isfinite(field[sy, sx])


def generate_dataset_split(
    out_dir: Path,
    num_samples: int,
    map_cfg: MapConfig,
    ds_cfg: DatasetConfig,
    seed: int,
) -> Dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.npz"):
        old.unlink()

    rng = np.random.default_rng(seed)
    counts: Dict[str, int] = {"random": 0, "narrow": 0, "parking": 0}

    created = 0
    tries = 0
    max_tries = max(2000, num_samples * 30)
    fill_value = ds_cfg.max_teacher_value

    while created < num_samples and tries < max_tries:
        tries += 1
        scene = generate_scene(map_cfg, ds_cfg.min_start_goal_dist_m, rng)
        esdf = compute_esdf(scene.occupancy, map_cfg.resolution)
        teacher = compute_2d_dijkstra_field(scene.occupancy, (scene.goal[0], scene.goal[1]), map_cfg.resolution)
        if not _is_reachable(teacher, (scene.start[0], scene.start[1]), map_cfg.resolution):
            continue

        teacher = fill_unreachable(teacher, scene.occupancy, fill_value=fill_value)

        sample_path = out_dir / f"sample_{created:05d}.npz"
        np.savez_compressed(
            sample_path,
            occupancy=scene.occupancy.astype(np.uint8),
            esdf=esdf.astype(np.float32),
            teacher=teacher.astype(np.float32),
            start=np.asarray(scene.start, dtype=np.float32),
            goal=np.asarray(scene.goal, dtype=np.float32),
            resolution=np.float32(map_cfg.resolution),
            scenario=np.array(scene.scenario),
            fill_value=np.float32(fill_value),
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
    }
    with (out_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return counts


def describe_split(name: str, counts: Dict[str, int]) -> str:
    return f"{name}: {scenario_histogram(counts)}"
