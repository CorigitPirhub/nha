from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from network.inference import NeuralHeuristicPredictor
from utils.common import ensure_dirs, set_seed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze neural heuristic prediction error against teacher.")
    p.add_argument("--data", type=Path, default=Path("data_benchmark/test"))
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/heuristic_net.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    p.add_argument("--hist-out", type=Path, default=Path("outputs/figures/error_histogram.png"))
    p.add_argument("--json-out", type=Path, default=Path("outputs/logs/error_analysis.json"))
    return p.parse_args()


def _resample_yaw_channels(field: np.ndarray, out_bins: int) -> np.ndarray:
    in_bins = int(field.shape[0])
    if in_bins == out_bins:
        return field
    src = np.arange(in_bins, dtype=np.float32)
    dst = (np.arange(out_bins, dtype=np.float32) + 0.5) * in_bins / out_bins - 0.5
    floor = np.floor(dst).astype(np.int32) % in_bins
    ceil = (floor + 1) % in_bins
    w = dst - np.floor(dst)
    return (1.0 - w)[:, None, None] * field[floor] + w[:, None, None] * field[ceil]


def _teacher_match(pred: np.ndarray, sample: np.lib.npyio.NpzFile) -> np.ndarray:
    if "teacher_3d" in sample:
        gt = sample["teacher_3d"].astype(np.float32)
    else:
        gt2 = sample["teacher"].astype(np.float32)
        gt = gt2[None, ...]

    if pred.ndim == 2:
        return gt[0] if gt.ndim == 3 else gt

    if gt.ndim == 2:
        gt = gt[None, ...]
    if pred.shape[0] != gt.shape[0]:
        gt = _resample_yaw_channels(gt, pred.shape[0]).astype(np.float32)
    return gt


