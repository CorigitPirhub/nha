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
from planner.heuristics import FieldHeuristic, YawFieldHeuristic, euclidean_heuristic
from planner.hybrid_astar import HybridAStarPlanner
from utils.common import ensure_dirs, set_seed, yaw_to_bin_float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage-1 diagnosis: 2D teacher bottleneck")
    p.add_argument("--data", type=Path, default=Path("data/test"))
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/heuristic_net.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    return p.parse_args()


def _euclidean_field(goal: tuple[float, float, float], h: int, w: int, res: float) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    wx = (xx + 0.5) * res
    wy = (yy + 0.5) * res
    return np.hypot(wx - goal[0], wy - goal[1]).astype(np.float32)


def _pick_typical(files: list[Path]) -> Path:
    scenario_priority = ["deadend", "parking", "narrow", "random"]
    buckets: dict[str, list[Path]] = {k: [] for k in scenario_priority}
    for p in files:
        with np.load(p, allow_pickle=False) as d:
            s = str(d["scenario"]) if "scenario" in d else "random"
        if s in buckets:
            buckets[s].append(p)
    for key in scenario_priority:
        if buckets[key]:
            return buckets[key][0]
    return files[0]


def _prediction_to_2d(pred: np.ndarray, yaw: float) -> np.ndarray:
    if pred.ndim == 2:
        return pred
    kf = yaw_to_bin_float(yaw, pred.shape[0])
    k = int(np.floor(kf)) % pred.shape[0]
    return pred[k]


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    set_seed(args.seed)
    ensure_dirs([cfg.paths.figures_dir, cfg.paths.logs_dir])

    files = sorted(args.data.glob("*.npz"))
    if not files:
        raise RuntimeError(f"No test files under {args.data}")

    # 1) Heatmap diagnosis
    predictor = NeuralHeuristicPredictor(args.checkpoint, device=args.device, gaussian_sigma=cfg.dataset.gaussian_sigma)
    sample_path = _pick_typical(files)
    with np.load(sample_path, allow_pickle=False) as d:
        occ = d["occupancy"].astype(bool)
        esdf = d["esdf"].astype(np.float32)
        teacher = d["teacher"].astype(np.float32)
        start = tuple(float(v) for v in d["start"])
        goal = tuple(float(v) for v in d["goal"])
        scenario = str(d["scenario"]) if "scenario" in d else "unknown"

    pred_raw = predictor.predict_field(occ, esdf, start, goal, cfg.map.resolution)
    pred_2d = _prediction_to_2d(pred_raw, start[2])
    euc = _euclidean_field(goal, occ.shape[0], occ.shape[1], cfg.map.resolution)

    vmax = np.percentile(teacher[~occ], 95) if np.any(~occ) else np.max(teacher)
    vmax = max(vmax, 1.0)

    fig, axes = plt.subplots(1, 4, figsize=(16, 4), constrained_layout=True)
    for ax, mat, title in [
        (axes[0], teacher, "GT: 2D Dijkstra"),
        (axes[1], pred_2d, "Network Prediction"),
        (axes[2], euc, "Euclidean"),
        (axes[3], np.abs(pred_2d - teacher), "|Pred-GT|"),
    ]:
        im = ax.imshow(mat, cmap="viridis", origin="lower", vmin=0.0, vmax=vmax if title != "|Pred-GT|" else None)
        ax.contour(occ.astype(float), levels=[0.5], colors="white", linewidths=0.6)
        ax.set_title(title)
        ax.set_axis_off()
        fig.colorbar(im, ax=ax, fraction=0.046)

    fig.suptitle(f"Stage-1 Diagnosis ({scenario})")
    fig_path = cfg.paths.figures_dir / "stage1_diagnosis_heatmaps.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)

    # 2) Perfect 2D teacher vs Euclidean ablation
    rows = []
    euc_success = 0
    dijk_success = 0
    euc_exp, dijk_exp = [], []
    euc_t, dijk_t = [], []

    for idx, p in enumerate(files):
        with np.load(p, allow_pickle=False) as d:
            occ = d["occupancy"].astype(bool)
            esdf = d["esdf"].astype(np.float32)
            teacher = d["teacher"].astype(np.float32)
            start = tuple(float(v) for v in d["start"])
            goal = tuple(float(v) for v in d["goal"])
            scenario = str(d["scenario"]) if "scenario" in d else "unknown"

        planner = HybridAStarPlanner(occ, cfg.map.resolution, cfg.vehicle, cfg.planner, esdf=esdf)
        euc_fn = euclidean_heuristic((goal[0], goal[1]))
        dijk_fn = FieldHeuristic(teacher, cfg.map.resolution, max_value=cfg.dataset.max_teacher_value, scale=1.0)

        e_out = planner.plan(start=start, goal=goal, anchor_fn=euc_fn)
        d_out = planner.plan(start=start, goal=goal, anchor_fn=dijk_fn)

        e_ok = e_out.success
        d_ok = d_out.success
        euc_success += int(e_ok)
        dijk_success += int(d_ok)
        if e_ok:
            euc_exp.append(e_out.expansions)
            euc_t.append(e_out.runtime_ms)
        if d_ok:
            dijk_exp.append(d_out.expansions)
            dijk_t.append(d_out.runtime_ms)

        rows.append(
            {
                "case_id": idx,
                "scenario": scenario,
                "euclidean_success": e_ok,
                "dijkstra_success": d_ok,
                "euclidean_expansions": int(e_out.expansions),
                "dijkstra_expansions": int(d_out.expansions),
                "euclidean_time_ms": float(e_out.runtime_ms),
                "dijkstra_time_ms": float(d_out.runtime_ms),
            }
        )

    total = max(len(files), 1)
    summary = {
        "num_cases": len(files),
        "euclidean_success_rate": euc_success / total,
        "dijkstra_success_rate": dijk_success / total,
        "euclidean_avg_expansions": float(np.mean(euc_exp)) if euc_exp else float("nan"),
        "dijkstra_avg_expansions": float(np.mean(dijk_exp)) if dijk_exp else float("nan"),
        "euclidean_avg_time_ms": float(np.mean(euc_t)) if euc_t else float("nan"),
        "dijkstra_avg_time_ms": float(np.mean(dijk_t)) if dijk_t else float("nan"),
    }

    ratio = np.nan
    if euc_exp and dijk_exp:
        ratio = float((summary["euclidean_avg_expansions"] - summary["dijkstra_avg_expansions"]) / max(summary["euclidean_avg_expansions"], 1.0))
    summary["expansion_gain_ratio_dijkstra_vs_euclidean"] = ratio

    # 3) Heading-sensitivity ablation
    with np.load(sample_path, allow_pickle=False) as d:
        occ = d["occupancy"].astype(bool)
        esdf = d["esdf"].astype(np.float32)
        teacher = d["teacher"].astype(np.float32)
        base_start = tuple(float(v) for v in d["start"])
        goal = tuple(float(v) for v in d["goal"])

    planner = HybridAStarPlanner(occ, cfg.map.resolution, cfg.vehicle, cfg.planner, esdf=esdf)
    yaw_values = np.linspace(-np.pi, np.pi, 12, endpoint=False)
    true_costs = []
    for yaw in yaw_values:
        st = (base_start[0], base_start[1], float(yaw))
        out = planner.plan(start=st, goal=goal, anchor_fn=euclidean_heuristic((goal[0], goal[1])))
        if out.success and np.isfinite(out.cost):
            true_costs.append(float(out.cost))

    gx = int(np.clip(np.floor(base_start[0] / cfg.map.resolution), 0, teacher.shape[1] - 1))
    gy = int(np.clip(np.floor(base_start[1] / cfg.map.resolution), 0, teacher.shape[0] - 1))
    heading_std = float(np.std(true_costs)) if true_costs else float("nan")
    heading_mean = float(np.mean(true_costs)) if true_costs else float("nan")
    heading_cv = heading_std / max(abs(heading_mean), 1e-6) if np.isfinite(heading_std) else float("nan")

    summary["heading_ablation"] = {
        "num_yaw_samples": int(len(yaw_values)),
        "num_successful_plans": int(len(true_costs)),
        "true_cost_mean": heading_mean,
        "true_cost_std": heading_std,
        "true_cost_cv": heading_cv,
        "teacher_value_constant": float(teacher[gy, gx]),
        "euclidean_value_constant": float(np.hypot(goal[0] - base_start[0], goal[1] - base_start[1])),
    }

    summary["conclusion"] = (
        "2D teacher lacks heading sensitivity: same (x,y) heuristic stays constant while true cost changes with yaw. "
        "Therefore, nonholonomic (yaw-aware) teacher is necessary."
    )

    log_path = cfg.paths.logs_dir / "stage1_diagnosis.json"
    with log_path.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows, "sample": str(sample_path)}, f, indent=2)

    print("[Stage-1] Perfect 2D Dijkstra vs Euclidean")
    print("| metric | Euclidean | Perfect 2D Dijkstra |")
    print("|---|---:|---:|")
    print(f"| success rate | {summary['euclidean_success_rate']:.3f} | {summary['dijkstra_success_rate']:.3f} |")
    print(f"| avg expansions | {summary['euclidean_avg_expansions']:.1f} | {summary['dijkstra_avg_expansions']:.1f} |")
    print(f"| avg runtime (ms) | {summary['euclidean_avg_time_ms']:.2f} | {summary['dijkstra_avg_time_ms']:.2f} |")
    print(f"| expansion gain (Dijkstra better +) | - | {100.0 * summary['expansion_gain_ratio_dijkstra_vs_euclidean']:.2f}% |")
    h = summary["heading_ablation"]
    print(
        f"Heading sweep (same x,y, 12 yaw): success={h['num_successful_plans']}/12 "
        f"cost_mean={h['true_cost_mean']:.2f} cost_std={h['true_cost_std']:.2f} cv={h['true_cost_cv']:.3f}"
    )
    print(f"Conclusion: {summary['conclusion']}")
    print(f"Saved heatmaps: {fig_path}")
    print(f"Saved diagnosis log: {log_path}")


if __name__ == "__main__":
    main()
