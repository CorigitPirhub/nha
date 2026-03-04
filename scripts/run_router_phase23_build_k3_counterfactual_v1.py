from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from network.inference import NeuralHeuristicPredictor
from scripts.evaluate_baselines import _astar_grid, _euclidean_field, _path_length, _resolve_2d_heuristic, _world_to_grid


@dataclass(frozen=True)
class MidArmResult:
    success: bool
    expansions: float
    runtime_ms: float
    infer_ms: float
    search_ms: float
    path_len: float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase23 builder: extend frozen fast/slow counterfactual tables to K=3 arms by adding a configurable `mid` arm."
    )
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--split", type=str, default="test", choices=["calib", "test"])
    p.add_argument(
        "--base-parquet",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/common/router_counterfactual_test.parquet"),
        help="Frozen fast/slow counterfactual table (Phase9 bench).",
    )
    p.add_argument("--mid-method", type=str, default="midnet", choices=["midnet", "crop_raw", "crop_padded", "lowres"])
    p.add_argument(
        "--mid-checkpoint",
        type=Path,
        default=Path("outputs/router_phase23_midnet_tinyunet_b64_ctx_v1/checkpoints/heuristic_net.pt"),
        help="Checkpoint used for midnet mid arm.",
    )
    p.add_argument(
        "--slow-checkpoint",
        type=Path,
        default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"),
        help="Checkpoint used when mid-method is crop/lowres based on the slow model.",
    )
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--standard-base-mode", type=str, default="euclidean", choices=["euclidean", "rs"])
    p.add_argument("--grid-max-expansions", type=int, default=50000)

    # Crop mid.
    p.add_argument("--crop-margin-cells", type=int, default=8)
    p.add_argument("--crop-pad-multiple", type=int, default=32)

    # Low-res mid.
    p.add_argument("--lowres-factor", type=int, default=2)

    p.add_argument("--max-cases", type=int, default=-1, help="If >0, subsample cases for a quick build.")
    p.add_argument("--seed", type=int, default=7)

    p.add_argument("--out-parquet", type=Path, default=Path("outputs/router_phase23_portfolio_v1/common/router_counterfactual_test_k3.parquet"))
    p.add_argument("--out-report", type=Path, default=Path("outputs/router_phase23_portfolio_v1/common/router_counterfactual_test_k3_report.json"))
    return p.parse_args()


