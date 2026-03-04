from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.router_policy_v1 import sha256_file, write_json


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export a single deployable router policy artifact (v1).")
    p.add_argument("--policy-seed", type=int, default=11, help="Phase-8 seed used as the policy source/seed.")
    p.add_argument("--phase8-out", type=Path, default=Path("outputs/router_phase8_strict_v1"))

    p.add_argument(
        "--calib-parquet",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/common/router_counterfactual_calib.parquet"),
    )
    p.add_argument(
        "--test-parquet",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/common/router_counterfactual_test.parquet"),
    )
    p.add_argument(
        "--static-features-calib",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/common/risk/features_calib.parquet"),
    )
    p.add_argument(
        "--static-features-test",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/common/risk/features_test.parquet"),
    )
    p.add_argument(
        "--probe-features-calib",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/router_eval/common/probe_features_calib.parquet"),
    )
    p.add_argument(
        "--probe-features-test",
        type=Path,
        default=Path("outputs/router_phase9_bench_v1/router_eval/common/probe_features_test.parquet"),
    )
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--out-dir", type=Path, default=Path("artifacts/router_policy_v1"))
    p.add_argument("--force", action="store_true")
    return p.parse_args()


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _load_source_policy(phase8_out: Path, seed: int) -> tuple[dict, dict]:
    root = phase8_out / "seeds" / f"seed_{seed}" / "mixed"
    conf = root / "conformal_strict_v2" / "policy_metrics.json"
    probe = root / "probe_strict_v2" / "policy_metrics.json"
    if not conf.exists():
        raise FileNotFoundError(f"Missing Phase-8 conformal policy metrics: {conf}")
    if not probe.exists():
        raise FileNotFoundError(f"Missing Phase-8 probe policy metrics: {probe}")
    return _read_json(conf), _read_json(probe)


def _merge_conformal_tables(calib_cf: Path, test_cf: Path, static_calib: Path, static_test: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    for p in (calib_cf, test_cf, static_calib, static_test):
        if not p.exists():
            raise FileNotFoundError(p)
    c = pd.read_parquet(calib_cf)
    t = pd.read_parquet(test_cf)
    fc = pd.read_parquet(static_calib)
    ft = pd.read_parquet(static_test)
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
        "q_rel",
        "c",
    ]
    miss = int(c[need].isna().sum().sum()) + int(t[need].isna().sum().sum())
    if miss != 0:
        raise RuntimeError(f"Missing conformal features after merge: {miss}")
    return c, t


def _merge_probe_tables(
    calib_cf: Path,
    test_cf: Path,
    static_calib: Path,
    static_test: Path,
    probe_calib: Path,
    probe_test: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    for p in (calib_cf, test_cf, static_calib, static_test, probe_calib, probe_test):
        if not p.exists():
            raise FileNotFoundError(p)
    c = pd.read_parquet(calib_cf)
    t = pd.read_parquet(test_cf)
    fc = pd.read_parquet(static_calib)
    ft = pd.read_parquet(static_test)
    pc = pd.read_parquet(probe_calib)
    pt = pd.read_parquet(probe_test)
    c = c.merge(fc, on=["sample_name", "difficulty"], how="inner").merge(pc, on=["sample_name", "difficulty"], how="left")
    t = t.merge(ft, on=["sample_name", "difficulty"], how="inner").merge(pt, on=["sample_name", "difficulty"], how="left")
    probe_cols = [c for c in pc.columns if c.startswith("probe_")]
    miss = int(c[probe_cols].isna().sum().sum()) + int(t[probe_cols].isna().sum().sum())
    if miss != 0:
        raise RuntimeError(f"Missing probe features after merge: {miss}")
    return c, t


def _conformal_feature_spec() -> tuple[list[str], list[str]]:
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
    return feat_num, feat_cat


def _probe_feature_spec() -> tuple[list[str], list[str]]:
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
        "L_fast",
        "T_fast_ms",
        "search_fast_ms",
        "path_len_fast",
        "ood_family",
    ]
    feat_cat = ["difficulty", "source_dataset", "scenario", "map_id"]
    return feat_num, feat_cat


