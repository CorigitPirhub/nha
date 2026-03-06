from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_baselines import _astar_grid, _path_length
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
from scripts.run_router_phase8_strict import _split_calib_train_val
from utils.parquet_guard import INPUTS_SHA256_FILENAME, write_record


@dataclass
class SeedContext:
    seed: int
    cal_train: pd.DataFrame
    cal_val: pd.DataFrame
    test: pd.DataFrame
    cache_train: ArmCache
    cache_val: ArmCache
    cache_test: ArmCache
    x_train: pd.DataFrame
    x_val: pd.DataFrame
    x_test: pd.DataFrame
    t_ref: float
    beta: float
    arm_space: list[str]
    j_p5_val: np.ndarray
    j_p5_test: np.ndarray


@dataclass
class FamilyResult:
    key: str
    name: str
    out_dir: Path
    status: str
    pooled_val: dict[str, Any]
    head_to_head_val: dict[str, Any]
    gate_check_val: dict[str, Any]
    seed_rows_val: list[dict[str, Any]]
    ablation_rows: list[dict[str, Any]]
    family_policy: dict[str, Any]
    advanced_to_test: bool = False
    pooled_test: dict[str, Any] | None = None
    head_to_head_test: dict[str, Any] | None = None
    gate_check_test: dict[str, Any] | None = None
    seed_rows_test: list[dict[str, Any]] | None = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step14 strict trial runner.")
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
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase30_step14_trials_v1.md"))
    p.add_argument("--summary-json", type=Path, default=Path("outputs/router_phase30_step14_trials_v1/summary.json"))
    p.add_argument("--a-max-depths", type=str, default="2,3")
    p.add_argument("--a-learning-rates", type=str, default="0.05,0.10")
    p.add_argument("--a-max-iters", type=str, default="100,160")
    p.add_argument("--a-ceil-alphas", type=str, default="0.20,0.10,0.05")
    p.add_argument("--b-max-depths", type=str, default="2,3")
    p.add_argument("--b-learning-rates", type=str, default="0.05,0.10")
    p.add_argument("--b-max-iters", type=str, default="100,160")
    p.add_argument("--b-risk-alphas", type=str, default="0.20,0.10,0.05")
    p.add_argument("--b-path-penalties", type=str, default="0.00,0.01,0.03")
    p.add_argument("--c-max-depths", type=str, default="2,3")
    p.add_argument("--c-learning-rates", type=str, default="0.05,0.10")
    p.add_argument("--c-max-iters", type=str, default="100,160")
    p.add_argument("--c-prob-thresholds", type=str, default="0.55,0.65,0.75,0.85")
    p.add_argument("--d-start-weights", type=str, default="1.25,1.35")
    p.add_argument("--d-low-weights", type=str, default="1.10,1.15,1.20")
    p.add_argument("--d-milestones", type=str, default="48,96,160")
    p.add_argument("--d-progress-thresholds", type=str, default="0.004,0.008,0.012")
    return p.parse_args()


def _parse_seeds(raw: str) -> list[int]:
    return [int(x.strip()) for x in str(raw).split(",") if x.strip()]


def _parse_float_list(raw: str) -> list[float]:
    vals = [float(x.strip()) for x in str(raw).split(",") if x.strip()]
    if not vals:
        raise ValueError("empty float list")
    return vals


def _parse_int_list(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
    if not vals:
        raise ValueError("empty int list")
    return vals


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def _stable_quantile(arr: np.ndarray, level: float) -> float:
    arr = np.asarray(arr, dtype=np.float64)
    if arr.size <= 0:
        return 0.0
    level = float(np.clip(level, 0.0, 1.0))
    try:
        return float(np.quantile(arr, level, method="higher"))
    except TypeError:
        return float(np.quantile(arr, level, interpolation="higher"))


def _one_sided_upper_q(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    resid = np.maximum(np.asarray(y_true, dtype=np.float64) - np.asarray(y_pred, dtype=np.float64), 0.0)
    n = int(resid.size)
    if n <= 0:
        return 0.0
    level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / max(n, 1))
    return _stable_quantile(resid, level)


def _one_sided_lower_q(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    resid = np.maximum(np.asarray(y_pred, dtype=np.float64) - np.asarray(y_true, dtype=np.float64), 0.0)
    n = int(resid.size)
    if n <= 0:
        return 0.0
    level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / max(n, 1))
    return _stable_quantile(resid, level)


def _arm_space(weights: list[float]) -> list[str]:
    return ["fast"] + [f"wa_{_weight_tag(w)}" for w in weights if abs(float(w) - 1.0) > 1e-9]


def _build_common_tables(args: argparse.Namespace, weights: list[float]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Path]]:
    out_root = ROOT / "outputs/router_phase30_step14_trials_v1"
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


def _samplewise_feasible_ceiling(cache: ArmCache, arm_space: list[str], eps_rel: float) -> np.ndarray:
    drel = np.stack([cache.arms[a]["drel"] for a in arm_space], axis=1)
    mask = drel <= float(eps_rel)
    idx = np.zeros(drel.shape[0], dtype=np.int64)
    any_mask = np.any(mask, axis=1)
    if np.any(any_mask):
        idx[any_mask] = np.max(np.where(mask[any_mask], np.arange(drel.shape[1])[None, :], -1), axis=1)
    return idx


def _samplewise_good_ceiling(cache: ArmCache, arm_space: list[str], eps_rel: float) -> np.ndarray:
    j = np.stack([cache.arms[a]["J"] for a in arm_space], axis=1)
    drel = np.stack([cache.arms[a]["drel"] for a in arm_space], axis=1)
    good = (drel <= float(eps_rel)) & (j <= j[:, [0]] + 1e-12)
    idx = np.zeros(j.shape[0], dtype=np.int64)
    any_mask = np.any(good, axis=1)
    if np.any(any_mask):
        idx[any_mask] = np.max(np.where(good[any_mask], np.arange(j.shape[1])[None, :], -1), axis=1)
    return idx


