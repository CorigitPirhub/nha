from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.esdf import compute_esdf
from env.teacher import compute_2d_dijkstra_field
from utils.common import ensure_dirs, set_seed


MP_CLASS_FILES = (
    "forest_032_moore_c8.npz",
    "mazes_032_moore_c8.npz",
    "alternating_gaps_032_moore_c8.npz",
    "shifting_gaps_032_moore_c8.npz",
    "gaps_and_forest_032_moore_c8.npz",
    "single_bugtrap_032_moore_c8.npz",
    "multiple_bugtraps_032_moore_c8.npz",
    "bugtrap_forest_032_moore_c8.npz",
)

MP_DIFFICULTY_MAP = {
    "forest": "simple",
    "mazes": "hard",
    "alternating_gaps": "medium",
    "shifting_gaps": "medium",
    "gaps_and_forest": "hard",
    "single_bugtrap": "medium",
    "multiple_bugtraps": "hard",
    "bugtrap_forest": "hard",
}


@dataclass
class ConvertConfig:
    output_root: Path
    external_root: Path
    seed: int
    resolution_m: float
    mp_train_per_class: int
    mp_test_per_class: int
    csm_num_maps: int
    csm_train_maps: int
    csm_train_per_map: int
    csm_test_per_map: int
    csm_crop_size: int
    auto_download: bool


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert MP/CSM benchmark datasets into repo .npz format")
    p.add_argument("--output-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--external-root", type=Path, default=Path("data/benchmark/.external"))
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--resolution", type=float, default=0.5)

    p.add_argument("--mp-train-per-class", type=int, default=800)
    p.add_argument("--mp-test-per-class", type=int, default=100)

    p.add_argument("--csm-num-maps", type=int, default=30)
    p.add_argument("--csm-train-maps", type=int, default=20)
    p.add_argument("--csm-train-per-map", type=int, default=40)
    p.add_argument("--csm-test-per-map", type=int, default=40)
    p.add_argument("--csm-crop-size", type=int, default=128)

    p.add_argument("--no-auto-download", action="store_true")
    return p.parse_args()


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, check=True, cwd=None if cwd is None else str(cwd))


def _clone_or_update_repo(repo_url: str, dst: Path) -> Path:
    if dst.exists() and (dst / ".git").exists():
        # Keep local cached snapshot to avoid network stalls during repeated conversions.
        return dst
    ensure_dirs([dst.parent])
    _run(["git", "clone", "--depth", "1", repo_url, str(dst)])
    return dst


def _download_and_unzip(url: str, zip_path: Path, extract_to: Path) -> None:
    ensure_dirs([zip_path.parent, extract_to])
    if not zip_path.exists():
        urllib.request.urlretrieve(url, str(zip_path))
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(str(extract_to))


def _grid_to_world(ix: int, iy: int, resolution: float) -> tuple[float, float]:
    return (ix + 0.5) * resolution, (iy + 0.5) * resolution


def _pick_random_start(
    dist: np.ndarray,
    occupancy: np.ndarray,
    min_dist_m: float,
    rng: np.random.Generator,
    unreachable_value: float = 1024.0,
) -> tuple[int, int] | None:
    candidate_mask = (
        (~occupancy)
        & np.isfinite(dist)
        & (dist >= float(min_dist_m))
        & (~np.isclose(dist, float(unreachable_value), atol=1e-6))
    )
    valid = np.argwhere(candidate_mask)
    if valid.size == 0:
        valid = np.argwhere(
            (~occupancy)
            & np.isfinite(dist)
            & (dist > 0.0)
            & (~np.isclose(dist, float(unreachable_value), atol=1e-6))
        )
        if valid.size == 0:
            return None
    yx = valid[int(rng.integers(0, len(valid)))]
    sx, sy = int(yx[1]), int(yx[0])
    d = float(dist[sy, sx])
    assert not np.isclose(d, float(unreachable_value), atol=1e-6), "sample_start_goal picked unreachable sentinel"
    assert np.isfinite(d), "sample_start_goal picked infinite distance"
    return sx, sy


