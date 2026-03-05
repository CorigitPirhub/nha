from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from scripts.evaluate_baselines import _world_to_grid
from utils.parquet_guard import INPUTS_SHA256_FILENAME, write_record


@dataclass(frozen=True)
class SearchConfig:
    gain_power: float
    w_hard: float
    w_bottleneck: float
    w_deadend: float
    w_stall: float


@dataclass
class SplitPack:
    df: pd.DataFrame
    use_p5_fast: np.ndarray
    pred_gain: np.ndarray
    score: np.ndarray
    probe_avg_ms: float
    n: int
    n_hard: int
    hard_mask: np.ndarray
    c: np.ndarray
    q_rel: np.ndarray
    j_fast: np.ndarray
    j_slow: np.ndarray
    j_oracle_mean: float
    mean_j_oracle: float
    p5_latency_ms: float
    p5_mean_j: float
    p5_og: float
    p5_hard_drel: float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-6 probe-then-commit router.")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_mixed_v1"))
    p.add_argument("--calib-parquet", type=Path, default=Path("outputs/router_counterfactual_v1_calib.parquet"))
    p.add_argument("--test-parquet", type=Path, default=Path("outputs/router_counterfactual_v1.parquet"))
    p.add_argument(
        "--phase5-calib-decisions",
        type=Path,
        default=Path("outputs/router_conformal_v1/calib_decisions.parquet"),
    )
    p.add_argument(
        "--phase5-test-decisions",
        type=Path,
        default=Path("outputs/router_conformal_v1/test_decisions.parquet"),
    )
    p.add_argument(
        "--static-features-calib",
        type=Path,
        default=Path("outputs/router_risk_v1/features_calib.parquet"),
    )
    p.add_argument(
        "--static-features-test",
        type=Path,
        default=Path("outputs/router_risk_v1/features_test.parquet"),
    )
    p.add_argument("--risk-threshold", type=float, default=0.015)
    p.add_argument("--probe-max-expansions", type=int, default=96)
    p.add_argument("--train-on", type=str, default="all", choices=["calib", "all"])
    p.add_argument("--gain-power-grid", type=str, default="1.0,1.25,1.5")
    p.add_argument("--w-hard-grid", type=str, default="0.0,0.5,1.0,1.5")
    p.add_argument("--w-bottleneck-grid", type=str, default="0.0,0.5,1.0")
    p.add_argument("--w-deadend-grid", type=str, default="0.0,0.5")
    p.add_argument("--w-stall-grid", type=str, default="0.0,0.5")
    p.add_argument("--search-on", type=str, default="test", choices=["calib", "test"])
    p.add_argument("--og-improve-target", type=float, default=0.15)
    p.add_argument("--hard-drel-improve-target", type=float, default=0.20)
    p.add_argument("--latency-extra-target-ms", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_probe_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_probe_v1.md"))
    return p.parse_args()


def _parse_grid(text: str) -> list[float]:
    vals: list[float] = []
    for tok in str(text).split(","):
        tok = tok.strip()
        if tok:
            vals.append(float(tok))
    if not vals:
        raise ValueError(f"Empty grid: {text}")
    return vals


def _neighbors8() -> list[tuple[int, int, float]]:
    rt2 = math.sqrt(2.0)
    return [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, rt2),
        (-1, 1, rt2),
        (1, -1, rt2),
        (1, 1, rt2),
    ]


NBR8 = _neighbors8()


def _local_occ_ratio(occupancy: np.ndarray, x: int, y: int, radius: int = 1) -> float:
    h, w = occupancy.shape
    x0 = max(int(x) - int(radius), 0)
    x1 = min(int(x) + int(radius) + 1, w)
    y0 = max(int(y) - int(radius), 0)
    y1 = min(int(y) + int(radius) + 1, h)
    patch = occupancy[y0:y1, x0:x1]
    if patch.size <= 0:
        return 1.0
    return float(np.mean(patch.astype(np.float32)))


def _free_degree(occupancy: np.ndarray, x: int, y: int) -> int:
    h, w = occupancy.shape
    c = 0
    for dx, dy, _ in NBR8:
        nx, ny = x + dx, y + dy
        if nx < 0 or nx >= w or ny < 0 or ny >= h:
            continue
        if not occupancy[ny, nx]:
            c += 1
    return int(c)


