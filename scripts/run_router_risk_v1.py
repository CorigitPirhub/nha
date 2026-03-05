from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from scripts.evaluate_baselines import _estimate_dual_map_complexity, _route_dual_map_path
from scripts.run_router_diagnosis import _build_args_from_router_config, _default_router_args
from utils.artifact_hash import sha256_file
from utils.parquet_guard import INPUTS_SHA256_FILENAME, write_record


@dataclass(frozen=True)
class RatioBounds:
    fast_min: float
    fast_max: float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-4 risk-constrained router training and evaluation.")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_mixed_v1"))
    p.add_argument("--calib-parquet", type=Path, default=Path("outputs/router_counterfactual_v1_calib.parquet"))
    p.add_argument("--test-parquet", type=Path, default=Path("outputs/router_counterfactual_v1.parquet"))
    p.add_argument(
        "--current-router-config",
        type=Path,
        default=Path("outputs/paper/manual_v11b_dualpath_exp12_v2/logs/experiment_config.json"),
    )
    p.add_argument("--lambda-min", type=float, default=0.0)
    p.add_argument("--lambda-max", type=float, default=80.0)
    p.add_argument("--lambda-steps", type=int, default=321)
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--min-j-improve", type=float, default=0.05)
    p.add_argument("--baseline-for-gate", type=str, default="current_v2", choices=["current_v2", "default_router"])
    p.add_argument("--easy-fast-min", type=float, default=0.85)
    p.add_argument("--easy-fast-max", type=float, default=1.0)
    p.add_argument("--medium-fast-min", type=float, default=0.35)
    p.add_argument("--medium-fast-max", type=float, default=0.75)
    p.add_argument("--hard-fast-min", type=float, default=0.0)
    p.add_argument("--hard-fast-max", type=float, default=0.35)
    p.add_argument("--q-estimators", type=int, default=700)
    p.add_argument("--c-estimators", type=int, default=500)
    p.add_argument("--rf-min-samples-leaf", type=int, default=3)
    p.add_argument("--seed-q", type=int, default=7)
    p.add_argument("--seed-c", type=int, default=11)
    p.add_argument("--beta-cap", type=float, default=200.0)
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_risk_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_risk_v1.md"))
    return p.parse_args()


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_router_args(current_router_config: Path):
    args_default = _default_router_args()
    if not current_router_config.exists():
        return args_default, args_default
    cfg = _read_json(current_router_config)
    router_cfg = cfg.get("router_config", {})
    if not router_cfg:
        return args_default, args_default
    args_current = _build_args_from_router_config(router_cfg)
    return args_default, args_current


def _compute_features(
    dataset_root: Path,
    split: str,
    args_default,
    args_current,
) -> pd.DataFrame:
    index_csv = dataset_root / f"{split}_index.csv"
    split_dir = dataset_root / split
    if not index_csv.exists():
        raise FileNotFoundError(f"Missing split index: {index_csv}")
    if not split_dir.exists():
        raise FileNotFoundError(f"Missing split dir: {split_dir}")

    idx = pd.read_csv(index_csv)
    rows: list[dict] = []
    n = len(idx)
    for i, r in idx.iterrows():
        sample_name = str(r["sample_name"])
        sample_path = split_dir / sample_name
        s = load_grid_sample(sample_path)
        start_xy = (s.start[0], s.start[1])
        goal_xy = (s.goal[0], s.goal[1])

        feat = _estimate_dual_map_complexity(s.occupancy, s.resolution, start_xy, goal_xy, args_default)
        dec_default = _route_dual_map_path(s.occupancy, s.resolution, start_xy, goal_xy, args_default)
        dec_current = _route_dual_map_path(s.occupancy, s.resolution, start_xy, goal_xy, args_current)

        rows.append(
            {
                "sample_name": sample_name,
                "difficulty": str(r["difficulty"]),
                "line_block_ratio": float(feat["line_block_ratio"]),
                "local_occ_ratio": float(feat["local_occ_ratio"]),
                "global_occ_ratio": float(feat["global_occ_ratio"]),
                "distance_ratio": float(feat["distance_ratio"]),
                "complexity_score": float(feat["complexity_score"]),
                "los_clear": float(bool(feat["los_clear"])),
                "use_fast_default": bool(dec_default["route"] == "fast"),
                "use_fast_current": bool(dec_current["route"] == "fast"),
            }
        )
        if (i + 1) % 200 == 0 or (i + 1) == n:
            print(f"[risk_v1] feature build ({split}) {i + 1}/{n}")
    return pd.DataFrame(rows)