def _decode_mp_teacher_distance(raw_dist: np.ndarray, unreachable_value: float = 1024.0) -> np.ndarray:
    raw = raw_dist.astype(np.float32)
    finite = raw[np.isfinite(raw)]
    if finite.size == 0:
        return np.full_like(raw, np.inf, dtype=np.float32)

    # MP packed labels may use negative signed distances (reachable) and -1024 for unreachable.
    neg_ratio = float(np.mean(finite < 0.0))
    if neg_ratio >= 0.5:
        dist = np.maximum(-raw, 0.0).astype(np.float32)
    else:
        dist = np.maximum(raw, 0.0).astype(np.float32)

    sent = float(unreachable_value)
    sentinel_mask = (
        np.isclose(np.abs(raw), sent, atol=1e-3)
        | np.isclose(dist, sent, atol=1e-3)
        | (dist >= sent - 1e-3)
    )
    dist[sentinel_mask] = np.inf
    return dist.astype(np.float32)


def _difficulty_from_occ_ratio(occ: np.ndarray) -> str:
    ratio = float(np.mean(occ.astype(np.float32)))
    if ratio < 0.22:
        return "simple"
    if ratio < 0.34:
        return "medium"
    return "hard"


def _otsu_threshold(img: np.ndarray) -> float:
    hist, bin_edges = np.histogram(img.ravel(), bins=256, range=(0.0, 255.0))
    hist = hist.astype(np.float64)
    prob = hist / np.maximum(hist.sum(), 1.0)
    omega = np.cumsum(prob)
    mu = np.cumsum(prob * np.arange(256))
    mu_t = mu[-1]
    sigma_b_sq = (mu_t * omega - mu) ** 2 / np.maximum(omega * (1.0 - omega), 1e-12)
    idx = int(np.argmax(sigma_b_sq))
    return float((bin_edges[idx] + bin_edges[idx + 1]) * 0.5)


def _load_grayscale(path: Path) -> np.ndarray:
    try:
        import imageio.v3 as iio

        arr = iio.imread(path)
    except Exception:
        from PIL import Image

        arr = np.asarray(Image.open(path).convert("L"))

    if arr.ndim == 3:
        arr = arr[..., :3].mean(axis=2)
    return arr.astype(np.float32)


def _crop_and_resize(gray: np.ndarray, crop_size: int, out_size: int, rng: np.random.Generator) -> np.ndarray:
    h, w = gray.shape
    if h < crop_size or w < crop_size:
        scale = max(crop_size / max(h, 1), crop_size / max(w, 1))
        gray = ndimage.zoom(gray, zoom=scale, order=1)
        h, w = gray.shape
    y0 = int(rng.integers(0, h - crop_size + 1))
    x0 = int(rng.integers(0, w - crop_size + 1))
    crop = gray[y0 : y0 + crop_size, x0 : x0 + crop_size]
    zoom = out_size / float(crop_size)
    out = ndimage.zoom(crop, zoom=zoom, order=1)
    if out.shape != (out_size, out_size):
        out = ndimage.zoom(out, zoom=(out_size / max(out.shape[0], 1), out_size / max(out.shape[1], 1)), order=1)
        out = out[:out_size, :out_size]
        if out.shape != (out_size, out_size):
            pad_h = out_size - out.shape[0]
            pad_w = out_size - out.shape[1]
            out = np.pad(out, ((0, max(pad_h, 0)), (0, max(pad_w, 0))), mode="edge")[:out_size, :out_size]
    return out.astype(np.float32)


def _gray_to_occupancy(gray: np.ndarray) -> np.ndarray:
    thr = _otsu_threshold(gray)
    occ = gray < thr
    free_ratio = float(np.mean((~occ).astype(np.float32)))
    if free_ratio < 0.15 or free_ratio > 0.9:
        occ = gray > thr
    occ = occ.astype(bool)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    return occ


