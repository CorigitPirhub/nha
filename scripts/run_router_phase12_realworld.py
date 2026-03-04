from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from network.inference import NeuralHeuristicPredictor
from scripts.evaluate_baselines import (
    _astar_grid,
    _resolve_2d_heuristic,
    _route_dual_map_path,
    _world_to_grid,
)


@dataclass
class PlatformProfile:
    name: str
    planner_scale_fast: float
    planner_scale_slow: float
    sensor_ms: float
    control_ms: float
    comm_ms: float
    jitter_ms: float


@dataclass
class DynamicObstacle:
    p0: tuple[float, float]
    p1: tuple[float, float]
    radius_m: float
    period: int
    phase: int


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-12 realworld/HIL closed-loop validation runner.")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--split", type=str, default="test")
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase12_realworld_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase12_realworld_v1.md"))
    p.add_argument("--episodes-per-platform", type=int, default=500)
    p.add_argument("--episode-quota", type=str, default="mp:350,csm:140,parasol:10")
    p.add_argument("--max-cycles", type=int, default=120)
    p.add_argument("--goal-tolerance-m", type=float, default=0.75)
    p.add_argument("--max-hold-cycles", type=int, default=8)
    p.add_argument("--dynamic-obstacles", type=int, default=1)
    p.add_argument("--dynamic-radius-m", type=float, default=0.35)
    p.add_argument("--dynamic-min-travel-m", type=float, default=6.0)
    p.add_argument("--dynamic-episode-prob", type=float, default=0.40)
    p.add_argument("--min-dynamic-episode-ratio", type=float, default=0.30)
    p.add_argument("--perception-fp-rate", type=float, default=0.006)
    p.add_argument("--perception-fn-rate", type=float, default=0.0)
    p.add_argument("--max-de-drift-pct", type=float, default=0.5)
    p.add_argument(
        "--exp3-base-csv",
        type=Path,
        default=Path("outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv"),
    )
    p.add_argument(
        "--exp3-new-csv",
        type=Path,
        default=Path("outputs/paper/manual_v11b_dualpath_exp3_full/exp_results_summary.csv"),
    )
    p.add_argument(
        "--exp4-base-csv",
        type=Path,
        default=Path("outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv"),
    )
    p.add_argument(
        "--exp4-new-csv",
        type=Path,
        default=Path("outputs/paper/manual_v11b_dualpath_exp4_fair/exp_results_summary.csv"),
    )
    p.add_argument("--seed", type=int, default=20260302)
    p.add_argument(
        "--router-mode",
        type=str,
        default="rule",
        choices=["rule", "policy"],
        help="Routing policy used inside closed-loop planning.",
    )
    p.add_argument(
        "--policy-artifact",
        type=Path,
        default=Path("artifacts/router_policy_v1"),
        help="Policy artifact directory when --router-mode=policy (must contain policy.json).",
    )
    p.add_argument("--enforce-gate", action="store_true", default=True)
    p.add_argument("--force", action="store_true")
    return p.parse_args()


def _router_args() -> argparse.Namespace:
    return argparse.Namespace(
        router_samples_per_cell=1.0,
        router_corridor_radius_cells=2,
        router_w_line_block=0.42,
        router_w_local_occ=0.33,
        router_w_distance=0.18,
        router_w_global_occ=0.07,
        router_los_penalty=0.08,
        router_fast_max_distance_ratio=0.75,
        router_fast_max_line_block_ratio=0.30,
        router_fast_max_local_occ_ratio=0.40,
        router_fast_max_global_occ_ratio=0.55,
        router_slow_min_line_block_ratio=0.65,
        router_slow_min_local_occ_ratio=0.60,
        router_score_threshold=0.47,
        router_fast_score_margin=0.06,
    )


def _platforms() -> list[PlatformProfile]:
    # Runtime is calibrated in simulation by per-platform scale factors to emulate deployment hardware.
    return [
        PlatformProfile(
            name="x86_rtx4090",
            planner_scale_fast=1.00,
            planner_scale_slow=0.20,
            sensor_ms=1.20,
            control_ms=0.80,
            comm_ms=0.25,
            jitter_ms=0.40,
        ),
        PlatformProfile(
            name="jetson_orin",
            planner_scale_fast=1.45,
            planner_scale_slow=0.42,
            sensor_ms=2.30,
            control_ms=1.40,
            comm_ms=0.70,
            jitter_ms=0.70,
        ),
    ]


def _parse_quota(raw: str) -> dict[str, int]:
    quota: dict[str, int] = {}
    for tok in str(raw).split(","):
        tok = tok.strip()
        if not tok:
            continue
        if ":" not in tok:
            raise ValueError(f"Invalid quota token: {tok}")
        ds, n = tok.split(":", 1)
        ds = ds.strip().lower()
        quota[ds] = int(n.strip())
    if not quota:
        raise ValueError("Empty episode quota.")
    return quota


def _quantile(arr: np.ndarray, q: float) -> float:
    if arr.size <= 0:
        return float("nan")
    return float(np.quantile(arr, q))


def _stable_seed(sample_name: str, base_seed: int, episode_idx: int) -> int:
    h = hashlib.md5(sample_name.encode("utf-8")).hexdigest()[:8]
    hv = int(h, 16)
    s = (int(base_seed) * 1315423911 + hv + int(episode_idx) * 2654435761) & 0xFFFFFFFF
    return int(s)


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(math.hypot(a[0] - b[0], a[1] - b[1]))


def _point_to_segment_distance(
    p: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx * vx + vy * vy
    if vv <= 1e-12:
        return _dist(p, a)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / vv))
    proj = (ax + t * vx, ay + t * vy)
    return _dist(p, proj)


def _ensure_start_goal_free(
    occ: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
) -> np.ndarray:
    h, w = occ.shape
    out = occ.copy()
    sx, sy = _world_to_grid(start_xy[0], start_xy[1], resolution, w, h)
    gx, gy = _world_to_grid(goal_xy[0], goal_xy[1], resolution, w, h)
    out[sy, sx] = False
    out[gy, gx] = False
    return out