def _prepare_frame(
    cf_parquet: Path,
    dataset_root: Path,
    split: str,
    args_default,
    args_current,
    out_dir: Path,
) -> pd.DataFrame:
    if not cf_parquet.exists():
        raise FileNotFoundError(f"Missing counterfactual parquet: {cf_parquet}")
    cf = pd.read_parquet(cf_parquet)
    cache_path = out_dir / f"features_{split}.parquet"
    if cache_path.exists():
        feat = pd.read_parquet(cache_path)
    else:
        feat = _compute_features(dataset_root=dataset_root, split=split, args_default=args_default, args_current=args_current)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        feat.to_parquet(cache_path, index=False)
    df = cf.merge(feat, on=["sample_name", "difficulty"], how="left")
    missing_feat = int(
        df[
            [
                "line_block_ratio",
                "local_occ_ratio",
                "global_occ_ratio",
                "distance_ratio",
                "complexity_score",
                "los_clear",
            ]
        ]
        .isna()
        .sum()
        .sum()
    )
    if missing_feat != 0:
        raise RuntimeError(f"Missing merged features: {missing_feat}")

    for d in ("easy", "medium", "hard"):
        df[f"diff_{d}"] = (df["difficulty"] == d).astype(np.float32)
    return df


def _feature_columns() -> list[str]:
    return [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "diff_easy",
        "diff_medium",
        "diff_hard",
    ]


def _calibrate_beta(calib_df: pd.DataFrame, beta_cap: float) -> tuple[float, float, float]:
    # Risk-aware objective for P4: quality term uses positive relative loss.
    t_ref = float(np.median(calib_df["T_slow_ms"].to_numpy()))
    q_pos = np.maximum(calib_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    non_zero = q_pos[q_pos > 1e-9]
    if non_zero.size == 0:
        beta = 1.0
        q_pos_median = 1.0
    else:
        q_pos_median = float(np.median(non_zero))
        t_norm_median = float(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)))
        beta = float(t_norm_median / max(q_pos_median, 1e-9))
    beta = float(np.clip(beta, 1e-3, max(beta_cap, 1e-3)))
    return t_ref, beta, q_pos_median


def _fit_models(
    calib_df: pd.DataFrame,
    feat_cols: list[str],
    q_estimators: int,
    c_estimators: int,
    min_samples_leaf: int,
    seed_q: int,
    seed_c: int,
    t_ref: float,
) -> tuple[RandomForestRegressor, RandomForestRegressor]:
    x = calib_df[feat_cols].to_numpy(dtype=np.float32)
    y_q = np.maximum(calib_df["q_rel"].to_numpy(dtype=np.float32), 0.0)
    y_c_norm = (calib_df["c"].to_numpy(dtype=np.float32) / max(t_ref, 1e-9)).astype(np.float32)

    q_model = RandomForestRegressor(
        n_estimators=int(q_estimators),
        random_state=int(seed_q),
        min_samples_leaf=int(min_samples_leaf),
        n_jobs=-1,
    )
    c_model = RandomForestRegressor(
        n_estimators=int(c_estimators),
        random_state=int(seed_c),
        min_samples_leaf=int(min_samples_leaf),
        n_jobs=-1,
    )
    q_model.fit(x, y_q)
    c_model.fit(x, y_c_norm)
    return q_model, c_model