def _write_sample(
    out_path: Path,
    occupancy: np.ndarray,
    teacher_2d: np.ndarray,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    resolution: float,
    scenario: str,
    difficulty: str,
    source_dataset: str,
    map_id: str,
) -> None:
    esdf = compute_esdf(occupancy, resolution=resolution)
    start = np.asarray([start_xy[0], start_xy[1], 0.0], dtype=np.float32)
    goal = np.asarray([goal_xy[0], goal_xy[1], 0.0], dtype=np.float32)
    fill = 1e6
    teacher_2d = teacher_2d.astype(np.float32)
    teacher_2d = np.where(np.isfinite(teacher_2d), teacher_2d, fill)
    teacher_2d[occupancy] = fill

    np.savez_compressed(
        out_path,
        occupancy=occupancy.astype(bool),
        esdf=esdf.astype(np.float32),
        teacher=teacher_2d.astype(np.float32),
        teacher_2d=teacher_2d.astype(np.float32),
        teacher_3d=teacher_2d[None, ...].astype(np.float32),
        start=start,
        goal=goal,
        resolution=np.float32(resolution),
        fill_value=np.float32(fill),
        scenario=np.asarray(scenario),
        category=np.asarray("U"),
        difficulty=np.asarray(difficulty),
        task_type=np.asarray("shortest_path"),
        source_dataset=np.asarray(source_dataset),
        map_id=np.asarray(map_id),
    )


def _convert_mp(cfg: ConvertConfig, planning_repo: Path) -> dict:
    src_root = planning_repo / "data" / "mpd"
    out_root = cfg.output_root / "mp"
    train_dir = out_root / "train"
    test_dir = out_root / "test"
    ensure_dirs([train_dir, test_dir])

    for p in train_dir.glob("sample_*.npz"):
        p.unlink()
    for p in test_dir.glob("sample_*.npz"):
        p.unlink()

    rng = np.random.default_rng(cfg.seed + 11)
    train_idx = 0
    test_idx = 0

    for class_file in MP_CLASS_FILES:
        fpath = src_root / class_file
        if not fpath.exists():
            raise FileNotFoundError(f"Missing MP class file: {fpath}")

        class_name = class_file.split("_032")[0]
        difficulty = MP_DIFFICULTY_MAP.get(class_name, "medium")

        with np.load(fpath, allow_pickle=False) as z:
            train_maps = z["arr_0"]
            train_goals = z["arr_1"]
            train_dist = z["arr_3"]

            test_maps = z["arr_8"]
            test_goals = z["arr_9"]
            test_dist = z["arr_11"]

        for i in range(min(cfg.mp_train_per_class, train_maps.shape[0])):
            free = train_maps[i] > 0.5
            occ = np.logical_not(free)
            goal_map = train_goals[i, 0]
            raw_dist = train_dist[i, 0].astype(np.float32)
            dist = _decode_mp_teacher_distance(raw_dist, unreachable_value=1024.0)
            dist[occ] = np.inf
            gy, gx = np.unravel_index(int(np.argmax(goal_map)), goal_map.shape)
            pick = _pick_random_start(dist, occ, min_dist_m=4.0 * cfg.resolution_m, rng=rng, unreachable_value=1024.0)
            if pick is None:
                continue
            sx, sy = pick
            d_start = float(dist[sy, sx])
            assert not np.isclose(d_start, 1024.0, atol=1e-6), "sample_start_goal picked sentinel 1024.0"
            assert np.isfinite(d_start), "sample_start_goal picked non-finite teacher distance"
            start_xy = _grid_to_world(sx, sy, cfg.resolution_m)
            goal_xy = _grid_to_world(int(gx), int(gy), cfg.resolution_m)

            out = train_dir / f"sample_{train_idx:06d}.npz"
            _write_sample(
                out_path=out,
                occupancy=occ,
                teacher_2d=dist,
                start_xy=start_xy,
                goal_xy=goal_xy,
                resolution=cfg.resolution_m,
                scenario=class_name,
                difficulty=difficulty,
                source_dataset="mp",
                map_id=f"mp_{class_name}",
            )
            train_idx += 1

        for i in range(min(cfg.mp_test_per_class, test_maps.shape[0])):
            free = test_maps[i] > 0.5
            occ = np.logical_not(free)
            goal_map = test_goals[i, 0]
            raw_dist = test_dist[i, 0].astype(np.float32)
            dist = _decode_mp_teacher_distance(raw_dist, unreachable_value=1024.0)
            dist[occ] = np.inf
            gy, gx = np.unravel_index(int(np.argmax(goal_map)), goal_map.shape)
            pick = _pick_random_start(dist, occ, min_dist_m=4.0 * cfg.resolution_m, rng=rng, unreachable_value=1024.0)
            if pick is None:
                continue
            sx, sy = pick
            d_start = float(dist[sy, sx])
            assert not np.isclose(d_start, 1024.0, atol=1e-6), "sample_start_goal picked sentinel 1024.0"
            assert np.isfinite(d_start), "sample_start_goal picked non-finite teacher distance"
            start_xy = _grid_to_world(sx, sy, cfg.resolution_m)
            goal_xy = _grid_to_world(int(gx), int(gy), cfg.resolution_m)

            out = test_dir / f"sample_{test_idx:06d}.npz"
            _write_sample(
                out_path=out,
                occupancy=occ,
                teacher_2d=dist,
                start_xy=start_xy,
                goal_xy=goal_xy,
                resolution=cfg.resolution_m,
                scenario=class_name,
                difficulty=difficulty,
                source_dataset="mp",
                map_id=f"mp_{class_name}",
            )
            test_idx += 1

    return {
        "train_count": train_idx,
        "test_count": test_idx,
        "class_files": list(MP_CLASS_FILES),
    }