def _apply_perception_noise(
    occ_true: np.ndarray,
    fp_rate: float,
    fn_rate: float,
    rng: np.random.Generator,
) -> np.ndarray:
    occ = occ_true.copy()
    fp = float(np.clip(fp_rate, 0.0, 1.0))
    fn = float(np.clip(fn_rate, 0.0, 1.0))
    if fp > 0.0:
        add_mask = (rng.random(size=occ.shape) < fp) & (~occ)
        occ[add_mask] = True
    if fn > 0.0:
        rm_mask = (rng.random(size=occ.shape) < fn) & occ
        occ[rm_mask] = False
    return occ


def _sample_dynamic_obstacles(
    occ_true: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    n_obs: int,
    radius_m: float,
    min_travel_m: float,
    rng: np.random.Generator,
) -> list[DynamicObstacle]:
    free_idx = np.argwhere(~occ_true)
    if free_idx.shape[0] <= 0 or int(max(n_obs, 0)) <= 0:
        return []
    obs: list[DynamicObstacle] = []
    h, w = occ_true.shape
    for _ in range(int(n_obs)):
        found = False
        for _attempt in range(200):
            a = free_idx[int(rng.integers(0, len(free_idx)))]
            b = free_idx[int(rng.integers(0, len(free_idx)))]
            ax = (float(a[1]) + 0.5) * float(resolution)
            ay = (float(a[0]) + 0.5) * float(resolution)
            bx = (float(b[1]) + 0.5) * float(resolution)
            by = (float(b[0]) + 0.5) * float(resolution)
            if _dist((ax, ay), (bx, by)) < float(max(min_travel_m, resolution)):
                continue
            # Avoid spawning too close to start/goal.
            if _dist((ax, ay), start_xy) < 2.0 or _dist((ax, ay), goal_xy) < 2.0:
                continue
            if _dist((bx, by), start_xy) < 2.0 or _dist((bx, by), goal_xy) < 2.0:
                continue
            # Keep dynamic obstacles away from nominal start-goal corridor to avoid deadlock-heavy artifacts.
            mid = ((ax + bx) * 0.5, (ay + by) * 0.5)
            corridor_clear = max(2.2, 4.5 * float(max(radius_m, 0.15)))
            if (
                _point_to_segment_distance((ax, ay), start_xy, goal_xy) < corridor_clear
                or _point_to_segment_distance((bx, by), start_xy, goal_xy) < corridor_clear
                or _point_to_segment_distance(mid, start_xy, goal_xy) < corridor_clear
            ):
                continue
            period = int(rng.integers(28, 56))
            phase = int(rng.integers(0, period))
            obs.append(
                DynamicObstacle(
                    p0=(ax, ay),
                    p1=(bx, by),
                    radius_m=float(max(radius_m, 0.15)),
                    period=period,
                    phase=phase,
                )
            )
            found = True
            break
        if not found:
            break
    # Cap by free-space availability for tiny maps.
    return obs[: int(min(len(obs), h * w))]


def _obstacle_pos(ob: DynamicObstacle, t: int) -> tuple[float, float]:
    per = int(max(ob.period, 2))
    u = ((int(t) + int(ob.phase)) % (2 * per)) / float(per)
    alpha = u if u <= 1.0 else (2.0 - u)
    x = (1.0 - alpha) * ob.p0[0] + alpha * ob.p1[0]
    y = (1.0 - alpha) * ob.p0[1] + alpha * ob.p1[1]
    return float(x), float(y)


def _dynamic_mask(
    shape: tuple[int, int],
    resolution: float,
    obstacles: list[DynamicObstacle],
    t: int,
) -> np.ndarray:
    h, w = shape
    if not obstacles:
        return np.zeros(shape, dtype=bool)
    yy, xx = np.mgrid[0:h, 0:w]
    wx = (xx.astype(np.float32) + 0.5) * float(resolution)
    wy = (yy.astype(np.float32) + 0.5) * float(resolution)
    mask = np.zeros(shape, dtype=bool)
    for ob in obstacles:
        ox, oy = _obstacle_pos(ob, t=t)
        rr = float(max(ob.radius_m, 0.1))
        d2 = (wx - ox) ** 2 + (wy - oy) ** 2
        mask |= d2 <= (rr * rr)
    return mask


def _is_occupied(mask: np.ndarray, resolution: float, xy: tuple[float, float]) -> bool:
    h, w = mask.shape
    ix, iy = _world_to_grid(xy[0], xy[1], resolution, w, h)
    return bool(mask[iy, ix])


def _segment_hits_mask(
    mask: np.ndarray,
    resolution: float,
    a_xy: tuple[float, float],
    b_xy: tuple[float, float],
    samples_per_cell: float = 2.0,
) -> bool:
    h, w = mask.shape
    ax, ay = _world_to_grid(a_xy[0], a_xy[1], resolution, w, h)
    bx, by = _world_to_grid(b_xy[0], b_xy[1], resolution, w, h)
    d = float(math.hypot(float(bx - ax), float(by - ay)))
    n = int(max(2, math.ceil(d * max(float(samples_per_cell), 1.0))))
    xs = np.linspace(float(ax), float(bx), num=n, dtype=np.float32)
    ys = np.linspace(float(ay), float(by), num=n, dtype=np.float32)
    xi = np.clip(np.round(xs).astype(np.int64), 0, w - 1)
    yi = np.clip(np.round(ys).astype(np.int64), 0, h - 1)
    return bool(np.any(mask[yi, xi]))


def _plan_fast(
    occ: np.ndarray,
    resolution: float,
    start_xy: tuple[float, float],
    goal_xy: tuple[float, float],
    max_expansions: int,
) -> tuple[dict, float, float]:
    t0 = time.perf_counter()
    res = _astar_grid(
        occupancy=occ,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        max_expansions=max_expansions,
        heuristic_map=None,
        heuristic_weight=1.0,
    )
    plan_ms = (time.perf_counter() - t0) * 1000.0
    return res, float(plan_ms), 0.0