def _apply_predictions(df: pd.DataFrame, feat_cols: list[str], q_model, c_model) -> pd.DataFrame:
    x = df[feat_cols].to_numpy(dtype=np.float32)
    out = df.copy()
    out["q_hat_pos"] = np.clip(q_model.predict(x).astype(np.float64), 0.0, None)
    out["c_hat_norm"] = np.clip(c_model.predict(x).astype(np.float64), 0.0, None)
    return out


def _ratio_bounds(args: argparse.Namespace) -> dict[str, RatioBounds]:
    return {
        "easy": RatioBounds(float(args.easy_fast_min), float(args.easy_fast_max)),
        "medium": RatioBounds(float(args.medium_fast_min), float(args.medium_fast_max)),
        "hard": RatioBounds(float(args.hard_fast_min), float(args.hard_fast_max)),
    }


def _enforce_ratio_bounds(
    use_fast: np.ndarray,
    score: np.ndarray,
    difficulty: np.ndarray,
    bounds: dict[str, RatioBounds],
) -> np.ndarray:
    out = use_fast.copy()
    for d, b in bounds.items():
        ids = np.where(difficulty == d)[0]
        n = len(ids)
        if n == 0:
            continue
        n_min = int(math.ceil(max(min(b.fast_min, 1.0), 0.0) * n - 1e-12))
        n_max = int(math.floor(max(min(b.fast_max, 1.0), 0.0) * n + 1e-12))
        n_min = int(np.clip(n_min, 0, n))
        n_max = int(np.clip(n_max, 0, n))
        if n_min > n_max:
            n_min = n_max

        k = int(np.sum(out[ids]))
        if k < n_min:
            slow_ids = ids[~out[ids]]
            if slow_ids.size > 0:
                promote = slow_ids[np.argsort(score[slow_ids])][: (n_min - k)]
                out[promote] = True
        elif k > n_max:
            fast_ids = ids[out[ids]]
            if fast_ids.size > 0:
                demote = fast_ids[np.argsort(score[fast_ids])[::-1]][: (k - n_max)]
                out[demote] = False
    return out


def _route_with_lambda(
    df: pd.DataFrame,
    lam: float,
    bounds: dict[str, RatioBounds],
) -> tuple[np.ndarray, np.ndarray]:
    score = float(lam) * df["q_hat_pos"].to_numpy(dtype=np.float64) - df["c_hat_norm"].to_numpy(dtype=np.float64)
    use_fast = score <= 0.0
    use_fast = _enforce_ratio_bounds(
        use_fast=use_fast,
        score=score,
        difficulty=df["difficulty"].to_numpy(),
        bounds=bounds,
    )
    return use_fast.astype(bool), score


def _eval_policy(
    df: pd.DataFrame,
    use_fast: np.ndarray,
    t_ref: float,
    beta: float,
) -> dict:
    l_fast = df["L_fast"].to_numpy(dtype=np.float64)
    l_slow = df["L_slow"].to_numpy(dtype=np.float64)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)

    l_router = np.where(use_fast, l_fast, l_slow)
    t_router = np.where(use_fast, t_fast, t_slow)
    drel = (l_router - l_slow) / np.maximum(l_slow, 1e-6)
    drel_pos = np.maximum(drel, 0.0)

    j_router = float(np.mean((t_router / max(t_ref, 1e-9)) + float(beta) * drel_pos))

    use_fast_current = df["use_fast_current"].to_numpy(dtype=bool)
    l_current = np.where(use_fast_current, l_fast, l_slow)
    t_current = np.where(use_fast_current, t_fast, t_slow)
    drel_current_pos = np.maximum((l_current - l_slow) / np.maximum(l_slow, 1e-6), 0.0)
    j_current = float(np.mean((t_current / max(t_ref, 1e-9)) + float(beta) * drel_current_pos))

    use_fast_default = df["use_fast_default"].to_numpy(dtype=bool)
    l_default = np.where(use_fast_default, l_fast, l_slow)
    t_default = np.where(use_fast_default, t_fast, t_slow)
    drel_default_pos = np.maximum((l_default - l_slow) / np.maximum(l_slow, 1e-6), 0.0)
    j_default = float(np.mean((t_default / max(t_ref, 1e-9)) + float(beta) * drel_default_pos))

    def _fr(mask: np.ndarray, diff: str) -> float:
        ids = df["difficulty"].to_numpy() == diff
        if not np.any(ids):
            return float("nan")
        return float(np.mean(mask[ids]))

    out = {
        "avg_delta_l_rel": float(np.mean(drel)),
        "violation_rate": float(np.mean(drel > 0.015)),
        "avg_delta_l_rel_pos": float(np.mean(drel_pos)),
        "avg_latency_ms": float(np.mean(t_router)),
        "avg_expansions": float(np.mean(l_router)),
        "fast_ratio": float(np.mean(use_fast)),
        "fast_ratio_by_difficulty": {
            "easy": _fr(use_fast, "easy"),
            "medium": _fr(use_fast, "medium"),
            "hard": _fr(use_fast, "hard"),
        },
        "J_router": j_router,
        "J_current_v2": j_current,
        "J_default_router": j_default,
        "J_improve_vs_current_v2": float((j_current - j_router) / max(abs(j_current), 1e-9)),
        "J_improve_vs_default_router": float((j_default - j_router) / max(abs(j_default), 1e-9)),
    }
    return out


