from __future__ import annotations

import argparse
import heapq
import math
import json
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
from scripts.evaluate_baselines import _astar_grid, _euclidean_field, _resolve_2d_heuristic, _world_to_grid


@dataclass(frozen=True)
class MidArmResult:
    arm: str
    success: bool
    L: float
    T_ms: float
    infer_ms: float
    search_ms: float


def _neighbors8() -> list[tuple[int, int, float]]:
    rt2 = math.sqrt(2.0)
    return [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, rt2),
        (-1, 1, rt2),
        (1, -1, rt2),
        (1, 1, rt2),
    ]


def _astar_grid_hybrid_crop(
    *,
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    max_expansions: int,
    crop_heuristic: np.ndarray,
    crop_bbox: tuple[int, int, int, int],  # (x0,x1,y0,y1) in full-grid coordinates
    heuristic_weight: float = 1.0,
) -> dict:
    """
    A* with Euclidean heuristic outside a crop, and a provided heuristic map inside the crop.
    This avoids building a full-map Euclidean field (important when the crop is small).
    """

    t0 = time.perf_counter()
    h, w = occupancy.shape
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)

    if occupancy[sy, sx] or occupancy[gy, gx]:
        return {
            "success": False,
            "expansions": 0,
            "runtime_ms": (time.perf_counter() - t0) * 1000.0,
            "path": [],
        }

    x0, x1, y0, y1 = (int(crop_bbox[0]), int(crop_bbox[1]), int(crop_bbox[2]), int(crop_bbox[3]))
    crop_h, crop_w = crop_heuristic.shape
    if crop_h != (y1 - y0) or crop_w != (x1 - x0):
        raise ValueError(f"crop_heuristic shape {crop_heuristic.shape} does not match bbox {(x0, x1, y0, y1)}")

    def h_fn(ix: int, iy: int) -> float:
        if (x0 <= ix < x1) and (y0 <= iy < y1):
            v = float(crop_heuristic[iy - y0, ix - x0])
            if not np.isfinite(v):
                return 1e6
            return max(v, 0.0)
        return math.hypot((gx - ix) * resolution, (gy - iy) * resolution)

    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    counter = 0
    start = (sx, sy)
    goal = (gx, gy)
    g_cost: dict[tuple[int, int], float] = {start: 0.0}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    f0 = heuristic_weight * h_fn(sx, sy)
    heapq.heappush(open_heap, (f0, 0.0, counter, start))

    expansions = 0
    nbrs = _neighbors8()

    while open_heap and expansions < max(int(max_expansions), 1):
        _f, g, _, node = heapq.heappop(open_heap)
        if g > g_cost.get(node, float("inf")) + 1e-9:
            continue

        expansions += 1
        if node == goal:
            # For pilot metrics we don't need the explicit path, keep it empty to save overhead.
            return {
                "success": True,
                "expansions": expansions,
                "runtime_ms": (time.perf_counter() - t0) * 1000.0,
                "path": [],
            }

        x, y = node
        for dx, dy, step in nbrs:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            if occupancy[ny, nx]:
                continue
            ng = g + step * resolution
            nkey = (nx, ny)
            if ng + 1e-9 >= g_cost.get(nkey, float("inf")):
                continue
            g_cost[nkey] = ng
            parent[nkey] = node
            counter += 1
            nf = ng + heuristic_weight * h_fn(nx, ny)
            heapq.heappush(open_heap, (nf, ng, counter, nkey))

    return {
        "success": False,
        "expansions": expansions,
        "runtime_ms": (time.perf_counter() - t0) * 1000.0,
        "path": [],
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase23 pilot: prototype 2-3 candidate mid arms and quickly check if any provides a non-dominated tradeoff."
    )
    # Default to Phase-9 public benchmark dataset since the reference counterfactual tables come from Phase-9 bench.
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--split", type=str, default="test", choices=["calib", "test"])
    p.add_argument("--ref-calib-parquet", type=Path, default=Path("outputs/router_phase9_bench_v1/common/router_counterfactual_calib.parquet"))
    p.add_argument("--ref-test-parquet", type=Path, default=Path("outputs/router_phase9_bench_v1/common/router_counterfactual_test.parquet"))
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--standard-base-mode", type=str, default="euclidean", choices=["euclidean", "rs"])
    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)

    p.add_argument("--max-cases", type=int, default=80, help="Pilot sample size (small by design).")
    p.add_argument("--seed", type=int, default=7)

    # Candidate mid-arm designs.
    p.add_argument("--mid-crop-margin-cells", type=int, default=48, help="Crop margin (cells) for corridor crop inference arm.")
    p.add_argument(
        "--mid-crop-pad-multiple",
        type=int,
        default=32,
        help="If >0, expand the crop to the nearest multiple to reduce shape-variance overhead on CUDA (e.g., 32 => {32,64,96,...}).",
    )
    p.add_argument("--mid-wastar-weight", type=float, default=1.5, help="Heuristic weight for Weighted A* mid arm (no inference).")

    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase23_portfolio_pilot_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase23_portfolio_pilot_v1.md"))
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