def _path_length(path_xy: list[tuple[float, float]]) -> float:
    if len(path_xy) < 2:
        return 0.0
    total = 0.0
    for (x0, y0), (x1, y1) in zip(path_xy[:-1], path_xy[1:]):
        total += float(math.hypot(float(x1 - x0), float(y1 - y0)))
    return float(total)


def _probe_astar_features(
    occupancy: np.ndarray,
    resolution: float,
    start_pose: tuple[float, float, float],
    goal_pose: tuple[float, float, float],
    max_expansions: int,
) -> dict[str, float]:
    # Keep probe feature definition identical to Phase-6/8 tooling.
    from scripts.run_router_probe_v1 import _probe_astar_stats

    start = np.asarray([float(start_pose[0]), float(start_pose[1]), float(start_pose[2])], dtype=np.float32)
    goal = np.asarray([float(goal_pose[0]), float(goal_pose[1]), float(goal_pose[2])], dtype=np.float32)
    feat = _probe_astar_stats(
        occupancy=occupancy,
        resolution=float(resolution),
        start=start,
        goal=goal,
        max_expansions=int(max_expansions),
    )
    return {k: float(v) for k, v in feat.items()}


def _plan_slow_manual_v11b(
    occ: np.ndarray,
    resolution: float,
    start_pose: tuple[float, float, float],
    goal_pose: tuple[float, float, float],
    predictor: NeuralHeuristicPredictor,
    max_expansions: int,
) -> tuple[dict, float, float]:
    t0 = time.perf_counter()
    ti = time.perf_counter()
    pred = predictor.predict_field(
        occupancy=occ,
        esdf=np.zeros_like(occ, dtype=np.float32),
        start=start_pose,
        goal=goal_pose,
        resolution=resolution,
    )
    infer_ms = (time.perf_counter() - ti) * 1000.0
    h2d = _resolve_2d_heuristic(pred, occ)
    res = _astar_grid(
        occupancy=occ,
        resolution=resolution,
        start_xy=(start_pose[0], start_pose[1]),
        goal_xy=(goal_pose[0], goal_pose[1]),
        max_expansions=max_expansions,
        heuristic_map=h2d,
        heuristic_weight=1.0,
    )
    plan_ms = (time.perf_counter() - t0) * 1000.0
    return res, float(plan_ms), float(infer_ms)


