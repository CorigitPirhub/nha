from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from network.inference import NeuralHeuristicPredictor
from scripts.evaluate_baselines import _astar_grid, _euclidean_field, _path_length, _resolve_2d_heuristic


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase23 mid-net pilot: evaluate a smaller neural arm as `mid` vs frozen fast/slow.")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--split", type=str, default="test", choices=["calib", "test"])
    p.add_argument("--ref-calib-parquet", type=Path, default=Path("outputs/router_phase9_bench_v1/common/router_counterfactual_calib.parquet"))
    p.add_argument("--ref-test-parquet", type=Path, default=Path("outputs/router_phase9_bench_v1/common/router_counterfactual_test.parquet"))
    p.add_argument("--mid-checkpoint", type=Path, default=Path("outputs/router_phase23_midnet_tinyunet_b32_ctx_v1/checkpoints/heuristic_net.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--standard-base-mode", type=str, default="euclidean", choices=["euclidean", "rs"])
    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)

    p.add_argument("--max-cases", type=int, default=200)
    p.add_argument("--seed", type=int, default=7)

    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase23_midnet_arm_pilot_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase23_midnet_arm_pilot_v1.md"))
    return p.parse_args()


def _calibrate_beta_from_ref(calib_df: pd.DataFrame, *, beta_cap: float = 200.0) -> tuple[float, float]:
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


def _wilson_ci95(k: int, n: int, *, alpha: float) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    z = float(NormalDist().inv_cdf(1.0 - float(alpha) / 2.0))
    phat = float(k / n)
    den = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / den
    half = (z * np.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)) / den
    return float(max(0.0, center - half)), float(min(1.0, center + half))


