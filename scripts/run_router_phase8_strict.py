from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reuse phase-6 probe feature extraction to keep the probe signal definition identical.
from scripts.run_router_probe_v1 import _build_probe_features
from utils.artifact_hash import sha256_file
from utils.parquet_guard import INPUTS_SHA256_FILENAME, write_record


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-8 strict branch fix (no backoff): stratified conformal + stratified probe.")
    p.add_argument("--seeds", type=str, default="7,11,19,23,31")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_mixed_v1"))
    p.add_argument("--calib-parquet", type=Path, default=Path("outputs/router_phase7_v1/common/router_counterfactual_calib.parquet"))
    p.add_argument("--test-parquet", type=Path, default=Path("outputs/router_phase7_v1/common/router_counterfactual_test.parquet"))
    p.add_argument(
        "--static-features-calib",
        type=Path,
        default=Path("outputs/router_phase7_v1/seeds/seed_7/mixed/risk/features_calib.parquet"),
    )
    p.add_argument(
        "--static-features-test",
        type=Path,
        default=Path("outputs/router_phase7_v1/seeds/seed_7/mixed/risk/features_test.parquet"),
    )
    p.add_argument(
        "--probe-features-calib",
        type=Path,
        default=Path("outputs/router_phase7_v1/seeds/seed_7/mixed/probe_strict/probe_features_calib.parquet"),
    )
    p.add_argument(
        "--probe-features-test",
        type=Path,
        default=Path("outputs/router_phase7_v1/seeds/seed_7/mixed/probe_strict/probe_features_test.parquet"),
    )
    p.add_argument("--epsilon-rel", type=float, default=0.015)

    # P8 strict targets.
    p.add_argument(
        "--strict-violation-target",
        type=float,
        default=0.05,
        help="Target upper bound on violation probability V = P(use_fast & q_rel > eps_rel). "
        "Must match the frozen protocol alpha (default: 0.05).",
    )
    p.add_argument(
        "--strict-ci-upper-target",
        type=float,
        default=0.05,
        help="Target upper bound on the 95% Wilson CI upper for the violation rate. "
        "Use the same value as --strict-violation-target for a paper-grade risk bound.",
    )
    p.add_argument(
        "--strict-tune-violation-margin",
        type=float,
        default=0.01,
        help="Safety margin subtracted from --strict-violation-target when tuning on the selection split.",
    )
    p.add_argument(
        "--strict-tune-ci-margin",
        type=float,
        default=0.01,
        help="Safety margin subtracted from --strict-ci-upper-target when tuning on the selection split.",
    )
    p.add_argument(
        "--strict-conformal-alpha-grid",
        type=str,
        default="0.10,0.15,0.20,0.25,0.30,0.35",
        help="Grid over one-sided split-conformal miscoverage alpha for p_upper(x) = clip(p_hat + q_d, 0, 1).",
    )
    p.add_argument("--strict-score-a-grid", type=str, default="0.75,1.0,1.25")
    p.add_argument("--strict-score-b-grid", type=str, default="0.0,0.5,1.0")
    p.add_argument("--strict-search-window", type=int, default=90)
    p.add_argument("--strict-search-step", type=int, default=3)

    # Probe targets use hard positive-risk improvement to avoid sign ambiguity on hard mean drel.
    p.add_argument("--probe-og-improve-target", type=float, default=0.05)
    p.add_argument("--probe-hard-pos-improve-target", type=float, default=0.10)
    p.add_argument("--probe-latency-extra-target-ms", type=float, default=5.0)
    p.add_argument("--probe-gain-power-grid", type=str, default="1.0,1.25,1.5")
    p.add_argument("--probe-w-hard-grid", type=str, default="0.5,1.0,1.5,2.0")
    p.add_argument("--probe-w-bottleneck-grid", type=str, default="0.0,0.5,1.0")
    p.add_argument("--probe-w-stall-grid", type=str, default="0.0,0.5")
    p.add_argument("--probe-grid-divisor", type=int, default=30)
    p.add_argument(
        "--probe-selection-mode",
        type=str,
        default="grid_search",
        choices=["grid_search", "conformal_lcb", "knapsack_lcb"],
        help="How to select the probe flip budget k_by_diff on the selection split. "
        "`grid_search` matches the historical Phase-8 behavior (score hyperparameter sweep + target gates). "
        "`conformal_lcb` uses a one-sided split-conformal lower confidence bound (LCB) on predicted J-gain to select flips "
        "without a hyperparameter sweep (more stable under strict audits). "
        "`knapsack_lcb` predicts *signed* J-gain, conformalizes a one-sided LCB by difficulty, then selects flips under "
        "a mean-latency budget via a greedy knapsack (maximize LCB gain per ms).",
    )
    p.add_argument(
        "--probe-lcb-alpha",
        type=float,
        default=0.10,
        help="Only used when --probe-selection-mode=conformal_lcb. Miscoverage level for one-sided split-conformal LCB on J-gain.",
    )
    p.add_argument(
        "--probe-include-cost-feature",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="If enabled, include a *predicted* cost proxy c_hat(x) (estimated from deployable static features) "
        "as a probe gain feature. Avoids any oracle per-sample cost leakage (do NOT use counterfactual c at routing time).",
    )
    p.add_argument(
        "--calib-split-mode",
        type=str,
        default="train_val",
        choices=["none", "train_val"],
        help="How to split the calibration split for selection. "
        "`train_val` fits predictors on calib_train and selects thresholds on calib_val; "
        "`none` uses the full calib split (legacy).",
    )
    p.add_argument(
        "--calib-train-frac",
        type=float,
        default=0.60,
        help="Fraction of calib used as calib_train when --calib-split-mode=train_val (stratified by difficulty).",
    )
    p.add_argument(
        "--calib-split-seed",
        type=int,
        default=20260302,
        help="Deterministic seed used for calib_train/calib_val split when --calib-split-mode=train_val.",
    )
    p.add_argument(
        "--conformal-select-on",
        type=str,
        default="calib",
        choices=["calib", "test"],
        help="Which split is used to select conformal hyperparameters (alpha/a/b + k_by_diff). "
        "Use 'calib' to avoid test-set tuning in audits; 'test' matches historical Phase-8 behavior.",
    )
    p.add_argument(
        "--probe-search-on",
        type=str,
        default="calib",
        choices=["calib", "test"],
        help="Which split is used to search probe flip counts (k_by_diff). "
        "Use 'calib' to avoid test-set tuning in audits; 'test' matches historical Phase-8 behavior.",
    )

    p.add_argument("--gbc-n-estimators", type=int, default=500)
    p.add_argument("--gbc-learning-rate", type=float, default=0.04)
    p.add_argument("--gbc-max-depth", type=int, default=3)
    p.add_argument("--gbc-subsample", type=float, default=0.9)
    p.add_argument("--gbr-n-estimators", type=int, default=700)
    p.add_argument("--gbr-learning-rate", type=float, default=0.04)
    p.add_argument("--gbr-max-depth", type=int, default=3)
    p.add_argument("--gbr-subsample", type=float, default=0.9)

    # Step12-R recovery variants (strict semantics).
    p.add_argument(
        "--emit-probe-voi-gate",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Emit a selective-probe policy (probe_selective_v1) that gates probe execution by a conformal value-of-information rule.",
    )
    p.add_argument(
        "--probe-voi-alpha",
        type=float,
        default=0.10,
        help="Miscoverage level for one-sided split-conformal bounds used in the VoI gate (LCB on gain, UCB on probe cost).",
    )
    p.add_argument(
        "--probe-voi-threshold-quantiles",
        type=int,
        default=81,
        help="Number of quantile thresholds evaluated on calib_val to pick the VoI gate threshold (calib-only selection).",
    )

    p.add_argument(
        "--emit-probe-boundary-gate",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Emit a boundary-probe policy (probe_boundary_v1) that runs probe only when the P5 score is near its threshold.",
    )
    p.add_argument(
        "--probe-boundary-quantiles",
        type=int,
        default=41,
        help="Number of distance-to-threshold quantiles evaluated on calib_val to pick the boundary gate width (calib-only selection).",
    )

    p.add_argument(
        "--emit-probe-risktrade",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Emit a risk-trading probe policy (probe_risktrade_v1) that allows both slow->fast and fast->slow changes under a conformal risk budget.",
    )
    p.add_argument(
        "--probe-risktrade-alpha",
        type=float,
        default=0.10,
        help="Miscoverage level for split-conformal bounds in risk-trading (LCB on benefit, UCB on violation probability).",
    )
    p.add_argument(
        "--probe-risktrade-threshold-quantiles",
        type=int,
        default=81,
        help="Number of score quantiles evaluated on calib_val to pick the risk-trade ratio threshold (calib-only selection).",
    )

    p.add_argument(
        "--emit-probe-prefixreuse",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Emit a prefix-reuse accounting variant (probe_prefixreuse_v1): probe cost is charged only when the final route is fast "
        "(the probe is discarded). When the final route is slow, probe compute is assumed reused as a slow-prefix and not added on top.",
    )

    # Step12-R2 recovery variants (strict semantics; no test tuning).
    p.add_argument(
        "--emit-trace-switch",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Emit a trace-switch policy (trace_switch_v1): use fast-prefix trace features (the existing probe_* A* prefix stats) "
        "to decide switching from the P5-fast branch to slow. Strict accounting: the trace cost is charged only when the final route "
        "is slow (sequential switch); when the final route is fast, the trace is treated as a fast-prefix and not added on top.",
    )
    p.add_argument(
        "--trace-switch-alpha",
        type=float,
        default=0.10,
        help="Miscoverage level for one-sided split-conformal LCB on predicted net J-improvement (calib_val calibration only).",
    )
    p.add_argument(
        "--trace-switch-threshold-quantiles",
        type=int,
        default=81,
        help="Number of quantile thresholds evaluated on calib_val to pick the trace-switch threshold (calib-only selection).",
    )
    p.add_argument(
        "--trace-switch-overhead-mode",
        type=str,
        default="trace_slow_only",
        choices=["trace_slow_only", "trace_slow_overlap_infer"],
        help="Strict accounting mode for trace-switch overhead. "
        "`trace_slow_only`: charge full probe/trace runtime when switching to slow. "
        "`trace_slow_overlap_infer`: assume probe/trace (CPU) overlaps with slow inference (GPU) and charge only max(0, probe_ms-infer_slow_ms) when switching to slow.",
    )

    p.add_argument(
        "--emit-partition-crc",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Emit a learned partitioned CRC policy (partition_crc_v1): learn a deployable partitioner on calib_train, "
        "compute split-conformal upper offsets within partitions on calib_val, then run the same strict tau-by-difficulty "
        "search as conformal_strict_v2. No probe is used (probe_used=false).",
    )
    p.add_argument("--partition-crc-max-leaves", type=int, default=8, help="Max leaf nodes for the partitioner tree.")
    p.add_argument("--partition-crc-min-leaf", type=int, default=80, help="Min samples per partition leaf (stability).")

    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase8_strict_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase8_strict_v1.md"))
    p.add_argument("--enforce-gate", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def _parse_seeds(raw: str) -> list[int]:
    out: list[int] = []
    for tok in str(raw).split(","):
        tok = tok.strip()
        if tok:
            out.append(int(tok))
    if not out:
        raise ValueError("Empty seed list.")
    return out


def _parse_grid(raw: str) -> list[float]:
    vals: list[float] = []
    for tok in str(raw).split(","):
        tok = tok.strip()
        if tok:
            vals.append(float(tok))
    if not vals:
        raise ValueError(f"Empty grid: {raw}")
    return vals


def _one_sided_residual_quantile_overestimate(res: np.ndarray, alpha: float) -> float:
    res = np.asarray(res, dtype=np.float64)
    n = int(res.size)
    if n <= 0:
        return 0.0
    level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / n)
    level = float(np.clip(level, 0.0, 1.0))
    try:
        q = float(np.quantile(res, level, method="higher"))
    except TypeError:  # pragma: no cover
        q = float(np.quantile(res, level, interpolation="higher"))
    return q


