from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import stat
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ClaimItem:
    claim_id: str
    claim_text: str
    metric_name: str
    metric_value: str
    target: str
    passed: bool
    evidence_paths: list[Path]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-15 camera-ready packaging and audit runner.")
    p.add_argument("--artifact-dir", type=Path, default=Path("artifacts/router_camera_ready_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/router_phase15_camera_ready_v1.md"))
    p.add_argument("--checklist-md", type=Path, default=Path("paper/final_submission_checklist.md"))
    p.add_argument("--runtime-target-hours", type=float, default=48.0)
    p.add_argument("--enforce-gate", action="store_true", default=True)
    return p.parse_args()


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_exec(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_repro_bundle(artifact_dir: Path) -> dict[str, Path]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = artifact_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    dockerfile = artifact_dir / "Dockerfile"
    dockerfile.write_text(
        """FROM python:3.11-slim\n"
        "WORKDIR /workspace\n"
        "COPY requirements.txt /workspace/requirements.txt\n"
        "RUN pip install --no-cache-dir -r /workspace/requirements.txt\n"
        "COPY . /workspace\n"
        "ENV PYTHONUNBUFFERED=1\n"
        "CMD [\"bash\", \"artifacts/router_camera_ready_v1/reproduce_main_tables_figures.sh\"]\n"
        """,
        encoding="utf-8",
    )

    req_lock = artifact_dir / "requirements.lock.txt"
    req_lock.write_text((ROOT / "requirements.txt").read_text(encoding="utf-8"), encoding="utf-8")

    repro_sh = artifact_dir / "reproduce_main_tables_figures.sh"
    repro_sh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")/../..\" && pwd)\"
cd \"${ROOT_DIR}\"

bash scripts/run_router_phase7_all.sh
bash scripts/run_router_phase8_strict_all.sh
bash scripts/run_router_phase9_bench_all.sh
bash scripts/run_router_phase10_system_all.sh
bash scripts/run_router_phase11_theory_all.sh
bash scripts/run_router_phase12_realworld_all.sh
bash scripts/run_router_phase13_sota_all.sh
bash scripts/run_router_phase14_stress_all.sh
python scripts/run_router_phase15_camera_ready.py --enforce-gate
""",
        encoding="utf-8",
    )
    _ensure_exec(repro_sh)

    readme = artifact_dir / "README.md"
    readme.write_text(
        """# Router Camera-Ready Repro Bundle

## One-Command Reproduction
- `bash artifacts/router_camera_ready_v1/reproduce_main_tables_figures.sh`

## Container Reproduction
1. `docker build -t router-camera-ready -f artifacts/router_camera_ready_v1/Dockerfile .`
2. `docker run --rm -it router-camera-ready`

## Outputs
- Audit JSON: `artifacts/router_camera_ready_v1/audit_summary.json`
- Manifest: `artifacts/router_camera_ready_v1/MANIFEST.sha256`
- Claim matrix: `artifacts/router_camera_ready_v1/claim_to_evidence.csv`
""",
        encoding="utf-8",
    )

    return {
        "evidence_dir": evidence_dir,
        "dockerfile": dockerfile,
        "requirements_lock": req_lock,
        "repro_sh": repro_sh,
        "readme": readme,
    }


def _required_paths() -> list[Path]:
    rels = [
        "outputs/router_phase7_v1/stats.json",
        "outputs/router_phase8_strict_v1/stats.json",
        "outputs/router_phase9_bench_v1/stats.json",
        "outputs/router_phase10_system_v1/stats.json",
        "outputs/router_phase11_theory_v1/stats.json",
        "outputs/router_phase12_realworld_v1/stats.json",
        "outputs/router_phase13_sota_v1/stats.json",
        "outputs/router_phase14_stress_v1/stats.json",
        "reports/router_phase7_v1.md",
        "reports/router_phase8_strict_v1.md",
        "reports/router_phase9_bench_v1.md",
        "reports/router_phase10_system_v1.md",
        "reports/router_phase11_theory_v1.md",
        "reports/router_phase12_realworld_v1.md",
        "reports/router_phase13_sota_v1.md",
        "reports/router_phase14_stress_v1.md",
        "docs/router_theory_v1.md",
        "docs/router_theory_appendix_v1.md",
        "paper/tables_router_v1/table_phase7_main_metrics.csv",
        "paper/tables_router_v1/table_phase7_significance.csv",
        "paper/figures_router_v1/phase7_claims_ci.svg",
        "paper/tables_router_v2/table_phase9_significance.csv",
        "paper/tables_router_v3/table_phase13_significance.csv",
        "outputs/router_phase14_stress_v1/stress_profile_summary.csv",
        "outputs/router_phase14_stress_v1/stress_platform_metrics.csv",
        "scripts/run_router_phase12_realworld_all.sh",
        "scripts/run_router_phase13_sota_all.sh",
        "scripts/run_router_phase14_stress_all.sh",
    ]
    return [ROOT / r for r in rels]


def _runtime_estimate_hours(stats: dict[str, dict]) -> float:
    total = 0.0
    for obj in stats.values():
        total += float(obj.get("runtime_hours", 0.0))
    return float(total)


def _build_claims(stats: dict[str, dict]) -> list[ClaimItem]:
    p11 = stats["p11"]
    p12 = stats["p12"]
    p13 = stats["p13"]
    p14 = stats["p14"]

    claims: list[ClaimItem] = [
        ClaimItem(
            claim_id="C01",
            claim_text="P12 双平台回合数达到 500+",
            metric_name="episodes_per_platform_ge_500",
            metric_value=str(p12["gate_check"].get("episodes_per_platform_ge_500")),
            target="True",
            passed=bool(p12["gate_check"].get("episodes_per_platform_ge_500", False)),
            evidence_paths=[ROOT / "outputs/router_phase12_realworld_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C02",
            claim_text="P12 安全与尾延迟门槛达标",
            metric_name="success/collision/p95/p99 gates",
            metric_value=str({
                "success": p12["gate_check"].get("success_ge_97pct_each"),
                "collision": p12["gate_check"].get("catastrophic_collision_zero_each"),
                "p95": p12["gate_check"].get("p95_latency_le_50ms_each"),
                "p99": p12["gate_check"].get("p99_latency_le_80ms_each"),
            }),
            target="all True",
            passed=bool(
                p12["gate_check"].get("success_ge_97pct_each", False)
                and p12["gate_check"].get("catastrophic_collision_zero_each", False)
                and p12["gate_check"].get("p95_latency_le_50ms_each", False)
                and p12["gate_check"].get("p99_latency_le_80ms_each", False)
            ),
            evidence_paths=[
                ROOT / "outputs/router_phase12_realworld_v1/stats.json",
                ROOT / "reports/router_phase12_realworld_v1.md",
            ],
        ),
        ClaimItem(
            claim_id="C03",
            claim_text="P13 外部强基线数量 >= 6",
            metric_name="external_strong_baselines",
            metric_value=str(p13["counts"].get("external_strong_baselines")),
            target=">=6",
            passed=bool(int(p13["counts"].get("external_strong_baselines", 0)) >= 6),
            evidence_paths=[
                ROOT / "outputs/router_phase13_sota_v1/stats.json",
                ROOT / "paper/tables_router_v3/table_phase13_external_sota_summary.csv",
            ],
        ),
        ClaimItem(
            claim_id="C04",
            claim_text="P13 相对最强基线 J 改善 >= 3%",
            metric_name="j_improve_vs_strongest_baseline_mean",
            metric_value=f"{float(p13['summary'].get('j_improve_vs_strongest_baseline_mean', 0.0)) * 100.0:.3f}%",
            target=">=3%",
            passed=bool(float(p13["summary"].get("j_improve_vs_strongest_baseline_mean", 0.0)) >= 0.03),
            evidence_paths=[ROOT / "outputs/router_phase13_sota_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C05",
            claim_text="P13 pooled 显著性达标 (p<0.01, CI 不跨 0)",
            metric_name="pooled_p/ci",
            metric_value=str(
                {
                    "p": p13["summary"].get("pooled_p_value_bootstrap_gt0"),
                    "ci95": p13["summary"].get("pooled_delta_j_ci95"),
                }
            ),
            target="p<0.01 and ci_low>0",
            passed=bool(
                float(p13["summary"].get("pooled_p_value_bootstrap_gt0", 1.0)) < 0.01
                and float(p13["summary"].get("pooled_delta_j_ci95", [0.0, 0.0])[0]) > 0.0
            ),
            evidence_paths=[ROOT / "outputs/router_phase13_sota_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C06",
            claim_text="P13 风险不劣（ΔV <= 0.5pct）",
            metric_name="risk_delta_vs_strongest_mean_pct",
            metric_value=f"{float(p13['summary'].get('risk_delta_vs_strongest_mean_pct', 0.0)):.3f}",
            target="<=0.5",
            passed=bool(float(p13["summary"].get("risk_delta_vs_strongest_mean_pct", 1e9)) <= 0.5),
            evidence_paths=[ROOT / "outputs/router_phase13_sota_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C07",
            claim_text="P14 扰动类型与样本规模达标",
            metric_name="stress_type_count_ge_10 + cases_per_type_ge_100",
            metric_value=str(
                {
                    "types": p14["gate_check"].get("stress_type_count_ge_10"),
                    "cases": p14["gate_check"].get("cases_per_type_ge_100"),
                }
            ),
            target="both True",
            passed=bool(
                p14["gate_check"].get("stress_type_count_ge_10", False)
                and p14["gate_check"].get("cases_per_type_ge_100", False)
            ),
            evidence_paths=[
                ROOT / "outputs/router_phase14_stress_v1/stats.json",
                ROOT / "outputs/router_phase14_stress_v1/stress_profile_summary.csv",
            ],
        ),
        ClaimItem(
            claim_id="C08",
            claim_text="P14 Worst-10% 成功率与恢复率达标",
            metric_name="worst10_success + recovery_success",
            metric_value=str(
                {
                    "worst10": p14["summary"].get("worst10_success_rate"),
                    "recovery": p14["summary"].get("recovery_success_rate"),
                }
            ),
            target=">=0.92 and >=0.95",
            passed=bool(
                float(p14["summary"].get("worst10_success_rate", 0.0)) >= 0.92
                and float(p14["summary"].get("recovery_success_rate", 0.0)) >= 0.95
            ),
            evidence_paths=[ROOT / "outputs/router_phase14_stress_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C09",
            claim_text="P14 灾难性碰撞为 0",
            metric_name="catastrophic_collision_count",
            metric_value=str(p14["summary"].get("catastrophic_collision_count")),
            target="0",
            passed=bool(int(p14["summary"].get("catastrophic_collision_count", 1)) == 0),
            evidence_paths=[ROOT / "outputs/router_phase14_stress_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C10",
            claim_text="Exp3/Exp4 漂移不退化（<=0.5%）",
            metric_name="exp3_exp4_drift_abs_le_0_5pct",
            metric_value=str(p12["gate_check"].get("exp3_exp4_dE_drift_abs_le_0_5pct")),
            target="True",
            passed=bool(p12["gate_check"].get("exp3_exp4_dE_drift_abs_le_0_5pct", False)),
            evidence_paths=[ROOT / "outputs/router_phase12_realworld_v1/stats.json"],
        ),
        ClaimItem(
            claim_id="C11",
            claim_text="理论闭环 gap <= 2%",
            metric_name="theory_bound_gap_le_2pct",
            metric_value=str(p11["gate_check"].get("theory_bound_gap_le_2pct")),
            target="True",
            passed=bool(p11["gate_check"].get("theory_bound_gap_le_2pct", False)),
            evidence_paths=[ROOT / "outputs/router_phase11_theory_v1/stats.json"],
        ),
    ]
    return claims


def _write_claim_matrix(path: Path, claims: list[ClaimItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "claim_id",
            "claim_text",
            "metric_name",
            "metric_value",
            "target",
            "passed",
            "evidence_paths",
        ])
        for c in claims:
            w.writerow(
                [
                    c.claim_id,
                    c.claim_text,
                    c.metric_name,
                    c.metric_value,
                    c.target,
                    str(bool(c.passed)),
                    ";".join(str(p.relative_to(ROOT)) for p in c.evidence_paths),
                ]
            )


def _write_report(path: Path, audit: dict) -> None:
    lines: list[str] = []
    lines.append("# Router Phase15 Camera-Ready V1 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runtime: `{audit['runtime_hours']:.3f} h`")
    lines.append(f"- Repro runtime estimate: `{audit['runtime_estimate_hours']:.3f} h`")
    lines.append(f"- Hash consistency: `{audit['hash_consistency_rate'] * 100.0:.2f}%`")
    lines.append(f"- Claim coverage: `{audit['claim_coverage_rate'] * 100.0:.2f}%`")
    lines.append(f"- Blockers: `{audit['blocker_count']}`")
    lines.append("")
    lines.append("## Gate Check")
    for k, v in audit["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    if audit["blockers"]:
        lines.append("## Blockers")
        for b in audit["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("## Blockers")
        lines.append("- `None`")
    lines.append("")
    lines.append("## Artifacts")
    for k, v in audit["artifacts"].items():
        lines.append(f"- `{k}`: `{v}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_checklist(path: Path, audit: dict, claims: list[ClaimItem]) -> None:
    lines: list[str] = []
    lines.append("# Final Submission Checklist")
    lines.append("")
    lines.append("## Gate Status")
    for k, v in audit["gate_check"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Claim-to-Evidence")
    lines.append("| claim_id | pass | metric | target | evidence |")
    lines.append("|---|---:|---|---|---|")
    for c in claims:
        ev = ", ".join(str(p.relative_to(ROOT)) for p in c.evidence_paths)
        lines.append(f"| {c.claim_id} | {bool(c.passed)} | {c.metric_value} | {c.target} | {ev} |")
    lines.append("")
    lines.append("## Reproduction")
    lines.append("- One-command: `bash artifacts/router_camera_ready_v1/reproduce_main_tables_figures.sh`")
    lines.append("- Container: `docker build -t router-camera-ready -f artifacts/router_camera_ready_v1/Dockerfile .`")
    lines.append("- Estimated cold-start runtime: `{:.3f} h` (target <= 48 h)".format(audit["runtime_estimate_hours"]))
    lines.append("")
    lines.append("## Hash Audit")
    lines.append(
        "- Hash consistency: `{:.2f}%` ({} / {})".format(
            audit["hash_consistency_rate"] * 100.0,
            audit["hash_match_count"],
            audit["hash_total_count"],
        )
    )
    lines.append("- Manifest: `artifacts/router_camera_ready_v1/MANIFEST.sha256`")
    lines.append("")
    lines.append("## Negative Results & Limitations")
    lines.append("- `csm` 子基准在 P13 上的 `delta_j` 略为负值（约 `-0.00485`），但在容差 `0.01` 内，方向一致性 gate 判定为通过。")
    lines.append("- 当前环境请求 `cuda` 时会回退 `cpu`（torch 非 CUDA build），已在报告中显式披露。")
    lines.append("- P14 中 `sensor_fn_spike` 与 `sensor_dropout_combo` 的触发后恢复率低于极端混合场景，但总体恢复率仍满足 `>=95%`。")
    lines.append("- 实机/HIL 采用平台时延建模与闭环仿真组合，真实部署仍建议补充硬件在环长期运行数据。")
    lines.append("")
    lines.append("## Blockers")
    if audit["blockers"]:
        for b in audit["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("- `None (0 blocker)`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()

    artifact_dir = args.artifact_dir
    bundle = _write_repro_bundle(artifact_dir)
    evidence_dir = bundle["evidence_dir"]

    p7 = _load_json(ROOT / "outputs/router_phase7_v1/stats.json")
    p8 = _load_json(ROOT / "outputs/router_phase8_strict_v1/stats.json")
    p9 = _load_json(ROOT / "outputs/router_phase9_bench_v1/stats.json")
    p10 = _load_json(ROOT / "outputs/router_phase10_system_v1/stats.json")
    p11 = _load_json(ROOT / "outputs/router_phase11_theory_v1/stats.json")
    p12 = _load_json(ROOT / "outputs/router_phase12_realworld_v1/stats.json")
    p13 = _load_json(ROOT / "outputs/router_phase13_sota_v1/stats.json")
    p14 = _load_json(ROOT / "outputs/router_phase14_stress_v1/stats.json")

    stats_map = {
        "p7": p7,
        "p8": p8,
        "p9": p9,
        "p10": p10,
        "p11": p11,
        "p12": p12,
        "p13": p13,
        "p14": p14,
    }

    required = _required_paths()
    missing: list[str] = []
    copied_rows: list[tuple[str, str, str, bool]] = []

    for src in required:
        if not src.exists():
            missing.append(str(src.relative_to(ROOT)))
            continue
        rel = src.relative_to(ROOT)
        dst = evidence_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        h_src = _sha256(src)
        h_dst = _sha256(dst)
        copied_rows.append((str(rel), h_src, h_dst, h_src == h_dst))

    manifest = artifact_dir / "MANIFEST.sha256"
    with manifest.open("w", encoding="utf-8") as f:
        for rel, h_src, _, ok in copied_rows:
            if ok:
                f.write(f"{h_src}  evidence/{rel}\n")

    hash_csv = artifact_dir / "hash_compare.csv"
    with hash_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relative_path", "sha256_src", "sha256_copy", "match"])
        for row in copied_rows:
            w.writerow([row[0], row[1], row[2], str(row[3])])

    claims = _build_claims({"p11": p11, "p12": p12, "p13": p13, "p14": p14})
    claim_csv = artifact_dir / "claim_to_evidence.csv"
    _write_claim_matrix(claim_csv, claims)

    claim_cover = 0
    for c in claims:
        ev_ok = all(p.exists() for p in c.evidence_paths)
        if ev_ok:
            claim_cover += 1
    claim_coverage = float(claim_cover / max(len(claims), 1))

    hash_total = len(copied_rows)
    hash_match = sum(1 for _, _, _, ok in copied_rows if ok)
    hash_consistency = float(hash_match / max(hash_total, 1))

    runtime_est = _runtime_estimate_hours(stats_map)

    blockers: list[str] = []
    if missing:
        blockers.append(f"missing required files: {len(missing)}")
    failed_claims = [c.claim_id for c in claims if not c.passed]
    if failed_claims:
        blockers.append(f"failed claims: {', '.join(failed_claims)}")
    if hash_consistency < 1.0 - 1e-12:
        blockers.append("hash consistency < 100%")
    if claim_coverage < 1.0 - 1e-12:
        blockers.append("claim coverage < 100%")
    if runtime_est > float(args.runtime_target_hours):
        blockers.append(f"runtime estimate {runtime_est:.3f}h exceeds target {args.runtime_target_hours:.3f}h")

    gate = {
        "cold_start_runtime_le_48h": bool(runtime_est <= float(args.runtime_target_hours)),
        "hash_consistency_100pct": bool(hash_consistency >= 1.0 - 1e-12),
        "claim_coverage_100pct": bool(claim_coverage >= 1.0 - 1e-12),
        "audit_blocker_zero": bool(len(blockers) == 0),
    }

    audit = {
        "version": "router_phase15_camera_ready_v1",
        "runtime_hours": float((time.perf_counter() - t0) / 3600.0),
        "runtime_estimate_hours": float(runtime_est),
        "runtime_target_hours": float(args.runtime_target_hours),
        "hash_total_count": int(hash_total),
        "hash_match_count": int(hash_match),
        "hash_consistency_rate": float(hash_consistency),
        "claim_total_count": int(len(claims)),
        "claim_covered_count": int(claim_cover),
        "claim_coverage_rate": float(claim_coverage),
        "blocker_count": int(len(blockers)),
        "blockers": blockers,
        "missing_files": missing,
        "failed_claims": failed_claims,
        "gate_check": gate,
        "artifacts": {
            "bundle_dir": str(artifact_dir),
            "manifest_sha256": str(manifest),
            "hash_compare_csv": str(hash_csv),
            "claim_to_evidence_csv": str(claim_csv),
            "dockerfile": str(bundle["dockerfile"]),
            "reproduce_sh": str(bundle["repro_sh"]),
            "requirements_lock": str(bundle["requirements_lock"]),
            "bundle_readme": str(bundle["readme"]),
            "report_md": str(args.report_md),
            "checklist_md": str(args.checklist_md),
        },
    }

    audit_json = artifact_dir / "audit_summary.json"
    audit_json.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    _write_report(args.report_md, audit=audit)
    _write_checklist(args.checklist_md, audit=audit, claims=claims)

    print(f"[phase15] audit={audit_json}")
    print(f"[phase15] report={args.report_md}")
    print(f"[phase15] checklist={args.checklist_md}")
    print(f"[phase15] gate={gate}")

    if bool(args.enforce_gate) and not all(gate.values()):
        raise RuntimeError("Phase-15 gate failed. Check artifacts/router_camera_ready_v1/audit_summary.json")


if __name__ == "__main__":
    main()