def _prepare_csm_raw_maps(cfg: ConvertConfig, planning_repo: Path) -> list[Path]:
    raw_root = planning_repo / "data" / "street" / "original" / "all"
    ensure_dirs([raw_root])
    maps = sorted(raw_root.glob("*_256.png"))

    if maps:
        return maps

    if not cfg.auto_download:
        return maps

    zip_path = planning_repo / "data" / "street" / "original" / "street-png.zip"
    _download_and_unzip(
        url="https://www.movingai.com/benchmarks/street/street-png.zip",
        zip_path=zip_path,
        extract_to=raw_root,
    )
    maps = sorted(raw_root.glob("*_256.png"))
    return maps


def _convert_csm_from_maps(cfg: ConvertConfig, planning_repo: Path) -> dict:
    maps = _prepare_csm_raw_maps(cfg, planning_repo)
    if len(maps) < cfg.csm_num_maps:
        raise RuntimeError(
            f"Need at least {cfg.csm_num_maps} CSM maps, got {len(maps)} under {planning_repo / 'data/street/original/all'}"
        )

    sel_maps = maps[: cfg.csm_num_maps]
    train_maps = sel_maps[: cfg.csm_train_maps]
    test_maps = sel_maps[cfg.csm_train_maps : cfg.csm_num_maps]

    out_root = cfg.output_root / "csm"
    train_dir = out_root / "train"
    test_dir = out_root / "test"
    ensure_dirs([train_dir, test_dir])

    for p in train_dir.glob("sample_*.npz"):
        p.unlink()
    for p in test_dir.glob("sample_*.npz"):
        p.unlink()

    rng = np.random.default_rng(cfg.seed + 23)

    def gen_split(map_list: Iterable[Path], n_per_map: int, out_dir: Path, start_idx: int) -> int:
        idx = start_idx
        for mp in map_list:
            base = mp.stem
            gray = _load_grayscale(mp)
            produced = 0
            attempts = 0
            max_attempts = int(max(200, n_per_map * 300))

            while produced < int(n_per_map) and attempts < max_attempts:
                attempts += 1
                crop = _crop_and_resize(gray, crop_size=cfg.csm_crop_size, out_size=64, rng=rng)
                occ = _gray_to_occupancy(crop)

                # Sample valid goal/start from connected free-space.
                ok = False
                for _attempt in range(80):
                    free = np.argwhere(~occ)
                    if free.size == 0:
                        break
                    gyx = free[int(rng.integers(0, len(free)))]
                    gx, gy = int(gyx[1]), int(gyx[0])
                    goal_xy = _grid_to_world(gx, gy, cfg.resolution_m)
                    dist = compute_2d_dijkstra_field(occ, goal_xy, cfg.resolution_m)
                    start_pick = _pick_random_start(dist, occ, min_dist_m=6.0 * cfg.resolution_m, rng=rng)
                    if start_pick is None:
                        continue
                    sx, sy = start_pick
                    start_xy = _grid_to_world(sx, sy, cfg.resolution_m)
                    ok = True
                    break

                if not ok:
                    continue

                difficulty = _difficulty_from_occ_ratio(occ)
                out = out_dir / f"sample_{idx:06d}.npz"
                _write_sample(
                    out_path=out,
                    occupancy=occ,
                    teacher_2d=dist,
                    start_xy=start_xy,
                    goal_xy=goal_xy,
                    resolution=cfg.resolution_m,
                    scenario="csm_city_street",
                    difficulty=difficulty,
                    source_dataset="csm",
                    map_id=base,
                )
                idx += 1
                produced += 1

            if produced < int(n_per_map):
                raise RuntimeError(
                    f"CSM map {base} generated {produced}/{int(n_per_map)} samples after {attempts} attempts"
                )
        return idx

    train_end = gen_split(train_maps, cfg.csm_train_per_map, train_dir, 0)
    test_end = gen_split(test_maps, cfg.csm_test_per_map, test_dir, 0)

    return {
        "num_maps_total": len(sel_maps),
        "num_maps_train": len(train_maps),
        "num_maps_test": len(test_maps),
        "train_count": train_end,
        "test_count": test_end,
        "source": "movingai_street_png",
    }