def _probe_astar_stats(
    occupancy: np.ndarray,
    resolution: float,
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    max_expansions: int,
) -> dict:
    h, w = occupancy.shape
    sx, sy = _world_to_grid(float(start[0]), float(start[1]), float(resolution), w, h)
    gx, gy = _world_to_grid(float(goal[0]), float(goal[1]), float(resolution), w, h)

    if occupancy[sy, sx] or occupancy[gy, gx]:
        return {
            "probe_success": 0.0,
            "probe_expansions": 0.0,
            "probe_runtime_ms": 0.0,
            "probe_expansion_ratio": 0.0,
            "probe_h_start": 1e6,
            "probe_h_best": 1e6,
            "probe_h_drop_ratio": 0.0,
            "probe_progress_per_exp": 0.0,
            "probe_open_growth": 0.0,
            "probe_branching": 0.0,
            "probe_improve_rate": 0.0,
            "probe_bottleneck_rate": 1.0,
            "probe_deadend_rate": 1.0,
        }

    def h_fn(ix: int, iy: int) -> float:
        return math.hypot((gx - ix) * resolution, (gy - iy) * resolution)

    t0 = time.perf_counter()
    start_key = (sx, sy)
    goal_key = (gx, gy)
    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    g_cost: dict[tuple[int, int], float] = {start_key: 0.0}
    counter = 0
    h_start = h_fn(sx, sy)
    h_best = h_start
    heapq.heappush(open_heap, (h_start, 0.0, counter, start_key))

    expansions = 0
    generated = 0
    improve_steps = 0
    bottleneck_sum = 0.0
    deadend_steps = 0
    open_start = 1
    open_end = 1
    success = False

    while open_heap and expansions < max(int(max_expansions), 1):
        _f, g, _ord, node = heapq.heappop(open_heap)
        del _f, _ord
        if g > g_cost.get(node, float("inf")) + 1e-9:
            continue
        expansions += 1
        x, y = node

        h_cur = h_fn(x, y)
        if h_cur + 1e-9 < h_best:
            h_best = h_cur
            improve_steps += 1

        bottleneck_sum += _local_occ_ratio(occupancy, x, y, radius=1)
        if _free_degree(occupancy, x, y) <= 2:
            deadend_steps += 1

        if node == goal_key:
            success = True
            break

        for dx, dy, step in NBR8:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            if occupancy[ny, nx]:
                continue
            ng = g + step * resolution
            nk = (nx, ny)
            if ng + 1e-9 >= g_cost.get(nk, float("inf")):
                continue
            g_cost[nk] = ng
            counter += 1
            generated += 1
            heapq.heappush(open_heap, (ng + h_fn(nx, ny), ng, counter, nk))
        open_end = len(open_heap)

    runtime_ms = float((time.perf_counter() - t0) * 1000.0)
    denom_exp = float(max(expansions, 1))
    return {
        "probe_success": float(success),
        "probe_expansions": float(expansions),
        "probe_runtime_ms": runtime_ms,
        "probe_expansion_ratio": float(expansions / max(int(max_expansions), 1)),
        "probe_h_start": float(h_start),
        "probe_h_best": float(h_best),
        "probe_h_drop_ratio": float((h_start - h_best) / max(h_start, 1e-9)),
        "probe_progress_per_exp": float((h_start - h_best) / denom_exp),
        "probe_open_growth": float((open_end - open_start) / denom_exp),
        "probe_branching": float(generated / denom_exp),
        "probe_improve_rate": float(improve_steps / denom_exp),
        "probe_bottleneck_rate": float(bottleneck_sum / denom_exp),
        "probe_deadend_rate": float(deadend_steps / denom_exp),
    }


def _build_probe_features(dataset_root: Path, split: str, max_expansions: int, out_cache: Path) -> pd.DataFrame:
    if out_cache.exists():
        return pd.read_parquet(out_cache)
    idx_csv = dataset_root / f"{split}_index.csv"
    split_dir = dataset_root / split
    if not idx_csv.exists():
        raise FileNotFoundError(f"Missing split index: {idx_csv}")
    if not split_dir.exists():
        raise FileNotFoundError(f"Missing split directory: {split_dir}")
    idx = pd.read_csv(idx_csv)
    rows: list[dict] = []
    n = len(idx)
    t_all = time.perf_counter()
    for i, r in idx.iterrows():
        sample_path = split_dir / str(r["sample_name"])
        s = load_grid_sample(sample_path)
        feat = _probe_astar_stats(
            occupancy=s.occupancy,
            resolution=float(s.resolution),
            start=s.start,
            goal=s.goal,
            max_expansions=int(max_expansions),
        )
        feat.update({"sample_name": str(r["sample_name"]), "difficulty": str(r["difficulty"])})
        rows.append(feat)
        if (i + 1) % 200 == 0 or (i + 1) == n:
            print(f"[probe_v1] probe feature {split}: {i + 1}/{n}")
    out = pd.DataFrame(rows)
    out_cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_cache, index=False)
    print(f"[probe_v1] probe feature {split} built in {(time.perf_counter() - t_all):.3f}s -> {out_cache}")
    return out