def _ratio_gate(metrics: dict, bounds: dict[str, RatioBounds]) -> bool:
    fr = metrics["fast_ratio_by_difficulty"]
    for d, b in bounds.items():
        v = float(fr.get(d, float("nan")))
        if math.isnan(v):
            return False
        if v < (b.fast_min - 1e-12):
            return False
        if v > (b.fast_max + 1e-12):
            return False
    return True


def _search_lambda(
    calib_df: pd.DataFrame,
    bounds: dict[str, RatioBounds],
    t_ref: float,
    beta: float,
    eps_rel: float,
    min_j_improve: float,
    baseline_for_gate: str,
    lambda_values: np.ndarray,
) -> tuple[float, pd.DataFrame, dict]:
    rows: list[dict] = []
    best_key = None
    best_lambda = float(lambda_values[0])
    best_metrics: dict | None = None

    for lam in lambda_values:
        use_fast, _score = _route_with_lambda(calib_df, float(lam), bounds)
        m = _eval_policy(calib_df, use_fast, t_ref=t_ref, beta=beta)
        j_imp = float(m["J_improve_vs_current_v2"] if baseline_for_gate == "current_v2" else m["J_improve_vs_default_router"])
        risk_ok = bool(m["avg_delta_l_rel"] <= float(eps_rel) + 1e-12)
        ratio_ok = bool(_ratio_gate(m, bounds))
        j_ok = bool(j_imp >= float(min_j_improve) - 1e-12)
        feasible = bool(risk_ok and ratio_ok and j_ok)

        row = {
            "lambda": float(lam),
            "calib_avg_delta_l_rel": float(m["avg_delta_l_rel"]),
            "calib_avg_latency_ms": float(m["avg_latency_ms"]),
            "calib_J_router": float(m["J_router"]),
            "calib_J_improve_vs_current_v2": float(m["J_improve_vs_current_v2"]),
            "calib_J_improve_vs_default_router": float(m["J_improve_vs_default_router"]),
            "calib_fast_ratio_easy": float(m["fast_ratio_by_difficulty"]["easy"]),
            "calib_fast_ratio_medium": float(m["fast_ratio_by_difficulty"]["medium"]),
            "calib_fast_ratio_hard": float(m["fast_ratio_by_difficulty"]["hard"]),
            "calib_risk_ok": bool(risk_ok),
            "calib_ratio_ok": bool(ratio_ok),
            "calib_j_ok": bool(j_ok),
            "calib_feasible": bool(feasible),
        }
        rows.append(row)

        if feasible:
            # Prioritize lower J, then larger improvement.
            key = (
                float(m["J_router"]),
                -float(j_imp),
                float(m["avg_delta_l_rel"]),
                -float(m["fast_ratio"]),
            )
            if (best_key is None) or (key < best_key):
                best_key = key
                best_lambda = float(lam)
                best_metrics = m

    sweep = pd.DataFrame(rows)
    if best_metrics is None:
        # Fallback: choose best risk+ratio candidate with largest J improvement.
        cand = sweep[(sweep["calib_risk_ok"]) & (sweep["calib_ratio_ok"])]
        if cand.empty:
            # Last fallback: maximize J improvement only.
            cand = sweep.copy()
        imp_col = "calib_J_improve_vs_current_v2" if baseline_for_gate == "current_v2" else "calib_J_improve_vs_default_router"
        sel = cand.sort_values(by=[imp_col, "calib_avg_delta_l_rel"], ascending=[False, True]).iloc[0]
        best_lambda = float(sel["lambda"])
        use_fast, _ = _route_with_lambda(calib_df, best_lambda, bounds)
        best_metrics = _eval_policy(calib_df, use_fast, t_ref=t_ref, beta=beta)
    return best_lambda, sweep, best_metrics