def _calibrate_beta_from_ref(calib_df: pd.DataFrame, *, beta_cap: float = 200.0) -> tuple[float, float]:
    # Keep consistent with scripts/run_router_risk_v1.py
    t_ref = float(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(calib_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    non_zero = q_pos[q_pos > 1e-9]
    if non_zero.size == 0:
        beta = 1.0
    else:
        q_pos_median = float(np.median(non_zero))
        t_norm_median = float(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)))
        beta = float(t_norm_median / max(q_pos_median, 1e-9))
    beta = float(np.clip(beta, 1e-3, max(beta_cap, 1e-3)))
    return t_ref, beta


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


def _run_mid_wastar(
    *,
    occupancy: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    weight: float,
    max_expansions: int,
) -> MidArmResult:
    r = _astar_grid(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        max_expansions=int(max_expansions),
        heuristic_map=None,
        heuristic_weight=float(weight),
        record_expanded=False,
    )
    return MidArmResult(
        arm=f"mid_wastar_w{float(weight):.2f}",
        success=bool(r["success"]),
        L=float(r["expansions"]),
        T_ms=float(r["runtime_ms"]),
        infer_ms=0.0,
        search_ms=float(r["runtime_ms"]),
    )


def _run_mid_lowres_infer(
    *,
    predictor: NeuralHeuristicPredictor,
    occupancy: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    lowres_factor: int,
    max_expansions: int,
    standard_base_mode: str,
) -> MidArmResult:
    t_total0 = time.perf_counter()
    f = int(max(lowres_factor, 1))
    occ_lr = _downsample_occupancy_or(occupancy, f)
    res_lr = float(resolution) * float(f)

    t0 = time.perf_counter()
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
    infer_ms = float((time.perf_counter() - t0) * 1000.0)
    h_lr = _resolve_2d_heuristic(pred_lr, occ_lr)
    h_full = _upsample_to_shape(h_lr, occupancy.shape)
    h_full = _resolve_2d_heuristic(h_full, occupancy)

    r = _astar_grid(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=(start[0], start[1]),
        goal_xy=(goal[0], goal[1]),
        max_expansions=int(max_expansions),
        heuristic_map=h_full,
        heuristic_weight=1.0,
        record_expanded=False,
    )
    total_ms = float((time.perf_counter() - t_total0) * 1000.0)
    return MidArmResult(
        arm=f"mid_lowres_ds{f}",
        success=bool(r["success"]),
        L=float(r["expansions"]),
        T_ms=float(total_ms),
        infer_ms=float(infer_ms),
        search_ms=float(r["runtime_ms"]),
    )


