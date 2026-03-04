from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.router_method_core import (
    ConformalStageConfig,
    ConformalStageRouter,
    CounterfactualSchema,
    ProbeFlipRouter,
    ProbeFlipStageConfig,
    RiskBudgetProtocol,
    derive_q_rel_and_c,
    router_metrics,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase21 minimal demo: risk-bounded adaptive compute routing (toy).")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--n-calib", type=int, default=1200)
    p.add_argument("--n-test", type=int, default=1200)
    p.add_argument("--epsilon-rel", type=float, default=0.015)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase21_neurips_positioning_v1"))
    p.add_argument("--write-parquet", action="store_true", help="Also write calib/test tables (for debugging).")
    return p.parse_args()


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _make_split(
    *,
    rng: np.random.Generator,
    n: int,
    epsilon_rel: float,
    split_name: str,
) -> pd.DataFrame:
    # Balanced groups.
    diffs = np.array(["easy", "medium", "hard"], dtype=object)
    difficulty = diffs[rng.integers(0, 3, size=n)]

    # Synthetic static features (roughly mimicking router features).
    global_occ_ratio = np.clip(rng.normal(loc=0.35, scale=0.18, size=n), 0.0, 1.0)
    local_occ_ratio = np.clip(rng.normal(loc=0.30, scale=0.20, size=n), 0.0, 1.0)
    line_block_ratio = np.clip(rng.normal(loc=0.25, scale=0.22, size=n), 0.0, 1.0)
    distance_ratio = np.clip(rng.normal(loc=0.65, scale=0.18, size=n), 0.05, 1.2)
    complexity_score = np.clip(
        0.40 * global_occ_ratio + 0.35 * local_occ_ratio + 0.25 * line_block_ratio + rng.normal(0.0, 0.05, size=n),
        0.0,
        1.0,
    )
    los_clear = (rng.random(n) > (0.15 + 0.60 * line_block_ratio)).astype(np.float64)

    # Task meta (categorical).
    source_dataset = np.array(["toy_v1"] * n, dtype=object)
    scenario = np.array(["nav"] * n, dtype=object)
    map_id = np.array([f"m{int(i)}" for i in rng.integers(0, 10, size=n)], dtype=object)
    ood_family = rng.integers(0, 3, size=n).astype(np.int64)

    # Latency model.
    base_fast = 4.0 + 2.0 * distance_ratio
    t_fast_ms = np.clip(base_fast + 6.0 * complexity_score + rng.normal(0.0, 0.6, size=n), 1.0, None)
    c_ms = np.clip(10.0 + 25.0 * complexity_score + rng.normal(0.0, 1.2, size=n), 2.0, None)
    t_slow_ms = t_fast_ms + c_ms

    # Quality model (slow is reference).
    l_slow = np.where(
        difficulty == "easy",
        rng.normal(loc=900.0, scale=120.0, size=n),
        np.where(difficulty == "medium", rng.normal(loc=2300.0, scale=260.0, size=n), rng.normal(loc=5200.0, scale=520.0, size=n)),
    )
    l_slow = np.clip(l_slow, 80.0, None).astype(np.float64)

    # Violation probability under fast.
    diff_bias = np.where(difficulty == "easy", -1.2, np.where(difficulty == "medium", -0.6, 0.0))
    logit = -2.0 + 3.8 * complexity_score + 1.2 * (1.0 - los_clear) + diff_bias + rng.normal(0.0, 0.35, size=n)
    p_vio = np.clip(_sigmoid(logit), 1e-4, 1.0 - 1e-4)
    y_vio = rng.random(n) < p_vio

    # Relative quality loss q_rel under fast.
    q_rel = np.zeros(n, dtype=np.float64)
    q_rel[~y_vio] = rng.uniform(-0.02, float(epsilon_rel) * 0.8, size=int(np.sum(~y_vio)))
    q_rel[y_vio] = rng.uniform(float(epsilon_rel) * 1.2, 0.30, size=int(np.sum(y_vio)))
    q_rel = np.clip(q_rel, -0.5, 2.0)

    l_fast = l_slow * (1.0 + q_rel)
    l_fast = np.clip(l_fast, 1.0, None)

    # A few additional "fast metrics" used in some feature lists.
    search_fast_ms = np.clip(t_fast_ms * rng.uniform(0.75, 0.95, size=n), 0.5, None)
    path_len_fast = np.clip(4.0 + 20.0 * distance_ratio + rng.normal(0.0, 1.0, size=n), 1.0, None)

    # Synthetic probe features: correlate with risk and potential gain.
    probe_runtime_ms = np.clip(0.6 + 2.2 * complexity_score + rng.normal(0.0, 0.2, size=n), 0.1, None)
    probe_expansions = np.clip(20.0 + 110.0 * complexity_score + rng.normal(0.0, 8.0, size=n), 1.0, None)
    probe_success = np.ones(n, dtype=np.float64)
    probe_expansion_ratio = np.clip(probe_expansions / np.maximum(l_slow / 60.0, 1.0), 0.0, 5.0)
    probe_h_drop_ratio = np.clip(0.75 - 0.55 * complexity_score + rng.normal(0.0, 0.08, size=n), 0.0, 1.0)
    probe_progress_per_exp = np.clip(0.08 + 0.40 * (1.0 - complexity_score) + rng.normal(0.0, 0.03, size=n), 0.0, None)
    probe_open_growth = np.clip(0.20 + 0.90 * complexity_score + rng.normal(0.0, 0.08, size=n), 0.0, None)
    probe_branching = np.clip(1.2 + 1.6 * complexity_score + rng.normal(0.0, 0.15, size=n), 0.1, None)
    probe_improve_rate = np.clip(0.10 + 0.90 * (1.0 - probe_h_drop_ratio) + rng.normal(0.0, 0.08, size=n), 0.0, None)
    probe_bottleneck_rate = np.clip(0.10 + 0.85 * complexity_score + rng.normal(0.0, 0.10, size=n), 0.0, 1.0)
    probe_deadend_rate = np.clip(0.05 + 0.60 * complexity_score + rng.normal(0.0, 0.05, size=n), 0.0, 1.0)

    df = pd.DataFrame(
        {
            "sample_name": [f"{split_name}_{i:06d}" for i in range(n)],
            "difficulty": difficulty,
            "source_dataset": source_dataset,
            "scenario": scenario,
            "map_id": map_id,
            "ood_family": ood_family,
            "line_block_ratio": line_block_ratio,
            "local_occ_ratio": local_occ_ratio,
            "global_occ_ratio": global_occ_ratio,
            "distance_ratio": distance_ratio,
            "complexity_score": complexity_score,
            "los_clear": los_clear,
            "L_fast": l_fast,
            "L_slow": l_slow,
            "T_fast_ms": t_fast_ms,
            "T_slow_ms": t_slow_ms,
            "search_fast_ms": search_fast_ms,
            "path_len_fast": path_len_fast,
            "q_rel": q_rel,
            "c": c_ms,
            # Probe features.
            "probe_success": probe_success,
            "probe_expansions": probe_expansions,
            "probe_runtime_ms": probe_runtime_ms,
            "probe_expansion_ratio": probe_expansion_ratio,
            "probe_h_drop_ratio": probe_h_drop_ratio,
            "probe_progress_per_exp": probe_progress_per_exp,
            "probe_open_growth": probe_open_growth,
            "probe_branching": probe_branching,
            "probe_improve_rate": probe_improve_rate,
            "probe_bottleneck_rate": probe_bottleneck_rate,
            "probe_deadend_rate": probe_deadend_rate,
        }
    )
    return df


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    protocol = RiskBudgetProtocol(epsilon_rel=float(args.epsilon_rel), alpha=float(args.alpha))
    schema = CounterfactualSchema()

    rng = np.random.default_rng(int(args.seed))
    calib_df = _make_split(rng=rng, n=int(args.n_calib), epsilon_rel=float(protocol.epsilon_rel), split_name="calib")
    test_df = _make_split(rng=rng, n=int(args.n_test), epsilon_rel=float(protocol.epsilon_rel), split_name="test")

    # Global scaling for J (same for all methods in this demo).
    t_ref = float(max(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64)), 1e-9))
    q_rel_cal, _ = derive_q_rel_and_c(calib_df, schema=schema)
    q_pos = np.maximum(q_rel_cal, 0.0)
    nz = q_pos[q_pos > 1e-9]
    q_med = float(np.median(nz)) if nz.size > 0 else 1.0
    beta = float(np.clip(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64) / t_ref) / max(q_med, 1e-9), 1e-3, 200.0))

    # --- Stage 1: static conformal+cost routing ---
    conf_cfg = ConformalStageConfig(
        protocol=protocol,
        schema=schema,
        alpha_conformal=0.10,  # 90% one-sided split conformal upper bound
        score_power_a=1.0,
        score_cost_power_b=1.0,
    )
    stage1 = ConformalStageRouter(
        cfg=conf_cfg,
        violation_clf=make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1200, solver="lbfgs"),
        ),
        cost_reg=make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=int(args.seed))),
        auto_select_k_by_risk=True,
    ).fit(calib_df)

    use_fast_conf_test, meta_conf = stage1.route(test_df)

    # --- Stage 2: probe flip (fast -> slow) ---
    probe_cfg = ProbeFlipStageConfig(
        schema=schema,
        gain_power=1.0,
        w_hard=0.60,
        w_bottleneck=0.40,
        w_stall=0.25,
    )
    # Flip a small number per group (demo): this should reduce J without increasing risk.
    k_probe = {"easy": 0, "medium": 8, "hard": 18}
    stage2 = ProbeFlipRouter(
        cfg=probe_cfg,
        base=stage1,
        gain_reg=make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=int(args.seed))),
        k_flip_to_slow_by_group=k_probe,
    ).fit(calib_df)

    use_fast_probe_test, meta_probe = stage2.route(test_df)

    # Baselines for comparison on the same synthetic table.
    forced_fast = np.ones(len(test_df), dtype=bool)
    forced_slow = np.zeros(len(test_df), dtype=bool)

    m_fast = router_metrics(test_df, use_fast=forced_fast, protocol=protocol, schema=schema, t_ref=t_ref, beta=beta)
    m_slow = router_metrics(test_df, use_fast=forced_slow, protocol=protocol, schema=schema, t_ref=t_ref, beta=beta)
    m_conf = router_metrics(test_df, use_fast=use_fast_conf_test, protocol=protocol, schema=schema, t_ref=t_ref, beta=beta)
    m_probe = router_metrics(test_df, use_fast=use_fast_probe_test, protocol=protocol, schema=schema, t_ref=t_ref, beta=beta)

    stats = {
        "version": "router_phase21_minimal_demo_v1",
        "seed": int(args.seed),
        "protocol": asdict(protocol),
        "objective": {"t_ref": float(t_ref), "beta": float(beta), "J_def": "J = T/T_ref + beta*max(delta_l_rel,0)"},
        "methods": {
            "forced_fast": m_fast,
            "forced_slow": m_slow,
            "conformal_stage": m_conf,
            "probe_flip_stage": m_probe,
        },
        "gate_check": {
            "demo_runs_under_10s": bool((time.perf_counter() - t0) <= 10.0),
            "probe_is_monotone_safe": bool(np.all((~use_fast_probe_test) | use_fast_conf_test)),
        },
        "artifacts": {
            "stage1_meta_keys": sorted(list(meta_conf.keys())),
            "stage2_meta_keys": sorted(list(meta_probe.keys())),
        },
        "runtime_seconds": float(time.perf_counter() - t0),
    }

    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    if bool(args.write_parquet):
        calib_df.to_parquet(out_dir / "toy_calib.parquet", index=False)
        test_df.to_parquet(out_dir / "toy_test.parquet", index=False)

    # Minimal console summary (for quick verification).
    def _fmt(name: str, m: dict) -> str:
        return (
            f"{name}: fast={m['fast_ratio']:.3f}, V={m['violation_rate']:.3f}, "
            f"J={m.get('J_mean', float('nan')):.3f}, p95CI_up={m['violation_rate_ci95'][1]:.3f}"
        )

    print(_fmt("forced_fast", m_fast))
    print(_fmt("conformal", m_conf))
    print(_fmt("probe", m_probe))
    print(_fmt("forced_slow", m_slow))
    print(f"[phase21] wrote: {out_dir/'stats.json'}")
    print(f"[phase21] runtime_s={stats['runtime_seconds']:.3f}")


if __name__ == "__main__":
    main()