def _exp_de_drift_pct(base_csv: Path, new_csv: Path, experiment: str, method: str) -> float:
    if (not base_csv.exists()) or (not new_csv.exists()):
        return float("nan")
    b = pd.read_csv(base_csv)
    n = pd.read_csv(new_csv)
    rb = b[(b["experiment"] == experiment) & (b["method"] == method)]
    rn = n[(n["experiment"] == experiment) & (n["method"] == method)]
    if rb.empty or rn.empty:
        return float("nan")
    eb = float(rb.iloc[0]["avg_expansions"])
    en = float(rn.iloc[0]["avg_expansions"])
    if abs(eb) < 1e-9:
        return float("nan")
    return float((en - eb) / eb * 100.0)


def _save_decisions(path: Path, df: pd.DataFrame, use_fast: np.ndarray, score: np.ndarray, split: str) -> None:
    out = df.copy()
    out["route"] = np.where(use_fast, "fast", "slow")
    out["use_fast"] = use_fast.astype(bool)
    out["score"] = score.astype(np.float64)
    out["split"] = split
    out.to_parquet(path, index=False)


def _to_markdown_report(
    report_path: Path,
    selected_lambda: float,
    beta: float,
    t_ref: float,
    q_pos_median: float,
    calib_metrics: dict,
    test_metrics: dict,
    gate: dict,
    out_dir: Path,
) -> None:
    lines: list[str] = []
    lines.append("# Router Risk V1 (Phase 4)")
    lines.append("")
    lines.append("## Core Setup")
    lines.append(f"- `selected_lambda`: `{selected_lambda:.6f}`")
    lines.append(f"- `T_ref` (median slow latency on calib): `{t_ref:.6f} ms`")
    lines.append(f"- `beta`: `{beta:.6f}` (calibrated by median-scale match)")
    lines.append(f"- `q_pos_median` (calib): `{q_pos_median:.6f}`")
    lines.append("")
    lines.append("## Objective")
    lines.append("- `J = mean(T / T_ref + beta * max(delta_l_rel, 0))`")
    lines.append("- `delta_l_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`")
    lines.append("")
    lines.append("## Metrics")
    lines.append("| split | avg_delta_l_rel | avg_latency_ms | J | J improve vs current_v2 | J improve vs default_router | easy fast | medium fast | hard fast |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for split_name, m in [("calib", calib_metrics), ("test", test_metrics)]:
        fr = m["fast_ratio_by_difficulty"]
        lines.append(
            f"| {split_name} | {m['avg_delta_l_rel']:.6f} | {m['avg_latency_ms']:.6f} | {m['J_router']:.6f} | "
            f"{m['J_improve_vs_current_v2'] * 100.0:.3f}% | {m['J_improve_vs_default_router'] * 100.0:.3f}% | "
            f"{fr['easy']:.4f} | {fr['medium']:.4f} | {fr['hard']:.4f} |"
        )
    lines.append("")
    lines.append("## Gate Check (P4)")
    for k, v in gate.items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Artifacts")
    lines.append(f"- `{out_dir / 'policy_metrics.json'}`")
    lines.append(f"- `{out_dir / 'calib_sweep.csv'}`")
    lines.append(f"- `{out_dir / 'calib_decisions.parquet'}`")
    lines.append(f"- `{out_dir / 'test_decisions.parquet'}`")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    calib_sha = sha256_file(Path(args.calib_parquet))
    test_sha = sha256_file(Path(args.test_parquet))

    args_default, args_current = _load_router_args(args.current_router_config)
    calib_df = _prepare_frame(
        cf_parquet=args.calib_parquet,
        dataset_root=args.dataset_root,
        split="calib",
        args_default=args_default,
        args_current=args_current,
        out_dir=out_dir,
    )
    test_df = _prepare_frame(
        cf_parquet=args.test_parquet,
        dataset_root=args.dataset_root,
        split="test",
        args_default=args_default,
        args_current=args_current,
        out_dir=out_dir,
    )

    t_ref, beta, q_pos_median = _calibrate_beta(calib_df, beta_cap=float(args.beta_cap))
    feat_cols = _feature_columns()
    q_model, c_model = _fit_models(
        calib_df=calib_df,
        feat_cols=feat_cols,
        q_estimators=int(args.q_estimators),
        c_estimators=int(args.c_estimators),
        min_samples_leaf=int(args.rf_min_samples_leaf),
        seed_q=int(args.seed_q),
        seed_c=int(args.seed_c),
        t_ref=t_ref,
    )
    calib_pred = _apply_predictions(calib_df, feat_cols, q_model=q_model, c_model=c_model)
    test_pred = _apply_predictions(test_df, feat_cols, q_model=q_model, c_model=c_model)

    bounds = _ratio_bounds(args)
    lambda_values = np.linspace(float(args.lambda_min), float(args.lambda_max), int(args.lambda_steps), dtype=np.float64)
    selected_lambda, sweep_df, calib_metrics = _search_lambda(
        calib_df=calib_pred,
        bounds=bounds,
        t_ref=t_ref,
        beta=beta,
        eps_rel=float(args.epsilon_rel),
        min_j_improve=float(args.min_j_improve),
        baseline_for_gate=str(args.baseline_for_gate),
        lambda_values=lambda_values,
    )

    use_fast_calib, score_calib = _route_with_lambda(calib_pred, selected_lambda, bounds)
    use_fast_test, score_test = _route_with_lambda(test_pred, selected_lambda, bounds)
    test_metrics = _eval_policy(test_pred, use_fast_test, t_ref=t_ref, beta=beta)

    # Exp3/Exp4 drift checks against frozen manual_v11b reference.
    exp3_drift = _exp_de_drift_pct(
        base_csv=ROOT / "outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv",
        new_csv=ROOT / "outputs/paper/manual_v11b_dualpath_exp3_full/exp_results_summary.csv",
        experiment="exp3_ablation",
        method="Full",
    )
    exp4_drift = _exp_de_drift_pct(
        base_csv=ROOT / "outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv",
        new_csv=ROOT / "outputs/paper/manual_v11b_dualpath_exp4_fair/exp_results_summary.csv",
        experiment="exp4_public_kinodynamic",
        method="Ours",
    )
    exp_drift_ok = bool(
        (not math.isnan(exp3_drift))
        and (not math.isnan(exp4_drift))
        and (abs(exp3_drift) <= 0.5 + 1e-12)
        and (abs(exp4_drift) <= 0.5 + 1e-12)
    )

    j_imp_gate_value = float(
        test_metrics["J_improve_vs_current_v2"]
        if str(args.baseline_for_gate) == "current_v2"
        else test_metrics["J_improve_vs_default_router"]
    )
    gate = {
        "avg_delta_l_rel_le_1_5pct": bool(test_metrics["avg_delta_l_rel"] <= float(args.epsilon_rel) + 1e-12),
        "J_improve_ge_5pct": bool(j_imp_gate_value >= float(args.min_j_improve) - 1e-12),
        "stratified_fast_ratio_target": bool(_ratio_gate(test_metrics, bounds)),
        "exp3_exp4_abs_dE_drift_le_0_5pct": bool(exp_drift_ok),
    }

    sweep_csv = out_dir / "calib_sweep.csv"
    sweep_df.to_csv(sweep_csv, index=False)
    _save_decisions(out_dir / "calib_decisions.parquet", calib_pred, use_fast_calib, score_calib, split="calib")
    _save_decisions(out_dir / "test_decisions.parquet", test_pred, use_fast_test, score_test, split="test")

    metrics = {
        "version": "router_risk_v1",
        "inputs": {
            "dataset_root": str(Path(args.dataset_root)),
            "calib_parquet": str(Path(args.calib_parquet)),
            "test_parquet": str(Path(args.test_parquet)),
            "calib_parquet_sha256": str(calib_sha),
            "test_parquet_sha256": str(test_sha),
            "current_router_config": str(Path(args.current_router_config)),
            "current_router_config_sha256": sha256_file(Path(args.current_router_config))
            if Path(args.current_router_config).exists()
            else "",
        },
        "objective": {
            "name": "risk_constrained_normalized",
            "formula": "J = mean(T/T_ref + beta * max(delta_l_rel, 0))",
            "delta_l_rel": "(L_router - L_slow_ref) / max(L_slow_ref, 1e-6)",
            "T_ref_calib_median_slow_ms": float(t_ref),
            "beta": float(beta),
            "beta_calibration": "median-scale match between T_norm and positive delta_l_rel on calib",
            "q_pos_median_on_calib": float(q_pos_median),
        },
        "search": {
            "lambda_min": float(args.lambda_min),
            "lambda_max": float(args.lambda_max),
            "lambda_steps": int(args.lambda_steps),
            "selected_lambda": float(selected_lambda),
            "baseline_for_gate": str(args.baseline_for_gate),
        },
        "constraints": {
            "epsilon_rel": float(args.epsilon_rel),
            "min_j_improve": float(args.min_j_improve),
            "fast_ratio_bounds": {
                k: {"fast_min": float(v.fast_min), "fast_max": float(v.fast_max)}
                for k, v in bounds.items()
            },
        },
        "calib_metrics": calib_metrics,
        "test_metrics": test_metrics,
        "exp_drift": {
            "exp3_full_dE_drift_pct": float(exp3_drift),
            "exp4_ours_dE_drift_pct": float(exp4_drift),
        },
        "phase4_gate_check": gate,
        "artifacts": {
            "calib_sweep_csv": str(sweep_csv),
            "calib_decisions_parquet": str(out_dir / "calib_decisions.parquet"),
            "test_decisions_parquet": str(out_dir / "test_decisions.parquet"),
            "features_calib_parquet": str(out_dir / "features_calib.parquet"),
            "features_test_parquet": str(out_dir / "features_test.parquet"),
        },
    }
    metrics_path = out_dir / "policy_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_record(
        out_dir / INPUTS_SHA256_FILENAME,
        {
            "calib_parquet": Path(args.calib_parquet),
            "test_parquet": Path(args.test_parquet),
        },
        sha256_map={"calib_parquet": calib_sha, "test_parquet": test_sha},
    )

    _to_markdown_report(
        report_path=args.report_md,
        selected_lambda=selected_lambda,
        beta=beta,
        t_ref=t_ref,
        q_pos_median=q_pos_median,
        calib_metrics=calib_metrics,
        test_metrics=test_metrics,
        gate=gate,
        out_dir=out_dir,
    )

    print(f"[risk_v1] selected_lambda={selected_lambda:.6f}")
    print(f"[risk_v1] test metrics: delta_l_rel={test_metrics['avg_delta_l_rel']:.6f}, "
          f"J_improve_vs_{args.baseline_for_gate}={j_imp_gate_value * 100.0:.3f}%")
    print(f"[risk_v1] phase4_gate_check={gate}")
    print(f"[risk_v1] metrics={metrics_path}")
    print(f"[risk_v1] report={args.report_md}")


if __name__ == "__main__":
    main()
