from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.scenario_generator import build_generalization_dataset
from network.inference import NeuralHeuristicPredictor
from utils.common import ensure_dirs, set_seed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Diagnose hard-scene residual quality on narrow/deadend/maze cases")
    p.add_argument("--dataset-root", type=Path, default=Path("data/diagnostics/hard_residual"))
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/heuristic_net_hard_optimized.pt"))
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--num-cases", type=int, default=50)
    p.add_argument("--vis-cases", type=int, default=8)
    p.add_argument("--skip-generation", action="store_true")
    p.add_argument("--report-path", type=Path, default=Path("outputs/paper/hard_residual_diagnosis.md"))
    p.add_argument("--json-path", type=Path, default=Path("outputs/paper/logs/hard_residual_diagnosis.json"))
    p.add_argument("--fig-dir", type=Path, default=Path("outputs/paper/figures/hard_residual"))
    return p.parse_args()


def _resample_yaw_channels(field: np.ndarray, out_bins: int) -> np.ndarray:
    if field.ndim == 2:
        return np.repeat(field[None, ...], out_bins, axis=0).astype(np.float32)
    in_bins = int(field.shape[0])
    if in_bins == out_bins:
        return field.astype(np.float32)
    src = np.arange(in_bins, dtype=np.float32)
    dst = (np.arange(out_bins, dtype=np.float32) + 0.5) * in_bins / max(out_bins, 1) - 0.5
    floor = np.floor(dst).astype(np.int32) % in_bins
    ceil = (floor + 1) % in_bins
    w = dst - np.floor(dst)
    return ((1.0 - w)[:, None, None] * field[floor] + w[:, None, None] * field[ceil]).astype(np.float32)


def _build_diagnostic_dataset(args: argparse.Namespace) -> dict:
    cfg = DEFAULT_CONFIG
    map_cfg = replace(cfg.map)
    ds_cfg = replace(cfg.dataset)
    planner_cfg = replace(cfg.planner)
    ds_cfg.teacher_mode = "hybrid_rs_consistent_esdf"
    ds_cfg.teacher_yaw_bins = 8
    ds_cfg.teacher_rs_backend = "approx"
    ds_cfg.teacher_rs_step_size = 1.0
    ds_cfg.hybrid_obstacle_alpha = 0.15
    ds_cfg.hybrid_obstacle_threshold_m = 1.6

    return build_generalization_dataset(
        output_root=args.dataset_root,
        train_count=int(args.num_cases),
        val_count=0,
        test_count=0,
        seed=int(args.seed),
        map_cfg=map_cfg,
        ds_cfg=ds_cfg,
        planner_cfg=planner_cfg,
        dynamic_horizon=24,
        dynamic_dt=0.45,
        use_augmentation=False,
        include_rs_base=True,
        difficulty_filter=("hard",),
        template_filter=("narrow_passage", "maze_single", "deadend_labyrinth"),
        task_filter=("narrow_passage", "deadend_reverse", "dynamic_avoid"),
        distribution_filter=("cluster", "along_path", "random"),
    )


def _finite_mean(arr: np.ndarray) -> float:
    v = arr[np.isfinite(arr)]
    if v.size == 0:
        return float("nan")
    return float(np.mean(v))


def _finite_rmse(arr: np.ndarray) -> float:
    v = arr[np.isfinite(arr)]
    if v.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(v**2)))


