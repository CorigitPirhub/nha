from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.esdf import compute_esdf
from env.teacher import compute_2d_dijkstra_field
from utils.common import ensure_dirs, set_seed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert Parasol-like narrow benchmarks to repo npz format")
    p.add_argument("--output-root", type=Path, default=Path("data/benchmark/parasol_narrow"))
    p.add_argument("--raw-root", type=Path, default=None, help="Optional raw map directory (png/pgm/npy/npz).")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--resolution", type=float, default=0.5)
    p.add_argument("--map-size", type=int, default=96)
    p.add_argument("--train-samples", type=int, default=120)
    p.add_argument("--test-samples", type=int, default=60)
    p.add_argument("--synthetic-only", action="store_true")
    return p.parse_args()


def _grid_to_world(ix: int, iy: int, resolution: float) -> tuple[float, float]:
    return (ix + 0.5) * resolution, (iy + 0.5) * resolution


def _otsu_threshold(img: np.ndarray) -> float:
    hist, edges = np.histogram(img.ravel(), bins=256, range=(0.0, 255.0))
    hist = hist.astype(np.float64)
    prob = hist / max(hist.sum(), 1.0)
    omega = np.cumsum(prob)
    mu = np.cumsum(prob * np.arange(256))
    mu_t = mu[-1]
    sigma_b = (mu_t * omega - mu) ** 2 / np.maximum(omega * (1.0 - omega), 1e-12)
    i = int(np.argmax(sigma_b))
    return float((edges[i] + edges[i + 1]) * 0.5)


def _load_gray(path: Path) -> np.ndarray:
    try:
        import imageio.v3 as iio

        arr = iio.imread(path)
    except Exception:
        from PIL import Image

        arr = np.asarray(Image.open(path).convert("L"))

    if arr.ndim == 3:
        arr = arr[..., :3].mean(axis=2)
    return arr.astype(np.float32)


def _to_occ_from_gray(gray: np.ndarray, out_size: int) -> np.ndarray:
    g = gray.astype(np.float32)
    if g.shape != (out_size, out_size):
        zoom = (out_size / max(g.shape[0], 1), out_size / max(g.shape[1], 1))
        g = ndimage.zoom(g, zoom=zoom, order=1)
        g = g[:out_size, :out_size]
    thr = _otsu_threshold(g)
    occ = g < thr
    free = float(np.mean((~occ).astype(np.float32)))
    if free < 0.15 or free > 0.9:
        occ = g > thr
    occ = occ.astype(bool)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    return occ


def _draw_rect(occ: np.ndarray, x0: int, y0: int, x1: int, y1: int, value: bool) -> None:
    h, w = occ.shape
    xa = int(np.clip(min(x0, x1), 0, w - 1))
    xb = int(np.clip(max(x0, x1), 0, w - 1))
    ya = int(np.clip(min(y0, y1), 0, h - 1))
    yb = int(np.clip(max(y0, y1), 0, h - 1))
    occ[ya : yb + 1, xa : xb + 1] = value


