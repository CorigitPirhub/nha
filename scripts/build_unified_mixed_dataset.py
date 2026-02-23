from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
import sys

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.esdf import compute_esdf
from utils.common import ensure_dirs, set_seed


def _to_jsonable(x: Any) -> Any:
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, dict):
        return {str(k): _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v) for v in x]
    return x


def _resize_2d(arr: np.ndarray, out_h: int, out_w: int, order: int, cval: float) -> np.ndarray:
    h, w = arr.shape
    if h == out_h and w == out_w:
        return arr.astype(np.float32, copy=True)
    zoom = (float(out_h) / max(h, 1), float(out_w) / max(w, 1))
    return ndimage.zoom(arr.astype(np.float32), zoom=zoom, order=order, mode="constant", cval=float(cval)).astype(np.float32)


def _resize_bool(arr: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    out = _resize_2d(arr.astype(np.float32), out_h, out_w, order=0, cval=1.0)
    return (out > 0.5)


def _resize_chw(arr: np.ndarray, out_h: int, out_w: int, order: int, cval: float) -> np.ndarray:
    if arr.ndim != 3:
        raise ValueError(f"Expected CHW, got shape={arr.shape}")
    c, h, w = arr.shape
    if h == out_h and w == out_w:
        return arr.astype(np.float32, copy=True)
    zoom = (1.0, float(out_h) / max(h, 1), float(out_w) / max(w, 1))
    return ndimage.zoom(arr.astype(np.float32), zoom=zoom, order=order, mode="constant", cval=float(cval)).astype(np.float32)


def _resize_tchw(arr: np.ndarray, out_h: int, out_w: int, order: int, cval: float) -> np.ndarray:
    if arr.ndim != 4:
        raise ValueError(f"Expected TCHW, got shape={arr.shape}")
    t, c, h, w = arr.shape
    if h == out_h and w == out_w:
        return arr.astype(np.float32, copy=True)
    zoom = (1.0, 1.0, float(out_h) / max(h, 1), float(out_w) / max(w, 1))
    return ndimage.zoom(arr.astype(np.float32), zoom=zoom, order=order, mode="constant", cval=float(cval)).astype(np.float32)


def _match_channels(field: np.ndarray, yaw_bins: int) -> np.ndarray:
    if field.ndim != 3:
        raise ValueError(f"Expected 3D field, got shape={field.shape}")
    c = int(field.shape[0])
    if c == yaw_bins:
        return field.astype(np.float32, copy=False)
    if c == 1:
        return np.repeat(field, yaw_bins, axis=0).astype(np.float32)
    idx = (np.floor(np.arange(yaw_bins, dtype=np.float32) * (c / float(yaw_bins))).astype(np.int64)) % c
    return field[idx].astype(np.float32)


def _sample_without_replacement(files: list[Path], count: int, rng: np.random.Generator) -> list[Path]:
    count = int(max(count, 0))
    if count <= 0:
        return []
    if count >= len(files):
        return list(files)
    idx = rng.choice(len(files), size=count, replace=False)
    return [files[int(i)] for i in idx]


def _safe_scalar(arr: Any, default: float) -> float:
    try:
        return float(arr)
    except Exception:
        return float(default)


def _load_npz(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _convert_one(
    src: Path,
    dst: Path,
    out_size: int,
    yaw_bins: int,
    scenario_type: str,
    source_split: str,
) -> dict[str, Any]:
    raw = _load_npz(src)

    occupancy = raw["occupancy"].astype(bool)
    h0, w0 = occupancy.shape
    out_h, out_w = int(out_size), int(out_size)

    resolution = _safe_scalar(raw.get("resolution", DEFAULT_CONFIG.map.resolution), DEFAULT_CONFIG.map.resolution)
    # Preserve physical extent when resizing to a canonical grid size.
    scale_h = float(h0) / max(out_h, 1)
    scale_w = float(w0) / max(out_w, 1)
    resolution_new = float(resolution * 0.5 * (scale_h + scale_w))

    occ = _resize_bool(occupancy, out_h, out_w)
    occ_static = _resize_bool(raw.get("occupancy_static", occupancy), out_h, out_w)

    esdf = compute_esdf(occ, resolution_new)
    fill_value = _safe_scalar(raw.get("fill_value", DEFAULT_CONFIG.dataset.max_teacher_value), DEFAULT_CONFIG.dataset.max_teacher_value)

    teacher_2d_src = raw.get("teacher_2d", raw.get("teacher", None))
    if teacher_2d_src is None:
        yy, xx = np.mgrid[0:h0, 0:w0]
        goal = raw.get("goal", np.array([0.5 * w0 * resolution, 0.5 * h0 * resolution, 0.0], dtype=np.float32)).astype(np.float32)
        wx = (xx + 0.5) * resolution
        wy = (yy + 0.5) * resolution
        teacher_2d_src = np.hypot(wx - float(goal[0]), wy - float(goal[1])).astype(np.float32)
    teacher_2d = _resize_2d(np.asarray(teacher_2d_src, dtype=np.float32), out_h, out_w, order=1, cval=fill_value)
    teacher_2d = np.clip(teacher_2d, 0.0, fill_value).astype(np.float32)

    teacher_3d_src = raw.get("teacher_3d", teacher_2d_src[None, ...] if isinstance(teacher_2d_src, np.ndarray) else teacher_2d[None, ...])
    teacher_3d_src = np.asarray(teacher_3d_src, dtype=np.float32)
    if teacher_3d_src.ndim == 2:
        teacher_3d_src = teacher_3d_src[None, ...]
    teacher_3d_src = _match_channels(teacher_3d_src, yaw_bins=yaw_bins)
    teacher_3d = _resize_chw(teacher_3d_src, out_h, out_w, order=1, cval=fill_value)
    teacher_3d = np.clip(teacher_3d, 0.0, fill_value).astype(np.float32)

    if scenario_type == "standard":
        rs_base_3d = teacher_3d.copy()
        temporal_residual_3d = np.zeros((3, yaw_bins, out_h, out_w), dtype=np.float32)
        dynamic_risk = np.zeros((out_h, out_w), dtype=np.float32)
        dynamic_risk_seq = np.zeros((3, out_h, out_w), dtype=np.float32)
        dynamic_block_threshold = float(raw.get("dynamic_block_threshold", 0.25))
    else:
        rs_src = raw.get("rs_base_3d", teacher_3d_src)
        rs_src = np.asarray(rs_src, dtype=np.float32)
        if rs_src.ndim == 2:
            rs_src = rs_src[None, ...]
        rs_src = _match_channels(rs_src, yaw_bins=yaw_bins)
        rs_base_3d = _resize_chw(rs_src, out_h, out_w, order=1, cval=fill_value)
        rs_base_3d = np.clip(rs_base_3d, 0.0, fill_value).astype(np.float32)

        if "temporal_residual_3d" in raw:
            tmp = np.asarray(raw["temporal_residual_3d"], dtype=np.float32)
            if tmp.ndim == 4:
                if tmp.shape[1] != yaw_bins:
                    remapped = np.zeros((tmp.shape[0], yaw_bins, tmp.shape[2], tmp.shape[3]), dtype=np.float32)
                    for t in range(tmp.shape[0]):
                        remapped[t] = _match_channels(tmp[t], yaw_bins=yaw_bins)
                    tmp = remapped
                temporal_residual_3d = _resize_tchw(tmp, out_h, out_w, order=1, cval=0.0)
            else:
                temporal_residual_3d = np.zeros((3, yaw_bins, out_h, out_w), dtype=np.float32)
        else:
            temporal_residual_3d = np.zeros((3, yaw_bins, out_h, out_w), dtype=np.float32)

        dynamic_risk = _resize_2d(np.asarray(raw.get("dynamic_risk", np.zeros((h0, w0), dtype=np.float32)), dtype=np.float32), out_h, out_w, order=1, cval=0.0)
        if "dynamic_risk_seq" in raw:
            drs = np.asarray(raw["dynamic_risk_seq"], dtype=np.float32)
            if drs.ndim == 3:
                seq = []
                for i in range(min(drs.shape[0], 3)):
                    seq.append(_resize_2d(drs[i], out_h, out_w, order=1, cval=0.0))
                while len(seq) < 3:
                    seq.append(dynamic_risk.copy())
                dynamic_risk_seq = np.stack(seq[:3], axis=0).astype(np.float32)
            else:
                dynamic_risk_seq = np.repeat(dynamic_risk[None, ...], 3, axis=0).astype(np.float32)
        else:
            dynamic_risk_seq = np.repeat(dynamic_risk[None, ...], 3, axis=0).astype(np.float32)
        dynamic_block_threshold = float(raw.get("dynamic_block_threshold", 0.25))

    teacher = teacher_2d.astype(np.float32)
    teacher_2d = teacher_2d.astype(np.float32)

    start = np.asarray(raw.get("start", np.array([resolution_new, resolution_new, 0.0], dtype=np.float32)), dtype=np.float32)
    goal = np.asarray(raw.get("goal", np.array([(out_w - 1) * resolution_new, (out_h - 1) * resolution_new, 0.0], dtype=np.float32)), dtype=np.float32)

    veh = DEFAULT_CONFIG.vehicle
    pl = DEFAULT_CONFIG.planner

    out: dict[str, Any] = {
        "occupancy": occ.astype(np.uint8),
        "occupancy_static": occ_static.astype(np.uint8),
        "dynamic_risk": np.clip(dynamic_risk, 0.0, 1.0).astype(np.float32),
        "dynamic_risk_seq": np.clip(dynamic_risk_seq, 0.0, 1.0).astype(np.float32),
        "dynamic_block_threshold": np.float32(dynamic_block_threshold),
        "esdf": esdf.astype(np.float32),
        "teacher": teacher.astype(np.float32),
        "teacher_2d": teacher_2d.astype(np.float32),
        "teacher_3d": teacher_3d.astype(np.float32),
        "rs_base_3d": rs_base_3d.astype(np.float32),
        "temporal_residual_3d": np.maximum(temporal_residual_3d, 0.0).astype(np.float32),
        "start": start.astype(np.float32),
        "goal": goal.astype(np.float32),
        "resolution": np.float32(resolution_new),
        "fill_value": np.float32(fill_value),
        "scenario": np.asarray(raw.get("scenario", "mixed"), dtype="<U32"),
        "category": np.asarray(raw.get("category", "C" if scenario_type == "hard" else "A"), dtype="<U4"),
        "difficulty": np.asarray(raw.get("difficulty", "hard" if scenario_type == "hard" else "standard"), dtype="<U16"),
        "task_type": np.asarray(raw.get("task_type", "benchmark" if scenario_type == "standard" else "dynamic_avoid"), dtype="<U32"),
        "scenario_type": np.asarray(scenario_type, dtype="<U16"),
        "source_dataset": np.asarray(raw.get("source_dataset", "mix"), dtype="<U16"),
        "source_split": np.asarray(source_split, dtype="<U8"),
        "vehicle_wheel_base": np.float32(_safe_scalar(raw.get("vehicle_wheel_base", veh.wheel_base), veh.wheel_base)),
        "vehicle_track_width": np.float32(_safe_scalar(raw.get("vehicle_track_width", 1.0), 1.0)),
        "vehicle_length": np.float32(_safe_scalar(raw.get("vehicle_length", veh.length), veh.length)),
        "vehicle_width": np.float32(_safe_scalar(raw.get("vehicle_width", veh.width), veh.width)),
        "vehicle_max_steer_deg": np.float32(_safe_scalar(raw.get("vehicle_max_steer_deg", veh.max_steer_deg), veh.max_steer_deg)),
        "vehicle_min_turn_radius": np.float32(_safe_scalar(raw.get("vehicle_min_turn_radius", veh.min_turn_radius), veh.min_turn_radius)),
        "vehicle_load_factor": np.float32(_safe_scalar(raw.get("vehicle_load_factor", 1.0), 1.0)),
        "vehicle_battery": np.float32(_safe_scalar(raw.get("vehicle_battery", 100.0), 100.0)),
        "vehicle_max_speed_scale": np.float32(_safe_scalar(raw.get("vehicle_max_speed_scale", 1.0), 1.0)),
        "vehicle_steer_rate_scale": np.float32(_safe_scalar(raw.get("vehicle_steer_rate_scale", 1.0), 1.0)),
        "planner_step_size": np.float32(_safe_scalar(raw.get("planner_step_size", pl.step_size), pl.step_size)),
        "planner_reverse_penalty": np.float32(_safe_scalar(raw.get("planner_reverse_penalty", pl.reverse_penalty), pl.reverse_penalty)),
        "planner_steer_penalty": np.float32(_safe_scalar(raw.get("planner_steer_penalty", pl.steer_penalty), pl.steer_penalty)),
        "planner_steer_change_penalty": np.float32(_safe_scalar(raw.get("planner_steer_change_penalty", pl.steer_change_penalty), pl.steer_change_penalty)),
    }

    # Keep optional motion metadata if present.
    for key in ["dynamic_tracks", "dynamic_radii_m", "dynamic_active", "dynamic_speed_mps", "dynamic_mode_ids", "goal_sequence"]:
        if key in raw:
            out[key] = np.asarray(raw[key])

    np.savez_compressed(dst, **out)
    return {
        "scenario_type": scenario_type,
        "difficulty": str(out["difficulty"]),
        "task_type": str(out["task_type"]),
        "scenario": str(out["scenario"]),
        "source_dataset": str(out["source_dataset"]),
    }


def _counts_from_ratio(hard_available: int, hard_ratio: float, total_count: int) -> tuple[int, int]:
    r = float(np.clip(hard_ratio, 1e-3, 0.999))
    if int(total_count) > 0:
        total = int(total_count)
        hard = int(round(total * r))
        hard = int(np.clip(hard, 0, hard_available))
        std = max(total - hard, 0)
        return hard, std
    hard = int(max(hard_available, 0))
    std = int(round(hard * (1.0 - r) / r))
    return hard, max(std, 0)


def _list_samples(root: Path) -> list[Path]:
    return sorted(Path(root).glob("sample_*.npz"))


def _write_split(
    split: str,
    out_root: Path,
    hard_files: list[Path],
    std_files: list[Path],
    out_size: int,
    yaw_bins: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    split_dir = out_root / split
    split_dir.mkdir(parents=True, exist_ok=True)
    for p in split_dir.glob("sample_*.npz"):
        p.unlink()

    mixed: list[tuple[Path, str]] = [(p, "hard") for p in hard_files] + [(p, "standard") for p in std_files]
    if mixed:
        order = rng.permutation(len(mixed))
        mixed = [mixed[int(i)] for i in order]

    meta_rows: list[dict[str, Any]] = []
    for i, (src, s_type) in enumerate(mixed):
        dst = split_dir / f"sample_{i:06d}.npz"
        row = _convert_one(src=src, dst=dst, out_size=out_size, yaw_bins=yaw_bins, scenario_type=s_type, source_split=split)
        meta_rows.append(row)
        if (i + 1) % 200 == 0 or (i + 1) == len(mixed):
            print(f"[{split}] converted {i + 1}/{len(mixed)}")

    n = len(meta_rows)
    hard_n = sum(1 for r in meta_rows if r["scenario_type"] == "hard")
    std_n = sum(1 for r in meta_rows if r["scenario_type"] == "standard")
    dyn_n = sum(1 for r in meta_rows if str(r.get("task_type", "")) == "dynamic_avoid")

    return {
        "num_samples": n,
        "hard_samples": hard_n,
        "standard_samples": std_n,
        "hard_ratio": float(hard_n / max(n, 1)),
        "standard_ratio": float(std_n / max(n, 1)),
        "dynamic_avoid_ratio": float(dyn_n / max(n, 1)),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build unified Standard+Hard mixed dataset with canonical size/yaw channels.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--hard-root", type=Path, default=Path("data_hard_dynamic_yaw8m48"))
    p.add_argument("--output-root", type=Path, default=Path("data/unified_standard_hard_mixed"))
    p.add_argument("--out-size", type=int, default=64)
    p.add_argument("--yaw-bins", type=int, default=8)
    p.add_argument("--hard-ratio", type=float, default=0.6)
    p.add_argument("--train-total", type=int, default=0, help="Total mixed train samples (0=auto from hard split + ratio).")
    p.add_argument("--val-total", type=int, default=0, help="Total mixed val samples (0=auto from hard split + ratio).")
    p.add_argument("--test-total", type=int, default=0, help="Total mixed test samples (0=auto from hard split + ratio).")
    p.add_argument("--seed", type=int, default=7)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(int(args.seed))
    rng = np.random.default_rng(int(args.seed))

    mp_train = _list_samples(args.benchmark_root / "mp" / "train")
    csm_train = _list_samples(args.benchmark_root / "csm" / "train")
    std_train_pool = mp_train + csm_train
    if not std_train_pool:
        raise RuntimeError("No standard train samples found under benchmark root.")

    mp_test = _list_samples(args.benchmark_root / "mp" / "test")
    csm_test = _list_samples(args.benchmark_root / "csm" / "test")
    std_test_pool = mp_test + csm_test
    if not std_test_pool:
        raise RuntimeError("No standard test samples found under benchmark root.")

    hard_train_pool = _list_samples(args.hard_root / "train")
    hard_val_pool = _list_samples(args.hard_root / "val")
    hard_test_pool = _list_samples(args.hard_root / "test")
    if not hard_train_pool or not hard_val_pool or not hard_test_pool:
        raise RuntimeError("Hard dataset splits are missing under hard root.")

    train_hard_n, train_std_n = _counts_from_ratio(len(hard_train_pool), float(args.hard_ratio), int(args.train_total))
    val_hard_n, val_std_n = _counts_from_ratio(len(hard_val_pool), float(args.hard_ratio), int(args.val_total))
    test_hard_n, test_std_n = _counts_from_ratio(len(hard_test_pool), float(args.hard_ratio), int(args.test_total))

    hard_train_sel = _sample_without_replacement(hard_train_pool, train_hard_n, rng)
    hard_val_sel = _sample_without_replacement(hard_val_pool, val_hard_n, rng)
    hard_test_sel = _sample_without_replacement(hard_test_pool, test_hard_n, rng)

    # Keep standard train/val disjoint by splitting one common pool.
    std_train_val_need = int(train_std_n + val_std_n)
    std_train_val_sel = _sample_without_replacement(std_train_pool, std_train_val_need, rng)
    std_train_sel = std_train_val_sel[:train_std_n]
    std_val_sel = std_train_val_sel[train_std_n : train_std_n + val_std_n]
    if len(std_val_sel) < val_std_n:
        extra_need = val_std_n - len(std_val_sel)
        used = {p.resolve() for p in std_train_val_sel}
        extra_pool = [p for p in std_train_pool if p.resolve() not in used]
        std_val_sel += _sample_without_replacement(extra_pool, extra_need, rng)

    std_test_sel = _sample_without_replacement(std_test_pool, test_std_n, rng)

    ensure_dirs([args.output_root, args.output_root / "train", args.output_root / "val", args.output_root / "test"])

    train_meta = _write_split(
        split="train",
        out_root=args.output_root,
        hard_files=hard_train_sel,
        std_files=std_train_sel,
        out_size=int(args.out_size),
        yaw_bins=int(args.yaw_bins),
        rng=rng,
    )
    val_meta = _write_split(
        split="val",
        out_root=args.output_root,
        hard_files=hard_val_sel,
        std_files=std_val_sel,
        out_size=int(args.out_size),
        yaw_bins=int(args.yaw_bins),
        rng=rng,
    )
    test_meta = _write_split(
        split="test",
        out_root=args.output_root,
        hard_files=hard_test_sel,
        std_files=std_test_sel,
        out_size=int(args.out_size),
        yaw_bins=int(args.yaw_bins),
        rng=rng,
    )

    meta = {
        "seed": int(args.seed),
        "output_root": str(args.output_root),
        "benchmark_root": str(args.benchmark_root),
        "hard_root": str(args.hard_root),
        "out_size": int(args.out_size),
        "yaw_bins": int(args.yaw_bins),
        "hard_ratio_target": float(args.hard_ratio),
        "teacher_mode": "reeds_shepp_consistent",
        "teacher_rs_backend": DEFAULT_CONFIG.dataset.teacher_rs_backend,
        "teacher_rs_step_size": float(DEFAULT_CONFIG.dataset.teacher_rs_step_size),
        "include_rs_base": True,
        "splits": {
            "train": train_meta,
            "val": val_meta,
            "test": test_meta,
        },
        "selected_counts": {
            "train": {"hard": len(hard_train_sel), "standard": len(std_train_sel)},
            "val": {"hard": len(hard_val_sel), "standard": len(std_val_sel)},
            "test": {"hard": len(hard_test_sel), "standard": len(std_test_sel)},
        },
        "config_snapshot": _to_jsonable(asdict(DEFAULT_CONFIG)),
    }
    (args.output_root / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("Saved unified dataset:")
    print(f"- {args.output_root}")
    print(json.dumps(meta["splits"], indent=2))


if __name__ == "__main__":
    main()