def _norm_to_u8(v: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        return np.zeros(v.shape, dtype=np.uint8)
    t = np.clip((v - vmin) / (vmax - vmin), 0.0, 1.0)
    return (255.0 * t).astype(np.uint8)


def _err_to_rgb(err: np.ndarray, lim: float) -> np.ndarray:
    lim = float(max(lim, 1e-6))
    z = np.clip(err / lim, -1.0, 1.0)
    r = (np.clip(z, 0.0, 1.0) * 255.0).astype(np.uint8)
    b = (np.clip(-z, 0.0, 1.0) * 255.0).astype(np.uint8)
    g = ((1.0 - np.abs(z)) * 170.0).astype(np.uint8)
    return np.stack([r, g, b], axis=-1)


def _save_case_figure(
    out_path: Path,
    occupancy: np.ndarray,
    teacher_res_2d: np.ndarray,
    pred_res_2d: np.ndarray,
    err_2d: np.ndarray,
    title: str,
) -> None:
    occ_img = np.where(occupancy, 0, 255).astype(np.uint8)
    vmax = float(np.nanpercentile(np.concatenate([teacher_res_2d[~occupancy], pred_res_2d[~occupancy]]), 95)) if np.any(~occupancy) else 1.0
    vmax = float(max(vmax, 1.0))
    teacher_u8 = _norm_to_u8(teacher_res_2d, 0.0, vmax)
    pred_u8 = _norm_to_u8(pred_res_2d, 0.0, vmax)
    err_rgb = _err_to_rgb(err_2d, lim=float(max(np.nanpercentile(np.abs(err_2d[~occupancy]), 95), 1.0)) if np.any(~occupancy) else 1.0)

    occ_rgb = np.stack([occ_img, occ_img, occ_img], axis=-1)
    teacher_rgb = np.stack([teacher_u8, teacher_u8, teacher_u8], axis=-1)
    pred_rgb = np.stack([pred_u8, pred_u8, pred_u8], axis=-1)

    pad = 6
    h, w = occupancy.shape
    canvas = np.full((h + 28, w * 4 + pad * 5, 3), 255, dtype=np.uint8)

    def put(panel: np.ndarray, k: int) -> None:
        x0 = pad + k * (w + pad)
        canvas[22 : 22 + h, x0 : x0 + w] = panel

    put(occ_rgb, 0)
    put(teacher_rgb, 1)
    put(pred_rgb, 2)
    put(err_rgb, 3)

    img = Image.fromarray(canvas, mode="RGB")
    draw = ImageDraw.Draw(img)
    draw.text((6, 4), title, fill=(0, 0, 0))
    labels = ["occ", "teacher_res", "pred_res", "pred-teacher"]
    for i, lbl in enumerate(labels):
        draw.text((pad + i * (w + pad), 22 + h + 2), lbl, fill=(20, 20, 20))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def _safe_group_mean(rows: list[dict], key: str) -> float:
    vals = [float(r.get(key, float("nan"))) for r in rows]
    vals = [v for v in vals if np.isfinite(v)]
    if not vals:
        return float("nan")
    return float(np.mean(vals))


def _write_report(
    report_path: Path,
    rows: list[dict],
    by_scenario: dict[str, list[dict]],
    fig_paths: list[Path],
    checkpoint: Path,
    dataset_root: Path,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    overall = {
        "mae": _safe_group_mean(rows, "mae"),
        "rmse": _safe_group_mean(rows, "rmse"),
        "bias": _safe_group_mean(rows, "bias"),
        "over_ratio": _safe_group_mean(rows, "over_ratio"),
        "under_ratio": _safe_group_mean(rows, "under_ratio"),
        "corridor_bias": _safe_group_mean(rows, "corridor_bias"),
        "corridor_mae": _safe_group_mean(rows, "corridor_mae"),
        "open_bias": _safe_group_mean(rows, "open_bias"),
        "open_mae": _safe_group_mean(rows, "open_mae"),
    }

    lines: list[str] = []
    lines.append("# Hard 残差诊断报告")
    lines.append("")
    lines.append(f"- checkpoint: `{checkpoint}`")
    lines.append(f"- diagnostic dataset: `{dataset_root}`")
    lines.append(f"- num cases: {len(rows)}")
    lines.append("")
    lines.append("## 总体误差")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---:|")
    for k in ["mae", "rmse", "bias", "over_ratio", "under_ratio", "corridor_bias", "corridor_mae", "open_bias", "open_mae"]:
        v = overall[k]
        lines.append(f"| {k} | {v:.4f} |")
    lines.append("")
    lines.append("## 按场景类型统计")
    lines.append("")
    lines.append("| scenario | num | mae | bias | over_ratio | corridor_mae | corridor_bias |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for sc, sc_rows in sorted(by_scenario.items()):
        lines.append(
            "| {sc} | {n} | {mae:.4f} | {bias:.4f} | {over:.4f} | {cmae:.4f} | {cbias:.4f} |".format(
                sc=sc,
                n=len(sc_rows),
                mae=_safe_group_mean(sc_rows, "mae"),
                bias=_safe_group_mean(sc_rows, "bias"),
                over=_safe_group_mean(sc_rows, "over_ratio"),
                cmae=_safe_group_mean(sc_rows, "corridor_mae"),
                cbias=_safe_group_mean(sc_rows, "corridor_bias"),
            )
        )
    lines.append("")
    lines.append("## 典型可视化")
    lines.append("")
    for p in fig_paths:
        lines.append(f"- `{p}`")
    lines.append("")
    lines.append("## 诊断结论")
    lines.append("")
    if np.isfinite(overall["corridor_bias"]) and overall["corridor_bias"] > 0.2:
        lines.append("- 模型在窄道/瓶颈区域存在系统性正偏（过高残差），会抬高启发式并干扰 Hard 搜索。")
    else:
        lines.append("- 窄道区域偏差不显著，主要误差来自全局场景建模或动态风险耦合。")
    if np.isfinite(overall["over_ratio"]) and overall["over_ratio"] > 0.5:
        lines.append("- 过高估计比例较高，建议降低 hard 样本低估惩罚并增加过高残差抑制项。")
    else:
        lines.append("- 过高估计比例可控，可优先从模型感受野扩展提升全局一致性。")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    set_seed(int(args.seed))
    ensure_dirs([args.dataset_root, args.report_path.parent, args.json_path.parent, args.fig_dir])

    if not args.skip_generation:
        meta = _build_diagnostic_dataset(args)
        (args.dataset_root / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    elif not (args.dataset_root / "train").exists():
        raise FileNotFoundError(f"Missing diagnostic split: {args.dataset_root / 'train'}")

    predictor = NeuralHeuristicPredictor(
        checkpoint=args.checkpoint,
        device=args.device,
        gaussian_sigma=DEFAULT_CONFIG.dataset.gaussian_sigma,
    )

    files = sorted((args.dataset_root / "train").glob("sample_*.npz"))
    if not files:
        raise RuntimeError(f"No diagnostic samples under {(args.dataset_root / 'train')}")

    rows: list[dict] = []
    by_scenario: dict[str, list[dict]] = defaultdict(list)

    for p in files:
        with np.load(p, allow_pickle=False) as z:
            occ = z["occupancy"].astype(bool)
            esdf = z["esdf"].astype(np.float32)
            start = tuple(float(v) for v in z["start"].astype(np.float32))
            goal = tuple(float(v) for v in z["goal"].astype(np.float32))
            resolution = float(z["resolution"])
            scenario = str(z["scenario"]) if "scenario" in z else "unknown"
            task_type = str(z["task_type"]) if "task_type" in z else "unknown"
            teacher = z["teacher_3d"].astype(np.float32) if "teacher_3d" in z else z["teacher"][None, ...].astype(np.float32)
            if "rs_base_3d" in z:
                rs_base = z["rs_base_3d"].astype(np.float32)
            else:
                rs_base = predictor.compute_rs_analytical_base_field(occ, goal, resolution)
            veh_width = float(z["vehicle_width"]) if "vehicle_width" in z else float(DEFAULT_CONFIG.vehicle.width)
            dyn = z["dynamic_risk"].astype(np.float32) if "dynamic_risk" in z else None
            dyn_seq = z["dynamic_risk_seq"].astype(np.float32) if "dynamic_risk_seq" in z else None
            vehicle_context = {
                "wheel_base": float(z["vehicle_wheel_base"]) if "vehicle_wheel_base" in z else float(DEFAULT_CONFIG.vehicle.wheel_base),
                "max_steer_deg": float(z["vehicle_max_steer_deg"]) if "vehicle_max_steer_deg" in z else float(DEFAULT_CONFIG.vehicle.max_steer_deg),
                "battery": float(z["vehicle_battery"]) if "vehicle_battery" in z else 100.0,
                "load_factor": float(z["vehicle_load_factor"]) if "vehicle_load_factor" in z else 1.0,
            }

        pred_res = predictor.predict_residual_field(
            occupancy=occ,
            esdf=esdf,
            start=start,
            goal=goal,
            resolution=resolution,
            dynamic_risk=dyn,
            dynamic_risk_seq=dyn_seq,
            vehicle_context=vehicle_context,
        )
        pred_res = np.maximum(pred_res, 0.0).astype(np.float32)

        if pred_res.ndim == 2:
            pred_res = pred_res[None, ...]
        if rs_base.ndim == 2:
            rs_base = rs_base[None, ...]
        if rs_base.shape[0] != teacher.shape[0]:
            rs_base = _resample_yaw_channels(rs_base, teacher.shape[0])
        if pred_res.shape[0] != teacher.shape[0]:
            pred_res = _resample_yaw_channels(pred_res, teacher.shape[0])

        teacher_res = np.maximum(teacher - rs_base, 0.0).astype(np.float32)
        valid_2d = (~occ) & np.isfinite(teacher[0]) & np.isfinite(rs_base[0])
        valid = np.broadcast_to(valid_2d[None, ...], teacher_res.shape)

        diff = (pred_res - teacher_res).astype(np.float32)
        v = diff[valid]
        if v.size == 0:
            continue

        corridor_mask_2d = (~occ) & (esdf <= 0.95 * float(max(veh_width, 1e-3)))
        open_mask_2d = (~occ) & (esdf >= 1.8 * float(max(veh_width, 1e-3)))
        corridor_mask = np.broadcast_to(corridor_mask_2d[None, ...], teacher_res.shape) & valid
        open_mask = np.broadcast_to(open_mask_2d[None, ...], teacher_res.shape) & valid

        row = {
            "file": str(p),
            "scenario": scenario,
            "task_type": task_type,
            "mae": float(np.mean(np.abs(v))),
            "rmse": _finite_rmse(v),
            "bias": float(np.mean(v)),
            "over_ratio": float(np.mean(v > 0.3)),
            "under_ratio": float(np.mean(v < -0.3)),
            "corridor_mae": _finite_mean(np.abs(diff[corridor_mask])) if np.any(corridor_mask) else float("nan"),
            "corridor_bias": _finite_mean(diff[corridor_mask]) if np.any(corridor_mask) else float("nan"),
            "open_mae": _finite_mean(np.abs(diff[open_mask])) if np.any(open_mask) else float("nan"),
            "open_bias": _finite_mean(diff[open_mask]) if np.any(open_mask) else float("nan"),
        }
        rows.append(row)
        by_scenario[scenario].append(row)

    if not rows:
        raise RuntimeError("No valid diagnostic rows were produced")

    # Pick worst corridor-bias cases for visualization.
    worst = sorted(
        rows,
        key=lambda r: float(r.get("corridor_bias", float("-inf"))) if np.isfinite(float(r.get("corridor_bias", float("nan")))) else -1e9,
        reverse=True,
    )[: max(1, int(args.vis_cases))]

    fig_paths: list[Path] = []
    for i, r in enumerate(worst):
        p = Path(r["file"])
        with np.load(p, allow_pickle=False) as z:
            occ = z["occupancy"].astype(bool)
            esdf = z["esdf"].astype(np.float32)
            start = tuple(float(v) for v in z["start"].astype(np.float32))
            goal = tuple(float(v) for v in z["goal"].astype(np.float32))
            resolution = float(z["resolution"])
            scenario = str(z["scenario"]) if "scenario" in z else "unknown"
            teacher = z["teacher_3d"].astype(np.float32) if "teacher_3d" in z else z["teacher"][None, ...].astype(np.float32)
            if "rs_base_3d" in z:
                rs_base = z["rs_base_3d"].astype(np.float32)
            else:
                rs_base = predictor.compute_rs_analytical_base_field(occ, goal, resolution)
            dyn = z["dynamic_risk"].astype(np.float32) if "dynamic_risk" in z else None
            dyn_seq = z["dynamic_risk_seq"].astype(np.float32) if "dynamic_risk_seq" in z else None
            vehicle_context = {
                "wheel_base": float(z["vehicle_wheel_base"]) if "vehicle_wheel_base" in z else float(DEFAULT_CONFIG.vehicle.wheel_base),
                "max_steer_deg": float(z["vehicle_max_steer_deg"]) if "vehicle_max_steer_deg" in z else float(DEFAULT_CONFIG.vehicle.max_steer_deg),
                "battery": float(z["vehicle_battery"]) if "vehicle_battery" in z else 100.0,
                "load_factor": float(z["vehicle_load_factor"]) if "vehicle_load_factor" in z else 1.0,
            }

        pred_res = predictor.predict_residual_field(
            occupancy=occ,
            esdf=esdf,
            start=start,
            goal=goal,
            resolution=resolution,
            dynamic_risk=dyn,
            dynamic_risk_seq=dyn_seq,
            vehicle_context=vehicle_context,
        )
        pred_res = np.maximum(pred_res, 0.0).astype(np.float32)
        if pred_res.ndim == 2:
            pred_res = pred_res[None, ...]
        if rs_base.ndim == 2:
            rs_base = rs_base[None, ...]
        if rs_base.shape[0] != teacher.shape[0]:
            rs_base = _resample_yaw_channels(rs_base, teacher.shape[0])
        if pred_res.shape[0] != teacher.shape[0]:
            pred_res = _resample_yaw_channels(pred_res, teacher.shape[0])

        teacher_res = np.maximum(teacher - rs_base, 0.0).astype(np.float32)
        teacher2 = np.min(teacher_res, axis=0)
        pred2 = np.min(pred_res, axis=0)
        err2 = pred2 - teacher2

        out = args.fig_dir / f"diagnosis_case_{i:02d}_{scenario}.png"
        _save_case_figure(
            out_path=out,
            occupancy=occ,
            teacher_res_2d=teacher2,
            pred_res_2d=pred2,
            err_2d=err2,
            title=f"{scenario} | bias={float(r['bias']):.3f} | corridor_bias={float(r['corridor_bias']):.3f}",
        )
        fig_paths.append(out)

    out_json = {
        "checkpoint": str(args.checkpoint),
        "dataset_root": str(args.dataset_root),
        "num_rows": len(rows),
        "overall": {
            "mae": _safe_group_mean(rows, "mae"),
            "rmse": _safe_group_mean(rows, "rmse"),
            "bias": _safe_group_mean(rows, "bias"),
            "over_ratio": _safe_group_mean(rows, "over_ratio"),
            "under_ratio": _safe_group_mean(rows, "under_ratio"),
            "corridor_mae": _safe_group_mean(rows, "corridor_mae"),
            "corridor_bias": _safe_group_mean(rows, "corridor_bias"),
            "open_mae": _safe_group_mean(rows, "open_mae"),
            "open_bias": _safe_group_mean(rows, "open_bias"),
        },
        "by_scenario": {
            k: {
                "num": len(v),
                "mae": _safe_group_mean(v, "mae"),
                "bias": _safe_group_mean(v, "bias"),
                "over_ratio": _safe_group_mean(v, "over_ratio"),
                "corridor_mae": _safe_group_mean(v, "corridor_mae"),
                "corridor_bias": _safe_group_mean(v, "corridor_bias"),
            }
            for k, v in sorted(by_scenario.items())
        },
        "rows": rows,
        "figures": [str(p) for p in fig_paths],
    }
    args.json_path.write_text(json.dumps(out_json, indent=2), encoding="utf-8")

    _write_report(
        report_path=args.report_path,
        rows=rows,
        by_scenario=by_scenario,
        fig_paths=fig_paths,
        checkpoint=args.checkpoint,
        dataset_root=args.dataset_root,
    )

    print(f"diagnosis json: {args.json_path}")
    print(f"diagnosis report: {args.report_path}")
    for p in fig_paths:
        print(f"figure: {p}")


if __name__ == "__main__":
    main()
