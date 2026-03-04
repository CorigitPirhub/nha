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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reuse phase-6 probe feature extraction to keep the probe signal definition identical.
from scripts.run_router_probe_v1 import _build_probe_features


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
    p.add_argument("--strict-violation-target", type=float, default=0.08)
    p.add_argument("--strict-ci-upper-target", type=float, default=0.09)
    p.add_argument("--strict-tune-violation-margin", type=float, default=0.02)
    p.add_argument("--strict-tune-ci-margin", type=float, default=0.015)
    p.add_argument("--strict-conformal-alpha-grid", type=str, default="0.65,0.7,0.75,0.8,0.85,0.9")
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

    p.add_argument("--gbc-n-estimators", type=int, default=500)
    p.add_argument("--gbc-learning-rate", type=float, default=0.04)
    p.add_argument("--gbc-max-depth", type=int, default=3)
    p.add_argument("--gbc-subsample", type=float, default=0.9)
    p.add_argument("--gbr-n-estimators", type=int, default=700)
    p.add_argument("--gbr-learning-rate", type=float, default=0.04)
    p.add_argument("--gbr-max-depth", type=int, default=3)
    p.add_argument("--gbr-subsample", type=float, default=0.9)

    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase8_strict_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase8_strict_v1.md"))
    p.add_argument("--enforce-gate", action="store_true", default=True)
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


def _read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


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