def _write_report(path: Path, stats: dict) -> None:
    lines: list[str] = []
    lines.append("# Phase23 Mid-Net Arm Pilot (v1)")
    lines.append("")
    lines.append("This pilot evaluates a smaller neural planner arm (`mid`) against the frozen Phase-9 fast/slow counterfactual tables.")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Date: `{stats['date']}`")
    lines.append(f"- Mid checkpoint: `{stats['mid_checkpoint']}`")
    lines.append(f"- Cases: `{stats['num_cases']}` (pilot subset)")
    lines.append(f"- RNG seed: `{stats['seed']}`")
    lines.append(f"- Device: `{stats['device']}`")
    lines.append(f"- `epsilon_rel`: `{stats['epsilon_rel']}`")
    lines.append(f"- `alpha`: `{stats['alpha']}`")
    lines.append(f"- `T_ref` (median slow calib): `{stats['t_ref_ms']:.6f} ms`")
    lines.append(f"- `beta` (risk-aware, from calib): `{stats['beta']:.6f}`")
    lines.append("")
    lines.append("## Aggregate Points (test subset)")
    lines.append(pd.DataFrame(stats["points"]).to_markdown(index=False))
    lines.append("")
    lines.append("## Mid Arm Diagnostics")
    for k, v in stats["mid_diag"].items():
        lines.append(f"- `{k}`: `{v}`")
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

    # Sample pilot cases from reference test parquet.
    rng = np.random.default_rng(int(args.seed))
    all_names = ref_test["sample_name"].astype(str).tolist()
    if not all_names:
        raise RuntimeError(f"Empty reference test parquet: {args.ref_test_parquet}")
    n = int(min(max(int(args.max_cases), 1), len(all_names)))
    pick = rng.choice(np.asarray(all_names, dtype=object), size=n, replace=False)
    pick_set = set(str(x) for x in pick.tolist())
    sub = ref_test[ref_test["sample_name"].astype(str).isin(pick_set)].copy()
    sub = sub.sort_values("sample_name").reset_index(drop=True)

    predictor_mid = NeuralHeuristicPredictor(args.mid_checkpoint, device=str(args.device))

    rows: list[dict] = []
    for i, r in enumerate(sub.itertuples(index=False), start=1):
        sample_name = str(getattr(r, "sample_name"))
        p = args.dataset_root / str(args.split) / sample_name
        if not p.exists():
            raise FileNotFoundError(p)
        s = load_grid_sample(p)
        start = (float(s.start[0]), float(s.start[1]), float(s.start[2]))
        goal = (float(s.goal[0]), float(s.goal[1]), float(s.goal[2]))

        # Mid inference + A*.
        t_mid0 = time.perf_counter()
        base_override = None
        if predictor_mid.prediction_mode == "residual" and str(args.standard_base_mode).lower() == "euclidean":
            base_override = _euclidean_field(
                occupancy=s.occupancy,
                goal_xy=(goal[0], goal[1]),
                resolution=float(s.resolution),
                fill_value=1e6,
            )
        pred = predictor_mid.predict_field(
            occupancy=s.occupancy,
            esdf=np.zeros_like(s.occupancy, dtype=np.float32),
            start=start,
            goal=goal,
            resolution=float(s.resolution),
            base_field_override=base_override,
        )
        infer_mid_ms = float((time.perf_counter() - t_mid0) * 1000.0)
        h_mid = _resolve_2d_heuristic(pred, s.occupancy)

        res = _astar_grid(
            occupancy=s.occupancy,
            resolution=float(s.resolution),
            start_xy=(start[0], start[1]),
            goal_xy=(goal[0], goal[1]),
            max_expansions=int(args.grid_max_expansions),
            heuristic_map=h_mid,
            heuristic_weight=1.0,
            record_expanded=False,
        )
        l_mid = float(res["expansions"])
        search_mid_ms = float(res["runtime_ms"])
        t_mid_ms = float(infer_mid_ms + search_mid_ms)
        path_len_mid = float(_path_length(res.get("path", [])))

        rows.append(
            {
                "sample_name": sample_name,
                "difficulty": str(getattr(r, "difficulty")),
                "ood_family": int(getattr(r, "ood_family")),
                "L_fast": float(getattr(r, "L_fast")),
                "T_fast_ms": float(getattr(r, "T_fast_ms")),
                "path_len_fast": float(getattr(r, "path_len_fast")),
                "L_slow": float(getattr(r, "L_slow")),
                "T_slow_ms": float(getattr(r, "T_slow_ms")),
                "path_len_slow": float(getattr(r, "path_len_slow")),
                "L_mid": float(l_mid),
                "T_mid_ms": float(t_mid_ms),
                "infer_mid_ms": float(infer_mid_ms),
                "search_mid_ms": float(search_mid_ms),
                "path_len_mid": float(path_len_mid),
                "mid_success": bool(res["success"]),
            }
        )

        if i % 50 == 0 or i == len(sub):
            print(f"[phase23-midnet-pilot] processed {i}/{len(sub)}")

    df = pd.DataFrame(rows)
    out_parquet = args.out_dir / "pilot_midnet_counterfactual_test.parquet"
    df.to_parquet(out_parquet, index=False)

    points: list[dict] = []
    points.append({"arm": "always_fast", **_arm_point(df, arm_L="L_fast", arm_T="T_fast_ms", epsilon_rel=args.epsilon_rel, t_ref=t_ref, beta=beta)})
    points.append({"arm": "always_midnet", **_arm_point(df, arm_L="L_mid", arm_T="T_mid_ms", epsilon_rel=args.epsilon_rel, t_ref=t_ref, beta=beta)})
    points.append({"arm": "always_slow_ref", **_arm_point(df, arm_L="L_slow", arm_T="T_slow_ms", epsilon_rel=args.epsilon_rel, t_ref=t_ref, beta=beta)})

    # Mid diagnostics.
    q_rel_mid = (df["L_mid"].to_numpy(dtype=np.float64) - df["L_slow"].to_numpy(dtype=np.float64)) / np.maximum(
        df["L_slow"].to_numpy(dtype=np.float64), 1e-6
    )
    vio_mid = q_rel_mid > float(args.epsilon_rel)
    k = int(np.sum(vio_mid))
    n = int(len(vio_mid))
    ci_lo, ci_hi = _wilson_ci95(k, n, alpha=float(args.alpha))
    path_ratio = df["path_len_mid"].to_numpy(dtype=np.float64) / np.maximum(df["path_len_fast"].to_numpy(dtype=np.float64), 1e-9)
    mid_diag = {
        "mid_success_rate": float(np.mean(df["mid_success"].to_numpy(dtype=bool))),
        "mid_infer_ms_mean": float(np.mean(df["infer_mid_ms"].to_numpy(dtype=np.float64))),
        "mid_search_ms_mean": float(np.mean(df["search_mid_ms"].to_numpy(dtype=np.float64))),
        "mid_path_len_ratio_vs_fast_mean": float(np.mean(path_ratio[np.isfinite(path_ratio)])),
        "mid_path_len_ratio_vs_fast_p99": float(np.quantile(path_ratio[np.isfinite(path_ratio)], 0.99)),
        "mid_violation_ci95": [float(ci_lo), float(ci_hi)],
    }

    # Oracle complementarity.
    def _j_vals(L_col: str, T_col: str) -> np.ndarray:
        l = df[L_col].to_numpy(dtype=np.float64)
        t = df[T_col].to_numpy(dtype=np.float64)
        l_slow = df["L_slow"].to_numpy(dtype=np.float64)
        drel_pos = np.maximum((l - l_slow) / np.maximum(l_slow, 1e-6), 0.0)
        return (t / max(t_ref, 1e-9)) + float(beta) * drel_pos

    j_fast = _j_vals("L_fast", "T_fast_ms")
    j_mid = _j_vals("L_mid", "T_mid_ms")
    j_slow = _j_vals("L_slow", "T_slow_ms")
    arr = np.stack([j_fast, j_mid, j_slow], axis=0)
    best_idx = np.argmin(arr, axis=0)
    best = arr[best_idx, np.arange(arr.shape[1])]
    oracle = [
        {
            "oracle_set": "{fast,slow}",
            "J_oracle_mean": float(np.mean(np.minimum(j_fast, j_slow))),
        },
        {
            "oracle_set": "{fast,mid,slow}",
            "J_oracle_mean": float(np.mean(best)),
            "share_fast": float(np.mean(best_idx == 0)),
            "share_mid": float(np.mean(best_idx == 1)),
            "share_slow": float(np.mean(best_idx == 2)),
        },
    ]

    stats = {
        "date": time.strftime("%Y-%m-%d"),
        "seed": int(args.seed),
        "device": str(args.device),
        "mid_checkpoint": str(args.mid_checkpoint),
        "num_cases": int(len(df)),
        "epsilon_rel": float(args.epsilon_rel),
        "alpha": float(args.alpha),
        "t_ref_ms": float(t_ref),
        "beta": float(beta),
        "points": points,
        "mid_diag": mid_diag,
        "oracle": oracle,
        "runtime_s": float(time.perf_counter() - t0),
        "artifacts": {
            "pilot_midnet_counterfactual_test_parquet": str(out_parquet),
        },
    }
    (args.out_dir / "stats.json").write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    _write_report(args.report_md, stats)
    print(f"[phase23-midnet-pilot] done in {stats['runtime_s']:.3f}s")


if __name__ == "__main__":
    main()