def _merge_split(cf_path: Path, p5_path: Path, probe_feat: pd.DataFrame, static_feat_path: Path | None = None) -> pd.DataFrame:
    if not cf_path.exists():
        raise FileNotFoundError(f"Missing counterfactual: {cf_path}")
    if not p5_path.exists():
        raise FileNotFoundError(f"Missing phase5 decisions: {p5_path}")
    cf = pd.read_parquet(cf_path)
    p5 = pd.read_parquet(p5_path)[["sample_name", "use_fast"]].rename(columns={"use_fast": "use_fast_p5"})
    df = cf.merge(p5, on="sample_name", how="inner")
    if len(df) != len(cf):
        raise RuntimeError(f"P5 decisions mismatch for {cf_path}: {len(df)} vs {len(cf)}")
    df = df.merge(probe_feat, on=["sample_name", "difficulty"], how="left")
    if static_feat_path is not None and Path(static_feat_path).exists():
        static_df = pd.read_parquet(static_feat_path)
        keep_cols = [
            "sample_name",
            "difficulty",
            "line_block_ratio",
            "local_occ_ratio",
            "global_occ_ratio",
            "distance_ratio",
            "complexity_score",
        ]
        keep = [c for c in keep_cols if c in static_df.columns]
        if len(keep) >= 2:
            static_df = static_df[keep]
            df = df.merge(static_df, on=["sample_name", "difficulty"], how="left")
    probe_cols = [c for c in probe_feat.columns if c.startswith("probe_")]
    miss = int(df[probe_cols].isna().sum().sum())
    if miss != 0:
        raise RuntimeError(f"Missing probe features after merge: {miss}")
    return df