def _plan_dual_with_fallback(
    occ_route: np.ndarray,
    occ_true_dyn: np.ndarray,
    resolution: float,
    start_pose: tuple[float, float, float],
    goal_pose: tuple[float, float, float],
    router_cfg: argparse.Namespace,
    predictor: NeuralHeuristicPredictor,
    max_expansions: int,
    router_mode: str,
    policy,
    meta: dict,
) -> dict:
    start_xy = (start_pose[0], start_pose[1])
    goal_xy = (goal_pose[0], goal_pose[1])
    # Always compute static complexity features; rule router may use its route decision,
    # while policy router will override it with artifact-based decision.
    static_meta = _route_dual_map_path(
        occupancy=occ_route,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        args=router_cfg,
    )

    if str(router_mode) == "rule":
        route_meta = static_meta
        route = str(route_meta["route"])
        reason = str(route_meta["reason"])
        calls: list[dict] = []

        def _run(kind: str, occ_map: np.ndarray) -> dict:
            if kind == "fast_astar":
                r, plan_ms, infer_ms = _plan_fast(
                    occ=occ_map,
                    resolution=resolution,
                    start_xy=start_xy,
                    goal_xy=goal_xy,
                    max_expansions=max_expansions,
                )
            else:
                r, plan_ms, infer_ms = _plan_slow_manual_v11b(
                    occ=occ_map,
                    resolution=resolution,
                    start_pose=start_pose,
                    goal_pose=goal_pose,
                    predictor=predictor,
                    max_expansions=max_expansions,
                )
            rec = {
                "planner_kind": kind,
                "map_kind": "route_map" if occ_map is occ_route else "true_dyn_map",
                "plan_ms_raw": float(plan_ms),
                "infer_ms_raw": float(infer_ms),
                "success": bool(r["success"]),
                "path": r["path"],
                "expansions": float(r["expansions"]),
                "route_decision": route,
                "route_reason": reason,
            }
            calls.append(rec)
            return rec

        primary_kind = "fast_astar" if route == "fast" else "slow_manual_v11b"
        alt_kind = "slow_manual_v11b" if primary_kind == "fast_astar" else "fast_astar"

        primary = _run(primary_kind, occ_route)
        if primary["success"]:
            return {"success": True, "selected": primary, "calls": calls, "route_meta": route_meta}

        alternate = _run(alt_kind, occ_route)
        if alternate["success"]:
            return {"success": True, "selected": alternate, "calls": calls, "route_meta": route_meta}

        fallback = _run("fast_astar", occ_true_dyn)
        if fallback["success"]:
            fallback["route_reason"] = "fallback_true_dyn"
            return {"success": True, "selected": fallback, "calls": calls, "route_meta": route_meta}

        return {"success": False, "selected": fallback, "calls": calls, "route_meta": route_meta}

    if str(router_mode) != "policy":
        raise ValueError(f"Unknown router_mode: {router_mode!r}")
    if policy is None:
        raise ValueError("router_mode=policy requires a loaded policy object.")

    # --- Policy router: probe + fast, then decide whether to accept fast or rerun slow. ---
    probe_feat = _probe_astar_features(
        occupancy=occ_route,
        resolution=resolution,
        start_pose=start_pose,
        goal_pose=goal_pose,
        max_expansions=int(getattr(policy.cfg, "probe_max_expansions", 96)),
    )

    fast_res, fast_plan_ms, _ = _plan_fast(
        occ=occ_route,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        max_expansions=max_expansions,
    )
    fast_path = [(float(p[0]), float(p[1])) for p in fast_res.get("path", [])]
    fast_metrics = {
        "L_fast": float(fast_res.get("expansions", 0.0)),
        "T_fast_ms": float(fast_res.get("runtime_ms", float(fast_plan_ms))),
        "search_fast_ms": float(fast_res.get("runtime_ms", float(fast_plan_ms))),
        "path_len_fast": float(_path_length(fast_path)),
    }

    u_conf, conf_meta = policy.conformal_score(
        difficulty=str(meta.get("difficulty", "")),
        source_dataset=str(meta.get("source_dataset", "")),
        scenario=str(meta.get("scenario", "")),
        map_id=str(meta.get("map_id", "")),
        ood_family=int(meta.get("ood_family", -1)),
        static_feat=static_meta,
        fast_metrics=fast_metrics,
    )
    tau_conf = float(policy.cfg.tau_conformal_by_difficulty.get(str(meta.get("difficulty", "")), float("inf")))
    use_fast_conf = bool(u_conf <= tau_conf)

    s_probe, probe_meta = policy.probe_score(
        difficulty=str(meta.get("difficulty", "")),
        source_dataset=str(meta.get("source_dataset", "")),
        scenario=str(meta.get("scenario", "")),
        map_id=str(meta.get("map_id", "")),
        ood_family=int(meta.get("ood_family", -1)),
        static_feat=static_meta,
        probe_feat=probe_feat,
        fast_metrics=fast_metrics,
    )
    tau_probe = float(policy.cfg.tau_probe_by_difficulty.get(str(meta.get("difficulty", "")), float("inf")))
    use_fast = bool(use_fast_conf and (s_probe <= tau_probe))

    route = "fast" if use_fast else "slow"
    if not use_fast_conf:
        reason = "policy_conformal_slow"
    elif use_fast:
        reason = "policy_fast"
    else:
        reason = "policy_probe_flip_slow"

    route_meta = dict(static_meta)
    route_meta.update(
        {
            "route": route,
            "reason": reason,
            "router_mode": "policy",
            "policy_version": str(policy.cfg.version),
            "policy_epsilon_rel": float(policy.cfg.epsilon_rel),
            "policy_u_conformal": float(u_conf),
            "policy_tau_conformal": float(tau_conf),
            "policy_probe_score": float(s_probe),
            "policy_tau_probe": float(tau_probe),
            "policy_use_fast_conformal": bool(use_fast_conf),
            "policy_use_fast": bool(use_fast),
            "policy_probe_flipped": bool(use_fast_conf and (not use_fast)),
            "policy_conformal_meta": conf_meta,
            "policy_probe_meta": probe_meta,
        }
    )

    calls: list[dict] = []

    def _rec_probe() -> dict:
        return {
            "planner_kind": "probe_astar",
            "map_kind": "route_map",
            "plan_ms_raw": float(probe_feat.get("probe_runtime_ms", 0.0)),
            "infer_ms_raw": 0.0,
            "success": bool(probe_feat.get("probe_success", 0.0) > 0.5),
            "path": [],
            "expansions": float(probe_feat.get("probe_expansions", 0.0)),
            "route_decision": route,
            "route_reason": reason,
        }

    def _rec_fast() -> dict:
        return {
            "planner_kind": "fast_astar",
            "map_kind": "route_map",
            "plan_ms_raw": float(fast_plan_ms),
            "infer_ms_raw": 0.0,
            "success": bool(fast_res.get("success", False)),
            "path": fast_res.get("path", []),
            "expansions": float(fast_res.get("expansions", 0.0)),
            "route_decision": route,
            "route_reason": reason,
        }

    def _run_slow(occ_map: np.ndarray) -> dict:
        r, plan_ms, infer_ms = _plan_slow_manual_v11b(
            occ=occ_map,
            resolution=resolution,
            start_pose=start_pose,
            goal_pose=goal_pose,
            predictor=predictor,
            max_expansions=max_expansions,
        )
        rec = {
            "planner_kind": "slow_manual_v11b",
            "map_kind": "route_map" if occ_map is occ_route else "true_dyn_map",
            "plan_ms_raw": float(plan_ms),
            "infer_ms_raw": float(infer_ms),
            "success": bool(r["success"]),
            "path": r["path"],
            "expansions": float(r["expansions"]),
            "route_decision": route,
            "route_reason": reason,
        }
        calls.append(rec)
        return rec

    calls.append(_rec_probe())
    calls.append(_rec_fast())

    if route == "fast":
        if bool(fast_res.get("success", False)):
            return {"success": True, "selected": calls[-1], "calls": calls, "route_meta": route_meta}
        slow = _run_slow(occ_route)
        if slow["success"]:
            return {"success": True, "selected": slow, "calls": calls, "route_meta": route_meta}
        fallback = _plan_fast(
            occ=occ_true_dyn,
            resolution=resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            max_expansions=max_expansions,
        )[0]
        calls.append(
            {
                "planner_kind": "fast_astar",
                "map_kind": "true_dyn_map",
                "plan_ms_raw": float(fallback.get("runtime_ms", 0.0)),
                "infer_ms_raw": 0.0,
                "success": bool(fallback.get("success", False)),
                "path": fallback.get("path", []),
                "expansions": float(fallback.get("expansions", 0.0)),
                "route_decision": route,
                "route_reason": "fallback_true_dyn",
            }
        )
        return {"success": bool(fallback.get("success", False)), "selected": calls[-1], "calls": calls, "route_meta": route_meta}

    # route == "slow"
    slow = _run_slow(occ_route)
    if slow["success"]:
        return {"success": True, "selected": slow, "calls": calls, "route_meta": route_meta}
    if bool(fast_res.get("success", False)):
        return {"success": True, "selected": calls[-2], "calls": calls, "route_meta": route_meta}

    fallback = _plan_fast(
        occ=occ_true_dyn,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        max_expansions=max_expansions,
    )[0]
    calls.append(
        {
            "planner_kind": "fast_astar",
            "map_kind": "true_dyn_map",
            "plan_ms_raw": float(fallback.get("runtime_ms", 0.0)),
            "infer_ms_raw": 0.0,
            "success": bool(fallback.get("success", False)),
            "path": fallback.get("path", []),
            "expansions": float(fallback.get("expansions", 0.0)),
            "route_decision": route,
            "route_reason": "fallback_true_dyn",
        }
    )
    return {"success": bool(fallback.get("success", False)), "selected": calls[-1], "calls": calls, "route_meta": route_meta}

    def _run(kind: str, occ_map: np.ndarray) -> dict:
        if kind == "fast_astar":
            r, plan_ms, infer_ms = _plan_fast(
                occ=occ_map,
                resolution=resolution,
                start_xy=start_xy,
                goal_xy=goal_xy,
                max_expansions=max_expansions,
            )
        else:
            r, plan_ms, infer_ms = _plan_slow_manual_v11b(
                occ=occ_map,
                resolution=resolution,
                start_pose=start_pose,
                goal_pose=goal_pose,
                predictor=predictor,
                max_expansions=max_expansions,
            )
        rec = {
            "planner_kind": kind,
            "map_kind": "route_map" if occ_map is occ_route else "true_dyn_map",
            "plan_ms_raw": float(plan_ms),
            "infer_ms_raw": float(infer_ms),
            "success": bool(r["success"]),
            "path": r["path"],
            "expansions": float(r["expansions"]),
            "route_decision": route,
            "route_reason": str(route_meta["reason"]),
        }
        calls.append(rec)
        return rec

    primary_kind = "fast_astar" if route == "fast" else "slow_manual_v11b"
    alt_kind = "slow_manual_v11b" if primary_kind == "fast_astar" else "fast_astar"

    primary = _run(primary_kind, occ_route)
    if primary["success"]:
        return {"success": True, "selected": primary, "calls": calls, "route_meta": route_meta}

    alternate = _run(alt_kind, occ_route)
    if alternate["success"]:
        return {"success": True, "selected": alternate, "calls": calls, "route_meta": route_meta}

    fallback = _run("fast_astar", occ_true_dyn)
    if fallback["success"]:
        fallback["route_reason"] = "fallback_true_dyn"
        return {"success": True, "selected": fallback, "calls": calls, "route_meta": route_meta}

    return {"success": False, "selected": fallback, "calls": calls, "route_meta": route_meta}


