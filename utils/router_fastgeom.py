from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

from baselines.common import load_grid_sample
from scripts.evaluate_baselines import _astar_grid, _path_length, _world_to_grid


def _read_index(index_csv: Path) -> list[dict[str, str]]:
    if not index_csv.exists():
        raise FileNotFoundError(f"Missing split index: {index_csv}")
    rows: list[dict[str, str]] = []
    with index_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({str(k): str(v) for k, v in row.items()})
    if not rows:
        raise RuntimeError(f"Empty split index: {index_csv}")
    return rows


def _point_to_line_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    vx = float(bx - ax)
    vy = float(by - ay)
    wx = float(px - ax)
    wy = float(py - ay)
    denom = vx * vx + vy * vy
    if denom <= 1e-12:
        return float(math.hypot(wx, wy))
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / denom))
    qx = ax + t * vx
    qy = ay + t * vy
    return float(math.hypot(px - qx, py - qy))


def _path_turn_stats(path_xy: list[tuple[float, float]]) -> tuple[float, float]:
    if len(path_xy) < 3:
        return 0.0, 0.0
    turns: list[float] = []
    for (x0, y0), (x1, y1), (x2, y2) in zip(path_xy[:-2], path_xy[1:-1], path_xy[2:]):
        v1 = np.asarray([float(x1 - x0), float(y1 - y0)], dtype=np.float64)
        v2 = np.asarray([float(x2 - x1), float(y2 - y1)], dtype=np.float64)
        n1 = float(np.linalg.norm(v1))
        n2 = float(np.linalg.norm(v2))
        if n1 <= 1e-12 or n2 <= 1e-12:
            continue
        cos = float(np.clip(float(np.dot(v1, v2)) / max(n1 * n2, 1e-12), -1.0, 1.0))
        turns.append(float(abs(math.acos(cos))))
    if not turns:
        return 0.0, 0.0
    arr = np.asarray(turns, dtype=np.float64)
    return float(np.mean(arr)), float(np.sum(arr))


def _corridor_occ_mean(path_xy: list[tuple[float, float]], occupancy: np.ndarray, resolution: float, radius_cells: int) -> float:
    if not path_xy:
        return 0.0
    if int(radius_cells) <= 0:
        return 0.0
    h, w = occupancy.shape
    occ_u8 = occupancy.astype(np.uint8)
    vals: list[float] = []
    for x, y in path_xy:
        gx, gy = _world_to_grid(float(x), float(y), float(resolution), w, h)
        x0 = max(int(gx) - int(radius_cells), 0)
        x1 = min(int(gx) + int(radius_cells) + 1, w)
        y0 = max(int(gy) - int(radius_cells), 0)
        y1 = min(int(gy) + int(radius_cells) + 1, h)
        patch = occ_u8[y0:y1, x0:x1]
        vals.append(float(np.mean(patch)))
    if not vals:
        return 0.0
    return float(np.mean(np.asarray(vals, dtype=np.float64)))


def _path_clearance_stats(path_xy: list[tuple[float, float]], clearance_m: np.ndarray, resolution: float) -> tuple[float, float, float]:
    if not path_xy:
        return 0.0, 0.0, 0.0
    h, w = clearance_m.shape
    vals: list[float] = []
    for x, y in path_xy:
        gx, gy = _world_to_grid(float(x), float(y), float(resolution), w, h)
        vals.append(float(clearance_m[gy, gx]))
    arr = np.asarray(vals, dtype=np.float64)
    return float(np.mean(arr)), float(np.std(arr)), float(np.min(arr))


def _line_dev_stats(path_xy: list[tuple[float, float]], start_xy: tuple[float, float], goal_xy: tuple[float, float]) -> tuple[float, float]:
    if not path_xy:
        return 0.0, 0.0
    vals = [
        _point_to_line_distance(float(x), float(y), float(start_xy[0]), float(start_xy[1]), float(goal_xy[0]), float(goal_xy[1]))
        for x, y in path_xy
    ]
    arr = np.asarray(vals, dtype=np.float64)
    return float(np.mean(arr)), float(np.quantile(arr, 0.90))


