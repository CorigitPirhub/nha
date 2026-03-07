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
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_router_phase8_strict import _split_calib_train_val
from scripts.run_router_phase29_step12r4_trials_v1 import (
    ArmCache,
    FASTGEOM_COLS,
    STATIC_BASE_COLS,
    _is_feasible,
    _objective_from_calib_train,
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


@dataclass
class InnerContext:
    fit_df: pd.DataFrame
    regcal_df: pd.DataFrame
    fit_cache: ArmCache
    regcal_cache: ArmCache
    x_fit: pd.DataFrame
    x_regcal: pd.DataFrame
    x_val: pd.DataFrame
    x_test: pd.DataFrame


@dataclass
class RegimeModelState:
    incumbent_arm: str
    candidate_arms: list[str]
    n_clusters: int
    clf: Any
    aps_q: float
    templates_j: np.ndarray
    templates_d: np.ndarray
    templates_p: np.ndarray
    q_j: np.ndarray
    q_d: np.ndarray
    q_p: np.ndarray
    q_delta: np.ndarray


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step14 TARP-line strict trial runner (phase32).")
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
    p.add_argument("--path-rel-mean-max", type=float, default=0.01)
    p.add_argument("--path-rel-p95-max", type=float, default=0.05)
    p.add_argument("--max-cases", type=int, default=-1)
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase32_step14_tarp_line_v1.md"))
    p.add_argument("--summary-json", type=Path, default=Path("outputs/router_phase32_step14_tarp_line_v1/summary.json"))
    p.add_argument("--clusters", type=str, default="3,4")
    p.add_argument("--challenger-counts", type=str, default="2,3")
    p.add_argument("--cls-max-depths", type=str, default="2,3")
    p.add_argument("--cls-learning-rates", type=str, default="0.10")
    p.add_argument("--cls-max-iters", type=str, default="120,200")
    p.add_argument("--set-alphas", type=str, default="0.10,0.20")
    p.add_argument("--sample-path-guards", type=str, default="0.05")
    p.add_argument("--mix-lambdas", type=str, default="0.25,0.50")
    p.add_argument("--gate-margins", type=str, default="0.0002,0.0005")
    p.add_argument("--classifier-kind", type=str, default="tree", choices=["tree", "hgb"])
    p.add_argument("--families", type=str, default="F2A,F2B,F2C")
    return p.parse_args()


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


def _align_features(df_fit: pd.DataFrame, df_regcal: pd.DataFrame, df_val: pd.DataFrame, df_test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cols = STATIC_BASE_COLS + FASTGEOM_COLS + ["difficulty"]
    x_fit = pd.get_dummies(df_fit[cols], columns=["difficulty"], drop_first=False)
    x_regcal = pd.get_dummies(df_regcal[cols], columns=["difficulty"], drop_first=False).reindex(columns=x_fit.columns, fill_value=0)
    x_val = pd.get_dummies(df_val[cols], columns=["difficulty"], drop_first=False).reindex(columns=x_fit.columns, fill_value=0)
    x_test = pd.get_dummies(df_test[cols], columns=["difficulty"], drop_first=False).reindex(columns=x_fit.columns, fill_value=0)
    return x_fit, x_regcal, x_val, x_test


def _upper_pos_quantile(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    resid = np.maximum(np.asarray(y_true, dtype=np.float64) - np.asarray(y_pred, dtype=np.float64), 0.0)
    n = int(resid.size)
    if n <= 0:
        return 0.0
    level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / max(n, 1))
    return float(_stable_quantile(resid, level))


def _build_inner_context(ctx: SeedContext, *, inner_fit_frac: float, seed: int, weights: list[float]) -> InnerContext:
    fit_df, regcal_df, _ = _split_calib_train_val(ctx.cal_train, train_frac=float(inner_fit_frac), seed=int(seed))
    fit_cache = ArmCache(fit_df, weights, t_ref=float(ctx.t_ref), beta=float(ctx.beta))
    regcal_cache = ArmCache(regcal_df, weights, t_ref=float(ctx.t_ref), beta=float(ctx.beta))
    x_fit, x_regcal, x_val, x_test = _align_features(fit_df, regcal_df, ctx.cal_val, ctx.test)
    return InnerContext(
        fit_df=fit_df,
        regcal_df=regcal_df,
        fit_cache=fit_cache,
        regcal_cache=regcal_cache,
        x_fit=x_fit,
        x_regcal=x_regcal,
        x_val=x_val,
        x_test=x_test,
    )


def _best_feasible_constant(cache: ArmCache, arm_space: list[str], args: argparse.Namespace) -> str:
    best_arm = "fast"
    best_j = float("inf")
    for arm in arm_space:
        selected = np.asarray([arm] * len(cache.df), dtype=str)
        metrics = _selection_metrics(cache, selected, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        if not _is_feasible(metrics, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
            continue
        if float(metrics["J_mean"]) < float(best_j):
            best_arm = str(arm)
            best_j = float(metrics["J_mean"])
    return best_arm


def _candidate_arms(fit_cache: ArmCache, arm_space: list[str], incumbent: str, challenger_count: int) -> list[str]:
    inc_j = fit_cache.arms[incumbent]["J"]
    ranked = []
    for arm in arm_space:
        if arm == incumbent:
            continue
        mean_res = float(np.mean(fit_cache.arms[arm]["J"] - inc_j))
        ranked.append((mean_res, arm))
    ranked.sort(key=lambda x: x[0])
    challengers = [str(arm) for _, arm in ranked[: max(int(challenger_count), 1)]]
    return [str(incumbent)] + challengers


def _residual_embedding(cache: ArmCache, candidate_arms: list[str], incumbent: str) -> np.ndarray:
    inc_j = cache.arms[incumbent]["J"]
    inc_d = cache.arms[incumbent]["drel"]
    inc_p = cache.arms[incumbent]["path_rel"]
    cols = []
    for arm in candidate_arms:
        if arm == incumbent:
            continue
        cols.append((cache.arms[arm]["J"] - inc_j).astype(np.float64))
        cols.append((cache.arms[arm]["drel"] - inc_d).astype(np.float64))
        cols.append((cache.arms[arm]["path_rel"] - inc_p).astype(np.float64))
    if not cols:
        return np.zeros((len(cache.df), 1), dtype=np.float64)
    return np.stack(cols, axis=1).astype(np.float64)


def _align_probs(clf: HistGradientBoostingClassifier, x_df: pd.DataFrame, n_clusters: int) -> np.ndarray:
    raw = clf.predict_proba(x_df)
    probs = np.zeros((len(x_df), int(n_clusters)), dtype=np.float64)
    classes = np.asarray(clf.classes_, dtype=np.int64)
    probs[:, classes] = np.asarray(raw, dtype=np.float64)
    denom = np.sum(probs, axis=1, keepdims=True)
    probs = probs / np.maximum(denom, 1e-12)
    return probs


def _aps_quantile(probs: np.ndarray, labels: np.ndarray, alpha: float) -> float:
    scores = []
    for i in range(len(labels)):
        p = np.asarray(probs[i], dtype=np.float64)
        order = np.argsort(-p)
        cum = np.cumsum(p[order])
        pos = int(np.where(order == int(labels[i]))[0][0])
        scores.append(float(cum[pos]))
    scores_arr = np.asarray(scores, dtype=np.float64)
    n = int(scores_arr.size)
    if n <= 0:
        return 1.0
    level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / max(n, 1))
    return float(_stable_quantile(scores_arr, level))


def _aps_set(prob_row: np.ndarray, q: float) -> np.ndarray:
    p = np.asarray(prob_row, dtype=np.float64)
    order = np.argsort(-p)
    cum = np.cumsum(p[order])
    idx = int(np.searchsorted(cum, float(q), side="left"))
    idx = min(idx, len(order) - 1)
    keep = np.asarray(order[: idx + 1], dtype=np.int64)
    if keep.size <= 0:
        return np.asarray([int(order[0])], dtype=np.int64)
    return keep


def _template_means(cache: ArmCache, labels: np.ndarray, candidate_arms: list[str], n_clusters: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    global_j = np.asarray([np.mean(cache.arms[a]["J"]) for a in candidate_arms], dtype=np.float64)
    global_d = np.asarray([np.mean(cache.arms[a]["drel"]) for a in candidate_arms], dtype=np.float64)
    global_p = np.asarray([np.mean(cache.arms[a]["path_rel"]) for a in candidate_arms], dtype=np.float64)
    t_j = np.tile(global_j[None, :], (int(n_clusters), 1))
    t_d = np.tile(global_d[None, :], (int(n_clusters), 1))
    t_p = np.tile(global_p[None, :], (int(n_clusters), 1))
    labels = np.asarray(labels, dtype=np.int64)
    for r in range(int(n_clusters)):
        mask = labels == int(r)
        if int(np.sum(mask)) < 8:
            continue
        for a_idx, arm in enumerate(candidate_arms):
            t_j[r, a_idx] = float(np.mean(cache.arms[arm]["J"][mask]))
            t_d[r, a_idx] = float(np.mean(cache.arms[arm]["drel"][mask]))
            t_p[r, a_idx] = float(np.mean(cache.arms[arm]["path_rel"][mask]))
    return t_j, t_d, t_p


def _calibrate_template_errors(regcal_cache: ArmCache, labels_regcal: np.ndarray, candidate_arms: list[str], incumbent: str, templates_j: np.ndarray, templates_d: np.ndarray, templates_p: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    q_j = []
    q_d = []
    q_p = []
    q_delta = []
    inc_idx = candidate_arms.index(str(incumbent))
    labels_regcal = np.asarray(labels_regcal, dtype=np.int64)
    for a_idx, arm in enumerate(candidate_arms):
        y_j = regcal_cache.arms[arm]["J"]
        pred_j = templates_j[labels_regcal, a_idx]
        y_d = regcal_cache.arms[arm]["drel"]
        pred_d = templates_d[labels_regcal, a_idx]
        y_p = regcal_cache.arms[arm]["path_rel"]
        pred_p = templates_p[labels_regcal, a_idx]
        q_j.append(_upper_pos_quantile(y_j, pred_j, alpha=float(alpha)))
        q_d.append(_upper_pos_quantile(y_d, pred_d, alpha=float(alpha)))
        q_p.append(_upper_pos_quantile(y_p, pred_p, alpha=float(alpha)))
        y_delta = y_j - regcal_cache.arms[incumbent]["J"]
        pred_delta = templates_j[labels_regcal, a_idx] - templates_j[labels_regcal, inc_idx]
        q_delta.append(_upper_pos_quantile(y_delta, pred_delta, alpha=float(alpha)))
    return np.asarray(q_j, dtype=np.float64), np.asarray(q_d, dtype=np.float64), np.asarray(q_p, dtype=np.float64), np.asarray(q_delta, dtype=np.float64)


def _fit_regime_model(inner: InnerContext, ctx: SeedContext, args: argparse.Namespace, *, n_clusters: int, challenger_count: int, max_depth: int, learning_rate: float, max_iter: int, set_alpha: float, seed: int) -> RegimeModelState:
    incumbent = _best_feasible_constant(inner.fit_cache, ctx.arm_space, args)
    candidate_arms = _candidate_arms(inner.fit_cache, ctx.arm_space, incumbent, challenger_count)
    emb_fit = _residual_embedding(inner.fit_cache, candidate_arms, incumbent)
    mu = np.mean(emb_fit, axis=0, keepdims=True)
    sigma = np.std(emb_fit, axis=0, keepdims=True) + 1e-6
    emb_fit_z = (emb_fit - mu) / sigma
    kmeans = KMeans(n_clusters=int(n_clusters), n_init=10, random_state=int(seed))
    labels_fit = kmeans.fit_predict(emb_fit_z)
    emb_regcal = _residual_embedding(inner.regcal_cache, candidate_arms, incumbent)
    labels_regcal = kmeans.predict((emb_regcal - mu) / sigma)
    if str(args.classifier_kind) == "tree":
        del learning_rate, max_iter
        clf = DecisionTreeClassifier(max_depth=int(max_depth), random_state=int(seed) + 701, min_samples_leaf=20)
    else:
        clf = HistGradientBoostingClassifier(max_depth=int(max_depth), learning_rate=float(learning_rate), max_iter=int(max_iter), random_state=int(seed) + 701)
    clf.fit(inner.x_fit, labels_fit)
    probs_regcal = _align_probs(clf, inner.x_regcal, int(n_clusters))
    aps_q = _aps_quantile(probs_regcal, labels_regcal, alpha=float(set_alpha))
    templates_j, templates_d, templates_p = _template_means(inner.fit_cache, labels_fit, candidate_arms, int(n_clusters))
    q_j, q_d, q_p, q_delta = _calibrate_template_errors(inner.regcal_cache, labels_regcal, candidate_arms, incumbent, templates_j, templates_d, templates_p, alpha=float(set_alpha))
    return RegimeModelState(
        incumbent_arm=str(incumbent),
        candidate_arms=list(candidate_arms),
        n_clusters=int(n_clusters),
        clf=clf,
        aps_q=float(aps_q),
        templates_j=templates_j,
        templates_d=templates_d,
        templates_p=templates_p,
        q_j=q_j,
        q_d=q_d,
        q_p=q_p,
        q_delta=q_delta,
    )


def _select_rrsv(state: RegimeModelState, x_df: pd.DataFrame, *, eps_rel: float, sample_path_guard: float) -> tuple[np.ndarray, dict[str, float]]:
    probs = _align_probs(state.clf, x_df, state.n_clusters)
    selected = []
    set_sizes = []
    entropies = []
    for i in range(len(x_df)):
        p = probs[i]
        S = _aps_set(p, state.aps_q)
        set_sizes.append(float(len(S)))
        entropies.append(float(-np.sum(p * np.log(np.maximum(p, 1e-12)))))
        best_arm = str(state.incumbent_arm)
        best_score = float("inf")
        for a_idx, arm in enumerate(state.candidate_arms):
            if arm == state.incumbent_arm:
                score = 0.0
            else:
                score = float(np.max(state.templates_j[S, a_idx]) + state.q_j[a_idx])
            risk_up = float(np.max(state.templates_d[S, a_idx]) + state.q_d[a_idx])
            path_up = float(np.max(state.templates_p[S, a_idx]) + state.q_p[a_idx])
            if arm != state.incumbent_arm and (risk_up > float(eps_rel) or path_up > float(sample_path_guard)):
                continue
            if score < best_score:
                best_score = score
                best_arm = str(arm)
        selected.append(best_arm)
    return np.asarray(selected, dtype=str), {
        "regime_set_size_mean": float(np.mean(set_sizes)) if set_sizes else 0.0,
        "posterior_entropy_mean": float(np.mean(entropies)) if entropies else 0.0,
    }


def _select_rrmix(state: RegimeModelState, x_df: pd.DataFrame, *, eps_rel: float, sample_path_guard: float, mix_lambda: float) -> tuple[np.ndarray, dict[str, float]]:
    probs = _align_probs(state.clf, x_df, state.n_clusters)
    selected = []
    entropies = []
    for i in range(len(x_df)):
        p = probs[i]
        entropies.append(float(-np.sum(p * np.log(np.maximum(p, 1e-12)))))
        best_arm = str(state.incumbent_arm)
        best_score = float("inf")
        for a_idx, arm in enumerate(state.candidate_arms):
            mu_j = float(np.dot(p, state.templates_j[:, a_idx]))
            mu_d = float(np.dot(p, state.templates_d[:, a_idx]))
            mu_p = float(np.dot(p, state.templates_p[:, a_idx]))
            std_j = float(np.sqrt(np.dot(p, np.square(state.templates_j[:, a_idx] - mu_j))))
            std_d = float(np.sqrt(np.dot(p, np.square(state.templates_d[:, a_idx] - mu_d))))
            std_p = float(np.sqrt(np.dot(p, np.square(state.templates_p[:, a_idx] - mu_p))))
            score = mu_j + float(state.q_j[a_idx]) + float(mix_lambda) * std_j
            risk_up = mu_d + float(state.q_d[a_idx]) + float(mix_lambda) * std_d
            path_up = mu_p + float(state.q_p[a_idx]) + float(mix_lambda) * std_p
            if arm != state.incumbent_arm and (risk_up > float(eps_rel) or path_up > float(sample_path_guard)):
                continue
            if score < best_score:
                best_score = score
                best_arm = str(arm)
        selected.append(best_arm)
    return np.asarray(selected, dtype=str), {
        "posterior_entropy_mean": float(np.mean(entropies)) if entropies else 0.0,
    }


def _select_rrgate(state: RegimeModelState, x_df: pd.DataFrame, *, eps_rel: float, sample_path_guard: float, gate_margin: float) -> tuple[np.ndarray, dict[str, float]]:
    probs = _align_probs(state.clf, x_df, state.n_clusters)
    selected = []
    set_sizes = []
    inc_idx = state.candidate_arms.index(str(state.incumbent_arm))
    for i in range(len(x_df)):
        p = probs[i]
        S = _aps_set(p, state.aps_q)
        set_sizes.append(float(len(S)))
        best_arm = str(state.incumbent_arm)
        best_improve = 0.0
        for a_idx, arm in enumerate(state.candidate_arms):
            if arm == state.incumbent_arm:
                continue
            improve_up = float(np.max(state.templates_j[S, a_idx] - state.templates_j[S, inc_idx]) + state.q_delta[a_idx])
            risk_up = float(np.max(state.templates_d[S, a_idx]) + state.q_d[a_idx])
            path_up = float(np.max(state.templates_p[S, a_idx]) + state.q_p[a_idx])
            if risk_up > float(eps_rel) or path_up > float(sample_path_guard):
                continue
            if improve_up < -float(gate_margin) and improve_up < best_improve:
                best_improve = improve_up
                best_arm = str(arm)
        selected.append(best_arm)
    return np.asarray(selected, dtype=str), {
        "regime_set_size_mean": float(np.mean(set_sizes)) if set_sizes else 0.0,
    }


def _tarp_gate_from_val(result: FamilyResult, seed_rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    h2h = result.head_to_head_val
    unique_arms = sorted({str(k) for row in seed_rows for k, v in row.get("arm_distribution", {}).items() if float(v) > 1e-12})
    dominant_list = []
    for row in seed_rows:
        ad = row.get("arm_distribution", {})
        if isinstance(ad, dict) and ad:
            dominant_list.append(max(float(v) for v in ad.values()))
    nonconst_count = int(sum(float(v) < 0.95 for v in dominant_list))
    gate = {
        "risk_ci95_upper_le_alpha_all_seeds": bool(all(float(r["violation_ci95_upper"]) <= float(args.alpha) + 1e-12 for r in seed_rows)),
        "path_audit_hold_all_seeds": bool(all(float(r["path_rel_mean"]) <= float(args.path_rel_mean_max) + 1e-12 and float(r["path_rel_p95"]) <= float(args.path_rel_p95_max) + 1e-12 for r in seed_rows)),
        "beats_M_on_val_mean": bool(float(h2h["M"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_N_on_val_mean": bool(float(h2h["N"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_O_on_val_mean": bool(float(h2h["O"]["pooled"]["mean_delta_j"]) > 0.0),
        "unique_arms": unique_arms,
        "dominant_arm_fraction_max": float(max(dominant_list) if dominant_list else 1.0),
        "nonconstant_seed_count": int(nonconst_count),
        "not_constantized": bool((len(unique_arms) >= 2) and (nonconst_count >= 3)),
    }
    result.gate_check_val = gate
    return gate


def _advance_tarp(result: FamilyResult) -> bool:
    gate = result.gate_check_val
    return bool(
        gate.get("risk_ci95_upper_le_alpha_all_seeds", False)
        and gate.get("path_audit_hold_all_seeds", False)
        and gate.get("beats_M_on_val_mean", False)
        and gate.get("beats_N_on_val_mean", False)
        and gate.get("beats_O_on_val_mean", False)
        and gate.get("not_constantized", False)
    )


def _evaluate_test_tarp(result: FamilyResult, seed_states: dict[int, dict[str, Any]], ctxs: dict[int, SeedContext], baselines: dict[str, dict[int, dict[str, Any]]], args: argparse.Namespace) -> pd.DataFrame | None:
    seed_rows_test = []
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None
    for seed, ctx in ctxs.items():
        selected_test = np.asarray(seed_states[seed]["selected_test"], dtype=str)
        metrics_test = _selection_metrics(ctx.cache_test, selected_test, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        row, _ = _summarize_seed(seed=seed, test_metrics=metrics_test, j_p5_test=ctx.j_p5_test, selected_test=selected_test, method_name=f"{result.name}(test)", policy_desc=seed_states[seed].get("params", {}))
        for key, val in seed_states[seed].get("summary_test", {}).items():
            row[str(key)] = float(val)
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


def _eval_tarp_variant(
    *,
    ctxs: dict[int, SeedContext],
    inner_ctxs: dict[int, InnerContext],
    args: argparse.Namespace,
    key: str,
    name: str,
    out_dir: Path,
    decision_kind: str,
) -> tuple[FamilyResult, dict[int, dict[str, Any]], dict[int, np.ndarray], pd.DataFrame | None]:
    seed_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays: dict[int, np.ndarray] = {}
    failure_df = None

    clusters = _parse_int_list(args.clusters)
    challenger_counts = _parse_int_list(args.challenger_counts)
    depths = _parse_int_list(args.cls_max_depths)
    lrs = _parse_float_list(args.cls_learning_rates)
    max_iters = _parse_int_list(args.cls_max_iters)
    set_alphas = _parse_float_list(args.set_alphas)
    sample_path_guards = _parse_float_list(args.sample_path_guards)
    mix_lambdas = _parse_float_list(args.mix_lambdas)
    gate_margins = _parse_float_list(args.gate_margins)

    for seed in sorted(ctxs.keys()):
        ctx = ctxs[seed]
        inner = inner_ctxs[seed]
        best = None
        for n_clusters, challenger_count, depth, lr, max_iter, set_alpha in product(clusters, challenger_counts, depths, lrs, max_iters, set_alphas):
            model_state = _fit_regime_model(inner, ctx, args, n_clusters=int(n_clusters), challenger_count=int(challenger_count), max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), set_alpha=float(set_alpha), seed=int(seed))
            base_cfg = {
                "n_clusters": int(n_clusters),
                "challenger_count": int(challenger_count),
                "depth": int(depth),
                "learning_rate": float(lr),
                "max_iter": int(max_iter),
                "set_alpha": float(set_alpha),
                "incumbent_arm": model_state.incumbent_arm,
                "candidate_arms": list(model_state.candidate_arms),
            }
            if decision_kind == "rrsv":
                decision_grid = [(float(pg),) for pg in sample_path_guards]
            elif decision_kind == "rrmix":
                decision_grid = [(float(pg), float(lam)) for pg, lam in product(sample_path_guards, mix_lambdas)]
            elif decision_kind == "rrgate":
                decision_grid = [(float(pg), float(margin)) for pg, margin in product(sample_path_guards, gate_margins)]
            else:
                raise ValueError(decision_kind)
            for decision_params in decision_grid:
                if decision_kind == "rrsv":
                    sample_path_guard = decision_params[0]
                    selected_val, summary_val = _select_rrsv(model_state, inner.x_val, eps_rel=float(args.epsilon_rel), sample_path_guard=float(sample_path_guard))
                    selected_test, summary_test = _select_rrsv(model_state, inner.x_test, eps_rel=float(args.epsilon_rel), sample_path_guard=float(sample_path_guard))
                    cfg = {**base_cfg, "sample_path_guard": float(sample_path_guard)}
                elif decision_kind == "rrmix":
                    sample_path_guard, mix_lambda = decision_params
                    selected_val, summary_val = _select_rrmix(model_state, inner.x_val, eps_rel=float(args.epsilon_rel), sample_path_guard=float(sample_path_guard), mix_lambda=float(mix_lambda))
                    selected_test, summary_test = _select_rrmix(model_state, inner.x_test, eps_rel=float(args.epsilon_rel), sample_path_guard=float(sample_path_guard), mix_lambda=float(mix_lambda))
                    cfg = {**base_cfg, "sample_path_guard": float(sample_path_guard), "mix_lambda": float(mix_lambda)}
                else:
                    sample_path_guard, gate_margin = decision_params
                    selected_val, summary_val = _select_rrgate(model_state, inner.x_val, eps_rel=float(args.epsilon_rel), sample_path_guard=float(sample_path_guard), gate_margin=float(gate_margin))
                    selected_test, summary_test = _select_rrgate(model_state, inner.x_test, eps_rel=float(args.epsilon_rel), sample_path_guard=float(sample_path_guard), gate_margin=float(gate_margin))
                    cfg = {**base_cfg, "sample_path_guard": float(sample_path_guard), "gate_margin": float(gate_margin)}
                metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
                ablation_rows.append(
                    {
                        "seed": int(seed),
                        "decision_kind": str(decision_kind),
                        **cfg,
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
                    best = {
                        "selected_val": selected_val,
                        "selected_test": selected_test,
                        "metrics_val": metrics_val,
                        "params": cfg,
                        "summary_val": summary_val,
                        "summary_test": summary_test,
                    }
        if best is None:
            incumbent = _best_feasible_constant(inner.fit_cache, ctx.arm_space, args)
            selected_val = np.asarray([incumbent] * len(ctx.cal_val), dtype=str)
            selected_test = np.asarray([incumbent] * len(ctx.test), dtype=str)
            best = {
                "selected_val": selected_val,
                "selected_test": selected_test,
                "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha)),
                "params": {"fallback_incumbent": str(incumbent)},
                "summary_val": {},
                "summary_test": {},
            }
        row, _ = _summarize_seed(seed=int(seed), test_metrics=best["metrics_val"], j_p5_test=ctx.j_p5_val, selected_test=best["selected_val"], method_name=f"{name}(val)", policy_desc=best["params"])
        for k, v in best.get("summary_val", {}).items():
            row[str(k)] = float(v)
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(best["metrics_val"]["J_array"], dtype=np.float64)
        seed_states[seed] = {
            "selected_test": best["selected_test"],
            "params": best["params"],
            "summary_test": best.get("summary_test", {}),
        }
        if failure_df is None:
            failure_df = _representative_failures(ctx.cal_val, best["selected_val"], ctx.cache_val, ctx.j_p5_val)
        print(f"[step14-tarp:{decision_kind}] seed {seed} done; best_params={best['params']}")
    pooled = _pooled_stats(np.concatenate([ctxs[s].j_p5_val - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key=str(key), name=str(name), out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": str(name), "decision_kind": str(decision_kind)})
    return result, seed_states, cand_arrays, failure_df


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    weights = _parse_weights(args.weights)
    calib, test, input_parquets = _build_common_tables(args, weights)
    ctxs = _build_seed_contexts(args, calib, test, weights)
    baselines = _fit_baselines(ctxs, args)
    inner_ctxs = {
        seed: _build_inner_context(ctx, inner_fit_frac=float(args.inner_fit_frac), seed=int(args.calib_split_seed) + 1000 + int(seed), weights=weights)
        for seed, ctx in ctxs.items()
    }

    families: list[FamilyResult] = []
    seed_states_all: dict[str, dict[int, dict[str, Any]]] = {}
    failures: dict[str, pd.DataFrame | None] = {}

    suffix = "_hgb_v1" if str(args.classifier_kind) == "hgb" else "_v1"
    all_specs = {
        "F2A": ("F2A", "TARP-RRSV", ROOT / f"outputs/router_phase32_step14_f2a_tarp_rrsv{suffix}", "rrsv"),
        "F2B": ("F2B", "TARP-RRMIX", ROOT / f"outputs/router_phase32_step14_f2b_tarp_rrmix{suffix}", "rrmix"),
        "F2C": ("F2C", "TARP-RRGATE", ROOT / f"outputs/router_phase32_step14_f2c_tarp_rrgate{suffix}", "rrgate"),
    }
    family_order = [x.strip() for x in str(args.families).split(",") if x.strip()]
    family_specs = [all_specs[k] for k in family_order]

    for key, name, out_dir, decision_kind in family_specs:
        fam, seed_states, cand_arrays, fail_df = _eval_tarp_variant(ctxs=ctxs, inner_ctxs=inner_ctxs, args=args, key=key, name=name, out_dir=out_dir, decision_kind=decision_kind)
        _attach_head_to_head(fam, fam.seed_rows_val, cand_arrays, baselines, "val", int(args.bootstrap_n))
        _tarp_gate_from_val(fam, fam.seed_rows_val, args)
        families.append(fam)
        seed_states_all[key] = seed_states
        failures[key] = fail_df

    chosen_key = None
    chosen_reason = "No candidate selected yet."
    promising = [fam for fam in families if _advance_tarp(fam)]
    if not promising:
        chosen_reason = "All TARP-line variants failed to beat M/N/O on calib_val or failed the TARP non-degeneracy gate; no candidate was allowed to consume test."
    else:
        promising = sorted(promising, key=lambda fam: float(np.mean([row["mean_delta_j"] for row in fam.seed_rows_val])), reverse=True)
        chosen = promising[0]
        chosen_key = chosen.key
        chosen_reason = "Selected by pooled calib_val performance with TARP-line strict gates satisfied; only this candidate is allowed to consume test."
        chosen.status = "chosen_for_test"
        failure_df_test = _evaluate_test_tarp(chosen, seed_states_all[chosen.key], ctxs, baselines, args)
        failures[chosen.key] = failure_df_test
        if chosen.gate_check_test and all(bool(v) for v in chosen.gate_check_test.values()):
            chosen.status = "tested_positive"
        else:
            chosen.status = "tested_negative"

    summary = {
        "version": "step14_tarp_line_v1",
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
    print(f"[step14-tarp] summary={args.summary_json}")
    print(f"[step14-tarp] report={args.report_md}")


if __name__ == "__main__":
    main()