def _run_mid_crop_infer(
    *,
    predictor: NeuralHeuristicPredictor,
    occupancy: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    crop_margin_cells: int,
    crop_pad_multiple: int,
    max_expansions: int,
    standard_base_mode: str,
) -> MidArmResult:
    t_total0 = time.perf_counter()
    h, w = occupancy.shape
    sx, sy = _world_to_grid(float(start[0]), float(start[1]), float(resolution), w, h)
    gx, gy = _world_to_grid(float(goal[0]), float(goal[1]), float(resolution), w, h)

    m = int(max(crop_margin_cells, 0))
    x0 = max(min(sx, gx) - m, 0)
    x1 = min(max(sx, gx) + m + 1, w)
    y0 = max(min(sy, gy) - m, 0)
    y1 = min(max(sy, gy) + m + 1, h)

    pad = int(max(crop_pad_multiple, 0))
    if pad > 0:
        cur_h = int(y1 - y0)
        cur_w = int(x1 - x0)
        target_h = int(min(h, int(math.ceil(cur_h / pad) * pad)))
        target_w = int(min(w, int(math.ceil(cur_w / pad) * pad)))
        # Re-center the crop to keep both endpoints inside.
        cy = int((y0 + y1) // 2)
        cx = int((x0 + x1) // 2)
        y0 = int(np.clip(cy - target_h // 2, 0, h - target_h))
        y1 = int(y0 + target_h)
        x0 = int(np.clip(cx - target_w // 2, 0, w - target_w))
        x1 = int(x0 + target_w)

    occ_crop = occupancy[y0:y1, x0:x1].astype(bool)
    # Shift start/goal into crop-local frame (world coords).
    start_crop = (float(start[0]) - float(x0) * float(resolution), float(start[1]) - float(y0) * float(resolution), float(start[2]))
    goal_crop = (float(goal[0]) - float(x0) * float(resolution), float(goal[1]) - float(y0) * float(resolution), float(goal[2]))

    t0 = time.perf_counter()
    base_override = _maybe_base_override(
        predictor=predictor,
        occupancy=occ_crop,
        goal_xy=(goal_crop[0], goal_crop[1]),
        resolution=resolution,
        standard_base_mode=standard_base_mode,
    )
    pred_crop = predictor.predict_field(
        occupancy=occ_crop,
        esdf=np.zeros_like(occ_crop, dtype=np.float32),
        start=start_crop,
        goal=goal_crop,
        resolution=resolution,
        base_field_override=base_override,
    )
    infer_ms = float((time.perf_counter() - t0) * 1000.0)
    h_crop = _resolve_2d_heuristic(pred_crop, occ_crop)

    r = _astar_grid_hybrid_crop(
        occupancy=occupancy,
        resolution=resolution,
        start_xy=(float(start[0]), float(start[1])),
        goal_xy=(float(goal[0]), float(goal[1])),
        max_expansions=int(max_expansions),
        crop_heuristic=h_crop,
        crop_bbox=(x0, x1, y0, y1),
        heuristic_weight=1.0,
    )
    total_ms = float((time.perf_counter() - t_total0) * 1000.0)
    return MidArmResult(
        arm=f"mid_crop_m{m}_p{pad}" if pad > 0 else f"mid_crop_m{m}",
        success=bool(r["success"]),
        L=float(r["expansions"]),
        T_ms=float(total_ms),
        infer_ms=float(infer_ms),
        search_ms=float(r["runtime_ms"]),
    )


def _arm_point(
    df: pd.DataFrame,
    *,
    arm_L: str,
    arm_T: str,
    epsilon_rel: float,
    t_ref: float,
    beta: float,
) -> dict[str, float]:
    l = df[arm_L].to_numpy(dtype=np.float64)
    t = df[arm_T].to_numpy(dtype=np.float64)
    l_slow = df["L_slow"].to_numpy(dtype=np.float64)
    drel = (l - l_slow) / np.maximum(l_slow, 1e-6)
    drel_pos = np.maximum(drel, 0.0)
    vio = drel > float(epsilon_rel)
    j = (t / max(float(t_ref), 1e-9)) + float(beta) * drel_pos
    return {
        "avg_latency_ms": float(np.mean(t)),
        "avg_delta_l_rel": float(np.mean(drel)),
        "avg_delta_l_rel_pos": float(np.mean(drel_pos)),
        "violation_rate": float(np.mean(vio)),
        "J_mean": float(np.mean(j)),
    }


def _dominates(a: dict[str, float], b: dict[str, float]) -> bool:
    # Conservative dominance check in the (latency, violation, J) space.
    le = (a["avg_latency_ms"] <= b["avg_latency_ms"] + 1e-12) and (a["violation_rate"] <= b["violation_rate"] + 1e-12) and (
        a["J_mean"] <= b["J_mean"] + 1e-12
    )
    lt = (a["avg_latency_ms"] < b["avg_latency_ms"] - 1e-9) or (a["violation_rate"] < b["violation_rate"] - 1e-9) or (a["J_mean"] < b["J_mean"] - 1e-9)
    return bool(le and lt)


def _write_report(path: Path, stats: dict) -> None:
    lines: list[str] = []
    lines.append("# Phase23 Portfolio Mid-Arm Pilot (v1)")
    lines.append("")
    lines.append("This pilot prototypes 2–3 candidate `mid` arms and checks if any yields a non-dominated tradeoff under the frozen protocol semantics.")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Date: `{stats['date']}`")
    lines.append(f"- Cases: `{stats['num_cases']}` (pilot subset)")
    lines.append(f"- RNG seed: `{stats['seed']}`")
    lines.append(f"- `epsilon_rel`: `{stats['epsilon_rel']}`")
    lines.append(f"- `alpha`: `{stats['alpha']}`")
    lines.append(f"- `T_ref` (median slow calib): `{stats['t_ref_ms']:.6f} ms`")
    lines.append(f"- `beta` (risk-aware, from calib): `{stats['beta']:.6f}`")
    lines.append("")
    lines.append("## Candidate Mid Arms")
    for row in stats["mid_arms"]:
        lines.append(f"- `{row}`")
    lines.append("")
    lines.append("## Aggregate Points (test subset)")
    lines.append(pd.DataFrame(stats["points"]).to_markdown(index=False))
    lines.append("")
    lines.append("## Dominance Summary")
    for s in stats["dominance_summary"]:
        lines.append(f"- {s}")
    lines.append("")
    lines.append("## Oracle Complementarity (lower is better)")
    lines.append(pd.DataFrame(stats["oracle"]).to_markdown(index=False))
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    ref_calib = pd.read_parquet(args.ref_calib_parquet).copy()
    ref_test = pd.read_parquet(args.ref_test_parquet).copy()
    t_ref, beta = _calibrate_beta_from_ref(ref_calib)

    # Sample pilot cases from reference test parquet to ensure alignment.
    rng = np.random.default_rng(int(args.seed))
    all_names = ref_test["sample_name"].astype(str).tolist()
    if not all_names:
        raise RuntimeError(f"Empty reference test parquet: {args.ref_test_parquet}")
    n = int(min(max(int(args.max_cases), 1), len(all_names)))
    pick = rng.choice(np.asarray(all_names, dtype=object), size=n, replace=False)
    pick_set = set(str(x) for x in pick.tolist())
    sub = ref_test[ref_test["sample_name"].astype(str).isin(pick_set)].copy()
    sub = sub.sort_values("sample_name").reset_index(drop=True)

    predictor = NeuralHeuristicPredictor(args.checkpoint, device=str(args.device))

    out_rows: list[dict] = []
    mid_arms: list[str] = []
    mid_arms.append(
        f"mid_crop_m{int(args.mid_crop_margin_cells)}_p{int(args.mid_crop_pad_multiple)} (corridor crop + pad-to-multiple + A* w=1)"
    )
    mid_arms.append(f"mid_crop_m{int(args.mid_crop_margin_cells)} (corridor crop (raw) + A* w=1)")
    mid_arms.append(f"mid_wastar_w{float(args.mid_wastar_weight):.2f} (Weighted A* with euclidean heuristic, no inference)")

    for i, r in enumerate(sub.itertuples(index=False), start=1):
        sample_name = str(getattr(r, "sample_name"))
        split_dir = args.dataset_root / str(args.split)
        p = split_dir / sample_name
        if not p.exists():
            raise FileNotFoundError(f"Missing sample file: {p}")
        s = load_grid_sample(p)

        start = (float(s.start[0]), float(s.start[1]), float(s.start[2]))
        goal = (float(s.goal[0]), float(s.goal[1]), float(s.goal[2]))
        start_xy = (start[0], start[1])
        goal_xy = (goal[0], goal[1])

        # Mid arms.
        mid1 = _run_mid_crop_infer(
            predictor=predictor,
            occupancy=s.occupancy,
            resolution=float(s.resolution),
            start=start,
            goal=goal,
            crop_margin_cells=int(args.mid_crop_margin_cells),
            crop_pad_multiple=int(args.mid_crop_pad_multiple),
            max_expansions=int(args.grid_max_expansions),
            standard_base_mode=str(args.standard_base_mode),
        )
        mid2 = _run_mid_crop_infer(
            predictor=predictor,
            occupancy=s.occupancy,
            resolution=float(s.resolution),
            start=start,
            goal=goal,
            crop_margin_cells=int(args.mid_crop_margin_cells),
            crop_pad_multiple=0,
            max_expansions=int(args.grid_max_expansions),
            standard_base_mode=str(args.standard_base_mode),
        )
        mid3 = _run_mid_wastar(
            occupancy=s.occupancy,
            resolution=float(s.resolution),
            start_xy=start_xy,
            goal_xy=goal_xy,
            weight=float(args.mid_wastar_weight),
            max_expansions=int(args.grid_max_expansions),
        )

        out_rows.append(
            {
                "sample_name": sample_name,
                "difficulty": str(getattr(r, "difficulty")),
                "ood_family": int(getattr(r, "ood_family")),
                "L_fast": float(getattr(r, "L_fast")),
                "T_fast_ms": float(getattr(r, "T_fast_ms")),
                "L_slow": float(getattr(r, "L_slow")),
                "T_slow_ms": float(getattr(r, "T_slow_ms")),
                "mid1_arm": mid1.arm,
                "mid1_success": bool(mid1.success),
                "L_mid1": float(mid1.L),
                "T_mid1_ms": float(mid1.T_ms),
                "infer_mid1_ms": float(mid1.infer_ms),
                "search_mid1_ms": float(mid1.search_ms),
                "mid2_arm": mid2.arm,
                "mid2_success": bool(mid2.success),
                "L_mid2": float(mid2.L),
                "T_mid2_ms": float(mid2.T_ms),
                "infer_mid2_ms": float(mid2.infer_ms),
                "search_mid2_ms": float(mid2.search_ms),
                "mid3_arm": mid3.arm,
                "mid3_success": bool(mid3.success),
                "L_mid3": float(mid3.L),
                "T_mid3_ms": float(mid3.T_ms),
                "infer_mid3_ms": float(mid3.infer_ms),
                "search_mid3_ms": float(mid3.search_ms),
            }
        )

        if i % 20 == 0 or i == len(sub):
            print(f"[phase23-pilot] processed {i}/{len(sub)}")

    out_df = pd.DataFrame(out_rows)
    out_parquet = args.out_dir / "pilot_mid_counterfactual_test.parquet"
    out_df.to_parquet(out_parquet, index=False)

    # Aggregate points.
    points: list[dict] = []
    points.append({"arm": "always_fast", **_arm_point(out_df, arm_L="L_fast", arm_T="T_fast_ms", epsilon_rel=args.epsilon_rel, t_ref=t_ref, beta=beta)})
    points.append({"arm": out_df["mid1_arm"].iloc[0], **_arm_point(out_df, arm_L="L_mid1", arm_T="T_mid1_ms", epsilon_rel=args.epsilon_rel, t_ref=t_ref, beta=beta)})
    points.append({"arm": out_df["mid2_arm"].iloc[0], **_arm_point(out_df, arm_L="L_mid2", arm_T="T_mid2_ms", epsilon_rel=args.epsilon_rel, t_ref=t_ref, beta=beta)})
    points.append({"arm": out_df["mid3_arm"].iloc[0], **_arm_point(out_df, arm_L="L_mid3", arm_T="T_mid3_ms", epsilon_rel=args.epsilon_rel, t_ref=t_ref, beta=beta)})
    points.append({"arm": "always_slow_ref", **_arm_point(out_df, arm_L="L_slow", arm_T="T_slow_ms", epsilon_rel=args.epsilon_rel, t_ref=t_ref, beta=beta)})

    # Dominance summary.
    pt_map = {p["arm"]: p for p in points}
    arms = [p["arm"] for p in points]
    dom_lines: list[str] = []
    for a in arms:
        for b in arms:
            if a == b:
                continue
            if _dominates(pt_map[a], pt_map[b]):
                dom_lines.append(f"`{a}` dominates `{b}`")
    if not dom_lines:
        dom_lines = ["No strict dominance detected among the aggregated arm points."]

    # Oracle complementarity: best single arm vs oracle over {fast, midX, slow}.
    def _j_vals(L_col: str, T_col: str) -> np.ndarray:
        l = out_df[L_col].to_numpy(dtype=np.float64)
        t = out_df[T_col].to_numpy(dtype=np.float64)
        l_slow = out_df["L_slow"].to_numpy(dtype=np.float64)
        drel_pos = np.maximum((l - l_slow) / np.maximum(l_slow, 1e-6), 0.0)
        return (t / max(t_ref, 1e-9)) + float(beta) * drel_pos

    j_fast = _j_vals("L_fast", "T_fast_ms")
    j_slow = _j_vals("L_slow", "T_slow_ms")
    j_mid1 = _j_vals("L_mid1", "T_mid1_ms")
    j_mid2 = _j_vals("L_mid2", "T_mid2_ms")
    j_mid3 = _j_vals("L_mid3", "T_mid3_ms")

    def _oracle_stats(j_stack: list[tuple[str, np.ndarray]]) -> dict[str, float]:
        names = [n for n, _ in j_stack]
        arr = np.stack([v for _, v in j_stack], axis=0)
        best_idx = np.argmin(arr, axis=0)
        best = arr[best_idx, np.arange(arr.shape[1])]
        counts = {names[i]: int(np.sum(best_idx == i)) for i in range(len(names))}
        total = int(arr.shape[1])
        out = {"J_oracle_mean": float(np.mean(best))}
        out.update({f"share_{k}": float(v / max(total, 1)) for k, v in counts.items()})
        return out

    oracle_rows: list[dict] = []
    # 2-arm vs 3-arm oracles to estimate complementarity potential.
    oracle_rows.append(
        {
            "oracle_set": "{fast,slow}",
            **_oracle_stats([("fast", j_fast), ("slow", j_slow)]),
        }
    )
    oracle_rows.append(
        {
            "oracle_set": "{fast,mid_crop_padded,slow}",
            **_oracle_stats([("fast", j_fast), ("mid_crop_padded", j_mid1), ("slow", j_slow)]),
        }
    )
    oracle_rows.append(
        {
            "oracle_set": "{fast,mid_crop_raw,slow}",
            **_oracle_stats([("fast", j_fast), ("mid_crop_raw", j_mid2), ("slow", j_slow)]),
        }
    )
    oracle_rows.append(
        {
            "oracle_set": "{fast,mid_wastar,slow}",
            **_oracle_stats([("fast", j_fast), ("mid_wastar", j_mid3), ("slow", j_slow)]),
        }
    )
    oracle_rows.append(
        {
            "oracle_set": "{fast,mid_crop_padded,mid_crop_raw,mid_wastar,slow}",
            **_oracle_stats(
                [
                    ("fast", j_fast),
                    ("mid_crop_padded", j_mid1),
                    ("mid_crop_raw", j_mid2),
                    ("mid_wastar", j_mid3),
                    ("slow", j_slow),
                ]
            ),
        }
    )

    stats = {
        "date": time.strftime("%Y-%m-%d"),
        "seed": int(args.seed),
        "num_cases": int(len(out_df)),
        "epsilon_rel": float(args.epsilon_rel),
        "alpha": float(args.alpha),
        "t_ref_ms": float(t_ref),
        "beta": float(beta),
        "mid_arms": list(mid_arms),
        "points": points,
        "dominance_summary": dom_lines,
        "oracle": oracle_rows,
        "runtime_s": float(time.perf_counter() - t0),
        "artifacts": {
            "pilot_mid_counterfactual_test_parquet": str(out_parquet),
        },
    }
    (args.out_dir / "stats.json").write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    _write_report(args.report_md, stats)

    print(f"[phase23-pilot] done in {stats['runtime_s']:.3f}s")


if __name__ == "__main__":
    main()
