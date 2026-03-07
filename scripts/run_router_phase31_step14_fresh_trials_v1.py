from __future__ import annotations

import argparse
import json
import math
import sys
import time
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import ndimage
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from scripts.evaluate_baselines import _path_length
from scripts.run_router_phase8_strict import _split_calib_train_val, _wilson_ci
from scripts.run_router_phase29_step12r4_trials_v1 import (
    ArmCache,
    _build_feature_matrices,
    _build_weight_tables,
    _is_feasible,
    _load_p5_decisions,
    _make_fastgeom_tables,
    _objective_from_calib_train,
    _parse_weights,
    _pooled_stats,
    _selection_metrics,
    _summarize_seed,
    _weight_tag,
)
from scripts.run_router_phase30_step14_trials_v1 import (
    FamilyResult,
    SeedContext,
    _arm_space,
    _attach_head_to_head,
    _evaluate_test_for_family,
    _jsonable,
    _neighbors8,
    _pair_features,
    _parse_float_list,
    _parse_int_list,
    _report_summary,
    _representative_failures,
    _reshape_armwise,
    _stable_quantile,
    _world_to_grid,
    _write_candidate_artifacts,
)


def _upper_resid_quantile(*, y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    resid = np.maximum(np.asarray(y_pred, dtype=np.float64) - np.asarray(y_true, dtype=np.float64), 0.0)
    n = int(resid.size)
    if n <= 0:
        return 0.0
    level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / max(n, 1))
    return _stable_quantile(resid, level)


DIFFICULTIES = ("easy", "medium", "hard")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step14 fresh strict trial runner (E/F/G/H).")
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--strict-phase9-root", type=Path, default=Path("outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak"))
    p.add_argument("--weights", type=str, default="1.00,1.05,1.10,1.15,1.20,1.25,1.35")
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--calib-train-frac", type=float, default=0.60)
    p.add_argument("--calib-split-seed", type=int, default=20260306)
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument("--path-rel-mean-max", type=float, default=0.01)
    p.add_argument("--path-rel-p95-max", type=float, default=0.05)
    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--fastgeom-max-expansions", type=int, default=50000)
    p.add_argument("--fastgeom-corridor-radius-cells", type=int, default=2)
    p.add_argument("--max-cases", type=int, default=-1)
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase31_step14_fresh_trials_v1.md"))
    p.add_argument("--summary-json", type=Path, default=Path("outputs/router_phase31_step14_fresh_trials_v1/summary.json"))
    p.add_argument("--e-max-depths", type=str, default="2,3")
    p.add_argument("--e-learning-rates", type=str, default="0.05,0.10")
    p.add_argument("--e-max-iters", type=str, default="100,160")
    p.add_argument("--e-gain-alphas", type=str, default="0.20,0.10,0.05")
    p.add_argument("--e-path-guards", type=str, default="0.02,0.04")
    p.add_argument("--f-n-clusters", type=str, default="2,3,4")
    p.add_argument("--f-max-depths", type=str, default="2,3")
    p.add_argument("--f-learning-rates", type=str, default="0.05,0.10")
    p.add_argument("--f-max-iters", type=str, default="120,200")
    p.add_argument("--f-uncertainty-thresholds", type=str, default="0.55,0.75,0.90")
    p.add_argument("--g-lambdas", type=str, default="0.20,0.35")
    p.add_argument("--g-clearance-quantiles", type=str, default="0.50,0.65")
    p.add_argument("--g-line-sigmas", type=str, default="3.0")
    p.add_argument("--h-aggressive-weights", type=str, default="1.25,1.35")
    p.add_argument("--h-balanced-weight", type=float, default=1.20)
    p.add_argument("--h-cautious-weights", type=str, default="1.05")
    p.add_argument("--h-check-every", type=int, default=32)
    p.add_argument("--h-dup-high", type=str, default="0.55,0.70")
    p.add_argument("--h-progress-low", type=str, default="0.002,0.005")
    return p.parse_args()


def _parse_seeds(raw: str) -> list[int]:
    return [int(x.strip()) for x in str(raw).split(",") if x.strip()]


def _build_common_tables(args: argparse.Namespace, weights: list[float]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Path]]:
    out_root = ROOT / "outputs/router_phase31_step14_fresh_trials_v1"
    out_root.mkdir(parents=True, exist_ok=True)
    weight_cal_pq, weight_test_pq = _build_weight_tables(args, out_root, weights)
    fastgeom_cal_pq, fastgeom_test_pq = _make_fastgeom_tables(args, out_root)
    strict_root = Path(args.strict_phase9_root)
    calib_cf = strict_root / "common" / "router_counterfactual_calib.parquet"
    test_cf = strict_root / "common" / "router_counterfactual_test.parquet"
    static_cal = strict_root / "common" / "risk" / "features_calib.parquet"
    static_test = strict_root / "common" / "risk" / "features_test.parquet"
    calib = pd.read_parquet(calib_cf).merge(pd.read_parquet(static_cal), on=["sample_name", "difficulty"], how="inner")
    calib = calib.merge(pd.read_parquet(weight_cal_pq), on=["sample_name", "difficulty"], how="inner")
    calib = calib.merge(pd.read_parquet(fastgeom_cal_pq), on=["sample_name", "difficulty"], how="inner")
    test = pd.read_parquet(test_cf).merge(pd.read_parquet(static_test), on=["sample_name", "difficulty"], how="inner")
    test = test.merge(pd.read_parquet(weight_test_pq), on=["sample_name", "difficulty"], how="inner")
    test = test.merge(pd.read_parquet(fastgeom_test_pq), on=["sample_name", "difficulty"], how="inner")
    inputs = {
        "counterfactual_calib": calib_cf,
        "counterfactual_test": test_cf,
        "risk_features_calib": static_cal,
        "risk_features_test": static_test,
        "wastar_calib": weight_cal_pq,
        "wastar_test": weight_test_pq,
        "fastgeom_calib": fastgeom_cal_pq,
        "fastgeom_test": fastgeom_test_pq,
    }
    return calib, test, inputs


def _p5_j(cache: ArmCache, use_fast: np.ndarray) -> np.ndarray:
    return np.where(np.asarray(use_fast, dtype=bool), cache.arms["fast"]["J"], cache.arms["slow"]["J"]).astype(np.float64)


def _build_seed_contexts(args: argparse.Namespace, calib: pd.DataFrame, test: pd.DataFrame, weights: list[float]) -> dict[int, SeedContext]:
    ctxs: dict[int, SeedContext] = {}
    arm_space = _arm_space(weights)
    for seed in _parse_seeds(args.seeds):
        p5_cal = _load_p5_decisions(args.strict_phase9_root, seed, "calib")
        p5_test = _load_p5_decisions(args.strict_phase9_root, seed, "test")
        cal = calib.merge(p5_cal, on="sample_name", how="inner")
        te = test.merge(p5_test, on="sample_name", how="inner")
        cal_train, cal_val, _ = _split_calib_train_val(cal, train_frac=float(args.calib_train_frac), seed=int(args.calib_split_seed) + int(seed))
        t_ref, beta = _objective_from_calib_train(cal_train)
        cache_train = ArmCache(cal_train, weights, t_ref=t_ref, beta=beta)
        cache_val = ArmCache(cal_val, weights, t_ref=t_ref, beta=beta)
        cache_test = ArmCache(te, weights, t_ref=t_ref, beta=beta)
        x_train, x_val, x_test = _build_feature_matrices(cal_train, cal_val, te)
        ctxs[int(seed)] = SeedContext(
            seed=int(seed),
            cal_train=cal_train,
            cal_val=cal_val,
            test=te,
            cache_train=cache_train,
            cache_val=cache_val,
            cache_test=cache_test,
            x_train=x_train,
            x_val=x_val,
            x_test=x_test,
            t_ref=float(t_ref),
            beta=float(beta),
            arm_space=list(arm_space),
            j_p5_val=_p5_j(cache_val, cal_val["use_fast_p5"].to_numpy(dtype=bool)),
            j_p5_test=_p5_j(cache_test, te["use_fast_p5"].to_numpy(dtype=bool)),
        )
    return ctxs


