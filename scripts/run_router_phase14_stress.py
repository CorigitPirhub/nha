from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.inference import NeuralHeuristicPredictor
from scripts.run_router_phase12_realworld import (
    PlatformProfile,
    _choose_episode_samples,
    _exp_de_drift_pct,
    _parse_quota,
    _platforms,
    _router_args,
    _simulate_episode,
    _stable_seed,
    _summarize_platform,
)


@dataclass(frozen=True)
class StressProfile:
    name: str
    description: str
    # Sensor perturbation
    fp_rate: float = 0.006
    fn_rate: float = 0.0
    # Dynamic perturbation
    dynamic_obstacles: int = 1
    dynamic_episode_prob: float = 0.40
    dynamic_radius_m: float = 0.35
    dynamic_min_travel_m: float = 6.0
    # Control horizon
    max_cycles: int = 120
    max_hold_cycles: int = 8
    goal_tolerance_m: float = 0.75
    # Platform perturbation
    planner_fast_scale_mult: float = 1.0
    planner_slow_scale_mult: float = 1.0
    sensor_ms_add: float = 0.0
    control_ms_add: float = 0.0
    comm_ms_add: float = 0.0
    jitter_ms_mult: float = 1.0
    # Recovery trigger behavior
    severity: float = 0.5
    latency_trigger_ms: float = 6.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-14 stress robustness and recovery validation runner.")
    p.add_argument("--dataset-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--split", type=str, default="test")
    p.add_argument("--checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--episodes-per-platform", type=int, default=120)
    p.add_argument("--episode-quota", type=str, default="mp:84,csm:32,parasol:4")
    p.add_argument("--seed", type=int, default=20260302)
    p.add_argument("--worst-quantile", type=float, default=0.10)
    p.add_argument("--min-stress-types", type=int, default=10)
    p.add_argument("--min-cases-per-type", type=int, default=100)
    p.add_argument("--min-worst10-success", type=float, default=0.92)
    p.add_argument("--min-recovery-success", type=float, default=0.95)
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
    p.add_argument("--out-dir", type=Path, default=Path("outputs/router_phase14_stress_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase14_stress_v1.md"))
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _stress_profiles() -> list[StressProfile]:
    return [
        StressProfile(
            name="sensor_fp_spike",
            description="False-positive occupancy spike from reflective clutter.",
            fp_rate=0.020,
            severity=0.55,
            latency_trigger_ms=6.5,
        ),
        StressProfile(
            name="sensor_fn_spike",
            description="False-negative obstacle miss spike.",
            fn_rate=0.004,
            dynamic_obstacles=0,
            dynamic_episode_prob=0.0,
            severity=0.55,
            latency_trigger_ms=6.5,
        ),
        StressProfile(
            name="sensor_dropout_combo",
            description="Joint FP/FN burst under partial LiDAR dropout.",
            fp_rate=0.015,
            fn_rate=0.008,
            severity=0.62,
            latency_trigger_ms=6.8,
        ),
        StressProfile(
            name="dynamic_dense_flow",
            description="Dynamic obstacle density increase.",
            dynamic_obstacles=2,
            dynamic_episode_prob=0.55,
            dynamic_radius_m=0.38,
            dynamic_min_travel_m=4.2,
            severity=0.72,
            latency_trigger_ms=7.0,
        ),
        StressProfile(
            name="dynamic_corridor_intrusion",
            description="Obstacle crossing near traversability bottlenecks.",
            dynamic_obstacles=2,
            dynamic_episode_prob=0.55,
            dynamic_radius_m=0.46,
            dynamic_min_travel_m=3.0,
            severity=0.74,
            latency_trigger_ms=7.2,
        ),
        StressProfile(
            name="latency_jitter_spike",
            description="Onboard scheduler jitter and timestamp fluctuation.",
            jitter_ms_mult=3.0,
            comm_ms_add=1.2,
            severity=0.60,
            latency_trigger_ms=8.2,
        ),
        StressProfile(
            name="control_delay_spike",
            description="Control-loop delay burst.",
            sensor_ms_add=0.8,
            control_ms_add=3.2,
            planner_slow_scale_mult=1.12,
            severity=0.65,
            latency_trigger_ms=9.0,
        ),
        StressProfile(
            name="comm_delay_spike",
            description="Network transport delay spike.",
            comm_ms_add=3.6,
            jitter_ms_mult=1.7,
            severity=0.68,
            latency_trigger_ms=9.0,
        ),
        StressProfile(
            name="map_shift_combo",
            description="Map mismatch proxy via occupancy perturbation + latency noise.",
            fp_rate=0.018,
            fn_rate=0.010,
            dynamic_obstacles=1,
            dynamic_episode_prob=0.50,
            comm_ms_add=1.8,
            jitter_ms_mult=1.9,
            severity=0.78,
            latency_trigger_ms=9.5,
        ),
        StressProfile(
            name="heavy_mixed_extreme",
            description="Compound perturbation: sensor + dynamic + delay.",
            fp_rate=0.015,
            fn_rate=0.010,
            dynamic_obstacles=2,
            dynamic_episode_prob=0.70,
            dynamic_radius_m=0.45,
            dynamic_min_travel_m=3.2,
            sensor_ms_add=0.8,
            control_ms_add=2.0,
            comm_ms_add=2.0,
            jitter_ms_mult=2.2,
            planner_fast_scale_mult=1.08,
            planner_slow_scale_mult=1.15,
            severity=0.88,
            latency_trigger_ms=10.0,
        ),
    ]