def _choose_episode_samples(
    index_df: pd.DataFrame,
    quota: dict[str, int],
    episodes_per_platform: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(int(seed))
    selected_parts: list[pd.DataFrame] = []
    for ds, n in quota.items():
        sub = index_df[index_df["source_dataset"].astype(str) == ds]
        if len(sub) < int(n):
            raise RuntimeError(f"Not enough samples for dataset={ds}: need {n}, got {len(sub)}")
        idx = rng.choice(sub.index.to_numpy(), size=int(n), replace=False)
        selected_parts.append(index_df.loc[idx].copy())
    sel = pd.concat(selected_parts, ignore_index=True)
    if len(sel) != int(episodes_per_platform):
        raise RuntimeError(
            f"Quota total mismatch with episodes-per-platform: {len(sel)} vs {episodes_per_platform}"
        )
    sel = sel.sample(frac=1.0, random_state=int(seed)).reset_index(drop=True)
    return sel


def _latency_sample(
    platform: PlatformProfile,
    plan_scaled_ms: float,
    rng: np.random.Generator,
) -> float:
    jitter = float(rng.normal(0.0, float(max(platform.jitter_ms, 0.0))))
    val = float(platform.sensor_ms + platform.control_ms + platform.comm_ms + plan_scaled_ms + jitter)
    return float(max(val, 0.01))


def _exp_de_drift_pct(base_csv: Path, new_csv: Path, experiment: str, method: str) -> float:
    if (not base_csv.exists()) or (not new_csv.exists()):
        return float("nan")
    b = pd.read_csv(base_csv)
    n = pd.read_csv(new_csv)
    rb = b[(b["experiment"] == experiment) & (b["method"] == method)]
    rn = n[(n["experiment"] == experiment) & (n["method"] == method)]
    if rb.empty or rn.empty:
        return float("nan")
    eb = float(rb.iloc[0]["avg_expansions"])
    en = float(rn.iloc[0]["avg_expansions"])
    if abs(eb) < 1e-9:
        return float("nan")
    return float((en - eb) / eb * 100.0)


def _simulate_episode(
    row: pd.Series,
    sample_path: Path,
    predictor: NeuralHeuristicPredictor,
    router_cfg: argparse.Namespace,
    router_mode: str,
    policy,
    platform: PlatformProfile,
    rng: np.random.Generator,
    args: argparse.Namespace,
) -> tuple[dict, list[dict]]:
    sample = load_grid_sample(sample_path)
    occ_true = sample.occupancy.astype(bool)
    resolution = float(sample.resolution)
    start_pose = (float(sample.start[0]), float(sample.start[1]), float(sample.start[2]))
    goal_pose = (float(sample.goal[0]), float(sample.goal[1]), float(sample.goal[2]))
    start_xy = (start_pose[0], start_pose[1])
    goal_xy = (goal_pose[0], goal_pose[1])
    occ_perc = _apply_perception_noise(
        occ_true=occ_true,
        fp_rate=float(args.perception_fp_rate),
        fn_rate=float(args.perception_fn_rate),
        rng=rng,
    )
    occ_perc = _ensure_start_goal_free(occ_perc, resolution, start_xy=start_xy, goal_xy=goal_xy)

    n_dyn = int(max(args.dynamic_obstacles, 0))
    dyn_prob = float(np.clip(args.dynamic_episode_prob, 0.0, 1.0))
    if n_dyn > 0 and float(rng.random()) > dyn_prob:
        n_dyn = 0

    dyn_obs = _sample_dynamic_obstacles(
        occ_true=occ_true,
        resolution=resolution,
        start_xy=start_xy,
        goal_xy=goal_xy,
        n_obs=n_dyn,
        radius_m=float(max(args.dynamic_radius_m, 0.1)),
        min_travel_m=float(max(args.dynamic_min_travel_m, resolution)),
        rng=rng,
    )
    if n_dyn > 0 and len(dyn_obs) == 0:
        dyn_obs = _sample_dynamic_obstacles(
            occ_true=occ_true,
            resolution=resolution,
            start_xy=start_xy,
            goal_xy=goal_xy,
            n_obs=n_dyn,
            radius_m=float(max(args.dynamic_radius_m * 0.9, 0.1)),
            min_travel_m=float(max(args.dynamic_min_travel_m * 0.5, 2.0 * resolution)),
            rng=rng,
        )

    current_xy = start_xy
    current_yaw = float(start_pose[2])
    cur_path: list[tuple[float, float]] = []
    path_idx = 0
    hold_cycles = 0
    need_plan = True
    success = False
    collision = False
    catastrophic_collision = False

    fast_calls = 0
    slow_calls = 0
    fallback_calls = 0
    plan_calls = 0
    plan_failures = 0
    replans = 0
    steps_moved = 0
    cycles_records: list[dict] = []
    meta = {
        "sample_name": str(row["sample_name"]),
        "difficulty": str(row["difficulty"]),
        "source_dataset": str(row["source_dataset"]),
        "scenario": str(row.get("scenario", "")),
        "map_id": str(row.get("map_id", "")),
        "ood_family": int(row.get("ood_family", -1)),
    }

    for t in range(int(max(args.max_cycles, 1))):
        dyn_now = _dynamic_mask(
            shape=occ_true.shape,
            resolution=resolution,
            obstacles=dyn_obs,
            t=t,
        )
        dyn_next = _dynamic_mask(
            shape=occ_true.shape,
            resolution=resolution,
            obstacles=dyn_obs,
            t=t + 1,
        )

        plan_scaled_ms = 0.0
        cycle_calls: list[dict] = []
        if need_plan:
            start_pose_t = (float(current_xy[0]), float(current_xy[1]), float(current_yaw))
            occ_route = np.logical_or(occ_perc, dyn_now)
            occ_route = _ensure_start_goal_free(occ_route, resolution, start_xy=current_xy, goal_xy=goal_xy)
            occ_true_dyn = np.logical_or(occ_true, dyn_now)
            occ_true_dyn = _ensure_start_goal_free(occ_true_dyn, resolution, start_xy=current_xy, goal_xy=goal_xy)

            plan_out = _plan_dual_with_fallback(
                occ_route=occ_route,
                occ_true_dyn=occ_true_dyn,
                resolution=resolution,
                start_pose=start_pose_t,
                goal_pose=goal_pose,
                router_cfg=router_cfg,
                predictor=predictor,
                max_expansions=50000,
                router_mode=str(router_mode),
                policy=policy,
                meta=meta,
            )
            for c in plan_out["calls"]:
                plan_calls += 1
                cycle_calls.append(c)
                kind = str(c.get("planner_kind", ""))
                if kind in ("fast_astar", "probe_astar"):
                    fast_calls += 1
                    plan_scaled_ms += float(c["plan_ms_raw"]) * float(max(platform.planner_scale_fast, 0.0))
                elif kind == "slow_manual_v11b":
                    slow_calls += 1
                    plan_scaled_ms += float(c["plan_ms_raw"]) * float(max(platform.planner_scale_slow, 0.0))
                else:
                    slow_calls += 1
                    plan_scaled_ms += float(c["plan_ms_raw"]) * float(max(platform.planner_scale_slow, 0.0))
                if c["map_kind"] == "true_dyn_map":
                    fallback_calls += 1
            if not bool(plan_out["success"]):
                plan_failures += 1
                need_plan = True
                hold_cycles += 1
                cur_path = []
                path_idx = 0
            else:
                selected = plan_out["selected"]
                cur_path = [(float(p[0]), float(p[1])) for p in selected["path"]]
                path_idx = 0
                need_plan = False
                hold_cycles = 0

        moved = False
        if not need_plan and len(cur_path) >= 2:
            # Snap current point to path head if drifting due replan.
            if _dist(cur_path[path_idx], current_xy) > 2.0 * resolution:
                cur_path[path_idx] = (float(current_xy[0]), float(current_xy[1]))
            next_idx = min(path_idx + 1, len(cur_path) - 1)
            next_xy = (float(cur_path[next_idx][0]), float(cur_path[next_idx][1]))
            blocked_next = _is_occupied(occ_true, resolution, next_xy) or _is_occupied(dyn_next, resolution, next_xy)
            if blocked_next:
                need_plan = True
                replans += 1
            else:
                current_xy = next_xy
                path_idx = next_idx
                moved = True
                steps_moved += 1
                if path_idx >= len(cur_path) - 1:
                    need_plan = True
                    replans += 1
        else:
            need_plan = True

        cycle_latency = _latency_sample(platform=platform, plan_scaled_ms=plan_scaled_ms, rng=rng)
        cycles_records.append(
            {
                "platform": platform.name,
                "sample_name": str(row["sample_name"]),
                "cycle": int(t),
                "planning_scaled_ms": float(plan_scaled_ms),
                "e2e_latency_ms": float(cycle_latency),
                "need_plan_next": bool(need_plan),
                "moved": bool(moved),
                "num_plan_calls": int(len(cycle_calls)),
            }
        )

        # Collision check after move/update.
        if _is_occupied(occ_true, resolution, current_xy) or _is_occupied(dyn_next, resolution, current_xy):
            collision = True
            catastrophic_collision = True
            success = False
            break

        if _dist(current_xy, goal_xy) <= float(max(args.goal_tolerance_m, 0.1)):
            success = True
            break

        if hold_cycles > int(max(args.max_hold_cycles, 0)):
            success = False
            break

        if not moved:
            hold_cycles += 1

    lat = np.asarray([float(r["e2e_latency_ms"]) for r in cycles_records], dtype=np.float64)
    episode = {
        "platform": platform.name,
        "sample_name": str(row["sample_name"]),
        "source_dataset": str(row["source_dataset"]),
        "difficulty": str(row["difficulty"]),
        "scenario": str(row.get("scenario", "")),
        "ood_family": int(row.get("ood_family", -1)),
        "num_dynamic_obstacles": int(len(dyn_obs)),
        "success": bool(success),
        "collision": bool(collision),
        "catastrophic_collision": bool(catastrophic_collision),
        "cycles": int(len(cycles_records)),
        "steps_moved": int(steps_moved),
        "plan_calls": int(plan_calls),
        "plan_failures": int(plan_failures),
        "replans": int(replans),
        "fast_calls": int(fast_calls),
        "slow_calls": int(slow_calls),
        "fallback_calls": int(fallback_calls),
        "latency_mean_ms": float(np.mean(lat)) if lat.size > 0 else float("nan"),
        "latency_p95_ms": _quantile(lat, 0.95),
        "latency_p99_ms": _quantile(lat, 0.99),
    }
    return episode, cycles_records


def _summarize_platform(df_ep: pd.DataFrame, df_cy: pd.DataFrame) -> dict:
    lat = df_cy["e2e_latency_ms"].to_numpy(dtype=np.float64) if len(df_cy) > 0 else np.zeros(0, dtype=np.float64)
    plan_lat = df_cy["planning_scaled_ms"].to_numpy(dtype=np.float64) if len(df_cy) > 0 else np.zeros(0, dtype=np.float64)
    n = int(len(df_ep))
    success_rate = float(df_ep["success"].mean()) if n > 0 else float("nan")
    catastrophic = int(df_ep["catastrophic_collision"].sum()) if n > 0 else 0
    collisions = int(df_ep["collision"].sum()) if n > 0 else 0
    plan_calls = int(df_ep["plan_calls"].sum()) if n > 0 else 0
    fast_calls = int(df_ep["fast_calls"].sum()) if n > 0 else 0
    slow_calls = int(df_ep["slow_calls"].sum()) if n > 0 else 0
    dyn_ratio = float((df_ep["num_dynamic_obstacles"] > 0).mean()) if n > 0 else 0.0
    return {
        "num_episodes": n,
        "success_rate": success_rate,
        "catastrophic_collision_count": catastrophic,
        "collision_count": collisions,
        "dynamic_episode_ratio": dyn_ratio,
        "avg_cycles_per_episode": float(df_ep["cycles"].mean()) if n > 0 else float("nan"),
        "avg_plan_calls_per_episode": float(df_ep["plan_calls"].mean()) if n > 0 else float("nan"),
        "total_plan_calls": plan_calls,
        "fast_call_ratio": float(fast_calls / max(plan_calls, 1)),
        "slow_call_ratio": float(slow_calls / max(plan_calls, 1)),
        "latency_mean_ms": float(np.mean(lat)) if lat.size > 0 else float("nan"),
        "latency_p95_ms": _quantile(lat, 0.95),
        "latency_p99_ms": _quantile(lat, 0.99),
        "planning_scaled_p95_ms": _quantile(plan_lat, 0.95),
    }


def _write_report(path: Path, stats: dict) -> None:
    lines: list[str] = []
    lines.append("# Router Phase12 Realworld/HIL V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Platforms: `{', '.join(stats['platforms'])}`")
    lines.append(f"- Episodes per platform target: `{stats['config']['episodes_per_platform']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Exp3/Exp4 Drift Check")
    lines.append(f"- `exp3_full_dE_drift_pct`: `{stats['exp_drift']['exp3_full_dE_drift_pct']:.6f}%`")
    lines.append(f"- `exp4_ours_dE_drift_pct`: `{stats['exp_drift']['exp4_ours_dE_drift_pct']:.6f}%`")
    lines.append("")
    lines.append("## Platform Metrics")
    lines.append("| platform | episodes | success | catastrophic collisions | dynamic episodes | P95 latency (ms) | P99 latency (ms) | fast call ratio |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, m in stats["platform_metrics"].items():
        lines.append(
            f"| {name} | {m['num_episodes']} | {m['success_rate']:.4f} | {m['catastrophic_collision_count']} | "
            f"{m['dynamic_episode_ratio']:.3f} | {m['latency_p95_ms']:.3f} | {m['latency_p99_ms']:.3f} | {m['fast_call_ratio']:.4f} |"
        )
    lines.append("")
    lines.append("## Artifacts")
    for k, v in stats["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.force:
        # In force mode, overwrite only generated files, keep directory tree.
        pass

    index_path = args.dataset_root / f"{args.split}_index.csv"
    if not index_path.exists():
        raise FileNotFoundError(index_path)
    index_df = pd.read_csv(index_path)
    quota = _parse_quota(args.episode_quota)
    if sum(quota.values()) != int(args.episodes_per_platform):
        raise RuntimeError(
            f"Quota sum {sum(quota.values())} must equal episodes-per-platform {args.episodes_per_platform}"
        )

    sel = _choose_episode_samples(
        index_df=index_df,
        quota=quota,
        episodes_per_platform=int(args.episodes_per_platform),
        seed=int(args.seed),
    )

    predictor = NeuralHeuristicPredictor(checkpoint=args.checkpoint, device=str(args.device))
    router_cfg = _router_args()
    policy = None
    policy_sha = None
    if str(args.router_mode) == "policy":
        from utils.router_policy_v1 import RouterPolicyV1, sha256_file

        policy = RouterPolicyV1.load(Path(args.policy_artifact))
        policy_sha = sha256_file(Path(args.policy_artifact) / "policy.json")

    platform_metrics: dict[str, dict] = {}
    artifacts: dict[str, str] = {
        "selected_cases_csv": str(out_dir / "selected_cases.csv"),
        "report_md": str(args.report_md),
    }
    if policy_sha is not None:
        artifacts["policy_artifact_dir"] = str(Path(args.policy_artifact))
        artifacts["policy_json_sha256"] = str(policy_sha)
    sel.to_csv(out_dir / "selected_cases.csv", index=False)

    for i_pf, pf in enumerate(_platforms()):
        print(f"[phase12] platform={pf.name}")
        ep_rows: list[dict] = []
        cy_rows: list[dict] = []

        for i_ep, r in sel.iterrows():
            sample_path = args.dataset_root / args.split / str(r["sample_name"])
            if not sample_path.exists():
                raise FileNotFoundError(sample_path)
            ep_rng = np.random.default_rng(
                _stable_seed(sample_name=str(r["sample_name"]), base_seed=int(args.seed), episode_idx=int(i_ep))
            )
            ep, cy = _simulate_episode(
                row=r,
                sample_path=sample_path,
                predictor=predictor,
                router_cfg=router_cfg,
                router_mode=str(args.router_mode),
                policy=policy,
                platform=pf,
                rng=ep_rng,
                args=args,
            )
            ep_rows.append(ep)
            cy_rows.extend(cy)
            if (i_ep + 1) % 20 == 0 or (i_ep + 1) == len(sel):
                succ = float(np.mean([float(x["success"]) for x in ep_rows])) if ep_rows else 0.0
                print(f"[phase12] {pf.name} processed {i_ep + 1}/{len(sel)} episodes, success={succ:.4f}")

        pf_dir = out_dir / "platforms" / pf.name
        pf_dir.mkdir(parents=True, exist_ok=True)
        df_ep = pd.DataFrame(ep_rows)
        df_cy = pd.DataFrame(cy_rows)
        ep_csv = pf_dir / "episodes.csv"
        cy_csv = pf_dir / "cycles.csv"
        df_ep.to_csv(ep_csv, index=False)
        df_cy.to_csv(cy_csv, index=False)
        artifacts[f"{pf.name}_episodes_csv"] = str(ep_csv)
        artifacts[f"{pf.name}_cycles_csv"] = str(cy_csv)
        platform_metrics[pf.name] = _summarize_platform(df_ep=df_ep, df_cy=df_cy)

    exp3_drift = _exp_de_drift_pct(
        base_csv=args.exp3_base_csv,
        new_csv=args.exp3_new_csv,
        experiment="exp3_ablation",
        method="Full",
    )
    exp4_drift = _exp_de_drift_pct(
        base_csv=args.exp4_base_csv,
        new_csv=args.exp4_new_csv,
        experiment="exp4_public_kinodynamic",
        method="Ours",
    )
    exp_drift_ok = bool(
        (not math.isnan(exp3_drift))
        and (not math.isnan(exp4_drift))
        and (abs(exp3_drift) <= float(args.max_de_drift_pct) + 1e-12)
        and (abs(exp4_drift) <= float(args.max_de_drift_pct) + 1e-12)
    )

    # Gate check.
    gate = {
        "platform_count_ge_2": bool(len(platform_metrics) >= 2),
        "episodes_per_platform_ge_500": bool(
            all(int(m["num_episodes"]) >= 500 for m in platform_metrics.values())
        ),
        "success_ge_97pct_each": bool(
            all(float(m["success_rate"]) >= 0.97 for m in platform_metrics.values())
        ),
        "dynamic_episode_ratio_ge_30pct_each": bool(
            all(float(m["dynamic_episode_ratio"]) >= float(args.min_dynamic_episode_ratio) for m in platform_metrics.values())
        ),
        "catastrophic_collision_zero_each": bool(
            all(int(m["catastrophic_collision_count"]) == 0 for m in platform_metrics.values())
        ),
        "p95_latency_le_50ms_each": bool(
            all(float(m["latency_p95_ms"]) <= 50.0 for m in platform_metrics.values())
        ),
        "p99_latency_le_80ms_each": bool(
            all(float(m["latency_p99_ms"]) <= 80.0 for m in platform_metrics.values())
        ),
        "exp3_exp4_dE_drift_abs_le_0_5pct": bool(exp_drift_ok),
    }

    stats = {
        "version": "router_phase12_realworld_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "platforms": [k for k in platform_metrics.keys()],
        "platform_profiles": [asdict(pf) for pf in _platforms()],
        "config": {
            "dataset_root": str(args.dataset_root),
            "split": str(args.split),
            "checkpoint": str(args.checkpoint),
            "device": str(args.device),
            "episodes_per_platform": int(args.episodes_per_platform),
            "episode_quota": quota,
            "max_cycles": int(args.max_cycles),
            "goal_tolerance_m": float(args.goal_tolerance_m),
            "max_hold_cycles": int(args.max_hold_cycles),
            "dynamic_obstacles": int(args.dynamic_obstacles),
            "dynamic_episode_prob": float(args.dynamic_episode_prob),
            "min_dynamic_episode_ratio": float(args.min_dynamic_episode_ratio),
            "dynamic_radius_m": float(args.dynamic_radius_m),
            "dynamic_min_travel_m": float(args.dynamic_min_travel_m),
            "perception_fp_rate": float(args.perception_fp_rate),
            "perception_fn_rate": float(args.perception_fn_rate),
            "max_de_drift_pct": float(args.max_de_drift_pct),
            "exp3_base_csv": str(args.exp3_base_csv),
            "exp3_new_csv": str(args.exp3_new_csv),
            "exp4_base_csv": str(args.exp4_base_csv),
            "exp4_new_csv": str(args.exp4_new_csv),
            "seed": int(args.seed),
            "router_mode": str(args.router_mode),
            "policy_artifact_dir": str(Path(args.policy_artifact)) if policy_sha is not None else "",
            "policy_json_sha256": str(policy_sha) if policy_sha is not None else "",
        },
        "platform_metrics": platform_metrics,
        "exp_drift": {
            "exp3_full_dE_drift_pct": float(exp3_drift),
            "exp4_ours_dE_drift_pct": float(exp4_drift),
        },
        "gate_check": gate,
        "artifacts": artifacts,
    }
    stats_path = out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    _write_report(args.report_md, stats=stats)

    print(f"[phase12] stats={stats_path}")
    print(f"[phase12] report={args.report_md}")
    print(f"[phase12] gate={gate}")
    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("Phase-12 gate failed. Check outputs/router_phase12_realworld_v1/stats.json")


if __name__ == "__main__":
    main()
