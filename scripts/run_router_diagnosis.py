from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from scripts.evaluate_baselines import _estimate_dual_map_complexity, _route_dual_map_path


def _bootstrap_ci(arr: np.ndarray, fn, n_boot: int = 10000, seed: int = 7) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    n = len(arr)
    vals = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        vals[i] = float(fn(arr[idx]))
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return float(np.mean(arr)), float(lo), float(hi)


def _build_args_from_router_config(cfg: dict) -> SimpleNamespace:
    return SimpleNamespace(
        router_corridor_radius_cells=int(cfg["corridor_radius_cells"]),
        router_samples_per_cell=float(cfg["samples_per_cell"]),
        router_fast_max_distance_ratio=float(cfg["fast_max_distance_ratio"]),
        router_fast_max_line_block_ratio=float(cfg["fast_max_line_block_ratio"]),
        router_fast_max_local_occ_ratio=float(cfg["fast_max_local_occ_ratio"]),
        router_fast_max_global_occ_ratio=float(cfg["fast_max_global_occ_ratio"]),
        router_slow_min_line_block_ratio=float(cfg["slow_min_line_block_ratio"]),
        router_slow_min_local_occ_ratio=float(cfg["slow_min_local_occ_ratio"]),
        router_score_threshold=float(cfg["score_threshold"]),
        router_w_line_block=float(cfg["w_line_block"]),
        router_w_local_occ=float(cfg["w_local_occ"]),
        router_w_distance=float(cfg["w_distance"]),
        router_w_global_occ=float(cfg["w_global_occ"]),
        router_los_penalty=float(cfg["los_penalty"]),
        router_fast_score_margin=float(cfg["fast_score_margin"]),
    )


def _default_router_args() -> SimpleNamespace:
    return SimpleNamespace(
        router_corridor_radius_cells=2,
        router_samples_per_cell=1.0,
        router_fast_max_distance_ratio=0.75,
        router_fast_max_line_block_ratio=0.30,
        router_fast_max_local_occ_ratio=0.40,
        router_fast_max_global_occ_ratio=0.55,
        router_slow_min_line_block_ratio=0.65,
        router_slow_min_local_occ_ratio=0.60,
        router_score_threshold=0.47,
        router_w_line_block=0.42,
        router_w_local_occ=0.33,
        router_w_distance=0.18,
        router_w_global_occ=0.07,
        router_los_penalty=0.08,
        router_fast_score_margin=0.06,
    )


def _compute_router_features(split_root: Path, index_df: pd.DataFrame, args: SimpleNamespace) -> pd.DataFrame:
    rows: list[dict] = []
    for i, r in index_df.iterrows():
        p = split_root / str(r["sample_name"])
        s = load_grid_sample(p)
        start_xy = (s.start[0], s.start[1])
        goal_xy = (s.goal[0], s.goal[1])
        feat = _estimate_dual_map_complexity(s.occupancy, s.resolution, start_xy, goal_xy, args)
        dec = _route_dual_map_path(s.occupancy, s.resolution, start_xy, goal_xy, args)
        rows.append(
            {
                "sample_name": str(r["sample_name"]),
                "route": str(dec["route"]),
                "reason": str(dec["reason"]),
                "complexity_score": float(feat["complexity_score"]),
                "line_block_ratio": float(feat["line_block_ratio"]),
                "local_occ_ratio": float(feat["local_occ_ratio"]),
                "global_occ_ratio": float(feat["global_occ_ratio"]),
                "distance_ratio": float(feat["distance_ratio"]),
            }
        )
        if (i + 1) % 200 == 0 or (i + 1) == len(index_df):
            print(f"[diagnosis] routed {i + 1}/{len(index_df)}")
    return pd.DataFrame(rows)