def _gen_bugtrap(size: int, rng: np.random.Generator) -> np.ndarray:
    occ = np.ones((size, size), dtype=bool)
    _draw_rect(occ, 2, 2, size - 3, size - 3, value=False)
    cx = int(size * 0.52 + rng.integers(-4, 5))
    cy = int(size * 0.52 + rng.integers(-4, 5))
    w = int(size * 0.32)
    h = int(size * 0.26)
    wall = int(max(3, size * 0.035))
    # U-shape trap.
    _draw_rect(occ, cx - w // 2, cy - h // 2, cx - w // 2 + wall, cy + h // 2, value=True)
    _draw_rect(occ, cx + w // 2 - wall, cy - h // 2, cx + w // 2, cy + h // 2, value=True)
    _draw_rect(occ, cx - w // 2, cy + h // 2 - wall, cx + w // 2, cy + h // 2, value=True)
    # Narrow entrance.
    gap_w = int(max(2, size * 0.03))
    _draw_rect(occ, cx - gap_w // 2, cy - h // 2, cx + gap_w // 2, cy - h // 2 + wall, value=False)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    return occ


def _gen_alpha_puzzle(size: int, rng: np.random.Generator) -> np.ndarray:
    occ = np.ones((size, size), dtype=bool)
    _draw_rect(occ, 2, 2, size - 3, size - 3, value=False)
    cx = int(size * 0.5)
    cy = int(size * 0.5)
    # Two crossing walls with offset slits.
    wall = int(max(3, size * 0.04))
    _draw_rect(occ, cx - wall // 2, int(size * 0.18), cx + wall // 2, int(size * 0.82), value=True)
    _draw_rect(occ, int(size * 0.18), cy - wall // 2, int(size * 0.82), cy + wall // 2, value=True)
    slit = int(max(2, size * 0.03))
    _draw_rect(occ, cx - wall // 2 - 1, int(size * 0.30), cx + wall // 2 + 1, int(size * 0.30) + slit, value=False)
    _draw_rect(occ, cx - wall // 2 - 1, int(size * 0.68), cx + wall // 2 + 1, int(size * 0.68) + slit, value=False)
    _draw_rect(occ, int(size * 0.30), cy - wall // 2 - 1, int(size * 0.30) + slit, cy + wall // 2 + 1, value=False)
    _draw_rect(occ, int(size * 0.68), cy - wall // 2 - 1, int(size * 0.68) + slit, cy + wall // 2 + 1, value=False)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    return occ


def _gen_flange(size: int, rng: np.random.Generator) -> np.ndarray:
    occ = np.ones((size, size), dtype=bool)
    _draw_rect(occ, 2, 2, size - 3, size - 3, value=False)
    # S-like narrow corridor.
    w = int(max(3, size * 0.05))
    _draw_rect(occ, int(size * 0.12), int(size * 0.18), int(size * 0.88), int(size * 0.18) + w, value=True)
    _draw_rect(occ, int(size * 0.12), int(size * 0.46), int(size * 0.88), int(size * 0.46) + w, value=True)
    _draw_rect(occ, int(size * 0.12), int(size * 0.74), int(size * 0.88), int(size * 0.74) + w, value=True)
    _draw_rect(occ, int(size * 0.24), int(size * 0.18), int(size * 0.24) + w, int(size * 0.46), value=False)
    _draw_rect(occ, int(size * 0.76), int(size * 0.46), int(size * 0.76) + w, int(size * 0.74), value=False)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    return occ


def _difficulty_from_occ(occ: np.ndarray) -> str:
    ratio = float(np.mean(occ.astype(np.float32)))
    if ratio < 0.25:
        return "medium"
    return "hard"


def _pick_start_goal(occ: np.ndarray, resolution: float, rng: np.random.Generator, min_dist_m: float = 10.0) -> tuple[tuple[float, float, float], tuple[float, float, float], np.ndarray] | None:
    free = np.argwhere(~occ)
    if free.size == 0:
        return None
    for _ in range(60):
        gyx = free[int(rng.integers(0, len(free)))]
        gy, gx = int(gyx[0]), int(gyx[1])
        goal_xy = _grid_to_world(gx, gy, resolution)
        dist = compute_2d_dijkstra_field(occ, goal_xy, resolution)
        cand = np.argwhere((~occ) & np.isfinite(dist) & (dist >= min_dist_m))
        if cand.size == 0:
            continue
        syx = cand[int(rng.integers(0, len(cand)))]
        sy, sx = int(syx[0]), int(syx[1])
        start_xy = _grid_to_world(sx, sy, resolution)
        start = (float(start_xy[0]), float(start_xy[1]), float(rng.uniform(-math.pi, math.pi)))
        goal = (float(goal_xy[0]), float(goal_xy[1]), float(rng.uniform(-math.pi, math.pi)))
        return start, goal, dist
    return None


def _scenario_from_name(name: str) -> str:
    s = name.lower()
    if re.search(r"bug.?trap", s):
        return "bug_trap"
    if "alpha" in s:
        return "alpha_puzzle"
    if "flange" in s:
        return "flange"
    return "parasol_misc"


def _collect_raw_maps(raw_root: Path, out_size: int) -> list[tuple[str, np.ndarray]]:
    maps: list[tuple[str, np.ndarray]] = []
    exts = {".png", ".pgm", ".jpg", ".jpeg", ".npy", ".npz"}
    for p in sorted(raw_root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        try:
            if p.suffix.lower() == ".npy":
                occ = np.load(p, allow_pickle=False).astype(bool)
            elif p.suffix.lower() == ".npz":
                z = np.load(p, allow_pickle=False)
                if "occupancy" in z:
                    occ = z["occupancy"].astype(bool)
                else:
                    continue
            else:
                occ = _to_occ_from_gray(_load_gray(p), out_size=out_size)
            if occ.shape != (out_size, out_size):
                occ = ndimage.zoom(occ.astype(np.float32), zoom=(out_size / max(occ.shape[0], 1), out_size / max(occ.shape[1], 1)), order=0) > 0.5
            occ[0, :] = True
            occ[-1, :] = True
            occ[:, 0] = True
            occ[:, -1] = True
            maps.append((_scenario_from_name(p.stem), occ.astype(bool)))
        except Exception:
            continue
    return maps


def _build_synthetic_maps(size: int, seed: int) -> list[tuple[str, np.ndarray]]:
    rng = np.random.default_rng(seed + 19)
    out: list[tuple[str, np.ndarray]] = []
    for i in range(3):
        out.append((f"bug_trap_{i}", _gen_bugtrap(size, rng)))
        out.append((f"alpha_puzzle_{i}", _gen_alpha_puzzle(size, rng)))
        out.append((f"flange_{i}", _gen_flange(size, rng)))
    return out


def _write_sample(
    out_path: Path,
    occ: np.ndarray,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    d2: np.ndarray,
    resolution: float,
    scenario: str,
    map_id: str,
) -> None:
    fill = 1e6
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
        scenario=np.asarray(scenario),
        difficulty=np.asarray(_difficulty_from_occ(occ)),
        task_type=np.asarray("narrow_passage"),
        source_dataset=np.asarray("parasol"),
        map_id=np.asarray(map_id),
        category=np.asarray("C"),
    )


def _scan_split(split_dir: Path) -> dict:
    files = sorted(split_dir.glob("sample_*.npz"))
    scenario_hist = Counter()
    diff_hist = Counter()
    map_hist = Counter()
    for p in files:
        with np.load(p, allow_pickle=False) as z:
            scenario_hist[str(z["scenario"])] += 1
            diff_hist[str(z["difficulty"])] += 1
            map_hist[str(z["map_id"])] += 1
    return {
        "num_samples": len(files),
        "scenario_histogram": dict(sorted(scenario_hist.items())),
        "difficulty_histogram": dict(sorted(diff_hist.items())),
        "num_maps": len(map_hist),
    }


def main() -> None:
    args = parse_args()
    set_seed(int(args.seed))
    ensure_dirs([args.output_root, args.output_root / "train", args.output_root / "test"])
    for p in (args.output_root / "train").glob("sample_*.npz"):
        p.unlink()
    for p in (args.output_root / "test").glob("sample_*.npz"):
        p.unlink()

    maps: list[tuple[str, np.ndarray]] = []
    raw_used = False
    if args.raw_root is not None and args.raw_root.exists() and not args.synthetic_only:
        maps = _collect_raw_maps(args.raw_root, out_size=int(args.map_size))
        raw_used = len(maps) > 0
    if not maps:
        maps = _build_synthetic_maps(size=int(args.map_size), seed=int(args.seed))

    rng = np.random.default_rng(int(args.seed) + 123)
    train_target = int(max(args.train_samples, 1))
    test_target = int(max(args.test_samples, 1))
    train_idx = 0
    test_idx = 0

    # Split maps by index for train/test diversity.
    map_ids = list(range(len(maps)))
    rng.shuffle(map_ids)
    cut = max(1, int(round(0.67 * len(map_ids))))
    train_map_ids = set(map_ids[:cut])

    max_iters = max(2500, 30 * (train_target + test_target))
    it = 0
    while (train_idx < train_target or test_idx < test_target) and it < max_iters:
        it += 1
        k = int(rng.integers(0, len(maps)))
        map_name, occ = maps[k]
        picked = _pick_start_goal(occ, resolution=float(args.resolution), rng=rng, min_dist_m=10.0 * float(args.resolution))
        if picked is None:
            continue
        start, goal, d2 = picked
        scenario = _scenario_from_name(map_name)
        map_id = f"parasol_{k:02d}_{map_name}"

        if k in train_map_ids and train_idx < train_target:
            out = args.output_root / "train" / f"sample_{train_idx:06d}.npz"
            _write_sample(out, occ, start, goal, d2, float(args.resolution), scenario=scenario, map_id=map_id)
            train_idx += 1
        elif k not in train_map_ids and test_idx < test_target:
            out = args.output_root / "test" / f"sample_{test_idx:06d}.npz"
            _write_sample(out, occ, start, goal, d2, float(args.resolution), scenario=scenario, map_id=map_id)
            test_idx += 1

    if train_idx < train_target or test_idx < test_target:
        raise RuntimeError(f"Failed to generate enough samples: train {train_idx}/{train_target}, test {test_idx}/{test_target}")

    meta = {
        "name": "parasol_narrow_converted",
        "seed": int(args.seed),
        "source": "raw_maps" if raw_used else "synthetic_classic_proxies",
        "raw_root": str(args.raw_root) if args.raw_root is not None else "",
        "resolution": float(args.resolution),
        "map_size": int(args.map_size),
        "splits": {
            "train": _scan_split(args.output_root / "train"),
            "test": _scan_split(args.output_root / "test"),
        },
    }
    (args.output_root / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Saved:")
    print(f"- {args.output_root / 'train'}")
    print(f"- {args.output_root / 'test'}")
    print(f"- {args.output_root / 'meta.json'}")


if __name__ == "__main__":
    main()