def _fit_baselines(ctxs: dict[int, SeedContext], args: argparse.Namespace) -> dict[str, dict[int, dict[str, Any]]]:
    from scripts.run_router_phase30_step14_trials_v1 import _fit_baselines as _fit_baselines_phase30

    return _fit_baselines_phase30(ctxs, args)


def _representative_failures_dynamic(df: pd.DataFrame, selected: np.ndarray, j_array: np.ndarray, p5_j: np.ndarray, *, topk: int = 15) -> pd.DataFrame:
    delta = np.asarray(p5_j, dtype=np.float64) - np.asarray(j_array, dtype=np.float64)
    return pd.DataFrame(
        {
            "sample_name": df["sample_name"].astype(str),
            "difficulty": df["difficulty"].astype(str),
            "selected_arm": np.asarray(selected, dtype=str),
            "delta_j_vs_p5": delta,
        }
    ).sort_values("delta_j_vs_p5", ascending=True).head(int(topk)).reset_index(drop=True)


def _family_gate_from_val_fresh(result: FamilyResult) -> dict[str, Any]:
    h2h = result.head_to_head_val
    unique_arms = sorted({str(k) for row in result.seed_rows_val for k, v in row.get("arm_distribution", {}).items() if float(v) > 1e-12})
    dominant = 0.0
    for row in result.seed_rows_val:
        ad = row.get("arm_distribution", {})
        if isinstance(ad, dict) and ad:
            dominant = max(dominant, max(float(v) for v in ad.values()))
    gate = {
        "risk_ci95_upper_le_alpha_all_seeds": bool(all(float(r["violation_ci95_upper"]) <= float(args_global.alpha) + 1e-12 for r in result.seed_rows_val)),
        "path_audit_hold_all_seeds": bool(all(float(r["path_rel_mean"]) <= float(args_global.path_rel_mean_max) + 1e-12 and float(r["path_rel_p95"]) <= float(args_global.path_rel_p95_max) + 1e-12 for r in result.seed_rows_val)),
        "beats_M_on_val_mean": bool(float(h2h["M"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_N_on_val_mean": bool(float(h2h["N"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_O_on_val_mean": bool(float(h2h["O"]["pooled"]["mean_delta_j"]) > 0.0),
        "unique_arms": unique_arms,
        "dominant_arm_fraction_max": float(dominant),
    }
    if result.key in {"E", "F"}:
        gate["not_constantized"] = bool((len(unique_arms) >= 3) and (float(dominant) < 0.95))
    if result.key == "G":
        avg_field_std = float(np.mean([float(r.get("field_std_mean", 0.0)) for r in result.seed_rows_val]))
        gate["avg_field_std"] = avg_field_std
        gate["not_trivial_field"] = bool(avg_field_std > 0.03)
    if result.key == "H":
        avg_switch = float(np.mean([float(r.get("switch_rate", 0.0)) for r in result.seed_rows_val]))
        avg_state_div = float(np.mean([float(r.get("state_diversity", 0.0)) for r in result.seed_rows_val]))
        gate["avg_switch_rate"] = avg_switch
        gate["avg_state_diversity"] = avg_state_div
        gate["not_trivial_schedule"] = bool((avg_switch > 0.05) and (avg_state_div > 0.5))
    result.gate_check_val = gate
    return gate


def _advance_family_fresh(result: FamilyResult) -> bool:
    gate = result.gate_check_val
    base_ok = bool(gate.get("risk_ci95_upper_le_alpha_all_seeds", False) and gate.get("path_audit_hold_all_seeds", False) and gate.get("beats_M_on_val_mean", False) and gate.get("beats_N_on_val_mean", False) and gate.get("beats_O_on_val_mean", False))
    if result.key in {"E", "F"}:
        base_ok = base_ok and bool(gate.get("not_constantized", False))
    if result.key == "G":
        base_ok = base_ok and bool(gate.get("not_trivial_field", False))
    if result.key == "H":
        base_ok = base_ok and bool(gate.get("not_trivial_schedule", False))
    return bool(base_ok)


def _arm_index_map(arm_space: list[str]) -> dict[str, int]:
    return {str(a): i for i, a in enumerate(arm_space)}


def _predict_carl(state: dict[str, Any], x_df: pd.DataFrame, arm_space: list[str], eps_rel: float) -> np.ndarray:
    n = len(x_df)
    k = len(arm_space)
    pair_x, _ = _pair_features(x_df, arm_space)
    d_pred = _reshape_armwise(state["model_d"].predict(pair_x), n, k)
    p_pred = _reshape_armwise(state["model_p"].predict(pair_x), n, k)
    d_u = np.maximum.accumulate(d_pred, axis=1) + np.asarray(state["q_d"], dtype=np.float64)[None, :]
    p_u = np.maximum.accumulate(p_pred, axis=1) + np.asarray(state["q_p"], dtype=np.float64)[None, :]
    gain_u_cols = []
    for idx, model in enumerate(state["gain_models"]):
        gain_u_cols.append(np.asarray(model.predict(x_df), dtype=np.float64) + float(state["q_gain"][idx]))
    gain_u = np.stack(gain_u_cols, axis=1) if gain_u_cols else np.zeros((n, 0), dtype=np.float64)
    selected_idx = np.zeros(n, dtype=np.int64)
    for i in range(n):
        cur = 0
        for j in range(k - 1):
            if float(gain_u[i, j]) < 0.0 and float(d_u[i, j + 1]) <= float(eps_rel) and float(p_u[i, j + 1]) <= float(state["path_guard"]):
                cur = j + 1
            else:
                break
        selected_idx[i] = int(cur)
    return np.asarray([arm_space[int(i)] for i in selected_idx], dtype=str)


def _eval_family_E(ctxs: dict[int, SeedContext], args: argparse.Namespace) -> tuple[FamilyResult, dict[int, dict[str, Any]], pd.DataFrame | None]:
    out_dir = ROOT / "outputs/router_phase31_step14_e_carl_wa_v1"
    seed_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None
    depths = _parse_int_list(args.e_max_depths)
    lrs = _parse_float_list(args.e_learning_rates)
    max_iters = _parse_int_list(args.e_max_iters)
    gain_alphas = _parse_float_list(args.e_gain_alphas)
    path_guards = _parse_float_list(args.e_path_guards)
    for seed, ctx in ctxs.items():
        j_train = np.stack([ctx.cache_train.arms[a]["J"] for a in ctx.arm_space], axis=1)
        gain_train = j_train[:, 1:] - j_train[:, :-1]
        pair_train_x, _ = _pair_features(ctx.x_train, ctx.arm_space)
        y_d = np.concatenate([ctx.cache_train.arms[a]["drel"] for a in ctx.arm_space]).astype(np.float64)
        y_p = np.concatenate([ctx.cache_train.arms[a]["path_rel"] for a in ctx.arm_space]).astype(np.float64)
        best = None
        for depth in depths:
            for lr in lrs:
                for max_iter in max_iters:
                    model_d = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed) + 13)
                    model_p = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed) + 29)
                    model_d.fit(pair_train_x, y_d)
                    model_p.fit(pair_train_x, y_p)
                    d_pred_train = _reshape_armwise(model_d.predict(pair_train_x), len(ctx.x_train), len(ctx.arm_space))
                    p_pred_train = _reshape_armwise(model_p.predict(pair_train_x), len(ctx.x_train), len(ctx.arm_space))
                    gain_models = []
                    gain_train_pred = []
                    for j in range(len(ctx.arm_space) - 1):
                        model = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed) + 101 + int(j) * 17)
                        model.fit(ctx.x_train, gain_train[:, j])
                        gain_models.append(model)
                        gain_train_pred.append(np.asarray(model.predict(ctx.x_train), dtype=np.float64))
                    for gain_alpha in gain_alphas:
                        q_gain = [
                            _upper_resid_quantile(y_true=gain_train[:, j], y_pred=gain_train_pred[j], alpha=float(gain_alpha))
                            for j in range(len(ctx.arm_space) - 1)
                        ]
                        q_d = [
                            _upper_resid_quantile(y_true=ctx.cache_train.arms[a]["drel"], y_pred=d_pred_train[:, idx], alpha=float(gain_alpha))
                            for idx, a in enumerate(ctx.arm_space)
                        ]
                        q_p = [
                            _upper_resid_quantile(y_true=ctx.cache_train.arms[a]["path_rel"], y_pred=p_pred_train[:, idx], alpha=float(gain_alpha))
                            for idx, a in enumerate(ctx.arm_space)
                        ]
                        for path_guard in path_guards:
                            state = {
                                "gain_models": gain_models,
                                "model_d": model_d,
                                "model_p": model_p,
                                "q_gain": q_gain,
                                "q_d": q_d,
                                "q_p": q_p,
                                "path_guard": float(path_guard),
                            }
                            selected_val = _predict_carl(state, ctx.x_val, ctx.arm_space, float(args.epsilon_rel))
                            metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
                            ablation_rows.append(
                                {
                                    "seed": int(seed),
                                    "depth": int(depth),
                                    "learning_rate": float(lr),
                                    "max_iter": int(max_iter),
                                    "gain_alpha": float(gain_alpha),
                                    "path_guard": float(path_guard),
                                    "J_mean_val": float(metrics_val["J_mean"]),
                                    "violation_ci95_upper": float(metrics_val["violation_ci95_upper"]),
                                    "path_rel_mean": float(metrics_val["path_rel_mean"]),
                                    "path_rel_p95": float(metrics_val["path_rel_p95"]),
                                    "unique_arms": int(sum(float(v) > 1e-12 for v in metrics_val["arm_distribution"].values())),
                                }
                            )
                            if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                                continue
                            if best is None or float(metrics_val["J_mean"]) < float(best["metrics_val"]["J_mean"]):
                                best_state = dict(state)
                                best_state["selected_test"] = _predict_carl(state, ctx.x_test, ctx.arm_space, float(args.epsilon_rel))
                                best = {
                                    "state": best_state,
                                    "params": {"depth": int(depth), "learning_rate": float(lr), "max_iter": int(max_iter), "gain_alpha": float(gain_alpha), "path_guard": float(path_guard)},
                                    "selected_val": selected_val,
                                    "metrics_val": metrics_val,
                                }
        if best is None:
            selected_val = np.asarray(["fast"] * len(ctx.cal_val), dtype=str)
            best = {
                "state": {"selected_test": np.asarray(["fast"] * len(ctx.test), dtype=str)},
                "params": {"fallback": "all_fast"},
                "selected_val": selected_val,
                "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha)),
            }
        row, _ = _summarize_seed(seed=seed, test_metrics=best["metrics_val"], j_p5_test=ctx.j_p5_val, selected_test=best["selected_val"], method_name="CARL-WA(val)", policy_desc=best["params"])
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(best["metrics_val"]["J_array"], dtype=np.float64)
        seed_states[seed] = best
        if failure_df is None:
            failure_df = _representative_failures(ctx.cal_val, best["selected_val"], ctx.cache_val, ctx.j_p5_val)
    pooled = _pooled_stats(np.concatenate([ctxs[s].j_p5_val - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key="E", name="CARL-WA", out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": "CARL-WA"})
    return result, seed_states, failure_df


def _response_embedding(cache: ArmCache, arm_space: list[str]) -> np.ndarray:
    j = np.stack([cache.arms[a]["J"] for a in arm_space], axis=1)
    d = np.stack([cache.arms[a]["drel"] for a in arm_space], axis=1)
    p = np.stack([cache.arms[a]["path_rel"] for a in arm_space], axis=1)
    return np.concatenate([j[:, 1:] - j[:, [0]], d[:, 1:], p[:, 1:]], axis=1).astype(np.float64)


def _choose_regime_arms(ctx: SeedContext, labels: np.ndarray, arm_space: list[str]) -> tuple[dict[int, str], str]:
    global_arm = None
    for arm in arm_space:
        metrics = _selection_metrics(ctx.cache_train, np.asarray([arm] * len(ctx.cal_train), dtype=str), eps_rel=float(args_global.epsilon_rel), alpha=float(args_global.alpha))
        if not _is_feasible(metrics, alpha=float(args_global.alpha), path_rel_mean_max=float(args_global.path_rel_mean_max), path_rel_p95_max=float(args_global.path_rel_p95_max)):
            continue
        if global_arm is None or float(metrics["J_mean"]) < float(global_arm[1]):
            global_arm = (arm, float(metrics["J_mean"]))
    fallback_arm = str(global_arm[0] if global_arm is not None else "fast")
    regime_to_arm: dict[int, str] = {}
    for regime in sorted(set(int(x) for x in labels.tolist())):
        mask = labels == int(regime)
        if int(np.sum(mask)) <= 0:
            regime_to_arm[int(regime)] = fallback_arm
            continue
        best_arm = fallback_arm
        best_mean = float("inf")
        for arm in arm_space:
            mean_j = float(np.mean(ctx.cache_train.arms[arm]["J"][mask]))
            if mean_j < best_mean:
                best_mean = mean_j
                best_arm = arm
        regime_to_arm[int(regime)] = best_arm
    return regime_to_arm, fallback_arm


def _predict_tarp(state: dict[str, Any], x_df: pd.DataFrame, arm_space: list[str]) -> np.ndarray:
    probs_raw = state["clf"].predict_proba(x_df)
    n = len(x_df)
    n_regimes = int(state["n_regimes"])
    probs = np.zeros((n, n_regimes), dtype=np.float64)
    classes = state["clf"].classes_.astype(int)
    probs[:, classes] = probs_raw
    arm_rank = _arm_index_map(arm_space)
    selected = []
    for i in range(n):
        max_p = float(np.max(probs[i])) if n_regimes > 0 else 0.0
        keep = np.where(probs[i] >= float(state["tau"]) * max(max_p, 1e-12))[0]
        if keep.size <= 0:
            selected.append(str(state["fallback_arm"]))
            continue
        candidate_arms = [str(state["regime_to_arm"][int(r)]) for r in keep]
        chosen = min(candidate_arms, key=lambda a: arm_rank.get(str(a), 10**9))
        selected.append(str(chosen))
    return np.asarray(selected, dtype=str)


def _eval_family_F(ctxs: dict[int, SeedContext], args: argparse.Namespace) -> tuple[FamilyResult, dict[int, dict[str, Any]], pd.DataFrame | None]:
    out_dir = ROOT / "outputs/router_phase31_step14_f_tarp_wa_v1"
    seed_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None
    n_clusters_list = _parse_int_list(args.f_n_clusters)
    depths = _parse_int_list(args.f_max_depths)
    lrs = _parse_float_list(args.f_learning_rates)
    max_iters = _parse_int_list(args.f_max_iters)
    taus = _parse_float_list(args.f_uncertainty_thresholds)
    for seed, ctx in ctxs.items():
        emb_train = _response_embedding(ctx.cache_train, ctx.arm_space)
        mean = np.mean(emb_train, axis=0)
        std = np.std(emb_train, axis=0) + 1e-6
        emb_train_z = (emb_train - mean[None, :]) / std[None, :]
        best = None
        for n_clusters in n_clusters_list:
            kmeans = KMeans(n_clusters=int(n_clusters), n_init=10, random_state=int(seed))
            labels_train = kmeans.fit_predict(emb_train_z)
            regime_to_arm, fallback_arm = _choose_regime_arms(ctx, labels_train, ctx.arm_space)
            for depth in depths:
                for lr in lrs:
                    for max_iter in max_iters:
                        clf = HistGradientBoostingClassifier(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed) + 401)
                        clf.fit(ctx.x_train, labels_train)
                        for tau in taus:
                            state = {
                                "clf": clf,
                                "tau": float(tau),
                                "n_regimes": int(n_clusters),
                                "regime_to_arm": regime_to_arm,
                                "fallback_arm": fallback_arm,
                            }
                            selected_val = _predict_tarp(state, ctx.x_val, ctx.arm_space)
                            metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
                            ablation_rows.append(
                                {
                                    "seed": int(seed),
                                    "n_clusters": int(n_clusters),
                                    "depth": int(depth),
                                    "learning_rate": float(lr),
                                    "max_iter": int(max_iter),
                                    "tau": float(tau),
                                    "J_mean_val": float(metrics_val["J_mean"]),
                                    "violation_ci95_upper": float(metrics_val["violation_ci95_upper"]),
                                    "path_rel_mean": float(metrics_val["path_rel_mean"]),
                                    "path_rel_p95": float(metrics_val["path_rel_p95"]),
                                    "unique_arms": int(sum(float(v) > 1e-12 for v in metrics_val["arm_distribution"].values())),
                                }
                            )
                            if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                                continue
                            if best is None or float(metrics_val["J_mean"]) < float(best["metrics_val"]["J_mean"]):
                                best_state = dict(state)
                                best_state["selected_test"] = _predict_tarp(state, ctx.x_test, ctx.arm_space)
                                best = {
                                    "state": best_state,
                                    "params": {"n_clusters": int(n_clusters), "depth": int(depth), "learning_rate": float(lr), "max_iter": int(max_iter), "tau": float(tau), "regime_to_arm": regime_to_arm, "fallback_arm": fallback_arm},
                                    "selected_val": selected_val,
                                    "metrics_val": metrics_val,
                                }
        if best is None:
            selected_val = np.asarray(["fast"] * len(ctx.cal_val), dtype=str)
            best = {
                "state": {"selected_test": np.asarray(["fast"] * len(ctx.test), dtype=str)},
                "params": {"fallback": "all_fast"},
                "selected_val": selected_val,
                "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha)),
            }
        row, _ = _summarize_seed(seed=seed, test_metrics=best["metrics_val"], j_p5_test=ctx.j_p5_val, selected_test=best["selected_val"], method_name="TARP-WA(val)", policy_desc=best["params"])
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(best["metrics_val"]["J_array"], dtype=np.float64)
        seed_states[seed] = best
        if failure_df is None:
            failure_df = _representative_failures(ctx.cal_val, best["selected_val"], ctx.cache_val, ctx.j_p5_val)
    pooled = _pooled_stats(np.concatenate([ctxs[s].j_p5_val - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key="F", name="TARP-WA", out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": "TARP-WA"})
    return result, seed_states, failure_df


def _line_distance_map(height: int, width: int, resolution: float, start_xy: tuple[float, float], goal_xy: tuple[float, float]) -> np.ndarray:
    xs = (np.arange(width, dtype=np.float64) + 0.5) * float(resolution)
    ys = (np.arange(height, dtype=np.float64) + 0.5) * float(resolution)
    xx, yy = np.meshgrid(xs, ys)
    ax, ay = float(start_xy[0]), float(start_xy[1])
    bx, by = float(goal_xy[0]), float(goal_xy[1])
    vx = bx - ax
    vy = by - ay
    denom = max(vx * vx + vy * vy, 1e-9)
    wx = xx - ax
    wy = yy - ay
    t = np.clip((wx * vx + wy * vy) / denom, 0.0, 1.0)
    qx = ax + t * vx
    qy = ay + t * vy
    return np.sqrt((xx - qx) ** 2 + (yy - qy) ** 2).astype(np.float32)


def _build_cpsf_bonus(occupancy: np.ndarray, resolution: float, start_xy: tuple[float, float], goal_xy: tuple[float, float], *, lambda_scale: float, clearance_quantile: float, line_sigma_m: float) -> np.ndarray:
    clearance = ndimage.distance_transform_edt((~occupancy).astype(np.uint8)).astype(np.float32) * float(resolution)
    free = clearance[~occupancy]
    thr = float(np.quantile(free, float(np.clip(clearance_quantile, 0.05, 0.95)))) if free.size > 0 else float(resolution)
    openness = np.clip((clearance - thr) / max(thr, 1e-6), 0.0, 1.0)
    line_dist = _line_distance_map(occupancy.shape[0], occupancy.shape[1], float(resolution), start_xy, goal_xy)
    line_align = np.exp(-np.square(line_dist) / max(2.0 * float(line_sigma_m) * float(line_sigma_m), 1e-6))
    bonus = float(lambda_scale) * openness * line_align
    bonus = np.clip(bonus, 0.0, 0.35).astype(np.float32)
    bonus[occupancy] = 0.0
    return bonus


def _grid_to_world(ix: int, iy: int, resolution: float) -> tuple[float, float]:
    return ((ix + 0.5) * resolution, (iy + 0.5) * resolution)


def _astar_grid_cpsf(occupancy: np.ndarray, resolution: float, start_xy: tuple[float, float], goal_xy: tuple[float, float], max_expansions: int, *, lambda_scale: float, clearance_quantile: float, line_sigma_m: float) -> dict[str, Any]:
    import heapq

    t0 = time.perf_counter()
    h, w = occupancy.shape
    bonus = _build_cpsf_bonus(occupancy, resolution, start_xy, goal_xy, lambda_scale=float(lambda_scale), clearance_quantile=float(clearance_quantile), line_sigma_m=float(line_sigma_m))
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)
    if occupancy[sy, sx] or occupancy[gy, gx]:
        return {"success": False, "expansions": 0, "runtime_ms": (time.perf_counter() - t0) * 1000.0, "path": [], "field_std": float(np.std(bonus[~occupancy])) if np.any(~occupancy) else 0.0}

    def h_fn(ix: int, iy: int) -> float:
        return math.hypot((gx - ix) * resolution, (gy - iy) * resolution)

    start = (sx, sy)
    goal = (gx, gy)
    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    g_cost: dict[tuple[int, int], float] = {start: 0.0}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    counter = 0
    heapq.heappush(open_heap, ((1.0 + float(bonus[sy, sx])) * h_fn(sx, sy), 0.0, counter, start))
    expansions = 0
    nbrs = _neighbors8()
    expanded_nodes: list[tuple[int, int]] = []
    while open_heap and expansions < max(int(max_expansions), 1):
        _, g, _, node = heapq.heappop(open_heap)
        if g > g_cost.get(node, float("inf")) + 1e-9:
            continue
        expansions += 1
        x, y = node
        expanded_nodes.append((x, y))
        if node == goal:
            path_grid: list[tuple[int, int]] = []
            cur = node
            while cur is not None:
                path_grid.append(cur)
                cur = parent.get(cur)
            path_grid.reverse()
            path_xy = [_grid_to_world(ix, iy, resolution) for ix, iy in path_grid]
            exp_bonus = np.asarray([bonus[iy, ix] for ix, iy in expanded_nodes], dtype=np.float64) if expanded_nodes else np.zeros(1, dtype=np.float64)
            return {
                "success": True,
                "expansions": expansions,
                "runtime_ms": (time.perf_counter() - t0) * 1000.0,
                "path": path_xy,
                "field_std": float(np.std(exp_bonus)),
            }
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
            nf = ng + (1.0 + float(bonus[ny, nx])) * h_fn(nx, ny)
            heapq.heappush(open_heap, (nf, ng, counter, nkey))
    exp_bonus = np.asarray([bonus[iy, ix] for ix, iy in expanded_nodes], dtype=np.float64) if expanded_nodes else np.asarray([np.std(bonus[~occupancy]) if np.any(~occupancy) else 0.0], dtype=np.float64)
    return {"success": False, "expansions": expansions, "runtime_ms": (time.perf_counter() - t0) * 1000.0, "path": [], "field_std": float(np.std(exp_bonus))}


def _cpsf_config_grid(args: argparse.Namespace) -> list[dict[str, Any]]:
    cfgs: list[dict[str, Any]] = []
    for lam in _parse_float_list(args.g_lambdas):
        for cq in _parse_float_list(args.g_clearance_quantiles):
            for sigma in _parse_float_list(args.g_line_sigmas):
                tag = f"cpsf_l{int(round(lam * 100)):03d}_q{int(round(cq * 100)):02d}_s{int(round(sigma * 10)):03d}"
                cfgs.append({"tag": tag, "lambda_scale": float(lam), "clearance_quantile": float(cq), "line_sigma_m": float(sigma)})
    return cfgs


def _build_cpsf_tables(args: argparse.Namespace, *, include_test: bool) -> tuple[Path, Path | None, list[dict[str, Any]]]:
    out_dir = ROOT / "outputs/router_phase31_step14_g_cpsf_wa_v1" / "common"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfgs = _cpsf_config_grid(args)
    cal_path = out_dir / "cpsf_calib.parquet"
    test_path = out_dir / "cpsf_test.parquet"

    def _ensure(split: str, out_path: Path) -> None:
        if out_path.exists():
            try:
                df = pd.read_parquet(out_path)
                need = {f"L_{cfg['tag']}" for cfg in cfgs} | {f"T_{cfg['tag']}_ms" for cfg in cfgs} | {f"path_len_{cfg['tag']}" for cfg in cfgs} | {f"field_std_{cfg['tag']}" for cfg in cfgs}
                if need.issubset(set(df.columns.tolist())):
                    return
            except Exception:
                pass
        idx = pd.read_csv(Path(args.dataset_root) / f"{split}_index.csv")
        if int(args.max_cases) > 0 and int(args.max_cases) < len(idx):
            idx = idx.sample(n=int(args.max_cases), random_state=20260316 if split == "calib" else 20260317).sort_values("sample_name").reset_index(drop=True)
        rows: list[dict[str, Any]] = []
        split_dir = Path(args.dataset_root) / split
        total = len(idx)
        for i, row in idx.iterrows():
            sample = load_grid_sample(split_dir / str(row["sample_name"]))
            meta: dict[str, Any] = {"sample_name": str(row["sample_name"]), "difficulty": str(row["difficulty"])}
            start_xy = (float(sample.start[0]), float(sample.start[1]))
            goal_xy = (float(sample.goal[0]), float(sample.goal[1]))
            for cfg in cfgs:
                res = _astar_grid_cpsf(sample.occupancy, float(sample.resolution), start_xy, goal_xy, int(args.grid_max_expansions), lambda_scale=float(cfg["lambda_scale"]), clearance_quantile=float(cfg["clearance_quantile"]), line_sigma_m=float(cfg["line_sigma_m"]))
                tag = cfg["tag"]
                meta[f"success_{tag}"] = bool(res["success"])
                meta[f"L_{tag}"] = float(res["expansions"])
                meta[f"T_{tag}_ms"] = float(res["runtime_ms"])
                meta[f"path_len_{tag}"] = float(_path_length(res.get("path", [])))
                meta[f"field_std_{tag}"] = float(res.get("field_std", 0.0))
            rows.append(meta)
            if (i + 1) % 200 == 0 or (i + 1) == total:
                print(f"[step14-g] {split} processed {i + 1}/{total}")
        pd.DataFrame(rows).to_parquet(out_path, index=False)

    _ensure("calib", cal_path)
    if include_test:
        _ensure("test", test_path)
        return cal_path, test_path, cfgs
    return cal_path, None, cfgs


def _astar_grid_ceta(occupancy: np.ndarray, resolution: float, start_xy: tuple[float, float], goal_xy: tuple[float, float], max_expansions: int, *, aggressive_weight: float, balanced_weight: float, cautious_weight: float, check_every: int, dup_high: float, progress_low: float) -> dict[str, Any]:
    import heapq

    t0 = time.perf_counter()
    h, w = occupancy.shape
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)
    if occupancy[sy, sx] or occupancy[gy, gx]:
        return {"success": False, "expansions": 0, "runtime_ms": (time.perf_counter() - t0) * 1000.0, "path": [], "switch_rate": 0.0, "state_diversity": 0.0}

    def h_fn(ix: int, iy: int) -> float:
        return math.hypot((gx - ix) * resolution, (gy - iy) * resolution)

    weights = {0: float(cautious_weight), 1: float(balanced_weight), 2: float(aggressive_weight)}
    state = 1
    state_visits = {0: 0, 1: 0, 2: 0}
    switches = 0
    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    g_cost: dict[tuple[int, int], float] = {(sx, sy): 0.0}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {(sx, sy): None}
    counter = 0
    h0 = h_fn(sx, sy)
    best_h = h0
    last_best_h = h0
    generated_win = 0
    duplicate_win = 0
    heapq.heappush(open_heap, (weights[state] * h0, 0.0, counter, (sx, sy)))
    expansions = 0
    nbrs = _neighbors8()
    while open_heap and expansions < max(int(max_expansions), 1):
        _, g, _, node = heapq.heappop(open_heap)
        if g > g_cost.get(node, float("inf")) + 1e-9:
            continue
        expansions += 1
        state_visits[state] += 1
        x, y = node
        best_h = min(best_h, h_fn(x, y))
        if node == (gx, gy):
            path_grid: list[tuple[int, int]] = []
            cur = node
            while cur is not None:
                path_grid.append(cur)
                cur = parent.get(cur)
            path_grid.reverse()
            path_xy = [_grid_to_world(ix, iy, resolution) for ix, iy in path_grid]
            checks = max(expansions / max(int(check_every), 1), 1.0)
            return {
                "success": True,
                "expansions": expansions,
                "runtime_ms": (time.perf_counter() - t0) * 1000.0,
                "path": path_xy,
                "switch_rate": float(switches / checks),
                "state_diversity": float(sum(int(v > 0) for v in state_visits.values()) / 3.0),
            }
        if expansions % max(int(check_every), 1) == 0:
            dup_ratio = float(duplicate_win / max(generated_win, 1))
            progress = float((last_best_h - best_h) / max(h0, 1e-9))
            if dup_ratio > float(dup_high) or progress < float(progress_low):
                new_state = 0
            elif dup_ratio < float(dup_high) * 0.5 and progress > float(progress_low) * 2.0:
                new_state = 2
            else:
                new_state = 1
            if new_state != state:
                switches += 1
            state = int(new_state)
            generated_win = 0
            duplicate_win = 0
            last_best_h = best_h
        for dx, dy, step in nbrs:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            if occupancy[ny, nx]:
                continue
            generated_win += 1
            ng = g + step * resolution
            nkey = (nx, ny)
            if ng + 1e-9 >= g_cost.get(nkey, float("inf")):
                duplicate_win += 1
                continue
            g_cost[nkey] = ng
            parent[nkey] = node
            counter += 1
            nf = ng + weights[state] * h_fn(nx, ny)
            heapq.heappush(open_heap, (nf, ng, counter, nkey))
    checks = max(expansions / max(int(check_every), 1), 1.0)
    return {"success": False, "expansions": expansions, "runtime_ms": (time.perf_counter() - t0) * 1000.0, "path": [], "switch_rate": float(switches / checks), "state_diversity": float(sum(int(v > 0) for v in state_visits.values()) / 3.0)}


def _ceta_config_grid(args: argparse.Namespace) -> list[dict[str, Any]]:
    cfgs: list[dict[str, Any]] = []
    for aggr in _parse_float_list(args.h_aggressive_weights):
        for caut in _parse_float_list(args.h_cautious_weights):
            if float(caut) >= float(args.h_balanced_weight) or float(args.h_balanced_weight) >= float(aggr):
                continue
            for dup_hi in _parse_float_list(args.h_dup_high):
                for prog_low in _parse_float_list(args.h_progress_low):
                    tag = f"ceta_a{int(round(aggr * 100)):03d}_b{int(round(float(args.h_balanced_weight) * 100)):03d}_c{int(round(caut * 100)):03d}_d{int(round(dup_hi * 100)):02d}_p{int(round(prog_low * 1000)):03d}"
                    cfgs.append({"tag": tag, "aggressive_weight": float(aggr), "balanced_weight": float(args.h_balanced_weight), "cautious_weight": float(caut), "check_every": int(args.h_check_every), "dup_high": float(dup_hi), "progress_low": float(prog_low)})
    return cfgs


def _build_ceta_tables(args: argparse.Namespace, *, include_test: bool) -> tuple[Path, Path | None, list[dict[str, Any]]]:
    out_dir = ROOT / "outputs/router_phase31_step14_h_ceta_wa_v1" / "common"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfgs = _ceta_config_grid(args)
    cal_path = out_dir / "ceta_calib.parquet"
    test_path = out_dir / "ceta_test.parquet"

    def _ensure(split: str, out_path: Path) -> None:
        if out_path.exists():
            try:
                df = pd.read_parquet(out_path)
                need = {f"L_{cfg['tag']}" for cfg in cfgs} | {f"T_{cfg['tag']}_ms" for cfg in cfgs} | {f"path_len_{cfg['tag']}" for cfg in cfgs} | {f"switch_rate_{cfg['tag']}" for cfg in cfgs} | {f"state_diversity_{cfg['tag']}" for cfg in cfgs}
                if need.issubset(set(df.columns.tolist())):
                    return
            except Exception:
                pass
        idx = pd.read_csv(Path(args.dataset_root) / f"{split}_index.csv")
        if int(args.max_cases) > 0 and int(args.max_cases) < len(idx):
            idx = idx.sample(n=int(args.max_cases), random_state=20260318 if split == "calib" else 20260319).sort_values("sample_name").reset_index(drop=True)
        rows: list[dict[str, Any]] = []
        split_dir = Path(args.dataset_root) / split
        total = len(idx)
        for i, row in idx.iterrows():
            sample = load_grid_sample(split_dir / str(row["sample_name"]))
            meta: dict[str, Any] = {"sample_name": str(row["sample_name"]), "difficulty": str(row["difficulty"])}
            start_xy = (float(sample.start[0]), float(sample.start[1]))
            goal_xy = (float(sample.goal[0]), float(sample.goal[1]))
            for cfg in cfgs:
                res = _astar_grid_ceta(sample.occupancy, float(sample.resolution), start_xy, goal_xy, int(args.grid_max_expansions), aggressive_weight=float(cfg["aggressive_weight"]), balanced_weight=float(cfg["balanced_weight"]), cautious_weight=float(cfg["cautious_weight"]), check_every=int(cfg["check_every"]), dup_high=float(cfg["dup_high"]), progress_low=float(cfg["progress_low"]))
                tag = cfg["tag"]
                meta[f"success_{tag}"] = bool(res["success"])
                meta[f"L_{tag}"] = float(res["expansions"])
                meta[f"T_{tag}_ms"] = float(res["runtime_ms"])
                meta[f"path_len_{tag}"] = float(_path_length(res.get("path", [])))
                meta[f"switch_rate_{tag}"] = float(res.get("switch_rate", 0.0))
                meta[f"state_diversity_{tag}"] = float(res.get("state_diversity", 0.0))
            rows.append(meta)
            if (i + 1) % 200 == 0 or (i + 1) == total:
                print(f"[step14-h] {split} processed {i + 1}/{total}")
        pd.DataFrame(rows).to_parquet(out_path, index=False)

    _ensure("calib", cal_path)
    if include_test:
        _ensure("test", test_path)
        return cal_path, test_path, cfgs
    return cal_path, None, cfgs


def _selection_metrics_dynamic(df: pd.DataFrame, mapping: dict[str, str], *, t_ref: float, beta: float, eps_rel: float, extra_prefixes: list[str]) -> tuple[dict[str, Any], np.ndarray]:
    diff_arr = df["difficulty"].astype(str).to_numpy(dtype=str)
    n = len(df)
    l_slow = df["L_slow"].to_numpy(dtype=np.float64)
    path_slow = df["path_len_slow"].to_numpy(dtype=np.float64)
    j = np.zeros(n, dtype=np.float64)
    drel = np.zeros(n, dtype=np.float64)
    path_rel = np.zeros(n, dtype=np.float64)
    latency = np.zeros(n, dtype=np.float64)
    selected = np.empty(n, dtype=object)
    extra_vals: dict[str, np.ndarray] = {prefix: np.zeros(n, dtype=np.float64) for prefix in extra_prefixes}
    for diff, tag in mapping.items():
        mask = diff_arr == str(diff)
        if not np.any(mask):
            continue
        l = df.loc[mask, f"L_{tag}"].to_numpy(dtype=np.float64)
        t = df.loc[mask, f"T_{tag}_ms"].to_numpy(dtype=np.float64)
        p = df.loc[mask, f"path_len_{tag}"].to_numpy(dtype=np.float64)
        drel[mask] = (l - l_slow[mask]) / np.maximum(l_slow[mask], 1e-6)
        path_rel[mask] = (p - path_slow[mask]) / np.maximum(path_slow[mask], 1e-6)
        latency[mask] = t
        j[mask] = t / max(float(t_ref), 1e-9) + float(beta) * np.maximum(drel[mask], 0.0)
        selected[mask] = str(tag)
        for prefix in extra_prefixes:
            extra_vals[prefix][mask] = df.loc[mask, f"{prefix}_{tag}"].to_numpy(dtype=np.float64)
    vio = drel > float(eps_rel)
    _, ci_hi = _wilson_ci(int(np.sum(vio)), int(n))
    counts = {str(k): int(np.sum(selected == str(k))) for k in sorted(set(str(v) for v in mapping.values()))}
    metrics: dict[str, Any] = {
        "J_mean": float(np.mean(j)),
        "J_array": j,
        "drel_array": drel,
        "path_rel_array": path_rel,
        "violation_rate": float(np.mean(vio.astype(np.float64))),
        "violation_ci95_upper": float(ci_hi),
        "path_rel_mean": float(np.mean(path_rel)),
        "path_rel_p95": float(np.quantile(path_rel, 0.95)),
        "avg_latency_ms": float(np.mean(latency)),
        "arm_counts": counts,
        "arm_distribution": {k: float(v / max(n, 1)) for k, v in counts.items()},
    }
    for prefix in extra_prefixes:
        metrics[f"{prefix}_mean"] = float(np.mean(extra_vals[prefix]))
    return metrics, np.asarray(selected, dtype=str)


def _best_dynamic_mapping(df: pd.DataFrame, tags: list[str], *, t_ref: float, beta: float, eps_rel: float, extra_prefixes: list[str]) -> tuple[dict[str, str], dict[str, Any], np.ndarray, dict[str, Any], list[dict[str, Any]]]:
    best_mapping = {diff: str(tags[0]) for diff in DIFFICULTIES}
    best_metrics: dict[str, Any] | None = None
    best_selected = np.asarray([str(tags[0])] * len(df), dtype=str)
    best_params: dict[str, Any] = {}
    ablations: list[dict[str, Any]] = []
    for combo in product(tags, repeat=len(DIFFICULTIES)):
        mapping = {diff: str(tag) for diff, tag in zip(DIFFICULTIES, combo)}
        metrics, selected = _selection_metrics_dynamic(df, mapping, t_ref=t_ref, beta=beta, eps_rel=eps_rel, extra_prefixes=extra_prefixes)
        row = {"mapping": json.dumps(mapping, ensure_ascii=False), "J_mean_val": float(metrics["J_mean"]), "violation_ci95_upper": float(metrics["violation_ci95_upper"]), "path_rel_mean": float(metrics["path_rel_mean"]), "path_rel_p95": float(metrics["path_rel_p95"]), "unique_arms": int(sum(float(v) > 1e-12 for v in metrics["arm_distribution"].values()))}
        for prefix in extra_prefixes:
            row[f"{prefix}_mean"] = float(metrics.get(f"{prefix}_mean", 0.0))
        ablations.append(row)
        if not _is_feasible(metrics, alpha=float(args_global.alpha), path_rel_mean_max=float(args_global.path_rel_mean_max), path_rel_p95_max=float(args_global.path_rel_p95_max)):
            continue
        if best_metrics is None or float(metrics["J_mean"]) < float(best_metrics["J_mean"]):
            best_mapping = mapping
            best_metrics = metrics
            best_selected = selected
            best_params = {"mapping_by_difficulty": mapping}
    if best_metrics is None:
        best_metrics, best_selected = _selection_metrics_dynamic(df, best_mapping, t_ref=t_ref, beta=beta, eps_rel=eps_rel, extra_prefixes=extra_prefixes)
        best_params = {"mapping_by_difficulty": best_mapping, "fallback": True}
    return best_mapping, best_metrics, best_selected, best_params, ablations


def _eval_family_G(ctxs: dict[int, SeedContext], args: argparse.Namespace, calib_common: pd.DataFrame, input_parquets: dict[str, Path]) -> tuple[FamilyResult, dict[int, dict[str, Any]], pd.DataFrame | None, dict[str, Path]]:
    out_dir = ROOT / "outputs/router_phase31_step14_g_cpsf_wa_v1"
    dyn_cal, _, cfgs = _build_cpsf_tables(args, include_test=False)
    calib = calib_common.merge(pd.read_parquet(dyn_cal), on=["sample_name", "difficulty"], how="inner")
    tags = [str(cfg["tag"]) for cfg in cfgs]
    seed_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None
    family_inputs = dict(input_parquets)
    family_inputs["cpsf_calib"] = dyn_cal
    for seed, ctx in ctxs.items():
        cal = ctx.cal_val.merge(calib[[c for c in calib.columns if c == "sample_name" or c == "difficulty" or c.startswith(("L_cpsf_", "T_cpsf_", "path_len_cpsf_", "field_std_cpsf_"))]], on=["sample_name", "difficulty"], how="inner")
        mapping, metrics_val, selected_val, params, local_abls = _best_dynamic_mapping(cal, tags, t_ref=float(ctx.t_ref), beta=float(ctx.beta), eps_rel=float(args.epsilon_rel), extra_prefixes=["field_std"])
        for row in local_abls:
            row["seed"] = int(seed)
            ablation_rows.append(row)
        row, _ = _summarize_seed(seed=seed, test_metrics=metrics_val, j_p5_test=ctx.j_p5_val, selected_test=selected_val, method_name="CPSF-WA(val)", policy_desc=params)
        row["field_std_mean"] = float(metrics_val.get("field_std_mean", 0.0))
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(metrics_val["J_array"], dtype=np.float64)
        seed_states[seed] = {"mapping": mapping, "params": params}
        if failure_df is None:
            failure_df = _representative_failures_dynamic(cal, selected_val, metrics_val["J_array"], ctx.j_p5_val)
    pooled = _pooled_stats(np.concatenate([ctxs[s].j_p5_val - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key="G", name="CPSF-WA", out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": "CPSF-WA", "num_configs": len(cfgs)})
    return result, seed_states, failure_df, family_inputs


def _eval_family_H(ctxs: dict[int, SeedContext], args: argparse.Namespace, calib_common: pd.DataFrame, input_parquets: dict[str, Path]) -> tuple[FamilyResult, dict[int, dict[str, Any]], pd.DataFrame | None, dict[str, Path]]:
    out_dir = ROOT / "outputs/router_phase31_step14_h_ceta_wa_v1"
    dyn_cal, _, cfgs = _build_ceta_tables(args, include_test=False)
    calib = calib_common.merge(pd.read_parquet(dyn_cal), on=["sample_name", "difficulty"], how="inner")
    tags = [str(cfg["tag"]) for cfg in cfgs]
    seed_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None
    family_inputs = dict(input_parquets)
    family_inputs["ceta_calib"] = dyn_cal
    for seed, ctx in ctxs.items():
        cal = ctx.cal_val.merge(calib[[c for c in calib.columns if c == "sample_name" or c == "difficulty" or c.startswith(("L_ceta_", "T_ceta_", "path_len_ceta_", "switch_rate_ceta_", "state_diversity_ceta_"))]], on=["sample_name", "difficulty"], how="inner")
        mapping, metrics_val, selected_val, params, local_abls = _best_dynamic_mapping(cal, tags, t_ref=float(ctx.t_ref), beta=float(ctx.beta), eps_rel=float(args.epsilon_rel), extra_prefixes=["switch_rate", "state_diversity"])
        for row in local_abls:
            row["seed"] = int(seed)
            ablation_rows.append(row)
        row, _ = _summarize_seed(seed=seed, test_metrics=metrics_val, j_p5_test=ctx.j_p5_val, selected_test=selected_val, method_name="CETA-WA(val)", policy_desc=params)
        row["switch_rate"] = float(metrics_val.get("switch_rate_mean", 0.0))
        row["state_diversity"] = float(metrics_val.get("state_diversity_mean", 0.0))
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(metrics_val["J_array"], dtype=np.float64)
        seed_states[seed] = {"mapping": mapping, "params": params}
        if failure_df is None:
            failure_df = _representative_failures_dynamic(cal, selected_val, metrics_val["J_array"], ctx.j_p5_val)
    pooled = _pooled_stats(np.concatenate([ctxs[s].j_p5_val - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key="H", name="CETA-WA", out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": "CETA-WA", "num_configs": len(cfgs)})
    return result, seed_states, failure_df, family_inputs


def _evaluate_test_dynamic(result: FamilyResult, seed_states: dict[int, dict[str, Any]], ctxs: dict[int, SeedContext], baselines: dict[str, dict[int, dict[str, Any]]], args: argparse.Namespace) -> tuple[pd.DataFrame | None, dict[str, Path]]:
    seed_rows_test: list[dict[str, Any]] = []
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None
    if result.key == "G":
        dyn_cal, dyn_test, _ = _build_cpsf_tables(args, include_test=True)
        if dyn_test is None:
            raise RuntimeError("CPSF test table missing")
        dyn_df = pd.read_parquet(dyn_test)
        family_inputs = {"cpsf_calib": dyn_cal, "cpsf_test": dyn_test}
        extra_prefixes = ["field_std"]
    elif result.key == "H":
        dyn_cal, dyn_test, _ = _build_ceta_tables(args, include_test=True)
        if dyn_test is None:
            raise RuntimeError("CETA test table missing")
        dyn_df = pd.read_parquet(dyn_test)
        family_inputs = {"ceta_calib": dyn_cal, "ceta_test": dyn_test}
        extra_prefixes = ["switch_rate", "state_diversity"]
    else:
        raise RuntimeError(f"Unsupported dynamic family {result.key}")
    for seed in sorted(seed_states.keys()):
        state = seed_states[seed]
        ctx = ctxs[seed]
        te = ctx.test.merge(dyn_df, on=["sample_name", "difficulty"], how="inner")
        metrics_test, selected_test = _selection_metrics_dynamic(te, state["mapping"], t_ref=float(ctx.t_ref), beta=float(ctx.beta), eps_rel=float(args.epsilon_rel), extra_prefixes=extra_prefixes)
        row, _ = _summarize_seed(seed=seed, test_metrics=metrics_test, j_p5_test=ctx.j_p5_test, selected_test=selected_test, method_name=f"{result.name}(test)", policy_desc=state["params"])
        if result.key == "G":
            row["field_std_mean"] = float(metrics_test.get("field_std_mean", 0.0))
        if result.key == "H":
            row["switch_rate"] = float(metrics_test.get("switch_rate_mean", 0.0))
            row["state_diversity"] = float(metrics_test.get("state_diversity_mean", 0.0))
        seed_rows_test.append(row)
        cand_arrays[seed] = np.asarray(metrics_test["J_array"], dtype=np.float64)
        if failure_df is None:
            failure_df = _representative_failures_dynamic(te, selected_test, metrics_test["J_array"], ctx.j_p5_test)
    result.pooled_test = _pooled_stats(np.concatenate([ctxs[s].j_p5_test - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result.seed_rows_test = seed_rows_test
    _attach_head_to_head(result, seed_rows_test, cand_arrays, baselines, "test", int(args.bootstrap_n))
    gate_test = {
        "risk_ci95_upper_le_alpha_all_seeds": bool(all(float(r["violation_ci95_upper"]) <= float(args.alpha) + 1e-12 for r in seed_rows_test)),
        "path_audit_hold_all_seeds": bool(all(float(r["path_rel_mean"]) <= float(args.path_rel_mean_max) + 1e-12 and float(r["path_rel_p95"]) <= float(args.path_rel_p95_max) + 1e-12 for r in seed_rows_test)),
        "beats_M_on_test_sign": bool(float(result.head_to_head_test["M"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_N_on_test_sign": bool(float(result.head_to_head_test["N"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_O_on_test_sign": bool(float(result.head_to_head_test["O"]["pooled"]["mean_delta_j"]) > 0.0),
    }
    if result.key == "G":
        avg_field_std = float(np.mean([float(r.get("field_std_mean", 0.0)) for r in seed_rows_test]))
        gate_test["avg_field_std"] = avg_field_std
        gate_test["not_trivial_field"] = bool(avg_field_std > 0.03)
    if result.key == "H":
        avg_switch = float(np.mean([float(r.get("switch_rate", 0.0)) for r in seed_rows_test]))
        avg_state_div = float(np.mean([float(r.get("state_diversity", 0.0)) for r in seed_rows_test]))
        gate_test["avg_switch_rate"] = avg_switch
        gate_test["avg_state_diversity"] = avg_state_div
        gate_test["not_trivial_schedule"] = bool((avg_switch > 0.05) and (avg_state_div > 0.5))
    result.gate_check_test = gate_test
    result.advanced_to_test = True
    return failure_df, family_inputs


def main() -> None:
    global args_global
    args = parse_args()
    args_global = args
    t0 = time.perf_counter()
    weights = _parse_weights(args.weights)
    calib, test, base_inputs = _build_common_tables(args, weights)
    ctxs = _build_seed_contexts(args, calib, test, weights)
    baselines = _fit_baselines(ctxs, args)

    families: list[FamilyResult] = []
    aux_states: dict[str, dict[int, dict[str, Any]]] = {}
    failures: dict[str, pd.DataFrame | None] = {}
    family_inputs: dict[str, dict[str, Path]] = {}

    for key, fn in [("E", _eval_family_E), ("F", _eval_family_F)]:
        fam, states, fail_df = fn(ctxs, args)
        aux_states[key] = states
        failures[key] = fail_df
        candidate_arrays = {seed: np.asarray(states[seed]["metrics_val"]["J_array"], dtype=np.float64) for seed in sorted(states.keys())}
        _attach_head_to_head(fam, fam.seed_rows_val, candidate_arrays, baselines, "val", int(args.bootstrap_n))
        _family_gate_from_val_fresh(fam)
        families.append(fam)
        family_inputs[key] = dict(base_inputs)

    fam_g, states_g, fail_g, inputs_g = _eval_family_G(ctxs, args, calib, base_inputs)
    aux_states["G"] = states_g
    failures["G"] = fail_g
    cand_arrays_g = {}
    cpsf_cal = pd.read_parquet(inputs_g["cpsf_calib"])
    for seed in sorted(states_g.keys()):
        ctx = ctxs[seed]
        cal = ctx.cal_val.merge(cpsf_cal, on=["sample_name", "difficulty"], how="inner")
        metrics, _ = _selection_metrics_dynamic(cal, states_g[seed]["mapping"], t_ref=float(ctx.t_ref), beta=float(ctx.beta), eps_rel=float(args.epsilon_rel), extra_prefixes=["field_std"])
        states_g[seed]["metrics_val"] = metrics
        cand_arrays_g[seed] = np.asarray(metrics["J_array"], dtype=np.float64)
    _attach_head_to_head(fam_g, fam_g.seed_rows_val, cand_arrays_g, baselines, "val", int(args.bootstrap_n))
    _family_gate_from_val_fresh(fam_g)
    families.append(fam_g)
    family_inputs["G"] = inputs_g

    fam_h, states_h, fail_h, inputs_h = _eval_family_H(ctxs, args, calib, base_inputs)
    aux_states["H"] = states_h
    failures["H"] = fail_h
    cand_arrays_h = {}
    ceta_cal = pd.read_parquet(inputs_h["ceta_calib"])
    for seed in sorted(states_h.keys()):
        ctx = ctxs[seed]
        cal = ctx.cal_val.merge(ceta_cal, on=["sample_name", "difficulty"], how="inner")
        metrics, _ = _selection_metrics_dynamic(cal, states_h[seed]["mapping"], t_ref=float(ctx.t_ref), beta=float(ctx.beta), eps_rel=float(args.epsilon_rel), extra_prefixes=["switch_rate", "state_diversity"])
        states_h[seed]["metrics_val"] = metrics
        cand_arrays_h[seed] = np.asarray(metrics["J_array"], dtype=np.float64)
    _attach_head_to_head(fam_h, fam_h.seed_rows_val, cand_arrays_h, baselines, "val", int(args.bootstrap_n))
    _family_gate_from_val_fresh(fam_h)
    families.append(fam_h)
    family_inputs["H"] = inputs_h

    chosen_key = None
    chosen_reason = "No candidate selected yet."
    promising = [fam for fam in families if _advance_family_fresh(fam)]
    if not promising:
        chosen_reason = "E/F/G/H all failed to beat M/N/O on calib_val or violated the family-specific non-degeneracy gate; no candidate was allowed to consume test."
    else:
        promising = sorted(promising, key=lambda fam: float(np.mean([row["mean_delta_j"] for row in fam.seed_rows_val])), reverse=True)
        chosen = promising[0]
        chosen_key = chosen.key
        chosen_reason = "Selected by pooled calib_val performance with strict gates satisfied; only this family is allowed to consume test."
        chosen.status = "chosen_for_test"
        if chosen.key in {"E", "F"}:
            failure_df_test = _evaluate_test_for_family(chosen, aux_states[chosen.key], ctxs, baselines, args)
            if failure_df_test is not None:
                failures[chosen.key] = failure_df_test
        else:
            failure_df_test, extra_inputs = _evaluate_test_dynamic(chosen, aux_states[chosen.key], ctxs, baselines, args)
            failures[chosen.key] = failure_df_test
            family_inputs[chosen.key] = {**family_inputs[chosen.key], **extra_inputs}
        if chosen.gate_check_test and all(bool(v) for v in chosen.gate_check_test.values() if isinstance(v, (bool, np.bool_))):
            chosen.status = "tested_positive"
        else:
            chosen.status = "tested_negative"

    summary = {
        "version": "step14_fresh_trials_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "chosen_family_for_test": chosen_key,
        "chosen_reason": chosen_reason,
        "families": [
            {
                "key": fam.key,
                "name": fam.name,
                "status": fam.status,
                "pooled_val": fam.pooled_val,
                "head_to_head_val": fam.head_to_head_val,
                "gate_check_val": fam.gate_check_val,
                "advanced_to_test": fam.advanced_to_test,
                "pooled_test": fam.pooled_test,
                "head_to_head_test": fam.head_to_head_test,
                "gate_check_test": fam.gate_check_test,
            }
            for fam in families
        ],
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(_jsonable(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    _report_summary(args.report_md, families, chosen_key, chosen_reason)
    for fam in families:
        inputs = family_inputs[fam.key]
        art_inputs = inputs if fam.advanced_to_test else {k: v for k, v in inputs.items() if "test" not in str(k)}
        _write_candidate_artifacts(fam, input_parquets=art_inputs, representative_rows=failures.get(fam.key))
    print(f"[step14-fresh] summary={args.summary_json}")
    print(f"[step14-fresh] report={args.report_md}")


if __name__ == "__main__":
    main()