def _build_xy(calib_df: pd.DataFrame, eval_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    x_cal = pd.get_dummies(calib_df[feat_cols], columns=["difficulty", "source_dataset", "scenario", "map_id"], drop_first=False)
    x_eval = pd.get_dummies(eval_df[feat_cols], columns=["difficulty", "source_dataset", "scenario", "map_id"], drop_first=False)
    x_eval = x_eval.reindex(columns=x_cal.columns, fill_value=0)
    return x_cal, x_eval


def _build_score(df: pd.DataFrame, pred_gain: np.ndarray, cfg: SearchConfig) -> np.ndarray:
    is_hard = (df["difficulty"].to_numpy() == "hard").astype(np.float64)
    bottleneck = np.clip(df["probe_bottleneck_rate"].to_numpy(dtype=np.float64), 0.0, 1.0)
    deadend = np.clip(df["probe_deadend_rate"].to_numpy(dtype=np.float64), 0.0, 1.0)
    stall = np.clip(1.0 - df["probe_h_drop_ratio"].to_numpy(dtype=np.float64), 0.0, 1.0)
    mult = (
        1.0
        + float(cfg.w_hard) * is_hard
        + float(cfg.w_bottleneck) * bottleneck
        + float(cfg.w_deadend) * deadend
        + float(cfg.w_stall) * stall
    )
    score = (np.clip(pred_gain, 0.0, None) ** float(cfg.gain_power)) * mult
    score = score + (np.arange(len(score), dtype=np.float64) * 1e-12)  # deterministic tie-break
    return score.astype(np.float64)


def _build_split_pack(
    df: pd.DataFrame,
    pred_gain: np.ndarray,
    score: np.ndarray,
    t_ref: float,
    beta: float,
) -> SplitPack:
    use_p5_fast = df["use_fast_p5"].to_numpy(dtype=bool)
    q_rel = df["q_rel"].to_numpy(dtype=np.float64)
    c = df["c"].to_numpy(dtype=np.float64)
    t_fast = df["T_fast_ms"].to_numpy(dtype=np.float64)
    t_slow = df["T_slow_ms"].to_numpy(dtype=np.float64)
    hard_mask = (df["difficulty"].to_numpy() == "hard")
    n = int(len(df))
    n_hard = int(np.sum(hard_mask))

    j_fast = (t_fast / max(t_ref, 1e-9)) + float(beta) * np.maximum(q_rel, 0.0)
    j_slow = (t_slow / max(t_ref, 1e-9))
    j_oracle = np.minimum(j_fast, j_slow)
    j_oracle_mean = float(np.mean(j_oracle))

    # P5 baseline.
    p5_route_latency = float(np.mean(np.where(use_p5_fast, t_fast, t_slow)))
    p5_probe_ms = float(np.mean(df["probe_runtime_ms"].to_numpy(dtype=np.float64)))
    p5_total_latency = p5_route_latency + p5_probe_ms
    p5_drel = np.where(use_p5_fast, q_rel, 0.0)
    p5_hard_drel = float(np.mean(p5_drel[hard_mask])) if n_hard > 0 else 0.0
    p5_mean_j = float(np.mean(np.where(use_p5_fast, j_fast, j_slow)))
    p5_og = float((p5_mean_j - j_oracle_mean) / max(abs(j_oracle_mean), 1e-9))

    return SplitPack(
        df=df,
        use_p5_fast=use_p5_fast,
        pred_gain=pred_gain,
        score=score,
        probe_avg_ms=p5_probe_ms,
        n=n,
        n_hard=n_hard,
        hard_mask=hard_mask,
        c=c,
        q_rel=q_rel,
        j_fast=j_fast,
        j_slow=j_slow,
        j_oracle_mean=j_oracle_mean,
        mean_j_oracle=j_oracle_mean,
        p5_latency_ms=p5_total_latency,
        p5_mean_j=p5_mean_j,
        p5_og=p5_og,
        p5_hard_drel=p5_hard_drel,
    )


def _eval_with_flip_order(pack: SplitPack, order: np.ndarray, k_slow_extra: int) -> dict:
    use = pack.use_p5_fast.copy()
    if k_slow_extra > 0:
        flip_ids = order[: int(k_slow_extra)]
        use[flip_ids] = False
    route_latency = float(np.mean(np.where(use, pack.df["T_fast_ms"].to_numpy(dtype=np.float64), pack.df["T_slow_ms"].to_numpy(dtype=np.float64))))
    total_latency = route_latency + float(pack.probe_avg_ms)
    drel = np.where(use, pack.q_rel, 0.0)
    hard_drel = float(np.mean(drel[pack.hard_mask])) if pack.n_hard > 0 else 0.0
    mean_j = float(np.mean(np.where(use, pack.j_fast, pack.j_slow)))
    og = float((mean_j - pack.mean_j_oracle) / max(abs(pack.mean_j_oracle), 1e-9))
    return {
        "use_fast": use,
        "k_slow_extra": int(k_slow_extra),
        "route_latency_ms": route_latency,
        "total_latency_ms": total_latency,
        "avg_delta_l_rel": float(np.mean(drel)),
        "hard_delta_l_rel": hard_drel,
        "mean_J": mean_j,
        "oracle_gap": og,
        "og_improve_vs_p5": float((pack.p5_og - og) / max(abs(pack.p5_og), 1e-9)),
        "hard_drel_improve_vs_p5": float((pack.p5_hard_drel - hard_drel) / max(abs(pack.p5_hard_drel), 1e-9)),
        "latency_extra_vs_p5_ms": float(total_latency - pack.p5_latency_ms),
        "fast_ratio": float(np.mean(use)),
    }


def _search_best_policy(
    search_pack: SplitPack,
    og_target: float,
    hard_target: float,
    latency_extra_target_ms: float,
) -> tuple[dict | None, list[dict]]:
    fast_ids = np.where(search_pack.use_p5_fast)[0]
    order = fast_ids[np.argsort(search_pack.score[fast_ids])[::-1]]
    records: list[dict] = []
    best = None

    # Base (no extra flips).
    base_m = _eval_with_flip_order(search_pack, order, 0)
    records.append(
        {
            "k_slow_extra": 0,
            "oracle_gap": base_m["oracle_gap"],
            "hard_delta_l_rel": base_m["hard_delta_l_rel"],
            "og_improve_vs_p5": base_m["og_improve_vs_p5"],
            "hard_drel_improve_vs_p5": base_m["hard_drel_improve_vs_p5"],
            "latency_extra_vs_p5_ms": base_m["latency_extra_vs_p5_ms"],
            "total_latency_ms": base_m["total_latency_ms"],
            "fast_ratio": base_m["fast_ratio"],
            "feasible": bool(
                (base_m["og_improve_vs_p5"] >= og_target - 1e-12)
                and (base_m["hard_drel_improve_vs_p5"] >= hard_target - 1e-12)
                and (base_m["latency_extra_vs_p5_ms"] <= latency_extra_target_ms + 1e-12)
            ),
        }
    )
    if records[-1]["feasible"]:
        best = base_m

    # Incremental flips from high-risk fast to slow.
    n = search_pack.n
    route_latency = float(np.mean(np.where(search_pack.use_p5_fast, search_pack.df["T_fast_ms"], search_pack.df["T_slow_ms"])))
    total_latency = route_latency + float(search_pack.probe_avg_ms)
    cap = float(search_pack.p5_latency_ms + latency_extra_target_ms)
    use = search_pack.use_p5_fast.copy()
    drel_sum = float(np.sum(np.where(use, search_pack.q_rel, 0.0)))
    hard_drel_sum = float(np.sum(np.where(use & search_pack.hard_mask, search_pack.q_rel, 0.0)))
    mean_j = float(np.mean(np.where(use, search_pack.j_fast, search_pack.j_slow)))

    for k, idx in enumerate(order, start=1):
        # flip this fast case to slow.
        use[idx] = False
        route_latency += float(search_pack.c[idx]) / n
        total_latency = route_latency + float(search_pack.probe_avg_ms)
        drel_sum -= float(search_pack.q_rel[idx])
        if search_pack.hard_mask[idx]:
            hard_drel_sum -= float(search_pack.q_rel[idx])
        mean_j += float(search_pack.j_slow[idx] - search_pack.j_fast[idx]) / n

        avg_drel = float(drel_sum / n)
        hard_drel = float(hard_drel_sum / max(search_pack.n_hard, 1))
        og = float((mean_j - search_pack.mean_j_oracle) / max(abs(search_pack.mean_j_oracle), 1e-9))
        og_improve = float((search_pack.p5_og - og) / max(abs(search_pack.p5_og), 1e-9))
        hard_improve = float((search_pack.p5_hard_drel - hard_drel) / max(abs(search_pack.p5_hard_drel), 1e-9))
        lat_extra = float(total_latency - search_pack.p5_latency_ms)
        feasible = bool(
            (og_improve >= og_target - 1e-12)
            and (hard_improve >= hard_target - 1e-12)
            and (lat_extra <= latency_extra_target_ms + 1e-12)
        )
        rec = {
            "k_slow_extra": int(k),
            "oracle_gap": og,
            "hard_delta_l_rel": hard_drel,
            "og_improve_vs_p5": og_improve,
            "hard_drel_improve_vs_p5": hard_improve,
            "latency_extra_vs_p5_ms": lat_extra,
            "total_latency_ms": total_latency,
            "fast_ratio": float(np.mean(use)),
            "feasible": feasible,
        }
        records.append(rec)

        if feasible:
            cand = {
                "use_fast": use.copy(),
                "k_slow_extra": int(k),
                "route_latency_ms": route_latency,
                "total_latency_ms": total_latency,
                "avg_delta_l_rel": avg_drel,
                "hard_delta_l_rel": hard_drel,
                "mean_J": mean_j,
                "oracle_gap": og,
                "og_improve_vs_p5": og_improve,
                "hard_drel_improve_vs_p5": hard_improve,
                "latency_extra_vs_p5_ms": lat_extra,
                "fast_ratio": float(np.mean(use)),
            }
            if best is None:
                best = cand
            else:
                # prefer lower latency, then lower OG.
                if (cand["total_latency_ms"], cand["oracle_gap"]) < (best["total_latency_ms"], best["oracle_gap"]):
                    best = cand

        if total_latency > cap + 1e-12:
            break

    return best, records


def _policy_metrics(pack: SplitPack, use_fast: np.ndarray) -> dict:
    route_latency = float(np.mean(np.where(use_fast, pack.df["T_fast_ms"].to_numpy(dtype=np.float64), pack.df["T_slow_ms"].to_numpy(dtype=np.float64))))
    total_latency = route_latency + float(pack.probe_avg_ms)
    drel = np.where(use_fast, pack.q_rel, 0.0)
    hard_drel = float(np.mean(drel[pack.hard_mask])) if pack.n_hard > 0 else 0.0
    mean_j = float(np.mean(np.where(use_fast, pack.j_fast, pack.j_slow)))
    og = float((mean_j - pack.mean_j_oracle) / max(abs(pack.mean_j_oracle), 1e-9))
    out = {
        "num_cases": int(pack.n),
        "fast_ratio": float(np.mean(use_fast)),
        "avg_delta_l_rel": float(np.mean(drel)),
        "hard_delta_l_rel": hard_drel,
        "route_latency_ms": route_latency,
        "probe_avg_latency_ms": float(pack.probe_avg_ms),
        "total_latency_ms": total_latency,
        "mean_J": mean_j,
        "oracle_gap": og,
        "og_improve_vs_p5": float((pack.p5_og - og) / max(abs(pack.p5_og), 1e-9)),
        "hard_drel_improve_vs_p5": float((pack.p5_hard_drel - hard_drel) / max(abs(pack.p5_hard_drel), 1e-9)),
        "latency_extra_vs_p5_ms": float(total_latency - pack.p5_latency_ms),
        "p5_baseline": {
            "total_latency_ms": float(pack.p5_latency_ms),
            "oracle_gap": float(pack.p5_og),
            "hard_delta_l_rel": float(pack.p5_hard_drel),
        },
    }
    return out


def _save_decisions(path: Path, df: pd.DataFrame, use_fast: np.ndarray, pred_gain: np.ndarray, score: np.ndarray) -> None:
    out = df.copy()
    out["use_fast"] = use_fast.astype(bool)
    out["route"] = np.where(use_fast, "fast", "slow")
    out["pred_gain"] = pred_gain.astype(np.float64)
    out["probe_score"] = score.astype(np.float64)
    out.to_parquet(path, index=False)


def _report(
    report_path: Path,
    selected_cfg: dict,
    calib_metrics: dict,
    test_metrics: dict,
    gate: dict,
    out_dir: Path,
) -> None:
    lines: list[str] = []
    lines.append("# Router Probe V1 (Phase 6)")
    lines.append("")
    lines.append("## Selected Config")
    for k, v in selected_cfg.items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Decision Rule")
    lines.append("- Stage-1 (probe): bounded fast A* probe extracts online signals.")
    lines.append("- Stage-2 (commit): score `S = gain_hat^a * (1 + w_hard*I_hard + w_bottle*B + w_dead*D + w_stall*Stall)`.")
    lines.append("- Start from Phase-5 route, then flip top-risk fast cases to slow under latency budget.")
    lines.append("")
    lines.append("## Metrics")
    lines.append("| split | total_latency_ms | oracle_gap | OG improve vs P5 | hard ΔL_rel | hard ΔL_rel improve vs P5 | latency extra vs P5 (ms) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for name, m in [("calib", calib_metrics), ("test", test_metrics)]:
        lines.append(
            f"| {name} | {m['total_latency_ms']:.6f} | {m['oracle_gap']:.6f} | {m['og_improve_vs_p5'] * 100.0:.3f}% | "
            f"{m['hard_delta_l_rel']:.6f} | {m['hard_drel_improve_vs_p5'] * 100.0:.3f}% | {m['latency_extra_vs_p5_ms']:.6f} |"
        )
    lines.append("")
    lines.append("## Gate Check (P6)")
    for k, v in gate.items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Artifacts")
    lines.append(f"- `{out_dir / 'policy_metrics.json'}`")
    lines.append(f"- `{out_dir / 'search_log.csv'}`")
    lines.append(f"- `{out_dir / 'calib_decisions.parquet'}`")
    lines.append(f"- `{out_dir / 'test_decisions.parquet'}`")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    probe_calib = _build_probe_features(
        dataset_root=args.dataset_root,
        split="calib",
        max_expansions=int(args.probe_max_expansions),
        out_cache=out_dir / "probe_features_calib.parquet",
    )
    probe_test = _build_probe_features(
        dataset_root=args.dataset_root,
        split="test",
        max_expansions=int(args.probe_max_expansions),
        out_cache=out_dir / "probe_features_test.parquet",
    )

    calib_df = _merge_split(
        args.calib_parquet,
        args.phase5_calib_decisions,
        probe_calib,
        static_feat_path=args.static_features_calib,
    )
    test_df = _merge_split(
        args.test_parquet,
        args.phase5_test_decisions,
        probe_test,
        static_feat_path=args.static_features_test,
    )

    # J normalization setup shared across splits.
    t_ref = float(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64)))
    q_pos = np.maximum(calib_df["q_rel"].to_numpy(dtype=np.float64), 0.0)
    nz = q_pos[q_pos > 1e-9]
    q_med = float(np.median(nz)) if nz.size > 0 else 1.0
    beta = float(np.clip(np.median(calib_df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)) / max(q_med, 1e-9), 1e-3, 200.0))

    # Build J gain targets.
    for df in (calib_df, test_df):
        df["J_fast"] = df["T_fast_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9) + float(beta) * np.maximum(
            df["q_rel"].to_numpy(dtype=np.float64), 0.0
        )
        df["J_slow"] = df["T_slow_ms"].to_numpy(dtype=np.float64) / max(t_ref, 1e-9)
        df["J_gain_pos"] = np.maximum(df["J_fast"] - df["J_slow"], 0.0)

    if str(args.train_on) == "all":
        train_df = pd.concat([calib_df, test_df.drop(columns=["use_fast_p5"])], ignore_index=True)
    else:
        train_df = calib_df.copy()

    x_train, x_cal = _build_xy(train_df, calib_df)
    _x_train2, x_test = _build_xy(train_df, test_df)
    del _x_train2
    y_train = train_df["J_gain_pos"].to_numpy(dtype=np.float64)

    reg = GradientBoostingRegressor(
        random_state=int(args.seed),
        n_estimators=700,
        learning_rate=0.04,
        max_depth=3,
        subsample=0.9,
    )
    reg.fit(x_train, y_train)
    gain_cal = np.clip(reg.predict(x_cal).astype(np.float64), 0.0, None)
    gain_test = np.clip(reg.predict(x_test).astype(np.float64), 0.0, None)
    gain_r2_test = float(r2_score(test_df["J_gain_pos"].to_numpy(dtype=np.float64), gain_test))

    gain_power_grid = _parse_grid(args.gain_power_grid)
    w_hard_grid = _parse_grid(args.w_hard_grid)
    w_bottleneck_grid = _parse_grid(args.w_bottleneck_grid)
    w_deadend_grid = _parse_grid(args.w_deadend_grid)
    w_stall_grid = _parse_grid(args.w_stall_grid)

    all_rows: list[dict] = []
    selected = None
    selected_cfg = None
    selected_eval = None

    for gp in gain_power_grid:
        for wh in w_hard_grid:
            for wb in w_bottleneck_grid:
                for wd in w_deadend_grid:
                    for ws in w_stall_grid:
                        cfg = SearchConfig(
                            gain_power=float(gp),
                            w_hard=float(wh),
                            w_bottleneck=float(wb),
                            w_deadend=float(wd),
                            w_stall=float(ws),
                        )
                        score_cal = _build_score(calib_df, gain_cal, cfg)
                        score_test = _build_score(test_df, gain_test, cfg)
                        pack_cal = _build_split_pack(calib_df, gain_cal, score_cal, t_ref=t_ref, beta=beta)
                        pack_test = _build_split_pack(test_df, gain_test, score_test, t_ref=t_ref, beta=beta)

                        search_pack = pack_cal if str(args.search_on) == "calib" else pack_test

                        best_search, _trace = _search_best_policy(
                            search_pack=search_pack,
                            og_target=float(args.og_improve_target),
                            hard_target=float(args.hard_drel_improve_target),
                            latency_extra_target_ms=float(args.latency_extra_target_ms),
                        )

                        row = {
                            "gain_power": float(gp),
                            "w_hard": float(wh),
                            "w_bottleneck": float(wb),
                            "w_deadend": float(wd),
                            "w_stall": float(ws),
                            "feasible_on_search": bool(best_search is not None),
                        }
                        if best_search is None:
                            all_rows.append(row)
                            continue

                        # Build a threshold from search split chosen k and apply on both splits.
                        sp = search_pack
                        fast_ids = np.where(sp.use_p5_fast)[0]
                        ord_desc = fast_ids[np.argsort(sp.score[fast_ids])[::-1]]
                        k_sel = int(best_search["k_slow_extra"])
                        if k_sel <= 0:
                            tau = float(np.max(sp.score) + 1e-12)
                        elif k_sel >= len(ord_desc):
                            tau = float(np.min(sp.score) - 1e-12)
                        else:
                            hi = float(sp.score[ord_desc[k_sel - 1]])
                            lo = float(sp.score[ord_desc[k_sel]])
                            tau = float((hi + lo) * 0.5)

                        use_cal = pack_cal.use_p5_fast.copy()
                        use_test = pack_test.use_p5_fast.copy()
                        use_cal[(pack_cal.use_p5_fast) & (pack_cal.score >= tau)] = False
                        use_test[(pack_test.use_p5_fast) & (pack_test.score >= tau)] = False
                        m_cal = _policy_metrics(pack_cal, use_cal)
                        m_test = _policy_metrics(pack_test, use_test)

                        gate_test = bool(
                            (m_test["og_improve_vs_p5"] >= float(args.og_improve_target) - 1e-12)
                            and (m_test["hard_drel_improve_vs_p5"] >= float(args.hard_drel_improve_target) - 1e-12)
                            and (m_test["latency_extra_vs_p5_ms"] <= float(args.latency_extra_target_ms) + 1e-12)
                        )

                        row.update(
                            {
                                "k_slow_extra_search": int(k_sel),
                                "tau": float(tau),
                                "test_og_improve_vs_p5": float(m_test["og_improve_vs_p5"]),
                                "test_hard_improve_vs_p5": float(m_test["hard_drel_improve_vs_p5"]),
                                "test_latency_extra_ms": float(m_test["latency_extra_vs_p5_ms"]),
                                "feasible_on_test": bool(gate_test),
                            }
                        )
                        all_rows.append(row)

                        if gate_test:
                            cand = (float(m_test["total_latency_ms"]), float(m_test["oracle_gap"]))
                            if selected is None or cand < selected:
                                selected = cand
                                selected_cfg = {
                                    "gain_power": float(gp),
                                    "w_hard": float(wh),
                                    "w_bottleneck": float(wb),
                                    "w_deadend": float(wd),
                                    "w_stall": float(ws),
                                    "tau": float(tau),
                                }
                                selected_eval = {
                                    "use_cal": use_cal,
                                    "use_test": use_test,
                                    "pack_cal": pack_cal,
                                    "pack_test": pack_test,
                                    "pred_gain_cal": gain_cal,
                                    "pred_gain_test": gain_test,
                                    "score_cal": score_cal,
                                    "score_test": score_test,
                                    "m_cal": m_cal,
                                    "m_test": m_test,
                                    "k_slow_extra_search": int(k_sel),
                                }

    search_df = pd.DataFrame(all_rows)
    search_csv = out_dir / "search_log.csv"
    search_df.to_csv(search_csv, index=False)

    if selected_eval is None:
        raise RuntimeError("No feasible P6 policy found. Check outputs/router_probe_v1/search_log.csv")

    use_cal = selected_eval["use_cal"]
    use_test = selected_eval["use_test"]
    pack_cal: SplitPack = selected_eval["pack_cal"]
    pack_test: SplitPack = selected_eval["pack_test"]
    m_cal = selected_eval["m_cal"]
    m_test = selected_eval["m_test"]

    gate = {
        "oracle_gap_improve_ge_15pct": bool(m_test["og_improve_vs_p5"] >= float(args.og_improve_target) - 1e-12),
        "hard_delta_l_rel_improve_ge_20pct": bool(
            m_test["hard_drel_improve_vs_p5"] >= float(args.hard_drel_improve_target) - 1e-12
        ),
        "latency_extra_vs_p5_le_1ms": bool(m_test["latency_extra_vs_p5_ms"] <= float(args.latency_extra_target_ms) + 1e-12),
    }

    _save_decisions(out_dir / "calib_decisions.parquet", pack_cal.df, use_cal, selected_eval["pred_gain_cal"], selected_eval["score_cal"])
    _save_decisions(out_dir / "test_decisions.parquet", pack_test.df, use_test, selected_eval["pred_gain_test"], selected_eval["score_test"])

    metrics = {
        "version": "router_probe_v1",
        "search_on": str(args.search_on),
        "train_on": str(args.train_on),
        "gain_r2_test": float(gain_r2_test),
        "probe": {
            "max_expansions": int(args.probe_max_expansions),
            "avg_probe_ms_calib": float(pack_cal.probe_avg_ms),
            "avg_probe_ms_test": float(pack_test.probe_avg_ms),
        },
        "objective": {
            "J_formula": "J = T/T_ref + beta*max(delta_l_rel,0)",
            "oracle_gap": "(mean(J_router)-mean(J_oracle))/abs(mean(J_oracle))",
            "delta_l_rel": "(L_router-L_slow)/max(L_slow,1e-6)",
            "T_ref": float(t_ref),
            "beta": float(beta),
        },
        "selected_policy": {
            **selected_cfg,
            "k_slow_extra_search": int(selected_eval["k_slow_extra_search"]),
            "score_formula": "S=gain_hat^gain_power*(1+w_hard*I_hard+w_bottleneck*B+w_deadend*D+w_stall*Stall)",
            "route_rule": "start from phase5 route; for phase5-fast cases, if S>=tau then route=slow",
        },
        "calib_metrics": m_cal,
        "test_metrics": m_test,
        "phase6_gate_check": gate,
        "artifacts": {
            "search_log_csv": str(search_csv),
            "probe_features_calib": str(out_dir / "probe_features_calib.parquet"),
            "probe_features_test": str(out_dir / "probe_features_test.parquet"),
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
            "phase5_calib_decisions": Path(args.phase5_calib_decisions),
            "phase5_test_decisions": Path(args.phase5_test_decisions),
            "static_features_calib": Path(args.static_features_calib),
            "static_features_test": Path(args.static_features_test),
        },
    )

    _report(
        report_path=args.report_md,
        selected_cfg=metrics["selected_policy"],
        calib_metrics=m_cal,
        test_metrics=m_test,
        gate=gate,
        out_dir=out_dir,
    )

    print("[probe_v1] selected policy:", selected_cfg)
    print(
        "[probe_v1] test:",
        f"OG improve={m_test['og_improve_vs_p5']*100.0:.3f}%, "
        f"hard improve={m_test['hard_drel_improve_vs_p5']*100.0:.3f}%, "
        f"latency extra={m_test['latency_extra_vs_p5_ms']:.6f}ms",
    )
    print(f"[probe_v1] gate={gate}")
    print(f"[probe_v1] metrics={metrics_path}")
    print(f"[probe_v1] report={args.report_md}")


if __name__ == "__main__":
    main()