def _build_xy(df_cal: pd.DataFrame, df_test: pd.DataFrame, feat_num: list[str], feat_cat: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    x_cal = pd.get_dummies(df_cal[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_test = pd.get_dummies(df_test[feat_num + feat_cat], columns=feat_cat, drop_first=False)
    x_test = x_test.reindex(columns=x_cal.columns, fill_value=0)
    return x_cal, x_test


def _split_conformal_offsets(calib_df: pd.DataFrame, y_cal: np.ndarray, p_cal: np.ndarray, alpha: float) -> dict[str, float]:
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


def _apply_probe_k_by_diff(
    df: pd.DataFrame, score: np.ndarray, use_p5_fast: np.ndarray, k_by_diff: dict[str, int]
) -> tuple[np.ndarray, dict[str, float]]:
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


def _policy_static_feature_args() -> dict:
    # Must match `scripts/run_router_diagnosis.py:_default_router_args`.
    ns = SimpleNamespace(
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
    return dict(ns.__dict__)


def _dump_joblib(path: Path, obj: object) -> None:
    try:
        import joblib  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependency: joblib (required for policy export)") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, path)


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    policy_json = out_dir / "policy.json"
    sha_path = out_dir / "POLICY.sha256"
    if (not bool(args.force)) and policy_json.exists() and sha_path.exists():
        print(f"[export_policy_v1] exists: {policy_json}")
        return

    conf_src, probe_src = _load_source_policy(phase8_out=args.phase8_out, seed=int(args.policy_seed))
    conf_sel = conf_src["selected_policy"]
    probe_sel = probe_src["selected_policy"]

    if bool(probe_sel.get("oracle_assist_used", False)):
        raise RuntimeError(
            f"Selected Phase-8 probe policy uses oracle assist (not deployable). Choose a different seed. seed={args.policy_seed}"
        )

    # Load merged frames.
    conf_cal, conf_test = _merge_conformal_tables(
        calib_cf=args.calib_parquet,
        test_cf=args.test_parquet,
        static_calib=args.static_features_calib,
        static_test=args.static_features_test,
    )
    probe_cal, probe_test = _merge_probe_tables(
        calib_cf=args.calib_parquet,
        test_cf=args.test_parquet,
        static_calib=args.static_features_calib,
        static_test=args.static_features_test,
        probe_calib=args.probe_features_calib,
        probe_test=args.probe_features_test,
    )

    eps = float(args.epsilon_rel)

    # --- Conformal violation classifier (p_hat) ---
    conf_feat_num, conf_feat_cat = _conformal_feature_spec()
    x_conf_cal, x_conf_test = _build_xy(conf_cal, conf_test, feat_num=conf_feat_num, feat_cat=conf_feat_cat)
    y_conf_cal = (conf_cal["q_rel"].to_numpy(dtype=np.float64) > eps).astype(np.float64)

    gbc = GradientBoostingClassifier(
        random_state=int(args.policy_seed),
        n_estimators=500,
        learning_rate=0.04,
        max_depth=3,
        subsample=0.9,
    )
    gbc.fit(x_conf_cal, y_conf_cal)
    p_cal = gbc.predict_proba(x_conf_cal)[:, 1].astype(np.float64)
    p_test = gbc.predict_proba(x_conf_test)[:, 1].astype(np.float64)

    alpha = float(conf_sel["alpha_conformal"])
    q_by_diff = _split_conformal_offsets(conf_cal, y_cal=y_conf_cal, p_cal=p_cal, alpha=alpha)
    p_cal_u = np.clip(p_cal + np.array([q_by_diff[d] for d in conf_cal["difficulty"]], dtype=np.float64), 0.0, 1.0)
    p_test_u = np.clip(p_test + np.array([q_by_diff[d] for d in conf_test["difficulty"]], dtype=np.float64), 0.0, 1.0)

    # --- Cost model for c_hat (t_slow - t_fast) ---
    gbr_cost = GradientBoostingRegressor(
        random_state=int(args.policy_seed),
        n_estimators=700,
        learning_rate=0.04,
        max_depth=3,
        subsample=0.9,
    )
    gbr_cost.fit(x_conf_cal, conf_cal["c"].to_numpy(dtype=np.float64))
    c_hat_cal = np.clip(gbr_cost.predict(x_conf_cal).astype(np.float64), 1e-6, None)
    c_hat_test = np.clip(gbr_cost.predict(x_conf_test).astype(np.float64), 1e-6, None)

    c_ref = float(np.median(conf_cal["c"].to_numpy(dtype=np.float64)))
    c_norm_cal = np.clip(c_hat_cal / max(c_ref, 1e-6), 1e-6, None)
    c_norm_test = np.clip(c_hat_test / max(c_ref, 1e-6), 1e-6, None)

    a = float(conf_sel["score_power_a"])
    b = float(conf_sel["score_cost_power_b"])
    u_cal = (np.clip(p_cal_u, 1e-9, 1.0) ** a) / (c_norm_cal**b)
    u_test = (np.clip(p_test_u, 1e-9, 1.0) ** a) / (c_norm_test**b)
    u_cal = (u_cal + np.arange(len(u_cal), dtype=np.float64) * 1e-12).astype(np.float64)
    u_test = (u_test + np.arange(len(u_test), dtype=np.float64) * 1e-12).astype(np.float64)

    k_conf = {k: int(v) for k, v in conf_sel["k_slow_by_difficulty"].items()}
    use_fast_cal, tau_conf = _apply_k_by_diff(conf_cal, u_cal, k_by_diff=k_conf)

    # Apply tau thresholds on test.
    diff_test = conf_test["difficulty"].to_numpy()
    use_fast_test = np.ones(len(conf_test), dtype=bool)
    for d in ("easy", "medium", "hard"):
        mask = diff_test == d
        use_fast_test[mask] = u_test[mask] <= float(tau_conf.get(d, float("inf")))

    # --- Probe gain regressor + flip policy ---
    probe_feat_num, probe_feat_cat = _probe_feature_spec()
    x_probe_cal, x_probe_test = _build_xy(probe_cal, probe_test, feat_num=probe_feat_num, feat_cat=probe_feat_cat)

    t_ref = float(np.median(probe_cal["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(probe_cal["q_rel"].to_numpy(dtype=np.float64), 0.0)
    nz = q_pos[q_pos > 1e-9]
    q_med = float(np.median(nz)) if nz.size > 0 else 1.0
    beta = float(
        np.clip(
            np.median(probe_cal["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)) / max(q_med, 1e-9),
            1e-3,
            200.0,
        )
    )
    j_fast_cal = probe_cal["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + beta * np.maximum(
        probe_cal["q_rel"].to_numpy(dtype=np.float64), 0.0
    )
    j_slow_cal = probe_cal["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
    y_gain = np.maximum(j_fast_cal - j_slow_cal, 0.0)

    gbr_gain = GradientBoostingRegressor(
        random_state=int(args.policy_seed),
        n_estimators=700,
        learning_rate=0.04,
        max_depth=3,
        subsample=0.9,
    )
    gbr_gain.fit(x_probe_cal, y_gain)

    gain_cal = np.clip(gbr_gain.predict(x_probe_cal).astype(np.float64), 0.0, None)
    gain_test = np.clip(gbr_gain.predict(x_probe_test).astype(np.float64), 0.0, None)

    hard_cal = (probe_cal["difficulty"].to_numpy() == "hard").astype(np.float64)
    hard_test = (probe_test["difficulty"].to_numpy() == "hard").astype(np.float64)
    bottle_cal = np.clip(probe_cal["probe_bottleneck_rate"].to_numpy(dtype=np.float64), 0.0, 1.0)
    bottle_test = np.clip(probe_test["probe_bottleneck_rate"].to_numpy(dtype=np.float64), 0.0, 1.0)
    stall_cal = np.clip(1.0 - probe_cal["probe_h_drop_ratio"].to_numpy(dtype=np.float64), 0.0, 1.0)
    stall_test = np.clip(1.0 - probe_test["probe_h_drop_ratio"].to_numpy(dtype=np.float64), 0.0, 1.0)

    gain_power = float(probe_sel["gain_power"])
    w_hard = float(probe_sel["w_hard"])
    w_bottle = float(probe_sel["w_bottleneck"])
    w_stall = float(probe_sel["w_stall"])

    mult_cal = 1.0 + w_hard * hard_cal + w_bottle * bottle_cal + w_stall * stall_cal
    mult_test = 1.0 + w_hard * hard_test + w_bottle * bottle_test + w_stall * stall_test
    s_cal = (gain_cal ** gain_power) * mult_cal + (np.arange(len(gain_cal), dtype=np.float64) * 1e-12)
    s_test = (gain_test ** gain_power) * mult_test + (np.arange(len(gain_test), dtype=np.float64) * 1e-12)

    k_probe = {k: int(v) for k, v in probe_sel["k_slow_by_difficulty"].items()}
    use_fast_final_cal, tau_probe = _apply_probe_k_by_diff(
        probe_cal,
        s_cal.astype(np.float64),
        use_p5_fast=use_fast_cal,
        k_by_diff=k_probe,
    )

    # Apply probe thresholds on test.
    diff_test2 = probe_test["difficulty"].to_numpy()
    use_fast_final_test = use_fast_test.copy()
    for d in ("easy", "medium", "hard"):
        mask = (diff_test2 == d) & use_fast_test
        use_fast_final_test[mask] = s_test[mask] <= float(tau_probe.get(d, float("inf")))

    # Persist models.
    m_conf_path = out_dir / "conformal_violation_clf.joblib"
    m_cost_path = out_dir / "cost_regressor.joblib"
    m_gain_path = out_dir / "probe_gain_regressor.joblib"
    _dump_joblib(m_conf_path, gbc)
    _dump_joblib(m_cost_path, gbr_cost)
    _dump_joblib(m_gain_path, gbr_gain)

    model_sha = {
        "conformal_violation_clf": sha256_file(m_conf_path),
        "cost_regressor": sha256_file(m_cost_path),
        "probe_gain_regressor": sha256_file(m_gain_path),
    }

    # Difficulty priors from calibration.
    diff_counts = conf_cal["difficulty"].value_counts().to_dict()
    diff_prior = {k: float(v / max(len(conf_cal), 1)) for k, v in diff_counts.items()}

    policy = {
        "version": "router_policy_v1",
        "created_unix_s": int(time.time()),
        "protocol": {"name": "router_protocol_v1", "epsilon_rel": float(eps)},
        "source": {
            "phase8_out": str(Path(args.phase8_out)),
            "policy_seed": int(args.policy_seed),
            "phase8_conformal_policy_version": str(conf_src.get("version", "")),
            "phase8_probe_policy_version": str(probe_src.get("version", "")),
        },
        "difficulty_prior": diff_prior,
        "static_feature_args": _policy_static_feature_args(),
        "models": {
            "conformal_violation_clf": {
                "type": "sklearn.GradientBoostingClassifier",
                "joblib": m_conf_path.name,
                "sha256": model_sha["conformal_violation_clf"],
                "columns": list(x_conf_cal.columns),
                "feature_num": conf_feat_num,
                "feature_cat": conf_feat_cat,
                "y_def": f"(q_rel > {eps})",
            },
            "cost_regressor": {
                "type": "sklearn.GradientBoostingRegressor",
                "joblib": m_cost_path.name,
                "sha256": model_sha["cost_regressor"],
                "columns": list(x_conf_cal.columns),
                "feature_num": conf_feat_num,
                "feature_cat": conf_feat_cat,
                "target_def": "c = T_slow_ms - T_fast_ms",
            },
            "probe_gain_regressor": {
                "type": "sklearn.GradientBoostingRegressor",
                "joblib": m_gain_path.name,
                "sha256": model_sha["probe_gain_regressor"],
                "columns": list(x_probe_cal.columns),
                "feature_num": probe_feat_num,
                "feature_cat": probe_feat_cat,
                "target_def": "J_gain_pos = max(J_fast - J_slow, 0)",
            },
        },
        "conformal": {
            "alpha_conformal": float(alpha),
            "score_power_a": float(a),
            "score_cost_power_b": float(b),
            "q_by_difficulty": {k: float(v) for k, v in q_by_diff.items()},
            "k_slow_by_difficulty": {k: int(v) for k, v in k_conf.items()},
            "c_ref_calib_median_ms": float(c_ref),
            "tau_by_difficulty": {k: float(v) for k, v in tau_conf.items()},
            "rule": "U = (p_upper^a) / (c_norm^b); fast iff U <= tau_d",
            "p_upper_def": "p_upper = clip(p_hat + q_difficulty, 0, 1)",
            "c_norm_def": "c_norm = clip(c_hat_ms / c_ref, 1e-6, inf)",
        },
        "probe": {
            "max_expansions": 96,
            "gain_power": float(gain_power),
            "w_hard": float(w_hard),
            "w_bottleneck": float(w_bottle),
            "w_stall": float(w_stall),
            "k_slow_by_difficulty": {k: int(v) for k, v in k_probe.items()},
            "tau_by_difficulty": {k: float(v) for k, v in tau_probe.items()},
            "rule": "start from conformal; if fast then flip to slow when probe_score > tau_d",
            "probe_score_def": "probe_score = (pred_gain^gain_power) * (1 + w_hard*I_hard + w_bottleneck*bottleneck + w_stall*stall)",
        },
        "export_debug": {
            "calib": {
                "conformal_fast_ratio": float(np.mean(use_fast_cal)),
                "probe_fast_ratio": float(np.mean(use_fast_final_cal)),
                "conformal_tau": {k: float(v) for k, v in tau_conf.items()},
                "probe_tau": {k: float(v) for k, v in tau_probe.items()},
            },
            "test": {
                "conformal_fast_ratio": float(np.mean(use_fast_test)),
                "probe_fast_ratio": float(np.mean(use_fast_final_test)),
            },
        },
        "runtime": {"export_seconds": float(time.perf_counter() - t0)},
    }

    write_json(policy_json, policy)
    policy_sha = sha256_file(policy_json)
    sha_path.write_text(f"{policy_sha}  policy.json\n", encoding="utf-8")

    print(f"[export_policy_v1] wrote: {policy_json}")
    print(f"[export_policy_v1] sha256(policy.json)={policy_sha}")
    print(f"[export_policy_v1] models: {m_conf_path.name}, {m_cost_path.name}, {m_gain_path.name}")


if __name__ == "__main__":
    main()