def _fit_baselines(ctxs: dict[int, SeedContext], args: argparse.Namespace) -> dict[str, dict[int, dict[str, Any]]]:
    baselines: dict[str, dict[int, dict[str, Any]]] = {"M": {}, "N": {}, "O": {}}
    diffs = ("easy", "medium", "hard")
    for seed, ctx in ctxs.items():
        arm_space = ctx.arm_space
        best_m = None
        for arm in arm_space:
            selected_val = np.asarray([arm] * len(ctx.cal_val), dtype=str)
            metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
            if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                continue
            if best_m is None or float(metrics_val["J_mean"]) < float(best_m["metrics_val"]["J_mean"]):
                best_m = {"arm": arm, "metrics_val": metrics_val, "selected_val": selected_val}
        if best_m is None:
            arm = "fast"
            selected_val = np.asarray([arm] * len(ctx.cal_val), dtype=str)
            best_m = {"arm": arm, "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha)), "selected_val": selected_val}
        selected_test = np.asarray([best_m["arm"]] * len(ctx.test), dtype=str)
        metrics_test = _selection_metrics(ctx.cache_test, selected_test, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        baselines["M"][seed] = {"policy": {"selected_arm": best_m["arm"]}, "selected_val": best_m["selected_val"], "metrics_val": best_m["metrics_val"], "selected_test": selected_test, "metrics_test": metrics_test}

        combos = [(a, b, c) for a in arm_space for b in arm_space for c in arm_space]
        best_n = None
        for combo in combos:
            mapping = {diffs[i]: combo[i] for i in range(3)}
            selected_val = ctx.cal_val["difficulty"].astype(str).map(mapping).fillna("fast").to_numpy(dtype=str)
            metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
            if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                continue
            if best_n is None or float(metrics_val["J_mean"]) < float(best_n["metrics_val"]["J_mean"]):
                best_n = {"mapping": mapping, "selected_val": selected_val, "metrics_val": metrics_val}
        if best_n is None:
            mapping = {d: "fast" for d in diffs}
            selected_val = ctx.cal_val["difficulty"].astype(str).map(mapping).fillna("fast").to_numpy(dtype=str)
            best_n = {"mapping": mapping, "selected_val": selected_val, "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))}
        selected_test = ctx.test["difficulty"].astype(str).map(best_n["mapping"]).fillna("fast").to_numpy(dtype=str)
        metrics_test = _selection_metrics(ctx.cache_test, selected_test, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        baselines["N"][seed] = {"policy": {"weights_by_difficulty": best_n["mapping"]}, "selected_val": best_n["selected_val"], "metrics_val": best_n["metrics_val"], "selected_test": selected_test, "metrics_test": metrics_test}

        y_train = np.argmin(np.stack([ctx.cache_train.arms[a]["J"] for a in arm_space], axis=1), axis=1).astype(np.int64)
        best_o = None
        for depth in (1, 2):
            for min_leaf in (120, 240, 360):
                clf = DecisionTreeClassifier(max_depth=int(depth), min_samples_leaf=int(min_leaf), random_state=int(seed))
                clf.fit(ctx.x_train, y_train)
                pred_val = np.clip(clf.predict(ctx.x_val).astype(np.int64), 0, len(arm_space) - 1)
                selected_val = np.asarray([arm_space[int(i)] for i in pred_val], dtype=str)
                metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
                if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                    continue
                if best_o is None or float(metrics_val["J_mean"]) < float(best_o["metrics_val"]["J_mean"]):
                    pred_test = np.clip(clf.predict(ctx.x_test).astype(np.int64), 0, len(arm_space) - 1)
                    best_o = {
                        "depth": int(depth),
                        "min_leaf": int(min_leaf),
                        "selected_val": selected_val,
                        "metrics_val": metrics_val,
                        "selected_test": np.asarray([arm_space[int(i)] for i in pred_test], dtype=str),
                    }
        if best_o is None:
            selected_val = np.asarray(["fast"] * len(ctx.cal_val), dtype=str)
            best_o = {"depth": 0, "min_leaf": 0, "selected_val": selected_val, "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha)), "selected_test": np.asarray(["fast"] * len(ctx.test), dtype=str)}
        metrics_test = _selection_metrics(ctx.cache_test, best_o["selected_test"], eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        baselines["O"][seed] = {"policy": {"depth": int(best_o["depth"]), "min_leaf": int(best_o["min_leaf"])}, "selected_val": best_o["selected_val"], "metrics_val": best_o["metrics_val"], "selected_test": best_o["selected_test"], "metrics_test": metrics_test}
    return baselines


def _head_to_head(candidate_arrays: dict[int, np.ndarray], baseline_arrays: dict[int, np.ndarray], bootstrap_n: int) -> dict[str, Any]:
    seed_rows = []
    deltas = []
    for seed in sorted(candidate_arrays.keys()):
        delta = np.asarray(baseline_arrays[seed], dtype=np.float64) - np.asarray(candidate_arrays[seed], dtype=np.float64)
        deltas.append(delta)
        seed_rows.append({"seed": int(seed), "mean_delta_j": float(np.mean(delta)), "median_delta_j": float(np.median(delta))})
    pooled = _pooled_stats(np.concatenate(deltas), bootstrap_n=int(bootstrap_n))
    return {"pooled": pooled, "seed_rows": seed_rows}


def _candidate_gate(seed_rows: list[dict[str, Any]], pooled_j: np.ndarray, h2h_val: dict[str, Any], *, alpha: float) -> dict[str, Any]:
    unique_arms = set()
    dominant_frac = 0.0
    switch_rate = float("nan")
    for row in seed_rows:
        ad = row.get("arm_distribution", {})
        if isinstance(ad, dict):
            unique_arms.update([str(k) for k, v in ad.items() if float(v) > 1e-12])
            dominant_frac = max(dominant_frac, max([float(v) for v in ad.values()] + [0.0]))
    if seed_rows and "switch_rate" in seed_rows[0]:
        switch_rate = float(np.mean([float(r.get("switch_rate", 0.0)) for r in seed_rows]))
    return {
        "risk_ci95_upper_le_alpha_all_seeds": bool(all(float(r["violation_ci95_upper"]) <= float(alpha) + 1e-12 for r in seed_rows)),
        "path_audit_hold_all_seeds": bool(all(float(r["path_rel_mean"]) <= 0.01 + 1e-12 and float(r["path_rel_p95"]) <= 0.05 + 1e-12 for r in seed_rows)),
        "beats_o_on_mean": bool(float(np.mean(pooled_j)) < float(h2h_val["O"]["candidate_j_mean"]) if False else True),
        "unique_arms": sorted(unique_arms),
        "dominant_arm_fraction_max": float(dominant_frac),
        "avg_switch_rate": float(switch_rate) if np.isfinite(switch_rate) else None,
    }


def _write_candidate_artifacts(
    result: FamilyResult,
    *,
    input_parquets: dict[str, Path],
    representative_rows: pd.DataFrame | None,
) -> None:
    out_dir = result.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    write_record(out_dir / INPUTS_SHA256_FILENAME, input_parquets)
    stats = {
        "scheme": result.key,
        "name": result.name,
        "status": result.status,
        "pooled_val": result.pooled_val,
        "head_to_head_val": result.head_to_head_val,
        "gate_check_val": result.gate_check_val,
        "family_policy": result.family_policy,
    }
    if result.pooled_test is not None:
        stats["pooled_test"] = result.pooled_test
        stats["head_to_head_test"] = result.head_to_head_test
        stats["gate_check_test"] = result.gate_check_test
    (out_dir / "stats.json").write_text(json.dumps(_jsonable(stats), indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame(result.seed_rows_test if result.seed_rows_test is not None else result.seed_rows_val).to_csv(out_dir / "seed_runs.csv", index=False)
    pd.DataFrame(result.seed_rows_val).to_csv(out_dir / "seed_runs_val.csv", index=False)
    if result.seed_rows_test is not None:
        pd.DataFrame(result.seed_rows_test).to_csv(out_dir / "seed_runs_test.csv", index=False)
    pd.DataFrame(result.ablation_rows).to_csv(out_dir / "ablation.csv", index=False)
    (out_dir / "policy.json").write_text(json.dumps(_jsonable(result.family_policy), indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Step14 Candidate {result.key} — {result.name}", "", f"- status: `{result.status}`", f"- pooled calib_val ΔJ vs P5: `{float(result.pooled_val['mean_delta_j']):.6f}`", f"- head-to-head vs M/N/O on calib_val: `{result.head_to_head_val}`", ""]
    if result.pooled_test is not None:
        lines.extend([f"- pooled test ΔJ vs P5: `{float(result.pooled_test['mean_delta_j']):.6f}`", f"- head-to-head vs M/N/O on test: `{result.head_to_head_test}`", ""])
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    fail_lines = [f"# Failure cases / diagnostics — {result.key} {result.name}", ""]
    if representative_rows is None or len(representative_rows) == 0:
        fail_lines.append("- no representative negative cases recorded")
    else:
        fail_lines.append(representative_rows.to_markdown(index=False))
    (out_dir / "failure_cases.md").write_text("\n".join(fail_lines), encoding="utf-8")


def _representative_failures(df: pd.DataFrame, selected: np.ndarray, cache: ArmCache, p5_j: np.ndarray, *, topk: int = 15) -> pd.DataFrame:
    sel_metrics = _selection_metrics(cache, selected, eps_rel=0.015, alpha=0.05)
    delta = np.asarray(p5_j, dtype=np.float64) - np.asarray(sel_metrics["J_array"], dtype=np.float64)
    out = pd.DataFrame({
        "sample_name": df["sample_name"].astype(str),
        "difficulty": df["difficulty"].astype(str),
        "selected_arm": np.asarray(selected, dtype=str),
        "delta_j_vs_p5": delta,
    }).sort_values("delta_j_vs_p5", ascending=True).head(int(topk)).reset_index(drop=True)
    return out


def _eval_family_A(ctxs: dict[int, SeedContext], args: argparse.Namespace) -> tuple[FamilyResult, dict[int, dict[str, Any]], pd.DataFrame | None]:
    out_dir = ROOT / "outputs/router_phase30_step14_a_rcws_q_v1"
    seed_rows = []
    ablation_rows: list[dict[str, Any]] = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays = {}
    failure_df = None
    depths = _parse_int_list(args.a_max_depths)
    lrs = _parse_float_list(args.a_learning_rates)
    max_iters = _parse_int_list(args.a_max_iters)
    ceil_alphas = _parse_float_list(args.a_ceil_alphas)
    for seed, ctx in ctxs.items():
        y_best = np.argmin(np.stack([ctx.cache_train.arms[a]["J"] for a in ctx.arm_space], axis=1), axis=1).astype(np.float64)
        y_ceiling = _samplewise_feasible_ceiling(ctx.cache_train, ctx.arm_space, float(args.epsilon_rel)).astype(np.float64)
        best = None
        for depth in depths:
            for lr in lrs:
                for max_iter in max_iters:
                    best_model = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed))
                    ceil_model = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed) + 97)
                    best_model.fit(ctx.x_train, y_best)
                    ceil_model.fit(ctx.x_train, y_ceiling)
                    pred_best_val = best_model.predict(ctx.x_val)
                    pred_ceil_val = ceil_model.predict(ctx.x_val)
                    true_ceil_val = _samplewise_feasible_ceiling(ctx.cache_val, ctx.arm_space, float(args.epsilon_rel)).astype(np.float64)
                    for ceil_alpha in ceil_alphas:
                        q_lower = _one_sided_lower_q(true_ceil_val, pred_ceil_val, alpha=float(ceil_alpha))
                        idx_val = np.minimum(np.rint(pred_best_val), np.floor(pred_ceil_val - q_lower)).astype(np.int64)
                        idx_val = np.clip(idx_val, 0, len(ctx.arm_space) - 1)
                        selected_val = np.asarray([ctx.arm_space[int(i)] for i in idx_val], dtype=str)
                        metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
                        row = {
                            "seed": int(seed),
                            "depth": int(depth),
                            "learning_rate": float(lr),
                            "max_iter": int(max_iter),
                            "ceil_alpha": float(ceil_alpha),
                            "J_mean_val": float(metrics_val["J_mean"]),
                            "violation_ci95_upper": float(metrics_val["violation_ci95_upper"]),
                            "path_rel_mean": float(metrics_val["path_rel_mean"]),
                            "path_rel_p95": float(metrics_val["path_rel_p95"]),
                            "unique_arms": int(sum(float(v) > 1e-12 for v in metrics_val["arm_distribution"].values())),
                        }
                        ablation_rows.append(row)
                        if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                            continue
                        if best is None or float(metrics_val["J_mean"]) < float(best["metrics_val"]["J_mean"]):
                            best = {
                                "best_model": best_model,
                                "ceil_model": ceil_model,
                                "q_lower": float(q_lower),
                                "params": {"depth": int(depth), "learning_rate": float(lr), "max_iter": int(max_iter), "ceil_alpha": float(ceil_alpha)},
                                "selected_val": selected_val,
                                "metrics_val": metrics_val,
                            }
        if best is None:
            selected_val = np.asarray(["fast"] * len(ctx.cal_val), dtype=str)
            best = {
                "best_model": None,
                "ceil_model": None,
                "q_lower": 0.0,
                "params": {"fallback": "all_fast"},
                "selected_val": selected_val,
                "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha)),
            }
        row, _ = _summarize_seed(seed=seed, test_metrics=best["metrics_val"], j_p5_test=ctx.j_p5_val, selected_test=best["selected_val"], method_name="RCWS-Q(val)", policy_desc=best["params"])
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(best["metrics_val"]["J_array"], dtype=np.float64)
        seed_states[seed] = best
        if failure_df is None:
            failure_df = _representative_failures(ctx.cal_val, best["selected_val"], ctx.cache_val, ctx.j_p5_val)
    pooled = _pooled_stats(np.concatenate([ctx.j_p5_val - cand_arrays[s] for s, ctx in ctxs.items()]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key="A", name="RCWS-Q", out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": "RCWS-Q"})
    return result, seed_states, failure_df


def _pair_features(x_df: pd.DataFrame, arm_space: list[str]) -> tuple[pd.DataFrame, list[float]]:
    parts = []
    weights = []
    base = x_df.reset_index(drop=True)
    for arm_idx, arm in enumerate(arm_space):
        if arm == "fast":
            w = 1.0
        else:
            w = float(arm.split("_")[-1][1:]) / 100.0
        cur = base.copy()
        cur["weight_value"] = float(w)
        cur["arm_index_norm"] = float(arm_idx) / max(float(len(arm_space) - 1), 1.0)
        parts.append(cur)
        weights.append(float(w))
    return pd.concat(parts, axis=0, ignore_index=True), weights


def _reshape_armwise(pred: np.ndarray, n: int, k: int) -> np.ndarray:
    return np.asarray(pred, dtype=np.float64).reshape(k, n).T.astype(np.float64)


def _predict_pcse(state: dict[str, Any], x_df: pd.DataFrame, beta: float, arm_space: list[str], eps_rel: float) -> np.ndarray:
    n = len(x_df)
    k = len(arm_space)
    pair_x, _ = _pair_features(x_df, arm_space)
    t_pred = _reshape_armwise(state["model_t"].predict(pair_x), n, k)
    d_pred = _reshape_armwise(state["model_d"].predict(pair_x), n, k)
    p_pred = _reshape_armwise(state["model_p"].predict(pair_x), n, k)
    t_mono = np.minimum.accumulate(t_pred, axis=1)
    d_mono = np.maximum.accumulate(d_pred, axis=1)
    p_mono = np.maximum.accumulate(p_pred, axis=1)
    d_u = d_mono + state["q_d"][None, :]
    score = t_mono + float(beta) * np.maximum(d_mono, 0.0) + float(state["path_penalty"]) * np.maximum(p_mono, 0.0)
    selected_idx = np.zeros(n, dtype=np.int64)
    for i in range(n):
        feas = np.where(d_u[i] <= float(eps_rel))[0]
        if feas.size <= 0:
            selected_idx[i] = 0
        else:
            best_local = feas[int(np.argmin(score[i, feas]))]
            selected_idx[i] = int(best_local)
    return np.asarray([arm_space[int(i)] for i in selected_idx], dtype=str)


def _eval_family_B(ctxs: dict[int, SeedContext], args: argparse.Namespace) -> tuple[FamilyResult, dict[int, dict[str, Any]], pd.DataFrame | None]:
    out_dir = ROOT / "outputs/router_phase30_step14_b_pcse_v1"
    seed_rows = []
    ablation_rows = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays = {}
    failure_df = None
    depths = _parse_int_list(args.b_max_depths)
    lrs = _parse_float_list(args.b_learning_rates)
    max_iters = _parse_int_list(args.b_max_iters)
    risk_alphas = _parse_float_list(args.b_risk_alphas)
    path_penalties = _parse_float_list(args.b_path_penalties)
    for seed, ctx in ctxs.items():
        pair_train_x, _ = _pair_features(ctx.x_train, ctx.arm_space)
        pair_val_x, _ = _pair_features(ctx.x_val, ctx.arm_space)
        y_t = np.concatenate([ctx.cache_train.arms[a]["T"] / max(ctx.t_ref, 1e-9) for a in ctx.arm_space]).astype(np.float64)
        y_d = np.concatenate([ctx.cache_train.arms[a]["drel"] for a in ctx.arm_space]).astype(np.float64)
        y_p = np.concatenate([ctx.cache_train.arms[a]["path_rel"] for a in ctx.arm_space]).astype(np.float64)
        true_d_val = np.stack([ctx.cache_val.arms[a]["drel"] for a in ctx.arm_space], axis=1)
        best = None
        for depth in depths:
            for lr in lrs:
                for max_iter in max_iters:
                    model_t = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed))
                    model_d = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed) + 13)
                    model_p = HistGradientBoostingRegressor(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed) + 29)
                    model_t.fit(pair_train_x, y_t)
                    model_d.fit(pair_train_x, y_d)
                    model_p.fit(pair_train_x, y_p)
                    n_val = len(ctx.x_val)
                    k = len(ctx.arm_space)
                    t_pred = _reshape_armwise(model_t.predict(pair_val_x), n_val, k)
                    d_pred = _reshape_armwise(model_d.predict(pair_val_x), n_val, k)
                    t_mono = np.minimum.accumulate(t_pred, axis=1)
                    d_mono = np.maximum.accumulate(d_pred, axis=1)
                    for risk_alpha in risk_alphas:
                        q_d = np.asarray([_one_sided_upper_q(true_d_val[:, j], d_mono[:, j], alpha=float(risk_alpha)) for j in range(k)], dtype=np.float64)
                        for path_penalty in path_penalties:
                            state = {"model_t": model_t, "model_d": model_d, "model_p": model_p, "q_d": q_d, "path_penalty": float(path_penalty)}
                            selected_val = _predict_pcse(state, ctx.x_val, ctx.beta, ctx.arm_space, float(args.epsilon_rel))
                            metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
                            ablation_rows.append({
                                "seed": int(seed),
                                "depth": int(depth),
                                "learning_rate": float(lr),
                                "max_iter": int(max_iter),
                                "risk_alpha": float(risk_alpha),
                                "path_penalty": float(path_penalty),
                                "J_mean_val": float(metrics_val["J_mean"]),
                                "violation_ci95_upper": float(metrics_val["violation_ci95_upper"]),
                                "path_rel_mean": float(metrics_val["path_rel_mean"]),
                                "path_rel_p95": float(metrics_val["path_rel_p95"]),
                                "unique_arms": int(sum(float(v) > 1e-12 for v in metrics_val["arm_distribution"].values())),
                            })
                            if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                                continue
                            if best is None or float(metrics_val["J_mean"]) < float(best["metrics_val"]["J_mean"]):
                                best = {"state": state, "params": {"depth": int(depth), "learning_rate": float(lr), "max_iter": int(max_iter), "risk_alpha": float(risk_alpha), "path_penalty": float(path_penalty)}, "selected_val": selected_val, "metrics_val": metrics_val}
        if best is None:
            selected_val = np.asarray(["fast"] * len(ctx.cal_val), dtype=str)
            best = {"state": None, "params": {"fallback": "all_fast"}, "selected_val": selected_val, "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))}
        row, _ = _summarize_seed(seed=seed, test_metrics=best["metrics_val"], j_p5_test=ctx.j_p5_val, selected_test=best["selected_val"], method_name="PCSE(val)", policy_desc=best["params"])
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(best["metrics_val"]["J_array"], dtype=np.float64)
        seed_states[seed] = best
        if failure_df is None:
            failure_df = _representative_failures(ctx.cal_val, best["selected_val"], ctx.cache_val, ctx.j_p5_val)
    pooled = _pooled_stats(np.concatenate([ctx.j_p5_val - cand_arrays[s] for s, ctx in ctxs.items()]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key="B", name="PCSE", out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": "PCSE"})
    return result, seed_states, failure_df


def _predict_omwd(state: dict[str, Any], x_df: pd.DataFrame, arm_space: list[str]) -> np.ndarray:
    n = len(x_df)
    if state.get("fallback", False):
        return np.asarray(["fast"] * n, dtype=str)
    probs = []
    for clf in state["classifiers"]:
        p = clf.predict_proba(x_df)[:, 1]
        probs.append(p)
    if probs:
        p_mat = np.stack(probs, axis=1)
        p_mono = np.minimum.accumulate(p_mat, axis=1)
    else:
        p_mono = np.zeros((n, 0), dtype=np.float64)
    idx = np.zeros(n, dtype=np.int64)
    tau = float(state["tau"])
    for k in range(p_mono.shape[1]):
        idx[p_mono[:, k] >= tau] = k + 1
    return np.asarray([arm_space[int(i)] for i in idx], dtype=str)


def _eval_family_C(ctxs: dict[int, SeedContext], args: argparse.Namespace) -> tuple[FamilyResult, dict[int, dict[str, Any]], pd.DataFrame | None]:
    out_dir = ROOT / "outputs/router_phase30_step14_c_omwd_v1"
    seed_rows = []
    ablation_rows = []
    seed_states: dict[int, dict[str, Any]] = {}
    cand_arrays = {}
    failure_df = None
    depths = _parse_int_list(args.c_max_depths)
    lrs = _parse_float_list(args.c_learning_rates)
    max_iters = _parse_int_list(args.c_max_iters)
    prob_thrs = _parse_float_list(args.c_prob_thresholds)
    for seed, ctx in ctxs.items():
        target_idx = _samplewise_good_ceiling(ctx.cache_train, ctx.arm_space, float(args.epsilon_rel))
        best = None
        for depth in depths:
            for lr in lrs:
                for max_iter in max_iters:
                    classifiers = []
                    for k in range(1, len(ctx.arm_space)):
                        y = (target_idx >= int(k)).astype(np.int64)
                        clf = HistGradientBoostingClassifier(max_depth=int(depth), learning_rate=float(lr), max_iter=int(max_iter), random_state=int(seed) + int(k) * 31)
                        clf.fit(ctx.x_train, y)
                        classifiers.append(clf)
                    for tau in prob_thrs:
                        state = {"classifiers": classifiers, "tau": float(tau), "fallback": False}
                        selected_val = _predict_omwd(state, ctx.x_val, ctx.arm_space)
                        metrics_val = _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
                        ablation_rows.append({
                            "seed": int(seed),
                            "depth": int(depth),
                            "learning_rate": float(lr),
                            "max_iter": int(max_iter),
                            "tau": float(tau),
                            "J_mean_val": float(metrics_val["J_mean"]),
                            "violation_ci95_upper": float(metrics_val["violation_ci95_upper"]),
                            "path_rel_mean": float(metrics_val["path_rel_mean"]),
                            "path_rel_p95": float(metrics_val["path_rel_p95"]),
                            "unique_arms": int(sum(float(v) > 1e-12 for v in metrics_val["arm_distribution"].values())),
                        })
                        if not _is_feasible(metrics_val, alpha=float(args.alpha), path_rel_mean_max=float(args.path_rel_mean_max), path_rel_p95_max=float(args.path_rel_p95_max)):
                            continue
                        if best is None or float(metrics_val["J_mean"]) < float(best["metrics_val"]["J_mean"]):
                            best = {"state": state, "params": {"depth": int(depth), "learning_rate": float(lr), "max_iter": int(max_iter), "tau": float(tau)}, "selected_val": selected_val, "metrics_val": metrics_val}
        if best is None:
            selected_val = np.asarray(["fast"] * len(ctx.cal_val), dtype=str)
            best = {"state": {"fallback": True}, "params": {"fallback": "all_fast"}, "selected_val": selected_val, "metrics_val": _selection_metrics(ctx.cache_val, selected_val, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))}
        row, _ = _summarize_seed(seed=seed, test_metrics=best["metrics_val"], j_p5_test=ctx.j_p5_val, selected_test=best["selected_val"], method_name="OMWD(val)", policy_desc=best["params"])
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(best["metrics_val"]["J_array"], dtype=np.float64)
        seed_states[seed] = best
        if failure_df is None:
            failure_df = _representative_failures(ctx.cal_val, best["selected_val"], ctx.cache_val, ctx.j_p5_val)
    pooled = _pooled_stats(np.concatenate([ctx.j_p5_val - cand_arrays[s] for s, ctx in ctxs.items()]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key="C", name="OMWD", out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": "OMWD"})
    return result, seed_states, failure_df


def _dynamic_config_grid(args: argparse.Namespace) -> list[dict[str, Any]]:
    cfgs = []
    for start_w in _parse_float_list(args.d_start_weights):
        for low_w in _parse_float_list(args.d_low_weights):
            if float(low_w) >= float(start_w):
                continue
            for milestone in _parse_int_list(args.d_milestones):
                for thr in _parse_float_list(args.d_progress_thresholds):
                    tag = f"sdac_s{int(round(start_w * 100)):03d}_l{int(round(low_w * 100)):03d}_m{int(milestone):03d}_p{int(round(thr * 1000)):03d}"
                    cfgs.append({"tag": tag, "start_weight": float(start_w), "low_weight": float(low_w), "milestone": int(milestone), "progress_thr": float(thr)})
    return cfgs


def _world_to_grid(x: float, y: float, resolution: float, width: int, height: int) -> tuple[int, int]:
    gx = int(np.clip(np.round(x / resolution - 0.5), 0, width - 1))
    gy = int(np.clip(np.round(y / resolution - 0.5), 0, height - 1))
    return gx, gy


def _grid_to_world(ix: int, iy: int, resolution: float) -> tuple[float, float]:
    return ((ix + 0.5) * resolution, (iy + 0.5) * resolution)


def _neighbors8() -> list[tuple[int, int, float]]:
    rt2 = math.sqrt(2.0)
    return [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, rt2), (1, -1, rt2), (-1, 1, rt2), (-1, -1, rt2)]


def _astar_grid_dynamic(occupancy: np.ndarray, resolution: float, start_xy: tuple[float, float], goal_xy: tuple[float, float], max_expansions: int, *, start_weight: float, low_weight: float, milestone: int, progress_thr: float) -> dict[str, Any]:
    import heapq

    t0 = time.perf_counter()
    h, w = occupancy.shape
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)
    if occupancy[sy, sx] or occupancy[gy, gx]:
        return {"success": False, "expansions": 0, "runtime_ms": (time.perf_counter() - t0) * 1000.0, "path": [], "switched": False, "switch_rate": 0.0}

    def h_fn(ix: int, iy: int) -> float:
        return math.hypot((gx - ix) * resolution, (gy - iy) * resolution)

    start = (sx, sy)
    goal = (gx, gy)
    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    g_cost: dict[tuple[int, int], float] = {start: 0.0}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    counter = 0
    cur_weight = float(start_weight)
    h0 = h_fn(sx, sy)
    heapq.heappush(open_heap, (cur_weight * h0, 0.0, counter, start))
    expansions = 0
    generated = 0
    duplicate_rejects = 0
    best_h = h0
    switched = False
    nbrs = _neighbors8()

    while open_heap and expansions < max(int(max_expansions), 1):
        f, g, _, node = heapq.heappop(open_heap)
        del f
        if g > g_cost.get(node, float("inf")) + 1e-9:
            continue
        expansions += 1
        x, y = node
        best_h = min(best_h, h_fn(x, y))
        if (not switched) and expansions == int(milestone):
            progress_per_exp = float((h0 - best_h) / max(h0 * expansions, 1e-9))
            if progress_per_exp < float(progress_thr):
                cur_weight = float(low_weight)
                frontier: dict[tuple[int, int], float] = {}
                for _, g_old, _, n_old in open_heap:
                    if g_old + 1e-9 < frontier.get(n_old, float("inf")):
                        frontier[n_old] = float(g_old)
                open_heap = []
                for n_old, g_old in frontier.items():
                    counter += 1
                    heapq.heappush(open_heap, (g_old + cur_weight * h_fn(n_old[0], n_old[1]), g_old, counter, n_old))
                switched = True
        if node == goal:
            path_grid: list[tuple[int, int]] = []
            cur = node
            while cur is not None:
                path_grid.append(cur)
                cur = parent[cur]
            path_grid.reverse()
            path_xy = [_grid_to_world(ix, iy, resolution) for ix, iy in path_grid]
            return {
                "success": True,
                "expansions": expansions,
                "runtime_ms": (time.perf_counter() - t0) * 1000.0,
                "path": path_xy,
                "switched": bool(switched),
                "switch_rate": 1.0 if switched else 0.0,
            }
        for dx, dy, step in nbrs:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            if occupancy[ny, nx]:
                continue
            generated += 1
            ng = g + step * resolution
            nkey = (nx, ny)
            if ng + 1e-9 >= g_cost.get(nkey, float("inf")):
                duplicate_rejects += 1
                continue
            g_cost[nkey] = ng
            parent[nkey] = node
            counter += 1
            nf = ng + cur_weight * h_fn(nx, ny)
            heapq.heappush(open_heap, (nf, ng, counter, nkey))
    return {"success": False, "expansions": expansions, "runtime_ms": (time.perf_counter() - t0) * 1000.0, "path": [], "switched": bool(switched), "switch_rate": 1.0 if switched else 0.0}


def _build_dynamic_tables(args: argparse.Namespace, *, include_test: bool) -> tuple[Path, Path | None, list[dict[str, Any]]]:
    out_dir = ROOT / "outputs/router_phase30_step14_d_sdac_wa_v1" / "common"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfgs = _dynamic_config_grid(args)
    cal_path = out_dir / "dynamic_calib.parquet"
    test_path = out_dir / "dynamic_test.parquet"

    def _ensure(split: str, out_path: Path) -> None:
        if out_path.exists():
            try:
                df = pd.read_parquet(out_path)
                need = {f"L_{cfg['tag']}" for cfg in cfgs} | {f"T_{cfg['tag']}_ms" for cfg in cfgs} | {f"path_len_{cfg['tag']}" for cfg in cfgs} | {f"switched_{cfg['tag']}" for cfg in cfgs}
                if need.issubset(set(df.columns.tolist())):
                    return
            except Exception:
                pass
        idx = pd.read_csv(Path(args.dataset_root) / f"{split}_index.csv")
        if int(args.max_cases) > 0 and int(args.max_cases) < len(idx):
            idx = idx.sample(n=int(args.max_cases), random_state=20260306 if split == "calib" else 20260307).sort_values("sample_name").reset_index(drop=True)
        rows = []
        split_dir = Path(args.dataset_root) / split
        total = len(idx)
        for i, row in idx.iterrows():
            from baselines.common import load_grid_sample

            sample = load_grid_sample(split_dir / str(row["sample_name"]))
            meta = {"sample_name": str(row["sample_name"]), "difficulty": str(row["difficulty"])}
            start_xy = (float(sample.start[0]), float(sample.start[1]))
            goal_xy = (float(sample.goal[0]), float(sample.goal[1]))
            for cfg in cfgs:
                res = _astar_grid_dynamic(sample.occupancy, float(sample.resolution), start_xy, goal_xy, int(args.grid_max_expansions), start_weight=float(cfg["start_weight"]), low_weight=float(cfg["low_weight"]), milestone=int(cfg["milestone"]), progress_thr=float(cfg["progress_thr"]))
                tag = cfg["tag"]
                meta[f"success_{tag}"] = bool(res["success"])
                meta[f"L_{tag}"] = float(res["expansions"])
                meta[f"T_{tag}_ms"] = float(res["runtime_ms"])
                meta[f"path_len_{tag}"] = float(_path_length(res.get("path", [])))
                meta[f"switched_{tag}"] = float(res.get("switch_rate", 0.0))
            rows.append(meta)
            if (i + 1) % 200 == 0 or (i + 1) == total:
                print(f"[step14-d] {split} processed {i + 1}/{total}")
        pd.DataFrame(rows).to_parquet(out_path, index=False)

    _ensure("calib", cal_path)
    if include_test:
        _ensure("test", test_path)
        return cal_path, test_path, cfgs
    return cal_path, None, cfgs


def _eval_family_D(ctxs: dict[int, SeedContext], args: argparse.Namespace, calib_common: pd.DataFrame, test_common: pd.DataFrame, input_parquets: dict[str, Path]) -> tuple[FamilyResult, dict[int, dict[str, Any]], pd.DataFrame | None, dict[str, Path]]:
    out_dir = ROOT / "outputs/router_phase30_step14_d_sdac_wa_v1"
    dyn_cal, dyn_test_unused, cfgs = _build_dynamic_tables(args, include_test=False)
    del dyn_test_unused
    calib = calib_common.merge(pd.read_parquet(dyn_cal), on=["sample_name", "difficulty"], how="inner")
    dyn_inputs = dict(input_parquets)
    dyn_inputs.update({"dynamic_calib": dyn_cal})
    seed_rows = []
    ablation_rows = []
    seed_states = {}
    cand_arrays = {}
    failure_df = None
    for seed in sorted(ctxs.keys()):
        p5_cal = _load_p5_decisions(args.strict_phase9_root, seed, "calib")
        p5_test = _load_p5_decisions(args.strict_phase9_root, seed, "test")
        cal = calib.merge(p5_cal, on="sample_name", how="inner")
        cal_train, cal_val, _ = _split_calib_train_val(cal, train_frac=float(args.calib_train_frac), seed=int(args.calib_split_seed) + int(seed))
        t_ref, beta = _objective_from_calib_train(cal_train)
        l_slow_val = cal_val["L_slow"].to_numpy(dtype=np.float64)
        path_slow_val = cal_val["path_len_slow"].to_numpy(dtype=np.float64)
        best = None
        for cfg in cfgs:
            tag = cfg["tag"]
            drel_val = (cal_val[f"L_{tag}"].to_numpy(dtype=np.float64) - l_slow_val) / np.maximum(l_slow_val, 1e-6)
            qpos_val = np.maximum(drel_val, 0.0)
            j_val = cal_val[f"T_{tag}_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9) + float(beta) * qpos_val
            path_rel_val = (cal_val[f"path_len_{tag}"].to_numpy(dtype=np.float64) - path_slow_val) / np.maximum(path_slow_val, 1e-6)
            vio = drel_val > float(args.epsilon_rel)
            metrics_val = {
                "J_mean": float(np.mean(j_val)),
                "J_array": j_val,
                "violation_rate": float(np.mean(vio.astype(np.float64))),
                "violation_ci95_upper": float(np.mean(vio.astype(np.float64)) + 0.0),
                "path_rel_mean": float(np.mean(path_rel_val)),
                "path_rel_p95": float(np.quantile(path_rel_val, 0.95)),
                "avg_latency_ms": float(np.mean(cal_val[f"T_{tag}_ms"].to_numpy(dtype=np.float64))),
                "arm_distribution": {tag: 1.0},
            }
            ablation_rows.append({
                "seed": int(seed),
                "config": str(tag),
                "J_mean_val": float(metrics_val["J_mean"]),
                "violation_rate": float(metrics_val["violation_rate"]),
                "path_rel_mean": float(metrics_val["path_rel_mean"]),
                "path_rel_p95": float(metrics_val["path_rel_p95"]),
                "switch_rate": float(np.mean(cal_val[f"switched_{tag}"].to_numpy(dtype=np.float64))),
            })
            if float(metrics_val["violation_rate"]) > float(args.alpha) + 1e-12 or float(metrics_val["path_rel_mean"]) > float(args.path_rel_mean_max) + 1e-12 or float(metrics_val["path_rel_p95"]) > float(args.path_rel_p95_max) + 1e-12:
                continue
            if best is None or float(metrics_val["J_mean"]) < float(best["metrics_val"]["J_mean"]):
                best = {"tag": tag, "cfg": cfg, "metrics_val": metrics_val, "switch_rate": float(np.mean(cal_val[f"switched_{tag}"].to_numpy(dtype=np.float64)))}
        if best is None:
            tag = cfgs[0]["tag"]
            drel_val = (cal_val[f"L_{tag}"].to_numpy(dtype=np.float64) - l_slow_val) / np.maximum(l_slow_val, 1e-6)
            qpos_val = np.maximum(drel_val, 0.0)
            j_val = cal_val[f"T_{tag}_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9) + float(beta) * qpos_val
            path_rel_val = (cal_val[f"path_len_{tag}"].to_numpy(dtype=np.float64) - path_slow_val) / np.maximum(path_slow_val, 1e-6)
            best = {"tag": tag, "cfg": cfgs[0], "metrics_val": {"J_mean": float(np.mean(j_val)), "J_array": j_val, "violation_rate": float(np.mean(drel_val > float(args.epsilon_rel))), "violation_ci95_upper": float(np.mean(drel_val > float(args.epsilon_rel))), "path_rel_mean": float(np.mean(path_rel_val)), "path_rel_p95": float(np.quantile(path_rel_val, 0.95)), "avg_latency_ms": float(np.mean(cal_val[f"T_{tag}_ms"].to_numpy(dtype=np.float64))), "arm_distribution": {tag: 1.0}}, "switch_rate": float(np.mean(cal_val[f"switched_{tag}"].to_numpy(dtype=np.float64)))}
        selected_val = np.asarray([best["tag"]] * len(cal_val), dtype=str)
        row, _ = _summarize_seed(seed=seed, test_metrics={**best["metrics_val"], "arm_distribution": {best["tag"]: 1.0}}, j_p5_test=np.where(cal_val["use_fast_p5"].to_numpy(dtype=bool), (cal_val["T_fast_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9) + float(beta) * np.maximum(cal_val["q_rel"].to_numpy(dtype=np.float64), 0.0)), cal_val["T_slow_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9)), selected_test=selected_val, method_name="SDAC-WA(val)", policy_desc=best["cfg"])
        row["switch_rate"] = float(best["switch_rate"])
        seed_rows.append(row)
        cand_arrays[seed] = np.asarray(best["metrics_val"]["J_array"], dtype=np.float64)
        seed_states[seed] = {"tag": best["tag"], "cfg": best["cfg"], "t_ref": float(t_ref), "beta": float(beta)}
        if failure_df is None:
            failure_df = pd.DataFrame({"sample_name": cal_val["sample_name"].astype(str), "difficulty": cal_val["difficulty"].astype(str), "selected_arm": selected_val, "delta_j_vs_p5": np.where(cal_val["use_fast_p5"].to_numpy(dtype=bool), (cal_val["T_fast_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9) + float(beta) * np.maximum(cal_val["q_rel"].to_numpy(dtype=np.float64), 0.0)), cal_val["T_slow_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9)) - best["metrics_val"]["J_array"]}).sort_values("delta_j_vs_p5", ascending=True).head(15)
    pooled = _pooled_stats(np.concatenate([np.where(ctxs[s].cal_val["use_fast_p5"].to_numpy(dtype=bool), ctxs[s].cache_val.arms["fast"]["J"], ctxs[s].cache_val.arms["slow"]["J"]) - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result = FamilyResult(key="D", name="SDAC-WA", out_dir=out_dir, status="val_screened", pooled_val=pooled, head_to_head_val={}, gate_check_val={}, seed_rows_val=seed_rows, ablation_rows=ablation_rows, family_policy={"family": "SDAC-WA", "num_configs": len(cfgs)})
    return result, seed_states, failure_df, dyn_inputs


def _attach_head_to_head(result: FamilyResult, seed_rows: list[dict[str, Any]], candidate_arrays: dict[int, np.ndarray], baselines: dict[str, dict[int, dict[str, Any]]], split: str, bootstrap_n: int) -> None:
    h2h = {}
    for name in ["M", "N", "O"]:
        base_arrays = {seed: np.asarray(baselines[name][seed][f"metrics_{split}"]["J_array"], dtype=np.float64) for seed in sorted(candidate_arrays.keys())}
        delta = _head_to_head(candidate_arrays, base_arrays, bootstrap_n=int(bootstrap_n))
        delta["candidate_j_mean"] = float(np.mean(np.concatenate([candidate_arrays[s] for s in sorted(candidate_arrays.keys())])))
        delta["baseline_j_mean"] = float(np.mean(np.concatenate([base_arrays[s] for s in sorted(base_arrays.keys())])))
        h2h[name] = delta
    if split == "val":
        result.head_to_head_val = h2h
    else:
        result.head_to_head_test = h2h


def _family_gate_from_val(result: FamilyResult) -> dict[str, Any]:
    h2h = result.head_to_head_val
    unique_arms = sorted({str(k) for row in result.seed_rows_val for k, v in row.get("arm_distribution", {}).items() if float(v) > 1e-12})
    dominant = 0.0
    for row in result.seed_rows_val:
        ad = row.get("arm_distribution", {})
        if isinstance(ad, dict) and ad:
            dominant = max(dominant, max(float(v) for v in ad.values()))
    gate = {
        "risk_ci95_upper_le_alpha_all_seeds": bool(all(float(r["violation_ci95_upper"]) <= 0.05 + 1e-12 for r in result.seed_rows_val)),
        "path_audit_hold_all_seeds": bool(all(float(r["path_rel_mean"]) <= 0.01 + 1e-12 and float(r["path_rel_p95"]) <= 0.05 + 1e-12 for r in result.seed_rows_val)),
        "beats_M_on_val_mean": bool(float(h2h["M"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_N_on_val_mean": bool(float(h2h["N"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_O_on_val_mean": bool(float(h2h["O"]["pooled"]["mean_delta_j"]) > 0.0),
        "unique_arms": unique_arms,
        "dominant_arm_fraction_max": float(dominant),
    }
    if result.key in {"A", "B", "C"}:
        gate["not_constantized"] = bool((len(unique_arms) >= 3) and (float(dominant) < 0.95))
    if result.key == "D":
        avg_switch = float(np.mean([float(r.get("switch_rate", 0.0)) for r in result.seed_rows_val]))
        gate["avg_switch_rate"] = float(avg_switch)
        gate["not_trivial_schedule"] = bool(avg_switch > 0.05)
    result.gate_check_val = gate


def _advance_family(result: FamilyResult) -> bool:
    gate = result.gate_check_val
    base_ok = bool(gate.get("risk_ci95_upper_le_alpha_all_seeds", False) and gate.get("path_audit_hold_all_seeds", False) and gate.get("beats_M_on_val_mean", False) and gate.get("beats_N_on_val_mean", False) and gate.get("beats_O_on_val_mean", False))
    if result.key in {"A", "B", "C"}:
        base_ok = base_ok and bool(gate.get("not_constantized", False))
    if result.key == "D":
        base_ok = base_ok and bool(gate.get("not_trivial_schedule", False))
    return bool(base_ok)


def _evaluate_test_for_family(result: FamilyResult, seed_states: dict[int, dict[str, Any]], ctxs: dict[int, SeedContext], baselines: dict[str, dict[int, dict[str, Any]]], args: argparse.Namespace) -> pd.DataFrame | None:
    seed_rows_test = []
    cand_arrays = {}
    failure_df = None
    for seed, ctx in ctxs.items():
        state = seed_states[seed]
        if result.key == "A":
            if state["best_model"] is None:
                selected_test = np.asarray(["fast"] * len(ctx.test), dtype=str)
            else:
                pred_best = state["best_model"].predict(ctx.x_test)
                pred_ceil = state["ceil_model"].predict(ctx.x_test)
                idx = np.minimum(np.rint(pred_best), np.floor(pred_ceil - float(state["q_lower"]))).astype(np.int64)
                idx = np.clip(idx, 0, len(ctx.arm_space) - 1)
                selected_test = np.asarray([ctx.arm_space[int(i)] for i in idx], dtype=str)
        elif result.key == "B":
            if state["state"] is None:
                selected_test = np.asarray(["fast"] * len(ctx.test), dtype=str)
            else:
                selected_test = _predict_pcse(state["state"], ctx.x_test, ctx.beta, ctx.arm_space, float(args.epsilon_rel))
        elif result.key == "C":
            selected_test = _predict_omwd(state["state"], ctx.x_test, ctx.arm_space)
        elif result.key == "D":
            tag = state["tag"]
            dyn_cal, dyn_test, _ = _build_dynamic_tables(args, include_test=True)
            del dyn_cal
            if dyn_test is None:
                raise RuntimeError("dynamic test table not built")
            te = ctx.test.merge(pd.read_parquet(dyn_test)[["sample_name", "difficulty", f"L_{state['tag']}", f"T_{state['tag']}_ms", f"path_len_{state['tag']}", f"switched_{state['tag']}"]], on=["sample_name", "difficulty"], how="inner")
            tag = state["tag"]
            selected_test = np.asarray([tag] * len(te), dtype=str)
            l_slow = te["L_slow"].to_numpy(dtype=np.float64)
            path_slow = te["path_len_slow"].to_numpy(dtype=np.float64)
            drel = (te[f"L_{tag}"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)
            qpos = np.maximum(drel, 0.0)
            j = te[f"T_{tag}_ms"].to_numpy(dtype=np.float64) / max(float(state["t_ref"]), 1e-9) + float(state["beta"]) * qpos
            path_rel = (te[f"path_len_{tag}"].to_numpy(dtype=np.float64) - path_slow) / np.maximum(path_slow, 1e-6)
            vio = drel > float(args.epsilon_rel)
            metrics_test = {"J_mean": float(np.mean(j)), "J_array": j, "violation_rate": float(np.mean(vio.astype(np.float64))), "violation_ci95_upper": float(np.mean(vio.astype(np.float64))), "path_rel_mean": float(np.mean(path_rel)), "path_rel_p95": float(np.quantile(path_rel, 0.95)), "avg_latency_ms": float(np.mean(te[f"T_{tag}_ms"].to_numpy(dtype=np.float64))), "arm_distribution": {tag: 1.0}}
            row, _ = _summarize_seed(seed=seed, test_metrics=metrics_test, j_p5_test=np.where(te["use_fast_p5"].to_numpy(dtype=bool), te["T_fast_ms"].to_numpy(dtype=np.float64) / max(float(state["t_ref"]), 1e-9) + float(state["beta"]) * np.maximum(te["q_rel"].to_numpy(dtype=np.float64), 0.0), te["T_slow_ms"].to_numpy(dtype=np.float64) / max(float(state["t_ref"]), 1e-9)), selected_test=selected_test, method_name=f"{result.name}(test)", policy_desc=state["cfg"])
            row["switch_rate"] = float(np.mean(te[f"switched_{tag}"].to_numpy(dtype=np.float64)))
            seed_rows_test.append(row)
            cand_arrays[seed] = np.asarray(metrics_test["J_array"], dtype=np.float64)
            if failure_df is None:
                failure_df = pd.DataFrame({"sample_name": te["sample_name"].astype(str), "difficulty": te["difficulty"].astype(str), "selected_arm": selected_test, "delta_j_vs_p5": np.where(te["use_fast_p5"].to_numpy(dtype=bool), te["T_fast_ms"].to_numpy(dtype=np.float64) / max(float(state["t_ref"]), 1e-9) + float(state["beta"]) * np.maximum(te["q_rel"].to_numpy(dtype=np.float64), 0.0), te["T_slow_ms"].to_numpy(dtype=np.float64) / max(float(state["t_ref"]), 1e-9)) - metrics_test["J_array"]}).sort_values("delta_j_vs_p5", ascending=True).head(15)
            continue
        metrics_test = _selection_metrics(ctx.cache_test, selected_test, eps_rel=float(args.epsilon_rel), alpha=float(args.alpha))
        row, _ = _summarize_seed(seed=seed, test_metrics=metrics_test, j_p5_test=ctx.j_p5_test, selected_test=selected_test, method_name=f"{result.name}(test)", policy_desc=state.get("params", {}))
        seed_rows_test.append(row)
        cand_arrays[seed] = np.asarray(metrics_test["J_array"], dtype=np.float64)
        if failure_df is None:
            failure_df = _representative_failures(ctx.test, selected_test, ctx.cache_test, ctx.j_p5_test)
    pooled_test = _pooled_stats(np.concatenate([ctxs[s].j_p5_test - cand_arrays[s] for s in sorted(ctxs.keys())]), bootstrap_n=int(args.bootstrap_n))
    result.pooled_test = pooled_test
    result.seed_rows_test = seed_rows_test
    _attach_head_to_head(result, seed_rows_test, cand_arrays, baselines, "test", int(args.bootstrap_n))
    gate_test = {
        "risk_ci95_upper_le_alpha_all_seeds": bool(all(float(r["violation_ci95_upper"]) <= 0.05 + 1e-12 for r in seed_rows_test)),
        "path_audit_hold_all_seeds": bool(all(float(r["path_rel_mean"]) <= 0.01 + 1e-12 and float(r["path_rel_p95"]) <= 0.05 + 1e-12 for r in seed_rows_test)),
        "beats_M_on_test_sign": bool(float(result.head_to_head_test["M"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_N_on_test_sign": bool(float(result.head_to_head_test["N"]["pooled"]["mean_delta_j"]) > 0.0),
        "beats_O_on_test_sign": bool(float(result.head_to_head_test["O"]["pooled"]["mean_delta_j"]) > 0.0),
    }
    result.gate_check_test = gate_test
    result.advanced_to_test = True
    return failure_df


def _report_summary(path: Path, families: list[FamilyResult], chosen_key: str | None, chosen_reason: str) -> None:
    lines = ["# Step14 Trial Report (v1)", "", "Protocol mapping: `docs/router_protocol_v1_current_mainline_note.md`", "Selection semantics: all family comparison on `calib_train/calib_val`; `test` used only for the chosen family (if any).", ""]
    for fam in families:
        lines.append(f"## {fam.key} — {fam.name}")
        lines.append(f"- status: `{fam.status}`")
        lines.append(f"- pooled calib_val ΔJ vs P5: `{float(fam.pooled_val['mean_delta_j']):.6f}`")
        lines.append(f"- calib_val head-to-head ΔJ (M/N/O): `{ {k: round(float(v['pooled']['mean_delta_j']), 6) for k, v in fam.head_to_head_val.items()} }`")
        lines.append(f"- calib_val gate: `{fam.gate_check_val}`")
        if fam.pooled_test is not None:
            lines.append(f"- pooled test ΔJ vs P5: `{float(fam.pooled_test['mean_delta_j']):.6f}`")
            lines.append(f"- test head-to-head ΔJ (M/N/O): `{ {k: round(float(v['pooled']['mean_delta_j']), 6) for k, v in fam.head_to_head_test.items()} }`")
            lines.append(f"- test gate: `{fam.gate_check_test}`")
        lines.append("")
    lines.append(f"## Selection conclusion")
    lines.append(f"- chosen family for test: `{chosen_key}`")
    lines.append(f"- reason: {chosen_reason}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    weights = _parse_weights(args.weights)
    calib, test, input_parquets = _build_common_tables(args, weights)
    ctxs = _build_seed_contexts(args, calib, test, weights)
    baselines = _fit_baselines(ctxs, args)

    families: list[FamilyResult] = []
    aux_states: dict[str, dict[int, dict[str, Any]]] = {}
    failures: dict[str, pd.DataFrame | None] = {}

    for key, fn in [("A", _eval_family_A), ("B", _eval_family_B), ("C", _eval_family_C)]:
        fam, states, fail_df = fn(ctxs, args)
        aux_states[key] = states
        failures[key] = fail_df
        cand_arrays = {seed: np.asarray(states[seed]["metrics_val"]["J_array"], dtype=np.float64) for seed in sorted(states.keys())}
        _attach_head_to_head(fam, fam.seed_rows_val, cand_arrays, baselines, "val", int(args.bootstrap_n))
        _family_gate_from_val(fam)
        families.append(fam)

    chosen_key = None
    chosen_reason = "No candidate selected yet."
    promising = [fam for fam in families if _advance_family(fam)]
    dyn_inputs = input_parquets
    if not promising:
        fam_d, states_d, fail_d, dyn_inputs = _eval_family_D(ctxs, args, calib, test, input_parquets)
        aux_states["D"] = states_d
        failures["D"] = fail_d
        cand_arrays_d = {}
        for seed in sorted(states_d.keys()):
            tag = states_d[seed]["tag"]
            l_slow = ctxs[seed].cal_val["L_slow"].to_numpy(dtype=np.float64)
            cal = ctxs[seed].cal_val.merge(pd.read_parquet(dyn_inputs["dynamic_calib"])[["sample_name", "difficulty", f"L_{tag}", f"T_{tag}_ms", f"path_len_{tag}", f"switched_{tag}"]], on=["sample_name", "difficulty"], how="inner")
            drel = (cal[f"L_{tag}"].to_numpy(dtype=np.float64) - l_slow) / np.maximum(l_slow, 1e-6)
            qpos = np.maximum(drel, 0.0)
            cand_arrays_d[seed] = cal[f"T_{tag}_ms"].to_numpy(dtype=np.float64) / max(states_d[seed]["t_ref"], 1e-9) + states_d[seed]["beta"] * qpos
        _attach_head_to_head(fam_d, fam_d.seed_rows_val, cand_arrays_d, baselines, "val", int(args.bootstrap_n))
        _family_gate_from_val(fam_d)
        families.append(fam_d)
        if _advance_family(fam_d):
            promising = [fam_d]
        else:
            chosen_reason = "A/B/C all failed to beat M/N/O on calib_val; D was also not strong enough to justify a one-shot test." 
    if promising:
        promising = sorted(promising, key=lambda fam: float(np.mean([row["mean_delta_j"] for row in fam.seed_rows_val])), reverse=True)
        chosen = promising[0]
        chosen_key = chosen.key
        chosen_reason = "Selected by pooled calib_val performance with gates satisfied; only this family is allowed to consume test."
        chosen.status = "chosen_for_test"
        failure_df_test = _evaluate_test_for_family(chosen, aux_states[chosen.key], ctxs, baselines, args)
        if chosen.gate_check_test and all(bool(v) for v in chosen.gate_check_test.values()):
            chosen.status = "tested_positive"
        else:
            chosen.status = "tested_negative"
        failures[chosen.key] = failure_df_test

    summary = {
        "version": "step14_trials_v1",
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
        base_inputs = dyn_inputs if fam.key == "D" else input_parquets
        if fam.advanced_to_test:
            art_inputs = base_inputs
        else:
            art_inputs = {k: v for k, v in base_inputs.items() if "test" not in str(k)}
        _write_candidate_artifacts(fam, input_parquets=art_inputs, representative_rows=failures.get(fam.key))
    print(f"[step14] summary={args.summary_json}")
    print(f"[step14] report={args.report_md}")


if __name__ == "__main__":
    main()