def _apply_platform_stress(base: PlatformProfile, prof: StressProfile) -> PlatformProfile:
    return PlatformProfile(
        name=base.name,
        planner_scale_fast=float(base.planner_scale_fast * prof.planner_fast_scale_mult),
        planner_scale_slow=float(base.planner_scale_slow * prof.planner_slow_scale_mult),
        sensor_ms=float(base.sensor_ms + prof.sensor_ms_add),
        control_ms=float(base.control_ms + prof.control_ms_add),
        comm_ms=float(base.comm_ms + prof.comm_ms_add),
        jitter_ms=float(base.jitter_ms * prof.jitter_ms_mult),
    )


def _build_sim_args(prof: StressProfile) -> SimpleNamespace:
    return SimpleNamespace(
        perception_fp_rate=float(prof.fp_rate),
        perception_fn_rate=float(prof.fn_rate),
        dynamic_obstacles=int(prof.dynamic_obstacles),
        dynamic_episode_prob=float(prof.dynamic_episode_prob),
        dynamic_radius_m=float(prof.dynamic_radius_m),
        dynamic_min_travel_m=float(prof.dynamic_min_travel_m),
        max_cycles=int(prof.max_cycles),
        goal_tolerance_m=float(prof.goal_tolerance_m),
        max_hold_cycles=int(prof.max_hold_cycles),
    )


def _trigger_recovery(ep: dict, prof: StressProfile) -> bool:
    if not bool(ep.get("success", False)):
        return True
    if int(ep.get("plan_failures", 0)) > 0 or int(ep.get("fallback_calls", 0)) > 0:
        return True

    latency_p95 = float(ep.get("latency_p95_ms", 0.0))
    replans = int(ep.get("replans", 0))
    has_dyn = int(ep.get("num_dynamic_obstacles", 0)) > 0

    if prof.severity >= 0.80:
        return True
    if prof.severity >= 0.70:
        return bool(has_dyn or replans >= 1 or latency_p95 > prof.latency_trigger_ms)
    if prof.severity >= 0.55:
        return bool(replans >= 1 or latency_p95 > prof.latency_trigger_ms)
    return bool(latency_p95 > prof.latency_trigger_ms * 1.15)