def _static_gate_design_matrix(df: pd.DataFrame, *, ref_cols: pd.Index | None = None) -> pd.DataFrame:
    feat_num = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
    ]
    feat_cat = ["difficulty"]
    missing = [c for c in (feat_num + feat_cat) if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing gate features: {missing}")
    x = pd.get_dummies(df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    if ref_cols is not None:
        x = x.reindex(columns=ref_cols, fill_value=0)
    return x


def _route_only_J(
    df: pd.DataFrame,
    use_fast: np.ndarray,
    *,
    t_ref: float,
    beta: float,
) -> np.ndarray:
    uf = np.asarray(use_fast, dtype=bool)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
    q_pos = np.maximum(df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    j_fast = t_fast / max(float(t_ref), 1e-9) + float(beta) * q_pos
    j_slow = t_slow / max(float(t_ref), 1e-9)
    return np.where(uf, j_fast, j_slow).astype(np.float64)


def _probe_cost_norm(df: pd.DataFrame, *, t_ref: float) -> np.ndarray:
    if "probe_runtime_ms" not in df.columns:
        raise RuntimeError("Missing probe_runtime_ms for probe cost accounting.")
    return (np.clip(df["probe_runtime_ms"].to_numpy(dtype=np.float64), 0.0, None) / max(float(t_ref), 1e-9)).astype(np.float64)


def _write_policy_meta(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _save_policy_decisions(
    out_dir: Path,
    *,
    split_name: str,
    df: pd.DataFrame,
    use_fast: np.ndarray,
    probe_used: np.ndarray,
    extra_cols: dict[str, np.ndarray] | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(
        {
            "sample_name": df["sample_name"].astype(str),
            "difficulty": df["difficulty"].astype(str),
            "use_fast": np.asarray(use_fast, dtype=bool),
            "probe_used": np.asarray(probe_used, dtype=bool),
        }
    )
    out["route"] = np.where(out["use_fast"].to_numpy(dtype=bool), "fast", "slow")
    if extra_cols:
        for k, v in extra_cols.items():
            out[str(k)] = np.asarray(v)
    path = out_dir / f"{split_name}_decisions.parquet"
    out.to_parquet(path, index=False)
    return path


def _run_probe_voi_gate_seed(
    *,
    seed: int,
    calib_train_df: pd.DataFrame,
    calib_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    use_fast_p5_train: np.ndarray,
    use_fast_p5_val: np.ndarray,
    use_fast_p5_test: np.ndarray,
    use_fast_probe_train: np.ndarray,
    use_fast_probe_val: np.ndarray,
    use_fast_probe_test: np.ndarray,
    t_ref: float,
    beta: float,
    alpha: float,
    threshold_quantiles: int,
    out_dir: Path,
    input_hashes: dict[str, str],
    calib_split_cfg: dict[str, object],
) -> dict:
    # Targets: route-only gain and probe overhead cost in normalized units.
    j_p5_train = _route_only_J(calib_train_df, use_fast_p5_train, t_ref=t_ref, beta=beta)
    j_probe_train = _route_only_J(calib_train_df, use_fast_probe_train, t_ref=t_ref, beta=beta)
    y_gain_train = (j_p5_train - j_probe_train).astype(np.float64)
    y_cost_train = _probe_cost_norm(calib_train_df, t_ref=t_ref)

    x_train = _static_gate_design_matrix(calib_train_df)
    reg_gain = GradientBoostingRegressor(
        random_state=int(seed),
        n_estimators=300,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.9,
    )
    reg_cost = GradientBoostingRegressor(
        random_state=int(seed) + 1000,
        n_estimators=250,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.9,
    )
    reg_gain.fit(x_train, y_gain_train)
    reg_cost.fit(x_train, y_cost_train)

    def _predict(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        x = _static_gate_design_matrix(df, ref_cols=x_train.columns)
        pred_gain = reg_gain.predict(x).astype(np.float64)
        pred_cost = np.clip(reg_cost.predict(x).astype(np.float64), 0.0, None)
        return pred_gain.astype(np.float64), pred_cost.astype(np.float64)

    # Calib-val: compute true quantities for threshold selection.
    j_p5_val = _route_only_J(calib_val_df, use_fast_p5_val, t_ref=t_ref, beta=beta)
    j_probe_val = _route_only_J(calib_val_df, use_fast_probe_val, t_ref=t_ref, beta=beta)
    gain_val = (j_p5_val - j_probe_val).astype(np.float64)
    cost_val = _probe_cost_norm(calib_val_df, t_ref=t_ref)
    pred_gain_val, pred_cost_val = _predict(calib_val_df)
    q_gain = _one_sided_residual_quantile_overestimate(np.maximum(pred_gain_val - gain_val, 0.0), alpha=float(alpha))
    q_cost = _one_sided_residual_quantile_overestimate(np.maximum(cost_val - pred_cost_val, 0.0), alpha=float(alpha))
    lcb_gain_val = (pred_gain_val - float(q_gain)).astype(np.float64)
    ucb_cost_val = (pred_cost_val + float(q_cost)).astype(np.float64)
    net_lcb_val = (lcb_gain_val - ucb_cost_val).astype(np.float64)

    # Pick a threshold on calib_val only (strict). Objective: maximize mean net gain vs P5.
    eligible_val = np.asarray(use_fast_p5_val, dtype=bool)
    cand = np.unique(
        np.quantile(
            net_lcb_val[eligible_val] if np.any(eligible_val) else net_lcb_val,
            np.linspace(0.0, 1.0, int(max(threshold_quantiles, 3))),
            method="higher",
        )
    )
    best = None
    for thr in cand.tolist() + [float("inf")]:
        mask = eligible_val & (net_lcb_val > float(thr))
        net_gain = float(np.mean((gain_val - cost_val) * mask.astype(np.float64)))
        probe_rate = float(np.mean(mask.astype(np.float64)))
        # Tie-break: prefer less probing.
        key = (net_gain, -probe_rate, -float(thr))
        if best is None or key > best["key"]:
            best = {"key": key, "thr": float(thr), "net_gain": net_gain, "probe_rate": probe_rate}
    assert best is not None
    thr = float(best["thr"])

    def _apply(df: pd.DataFrame, use_fast_p5: np.ndarray, use_fast_probe: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        j_p5 = _route_only_J(df, use_fast_p5, t_ref=t_ref, beta=beta)
        j_probe = _route_only_J(df, use_fast_probe, t_ref=t_ref, beta=beta)
        gain = (j_p5 - j_probe).astype(np.float64)
        cost = _probe_cost_norm(df, t_ref=t_ref)
        pred_gain, pred_cost = _predict(df)
        net_lcb = ((pred_gain - float(q_gain)) - (pred_cost + float(q_cost))).astype(np.float64)
        eligible = np.asarray(use_fast_p5, dtype=bool)
        probe_used = (eligible & (net_lcb > thr)).astype(bool)
        use_fast = np.where(probe_used, np.asarray(use_fast_probe, dtype=bool), np.asarray(use_fast_p5, dtype=bool))
        return use_fast.astype(bool), probe_used.astype(bool), gain, cost, net_lcb

    use_cal, probe_used_cal, gain_cal, cost_cal, _net_lcb_cal = _apply(calib_train_df, use_fast_p5_train, use_fast_probe_train)
    use_val, probe_used_val, _gain_val, _cost_val, _net_lcb_val2 = _apply(calib_val_df, use_fast_p5_val, use_fast_probe_val)
    use_test, probe_used_test, gain_test, cost_test, net_lcb_test = _apply(test_df, use_fast_p5_test, use_fast_probe_test)

    j_test = _route_only_J(test_df, use_test, t_ref=t_ref, beta=beta) + cost_test * probe_used_test.astype(np.float64)
    j_p5_test = _route_only_J(test_df, use_fast_p5_test, t_ref=t_ref, beta=beta)
    delta_j = (j_p5_test - j_test).astype(np.float64)

    out = out_dir
    cal_dec = _save_policy_decisions(
        out,
        split_name="calib",
        df=pd.concat([calib_train_df, calib_val_df], ignore_index=True),
        use_fast=np.concatenate([use_cal, use_val]),
        probe_used=np.concatenate([probe_used_cal, probe_used_val]),
    )
    test_dec = _save_policy_decisions(
        out,
        split_name="test",
        df=test_df,
        use_fast=use_test,
        probe_used=probe_used_test,
        extra_cols={
            "net_lcb": net_lcb_test.astype(np.float64),
            "net_gain": (gain_test - cost_test).astype(np.float64),
            "gain_route_only": gain_test,
            "probe_cost_norm": cost_test,
        },
    )

    meta = {
        "version": "probe_selective_v1",
        "seed": int(seed),
        "inputs": dict(input_hashes),
        "calib_split": dict(calib_split_cfg),
        "objective": {"T_ref": float(t_ref), "beta": float(beta)},
        "voi_gate": {
            "alpha": float(alpha),
            "q_gain": float(q_gain),
            "q_cost": float(q_cost),
            "threshold": float(thr),
            "val_net_gain_mean": float(best["net_gain"]),
            "val_probe_rate": float(best["probe_rate"]),
        },
        "test_metrics": {
            "probe_trigger_rate": float(np.mean(probe_used_test.astype(np.float64))),
            "delta_j_mean_vs_p5": float(np.mean(delta_j)),
            "delta_j_median_vs_p5": float(np.median(delta_j)),
            "probe_cost_norm_mean": float(np.mean(cost_test * probe_used_test.astype(np.float64))),
            "route_only_gain_mean": float(np.mean(gain_test * probe_used_test.astype(np.float64))),
        },
        "artifacts": {
            "calib_decisions_parquet": str(cal_dec),
            "test_decisions_parquet": str(test_dec),
        },
    }
    metrics_path = out / "policy_metrics.json"
    metrics_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"policy_dir": out, "metrics": meta, "metrics_path": metrics_path}


def _run_probe_boundary_gate_seed(
    *,
    seed: int,
    calib_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    use_fast_p5_val: np.ndarray,
    use_fast_p5_test: np.ndarray,
    use_fast_probe_val: np.ndarray,
    use_fast_probe_test: np.ndarray,
    tau_by_diff: dict[str, float],
    t_ref: float,
    beta: float,
    delta_quantiles: int,
    out_dir: Path,
    input_hashes: dict[str, str],
    calib_split_cfg: dict[str, object],
) -> dict:
    if "risk_score_p5" not in calib_val_df.columns or "risk_score_p5" not in test_df.columns:
        raise RuntimeError("Boundary gate requires risk_score_p5 in merged probe dataframe.")

    def _dist(df: pd.DataFrame) -> np.ndarray:
        diff = df["difficulty"].astype(str).to_numpy()
        tau = np.array([float(tau_by_diff.get(str(d), float("inf"))) for d in diff], dtype=np.float64)
        s = df["risk_score_p5"].to_numpy(dtype=np.float64)
        return np.abs(s - tau).astype(np.float64)

    dist_val = _dist(calib_val_df)
    dist_test = _dist(test_df)

    j_p5_val = _route_only_J(calib_val_df, use_fast_p5_val, t_ref=t_ref, beta=beta)
    j_probe_val = _route_only_J(calib_val_df, use_fast_probe_val, t_ref=t_ref, beta=beta)
    gain_val = (j_p5_val - j_probe_val).astype(np.float64)
    cost_val = _probe_cost_norm(calib_val_df, t_ref=t_ref)

    # Only P5-fast cases are eligible for the monotone probe upgrade.
    eligible_val = np.asarray(use_fast_p5_val, dtype=bool)
    cand = np.unique(
        np.quantile(
            dist_val[eligible_val] if np.any(eligible_val) else dist_val,
            np.linspace(0.0, 1.0, int(max(delta_quantiles, 3))),
            method="higher",
        )
    )
    best = None
    for delta in cand.tolist() + [float("inf")]:
        probe_used = eligible_val & (dist_val <= float(delta))
        net_gain = float(np.mean((gain_val - cost_val) * probe_used.astype(np.float64)))
        probe_rate = float(np.mean(probe_used.astype(np.float64)))
        key = (net_gain, -probe_rate, -float(delta))
        if best is None or key > best["key"]:
            best = {"key": key, "delta": float(delta), "net_gain": net_gain, "probe_rate": probe_rate}
    assert best is not None
    delta_sel = float(best["delta"])

    def _apply(df: pd.DataFrame, use_fast_p5: np.ndarray, use_fast_probe: np.ndarray, dist: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        eligible = np.asarray(use_fast_p5, dtype=bool)
        probe_used = eligible & (dist <= delta_sel)
        use_fast = np.where(probe_used, np.asarray(use_fast_probe, dtype=bool), np.asarray(use_fast_p5, dtype=bool))
        j_p5 = _route_only_J(df, use_fast_p5, t_ref=t_ref, beta=beta)
        j_route = _route_only_J(df, use_fast, t_ref=t_ref, beta=beta)
        cost = _probe_cost_norm(df, t_ref=t_ref) * probe_used.astype(np.float64)
        delta = (j_p5 - (j_route + cost)).astype(np.float64)
        return use_fast.astype(bool), probe_used.astype(bool), cost, delta

    use_test, probe_used_test, cost_test, delta_test = _apply(test_df, use_fast_p5_test, use_fast_probe_test, dist_test)

    out = out_dir
    test_dec = _save_policy_decisions(
        out,
        split_name="test",
        df=test_df,
        use_fast=use_test,
        probe_used=probe_used_test,
        extra_cols={
            "boundary_dist": dist_test,
            "probe_cost_norm": cost_test,
        },
    )
    meta = {
        "version": "probe_boundary_v1",
        "seed": int(seed),
        "inputs": dict(input_hashes),
        "calib_split": dict(calib_split_cfg),
        "objective": {"T_ref": float(t_ref), "beta": float(beta)},
        "boundary_gate": {
            "delta": float(delta_sel),
            "val_net_gain_mean": float(best["net_gain"]),
            "val_probe_rate": float(best["probe_rate"]),
        },
        "test_metrics": {
            "probe_trigger_rate": float(np.mean(probe_used_test.astype(np.float64))),
            "delta_j_mean_vs_p5": float(np.mean(delta_test)),
            "delta_j_median_vs_p5": float(np.median(delta_test)),
        },
        "artifacts": {"test_decisions_parquet": str(test_dec)},
    }
    metrics_path = out / "policy_metrics.json"
    metrics_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"policy_dir": out, "metrics": meta, "metrics_path": metrics_path}


def _risktrade_design_matrix(df: pd.DataFrame, *, ref_cols: pd.Index | None = None, include_cost_feature: bool = False) -> pd.DataFrame:
    feat_cols = [
        "probe_success",
        "probe_expansions",
        "probe_runtime_ms",
        "probe_expansion_ratio",
        "probe_h_drop_ratio",
        "probe_progress_per_exp",
        "probe_open_growth",
        "probe_branching",
        "probe_improve_rate",
        "probe_bottleneck_rate",
        "probe_deadend_rate",
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
        "difficulty",
    ]
    if bool(include_cost_feature):
        if "c_hat" not in df.columns:
            raise RuntimeError("Missing c_hat for risktrade include_cost_feature.")
        feat_cols.insert(feat_cols.index("difficulty"), "c_hat")
    missing = [c for c in feat_cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing risktrade features: {missing}")
    x = pd.get_dummies(df[feat_cols], columns=["difficulty"], drop_first=False)
    if ref_cols is not None:
        x = x.reindex(columns=ref_cols, fill_value=0)
    return x


def _run_probe_risktrade_seed(
    *,
    seed: int,
    calib_train_df: pd.DataFrame,
    calib_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    use_fast_p5_val: np.ndarray,
    use_fast_p5_test: np.ndarray,
    t_ref: float,
    beta: float,
    eps_rel: float,
    risk_alpha: float,
    threshold_quantiles: int,
    include_cost_feature: bool,
    out_dir: Path,
    input_hashes: dict[str, str],
    calib_split_cfg: dict[str, object],
) -> dict:
    # Targets on calib_train: benefit of choosing fast vs slow, and violation indicator under fast.
    q_rel_train = calib_train_df["q_rel"].to_numpy(dtype=np.float64)
    q_pos_train = np.maximum(q_rel_train, 0.0)
    j_fast_train = calib_train_df["T_fast_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9) + float(beta) * q_pos_train
    j_slow_train = calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9)
    y_benefit_train = (j_slow_train - j_fast_train).astype(np.float64)
    y_vio_train = (q_rel_train > float(eps_rel)).astype(np.float64)

    x_train = _risktrade_design_matrix(calib_train_df, include_cost_feature=bool(include_cost_feature))
    reg_benefit = GradientBoostingRegressor(
        random_state=int(seed),
        n_estimators=700,
        learning_rate=0.04,
        max_depth=3,
        subsample=0.9,
    )
    clf_vio = GradientBoostingClassifier(
        random_state=int(seed) + 10,
        n_estimators=500,
        learning_rate=0.04,
        max_depth=3,
        subsample=0.9,
    )
    reg_benefit.fit(x_train, y_benefit_train)
    clf_vio.fit(x_train, y_vio_train)

    def _predict_bounds(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, dict[str, float]]:
        x = _risktrade_design_matrix(df, ref_cols=x_train.columns, include_cost_feature=bool(include_cost_feature))
        pred_b = reg_benefit.predict(x).astype(np.float64)
        p_hat = clf_vio.predict_proba(x)[:, 1].astype(np.float64)
        # True labels for calibration of bounds (only used on calib_val).
        q_rel = df["q_rel"].to_numpy(dtype=np.float64)
        q_pos = np.maximum(q_rel, 0.0)
        j_fast = df["T_fast_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9) + float(beta) * q_pos
        j_slow = df["T_slow_ms"].to_numpy(dtype=np.float64) / max(float(t_ref), 1e-9)
        b_true = (j_slow - j_fast).astype(np.float64)
        y = (q_rel > float(eps_rel)).astype(np.float64)
        q_b = _one_sided_residual_quantile_overestimate(np.maximum(pred_b - b_true, 0.0), alpha=float(risk_alpha))
        b_lcb = (pred_b - float(q_b)).astype(np.float64)
        q_by_diff = _split_conformal_offsets(df, y_cal=y, p_cal=p_hat, alpha=float(risk_alpha))
        diff = df["difficulty"].to_numpy(dtype=str)
        p_ucb = np.clip(p_hat + np.array([q_by_diff[str(d)] for d in diff], dtype=np.float64), 0.0, 1.0).astype(np.float64)
        return b_lcb, p_ucb, b_true, float(q_b), {str(k): float(v) for k, v in q_by_diff.items()}

    b_lcb_val, p_ucb_val, _b_true_val, q_benefit, q_diff = _predict_bounds(calib_val_df)
    # Score: benefit per unit risk upper bound (larger => more attractive to run fast).
    score_val = b_lcb_val / np.maximum(p_ucb_val, 1e-9)
    cand = np.unique(
        np.quantile(
            score_val[np.isfinite(score_val)],
            np.linspace(0.0, 1.0, int(max(threshold_quantiles, 3))),
            method="higher",
        )
    )

    # Select tau on calib_val only: maximize J improvement vs P5 while keeping mean(p_ucb * use_fast) <= alpha.
    j_p5_val = _route_only_J(calib_val_df, use_fast_p5_val, t_ref=t_ref, beta=beta)
    cost_val = _probe_cost_norm(calib_val_df, t_ref=t_ref)  # always-probe cost model
    best = None
    for tau in cand.tolist() + [float("inf")]:
        use_fast = (b_lcb_val > 0.0) & (score_val >= float(tau))
        risk_bound = float(np.mean(p_ucb_val * use_fast.astype(np.float64)))
        if risk_bound > float(eps_rel) + 1.0:  # unreachable; keep simple guard
            pass
        if risk_bound > float(getattr(calib_split_cfg, "strict_violation_target", 0.05)) + 1e-12:
            # Use protocol alpha as target (strict_violation_target).
            pass
        # Use strict_violation_target from args (stored in calib_split_cfg via caller) when available.
        alpha_budget = float(calib_split_cfg.get("strict_violation_target", 0.05))
        if risk_bound > alpha_budget + 1e-12:
            continue
        j_rt = _route_only_J(calib_val_df, use_fast, t_ref=t_ref, beta=beta) + cost_val
        delta = float(np.mean((j_p5_val - j_rt).astype(np.float64)))
        probe_rate = 1.0  # always-probe in v1
        key = (delta, -risk_bound, -probe_rate, -float(tau))
        if best is None or key > best["key"]:
            best = {"key": key, "tau": float(tau), "delta": delta, "risk_bound": risk_bound, "alpha_budget": alpha_budget}
    if best is None:
        best = {"tau": float("inf"), "delta": float("nan"), "risk_bound": float("nan"), "alpha_budget": float(calib_split_cfg.get("strict_violation_target", 0.05))}
    tau_sel = float(best["tau"])

    # Apply to test.
    x_test = _risktrade_design_matrix(test_df, ref_cols=x_train.columns, include_cost_feature=bool(include_cost_feature))
    pred_b_test = reg_benefit.predict(x_test).astype(np.float64)
    p_hat_test = clf_vio.predict_proba(x_test)[:, 1].astype(np.float64)
    # Use calib_val bounds (q_benefit/q_diff) frozen.
    b_lcb_test = (pred_b_test - float(q_benefit)).astype(np.float64)
    diff_test = test_df["difficulty"].to_numpy(dtype=str)
    p_ucb_test = np.clip(p_hat_test + np.array([q_diff.get(str(d), 0.0) for d in diff_test], dtype=np.float64), 0.0, 1.0).astype(np.float64)
    score_test = b_lcb_test / np.maximum(p_ucb_test, 1e-9)
    use_fast_test = (b_lcb_test > 0.0) & (score_test >= tau_sel)
    probe_used_test = np.ones(len(test_df), dtype=bool)  # v1: always run probe to obtain psi(x)

    cost_test = _probe_cost_norm(test_df, t_ref=t_ref)
    j_test = _route_only_J(test_df, use_fast_test, t_ref=t_ref, beta=beta) + cost_test
    j_p5_test = _route_only_J(test_df, use_fast_p5_test, t_ref=t_ref, beta=beta)
    delta_test = (j_p5_test - j_test).astype(np.float64)

    out = out_dir
    test_dec = _save_policy_decisions(
        out,
        split_name="test",
        df=test_df,
        use_fast=use_fast_test,
        probe_used=probe_used_test,
        extra_cols={
            "benefit_lcb": b_lcb_test,
            "risk_ucb": p_ucb_test,
            "score": score_test,
            "probe_cost_norm": cost_test,
        },
    )
    meta = {
        "version": "probe_risktrade_v1",
        "seed": int(seed),
        "inputs": dict(input_hashes),
        "calib_split": dict(calib_split_cfg),
        "objective": {"T_ref": float(t_ref), "beta": float(beta), "eps_rel": float(eps_rel), "alpha": float(calib_split_cfg.get("strict_violation_target", 0.05))},
        "bounds": {"alpha_miscoverage": float(risk_alpha), "q_benefit": float(q_benefit), "q_risk_by_diff": dict(q_diff)},
        "selection": {"tau_score": float(tau_sel), "val_delta_j_mean_vs_p5": float(best.get("delta", float("nan"))), "val_risk_bound": float(best.get("risk_bound", float("nan")))},
        "test_metrics": {
            "probe_trigger_rate": float(np.mean(probe_used_test.astype(np.float64))),
            "delta_j_mean_vs_p5": float(np.mean(delta_test)),
            "delta_j_median_vs_p5": float(np.median(delta_test)),
            "risk_ucb_mean_fast": float(np.mean(p_ucb_test[use_fast_test])) if bool(np.any(use_fast_test)) else 0.0,
        },
        "artifacts": {"test_decisions_parquet": str(test_dec)},
    }
    metrics_path = out / "policy_metrics.json"
    metrics_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"policy_dir": out, "metrics": meta, "metrics_path": metrics_path}


def _run_probe_prefixreuse_seed(
    *,
    seed: int,
    calib_df: pd.DataFrame,
    calib_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    use_fast_p5_calib: np.ndarray,
    use_fast_p5_val: np.ndarray,
    use_fast_p5_test: np.ndarray,
    use_fast_probe_calib: np.ndarray,
    use_fast_probe_val: np.ndarray,
    use_fast_probe_test: np.ndarray,
    t_ref: float,
    beta: float,
    out_dir: Path,
    input_hashes: dict[str, str],
    calib_split_cfg: dict[str, object],
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    def _summarize(split_df: pd.DataFrame, use_fast_p5: np.ndarray, use_fast: np.ndarray) -> dict:
        uf = np.asarray(use_fast, dtype=bool)
        up5 = np.asarray(use_fast_p5, dtype=bool)
        cost_norm = _probe_cost_norm(split_df, t_ref=t_ref)
        j_p5 = _route_only_J(split_df, up5, t_ref=t_ref, beta=beta)
        j_route = _route_only_J(split_df, uf, t_ref=t_ref, beta=beta)
        overhead = cost_norm * uf.astype(np.float64)
        j = j_route + overhead
        delta = (j_p5 - j).astype(np.float64)

        t_fast = split_df["T_fast_ms"].to_numpy(dtype=np.float64)
        t_slow = split_df["T_slow_ms"].to_numpy(dtype=np.float64)
        route_lat = np.where(uf, t_fast, t_slow).astype(np.float64)
        probe_lat = split_df["probe_runtime_ms"].to_numpy(dtype=np.float64) * uf.astype(np.float64)
        total_lat = route_lat + probe_lat

        return {
            "num_cases": int(len(split_df)),
            "fast_ratio": float(np.mean(uf.astype(np.float64))),
            "probe_trigger_rate": 1.0,
            "probe_overhead_mode": "prefix_reuse",
            "mean_delta_j_vs_p5": float(np.mean(delta)),
            "median_delta_j_vs_p5": float(np.median(delta)),
            "mean_J_route": float(np.mean(j_route)),
            "mean_J": float(np.mean(j)),
            "mean_probe_overhead_norm": float(np.mean(overhead)),
            "route_latency_ms": float(np.mean(route_lat)),
            "probe_latency_ms": float(np.mean(probe_lat)),
            "total_latency_ms": float(np.mean(total_lat)),
        }

    probe_used_calib = np.ones(len(calib_df), dtype=bool)
    probe_used_test = np.ones(len(test_df), dtype=bool)
    cost_calib = _probe_cost_norm(calib_df, t_ref=t_ref)
    cost_test = _probe_cost_norm(test_df, t_ref=t_ref)
    overhead_calib = cost_calib * np.asarray(use_fast_probe_calib, dtype=np.float64)
    overhead_test = cost_test * np.asarray(use_fast_probe_test, dtype=np.float64)

    calib_dec = _save_policy_decisions(
        out_dir,
        split_name="calib",
        df=calib_df,
        use_fast=use_fast_probe_calib,
        probe_used=probe_used_calib,
        extra_cols={"probe_cost_norm": cost_calib, "probe_overhead_norm": overhead_calib},
    )
    test_dec = _save_policy_decisions(
        out_dir,
        split_name="test",
        df=test_df,
        use_fast=use_fast_probe_test,
        probe_used=probe_used_test,
        extra_cols={"probe_cost_norm": cost_test, "probe_overhead_norm": overhead_test},
    )

    meta = {
        "version": "probe_prefixreuse_v1",
        "seed": int(seed),
        "inputs": dict(input_hashes),
        "calib_split": dict(calib_split_cfg),
        "probe_overhead_mode": "prefix_reuse",
        "parent_policy": "probe_strict_v2",
        "objective": {
            "J_formula": "J = T/T_ref + beta*max(delta_l_rel,0)",
            "T_ref": float(t_ref),
            "beta": float(beta),
        },
        "delta_j_mean_vs_p5": {
            "calib": float(_summarize(calib_df, use_fast_p5_calib, use_fast_probe_calib)["mean_delta_j_vs_p5"]),
            "val": float(_summarize(calib_val_df, use_fast_p5_val, use_fast_probe_val)["mean_delta_j_vs_p5"]),
            "test": float(_summarize(test_df, use_fast_p5_test, use_fast_probe_test)["mean_delta_j_vs_p5"]),
            "selection": float(_summarize(calib_val_df, use_fast_p5_val, use_fast_probe_val)["mean_delta_j_vs_p5"]),
        },
        "calib_metrics": _summarize(calib_df, use_fast_p5_calib, use_fast_probe_calib),
        "val_metrics": _summarize(calib_val_df, use_fast_p5_val, use_fast_probe_val),
        "test_metrics": _summarize(test_df, use_fast_p5_test, use_fast_probe_test),
        "artifacts": {
            "calib_decisions_parquet": str(calib_dec),
            "test_decisions_parquet": str(test_dec),
        },
    }
    metrics_path = out_dir / "policy_metrics.json"
    metrics_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"policy_dir": out_dir, "metrics": meta, "metrics_path": metrics_path}


def _trace_switch_design_matrix(df: pd.DataFrame, *, ref_cols: pd.Index | None = None) -> pd.DataFrame:
    feat_num = [
        "probe_success",
        "probe_expansions",
        "probe_runtime_ms",
        "probe_expansion_ratio",
        "probe_h_drop_ratio",
        "probe_progress_per_exp",
        "probe_open_growth",
        "probe_branching",
        "probe_improve_rate",
        "probe_bottleneck_rate",
        "probe_deadend_rate",
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
    ]
    if "c_hat" in df.columns:
        feat_num.append("c_hat")
    feat_cat = ["difficulty"]
    missing = [c for c in (feat_num + feat_cat) if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing trace-switch features: {missing}")
    x = pd.get_dummies(df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    if ref_cols is not None:
        x = x.reindex(columns=ref_cols, fill_value=0)
    return x


def _run_trace_switch_seed(
    *,
    seed: int,
    calib_train_df: pd.DataFrame,
    calib_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    t_ref: float,
    beta: float,
    alpha: float,
    threshold_quantiles: int,
    overhead_mode: str,
    out_dir: Path,
    input_hashes: dict[str, str],
    calib_split_cfg: dict[str, object],
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    alpha = float(np.clip(float(alpha), 1e-6, 0.999999))

    def _net_improve(df: pd.DataFrame) -> np.ndarray:
        t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
        t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
        q_pos = np.maximum(df["q_rel"].to_numpy(dtype=np.float64), 0.0)
        j_fast = (t_fast / max(float(t_ref), 1e-9)) + float(beta) * q_pos
        j_slow = t_slow / max(float(t_ref), 1e-9)
        trace_cost = _probe_cost_norm(df, t_ref=float(t_ref))
        return (j_fast - (j_slow + trace_cost)).astype(np.float64)

    # Eligible = cases where P5 runs fast (we can only switch fast->slow; never slow->fast).
    elig_train = calib_train_df["use_fast_p5"].to_numpy(dtype=bool)
    elig_val = calib_val_df["use_fast_p5"].to_numpy(dtype=bool)
    elig_test = test_df["use_fast_p5"].to_numpy(dtype=bool)
    if not bool(np.any(elig_train)):
        raise RuntimeError("trace_switch_v1: no eligible (P5-fast) samples in calib_train.")

    y_train = _net_improve(calib_train_df)[elig_train]
    y_val = _net_improve(calib_val_df)[elig_val]
    y_test = _net_improve(test_df)[elig_test]

    x_train = _trace_switch_design_matrix(calib_train_df.loc[elig_train].reset_index(drop=True))
    x_val = _trace_switch_design_matrix(calib_val_df.loc[elig_val].reset_index(drop=True), ref_cols=x_train.columns)
    x_test = _trace_switch_design_matrix(test_df.loc[elig_test].reset_index(drop=True), ref_cols=x_train.columns)

    reg = GradientBoostingRegressor(
        random_state=int(seed),
        n_estimators=400,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.9,
    )
    reg.fit(x_train, y_train)

    pred_val = reg.predict(x_val).astype(np.float64)
    pred_test = reg.predict(x_test).astype(np.float64)
    resid_val = (pred_val - y_val).astype(np.float64)
    diff_val = calib_val_df.loc[elig_val, "difficulty"].to_numpy(dtype=str)
    diff_test = test_df.loc[elig_test, "difficulty"].to_numpy(dtype=str)

    q_by_diff: dict[str, float] = {}
    for d in ("easy", "medium", "hard"):
        vals = resid_val[diff_val == d]
        if vals.size <= 0:
            q_by_diff[d] = 0.0
            continue
        q_by_diff[d] = _one_sided_residual_quantile_overestimate(np.maximum(vals, 0.0), alpha=float(alpha))

    q_val_vec = np.array([q_by_diff.get(str(d), 0.0) for d in diff_val], dtype=np.float64)
    lcb_val = (pred_val - q_val_vec).astype(np.float64)

    # Calib-only threshold selection: maximize *overall* mean net improvement vs P5 (tie-break: fewer switches).
    cand = np.unique(
        np.quantile(
            lcb_val,
            np.linspace(0.0, 1.0, int(max(int(threshold_quantiles), 3))),
            method="higher",
        )
    ).tolist()
    cand.append(0.0)
    cand = sorted(set(float(x) for x in cand if np.isfinite(float(x))))
    best = None
    for thr in cand + [float("inf")]:
        sw = lcb_val > float(thr)
        net_gain = float(np.mean(y_val * sw.astype(np.float64)))
        gain_if_sw = float(np.mean(y_val[sw])) if bool(np.any(sw)) else 0.0
        rate = float(np.mean(sw.astype(np.float64)))
        # key: maximize total gain; tie-break prefer lower switch rate; then prefer *larger* thresholds (more conservative).
        key = (net_gain, -rate, gain_if_sw, float(thr))
        if best is None or key > best["key"]:
            best = {"key": key, "thr": float(thr), "net_gain": net_gain, "gain_if_sw": gain_if_sw, "rate": rate}
    assert best is not None
    thr = float(best["thr"])

    def _apply(df: pd.DataFrame, elig: np.ndarray, pred: np.ndarray, diff: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        q_vec = np.array([q_by_diff.get(str(d), 0.0) for d in diff], dtype=np.float64)
        lcb = (pred - q_vec).astype(np.float64)
        sw_sub = (lcb > float(thr)).astype(bool)
        sw = np.zeros(len(df), dtype=bool)
        sw[np.asarray(elig, dtype=bool)] = sw_sub
        lcb_full = np.full(len(df), float("nan"), dtype=np.float64)
        lcb_full[np.asarray(elig, dtype=bool)] = lcb
        use_fast = df["use_fast_p5"].to_numpy(dtype=bool).copy()
        use_fast[elig] = use_fast[elig] & (~sw_sub)
        probe_used = df["use_fast_p5"].to_numpy(dtype=bool).copy()
        return use_fast.astype(bool), probe_used.astype(bool), sw.astype(bool), lcb_full.astype(np.float64)

    # Apply to full splits.
    # NOTE: probe_used indicates "trace executed" (eligible branch). Overhead is charged only when the final route is slow.
    use_fast_cal, probe_used_cal, sw_cal, _lcb_cal = _apply(
        calib_train_df, elig_train, reg.predict(x_train).astype(np.float64), calib_train_df.loc[elig_train, "difficulty"].to_numpy(dtype=str)
    )
    use_fast_val, probe_used_val, sw_val, lcb_val2 = _apply(calib_val_df, elig_val, pred_val, diff_val)
    use_fast_test, probe_used_test, sw_test, lcb_test = _apply(test_df, elig_test, pred_test, diff_test)

    # Test delta-J vs P5 with strict trace accounting.
    j_p5_test = _route_only_J(test_df, test_df["use_fast_p5"].to_numpy(dtype=bool), t_ref=float(t_ref), beta=float(beta))
    j_route_test = _route_only_J(test_df, use_fast_test, t_ref=float(t_ref), beta=float(beta))
    cost_test = _probe_cost_norm(test_df, t_ref=float(t_ref))
    overhead_mode = str(overhead_mode).lower().strip()
    if overhead_mode == "trace_slow_only":
        overhead = cost_test * sw_test.astype(np.float64)
    elif overhead_mode == "trace_slow_overlap_infer":
        if "infer_slow_ms" not in test_df.columns:
            raise RuntimeError("trace_switch_v1: overhead_mode=trace_slow_overlap_infer requires infer_slow_ms in test_df.")
        infer_norm = np.clip(test_df["infer_slow_ms"].to_numpy(dtype=np.float64), 0.0, None) / max(float(t_ref), 1e-9)
        overhead = np.maximum(cost_test - infer_norm, 0.0) * sw_test.astype(np.float64)
    else:
        raise ValueError(f"trace_switch_v1: invalid overhead_mode={overhead_mode!r}")
    j_test = (j_route_test + overhead).astype(np.float64)
    delta = (j_p5_test - j_test).astype(np.float64)

    # Save decisions (calib+val concatenated for inspection; test includes debug columns).
    cal_dec = _save_policy_decisions(
        out_dir,
        split_name="calib",
        df=pd.concat([calib_train_df, calib_val_df], ignore_index=True),
        use_fast=np.concatenate([use_fast_cal, use_fast_val]),
        probe_used=np.concatenate([probe_used_cal, probe_used_val]),
        extra_cols={
            "switch_to_slow": np.concatenate([sw_cal, sw_val]).astype(bool),
        },
    )
    net_true_full = np.full(len(test_df), float("nan"), dtype=np.float64)
    net_true_full[elig_test] = y_test.astype(np.float64)
    test_dec = _save_policy_decisions(
        out_dir,
        split_name="test",
        df=test_df,
        use_fast=use_fast_test,
        probe_used=probe_used_test,
        extra_cols={
            "switch_to_slow": sw_test.astype(bool),
            "net_improve_lcb": lcb_test.astype(np.float64),
            "net_improve_true": net_true_full.astype(np.float64),
            "trace_cost_norm": cost_test.astype(np.float64),
            "trace_overhead_norm": overhead.astype(np.float64),
        },
    )

    meta = {
        "version": "trace_switch_v1",
        "seed": int(seed),
        "inputs": dict(input_hashes),
        "calib_split": dict(calib_split_cfg),
        "probe_overhead_mode": str(overhead_mode),
        "objective": {"T_ref": float(t_ref), "beta": float(beta)},
        "trace_switch": {
            "alpha": float(alpha),
            "q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()},
            "threshold": float(thr),
            "val_mean_net_improve": float(best["net_gain"]),
            "val_mean_net_improve_if_switched": float(best["gain_if_sw"]),
            "val_switch_rate": float(best["rate"]),
        },
        "test_metrics": {
            "trace_used_rate": float(np.mean(probe_used_test.astype(np.float64))),
            "switch_rate": float(np.mean(sw_test.astype(np.float64))),
            "delta_j_mean_vs_p5": float(np.mean(delta)),
            "delta_j_median_vs_p5": float(np.median(delta)),
            "mean_delta_j_route_only": float(np.mean((j_p5_test - j_route_test).astype(np.float64))),
            "mean_trace_overhead_norm": float(np.mean(overhead)),
        },
        "artifacts": {
            "calib_decisions_parquet": str(cal_dec),
            "test_decisions_parquet": str(test_dec),
        },
    }
    metrics_path = out_dir / "policy_metrics.json"
    metrics_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"policy_dir": out_dir, "metrics": meta, "metrics_path": metrics_path}


def _read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def _split_calib_train_val(
    df: pd.DataFrame,
    *,
    train_frac: float,
    seed: int,
    group_col: str = "difficulty",
    groups: tuple[str, ...] = ("easy", "medium", "hard"),
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    if not (0.0 < float(train_frac) < 1.0):
        raise ValueError(f"train_frac must be in (0,1): got {train_frac!r}")
    if group_col not in df.columns:
        raise ValueError(f"Missing group_col={group_col!r} in calib df.")
    if "sample_name" not in df.columns:
        raise ValueError("Missing sample_name in calib df.")

    rng = np.random.default_rng(int(seed))
    train_ids: list[int] = []
    val_ids: list[int] = []
    split_by_sample: dict[str, str] = {}

    for g in groups:
        ids = np.where(df[group_col].to_numpy().astype(str) == str(g))[0]
        if ids.size <= 0:
            continue
        perm = ids.copy()
        rng.shuffle(perm)
        n = int(perm.size)
        n_train = int(math.floor(float(train_frac) * n))
        if n >= 2:
            n_train = int(np.clip(n_train, 1, n - 1))
        else:
            n_train = int(np.clip(n_train, 0, n))
        tr = perm[:n_train]
        va = perm[n_train:]
        train_ids.extend(tr.tolist())
        val_ids.extend(va.tolist())
        for i in tr.tolist():
            split_by_sample[str(df.iloc[i]["sample_name"])] = "train"
        for i in va.tolist():
            split_by_sample[str(df.iloc[i]["sample_name"])] = "val"

    train_df = df.iloc[train_ids].reset_index(drop=True).copy()
    val_df = df.iloc[val_ids].reset_index(drop=True).copy()
    if train_df.empty or val_df.empty:
        raise RuntimeError(
            f"Invalid calib split: train={len(train_df)} val={len(val_df)}; "
            "check --calib-train-frac and dataset size."
        )
    return train_df, val_df, split_by_sample


def _apply_tau_by_diff(diff: np.ndarray, score: np.ndarray, tau_by_diff: dict[str, float]) -> np.ndarray:
    diff = np.asarray(diff).astype(str)
    score = np.asarray(score, dtype=np.float64)
    tau = np.array([float(tau_by_diff.get(str(d), float("inf"))) for d in diff], dtype=np.float64)
    return (score <= tau).astype(bool)


def _wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    phat = float(k / n)
    den = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / den
    half = (z * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)) / den
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return float(lo), float(hi)


def _ensure_probe_features(
    dataset_root: Path,
    probe_feat_calib: Path,
    probe_feat_test: Path,
    out_dir: Path,
) -> tuple[Path, Path]:
    common = out_dir / "common"
    common.mkdir(parents=True, exist_ok=True)
    cal = probe_feat_calib
    te = probe_feat_test
    if not cal.exists():
        cal = common / "probe_features_calib.parquet"
        _build_probe_features(dataset_root=dataset_root, split="calib", max_expansions=96, out_cache=cal)
    if not te.exists():
        te = common / "probe_features_test.parquet"
        _build_probe_features(dataset_root=dataset_root, split="test", max_expansions=96, out_cache=te)
    return cal, te


def _load_conformal_tables(calib_cf: Path, test_cf: Path, feat_calib: Path, feat_test: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    c = _read_parquet(calib_cf)
    t = _read_parquet(test_cf)
    fc = _read_parquet(feat_calib)
    ft = _read_parquet(feat_test)
    c = c.merge(fc, on=["sample_name", "difficulty"], how="inner")
    t = t.merge(ft, on=["sample_name", "difficulty"], how="inner")
    need = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
        "ood_family",
        "source_dataset",
        "scenario",
        "map_id",
    ]
    miss_c = int(c[need].isna().sum().sum())
    miss_t = int(t[need].isna().sum().sum())
    if miss_c != 0 or miss_t != 0:
        raise RuntimeError(f"Missing conformal features after merge: calib={miss_c}, test={miss_t}")
    return c, t


def _build_conformal_xy(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    eps: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    feat_num = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
    ]
    # IMPORTANT(validity): do not include dataset identifiers (source_dataset/scenario/map_id) or split-derived flags.
    # Keep only deployable group keys (difficulty) for stratified calibration.
    feat_cat = ["difficulty"]
    x_train = pd.get_dummies(train_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_val = pd.get_dummies(val_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_test = pd.get_dummies(test_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_val = x_val.reindex(columns=x_train.columns, fill_value=0)
    x_test = x_test.reindex(columns=x_train.columns, fill_value=0)
    y_train = (train_df["q_rel"].to_numpy(dtype=np.float64) > float(eps)).astype(np.float64)
    y_val = (val_df["q_rel"].to_numpy(dtype=np.float64) > float(eps)).astype(np.float64)
    return x_train, x_val, x_test, y_train, y_val


def _cost_feature_columns() -> tuple[list[str], list[str]]:
    feat_num = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
    ]
    feat_cat = ["difficulty"]
    return feat_num, feat_cat


def _cost_design_matrix(df: pd.DataFrame, *, ref_cols: pd.Index | None = None) -> pd.DataFrame:
    feat_num, feat_cat = _cost_feature_columns()
    missing = [c for c in (feat_num + feat_cat) if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing cost features: {missing}")
    x = pd.get_dummies(df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    if ref_cols is not None:
        x = x.reindex(columns=ref_cols, fill_value=0)
    return x


def _predict_cost_c_hat(
    *,
    seed: int,
    train_df: pd.DataFrame,
    eval_dfs: dict[str, pd.DataFrame],
    args: argparse.Namespace,
) -> tuple[GradientBoostingRegressor, dict[str, np.ndarray]]:
    if "c" not in train_df.columns:
        raise RuntimeError("Missing oracle cost column `c` in calibration dataframe.")
    x_train = _cost_design_matrix(train_df)
    y_train = np.clip(train_df["c"].to_numpy(dtype=np.float64), 0.0, None)
    reg = GradientBoostingRegressor(
        random_state=int(seed),
        n_estimators=int(args.gbr_n_estimators),
        learning_rate=float(args.gbr_learning_rate),
        max_depth=int(args.gbr_max_depth),
        subsample=float(args.gbr_subsample),
    )
    reg.fit(x_train, y_train)

    preds: dict[str, np.ndarray] = {}
    preds["train"] = np.clip(reg.predict(x_train).astype(np.float64), 1e-6, None)
    for name, df in eval_dfs.items():
        x = _cost_design_matrix(df, ref_cols=x_train.columns)
        preds[str(name)] = np.clip(reg.predict(x).astype(np.float64), 1e-6, None)
    return reg, preds


def _split_conformal_offsets(
    calib_df: pd.DataFrame,
    y_cal: np.ndarray,
    p_cal: np.ndarray,
    alpha: float,
) -> dict[str, float]:
    out: dict[str, float] = {}
    diff = calib_df["difficulty"].to_numpy()
    for d in ("easy", "medium", "hard"):
        mask = diff == d
        s = np.maximum(y_cal[mask] - p_cal[mask], 0.0)
        n = int(s.size)
        if n <= 0:
            out[d] = 0.0
            continue
        level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / n)
        level = float(np.clip(level, 0.0, 1.0))
        out[d] = float(np.quantile(s, level, method="higher"))
    return out


def _conformal_metric_from_k(
    pre_v_easy: np.ndarray,
    pre_v_med: np.ndarray,
    pre_v_hard: np.ndarray,
    pre_c_easy: np.ndarray,
    pre_c_med: np.ndarray,
    pre_c_hard: np.ndarray,
    base_v: int,
    base_lat: float,
    n_total: int,
    k_easy: int,
    k_med: int,
    k_hard: int,
) -> tuple[float, float, float]:
    v = int(base_v - (pre_v_easy[k_easy] + pre_v_med[k_med] + pre_v_hard[k_hard]))
    vio = float(v / max(n_total, 1))
    ci_up = float(_wilson_ci(v, n_total)[1])
    lat = float(base_lat + pre_c_easy[k_easy] + pre_c_med[k_med] + pre_c_hard[k_hard])
    return vio, ci_up, lat


def _apply_k_by_diff(df: pd.DataFrame, score: np.ndarray, k_by_diff: dict[str, int]) -> tuple[np.ndarray, dict[str, float]]:
    use_fast = np.ones(len(df), dtype=bool)
    tau: dict[str, float] = {}
    diff = df["difficulty"].to_numpy()
    for d in ("easy", "medium", "hard"):
        ids = np.where(diff == d)[0]
        ord_desc = ids[np.argsort(score[ids])[::-1]]
        k = int(np.clip(int(k_by_diff.get(d, 0)), 0, len(ord_desc)))
        if len(ord_desc) == 0:
            tau[d] = float("inf")
            continue
        use_fast[ord_desc[:k]] = False
        if k <= 0:
            tau[d] = float(np.max(score[ids]) + 1e-12)
        elif k >= len(ord_desc):
            tau[d] = float(np.min(score[ids]) - 1e-12)
        else:
            tau[d] = float((score[ord_desc[k - 1]] + score[ord_desc[k]]) * 0.5)
    return use_fast, tau


def _conformal_policy_metrics(df: pd.DataFrame, use_fast: np.ndarray, eps_rel: float) -> dict:
    q = df["q_rel"].to_numpy(dtype=np.float64)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
    drel = np.where(use_fast, q, 0.0)
    vio_mask = drel > float(eps_rel)
    k = int(np.sum(vio_mask))
    n = int(len(drel))
    ci_lo, ci_hi = _wilson_ci(k, n)
    hard = df["difficulty"].to_numpy() == "hard"
    pos = np.maximum(drel, 0.0)
    fr = {
        "easy": float(np.mean(use_fast[df["difficulty"].to_numpy() == "easy"])),
        "medium": float(np.mean(use_fast[df["difficulty"].to_numpy() == "medium"])),
        "hard": float(np.mean(use_fast[hard])),
    }
    return {
        "num_cases": n,
        "fast_ratio": float(np.mean(use_fast)),
        "fast_ratio_by_difficulty": fr,
        "avg_latency_ms": float(np.mean(np.where(use_fast, t_fast, t_slow))),
        "avg_delta_l_rel": float(np.mean(drel)),
        "avg_delta_l_rel_pos": float(np.mean(pos)),
        "hard_delta_l_rel_pos": float(np.mean(pos[hard])) if int(np.sum(hard)) > 0 else 0.0,
        "violation_rate": float(np.mean(vio_mask)),
        "violation_count": int(k),
        "violation_rate_ci95": [float(ci_lo), float(ci_hi)],
    }


def _run_conformal_seed(
    seed: int,
    calib_df: pd.DataFrame,
    calib_train_df: pd.DataFrame,
    calib_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    args: argparse.Namespace,
    out_dir: Path,
    *,
    input_hashes: dict[str, str] | None = None,
    calib_split_cfg: dict[str, object] | None = None,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    input_hashes = {} if input_hashes is None else dict(input_hashes)
    calib_split_cfg = {} if calib_split_cfg is None else dict(calib_split_cfg)

    select_on = str(getattr(args, "conformal_select_on", "calib")).lower().strip()
    if select_on not in {"calib", "test"}:
        raise ValueError(f"Invalid --conformal-select-on: {select_on!r}")

    x_train, x_val, x_test, y_train, y_val = _build_conformal_xy(calib_train_df, calib_val_df, test_df, eps=float(args.epsilon_rel))
    clf = GradientBoostingClassifier(
        random_state=int(seed),
        n_estimators=int(args.gbc_n_estimators),
        learning_rate=float(args.gbc_learning_rate),
        max_depth=int(args.gbc_max_depth),
        subsample=float(args.gbc_subsample),
    )
    clf.fit(x_train, y_train)
    p_val = clf.predict_proba(x_val)[:, 1].astype(np.float64)
    p_test = clf.predict_proba(x_test)[:, 1].astype(np.float64)
    feat_num = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
    ]
    feat_cat = ["difficulty"]
    x_all = pd.get_dummies(calib_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_all = x_all.reindex(columns=x_train.columns, fill_value=0)
    p_all = clf.predict_proba(x_all)[:, 1].astype(np.float64)

    alpha_grid = _parse_grid(args.strict_conformal_alpha_grid)
    a_grid = _parse_grid(args.strict_score_a_grid)
    b_grid = _parse_grid(args.strict_score_b_grid)
    tune_v_target = float(max(float(args.strict_violation_target) - float(args.strict_tune_violation_margin), 0.0))
    tune_ci_target = float(max(float(args.strict_ci_upper_target) - float(args.strict_tune_ci_margin), 0.0))

    # IMPORTANT(validity): never use oracle per-sample c = T_slow - T_fast in routing decisions.
    # Instead, fit a cost predictor c_hat(x) on calib_train using deployable static features only.
    cost_reg, c_hat = _predict_cost_c_hat(
        seed=int(seed),
        train_df=calib_train_df,
        eval_dfs={"all": calib_df, "val": calib_val_df, "test": test_df},
        args=args,
    )
    c_hat_train = np.asarray(c_hat["train"], dtype=np.float64)
    c_hat_all = np.asarray(c_hat["all"], dtype=np.float64)
    c_hat_val = np.asarray(c_hat["val"], dtype=np.float64)
    c_hat_test = np.asarray(c_hat["test"], dtype=np.float64)

    c_ref = float(np.median(c_hat_train))
    if not np.isfinite(c_ref) or c_ref <= 1e-9:
        c_ref = float(np.median(c_hat_all))
    c_ref = float(max(c_ref, 1e-6))

    c_norm_all = np.clip(c_hat_all / c_ref, 1e-6, None)
    c_norm_val = np.clip(c_hat_val / c_ref, 1e-6, None)
    c_norm_test = np.clip(c_hat_test / c_ref, 1e-6, None)
    q_val = calib_val_df["q_rel"].to_numpy(dtype=np.float64)
    diff_val = calib_val_df["difficulty"].to_numpy()
    diff_all = calib_df["difficulty"].to_numpy()
    diff_test = test_df["difficulty"].to_numpy()

    n_val = int(len(calib_val_df))
    base_v = int(np.sum(q_val > float(args.epsilon_rel)))
    base_lat = float(np.mean(calib_val_df["T_fast_ms"].to_numpy(dtype=np.float64)))

    rows: list[dict] = []
    selected = None

    for alpha in alpha_grid:
        q_by_diff = _split_conformal_offsets(calib_val_df, y_cal=y_val, p_cal=p_val, alpha=float(alpha))
        p_val_u = np.clip(
            p_val + np.array([q_by_diff[d] for d in diff_val], dtype=np.float64),
            0.0,
            1.0,
        )
        p_test_u = None
        if select_on == "test":
            p_test_u = np.clip(
                p_test + np.array([q_by_diff[d] for d in diff_test], dtype=np.float64),
                0.0,
                1.0,
            )

        for a in a_grid:
            for b in b_grid:
                score_val = (np.clip(p_val_u, 1e-9, 1.0) ** float(a)) / (np.clip(c_norm_val, 1e-6, None) ** float(b))
                score_test = None
                if select_on == "test":
                    assert p_test_u is not None
                    score_test = (np.clip(p_test_u, 1e-9, 1.0) ** float(a)) / (np.clip(c_norm_test, 1e-6, None) ** float(b))

                prep: dict[str, dict] = {}
                pre_v: dict[str, np.ndarray] = {}
                pre_c: dict[str, np.ndarray] = {}
                for d in ("easy", "medium", "hard"):
                    ids = np.where(diff_val == d)[0]
                    ord_desc = ids[np.argsort(score_val[ids])[::-1]]
                    prep[d] = {"ids": ids, "ord_desc": ord_desc, "n": len(ord_desc)}
                    pre_v[d] = np.concatenate([[0], np.cumsum((q_val[ord_desc] > float(args.epsilon_rel)).astype(np.int32))])
                    pre_c[d] = np.concatenate([[0.0], np.cumsum(c_hat_val[ord_desc] / max(n_val, 1))])

                # Greedy init that prioritizes high violation-reduction per latency under strict tune targets.
                k_init = {"easy": 0, "medium": 0, "hard": 0}
                ptr = {"easy": 0, "medium": 0, "hard": 0}
                cur_v = base_v
                cur_ci = _wilson_ci(cur_v, n_val)[1]
                while (cur_v / max(n_val, 1) > tune_v_target or cur_ci > tune_ci_target) and any(
                    ptr[d] < prep[d]["n"] for d in ("easy", "medium", "hard")
                ):
                    best_d = None
                    best_ratio = -1.0
                    for d in ("easy", "medium", "hard"):
                        p = int(ptr[d])
                        if p >= int(prep[d]["n"]):
                            continue
                        idx = int(prep[d]["ord_desc"][p])
                        vio_reduction = 1.0 if q_val[idx] > float(args.epsilon_rel) else 0.0
                        # Small score prior stabilizes tie-breaking on non-violating samples.
                        score_prior = float(np.clip(score_val[idx], 0.0, 1.0))
                        lat_cost = float(c_hat_val[idx] / max(n_val, 1))
                        ratio = (vio_reduction + 0.25 * score_prior) / max(lat_cost, 1e-9)
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_d = d
                    if best_d is None:
                        break
                    ptr[best_d] += 1
                    k_init[best_d] += 1
                    cur_v = int(
                        base_v
                        - (
                            pre_v["easy"][k_init["easy"]]
                            + pre_v["medium"][k_init["medium"]]
                            + pre_v["hard"][k_init["hard"]]
                        )
                    )
                    cur_ci = _wilson_ci(cur_v, n_val)[1]

                if cur_v / max(n_val, 1) > tune_v_target or cur_ci > tune_ci_target:
                    rows.append(
                        {
                            "alpha": float(alpha),
                            "a": float(a),
                            "b": float(b),
                            "feasible_on_tune": False,
                        }
                    )
                    continue

                w = int(max(args.strict_search_window, 0))
                step = int(max(args.strict_search_step, 1))
                ranges = {
                    d: range(
                        max(0, int(k_init[d]) - w),
                        min(int(prep[d]["n"]), int(k_init[d]) + w) + 1,
                        step,
                    )
                    for d in ("easy", "medium", "hard")
                }

                best_local = None
                for ke in ranges["easy"]:
                    for km in ranges["medium"]:
                        for kh in ranges["hard"]:
                            vio, ci_up, lat = _conformal_metric_from_k(
                                pre_v_easy=pre_v["easy"],
                                pre_v_med=pre_v["medium"],
                                pre_v_hard=pre_v["hard"],
                                pre_c_easy=pre_c["easy"],
                                pre_c_med=pre_c["medium"],
                                pre_c_hard=pre_c["hard"],
                                base_v=base_v,
                                base_lat=base_lat,
                                n_total=n_val,
                                k_easy=int(ke),
                                k_med=int(km),
                                k_hard=int(kh),
                            )
                            if vio > tune_v_target + 1e-12 or ci_up > tune_ci_target + 1e-12:
                                continue
                            cand = (lat, ci_up, vio, int(ke), int(km), int(kh))
                            if best_local is None or cand < best_local:
                                best_local = cand

                if best_local is None:
                    rows.append(
                        {
                            "alpha": float(alpha),
                            "a": float(a),
                            "b": float(b),
                            "feasible_on_tune": False,
                        }
                    )
                    continue

                k_by_diff = {"easy": int(best_local[3]), "medium": int(best_local[4]), "hard": int(best_local[5])}
                use_val, tau_by_diff = _apply_k_by_diff(calib_val_df, score_val, k_by_diff)
                m_val = _conformal_policy_metrics(calib_val_df, use_val, eps_rel=float(args.epsilon_rel))
                gate_val = bool(
                    float(m_val["violation_rate"]) <= float(args.strict_violation_target) + 1e-12
                    and float(m_val["violation_rate_ci95"][1]) <= float(args.strict_ci_upper_target) + 1e-12
                )
                gate_test = None
                m_test = None
                if select_on == "test":
                    assert score_test is not None
                    use_test = _apply_tau_by_diff(diff_test, score_test, tau_by_diff)
                    m_test = _conformal_policy_metrics(test_df, use_test, eps_rel=float(args.epsilon_rel))
                    gate_test = bool(
                        float(m_test["violation_rate"]) <= float(args.strict_violation_target) + 1e-12
                        and float(m_test["violation_rate_ci95"][1]) <= float(args.strict_ci_upper_target) + 1e-12
                    )

                row = {
                    "alpha": float(alpha),
                    "a": float(a),
                    "b": float(b),
                    "q_easy": float(q_by_diff["easy"]),
                    "q_medium": float(q_by_diff["medium"]),
                    "q_hard": float(q_by_diff["hard"]),
                    "k_slow_easy": int(k_by_diff["easy"]),
                    "k_slow_medium": int(k_by_diff["medium"]),
                    "k_slow_hard": int(k_by_diff["hard"]),
                    "tune_latency_ms": float(best_local[0]),
                    "tune_violation_rate": float(best_local[2]),
                    "tune_violation_ci_up": float(best_local[1]),
                    "val_latency_ms": float(m_val["avg_latency_ms"]),
                    "val_violation_rate": float(m_val["violation_rate"]),
                    "val_violation_ci_up": float(m_val["violation_rate_ci95"][1]),
                    "val_fast_ratio": float(m_val["fast_ratio"]),
                    "feasible_on_tune": True,
                    "feasible_on_val": bool(gate_val),
                }
                if m_test is not None:
                    row.update(
                        {
                            "test_latency_ms": float(m_test["avg_latency_ms"]),
                            "test_violation_rate": float(m_test["violation_rate"]),
                            "test_violation_ci_up": float(m_test["violation_rate_ci95"][1]),
                            "test_fast_ratio": float(m_test["fast_ratio"]),
                            "feasible_on_test": bool(gate_test),
                        }
                    )
                rows.append(row)

                if select_on == "calib":
                    if not gate_val:
                        continue
                    cand = (float(m_val["avg_latency_ms"]), float(m_val["violation_rate_ci95"][1]), float(m_val["violation_rate"]))
                else:
                    assert m_test is not None and gate_test is not None
                    if not bool(gate_test):
                        continue
                    cand = (float(m_test["avg_latency_ms"]), float(m_test["violation_rate_ci95"][1]), float(m_test["violation_rate"]))

                if selected is None or cand < selected["key"]:
                    selected = {
                        "key": cand,
                        "alpha": float(alpha),
                        "a": float(a),
                        "b": float(b),
                        "q_by_diff": q_by_diff,
                        "tau_by_diff": tau_by_diff,
                        "k_by_diff": k_by_diff,
                        "val_metrics": m_val,
                    }

    search_df = pd.DataFrame(rows)
    search_csv = out_dir / "search_log.csv"
    search_df.to_csv(search_csv, index=False)

    if selected is None:
        raise RuntimeError(
            f"No feasible strict conformal policy for seed={seed}. Check: {search_csv}"
        )

    def _save_decisions(
        path: Path,
        df: pd.DataFrame,
        use_fast: np.ndarray,
        p_upper: np.ndarray,
        score: np.ndarray,
        c_hat_ms: np.ndarray,
        c_hat_norm: np.ndarray,
    ) -> None:
        out = df.copy()
        out["p_upper"] = p_upper.astype(np.float64)
        out["risk_score"] = score.astype(np.float64)
        out["use_fast"] = use_fast.astype(bool)
        out["route"] = np.where(use_fast, "fast", "slow")
        out["U_conformal"] = score.astype(np.float64)
        out["c_hat_ms"] = np.asarray(c_hat_ms, dtype=np.float64)
        out["c_hat_norm"] = np.asarray(c_hat_norm, dtype=np.float64)
        out.to_parquet(path, index=False)

    # Final evaluation on calib/test is performed once for the selected hyperparameters.
    q_by_diff = selected["q_by_diff"]
    p_all_u = np.clip(p_all + np.array([q_by_diff[d] for d in diff_all], dtype=np.float64), 0.0, 1.0)
    p_test_u = np.clip(p_test + np.array([q_by_diff[d] for d in diff_test], dtype=np.float64), 0.0, 1.0)
    a_sel = float(selected["a"])
    b_sel = float(selected["b"])
    score_all = (np.clip(p_all_u, 1e-9, 1.0) ** a_sel) / (np.clip(c_norm_all, 1e-6, None) ** b_sel)
    p_val_u = np.clip(p_val + np.array([q_by_diff[d] for d in diff_val], dtype=np.float64), 0.0, 1.0)
    score_val = (np.clip(p_val_u, 1e-9, 1.0) ** a_sel) / (np.clip(c_norm_val, 1e-6, None) ** b_sel)
    score_test = (np.clip(p_test_u, 1e-9, 1.0) ** a_sel) / (np.clip(c_norm_test, 1e-6, None) ** b_sel)
    use_all = _apply_tau_by_diff(diff_all, score_all, selected["tau_by_diff"])
    use_val = _apply_tau_by_diff(diff_val, score_val, selected["tau_by_diff"])
    use_test = _apply_tau_by_diff(diff_test, score_test, selected["tau_by_diff"])
    m_all = _conformal_policy_metrics(calib_df, use_all, eps_rel=float(args.epsilon_rel))
    m_test = _conformal_policy_metrics(test_df, use_test, eps_rel=float(args.epsilon_rel))

    calib_dec = out_dir / "calib_decisions.parquet"
    test_dec = out_dir / "test_decisions.parquet"
    _save_decisions(calib_dec, calib_df, use_all, p_all_u, score_all, c_hat_all, c_norm_all)
    _save_decisions(test_dec, test_df, use_test, p_test_u, score_test, c_hat_test, c_norm_test)

    gate = {
        "violation_rate_le_target": bool(m_test["violation_rate"] <= float(args.strict_violation_target) + 1e-12),
        "violation_ci95_upper_le_target": bool(m_test["violation_rate_ci95"][1] <= float(args.strict_ci_upper_target) + 1e-12),
        "backoff_count_zero": True,
    }
    metrics = {
        "version": "conformal_strict_v2",
        "seed": int(seed),
        "inputs": dict(input_hashes),
        "calib_split": dict(calib_split_cfg),
        "cost_proxy": {
            "name": "c_hat_gbr_static_v1",
            "target_def": "c = T_slow_ms - T_fast_ms",
            "fit_split": "calib_train",
            "features_num": _cost_feature_columns()[0],
            "features_cat": _cost_feature_columns()[1],
            "ref_median_ms": float(c_ref),
            "model": {
                "type": "GradientBoostingRegressor",
                "n_estimators": int(args.gbr_n_estimators),
                "learning_rate": float(args.gbr_learning_rate),
                "max_depth": int(args.gbr_max_depth),
                "subsample": float(args.gbr_subsample),
            },
        },
        "strict_targets": {
            "violation_rate": float(args.strict_violation_target),
            "ci95_upper": float(args.strict_ci_upper_target),
        },
        "search_tune_targets": {
            "violation_rate": float(tune_v_target),
            "ci95_upper": float(tune_ci_target),
        },
        "selected_policy": {
            "alpha_conformal": float(selected["alpha"]),
            "score_power_a": float(selected["a"]),
            "score_cost_power_b": float(selected["b"]),
            "q_by_difficulty": {k: float(v) for k, v in selected["q_by_diff"].items()},
            "tau_by_difficulty": {k: float(v) for k, v in selected["tau_by_diff"].items()},
            "k_slow_by_difficulty": {k: int(v) for k, v in selected["k_by_diff"].items()},
            "rule": "difficulty-wise thresholded U_conformal; fast iff U<=tau_d",
            "backoff_count": 0,
            "selection_split": str(select_on),
            "oracle_assist_used": False,
        },
        "calib_metrics": m_all,
        "val_metrics": selected.get("val_metrics", {}),
        "test_metrics": m_test,
        "phase8_conformal_gate_check": gate,
        "artifacts": {
            "search_log_csv": str(search_csv),
            "calib_decisions_parquet": str(calib_dec),
            "test_decisions_parquet": str(test_dec),
        },
    }
    metrics_path = out_dir / "policy_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return {
        "metrics_path": metrics_path,
        "metrics": metrics,
        "calib_decisions": calib_dec,
        "test_decisions": test_dec,
        "use_fast_calib": use_all.astype(bool),
        "use_fast_val": use_val.astype(bool),
        "use_fast_test": use_test.astype(bool),
    }


def _split_conformal_offsets_by_partition(
    *,
    part_ids: np.ndarray,
    y_cal: np.ndarray,
    p_cal: np.ndarray,
    alpha: float,
) -> dict[int, float]:
    part_ids = np.asarray(part_ids, dtype=np.int64)
    y_cal = np.asarray(y_cal, dtype=np.float64)
    p_cal = np.asarray(p_cal, dtype=np.float64)
    if part_ids.shape[0] != y_cal.shape[0] or part_ids.shape[0] != p_cal.shape[0]:
        raise ValueError("partition offset: shape mismatch.")
    out: dict[int, float] = {}
    for pid in np.unique(part_ids).tolist():
        mask = part_ids == int(pid)
        s = np.maximum(y_cal[mask] - p_cal[mask], 0.0)
        n = int(s.size)
        if n <= 0:
            out[int(pid)] = 0.0
            continue
        level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / n)
        level = float(np.clip(level, 0.0, 1.0))
        out[int(pid)] = float(np.quantile(s, level, method="higher"))
    return out


def _run_partition_crc_seed(
    *,
    seed: int,
    calib_df: pd.DataFrame,
    calib_train_df: pd.DataFrame,
    calib_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    args: argparse.Namespace,
    out_dir: Path,
    input_hashes: dict[str, str],
    calib_split_cfg: dict[str, object],
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Objective parameters must be derived from calib_train only (strict; no test peeking).
    t_ref = float(np.median(calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(calib_train_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    nz = q_pos[q_pos > 1e-9]
    q_med = float(np.median(nz)) if nz.size > 0 else 1.0
    beta = float(
        np.clip(
            np.median(calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)) / max(q_med, 1e-9),
            1e-3,
            200.0,
        )
    )

    # Reuse the same base feature set as conformal_strict_v2, but tighten conformal offsets via learned partitions.
    x_train, x_val, x_test, y_train, y_val = _build_conformal_xy(
        calib_train_df, calib_val_df, test_df, eps=float(args.epsilon_rel)
    )
    clf = GradientBoostingClassifier(
        random_state=int(seed),
        n_estimators=int(args.gbc_n_estimators),
        learning_rate=float(args.gbc_learning_rate),
        max_depth=int(args.gbc_max_depth),
        subsample=float(args.gbc_subsample),
    )
    clf.fit(x_train, y_train)
    p_val = clf.predict_proba(x_val)[:, 1].astype(np.float64)
    p_test = clf.predict_proba(x_test)[:, 1].astype(np.float64)

    feat_num = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
    ]
    feat_cat = ["difficulty"]
    x_all = pd.get_dummies(calib_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_all = x_all.reindex(columns=x_train.columns, fill_value=0)
    p_all = clf.predict_proba(x_all)[:, 1].astype(np.float64)

    # Cost proxy c_hat(x) (deployable; fitted on calib_train only).
    _cost_reg, c_hat = _predict_cost_c_hat(
        seed=int(seed),
        train_df=calib_train_df,
        eval_dfs={"all": calib_df, "val": calib_val_df, "test": test_df},
        args=args,
    )
    c_hat_train = np.asarray(c_hat["train"], dtype=np.float64)
    c_hat_all = np.asarray(c_hat["all"], dtype=np.float64)
    c_hat_val = np.asarray(c_hat["val"], dtype=np.float64)
    c_hat_test = np.asarray(c_hat["test"], dtype=np.float64)

    c_ref = float(np.median(c_hat_train))
    if not np.isfinite(c_ref) or c_ref <= 1e-9:
        c_ref = float(np.median(c_hat_all))
    c_ref = float(max(c_ref, 1e-6))
    c_norm_all = np.clip(c_hat_all / c_ref, 1e-6, None)
    c_norm_val = np.clip(c_hat_val / c_ref, 1e-6, None)
    c_norm_test = np.clip(c_hat_test / c_ref, 1e-6, None)

    # Learn a small partitioner on calib_train only (deployable features).
    max_leaves = int(max(getattr(args, "partition_crc_max_leaves", 2), 2))
    min_leaf = int(max(getattr(args, "partition_crc_min_leaf", 1), 1))
    part = DecisionTreeClassifier(
        random_state=int(seed) + 991,
        max_leaf_nodes=max_leaves,
        min_samples_leaf=min_leaf,
    )
    part.fit(x_train, y_train)
    leaf_val = part.apply(x_val).astype(np.int64)
    leaf_test = part.apply(x_test).astype(np.int64)
    leaf_all = part.apply(x_all).astype(np.int64)

    alpha_grid = _parse_grid(args.strict_conformal_alpha_grid)
    a_grid = _parse_grid(args.strict_score_a_grid)
    b_grid = _parse_grid(args.strict_score_b_grid)
    tune_v_target = float(max(float(args.strict_violation_target) - float(args.strict_tune_violation_margin), 0.0))
    tune_ci_target = float(max(float(args.strict_ci_upper_target) - float(args.strict_tune_ci_margin), 0.0))

    q_val = calib_val_df["q_rel"].to_numpy(dtype=np.float64)
    diff_val = calib_val_df["difficulty"].to_numpy()
    diff_all = calib_df["difficulty"].to_numpy()
    diff_test = test_df["difficulty"].to_numpy()

    n_val = int(len(calib_val_df))
    base_v = int(np.sum(q_val > float(args.epsilon_rel)))
    base_lat = float(np.mean(calib_val_df["T_fast_ms"].to_numpy(dtype=np.float64)))

    rows: list[dict] = []
    selected = None

    for alpha in alpha_grid:
        q_by_leaf = _split_conformal_offsets_by_partition(part_ids=leaf_val, y_cal=y_val, p_cal=p_val, alpha=float(alpha))
        q_val_vec = np.array([float(q_by_leaf.get(int(pid), 0.0)) for pid in leaf_val], dtype=np.float64)
        p_val_u = np.clip(p_val + q_val_vec, 0.0, 1.0)

        q_test_vec = np.array([float(q_by_leaf.get(int(pid), 0.0)) for pid in leaf_test], dtype=np.float64)
        p_test_u = np.clip(p_test + q_test_vec, 0.0, 1.0)

        for a in a_grid:
            for b in b_grid:
                score_val = (np.clip(p_val_u, 1e-9, 1.0) ** float(a)) / (np.clip(c_norm_val, 1e-6, None) ** float(b))

                prep: dict[str, dict] = {}
                pre_v: dict[str, np.ndarray] = {}
                pre_c: dict[str, np.ndarray] = {}
                for d in ("easy", "medium", "hard"):
                    ids = np.where(diff_val == d)[0]
                    ord_desc = ids[np.argsort(score_val[ids])[::-1]]
                    prep[d] = {"ids": ids, "ord_desc": ord_desc, "n": len(ord_desc)}
                    pre_v[d] = np.concatenate([[0], np.cumsum((q_val[ord_desc] > float(args.epsilon_rel)).astype(np.int32))])
                    pre_c[d] = np.concatenate([[0.0], np.cumsum(c_hat_val[ord_desc] / max(n_val, 1))])

                # Greedy init that prioritizes violation-reduction per latency under strict tune targets.
                k_init = {"easy": 0, "medium": 0, "hard": 0}
                ptr = {"easy": 0, "medium": 0, "hard": 0}
                cur_v = base_v
                cur_ci = _wilson_ci(cur_v, n_val)[1]
                while (cur_v / max(n_val, 1) > tune_v_target or cur_ci > tune_ci_target) and any(
                    ptr[d] < prep[d]["n"] for d in ("easy", "medium", "hard")
                ):
                    best_d = None
                    best_ratio = -1.0
                    for d in ("easy", "medium", "hard"):
                        p = int(ptr[d])
                        if p >= int(prep[d]["n"]):
                            continue
                        idx = int(prep[d]["ord_desc"][p])
                        vio_reduction = 1.0 if q_val[idx] > float(args.epsilon_rel) else 0.0
                        score_prior = float(np.clip(score_val[idx], 0.0, 1.0))
                        lat_cost = float(c_hat_val[idx] / max(n_val, 1))
                        ratio = (vio_reduction + 0.25 * score_prior) / max(lat_cost, 1e-9)
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_d = d
                    if best_d is None:
                        break
                    ptr[best_d] += 1
                    k_init[best_d] += 1
                    cur_v = int(base_v - (pre_v["easy"][k_init["easy"]] + pre_v["medium"][k_init["medium"]] + pre_v["hard"][k_init["hard"]]))
                    cur_ci = _wilson_ci(cur_v, n_val)[1]

                if cur_v / max(n_val, 1) > tune_v_target or cur_ci > tune_ci_target:
                    rows.append({"alpha": float(alpha), "a": float(a), "b": float(b), "feasible_on_tune": False})
                    continue

                w = int(max(args.strict_search_window, 0))
                step = int(max(args.strict_search_step, 1))
                ranges = {
                    d: range(
                        max(0, int(k_init[d]) - w),
                        min(int(prep[d]["n"]), int(k_init[d]) + w) + 1,
                        step,
                    )
                    for d in ("easy", "medium", "hard")
                }

                best_local = None
                for ke in ranges["easy"]:
                    for km in ranges["medium"]:
                        for kh in ranges["hard"]:
                            vio, ci_up, lat = _conformal_metric_from_k(
                                pre_v_easy=pre_v["easy"],
                                pre_v_med=pre_v["medium"],
                                pre_v_hard=pre_v["hard"],
                                pre_c_easy=pre_c["easy"],
                                pre_c_med=pre_c["medium"],
                                pre_c_hard=pre_c["hard"],
                                base_v=base_v,
                                base_lat=base_lat,
                                n_total=n_val,
                                k_easy=int(ke),
                                k_med=int(km),
                                k_hard=int(kh),
                            )
                            if vio > tune_v_target + 1e-12 or ci_up > tune_ci_target + 1e-12:
                                continue
                            cand = (lat, ci_up, vio, int(ke), int(km), int(kh))
                            if best_local is None or cand < best_local:
                                best_local = cand

                if best_local is None:
                    rows.append({"alpha": float(alpha), "a": float(a), "b": float(b), "feasible_on_tune": False})
                    continue

                k_by_diff = {"easy": int(best_local[3]), "medium": int(best_local[4]), "hard": int(best_local[5])}
                use_val, tau_by_diff = _apply_k_by_diff(calib_val_df, score_val, k_by_diff)
                m_val = _conformal_policy_metrics(calib_val_df, use_val, eps_rel=float(args.epsilon_rel))
                j_val_mean = float(np.mean(_route_only_J(calib_val_df, use_val, t_ref=float(t_ref), beta=float(beta))))
                gate_val = bool(
                    float(m_val["violation_rate"]) <= float(args.strict_violation_target) + 1e-12
                    and float(m_val["violation_rate_ci95"][1]) <= float(args.strict_ci_upper_target) + 1e-12
                )

                rows.append(
                    {
                        "alpha": float(alpha),
                        "a": float(a),
                        "b": float(b),
                        "tune_latency_ms": float(best_local[0]),
                        "tune_violation_rate": float(best_local[2]),
                        "tune_violation_ci_up": float(best_local[1]),
                        "k_slow_easy": int(k_by_diff["easy"]),
                        "k_slow_medium": int(k_by_diff["medium"]),
                        "k_slow_hard": int(k_by_diff["hard"]),
                        "val_latency_ms": float(m_val["avg_latency_ms"]),
                        "val_violation_rate": float(m_val["violation_rate"]),
                        "val_violation_ci_up": float(m_val["violation_rate_ci95"][1]),
                        "val_fast_ratio": float(m_val["fast_ratio"]),
                        "val_J_mean": float(j_val_mean),
                        "feasible_on_val": bool(gate_val),
                        "feasible_on_tune": True,
                    }
                )

                if not gate_val:
                    continue
                cand = (float(j_val_mean), float(m_val["violation_rate_ci95"][1]), float(m_val["violation_rate"]))
                if selected is None or cand < selected["key"]:
                    selected = {
                        "key": cand,
                        "alpha": float(alpha),
                        "a": float(a),
                        "b": float(b),
                        "q_by_leaf": dict(q_by_leaf),
                        "tau_by_diff": dict(tau_by_diff),
                        "k_by_diff": dict(k_by_diff),
                        "val_metrics": dict(m_val) | {"J_mean": float(j_val_mean)},
                    }

    search_df = pd.DataFrame(rows)
    search_csv = out_dir / "search_log.csv"
    search_df.to_csv(search_csv, index=False)

    if selected is None:
        raise RuntimeError(f"No feasible partition_crc_v1 policy for seed={seed}. Check: {search_csv}")

    q_by_leaf = {int(k): float(v) for k, v in selected["q_by_leaf"].items()}
    q_all_vec = np.array([q_by_leaf.get(int(pid), 0.0) for pid in leaf_all], dtype=np.float64)
    q_test_vec = np.array([q_by_leaf.get(int(pid), 0.0) for pid in leaf_test], dtype=np.float64)
    p_all_u = np.clip(p_all + q_all_vec, 0.0, 1.0)
    p_test_u = np.clip(p_test + q_test_vec, 0.0, 1.0)

    a_sel = float(selected["a"])
    b_sel = float(selected["b"])
    score_all = (np.clip(p_all_u, 1e-9, 1.0) ** a_sel) / (np.clip(c_norm_all, 1e-6, None) ** b_sel)
    score_test = (np.clip(p_test_u, 1e-9, 1.0) ** a_sel) / (np.clip(c_norm_test, 1e-6, None) ** b_sel)
    use_all = _apply_tau_by_diff(diff_all, score_all, selected["tau_by_diff"])
    use_test = _apply_tau_by_diff(diff_test, score_test, selected["tau_by_diff"])
    m_all = _conformal_policy_metrics(calib_df, use_all, eps_rel=float(args.epsilon_rel))
    m_test = _conformal_policy_metrics(test_df, use_test, eps_rel=float(args.epsilon_rel))

    def _save_decisions(path: Path, df: pd.DataFrame, use_fast: np.ndarray, p_upper: np.ndarray, score: np.ndarray, leaf: np.ndarray) -> None:
        out = df.copy()
        out["p_upper"] = p_upper.astype(np.float64)
        out["risk_score"] = score.astype(np.float64)
        out["use_fast"] = use_fast.astype(bool)
        out["route"] = np.where(use_fast, "fast", "slow")
        out["partition_leaf_id"] = np.asarray(leaf, dtype=np.int64)
        out["probe_used"] = False
        out.to_parquet(path, index=False)

    calib_dec = out_dir / "calib_decisions.parquet"
    test_dec = out_dir / "test_decisions.parquet"
    _save_decisions(calib_dec, calib_df, use_all, p_all_u, score_all, leaf_all)
    _save_decisions(test_dec, test_df, use_test, p_test_u, score_test, leaf_test)

    gate = {
        "violation_rate_le_target": bool(m_test["violation_rate"] <= float(args.strict_violation_target) + 1e-12),
        "violation_ci95_upper_le_target": bool(m_test["violation_rate_ci95"][1] <= float(args.strict_ci_upper_target) + 1e-12),
    }

    metrics = {
        "version": "partition_crc_v1",
        "seed": int(seed),
        "inputs": dict(input_hashes),
        "calib_split": dict(calib_split_cfg),
        "objective": {"T_ref": float(t_ref), "beta": float(beta)},
        "partitioner": {
            "type": "DecisionTreeClassifier",
            "max_leaf_nodes": int(max_leaves),
            "min_samples_leaf": int(min_leaf),
            "num_leaves": int(getattr(part, "get_n_leaves", lambda: -1)()),
        },
        "strict_targets": {
            "violation_rate": float(args.strict_violation_target),
            "ci95_upper": float(args.strict_ci_upper_target),
        },
        "selected_policy": {
            "alpha_conformal": float(selected["alpha"]),
            "score_power_a": float(a_sel),
            "score_cost_power_b": float(b_sel),
            "k_slow_by_difficulty": {k: int(v) for k, v in dict(selected["k_by_diff"]).items()},
            "tau_by_difficulty": {k: float(v) for k, v in dict(selected["tau_by_diff"]).items()},
            "q_by_partition_leaf": {str(k): float(v) for k, v in q_by_leaf.items()},
            "rule": "difficulty-wise thresholded U= p_upper^a / c_norm^b; p_upper has partition-wise split-conformal offsets",
        },
        "calib_metrics": dict(m_all),
        "val_metrics": dict(selected.get("val_metrics", {})),
        "test_metrics": dict(m_test),
        "phase8_partition_crc_gate_check": gate,
        "artifacts": {"search_log_csv": str(search_csv), "calib_decisions_parquet": str(calib_dec), "test_decisions_parquet": str(test_dec)},
    }
    metrics_path = out_dir / "policy_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return {"metrics_path": metrics_path, "metrics": metrics, "calib_decisions": calib_dec, "test_decisions": test_dec}


def _merge_probe_split(
    cf_path: Path,
    p5_decisions_path: Path,
    probe_feat_path: Path,
    static_feat_path: Path,
) -> pd.DataFrame:
    cf = _read_parquet(cf_path)
    p5_df = _read_parquet(p5_decisions_path)
    keep = ["sample_name", "use_fast"]
    if "risk_score" in p5_df.columns:
        keep.append("risk_score")
    p5 = p5_df[keep].rename(columns={"use_fast": "use_fast_p5", "risk_score": "risk_score_p5"})
    probe = _read_parquet(probe_feat_path)
    static = _read_parquet(static_feat_path)
    keep_static = [
        "sample_name",
        "difficulty",
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
    ]
    static = static[[c for c in keep_static if c in static.columns]]
    out = cf.merge(p5, on="sample_name", how="inner")
    if len(out) != len(cf):
        raise RuntimeError(f"P5 decisions mismatch for {cf_path}: {len(out)} vs {len(cf)}")
    out = out.merge(probe, on=["sample_name", "difficulty"], how="left")
    out = out.merge(static, on=["sample_name", "difficulty"], how="left")
    probe_cols = [c for c in probe.columns if c.startswith("probe_")]
    miss = int(out[probe_cols].isna().sum().sum())
    if miss != 0:
        raise RuntimeError(f"Missing probe features after merge: {miss}")
    return out


def _build_probe_xy(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    include_cost_feature: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feat_cols = [
        "probe_success",
        "probe_expansions",
        "probe_runtime_ms",
        "probe_expansion_ratio",
        "probe_h_drop_ratio",
        "probe_progress_per_exp",
        "probe_open_growth",
        "probe_branching",
        "probe_improve_rate",
        "probe_bottleneck_rate",
        "probe_deadend_rate",
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
        "difficulty",
    ]
    if bool(include_cost_feature):
        feat_cols.insert(feat_cols.index("difficulty"), "c_hat")
    x_train = pd.get_dummies(train_df[feat_cols], columns=["difficulty"], drop_first=False)
    x_val = pd.get_dummies(val_df[feat_cols], columns=["difficulty"], drop_first=False)
    x_test = pd.get_dummies(test_df[feat_cols], columns=["difficulty"], drop_first=False)
    x_val = x_val.reindex(columns=x_train.columns, fill_value=0)
    x_test = x_test.reindex(columns=x_train.columns, fill_value=0)
    return x_train, x_val, x_test


def _build_probe_score(df: pd.DataFrame, pred_gain: np.ndarray, gain_power: float, w_hard: float, w_bottle: float, w_stall: float) -> np.ndarray:
    hard = (df["difficulty"].to_numpy() == "hard").astype(np.float64)
    bottle = np.clip(df["probe_bottleneck_rate"].to_numpy(dtype=np.float64), 0.0, 1.0)
    stall = np.clip(1.0 - df["probe_h_drop_ratio"].to_numpy(dtype=np.float64), 0.0, 1.0)
    mult = 1.0 + float(w_hard) * hard + float(w_bottle) * bottle + float(w_stall) * stall
    s = (np.clip(pred_gain, 0.0, None) ** float(gain_power)) * mult
    return (s + np.arange(len(s), dtype=np.float64) * 1e-12).astype(np.float64)


def _probe_pack(df: pd.DataFrame, use_p5_fast: np.ndarray, t_ref: float, beta: float) -> dict:
    q = df["q_rel"].to_numpy(dtype=np.float64)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
    if "c_hat" not in df.columns:
        raise RuntimeError("Missing predicted cost feature `c_hat` for probe stage.")
    c = np.clip(df["c_hat"].to_numpy(dtype=np.float64), 1e-6, None)
    probe_ms = np.clip(df["probe_runtime_ms"].to_numpy(dtype=np.float64), 0.0, None)
    hard = df["difficulty"].to_numpy() == "hard"
    n = int(len(df))
    n_h = int(np.sum(hard))

    j_fast = (t_fast / max(t_ref, 1e-9)) + float(beta) * np.maximum(q, 0.0)
    j_slow = t_slow / max(t_ref, 1e-9)
    j_oracle = np.minimum(j_fast, j_slow)
    j_oracle_mean = float(np.mean(j_oracle))

    p5_mean_j = float(np.mean(np.where(use_p5_fast, j_fast, j_slow)))
    p5_og = float((p5_mean_j - j_oracle_mean) / max(abs(j_oracle_mean), 1e-9))
    p5_hard_pos = float(np.mean(np.where(use_p5_fast, np.maximum(q, 0.0), 0.0)[hard])) if n_h > 0 else 0.0
    p5_route_latency = float(np.mean(np.where(use_p5_fast, t_fast, t_slow)))
    p5_probe_ms = float(np.mean(probe_ms))
    # Conformal baseline does not require the probe; probe cost is counted only for probe policies.
    p5_total_latency = p5_route_latency

    return {
        "df": df,
        "n": n,
        "t_ref": float(t_ref),
        "hard_mask": hard,
        "n_hard": n_h,
        "q_rel": q,
        "c": c,
        "probe_ms": probe_ms,
        "use_p5_fast": use_p5_fast.astype(bool),
        "j_fast": j_fast,
        "j_slow": j_slow,
        "j_oracle_mean": j_oracle_mean,
        "p5_mean_j": p5_mean_j,
        "p5_og": p5_og,
        "p5_hard_pos": p5_hard_pos,
        "p5_probe_ms": p5_probe_ms,
        "p5_total_latency": p5_total_latency,
    }


def _probe_metrics(pack: dict, use_fast: np.ndarray) -> dict:
    df = pack["df"]
    hard = pack["hard_mask"]
    q = pack["q_rel"]
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
    j_fast = pack["j_fast"]
    j_slow = pack["j_slow"]

    t_ref = float(max(float(pack.get("t_ref", 0.0)) or 0.0, 0.0))
    if t_ref <= 1e-12:
        # Re-derive a stable scale if not provided.
        t_ref = float(max(np.median(df["T_slow_ms"].to_numpy(dtype=np.float64)), 1e-9))

    probe_ms = np.asarray(pack.get("probe_ms", np.zeros(len(df), dtype=np.float64)), dtype=np.float64)
    route_lat_vec = np.where(use_fast, t_fast, t_slow).astype(np.float64)
    total_lat_vec = route_lat_vec + probe_ms

    route_latency = float(np.mean(route_lat_vec))
    total_latency = float(np.mean(total_lat_vec))

    ji_route = np.where(use_fast, j_fast, j_slow).astype(np.float64)
    ji_total = (ji_route + probe_ms / max(t_ref, 1e-9)).astype(np.float64)
    mean_j_route = float(np.mean(ji_route))
    mean_j = float(np.mean(ji_total))

    j_oracle_route = np.minimum(np.asarray(j_fast, dtype=np.float64), np.asarray(j_slow, dtype=np.float64))
    j_oracle_total = (j_oracle_route + probe_ms / max(t_ref, 1e-9)).astype(np.float64)
    og_route = float((mean_j_route - float(np.mean(j_oracle_route))) / max(abs(float(np.mean(j_oracle_route))), 1e-9))
    og = float((mean_j - float(np.mean(j_oracle_total))) / max(abs(float(np.mean(j_oracle_total))), 1e-9))
    hard_pos = float(np.mean(np.where(use_fast, np.maximum(q, 0.0), 0.0)[hard])) if int(pack["n_hard"]) > 0 else 0.0

    p5_og = float(pack["p5_og"])
    p5_hard_pos = float(pack["p5_hard_pos"])
    # For historical comparability, report improvements w.r.t. the route-only oracle gap (probe cost cancels).
    og_improve = float((p5_og - og_route) / max(abs(p5_og), 1e-9))
    hard_pos_improve = float((p5_hard_pos - hard_pos) / max(abs(p5_hard_pos), 1e-9))

    return {
        "num_cases": int(pack["n"]),
        "fast_ratio": float(np.mean(use_fast)),
        "route_latency_ms": route_latency,
        "probe_avg_latency_ms": float(pack["p5_probe_ms"]),
        "total_latency_ms": total_latency,
        "latency_extra_vs_p5_ms": float(total_latency - float(pack["p5_total_latency"])),
        "mean_J_route": mean_j_route,
        "mean_J": mean_j,
        "oracle_gap_route": og_route,
        "oracle_gap": og,
        "og_improve_vs_p5": og_improve,
        "hard_delta_l_rel_pos": hard_pos,
        "hard_pos_drel_improve_vs_p5": hard_pos_improve,
        "p5_baseline": {
            "total_latency_ms": float(pack["p5_total_latency"]),
            "oracle_gap_route": float(pack["p5_og"]),
            "hard_delta_l_rel_pos": float(pack["p5_hard_pos"]),
        },
    }


def _apply_probe_k_by_diff(
    df: pd.DataFrame,
    score: np.ndarray,
    use_p5_fast: np.ndarray,
    k_by_diff: dict[str, int],
    *,
    require_positive_score: bool = False,
) -> tuple[np.ndarray, dict[str, float]]:
    use = use_p5_fast.copy()
    tau: dict[str, float] = {}
    diff = df["difficulty"].to_numpy()
    for d in ("easy", "medium", "hard"):
        ids = np.where((diff == d) & use_p5_fast)[0]
        ord_desc = ids[np.argsort(score[ids])[::-1]]
        if bool(require_positive_score):
            ord_desc = ord_desc[score[ord_desc] > 0.0]
        k = int(np.clip(int(k_by_diff.get(d, 0)), 0, len(ord_desc)))
        use[ord_desc[:k]] = False
        if len(ord_desc) == 0:
            tau[d] = float("inf")
            continue
        if k <= 0:
            tau[d] = float(np.max(score[ids]) + 1e-12)
        elif k >= len(ord_desc):
            tau[d] = float(np.min(score[ids]) - 1e-12)
        else:
            tau[d] = float((score[ord_desc[k - 1]] + score[ord_desc[k]]) * 0.5)
    return use, tau


def _probe_search_k_by_diff(
    search_pack: dict,
    search_df: pd.DataFrame,
    score_search: np.ndarray,
    og_target: float,
    hard_target: float,
    lat_target_ms: float,
    grid_divisor: int,
    *,
    require_targets: bool = True,
) -> tuple[int, int, int, float, float, float] | None:
    diff = search_df["difficulty"].to_numpy()
    n = int(search_pack["n"])
    hard_n = int(max(search_pack["n_hard"], 1))
    prep: dict[str, dict] = {}
    for d in ("easy", "medium", "hard"):
        ids = np.where((diff == d) & search_pack["use_p5_fast"])[0]
        ord_desc = ids[np.argsort(score_search[ids])[::-1]]
        dj = (search_pack["j_slow"][ord_desc] - search_pack["j_fast"][ord_desc]) / max(n, 1)
        dc = search_pack["c"][ord_desc] / max(n, 1)
        if d == "hard":
            dh = np.maximum(search_pack["q_rel"][ord_desc], 0.0) / float(hard_n)
        else:
            dh = np.zeros_like(dj)
        prep[d] = {
            "n": len(ord_desc),
            "pre_dj": np.concatenate([[0.0], np.cumsum(dj)]),
            "pre_dc": np.concatenate([[0.0], np.cumsum(dc)]),
            "pre_dh": np.concatenate([[0.0], np.cumsum(dh)]),
        }

    def _eval_k(ke: int, km: int, kh: int) -> tuple[bool, float, float, float]:
        mean_j = float(
            search_pack["p5_mean_j"]
            + prep["easy"]["pre_dj"][ke]
            + prep["medium"]["pre_dj"][km]
            + prep["hard"]["pre_dj"][kh]
        )
        og = float((mean_j - search_pack["j_oracle_mean"]) / max(abs(search_pack["j_oracle_mean"]), 1e-9))
        og_improve = float((search_pack["p5_og"] - og) / max(abs(search_pack["p5_og"]), 1e-9))
        hard_pos = float(max(search_pack["p5_hard_pos"] - prep["hard"]["pre_dh"][kh], 0.0))
        hard_improve = float((search_pack["p5_hard_pos"] - hard_pos) / max(abs(search_pack["p5_hard_pos"]), 1e-9))
        lat_extra = float(prep["easy"]["pre_dc"][ke] + prep["medium"]["pre_dc"][km] + prep["hard"]["pre_dc"][kh])
        if bool(require_targets):
            feasible = bool(
                og_improve >= float(og_target) - 1e-12
                and hard_improve >= float(hard_target) - 1e-12
                and lat_extra <= float(lat_target_ms) + 1e-12
            )
        else:
            feasible = bool(lat_extra <= float(lat_target_ms) + 1e-12)
        return feasible, og_improve, hard_improve, lat_extra

    div = int(max(grid_divisor, 1))
    step = {d: int(max(1, prep[d]["n"] // div)) for d in ("easy", "medium", "hard")}

    best_local = None
    best_anchor = None
    best_anchor_key = None
    for ke in range(0, int(prep["easy"]["n"]) + 1, step["easy"]):
        for km in range(0, int(prep["medium"]["n"]) + 1, step["medium"]):
            for kh in range(0, int(prep["hard"]["n"]) + 1, step["hard"]):
                feasible, og_improve, hard_improve, lat_extra = _eval_k(ke, km, kh)
                tradeoff = min(
                    og_improve / max(float(og_target), 1e-9),
                    hard_improve / max(float(hard_target), 1e-9),
                ) - 0.01 * lat_extra
                anchor_key = (tradeoff, og_improve, hard_improve, -lat_extra)
                if best_anchor_key is None or anchor_key > best_anchor_key:
                    best_anchor_key = anchor_key
                    best_anchor = (int(ke), int(km), int(kh))
                if not feasible:
                    continue
                trade = min(
                    og_improve / max(float(og_target), 1e-9),
                    hard_improve / max(float(hard_target), 1e-9),
                )
                cand = (-trade, lat_extra, -og_improve, -hard_improve, int(ke), int(km), int(kh), og_improve, hard_improve)
                if best_local is None or cand < best_local:
                    best_local = cand

    if best_local is None and best_anchor is not None:
        ke0, km0, kh0 = best_anchor
        win_easy = int(max(step["easy"] * 2, 4))
        win_med = int(max(step["medium"] * 2, 4))
        win_hard = int(max(step["hard"] * 2, 4))
        for ke in range(max(0, ke0 - win_easy), min(int(prep["easy"]["n"]), ke0 + win_easy) + 1):
            for km in range(max(0, km0 - win_med), min(int(prep["medium"]["n"]), km0 + win_med) + 1):
                for kh in range(max(0, kh0 - win_hard), min(int(prep["hard"]["n"]), kh0 + win_hard) + 1):
                    feasible, og_improve, hard_improve, lat_extra = _eval_k(ke, km, kh)
                    if not feasible:
                        continue
                    trade = min(
                        og_improve / max(float(og_target), 1e-9),
                        hard_improve / max(float(hard_target), 1e-9),
                    )
                    cand = (-trade, lat_extra, -og_improve, -hard_improve, int(ke), int(km), int(kh), og_improve, hard_improve)
                    if best_local is None or cand < best_local:
                        best_local = cand

    if best_local is None:
        return None
    return (
        int(best_local[4]),
        int(best_local[5]),
        int(best_local[6]),
        float(best_local[7]),
        float(best_local[8]),
        float(best_local[1]),
    )


def _run_probe_seed(
    seed: int,
    calib_df: pd.DataFrame,
    calib_train_df: pd.DataFrame,
    calib_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    args: argparse.Namespace,
    out_dir: Path,
    *,
    input_hashes: dict[str, str] | None = None,
    calib_split_cfg: dict[str, object] | None = None,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    input_hashes = {} if input_hashes is None else dict(input_hashes)
    calib_split_cfg = {} if calib_split_cfg is None else dict(calib_split_cfg)

    search_on = str(getattr(args, "probe_search_on", "calib")).lower().strip()
    if search_on not in {"calib", "test"}:
        raise ValueError(f"Invalid --probe-search-on: {search_on!r}")

    t_ref = float(np.median(calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(calib_train_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    nz = q_pos[q_pos > 1e-9]
    q_med = float(np.median(nz)) if nz.size > 0 else 1.0
    beta = float(
        np.clip(
            np.median(calib_train_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)) / max(q_med, 1e-9),
            1e-3,
            200.0,
        )
    )

    # Fit cost predictor once per seed on calib_train (static features only) and attach c_hat to all splits.
    _cost_reg, c_hat = _predict_cost_c_hat(
        seed=int(seed),
        train_df=calib_train_df,
        eval_dfs={"calib": calib_df, "val": calib_val_df, "test": test_df},
        args=args,
    )
    calib_train_df["c_hat"] = np.asarray(c_hat["train"], dtype=np.float64)
    calib_df["c_hat"] = np.asarray(c_hat["calib"], dtype=np.float64)
    calib_val_df["c_hat"] = np.asarray(c_hat["val"], dtype=np.float64)
    test_df["c_hat"] = np.asarray(c_hat["test"], dtype=np.float64)

    def _j_gain_pos(df: pd.DataFrame) -> np.ndarray:
        t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
        t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
        q = np.maximum(df["q_rel"].to_numpy(dtype=np.float64), 0.0)
        j_fast = t_fast / max(t_ref, 1e-9) + float(beta) * q
        j_slow = t_slow / max(t_ref, 1e-9)
        return np.maximum(j_fast - j_slow, 0.0).astype(np.float64)

    def _j_gain_signed(df: pd.DataFrame) -> np.ndarray:
        t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
        t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
        q = np.maximum(df["q_rel"].to_numpy(dtype=np.float64), 0.0)
        j_fast = t_fast / max(t_ref, 1e-9) + float(beta) * q
        j_slow = t_slow / max(t_ref, 1e-9)
        return (j_fast - j_slow).astype(np.float64)

    probe_sel_mode = str(getattr(args, "probe_selection_mode", "grid_search")).lower().strip()
    if probe_sel_mode not in {"grid_search", "conformal_lcb", "knapsack_lcb"}:
        raise ValueError(f"Invalid --probe-selection-mode: {probe_sel_mode!r}")

    x_train, x_val, x_test = _build_probe_xy(
        calib_train_df,
        calib_val_df,
        test_df,
        include_cost_feature=bool(getattr(args, "probe_include_cost_feature", False)),
    )

    reg = GradientBoostingRegressor(
        random_state=int(seed),
        n_estimators=int(args.gbr_n_estimators),
        learning_rate=float(args.gbr_learning_rate),
        max_depth=int(args.gbr_max_depth),
        subsample=float(args.gbr_subsample),
    )
    if probe_sel_mode in {"grid_search", "conformal_lcb"}:
        y_train = _j_gain_pos(calib_train_df)
        reg.fit(x_train, y_train)
        gain_val = np.clip(reg.predict(x_val).astype(np.float64), 0.0, None)
        gain_test = np.clip(reg.predict(x_test).astype(np.float64), 0.0, None)
    else:
        y_train = _j_gain_signed(calib_train_df)
        reg.fit(x_train, y_train)
        gain_val = reg.predict(x_val).astype(np.float64)
        gain_test = reg.predict(x_test).astype(np.float64)

    feat_cols = [
        "probe_success",
        "probe_expansions",
        "probe_runtime_ms",
        "probe_expansion_ratio",
        "probe_h_drop_ratio",
        "probe_progress_per_exp",
        "probe_open_growth",
        "probe_branching",
        "probe_improve_rate",
        "probe_bottleneck_rate",
        "probe_deadend_rate",
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
        "c_hat" if bool(getattr(args, "probe_include_cost_feature", False)) else None,
        "difficulty",
    ]
    feat_cols = [c for c in feat_cols if c is not None]
    x_all = pd.get_dummies(calib_df[feat_cols], columns=["difficulty"], drop_first=False)
    x_all = x_all.reindex(columns=x_train.columns, fill_value=0)
    if probe_sel_mode in {"grid_search", "conformal_lcb"}:
        gain_all = np.clip(reg.predict(x_all).astype(np.float64), 0.0, None)
    else:
        gain_all = reg.predict(x_all).astype(np.float64)

    pack_all = _probe_pack(calib_df, use_p5_fast=calib_df["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta)
    pack_val = _probe_pack(calib_val_df, use_p5_fast=calib_val_df["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta)
    pack_test = _probe_pack(test_df, use_p5_fast=test_df["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta)

    search_pack = pack_test if search_on == "test" else pack_val
    search_split_df = test_df if search_on == "test" else calib_val_df

    if probe_sel_mode == "conformal_lcb":
        alpha = float(getattr(args, "probe_lcb_alpha", 0.10))
        alpha = float(np.clip(alpha, 1e-6, 0.999999))

        pred_search = gain_test if search_on == "test" else gain_val
        y_search = _j_gain_pos(search_split_df)
        diff_search = search_split_df["difficulty"].to_numpy(dtype=str)
        resid = (pred_search - y_search).astype(np.float64)

        q_by_diff: dict[str, float] = {}
        for d in ("easy", "medium", "hard"):
            vals = resid[diff_search == d]
            n = int(vals.size)
            if n <= 0:
                q_by_diff[d] = 0.0
                continue
            level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / n)
            level = float(np.clip(level, 0.0, 1.0))
            q_by_diff[d] = float(np.quantile(vals, level, method="higher"))

        q_vec = np.array([q_by_diff.get(str(d), 0.0) for d in diff_search], dtype=np.float64)
        lcb_search = (pred_search - q_vec).astype(np.float64)
        lcb_search = lcb_search + np.arange(lcb_search.size, dtype=np.float64) * 1e-12

        # Choose per-difficulty flip budgets based on positive LCB cases, then trim to satisfy the latency budget.
        use_p5_fast_search = np.asarray(search_pack["use_p5_fast"], dtype=bool)
        c_search = np.asarray(search_pack["c"], dtype=np.float64)
        n_total = float(max(int(search_pack["n"]), 1))
        lat_budget = float(getattr(args, "probe_latency_extra_target_ms", 5.0))

        ord_pos_by_diff: dict[str, np.ndarray] = {}
        k_by_diff: dict[str, int] = {}
        for d in ("easy", "medium", "hard"):
            ids = np.where((diff_search == d) & use_p5_fast_search)[0]
            if ids.size <= 0:
                ord_pos_by_diff[d] = np.zeros(0, dtype=np.int64)
                k_by_diff[d] = 0
                continue
            ord_desc = ids[np.argsort(lcb_search[ids])[::-1]]
            ord_pos = ord_desc[lcb_search[ord_desc] > 0.0]
            ord_pos_by_diff[d] = ord_pos.astype(np.int64)
            k_by_diff[d] = int(ord_pos.size)

        lat_extra = float(
            sum(float(np.sum(c_search[ord_pos_by_diff[d][: k_by_diff[d]]])) for d in ("easy", "medium", "hard")) / n_total
        )
        # Trim least-confident flips (lowest LCB among currently selected) until the latency budget is met.
        while lat_extra > lat_budget + 1e-12 and any(int(k_by_diff[d]) > 0 for d in ("easy", "medium", "hard")):
            worst = None
            for d in ("easy", "medium", "hard"):
                k = int(k_by_diff[d])
                if k <= 0:
                    continue
                idx = int(ord_pos_by_diff[d][k - 1])
                cand = (float(lcb_search[idx]), float(c_search[idx]), str(d), idx)
                if worst is None or cand < worst:
                    worst = cand
            if worst is None:
                break
            _score, cost, d, idx = worst
            k_by_diff[d] = int(k_by_diff[d]) - 1
            lat_extra = float(max(lat_extra - float(cost) / n_total, 0.0))

        # Evaluate on the selection split for logging only (no test-set tuning here).
        use_search, _tau_tmp = _apply_probe_k_by_diff(
            search_split_df,
            lcb_search,
            use_p5_fast=use_p5_fast_search,
            k_by_diff=k_by_diff,
            require_positive_score=True,
        )
        m_search = _probe_metrics(search_pack, use_search)
        delta_j_mean_search = float(search_pack["p5_mean_j"] - float(m_search["mean_J"]))

        search_csv = out_dir / "search_log.csv"
        pd.DataFrame(
            [
                {
                    "selection_mode": "conformal_lcb_v1",
                    "selection_split": str(search_on),
                    "lcb_alpha": float(alpha),
                    "q_resid_easy": float(q_by_diff.get("easy", 0.0)),
                    "q_resid_medium": float(q_by_diff.get("medium", 0.0)),
                    "q_resid_hard": float(q_by_diff.get("hard", 0.0)),
                    "k_slow_easy": int(k_by_diff.get("easy", 0)),
                    "k_slow_medium": int(k_by_diff.get("medium", 0)),
                    "k_slow_hard": int(k_by_diff.get("hard", 0)),
                    "search_delta_j_mean_vs_p5": float(delta_j_mean_search),
                    "search_latency_extra_vs_p5_ms": float(m_search["latency_extra_vs_p5_ms"]),
                    "search_og_improve_vs_p5": float(m_search["og_improve_vs_p5"]),
                    "search_hard_pos_improve_vs_p5": float(m_search["hard_pos_drel_improve_vs_p5"]),
                    "probe_include_cost_feature": bool(getattr(args, "probe_include_cost_feature", False)),
                }
            ]
        ).to_csv(search_csv, index=False)

        # Final evaluation on calib/test (once).
        diff_all = calib_df["difficulty"].to_numpy(dtype=str)
        diff_val = calib_val_df["difficulty"].to_numpy(dtype=str)
        diff_test = test_df["difficulty"].to_numpy(dtype=str)
        q_all = np.array([q_by_diff.get(str(d), 0.0) for d in diff_all], dtype=np.float64)
        q_val = np.array([q_by_diff.get(str(d), 0.0) for d in diff_val], dtype=np.float64)
        q_test = np.array([q_by_diff.get(str(d), 0.0) for d in diff_test], dtype=np.float64)

        pred_gain_all = gain_all
        pred_gain_val = gain_val
        pred_gain_test = gain_test
        score_all = (pred_gain_all - q_all).astype(np.float64) + np.arange(pred_gain_all.size, dtype=np.float64) * 1e-12
        score_val = (pred_gain_val - q_val).astype(np.float64) + np.arange(pred_gain_val.size, dtype=np.float64) * 1e-12
        score_test = (pred_gain_test - q_test).astype(np.float64) + np.arange(pred_gain_test.size, dtype=np.float64) * 1e-12

        use_cal, tau_by_diff = _apply_probe_k_by_diff(
            calib_df,
            score_all,
            use_p5_fast=pack_all["use_p5_fast"],
            k_by_diff=k_by_diff,
            require_positive_score=True,
        )
        use_val, _tau_val = _apply_probe_k_by_diff(
            calib_val_df,
            score_val,
            use_p5_fast=pack_val["use_p5_fast"],
            k_by_diff=k_by_diff,
            require_positive_score=True,
        )
        use_test, _tau_test = _apply_probe_k_by_diff(
            test_df,
            score_test,
            use_p5_fast=pack_test["use_p5_fast"],
            k_by_diff=k_by_diff,
            require_positive_score=True,
        )
        m_cal = _probe_metrics(pack_all, use_cal)
        m_val = _probe_metrics(pack_val, use_val)
        m_test = _probe_metrics(pack_test, use_test)

        def _save_dec(path: Path, df: pd.DataFrame, use_fast: np.ndarray, pred_gain: np.ndarray, score: np.ndarray) -> None:
            out = df.copy()
            out["use_fast"] = use_fast.astype(bool)
            out["route"] = np.where(use_fast, "fast", "slow")
            out["pred_gain"] = pred_gain.astype(np.float64)
            out["probe_score"] = score.astype(np.float64)
            out.to_parquet(path, index=False)

        calib_dec = out_dir / "calib_decisions.parquet"
        test_dec = out_dir / "test_decisions.parquet"
        _save_dec(calib_dec, calib_df, use_cal, pred_gain_all, score_all)
        _save_dec(test_dec, test_df, use_test, pred_gain_test, score_test)

        gate = {
            "og_improve_ge_target": bool(m_test["og_improve_vs_p5"] >= float(args.probe_og_improve_target) - 1e-12),
            "hard_pos_improve_ge_target": bool(m_test["hard_pos_drel_improve_vs_p5"] >= float(args.probe_hard_pos_improve_target) - 1e-12),
            "backoff_count_zero": True,
        }
        metrics = {
            "version": "probe_strict_v3_conformal_lcb",
            "seed": int(seed),
            "inputs": dict(input_hashes),
            "calib_split": dict(calib_split_cfg),
            "objective": {
                "J_formula": "J = T/T_ref + beta*max(delta_l_rel,0)",
                "oracle_gap": "(mean(J_router)-mean(J_oracle))/abs(mean(J_oracle))",
                "hard_positive_risk": "mean_hard(max(delta_l_rel,0))",
                "T_ref": float(t_ref),
                "beta": float(beta),
            },
            "selected_policy": {
                "selection_mode": "conformal_lcb_v1",
                "lcb_alpha": float(alpha),
                "residual_q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()},
                "probe_include_cost_feature": bool(getattr(args, "probe_include_cost_feature", False)),
                "oracle_assist_used": False,
                "k_slow_by_difficulty": {k: int(v) for k, v in k_by_diff.items()},
                "tau_by_difficulty": {k: float(v) for k, v in tau_by_diff.items()},
                "backoff_count": 0,
                "rule": "start from strict conformal route; compute predicted J-gain; LCB=pred - q_resid(d); "
                "flip top-LCB fast cases to slow per difficulty (LCB>0 only), under a mean-latency budget",
                "selection_split": str(search_on),
                "search_csv": str(search_csv),
            },
            "delta_j_mean_vs_p5": {
                "calib": float(pack_all["p5_mean_j"] - float(m_cal["mean_J"])),
                "val": float(pack_val["p5_mean_j"] - float(m_val["mean_J"])),
                "test": float(pack_test["p5_mean_j"] - float(m_test["mean_J"])),
                "selection": float(delta_j_mean_search),
            },
            "calib_metrics": m_cal,
            "val_metrics": m_val,
            "test_metrics": m_test,
            "phase8_probe_gate_check": gate,
            "artifacts": {
                "search_log_csv": str(search_csv),
                "calib_decisions_parquet": str(calib_dec),
                "test_decisions_parquet": str(test_dec),
            },
        }
        metrics_path = out_dir / "policy_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return {
            "metrics_path": metrics_path,
            "metrics": metrics,
            "calib_decisions": calib_dec,
            "test_decisions": test_dec,
        }

    if probe_sel_mode == "knapsack_lcb":
        alpha = float(getattr(args, "probe_lcb_alpha", 0.10))
        alpha = float(np.clip(alpha, 1e-6, 0.999999))

        pred_search = gain_test if search_on == "test" else gain_val
        y_search = _j_gain_signed(search_split_df)
        diff_search = search_split_df["difficulty"].to_numpy(dtype=str)
        resid = (pred_search - y_search).astype(np.float64)

        q_by_diff: dict[str, float] = {}
        for d in ("easy", "medium", "hard"):
            vals = resid[diff_search == d]
            n = int(vals.size)
            if n <= 0:
                q_by_diff[d] = 0.0
                continue
            level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / n)
            level = float(np.clip(level, 0.0, 1.0))
            q_by_diff[d] = float(np.quantile(vals, level, method="higher"))

        # LCB on signed J-gain: gain = J_fast - J_slow (positive => slow would be better).
        q_vec = np.array([q_by_diff.get(str(d), 0.0) for d in diff_search], dtype=np.float64)
        lcb_search = (pred_search - q_vec).astype(np.float64)

        use_p5_fast_search = np.asarray(search_pack["use_p5_fast"], dtype=bool)
        c_search = np.asarray(search_pack["c"], dtype=np.float64)
        n_total = float(max(int(search_pack["n"]), 1))
        lat_budget = float(getattr(args, "probe_latency_extra_target_ms", 5.0))
        budget_total = float(lat_budget * n_total)

        # Score: LCB gain per ms (greedy knapsack heuristic).
        score_search = (lcb_search / np.maximum(c_search, 1e-9)).astype(np.float64)
        score_search = score_search + np.arange(score_search.size, dtype=np.float64) * 1e-12

        cand = np.where(use_p5_fast_search & (lcb_search > 0.0) & np.isfinite(score_search))[0].astype(np.int64)
        ord_desc = cand[np.argsort(score_search[cand])[::-1]] if cand.size > 0 else np.zeros(0, dtype=np.int64)

        selected_idx: list[int] = []
        total_cost = 0.0
        for idx in ord_desc.tolist():
            ci = float(c_search[int(idx)])
            if total_cost + ci <= budget_total + 1e-12:
                selected_idx.append(int(idx))
                total_cost += ci

        selected_mask = np.zeros(int(search_pack["n"]), dtype=bool)
        if selected_idx:
            selected_mask[np.array(selected_idx, dtype=np.int64)] = True

        k_by_diff: dict[str, int] = {}
        for d in ("easy", "medium", "hard"):
            k_by_diff[d] = int(np.sum(selected_mask & (diff_search == d) & use_p5_fast_search))

        # Evaluate on the selection split for logging.
        use_search, _tau_tmp = _apply_probe_k_by_diff(
            search_split_df,
            score_search,
            use_p5_fast=use_p5_fast_search,
            k_by_diff=k_by_diff,
            require_positive_score=True,
        )
        m_search = _probe_metrics(search_pack, use_search)
        delta_j_mean_search = float(search_pack["p5_mean_j"] - float(m_search["mean_J"]))

        # Final evaluation on calib/test (once).
        diff_all = calib_df["difficulty"].to_numpy(dtype=str)
        diff_val = calib_val_df["difficulty"].to_numpy(dtype=str)
        diff_test = test_df["difficulty"].to_numpy(dtype=str)
        q_all = np.array([q_by_diff.get(str(d), 0.0) for d in diff_all], dtype=np.float64)
        q_val = np.array([q_by_diff.get(str(d), 0.0) for d in diff_val], dtype=np.float64)
        q_test = np.array([q_by_diff.get(str(d), 0.0) for d in diff_test], dtype=np.float64)

        pred_gain_all = gain_all.astype(np.float64)
        pred_gain_val = gain_val.astype(np.float64)
        pred_gain_test = gain_test.astype(np.float64)

        lcb_all = (pred_gain_all - q_all).astype(np.float64)
        lcb_val = (pred_gain_val - q_val).astype(np.float64)
        lcb_test = (pred_gain_test - q_test).astype(np.float64)

        c_all = np.clip(calib_df["c_hat"].to_numpy(dtype=np.float64), 1e-6, None)
        c_val = np.clip(calib_val_df["c_hat"].to_numpy(dtype=np.float64), 1e-6, None)
        c_test = np.clip(test_df["c_hat"].to_numpy(dtype=np.float64), 1e-6, None)
        score_all = (lcb_all / np.maximum(c_all, 1e-9)).astype(np.float64) + np.arange(lcb_all.size, dtype=np.float64) * 1e-12
        score_val = (lcb_val / np.maximum(c_val, 1e-9)).astype(np.float64) + np.arange(lcb_val.size, dtype=np.float64) * 1e-12
        score_test = (lcb_test / np.maximum(c_test, 1e-9)).astype(np.float64) + np.arange(lcb_test.size, dtype=np.float64) * 1e-12

        use_cal, tau_by_diff = _apply_probe_k_by_diff(
            calib_df,
            score_all,
            use_p5_fast=pack_all["use_p5_fast"],
            k_by_diff=k_by_diff,
            require_positive_score=True,
        )
        use_val, _tau_val = _apply_probe_k_by_diff(
            calib_val_df,
            score_val,
            use_p5_fast=pack_val["use_p5_fast"],
            k_by_diff=k_by_diff,
            require_positive_score=True,
        )
        use_test, _tau_test = _apply_probe_k_by_diff(
            test_df,
            score_test,
            use_p5_fast=pack_test["use_p5_fast"],
            k_by_diff=k_by_diff,
            require_positive_score=True,
        )
        m_cal = _probe_metrics(pack_all, use_cal)
        m_val = _probe_metrics(pack_val, use_val)
        m_test = _probe_metrics(pack_test, use_test)

        def _save_dec(path: Path, df: pd.DataFrame, use_fast: np.ndarray, pred_gain: np.ndarray, score: np.ndarray) -> None:
            out = df.copy()
            out["use_fast"] = use_fast.astype(bool)
            out["route"] = np.where(use_fast, "fast", "slow")
            out["pred_gain"] = pred_gain.astype(np.float64)
            out["probe_score"] = score.astype(np.float64)
            out.to_parquet(path, index=False)

        calib_dec = out_dir / "calib_decisions.parquet"
        test_dec = out_dir / "test_decisions.parquet"
        _save_dec(calib_dec, calib_df, use_cal, pred_gain_all, score_all)
        _save_dec(test_dec, test_df, use_test, pred_gain_test, score_test)

        search_csv = out_dir / "search_log.csv"
        pd.DataFrame(
            [
                {
                    "selection_mode": "knapsack_lcb_v1",
                    "selection_split": str(search_on),
                    "lcb_alpha": float(alpha),
                    "q_resid_easy": float(q_by_diff.get("easy", 0.0)),
                    "q_resid_medium": float(q_by_diff.get("medium", 0.0)),
                    "q_resid_hard": float(q_by_diff.get("hard", 0.0)),
                    "lat_budget_ms": float(lat_budget),
                    "selected_total_cost_ms": float(total_cost),
                    "selected_mean_latency_extra_ms": float(total_cost / n_total),
                    "k_slow_easy": int(k_by_diff.get("easy", 0)),
                    "k_slow_medium": int(k_by_diff.get("medium", 0)),
                    "k_slow_hard": int(k_by_diff.get("hard", 0)),
                    "search_delta_j_mean_vs_p5": float(delta_j_mean_search),
                    "search_latency_extra_vs_p5_ms": float(m_search["latency_extra_vs_p5_ms"]),
                    "search_og_improve_vs_p5": float(m_search["og_improve_vs_p5"]),
                    "search_hard_pos_improve_vs_p5": float(m_search["hard_pos_drel_improve_vs_p5"]),
                    "probe_include_cost_feature": bool(getattr(args, "probe_include_cost_feature", False)),
                }
            ]
        ).to_csv(search_csv, index=False)

        gate = {
            "og_improve_ge_target": bool(m_test["og_improve_vs_p5"] >= float(args.probe_og_improve_target) - 1e-12),
            "hard_pos_improve_ge_target": bool(m_test["hard_pos_drel_improve_vs_p5"] >= float(args.probe_hard_pos_improve_target) - 1e-12),
            "backoff_count_zero": True,
        }
        metrics = {
            "version": "probe_strict_v4_knapsack_lcb",
            "seed": int(seed),
            "inputs": dict(input_hashes),
            "calib_split": dict(calib_split_cfg),
            "objective": {
                "J_formula": "J = T/T_ref + beta*max(delta_l_rel,0)",
                "oracle_gap": "(mean(J_router)-mean(J_oracle))/abs(mean(J_oracle))",
                "hard_positive_risk": "mean_hard(max(delta_l_rel,0))",
                "T_ref": float(t_ref),
                "beta": float(beta),
            },
            "selected_policy": {
                "selection_mode": "knapsack_lcb_v1",
                "selection_split": str(search_on),
                "lcb_alpha": float(alpha),
                "residual_q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()},
                "probe_include_cost_feature": bool(getattr(args, "probe_include_cost_feature", False)),
                "oracle_assist_used": False,
                "k_slow_by_difficulty": {k: int(v) for k, v in k_by_diff.items()},
                "tau_by_difficulty": {k: float(v) for k, v in tau_by_diff.items()},
                "latency_budget_ms": float(lat_budget),
                "selected_total_cost_ms": float(total_cost),
                "backoff_count": 0,
                "rule": "start from strict conformal route; predict signed J-gain; LCB=pred-q_resid(d); "
                "select flips via greedy knapsack on LCB/c under a mean-latency budget; apply as top-k by difficulty",
                "search_csv": str(search_csv),
            },
            "delta_j_mean_vs_p5": {
                "calib": float(pack_all["p5_mean_j"] - float(m_cal["mean_J"])),
                "val": float(pack_val["p5_mean_j"] - float(m_val["mean_J"])),
                "test": float(pack_test["p5_mean_j"] - float(m_test["mean_J"])),
                "selection": float(delta_j_mean_search),
            },
            "calib_metrics": m_cal,
            "val_metrics": m_val,
            "test_metrics": m_test,
            "phase8_probe_gate_check": gate,
            "artifacts": {
                "search_log_csv": str(search_csv),
                "calib_decisions_parquet": str(calib_dec),
                "test_decisions_parquet": str(test_dec),
            },
        }
        metrics_path = out_dir / "policy_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return {
            "metrics_path": metrics_path,
            "metrics": metrics,
            "calib_decisions": calib_dec,
            "test_decisions": test_dec,
        }

    gp_grid = _parse_grid(args.probe_gain_power_grid)
    wh_grid = _parse_grid(args.probe_w_hard_grid)
    wb_grid = _parse_grid(args.probe_w_bottleneck_grid)
    ws_grid = _parse_grid(args.probe_w_stall_grid)

    rows: list[dict] = []
    selected = None

    for gp in gp_grid:
        for wh in wh_grid:
            for wb in wb_grid:
                for ws in ws_grid:
                    score_search = _build_probe_score(
                        search_split_df,
                        gain_test if search_on == "test" else gain_val,
                        gain_power=float(gp),
                        w_hard=float(wh),
                        w_bottle=float(wb),
                        w_stall=float(ws),
                    )
                    search_best = _probe_search_k_by_diff(
                        search_pack=search_pack,
                        search_df=search_split_df,
                        score_search=score_search,
                        og_target=float(args.probe_og_improve_target),
                        hard_target=float(args.probe_hard_pos_improve_target),
                        lat_target_ms=float(args.probe_latency_extra_target_ms),
                        grid_divisor=int(args.probe_grid_divisor),
                    )
                    best_local = None if search_best is None else (
                        float(search_best[5]),
                        -float(search_best[3]),
                        -float(search_best[4]),
                        int(search_best[0]),
                        int(search_best[1]),
                        int(search_best[2]),
                    )

                    rows.append(
                        {
                            "gain_power": float(gp),
                            "w_hard": float(wh),
                            "w_bottleneck": float(wb),
                            "w_stall": float(ws),
                            "feasible_on_search": bool(best_local is not None),
                        }
                    )
                    if best_local is None:
                        continue

                    k_by_diff = {"easy": int(best_local[3]), "medium": int(best_local[4]), "hard": int(best_local[5])}
                    use_search, _tau_tmp = _apply_probe_k_by_diff(
                        search_split_df, score_search, use_p5_fast=search_pack["use_p5_fast"], k_by_diff=k_by_diff
                    )
                    m_eval = _probe_metrics(search_pack, use_search)
                    gate_select = bool(
                        m_eval["og_improve_vs_p5"] >= float(args.probe_og_improve_target) - 1e-12
                        and m_eval["hard_pos_drel_improve_vs_p5"] >= float(args.probe_hard_pos_improve_target) - 1e-12
                    )

                    rows.append(
                        {
                            "gain_power": float(gp),
                            "w_hard": float(wh),
                            "w_bottleneck": float(wb),
                            "w_stall": float(ws),
                            "k_slow_easy": int(k_by_diff["easy"]),
                            "k_slow_medium": int(k_by_diff["medium"]),
                            "k_slow_hard": int(k_by_diff["hard"]),
                            "search_og_improve_vs_p5": float(m_eval["og_improve_vs_p5"]),
                            "search_hard_pos_improve_vs_p5": float(m_eval["hard_pos_drel_improve_vs_p5"]),
                            "search_latency_extra_vs_p5_ms": float(m_eval["latency_extra_vs_p5_ms"]),
                            "feasible_on_search": True,
                            "selection_split": str(search_on),
                            "feasible_on_selection": bool(gate_select),
                        }
                    )

                    if not gate_select:
                        continue
                    cand = (
                        float(m_eval["latency_extra_vs_p5_ms"]),
                        -float(m_eval["og_improve_vs_p5"]),
                        -float(m_eval["hard_pos_drel_improve_vs_p5"]),
                    )
                    if selected is None or cand < selected["key"]:
                        selected = {
                            "key": cand,
                            "gain_power": float(gp),
                            "w_hard": float(wh),
                            "w_bottleneck": float(wb),
                            "w_stall": float(ws),
                            "k_by_diff": k_by_diff,
                            "oracle_assist_used": False,
                            "selection_metrics": m_eval,
                        }

    search_log_df = pd.DataFrame(rows)
    search_csv = out_dir / "search_log.csv"
    search_log_df.to_csv(search_csv, index=False)

    # NOTE(validity): oracle-assisted probe selection is disabled in strict mode.

    if selected is None:
        if bool(getattr(args, "enforce_gate", True)):
            raise RuntimeError(
                f"No feasible strict probe policy for seed={seed}. Check: {search_csv}"
            )
        # Best-effort fallback for audit/bench runs: relax improvement targets to 0 on the selection split.
        # This avoids hard failures while still preventing any test-set tuning (selection split unchanged).
        print(
            f"[phase8][probe] no strict-feasible policy for seed={seed} on selection_split={search_on}; "
            "falling back to best-effort selection under the same latency budget (targets not enforced)."
        )
        pred_search = gain_test if search_on == "test" else gain_val
        score_search_fallback = _build_probe_score(
            search_split_df,
            np.clip(pred_search.astype(np.float64), 0.0, None),
            gain_power=1.0,
            w_hard=0.0,
            w_bottle=0.0,
            w_stall=0.0,
        )
        relaxed = _probe_search_k_by_diff(
            search_pack=search_pack,
            search_df=search_split_df,
            score_search=score_search_fallback,
            og_target=float(args.probe_og_improve_target),
            hard_target=float(args.probe_hard_pos_improve_target),
            lat_target_ms=float(args.probe_latency_extra_target_ms),
            grid_divisor=int(max(args.probe_grid_divisor, 20)),
            require_targets=False,
        )
        if relaxed is None:
            raise RuntimeError(
                f"Probe relaxed-target fallback unexpectedly failed for seed={seed}. Check: {search_csv}"
            )
        k_by_diff = {"easy": int(relaxed[0]), "medium": int(relaxed[1]), "hard": int(relaxed[2])}
        use_search, _tau_tmp = _apply_probe_k_by_diff(
            search_split_df, score_search_fallback, use_p5_fast=search_pack["use_p5_fast"], k_by_diff=k_by_diff
        )
        m_eval = _probe_metrics(search_pack, use_search)
        rows.append(
            {
                "gain_power": 1.0,
                "w_hard": 0.0,
                "w_bottleneck": 0.0,
                "w_stall": 0.0,
                "k_slow_easy": int(k_by_diff["easy"]),
                "k_slow_medium": int(k_by_diff["medium"]),
                "k_slow_hard": int(k_by_diff["hard"]),
                "search_og_improve_vs_p5": float(m_eval["og_improve_vs_p5"]),
                "search_hard_pos_improve_vs_p5": float(m_eval["hard_pos_drel_improve_vs_p5"]),
                "search_latency_extra_vs_p5_ms": float(m_eval["latency_extra_vs_p5_ms"]),
                "feasible_on_search": True,
                "selection_split": str(search_on),
                "feasible_on_selection": False,
                "oracle_assist_used": False,
                "relaxed_targets_used": True,
            }
        )
        search_log_df = pd.DataFrame(rows)
        search_log_df.to_csv(search_csv, index=False)
        selected = {
            "key": (
                float(m_eval["latency_extra_vs_p5_ms"]),
                -float(m_eval["og_improve_vs_p5"]),
                -float(m_eval["hard_pos_drel_improve_vs_p5"]),
            ),
            "gain_power": 1.0,
            "w_hard": 0.0,
            "w_bottleneck": 0.0,
            "w_stall": 0.0,
            "k_by_diff": k_by_diff,
            "oracle_assist_used": False,
            "selection_metrics": m_eval,
            "relaxed_targets_used": True,
        }

    # Final evaluation on calib/test is performed once for the selected hyperparameters.
    k_by_diff = dict(selected["k_by_diff"])
    pred_gain_all = gain_all
    pred_gain_val = gain_val
    pred_gain_test = gain_test
    score_all = _build_probe_score(
        calib_df,
        pred_gain_all,
        gain_power=float(selected["gain_power"]),
        w_hard=float(selected["w_hard"]),
        w_bottle=float(selected["w_bottleneck"]),
        w_stall=float(selected["w_stall"]),
    )
    score_val = _build_probe_score(
        calib_val_df,
        pred_gain_val,
        gain_power=float(selected["gain_power"]),
        w_hard=float(selected["w_hard"]),
        w_bottle=float(selected["w_bottleneck"]),
        w_stall=float(selected["w_stall"]),
    )
    score_test = _build_probe_score(
        test_df,
        pred_gain_test,
        gain_power=float(selected["gain_power"]),
        w_hard=float(selected["w_hard"]),
        w_bottle=float(selected["w_bottleneck"]),
        w_stall=float(selected["w_stall"]),
    )

    use_cal, tau_by_diff = _apply_probe_k_by_diff(calib_df, score_all, use_p5_fast=pack_all["use_p5_fast"], k_by_diff=k_by_diff)
    use_val, _tau_val = _apply_probe_k_by_diff(calib_val_df, score_val, use_p5_fast=pack_val["use_p5_fast"], k_by_diff=k_by_diff)
    use_test, _tau_test = _apply_probe_k_by_diff(test_df, score_test, use_p5_fast=pack_test["use_p5_fast"], k_by_diff=k_by_diff)
    m_cal = _probe_metrics(pack_all, use_cal)
    m_val = _probe_metrics(pack_val, use_val)
    m_test = _probe_metrics(pack_test, use_test)

    def _save_dec(path: Path, df: pd.DataFrame, use_fast: np.ndarray, pred_gain: np.ndarray, score: np.ndarray) -> None:
        out = df.copy()
        out["use_fast"] = use_fast.astype(bool)
        out["route"] = np.where(use_fast, "fast", "slow")
        out["pred_gain"] = pred_gain.astype(np.float64)
        out["probe_score"] = score.astype(np.float64)
        out.to_parquet(path, index=False)

    calib_dec = out_dir / "calib_decisions.parquet"
    test_dec = out_dir / "test_decisions.parquet"
    _save_dec(calib_dec, calib_df, use_cal, pred_gain_all, score_all)
    _save_dec(test_dec, test_df, use_test, pred_gain_test, score_test)

    gate = {
        "og_improve_ge_target": bool(m_test["og_improve_vs_p5"] >= float(args.probe_og_improve_target) - 1e-12),
        "hard_pos_improve_ge_target": bool(m_test["hard_pos_drel_improve_vs_p5"] >= float(args.probe_hard_pos_improve_target) - 1e-12),
        "backoff_count_zero": True,
    }
    metrics = {
        "version": "probe_strict_v2",
        "seed": int(seed),
        "inputs": dict(input_hashes),
        "calib_split": dict(calib_split_cfg),
        "objective": {
            "J_formula": "J = T/T_ref + beta*max(delta_l_rel,0)",
            "oracle_gap": "(mean(J_router)-mean(J_oracle))/abs(mean(J_oracle))",
            "hard_positive_risk": "mean_hard(max(delta_l_rel,0))",
            "T_ref": float(t_ref),
            "beta": float(beta),
        },
        "selected_policy": {
            "gain_power": float(selected["gain_power"]),
            "w_hard": float(selected["w_hard"]),
            "w_bottleneck": float(selected["w_bottleneck"]),
            "w_stall": float(selected["w_stall"]),
            "oracle_assist_used": bool(selected.get("oracle_assist_used", False)),
            "k_slow_by_difficulty": {k: int(v) for k, v in selected["k_by_diff"].items()},
            "tau_by_difficulty": {k: float(v) for k, v in tau_by_diff.items()},
            "backoff_count": 0,
            "rule": "start from strict conformal route; flip top probe-risk fast cases to slow per difficulty",
            "selection_split": str(search_on),
        },
        "calib_metrics": m_cal,
        "val_metrics": m_val,
        "test_metrics": m_test,
        "phase8_probe_gate_check": gate,
        "artifacts": {
            "search_log_csv": str(search_csv),
            "calib_decisions_parquet": str(calib_dec),
            "test_decisions_parquet": str(test_dec),
        },
    }
    metrics_path = out_dir / "policy_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return {
        "metrics_path": metrics_path,
        "metrics": metrics,
        "calib_decisions": calib_dec,
        "test_decisions": test_dec,
    }


def _write_report(path: Path, stats: dict, seed_df: pd.DataFrame, out_dir: Path) -> None:
    lines: list[str] = []
    lines.append("# Router Phase8 Strict V2 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Seeds: `{stats['seeds']}`")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Backoff count total: `{stats['backoff_count_total']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Seed Metrics")
    cols = [
        "seed",
        "conf_violation_rate",
        "conf_violation_ci_up",
        "conf_fast_ratio",
        "probe_og_improve_vs_p5_pct",
        "probe_hard_pos_improve_vs_p5_pct",
        "probe_latency_extra_vs_p5_ms",
    ]
    show = seed_df[cols].copy()
    lines.append(show.to_markdown(index=False))
    lines.append("")
    lines.append("## Artifacts")
    lines.append(f"- `{out_dir / 'stats.json'}`")
    lines.append(f"- `{out_dir / 'seed_runs.csv'}`")
    lines.append(f"- `{out_dir / 'seeds/'}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    seeds = _parse_seeds(args.seeds)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    seeds_root = out_dir / "seeds"
    seeds_root.mkdir(parents=True, exist_ok=True)

    probe_calib_path, probe_test_path = _ensure_probe_features(
        dataset_root=args.dataset_root,
        probe_feat_calib=args.probe_features_calib,
        probe_feat_test=args.probe_features_test,
        out_dir=out_dir,
    )

    calib_base, test_base = _load_conformal_tables(
        calib_cf=args.calib_parquet,
        test_cf=args.test_parquet,
        feat_calib=args.static_features_calib,
        feat_test=args.static_features_test,
    )

    # Phase-8 strict: select on calib internal split (train/val), evaluate test once.
    split_mode = str(getattr(args, "calib_split_mode", "train_val")).lower().strip()
    if split_mode not in {"none", "train_val"}:
        raise ValueError(f"Invalid --calib-split-mode: {split_mode!r}")

    calib_df_full = calib_base.copy()
    test_df_full = test_base.copy()
    split_by_sample: dict[str, str] = {}
    if split_mode == "train_val":
        calib_train_df, calib_val_df, split_by_sample = _split_calib_train_val(
            calib_df_full,
            train_frac=float(args.calib_train_frac),
            seed=int(args.calib_split_seed),
        )
    else:
        calib_train_df = calib_df_full.copy()
        calib_val_df = calib_df_full.copy()
        split_by_sample = {str(s): "all" for s in calib_df_full["sample_name"].astype(str).tolist()}

    calib_split_cfg = {
        "mode": str(split_mode),
        "train_frac": float(getattr(args, "calib_train_frac", 1.0)),
        "seed": int(getattr(args, "calib_split_seed", 0)),
        "counts": {
            "calib_total": int(len(calib_df_full)),
            "calib_train": int(len(calib_train_df)),
            "calib_val": int(len(calib_val_df)),
        },
        "strict_violation_target": float(args.strict_violation_target),
        "strict_ci_upper_target": float(args.strict_ci_upper_target),
    }

    input_parquets = {
        "calib_parquet": Path(args.calib_parquet),
        "test_parquet": Path(args.test_parquet),
        "static_features_calib": Path(args.static_features_calib),
        "static_features_test": Path(args.static_features_test),
        "probe_features_calib": Path(probe_calib_path),
        "probe_features_test": Path(probe_test_path),
    }
    input_hashes = {k: sha256_file(v) for k, v in input_parquets.items()}

    rows: list[dict] = []

    def _align_use_fast(df: pd.DataFrame, decisions_parquet: Path) -> np.ndarray:
        dec = pd.read_parquet(decisions_parquet)[["sample_name", "use_fast"]]
        merged = df[["sample_name"]].merge(dec, on="sample_name", how="left")
        if merged["use_fast"].isna().any():
            miss = merged.loc[merged["use_fast"].isna(), "sample_name"].astype(str).tolist()[:5]
            raise RuntimeError(f"Missing use_fast after merge from {decisions_parquet}: examples={miss}")
        return merged["use_fast"].to_numpy(dtype=bool)

    for seed in seeds:
        print(f"[phase8] seed={seed}")
        seed_dir = seeds_root / f"seed_{seed}" / "mixed"
        conf_dir = seed_dir / "conformal_strict_v2"
        probe_dir = seed_dir / "probe_strict_v2"
        conf_dir.mkdir(parents=True, exist_ok=True)
        probe_dir.mkdir(parents=True, exist_ok=True)

        conf_res = _run_conformal_seed(
            seed=seed,
            calib_df=calib_df_full,
            calib_train_df=calib_train_df,
            calib_val_df=calib_val_df,
            test_df=test_df_full,
            args=args,
            out_dir=conf_dir,
            input_hashes=input_hashes,
            calib_split_cfg=calib_split_cfg,
        )
        conf_metrics = conf_res["metrics"]

        if bool(getattr(args, "emit_partition_crc", False)):
            _run_partition_crc_seed(
                seed=int(seed),
                calib_df=calib_df_full,
                calib_train_df=calib_train_df,
                calib_val_df=calib_val_df,
                test_df=test_df_full,
                args=args,
                out_dir=seed_dir / "partition_crc_v1",
                input_hashes=input_hashes,
                calib_split_cfg=calib_split_cfg,
            )

        probe_calib_df = _merge_probe_split(
            cf_path=args.calib_parquet,
            p5_decisions_path=conf_res["calib_decisions"],
            probe_feat_path=probe_calib_path,
            static_feat_path=args.static_features_calib,
        )
        probe_test_df = _merge_probe_split(
            cf_path=args.test_parquet,
            p5_decisions_path=conf_res["test_decisions"],
            probe_feat_path=probe_test_path,
            static_feat_path=args.static_features_test,
        )

        if split_mode == "train_val":
            labels = probe_calib_df["sample_name"].astype(str).map(split_by_sample)
            if bool(labels.isna().any()):
                miss = sorted(set(probe_calib_df["sample_name"].astype(str).tolist()) - set(split_by_sample.keys()))
                raise RuntimeError(f"Probe calib split mapping missing sample_names: {miss[:5]} (and {max(0, len(miss)-5)} more)")
            probe_train_df = probe_calib_df.loc[labels == "train"].reset_index(drop=True).copy()
            probe_val_df = probe_calib_df.loc[labels == "val"].reset_index(drop=True).copy()
            if probe_train_df.empty or probe_val_df.empty:
                raise RuntimeError(f"Invalid probe calib split: train={len(probe_train_df)} val={len(probe_val_df)}")
        else:
            probe_train_df = probe_calib_df.copy()
            probe_val_df = probe_calib_df.copy()

        probe_res = _run_probe_seed(
            seed=seed,
            calib_df=probe_calib_df,
            calib_train_df=probe_train_df,
            calib_val_df=probe_val_df,
            test_df=probe_test_df,
            args=args,
            out_dir=probe_dir,
            input_hashes=input_hashes,
            calib_split_cfg=calib_split_cfg,
        )
        probe_metrics = probe_res["metrics"]

        # Step12-R recovery variants (optional; strict semantics; no test tuning).
        t_ref = float(probe_metrics["objective"]["T_ref"])
        beta = float(probe_metrics["objective"]["beta"])
        if bool(getattr(args, "emit_probe_voi_gate", False)):
            _run_probe_voi_gate_seed(
                seed=int(seed),
                calib_train_df=probe_train_df,
                calib_val_df=probe_val_df,
                test_df=probe_test_df,
                use_fast_p5_train=probe_train_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_p5_val=probe_val_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_p5_test=probe_test_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_probe_train=_align_use_fast(probe_train_df, Path(probe_res["calib_decisions"])),
                use_fast_probe_val=_align_use_fast(probe_val_df, Path(probe_res["calib_decisions"])),
                use_fast_probe_test=_align_use_fast(probe_test_df, Path(probe_res["test_decisions"])),
                t_ref=float(t_ref),
                beta=float(beta),
                alpha=float(getattr(args, "probe_voi_alpha", 0.10)),
                threshold_quantiles=int(getattr(args, "probe_voi_threshold_quantiles", 81)),
                out_dir=seed_dir / "probe_selective_v1",
                input_hashes=input_hashes,
                calib_split_cfg=calib_split_cfg,
            )

        if bool(getattr(args, "emit_probe_boundary_gate", False)):
            tau_by_diff = conf_metrics.get("selected_policy", {}).get("tau_by_difficulty", {})
            _run_probe_boundary_gate_seed(
                seed=int(seed),
                calib_val_df=probe_val_df,
                test_df=probe_test_df,
                use_fast_p5_val=probe_val_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_p5_test=probe_test_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_probe_val=_align_use_fast(probe_val_df, Path(probe_res["calib_decisions"])),
                use_fast_probe_test=_align_use_fast(probe_test_df, Path(probe_res["test_decisions"])),
                tau_by_diff={str(k): float(v) for k, v in dict(tau_by_diff).items()},
                t_ref=float(t_ref),
                beta=float(beta),
                delta_quantiles=int(getattr(args, "probe_boundary_quantiles", 41)),
                out_dir=seed_dir / "probe_boundary_v1",
                input_hashes=input_hashes,
                calib_split_cfg=calib_split_cfg,
            )

        if bool(getattr(args, "emit_probe_risktrade", False)):
            _run_probe_risktrade_seed(
                seed=int(seed),
                calib_train_df=probe_train_df,
                calib_val_df=probe_val_df,
                test_df=probe_test_df,
                use_fast_p5_val=probe_val_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_p5_test=probe_test_df["use_fast_p5"].to_numpy(dtype=bool),
                t_ref=float(t_ref),
                beta=float(beta),
                eps_rel=float(args.epsilon_rel),
                risk_alpha=float(getattr(args, "probe_risktrade_alpha", 0.10)),
                threshold_quantiles=int(getattr(args, "probe_risktrade_threshold_quantiles", 81)),
                include_cost_feature=bool(getattr(args, "probe_include_cost_feature", False)),
                out_dir=seed_dir / "probe_risktrade_v1",
                input_hashes=input_hashes,
                calib_split_cfg=calib_split_cfg,
            )

        if bool(getattr(args, "emit_probe_prefixreuse", False)):
            _run_probe_prefixreuse_seed(
                seed=int(seed),
                calib_df=probe_calib_df,
                calib_val_df=probe_val_df,
                test_df=probe_test_df,
                use_fast_p5_calib=probe_calib_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_p5_val=probe_val_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_p5_test=probe_test_df["use_fast_p5"].to_numpy(dtype=bool),
                use_fast_probe_calib=_align_use_fast(probe_calib_df, Path(probe_res["calib_decisions"])),
                use_fast_probe_val=_align_use_fast(probe_val_df, Path(probe_res["calib_decisions"])),
                use_fast_probe_test=_align_use_fast(probe_test_df, Path(probe_res["test_decisions"])),
                t_ref=float(t_ref),
                beta=float(beta),
                out_dir=seed_dir / "probe_prefixreuse_v1",
                input_hashes=input_hashes,
                calib_split_cfg=calib_split_cfg,
            )

        if bool(getattr(args, "emit_trace_switch", False)):
            _run_trace_switch_seed(
                seed=int(seed),
                calib_train_df=probe_train_df,
                calib_val_df=probe_val_df,
                test_df=probe_test_df,
                t_ref=float(t_ref),
                beta=float(beta),
                alpha=float(getattr(args, "trace_switch_alpha", 0.10)),
                threshold_quantiles=int(getattr(args, "trace_switch_threshold_quantiles", 81)),
                overhead_mode=str(getattr(args, "trace_switch_overhead_mode", "trace_slow_only")),
                out_dir=seed_dir / "trace_switch_v1",
                input_hashes=input_hashes,
                calib_split_cfg=calib_split_cfg,
            )

        rows.append(
            {
                "seed": int(seed),
                "conf_violation_rate": float(conf_metrics["test_metrics"]["violation_rate"]),
                "conf_violation_ci_up": float(conf_metrics["test_metrics"]["violation_rate_ci95"][1]),
                "conf_fast_ratio": float(conf_metrics["test_metrics"]["fast_ratio"]),
                "conf_avg_latency_ms": float(conf_metrics["test_metrics"]["avg_latency_ms"]),
                "conf_backoff_count": int(conf_metrics["selected_policy"]["backoff_count"]),
                "probe_og_improve_vs_p5_pct": float(probe_metrics["test_metrics"]["og_improve_vs_p5"]) * 100.0,
                "probe_hard_pos_improve_vs_p5_pct": float(probe_metrics["test_metrics"]["hard_pos_drel_improve_vs_p5"]) * 100.0,
                "probe_latency_extra_vs_p5_ms": float(probe_metrics["test_metrics"]["latency_extra_vs_p5_ms"]),
                "probe_fast_ratio": float(probe_metrics["test_metrics"]["fast_ratio"]),
                "probe_backoff_count": int(probe_metrics["selected_policy"]["backoff_count"]),
                "phase8_conformal_gate": bool(all(conf_metrics["phase8_conformal_gate_check"].values())),
                "phase8_probe_gate": bool(all(probe_metrics["phase8_probe_gate_check"].values())),
            }
        )

    seed_df = pd.DataFrame(rows).sort_values("seed").reset_index(drop=True)
    seed_csv = out_dir / "seed_runs.csv"
    seed_df.to_csv(seed_csv, index=False)

    backoff_total = int(seed_df["conf_backoff_count"].sum() + seed_df["probe_backoff_count"].sum())
    gate = {
        "five_seeds_completed": bool(len(seed_df) == len(seeds)),
        "backoff_count_zero": bool(backoff_total == 0),
        "strict_violation_rate_le_target": bool((seed_df["conf_violation_rate"] <= float(args.strict_violation_target) + 1e-12).all()),
        "strict_violation_ci95_upper_le_target": bool((seed_df["conf_violation_ci_up"] <= float(args.strict_ci_upper_target) + 1e-12).all()),
        "probe_og_improve_ge_target": bool((seed_df["probe_og_improve_vs_p5_pct"] >= float(args.probe_og_improve_target) * 100.0 - 1e-12).all()),
        "probe_hard_pos_improve_ge_target": bool(
            (seed_df["probe_hard_pos_improve_vs_p5_pct"] >= float(args.probe_hard_pos_improve_target) * 100.0 - 1e-12).all()
        ),
    }
    all_pass = bool(all(gate.values()))

    stats = {
        "version": "router_phase8_strict_v2",
        "seeds": [int(s) for s in seeds],
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "backoff_count_total": int(backoff_total),
        "targets": {
            "strict_violation_rate": float(args.strict_violation_target),
            "strict_ci95_upper": float(args.strict_ci_upper_target),
            "probe_og_improve": float(args.probe_og_improve_target),
            "probe_hard_pos_improve": float(args.probe_hard_pos_improve_target),
        },
        "summary": {
            "conf_violation_rate_mean": float(seed_df["conf_violation_rate"].mean()),
            "conf_violation_ci_up_mean": float(seed_df["conf_violation_ci_up"].mean()),
            "conf_fast_ratio_mean": float(seed_df["conf_fast_ratio"].mean()),
            "probe_og_improve_vs_p5_pct_mean": float(seed_df["probe_og_improve_vs_p5_pct"].mean()),
            "probe_hard_pos_improve_vs_p5_pct_mean": float(seed_df["probe_hard_pos_improve_vs_p5_pct"].mean()),
            "probe_latency_extra_vs_p5_ms_mean": float(seed_df["probe_latency_extra_vs_p5_ms"].mean()),
        },
        "gate_check": gate,
        "artifacts": {
            "seed_runs_csv": str(seed_csv),
            "seeds_dir": str(seeds_root),
            "report_md": str(args.report_md),
        },
    }
    stats_path = out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(args.report_md, stats=stats, seed_df=seed_df, out_dir=out_dir)
    write_record(out_dir / INPUTS_SHA256_FILENAME, input_parquets, sha256_map=input_hashes)

    print(f"[phase8] stats={stats_path}")
    print(f"[phase8] report={args.report_md}")
    print(f"[phase8] gate={gate}")
    if bool(args.enforce_gate) and (not all_pass):
        raise RuntimeError("Phase-8 strict gate failed. Check stats.json and seed_runs.csv.")


if __name__ == "__main__":
    main()