def _mask_valid(occupancy: np.ndarray, teacher: np.ndarray, fill_value: float) -> np.ndarray:
    if teacher.ndim == 2:
        base = (~occupancy) & np.isfinite(teacher) & (teacher < 0.95 * fill_value)
        return base

    base = (~occupancy) & np.isfinite(teacher[0]) & (teacher[0] < 0.95 * fill_value)
    return np.broadcast_to(base[None, ...], teacher.shape)


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    set_seed(args.seed)
    ensure_dirs([args.hist_out.parent, args.json_out.parent])

    files = sorted(args.data.glob("*.npz"))
    if not files:
        raise RuntimeError(f"No npz samples found under {args.data}")

    rng = np.random.default_rng(args.seed)
    n = int(np.clip(args.samples, 1, len(files)))
    pick = rng.choice(len(files), size=n, replace=False)
    picked_files = [files[int(i)] for i in pick]

    predictor = NeuralHeuristicPredictor(args.checkpoint, device=args.device, gaussian_sigma=cfg.dataset.gaussian_sigma)

    all_err = []
    near_err = []
    far_err = []
    per_case = []

    for p in picked_files:
        with np.load(p, allow_pickle=False) as sample:
            occupancy = sample["occupancy"].astype(bool)
            esdf = sample["esdf"].astype(np.float32)
            start = tuple(float(v) for v in sample["start"])
            goal = tuple(float(v) for v in sample["goal"])
            teacher_2d = sample["teacher_2d"].astype(np.float32) if "teacher_2d" in sample else sample["teacher"].astype(np.float32)
            fill_value = float(sample["fill_value"]) if "fill_value" in sample else cfg.dataset.max_teacher_value
            scenario = str(sample["scenario"]) if "scenario" in sample else "unknown"

            pred = predictor.predict_field(occupancy, esdf, start, goal, resolution=cfg.map.resolution)
            gt = _teacher_match(pred, sample)

        valid = _mask_valid(occupancy, gt, fill_value)
        err = (pred - gt)[valid]
        if err.size == 0:
            continue

        all_err.append(err.astype(np.float64))
        case_mae = float(np.mean(np.abs(err)))
        case_rmse = float(np.sqrt(np.mean(err**2)))
        case_bias = float(np.mean(err))
        case_under = float(np.mean(err < 0.0))

        if gt.ndim == 3:
            near_mask_base = (teacher_2d <= 6.0) & (~occupancy) & np.isfinite(teacher_2d) & (teacher_2d < 0.95 * fill_value)
            far_mask_base = (teacher_2d > 6.0) & (~occupancy) & np.isfinite(teacher_2d) & (teacher_2d < 0.95 * fill_value)
            near_mask = np.broadcast_to(near_mask_base[None, ...], gt.shape) & valid
            far_mask = np.broadcast_to(far_mask_base[None, ...], gt.shape) & valid
        else:
            near_mask = (teacher_2d <= 6.0) & valid
            far_mask = (teacher_2d > 6.0) & valid

        if np.any(near_mask):
            near_err.append((pred - gt)[near_mask].astype(np.float64))
        if np.any(far_mask):
            far_err.append((pred - gt)[far_mask].astype(np.float64))

        per_case.append(
            {
                "file": str(p),
                "scenario": scenario,
                "mae": case_mae,
                "rmse": case_rmse,
                "bias": case_bias,
                "under_ratio": case_under,
            }
        )

    if not all_err:
        raise RuntimeError("No valid error samples collected; check mask/data.")

    err_all = np.concatenate(all_err, axis=0)
    err_near = np.concatenate(near_err, axis=0) if near_err else np.array([], dtype=np.float64)
    err_far = np.concatenate(far_err, axis=0) if far_err else np.array([], dtype=np.float64)

    def _stats(e: np.ndarray) -> dict:
        if e.size == 0:
            return {
                "num": 0,
                "mae": float("nan"),
                "rmse": float("nan"),
                "bias": float("nan"),
                "under_ratio": float("nan"),
                "q10": float("nan"),
                "q50": float("nan"),
                "q90": float("nan"),
            }
        return {
            "num": int(e.size),
            "mae": float(np.mean(np.abs(e))),
            "rmse": float(np.sqrt(np.mean(e**2))),
            "bias": float(np.mean(e)),
            "under_ratio": float(np.mean(e < 0.0)),
            "q10": float(np.quantile(e, 0.10)),
            "q50": float(np.quantile(e, 0.50)),
            "q90": float(np.quantile(e, 0.90)),
        }

    report = {
        "num_files_total": len(files),
        "num_files_sampled": len(picked_files),
        "checkpoint": str(args.checkpoint),
        "dataset": str(args.data),
        "overall": _stats(err_all),
        "near_goal_d<=6m": _stats(err_near),
        "far_goal_d>6m": _stats(err_far),
        "per_case": per_case,
    }

    fig = plt.figure(figsize=(8, 4.2), constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.hist(err_all, bins=80, color="#2d6cdf", alpha=0.8, edgecolor="white", linewidth=0.2)
    ax.axvline(0.0, color="black", linestyle="--", linewidth=1.0)
    ax.set_title("Prediction Error Distribution (h_pred - h_teacher)")
    ax.set_xlabel("Error (meters)")
    ax.set_ylabel("Count")
    fig.savefig(args.hist_out, dpi=160)
    plt.close(fig)

    with args.json_out.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    o = report["overall"]
    print("| metric | value |")
    print("|---|---:|")
    print(f"| sampled files | {len(picked_files)} |")
    print(f"| MAE (m) | {o['mae']:.4f} |")
    print(f"| RMSE (m) | {o['rmse']:.4f} |")
    print(f"| Bias mean(pred-gt) (m) | {o['bias']:.4f} |")
    print(f"| Underestimation ratio (pred<gt) | {100.0 * o['under_ratio']:.2f}% |")
    print(f"Histogram: {args.hist_out}")
    print(f"JSON report: {args.json_out}")


if __name__ == "__main__":
    main()