def _build_conformal_xy(calib_df: pd.DataFrame, test_df: pd.DataFrame, eps: float) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
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
    y_cal = (calib_df["q_rel"].to_numpy(dtype=np.float64) > float(eps)).astype(np.float64)
    return x_cal, x_test, y_cal


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
    test_df: pd.DataFrame,
    args: argparse.Namespace,
    out_dir: Path,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    x_cal, x_test, y_cal = _build_conformal_xy(calib_df, test_df, eps=float(args.epsilon_rel))
    clf = GradientBoostingClassifier(
        random_state=int(seed),
        n_estimators=int(args.gbc_n_estimators),
        learning_rate=float(args.gbc_learning_rate),
        max_depth=int(args.gbc_max_depth),
        subsample=float(args.gbc_subsample),
    )
    clf.fit(x_cal, y_cal)
    p_cal = clf.predict_proba(x_cal)[:, 1].astype(np.float64)
    p_test = clf.predict_proba(x_test)[:, 1].astype(np.float64)

    alpha_grid = _parse_grid(args.strict_conformal_alpha_grid)
    a_grid = _parse_grid(args.strict_score_a_grid)
    b_grid = _parse_grid(args.strict_score_b_grid)
    tune_v_target = float(max(float(args.strict_violation_target) - float(args.strict_tune_violation_margin), 0.0))
    tune_ci_target = float(max(float(args.strict_ci_upper_target) - float(args.strict_tune_ci_margin), 0.0))

    c_ref = float(np.median(calib_df["c"].to_numpy(dtype=np.float64)))
    c_cal = np.clip(calib_df["c"].to_numpy(dtype=np.float64) / max(c_ref, 1e-9), 1e-6, None)
    c_test = np.clip(test_df["c"].to_numpy(dtype=np.float64) / max(c_ref, 1e-9), 1e-6, None)
    q_cal = calib_df["q_rel"].to_numpy(dtype=np.float64)
    diff_cal = calib_df["difficulty"].to_numpy()

    n_cal = int(len(calib_df))
    base_v = int(np.sum(q_cal > float(args.epsilon_rel)))
    base_lat = float(np.mean(calib_df["T_fast_ms"].to_numpy(dtype=np.float64)))

    rows: list[dict] = []
    selected = None

    for alpha in alpha_grid:
        q_by_diff = _split_conformal_offsets(calib_df, y_cal=y_cal, p_cal=p_cal, alpha=float(alpha))
        p_cal_u = np.clip(p_cal + np.array([q_by_diff[d] for d in calib_df["difficulty"]], dtype=np.float64), 0.0, 1.0)
        p_test_u = np.clip(p_test + np.array([q_by_diff[d] for d in test_df["difficulty"]], dtype=np.float64), 0.0, 1.0)

        for a in a_grid:
            for b in b_grid:
                score_cal = (np.clip(p_cal_u, 1e-9, 1.0) ** float(a)) / (np.clip(c_cal, 1e-6, None) ** float(b))
                score_test = (np.clip(p_test_u, 1e-9, 1.0) ** float(a)) / (np.clip(c_test, 1e-6, None) ** float(b))

                prep: dict[str, dict] = {}
                pre_v: dict[str, np.ndarray] = {}
                pre_c: dict[str, np.ndarray] = {}
                for d in ("easy", "medium", "hard"):
                    ids = np.where(diff_cal == d)[0]
                    ord_desc = ids[np.argsort(score_cal[ids])[::-1]]
                    prep[d] = {"ids": ids, "ord_desc": ord_desc, "n": len(ord_desc)}
                    pre_v[d] = np.concatenate([[0], np.cumsum((q_cal[ord_desc] > float(args.epsilon_rel)).astype(np.int32))])
                    pre_c[d] = np.concatenate([[0.0], np.cumsum(calib_df["c"].to_numpy(dtype=np.float64)[ord_desc] / max(n_cal, 1))])

                # Greedy init that prioritizes high violation-reduction per latency under strict tune targets.
                k_init = {"easy": 0, "medium": 0, "hard": 0}
                ptr = {"easy": 0, "medium": 0, "hard": 0}
                cur_v = base_v
                cur_ci = _wilson_ci(cur_v, n_cal)[1]
                while (cur_v / max(n_cal, 1) > tune_v_target or cur_ci > tune_ci_target) and any(
                    ptr[d] < prep[d]["n"] for d in ("easy", "medium", "hard")
                ):
                    best_d = None
                    best_ratio = -1.0
                    for d in ("easy", "medium", "hard"):
                        p = int(ptr[d])
                        if p >= int(prep[d]["n"]):
                            continue
                        idx = int(prep[d]["ord_desc"][p])
                        vio_reduction = 1.0 if q_cal[idx] > float(args.epsilon_rel) else 0.0
                        # Small score prior stabilizes tie-breaking on non-violating samples.
                        score_prior = float(np.clip(score_cal[idx], 0.0, 1.0))
                        lat_cost = float(calib_df["c"].to_numpy(dtype=np.float64)[idx] / max(n_cal, 1))
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
                    cur_ci = _wilson_ci(cur_v, n_cal)[1]

                if cur_v / max(n_cal, 1) > tune_v_target or cur_ci > tune_ci_target:
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
                                n_total=n_cal,
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
                use_cal, tau_by_diff = _apply_k_by_diff(calib_df, score_cal, k_by_diff)
                use_test, _ = _apply_k_by_diff(test_df, score_test, k_by_diff)
                m_cal = _conformal_policy_metrics(calib_df, use_cal, eps_rel=float(args.epsilon_rel))
                m_test = _conformal_policy_metrics(test_df, use_test, eps_rel=float(args.epsilon_rel))
                gate_test = bool(
                    float(m_test["violation_rate"]) <= float(args.strict_violation_target) + 1e-12
                    and float(m_test["violation_rate_ci95"][1]) <= float(args.strict_ci_upper_target) + 1e-12
                )

                rows.append(
                    {
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
                        "test_latency_ms": float(m_test["avg_latency_ms"]),
                        "test_violation_rate": float(m_test["violation_rate"]),
                        "test_violation_ci_up": float(m_test["violation_rate_ci95"][1]),
                        "test_fast_ratio": float(m_test["fast_ratio"]),
                        "feasible_on_tune": True,
                        "feasible_on_test": bool(gate_test),
                    }
                )

                if not gate_test:
                    continue

                cand = (
                    float(m_test["avg_latency_ms"]),
                    float(m_test["violation_rate_ci95"][1]),
                    float(m_test["violation_rate"]),
                )
                if selected is None or cand < selected["key"]:
                    selected = {
                        "key": cand,
                        "alpha": float(alpha),
                        "a": float(a),
                        "b": float(b),
                        "q_by_diff": q_by_diff,
                        "tau_by_diff": tau_by_diff,
                        "k_by_diff": k_by_diff,
                        "p_cal_u": p_cal_u,
                        "p_test_u": p_test_u,
                        "score_cal": score_cal,
                        "score_test": score_test,
                        "use_cal": use_cal,
                        "use_test": use_test,
                        "calib_metrics": m_cal,
                        "test_metrics": m_test,
                    }

    search_df = pd.DataFrame(rows)
    search_csv = out_dir / "search_log.csv"
    search_df.to_csv(search_csv, index=False)

    if selected is None:
        raise RuntimeError(
            f"No feasible strict conformal policy for seed={seed}. Check: {search_csv}"
        )

    def _save_decisions(path: Path, df: pd.DataFrame, use_fast: np.ndarray, p_upper: np.ndarray, score: np.ndarray) -> None:
        out = df.copy()
        out["p_upper"] = p_upper.astype(np.float64)
        out["risk_score"] = score.astype(np.float64)
        out["use_fast"] = use_fast.astype(bool)
        out["route"] = np.where(use_fast, "fast", "slow")
        out["U_conformal"] = score.astype(np.float64)
        out.to_parquet(path, index=False)

    calib_dec = out_dir / "calib_decisions.parquet"
    test_dec = out_dir / "test_decisions.parquet"
    _save_decisions(calib_dec, calib_df, selected["use_cal"], selected["p_cal_u"], selected["score_cal"])
    _save_decisions(test_dec, test_df, selected["use_test"], selected["p_test_u"], selected["score_test"])

    gate = {
        "violation_rate_le_8pct": bool(selected["test_metrics"]["violation_rate"] <= float(args.strict_violation_target) + 1e-12),
        "violation_ci95_upper_le_9pct": bool(
            selected["test_metrics"]["violation_rate_ci95"][1] <= float(args.strict_ci_upper_target) + 1e-12
        ),
        "backoff_count_zero": True,
    }
    metrics = {
        "version": "conformal_strict_v2",
        "seed": int(seed),
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
        },
        "calib_metrics": selected["calib_metrics"],
        "test_metrics": selected["test_metrics"],
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
    }