def _convert_csm_from_packed_npz(cfg: ConvertConfig, planning_repo: Path) -> dict:
    packed = planning_repo / "data" / "street" / "mixed_064_moore_c16.npz"
    if not packed.exists():
        raise FileNotFoundError(f"Missing packed CSM npz: {packed}")

    out_root = cfg.output_root / "csm"
    train_dir = out_root / "train"
    test_dir = out_root / "test"
    ensure_dirs([train_dir, test_dir])

    for p in train_dir.glob("sample_*.npz"):
        p.unlink()
    for p in test_dir.glob("sample_*.npz"):
        p.unlink()

    with np.load(packed, allow_pickle=False) as z:
        x_tr = z["arr_0"]
        g_tr = z["arr_1"]
        d_tr = z["arr_3"]
        x_te = z["arr_8"]
        g_te = z["arr_9"]
        d_te = z["arr_11"]

    rng = np.random.default_rng(cfg.seed + 41)

    def write_split(x, g, d, out_dir: Path, limit: int) -> int:
        idx = 0
        n = min(limit, x.shape[0])
        for i in range(n):
            free = x[i] > 0.5
            occ = np.logical_not(free)
            goal_map = g[i, 0]
            raw_dist = d[i, 0].astype(np.float32)
            dist = _decode_mp_teacher_distance(raw_dist, unreachable_value=4096.0)
            dist[occ] = np.inf
            gy, gx = np.unravel_index(int(np.argmax(goal_map)), goal_map.shape)
            pick = _pick_random_start(dist, occ, min_dist_m=6.0 * cfg.resolution_m, rng=rng, unreachable_value=4096.0)
            if pick is None:
                continue
            sx, sy = pick
            d_start = float(dist[sy, sx])
            assert np.isfinite(d_start), "sample_start_goal picked non-finite teacher distance (CSM packed)"
            start_xy = _grid_to_world(sx, sy, cfg.resolution_m)
            goal_xy = _grid_to_world(int(gx), int(gy), cfg.resolution_m)
            out = out_dir / f"sample_{idx:06d}.npz"
            _write_sample(
                out_path=out,
                occupancy=occ,
                teacher_2d=dist,
                start_xy=start_xy,
                goal_xy=goal_xy,
                resolution=cfg.resolution_m,
                scenario="csm_city_street",
                difficulty=_difficulty_from_occ_ratio(occ),
                source_dataset="csm",
                map_id=f"packed_{i // max(cfg.csm_train_per_map, 1):03d}",
            )
            idx += 1
        return idx

    train_target = cfg.csm_train_maps * cfg.csm_train_per_map
    test_target = (cfg.csm_num_maps - cfg.csm_train_maps) * cfg.csm_test_per_map

    train_count = write_split(x_tr, g_tr, d_tr, train_dir, train_target)
    test_count = write_split(x_te, g_te, d_te, test_dir, test_target)

    return {
        "num_maps_total": cfg.csm_num_maps,
        "num_maps_train": cfg.csm_train_maps,
        "num_maps_test": cfg.csm_num_maps - cfg.csm_train_maps,
        "train_count": train_count,
        "test_count": test_count,
        "source": "planning_datasets_packed_npz_fallback",
    }