def _downsample_occupancy_or(occ: np.ndarray, factor: int) -> np.ndarray:
    occ = occ.astype(bool)
    f = int(max(factor, 1))
    if f <= 1:
        return occ
    h, w = occ.shape
    pad_h = (-h) % f
    pad_w = (-w) % f
    if pad_h or pad_w:
        occ = np.pad(occ, ((0, pad_h), (0, pad_w)), mode="constant", constant_values=True)
    h2, w2 = occ.shape
    occ4 = occ.reshape(h2 // f, f, w2 // f, f)
    return occ4.max(axis=(1, 3)).astype(bool)


def _upsample_to_shape(field: np.ndarray, shape_hw: tuple[int, int]) -> np.ndarray:
    h, w = int(shape_hw[0]), int(shape_hw[1])
    if field.ndim != 2:
        raise ValueError(f"Expected 2D field, got shape {field.shape}")
    h0, w0 = field.shape
    if (h0 == h) and (w0 == w):
        return field.astype(np.float32)
    zy = float(h / max(h0, 1))
    zx = float(w / max(w0, 1))
    up = ndimage.zoom(field.astype(np.float32), zoom=(zy, zx), order=1)
    up = up[:h, :w]
    if up.shape != (h, w):
        out = np.full((h, w), 1e6, dtype=np.float32)
        out[: up.shape[0], : up.shape[1]] = up
        return out
    return up.astype(np.float32)


def _maybe_base_override(
    *,
    predictor: NeuralHeuristicPredictor,
    occupancy: np.ndarray,
    goal_xy: tuple[float, float],
    resolution: float,
    standard_base_mode: str,
) -> np.ndarray | None:
    if predictor.prediction_mode != "residual":
        return None
    if str(standard_base_mode).lower() != "euclidean":
        return None
    return _euclidean_field(occupancy=occupancy, goal_xy=goal_xy, resolution=resolution, fill_value=1e6)


def _crop_bbox(
    *,
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    margin_cells: int,
    pad_multiple: int,
) -> tuple[int, int, int, int]:
    h, w = occupancy.shape
    sx, sy = _world_to_grid(float(start_xy[0]), float(start_xy[1]), float(resolution), w, h)
    gx, gy = _world_to_grid(float(goal_xy[0]), float(goal_xy[1]), float(resolution), w, h)

    m = int(max(margin_cells, 0))
    x0 = max(min(sx, gx) - m, 0)
    x1 = min(max(sx, gx) + m + 1, w)
    y0 = max(min(sy, gy) - m, 0)
    y1 = min(max(sy, gy) + m + 1, h)

    pad = int(max(pad_multiple, 0))
    if pad > 0:
        cur_h = int(y1 - y0)
        cur_w = int(x1 - x0)
        target_h = int(min(h, int(math.ceil(cur_h / pad) * pad)))
        target_w = int(min(w, int(math.ceil(cur_w / pad) * pad)))
        cy = int((y0 + y1) // 2)
        cx = int((x0 + x1) // 2)
        y0 = int(np.clip(cy - target_h // 2, 0, h - target_h))
        y1 = int(y0 + target_h)
        x0 = int(np.clip(cx - target_w // 2, 0, w - target_w))
        x1 = int(x0 + target_w)
    return int(x0), int(x1), int(y0), int(y1)


def _astar_hybrid_crop(
    *,
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    max_expansions: int,
    crop_heuristic: np.ndarray,
    crop_bbox: tuple[int, int, int, int],
) -> dict:
    # Reuse the A* implementation by constructing a full map heuristic:
    # outside crop => Euclidean; inside crop => neural. This is fast enough for our grid sizes.
    x0, x1, y0, y1 = crop_bbox
    h_full = _euclidean_field(occupancy=occupancy, goal_xy=goal_xy, resolution=resolution, fill_value=1e6)
    h_full[y0:y1, x0:x1] = crop_heuristic.astype(np.float32)
    h_full = _resolve_2d_heuristic(h_full, occupancy)
    return _astar_grid(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        max_expansions=int(max_expansions),
        heuristic_map=h_full,
        heuristic_weight=1.0,
        record_expanded=False,
    )


def _run_midnet(
    *,
    predictor: NeuralHeuristicPredictor,
    occupancy: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    max_expansions: int,
    standard_base_mode: str,
) -> MidArmResult:
    t0 = time.perf_counter()
    infer0 = time.perf_counter()
    base_override = _maybe_base_override(
        predictor=predictor,
        occupancy=occupancy,
        goal_xy=(goal[0], goal[1]),
        resolution=resolution,
        standard_base_mode=standard_base_mode,
    )
    pred = predictor.predict_field(
        occupancy=occupancy,
        esdf=np.zeros_like(occupancy, dtype=np.float32),
        start=start,
        goal=goal,
        resolution=resolution,
        base_field_override=base_override,
    )
    infer_ms = float((time.perf_counter() - infer0) * 1000.0)
    h = _resolve_2d_heuristic(pred, occupancy)
    res = _astar_grid(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=(start[0], start[1]),
        goal_xy=(goal[0], goal[1]),
        max_expansions=int(max_expansions),
        heuristic_map=h,
        heuristic_weight=1.0,
        record_expanded=False,
    )
    total_ms = float((time.perf_counter() - t0) * 1000.0)
    return MidArmResult(
        success=bool(res["success"]),
        expansions=float(res["expansions"]),
        runtime_ms=total_ms,
        infer_ms=infer_ms,
        search_ms=float(res["runtime_ms"]),
        path_len=float(_path_length(res.get("path", []))),
    )


def _run_mid_crop(
    *,
    predictor: NeuralHeuristicPredictor,
    occupancy: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    max_expansions: int,
    standard_base_mode: str,
    margin_cells: int,
    pad_multiple: int,
) -> MidArmResult:
    t0 = time.perf_counter()
    bbox = _crop_bbox(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=(start[0], start[1]),
        goal_xy=(goal[0], goal[1]),
        margin_cells=margin_cells,
        pad_multiple=pad_multiple,
    )
    x0, x1, y0, y1 = bbox
    occ_crop = occupancy[y0:y1, x0:x1].astype(bool)
    start_crop = (float(start[0]) - float(x0) * float(resolution), float(start[1]) - float(y0) * float(resolution), float(start[2]))
    goal_crop = (float(goal[0]) - float(x0) * float(resolution), float(goal[1]) - float(y0) * float(resolution), float(goal[2]))

    infer0 = time.perf_counter()
    base_override = _maybe_base_override(
        predictor=predictor,
        occupancy=occ_crop,
        goal_xy=(goal_crop[0], goal_crop[1]),
        resolution=resolution,
        standard_base_mode=standard_base_mode,
    )
    pred = predictor.predict_field(
        occupancy=occ_crop,
        esdf=np.zeros_like(occ_crop, dtype=np.float32),
        start=start_crop,
        goal=goal_crop,
        resolution=resolution,
        base_field_override=base_override,
    )
    infer_ms = float((time.perf_counter() - infer0) * 1000.0)
    h_crop = _resolve_2d_heuristic(pred, occ_crop)
    res = _astar_hybrid_crop(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=(start[0], start[1]),
        goal_xy=(goal[0], goal[1]),
        max_expansions=int(max_expansions),
        crop_heuristic=h_crop,
        crop_bbox=bbox,
    )
    total_ms = float((time.perf_counter() - t0) * 1000.0)
    return MidArmResult(
        success=bool(res["success"]),
        expansions=float(res["expansions"]),
        runtime_ms=total_ms,
        infer_ms=infer_ms,
        search_ms=float(res["runtime_ms"]),
        path_len=float(_path_length(res.get("path", []))),
    )


def _run_mid_lowres(
    *,
    predictor: NeuralHeuristicPredictor,
    occupancy: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    max_expansions: int,
    standard_base_mode: str,
    factor: int,
) -> MidArmResult:
    t0 = time.perf_counter()
    f = int(max(factor, 1))
    occ_lr = _downsample_occupancy_or(occupancy, f)
    res_lr = float(resolution) * float(f)

    infer0 = time.perf_counter()
    base_override = _maybe_base_override(
        predictor=predictor,
        occupancy=occ_lr,
        goal_xy=(goal[0], goal[1]),
        resolution=res_lr,
        standard_base_mode=standard_base_mode,
    )
    pred_lr = predictor.predict_field(
        occupancy=occ_lr,
        esdf=np.zeros_like(occ_lr, dtype=np.float32),
        start=start,
        goal=goal,
        resolution=res_lr,
        base_field_override=base_override,
    )
    infer_ms = float((time.perf_counter() - infer0) * 1000.0)
    h_lr = _resolve_2d_heuristic(pred_lr, occ_lr)
    h_full = _upsample_to_shape(h_lr, occupancy.shape)
    h_full = _resolve_2d_heuristic(h_full, occupancy)

    res = _astar_grid(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=(start[0], start[1]),
        goal_xy=(goal[0], goal[1]),
        max_expansions=int(max_expansions),
        heuristic_map=h_full,
        heuristic_weight=1.0,
        record_expanded=False,
    )
    total_ms = float((time.perf_counter() - t0) * 1000.0)
    return MidArmResult(
        success=bool(res["success"]),
        expansions=float(res["expansions"]),
        runtime_ms=total_ms,
        infer_ms=infer_ms,
        search_ms=float(res["runtime_ms"]),
        path_len=float(_path_length(res.get("path", []))),
    )


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    base = pd.read_parquet(args.base_parquet).copy()
    if base.empty:
        raise RuntimeError(f"Empty base parquet: {args.base_parquet}")

    # Optional subsample.
    if int(args.max_cases) > 0 and int(args.max_cases) < len(base):
        rng = np.random.default_rng(int(args.seed))
        pick = rng.choice(base["sample_name"].astype(str).to_numpy(), size=int(args.max_cases), replace=False)
        base = base[base["sample_name"].astype(str).isin(set(str(x) for x in pick.tolist()))].copy()
        base = base.sort_values("sample_name").reset_index(drop=True)

    mid_method = str(args.mid_method).lower()
    if mid_method == "midnet":
        predictor = NeuralHeuristicPredictor(args.mid_checkpoint, device=str(args.device))
        mid_tag = f"midnet::{Path(args.mid_checkpoint).name}"
    else:
        predictor = NeuralHeuristicPredictor(args.slow_checkpoint, device=str(args.device))
        mid_tag = f"{mid_method}::{Path(args.slow_checkpoint).name}"

    rows: list[dict] = []
    for i, r in enumerate(base.itertuples(index=False), start=1):
        sample_name = str(getattr(r, "sample_name"))
        p = args.dataset_root / str(args.split) / sample_name
        if not p.exists():
            raise FileNotFoundError(p)
        s = load_grid_sample(p)
        start = (float(s.start[0]), float(s.start[1]), float(s.start[2]))
        goal = (float(s.goal[0]), float(s.goal[1]), float(s.goal[2]))

        if mid_method == "midnet":
            mid = _run_midnet(
                predictor=predictor,
                occupancy=s.occupancy,
                resolution=float(s.resolution),
                start=start,
                goal=goal,
                max_expansions=int(args.grid_max_expansions),
                standard_base_mode=str(args.standard_base_mode),
            )
        elif mid_method == "crop_raw":
            mid = _run_mid_crop(
                predictor=predictor,
                occupancy=s.occupancy,
                resolution=float(s.resolution),
                start=start,
                goal=goal,
                max_expansions=int(args.grid_max_expansions),
                standard_base_mode=str(args.standard_base_mode),
                margin_cells=int(args.crop_margin_cells),
                pad_multiple=0,
            )
        elif mid_method == "crop_padded":
            mid = _run_mid_crop(
                predictor=predictor,
                occupancy=s.occupancy,
                resolution=float(s.resolution),
                start=start,
                goal=goal,
                max_expansions=int(args.grid_max_expansions),
                standard_base_mode=str(args.standard_base_mode),
                margin_cells=int(args.crop_margin_cells),
                pad_multiple=int(args.crop_pad_multiple),
            )
        elif mid_method == "lowres":
            mid = _run_mid_lowres(
                predictor=predictor,
                occupancy=s.occupancy,
                resolution=float(s.resolution),
                start=start,
                goal=goal,
                max_expansions=int(args.grid_max_expansions),
                standard_base_mode=str(args.standard_base_mode),
                factor=int(args.lowres_factor),
            )
        else:
            raise ValueError(f"Unknown mid_method: {mid_method}")

        rows.append(
            {
                "sample_name": sample_name,
                "success_mid": bool(mid.success),
                "L_mid": float(mid.expansions),
                "T_mid_ms": float(mid.runtime_ms),
                "infer_mid_ms": float(mid.infer_ms),
                "search_mid_ms": float(mid.search_ms),
                "path_len_mid": float(mid.path_len),
            }
        )
        if i % 200 == 0 or i == len(base):
            print(f"[phase23-build-k3] {mid_method} processed {i}/{len(base)}")

    mid_df = pd.DataFrame(rows)
    merged = base.merge(mid_df, on="sample_name", how="inner")
    if len(merged) != len(base):
        raise RuntimeError(f"Mid merge mismatch: {len(merged)} vs {len(base)}")

    # Derived convenience columns.
    l_slow = merged["L_slow"].to_numpy(dtype=np.float64)
    merged["q_rel_mid"] = (merged["L_mid"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)
    merged["c_mid_ms"] = merged["T_slow_ms"].to_numpy(dtype=np.float64) - merged["T_mid_ms"].to_numpy(dtype=np.float64)

    args.out_parquet.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(args.out_parquet, index=False)

    miss = int(merged[["L_mid", "T_mid_ms", "q_rel_mid"]].isna().sum().sum())
    stats = {
        "version": "router_phase23_counterfactual_k3_v1",
        "mid_method": mid_method,
        "mid_tag": mid_tag,
        "dataset_root": str(args.dataset_root.resolve()),
        "split": str(args.split),
        "base_parquet": str(args.base_parquet),
        "out_parquet": str(args.out_parquet),
        "num_cases": int(len(merged)),
        "missing_required_values_mid": int(miss),
        "aggregate": {
            "mean_T_fast_ms": float(merged["T_fast_ms"].mean()),
            "mean_T_mid_ms": float(merged["T_mid_ms"].mean()),
            "mean_T_slow_ms": float(merged["T_slow_ms"].mean()),
            "mean_q_rel_fast": float(merged["q_rel"].mean()),
            "mean_q_rel_mid": float(merged["q_rel_mid"].mean()),
            "vio_rate_fast": float(np.mean((merged["q_rel"].to_numpy(dtype=np.float64) > 0.015).astype(np.float64))),
            "vio_rate_mid": float(np.mean((merged["q_rel_mid"].to_numpy(dtype=np.float64) > 0.015).astype(np.float64))),
        },
        "runtime_s": float(time.perf_counter() - t0),
    }
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[phase23-build-k3] wrote: {args.out_parquet}")


if __name__ == "__main__":
    main()

