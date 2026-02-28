from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import tarfile
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.esdf import compute_esdf
from env.teacher import compute_2d_dijkstra_field
from utils.common import ensure_dirs, set_seed


@dataclass
class QuerySpec:
    scenario_name: str
    map_id: str
    pairs: list[tuple[tuple[float, float, float], tuple[float, float, float]]]
    bounds: tuple[float, float, float, float] | None


def parse_args() -> argparse.Namespace:
    default_clearance = float(np.hypot(DEFAULT_CONFIG.vehicle.length * 0.5, DEFAULT_CONFIG.vehicle.width * 0.5))
    p = argparse.ArgumentParser(description="Convert Parasol-like narrow benchmarks to repo npz format")
    p.add_argument("--output-root", type=Path, default=Path("data/benchmark/parasol_narrow"))
    p.add_argument("--raw-root", type=Path, default=None, help="Optional raw map directory (png/pgm/npy/npz).")
    p.add_argument("--open-ppl-root", type=Path, default=Path("data/benchmark/.external/open-ppl-env"))
    p.add_argument("--open-ppl-repo-url", type=str, default="https://github.com/parasollab/open-ppl-env.git")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--resolution", type=float, default=0.5)
    p.add_argument("--map-size", type=int, default=96)
    p.add_argument("--train-samples", type=int, default=120)
    p.add_argument("--test-samples", type=int, default=60)
    p.add_argument("--synthetic-only", action="store_true")
    p.add_argument("--no-auto-download", action="store_true")
    p.add_argument("--include-all-open-scenes", action="store_true")
    p.add_argument(
        "--scene-filter",
        type=str,
        default="bug_trap,alpha,flange",
        help="Comma-separated scene keywords used when --include-all-open-scenes is not set.",
    )
    p.add_argument("--disable-flange-variants", action="store_true")
    p.add_argument(
        "--train-ratio",
        type=float,
        default=0.0,
        help="Split ratio of open-ppl tasks into train. Default 0.0 means all public tasks are in test split.",
    )
    p.add_argument(
        "--min-clearance-m",
        type=float,
        default=default_clearance,
        help="Minimum ESDF clearance (meters) required for mapped start/goal. Fallback keeps all tasks if unmet.",
    )
    return p.parse_args()


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, check=True, cwd=None if cwd is None else str(cwd))


def _clone_or_update_repo(repo_url: str, dst: Path) -> Path:
    if dst.exists() and (dst / ".git").exists():
        return dst
    ensure_dirs([dst.parent])
    _run(["git", "clone", "--depth", "1", repo_url, str(dst)])
    return dst


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


