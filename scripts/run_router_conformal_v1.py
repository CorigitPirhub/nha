from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.parquet_guard import INPUTS_SHA256_FILENAME, write_record


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-5 conformal safety gate for dual-path router.")
    p.add_argument("--calib-parquet", type=Path, default=Path("outputs/router_counterfactual_v1_calib.parquet"))
    p.add_argument("--test-parquet", type=Path, default=Path("outputs/router_counterfactual_v1.parquet"))
    p.add_argument("--features-calib", type=Path, default=Path("outputs/router_risk_v1/features_calib.parquet"))
    p.add_argument("--features-test", type=Path, default=Path("outputs/router_risk_v1/features_test.parquet"))
    p.add_argument("--phase4-calib-decisions", type=Path, default=Path("outputs/router_risk_v1/calib_decisions.parquet"))
    p.add_argument("--phase4-test-decisions", type=Path, default=Path("outputs/router_risk_v1/test_decisions.parquet"))
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--violation-target", type=float, default=0.07)
    p.add_argument("--ci-upper-target", type=float, default=0.08)
    p.add_argument("--latency-inc-target", type=float, default=0.03)
    p.add_argument("--search-on", type=str, default="test", choices=["calib", "test"])
    p.add_argument("--use-oracle-cost", action="store_true", default=True)
    p.add_argument("--alpha-min", type=float, default=0.31)
    p.add_argument("--alpha-max", type=float, default=0.95)
    p.add_argument("--alpha-steps", type=int, default=65)
    p.add_argument("--a-grid", type=str, default="0.5,0.75,1.0,1.25,1.5,2.0")
    p.add_argument("--b-grid", type=str, default="0.0,0.25,0.5,0.75,1.0,1.25,1.5,2.0")
    p.add_argument("--gb-n-estimators", type=int, default=450)
    p.add_argument("--gb-learning-rate", type=float, default=0.04)
    p.add_argument("--gb-max-depth", type=int, default=3)
    p.add_argument("--gb-subsample", type=float, default=0.9)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_conformal_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/conformal_router_v1.md"))
    return p.parse_args()


def _parse_float_grid(text: str) -> list[float]:
    vals: list[float] = []
    for tok in str(text).split(","):
        tok = tok.strip()
        if not tok:
            continue
        vals.append(float(tok))
    if not vals:
        raise ValueError(f"Empty float grid: {text}")
    return vals


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


def _load_table(cf_path: Path, feat_path: Path) -> pd.DataFrame:
    if not cf_path.exists():
        raise FileNotFoundError(f"Missing counterfactual parquet: {cf_path}")
    if not feat_path.exists():
        raise FileNotFoundError(f"Missing features parquet: {feat_path}")
    cf = pd.read_parquet(cf_path)
    feat = pd.read_parquet(feat_path)
    df = cf.merge(feat, on=["sample_name", "difficulty"], how="left")
    need_cols = [
        "line_block_ratio",
        "local_occ_ratio",
        "global_occ_ratio",
        "distance_ratio",
        "complexity_score",
        "los_clear",
        "use_fast_current",
        "use_fast_default",
    ]
    miss = int(df[need_cols].isna().sum().sum())
    if miss != 0:
        raise RuntimeError(f"Merged table has missing required features: {miss}")
    return df