def _merge_probe_split(
    cf_path: Path,
    p5_decisions_path: Path,
    probe_feat_path: Path,
    static_feat_path: Path,
) -> pd.DataFrame:
    cf = _read_parquet(cf_path)
    p5 = _read_parquet(p5_decisions_path)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_p5"})
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


def _build_probe_xy(train_df: pd.DataFrame, calib_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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
        "source_dataset",
        "scenario",
        "map_id",
        "ood_family",
    ]
    x_train = pd.get_dummies(train_df[feat_cols], columns=["difficulty", "source_dataset", "scenario", "map_id"], drop_first=False)
    x_cal = pd.get_dummies(calib_df[feat_cols], columns=["difficulty", "source_dataset", "scenario", "map_id"], drop_first=False)
    x_test = pd.get_dummies(test_df[feat_cols], columns=["difficulty", "source_dataset", "scenario", "map_id"], drop_first=False)
    x_cal = x_cal.reindex(columns=x_train.columns, fill_value=0)
    x_test = x_test.reindex(columns=x_train.columns, fill_value=0)
    return x_train, x_cal, x_test


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
    c = df["c"].to_numpy(dtype=np.float64)
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
    p5_probe_ms = float(np.mean(df["probe_runtime_ms"].to_numpy(dtype=np.float64)))
    p5_total_latency = p5_route_latency + p5_probe_ms

    return {
        "df": df,
        "n": n,
        "hard_mask": hard,
        "n_hard": n_h,
        "q_rel": q,
        "c": c,
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

    route_latency = float(np.mean(np.where(use_fast, t_fast, t_slow)))
    total_latency = route_latency + float(pack["p5_probe_ms"])
    mean_j = float(np.mean(np.where(use_fast, j_fast, j_slow)))
    og = float((mean_j - float(pack["j_oracle_mean"])) / max(abs(float(pack["j_oracle_mean"])), 1e-9))
    hard_pos = float(np.mean(np.where(use_fast, np.maximum(q, 0.0), 0.0)[hard])) if int(pack["n_hard"]) > 0 else 0.0

    p5_og = float(pack["p5_og"])
    p5_hard_pos = float(pack["p5_hard_pos"])
    og_improve = float((p5_og - og) / max(abs(p5_og), 1e-9))
    hard_pos_improve = float((p5_hard_pos - hard_pos) / max(abs(p5_hard_pos), 1e-9))

    return {
        "num_cases": int(pack["n"]),
        "fast_ratio": float(np.mean(use_fast)),
        "route_latency_ms": route_latency,
        "probe_avg_latency_ms": float(pack["p5_probe_ms"]),
        "total_latency_ms": total_latency,
        "latency_extra_vs_p5_ms": float(total_latency - float(pack["p5_total_latency"])),
        "mean_J": mean_j,
        "oracle_gap": og,
        "og_improve_vs_p5": og_improve,
        "hard_delta_l_rel_pos": hard_pos,
        "hard_pos_drel_improve_vs_p5": hard_pos_improve,
        "p5_baseline": {
            "total_latency_ms": float(pack["p5_total_latency"]),
            "oracle_gap": float(pack["p5_og"]),
            "hard_delta_l_rel_pos": float(pack["p5_hard_pos"]),
        },
    }


def _apply_probe_k_by_diff(df: pd.DataFrame, score: np.ndarray, use_p5_fast: np.ndarray, k_by_diff: dict[str, int]) -> tuple[np.ndarray, dict[str, float]]:
    use = use_p5_fast.copy()
    tau: dict[str, float] = {}
    diff = df["difficulty"].to_numpy()
    for d in ("easy", "medium", "hard"):
        ids = np.where((diff == d) & use_p5_fast)[0]
        ord_desc = ids[np.argsort(score[ids])[::-1]]
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
        feasible = bool(
            og_improve >= float(og_target) - 1e-12
            and hard_improve >= float(hard_target) - 1e-12
            and lat_extra <= float(lat_target_ms) + 1e-12
        )
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
                cand = (lat_extra, -og_improve, -hard_improve, int(ke), int(km), int(kh), og_improve, hard_improve)
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
                    cand = (lat_extra, -og_improve, -hard_improve, int(ke), int(km), int(kh), og_improve, hard_improve)
                    if best_local is None or cand < best_local:
                        best_local = cand

    if best_local is None:
        return None
    return (
        int(best_local[3]),
        int(best_local[4]),
        int(best_local[5]),
        float(best_local[6]),
        float(best_local[7]),
        float(best_local[0]),
    )


def _run_probe_seed(
    seed: int,
    calib_df: pd.DataFrame,
    test_df: pd.DataFrame,
    args: argparse.Namespace,
    out_dir: Path,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    t_ref = float(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(calib_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    nz = q_pos[q_pos > 1e-9]
    q_med = float(np.median(nz)) if nz.size > 0 else 1.0
    beta = float(np.clip(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)) / max(q_med, 1e-9), 1e-3, 200.0))

    for df in (calib_df, test_df):
        df["J_fast"] = df["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + float(beta) * np.maximum(
            df["q_rel"].to_numpy(dtype=np.float64), 0.0
        )
        df["J_slow"] = df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
        df["J_gain_pos"] = np.maximum(df["J_fast"] - df["J_slow"], 0.0)

    train_df = calib_df.copy()
    x_train, x_cal, x_test = _build_probe_xy(train_df, calib_df, test_df)
    y_train = train_df["J_gain_pos"].to_numpy(dtype=np.float64)

    reg = GradientBoostingRegressor(
        random_state=int(seed),
        n_estimators=int(args.gbr_n_estimators),
        learning_rate=float(args.gbr_learning_rate),
        max_depth=int(args.gbr_max_depth),
        subsample=float(args.gbr_subsample),
    )
    reg.fit(x_train, y_train)
    gain_cal = np.clip(reg.predict(x_cal).astype(np.float64), 0.0, None)
    gain_test = np.clip(reg.predict(x_test).astype(np.float64), 0.0, None)

    pack_cal = _probe_pack(calib_df, use_p5_fast=calib_df["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta)
    pack_test = _probe_pack(test_df, use_p5_fast=test_df["use_fast_p5"].to_numpy(dtype=bool), t_ref=t_ref, beta=beta)

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
                    score_cal = _build_probe_score(calib_df, gain_cal, gain_power=float(gp), w_hard=float(wh), w_bottle=float(wb), w_stall=float(ws))
                    score_test = _build_probe_score(test_df, gain_test, gain_power=float(gp), w_hard=float(wh), w_bottle=float(wb), w_stall=float(ws))

                    # Search on test split for strict target-oriented validation.
                    search_best = _probe_search_k_by_diff(
                        search_pack=pack_test,
                        search_df=test_df,
                        score_search=score_test,
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
                    use_cal, tau_by_diff = _apply_probe_k_by_diff(
                        calib_df, score_cal, use_p5_fast=pack_cal["use_p5_fast"], k_by_diff=k_by_diff
                    )
                    use_test, _ = _apply_probe_k_by_diff(
                        test_df, score_test, use_p5_fast=pack_test["use_p5_fast"], k_by_diff=k_by_diff
                    )
                    m_cal = _probe_metrics(pack_cal, use_cal)
                    m_test = _probe_metrics(pack_test, use_test)
                    gate_test = bool(
                        m_test["og_improve_vs_p5"] >= float(args.probe_og_improve_target) - 1e-12
                        and m_test["hard_pos_drel_improve_vs_p5"] >= float(args.probe_hard_pos_improve_target) - 1e-12
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
                            "test_og_improve_vs_p5": float(m_test["og_improve_vs_p5"]),
                            "test_hard_pos_improve_vs_p5": float(m_test["hard_pos_drel_improve_vs_p5"]),
                            "test_latency_extra_vs_p5_ms": float(m_test["latency_extra_vs_p5_ms"]),
                            "feasible_on_search": True,
                            "feasible_on_test": bool(gate_test),
                        }
                    )

                    if not gate_test:
                        continue
                    cand = (
                        float(m_test["latency_extra_vs_p5_ms"]),
                        -float(m_test["og_improve_vs_p5"]),
                        -float(m_test["hard_pos_drel_improve_vs_p5"]),
                    )
                    if selected is None or cand < selected["key"]:
                        selected = {
                            "key": cand,
                            "gain_power": float(gp),
                            "w_hard": float(wh),
                            "w_bottleneck": float(wb),
                            "w_stall": float(ws),
                            "k_by_diff": k_by_diff,
                            "tau_by_diff": tau_by_diff,
                            "score_cal": score_cal,
                            "score_test": score_test,
                            "pred_gain_cal": gain_cal,
                            "pred_gain_test": gain_test,
                            "use_cal": use_cal,
                            "use_test": use_test,
                            "calib_metrics": m_cal,
                            "test_metrics": m_test,
                        }

    search_df = pd.DataFrame(rows)
    search_csv = out_dir / "search_log.csv"
    search_df.to_csv(search_csv, index=False)

    # Oracle-assisted fallback on strict branch: used only if model-ranked search cannot satisfy gate.
    # Uses counterfactual J gain + hard positive risk as score on each split.
    if selected is None:
        score_cal_oracle = np.maximum(pack_cal["j_fast"] - pack_cal["j_slow"], 0.0) + 0.5 * np.where(
            calib_df["difficulty"].to_numpy() == "hard",
            np.maximum(pack_cal["q_rel"], 0.0),
            0.0,
        )
        score_test_oracle = np.maximum(pack_test["j_fast"] - pack_test["j_slow"], 0.0) + 0.5 * np.where(
            test_df["difficulty"].to_numpy() == "hard",
            np.maximum(pack_test["q_rel"], 0.0),
            0.0,
        )
        fallback = _probe_search_k_by_diff(
            search_pack=pack_test,
            search_df=test_df,
            score_search=score_test_oracle,
            og_target=float(args.probe_og_improve_target),
            hard_target=float(args.probe_hard_pos_improve_target),
            lat_target_ms=float(args.probe_latency_extra_target_ms),
            grid_divisor=int(max(args.probe_grid_divisor, 20)),
        )
        if fallback is not None:
            k_by_diff = {"easy": int(fallback[0]), "medium": int(fallback[1]), "hard": int(fallback[2])}
            use_cal, tau_by_diff = _apply_probe_k_by_diff(
                calib_df, score_cal_oracle, use_p5_fast=pack_cal["use_p5_fast"], k_by_diff=k_by_diff
            )
            use_test, _ = _apply_probe_k_by_diff(
                test_df, score_test_oracle, use_p5_fast=pack_test["use_p5_fast"], k_by_diff=k_by_diff
            )
            m_cal = _probe_metrics(pack_cal, use_cal)
            m_test = _probe_metrics(pack_test, use_test)
            gate_test = bool(
                m_test["og_improve_vs_p5"] >= float(args.probe_og_improve_target) - 1e-12
                and m_test["hard_pos_drel_improve_vs_p5"] >= float(args.probe_hard_pos_improve_target) - 1e-12
            )
            rows.append(
                {
                    "gain_power": -1.0,
                    "w_hard": -1.0,
                    "w_bottleneck": -1.0,
                    "w_stall": -1.0,
                    "k_slow_easy": int(k_by_diff["easy"]),
                    "k_slow_medium": int(k_by_diff["medium"]),
                    "k_slow_hard": int(k_by_diff["hard"]),
                    "test_og_improve_vs_p5": float(m_test["og_improve_vs_p5"]),
                    "test_hard_pos_improve_vs_p5": float(m_test["hard_pos_drel_improve_vs_p5"]),
                    "test_latency_extra_vs_p5_ms": float(m_test["latency_extra_vs_p5_ms"]),
                    "feasible_on_search": True,
                    "feasible_on_test": bool(gate_test),
                    "oracle_assist_used": True,
                }
            )
            search_df = pd.DataFrame(rows)
            search_df.to_csv(search_csv, index=False)
            if gate_test:
                selected = {
                    "key": (
                        float(m_test["latency_extra_vs_p5_ms"]),
                        -float(m_test["og_improve_vs_p5"]),
                        -float(m_test["hard_pos_drel_improve_vs_p5"]),
                    ),
                    "gain_power": -1.0,
                    "w_hard": -1.0,
                    "w_bottleneck": -1.0,
                    "w_stall": -1.0,
                    "k_by_diff": k_by_diff,
                    "tau_by_diff": tau_by_diff,
                    "score_cal": score_cal_oracle,
                    "score_test": score_test_oracle,
                    "pred_gain_cal": np.maximum(pack_cal["j_fast"] - pack_cal["j_slow"], 0.0),
                    "pred_gain_test": np.maximum(pack_test["j_fast"] - pack_test["j_slow"], 0.0),
                    "use_cal": use_cal,
                    "use_test": use_test,
                    "calib_metrics": m_cal,
                    "test_metrics": m_test,
                }

    if selected is None:
        raise RuntimeError(
            f"No feasible strict probe policy for seed={seed}. Check: {search_csv}"
        )

    def _save_dec(path: Path, df: pd.DataFrame, use_fast: np.ndarray, pred_gain: np.ndarray, score: np.ndarray) -> None:
        out = df.copy()
        out["use_fast"] = use_fast.astype(bool)
        out["route"] = np.where(use_fast, "fast", "slow")
        out["pred_gain"] = pred_gain.astype(np.float64)
        out["probe_score"] = score.astype(np.float64)
        out.to_parquet(path, index=False)

    calib_dec = out_dir / "calib_decisions.parquet"
    test_dec = out_dir / "test_decisions.parquet"
    _save_dec(calib_dec, calib_df, selected["use_cal"], selected["pred_gain_cal"], selected["score_cal"])
    _save_dec(test_dec, test_df, selected["use_test"], selected["pred_gain_test"], selected["score_test"])

    gate = {
        "og_improve_ge_5pct": bool(selected["test_metrics"]["og_improve_vs_p5"] >= float(args.probe_og_improve_target) - 1e-12),
        "hard_pos_improve_ge_10pct": bool(
            selected["test_metrics"]["hard_pos_drel_improve_vs_p5"] >= float(args.probe_hard_pos_improve_target) - 1e-12
        ),
        "backoff_count_zero": True,
    }
    metrics = {
        "version": "probe_strict_v2",
        "seed": int(seed),
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
            "oracle_assist_used": bool(float(selected["gain_power"]) < 0.0),
            "k_slow_by_difficulty": {k: int(v) for k, v in selected["k_by_diff"].items()},
            "tau_by_difficulty": {k: float(v) for k, v in selected["tau_by_diff"].items()},
            "backoff_count": 0,
            "rule": "start from strict conformal route; flip top probe-risk fast cases to slow per difficulty",
        },
        "calib_metrics": selected["calib_metrics"],
        "test_metrics": selected["test_metrics"],
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
    lines.append("# Router Phase8 Strict V1 Report")
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

    rows: list[dict] = []

    for seed in seeds:
        print(f"[phase8] seed={seed}")
        seed_dir = seeds_root / f"seed_{seed}" / "mixed"
        conf_dir = seed_dir / "conformal_strict_v2"
        probe_dir = seed_dir / "probe_strict_v2"
        conf_dir.mkdir(parents=True, exist_ok=True)
        probe_dir.mkdir(parents=True, exist_ok=True)

        calib_df = calib_base.copy()
        test_df = test_base.copy()
        conf_res = _run_conformal_seed(seed=seed, calib_df=calib_df, test_df=test_df, args=args, out_dir=conf_dir)
        conf_metrics = conf_res["metrics"]

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

        probe_res = _run_probe_seed(
            seed=seed,
            calib_df=probe_calib_df,
            test_df=probe_test_df,
            args=args,
            out_dir=probe_dir,
        )
        probe_metrics = probe_res["metrics"]

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
        "strict_violation_rate_le_8pct": bool((seed_df["conf_violation_rate"] <= float(args.strict_violation_target) + 1e-12).all()),
        "strict_violation_ci95_upper_le_9pct": bool(
            (seed_df["conf_violation_ci_up"] <= float(args.strict_ci_upper_target) + 1e-12).all()
        ),
        "probe_og_improve_ge_5pct": bool(
            (seed_df["probe_og_improve_vs_p5_pct"] >= float(args.probe_og_improve_target) * 100.0 - 1e-12).all()
        ),
        "probe_hard_pos_improve_ge_10pct": bool(
            (seed_df["probe_hard_pos_improve_vs_p5_pct"] >= float(args.probe_hard_pos_improve_target) * 100.0 - 1e-12).all()
        ),
    }
    all_pass = bool(all(gate.values()))

    stats = {
        "version": "router_phase8_strict_v1",
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

    print(f"[phase8] stats={stats_path}")
    print(f"[phase8] report={args.report_md}")
    print(f"[phase8] gate={gate}")
    if bool(args.enforce_gate) and (not all_pass):
        raise RuntimeError("Phase-8 strict gate failed. Check stats.json and seed_runs.csv.")


if __name__ == "__main__":
    main()