def _expanded_stats(
    expanded: list[tuple[int, int]],
    *,
    goal_xy: tuple[float, float],
    resolution: float,
    h: int,
    w: int,
    euclid_dist_m: float,
) -> tuple[float, float, float, float]:
    if not expanded:
        return 0.0, 0.0, 0.0, 1.0
    pts = np.asarray(expanded, dtype=np.int64)
    xs = pts[:, 0]
    ys = pts[:, 1]
    bbox_area = int((int(xs.max()) - int(xs.min()) + 1) * (int(ys.max()) - int(ys.min()) + 1))
    uniq = np.unique(pts, axis=0)
    uniq_n = int(len(uniq))
    bbox_ratio = float(bbox_area / max(h * w, 1))
    fill_ratio = float(uniq_n / max(bbox_area, 1))
    map_ratio = float(uniq_n / max(h * w, 1))
    goal_d = np.hypot((uniq[:, 0].astype(np.float64) + 0.5) * float(resolution) - float(goal_xy[0]), (uniq[:, 1].astype(np.float64) + 0.5) * float(resolution) - float(goal_xy[1]))
    goal_ratio = float(np.min(goal_d) / max(float(euclid_dist_m), 1e-6))
    return bbox_ratio, fill_ratio, map_ratio, goal_ratio


def build_fastgeom_features(
    *,
    dataset_root: Path,
    split: str,
    out_cache: Path,
    max_expansions: int = 50000,
    corridor_radius_cells: int = 2,
) -> Path:
    dataset_root = Path(dataset_root)
    out_cache = Path(out_cache)
    out_cache.parent.mkdir(parents=True, exist_ok=True)

    rows_idx = _read_index(dataset_root / f"{split}_index.csv")
    split_dir = dataset_root / split
    if not split_dir.exists():
        raise FileNotFoundError(f"Missing split directory: {split_dir}")

    rows: list[dict[str, float | str]] = []
    total = len(rows_idx)
    for i, meta in enumerate(rows_idx, start=1):
        sample_name = str(meta["sample_name"])
        sample_path = split_dir / sample_name
        if not sample_path.exists():
            raise FileNotFoundError(sample_path)
        sample = load_grid_sample(sample_path)
        start_xy = (float(sample.start[0]), float(sample.start[1]))
        goal_xy = (float(sample.goal[0]), float(sample.goal[1]))
        euclid_dist_m = float(math.hypot(goal_xy[0] - start_xy[0], goal_xy[1] - start_xy[1]))
        h, w = sample.occupancy.shape

        fast = _astar_grid(
            occupancy=sample.occupancy,
            resolution=float(sample.resolution),
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=int(max_expansions),
            heuristic_map=None,
            heuristic_weight=1.0,
            record_expanded=True,
        )
        path_xy = [(float(x), float(y)) for x, y in fast.get("path", [])]
        path_len = float(_path_length(path_xy))
        clearance_m = ndimage.distance_transform_edt((~sample.occupancy).astype(np.uint8)).astype(np.float32) * float(sample.resolution)
        clear_mean, clear_std, clear_min = _path_clearance_stats(path_xy, clearance_m, float(sample.resolution))
        turn_mean, turn_sum = _path_turn_stats(path_xy)
        line_dev_mean, line_dev_p90 = _line_dev_stats(path_xy, start_xy, goal_xy)
        corridor_occ_mean = _corridor_occ_mean(path_xy, sample.occupancy, float(sample.resolution), int(corridor_radius_cells))
        bbox_ratio, fill_ratio, map_ratio, goal_ratio = _expanded_stats(
            fast.get("expanded", []),
            goal_xy=goal_xy,
            resolution=float(sample.resolution),
            h=int(h),
            w=int(w),
            euclid_dist_m=float(euclid_dist_m),
        )

        rows.append(
            {
                "sample_name": sample_name,
                "difficulty": str(meta["difficulty"]),
                "fg_path_stretch": float(path_len / max(euclid_dist_m, float(sample.resolution))),
                "fg_path_clear_mean": float(clear_mean),
                "fg_path_clear_std": float(clear_std),
                "fg_path_clear_min": float(clear_min),
                "fg_path_turn_mean_rad": float(turn_mean),
                "fg_path_turn_sum_rad": float(turn_sum),
                "fg_line_dev_mean_m": float(line_dev_mean),
                "fg_line_dev_p90_m": float(line_dev_p90),
                "fg_corridor_occ_mean": float(corridor_occ_mean),
                "fg_exp_bbox_ratio": float(bbox_ratio),
                "fg_exp_fill_ratio": float(fill_ratio),
                "fg_exp_map_ratio": float(map_ratio),
                "fg_exp_goal_dist_ratio": float(goal_ratio),
                "fg_exp_per_path_m": float(fast.get("expansions", 0) / max(path_len, float(sample.resolution))),
                "fg_ms_per_exp": float(float(fast.get("runtime_ms", 0.0)) / max(int(fast.get("expansions", 0)), 1)),
            }
        )
        if i % 200 == 0 or i == total:
            print(f"[fastgeom] {split} processed {i}/{total}")

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(f"No fastgeom rows generated for split={split!r}")
    if df.isna().any().any():
        raise RuntimeError(f"NaN detected in fastgeom features for split={split!r}")
    df.to_parquet(out_cache, index=False)
    return out_cache
