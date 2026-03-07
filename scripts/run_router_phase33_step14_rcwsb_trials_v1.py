from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_router_phase8_strict import _split_calib_train_val
from scripts.run_router_phase29_step12r4_trials_v1 import (
    ArmCache,
    _is_feasible,
    _parse_weights,
    _pooled_stats,
    _selection_metrics,
    _summarize_seed,
)
from scripts.run_router_phase30_step14_trials_v1 import (
    FamilyResult,
    SeedContext,
    _attach_head_to_head,
    _jsonable,
    _representative_failures,
    _report_summary,
    _stable_quantile,
    _write_candidate_artifacts,
)
from scripts.run_router_phase31_step14_fresh_trials_v1 import (
    _build_common_tables,
    _build_seed_contexts,
    _fit_baselines,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step14 final RCWS-B strict trial runner (phase33).")
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--strict-phase9-root", type=Path, default=Path("outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak"))
    p.add_argument("--weights", type=str, default="1.00,1.05,1.10,1.15,1.20,1.25,1.35")
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--calib-train-frac", type=float, default=0.60)
    p.add_argument("--calib-split-seed", type=int, default=20260306)
    p.add_argument("--inner-fit-frac", type=float, default=0.75)
    p.add_argument("--bootstrap-n", type=int, default=10000)
    p.add_argument("--grid-max-expansions", type=int, default=50000)
    p.add_argument("--fastgeom-max-expansions", type=int, default=50000)
    p.add_argument("--fastgeom-corridor-radius-cells", type=int, default=2)
    p.add_argument("--max-cases", type=int, default=-1)
    p.add_argument("--path-rel-mean-max", type=float, default=0.01)
    p.add_argument("--path-rel-p95-max", type=float, default=0.05)
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase33_step14_rcwsb_trials_v1.md"))
    p.add_argument("--summary-json", type=Path, default=Path("outputs/router_phase33_step14_rcwsb_trials_v1/summary.json"))
    p.add_argument("--ranks", type=str, default="1,2")
    p.add_argument("--windows", type=str, default="1,2")
    p.add_argument("--max-depths", type=str, default="2")
    p.add_argument("--learning-rates", type=str, default="0.10")
    p.add_argument("--max-iters", type=str, default="120")
    p.add_argument("--conformal-alphas", type=str, default="0.10")
    p.add_argument("--sample-path-guards", type=str, default="0.05")
    p.add_argument("--families", type=str, default="B1,B2,B3")
    p.add_argument("--out-suffix", type=str, default="_v1")
    return p.parse_args()


@dataclass
class InnerContext:
    fit_df: pd.DataFrame
    regcal_df: pd.DataFrame
    fit_cache: ArmCache
    regcal_cache: ArmCache


@dataclass
class BasisCurveState:
    arm_names: list[str]
    incumbent_arm: str
    incumbent_index: int
    variant: str
    j_mean: np.ndarray
    j_basis: np.ndarray
    j_models: list[HistGradientBoostingRegressor]
    d_mean: np.ndarray
    d_basis: np.ndarray
    d_models: list[HistGradientBoostingRegressor]
    p_mean: np.ndarray
    p_basis: np.ndarray
    p_models: list[HistGradientBoostingRegressor]
    q_j: np.ndarray
    q_d: np.ndarray
    q_p: np.ndarray
    sample_path_guard: float


def _parse_int_list(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
    if not vals:
        raise ValueError("empty int list")
    return vals


def _parse_float_list(raw: str) -> list[float]:
    vals = [float(x.strip()) for x in str(raw).split(",") if x.strip()]
    if not vals:
        raise ValueError("empty float list")
    return vals


def _parse_seeds(raw: str) -> list[int]:
    return [int(x.strip()) for x in str(raw).split(",") if x.strip()]


def _arm_weight(arm: str) -> float:
    if arm == "fast":
        return 1.0
    if arm == "slow":
        return 1e9
    return float(arm.split("_")[-1][1:]) / 100.0


def _ordered_arms(arm_space: list[str]) -> list[str]:
    return sorted([str(a) for a in arm_space], key=_arm_weight)


def _upper_pos_quantile(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    resid = np.maximum(np.asarray(y_true, dtype=np.float64) - np.asarray(y_pred, dtype=np.float64), 0.0)
    n = int(resid.size)
    if n <= 0:
        return 0.0
    level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / max(n, 1))
    return float(_stable_quantile(resid, level))


def _best_feasible_constant(cache: ArmCache, ordered_arms: list[str], args: argparse.Namespace) -> str:
    best_arm = str(ordered_arms[0])
    best_j = float("inf")
    for arm in ordered_arms:
        selected = np.asarray([arm] * len(cache.df), dtype=str)
        metrics = _selection_metrics(cache, selected, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        if not _is_feasible(metrics, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
            continue
        if float(metrics["J_mean"]) < float(best_j):
            best_arm = str(arm)
            best_j = float(metrics["J_mean"])
    return best_arm


def _window_arms(ordered_arms: list[str], incumbent_arm: str, window: int) -> list[str]:
    idx = ordered_arms.index(str(incumbent_arm))
    lo = max(0, idx - int(window))
    hi = min(len(ordered_arms), idx + int(window) + 1)
    return list(ordered_arms[lo:hi])


def _curve_matrix(cache: ArmCache, arms: list[str], field: str) -> np.ndarray:
    return np.stack([np.asarray(cache.arms[a][field], dtype=np.float64) for a in arms], axis=1)


def _basis_decompose(y: np.ndarray, rank: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype=np.float64)
    mean = np.mean(y, axis=0)
    centered = y - mean[None, :]
    if centered.size == 0 or np.allclose(centered, 0.0):
        return mean.astype(np.float64), np.zeros((0, y.shape[1]), dtype=np.float64), np.zeros((len(y), 0), dtype=np.float64)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    r = int(min(max(int(rank), 0), vt.shape[0]))
    if r <= 0:
        return mean.astype(np.float64), np.zeros((0, y.shape[1]), dtype=np.float64), np.zeros((len(y), 0), dtype=np.float64)
    basis = vt[:r].astype(np.float64)
    coeff = centered @ basis.T
    return mean.astype(np.float64), basis, coeff.astype(np.float64)


def _fit_models(x_df: pd.DataFrame, coeff: np.ndarray, *, depth: int, learning_rate: float, max_iter: int, seed: int) -> list[HistGradientBoostingRegressor]:
    coeff = np.asarray(coeff, dtype=np.float64)
    if coeff.ndim != 2 or coeff.shape[1] == 0:
        return []
    models: list[HistGradientBoostingRegressor] = []
    for idx in range(coeff.shape[1]):
        model = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(learning_rate), max_iter=int(max_iter), random_state=int(seed) + idx * 17)
        model.fit(x_df, coeff[:, idx])
        models.append(model)
    return models


def _predict_curve(models: list[HistGradientBoostingRegressor], x_df: pd.DataFrame, mean: np.ndarray, basis: np.ndarray) -> np.ndarray:
    mean = np.asarray(mean, dtype=np.float64)
    if len(models) == 0 or basis.shape[0] == 0:
        return np.tile(mean[None, :], (len(x_df), 1)).astype(np.float64)
    coeff_pred = np.stack([np.asarray(m.predict(x_df), dtype=np.float64) for m in models], axis=1)
    return (mean[None, :] + coeff_pred @ basis).astype(np.float64)


def _build_inner_context(ctx: SeedContext, *, inner_fit_frac: float, split_seed: int, weights: list[float]) -> InnerContext:
    fit_df, regcal_df, _ = _split_calib_train_val(ctx.cal_train, train_frac=float(inner_fit_frac), seed=int(split_seed))
    fit_cache = ArmCache(fit_df, weights, t_ref=float(ctx.t_ref), beta=float(ctx.beta))
    regcal_cache = ArmCache(regcal_df, weights, t_ref=float(ctx.t_ref), beta=float(ctx.beta))
    return InnerContext(fit_df=fit_df, regcal_df=regcal_df, fit_cache=fit_cache, regcal_cache=regcal_cache)


def _feature_mats(inner: InnerContext, ctx: SeedContext) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cols = [c for c in ctx.x_train.columns]
    x_fit = pd.get_dummies(inner.fit_df[[*inner.fit_df.columns]], columns=[], drop_first=False) if False else None
    del x_fit
    def _encode(df: pd.DataFrame) -> pd.DataFrame:
        cols0 = [c for c in [*ctx.x_train.columns] if c in ctx.x_train.columns]
        return pd.get_dummies(df[[*(set())]], columns=[], drop_first=False) if False else None
    # reuse aligned columns from SeedContext by reconstructing from original matrices' columns
    base_cols = [c for c in ctx.x_train.columns]
    def _align(df_raw: pd.DataFrame) -> pd.DataFrame:
        cols_src = [c for c in df_raw.columns if c in df_raw.columns]
        del cols_src
        use_cols = [
            "line_block_ratio", "local_occ_ratio", "global_occ_ratio", "distance_ratio", "complexity_score", "los_clear",
            "L_fast", "T_fast_ms", "search_fast_ms", "path_len_fast",
            "fg_path_stretch", "fg_path_clear_mean", "fg_path_clear_std", "fg_path_clear_min", "fg_path_turn_mean_rad", "fg_path_turn_sum_rad",
            "fg_line_dev_mean_m", "fg_line_dev_p90_m", "fg_corridor_occ_mean", "fg_exp_bbox_ratio", "fg_exp_fill_ratio", "fg_exp_map_ratio", "fg_exp_goal_dist_ratio", "fg_exp_per_path_m", "fg_ms_per_exp",
            "difficulty",
        ]
        x = pd.get_dummies(df_raw[use_cols], columns=["difficulty"], drop_first=False)
        return x.reindex(columns=base_cols, fill_value=0)
    return _align(inner.fit_df), _align(inner.regcal_df), _align(ctx.cal_val), _align(ctx.test)


def _fit_curve_state(
    *,
    variant: str,
    inner: InnerContext,
    ctx: SeedContext,
    args: argparse.Namespace,
    ordered_arms: list[str],
    rank: int,
    window: int,
    max_depth: int,
    learning_rate: float,
    max_iter: int,
    conformal_alpha: float,
    sample_path_guard: float,
    seed: int,
) -> BasisCurveState:
    incumbent = _best_feasible_constant(inner.fit_cache, ordered_arms, args)
    arms = _window_arms(ordered_arms, incumbent, int(window))
    inc_idx = arms.index(str(incumbent))
    j_fit_abs = _curve_matrix(inner.fit_cache, arms, "J")
    d_fit_abs = _curve_matrix(inner.fit_cache, arms, "drel")
    p_fit_abs = _curve_matrix(inner.fit_cache, arms, "path_rel")
    if str(variant) == "direct":
        j_fit = j_fit_abs
    else:
        j_fit = j_fit_abs - j_fit_abs[:, [inc_idx]]
    x_fit, x_regcal, _, _ = _feature_mats(inner, ctx)

    j_mean, j_basis, j_coeff = _basis_decompose(j_fit, rank=int(rank))
    d_mean, d_basis, d_coeff = _basis_decompose(d_fit_abs, rank=int(rank))
    p_mean, p_basis, p_coeff = _basis_decompose(p_fit_abs, rank=int(rank))

    j_models = _fit_models(x_fit, j_coeff, depth=int(max_depth), learning_rate=float(learning_rate), max_iter=int(max_iter), seed=int(seed) + 101)
    d_models = _fit_models(x_fit, d_coeff, depth=int(max_depth), learning_rate=float(learning_rate), max_iter=int(max_iter), seed=int(seed) + 211)
    p_models = _fit_models(x_fit, p_coeff, depth=int(max_depth), learning_rate=float(learning_rate), max_iter=int(max_iter), seed=int(seed) + 307)

    j_reg_pred = _predict_curve(j_models, x_regcal, j_mean, j_basis)
    d_reg_pred = _predict_curve(d_models, x_regcal, d_mean, d_basis)
    p_reg_pred = _predict_curve(p_models, x_regcal, p_mean, p_basis)

    j_reg_true_abs = _curve_matrix(inner.regcal_cache, arms, "J")
    d_reg_true = _curve_matrix(inner.regcal_cache, arms, "drel")
    p_reg_true = _curve_matrix(inner.regcal_cache, arms, "path_rel")
    if str(variant) == "direct":
        j_reg_true = j_reg_true_abs
    else:
        j_reg_true = j_reg_true_abs - j_reg_true_abs[:, [inc_idx]]
        j_reg_pred[:, inc_idx] = 0.0

    q_j = np.asarray([_upper_pos_quantile(j_reg_true[:, i], j_reg_pred[:, i], alpha=float(conformal_alpha)) for i in range(len(arms))], dtype=np.float64)
    q_d = np.asarray([_upper_pos_quantile(d_reg_true[:, i], d_reg_pred[:, i], alpha=float(conformal_alpha)) for i in range(len(arms))], dtype=np.float64)
    q_p = np.asarray([_upper_pos_quantile(p_reg_true[:, i], p_reg_pred[:, i], alpha=float(conformal_alpha)) for i in range(len(arms))], dtype=np.float64)

    return BasisCurveState(
        arm_names=list(arms),
        incumbent_arm=str(incumbent),
        incumbent_index=int(inc_idx),
        variant=str(variant),
        j_mean=j_mean,
        j_basis=j_basis,
        j_models=j_models,
        d_mean=d_mean,
        d_basis=d_basis,
        d_models=d_models,
        p_mean=p_mean,
        p_basis=p_basis,
        p_models=p_models,
        q_j=q_j,
        q_d=q_d,
        q_p=q_p,
        sample_path_guard=float(sample_path_guard),
    )


def _predict_state_curves(state: BasisCurveState, x_df: pd.DataFrame, *, monotone: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    j_pred = _predict_curve(state.j_models, x_df, state.j_mean, state.j_basis)
    d_pred = _predict_curve(state.d_models, x_df, state.d_mean, state.d_basis)
    p_pred = _predict_curve(state.p_models, x_df, state.p_mean, state.p_basis)
    if state.variant != "direct":
        j_pred[:, state.incumbent_index] = 0.0
    j_up = j_pred + state.q_j[None, :]
    d_up = d_pred + state.q_d[None, :]
    p_up = p_pred + state.q_p[None, :]
    if monotone:
        d_up = np.maximum.accumulate(d_up, axis=1)
        p_up = np.maximum.accumulate(p_up, axis=1)
    return j_up.astype(np.float64), d_up.astype(np.float64), p_up.astype(np.float64)


def _select_from_state(state: BasisCurveState, x_df: pd.DataFrame, *, eps_rel: float, monotone: bool) -> tuple[np.ndarray, dict[str, float]]:
    j_up, d_up, p_up = _predict_state_curves(state, x_df, monotone=bool(monotone))
    selected = []
    use_incumbent = []
    feasible_counts = []
    for i in range(len(x_df)):
        feas = [idx for idx in range(len(state.arm_names)) if float(d_up[i, idx]) <= float(eps_rel) and float(p_up[i, idx]) <= float(state.sample_path_guard)]
        feasible_counts.append(float(len(feas)))
        if not feas:
            selected.append(str(state.incumbent_arm))
            use_incumbent.append(1.0)
            continue
        if state.variant == "direct":
            best_idx = min(feas, key=lambda idx: float(j_up[i, idx]))
        else:
            cand = [idx for idx in feas if float(j_up[i, idx]) <= 0.0 + 1e-12]
            if cand:
                best_idx = min(cand, key=lambda idx: float(j_up[i, idx]))
            else:
                best_idx = int(state.incumbent_index)
        selected_arm = str(state.arm_names[int(best_idx)])
        selected.append(selected_arm)
        use_incumbent.append(1.0 if selected_arm == str(state.incumbent_arm) else 0.0)
    return np.asarray(selected, dtype=str), {
        "incumbent_fallback_rate": float(np.mean(use_incumbent)) if use_incumbent else 0.0,
        "avg_feasible_arm_count": float(np.mean(feasible_counts)) if feasible_counts else 0.0,
    }


def _gate_from_val(result: FamilyResult, args: argparse.Namespace) -> dict[str, Any]:
    h2h = result.head_to_head_val
    unique_arms = sorted({str(k) for row in result.seed_rows_val for k, v in row.get("arm_distribution", {}).items() if float(v) > 1e-12})
    dominant_list = []
    for row in result.seed_rows_val:
        ad = row.get("arm_distribution", {})
        if isinstance(ad, dict) and ad:
            dominant_list.append(max(float(v) for v in ad.values()))
    nonconst_count = int(sum(float(v) < 0.95 for v in dominant_list))
    gate = {
        "risk_ci95_upper_le_alpha_all_seeds": bool(all(float(r["violation_ci95_upper"]) <= float(args.alpha) + 1e-12 for r in result.seed_rows_val)),
        "path_audit_hold_all_seeds": bool(all(float(r["path_rel_mean"]) <= float(args.path_rel_mean_max) + 1e-12 and float(r["path_rel_p95"]) <= float(args.path_rel_p95_max) + 1e-12 for r in result.seed_rows_val)),
        "beats_M_on_val_mean": bool(float(h2h["M"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_N_on_val_mean": bool(float(h2h["N"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_O_on_val_mean": bool(float(h2h["O"]["pooled"]["mean_delta_j"]) > 0.0),
        "unique_arms": unique_arms,
        "dominant_arm_fraction_max": float(max(dominant_list) if dominant_list else 1.0),
        "nonconstant_seed_count": int(nonconst_count),
        "not_constantized": bool((len(unique_arms) >= 3) and (nonconst_count >= 2)),
    }
    result.gate_check_val = gate
    return gate


def _advance(result: FamilyResult) -> bool:
    g = result.gate_check_val
    return bool(
        g.get("risk_ci95_upper_le_alpha_all_seeds", False)
        and g.get("path_audit_hold_all_seeds", False)
        and g.get("beats_M_on_val_mean", False)
        and g.get("beats_N_on_val_mean", False)
        and g.get("beats_O_on_val_mean", False)
        and g.get("not_constantized", False)
    )


def _evaluate_test(result: FamilyResult, seed_states: dict[int, dict[str, Any]], ctxs: dict[int, SeedContext], baselines: dict[str, dict[int, dict[str, Any]]], args: argparse.Namespace) -> pd.DataFrame | None:
    seed_rows_test = []
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None
    for seed, ctx in ctxs.items():
        selected_test = np.asarray(seed_states[seed]["selected_test"], dtype=str)
        metrics_test = _selection_metrics(ctx.cache_test, selected_test, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        row, _ = _summarize_seed(seed=int(seed), test_metrics=metrics_test, j_p5_test=ctx.j_p5_test, selected_test=selected_test, method_name=f"{result.name}(test)", policy_desc=seed_states[seed].get("params", {}))
        for k, v in seed_states[seed].get("summary_test", {}).items():
            row[str(k)] = float(v)
        seed_rows_test.append(row)
        cand_arrays[seed] = np.asarray(metrics_test["J_array"], dtype=np.float64)
        if failure_df is None:
            failure_df = _representative_failures(ctx.test, selected_test, ctx.cache_test, ctx.j_p5_test)
    result.pooled_test = _pooled_stats(np.concatenate([ctxs[s].j_p5_test - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result.seed_rows_test = seed_rows_test
    _attach_head_to_head(result, seed_rows_test, cand_arrays, baselines, "test", int(args.bootstrap_n))
    result.gate_check_test = {
        "risk_ci95_upper_le_alpha_all_seeds": bool(all(float(r["violation_ci95_upper"]) <= float(args.alpha) + 1e-12 for r in seed_rows_test)),
        "path_audit_hold_all_seeds": bool(all(float(r["path_rel_mean"]) <= float(args.path_rel_mean_max) + 1e-12 and float(r["path_rel_p95"]) <= float(args.path_rel_p95_max) + 1e-12 for r in seed_rows_test)),
        "beats_M_on_test_sign": bool(float(result.head_to_head_test["M"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_N_on_test_sign": bool(float(result.head_to_head_test["N"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_O_on_test_sign": bool(float(result.head_to_head_test["O"]["pooled"]["mean_delta_j"]) > 0.0),
    }
    result.advanced_to_test = True
    return failure_df


def _eval_variant(
    *,
    key: str,
    name: str,
    variant: str,
    monotone: bool,
    out_dir: Path,
    ctxs: dict[int, SeedContext],
    inner_ctxs: dict[int, InnerContext],
    ordered_arms_map: dict[int, list[str]],
    feature_mats: dict[int, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]],
    args: argparse.Namespace,
) -> tuple[FamilyResult, dict[int, dict[str, Any]], dict[int, np.ndarray], pd.DataFrame | None]:
    seed_rows = []
    ablation_rows: list[dict[str, Any]] = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None
    ranks = _parse_int_list(args.ranks)
    windows = _parse_int_list(args.windows)
    depths = _parse_int_list(args.max_depths)
    lrs = _parse_float_list(args.learning_rates)
    max_iters = _parse_int_list(args.max_iters)
    conf_alphas = _parse_float_list(args.conformal_alphas)
    sample_guards = _parse_float_list(args.sample_path_guards)

    for seed in sorted(ctxs.keys()):
        ctx = ctxs[seed]
        inner = inner_ctxs[seed]
        ordered_arms = ordered_arms_map[seed]
        _, _, x_val, x_test = feature_mats[seed]
        best = None
        for rank, window, depth, lr, max_iter, conf_alpha, sample_guard in product(ranks, windows, depths, lrs, max_iters, conf_alphas, sample_guards):
            state = _fit_curve_state(
                variant=str(variant),
                inner=inner,
                ctx=ctx,
                args=args,
                ordered_arms=ordered_arms,
                rank=int(rank),
                window=int(window),
                max_depth=int(depth),
                learning_rate=float(lr),
                max_iter=int(max_iter),
                conformal_alpha=float(conf_alpha),
                sample_path_guard=float(sample_guard),
                seed=int(seed),
            )
            selected_val, summary_val = _select_from_state(state, x_val, eps_rel=float(args.epsilon_rel), monotone=bool(monotone))
            metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
            ablation_rows.append(
                {
                    "seed": int(seed),
                    "rank": int(rank),
                    "window": int(window),
                    "depth": int(depth),
                    "learning_rate": float(lr),
                    "max_iter": int(max_iter),
                    "conformal_alpha": float(conf_alpha),
                    "sample_path_guard": float(sample_guard),
                    "variant": str(variant),
                    "monotone": bool(monotone),
                    "incumbent_arm": str(state.incumbent_arm),
                    "candidate_arms": json.dumps(state.arm_names, ensure_ascii=False),
                    "J_mean_val": float(metrics_val["J_mean"]),
                    "violation_ci95_upper": float(metrics_val["violation_ci95_upper"]),
                    "path_rel_mean": float(metrics_val["path_rel_mean"]),
                    "path_rel_p95": float(metrics_val["path_rel_p95"]),
                    "unique_arms": int(sum(float(v) > 1e-12 for v in metrics_val["arm_distribution"].values())),
                    **{str(k): float(v) for k, v in summary_val.items()},
                }
            )
            if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                continue
            if best is None or float(metrics_val["J_mean"]) < float(best["metrics_val"]["J_mean"]):
                selected_test, summary_test = _select_from_state(state, x_test, eps_rel=float(args.epsilon_rel), monotone=bool(monotone))
                best = {
                    "state": state,
                    "selected_val": selected_val,
                    "selected_test": selected_test,
                    "metrics_val": metrics_val,
                    "params": {
                        "rank": int(rank),
                        "window": int(window),
                        "depth": int(depth),
                        "learning_rate": float(lr),
                        "max_iter": int(max_iter),
                        "conformal_alpha": float(conf_alpha),
                        "sample_path_guard": float(sample_guard),
                        "variant": str(variant),
                        "monotone": bool(monotone),
                        "incumbent_arm": str(state.incumbent_arm),
                        "candidate_arms": list(state.arm_names),
                    },
                    "summary_val": summary_val,
                    "summary_test": summary_test,
                }
        if best is None:
            incumbent = _best_feasible_constant(inner.fit_cache, ordered_arms, args)
            selected_val = np.asarray([incumbent] * len(ctx.cal_val), dtype=str)
            selected_test = np.asarray([incumbent] * len(ctx.test), dtype=str)
            best = {
                "selected_val": selected_val,
                "selected_test": selected_test,
                "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha)),
                "params": {"fallback_incumbent": str(incumbent), "variant": str(variant), "monotone": bool(monotone)},
                "summary_val": {},
                "summary_test": {},
            }
        row, _ = _summarize_seed(seed=int(seed), test_metrics=best["metrics_val"], j_p5_test=ctx.j_p5_val, selected_test=best["selected_val"], method_name=f"{name}(val)", policy_desc=best["params"])
        for k, v in best.get("summary_val", {}).items():
            row[str(k)] = float(v)
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(best["metrics_val"]["J_array"], dtype=np.float64)
        seed_states[seed] = {"selected_test": best["selected_test"], "params": best["params"], "summary_test": best.get("summary_test", {})}
        if failure_df is None:
            failure_df = _representative_failures(ctx.cal_val, best["selected_val"], ctx.cache_val, ctx.j_p5_val)
        print(f"[step14-rcwsb:{key}] seed {seed} done; best_params={best['params']}")

    pooled = _pooled_stats(np.concatenate([ctxs[s].j_p5_val - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key=str(key), name=str(name), out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": str(name), "variant": str(variant), "monotone": bool(monotone)})
    return result, seed_states, cand_arrays, failure_df


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    weights = _parse_weights(args.weights)
    calib, test, input_parquets = _build_common_tables(args, weights)
    ctxs = _build_seed_contexts(args, calib, test, weights)
    baselines = _fit_baselines(ctxs, args)
    inner_ctxs = {
        seed: _build_inner_context(ctx, inner_fit_frac=float(args.inner_fit_frac), split_seed=int(args.calib_split_seed) + 700 + int(seed), weights=weights)
        for seed, ctx in ctxs.items()
    }
    ordered_arms_map = {seed: _ordered_arms(ctx.arm_space) for seed, ctx in ctxs.items()}
    feature_mats = {seed: _feature_mats(inner_ctxs[seed], ctxs[seed]) for seed in sorted(ctxs.keys())}

    families: list[FamilyResult] = []
    seed_states_all: dict[str, dict[int, dict[str, Any]]] = {}
    failures: dict[str, pd.DataFrame | None] = {}

    suffix = str(args.out_suffix)
    all_specs = {
        "B1": ("B1", "RCWS-B-Direct", "direct", False, ROOT / f"outputs/router_phase33_step14_b1_rcwsb_direct{suffix}"),
        "B2": ("B2", "RCWS-B-Residual", "residual", False, ROOT / f"outputs/router_phase33_step14_b2_rcwsb_residual{suffix}"),
        "B3": ("B3", "RCWS-B-Monotone", "residual", True, ROOT / f"outputs/router_phase33_step14_b3_rcwsb_monotone{suffix}"),
    }
    family_order = [x.strip() for x in str(args.families).split(",") if x.strip()]
    specs = [all_specs[k] for k in family_order]

    for key, name, variant, monotone, out_dir in specs:
        fam, seed_states, cand_arrays, fail_df = _eval_variant(
            key=key,
            name=name,
            variant=variant,
            monotone=monotone,
            out_dir=out_dir,
            ctxs=ctxs,
            inner_ctxs=inner_ctxs,
            ordered_arms_map=ordered_arms_map,
            feature_mats=feature_mats,
            args=args,
        )
        _attach_head_to_head(fam, fam.seed_rows_val, cand_arrays, baselines, "val", int(args.bootstrap_n))
        _gate_from_val(fam, args)
        families.append(fam)
        seed_states_all[key] = seed_states
        failures[key] = fail_df

    chosen_key = None
    chosen_reason = "No candidate selected yet."
    promising = [fam for fam in families if _advance(fam)]
    if not promising:
        chosen_reason = "All RCWS-B variants failed to beat M/N/O on calib_val or failed the non-degeneracy gate; no candidate was allowed to consume test."
    else:
        promising = sorted(promising, key=lambda fam: float(np.mean([row["mean_delta_j"] for row in fam.seed_rows_val])), reverse=True)
        chosen = promising[0]
        chosen_key = chosen.key
        chosen_reason = "Selected by pooled calib_val performance with strict RCWS-B gates satisfied; only this candidate is allowed to consume test."
        chosen.status = "chosen_for_test"
        failure_df_test = _evaluate_test(chosen, seed_states_all[chosen.key], ctxs, baselines, args)
        failures[chosen.key] = failure_df_test
        if chosen.gate_check_test and all(bool(v) for v in chosen.gate_check_test.values()):
            chosen.status = "tested_positive"
        else:
            chosen.status = "tested_negative"

    summary = {
        "version": "step14_rcwsb_trials_v1",
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
        art_inputs = input_parquets if fam.advanced_to_test else {k: v for k, v in input_parquets.items() if "test" not in str(k)}
        _write_candidate_artifacts(fam, input_parquets=art_inputs, representative_rows=failures.get(fam.key))
    print(f"[step14-rcwsb] summary={args.summary_json}")
    print(f"[step14-rcwsb] report={args.report_md}")


if __name__ == "__main__":
    main()