def _gen_bugtrap(size: int, rng: np.random.Generator, tightness: float = 1.0) -> np.ndarray:
    occ = np.ones((size, size), dtype=bool)
    _draw_rect(occ, 2, 2, size - 3, size - 3, value=False)
    cx = int(size * 0.52 + rng.integers(-4, 5))
    cy = int(size * 0.52 + rng.integers(-4, 5))
    w = int(size * (0.30 + 0.04 * tightness))
    h = int(size * (0.24 + 0.03 * tightness))
    wall = int(max(3, size * (0.030 + 0.01 * tightness)))
    _draw_rect(occ, cx - w // 2, cy - h // 2, cx - w // 2 + wall, cy + h // 2, value=True)
    _draw_rect(occ, cx + w // 2 - wall, cy - h // 2, cx + w // 2, cy + h // 2, value=True)
    _draw_rect(occ, cx - w // 2, cy + h // 2 - wall, cx + w // 2, cy + h // 2, value=True)
    gap_w = int(max(2, size * (0.018 + 0.014 * tightness)))
    _draw_rect(occ, cx - gap_w // 2, cy - h // 2, cx + gap_w // 2, cy - h // 2 + wall, value=False)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    return occ


def _gen_alpha_puzzle(size: int, rng: np.random.Generator, tightness: float = 1.0) -> np.ndarray:
    del rng
    occ = np.ones((size, size), dtype=bool)
    _draw_rect(occ, 2, 2, size - 3, size - 3, value=False)
    cx = int(size * 0.5)
    cy = int(size * 0.5)
    wall = int(max(3, size * (0.03 + 0.015 * tightness)))
    _draw_rect(occ, cx - wall // 2, int(size * 0.16), cx + wall // 2, int(size * 0.84), value=True)
    _draw_rect(occ, int(size * 0.16), cy - wall // 2, int(size * 0.84), cy + wall // 2, value=True)
    slit = int(max(2, size * (0.02 + 0.015 * (1.2 - tightness))))
    _draw_rect(occ, cx - wall // 2 - 1, int(size * 0.29), cx + wall // 2 + 1, int(size * 0.29) + slit, value=False)
    _draw_rect(occ, cx - wall // 2 - 1, int(size * 0.69), cx + wall // 2 + 1, int(size * 0.69) + slit, value=False)
    _draw_rect(occ, int(size * 0.29), cy - wall // 2 - 1, int(size * 0.29) + slit, cy + wall // 2 + 1, value=False)
    _draw_rect(occ, int(size * 0.69), cy - wall // 2 - 1, int(size * 0.69) + slit, cy + wall // 2 + 1, value=False)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    return occ


def _gen_flange(size: int, rng: np.random.Generator, tightness: float = 1.0) -> np.ndarray:
    del rng
    occ = np.ones((size, size), dtype=bool)
    _draw_rect(occ, 2, 2, size - 3, size - 3, value=False)
    wall = int(max(2, size * (0.030 + 0.025 * tightness)))
    _draw_rect(occ, int(size * 0.12), int(size * 0.18), int(size * 0.88), int(size * 0.18) + wall, value=True)
    _draw_rect(occ, int(size * 0.12), int(size * 0.46), int(size * 0.88), int(size * 0.46) + wall, value=True)
    _draw_rect(occ, int(size * 0.12), int(size * 0.74), int(size * 0.88), int(size * 0.74) + wall, value=True)
    throat = int(max(2, wall * max(0.8, 1.35 - tightness)))
    _draw_rect(occ, int(size * 0.24), int(size * 0.18), int(size * 0.24) + throat, int(size * 0.46), value=False)
    _draw_rect(occ, int(size * 0.76), int(size * 0.46), int(size * 0.76) + throat, int(size * 0.74), value=False)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    return occ


def _gen_obstacle_field(size: int, rng: np.random.Generator, count: int = 16) -> np.ndarray:
    occ = np.zeros((size, size), dtype=bool)
    occ[0, :] = True
    occ[-1, :] = True
    occ[:, 0] = True
    occ[:, -1] = True
    for _ in range(count):
        w = int(rng.integers(max(3, size // 22), max(5, size // 9)))
        h = int(rng.integers(max(3, size // 22), max(5, size // 9)))
        x = int(rng.integers(2, max(3, size - w - 2)))
        y = int(rng.integers(2, max(3, size - h - 2)))
        occ[y : y + h, x : x + w] = True
    return occ


def _difficulty_from_occ(occ: np.ndarray) -> str:
    ratio = float(np.mean(occ.astype(np.float32)))
    if ratio < 0.25:
        return "medium"
    return "hard"


def _wrap_angle(a: float) -> float:
    return float(math.atan2(math.sin(a), math.cos(a)))


def _query_angle_to_rad(v: float) -> float:
    # Some query files store heading in degrees (e.g., -25), others in radians.
    if abs(float(v)) > (2.0 * math.pi):
        return float(np.deg2rad(v))
    return float(v)


def _scenario_from_name(name: str) -> str:
    s = name.lower()
    if re.search(r"bug.?trap", s):
        return "bug_trap"
    if "alpha" in s:
        return "alpha_puzzle"
    if "flange" in s:
        return "flange"
    if "maze" in s:
        return "maze"
    if "tunnel" in s or "zigzag" in s:
        return "narrow_passage"
    return "parasol_misc"


def _parse_variant_scale(name: str) -> float:
    m = re.search(r"flange[_-]?([0-9]+(?:\.[0-9]+)?)", name.lower())
    if m is None:
        return 1.0
    try:
        v = float(m.group(1))
    except Exception:
        return 1.0
    return float(np.clip(v, 0.75, 1.25))


def _generate_open_ppl_template(scene_name: str, map_id: str, size: int, seed: int) -> np.ndarray:
    scene = scene_name.lower()
    tightness = _parse_variant_scale(map_id)
    rng = np.random.default_rng(seed)
    if "bug" in scene:
        return _gen_bugtrap(size=size, rng=rng, tightness=tightness)
    if "alpha" in scene:
        return _gen_alpha_puzzle(size=size, rng=rng, tightness=tightness)
    if "flange" in scene:
        return _gen_flange(size=size, rng=rng, tightness=tightness)
    if "maze" in scene:
        return _gen_alpha_puzzle(size=size, rng=rng, tightness=1.15)
    if "tunnel" in scene or "zigzag" in scene or "serial" in scene or "periscope" in scene:
        return _gen_flange(size=size, rng=rng, tightness=1.18)
    if "obstacle" in scene or "box" in scene or "heterogeneous" in scene:
        return _gen_obstacle_field(size=size, rng=rng, count=max(10, size // 4))
    return _gen_alpha_puzzle(size=size, rng=rng, tightness=1.0)


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
                occ = ndimage.zoom(
                    occ.astype(np.float32),
                    zoom=(out_size / max(occ.shape[0], 1), out_size / max(occ.shape[1], 1)),
                    order=0,
                ) > 0.5
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


def _parse_boundary_box(text: str) -> tuple[float, float, float, float] | None:
    m = re.search(
        r"Boundary\s*Box\s*\[\s*([-+0-9.eE]+)\s*:\s*([-+0-9.eE]+)\s*;\s*([-+0-9.eE]+)\s*:\s*([-+0-9.eE]+)",
        text,
        flags=re.IGNORECASE,
    )
    if m is None:
        return None
    xmin, xmax, ymin, ymax = (float(m.group(i)) for i in range(1, 5))
    if xmax <= xmin or ymax <= ymin:
        return None
    return xmin, xmax, ymin, ymax


def _parse_query_pairs_from_text(text: str) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    entries: list[tuple[float, float, float]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        nums = [float(x) for x in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", line)]
        if len(nums) < 3:
            continue
        x = float(nums[1]) if len(nums) >= 2 else float(nums[0])
        y = float(nums[2]) if len(nums) >= 3 else 0.0
        yaw_raw = float(nums[3]) if len(nums) >= 4 else 0.0
        yaw = _query_angle_to_rad(yaw_raw)
        entries.append((x, y, yaw))

    pairs: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for i in range(0, len(entries) - 1, 2):
        pairs.append((entries[i], entries[i + 1]))
    return pairs


def _collect_open_ppl_specs(
    root: Path,
    include_all_open_scenes: bool,
    scene_filter: set[str],
    include_flange_variants: bool,
) -> list[QuerySpec]:
    specs: list[QuerySpec] = []
    if not root.exists():
        return specs

    def include_scene(path_key: str) -> bool:
        if include_all_open_scenes:
            return True
        key = path_key.lower()
        return any(tok in key for tok in scene_filter)

    query_files = sorted(root.rglob("*.query"))
    for q in query_files:
        if "vizmo" in q.name.lower():
            continue
        rel = q.relative_to(root)
        path_key = str(rel.parent).lower()
        if not include_scene(path_key):
            continue

        scene_name = q.parent.name
        map_id = str(rel.parent).replace("/", "_")
        env_candidates = sorted([p for p in q.parent.glob("*.env") if "vizmo" not in p.name.lower()])
        env_text = env_candidates[0].read_text(errors="ignore") if env_candidates else ""
        bounds = _parse_boundary_box(env_text)
        pairs = _parse_query_pairs_from_text(q.read_text(errors="ignore"))
        if not pairs:
            continue
        specs.append(QuerySpec(scenario_name=scene_name, map_id=map_id, pairs=pairs, bounds=bounds))

    if include_flange_variants:
        flange_dir = root / "flange_1.0"
        for tar_path in sorted(flange_dir.glob("flange_*.tar.gz")):
            map_id = tar_path.stem.replace(".tar", "")
            if not include_scene(map_id):
                continue
            with tarfile.open(tar_path, "r:gz") as tf:
                members = {m.name: m for m in tf.getmembers()}
                if "flange.query" not in members:
                    continue
                q_text = tf.extractfile(members["flange.query"]).read().decode("utf-8", errors="ignore")
                e_text = ""
                if "flange.env" in members:
                    e_text = tf.extractfile(members["flange.env"]).read().decode("utf-8", errors="ignore")
                pairs = _parse_query_pairs_from_text(q_text)
                if not pairs:
                    continue
                specs.append(
                    QuerySpec(
                        scenario_name="flange",
                        map_id=map_id,
                        pairs=pairs,
                        bounds=_parse_boundary_box(e_text),
                    )
                )
    return specs


def _infer_bounds_from_pairs(pairs: list[tuple[tuple[float, float, float], tuple[float, float, float]]]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for a, b in pairs:
        xs.extend([float(a[0]), float(b[0])])
        ys.extend([float(a[1]), float(b[1])])
    xmin = min(xs)
    xmax = max(xs)
    ymin = min(ys)
    ymax = max(ys)
    span_x = max(xmax - xmin, 1.0)
    span_y = max(ymax - ymin, 1.0)
    pad_x = 0.45 * span_x
    pad_y = 0.45 * span_y
    return xmin - pad_x, xmax + pad_x, ymin - pad_y, ymax + pad_y


def _world_to_grid_from_bounds(x: float, y: float, bounds: tuple[float, float, float, float], size: int) -> tuple[int, int]:
    xmin, xmax, ymin, ymax = bounds
    sx = max(xmax - xmin, 1e-6)
    sy = max(ymax - ymin, 1e-6)
    u = (x - xmin) / sx
    v = (y - ymin) / sy
    gx = int(np.clip(np.round(u * (size - 1)), 0, size - 1))
    gy = int(np.clip(np.round(v * (size - 1)), 0, size - 1))
    return gx, gy


def _snap_to_free(occ: np.ndarray, gx: int, gy: int) -> tuple[int, int] | None:
    h, w = occ.shape
    gx = int(np.clip(gx, 0, w - 1))
    gy = int(np.clip(gy, 0, h - 1))
    if not occ[gy, gx]:
        return gx, gy

    visited = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    q.append((gx, gy))
    visited[gy, gx] = True
    nbrs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    while q:
        x, y = q.popleft()
        for dx, dy in nbrs:
            nx = x + dx
            ny = y + dy
            if nx < 0 or ny < 0 or nx >= w or ny >= h or visited[ny, nx]:
                continue
            if not occ[ny, nx]:
                return nx, ny
            visited[ny, nx] = True
            q.append((nx, ny))
    return None


def _snap_to_clearance(
    occ: np.ndarray,
    esdf: np.ndarray,
    gx: int,
    gy: int,
    min_clearance: float,
) -> tuple[int, int] | None:
    h, w = occ.shape
    gx = int(np.clip(gx, 0, w - 1))
    gy = int(np.clip(gy, 0, h - 1))
    if (not occ[gy, gx]) and float(esdf[gy, gx]) >= float(min_clearance):
        return gx, gy

    cand = np.argwhere((~occ) & (esdf >= float(min_clearance)))
    if cand.size > 0:
        dx = cand[:, 1].astype(np.float32) - float(gx)
        dy = cand[:, 0].astype(np.float32) - float(gy)
        idx = int(np.argmin(dx * dx + dy * dy))
        yx = cand[idx]
        return int(yx[1]), int(yx[0])

    # Fallback: keep task but still bias toward largest clearance.
    free = np.argwhere(~occ)
    if free.size == 0:
        return None
    best_i = int(np.argmax(esdf[free[:, 0], free[:, 1]]))
    yx = free[best_i]
    return int(yx[1]), int(yx[0])


def _convert_open_ppl_tasks(args: argparse.Namespace) -> dict | None:
    open_root = Path(args.open_ppl_root)
    if not open_root.exists() and not bool(args.no_auto_download):
        open_root = _clone_or_update_repo(args.open_ppl_repo_url, open_root)
    if not open_root.exists():
        return None

    filter_tokens = {t.strip().lower() for t in str(args.scene_filter).split(",") if t.strip()}
    specs = _collect_open_ppl_specs(
        root=open_root,
        include_all_open_scenes=bool(args.include_all_open_scenes),
        scene_filter=filter_tokens,
        include_flange_variants=not bool(args.disable_flange_variants),
    )
    if not specs:
        return None

    train_dir = args.output_root / "train"
    test_dir = args.output_root / "test"
    rng = np.random.default_rng(int(args.seed) + 907)
    train_ratio = float(np.clip(float(args.train_ratio), 0.0, 0.95))

    train_idx = 0
    test_idx = 0
    written = 0
    dropped = 0

    for i_spec, spec in enumerate(specs):
        occ = _generate_open_ppl_template(
            scene_name=spec.scenario_name,
            map_id=spec.map_id,
            size=int(args.map_size),
            seed=int(args.seed) + 1003 + i_spec,
        )
        esdf_map = compute_esdf(occ, resolution=float(args.resolution)).astype(np.float32)
        bounds = spec.bounds if spec.bounds is not None else _infer_bounds_from_pairs(spec.pairs)

        for i_pair, (s_raw, g_raw) in enumerate(spec.pairs):
            sg = _world_to_grid_from_bounds(float(s_raw[0]), float(s_raw[1]), bounds=bounds, size=int(args.map_size))
            gg = _world_to_grid_from_bounds(float(g_raw[0]), float(g_raw[1]), bounds=bounds, size=int(args.map_size))
            s_snap = _snap_to_clearance(occ, esdf_map, sg[0], sg[1], float(args.min_clearance_m))
            g_snap = _snap_to_clearance(occ, esdf_map, gg[0], gg[1], float(args.min_clearance_m))

            if g_snap is None:
                free = np.argwhere(~occ)
                if free.size == 0:
                    dropped += 1
                    continue
                gyx = free[int(rng.integers(0, len(free)))]
                g_snap = (int(gyx[1]), int(gyx[0]))

            goal_xy = _grid_to_world(g_snap[0], g_snap[1], float(args.resolution))
            d2 = compute_2d_dijkstra_field(occ, goal_xy, float(args.resolution))
            reach = np.argwhere((~occ) & np.isfinite(d2) & (d2 > 1e-6))
            if reach.size == 0:
                dropped += 1
                continue

            if s_snap is None or (not np.isfinite(d2[s_snap[1], s_snap[0]])) or s_snap == g_snap:
                # Fallback to reachable cell with best clearance then distance.
                reach_y = reach[:, 0]
                reach_x = reach[:, 1]
                score = esdf_map[reach_y, reach_x] * 10.0 + d2[reach_y, reach_x]
                best_i = int(np.argmax(score))
                s_snap = (int(reach_x[best_i]), int(reach_y[best_i]))

            start_xy = _grid_to_world(s_snap[0], s_snap[1], float(args.resolution))
            start = (float(start_xy[0]), float(start_xy[1]), _wrap_angle(float(s_raw[2])))
            goal = (float(goal_xy[0]), float(goal_xy[1]), _wrap_angle(float(g_raw[2])))

            go_train = (train_ratio > 0.0) and (rng.random() < train_ratio)
            if go_train:
                out = train_dir / f"sample_{train_idx:06d}.npz"
                train_idx += 1
            else:
                out = test_dir / f"sample_{test_idx:06d}.npz"
                test_idx += 1
            _write_sample(
                out_path=out,
                occ=occ,
                start=start,
                goal=goal,
                d2=d2,
                resolution=float(args.resolution),
                scenario=_scenario_from_name(spec.scenario_name),
                map_id=f"{spec.map_id}_q{i_pair:03d}",
            )
            written += 1

    return {
        "source": "open_ppl_env_query_tasks",
        "open_ppl_root": str(open_root),
        "num_specs": len(specs),
        "num_written": written,
        "num_dropped": dropped,
        "train_count": train_idx,
        "test_count": test_idx,
        "scene_filter": sorted(list(filter_tokens)),
        "include_all_open_scenes": bool(args.include_all_open_scenes),
        "include_flange_variants": not bool(args.disable_flange_variants),
        "train_ratio": train_ratio,
    }


def _pick_start_goal(
    occ: np.ndarray,
    resolution: float,
    rng: np.random.Generator,
    min_dist_m: float = 10.0,
) -> tuple[tuple[float, float, float], tuple[float, float, float], np.ndarray] | None:
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


def _clear_split(output_root: Path) -> None:
    ensure_dirs([output_root, output_root / "train", output_root / "test"])
    for p in (output_root / "train").glob("sample_*.npz"):
        p.unlink()
    for p in (output_root / "test").glob("sample_*.npz"):
        p.unlink()


def main() -> None:
    args = parse_args()
    set_seed(int(args.seed))
    _clear_split(args.output_root)

    source_info: dict | None = None
    if not bool(args.synthetic_only):
        source_info = _convert_open_ppl_tasks(args)

    if source_info is None:
        maps: list[tuple[str, np.ndarray]] = []
        raw_used = False
        if args.raw_root is not None and args.raw_root.exists():
            maps = _collect_raw_maps(args.raw_root, out_size=int(args.map_size))
            raw_used = len(maps) > 0
        if not maps:
            maps = _build_synthetic_maps(size=int(args.map_size), seed=int(args.seed))

        rng = np.random.default_rng(int(args.seed) + 123)
        train_target = int(max(args.train_samples, 1))
        test_target = int(max(args.test_samples, 1))
        train_idx = 0
        test_idx = 0

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
            picked = _pick_start_goal(
                occ,
                resolution=float(args.resolution),
                rng=rng,
                min_dist_m=10.0 * float(args.resolution),
            )
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
            raise RuntimeError(
                f"Failed to generate enough samples: train {train_idx}/{train_target}, test {test_idx}/{test_target}"
            )
        source_info = {
            "source": "raw_maps" if raw_used else "synthetic_classic_proxies",
            "raw_root": str(args.raw_root) if args.raw_root is not None else "",
            "train_count": train_idx,
            "test_count": test_idx,
        }

    meta = {
        "name": "parasol_narrow_converted",
        "seed": int(args.seed),
        "resolution": float(args.resolution),
        "map_size": int(args.map_size),
        "conversion": source_info,
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