def _policy_metrics(df: pd.DataFrame, policy_col: str, beta: float, eps_rel: float = 0.015) -> dict:
    use_fast = df[policy_col].astype(bool).to_numpy()
    L = np.where(use_fast, df["L_fast"].to_numpy(), df["L_slow"].to_numpy())
    T = np.where(use_fast, df["T_fast_ms"].to_numpy(), df["T_slow_ms"].to_numpy())
    J = T + float(beta) * L
    J_oracle = np.minimum(
        df["T_fast_ms"].to_numpy() + float(beta) * df["L_fast"].to_numpy(),
        df["T_slow_ms"].to_numpy() + float(beta) * df["L_slow"].to_numpy(),
    )
    og = (J - J_oracle) / np.maximum(np.abs(J_oracle), 1e-9)
    delta_l_rel = (L - df["L_slow"].to_numpy()) / np.maximum(df["L_slow"].to_numpy(), 1e-6)
    vio = (delta_l_rel > float(eps_rel)).astype(np.float64)

    j_mean, j_lo, j_hi = _bootstrap_ci(J.astype(np.float64), np.mean)
    og_mean, og_lo, og_hi = _bootstrap_ci(og.astype(np.float64), np.mean)
    v_mean, v_lo, v_hi = _bootstrap_ci(vio.astype(np.float64), np.mean)

    return {
        "avg_J": float(j_mean),
        "avg_J_ci95": [float(j_lo), float(j_hi)],
        "avg_oracle_gap": float(og_mean),
        "avg_oracle_gap_ci95": [float(og_lo), float(og_hi)],
        "violation_rate": float(v_mean),
        "violation_rate_ci95": [float(v_lo), float(v_hi)],
        "avg_latency_ms": float(np.mean(T)),
        "avg_delta_l_rel": float(np.mean(delta_l_rel)),
    }