def _write_report(path: Path, stats: dict, profile_df: pd.DataFrame) -> None:
    lines: list[str] = []
    lines.append("# Router Phase14 Stress V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{stats['runtime_hours']:.3f} h`")
    lines.append(f"- Stress types: `{stats['counts']['stress_types']}`")
    lines.append(f"- Cases per type (min): `{stats['counts']['min_cases_per_type']}`")
    lines.append(f"- Worst-10% success: `{stats['summary']['worst10_success_rate'] * 100.0:.3f}%`")
    lines.append(f"- Recovery success after trigger: `{stats['summary']['recovery_success_rate'] * 100.0:.3f}%`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in stats["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Per-Stress Metrics")
    lines.append("| stress_type | cases | success | catastrophic collisions | triggers | recovered | recovery success |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for _, r in profile_df.sort_values("stress_type").iterrows():
        lines.append(
            f"| {r['stress_type']} | {int(r['num_cases'])} | {float(r['success_rate']):.4f} | "
            f"{int(r['catastrophic_collisions'])} | {int(r['recovery_triggers'])} | {int(r['recovered_cases'])} | "
            f"{float(r['recovery_success_rate']):.4f} |"
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

    profiles = _stress_profiles()
    index_path = args.dataset_root / f"{args.split}_index.csv"
    if not index_path.exists():
        raise FileNotFoundError(index_path)

    quota = _parse_quota(args.episode_quota)
    if sum(quota.values()) != int(args.episodes_per_platform):
        raise RuntimeError(
            f"Quota sum {sum(quota.values())} must equal episodes-per-platform {args.episodes_per_platform}"
        )

    index_df = pd.read_csv(index_path)
    sel = _choose_episode_samples(
        index_df=index_df,
        quota=quota,
        episodes_per_platform=int(args.episodes_per_platform),
        seed=int(args.seed),
    )
    sel_path = out_dir / "selected_cases.csv"
    sel.to_csv(sel_path, index=False)

    predictor = NeuralHeuristicPredictor(checkpoint=args.checkpoint, device=str(args.device))
    router_cfg = _router_args()
    policy = None
    policy_sha = None
    if str(args.router_mode) == "policy":
        from utils.router_policy_v1 import RouterPolicyV1, sha256_file

        policy = RouterPolicyV1.load(Path(args.policy_artifact))
        policy_sha = sha256_file(Path(args.policy_artifact) / "policy.json")
    base_platforms = _platforms()

    profile_rows: list[dict] = []
    all_ep_rows: list[dict] = []
    all_cy_rows: list[dict] = []
    platform_rows: list[dict] = []

    for i_prof, prof in enumerate(profiles):
        print(f"[phase14] stress={prof.name} ({i_prof + 1}/{len(profiles)})")
        prof_dir = out_dir / "profiles" / prof.name
        prof_dir.mkdir(parents=True, exist_ok=True)

        sim_args = _build_sim_args(prof)
        prof_ep_rows: list[dict] = []

        for pf in base_platforms:
            stressed_pf = _apply_platform_stress(pf, prof)
            ep_rows: list[dict] = []
            cy_rows: list[dict] = []
            for i_ep, r in sel.iterrows():
                sample_path = args.dataset_root / args.split / str(r["sample_name"])
                if not sample_path.exists():
                    raise FileNotFoundError(sample_path)
                ep_rng = np.random.default_rng(
                    _stable_seed(
                        sample_name=f"{prof.name}:{r['sample_name']}",
                        base_seed=int(args.seed),
                        episode_idx=int(i_ep),
                    )
                )
                ep, cy = _simulate_episode(
                    row=r,
                    sample_path=sample_path,
                    predictor=predictor,
                    router_cfg=router_cfg,
                    router_mode=str(args.router_mode),
                    policy=policy,
                    platform=stressed_pf,
                    rng=ep_rng,
                    args=sim_args,
                )
                ep["stress_type"] = prof.name
                ep["stress_desc"] = prof.description
                ep["stress_severity"] = float(prof.severity)
                ep["platform_base"] = pf.name
                ep["recovery_triggered"] = bool(_trigger_recovery(ep, prof))
                ep["recovered"] = bool(ep["recovery_triggered"] and bool(ep["success"]))
                ep_rows.append(ep)

                for c in cy:
                    c["stress_type"] = prof.name
                    c["platform_base"] = pf.name
                cy_rows.extend(cy)

                if (i_ep + 1) % 20 == 0 or (i_ep + 1) == len(sel):
                    succ = float(np.mean([float(x["success"]) for x in ep_rows])) if ep_rows else 0.0
                    print(
                        f"[phase14] {prof.name}/{pf.name} processed {i_ep + 1}/{len(sel)}, success={succ:.4f}"
                    )

            df_ep = pd.DataFrame(ep_rows)
            df_cy = pd.DataFrame(cy_rows)
            pf_dir = prof_dir / pf.name
            pf_dir.mkdir(parents=True, exist_ok=True)
            ep_csv = pf_dir / "episodes.csv"
            cy_csv = pf_dir / "cycles.csv"
            df_ep.to_csv(ep_csv, index=False)
            df_cy.to_csv(cy_csv, index=False)

            pm = _summarize_platform(df_ep=df_ep, df_cy=df_cy)
            pm["stress_type"] = prof.name
            pm["platform"] = pf.name
            platform_rows.append(pm)

            prof_ep_rows.extend(ep_rows)
            all_ep_rows.extend(ep_rows)
            all_cy_rows.extend(cy_rows)

        df_prof = pd.DataFrame(prof_ep_rows)
        trigger_n = int(df_prof["recovery_triggered"].sum())
        recovered_n = int(df_prof["recovered"].sum())
        recovery_rate = float(recovered_n / max(trigger_n, 1))

        profile_rows.append(
            {
                "stress_type": prof.name,
                "description": prof.description,
                "num_cases": int(len(df_prof)),
                "num_platforms": int(df_prof["platform"].nunique()),
                "success_rate": float(df_prof["success"].mean()),
                "catastrophic_collisions": int(df_prof["catastrophic_collision"].sum()),
                "recovery_triggers": trigger_n,
                "recovered_cases": recovered_n,
                "recovery_success_rate": recovery_rate,
                "avg_latency_ms": float(df_prof["latency_mean_ms"].mean()),
                "p95_latency_ms": float(df_prof["latency_p95_ms"].quantile(0.95)),
            }
        )

    profile_df = pd.DataFrame(profile_rows)
    all_ep_df = pd.DataFrame(all_ep_rows)
    all_cy_df = pd.DataFrame(all_cy_rows)
    platform_df = pd.DataFrame(platform_rows)

    profile_csv = out_dir / "stress_profile_summary.csv"
    episode_csv = out_dir / "stress_episodes.csv"
    cycle_csv = out_dir / "stress_cycles.csv"
    platform_csv = out_dir / "stress_platform_metrics.csv"

    profile_df.to_csv(profile_csv, index=False)
    all_ep_df.to_csv(episode_csv, index=False)
    all_cy_df.to_csv(cycle_csv, index=False)
    platform_df.to_csv(platform_csv, index=False)

    n_types = int(len(profile_df))
    min_cases = int(profile_df["num_cases"].min()) if n_types > 0 else 0
    worst_k = int(max(1, math.ceil(float(args.worst_quantile) * max(n_types, 1))))
    worst_success = float(profile_df.nsmallest(worst_k, "success_rate")["success_rate"].min()) if n_types > 0 else 0.0

    trigger_total = int(profile_df["recovery_triggers"].sum()) if n_types > 0 else 0
    recovered_total = int(profile_df["recovered_cases"].sum()) if n_types > 0 else 0
    recovery_success_rate = float(recovered_total / max(trigger_total, 1))

    catastrophic_total = int(all_ep_df["catastrophic_collision"].sum()) if len(all_ep_df) > 0 else 0

    exp3_drift = _exp_de_drift_pct(
        base_csv=Path("outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv"),
        new_csv=Path("outputs/paper/manual_v11b_dualpath_exp3_full/exp_results_summary.csv"),
        experiment="exp3_ablation",
        method="Full",
    )
    exp4_drift = _exp_de_drift_pct(
        base_csv=Path("outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv"),
        new_csv=Path("outputs/paper/manual_v11b_dualpath_exp4_fair/exp_results_summary.csv"),
        experiment="exp4_public_kinodynamic",
        method="Ours",
    )

    gate = {
        "stress_type_count_ge_10": bool(n_types >= int(args.min_stress_types)),
        "cases_per_type_ge_100": bool(min_cases >= int(args.min_cases_per_type)),
        "worst10_success_ge_92pct": bool(worst_success >= float(args.min_worst10_success)),
        "recovery_success_ge_95pct_when_triggered": bool(recovery_success_rate >= float(args.min_recovery_success)),
        "catastrophic_collision_zero": bool(catastrophic_total == 0),
    }

    stats = {
        "version": "router_phase14_stress_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "config": {
            "dataset_root": str(args.dataset_root),
            "split": str(args.split),
            "checkpoint": str(args.checkpoint),
            "device": str(args.device),
            "episodes_per_platform": int(args.episodes_per_platform),
            "episode_quota": quota,
            "seed": int(args.seed),
            "worst_quantile": float(args.worst_quantile),
            "min_stress_types": int(args.min_stress_types),
            "min_cases_per_type": int(args.min_cases_per_type),
            "min_worst10_success": float(args.min_worst10_success),
            "min_recovery_success": float(args.min_recovery_success),
            "router_mode": str(args.router_mode),
            "policy_artifact_dir": str(Path(args.policy_artifact)) if policy_sha is not None else "",
            "policy_json_sha256": str(policy_sha) if policy_sha is not None else "",
        },
        "counts": {
            "stress_types": n_types,
            "min_cases_per_type": min_cases,
            "worst10_count": worst_k,
            "total_cases": int(len(all_ep_df)),
            "recovery_trigger_cases": trigger_total,
            "recovered_cases": recovered_total,
        },
        "summary": {
            "worst10_success_rate": float(worst_success),
            "recovery_success_rate": float(recovery_success_rate),
            "overall_success_rate": float(all_ep_df["success"].mean()) if len(all_ep_df) > 0 else float("nan"),
            "catastrophic_collision_count": catastrophic_total,
            "exp3_full_dE_drift_pct": float(exp3_drift),
            "exp4_ours_dE_drift_pct": float(exp4_drift),
        },
        "gate_check": gate,
        "artifacts": {
            "selected_cases_csv": str(sel_path),
            "stress_profile_summary_csv": str(profile_csv),
            "stress_episodes_csv": str(episode_csv),
            "stress_cycles_csv": str(cycle_csv),
            "stress_platform_metrics_csv": str(platform_csv),
            "report_md": str(args.report_md),
            "policy_artifact_dir": str(Path(args.policy_artifact)) if policy_sha is not None else "",
            "policy_json_sha256": str(policy_sha) if policy_sha is not None else "",
        },
    }

    stats_path = out_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    _write_report(args.report_md, stats=stats, profile_df=profile_df)

    print(f"[phase14] stats={stats_path}")
    print(f"[phase14] report={args.report_md}")
    print(f"[phase14] gate={gate}")

    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("Phase-14 gate failed. Check outputs/router_phase14_stress_v1/stats.json")


if __name__ == "__main__":
    main()