def _scan_split(split_dir: Path) -> dict:
    files = sorted(split_dir.glob("sample_*.npz"))
    scenario_hist = Counter()
    difficulty_hist = Counter()
    map_hist = Counter()
    for p in files:
        with np.load(p, allow_pickle=False) as z:
            scenario_hist[str(z.get("scenario", "unknown"))] += 1
            difficulty_hist[str(z.get("difficulty", "unknown"))] += 1
            map_hist[str(z.get("map_id", "unknown"))] += 1
    return {
        "num_samples": len(files),
        "scenario_histogram": dict(sorted(scenario_hist.items())),
        "difficulty_histogram": dict(sorted(difficulty_hist.items())),
        "num_maps": len(map_hist),
    }


def _write_meta(dataset_root: Path, payload: dict) -> None:
    (dataset_root / "meta.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    cfg = ConvertConfig(
        output_root=args.output_root,
        external_root=args.external_root,
        seed=int(args.seed),
        resolution_m=float(args.resolution),
        mp_train_per_class=int(args.mp_train_per_class),
        mp_test_per_class=int(args.mp_test_per_class),
        csm_num_maps=int(args.csm_num_maps),
        csm_train_maps=int(args.csm_train_maps),
        csm_train_per_map=int(args.csm_train_per_map),
        csm_test_per_map=int(args.csm_test_per_map),
        csm_crop_size=int(args.csm_crop_size),
        auto_download=(not bool(args.no_auto_download)),
    )

    set_seed(cfg.seed)
    ensure_dirs([cfg.output_root, cfg.external_root])

    planning_repo = cfg.external_root / "planning-datasets"
    if cfg.auto_download:
        planning_repo = _clone_or_update_repo("https://github.com/omron-sinicx/planning-datasets.git", planning_repo)
    elif not planning_repo.exists():
        raise FileNotFoundError(f"Missing planning-datasets repo at {planning_repo}; enable auto-download")

    print("[1/3] Converting MP dataset...")
    mp_info = _convert_mp(cfg, planning_repo)

    print("[2/3] Converting CSM dataset...")
    try:
        csm_info = _convert_csm_from_packed_npz(cfg, planning_repo)
    except Exception as e:
        print(f"[warn] CSM packed-npz conversion failed: {e}")
        print("[warn] Falling back to raw-map conversion.")
        csm_info = _convert_csm_from_maps(cfg, planning_repo)

    print("[3/3] Writing metadata...")
    mp_root = cfg.output_root / "mp"
    csm_root = cfg.output_root / "csm"

    mp_meta = {
        "name": "mp_benchmark_converted",
        "seed": cfg.seed,
        "source_repo": str(planning_repo),
        "source": "planning-datasets/mpd",
        "resolution": cfg.resolution_m,
        "conversion": mp_info,
        "splits": {
            "train": _scan_split(mp_root / "train"),
            "test": _scan_split(mp_root / "test"),
        },
    }

    csm_meta = {
        "name": "csm_benchmark_converted",
        "seed": cfg.seed,
        "source_repo": str(planning_repo),
        "resolution": cfg.resolution_m,
        "conversion": csm_info,
        "splits": {
            "train": _scan_split(csm_root / "train"),
            "test": _scan_split(csm_root / "test"),
        },
    }

    _write_meta(mp_root, mp_meta)
    _write_meta(csm_root, csm_meta)

    merged = {
        "name": "benchmark_bundle",
        "seed": cfg.seed,
        "datasets": {
            "mp": mp_meta,
            "csm": csm_meta,
        },
    }
    (cfg.output_root / "meta.json").write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Saved:")
    print(f"- {mp_root}")
    print(f"- {csm_root}")
    print(f"- {cfg.output_root / 'meta.json'}")


if __name__ == "__main__":
    main()