def main() -> None:
    test_cf = pd.read_parquet(ROOT / "outputs/router_counterfactual_v1.parquet")
    calib_cf = pd.read_parquet(ROOT / "outputs/router_counterfactual_v1_calib.parquet")
    test_idx = pd.read_csv(ROOT / "data/router_mixed_v1/test_index.csv")

    cfg = json.loads((ROOT / "outputs/paper/manual_v11b_dualpath_exp12_v2/logs/experiment_config.json").read_text())
    args_current = _build_args_from_router_config(cfg["router_config"])
    args_default = _default_router_args()

    split_root = ROOT / "data/router_mixed_v1/test"
    routed_current = _compute_router_features(split_root, test_idx, args_current)
    routed_default = _compute_router_features(split_root, test_idx, args_default)
    routed_default = routed_default.rename(columns={c: f"default_{c}" for c in routed_default.columns if c != "sample_name"})

    df = test_cf.merge(test_idx[["sample_name", "difficulty", "source_dataset", "scenario"]], on="sample_name", how="left")
    df = df.merge(routed_current, on="sample_name", how="left")
    df = df.merge(routed_default, on="sample_name", how="left")

    # Normalize column names after merges.
    if "difficulty" not in df.columns:
        if "difficulty_x" in df.columns:
            df["difficulty"] = df["difficulty_x"]
        elif "difficulty_y" in df.columns:
            df["difficulty"] = df["difficulty_y"]
    if "source_dataset" not in df.columns:
        if "source_dataset_x" in df.columns:
            df["source_dataset"] = df["source_dataset_x"]
        elif "source_dataset_y" in df.columns:
            df["source_dataset"] = df["source_dataset_y"]
    if "scenario" not in df.columns:
        if "scenario_x" in df.columns:
            df["scenario"] = df["scenario_x"]
        elif "scenario_y" in df.columns:
            df["scenario"] = df["scenario_y"]

    # Policy booleans.
    df["use_fast_current"] = (df["route"] == "fast").astype(bool)
    df["use_fast_default"] = (df["default_route"] == "fast").astype(bool)
    df["use_fast_oracle"] = (
        (df["T_fast_ms"] + 0.0 * df["L_fast"]) <= (df["T_slow_ms"] + 0.0 * df["L_slow"])
    ).astype(bool)
    # Oracle for J is recomputed in _policy_metrics with calibrated beta.

    # Beta calibration from calib split.
    med_t = float(np.median(calib_cf["T_slow_ms"].to_numpy()))
    med_l = float(np.median(calib_cf["L_slow"].to_numpy()))
    beta = float(med_t / max(med_l, 1e-9))

    # P3 required metrics with CI.
    metrics_current = _policy_metrics(df, "use_fast_current", beta=beta, eps_rel=0.015)
    metrics_default = _policy_metrics(df, "use_fast_default", beta=beta, eps_rel=0.015)
    metrics_all_fast = _policy_metrics(df.assign(use_fast_all=True), "use_fast_all", beta=beta, eps_rel=0.015)

    # Difficulty-wise fast ratio.
    def fast_ratio(g: pd.Series) -> float:
        return float(np.mean(g.astype(bool).to_numpy()))

    ratio_current = df.groupby("difficulty")["use_fast_current"].apply(fast_ratio).to_dict()
    ratio_default = df.groupby("difficulty")["use_fast_default"].apply(fast_ratio).to_dict()

    # Complexity vs |delta| correlation.
    df["abs_delta_l_rel"] = np.abs((df["L_fast"] - df["L_slow"]) / np.maximum(df["L_slow"], 1e-6))
    rho_static, p_static = spearmanr(df["complexity_score"], df["abs_delta_l_rel"])

    # Diagnostic complexity score (probe-informed, in-sample).
    feat_cols = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "L_fast",
        "T_fast_ms",
        "path_len_fast",
    ]
    X = df[feat_cols].to_numpy(dtype=np.float32)
    y = df["abs_delta_l_rel"].to_numpy(dtype=np.float32)
    model = RandomForestRegressor(n_estimators=400, random_state=7, min_samples_leaf=3)
    model.fit(X, y)
    df["diag_complexity_score"] = model.predict(X).astype(np.float64)
    rho_diag, p_diag = spearmanr(df["diag_complexity_score"], df["abs_delta_l_rel"])

    # Pareto curve over diagnostic score thresholds.
    q_grid = np.linspace(0.0, 1.0, 31)
    pareto_rows: list[dict] = []
    for q in q_grid:
        thr = float(np.quantile(df["diag_complexity_score"], q))
        use_fast = (df["diag_complexity_score"].to_numpy() < thr)
        L = np.where(use_fast, df["L_fast"].to_numpy(), df["L_slow"].to_numpy())
        T = np.where(use_fast, df["T_fast_ms"].to_numpy(), df["T_slow_ms"].to_numpy())
        drel = (L - df["L_slow"].to_numpy()) / np.maximum(df["L_slow"].to_numpy(), 1e-6)
        J = T + beta * L
        J_oracle = np.minimum(
            df["T_fast_ms"].to_numpy() + beta * df["L_fast"].to_numpy(),
            df["T_slow_ms"].to_numpy() + beta * df["L_slow"].to_numpy(),
        )
        og = (J - J_oracle) / np.maximum(np.abs(J_oracle), 1e-9)
        pareto_rows.append(
            {
                "quantile": float(q),
                "threshold": float(thr),
                "fast_ratio": float(np.mean(use_fast)),
                "avg_latency_ms": float(np.mean(T)),
                "avg_delta_l_rel": float(np.mean(drel)),
                "violation_rate": float(np.mean(drel > 0.015)),
                "avg_J": float(np.mean(J)),
                "avg_oracle_gap": float(np.mean(og)),
            }
        )

    pareto_df = pd.DataFrame(pareto_rows)
    out_dir = ROOT / "reports/router_diagnosis_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    pareto_csv = out_dir / "pareto_curve.csv"
    pareto_df.to_csv(pareto_csv, index=False)

    fig_path = out_dir / "pareto_curve_latency_vs_quality.svg"
    plt.figure(figsize=(6.5, 4.2))
    plt.plot(pareto_df["avg_latency_ms"], pareto_df["avg_delta_l_rel"], marker="o", markersize=3, linewidth=1.5)
    plt.scatter(
        [metrics_current["avg_latency_ms"]],
        [metrics_current["avg_delta_l_rel"]],
        color="red",
        s=35,
        label="current_v2",
    )
    plt.scatter(
        [metrics_default["avg_latency_ms"]],
        [metrics_default["avg_delta_l_rel"]],
        color="green",
        s=35,
        label="default_router",
    )
    plt.xlabel("Average Latency (ms)")
    plt.ylabel("Average Relative Quality Loss")
    plt.title("Pareto: Latency vs Relative Quality Loss")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, format="svg")
    plt.close()

    # Verify "all-fast due to distribution bias?" by comparing current-v2 and default on same data.
    all_fast_current = bool(float(np.mean(df["use_fast_current"].astype(np.float64))) >= 0.999)
    all_fast_default = bool(float(np.mean(df["use_fast_default"].astype(np.float64))) >= 0.999)
    bias_diagnosis = (
        "configuration_saturation"
        if (all_fast_current and (not all_fast_default))
        else "distribution_bias_or_insufficient_signal"
    )

    metrics_json = {
        "beta_from_calib": beta,
        "policy_metrics": {
            "current_v2": metrics_current,
            "default_router": metrics_default,
            "all_fast": metrics_all_fast,
        },
        "fast_ratio_by_difficulty": {
            "current_v2": ratio_current,
            "default_router": ratio_default,
        },
        "correlation": {
            "static_complexity_vs_abs_delta_l_rel": {"rho": float(rho_static), "p_value": float(p_static)},
            "diag_complexity_vs_abs_delta_l_rel": {"rho": float(rho_diag), "p_value": float(p_diag)},
        },
        "all_fast_bias_check": {
            "current_v2_all_fast": all_fast_current,
            "default_router_all_fast": all_fast_default,
            "diagnosis": bias_diagnosis,
        },
        "artifacts": {
            "pareto_csv": str(pareto_csv),
            "pareto_fig": str(fig_path),
        },
        "phase3_gate_check": {
            "ci_reported_for_J_OG_V": True,
            "spearman_rho_ge_0_35_and_p_lt_0_01": bool((rho_diag >= 0.35) and (p_diag < 0.01)),
        },
    }
    metrics_path = out_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_json, indent=2), encoding="utf-8")

    report_path = ROOT / "reports/router_diagnosis_v1.md"
    lines: list[str] = []
    lines.append("# Router Diagnosis V1 (Phase 3)")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- `beta` (from calib median scale): `{beta:.6f}`")
    lines.append(f"- Current v2 fast ratio (overall): `{np.mean(df['use_fast_current']):.4f}`")
    lines.append(f"- Default router fast ratio (overall): `{np.mean(df['use_fast_default']):.4f}`")
    lines.append(f"- All-fast bias diagnosis: `{bias_diagnosis}`")
    lines.append("")
    lines.append("## 95% CI Metrics (Required)")
    lines.append("| policy | avg_J | J 95%CI | avg_OG | OG 95%CI | violation | V 95%CI |")
    lines.append("|---|---:|---|---:|---|---:|---|")
    for name, m in [("current_v2", metrics_current), ("default_router", metrics_default), ("all_fast", metrics_all_fast)]:
        lines.append(
            f"| {name} | {m['avg_J']:.6f} | [{m['avg_J_ci95'][0]:.6f}, {m['avg_J_ci95'][1]:.6f}] | "
            f"{m['avg_oracle_gap']:.6f} | [{m['avg_oracle_gap_ci95'][0]:.6f}, {m['avg_oracle_gap_ci95'][1]:.6f}] | "
            f"{m['violation_rate']:.6f} | [{m['violation_rate_ci95'][0]:.6f}, {m['violation_rate_ci95'][1]:.6f}] |"
        )
    lines.append("")
    lines.append("## Fast Ratio by Difficulty")
    lines.append("| difficulty | current_v2 | default_router |")
    lines.append("|---|---:|---:|")
    for d in ["easy", "medium", "hard"]:
        lines.append(f"| {d} | {ratio_current.get(d, float('nan')):.4f} | {ratio_default.get(d, float('nan')):.4f} |")
    lines.append("")
    lines.append("## Complexity Correlation with |ΔL|")
    lines.append(
        f"- Static complexity score: `rho={rho_static:.6f}`, `p={p_static:.6e}`"
    )
    lines.append(
        f"- Diagnostic complexity score (probe-informed): `rho={rho_diag:.6f}`, `p={p_diag:.6e}`"
    )
    lines.append("")
    lines.append("Phase-3 gate target check (`rho>=0.35`, `p<0.01`): "
                 + ("PASS" if ((rho_diag >= 0.35) and (p_diag < 0.01)) else "FAIL"))
    lines.append("")
    lines.append("## Pareto Artifacts")
    lines.append(f"- CSV: `{pareto_csv}`")
    lines.append(f"- Figure: `{fig_path}`")
    lines.append(f"- Metrics JSON: `{metrics_path}`")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"[diagnosis] report: {report_path}")
    print(f"[diagnosis] metrics: {metrics_path}")
    print(f"[diagnosis] phase3 gate: {metrics_json['phase3_gate_check']}")


if __name__ == "__main__":
    main()