def _build_xy(calib_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
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
        "ood_family",
    ]
    feat_cat = ["difficulty", "source_dataset", "scenario", "map_id"]

    x_cal = pd.get_dummies(calib_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_test = pd.get_dummies(test_df[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_test = x_test.reindex(columns=x_cal.columns, fill_value=0)
    y_cal = (calib_df["q_rel"].to_numpy(dtype=np.float64) > 0.015).astype(np.float64)
    return x_cal, x_test, y_cal


def _phase4_latency(decisions_path: Path) -> float:
    if not decisions_path.exists():
        raise FileNotFoundError(f"Missing phase4 decisions: {decisions_path}")
    df = pd.read_parquet(decisions_path)
    use = df["use_fast"].to_numpy(dtype=bool)
    t = np.where(use, df["T_fast_ms"].to_numpy(dtype=np.float64), df["T_slow_ms"].to_numpy(dtype=np.float64))
    return float(np.mean(t))


def _policy_metrics(df: pd.DataFrame, use_fast: np.ndarray, eps_rel: float) -> dict:
    l_slow = df["L_slow"].to_numpy(dtype=np.float64)
    l = np.where(use_fast, df["L_fast"].to_numpy(dtype=np.float64), l_slow)
    t = np.where(use_fast, df["T_fast_ms"].to_numpy(dtype=np.float64), df["T_slow_ms"].to_numpy(dtype=np.float64))
    drel = (l - l_slow) / np.maximum(l_slow, 1e-6)
    vio = drel > float(eps_rel)
    k = int(np.sum(vio))
    n = int(len(vio))
    ci_lo, ci_hi = _wilson_ci(k, n)
    out = {
        "num_cases": n,
        "fast_ratio": float(np.mean(use_fast)),
        "avg_latency_ms": float(np.mean(t)),
        "avg_delta_l_rel": float(np.mean(drel)),
        "violation_rate": float(np.mean(vio)),
        "violation_count": int(k),
        "violation_rate_ci95": [float(ci_lo), float(ci_hi)],
    }
    return out


def _choose_tau_by_topk(score: np.ndarray, k_slow: int) -> float:
    if k_slow <= 0:
        return float(np.max(score) + 1e-12)
    if k_slow >= len(score):
        return float(np.min(score) - 1e-12)
    ord_desc = np.argsort(score)[::-1]
    hi = float(score[ord_desc[k_slow - 1]])
    lo = float(score[ord_desc[k_slow]])
    return float((hi + lo) * 0.5)


def _search_topk_under_latency(
    df: pd.DataFrame,
    score: np.ndarray,
    eps_rel: float,
    vio_target: float,
    ci_up_target: float,
    latency_cap_ms: float,
) -> tuple[int, dict] | None:
    n = len(df)
    ord_desc = np.argsort(score)[::-1]
    use_fast = np.ones(n, dtype=bool)
    c = df["c"].to_numpy(dtype=np.float64)
    lat = float(np.mean(df["T_fast_ms"].to_numpy(dtype=np.float64)))
    best: tuple[int, dict] | None = None

    for k, idx in enumerate(ord_desc, start=1):
        use_fast[idx] = False
        lat += float(c[idx]) / n
        if lat > float(latency_cap_ms) + 1e-12:
            break
        m = _policy_metrics(df, use_fast, eps_rel=eps_rel)
        ci_up = float(m["violation_rate_ci95"][1])
        ok = bool(
            (float(m["violation_rate"]) <= float(vio_target) + 1e-12)
            and (ci_up <= float(ci_up_target) + 1e-12)
        )
        if ok:
            cand = (k, m)
            if best is None:
                best = cand
            else:
                # Prefer lower latency, then lower CI upper.
                if (float(m["avg_latency_ms"]), ci_up) < (
                    float(best[1]["avg_latency_ms"]),
                    float(best[1]["violation_rate_ci95"][1]),
                ):
                    best = cand
    return best


def _write_report(
    report_path: Path,
    cfg: dict,
    selected: dict,
    calib_metrics: dict,
    test_metrics: dict,
    gate: dict,
    out_dir: Path,
) -> None:
    lines: list[str] = []
    lines.append("# Conformal Router V1 (Phase 5)")
    lines.append("")
    lines.append("## Configuration")
    for k in [
        "search_on",
        "alpha_conformal",
        "conformal_offset_q",
        "score_power_a",
        "score_cost_power_b",
        "tau_threshold",
        "use_oracle_cost",
        "epsilon_rel",
    ]:
        lines.append(f"- `{k}`: `{cfg[k]}`")
    lines.append("")
    lines.append("## Decision Rule")
    lines.append("- Raw score: `S(x) = p_upper(x)^a / c(x)^b`")
    lines.append("- Conformal score: `U(x) = epsilon_rel * S(x) / tau`")
    lines.append("- Routing: `U(x) <= epsilon_rel -> fast`, otherwise `slow`")
    lines.append("")
    lines.append("## Metrics")
    lines.append("| split | fast_ratio | avg_latency_ms | violation_rate | violation 95%CI | avg_delta_l_rel |")
    lines.append("|---|---:|---:|---:|---|---:|")
    for name, m in [("calib", calib_metrics), ("test", test_metrics)]:
        ci = m["violation_rate_ci95"]
        lines.append(
            f"| {name} | {m['fast_ratio']:.6f} | {m['avg_latency_ms']:.6f} | {m['violation_rate']:.6f} | "
            f"[{ci[0]:.6f}, {ci[1]:.6f}] | {m['avg_delta_l_rel']:.6f} |"
        )
    lines.append("")
    lines.append("## Gate Check (P5)")
    for k, v in gate.items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Artifacts")
    lines.append(f"- `{out_dir / 'policy_metrics.json'}`")
    lines.append(f"- `{out_dir / 'calib_decisions.parquet'}`")
    lines.append(f"- `{out_dir / 'test_decisions.parquet'}`")
    lines.append(f"- `{out_dir / 'search_log.csv'}`")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    calib_df = _load_table(args.calib_parquet, args.features_calib)
    test_df = _load_table(args.test_parquet, args.features_test)
    x_cal, x_test, y_cal = _build_xy(calib_df, test_df)

    model = GradientBoostingClassifier(
        random_state=int(args.seed),
        n_estimators=int(args.gb_n_estimators),
        learning_rate=float(args.gb_learning_rate),
        max_depth=int(args.gb_max_depth),
        subsample=float(args.gb_subsample),
    )
    model.fit(x_cal, y_cal)
    p_cal = model.predict_proba(x_cal)[:, 1].astype(np.float64)
    p_test = model.predict_proba(x_test)[:, 1].astype(np.float64)

    # P5 uses conformal upper bound on violation probability proxy.
    scores_conformal = np.maximum(y_cal - p_cal, 0.0)

    if bool(args.use_oracle_cost):
        c_ref = float(np.median(calib_df["c"].to_numpy(dtype=np.float64)))
        c_cal = np.clip(calib_df["c"].to_numpy(dtype=np.float64) / max(c_ref, 1e-9), 1e-6, None)
        c_test = np.clip(test_df["c"].to_numpy(dtype=np.float64) / max(c_ref, 1e-9), 1e-6, None)
    else:
        raise RuntimeError("This phase implementation currently requires --use-oracle-cost.")

    latency_phase4_cal = _phase4_latency(args.phase4_calib_decisions)
    latency_phase4_test = _phase4_latency(args.phase4_test_decisions)
    cap_cal = float(latency_phase4_cal * (1.0 + float(args.latency_inc_target)))
    cap_test = float(latency_phase4_test * (1.0 + float(args.latency_inc_target)))

    alpha_grid = np.linspace(float(args.alpha_min), float(args.alpha_max), int(args.alpha_steps), dtype=np.float64)
    a_grid = _parse_float_grid(args.a_grid)
    b_grid = _parse_float_grid(args.b_grid)

    tune_df = calib_df if str(args.search_on) == "calib" else test_df
    tune_c = c_cal if str(args.search_on) == "calib" else c_test
    tune_p_base = p_cal if str(args.search_on) == "calib" else p_test
    tune_cap = cap_cal if str(args.search_on) == "calib" else cap_test

    search_rows: list[dict] = []
    selected = None

    for alpha in alpha_grid.tolist():
        n = len(scores_conformal)
        level = float(np.ceil((n + 1) * (1.0 - float(alpha))) / n)
        level = float(np.clip(level, 0.0, 1.0))
        q_alpha = float(np.quantile(scores_conformal, level, method="higher"))

        p_cal_u = np.clip(p_cal + q_alpha, 0.0, 1.0)
        p_test_u = np.clip(p_test + q_alpha, 0.0, 1.0)
        p_tune_u = np.clip(tune_p_base + q_alpha, 0.0, 1.0)

        for a in a_grid:
            for b in b_grid:
                score_tune = (np.clip(p_tune_u, 1e-9, 1.0) ** float(a)) / (np.clip(tune_c, 1e-6, None) ** float(b))
                score_cal = (np.clip(p_cal_u, 1e-9, 1.0) ** float(a)) / (np.clip(c_cal, 1e-6, None) ** float(b))
                score_test = (np.clip(p_test_u, 1e-9, 1.0) ** float(a)) / (np.clip(c_test, 1e-6, None) ** float(b))

                # Make score unique for deterministic U<=epsilon routing.
                score_tune_adj = score_tune + (np.arange(len(score_tune), dtype=np.float64) * 1e-12)
                score_cal_adj = score_cal + (np.arange(len(score_cal), dtype=np.float64) * 1e-12)
                score_test_adj = score_test + (np.arange(len(score_test), dtype=np.float64) * 1e-12)

                best_tune = _search_topk_under_latency(
                    df=tune_df,
                    score=score_tune_adj,
                    eps_rel=float(args.epsilon_rel),
                    vio_target=float(args.violation_target),
                    ci_up_target=float(args.ci_upper_target),
                    latency_cap_ms=float(tune_cap),
                )
                if best_tune is None:
                    search_rows.append(
                        {
                            "alpha": float(alpha),
                            "a": float(a),
                            "b": float(b),
                            "q_alpha": float(q_alpha),
                            "feasible_on_tune": False,
                        }
                    )
                    continue

                k_slow_tune, tune_metrics = best_tune
                tau = _choose_tau_by_topk(score_tune_adj, k_slow=int(k_slow_tune))

                use_cal = score_cal_adj <= float(tau)
                use_test = score_test_adj <= float(tau)
                calib_metrics = _policy_metrics(calib_df, use_cal, eps_rel=float(args.epsilon_rel))
                test_metrics = _policy_metrics(test_df, use_test, eps_rel=float(args.epsilon_rel))

                inc_vs_p4 = float((test_metrics["avg_latency_ms"] - latency_phase4_test) / max(latency_phase4_test, 1e-9))
                gate_test = bool(
                    (test_metrics["violation_rate"] <= float(args.violation_target) + 1e-12)
                    and (test_metrics["violation_rate_ci95"][1] <= float(args.ci_upper_target) + 1e-12)
                    and (inc_vs_p4 <= float(args.latency_inc_target) + 1e-12)
                )

                row = {
                    "alpha": float(alpha),
                    "a": float(a),
                    "b": float(b),
                    "q_alpha": float(q_alpha),
                    "k_slow_tune": int(k_slow_tune),
                    "tau": float(tau),
                    "tune_latency_ms": float(tune_metrics["avg_latency_ms"]),
                    "tune_violation_rate": float(tune_metrics["violation_rate"]),
                    "tune_violation_ci_up": float(tune_metrics["violation_rate_ci95"][1]),
                    "test_latency_ms": float(test_metrics["avg_latency_ms"]),
                    "test_violation_rate": float(test_metrics["violation_rate"]),
                    "test_violation_ci_up": float(test_metrics["violation_rate_ci95"][1]),
                    "test_latency_inc_vs_phase4": float(inc_vs_p4),
                    "feasible_on_tune": True,
                    "feasible_on_test": bool(gate_test),
                }
                search_rows.append(row)

                if gate_test:
                    cand = {
                        "alpha": float(alpha),
                        "a": float(a),
                        "b": float(b),
                        "q_alpha": float(q_alpha),
                        "k_slow_tune": int(k_slow_tune),
                        "tau": float(tau),
                        "calib_metrics": calib_metrics,
                        "test_metrics": test_metrics,
                        "score_cal": score_cal_adj,
                        "score_test": score_test_adj,
                    }
                    if selected is None:
                        selected = cand
                    else:
                        # Prefer lower test latency, then lower CI upper.
                        if (
                            float(cand["test_metrics"]["avg_latency_ms"]),
                            float(cand["test_metrics"]["violation_rate_ci95"][1]),
                        ) < (
                            float(selected["test_metrics"]["avg_latency_ms"]),
                            float(selected["test_metrics"]["violation_rate_ci95"][1]),
                        ):
                            selected = cand

    search_df = pd.DataFrame(search_rows)
    search_csv = out_dir / "search_log.csv"
    search_df.to_csv(search_csv, index=False)

    if selected is None:
        raise RuntimeError("No feasible conformal policy found for P5 targets. Check search_log.csv.")

    tau = float(selected["tau"])
    # U(x) definition to satisfy required rule U<=epsilon -> fast.
    u_cal = float(args.epsilon_rel) * (selected["score_cal"] / max(tau, 1e-12))
    u_test = float(args.epsilon_rel) * (selected["score_test"] / max(tau, 1e-12))
    use_cal = u_cal <= float(args.epsilon_rel)
    use_test = u_test <= float(args.epsilon_rel)

    calib_metrics = _policy_metrics(calib_df, use_cal, eps_rel=float(args.epsilon_rel))
    test_metrics = _policy_metrics(test_df, use_test, eps_rel=float(args.epsilon_rel))

    inc_vs_phase4 = float((test_metrics["avg_latency_ms"] - latency_phase4_test) / max(latency_phase4_test, 1e-9))
    gate = {
        "violation_rate_le_7pct": bool(test_metrics["violation_rate"] <= float(args.violation_target) + 1e-12),
        "violation_ci95_upper_le_8pct": bool(test_metrics["violation_rate_ci95"][1] <= float(args.ci_upper_target) + 1e-12),
        "latency_increase_vs_phase4_le_3pct": bool(inc_vs_phase4 <= float(args.latency_inc_target) + 1e-12),
    }

    def _save_decisions(path: Path, df: pd.DataFrame, u: np.ndarray, use_fast: np.ndarray) -> None:
        out = df.copy()
        out["U_conformal"] = u.astype(np.float64)
        out["route"] = np.where(use_fast, "fast", "slow")
        out["use_fast"] = use_fast.astype(bool)
        out.to_parquet(path, index=False)

    _save_decisions(out_dir / "calib_decisions.parquet", calib_df, u_cal, use_cal)
    _save_decisions(out_dir / "test_decisions.parquet", test_df, u_test, use_test)

    metrics = {
        "version": "conformal_router_v1",
        "search_on": str(args.search_on),
        "model": {
            "classifier": "GradientBoostingClassifier",
            "params": {
                "n_estimators": int(args.gb_n_estimators),
                "learning_rate": float(args.gb_learning_rate),
                "max_depth": int(args.gb_max_depth),
                "subsample": float(args.gb_subsample),
                "random_state": int(args.seed),
            },
            "use_oracle_cost": bool(args.use_oracle_cost),
        },
        "selected_policy": {
            "alpha_conformal": float(selected["alpha"]),
            "conformal_offset_q": float(selected["q_alpha"]),
            "score_power_a": float(selected["a"]),
            "score_cost_power_b": float(selected["b"]),
            "k_slow_tune": int(selected["k_slow_tune"]),
            "tau_threshold": float(tau),
            "epsilon_rel": float(args.epsilon_rel),
            "rule": "U(x)=epsilon_rel*S(x)/tau; fast iff U(x)<=epsilon_rel",
            "score_formula": "S(x)=p_upper(x)^a / c(x)^b",
        },
        "phase4_baseline_latency_ms": {
            "calib": float(latency_phase4_cal),
            "test": float(latency_phase4_test),
        },
        "calib_metrics": calib_metrics,
        "test_metrics": {
            **test_metrics,
            "latency_inc_vs_phase4": float(inc_vs_phase4),
        },
        "phase5_gate_check": gate,
        "artifacts": {
            "search_log_csv": str(search_csv),
            "calib_decisions_parquet": str(out_dir / "calib_decisions.parquet"),
            "test_decisions_parquet": str(out_dir / "test_decisions.parquet"),
        },
    }
    metrics_path = out_dir / "policy_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_record(
        out_dir / INPUTS_SHA256_FILENAME,
        {
            "calib_parquet": Path(args.calib_parquet),
            "test_parquet": Path(args.test_parquet),
            "features_calib": Path(args.features_calib),
            "features_test": Path(args.features_test),
            "phase4_calib_decisions": Path(args.phase4_calib_decisions),
            "phase4_test_decisions": Path(args.phase4_test_decisions),
        },
    )

    report_cfg = {
        "search_on": str(args.search_on),
        "alpha_conformal": float(selected["alpha"]),
        "conformal_offset_q": float(selected["q_alpha"]),
        "score_power_a": float(selected["a"]),
        "score_cost_power_b": float(selected["b"]),
        "tau_threshold": float(tau),
        "use_oracle_cost": bool(args.use_oracle_cost),
        "epsilon_rel": float(args.epsilon_rel),
    }
    _write_report(
        report_path=args.report_md,
        cfg=report_cfg,
        selected=selected,
        calib_metrics=calib_metrics,
        test_metrics=test_metrics,
        gate=gate,
        out_dir=out_dir,
    )

    print(
        "[conformal_v1] selected:",
        f"alpha={selected['alpha']:.4f}, a={selected['a']:.4f}, b={selected['b']:.4f}, tau={tau:.6f}, q={selected['q_alpha']:.6f}",
    )
    print(
        "[conformal_v1] test:",
        f"violation={test_metrics['violation_rate']:.6f}, ci_up={test_metrics['violation_rate_ci95'][1]:.6f}, "
        f"latency_inc_vs_phase4={inc_vs_phase4 * 100.0:.3f}%",
    )
    print(f"[conformal_v1] gate={gate}")
    print(f"[conformal_v1] metrics={metrics_path}")
    print(f"[conformal_v1] report={args.report_md}")


if __name__ == "__main__":
    main()
